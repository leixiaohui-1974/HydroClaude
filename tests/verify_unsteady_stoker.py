import numpy as np
import sys
from pathlib import Path
import matplotlib.pyplot as plt

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver

def stoker_analytical(x, t, h_L, h_R, g=9.81):
    """
    Analytical solution for the Stoker Dam Break problem (idealized).
    x=0 is the dam location.
    """
    if t <= 0:
        return np.where(x < 0, h_L, h_R)
    
    c_L = np.sqrt(g * h_L)
    c_R = np.sqrt(g * h_R)
    
    # Rarefaction wave boundaries
    x_A = -c_L * t
    
    # Solve for h_star (intermediate depth) and u_star (intermediate velocity)
    # Using the shock jump conditions and Riemann invariants
    # For a simple case where u_L = u_R = 0
    def find_h_star(h_L, h_R, g):
        h_star = (h_L + h_R) / 2.0 # Initial guess
        for _ in range(20):
            c_star = np.sqrt(g * h_star)
            f = 2 * (c_L - c_star) - (h_star - h_R) * np.sqrt(g * (h_star + h_R) / (2 * h_star * h_R))
            # Numerical derivative for Newton
            eps = 1e-5
            c_star_eps = np.sqrt(g * (h_star + eps))
            f_eps = 2 * (c_L - c_star_eps) - (h_star + eps - h_R) * np.sqrt(g * (h_star + eps + h_R) / (2 * (h_star + eps) * h_R))
            df = (f_eps - f) / eps
            h_star = h_star - f / df
        return h_star

    h_star = find_h_star(h_L, h_R, g)
    u_star = 2 * (c_L - np.sqrt(g * h_star))
    
    # Shock speed
    S = u_star * h_star / (h_star - h_R)
    x_B = (u_star - np.sqrt(g * h_star)) * t
    x_C = S * t
    
    h_res = np.zeros_like(x)
    u_res = np.zeros_like(x)
    
    for i, xi in enumerate(x):
        if xi < x_A:
            h_res[i] = h_L
            u_res[i] = 0.0
        elif xi < x_B:
            # Inside rarefaction wave
            u_res[i] = 2/3 * (xi/t + c_L)
            h_res[i] = 1/g * (2/3 * c_L - 1/3 * xi/t)**2
        elif xi < x_C:
            # Intermediate state
            h_res[i] = h_star
            u_res[i] = u_star
        else:
            # Right state
            h_res[i] = h_R
            u_res[i] = 0.0
            
    return h_res, u_res

def run_stoker_test():
    L = 2000.0
    nx = 201
    dx = L / (nx - 1)
    h_L = 5.0
    h_R = 2.0
    g = 9.81
    
    solver = HydrostaticCanalSolver(length=L, nx=nx, B=10.0, S0=0.0, n=0.0, g=g)
    # Initial condition: Dam at x = 1000m
    solver.h = np.where(solver.x < 1000.0, h_L, h_R)
    solver.hu = np.zeros(nx)
    
    dt = 0.5
    total_time = 50.0
    steps = int(total_time / dt)
    
    print(f"Running Stoker Dam Break test for {total_time}s...")
    for s in range(steps):
        h_new, hu_new = solver.step_preissmann(dt, enforce_bc=False)
        solver.h = h_new
        solver.hu = hu_new
        
    # Analytical solution at t=50s
    x_relative = solver.x - 1000.0
    h_ana, u_ana = stoker_analytical(x_relative, total_time, h_L, h_R, g)
    
    rmse = np.sqrt(np.mean((solver.h - h_ana)**2))
    max_err = np.max(np.abs(solver.h - h_ana))
    
    print("\n==================================================")
    print("Unsteady Verification (Stoker Dam Break)")
    print("==================================================")
    print(f"RMSE Error: {rmse:.6f} m")
    print(f"Max Error:  {max_err:.6f} m")
    print("--------------------------------------------------")
    if rmse < 0.05: # 5cm threshold for shock capturing
        print("RESULT: PASS")
    else:
        print("RESULT: FAIL (Accuracy needs improvement)")
    print("==================================================\n")

if __name__ == "__main__":
    run_stoker_test()
