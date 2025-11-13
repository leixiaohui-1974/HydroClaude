#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Riemann

Riemann
- HLL (Harten-Lax-van Leer)
- HLLC (HLL with Contact)

: Claude
: 2025-10-23
"""

import numpy as np


def hll_flux_shallow_water(U_L, U_R, B, g=9.81):
    """
    HLL Riemann

    Args:
        U_L:  [A, Q]
        U_R:  [A, Q]
        B:  (m)
        g:  (m/s²)

    Returns:
        F_hll: HLL [F_A, F_Q]
    """
    # 
    A_L, Q_L = U_L
    A_R, Q_R = U_R

    # 
    h_L = A_L / B if A_L > 1e-10 else 1e-10
    h_R = A_R / B if A_R > 1e-10 else 1e-10

    # 
    u_L = Q_L / A_L if A_L > 1e-10 else 0.0
    u_R = Q_R / A_R if A_R > 1e-10 else 0.0

    # 
    c_L = np.sqrt(g * h_L)
    c_R = np.sqrt(g * h_R)

    # Roe
    sqrt_h_L = np.sqrt(h_L)
    sqrt_h_R = np.sqrt(h_R)
    h_roe = (sqrt_h_L * h_L + sqrt_h_R * h_R) / (sqrt_h_L + sqrt_h_R)
    u_roe = (sqrt_h_L * u_L + sqrt_h_R * u_R) / (sqrt_h_L + sqrt_h_R)
    c_roe = np.sqrt(g * h_roe)

    # 
    s_L = min(u_L - c_L, u_roe - c_roe)
    s_R = max(u_R + c_R, u_roe + c_roe)

    # 
    # F = [Q, Q²/A + gI₁]
    # I₁ = A*h/2 = A²/(2B)
    F_L = np.array([
        Q_L,
        Q_L**2 / A_L + 0.5 * g * A_L * h_L if A_L > 1e-10 else 0.0
    ])

    F_R = np.array([
        Q_R,
        Q_R**2 / A_R + 0.5 * g * A_R * h_R if A_R > 1e-10 else 0.0
    ])

    # HLL
    if s_L >= 0:
        # 
        return F_L
    elif s_R <= 0:
        # 
        return F_R
    else:
        # HLL
        F_hll = (s_R * F_L - s_L * F_R + s_L * s_R * (U_R - U_L)) / (s_R - s_L)
        return F_hll


def hllc_flux_shallow_water(U_L, U_R, B, g=9.81):
    """
    HLLC Riemann

    

    Args:
        U_L, U_R: 
        B: 
        g: 

    Returns:
        F_hllc: HLLC
    """
    # 
    A_L, Q_L = U_L
    A_R, Q_R = U_R

    h_L = A_L / B if A_L > 1e-10 else 1e-10
    h_R = A_R / B if A_R > 1e-10 else 1e-10

    u_L = Q_L / A_L if A_L > 1e-10 else 0.0
    u_R = Q_R / A_R if A_R > 1e-10 else 0.0

    c_L = np.sqrt(g * h_L)
    c_R = np.sqrt(g * h_R)

    # Roe
    sqrt_h_L = np.sqrt(h_L)
    sqrt_h_R = np.sqrt(h_R)
    h_roe = (sqrt_h_L * h_L + sqrt_h_R * h_R) / (sqrt_h_L + sqrt_h_R)
    u_roe = (sqrt_h_L * u_L + sqrt_h_R * u_R) / (sqrt_h_L + sqrt_h_R)
    c_roe = np.sqrt(g * h_roe)

    # 
    s_L = min(u_L - c_L, u_roe - c_roe)
    s_R = max(u_R + c_R, u_roe + c_roe)

    # 
    s_star = (s_L * h_R * (u_R - s_R) - s_R * h_L * (u_L - s_L)) / \
             (h_R * (u_R - s_R) - h_L * (u_L - s_L))

    # 
    F_L = np.array([Q_L, Q_L**2 / A_L + 0.5 * g * A_L * h_L if A_L > 1e-10 else 0.0])
    F_R = np.array([Q_R, Q_R**2 / A_R + 0.5 * g * A_R * h_R if A_R > 1e-10 else 0.0])

    if s_L >= 0:
        return F_L
    elif s_R <= 0:
        return F_R
    elif s_L < 0 < s_star:
        # 
        U_star_L = np.array([
            h_L * (s_L - u_L) / (s_L - s_star),
            h_L * (s_L - u_L) / (s_L - s_star) * s_star * B
        ])
        return F_L + s_L * (U_star_L - U_L)
    else:  # s_star < 0 < s_R
        # 
        U_star_R = np.array([
            h_R * (s_R - u_R) / (s_R - s_star),
            h_R * (s_R - u_R) / (s_R - s_star) * s_star * B
        ])
        return F_R + s_R * (U_star_R - U_R)


def rusanov_flux(U_L, U_R, B, g=9.81):
    """
    Rusanov (Local Lax-Friedrichs) 

    

    Args:
        U_L, U_R: 
        B: 
        g: 

    Returns:
        F_rusanov: Rusanov
    """
    A_L, Q_L = U_L
    A_R, Q_R = U_R

    h_L = A_L / B if A_L > 1e-10 else 1e-10
    h_R = A_R / B if A_R > 1e-10 else 1e-10

    u_L = Q_L / A_L if A_L > 1e-10 else 0.0
    u_R = Q_R / A_R if A_R > 1e-10 else 0.0

    c_L = np.sqrt(g * h_L)
    c_R = np.sqrt(g * h_R)

    # 
    s_max = max(abs(u_L) + c_L, abs(u_R) + c_R)

    # 
    F_L = np.array([Q_L, Q_L**2 / A_L + 0.5 * g * A_L * h_L if A_L > 1e-10 else 0.0])
    F_R = np.array([Q_R, Q_R**2 / A_R + 0.5 * g * A_R * h_R if A_R > 1e-10 else 0.0])

    return 0.5 * (F_L + F_R) - 0.5 * s_max * (U_R - U_L)


# 
if __name__ == "__main__":
    print("=" * 60)
    print("Riemann")
    print("=" * 60)
    print()

    # 1: Dam break
    print("1: Dam break ()")
    B = 10.0
    g = 9.81

    # 
    h_L = 2.0
    u_L = 0.0
    A_L = B * h_L
    Q_L = A_L * u_L

    # 
    h_R = 1.0
    u_R = 0.0
    A_R = B * h_R
    Q_R = A_R * u_R

    U_L = np.array([A_L, Q_L])
    U_R = np.array([A_R, Q_R])

    F_hll = hll_flux_shallow_water(U_L, U_R, B, g)
    F_hllc = hllc_flux_shallow_water(U_L, U_R, B, g)
    F_rusanov = rusanov_flux(U_L, U_R, B, g)

    print(f"  : h={h_L}m, u={u_L}m/s")
    print(f"  : h={h_R}m, u={u_R}m/s")
    print(f"  HLL:     {F_hll}")
    print(f"  HLLC:    {F_hllc}")
    print(f"  Rusanov: {F_rusanov}")
    print()

    # 2: 
    print("2: ")
    h_L = 1.5
    u_L = 5.0  # Fr > 1
    A_L = B * h_L
    Q_L = A_L * u_L

    h_R = 1.0
    u_R = 1.0
    A_R = B * h_R
    Q_R = A_R * u_R

    U_L = np.array([A_L, Q_L])
    U_R = np.array([A_R, Q_R])

    F_hll = hll_flux_shallow_water(U_L, U_R, B, g)

    Fr_L = u_L / np.sqrt(g * h_L)
    print(f"  Froude: {Fr_L:.2f}")
    print(f"  HLL: {F_hll}")
    print()

    print("[OK] ")
