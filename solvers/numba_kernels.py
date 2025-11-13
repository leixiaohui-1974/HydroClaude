#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Numba JIT

Numba JIT

: HydroClaude Team
: 2025-10-31
Phase: 6.5 - Numba JIT
"""

import numpy as np
from numba import njit
from typing import Tuple


@njit(cache=True)
def hll_flux_kernel(
    h_L: float,
    Q_L: float,
    h_R: float,
    Q_R: float,
    B: float,
    g: float,
    eps_dry: float,
    use_entropy_fix: bool,
    use_critical_flow_treatment: bool
) -> Tuple[float, float]:
    """
    HLL RiemannJIT

    Args:
        h_L:  (m)
        Q_L:  (m³/s)
        h_R:  (m)
        Q_R:  (m³/s)
        B:  (m)
        g:  (m/s²)
        eps_dry:  (m)
        use_entropy_fix: 
        use_critical_flow_treatment: 

    Returns:
        (F_h, F_Q): 
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

    # Davis
    S_L = min(u_L - c_L, u_R - c_R)
    S_R = max(u_L + c_L, u_R + c_R)

    # Entropy
    if use_entropy_fix:
        # delta10%
        delta = 0.1 * max(abs(S_L), abs(S_R), 1e-10)

        # entropy
        S_L = entropy_fix_kernel(S_L, delta)
        S_R = entropy_fix_kernel(S_R, delta)

    # 
    F_h_L = Q_L
    F_Q_L = Q_L**2 / A_L + 0.5 * g * h_L**2 * B

    F_h_R = Q_R
    F_Q_R = Q_R**2 / A_R + 0.5 * g * h_R**2 * B

    # HLL
    if S_L >= 0:
        # 
        F_h = F_h_L
        F_Q = F_Q_L
    elif S_R <= 0:
        # 
        F_h = F_h_R
        F_Q = F_Q_R
    else:
        # HLL
        U_h_L = h_L
        U_h_R = h_R
        U_Q_L = Q_L
        U_Q_R = Q_R

        F_h = (S_R * F_h_L - S_L * F_h_R + S_L * S_R * (U_h_R - U_h_L)) / (S_R - S_L)
        F_Q = (S_R * F_Q_L - S_L * F_Q_R + S_L * S_R * (U_Q_R - U_Q_L)) / (S_R - S_L)

    # 
    if use_critical_flow_treatment:
        # Froude
        Fr_L = abs(u_L) / c_L if c_L > 1e-10 else 0.0
        Fr_R = abs(u_R) / c_R if c_R > 1e-10 else 0.0

        # Froude
        Fr_avg = 0.5 * (Fr_L + Fr_R)

        # 0.9 < Fr < 1.1
        if 0.9 < Fr_avg < 1.1:
            # Fr=1
            # alphaFr=10.5Fr=0.91.10
            alpha = 0.5 * (1.0 - abs(Fr_avg - 1.0) / 0.1)

            # Lax-Friedrichs
            max_speed = max(abs(u_L) + c_L, abs(u_R) + c_R, 1e-10)

            # 
            dissipation_h = alpha * max_speed * (h_R - h_L)
            dissipation_Q = alpha * max_speed * (Q_R - Q_L)

            F_h -= dissipation_h
            F_Q -= dissipation_Q

    return F_h, F_Q


@njit(cache=True)
def entropy_fix_kernel(lambda_val: float, delta: float) -> float:
    """
    Harten-Hyman EntropyJIT

    

    Args:
        lambda_val: 
        delta: 10%

    Returns:
        
    """
    if abs(lambda_val) >= delta:
        return lambda_val
    else:
        return (lambda_val**2 + delta**2) / (2.0 * delta)


@njit(cache=True)
def compute_source_term_kernel(
    h: float,
    Q: float,
    A: float,
    R: float,
    n: float,
    g: float,
    S0: float,
    well_balanced: bool
) -> float:
    """
    JIT

    Args:
        h:  (m)
        Q:  (m³/s)
        A:  (m²)
        R:  (m)
        n: Manning
        g:  (m/s²)
        S0: 
        well_balanced: Well-Balanced

    Returns:
        
    """
    # 
    if R > 1e-10 and abs(Q) > 1e-6:
        Sf = n**2 * Q**2 / (A**2 * R**(4.0/3.0))
        Sf = np.sign(Q) * Sf
    else:
        Sf = 0.0

    # Well-balancedhydrostatic reconstruction
    # 
    if well_balanced:
        return -g * A * Sf
    else:
        # 
        return g * A * (S0 - Sf)


@njit(cache=True)
def compute_friction_slope(
    Q: float,
    A: float,
    R: float,
    n: float
) -> float:
    """
    JIT

    Args:
        Q:  (m³/s)
        A:  (m²)
        R:  (m)
        n: Manning

    Returns:
         Sf
    """
    if R > 1e-10 and abs(Q) > 1e-6:
        Sf = n**2 * Q**2 / (A**2 * R**(4.0/3.0))
        return np.sign(Q) * Sf
    else:
        return 0.0


# HLL flux - 
@njit(cache=True, parallel=False)
def hll_flux_batch_kernel(
    h_L: np.ndarray,
    Q_L: np.ndarray,
    h_R: np.ndarray,
    Q_R: np.ndarray,
    B: float,
    g: float,
    eps_dry: float,
    use_entropy_fix: bool,
    use_critical_flow_treatment: bool
) -> Tuple[np.ndarray, np.ndarray]:
    """
    HLL Riemann - 

    Args:
        h_L:  (m)
        Q_L:  (m³/s)
        h_R:  (m)
        Q_R:  (m³/s)
        B:  (m)
        g:  (m/s²)
        eps_dry:  (m)
        use_entropy_fix: 
        use_critical_flow_treatment: 

    Returns:
        (F_h, F_Q): 
    """
    n = len(h_L)
    F_h = np.zeros(n)
    F_Q = np.zeros(n)

    for i in range(n):
        F_h[i], F_Q[i] = hll_flux_kernel(
            h_L[i], Q_L[i], h_R[i], Q_R[i],
            B, g, eps_dry,
            use_entropy_fix, use_critical_flow_treatment
        )

    return F_h, F_Q
