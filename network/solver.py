"""
网络求解器

实现河网系统的统一求解：
1. 按拓扑顺序求解各河段
2. 自动边界条件传递
3. 时间步长协调
4. 全局质量守恒验证

Stage 3 - Task 3.2.3

作者: HydroClaude Team
日期: 2025-10-29
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
import time

from .coupling import ReachCoupler, JunctionCoupler, BifurcationCoupler, StructureCoupler, PumpStationCoupler


class NetworkSolver:
    """
    河网求解器

    统一管理整个河网系统的求解过程。

    求解流程：
    1. 构建耦合器
    2. 确定拓扑顺序
    3. 按顺序求解各河段
    4. 传递边界条件
    5. 验证质量守恒

    Attributes:
        network: RiverNetwork实例
        couplers: 耦合器字典 {node_id: coupler}
        dt_global: 全局时间步长
        t: 当前时间
        solve_method: 求解方法 ('sequential', 'iterative')
    """

    def __init__(self, network, solve_method: str = 'sequential'):
        """
        初始化网络求解器

        Args:
            network: RiverNetwork实例
            solve_method: 求解方法
                - 'sequential': 顺序求解（默认）
                - 'iterative': 迭代求解
        """
        self.network = network
        self.solve_method = solve_method

        # 确保拓扑已构建
        if not self.network._topology_built:
            self.network.build_topology()

        # 耦合器
        self.couplers = {}
        self._build_couplers()

        # 时间管理
        self.t = 0.0
        self.dt_global = None
        self.time_history = []
        self.mass_error_history = []

        # 统计
        self.n_steps = 0
        self.total_time = 0.0

    def _build_couplers(self):
        """构建所有耦合器"""
        for node_id, node in self.network.nodes.items():
            n_upstream = len(node.upstream_reaches)
            n_downstream = len(node.downstream_reaches)

            if n_upstream == 0 or n_downstream == 0:
                # 边界节点，不需要耦合器
                continue

            if n_upstream == 1 and n_downstream == 1:
                # 检查节点类型
                from .pump_station import PumpStationNode

                if isinstance(node, PumpStationNode):
                    # 泵站节点，使用PumpStationCoupler
                    upstream_reach = self.network.reaches[node.upstream_reaches[0]]
                    downstream_reach = self.network.reaches[node.downstream_reaches[0]]
                    coupler = PumpStationCoupler(node, upstream_reach, downstream_reach)
                    self.couplers[node_id] = coupler
                elif hasattr(node, 'internal_structure') and node.internal_structure is not None:
                    # 内部建筑物，使用StructureCoupler
                    coupler = StructureCoupler(node.internal_structure)
                    self.couplers[node_id] = coupler
                else:
                    # 简单串联，使用ReachCoupler
                    upstream_reach = self.network.reaches[node.upstream_reaches[0]]
                    downstream_reach = self.network.reaches[node.downstream_reaches[0]]
                    coupler = ReachCoupler(upstream_reach, downstream_reach, node)
                    self.couplers[node_id] = coupler

            elif n_upstream > 1 and n_downstream == 1:
                # 汇流节点
                upstream_reaches = [self.network.reaches[rid]
                                  for rid in node.upstream_reaches]
                downstream_reach = self.network.reaches[node.downstream_reaches[0]]

                # 需要是JunctionNode
                from .nodes import JunctionNode
                if isinstance(node, JunctionNode):
                    coupler = JunctionCoupler(node, upstream_reaches, downstream_reach)
                    self.couplers[node_id] = coupler

            elif n_upstream == 1 and n_downstream > 1:
                # 分流节点
                upstream_reach = self.network.reaches[node.upstream_reaches[0]]
                downstream_reaches = [self.network.reaches[rid]
                                    for rid in node.downstream_reaches]

                # 需要是BifurcationNode
                from .nodes import BifurcationNode
                if isinstance(node, BifurcationNode):
                    coupler = BifurcationCoupler(node, upstream_reach, downstream_reaches)
                    self.couplers[node_id] = coupler

    def compute_global_dt(self, cfl: float = 0.5) -> float:
        """
        计算全局时间步长

        使用所有河段中最小的dt（CFL条件）

        Args:
            cfl: CFL数（默认0.5）

        Returns:
            全局时间步长 (s)
        """
        dt_list = []

        for reach in self.network.reaches.values():
            if reach.solver is None:
                continue

            # 计算该河段的dt
            if hasattr(reach.solver, 'compute_dt'):
                dt_reach = reach.solver.compute_dt(cfl=cfl)
            elif hasattr(reach.solver, 'dt'):
                dt_reach = reach.solver.dt
            else:
                # 默认值
                dt_reach = 1.0

            dt_list.append(dt_reach)

        if dt_list:
            dt_min = min(dt_list)
        else:
            dt_min = 1.0

        self.dt_global = dt_min
        return dt_min

    def step_sequential(self, dt: Optional[float] = None) -> float:
        """
        顺序求解一个时间步

        按拓扑顺序依次求解各河段，每次求解后立即传递边界条件。

        Args:
            dt: 时间步长，None则自动计算

        Returns:
            实际使用的时间步长
        """
        if dt is None:
            dt = self.compute_global_dt()

        # 1. 按拓扑顺序求解各河段
        for reach_id in self.network.topological_order:
            reach = self.network.reaches[reach_id]

            if reach.solver is None:
                continue

            # 求解该河段
            if hasattr(reach.solver, 'step'):
                reach.solver.step(dt)
            elif hasattr(reach.solver, 'solve'):
                reach.solver.solve()

        # 2. 传递边界条件
        self._transfer_boundary_conditions(dt=dt)

        # 3. 更新时间
        self.t += dt
        self.n_steps += 1

        return dt

    def step_iterative(self, dt: Optional[float] = None,
                      max_iter: int = 10, tol: float = 1e-4) -> Tuple[float, int]:
        """
        迭代求解一个时间步

        多次扫描网络，直到边界条件收敛。

        Args:
            dt: 时间步长
            max_iter: 最大迭代次数
            tol: 收敛容差

        Returns:
            (dt, n_iter): 时间步长，实际迭代次数
        """
        if dt is None:
            dt = self.compute_global_dt()

        for iteration in range(max_iter):
            # 求解所有河段
            for reach_id in self.network.topological_order:
                reach = self.network.reaches[reach_id]
                if reach.solver and hasattr(reach.solver, 'step'):
                    reach.solver.step(dt)

            # 传递边界条件
            self._transfer_boundary_conditions(dt=dt)

            # 检查收敛
            if self._check_convergence(tol):
                self.t += dt
                self.n_steps += 1
                return dt, iteration + 1

        # 未收敛
        print(f"Warning: Iterative solver did not converge after {max_iter} iterations")
        self.t += dt
        self.n_steps += 1
        return dt, max_iter

    def step(self, dt: Optional[float] = None):
        """
        求解一个时间步（根据solve_method选择方法）

        Args:
            dt: 时间步长

        Returns:
            时间步长（顺序）或 (dt, n_iter)（迭代）
        """
        if self.solve_method == 'sequential':
            return self.step_sequential(dt)
        elif self.solve_method == 'iterative':
            return self.step_iterative(dt)
        else:
            raise ValueError(f"Unknown solve_method: {self.solve_method}")

    def _transfer_boundary_conditions(self, dt: Optional[float] = None):
        """
        传递所有耦合器的边界条件

        Args:
            dt: 时间步长 (s)，用于泵站能耗计算
        """
        for node_id, coupler in self.couplers.items():
            if isinstance(coupler, ReachCoupler):
                coupler.transfer_boundary_conditions()
            elif isinstance(coupler, JunctionCoupler):
                coupler.couple()
            elif isinstance(coupler, BifurcationCoupler):
                coupler.couple()
            elif isinstance(coupler, StructureCoupler):
                coupler.couple()
            elif isinstance(coupler, PumpStationCoupler):
                coupler.couple(dt=dt)

    def _check_convergence(self, tol: float = 1e-4) -> bool:
        """
        检查迭代收敛

        检查所有耦合器的兼容性

        Args:
            tol: 容差

        Returns:
            是否收敛
        """
        for coupler in self.couplers.values():
            if isinstance(coupler, ReachCoupler):
                is_compatible, _ = coupler.check_compatibility(tol_h=tol, tol_Q=tol)
                if not is_compatible:
                    return False
        return True

    def run(self, t_end: float, dt: Optional[float] = None,
            output_interval: Optional[float] = None,
            verbose: bool = True) -> Dict:
        """
        运行网络模拟

        Args:
            t_end: 结束时间 (s)
            dt: 时间步长 (s)，None则自动计算
            output_interval: 输出间隔 (s)，None则不输出
            verbose: 是否打印进度

        Returns:
            模拟结果字典
        """
        if verbose:
            print(f"\n{'='*80}")
            print(f"运行网络模拟: {self.network.name}")
            print(f"{'='*80}")
            print(f"结束时间: {t_end:.1f} s")
            print(f"求解方法: {self.solve_method}")

        # 初始化
        self.t = 0.0
        self.n_steps = 0
        start_time = time.time()

        # 自动计算dt
        if dt is None:
            dt = self.compute_global_dt()
            if verbose:
                print(f"自动计算时间步长: {dt:.3f} s")

        # 输出控制
        next_output_time = 0.0 if output_interval else None

        # 时间循环
        while self.t < t_end:
            # 实际步长（最后一步可能较小）
            dt_actual = min(dt, t_end - self.t)

            # 求解
            self.step(dt_actual)

            # 输出
            if output_interval and self.t >= next_output_time:
                self._output_state(verbose)
                next_output_time += output_interval

            # 记录
            self.time_history.append(self.t)
            _, _, mass_error = self.network.check_global_mass_balance()
            self.mass_error_history.append(mass_error)

        # 结束
        self.total_time = time.time() - start_time

        if verbose:
            print(f"\n{'='*80}")
            print(f"模拟完成！")
            print(f"{'='*80}")
            self._print_summary()

        return self._get_results()

    def _output_state(self, verbose: bool = True):
        """输出当前状态"""
        if not verbose:
            return

        Q_in, Q_out, error = self.network.check_global_mass_balance()
        print(f"t={self.t:8.1f}s | 步数={self.n_steps:5d} | "
              f"Q_in={Q_in:8.2f} m³/s | Q_out={Q_out:8.2f} m³/s | "
              f"误差={error:6.3f}%")

    def _print_summary(self):
        """打印模拟摘要"""
        print(f"\n模拟统计:")
        print(f"  总时间: {self.total_time:.2f} s")
        print(f"  总步数: {self.n_steps}")
        print(f"  平均dt: {self.t/self.n_steps:.4f} s")
        print(f"  计算速度: {self.n_steps/self.total_time:.1f} steps/s")

        # 质量守恒
        if self.mass_error_history:
            max_error = max(self.mass_error_history)
            avg_error = np.mean(self.mass_error_history)
            print(f"\n质量守恒:")
            print(f"  最大误差: {max_error:.4f}%")
            print(f"  平均误差: {avg_error:.4f}%")

            if max_error < 1.0:
                print(f"  评价:  优秀 (< 1%)")
            elif max_error < 5.0:
                print(f"  评价: ️  良好 (< 5%)")
            else:
                print(f"  评价:  需改进 (> 5%)")

    def _get_results(self) -> Dict:
        """获取模拟结果"""
        return {
            't_end': self.t,
            'n_steps': self.n_steps,
            'total_time': self.total_time,
            'time_history': self.time_history,
            'mass_error_history': self.mass_error_history,
            'reaches': {
                reach_id: {
                    'h': reach.solver.h.copy() if hasattr(reach.solver, 'h') else None,
                    'Q': reach.solver.Q.copy() if hasattr(reach.solver, 'Q') else None
                }
                for reach_id, reach in self.network.reaches.items()
            }
        }

    def check_network_consistency(self, verbose: bool = True) -> Tuple[bool, List[str]]:
        """
        检查网络一致性

        验证所有耦合器的兼容性

        Args:
            verbose: 是否打印详细信息

        Returns:
            (is_consistent, problems): 是否一致，问题列表
        """
        problems = []

        for node_id, coupler in self.couplers.items():
            if isinstance(coupler, ReachCoupler):
                is_compatible, metrics = coupler.check_compatibility()

                if not is_compatible:
                    problems.append(
                        f"Node '{node_id}': Δh={metrics['delta_h']:.4f}m, "
                        f"ΔQ={metrics['delta_Q']:.4f}m³/s"
                    )

            elif isinstance(coupler, (JunctionCoupler, BifurcationCoupler)):
                is_balanced, error = coupler.check_mass_balance()

                if not is_balanced:
                    problems.append(
                        f"Node '{node_id}': Mass imbalance {error:.4f} m³/s"
                    )

        is_consistent = len(problems) == 0

        if verbose:
            print(f"\n网络一致性检查:")
            if is_consistent:
                print(f"   所有耦合器一致")
            else:
                print(f"   发现 {len(problems)} 个问题:")
                for problem in problems:
                    print(f"    - {problem}")

        return is_consistent, problems

    def plot_mass_balance_history(self):
        """绘制质量守恒历史"""
        try:
            import matplotlib.pyplot as plt

            fig, ax = plt.subplots(figsize=(12, 5))

            ax.plot(self.time_history, self.mass_error_history, 'b-', linewidth=2)
            ax.axhline(y=1.0, color='r', linestyle='--', label='1% 阈值')
            ax.axhline(y=5.0, color='orange', linestyle='--', label='5% 阈值')

            ax.set_xlabel('时间 (s)', fontsize=12)
            ax.set_ylabel('质量守恒误差 (%)', fontsize=12)
            ax.set_title(f'{self.network.name} - 质量守恒历史',
                        fontsize=14, fontweight='bold')
            ax.legend(fontsize=10)
            ax.grid(True, alpha=0.3)

            plt.tight_layout()
            return fig

        except ImportError:
            print("matplotlib not available")
            return None


# 便捷函数
def create_network_solver(network, solve_method: str = 'sequential') -> NetworkSolver:
    """
    创建网络求解器（便捷函数）

    Args:
        network: RiverNetwork实例
        solve_method: 求解方法 ('sequential', 'iterative')

    Returns:
        NetworkSolver实例
    """
    return NetworkSolver(network, solve_method=solve_method)


def solve_network(network, t_end: float, dt: Optional[float] = None,
                 solve_method: str = 'sequential', verbose: bool = True) -> Dict:
    """
    求解网络（便捷函数）

    Args:
        network: RiverNetwork实例
        t_end: 结束时间 (s)
        dt: 时间步长 (s)
        solve_method: 求解方法
        verbose: 是否打印信息

    Returns:
        模拟结果字典
    """
    solver = NetworkSolver(network, solve_method=solve_method)
    results = solver.run(t_end, dt=dt, verbose=verbose)
    return results


if __name__ == "__main__":
    """简单测试"""
    print("Network Solver Module")
    print("Provides unified solving for river networks")
    print()
    print("Main classes:")
    print("  - NetworkSolver: 统一网络求解器")
    print()
    print("Convenience functions:")
    print("  - create_network_solver(network)")
    print("  - solve_network(network, t_end)")
