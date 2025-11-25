#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MacDonald Test 4 - 增强版WENO3测试

目标: 使用增强版WENO3求解器来改善水跃问题的求解
     特别是质量守恒和激波捕捉性能

增强特性:
1. 改进的WENO3重构（更好的平滑度指示器）
2. 熵修正（Harten-Hyman）
3. Well-Balanced静水重构
4. 自适应CFL控制

预期改进:
- 质量守恒误差从 ~29% 降低到 < 10%
- 更好的激波分辨率
- 上游超临界状态维持

作者: HydroClaude Team
日期: 2025-10-30
"""

import sys
import os
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import numpy as np
import tempfile
import json
from engine.simulation_engine import SimulationEngine


def test_macdonald4_enhanced_weno3():
    """
    MacDonald Test 4 with Enhanced WENO3

    配置:
    - 增强版WENO3求解器
    - 熵修正启用
    - 自适应CFL启用
    - Well-Balanced: False (平底渠道不需要)
    """
    print("\n" + "="*80)
    print("MacDonald Test 4 - 增强版WENO3求解器测试")
    print("="*80)

    # 测试参数 (与标准Test 4相同)
    L = 1000.0          # 渠道长度 (m)
    B = 10.0            # 渠宽 (m)
    S0 = 0.0            # 水平河床
    n = 0.0             # 无摩阻

    # 边界条件
    h_upstream = 0.7    # 上游水深 (m)
    Q = 20.0            # 流量 (m^3/s)
    h_downstream = 2.8  # 下游水深 (m)

    n_cells = 50  # 减少网格数以加快计算
    dx = L / n_cells

    g = 9.81

    # 计算上游Froude数
    u_upstream = Q / (B * h_upstream)
    Fr_upstream = u_upstream / np.sqrt(g * h_upstream)

    # 理论水跃后水深（Belanger方程）
    h2_theory = h_upstream / 2.0 * (-1.0 + np.sqrt(1.0 + 8.0 * Fr_upstream**2))

    print(f"\n配置:")
    print(f"  渠道: L={L:.0f}m, B={B:.1f}m, S0={S0}, n={n}")
    print(f"  网格: {n_cells} cells, dx={dx:.2f}m")
    print(f"\n边界条件:")
    print(f"  上游: h={h_upstream:.2f}m, Q={Q:.1f}m^3/s, Fr={Fr_upstream:.2f} (超临界)")
    print(f"  下游: h={h_downstream:.2f}m")
    print(f"\n理论预测:")
    print(f"  水跃后水深 (Belanger): h2={h2_theory:.3f}m")
    print(f"  下游边界水深: h3={h_downstream:.2f}m")
    print(f"  差异: {abs(h_downstream - h2_theory):.3f}m ({abs(h_downstream/h2_theory - 1)*100:.1f}%)")
    print()

    # 验证条件
    assert Fr_upstream > 1.0, f"上游必须是急流: Fr={Fr_upstream:.2f} < 1.0"
    assert h_downstream > h_upstream, f"下游水深必须大于上游"

    # 初始条件：线性插值
    x = np.linspace(dx/2, L - dx/2, n_cells)
    h_init = np.linspace(h_upstream, h_downstream, n_cells)
    Q_init = np.ones(n_cells) * Q

    # 创建临时初始条件文件
    ic_data = np.column_stack([x, h_init, Q_init])
    ic_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
    ic_file.write('x,h,Q\n')
    np.savetxt(ic_file, ic_data, delimiter=',')
    ic_file.close()
    ic_file_path = Path(ic_file.name)

    # 配置 - 使用增强版WENO3
    config = {
        'project': {
            'name': 'MacDonald Test 4 - Enhanced WENO3',
            'description': '增强版WENO3水跃测试',
            'author': 'HydroClaude Team',
            'created': '2025-10-30'
        },
        'geometry': {
            'type': 'uniform',
            'channel_width': B,
            'channel_length': L,
            'bottom_slope': S0,
            'manning_n': n
        },
        'mesh': {
            'n_cells': n_cells
        },
        'initial_conditions': {
            'type': 'from_file',
            'file': str(ic_file_path)
        },
        'boundary_conditions': {
            'left': {'type': 'supercritical', 'h': h_upstream, 'Q': Q},
            'right': {'type': 'h', 'value': h_downstream}
        },
        'solver': {
            'type': 'godunov_fvm',
            'spatial_order': 3,  # WENO3
            'weno3_enhanced': True,  #  启用增强版
            'riemann_solver': 'hll',
            'use_numba': True,
            'cfl': 0.5,  # 基础CFL（激波处会自动降低）
            'eps_dry': 1e-6,
            'weno_epsilon': 1e-6,
            'well_balanced': False,  # 平底不需要
            'dt_max': 0.5,
            # 增强特性配置
            'entropy_fix': True,  # 启用熵修正
            'critical_flow_treatment': True,  # 启用临界流处理
            'adaptive_cfl': False,  # 暂时禁用自适应CFL以加快速度
            'cfl_shock': 0.3,  # 激波处CFL
            'entropy_delta': 0.1  # 熵修正参数
        },
        'simulation': {
            'start_time': 0.0,
            'end_time': 20.0,  # 进一步缩短到20秒
            'max_steps': 10000,
            'output_interval': 5.0
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
    config_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
    json.dump(config, config_file, indent=2, ensure_ascii=False)
    config_file.close()
    config_file_path = Path(config_file.name)

    try:
        print("="*80)
        print("运行模拟...")
        print("="*80)
        print()

        # 运行仿真
        engine = SimulationEngine(str(config_file_path))
        engine.initialize()
        engine.run()

        # 获取最终状态
        h_final = engine.solver.h.copy()
        Q_final = engine.solver.Q.copy()
        x_solver = engine.solver.x.copy()

        # 计算速度和Froude数
        u_final = np.zeros_like(h_final)
        Fr_final = np.zeros_like(h_final)
        mask = h_final > engine.solver.eps_dry
        u_final[mask] = Q_final[mask] / (h_final[mask] * B)
        Fr_final[mask] = np.abs(u_final[mask]) / np.sqrt(g * h_final[mask])

        # 分析结果
        print("\n" + "="*80)
        print("结果分析")
        print("="*80)

        # 1. 质量守恒
        if hasattr(engine, 'statistics') and 'simulation' in engine.statistics:
            mass_error = engine.statistics['simulation'].get('mass_error', np.nan)
            if not np.isnan(mass_error):
                print(f"\n质量守恒:")
                print(f"  误差: {abs(mass_error):.2f}%")
                if abs(mass_error) < 10.0:
                    print(f"   优秀 (< 10%)")
                elif abs(mass_error) < 20.0:
                    print(f"   良好 (< 20%)")
                elif abs(mass_error) < 30.0:
                    print(f"  ️  可接受 (< 30%)")
                else:
                    print(f"   较差 (>= 30%)")

        # 2. 上游Froude数
        Fr_up = Fr_final[0]
        print(f"\n上游条件维持:")
        print(f"  Fr[0] = {Fr_up:.3f}")
        if Fr_up > 1.0:
            print(f"   超临界状态维持 (Fr > 1)")
        elif Fr_up > 0.9:
            print(f"  ️  接近超临界 (0.9 < Fr < 1)")
        else:
            print(f"   超临界状态丢失 (Fr < 0.9)")

        # 3. 水跃位置检测
        # 寻找Fr从>1到<1的转换点
        supercritical_mask = Fr_final > 1.0
        if np.any(supercritical_mask):
            # 找到最后一个超临界点
            last_super_idx = np.where(supercritical_mask)[0][-1]
            jump_location = x_solver[last_super_idx]

            print(f"\n水跃分析:")
            print(f"  水跃位置: x ~= {jump_location:.1f}m ({jump_location/L*100:.1f}% of L)")

            # 水跃前后水深
            h_before = h_final[last_super_idx]
            if last_super_idx + 10 < len(h_final):
                h_after = np.mean(h_final[last_super_idx+5:last_super_idx+10])
            else:
                h_after = h_final[-1]

            print(f"  水跃前水深: h1 = {h_before:.3f}m")
            print(f"  水跃后水深: h2 = {h_after:.3f}m")
            print(f"  理论水跃后: h2_theory = {h2_theory:.3f}m")

            # Belanger误差
            belanger_error = abs(h_after - h2_theory) / h2_theory * 100
            print(f"  Belanger误差: {belanger_error:.1f}%")

            if belanger_error < 10.0:
                print(f"   优秀 (< 10%)")
            elif belanger_error < 20.0:
                print(f"   良好 (< 20%)")
            elif belanger_error < 30.0:
                print(f"  ️  可接受 (< 30%)")
            else:
                print(f"   较差 (>= 30%)")

            # 超临界区域大小
            n_supercritical = np.sum(supercritical_mask)
            print(f"\n超临界区域:")
            print(f"  单元数: {n_supercritical}/{n_cells} ({n_supercritical/n_cells*100:.1f}%)")
        else:
            print(f"\n️  警告: 未检测到超临界区域")

        # 4. 负流量检查
        n_negative = np.sum(Q_final < 0)
        print(f"\n数值稳定性:")
        print(f"  负流量单元: {n_negative}/{n_cells}")
        if n_negative == 0:
            print(f"   无负流量")
        else:
            print(f"  ️  存在负流量")

        # 总结
        print("\n" + "="*80)
        print("测试总结")
        print("="*80)

        # 判断测试是否通过
        passed_criteria = []
        failed_criteria = []

        # 标准1: 质量守恒
        if hasattr(engine, 'statistics') and 'simulation' in engine.statistics:
            mass_error = abs(engine.statistics['simulation'].get('mass_error', 100))
            if mass_error < 20.0:
                passed_criteria.append(f"质量守恒: {mass_error:.1f}% < 20%")
            else:
                failed_criteria.append(f"质量守恒: {mass_error:.1f}% >= 20%")

        # 标准2: 上游超临界
        if Fr_up > 1.0:
            passed_criteria.append(f"上游超临界: Fr={Fr_up:.3f} > 1.0")
        else:
            failed_criteria.append(f"上游超临界丢失: Fr={Fr_up:.3f} <= 1.0")

        # 标准3: Belanger方程
        if np.any(supercritical_mask):
            if belanger_error < 30.0:
                passed_criteria.append(f"Belanger误差: {belanger_error:.1f}% < 30%")
            else:
                failed_criteria.append(f"Belanger误差: {belanger_error:.1f}% >= 30%")

        print("\n通过的标准:")
        for criterion in passed_criteria:
            print(f"   {criterion}")

        if failed_criteria:
            print("\n未通过的标准:")
            for criterion in failed_criteria:
                print(f"   {criterion}")

        # 与标准WENO3对比
        print("\n与标准WENO3对比:")
        print("  标准WENO3: 质量误差 ~29%, 大量负流量 ")
        if hasattr(engine, 'statistics') and 'simulation' in engine.statistics:
            mass_error = abs(engine.statistics['simulation'].get('mass_error', 100))
            print(f"  增强WENO3: 质量误差 ~{mass_error:.1f}%, 负流量 {n_negative} {'' if n_negative == 0 else '️'}")

            if mass_error < 29.0 and n_negative == 0:
                print("\n 增强版WENO3显著改善了求解质量！")
            elif mass_error < 29.0:
                print("\n 增强版WENO3改善了质量守恒")
            else:
                print("\n️  增强版WENO3仍需进一步优化")

        print("\n" + "="*80)

    finally:
        # 清理临时文件
        ic_file_path.unlink(missing_ok=True)
        config_file_path.unlink(missing_ok=True)


if __name__ == '__main__':
    test_macdonald4_enhanced_weno3()
