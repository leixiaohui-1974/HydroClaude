import numpy as np
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver
from solvers.gate import SluiceGate

def run_gate_test():
    # Parameters
    L = 5000.0
    B = 10.0
    S0 = 0.0005
    n = 0.025
    g = 9.81
    nx = 51
    
    # Initial state: Q=10, h_down=2.5
    Q_init = 10.0
    h_down_init = 2.5
    
    # Create solver and add a gate at the middle (2.5km)
    solver = HydrostaticCanalSolver(length=L, nx=nx, B=B, S0=S0, n=n, g=g)
    
    # Gate opening: starts at 1.5m, then closes to 0.8m at t=300s
    def gate_opening_func(t):
        if t < 300:
            return 1.5
        elif t < 600:
            # Linear closing from 1.5 to 0.8
            return 1.5 - (1.5 - 0.8) * (t - 300) / 300
        else:
            return 0.8
            
    gate = SluiceGate(position=2500.0, width=B, opening=gate_opening_func)
    solver.add_structure(gate)
    
    print("Step 1: Computing initial steady state with gate...")
    solver.solve_steady_state(Q_target=Q_init, h_downstream=h_down_init, verbose=False)
    print(f"Initial steady state reached. h_up={solver.h[0]:.4f}m, h_gate_up={solver.h[24]:.4f}m, h_gate_down={solver.h[26]:.4f}m")
    
    # Unsteady simulation
    dt = 2.0
    total_time = 1200.0
    steps = int(total_time / dt)
    
    print(f"\nStep 2: Starting unsteady simulation with dynamic gate adjustment...")
    
    success = True
    try:
        for s in range(steps):
            t = s * dt
            
            # Step the solver
            h_new, hu_new = solver.step_preissmann(dt, enforce_bc=True, Q_in=Q_init, h_out=h_down_init)
            
            # Update state
            solver.h = h_new
            solver.hu = hu_new
            
            # Apply internal BC for gate
            solver._apply_internal_bc(t=t, Q_target=Q_init)
            
            if np.any(np.isnan(solver.h)):
                print(f"FAILED at t={t}s: NaN detected.")
                success = False
                break
            
            if s % 150 == 0:
                opening = gate.get_opening(t)
                print(f"t={t:4.0f}s | Opening={opening:.2f}m | h_up={solver.h[0]:.3f}m | h_gate_up={solver.h[24]:.3f}m | h_gate_down={solver.h[26]:.3f}m")
                
    except Exception as e:
        print(f"FAILED with error: {e}")
        success = False
        
    if success:
        print("\nSUCCESS: Unsteady simulation with gate completed.")
        print(f"Final state: h_gate_up={solver.h[24]:.4f}m, h_gate_down={solver.h[26]:.4f}m, Jump={solver.h[24]-solver.h[26]:.4f}m")
    else:
        print("\nRESULT: Gate coupling test failed.")

if __name__ == "__main__":
    run_gate_test()
