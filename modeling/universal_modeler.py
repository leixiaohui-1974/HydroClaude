#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
通用建模接口 - 主类

整合所有模块，提供一站式建模服务

作者: Claude
日期: 2025-10-24
"""

import numpy as np
from pathlib import Path
from typing import Optional, Dict, List
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modeling.config import ModelConfig
from modeling.grid_generator import GridGenerator
from modeling.adaptive_refiner import AdaptiveRefiner
from modeling.algorithm_selector import AlgorithmSelector
from modeling.steady_estimator import SteadyEstimator
from modeling.multi_validator import MultiValidator

from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver
from solvers.gate import (
    SluiceGate,
    PumpStation,
    BroadCrestedWeir,
    Orifice,
    Spillway,
    Transition,
    Drop
)
from utils.visualization_templates import VisualizationTemplates
from utils.result_validator import quick_validate_steady_state

# 控制系统
from control.control_interface import (
    ControlLoop,
    ControlConfig,
    create_control_loop
)


class UniversalModeler:
    """
    通用建模系统 - 主接口

    一站式水力学建模服务：
    1. 自动加载配置
    2. 自动生成网格
    3. 自动选择算法
    4. 自动估计初值
    5. 执行模拟
    6. 多重验证
    7. 自动生成报告和图表

    使用示例:
    ```python
    modeler = UniversalModeler("config.yaml")
    modeler.run()
    ```
    """

    def __init__(self, config_file: str):
        """
        初始化建模系统

        Args:
            config_file: 配置文件路径（YAML格式）
        """
        print("=" * 90)
        print("HydroClaude 通用建模系统 v1.0")
        print("=" * 90)

        # 加载配置
        print("\n[1/7] 加载配置文件...")
        self.config = ModelConfig(config_file)
        print(f"      ✓ 配置已加载: {config_file}")

        # 初始化各模块
        self.grid_generator = None
        self.adaptive_refiner = None
        self.algorithm_selector = AlgorithmSelector()
        self.steady_estimator = SteadyEstimator()
        self.multi_validator = MultiValidator()

        # 求解器和结果
        self.solver = None
        self.structures = []
        self.steady_result = None
        self.unsteady_result = None
        self.control_result = None
        self.control_loop = None

        # 输出设置
        self.output_dir = Path(self.config.get_output_config()['directory'])
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def setup_grid(self):
        """设置网格"""
        print("\n[2/7] 生成网格...")

        canal_params = self.config.get_canal_params()
        grid_config = self.config.get_grid_config()

        # 创建网格生成器
        self.grid_generator = GridGenerator(
            length=canal_params['length'],
            structures=self.structures
        )

        # 根据配置生成网格
        if grid_config['nx'] is not None:
            # 指定了网格点数
            x = self.grid_generator.generate_uniform_grid(nx=grid_config['nx'])
            print(f"      网格类型: 均匀网格")
            print(f"      网格点数: {grid_config['nx']}")

        elif grid_config['dx_target'] is not None:
            # 指定了目标间距
            if grid_config['adaptive'] and self.structures:
                # 自适应网格
                x = self.grid_generator.generate_adaptive_grid(
                    dx_min=grid_config['dx_target'] / 4,
                    dx_max=grid_config['dx_target']
                )
                print(f"      网格类型: 自适应网格（结构物附近加密）")
            else:
                # 均匀网格
                x = self.grid_generator.generate_uniform_grid(dx_target=grid_config['dx_target'])
                print(f"      网格类型: 均匀网格")

            print(f"      目标间距: {grid_config['dx_target']:.0f} m")

        else:
            # 自动推荐
            nx = self.grid_generator.recommend_grid_size(dx_target=100.0)
            x = self.grid_generator.generate_uniform_grid(nx=nx)
            print(f"      网格类型: 自动推荐")
            print(f"      网格点数: {nx}")

        # 验证网格质量
        validation = self.grid_generator.validate_grid(x)
        print(f"      网格质量: {validation['quality_rating']}")
        print(f"      间距范围: [{validation['dx_min']:.1f}, {validation['dx_max']:.1f}] m")
        print(f"      平均间距: {validation['dx_mean']:.1f} m")

        return x

    def setup_structures(self):
        """设置结构物"""
        print("\n[3/7] 设置结构物...")

        structures_config = self.config.get_structures()

        if not structures_config:
            print("      无结构物")
            return

        canal_params = self.config.get_canal_params()

        for struct_cfg in structures_config:
            struct_type = struct_cfg['type']
            position = struct_cfg['position']

            if struct_type == 'sluice_gate':
                # 支持 'opening' 或 'initial_opening'
                opening = struct_cfg.get('opening', struct_cfg.get('initial_opening', 1.0))
                structure = SluiceGate(
                    position=position,
                    width=struct_cfg.get('width', canal_params['B']),
                    opening=opening,
                    Cd=struct_cfg.get('Cd', 0.6)
                )
            elif struct_type == 'pump_station':
                structure = PumpStation(
                    position=position,
                    width=struct_cfg.get('width', canal_params['B']),
                    rated_flow=struct_cfg['rated_flow'],
                    rated_head=struct_cfg['rated_head'],
                    min_suction_head=struct_cfg.get('min_suction_head', 2.0)
                )
            elif struct_type == 'weir':
                structure = BroadCrestedWeir(
                    position=position,
                    width=struct_cfg.get('width', canal_params['B']),
                    crest_height=struct_cfg['crest_height'],
                    Cd=struct_cfg.get('Cd', 0.4)
                )
            elif struct_type == 'orifice':
                structure = Orifice(
                    position=position,
                    width=struct_cfg.get('width', canal_params['B']),
                    opening=struct_cfg['opening'],
                    invert_level=struct_cfg.get('invert_level', 0.0),
                    Cd=struct_cfg.get('Cd', 0.6)
                )
            elif struct_type == 'spillway':
                structure = Spillway(
                    position=position,
                    width=struct_cfg.get('width', canal_params['B']),
                    crest_elevation=struct_cfg['crest_elevation'],
                    spillway_type=struct_cfg.get('spillway_type', 'wes'),
                    Cd=struct_cfg.get('Cd', 2.1),
                    submergence_threshold=struct_cfg.get('submergence_threshold', 0.67)
                )
            elif struct_type == 'transition':
                structure = Transition(
                    position=position,
                    width_upstream=struct_cfg.get('width_upstream', canal_params['B']),
                    width_downstream=struct_cfg.get('width_downstream', canal_params['B']),
                    length=struct_cfg.get('length', 100.0),
                    transition_type=struct_cfg.get('transition_type', 'linear')
                )
            elif struct_type == 'drop':
                structure = Drop(
                    position=position,
                    width=struct_cfg.get('width', canal_params['B']),
                    drop_height=struct_cfg['drop_height'],
                    drop_type=struct_cfg.get('drop_type', 'vertical'),
                    Cd=struct_cfg.get('Cd', 0.8)
                )
            else:
                print(f"      ⚠ 未知结构物类型: {struct_type}，跳过")
                continue

            self.structures.append((position, structure))
            print(f"      ✓ {struct_type} @ {position:.0f} m")

        print(f"      总计: {len(self.structures)}个结构物")

    def setup_solver(self, x: np.ndarray):
        """设置求解器"""
        print("\n[4/7] 初始化求解器...")

        canal_params = self.config.get_canal_params()

        self.solver = HydrostaticCanalSolver(
            length=canal_params['length'],
            nx=len(x),
            B=canal_params['B'],
            S0=canal_params['S0'],
            n=canal_params['n'],
            g=canal_params['g'],
            internal_structures=self.structures if self.structures else None,
            x_grid=x
        )

        print(f"      求解器: HydrostaticCanalSolver")
        print(f"      网格点数: {len(x)}")
        print(f"      渠道参数: L={canal_params['length']/1000:.1f}km, B={canal_params['B']}m, S0={canal_params['S0']}")

        return self.solver

    def select_algorithm(self):
        """选择最优算法"""
        print("\n[5/7] 选择最优算法...")

        sim_config = self.config.get_simulation_config()
        canal_params = self.config.get_canal_params()

        if sim_config['type'] == 'steady':
            recommendation = self.algorithm_selector.select_steady_solver(
                length=canal_params['length'],
                nx=self.solver.nx,
                has_structures=len(self.structures) > 0,
                accuracy_requirement='high'
            )
        else:
            recommendation = self.algorithm_selector.select_unsteady_solver(
                length=canal_params['length'],
                nx=self.solver.nx,
                dt=sim_config['dt'],
                has_structures=len(self.structures) > 0
            )

        print(f"      推荐方法: {recommendation['method']}")
        if 'theta' in recommendation:
            print(f"      Preissmann θ: {recommendation['theta']}")
        if 'warnings' in recommendation and recommendation['warnings']:
            for warning in recommendation['warnings']:
                print(f"      ⚠ {warning}")

        return recommendation

    def run_steady_simulation(self):
        """运行稳态模拟"""
        print("\n[6/7] 执行稳态模拟...")

        bc = self.config.get_boundary_conditions()
        sim_config = self.config.get_simulation_config()

        # 提取流量和水深
        if bc['upstream_type'] == 'flow':
            Q_target = bc['upstream_value']
        else:
            raise ValueError("稳态模拟要求上游边界为流量类型")

        if bc['downstream_type'] == 'depth':
            h_downstream = bc['downstream_value']
        else:
            raise ValueError("稳态模拟要求下游边界为水深类型")

        # 使用稳态估计器获取初值
        print("\n      获取稳态初值...")
        h, hu, result = self.steady_estimator.estimate_from_steady_solution(
            solver=self.solver,
            Q_target=Q_target,
            h_downstream=h_downstream,
            max_iterations=sim_config['max_iterations'],
            convergence_tol=sim_config['convergence_tol'],
            verbose=False
        )

        self.steady_result = result
        self.steady_result['Q_target'] = Q_target
        self.steady_result['h_downstream'] = h_downstream

        # 快速验证
        if result['converged']:
            print(f"\n      ✓ 稳态求解成功")
            print(f"        迭代次数: {result['iterations']}")
            print(f"        流量误差: {result.get('final_flow_error', 0):.6f}%")
        else:
            print(f"\n      ⚠ 稳态求解未完全收敛")
            print(f"        已执行迭代: {result['iterations']}")

        return result

    def run_unsteady_simulation(self):
        """
        运行非稳态模拟

        Returns:
            result: 非稳态模拟结果
        """
        print("\n[6/7] 执行非稳态模拟...")

        bc = self.config.get_boundary_conditions()
        sim_config = self.config.get_simulation_config()

        # 非稳态参数
        dt = sim_config.get('dt', 1.0)  # 时间步长 (s)
        total_time = sim_config.get('total_time', 3600.0)  # 总模拟时间 (s)
        save_interval = sim_config.get('save_interval', 100)  # 保存间隔

        # 计算时间步数
        n_steps = int(total_time / dt)
        n_saves = n_steps // save_interval + 1

        print(f"      时间步长: {dt} s")
        print(f"      总时间: {total_time} s")
        print(f"      时间步数: {n_steps}")
        print(f"      保存点数: {n_saves}")

        # 获取稳态初值
        print("\n      获取稳态初值作为初始条件...")

        if bc['upstream_type'] == 'flow':
            Q_target = bc['upstream_value']
        else:
            raise ValueError("非稳态模拟要求上游边界为流量类型")

        if bc['downstream_type'] == 'depth':
            h_downstream = bc['downstream_value']
        else:
            raise ValueError("非稳态模拟要求下游边界为水深类型")

        # 初始化边界条件变量（可能随时间变化）
        self.unsteady_Q_target = Q_target
        self.unsteady_h_downstream = h_downstream

        # 使用稳态作为初始条件
        h, hu, steady_result = self.steady_estimator.estimate_from_steady_solution(
            solver=self.solver,
            Q_target=Q_target,
            h_downstream=h_downstream,
            max_iterations=sim_config.get('max_iterations', 5000),
            convergence_tol=sim_config.get('convergence_tol', 0.001),
            verbose=False
        )

        print(f"      ✓ 稳态初值已获取")

        # 初始化结果存储
        nx = len(self.solver.x)
        time_saves = []
        h_history = np.zeros((n_saves, nx))
        hu_history = np.zeros((n_saves, nx))

        # 保存初始状态
        time_saves.append(0.0)
        h_history[0, :] = self.solver.h.copy()
        hu_history[0, :] = self.solver.hu.copy()

        save_idx = 1

        # 检查是否有时变边界条件
        time_varying_bc = sim_config.get('time_varying_bc', None)

        print(f"\n      开始时间推进...")

        # 时间循环
        for step in range(1, n_steps + 1):
            current_time = step * dt

            # 更新时变边界条件（如果有）
            if time_varying_bc:
                self._apply_time_varying_bc(current_time, time_varying_bc)

            # Preissmann隐式时间步进（使用可能动态更新的边界条件）
            h_new, hu_new = self.solver.step_preissmann(
                dt=dt,
                max_iter=sim_config.get('preissmann_max_iter', 10),
                enforce_bc=True,
                Q_in=self.unsteady_Q_target,
                h_out=self.unsteady_h_downstream
            )

            # 更新状态
            self.solver.h = h_new
            self.solver.hu = hu_new

            # 定期保存
            if step % save_interval == 0:
                time_saves.append(current_time)
                h_history[save_idx, :] = h_new.copy()
                hu_history[save_idx, :] = hu_new.copy()
                save_idx += 1

                # 进度提示
                if step % (save_interval * 10) == 0:
                    progress = step / n_steps * 100
                    print(f"        进度: {progress:.1f}% (t = {current_time:.1f}s)")

        print(f"      ✓ 非稳态模拟完成")

        # 构造结果
        self.unsteady_result = {
            'converged': True,
            'n_steps': n_steps,
            'dt': dt,
            'total_time': total_time,
            'time': np.array(time_saves),
            'h_history': h_history[:save_idx, :],
            'hu_history': hu_history[:save_idx, :],
            'Q_target': Q_target,
            'h_downstream': h_downstream,
        }

        return self.unsteady_result

    def _apply_time_varying_bc(self, t: float, time_varying_bc: dict):
        """
        应用时变边界条件

        支持的类型：
        1. sinusoidal - 正弦波动
        2. step - 阶跃变化
        3. linear - 线性变化
        4. file - 从文件读取时间序列

        Args:
            t: 当前时间
            time_varying_bc: 时变边界条件配置
        """
        bc_type = time_varying_bc.get('type')

        if bc_type == 'sinusoidal':
            # 正弦波动：value(t) = base + amplitude * sin(2π * t / period + phase)
            base = time_varying_bc.get('base', 10.0)
            amplitude = time_varying_bc.get('amplitude', 2.0)
            period = time_varying_bc.get('period', 360.0)  # 周期（秒）
            phase = time_varying_bc.get('phase', 0.0)  # 相位（弧度）

            import math
            value = base + amplitude * math.sin(2 * math.pi * t / period + phase)

            # 应用到边界
            if time_varying_bc.get('boundary') == 'upstream':
                self._update_upstream_bc(value)
            elif time_varying_bc.get('boundary') == 'downstream':
                self._update_downstream_bc(value)

        elif bc_type == 'step':
            # 阶跃变化
            step_time = time_varying_bc.get('step_time', 300.0)
            value_before = time_varying_bc.get('value_before', 10.0)
            value_after = time_varying_bc.get('value_after', 15.0)

            value = value_after if t >= step_time else value_before

            if time_varying_bc.get('boundary') == 'upstream':
                self._update_upstream_bc(value)
            elif time_varying_bc.get('boundary') == 'downstream':
                self._update_downstream_bc(value)

        elif bc_type == 'linear':
            # 线性变化：value(t) = start + (end - start) * t / duration
            start_value = time_varying_bc.get('start_value', 10.0)
            end_value = time_varying_bc.get('end_value', 20.0)
            duration = time_varying_bc.get('duration', 600.0)

            if t <= duration:
                value = start_value + (end_value - start_value) * t / duration
            else:
                value = end_value

            if time_varying_bc.get('boundary') == 'upstream':
                self._update_upstream_bc(value)
            elif time_varying_bc.get('boundary') == 'downstream':
                self._update_downstream_bc(value)

        elif bc_type == 'file':
            # 从文件读取时间序列
            # TODO: 实现文件读取
            pass

    def _update_upstream_bc(self, value: float):
        """更新上游边界条件"""
        # 如果是流量边界，更新流量
        self.unsteady_Q_target = value

    def _update_downstream_bc(self, value: float):
        """更新下游边界条件"""
        # 如果是水深边界，更新水深
        self.unsteady_h_downstream = value

    def run_control_simulation(self):
        """
        运行带闭环控制的模拟

        实现控制在环（Control-in-the-Loop）仿真：
        1. 初始化控制器（PID、MPC等）
        2. 时间步进循环：
           - 从求解器获取测量值
           - 控制器计算控制输出
           - 应用控制到结构物
           - 执行水力仿真时间步
        3. 记录控制历史和性能指标

        Returns:
            控制仿真结果字典
        """
        print("\n[6/7] 执行控制仿真...")

        # 获取配置
        sim_config = self.config.get_simulation_config()
        control_config_dict = sim_config.get('control', {})
        bc = self.config.get_boundary_conditions()

        # 时间参数
        dt = sim_config['dt']
        total_time = sim_config['total_time']
        n_steps = int(total_time / dt)
        save_interval = sim_config.get('save_interval', 1)
        control_interval = control_config_dict.get('control_interval', 1)  # 控制周期（时间步数）

        # 边界条件
        if bc['upstream_type'] == 'flow':
            Q_target = bc['upstream_value']
        else:
            raise ValueError("控制仿真要求上游边界为流量类型")

        if bc['downstream_type'] == 'depth':
            h_downstream = bc['downstream_value']
        else:
            raise ValueError("控制仿真要求下游边界为水深类型")

        # 存储边界条件用于Preissmann求解器
        self.unsteady_Q_target = Q_target
        self.unsteady_h_downstream = h_downstream

        # 获取稳态初值
        print("\n      获取稳态初值...")
        h_init, hu_init, steady_result = self.steady_estimator.estimate_from_steady_solution(
            solver=self.solver,
            Q_target=Q_target,
            h_downstream=h_downstream,
            max_iterations=sim_config.get('max_iterations', 5000),
            convergence_tol=sim_config.get('convergence_tol', 0.001),
            verbose=False
        )
        self.solver.h[:] = h_init
        self.solver.hu[:] = hu_init
        print(f"      ✓ 初值设置完成 (收敛步数: {steady_result.get('iterations', 0)})")

        # 创建控制配置
        control_config = ControlConfig(
            control_interval=control_interval,
            monitoring_points=control_config_dict.get('monitoring_points', None),
            control_points=control_config_dict.get('control_points', None)
        )

        # 创建控制循环
        controller_type = control_config_dict.get('type', 'pid')
        controller_config = control_config_dict.get('controller', {})

        print(f"\n      创建控制循环...")
        print(f"      控制器类型: {controller_type.upper()}")
        print(f"      控制周期: {control_interval * dt:.1f} s")

        self.control_loop = create_control_loop(
            solver=self.solver,
            controller_type=controller_type,
            controller_config=controller_config,
            control_config=control_config
        )

        # 设定值
        setpoint = control_config_dict.get('setpoint', 2.0)
        print(f"      设定值: {setpoint} m")

        # 初始化历史记录
        n_saves = n_steps // save_interval + 1
        time_saves = []
        h_history = np.zeros((n_saves, self.solver.nx))
        hu_history = np.zeros((n_saves, self.solver.nx))
        control_history = []
        measurement_history = []
        error_history = []

        # 初始记录
        save_idx = 0
        time_saves.append(0.0)
        h_history[save_idx, :] = self.solver.h.copy()
        hu_history[save_idx, :] = self.solver.hu.copy()
        save_idx += 1

        print(f"\n      开始时间步进...")
        print(f"      总步数: {n_steps}, 保存间隔: {save_interval}")

        # 时间步进循环
        for step in range(1, n_steps + 1):
            current_time = step * dt

            # 控制步（按控制周期执行）
            if step % control_interval == 0:
                control_data = self.control_loop.step(
                    current_time=current_time,
                    dt=dt * control_interval,
                    setpoint=setpoint
                )

                # 记录控制数据
                control_history.append(control_data['control'])
                measurement_history.append(control_data['measurement'])
                error_history.append(control_data['error'])

            # 水力仿真时间步
            h_new, hu_new = self.solver.step_preissmann(
                dt=dt,
                max_iter=sim_config.get('preissmann_max_iter', 10),
                enforce_bc=True,
                Q_in=self.unsteady_Q_target,
                h_out=self.unsteady_h_downstream
            )

            self.solver.h[:] = h_new
            self.solver.hu[:] = hu_new

            # 保存结果
            if step % save_interval == 0:
                time_saves.append(current_time)
                h_history[save_idx, :] = self.solver.h.copy()
                hu_history[save_idx, :] = self.solver.hu.copy()
                save_idx += 1

            # 进度显示
            if step % (n_steps // 10) == 0:
                progress = step / n_steps * 100
                h_range = (self.solver.h.min(), self.solver.h.max())
                print(f"      进度: {progress:.0f}% | 时间: {current_time:.0f}s | 水深: [{h_range[0]:.2f}, {h_range[1]:.2f}] m")

        print(f"      ✓ 控制仿真完成")

        # 获取控制性能指标
        performance_metrics = self.control_loop.get_performance_metrics()

        # 构造结果
        self.control_result = {
            'converged': True,
            'n_steps': n_steps,
            'dt': dt,
            'total_time': total_time,
            'control_interval': control_interval,
            'controller_type': controller_type,
            'setpoint': setpoint,
            'time': np.array(time_saves),
            'h_history': h_history[:save_idx, :],
            'hu_history': hu_history[:save_idx, :],
            'control_history': np.array(control_history),
            'measurement_history': np.array(measurement_history),
            'error_history': np.array(error_history),
            'performance_metrics': performance_metrics,
            'Q_target': Q_target,
            'h_downstream': h_downstream,
        }

        # 打印性能指标
        print(f"\n      控制性能指标:")
        for key, value in performance_metrics.items():
            if isinstance(value, (int, float)):
                print(f"        {key}: {value:.4f}")

        return self.control_result

    def validate_results(self):
        """验证结果"""
        print("\n[7/7] 多重验证...")

        if self.steady_result is not None:
            Q_target = self.steady_result['Q_target']

            # 执行多重验证
            validation_results = self.multi_validator.run_all_validations(
                solver=self.solver,
                Q_target=Q_target,
                h_history=None
            )

            # 生成验证报告
            report_file = self.output_dir / "validation_report.txt"
            self.multi_validator.generate_report(str(report_file))

            return validation_results

    def generate_outputs(self):
        """生成输出文件和图表"""
        print("\n" + "=" * 90)
        print("生成输出文件...")
        print("=" * 90)

        output_config = self.config.get_output_config()
        prefix = output_config['prefix']
        sim_type = self.config.get('simulation.type')

        # 保存数值数据
        if 'npz' in output_config['formats']:
            data_file = self.output_dir / f"{prefix}_data.npz"

            if sim_type == 'steady':
                # 稳态数据
                np.savez(
                    data_file,
                    x=self.solver.x,
                    h=self.solver.h,
                    Q=self.solver.hu * self.solver.B,
                    result=self.steady_result
                )
            elif sim_type == 'control':
                # 控制仿真数据
                np.savez(
                    data_file,
                    x=self.solver.x,
                    time=self.control_result['time'],
                    h_history=self.control_result['h_history'],
                    hu_history=self.control_result['hu_history'],
                    control_history=self.control_result['control_history'],
                    measurement_history=self.control_result['measurement_history'],
                    error_history=self.control_result['error_history'],
                    result=self.control_result
                )
            else:
                # 非稳态数据
                np.savez(
                    data_file,
                    x=self.solver.x,
                    time=self.unsteady_result['time'],
                    h_history=self.unsteady_result['h_history'],
                    hu_history=self.unsteady_result['hu_history'],
                    result=self.unsteady_result
                )
            print(f"✓ 数据文件: {data_file}")

        # 生成图表
        if 'png' in output_config['formats']:
            viz = VisualizationTemplates(output_dir=str(self.output_dir))
            canal_params = self.config.get_canal_params()

            if sim_type == 'steady':
                # 稳态：纵剖面图
                fig1 = viz.plot_longitudinal_profile(
                    x=self.solver.x,
                    h=self.solver.h,
                    S0=self.solver.S0,
                    canal_length=canal_params['length'],
                    gate_positions=[pos for pos, _ in self.structures] if self.structures else None,
                    title=f"Longitudinal Profile - {prefix}",
                    filename=f"{prefix}_profile.png"
                )
                print(f"✓ 纵剖面图: {prefix}_profile.png")
                import matplotlib.pyplot as plt
                plt.close(fig1)

            elif sim_type == 'control':
                # 控制仿真：控制性能图表
                self._generate_control_outputs(viz, prefix, canal_params)

            else:
                # 非稳态：时间序列图等
                self._generate_unsteady_outputs(viz, prefix, canal_params)

        print("=" * 90)

    def _generate_unsteady_outputs(self, viz, prefix, canal_params):
        """生成非稳态模拟输出"""
        import matplotlib.pyplot as plt

        # 1. 最终时刻纵剖面
        fig1 = viz.plot_longitudinal_profile(
            x=self.solver.x,
            h=self.unsteady_result['h_history'][-1, :],
            S0=self.solver.S0,
            canal_length=canal_params['length'],
            gate_positions=[pos for pos, _ in self.structures] if self.structures else None,
            title=f"Final State - {prefix}",
            filename=f"{prefix}_final_profile.png"
        )
        print(f"✓ 最终纵剖面图: {prefix}_final_profile.png")
        plt.close(fig1)

        # 2. 时间序列图（选择几个监测点）
        x = self.solver.x
        nx = len(x)
        monitor_indices = [0, nx//4, nx//2, 3*nx//4, nx-1]
        monitor_positions = x[monitor_indices]

        # 构造变量字典
        variables = {}
        for i, idx in enumerate(monitor_indices):
            label = f"x = {monitor_positions[i]/1000:.1f}km"
            variables[label] = self.unsteady_result['h_history'][:, idx]

        fig2 = viz.plot_time_series(
            time=self.unsteady_result['time'],
            variables=variables,
            title=f"Water Depth Time Series - {prefix}",
            ylabel="Water Depth (m)",
            filename=f"{prefix}_time_series.png"
        )
        print(f"✓ 时间序列图: {prefix}_time_series.png")
        plt.close(fig2)

        print(f"  >> 非稳态结果生成完成")

    def _generate_control_outputs(self, viz, prefix, canal_params):
        """生成控制仿真输出"""
        import matplotlib.pyplot as plt

        # 1. 控制性能时间序列（误差、控制量、测量值）
        # 控制历史的时间点：从control_interval开始，每隔control_interval记录一次
        dt = self.control_result['dt']
        control_interval = self.control_result['control_interval']
        n_control_samples = len(self.control_result['error_history'])
        time = np.arange(1, n_control_samples + 1) * (dt * control_interval)

        # 创建控制性能图（3子图）
        fig, axes = plt.subplots(3, 1, figsize=(12, 10))

        # 子图1: 误差
        error = np.array(self.control_result['error_history'])
        if error.ndim == 2:
            error = error[:, 0]  # 取第一个监测点
        axes[0].plot(time, error, 'b-', linewidth=1.5, label='跟踪误差')
        axes[0].axhline(y=0, color='k', linestyle='--', alpha=0.3)
        axes[0].set_ylabel('误差 (m)', fontsize=12)
        axes[0].set_title(f'控制性能 - {prefix}', fontsize=14, fontweight='bold')
        axes[0].grid(True, alpha=0.3)
        axes[0].legend()

        # 子图2: 测量值 vs 设定值
        measurement = np.array(self.control_result['measurement_history'])
        if measurement.ndim == 2:
            measurement = measurement[:, 0]  # 取第一个监测点
        setpoint = self.control_result['setpoint']
        axes[1].plot(time, measurement, 'g-', linewidth=1.5, label='测量值')
        axes[1].axhline(y=setpoint, color='r', linestyle='--', linewidth=2, label=f'设定值 = {setpoint} m')
        axes[1].set_ylabel('水深 (m)', fontsize=12)
        axes[1].grid(True, alpha=0.3)
        axes[1].legend()

        # 子图3: 控制量
        control = np.array(self.control_result['control_history'])
        if control.ndim == 2:
            control = control[:, 0]  # 取第一个控制点
        axes[2].plot(time, control, 'r-', linewidth=1.5, label='控制量')
        axes[2].set_xlabel('时间 (s)', fontsize=12)
        axes[2].set_ylabel('控制量', fontsize=12)
        axes[2].grid(True, alpha=0.3)
        axes[2].legend()

        plt.tight_layout()
        control_file = str(self.output_dir / f"{prefix}_control_performance.png")
        plt.savefig(control_file, dpi=150, bbox_inches='tight')
        print(f"✓ 控制性能图: {prefix}_control_performance.png")
        plt.close(fig)

        # 2. 最终时刻纵剖面
        fig2 = viz.plot_longitudinal_profile(
            x=self.solver.x,
            h=self.control_result['h_history'][-1, :],
            S0=self.solver.S0,
            canal_length=canal_params['length'],
            gate_positions=[pos for pos, _ in self.structures] if self.structures else None,
            title=f"Final State (Control) - {prefix}",
            filename=f"{prefix}_final_profile.png"
        )
        print(f"✓ 最终纵剖面图: {prefix}_final_profile.png")
        plt.close(fig2)

        print(f"  >> 控制仿真结果生成完成")

    def run(self):
        """运行完整建模流程"""
        try:
            # 1. 设置结构物
            self.setup_structures()

            # 2. 生成网格
            x = self.setup_grid()

            # 3. 初始化求解器
            self.setup_solver(x)

            # 4. 选择算法
            self.select_algorithm()

            # 5. 运行模拟
            sim_type = self.config.get('simulation.type')
            if sim_type == 'steady':
                self.run_steady_simulation()
            elif sim_type == 'control':
                self.run_control_simulation()
            else:
                self.run_unsteady_simulation()

            # 6. 验证结果
            self.validate_results()

            # 7. 生成输出
            self.generate_outputs()

            print("\n" + "=" * 90)
            print("✓ 建模完成！")
            print(f"  结果目录: {self.output_dir}")
            print("=" * 90)

            return True

        except Exception as e:
            print(f"\n✗ 建模失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def __repr__(self) -> str:
        return f"UniversalModeler(config='{self.config.config_file}')"


if __name__ == "__main__":
    print("通用建模系统主模块")
    print("请通过配置文件使用此系统")
