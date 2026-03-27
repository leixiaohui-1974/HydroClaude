import numpy as np
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver

def standard_step_method(L, nx, B, S0, n, Q, h_down, g=9.81):
    """
    Reference Standard Step Method (SSM) for analytical comparison.
    Supports both subcritical and supercritical flow.
    """
    x = np.linspace(0, L, nx)
    dx = L / (nx - 1)
    h = np.zeros(nx)
    z = -S0 * x
    
    # Calculate critical depth
    h_c = (Q**2 / (g * B**2))**(1/3)
    # Calculate normal depth (Manning's)
    h_n = 1.0 # Initial guess
    for _ in range(20):
        R = (B * h_n) / (B + 2.0 * h_n)
        f = (n * Q / (B * h_n * R**(2/3)))**2 - S0
        df = -2 * (n * Q)**2 / (B**2 * h_n**3 * R**(4/3)) * (1 + 2/3 * (B/(B+2*h_n))) # Approx
        h_n = max(1e-6, h_n - f/df)

    if S0 <= (n**2 * g * B**2 / (B * (B/(B+2*h_c))**(4/3))): # Mild slope
        h[-1] = h_down
        for i in range(nx - 2, -1, -1):
            z_curr, z_next = z[i], z[i+1]
            h_next = h[i+1]
            v_next = Q / (B * h_next)
            E_next = z_next + h_next + v_next**2 / (2 * g)
            R_next = (B * h_next) / (B + 2.0 * h_next)
            Sf_next = (n * Q / (B * h_next * R_next**(2/3)))**2
            h_guess = max(h_next, 1e-6)
            for _ in range(30):
                h_guess = max(h_guess, 1e-6)
                v_guess = Q / (B * h_guess)
                R_guess = (B * h_guess) / (B + 2.0 * h_guess)
                Sf_guess = (n * Q / (B * h_guess * R_guess**(2/3)))**2
                Sf_avg = 0.5 * (Sf_next + Sf_guess)
                f = z_curr + h_guess + v_guess**2 / (2 * g) - (E_next + Sf_avg * dx)
                Fr2 = (v_guess**2) / (g * h_guess)
                df = 1.0 - Fr2 + 1.5 * Sf_avg * dx / h_guess
                if abs(df) < 0.01: df = 0.01 if df >= 0 else -0.01
                dh = np.clip(f / df, -0.5 * h_guess, 2.0 * h_guess)
                h_guess -= dh
                if abs(f) < 1e-9: break
            h[i] = h_guess
    else: # Steep slope
        h[0] = h_n * 0.99 # Start slightly below normal depth for S1, to allow convergence to normal depth
        for i in range(1, nx):
            z_up, z_curr = z[i-1], z[i]
            h_up = h[i-1]
            v_up = Q / (B * h_up)
            E_up = z_up + h_up + v_up**2 / (2 * g)
            R_up = (B * h_up) / (B + 2.0 * h_up)
            Sf_up = (n * Q / (B * h_up * R_up**(2/3)))**2
            h_guess = max(h_n * 1.01, 1e-6) # Start guess slightly above normal depth for S1, as it approaches normal depth from above
            for _ in range(30):
                h_guess = max(h_guess, 1e-6)
                v_guess = Q / (B * h_guess)
                R_guess = (B * h_guess) / (B + 2.0 * h_guess)
                Sf_guess = (n * Q / (B * h_guess * R_guess**(2/3)))**2
                Sf_avg = 0.5 * (Sf_up + Sf_guess)
                f = z_curr + h_guess + v_guess**2 / (2 * g) - (E_up - Sf_avg * dx)
                Fr2 = (v_guess**2) / (g * h_gues                # For supercritical flow, the energy equation is E_curr = E_up - Sf_avg * dx
                 # For supercritical flow, the energy equation is E_curr = E_up - Sf_avg * dx
                # The derivative of Sf_avg with respect to h_guess is negative, so the term should be positive in df.
                df = 1.0 - Fr2 + 1.5 * Sf_avg * dx / h_guessss
                if abs(df) < 0.01: df = 0.01 if df >= 0 else -0.01
                dh = np.clip(f / df, -0.5 * h_guess, 2.0 * h_guess)
                h_guess -= dh
                if abs(f) < 1e-9: break
            h[i] = h_guess
    return h

def run_test_case(name, L, nx, B, S0, n, Q, h_down):
    print(f"Testing Case: {name}...")
    solver = HydrostaticCanalSolver(length=L, nx=nx, B=B, S0=S0, n=n)
    solver.solve_steady_state(Q_target=Q, h_downstream=h_down, verbose=False)
    
    h_ref = standard_step_method(L, nx, B, S0, n, Q, h_down)
    rmse = np.sqrt(np.mean((solver.h - h_ref)**2))
    max_err = np.max(np.abs(solver.h - h_ref))
    
    status = "PASS" if rmse < 0.01 else "FAIL"
    print(f"  RMSE: {rmse:.6f}m, Max Err: {max_err:.6f}m -> {status}")
    return rmse < 0.01

def main():
    cases = [
        # name, L, nx, B, S0, n, Q, h_down
        ("M1 Backwater (Mild Slope)", 10000, 101, 10, 0.0005, 0.025, 15, 3.5),
        ("M2 Drawdown (Mild Slope)", 10000, 101, 10, 0.0005, 0.025, 15, 1.5),
        ("S1 Backwater (Steep Slope)", 2000, 51, 10, 0.01, 0.015, 50, 4.0),
        ("Long Canal (100km)", 100000, 501, 20, 0.0002, 0.02, 100, 6.0),
        ("High Flow (1000 m3/s)", 5000, 101, 50, 0.001, 0.03, 1000, 10.0),
    ]
    
    results = []
    for c in cases:
        results.append(run_test_case(*c))
    
    print("\n==================================================")
    print("Steady Flow Validation Matrix Summary")
    print("==================================================")
    passed = sum(results)
    total = len(results)
    print(f"Total Cases: {total} | Passed: {passed} | Failed: {total - passed}")
    print("==================================================\n")

if __name__ == "__main__":
    main()
