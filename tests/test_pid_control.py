import numpy as np
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver
from solvers.gate import SluiceGate, PIDController

def run_pid_test():
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
    
    # Create solver
    solver = HydrostaticCanalSolver(length=L, nx=nx, B=B, S0=S0, n=n, g=g)
    
    # Target: Maintain upstream water level at 2.0m
    # PID parameters: Kp=0.5, Ki=0.01, Kd=0.1
    pid = PIDController(Kp=0.5, Ki=0.01, Kd=0.1, target=2.0, min_out=0.1, max_out=3.0)
    gate = SluiceGate(position=2500.0, width=B, opening=pid)
    solver.add_structure(gate)
    
    print("Step 1: Computing initial steady state...")
    solver.solve_steady_state(Q_target=Q_init, h_downstream=h_down_init, verbose=False)
    print(f"Initial steady state reached. h_up={solver.h[0]:.4f}m, h_gate_up={solver.h[24]:.4f}m")
    
    # Unsteady simulation: Sudden increase in upstream discharge at t=200s
    dt = 2.0
    total_time = 2000.0
    steps = int(total_time / dt)
    
    print(f"\nStep 2: Starting PID closed-loop simulation (Disturbance at t=200s)...")
    
    success = True
    try:
        for s in range(steps):
            t = s * dt
            
            # Disturbance: Q_in increases from 10 to 20 at t=200s
            Q_in = 10.0 if t < 200 else 20.0
            
            # 1. Update PID based on current water level at gate upstream (index 24)
            gate.update_pid(solver.h[24], t)
            
            # 2. Step the solver
            h_new, hu_new = solver.step_preissmann(dt, enforce_bc=True, Q_in=Q_in, h_out=h_down_init)
            
            # 3. Update state
            solver.h = h_new
            solver.hu = hu_new
            
            # 4. Apply internal BC for gate
            solver._apply_internal_bc(t=t, Q_target=Q_in)
            
            if np.any(np.isnan(solver.h)):
                print(f"FAILED at t={t}s: NaN detected.")
                success = False
                break
            
            if s % 200 == 0:
                opening = gate.get_opening(t)
                print(f"t={t:4.0f}s | Q_in={Q_in:2.0f} | Opening={opening:.2f}m | h_gate_up={solver.h[24]:.3f}m (Target: 2.000)")
                
    except Exception as e:
        print(f"FAILED with error: {e}")
        success = False
        
    if success:
        print("\nSUCCESS: PID closed-loop simulation completed.")
        print(f"Final state: h_gate_up={solver.h[24]:.4f}m (Error: {abs(solver.h[24]-2.0):.4f}m)")
    else:
        print("\nRESULT: PID control test failed.")

if __name__ == "__main__":
    run_pid_test()
