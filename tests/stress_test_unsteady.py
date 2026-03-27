import numpy as np
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver

def run_stress_test():
    # Parameters for a 10km canal
    L = 10000.0
    B = 10.0
    S0 = 0.0005
    n = 0.025
    g = 9.81
    nx = 101
    
    # Initial steady state: Q=10, h_down=3.0
    Q_init = 10.0
    h_down_init = 3.0
    
    solver = HydrostaticCanalSolver(length=L, nx=nx, B=B, S0=S0, n=n, g=g)
    
    print("Step 1: Computing initial steady state...")
    solver.solve_steady_state(Q_target=Q_init, h_downstream=h_down_init, verbose=False)
    print(f"Initial steady state reached. h_up={solver.h[0]:.4f}m")
    
    # Unsteady simulation: Rapidly increase Q from 10 to 50 in 60 seconds
    dt = 2.0
    total_time = 1200.0
    steps = int(total_time / dt)
    
    Q_target = 50.0
    ramp_time = 60.0
    
    print(f"\nStep 2: Starting unsteady stress test (Q: {Q_init} -> {Q_target} in {ramp_time}s)...")
    
    success = True
    try:
        for s in range(steps):
            t = s * dt
            # Linear ramp for upstream discharge
            if t <= ramp_time:
                Q_in = Q_init + (Q_target - Q_init) * (t / ramp_time)
            else:
                Q_in = Q_target
            
            # Downstream boundary remains constant
            h_out = h_down_init
            
            # Step the solver
            h_new, hu_new = solver.step_preissmann(dt, enforce_bc=True, Q_in=Q_in, h_out=h_out)
            
            # Update state
            solver.h = h_new
            solver.hu = hu_new
            
            # Check for stability
            if np.any(np.isnan(solver.h)) or np.any(solver.h < 0):
                print(f"FAILED at t={t}s: Numerical instability detected (NaN or negative depth).")
                success = False
                break
            
            if s % 100 == 0:
                print(f"Progress: {t/total_time*100:.1f}% (t={t}s), h_up={solver.h[0]:.4f}m, Q_in={Q_in:.2f}")
                
    except Exception as e:
        print(f"FAILED with error: {e}")
        success = False
        
    if success:
        print("\nSUCCESS: Unsteady simulation completed without crashing.")
        print(f"Final state: h_up={solver.h[0]:.4f}m, h_down={solver.h[-1]:.4f}m")
    else:
        print("\nRESULT: Stress test failed. Solver needs optimization.")

if __name__ == "__main__":
    run_stress_test()
