#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MacDonald Test 4 with Entropy Fix

测试entropy_fix对无摩阻水跃的改善效果

作者: HydroClaude Team
日期: 2025-10-31
Phase: 6.3 - 混合流态求解器
"""

import sys
import warnings
warnings.filterwarnings("ignore")
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import numpy as np
import pytest
try:
    from solvers.godunov_fvm_weno3 import GodunvFVMWENO3
except ImportError as e:
    pytest.skip(f"Required module not available: {e}", allow_module_level=True)



def test_macdonald4_with_entropy_fix():
    """
    MacDonald Test 4 with Entropy Fix

    测试启用entropy_fix后对无摩阻水跃的改善
    """
    print("="*80)
    print("MacDonald Test 4 - Entropy Fix Test")
    print("="*80)

    # 参数设置（MacDonald Test 4原版）
    L = 1000.0       # 渠道长度 (m)
    B = 10.0         # 渠宽 (m)
    S0 = 0.0         # 水平河床
    n = 0.0          # 无摩阻（理想情况）
    Q = 20.0         # 流量 (m^3/s)
    h_upstream = 0.5   # 上游水深 (m) - 急流
    h_downstream = 2.5 # 下游水深 (m) - 缓流

    g = 9.81
    n_cells = 200  # 较细网格

    # 计算上游Froude数
    u_upstream = Q / (B * h_upstream)
    Fr_upstream = u_upstream / np.sqrt(g * h_upstream)

    print(f"\n测试参数:")
    print(f"  长度: {L} m")
    print(f"  网格: {n_cells} cells")
    print(f"  流量: {Q} m^3/s")
    print(f"  上游: h={h_upstream} m, Fr={Fr_upstream:.2f} (急流)")
    print(f"  下游: h={h_downstream} m")
    print(f"  Manning n={n} (无摩阻)")

    # 测试3种配置
    configs = [
        {"name": "标准WENO3", "entropy_fix": False, "use_enhanced_bc": False},
        {"name": "WENO3 + Entropy Fix", "entropy_fix": True, "use_enhanced_bc": False},
        {"name": "增强WENO3 + Entropy Fix", "entropy_fix": True, "use_enhanced_bc": True},
    ]

    results = []

    for config in configs:
        print(f"\n{'='*80}")
        print(f"测试配置: {config['name']}")
        print(f"{'='*80}")

        # 创建求解器
        solver = GodunvFVMWENO3(
            width=B,
            length=L,
            n_cells=n_cells,
            manning_n=max(n, 1e-6),  # 避免完全为0
            slope=S0 if S0 > 0 else 1e-6,
            entropy_fix=config['entropy_fix'],
            use_enhanced_bc=config['use_enhanced_bc'],
            well_balanced=False,  # 水平河床不需要
            cfl=0.3  # 较小CFL提高稳定性
        )

        # 初始条件：线性过渡（模拟水跃发展）
        x = np.linspace(0, L, n_cells)
        # 水深从上游到下游线性过渡
        h_init = h_upstream + (h_downstream - h_upstream) * (x / L)
        # 流量初始均匀
        Q_init = np.ones(n_cells) * Q

        # 边界条件
        bc_left = {'type': 'fixed_Q', 'Q': Q}
        bc_right = {'type': 'fixed_h', 'h': h_downstream}

        solver.initialize(h_init, Q_init, bc_left, bc_right)

        # 运行模拟（短时间）
        t_end = 20.0  # 20秒
        n_steps = 0
        t = 0.0

        initial_mass = solver._compute_total_mass()

        try:
            while t < t_end:
                solver.step()
                t = solver.t
                n_steps += 1

                # 检测负流量
                if np.any(solver.Q < -1e-6):
                    print(f"  ️  检测到负流量在 t={t:.2f}s")
                    break

                # 每5秒报告
                if n_steps % 100 == 0:
                    diag = solver.get_diagnostics()
                    print(f"  t={t:6.2f}s: h_avg={diag['h_mean']:.3f}m, "
                          f"Q_avg={diag['Q_mean']:.2f}m^3/s, "
                          f"mass_err={diag['mass_error']:.3f}%")

            # 最终诊断
            final_mass = solver._compute_total_mass()
            mass_error = (final_mass - initial_mass) / initial_mass * 100

            h_safe = np.maximum(solver.h, 1e-6)
            u = solver.Q / (B * h_safe)
            Fr = u / np.sqrt(g * h_safe)

            has_negative_Q = np.any(solver.Q < -1e-6)
            negative_Q_count = np.sum(solver.Q < -1e-6)

            print(f"\n  最终结果 (t={t:.2f}s):")
            print(f"    质量误差: {mass_error:.2f}%")
            print(f"    负流量数: {negative_Q_count}")
            print(f"    h范围: [{solver.h.min():.3f}, {solver.h.max():.3f}] m")
            print(f"    Q范围: [{solver.Q.min():.3f}, {solver.Q.max():.3f}] m^3/s")
            print(f"    Fr范围: [{Fr.min():.3f}, {Fr.max():.3f}]")

            # 评估成功标准
            success = (abs(mass_error) < 15.0 and not has_negative_Q)

            results.append({
                "name": config['name'],
                "mass_error": mass_error,
                "negative_Q": has_negative_Q,
                "negative_Q_count": negative_Q_count,
                "final_time": t,
                "success": success
            })

            if success:
                print(f"   测试成功")
            else:
                print(f"   测试失败")

        except Exception as e:
            print(f"   求解失败: {e}")
            results.append({
                "name": config['name'],
                "mass_error": None,
                "negative_Q": True,
                "negative_Q_count": None,
                "final_time": None,
                "success": False
            })

    # 总结对比
    print(f"\n{'='*80}")
    print("结果对比")
    print(f"{'='*80}")
    print(f"{'配置':<30} {'质量误差':<12} {'负流量':<10} {'状态':<10}")
    print(f"{'-'*80}")
    for r in results:
        mass_str = f"{r['mass_error']:.2f}%" if r['mass_error'] is not None else "N/A"
        neg_str = "是" if r['negative_Q'] else "否"
        status_str = "" if r['success'] else ""
        print(f"{r['name']:<30} {mass_str:<12} {neg_str:<10} {status_str:<10}")

    print(f"\n{'='*80}")
    print("结论:")
    print(f"{'='*80}")

    # 检查entropy_fix是否有改善
    if len(results) >= 2:
        baseline = results[0]
        entropy_result = results[1]

        if baseline['success'] or entropy_result['success']:
            print("  Entropy Fix对无摩阻水跃有一定改善")
        else:
            print("  Entropy Fix alone不足以解决无摩阻水跃问题")
            print("  建议:")
            print("    1. 结合局部Lax-Friedrichs flux")
            print("    2. 使用自适应耗散")
            print("    3. 或接受n>=0.01的实际工况限制")


if __name__ == '__main__':
    test_macdonald4_with_entropy_fix()
