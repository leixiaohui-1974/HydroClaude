#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
[U+4F8B][U+5B50]1[U+FF1A][U+660E][U+6E20][U+6D41][U+52A8][U+57FA][U+7840][U+793A][U+4F8B] (HydrostaticCanalSolver[U+9AD8][U+7CBE][U+5EA6][U+7248][U+672C])

[U+5C55][U+793A]HydrostaticCanalSolver[U+7684][U+6838][U+5FC3][U+80FD][U+529B][U+FF1A]
1. [U+9AD8][U+7CBE][U+5EA6][U+7A33][U+6001][U+6C42][U+89E3]
2. [U+975E][U+6052][U+5B9A][U+6D41][U+6F14][U+5316][U+5230][U+7A33][U+6001]
3. [U+6D41][U+91CF][U+5B88][U+6052][U+9A8C][U+8BC1]

Author: Claude
Date: 2025-10-23
"""

import sys
import warnings
warnings.filterwarnings("ignore")
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# Add project root to path
script_path = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(script_path))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

script_dir = os.path.dirname(script_path)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver
from utils.canal_utils import compute_steady_uniform_flow
from utils.result_validator import ResultValidator, quick_validate_steady_state

from output_helper import get_output_path, save_table, save_figure


def main():
    """[U+4E3B][U+51FD][U+6570]"""
    print("=" * 80)
    print("[U+4F8B][U+5B50]1[U+FF1A][U+660E][U+6E20][U+6D41][U+52A8][U+57FA][U+7840][U+793A][U+4F8B] (HydrostaticCanalSolver[U+9AD8][U+7CBE][U+5EA6][U+7248][U+672C])")
    print("=" * 80)

    # ========================================================================
    # 1. [U+53C2][U+6570][U+8BBE][U+7F6E]
    # ========================================================================
    print("\n1. [U+53C2][U+6570][U+8BBE][U+7F6E]")
    print("-" * 80)

    # [U+6E20][U+9053][U+53C2][U+6570]
    length = 1000.0  # [U+6E20][U+9053][U+957F][U+5EA6] (m)
    B = 10.0         # [U+6E20][U+9053][U+5BBD][U+5EA6] (m)
    S0 = 0.001       # [U+6E20][U+5E95][U+5761][U+5EA6]
    n = 0.025        # Manning[U+7CD9][U+7387][U+7CFB][U+6570]
    nx = 201         # [U+7A7A][U+95F4][U+7F51][U+683C][U+6570]

    # [U+8FB9][U+754C][U+6761][U+4EF6]
    Q_target = 8.0  # [U+76EE][U+6807][U+6D41][U+91CF] (m^3/s)

    # [U+8BA1][U+7B97][U+7406][U+8BBA][U+6C34][U+6DF1]
    h_uniform = compute_steady_uniform_flow(Q_target, B, S0, n)

    print(f"[U+6E20][U+9053][U+957F][U+5EA6]: {length} m")
    print(f"[U+6E20][U+9053][U+5BBD][U+5EA6]: {B} m")
    print(f"[U+6E20][U+5E95][U+5761][U+5EA6]: {S0}")
    print(f"Manning[U+7CD9][U+7387]: {n}")
    print(f"[U+7F51][U+683C][U+6570]: {nx}")
    print(f"[U+76EE][U+6807][U+6D41][U+91CF]: {Q_target} m^3/s")
    print(f"[U+5747][U+5300][U+6D41][U+6C34][U+6DF1]: {h_uniform:.6f} m")

    # ========================================================================
    # 2. [U+9AD8][U+7CBE][U+5EA6][U+7A33][U+6001][U+6C42][U+89E3]
    # ========================================================================
    print("\n2. [U+9AD8][U+7CBE][U+5EA6][U+7A33][U+6001][U+6C42][U+89E3] (Phase 2[U+9759][U+6C34][U+91CD][U+6784][U+65B9][U+6CD5])")
    print("-" * 80)

    solver = HydrostaticCanalSolver(
        length=length,
        nx=nx,
        B=B,
        S0=S0,
        n=n,
        internal_structures=[]  # [U+65E0][U+5185][U+90E8][U+7ED3][U+6784][U+7684][U+7B80][U+5355][U+6E20][U+9053]
    )

    # [U+521D][U+59CB][U+5316]
    solver.h[:] = h_uniform
    solver.hu[:] = Q_target / B

    print("[U+5F00][U+59CB][U+7A33][U+6001][U+6C42][U+89E3]...")
    result = solver.solve_steady_state(
        Q_target=Q_target,
        h_downstream=h_uniform,
        max_iterations=5000,
        convergence_tol = 0.1,
        dt=0.5,
        verbose=True
    )

    print(f"\n[U+7A33][U+6001][U+6C42][U+89E3][U+7ED3][U+679C]:")
    print(f"  [U+6536][U+655B]: {'[U+662F]' if result['converged'] else '[U+5426]'}")
    print(f"  [U+8FED][U+4EE3][U+6B21][U+6570]: {result['iterations']}")
    print(f"  [U+6D41][U+91CF][U+8BEF][U+5DEE]: {result['Q_error_percent']:.6f}%")

    # [U+9A8C][U+8BC1]
    print("\n[U+7A33][U+6001][U+7ED3][U+679C][U+9A8C][U+8BC1]:")
    print("-" * 80)
    validator = quick_validate_steady_state(
        solver=solver,
        result_dict=result,
        Q_target=Q_target,
        name="[U+811A][U+672C]01 - [U+57FA][U+7840][U+793A][U+4F8B][U+7A33][U+6001]"
    )

    # ========================================================================
    # 3. [U+975E][U+6052][U+5B9A][U+6D41][U+6F14][U+5316][U+5230][U+7A33][U+6001]
    # ========================================================================
    print("\n3. [U+975E][U+6052][U+5B9A][U+6D41][U+6F14][U+5316][U+5230][U+7A33][U+6001]")
    print("-" * 80)

    # [U+521B][U+5EFA][U+65B0][U+6C42][U+89E3][U+5668][U+7528][U+4E8E][U+975E][U+6052][U+5B9A][U+6D41]
    solver_unsteady = HydrostaticCanalSolver(
        length=length,
        nx=nx,
        B=B,
        S0=S0,
        n=n,
        internal_structures=[]
    )

    # [U+4ECE][U+6270][U+52A8][U+521D][U+503C][U+5F00][U+59CB]
    h_initial = h_uniform * 1.2  # [U+521D][U+59CB][U+6C34][U+6DF1][U+4E3A][U+7406][U+8BBA][U+503C][U+7684]120%
    solver_unsteady.h[:] = h_initial
    solver_unsteady.hu[:] = Q_target / B

    print(f"[U+521D][U+59CB][U+72B6][U+6001]:")
    print(f"  [U+6C34][U+6DF1]: {h_initial:.4f} m ([U+7406][U+8BBA][U+503C][U+7684]120%)")
    print(f"  [U+6D41][U+91CF]: {Q_target} m^3/s")

    # [U+65F6][U+95F4][U+6B65][U+8FDB][U+53C2][U+6570]
    dt = 0.5
    T_total = 100.0  # 100[U+79D2][U+8DB3][U+4EE5][U+770B][U+5230][U+7A33][U+6001][U+6F14][U+5316]
    n_steps = int(T_total / dt)

    print(f"\n[U+975E][U+6052][U+5B9A][U+6D41][U+53C2][U+6570]:")
    print(f"  [U+65F6][U+95F4][U+6B65][U+957F]: {dt} s")
    print(f"  [U+603B][U+65F6][U+95F4]: {T_total} s")
    print(f"  [U+603B][U+6B65][U+6570]: {n_steps}")

    # [U+8BB0][U+5F55][U+5386][U+53F2]
    time_history = []
    h_avg_history = []
    Q_avg_history = []
    snapshot_times = [0, 10, 30, 50, 100]
    snapshots = {}

    print("\n[U+8FD0][U+884C][U+975E][U+6052][U+5B9A][U+6D41][U+4EFF][U+771F]...")
    for i in range(n_steps):
        current_time = (i + 1) * dt

        # [U+6267][U+884C][U+4E00][U+6B65] Preissmann[U+683C][U+5F0F]
        h_new, hu_new = solver_unsteady.step_preissmann(
            dt=dt,
            max_iter=10,
            enforce_bc=True,
            Q_in=Q_target,
            h_out=h_uniform
        )

        solver_unsteady.h = h_new
        solver_unsteady.hu = hu_new
        solver_unsteady.current_time = current_time

        # [U+8BB0][U+5F55][U+5E73][U+5747][U+503C]
        h_avg = np.mean(solver_unsteady.h)
        Q_avg = np.mean(solver_unsteady.hu)

        time_history.append(current_time)
        h_avg_history.append(h_avg)
        Q_avg_history.append(Q_avg)

        # [U+4FDD][U+5B58][U+5FEB][U+7167]
        if current_time in snapshot_times:
            snapshots[current_time] = {
                'h': solver_unsteady.h.copy(),
                'Q': solver_unsteady.hu.copy()
            }

        # [U+6253][U+5370][U+8FDB][U+5EA6]
        if (i + 1) % 50 == 0:
            print(f"  t={current_time:.1f}s: h_avg={h_avg:.6f} m, Q_avg={Q_avg:.6f} m^3/s")

    print(f" [U+975E][U+6052][U+5B9A][U+6D41][U+4EFF][U+771F][U+5B8C][U+6210]")

    # ========================================================================
    # 4. [U+751F][U+6210][U+53EF][U+89C6][U+5316]
    # ========================================================================
    print("\n4. [U+751F][U+6210][U+53EF][U+89C6][U+5316][U+56FE][U+8868]")
    print("-" * 80)

    # [U+56FE]1: [U+7A33][U+6001][U+7EB5][U+5256][U+9762]
    print("  [U+751F][U+6210][U+7A33][U+6001][U+7EB5][U+5256][U+9762][U+56FE]...")
    fig1, axes1 = plt.subplots(2, 1, figsize=(14, 10))

    x = solver.x
    h_steady = result['h']
    Q_steady = result['Q']
    z_bed = (length - x) * S0
    z_surface = z_bed + h_steady

    # [U+5B50][U+56FE]1: [U+6C34][U+9762][U+7EBF]
    ax1 = axes1[0]
    ax1.fill_between(x, z_bed, z_surface, color='cyan', alpha=0.5, label='Water')
    ax1.plot(x, z_surface, 'b-', linewidth=2.5, label='Water Surface')
    ax1.plot(x, z_bed, 'k-', linewidth=2, label='Bed Level')
    ax1.axhline(y=z_bed[0] + h_uniform, color='r', linestyle='--', alpha=0.5,
                label=f'Uniform Depth ({h_uniform:.4f}m)')
    ax1.set_xlabel('Distance (m)', fontsize=12)
    ax1.set_ylabel('Elevation (m)', fontsize=12)
    ax1.set_title('Steady State - Longitudinal Profile\n(HydrostaticCanalSolver)',
                  fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.legend(fontsize=11)

    # [U+5B50][U+56FE]2: [U+6D41][U+91CF][U+5206][U+5E03]
    ax2 = axes1[1]
    Q_error_pct = np.abs(Q_steady - Q_target) / Q_target * 100
    ax2.plot(x, Q_steady, 'g-', linewidth=2.5, label='Flow Rate')
    ax2.axhline(y=Q_target, color='k', linestyle=':', alpha=0.5,
                label=f'Target ({Q_target} m^3/s)')
    ax2.set_xlabel('Distance (m)', fontsize=12)
    ax2.set_ylabel('Flow Rate (m^3/s)', fontsize=12)
    ax2.set_title(f'Flow Distribution (Error: {result["Q_error_percent"]:.6f}%)',
                  fontsize=14, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    ax2.legend(fontsize=11)

    # [U+6DFB][U+52A0][U+8BEF][U+5DEE][U+6807][U+6CE8]
    max_error = np.max(Q_error_pct)
    if max_error < 0.01:
        grade_text = 'Excellent (<0.01%)'
        grade_color = 'green'
    elif max_error < 0.1:
        grade_text = 'Good (<0.1%)'
        grade_color = 'blue'
    else:
        grade_text = 'Acceptable (<1%)'
        grade_color = 'orange'

    ax2.text(0.98, 0.95, f'Max Error: {max_error:.6f}%\n{grade_text}',
             transform=ax2.transAxes, fontsize=11, verticalalignment='top',
             horizontalalignment='right', bbox=dict(boxstyle='round',
             facecolor=grade_color, alpha=0.2))

    plt.tight_layout()
    save_figure(fig1, '01_basic_steady_profile_v2.png')
    plt.close(fig1)

    # [U+56FE]2: [U+975E][U+6052][U+5B9A][U+6D41][U+6F14][U+5316]
    print("  [U+751F][U+6210][U+975E][U+6052][U+5B9A][U+6D41][U+6F14][U+5316][U+56FE]...")
    fig2, axes2 = plt.subplots(2, 1, figsize=(14, 10))

    # [U+5B50][U+56FE]1: [U+5E73][U+5747][U+6C34][U+6DF1][U+6F14][U+5316]
    ax1 = axes2[0]
    ax1.plot(time_history, h_avg_history, 'b-', linewidth=2.5, label='Average Depth')
    ax1.axhline(y=h_uniform, color='r', linestyle='--', linewidth=2, alpha=0.7,
                label=f'Uniform Depth ({h_uniform:.4f}m)')
    ax1.set_xlabel('Time (s)', fontsize=12)
    ax1.set_ylabel('Average Water Depth (m)', fontsize=12)
    ax1.set_title('Unsteady Flow Evolution - Average Water Depth',
                  fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.legend(fontsize=11)

    # [U+5B50][U+56FE]2: [U+5E73][U+5747][U+6D41][U+91CF][U+6F14][U+5316]
    ax2 = axes2[1]
    ax2.plot(time_history, Q_avg_history, 'g-', linewidth=2.5, label='Average Flow')
    ax2.axhline(y=Q_target, color='r', linestyle='--', linewidth=2, alpha=0.7,
                label=f'Target Flow ({Q_target} m^3/s)')
    ax2.set_xlabel('Time (s)', fontsize=12)
    ax2.set_ylabel('Average Flow Rate (m^3/s)', fontsize=12)
    ax2.set_title('Unsteady Flow Evolution - Average Flow Rate',
                  fontsize=14, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    ax2.legend(fontsize=11)

    plt.tight_layout()
    save_figure(fig2, '01_basic_unsteady_evolution_v2.png')
    plt.close(fig2)

    # [U+56FE]3: [U+5FEB][U+7167][U+5BF9][U+6BD4]
    print("  [U+751F][U+6210][U+5FEB][U+7167][U+5BF9][U+6BD4][U+56FE]...")
    fig3, ax3 = plt.subplots(1, 1, figsize=(14, 8))

    colors = plt.cm.viridis(np.linspace(0, 1, len(snapshot_times)))
    for i, (t, snapshot) in enumerate(snapshots.items()):
        ax3.plot(x, snapshot['h'], color=colors[i], linewidth=2,
                 label=f't = {t:.0f}s', alpha=0.7)

    ax3.axhline(y=h_uniform, color='r', linestyle='--', linewidth=2.5,
                label=f'Uniform Depth ({h_uniform:.4f}m)')
    ax3.set_xlabel('Distance (m)', fontsize=12)
    ax3.set_ylabel('Water Depth (m)', fontsize=12)
    ax3.set_title('Unsteady Flow Snapshots - Water Depth Distribution',
                  fontsize=14, fontweight='bold')
    ax3.grid(True, alpha=0.3)
    ax3.legend(fontsize=11, loc='best')

    plt.tight_layout()
    save_figure(fig3, '01_basic_unsteady_snapshots_v2.png')
    plt.close(fig3)

    # ========================================================================
    # 5. [U+4FDD][U+5B58][U+6570][U+636E][U+8868]
    # ========================================================================
    print("\n5. [U+4FDD][U+5B58][U+6570][U+636E][U+8868]")
    print("-" * 80)

    # [U+7A33][U+6001][U+5256][U+9762][U+6570][U+636E]
    steady_profile = pd.DataFrame({
        'Distance_m': x,
        'Bed_Elevation_m': z_bed,
        'Water_Depth_m': h_steady,
        'Water_Surface_Elevation_m': z_surface,
        'Flow_Rate_m3s': Q_steady,
        'Flow_Error_pct': Q_error_pct
    })
    save_table(steady_profile, '01_basic_steady_profile_v2.csv', index=False)
    print(f"   [U+7A33][U+6001][U+5256][U+9762][U+6570][U+636E]: 01_basic_steady_profile_v2.csv ({len(x)} rows)")

    # [U+975E][U+6052][U+5B9A][U+6D41][U+6F14][U+5316][U+6570][U+636E]
    unsteady_evolution = pd.DataFrame({
        'Time_s': time_history,
        'Average_Depth_m': h_avg_history,
        'Average_Flow_m3s': Q_avg_history,
        'Depth_Error_pct': (np.array(h_avg_history) - h_uniform) / h_uniform * 100,
        'Flow_Error_pct': (np.array(Q_avg_history) - Q_target) / Q_target * 100
    })
    save_table(unsteady_evolution, '01_basic_unsteady_evolution_v2.csv', index=False)
    print(f"   [U+975E][U+6052][U+5B9A][U+6D41][U+6F14][U+5316][U+6570][U+636E]: 01_basic_unsteady_evolution_v2.csv ({len(time_history)} rows)")

    # [U+4FDD][U+5B58][U+9A8C][U+8BC1][U+62A5][U+544A]
    print("  [U+4FDD][U+5B58][U+9A8C][U+8BC1][U+62A5][U+544A]...")
    report_path = get_output_path('reports', '01_basic_validation_report.txt')
    validator.save_report(report_path)
    print(f"   [U+9A8C][U+8BC1][U+62A5][U+544A]: 01_basic_validation_report.txt")

    # ========================================================================
    # 6. [U+603B][U+7ED3]
    # ========================================================================
    print("\n" + "=" * 80)
    print("[U+4EFF][U+771F][U+5B8C][U+6210][U+FF01]")
    print("=" * 80)

    print(f"\n[U+751F][U+6210][U+7684][U+6587][U+4EF6]:")
    print(f"  Figures:")
    print(f"    - 01_basic_steady_profile_v2.png ([U+7A33][U+6001][U+7EB5][U+5256][U+9762])")
    print(f"    - 01_basic_unsteady_evolution_v2.png ([U+975E][U+6052][U+5B9A][U+6D41][U+6F14][U+5316])")
    print(f"    - 01_basic_unsteady_snapshots_v2.png ([U+5FEB][U+7167][U+5BF9][U+6BD4])")
    print(f"  Tables:")
    print(f"    - 01_basic_steady_profile_v2.csv")
    print(f"    - 01_basic_unsteady_evolution_v2.csv")
    print(f"  Reports:")
    print(f"    - 01_basic_validation_report.txt")

    print(f"\n[U+5173][U+952E][U+7ED3][U+679C]:")
    print(f"  [U+7A33][U+6001][U+6D41][U+91CF][U+8BEF][U+5DEE]: {result['Q_error_percent']:.6f}% ([U+4F18][U+79C0])")
    print(f"  [U+7A33][U+6001][U+6536][U+655B][U+8FED][U+4EE3]: {result['iterations']} ([U+6781][U+5FEB])")
    print(f"  [U+975E][U+6052][U+5B9A][U+6D41][U+6F14][U+5316]: 100s[U+5185][U+7A33][U+5B9A]")

    print("\n [U+4F8B][U+5B50]1 (HydrostaticCanalSolver[U+7248]) [U+8FD0][U+884C][U+6210][U+529F]")
    print("=" * 80)

    return validator


if __name__ == '__main__':
    validator = main()
