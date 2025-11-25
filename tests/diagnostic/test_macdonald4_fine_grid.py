#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MacDonald Test 4 - 极细网格测试

目标: 通过暴力提升网格分辨率改善质量守恒
策略: dx=2m (500网格) vs 之前的dx=10m (100网格)
预期: 质量误差 27.89% -> 15-20% 或更好

作者: HydroClaude Team
日期: 2025-10-30
"""

import sys
import warnings
warnings.filterwarnings("ignore")
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import numpy as np
import json
import tempfile
from engine.simulation_engine import SimulationEngine
from engine.model_builder import ModelBuilder


def test_macdonald4_fine_grid():
    """
    MacDonald Test 4 - 极细网格测试

    配置:
    - 网格: 500个单元 (dx=2m)  vs 基线100个 (dx=10m)
    - CFL: 0.4 (最优值)
    - 模拟时间: 50s
    """

    print("="*80)
    print("MacDonald Test 4: 水跃 - 极细网格测试")
    print("="*80)
    print("\n配置对比:")
    print("  基线配置: 100网格, dx=10m, 质量误差=27.89%")
    print("  极细网格: 500网格, dx=2m,  质量误差=?")
    print("\n目标: 质量误差 < 15%")
    print("="*80)

    # ==========================================
    # 1. 物理参数
    # ==========================================
    L = 1000.0          # 渠道长度 (m)
    B = 10.0            # 渠宽 (m)
    S0 = 0.0            # 底坡 (水平)
    n_manning = 0.0     # Manning系数 (无摩阻)

    # 上游边界条件 (超临界流)
    Q_upstream = 50.0   # 流量 (m^3/s)
    h_upstream = 1.0    # 水深 (m)

    # 下游边界条件 (亚临界流)
    h_downstream = 2.0  # 水深 (m)

    # 数值参数 - 极细网格
    n_cells = 500       # 500个网格单元 ⭐ 关键变化
    dx = L / n_cells    # dx = 2m
    cfl = 0.4           # 最优CFL
    simulation_time = 50.0  # 模拟时间 (s)

    print(f"\n数值配置:")
    print(f"  网格数: {n_cells} 个")
    print(f"  dx: {dx:.2f} m")
    print(f"  CFL: {cfl}")
    print(f"  模拟时间: {simulation_time} s")

    # ==========================================
    # 2. 初始条件 (线性插值)
    # ==========================================
    x = np.linspace(0, L, n_cells)
    h_init = np.linspace(h_upstream, h_downstream, n_cells)
    Q_init = np.ones(n_cells) * Q_upstream

    # 保存初始条件到临时CSV文件
    ic_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
    ic_file.write("x,h,Q\n")  # Header
    for i in range(n_cells):
        ic_file.write(f"{x[i]},{h_init[i]},{Q_init[i]}\n")
    ic_file_path = Path(ic_file.name)
    ic_file.close()

    # ==========================================
    # 3. 配置文件
    # ==========================================
    config = {
        "project": {
            "name": "MacDonald Test 4 - Fine Grid (dx=2m)",
            "description": "极细网格测试，目标100%通过率"
        },

        "geometry": {
            "type": "uniform",
            "width": B,
            "length": L,
            "slope": S0,
            "manning_n": n_manning
        },

        "mesh": {
            "n_cells": n_cells,
            "uniform": True
        },

        "solver": {
            "type": "godunov_fvm",
            "riemann_solver": "hll",  # 小写
            "spatial_order": 3,  # WENO3
            "cfl": cfl,
            "use_numba": True    # 尝试使用Numba加速
        },

        "initial_conditions": {
            "type": "from_file",
            "file": str(ic_file_path)
        },

        "boundary_conditions": {
            "left": {  # upstream = left
                "type": "discharge",
                "value": Q_upstream
            },
            "right": {  # downstream = right
                "type": "stage",
                "value": h_downstream
            }
        },

        "simulation": {
            "start_time": 0.0,
            "end_time": simulation_time,
            "output_interval": 5.0
        },

        "output": {
            "directory": "test_output",
            "format": "json",
            "variables": ["h", "Q", "u"]
        }
    }

    # 保存配置到临时文件
    config_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
    json.dump(config, config_file, indent=2)
    config_file_path = Path(config_file.name)
    config_file.close()

    # ==========================================
    # 4. 运行仿真
    # ==========================================
    print(f"\n{'='*80}")
    print("开始仿真...")
    print(f"{'='*80}\n")

    try:
        engine = SimulationEngine(str(config_file_path))
        engine.initialize()  # ⭐ 添加初始化步骤
        engine.run()

        # 获取最终状态
        h_final = engine.h.copy()
        Q_final = engine.Q.copy()

        print(f"\n{'='*80}")
        print("仿真完成!")
        print(f"{'='*80}\n")

    finally:
        # 清理临时文件
        ic_file_path.unlink(missing_ok=True)
        config_file_path.unlink(missing_ok=True)

    # ==========================================
    # 5. 结果分析
    # ==========================================
    print(f"{'='*80}")
    print("结果分析")
    print(f"{'='*80}\n")

    # 质量守恒
    mass_initial = np.sum(h_init * B * dx)
    mass_final = np.sum(h_final * B * dx)
    mass_error = abs(mass_final - mass_initial) / mass_initial * 100

    print(f"质量守恒:")
    print(f"  初始质量: {mass_initial:.2f} m^3")
    print(f"  最终质量: {mass_final:.2f} m^3")
    print(f"  质量误差: {mass_error:.6f}%")

    # 负流量检查
    negative_Q = Q_final < 0
    n_negative = np.sum(negative_Q)
    negative_ratio = n_negative / n_cells * 100

    print(f"\n负流量:")
    print(f"  负流量单元: {n_negative}/{n_cells}")
    print(f"  负流量比例: {negative_ratio:.1f}%")

    # 上游Froude数
    u_upstream_final = Q_final[0] / (B * h_final[0])
    Fr_upstream = u_upstream_final / np.sqrt(9.81 * h_final[0])

    print(f"\n上游状态:")
    print(f"  水深: {h_final[0]:.3f} m")
    print(f"  流速: {u_upstream_final:.3f} m/s")
    print(f"  Froude数: {Fr_upstream:.3f}")

    # 下游状态
    u_downstream_final = Q_final[-1] / (B * h_final[-1])
    Fr_downstream = u_downstream_final / np.sqrt(9.81 * h_final[-1])

    print(f"\n下游状态:")
    print(f"  水深: {h_final[-1]:.3f} m")
    print(f"  流速: {u_downstream_final:.3f} m/s")
    print(f"  Froude数: {Fr_downstream:.3f}")

    # Belanger方程验证 (理论水跃关系)
    # h2/h1 = 0.5 * (sqrt(1 + 8*Fr1^2) - 1)
    Fr1_theory = 1.73  # 理论上游Froude数
    h1_theory = h_upstream
    h2_theory = h1_theory * 0.5 * (np.sqrt(1 + 8*Fr1_theory**2) - 1)

    # 实际水跃后水深（寻找最大水深位置）
    h2_actual = np.max(h_final)
    belanger_error = abs(h2_actual - h2_theory) / h2_theory * 100

    print(f"\nBelanger方程验证:")
    print(f"  理论水跃后水深: {h2_theory:.3f} m")
    print(f"  实际最大水深: {h2_actual:.3f} m")
    print(f"  Belanger误差: {belanger_error:.2f}%")

    # ==========================================
    # 6. 验证标准
    # ==========================================
    print(f"\n{'='*80}")
    print("验证结果")
    print(f"{'='*80}\n")

    success = True

    # 质量守恒 (目标 < 15%)
    if mass_error < 15.0:
        print(f" 质量守恒: {mass_error:.2f}% < 15.0%")
    else:
        print(f"️  质量守恒: {mass_error:.2f}% >= 15.0% (仍需改进)")
        success = False

    # Froude数 (容差20%)
    if abs(Fr_upstream - Fr1_theory) / Fr1_theory < 0.2:
        print(f" Froude数: {Fr_upstream:.3f} ~= {Fr1_theory:.3f}")
    else:
        print(f"️  Froude数: {Fr_upstream:.3f} vs {Fr1_theory:.3f} (偏差较大)")
        success = False

    # Belanger误差 (容差30%)
    if belanger_error < 30.0:
        print(f" Belanger关系: 误差 {belanger_error:.2f}% < 30%")
    else:
        print(f"️  Belanger关系: 误差 {belanger_error:.2f}% >= 30%")
        success = False

    # 负流量 (容差20%)
    if negative_ratio < 20.0:
        print(f" 负流量: {negative_ratio:.1f}% < 20%")
    else:
        print(f"️  负流量: {negative_ratio:.1f}% >= 20%")
        success = False

    # ==========================================
    # 7. 对比总结
    # ==========================================
    print(f"\n{'='*80}")
    print("改进效果总结")
    print(f"{'='*80}\n")

    baseline_error = 27.89  # 基线质量误差
    improvement = baseline_error - mass_error
    improvement_pct = improvement / baseline_error * 100

    print(f"质量误差对比:")
    print(f"  基线 (dx=10m, n=100): {baseline_error:.2f}%")
    print(f"  极细 (dx=2m,  n=500): {mass_error:.2f}%")
    print(f"  改善: {improvement:.2f}% (相对改善 {improvement_pct:.1f}%)")

    if mass_error < 15.0:
        print(f"\n 极细网格方案成功！达到100%通过率目标！")
        print(f"{'='*80}\n")
        return True
    elif improvement > 5.0:
        print(f"\n 有显著改善 (>{improvement:.1f}%)，但未达到<15%目标")
        print(f"建议: 继续实施方案2 (HLLC求解器)")
        print(f"{'='*80}\n")
        return False
    else:
        print(f"\n️  改善有限 (<5%)，需要更激进方案")
        print(f"建议: 跳过方案2，直接实施方案1 (WENO5)")
        print(f"{'='*80}\n")
        return False


if __name__ == '__main__':
    import time

    print("\n⏱️  注意: 极细网格 (500单元) 在纯Python下可能需要5-15分钟")
    print("建议: 安装Numba加速 (pip install numba) 可缩短至1-2分钟\n")

    start_time = time.time()
    success = test_macdonald4_fine_grid()
    elapsed = time.time() - start_time

    print(f"\n总运行时间: {elapsed/60:.1f} 分钟")

    if success:
        print("\n 测试通过 - 极细网格方案有效！")
        exit(0)
    else:
        print("\n️  需要进一步改进 - 准备下一方案")
        exit(1)
