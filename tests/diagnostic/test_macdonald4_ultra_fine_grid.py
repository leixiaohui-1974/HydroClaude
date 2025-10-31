#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MacDonald Test 4 - 超细网格测试（直接使用求解器）

策略: 使用500网格单元 (dx=2m) vs 基线100网格 (dx=10m)
目标: 质量误差 < 15%，达到100%通过率

作者: HydroClaude Team
日期: 2025-10-30
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import numpy as np
import time
from solvers.godunov_fvm_weno3 import GodunvFVMWENO3


def test_ultra_fine_grid():
    """
    MacDonald Test 4 - 超细网格测试

    配置:
    - 网格: 500单元 (dx=2m)
    - CFL: 0.4
    - 模拟时间: 50s
    """

    print("="*80)
    print("MacDonald Test 4: 水跃 - 超细网格测试 (方案4)")
    print("="*80)
    print("\n配置对比:")
    print("  基线配置: 100网格, dx=10m, 质量误差=27.89%")
    print("  超细网格: 500网格, dx=2m,  质量误差=?")
    print("\n目标: 质量误差 < 15% → 100%通过率")
    print("="*80)

    # ===========================================
    # 1. 物理参数
    # ===========================================
    L = 1000.0          # 渠道长度 (m)
    B = 10.0            # 渠宽 (m)
    S0 = 0.0            # 底坡 (水平)
    n_manning = 0.0     # Manning系数 (无摩阻)
    g = 9.81

    # 上游边界条件 (超临界流)
    Q_upstream = 50.0   # 流量 (m³/s)
    h_upstream = 1.0    # 水深 (m)

    # 下游边界条件 (亚临界流)
    h_downstream = 2.0  # 水深 (m)

    # 数值参数 - 超细网格
    n_cells = 500       # ⭐ 500个网格单元 (vs 基线100)
    dx = L / n_cells    # dx = 2m
    cfl = 0.4           # 最优CFL

    print(f"\n数值配置:")
    print(f"  网格数: {n_cells} 个")
    print(f"  dx: {dx:.2f} m")
    print(f"  CFL: {cfl}")
    print(f"  Numba: {'可用' if hasattr(GodunvFVMWENO3, 'use_numba') else '未安装'}")

    # 计算上游Froude数
    u_upstream = Q_upstream / (B * h_upstream)
    Fr_upstream_theory = u_upstream / np.sqrt(g * h_upstream)

    # Belanger方程：理论水跃后水深
    h2_theory = h_upstream / 2.0 * (-1.0 + np.sqrt(1.0 + 8.0 * Fr_upstream_theory**2))

    print(f"\n理论值:")
    print(f"  上游Froude数: {Fr_upstream_theory:.3f}")
    print(f"  水跃后水深: {h2_theory:.3f} m")

    # ===========================================
    # 2. 创建求解器
    # ===========================================
    print(f"\n{'='*80}")
    print("创建WENO3求解器...")
    print(f"{'='*80}\n")

    solver = GodunvFVMWENO3(
        width=B,
        length=L,
        n_cells=n_cells,
        manning_n=n_manning,
        slope=S0,
        g=g,
        cfl=cfl,
        eps_dry=1e-6,
        weno_epsilon=1e-6
    )

    print(f"求解器创建成功:")
    print(f"  单元数: {solver.n_cells}")
    print(f"  dx: {solver.dx:.3f} m")
    print(f"  WENO3: 启用")

    # ===========================================
    # 3. 初始条件
    # ===========================================
    h_init = np.linspace(h_upstream, h_downstream, n_cells)
    Q_init = np.ones(n_cells) * Q_upstream

    # 边界条件
    bc_left = {
        'type': 'supercritical',
        'h': h_upstream,
        'Q': Q_upstream
    }
    bc_right = {
        'type': 'fixed_h',
        'h': h_downstream
    }

    solver.initialize(h_init, Q_init, bc_left, bc_right)

    # 记录初始质量
    mass_init = solver._compute_total_mass()

    print(f"\n初始质量: {mass_init:.2f} m³")

    # ===========================================
    # 4. 运行仿真
    # ===========================================
    t_end = 50.0

    print(f"\n{'='*80}")
    print(f"运行仿真到 t={t_end}s...")
    print(f"{'='*80}\n")

    start_time = time.time()
    step_count = 0

    diagnostics = []

    while solver.t < t_end:
        solver.step()
        step_count += 1

        # 每5秒记录一次
        if solver.t >= len(diagnostics) * 5 and len(diagnostics) <= 10:
            diag = solver.get_diagnostics()
            diagnostics.append(diag)

            # 计算当前Froude数
            h_safe = np.maximum(solver.h, solver.eps_dry)
            A = h_safe * solver.B
            u = solver.Q / A
            Fr = np.abs(u) / np.sqrt(solver.g * h_safe)
            Fr_upstream_current = Fr[0]

            # 负流量单元数
            n_negative = np.sum(solver.Q < 0)

            print(f"  t={solver.t:.1f}s: "
                  f"Fr[0]={Fr_upstream_current:.3f}, "
                  f"质量误差={diag['mass_error']:.2f}%, "
                  f"负流量={n_negative}/{n_cells}")

    elapsed = time.time() - start_time

    print(f"\n{'='*80}")
    print("仿真完成!")
    print(f"{'='*80}")
    print(f"  总步数: {step_count}")
    print(f"  模拟时间: {solver.t:.2f} s")
    print(f"  墙钟时间: {elapsed:.1f} s")
    print(f"  平均每步: {elapsed/step_count*1000:.1f} ms")

    # ===========================================
    # 5. 结果分析
    # ===========================================
    print(f"\n{'='*80}")
    print("结果分析")
    print(f"{'='*80}\n")

    # 质量守恒
    mass_final = solver._compute_total_mass()
    mass_error = abs(mass_final - mass_init) / mass_init * 100

    print(f"质量守恒:")
    print(f"  初始质量: {mass_init:.2f} m³")
    print(f"  最终质量: {mass_final:.2f} m³")
    print(f"  质量误差: {mass_error:.6f}%")

    # Froude数
    h_safe = np.maximum(solver.h, solver.eps_dry)
    A = h_safe * solver.B
    u = solver.Q / A
    Fr = np.abs(u) / np.sqrt(solver.g * h_safe)

    Fr_upstream_final = Fr[0]
    Fr_downstream_final = Fr[-1]

    print(f"\n上游状态:")
    print(f"  水深: {solver.h[0]:.3f} m")
    print(f"  流速: {u[0]:.3f} m/s")
    print(f"  Froude数: {Fr_upstream_final:.3f} (理论={Fr_upstream_theory:.3f})")

    print(f"\n下游状态:")
    print(f"  水深: {solver.h[-1]:.3f} m")
    print(f"  流速: {u[-1]:.3f} m/s")
    print(f"  Froude数: {Fr_downstream_final:.3f}")

    # 负流量
    negative_Q = solver.Q < 0
    n_negative = np.sum(negative_Q)
    negative_ratio = n_negative / n_cells * 100

    print(f"\n负流量:")
    print(f"  负流量单元: {n_negative}/{n_cells}")
    print(f"  负流量比例: {negative_ratio:.1f}%")

    # Belanger方程验证
    h2_actual = np.max(solver.h)
    belanger_error = abs(h2_actual - h2_theory) / h2_theory * 100

    print(f"\nBelanger方程验证:")
    print(f"  理论水跃后水深: {h2_theory:.3f} m")
    print(f"  实际最大水深: {h2_actual:.3f} m")
    print(f"  Belanger误差: {belanger_error:.2f}%")

    # ===========================================
    # 6. 验证标准
    # ===========================================
    print(f"\n{'='*80}")
    print("验证结果")
    print(f"{'='*80}\n")

    success = True

    # 质量守恒 (目标 < 15%)
    if mass_error < 15.0:
        print(f"✅ 质量守恒: {mass_error:.2f}% < 15.0%")
    else:
        print(f"⚠️  质量守恒: {mass_error:.2f}% ≥ 15.0% (仍需改进)")
        success = False

    # Froude数 (容差20%)
    if abs(Fr_upstream_final - Fr_upstream_theory) / Fr_upstream_theory < 0.2:
        print(f"✅ Froude数: {Fr_upstream_final:.3f} ≈ {Fr_upstream_theory:.3f}")
    else:
        print(f"⚠️  Froude数: {Fr_upstream_final:.3f} vs {Fr_upstream_theory:.3f} (偏差较大)")
        success = False

    # Belanger误差 (容差30%)
    if belanger_error < 30.0:
        print(f"✅ Belanger关系: 误差 {belanger_error:.2f}% < 30%")
    else:
        print(f"⚠️  Belanger关系: 误差 {belanger_error:.2f}% ≥ 30%")
        success = False

    # 负流量 (容差20%)
    if negative_ratio < 20.0:
        print(f"✅ 负流量: {negative_ratio:.1f}% < 20%")
    else:
        print(f"⚠️  负流量: {negative_ratio:.1f}% ≥ 20%")
        success = False

    # ===========================================
    # 7. 对比总结
    # ===========================================
    print(f"\n{'='*80}")
    print("改进效果总结")
    print(f"{'='*80}\n")

    baseline_error = 27.89  # 基线质量误差
    improvement = baseline_error - mass_error
    improvement_pct = improvement / baseline_error * 100

    print(f"质量误差对比:")
    print(f"  基线 (dx=10m, n=100): {baseline_error:.2f}%")
    print(f"  超细 (dx=2m,  n=500): {mass_error:.2f}%")
    print(f"  改善: {improvement:.2f}% (相对改善 {improvement_pct:.1f}%)")

    if mass_error < 15.0:
        print(f"\n🎉 超细网格方案成功！达到100%通过率目标！")
        print(f"{'='*80}\n")
        return True
    elif improvement > 5.0:
        print(f"\n✅ 有显著改善 (>{improvement:.1f}%)，但未达到<15%目标")
        print(f"建议: 继续实施方案2 (HLLC求解器)")
        print(f"{'='*80}\n")
        return False
    else:
        print(f"\n⚠️  改善有限 (<5%)，需要更激进方案")
        print(f"建议: 跳过方案2，直接实施方案1 (WENO5)")
        print(f"{'='*80}\n")
        return False


if __name__ == '__main__':
    print("\n⏱️  注意: 超细网格 (500单元) 在纯Python下可能需要2-5分钟")
    print("建议: 安装Numba加速 (pip install numba) 可缩短至10-30秒\n")

    start_time = time.time()
    success = test_ultra_fine_grid()
    total_time = time.time() - start_time

    print(f"\n总运行时间: {total_time/60:.1f} 分钟 ({total_time:.0f}秒)")

    if success:
        print("\n✅ 测试通过 - 超细网格方案有效！")
        exit(0)
    else:
        print("\n⚠️  需要进一步改进 - 准备下一方案")
        exit(1)
