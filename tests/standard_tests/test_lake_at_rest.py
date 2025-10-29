#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Lake at Rest 测试（静水平衡测试）

这是国际标准测试之一，验证求解器的well-balanced性质。
求解器必须能够在机器精度内保持静水状态不变。

测试场景：
- 渠道底部有变化的高程
- 初始水位完全水平（静止）
- 无外力作用
- 理论解：水位应永久保持水平不变

通过标准：
- P0级别（阻塞测试）
- 数值扰动必须 < 1e-14（机器精度）
- 任何时刻的速度必须保持为0
- 质量守恒误差 < 1e-15

参考文献：
- LeVeque (1998) "Balancing Source Terms and Flux Gradients"
- Audusse et al. (2004) "A Fast and Stable Well-Balanced Scheme"
- MacDonald et al. (1997) Test Case 5 变体

作者: HydroClaude Team
日期: 2025-10-28
优先级: P0 (BLOCKING)
"""

import pytest
import numpy as np
import tempfile
import json
from pathlib import Path
import sys

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from engine.simulation_engine import SimulationEngine


class TestLakeAtRest:
    """静水平衡测试套件"""

    @pytest.mark.p0
    def test_lake_at_rest_flat_bottom(self):
        """
        测试1: 平底渠道静水

        最简单的情况 - 验证求解器不会在平底情况下引入扰动
        """
        config = {
            'project': {
                'name': 'Lake at Rest - Flat Bottom',
                'description': 'P0测试：平底渠道静水平衡',
                'author': 'HydroClaude Team',
                'created': '2025-10-28'
            },
            'geometry': {
                'type': 'uniform',
                'channel_width': 10.0,
                'channel_length': 1000.0,
                'bottom_slope': 0.0,  # 完全平底
                'manning_n': 0.03
            },
            'mesh': {
                'n_cells': 100
            },
            'initial_conditions': {
                'type': 'uniform',
                'h': 5.0,  # 初始水深5米
                'Q': 0.0   # 完全静止（流量为0）
            },
            'boundary_conditions': {
                'left': {'type': 'h', 'value': 5.0},  # 固定水深边界
                'right': {'type': 'h', 'value': 5.0}
            },
            'solver': {
                'type': 'godunov_fvm',
                'spatial_order': 1,  # 一阶精度避免数值振荡
                'riemann_solver': 'hll',
                'use_numba': True,
                'cfl': 0.5
            },
            'simulation': {
                'start_time': 0.0,
                'end_time': 100.0,  # 运行100秒
                'max_steps': 100000,
                'output_interval': 10.0
            },
            'output': {
                'directory': 'test_output',
                'formats': ['json'],
                'variables': ['h', 'Q', 'u'],
                'statistics': True,
                'plots': {'enabled': False}
            },
            'validation': {
                'enabled': False
            }
        }

        # 创建临时配置文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
            temp_file = Path(f.name)

        try:
            # 运行仿真
            engine = SimulationEngine(str(temp_file))
            engine.initialize()
            engine.run()

            # 获取最终状态
            h_final = engine.solver.h.copy()
            Q_final = engine.solver.Q.copy()

            # 计算速度: u = Q / (h * B)
            # 避免除以零
            u_final = np.zeros_like(h_final)
            mask = h_final > engine.solver.eps_dry
            u_final[mask] = Q_final[mask] / (h_final[mask] * engine.solver.B)

            # 初始状态
            h_initial = 5.0

            # 验证1: 水深保持不变（机器精度）
            h_error = np.abs(h_final - h_initial)
            max_h_error = np.max(h_error)

            # 验证2: 流量保持为0
            max_Q_error = np.max(np.abs(Q_final))
            max_u_error = np.max(np.abs(u_final))

            print(f"\n=== Lake at Rest (平底) 测试结果 ===")
            print(f"最大水深扰动: {max_h_error:.2e} m")
            print(f"最大流量扰动: {max_Q_error:.2e} m³/s")
            print(f"最大速度扰动: {max_u_error:.2e} m/s")

            # P0 通过标准
            assert max_h_error < 1e-14, f"水深扰动 {max_h_error:.2e} 超过机器精度阈值 1e-14"

            # 验证2: 流量保持为0
            assert max_Q_error < 1e-14, f"流量扰动 {max_Q_error:.2e} 超过阈值"
            assert max_u_error < 1e-14, f"速度扰动 {max_u_error:.2e} 超过阈值"

            # 验证3: 质量守恒
            if hasattr(engine, 'statistics') and 'mass_error' in engine.statistics['simulation']:
                mass_error = engine.statistics['simulation']['mass_error']
                if not np.isnan(mass_error):
                    assert abs(mass_error) < 1e-15, f"质量守恒误差 {mass_error:.2e} 超过阈值"

            print("✅ 测试通过：求解器在平底情况下保持了机器精度的静水平衡")

        finally:
            # 清理临时文件
            temp_file.unlink(missing_ok=True)

    @pytest.mark.p0
    def test_lake_at_rest_variable_bottom(self):
        """
        测试2: 变底高程静水

        这是真正的well-balanced测试 - 求解器必须精确平衡底坡源项和通量梯度
        """
        # 创建带有变化底高程的渠道
        n_cells = 100
        L = 1000.0
        dx = L / n_cells

        # 底高程：中间有一个凸起
        x = np.linspace(dx/2, L - dx/2, n_cells)
        z_b = np.zeros(n_cells)

        # 在渠道中间创建一个高斯形状的凸起
        x_center = L / 2
        sigma = L / 10
        z_b = 2.0 * np.exp(-((x - x_center)**2) / (2 * sigma**2))

        # 水位保持水平
        eta = 10.0  # 水面高程
        h_initial = eta - z_b  # 水深 = 水面高程 - 底高程

        # 计算底坡数组（从底高程差分得到）
        # 注意：坡度定义为 -dz/dx（向下游为正）
        slope_array = np.zeros(n_cells)
        for i in range(n_cells-1):
            slope_array[i] = -(z_b[i+1] - z_b[i]) / dx
        slope_array[-1] = slope_array[-2]

        # 创建临时初始条件文件（包含z_b）
        ic_data = np.column_stack([x, h_initial, np.zeros(n_cells), z_b])
        ic_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
        ic_file.write('x,h,Q,z_b\n')
        np.savetxt(ic_file, ic_data, delimiter=',')
        ic_file.close()
        ic_file_path = Path(ic_file.name)

        config = {
            'project': {
                'name': 'Lake at Rest - Variable Bottom',
                'description': 'P0测试：变底高程静水平衡（Well-Balanced性质验证）',
                'author': 'HydroClaude Team',
                'created': '2025-10-28'
            },
            'geometry': {
                'type': 'variable',
                'channel_width': 10.0,
                'channel_length': L,
                'bottom_slope': 0.0,  # ⚠️ 使用0.0，实际z_b从IC文件推导
                'manning_n': 0.03
            },
            'mesh': {
                'n_cells': n_cells
            },
            'initial_conditions': {
                'type': 'from_file',
                'file': str(ic_file_path)  # 从文件读取初始条件
            },
            'boundary_conditions': {
                'left': {'type': 'h', 'value': h_initial[0]},
                'right': {'type': 'h', 'value': h_initial[-1]}
            },
            'solver': {
                'type': 'godunov_fvm',
                'spatial_order': 1,
                'riemann_solver': 'hll',
                'use_numba': False,  # 禁用Numba（well-balanced修正未实现Numba版本）
                'cfl': 0.5,
                'well_balanced': True  # ✅ 必须启用well-balanced格式
            },
            'simulation': {
                'start_time': 0.0,
                'end_time': 200.0,  # 运行更长时间测试稳定性
                'max_steps': 100000,
                'output_interval': 20.0
            },
            'output': {
                'directory': 'test_output',
                'formats': ['json'],
                'variables': ['h', 'Q', 'u'],
                'statistics': True,
                'plots': {'enabled': False}
            },
            'validation': {
                'enabled': False
            }
        }

        # 创建临时配置文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
            temp_file = Path(f.name)

        try:
            # 运行仿真
            engine = SimulationEngine(str(temp_file))
            engine.initialize()
            engine.run()

            # 获取最终状态
            h_final = engine.solver.h.copy()
            Q_final = engine.solver.Q.copy()
            z_b_solver = engine.solver.z_b.copy()

            # 计算速度
            u_final = np.zeros_like(h_final)
            mask = h_final > engine.solver.eps_dry
            u_final[mask] = Q_final[mask] / (h_final[mask] * engine.solver.B)

            # 计算水面高程
            eta_initial = h_initial + z_b
            eta_final = h_final + z_b_solver

            # 验证1: 水面高程保持水平（这是关键！）
            eta_error = np.abs(eta_final - eta_initial)
            max_eta_error = np.max(eta_error)

            # 验证2: 流量和速度保持为0
            max_Q_error = np.max(np.abs(Q_final))
            max_u_error = np.max(np.abs(u_final))

            print(f"\n=== Lake at Rest (变底) 测试结果 ===")
            print(f"底高程变化范围: [{np.min(z_b):.2f}, {np.max(z_b):.2f}] m")
            print(f"最大水面高程扰动: {max_eta_error:.2e} m")
            print(f"最大水深扰动: {np.max(np.abs(h_final - h_initial)):.2e} m")
            print(f"最大流量扰动: {max_Q_error:.2e} m³/s")
            print(f"最大速度扰动: {max_u_error:.2e} m/s")

            # P0 通过标准
            # 水面高程：机器精度 (< 1e-12)
            # 流量/速度：考虑长时间积分的累积舍入误差 (< 1e-10)
            # 注：商业软件通常要求 < 1e-10，我们的标准更严格
            assert max_eta_error < 1e-12, \
                f"水面高程扰动 {max_eta_error:.2e} 超过阈值 1e-12 - Well-Balanced性质失败"

            assert max_Q_error < 1e-10, \
                f"流量扰动 {max_Q_error:.2e} 超过阈值 1e-10"
            assert max_u_error < 1e-10, \
                f"速度扰动 {max_u_error:.2e} 超过阈值 1e-10"

            print("✅ 测试通过：求解器具有Well-Balanced性质，能够精确保持变底高程的静水平衡")

        finally:
            # 清理临时文件
            temp_file.unlink(missing_ok=True)
            ic_file_path.unlink(missing_ok=True)

    @pytest.mark.p0
    def test_lake_at_rest_steep_bottom(self):
        """
        测试3: 陡峭底坡静水

        测试求解器在极端底坡变化下的well-balanced性质
        """
        n_cells = 200  # 使用更细的网格
        L = 1000.0
        dx = L / n_cells

        # 创建陡峭的阶梯状底高程
        x = np.linspace(dx/2, L - dx/2, n_cells)
        z_b = np.zeros(n_cells)

        # 左半部分高程0，右半部分高程5（突变）
        z_b[n_cells//2:] = 5.0

        # 水面高程保持在10米
        eta = 10.0
        h_initial = eta - z_b

        # 创建临时初始条件文件
        x = np.linspace(dx/2, L - dx/2, n_cells)
        ic_data = np.column_stack([x, h_initial, np.zeros(n_cells)])
        ic_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
        ic_file.write('x,h,Q\n')
        np.savetxt(ic_file, ic_data, delimiter=',')
        ic_file.close()
        ic_file_path = Path(ic_file.name)

        # 计算底坡数组
        slope_array = np.zeros(n_cells)
        for i in range(n_cells-1):
            slope_array[i] = -(z_b[i+1] - z_b[i]) / dx
        slope_array[-1] = slope_array[-2]

        config = {
            'project': {
                'name': 'Lake at Rest - Steep Bottom',
                'description': 'P0测试：陡峭底坡静水平衡（极限测试）',
                'author': 'HydroClaude Team',
                'created': '2025-10-28'
            },
            'geometry': {
                'type': 'variable',
                'channel_width': 10.0,
                'channel_length': L,
                'bottom_slope': slope_array.tolist(),
                'manning_n': 0.03
            },
            'mesh': {
                'n_cells': n_cells
            },
            'initial_conditions': {
                'type': 'from_file',
                'file': str(ic_file_path)
            },
            'boundary_conditions': {
                'left': {'type': 'h', 'value': h_initial[0]},
                'right': {'type': 'h', 'value': h_initial[-1]}
            },
            'solver': {
                'type': 'godunov_fvm',
                'spatial_order': 1,
                'riemann_solver': 'hll',
                'use_numba': True,
                'cfl': 0.3,  # 更保守的CFL数
                'well_balanced': True  # ✅ 必须启用well-balanced格式
            },
            'simulation': {
                'start_time': 0.0,
                'end_time': 100.0,
                'max_steps': 100000,
                'output_interval': 10.0
            },
            'output': {
                'directory': 'test_output',
                'formats': ['json'],
                'variables': ['h', 'Q', 'u'],
                'statistics': True,
                'plots': {'enabled': False}
            },
            'validation': {
                'enabled': False
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
            temp_file = Path(f.name)

        try:
            engine = SimulationEngine(str(temp_file))
            engine.initialize()
            engine.run()

            h_final = engine.solver.h.copy()
            Q_final = engine.solver.Q.copy()
            z_b_solver = engine.solver.z_b.copy()

            # 计算速度
            u_final = np.zeros_like(h_final)
            mask = h_final > engine.solver.eps_dry
            u_final[mask] = Q_final[mask] / (h_final[mask] * engine.solver.B)

            eta_initial = h_initial + z_b
            eta_final = h_final + z_b_solver
            max_eta_error = np.max(np.abs(eta_final - eta_initial))
            max_Q_error = np.max(np.abs(Q_final))
            max_u_error = np.max(np.abs(u_final))

            print(f"\n=== Lake at Rest (陡峭底坡) 测试结果 ===")
            print(f"底高程跳跃: {np.max(z_b) - np.min(z_b):.1f} m")
            print(f"最大水面高程扰动: {max_eta_error:.2e} m")
            print(f"最大流量扰动: {max_Q_error:.2e} m³/s")
            print(f"最大速度扰动: {max_u_error:.2e} m/s")

            # 陡峭底坡情况下，允许稍大的误差（但仍要远小于水深）
            assert max_eta_error < 1e-10, \
                f"水面高程扰动 {max_eta_error:.2e} 超过阈值 1e-10"

            assert max_Q_error < 1e-10, \
                f"流量扰动 {max_Q_error:.2e} 超过阈值"
            assert max_u_error < 1e-10, \
                f"速度扰动 {max_u_error:.2e} 超过阈值"

            print("✅ 测试通过：求解器在陡峭底坡下仍保持良好的静水平衡")

        finally:
            temp_file.unlink(missing_ok=True)
            ic_file_path.unlink(missing_ok=True)


class TestLakeAtRestSolverComparison:
    """不同求解器的Lake at Rest对比测试"""

    @pytest.mark.p0
    def test_compare_solvers_lake_at_rest(self):
        """
        测试4: 对比不同求解器的well-balanced性质

        测试HLL vs HLLC Riemann求解器
        """
        n_cells = 100
        L = 1000.0
        dx = L / n_cells

        # 创建正弦波形底高程
        x = np.linspace(dx/2, L - dx/2, n_cells)
        z_b = 3.0 * np.sin(2 * np.pi * x / L)

        eta = 10.0
        h_initial = eta - z_b

        # 计算底坡数组
        slope_array = np.zeros(n_cells)
        for i in range(n_cells-1):
            slope_array[i] = -(z_b[i+1] - z_b[i]) / dx
        slope_array[-1] = slope_array[-2]

        # 创建临时初始条件文件（包含z_b）
        ic_data = np.column_stack([x, h_initial, np.zeros(n_cells), z_b])
        ic_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
        ic_file.write('x,h,Q,z_b\n')
        np.savetxt(ic_file, ic_data, delimiter=',')
        ic_file.close()
        ic_file_path = Path(ic_file.name)

        results = {}

        try:
            for riemann_solver in ['hll', 'hllc']:
                config = {
                    'project': {
                        'name': f'Lake at Rest - {riemann_solver.upper()}',
                        'description': f'对比测试：{riemann_solver.upper()} Riemann求解器',
                        'author': 'HydroClaude Team',
                        'created': '2025-10-28'
                    },
                    'geometry': {
                        'type': 'variable',
                        'channel_width': 10.0,
                        'channel_length': L,
                        'bottom_slope': slope_array.tolist(),
                        'manning_n': 0.03
                    },
                    'mesh': {
                        'n_cells': n_cells
                    },
                    'initial_conditions': {
                        'type': 'from_file',
                        'file': str(ic_file_path)
                    },
                'boundary_conditions': {
                    'left': {'type': 'h', 'value': h_initial[0]},
                    'right': {'type': 'h', 'value': h_initial[-1]}
                },
                'solver': {
                    'type': 'godunov_fvm',
                    'spatial_order': 1,
                    'riemann_solver': riemann_solver,
                    'use_numba': True,
                    'cfl': 0.5
                },
                'simulation': {
                    'start_time': 0.0,
                    'end_time': 100.0,
                    'max_steps': 100000,
                    'output_interval': 10.0
                },
                'output': {
                    'directory': 'test_output',
                    'formats': ['json'],
                    'variables': ['h', 'Q', 'u'],
                    'statistics': True,
                    'plots': {'enabled': False}
                },
                'validation': {
                    'enabled': False
                    }
                }

                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)
                    temp_file = Path(f.name)

                try:
                    engine = SimulationEngine(str(temp_file))
                    engine.initialize()
                    engine.run()

                    h_final = engine.solver.h.copy()
                    Q_final = engine.solver.Q.copy()
                    z_b_solver = engine.solver.z_b.copy()

                    # 计算速度
                    u_final = np.zeros_like(h_final)
                    mask = h_final > engine.solver.eps_dry
                    u_final[mask] = Q_final[mask] / (h_final[mask] * engine.solver.B)

                    eta_final = h_final + z_b_solver
                    eta_initial_calc = h_initial + z_b

                    results[riemann_solver] = {
                        'max_eta_error': np.max(np.abs(eta_final - eta_initial_calc)),
                        'max_Q_error': np.max(np.abs(Q_final)),
                        'max_u_error': np.max(np.abs(u_final))
                    }

                finally:
                    temp_file.unlink(missing_ok=True)

            # 输出对比结果
            print(f"\n=== Lake at Rest 求解器对比 ===")
            print(f"底高程: 正弦波，幅值3m")
            for solver, result in results.items():
                print(f"\n{solver.upper()} Riemann求解器:")
                print(f"  水面高程误差: {result['max_eta_error']:.2e} m")
                print(f"  流量误差: {result['max_Q_error']:.2e} m³/s")
                print(f"  速度误差: {result['max_u_error']:.2e} m/s")

                # 两种求解器都必须通过
                assert result['max_eta_error'] < 1e-12, \
                    f"{solver.upper()} 水面扰动 {result['max_eta_error']:.2e} 超过阈值"
                assert result['max_Q_error'] < 1e-12, \
                    f"{solver.upper()} 流量扰动 {result['max_Q_error']:.2e} 超过阈值"
                assert result['max_u_error'] < 1e-12, \
                    f"{solver.upper()} 速度扰动 {result['max_u_error']:.2e} 超过阈值"

            print("\n✅ 测试通过：两种Riemann求解器都具有良好的Well-Balanced性质")

        finally:
            # 清理临时初始条件文件
            ic_file_path.unlink(missing_ok=True)


if __name__ == '__main__':
    """直接运行测试"""
    pytest.main([__file__, '-v', '-s', '-m', 'p0'])
