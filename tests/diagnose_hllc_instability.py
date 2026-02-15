"""
Diagnose HLLC Numerical Instability

Purpose:
    Track HLLC internal state to identify source of NaN

Strategy:
    - Run Dam Break with HLLC
    - Record state every step
    - Identify first NaN occurrence
    - Analyze state before/after NaN
"""

import numpy as np
import warnings
warnings.filterwarnings("ignore")
import sys
import pytest
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from solvers.godunov_fvm_solver import GodunvFVMSolver
except ImportError as e:
    pytest.skip(f"Required module not available: {e}", allow_module_level=True)



def diagnose_hllc_instability():
    """Run HLLC Dam Break with detailed diagnostic output"""

    print("="*70)
    print("HLLC Numerical Instability Diagnosis")
    print("="*70)
    print()

    # Configuration
    width = 10.0
    length = 1000.0
    n_cells = 200
    dx = length / n_cells
    t_final = 5.0

    print(f"Configuration:")
    print(f"  Domain: {length}m x {width}m")
    print(f"  Cells: {n_cells} (dx = {dx:.2f}m)")
    print(f"  Target time: {t_final}s")
    print()

    # Initial conditions: Dam Break
    x_centers = np.linspace(dx/2, length - dx/2, n_cells)
    h_init = np.where(x_centers < length/2, 10.0, 1.0)
    Q_init = np.zeros(n_cells)

    # Boundary conditions
    bc_left = {'type': 'free'}
    bc_right = {'type': 'free'}

    # Create HLLC solver
    print("Creating HLLC solver...")
    solver = GodunvFVMSolver(
        width=width,
        length=length,
        n_cells=n_cells,
        manning_n=0.0,
        cfl=0.3,
        order=1,
        use_numba=True,
        riemann_solver='hllc',
        slope=0.0
    )

    solver.initialize(h_init, Q_init, bc_left, bc_right)
    print(f"Initial mass: {np.sum(solver.h * solver.dx * solver.B):.2f} m^3")
    print()

    # Run with diagnostic output
    print("Running simulation with diagnostics...")
    print()

    nan_detected = False
    last_good_state = None
    first_nan_state = None

    step_count = 0
    while solver.t < t_final and not nan_detected:
        # Record state before step
        h_before = solver.h.copy()
        Q_before = solver.Q.copy()
        t_before = solver.t

        # Take step
        solver.step()
        step_count += 1

        # Check for NaN
        has_nan_h = np.any(np.isnan(solver.h))
        has_nan_Q = np.any(np.isnan(solver.Q))

        if has_nan_h or has_nan_Q:
            nan_detected = True
            first_nan_state = {
                't': solver.t,
                'dt': solver.dt,
                'h': solver.h.copy(),
                'Q': solver.Q.copy(),
                'h_before': h_before,
                'Q_before': Q_before
            }

            print(f" NaN DETECTED at step {step_count}, t={solver.t:.3f}s")
            print()
            break

        # Record last good state
        last_good_state = {
            't': solver.t,
            'dt': solver.dt,
            'h': solver.h.copy(),
            'Q': solver.Q.copy()
        }

        # Print progress every 5 steps
        if step_count % 5 == 0:
            max_h = np.max(solver.h)
            max_Q = np.max(np.abs(solver.Q))
            min_h = np.min(solver.h)
            print(f"Step {step_count:3d}: t={solver.t:6.3f}s, dt={solver.dt:.4f}s, "
                  f"h=[{min_h:.3f}, {max_h:.3f}]m, max|Q|={max_Q:.1f}m^3/s")

    print()

    if nan_detected:
        print("="*70)
        print("NaN Analysis")
        print("="*70)
        print()

        # Find NaN locations
        nan_h_idx = np.where(np.isnan(first_nan_state['h']))[0]
        nan_Q_idx = np.where(np.isnan(first_nan_state['Q']))[0]

        print(f"NaN occurred at t={first_nan_state['t']:.3f}s")
        print(f"Time step: dt={first_nan_state['dt']:.4f}s")
        print()

        print(f"NaN locations:")
        print(f"  h: {len(nan_h_idx)} cells")
        if len(nan_h_idx) > 0:
            print(f"     Indices: {nan_h_idx[:10]}{'...' if len(nan_h_idx) > 10 else ''}")
        print(f"  Q: {len(nan_Q_idx)} cells")
        if len(nan_Q_idx) > 0:
            print(f"     Indices: {nan_Q_idx[:10]}{'...' if len(nan_Q_idx) > 10 else ''}")
        print()

        # Analyze first NaN location
        if len(nan_h_idx) > 0:
            first_nan_i = nan_h_idx[0]
        elif len(nan_Q_idx) > 0:
            first_nan_i = nan_Q_idx[0]
        else:
            first_nan_i = None

        if first_nan_i is not None:
            print(f"First NaN at cell i={first_nan_i} (x={x_centers[first_nan_i]:.1f}m):")
            print()

            # State before NaN
            h_bf = first_nan_state['h_before']
            Q_bf = first_nan_state['Q_before']

            print("State BEFORE time step:")
            window = 2  # Show +/-2 cells
            for offset in range(-window, window+1):
                idx = first_nan_i + offset
                if 0 <= idx < n_cells:
                    marker = " <- NaN" if idx == first_nan_i else ""
                    print(f"  Cell {idx:3d}: h={h_bf[idx]:8.4f}m, Q={Q_bf[idx]:9.3f}m^3/s{marker}")
            print()

            # State after NaN
            h_af = first_nan_state['h']
            Q_af = first_nan_state['Q']

            print("State AFTER time step:")
            for offset in range(-window, window+1):
                idx = first_nan_i + offset
                if 0 <= idx < n_cells:
                    marker = " <- NaN" if idx == first_nan_i else ""
                    h_val = h_af[idx]
                    Q_val = Q_af[idx]
                    h_str = f"{h_val:8.4f}" if not np.isnan(h_val) else "    NaN"
                    Q_str = f"{Q_val:9.3f}" if not np.isnan(Q_val) else "      NaN"
                    print(f"  Cell {idx:3d}: h={h_str}m, Q={Q_str}m^3/s{marker}")
            print()

            # Compute velocities
            print("Velocities BEFORE:")
            for offset in range(-window, window+1):
                idx = first_nan_i + offset
                if 0 <= idx < n_cells:
                    u = Q_bf[idx] / (h_bf[idx] * width + 1e-10)
                    marker = " <- NaN" if idx == first_nan_i else ""
                    print(f"  Cell {idx:3d}: u={u:8.3f}m/s{marker}")
            print()

            # Check for dry cells
            print("Dry cell check (h < 0.01m):")
            for offset in range(-window, window+1):
                idx = first_nan_i + offset
                if 0 <= idx < n_cells:
                    is_dry = h_bf[idx] < 0.01
                    marker = " <- DRY" if is_dry else ""
                    print(f"  Cell {idx:3d}: h={h_bf[idx]:8.4f}m{marker}")
            print()

        # Last good state summary
        if last_good_state is not None:
            print("Last GOOD state (before NaN):")
            print(f"  t = {last_good_state['t']:.3f}s")
            print(f"  dt = {last_good_state['dt']:.4f}s")
            print(f"  h: [{np.min(last_good_state['h']):.3f}, {np.max(last_good_state['h']):.3f}]m")
            print(f"  Q: [{np.min(last_good_state['Q']):.3f}, {np.max(last_good_state['Q']):.3f}]m^3/s")
            print()

        print("="*70)
        print("Hypothesis")
        print("="*70)
        print()

        # Check for common issues
        print("Checking common causes of NaN:")
        print()

        # 1. Negative depth
        if last_good_state is not None:
            min_h = np.min(last_good_state['h'])
            if min_h < 0:
                print(f" Negative depth detected: min(h) = {min_h:.6f}m")
                print("   -> sqrt(g*h) will produce NaN")
            else:
                print(f" No negative depths (min h = {min_h:.6f}m)")

        # 2. Dry cells
        if last_good_state is not None:
            dry_cells = np.sum(last_good_state['h'] < 0.01)
            if dry_cells > 0:
                print(f" {dry_cells} dry cells (h < 0.01m) detected")
                print("   -> Potential division by zero in HLLC")
            else:
                print(" No dry cells")

        # 3. Extreme velocities
        if last_good_state is not None:
            u = last_good_state['Q'] / (last_good_state['h'] * width + 1e-10)
            max_u = np.max(np.abs(u))
            if max_u > 20.0:  # Unrealistic for shallow water
                print(f" Extreme velocities detected: max|u| = {max_u:.1f}m/s")
                print("   -> Possible numerical instability")
            else:
                print(f" Velocities reasonable (max|u| = {max_u:.1f}m/s)")

        print()

    else:
        print(" Simulation completed without NaN")
        print(f"   Final time: {solver.t:.3f}s")
        print(f"   Total steps: {step_count}")

    print()
    print("="*70)
    print()


if __name__ == '__main__':
    diagnose_hllc_instability()
