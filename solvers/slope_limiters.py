#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Slope

TVD (Total Variation Diminishing) slope
- Minmod
- Van Leer
- Superbee
- MC (Monotonized Central)

MUSCL

: Claude
: 2025-10-23
"""

import numpy as np


def minmod(a, b, c=None):
    """
    Minmod

    :
      minmod(a,b,c) = { min(a,b,c)  if a,b,c > 0
                      { max(a,b,c)  if a,b,c < 0
                      { 0           otherwise

    :
      minmod(a,b) = { min(a,b)  if a,b > 0
                    { max(a,b)  if a,b < 0
                    { 0         otherwise

    Args:
        a, b, c: 

    Returns:
        
    """
    if c is None:
        # 
        return np.where(
            a * b > 0,
            np.where(np.abs(a) < np.abs(b), a, b),
            0.0
        )
    else:
        # 
        return np.where(
            (a > 0) & (b > 0) & (c > 0),
            np.minimum(np.minimum(a, b), c),
            np.where(
                (a < 0) & (b < 0) & (c < 0),
                np.maximum(np.maximum(a, b), c),
                0.0
            )
        )


def vanleer(a, b):
    """
    Van Leer

    φ(r) = (r + |r|) / (1 + |r|)
     r = a/b

    

    Args:
        a, b: 

    Returns:
        
    """
    # 
    eps = 1e-12

    #  r
    r = np.where(np.abs(b) > eps, a / b, 0.0)

    # Van Leer
    phi = (r + np.abs(r)) / (1 + np.abs(r))

    return phi * b


def superbee(a, b):
    """
    Superbee

    φ(r) = max(0, min(2r, 1), min(r, 2))
     r = a/b

    

    Args:
        a, b: 

    Returns:
        
    """
    eps = 1e-12

    #  r
    r = np.where(np.abs(b) > eps, a / b, 0.0)

    # Superbee
    phi = np.maximum(
        0,
        np.maximum(
            np.minimum(2 * r, 1),
            np.minimum(r, 2)
        )
    )

    return phi * b


def mc_limiter(a, b):
    """
    MC (Monotonized Central) 

    φ(r) = max(0, min((1+r)/2, 2, 2r))
     r = a/b

    MinmodSuperbee

    Args:
        a, b: 

    Returns:
        
    """
    eps = 1e-12

    #  r
    r = np.where(np.abs(b) > eps, a / b, 0.0)

    # MC
    phi = np.maximum(
        0,
        np.minimum(
            np.minimum((1 + r) / 2, 2),
            2 * r
        )
    )

    return phi * b


def compute_limited_slope(U_minus, U_center, U_plus, dx_minus, dx_center, dx_plus,
                          limiter='minmod', theta=1.5):
    """
    TVD

    MUSCL

    Args:
        U_minus: i-1
        U_center: i
        U_plus: i+1
        dx_minus: i-1
        dx_center: i
        dx_plus: i+1
        limiter:  ('minmod', 'vanleer', 'superbee', 'mc')
        theta: Minmodtheta (1.0-2.0, 1.5)

    Returns:
        sigma: 
    """
    # 
    grad_backward = (U_center - U_minus) / dx_center
    grad_forward = (U_plus - U_center) / dx_plus
    grad_central = (U_plus - U_minus) / (dx_center + dx_plus)

    if limiter == 'minmod':
        # Minmod
        sigma = minmod(theta * grad_backward, grad_central, theta * grad_forward)

    elif limiter == 'vanleer':
        # Van Leerbackwardforward
        sigma = vanleer(grad_backward, grad_forward)

    elif limiter == 'superbee':
        # Superbeebackwardforward
        sigma = superbee(grad_backward, grad_forward)

    elif limiter == 'mc':
        # MC
        sigma = mc_limiter(grad_backward, grad_forward)

    else:
        raise ValueError(f"Unknown limiter: {limiter}")

    return sigma


# 
if __name__ == "__main__":
    import matplotlib.pyplot as plt

    print("=" * 70)
    print("Slope")
    print("=" * 70)
    print()

    # 1: 
    print("1: ")
    a_vals = [1.0, -1.0, 1.0, 0.5]
    b_vals = [2.0, -0.5, -1.0, 1.0]

    print(f"{'a':>6} | {'b':>6} | {'minmod':>8} | {'vanleer':>8} | {'superbee':>8} | {'mc':>8}")
    print("-" * 70)

    for a, b in zip(a_vals, b_vals):
        mm = minmod(a, b)
        vl = vanleer(a, b)
        sb = superbee(a, b)
        mc = mc_limiter(a, b)
        print(f"{a:>6.2f} | {b:>6.2f} | {mm:>8.4f} | {vl:>8.4f} | {sb:>8.4f} | {mc:>8.4f}")

    print()

    # 2: 
    print("2: ")

    r = np.linspace(-2, 4, 200)

    # phi(r)
    phi_minmod = np.maximum(0, np.minimum(1, r))
    phi_vanleer = (r + np.abs(r)) / (1 + np.abs(r))
    phi_superbee = np.maximum(0, np.maximum(np.minimum(2*r, 1), np.minimum(r, 2)))
    phi_mc = np.maximum(0, np.minimum(np.minimum((1+r)/2, 2), 2*r))

    # TVD
    r_plot = np.linspace(0, 4, 100)
    tvd_lower = np.maximum(0, r_plot)
    tvd_upper = np.minimum(2, 2*r_plot)

    plt.figure(figsize=(10, 6))

    # TVD
    plt.fill_between(r_plot, tvd_lower, tvd_upper, alpha=0.2, color='gray', label='TVD')

    # 
    plt.plot(r, phi_minmod, 'b-', linewidth=2, label='Minmod')
    plt.plot(r, phi_vanleer, 'g-', linewidth=2, label='Van Leer')
    plt.plot(r, phi_superbee, 'r-', linewidth=2, label='Superbee')
    plt.plot(r, phi_mc, 'm-', linewidth=2, label='MC')

    plt.xlabel('r = (U_i - U_{i-1}) / (U_{i+1} - U_i)')
    plt.ylabel('φ(r)')
    plt.title('TVD Slope')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.xlim(-0.5, 4)
    plt.ylim(-0.5, 2.5)

    plt.savefig('slope_limiters_comparison.png', dpi=150, bbox_inches='tight')
    print("  [OK] : slope_limiters_comparison.png")

    print()

    # 3: 
    print("3: ")
    U = np.array([1.0, 1.5, 1.8, 1.7, 1.9, 2.0])
    dx = np.ones(len(U)) * 0.5

    print(f"   U: {U}")
    print(f"   dx: {dx}")
    print()

    # 
    for i in range(1, len(U) - 1):
        sigma_mm = compute_limited_slope(
            U[i-1], U[i], U[i+1],
            dx[i-1], dx[i], dx[i+1],
            limiter='minmod'
        )
        sigma_vl = compute_limited_slope(
            U[i-1], U[i], U[i+1],
            dx[i-1], dx[i], dx[i+1],
            limiter='vanleer'
        )

        print(f"  i={i}: minmod={sigma_mm:.4f}, vanleer={sigma_vl:.4f}")

    print()
    print("[OK] ")
