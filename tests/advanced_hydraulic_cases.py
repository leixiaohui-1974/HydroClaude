import numpy as np
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver
from solvers.gate import SluiceGate

def run_hydraulic_jump_test():
    """
    Case 1: Hydraulic Jump (Supercritical to Subcritical)
    L=1000m, S0=0.01 (Steep) then S0=0.0005 (Mild)
    """
    print("Testing Case: Hydraulic Jump (Composite Slope)...")
    L = 1000.0
    nx = 101
    dx = L / (nx - 1)
    B = 10.0
    n = 0.015
    Q = 30.0
    
    # Create solver with composite slope
    solver = HydrostaticCanalSolver(length=L, nx=nx, B=B, S0=0.001, n=n)
    # Manually set composite slope: first 500m is steep (0.02), last 500m is mild (0.0005)
    solver.z = np.zeros(nx)
    for i in range(nx):
        if i <= 50:
            solver.z[i] = -0.02 * (i * dx)
        else:
            solver.z[i] = solver.z[50] - 0.0005 * ((i - 50) * dx)
            
    # Solve steady state
    # Downstream boundary: h_down = 3.0m (Subcritical)
    # Upstream boundary: h_up = 0.5m (Supercritical)
    try:
        solver.solve_steady_state(Q_target=Q, h_downstream=3.0, max_iterations=2000, verbose=False)
        print(f"  Steady state reached. h_up={solver.h[0]:.4f}m, h_mid={solver.h[50]:.4f}m, h_down={solver.h[-1]:.4f}m")
        
        # Check for jump: Fr should cross 1.0
        v = Q / (B * solver.h)
        Fr = v / np.sqrt(9.81 * solver.h)
        jump_idx = np.where(np.diff(np.sign(Fr - 1.0)))[0]
        if len(jump_idx) > 0:
            print(f"  Hydraulic jump detected near x={solver.x[jump_idx[0]]:.1f}m")
            return True
        else:
            print("  No hydraulic jump detected (Check parameters).")
            return False
    except Exception as e:
        print(f"  FAILED with error: {e}")
        return False

def run_series_gates_test():
    """
    Case 2: Series Gates (3 gates in 10km canal)
    """
    print("\nTesting Case: Series Gates (Unsteady Interaction)...")
    L = 10000.0
    nx = 101
    B = 10.0
    S0 = 0.0005
    n = 0.025
    Q = 20.0
    
    solver = HydrostaticCanalSolver(length=L, nx=nx, B=B, S0=S0, n=n)
    # Add 3 gates at 2.5km, 5.0km, 7.5km
    gate1 = SluiceGate(position=2500.0, width=B, opening=1.5)
    gate2 = SluiceGate(position=5000.0, width=B, opening=1.5)
    gate3 = SluiceGate(position=7500.0, width=B, opening=1.5)
    solver.add_structure(gate1)
    solver.add_structure(gate2)
    solver.add_structure(gate3)
    
    print("  Computing initial steady state with 3 gates...")
    solver.solve_steady_state(Q_target=Q, h_downstream=3.0, verbose=False)
    
    # Unsteady: Close gate 2 slightly
    print("  Starting unsteady simulation (Closing middle gate)...")
    dt = 5.0
    total_time = 600.0
    steps = int(total_time / dt)
    
    success = True
    for s in range(steps):
        t = s * dt
        # Dynamic opening for gate 2: 1.5m -> 1.0m
        if t > 100:
            gate2.opening_func = lambda t: max(1.0, 1.5 - 0.001 * (t - 100))
            
        h_new, hu_new = solver.step_preissmann(dt, enforce_bc=True, Q_in=Q, h_out=3.0)
        solver.h, solver.hu = h_new, hu_new
        solver._apply_internal_bc(t=t, Q_target=Q)
        
        if np.any(np.isnan(solver.h)):
            print(f"  FAILED at t={t}s: NaN detected.")
            success = False
            break
            
    if success:
        print(f"  SUCCESS: Series gates simulation completed. h_gate2_up={solver.h[50]:.4f}m")
    return success

if __name__ == "__main__":
    print("==================================================")
    print("Advanced Hydraulic Cases Validation")
    print("==================================================")
    r1 = run_hydraulic_jump_test()
    r2 = run_series_gates_test()
    print("==================================================")
    print(f"Summary: {'PASS' if r1 and r2 else 'FAIL'}")
    print("==================================================")
