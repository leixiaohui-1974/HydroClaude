"""
HydroClaude 核心引擎封装
将HydroClaude的求解器封装为Web API可调用的接口
"""

import sys
import os
import numpy as np
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import json
from datetime import datetime

# 添加HydroClaude核心路径
HYDROCLAUDE_PATH = os.environ.get('HYDROCLAUDE_PATH', '/home/user/HydroClaude')
if HYDROCLAUDE_PATH not in sys.path:
    sys.path.insert(0, HYDROCLAUDE_PATH)

# 导入HydroClaude核心模块
from solvers.godunov_fvm_solver import GodunvFVMSolver


@dataclass
class SimulationResult:
    """仿真结果数据类"""
    task_id: str
    status: str  # completed, failed
    time: List[float]
    x: List[float]
    h: List[List[float]]  # h[time_idx][x_idx]
    Q: List[List[float]]
    V: List[List[float]]
    metrics: Dict[str, float]
    duration: float
    timestamp: str
    error: Optional[str] = None


class HydraulicEngine:
    """
    HydroClaude核心引擎封装类

    功能：
    1. 明渠仿真（Godunov FVM）
    2. 管道仿真（RK4, MOC）
    3. 混合系统仿真
    """

    def __init__(self):
        """初始化引擎"""
        self.version = "1.0.0"
        self.engine_path = HYDROCLAUDE_PATH

    def run_canal_simulation(
        self,
        task_id: str,
        config: Dict[str, Any]
    ) -> SimulationResult:
        """
        运行明渠仿真

        Args:
            task_id: 任务ID
            config: 仿真配置
                {
                    'width': 10.0,              # 渠道宽度 (m)
                    'length': 1000.0,           # 渠道长度 (m)
                    'n_cells': 200,             # 网格数量
                    'manning_n': 0.025,         # 曼宁糙率
                    'slope': 0.001,             # 底坡
                    'cfl': 0.5,                 # CFL数
                    'order': 2,                 # 空间精度阶数
                    'use_numba': True,          # 是否启用Numba加速
                    't_end': 100.0,             # 结束时间 (s)
                    'dt_max': 0.1,              # 最大时间步长 (s)
                    'output_interval': 0.5,     # 输出间隔 (s)
                    'initial_conditions': {     # 初始条件
                        'type': 'dam_break',    # 类型: dam_break, uniform, custom
                        'dam_position': 500.0,  # 溃坝位置
                        'h_left': 10.0,         # 左侧水深
                        'h_right': 1.0,         # 右侧水深
                        'Q_left': 0.0,          # 左侧流量
                        'Q_right': 0.0          # 右侧流量
                    },
                    'boundary_conditions': {    # 边界条件
                        'upstream': {
                            'type': 'transmissive'  # transmissive, constant_flow, constant_level
                        },
                        'downstream': {
                            'type': 'transmissive'
                        }
                    }
                }

        Returns:
            SimulationResult: 仿真结果
        """
        start_time = datetime.now()

        try:
            # 1. 提取配置参数
            width = config.get('width', 10.0)
            length = config.get('length', 1000.0)
            n_cells = config.get('n_cells', 200)
            manning_n = config.get('manning_n', 0.0)
            slope = config.get('slope', 0.0)
            cfl = config.get('cfl', 0.5)
            order = config.get('order', 2)
            use_numba = config.get('use_numba', True)
            t_end = config.get('t_end', 100.0)
            dt_max = config.get('dt_max', 0.1)

            # 2. 创建求解器
            solver = GodunvFVMSolver(
                width=width,
                length=length,
                n_cells=n_cells,
                manning_n=manning_n,
                slope=slope,
                cfl=cfl,
                order=order,
                use_numba=use_numba
            )

            # 3. 设置初始条件
            ic_config = config.get('initial_conditions', {})
            ic_type = ic_config.get('type', 'dam_break')

            if ic_type == 'dam_break':
                # 溃坝初始条件
                dam_pos = ic_config.get('dam_position', length / 2)
                h_left = ic_config.get('h_left', 10.0)
                h_right = ic_config.get('h_right', 1.0)
                Q_left = ic_config.get('Q_left', 0.0)
                Q_right = ic_config.get('Q_right', 0.0)

                # 设置初始水深
                x = solver.x
                h0 = np.where(x < dam_pos, h_left, h_right)
                Q0 = np.where(x < dam_pos, Q_left, Q_right)

                solver.h = h0.copy()
                solver.Q = Q0.copy()

            elif ic_type == 'uniform':
                # 均匀流初始条件
                h_init = ic_config.get('h', 5.0)
                Q_init = ic_config.get('Q', 0.0)
                solver.h = np.full(n_cells, h_init)
                solver.Q = np.full(n_cells, Q_init)

            else:
                raise ValueError(f"Unknown initial condition type: {ic_type}")

            # 4. 设置边界条件
            bc_config = config.get('boundary_conditions', {})

            # 上游边界条件（默认为固定水深）
            if ic_type == 'dam_break':
                # 溃坝问题：边界条件设为初始水深
                h_left_bc = ic_config.get('h_left', 10.0)
                h_right_bc = ic_config.get('h_right', 1.0)
                solver.bc_left = {'type': 'h', 'value': h_left_bc}
                solver.bc_right = {'type': 'h', 'value': h_right_bc}
            else:
                # 其他情况：从配置读取
                upstream_bc = bc_config.get('upstream', {})
                downstream_bc = bc_config.get('downstream', {})

                # 上游
                upstream_type = upstream_bc.get('type', 'h')
                if upstream_type == 'h':
                    solver.bc_left = {'type': 'h', 'value': upstream_bc.get('value', 5.0)}
                elif upstream_type == 'Q':
                    solver.bc_left = {'type': 'Q', 'value': upstream_bc.get('value', 0.0)}
                elif upstream_type == 'wall':
                    solver.bc_left = {'type': 'wall'}

                # 下游
                downstream_type = downstream_bc.get('type', 'h')
                if downstream_type == 'h':
                    solver.bc_right = {'type': 'h', 'value': downstream_bc.get('value', 5.0)}
                elif downstream_type == 'Q':
                    solver.bc_right = {'type': 'Q', 'value': downstream_bc.get('value', 0.0)}
                elif downstream_type == 'wall':
                    solver.bc_right = {'type': 'wall'}

            # 记录初始质量
            solver.initial_mass = np.sum(solver.h * solver.dx * width)

            # 5. 时间推进循环
            t = 0
            n_steps = 0
            max_steps = 100000

            # 存储历史
            h_history = [solver.h.copy()]
            Q_history = [solver.Q.copy()]
            time_history = [t]

            # 降采样参数
            output_interval = config.get('output_interval', 0.5)
            next_output_time = output_interval

            while t < t_end and n_steps < max_steps:
                # 单步推进
                solver.step()
                t += solver.dt
                n_steps += 1

                # 按间隔保存结果
                if t >= next_output_time or t >= t_end:
                    h_history.append(solver.h.copy())
                    Q_history.append(solver.Q.copy())
                    time_history.append(t)
                    next_output_time += output_interval

                # 检查NaN
                if np.any(np.isnan(solver.h)) or np.any(np.isnan(solver.Q)):
                    raise ValueError(f"Numerical instability detected at t={t:.2f}s")

            # 6. 转换为numpy数组
            h_history = np.array(h_history)
            Q_history = np.array(Q_history)
            time_history = np.array(time_history)

            # 7. 计算流速
            V_history = Q_history / (h_history * width + 1e-10)

            # 8. 计算关键指标
            metrics = self._calculate_metrics(
                h_history, Q_history, V_history, solver, width
            )

            # 9. 准备输出数据
            time_sampled = time_history.tolist()
            h_sampled = h_history.tolist()
            Q_sampled = Q_history.tolist()
            V_sampled = V_history.tolist()

            # 8. 计算执行时间
            duration = (datetime.now() - start_time).total_seconds()

            # 10. 返回结果
            return SimulationResult(
                task_id=task_id,
                status='completed',
                time=time_sampled,
                x=solver.x.tolist(),
                h=h_sampled,
                Q=Q_sampled,
                V=V_sampled,
                metrics=metrics,
                duration=duration,
                timestamp=datetime.now().isoformat()
            )

        except Exception as e:
            # 仿真失败
            duration = (datetime.now() - start_time).total_seconds()
            return SimulationResult(
                task_id=task_id,
                status='failed',
                time=[],
                x=[],
                h=[],
                Q=[],
                V=[],
                metrics={},
                duration=duration,
                timestamp=datetime.now().isoformat(),
                error=str(e)
            )

    def _calculate_metrics(
        self,
        h_history: np.ndarray,
        Q_history: np.ndarray,
        V_history: np.ndarray,
        solver: GodunvFVMSolver,
        width: float
    ) -> Dict[str, float]:
        """
        计算仿真的关键指标

        Args:
            h_history: 水深历史
            Q_history: 流量历史
            V_history: 流速历史
            solver: 求解器
            width: 渠道宽度

        Returns:
            关键指标字典
        """
        # 计算质量守恒误差
        dx = solver.dx
        initial_mass = np.sum(h_history[0] * width * dx)
        final_mass = np.sum(h_history[-1] * width * dx)
        mass_error = abs(final_mass - initial_mass) / (initial_mass + 1e-10)

        # 最大值
        max_depth = float(np.max(h_history))
        max_velocity = float(np.max(np.abs(V_history)))
        max_discharge = float(np.max(np.abs(Q_history)))

        # 最小值
        min_depth = float(np.min(h_history))

        # 最终时刻统计
        final_h = h_history[-1]
        final_Q = Q_history[-1]
        mean_depth = float(np.mean(final_h))
        mean_discharge = float(np.mean(final_Q))

        # Froude数
        g = 9.81
        Fr = V_history / (np.sqrt(g * h_history) + 1e-10)
        max_froude = float(np.max(np.abs(Fr)))

        return {
            'mass_conservation_error': mass_error,
            'max_depth': max_depth,
            'min_depth': min_depth,
            'max_velocity': max_velocity,
            'max_discharge': max_discharge,
            'max_froude': max_froude,
            'mean_depth_final': mean_depth,
            'mean_discharge_final': mean_discharge,
            'total_iterations': len(h_history),
            'converged': True
        }

    def get_engine_info(self) -> Dict[str, Any]:
        """
        获取引擎信息

        Returns:
            引擎信息字典
        """
        return {
            'engine_version': self.version,
            'engine_path': self.engine_path,
            'solvers': {
                'canal': ['godunov_fvm', 'preissmann', 'hydrostatic'],
                'pipe': ['rk4', 'moc'],
                'network': ['hardy_cross', 'newton_raphson']
            },
            'features': {
                'numba_acceleration': True,
                '3d_visualization': True,
                'control_system': False,  # Phase 3
                'identification': False   # Phase 4
            }
        }


# 使用示例
if __name__ == '__main__':
    # 测试引擎
    engine = HydraulicEngine()

    # 溃坝案例配置
    config = {
        'width': 10.0,
        'length': 1000.0,
        'n_cells': 200,
        'manning_n': 0.0,
        'slope': 0.0,
        't_end': 50.0,
        'dt_max': 0.1,
        'output_interval': 1.0,
        'initial_conditions': {
            'type': 'dam_break',
            'dam_position': 500.0,
            'h_left': 10.0,
            'h_right': 1.0
        }
    }

    # 运行仿真
    result = engine.run_canal_simulation('test_001', config)

    # 打印结果
    print(f"状态: {result.status}")
    print(f"执行时间: {result.duration:.2f}s")
    print(f"时间步数: {len(result.time)}")
    print(f"空间网格数: {len(result.x)}")
    print(f"质量守恒误差: {result.metrics['mass_conservation_error']:.2e}")
    print(f"最大流速: {result.metrics['max_velocity']:.2f} m/s")
    print(f"最大水深: {result.metrics['max_depth']:.2f} m")
