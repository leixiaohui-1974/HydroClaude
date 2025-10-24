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
from solvers.gate import SluiceGate, PumpStation, BroadCrestedWeir, Orifice
from utils.visualization_templates import VisualizationTemplates
from utils.result_validator import quick_validate_steady_state


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
        self.unsteady_results = None

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
                structure = SluiceGate(
                    position=position,
                    width=struct_cfg.get('width', canal_params['B']),
                    opening=struct_cfg['opening'],
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
        """运行非稳态模拟"""
        print("\n[6/7] 执行非稳态模拟...")
        print("      (非稳态模拟功能将在后续版本实现)")
        # TODO: 实现非稳态模拟
        return None

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

        # 保存数值数据
        if 'npz' in output_config['formats']:
            data_file = self.output_dir / f"{prefix}_data.npz"
            np.savez(
                data_file,
                x=self.solver.x,
                h=self.solver.h,
                Q=self.solver.hu * self.solver.B,
                result=self.steady_result
            )
            print(f"✓ 数据文件: {data_file}")

        # 生成图表
        if 'png' in output_config['formats']:
            viz = VisualizationTemplates(output_dir=str(self.output_dir))

            # 纵剖面图
            canal_params = self.config.get_canal_params()
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

        print("=" * 90)

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
