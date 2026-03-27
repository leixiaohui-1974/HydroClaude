import numpy as np
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver
from utils.canal_utils import compute_steady_uniform_flow

def standard_step_method(Q, B, n, S0, g, h_down, x_grid):
    """
    Standard Step Method to compute backwater curve (M1/M2) analytically.
    Energy Equation: H = z + h + v^2/(2g)
    dH/dx = -Sf
    """
    nx = len(x_grid)
    h_analytical = np.zeros(nx)
    h_analytical[-1] = h_down
    
    for i in range(nx - 2, -1, -1):
        dx = x_grid[i+1] - x_grid[i]
        h_curr = h_analytical[i+1]
        
        # Iterative solve for h[i] using Energy Equation
        # H[i] = H[i+1] + Sf_avg * dx
        # z[i] + h[i] + v[i]^2/2g = z[i+1] + h[i+1] + v[i+1]^2/2g + Sf_avg * dx
        
        z_curr = -S0 * x_grid[i]
        z_next = -S0 * x_grid[i+1]
        
        v_next = Q / (B * h_curr)
        E_next = z_next + h_curr + v_next**2 / (2 * g)
        
        # Manning Sf = (n*Q / (A*R^(2/3)))^2
        # Use actual hydraulic radius R = (B*h)/(B+2h)
        R_next = (B * h_curr) / (B + 2.0 * h_curr)
        Sf_next = (n * Q / (B * h_curr * R_next**(2/3)))**2
        
        h_guess = h_curr
        for _ in range(10):
            v_guess = Q / (B * h_guess)
            R_guess = (B * h_guess) / (B + 2.0 * h_guess)
            Sf_guess = (n * Q / (B * h_guess * R_guess**(2/3)))**2
            Sf_avg = 0.5 * (Sf_next + Sf_guess)
            
            # Residual of Energy Equation
            f = z_curr + h_guess + v_guess**2 / (2 * g) - (E_next + Sf_avg * dx)
            # Derivative df/dh approx 1 - Fr^2
            Fr2 = (v_guess**2) / (g * h_guess)
            df = 1.0 - Fr2
            
            h_guess = h_guess - f / df
            if abs(f) < 1e-8:
                break
        h_analytical[i] = h_guess
        
    return h_analytical

def run_verification():
    # Parameters
    L = 10000.0
    B = 10.0
    S0 = 0.0005
    n = 0.025
    g = 9.81
    Q = 15.0
    h_down = 3.5  # M1 curve (h_down > h_normal)
    nx = 101
    
    # 1. Compute Analytical Solution
    x_grid = np.linspace(0, L, nx)
    h_analytical = standard_step_method(Q, B, n, S0, g, h_down, x_grid)
    
    # 2. Run HydroClaude Steady Solver
    solver = HydrostaticCanalSolver(length=L, nx=nx, B=B, S0=S0, n=n, g=g)
    result = solver.solve_steady_state(Q_target=Q, h_downstream=h_down, max_iterations=5000, convergence_tol=1e-5)
    h_hydro = solver.h
    
    # 3. Compare
    rmse = np.sqrt(np.mean((h_hydro - h_analytical)**2))
    max_err = np.max(np.abs(h_hydro - h_analytical))
    
    print("="*50)
    print("Steady State Verification (M1 Backwater Curve)")
    print("="*50)
    print(f"Parameters: Q={Q}, S0={S0}, n={n}, L={L}")
    print(f"Downstream Boundary: h={h_down}m")
    print("-" * 50)
    print(f"RMSE Error: {rmse:.6f} m")
    print(f"Max Error:  {max_err:.6f} m")
    print("-" * 50)
    
    if rmse < 0.01:
        print("RESULT: PASS (Accuracy within 1cm)")
    else:
        print("RESULT: FAIL (Accuracy exceeds 1cm)")
    print("="*50)

if __name__ == "__main__":
    run_verification()
