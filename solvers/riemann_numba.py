#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Numba JITRiemann

@njit10-50

: HydroClaude Team
: 2025-10-29
"""

import numpy as np
from numba import njit


@njit
def minmod_numba(a, b):
    """MinmodNumba"""
    if a * b <= 0.0:
        return 0.0
    elif abs(a) < abs(b):
        return a
    else:
        return b


@njit
def hll_flux_numba(h_L, Q_L, h_R, Q_R, B, g, eps_dry):
    """
    HLL RiemannNumba

    Args:
        h_L, Q_L: 
        h_R, Q_R: 
        B: 
        g: 
        eps_dry: 

    Returns:
        F_h, F_Q: 
    """
    # 
    if h_L < eps_dry and h_R < eps_dry:
        return 0.0, 0.0

    # 
    A_L = max(h_L * B, eps_dry * B)
    u_L = Q_L / A_L
    c_L = np.sqrt(g * max(h_L, 0.0))

    # 
    A_R = max(h_R * B, eps_dry * B)
    u_R = Q_R / A_R
    c_R = np.sqrt(g * max(h_R, 0.0))

    # 
    S_L = min(u_L - c_L, u_R - c_R)
    S_R = max(u_L + c_L, u_R + c_R)

    # 
    F_h_L = Q_L
    F_Q_L = Q_L * Q_L / A_L + 0.5 * g * h_L * h_L * B

    F_h_R = Q_R
    F_Q_R = Q_R * Q_R / A_R + 0.5 * g * h_R * h_R * B

    # HLL
    if S_L >= 0.0:
        return F_h_L, F_Q_L
    elif S_R <= 0.0:
        return F_h_R, F_Q_R
    else:
        # 
        U_h_L = h_L
        U_h_R = h_R
        U_Q_L = Q_L
        U_Q_R = Q_R

        F_h = (S_R * F_h_L - S_L * F_h_R + S_L * S_R * (U_h_R - U_h_L)) / (S_R - S_L)
        F_Q = (S_R * F_Q_L - S_L * F_Q_R + S_L * S_R * (U_Q_R - U_Q_L)) / (S_R - S_L)

        return F_h, F_Q


@njit
def compute_source_term_numba(h, Q, B, g, S0, n, eps_dry):
    """
    Numba

    Args:
        h: 
        Q: 
        B: 
        g: 
        S0: 
        n: Manning
        eps_dry: 

    Returns:
        
    """
    A = max(h * B, eps_dry * B)
    P = B + 2.0 * h
    R = A / P if P > 1e-10 else 0.0

    if R > 1e-10 and abs(Q) > 1e-6:
        Sf = n * n * Q * Q / (A * A * R ** (4.0 / 3.0))
        if Q < 0:
            Sf = -Sf
    else:
        Sf = 0.0

    return g * A * (S0 - Sf)


@njit
def muscl_reconstruction_numba(phi_ext):
    """
    MUSCLNumba

    Args:
        phi_ext:  [n+2]

    Returns:
        phi_L, phi_R:  [n+1]
    """
    n = len(phi_ext) - 2
    phi_L = np.zeros(n + 1)
    phi_R = np.zeros(n + 1)

    for i in range(n + 1):
        # 
        if i > 0:
            slope_L = minmod_numba(
                phi_ext[i+1] - phi_ext[i],
                phi_ext[i] - phi_ext[i-1]
            )
            phi_L[i] = phi_ext[i] + 0.5 * slope_L
        else:
            phi_L[i] = phi_ext[i]

        # 
        if i < n:
            slope_R = minmod_numba(
                phi_ext[i+2] - phi_ext[i+1],
                phi_ext[i+1] - phi_ext[i]
            )
            phi_R[i] = phi_ext[i+1] - 0.5 * slope_R
        else:
            phi_R[i] = phi_ext[i+1]

    return phi_L, phi_R


@njit
def compute_all_fluxes_numba(h_L, h_R, Q_L, Q_R, B, g, eps_dry):
    """
    Numba

    Args:
        h_L, h_R:  [n+1]
        Q_L, Q_R:  [n+1]
        B: 
        g: 
        eps_dry: 

    Returns:
        F_h, F_Q:  [n+1]
    """
    n_interfaces = len(h_L)
    F_h = np.zeros(n_interfaces)
    F_Q = np.zeros(n_interfaces)

    for i in range(n_interfaces):
        F_h[i], F_Q[i] = hll_flux_numba(
            h_L[i], Q_L[i], h_R[i], Q_R[i], B, g, eps_dry
        )

    return F_h, F_Q


@njit
def compute_spatial_derivatives_numba(F_h, F_Q, S0_array, h_array, Q_array, B, g, n, eps_dry, dx):
    """
    Numba

    Args:
        F_h, F_Q:  [n+1]
        S0_array:  [n]
        h_array, Q_array:  [n]
        B, g, n: 
        eps_dry: 
        dx: 

    Returns:
        dh_dt, dQ_dt:  [n]
    """
    n_cells = len(h_array)
    dh_dt = np.zeros(n_cells)
    dQ_dt = np.zeros(n_cells)

    for i in range(n_cells):
        # 
        dh_dt[i] = -(F_h[i+1] - F_h[i]) / dx
        dQ_dt[i] = -(F_Q[i+1] - F_Q[i]) / dx

        # 
        S = compute_source_term_numba(h_array[i], Q_array[i], B, g, S0_array[i], n, eps_dry)
        dQ_dt[i] += S

    return dh_dt, dQ_dt


if __name__ == '__main__':
    print("=" * 80)
    print("Numba JIT")
    print("=" * 80)

    # HLL
    h_L, Q_L = 2.0, 10.0
    h_R, Q_R = 1.5, 8.0
    B, g, eps_dry = 10.0, 9.81, 1e-6

    F_h, F_Q = hll_flux_numba(h_L, Q_L, h_R, Q_R, B, g, eps_dry)
    print(f"\nHLL:")
    print(f"  : h_L={h_L}, Q_L={Q_L}, h_R={h_R}, Q_R={Q_R}")
    print(f"  : F_h={F_h:.3f}, F_Q={F_Q:.3f}")

    # MUSCL
    phi_ext = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    phi_L, phi_R = muscl_reconstruction_numba(phi_ext)
    print(f"\nMUSCL:")
    print(f"  : {phi_ext}")
    print(f"  phi_L: {phi_L}")
    print(f"  phi_R: {phi_R}")

    print("\n Numba")
    print("=" * 80)
