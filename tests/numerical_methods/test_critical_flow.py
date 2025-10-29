#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
临界流测试（Critical Flow Test）

测试求解器在Froude数接近1时的稳定性和准确性。

测试场景：
1. 渐缩喉道（Contraction）: 亚临界 → 临界 → 超临界
2. 临界流通过喉道（Critical Flow over Hump）
3. 跨临界流稳定性（Transcritical Flow Stability）

物理背景：
- 当Fr = 1时，流速等于波速，信息无法上传
- 数值上容易出现非物理激波（entropy-violating shocks）
- 需要Entropy Fix来保证物理正确性

参考文献：
- LeVeque (2002): Finite Volume Methods for Hyperbolic Problems
- Toro (2009): Riemann Solvers, Chapter 6 (Entropy Condition)
- MacDonald et al. (1997): Benchmark Test Cases

作者: HydroClaude Team
日期: 2025-10-29
优先级: P1
"""

import pytest
import numpy as np
import tempfile
import json
from pathlib import Path
import sys

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from engine.model_builder import ModelBuilder


class TestCriticalFlow:
    """临界流测试套件"""

    @pytest.mark.p1
    def test_critical_flow_detection(self):
        """
        测试1: 临界流检测

        验证求解器能正确识别和处理Fr ≈ 1的情况

        已知问题：当前测试设置（S0=0.001, n=0.03）在物理上不会产生稳定的临界流。
        流动会在摩阻和坡度作用下调整到亚临界状态（Fr≈0.08）。
        需要重新设计测试场景（如喉道收缩或堰流）来真正测试临界流。
        """
        pytest.skip("测试设置需重新设计：当前配置不产生稳定临界流（见test_critical_flow_treatment.py的实际临界流测试）")
        # 参数设置：设计一个Fr≈1的稳态流
        L = 1000.0
        B = 10.0
        Q = 10.0  # 固定流量
        S0 = 0.001  # 小坡度
        n = 0.03

        # 临界水深: h_c = (Q²/(g*B²))^(1/3)
        g = 9.81
        h_critical = (Q**2 / (g * B**2))**(1/3)
        u_critical = Q / (B * h_critical)
        Fr_critical = u_critical / np.sqrt(g * h_critical)

        print(f"\n临界流参数:")
        print(f"  h_critical = {h_critical:.4f} m")
        print(f"  u_critical = {u_critical:.4f} m/s")
        print(f"  Fr_critical = {Fr_critical:.4f}")

        # 创建初始条件：接近临界流
        n_cells = 100
        dx = L / n_cells
        x = np.linspace(dx/2, L - dx/2, n_cells)

        # 初始条件：在临界深度附近略微变化
        h_init = h_critical * (1.0 + 0.01 * np.sin(2*np.pi*x/L))  # ±1%扰动
        Q_init = np.ones(n_cells) * Q

        # 保存初始条件
        ic_data = np.column_stack([x, h_init, Q_init])
        ic_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
        ic_file.write('x,h,Q\n')
        np.savetxt(ic_file, ic_data, delimiter=',')
        ic_file.close()
        ic_file_path = Path(ic_file.name)

        # 配置
        config = {
            'project': {
                'name': 'Critical Flow Test',
                'description': 'P1测试：临界流数值稳定性',
                'author': 'HydroClaude Team'
            },
            'geometry': {
                'type': 'uniform',
                'channel_width': B,
                'channel_length': L,
                'bottom_slope': S0,
                'manning_n': n
            },
            'mesh': {'n_cells': n_cells},
            'initial_conditions': {
                'type': 'from_file',
                'file': str(ic_file_path)
            },
            'boundary_conditions': {
                'left': {'type': 'Q', 'value': Q},
                'right': {'type': 'critical'}  # 临界流出口
            },
            'solver': {
                'type': 'godunov_fvm',
                'spatial_order': 1,
                'riemann_solver': 'hll',
                'use_numba': True,
                'cfl': 0.5,
                'eps_dry': 1e-6,
                'well_balanced': True,
                'entropy_fix': True  # 启用Entropy Fix处理临界流
            },
            'simulation': {
                'start_time': 0.0,
                'end_time': 100.0,
                'max_steps': 10000,
                'output_interval': 10.0
            },
            'output': {
                'directory': '/tmp/test_critical_flow',
                'formats': [],
                'variables': [],
                'statistics': False,
                'plots': {'enabled': False}
            },
            'validation': {'enabled': False}
        }

        config_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump(config, config_file, indent=2)
        config_file.close()
        config_file_path = Path(config_file.name)

        try:
            print(f"\n运行模拟（目标: t=100s）...")

            builder = ModelBuilder.from_config_file(str(config_file_path))
            solver = builder.build_solver()

            mass_init = solver._compute_total_mass()

            # 运行到100秒
            while solver.t < 100.0 and solver.step_count < 10000:
                solver.step()

            print(f"\n模拟完成：")
            print(f"  最终时间: t = {solver.t:.2f} s")
            print(f"  总步数: {solver.step_count}")

            # 分析最终状态
            h_final = solver.h
            Q_final = solver.Q
            u_final = Q_final / (h_final * B)
            Fr_final = u_final / np.sqrt(g * h_final)

            # 计算Fr的统计
            Fr_mean = np.mean(Fr_final)
            Fr_std = np.std(Fr_final)
            Fr_min = np.min(Fr_final)
            Fr_max = np.max(Fr_final)

            print(f"\nFroude数分析:")
            print(f"  Fr平均: {Fr_mean:.4f}")
            print(f"  Fr标准差: {Fr_std:.4f}")
            print(f"  Fr范围: [{Fr_min:.4f}, {Fr_max:.4f}]")

            # 质量守恒
            mass_final = solver._compute_total_mass()
            mass_error = abs(mass_final - mass_init) / mass_init * 100

            print(f"\n质量守恒:")
            print(f"  误差: {mass_error:.2f}%")

            # 验证
            print(f"\n验证标准:")

            # 1. 模拟完成
            assert solver.t >= 90.0, f"模拟未完成：t={solver.t:.2f}s < 90s"
            print(f"  ✅ 模拟稳定完成：t={solver.t:.2f}s >= 90s")

            # 2. 质量守恒（临界流允许稍大误差）
            assert mass_error < 5.0, f"质量误差过大：{mass_error:.2f}% > 5%"
            print(f"  ✅ 质量守恒：{mass_error:.2f}% < 5%")

            # 3. Fr保持在临界流附近（允许一定范围）
            assert 0.8 < Fr_mean < 1.2, f"Fr偏离临界值：{Fr_mean:.4f} not in [0.8, 1.2]"
            print(f"  ✅ Fr接近临界：{Fr_mean:.4f} in [0.8, 1.2]")

            # 4. 解不应该产生巨大振荡
            assert Fr_std < 0.3, f"Fr振荡过大：std={Fr_std:.4f} > 0.3"
            print(f"  ✅ Fr稳定：std={Fr_std:.4f} < 0.3")

            # 5. 无负流量
            n_negative = np.sum(Q_final < 0)
            assert n_negative == 0, f"存在{n_negative}个负流量单元"
            print(f"  ✅ 无负流量")

            print("\n" + "="*70)
            print("✅ 临界流测试通过：求解器在Fr≈1时保持稳定")
            print("="*70)

        finally:
            # 清理临时文件
            ic_file_path.unlink(missing_ok=True)
            config_file_path.unlink(missing_ok=True)

    @pytest.mark.p1
    def test_transcritical_flow_over_bump(self):
        """
        测试2: 跨临界流通过凸起（经典测试）

        流态变化：亚临界 → 临界（凸起顶部） → 超临界

        这是测试Entropy Fix的标准案例
        """
        # TODO: 实施跨临界流测试
        # 参考: LeVeque (2002), Test Problem 13.3
        pytest.skip("待实施：跨临界流凸起测试")


if __name__ == "__main__":
    # 快速测试
    test = TestCriticalFlow()
    test.test_critical_flow_detection()
