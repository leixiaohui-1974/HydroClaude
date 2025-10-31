#!/usr/bin/env python3
"""
Test Different z_interface Selection Strategies for Well-Balanced Reconstruction

研究目标：
找到最优的z_interface选择方法，使Lake at Rest达到机器精度

测试策略：
1. MAX (current):     z* = max(z_b_L, z_b_R)  - 最保守
2. AVERAGE:           z* = 0.5*(z_b_L + z_b_R)  - 平均值
3. MIN:               z* = min(z_b_L, z_b_R)  - 最激进
4. UPWIND:            z* = z_b_L if u>0 else z_b_R  - 迎风
5. ADAPTIVE:          自适应选择

参考文献：
- Audusse et al. (2004) "A Fast and Stable Well-Balanced Scheme"
- Liang & Marche (2009) "Numerical resolution of well-balanced shallow water equations"
- Kurganov & Petrova (2007) "Central-upwind schemes"

作者: HydroClaude Team
日期: 2025-10-31
Phase: 9.2 - Well-Balanced Optimization
"""

import numpy as np
import sys
sys.path.insert(0, '.')

from solvers.godunov_fvm_solver import GodunvFVMSolver


class WellBalancedTester:
    """测试不同z_interface策略的Lake at Rest性能"""

    def __init__(self):
        self.results = {}

    def create_solver_with_strategy(self, strategy: str):
        """
        创建求解器并修改z_interface策略

        Args:
            strategy: 'max', 'average', 'min', 'upwind', 'adaptive'
        """
        # 基本配置
        L = 100.0
        n_cells = 100
        h0 = 10.0

        # 创建抛物线地形 (最大2m凸起)
        x = np.linspace(0, L, n_cells)
        z_b = 2.0 * (x - L/2)**2 / (L/2)**2

        # 创建求解器
        solver = GodunvFVMSolver(
            width=10.0,
            length=L,
            n_cells=n_cells,
            manning_n=0.0,  # 无摩阻（纯Lake at Rest）
            z_b=z_b,
            cfl=0.5,
            order=1,
            well_balanced=True,
            use_numba=True
        )

        # 初始条件：平水面
        h_init = np.full(n_cells, h0) - z_b
        Q_init = np.zeros(n_cells)
        bc_left = {'type': 'wall'}
        bc_right = {'type': 'wall'}

        solver.initialize(h_init, Q_init, bc_left, bc_right)

        # 修改z_interface策略
        self._patch_solver_strategy(solver, strategy)

        return solver

    def _patch_solver_strategy(self, solver, strategy: str):
        """
        通过monkey patching修改求解器的z_interface策略

        这是一个实验性方法，用于快速测试不同策略
        """
        original_hydrostatic = solver._hydrostatic_reconstruction

        if strategy == 'max':
            # 当前实现，不需要修改
            pass

        elif strategy == 'average':
            def hydrostatic_average(h_L, h_R, z_b_L, z_b_R):
                eta_L = h_L + z_b_L
                eta_R = h_R + z_b_R
                z_interface = 0.5 * (z_b_L + z_b_R)  # 平均值
                h_star_L = max(0.0, eta_L - z_interface)
                h_star_R = max(0.0, eta_R - z_interface)
                return h_star_L, h_star_R
            solver._hydrostatic_reconstruction = hydrostatic_average

        elif strategy == 'min':
            def hydrostatic_min(h_L, h_R, z_b_L, z_b_R):
                eta_L = h_L + z_b_L
                eta_R = h_R + z_b_R
                z_interface = min(z_b_L, z_b_R)  # 最小值
                h_star_L = max(0.0, eta_L - z_interface)
                h_star_R = max(0.0, eta_R - z_interface)
                return h_star_L, h_star_R
            solver._hydrostatic_reconstruction = hydrostatic_min

        elif strategy == 'upwind':
            def hydrostatic_upwind(h_L, h_R, z_b_L, z_b_R):
                eta_L = h_L + z_b_L
                eta_R = h_R + z_b_R

                # 计算界面流速（简单平均）
                A_L = max(h_L, 1e-6) * solver.B
                A_R = max(h_R, 1e-6) * solver.B
                # 注意：这里需要访问Q值，但在重构时Q可能不可用
                # 简化：假设静水，使用水面梯度判断
                if eta_L > eta_R:
                    z_interface = z_b_L  # 向右流动倾向，用左侧
                else:
                    z_interface = z_b_R  # 向左流动倾向，用右侧

                h_star_L = max(0.0, eta_L - z_interface)
                h_star_R = max(0.0, eta_R - z_interface)
                return h_star_L, h_star_R
            solver._hydrostatic_reconstruction = hydrostatic_upwind

        elif strategy == 'adaptive':
            def hydrostatic_adaptive(h_L, h_R, z_b_L, z_b_R):
                """
                自适应策略：
                - 如果水面基本水平（Lake at Rest），使用MIN（最激进，最小扰动）
                - 如果水面梯度大，使用MAX（最保守，最稳定）
                """
                eta_L = h_L + z_b_L
                eta_R = h_R + z_b_R

                # 判断标准
                eta_diff = abs(eta_L - eta_R)
                z_b_diff = abs(z_b_L - z_b_R)

                # 如果水面梯度远小于底坡梯度 → 接近Lake at Rest
                if eta_diff < 0.1 * z_b_diff and z_b_diff > 1e-10:
                    z_interface = min(z_b_L, z_b_R)  # 使用MIN
                else:
                    z_interface = max(z_b_L, z_b_R)  # 使用MAX

                h_star_L = max(0.0, eta_L - z_interface)
                h_star_R = max(0.0, eta_R - z_interface)
                return h_star_L, h_star_R
            solver._hydrostatic_reconstruction = hydrostatic_adaptive

        else:
            raise ValueError(f"Unknown strategy: {strategy}")

    def run_test(self, strategy: str, duration: float = 10.0):
        """
        运行单个策略的Lake at Rest测试

        Args:
            strategy: z_interface选择策略
            duration: 模拟时长（秒）

        Returns:
            性能指标字典
        """
        print(f"\n{'='*70}")
        print(f"Testing Strategy: {strategy.upper()}")
        print(f"{'='*70}")

        solver = self.create_solver_with_strategy(strategy)

        # 记录初始状态
        h_init = solver.h.copy()
        eta_init = solver.h + solver.z_b
        mass_init = np.sum(solver.h * solver.B * solver.dx)

        # 运行模拟
        step_count = 0
        while solver.t < duration:
            solver.step()
            step_count += 1

        # 计算扰动
        h_final = solver.h
        eta_final = solver.h + solver.z_b
        mass_final = np.sum(solver.h * solver.B * solver.dx)

        # 水面扰动（应该保持水平）
        eta_disturbance = np.max(np.abs(eta_final - eta_init))

        # 水深扰动
        h_disturbance = np.max(np.abs(h_final - h_init))

        # 流量扰动（应该保持零）
        Q_disturbance = np.max(np.abs(solver.Q))

        # 质量守恒
        mass_error = abs(mass_final - mass_init) / mass_init * 100

        # 结果
        result = {
            'strategy': strategy,
            'duration': solver.t,
            'steps': step_count,
            'eta_disturbance': eta_disturbance,
            'h_disturbance': h_disturbance,
            'Q_disturbance': Q_disturbance,
            'mass_error_pct': mass_error,
        }

        print(f"\nResults:")
        print(f"  Simulated time: {solver.t:.3f}s")
        print(f"  Steps: {step_count}")
        print(f"  Water surface disturbance: {eta_disturbance:.6e} m")
        print(f"  Water depth disturbance: {h_disturbance:.6e} m")
        print(f"  Discharge disturbance: {Q_disturbance:.6e} m³/s")
        print(f"  Mass conservation error: {mass_error:.6e} %")

        return result

    def run_all_strategies(self, duration: float = 10.0):
        """测试所有策略"""
        strategies = ['max', 'average', 'min', 'upwind', 'adaptive']

        print("\n" + "="*70)
        print("Z_INTERFACE STRATEGY COMPARISON FOR LAKE AT REST")
        print("="*70)
        print(f"\nConfiguration:")
        print(f"  Domain: 100m × 10m")
        print(f"  Cells: 100")
        print(f"  Topography: Parabolic (max 2m)")
        print(f"  Duration: {duration}s")
        print(f"  Manning n: 0.0 (frictionless)")

        for strategy in strategies:
            result = self.run_test(strategy, duration)
            self.results[strategy] = result

        self._print_summary()

    def _print_summary(self):
        """打印所有策略的对比总结"""
        print("\n" + "="*70)
        print("SUMMARY: Z_INTERFACE STRATEGY COMPARISON")
        print("="*70)

        # 表头
        print(f"\n{'Strategy':<12} {'η Disturb (m)':<15} {'Q Disturb':<15} {'Mass Err %':<15} {'Rating':<10}")
        print("-" * 70)

        # 找到最佳策略
        best_strategy = min(self.results.items(), key=lambda x: x[1]['eta_disturbance'])

        for strategy, result in self.results.items():
            eta_dist = result['eta_disturbance']
            Q_dist = result['Q_disturbance']
            mass_err = result['mass_error_pct']

            # 评级
            if eta_dist < 1e-10:
                rating = "⭐⭐⭐⭐⭐"
            elif eta_dist < 1e-6:
                rating = "⭐⭐⭐⭐"
            elif eta_dist < 1e-3:
                rating = "⭐⭐⭐"
            elif eta_dist < 1e-1:
                rating = "⭐⭐"
            else:
                rating = "⭐"

            # 标记最佳
            marker = " ← BEST" if strategy == best_strategy[0] else ""

            print(f"{strategy:<12} {eta_dist:<15.6e} {Q_dist:<15.6e} {mass_err:<15.6e} {rating:<10}{marker}")

        print("\n" + "="*70)
        print("RECOMMENDATION")
        print("="*70)

        best_name, best_result = best_strategy
        eta_best = best_result['eta_disturbance']

        print(f"\n✅ Best Strategy: {best_name.upper()}")
        print(f"   Water surface disturbance: {eta_best:.6e} m")

        if eta_best < 1e-10:
            print(f"   Status: ✅ MACHINE PRECISION - Excellent!")
            print(f"   Lake at Rest test: PASSED")
        elif eta_best < 1e-6:
            print(f"   Status: ⚠️  Near machine precision - Good")
            print(f"   Improvement: {best_result['eta_disturbance']} → {eta_best}")
        else:
            print(f"   Status: ❌ Still needs improvement")
            print(f"   Target: < 1e-10 m")

        print("\n" + "="*70)


if __name__ == '__main__':
    tester = WellBalancedTester()
    tester.run_all_strategies(duration=10.0)
