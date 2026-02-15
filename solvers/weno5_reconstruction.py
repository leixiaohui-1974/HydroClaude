#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
WENO5 (5th-order Weighted Essentially Non-Oscillatory) Reconstruction

WENO5Jiang & Shu, 1996

:
    Jiang, G. S., & Shu, C. W. (1996). Efficient implementation of weighted ENO schemes.
    Journal of Computational Physics, 126(1), 202-228.

: HydroClaude Team
: 2025-10-31
"""

import numpy as np
from numba import njit


@njit
def weno5_reconstruct(q: np.ndarray, epsilon: float = 1e-6) -> tuple:
    """
    WENO5

    5i-2, i-1, i, i+1, i+2i

    :
        q:  ( n)
        epsilon: 

    :
        q_L:  q_{i-1/2}^+ ( n-1)
        q_R:  q_{i+1/2}^- ( n-1)

    :
        - 2ghost2
        - i=2..n-3
    """
    n = len(q)
    q_L = np.zeros(n - 1)  # q_{i+1/2}^-
    q_R = np.zeros(n - 1)  # q_{i+1/2}^+

    # WENO5
    gamma0 = 0.1
    gamma1 = 0.6
    gamma2 = 0.3

    # 
    # nghostWENO5
    # - i-2, i-1, i, i+1, i+2
    # - i-1, i, i+1, i+2, i+3
    # i2n-3
    #             i2n-4i+3<n
    # i=2..n-2
    for i in range(2, n - 1):  # 
        # ================================================
        # q_{i+1/2}^- i-2, i-1, i, i+1, i+2
        # ================================================

        # stencil
        # S0: {i-2, i-1, i}   ()
        # S1: {i-1, i, i+1}   ()
        # S2: {i, i+1, i+2}   ()

        # S0: 3
        q0_L = (2.0 * q[i-2] - 7.0 * q[i-1] + 11.0 * q[i]) / 6.0

        # S1: 3
        q1_L = (-q[i-1] + 5.0 * q[i] + 2.0 * q[i+1]) / 6.0

        # S2: 3
        q2_L = (2.0 * q[i] + 5.0 * q[i+1] - q[i+2]) / 6.0

        # smoothness indicators
        beta0 = (13.0 / 12.0) * (q[i-2] - 2.0 * q[i-1] + q[i])**2 + \
                (1.0 / 4.0) * (q[i-2] - 4.0 * q[i-1] + 3.0 * q[i])**2

        beta1 = (13.0 / 12.0) * (q[i-1] - 2.0 * q[i] + q[i+1])**2 + \
                (1.0 / 4.0) * (q[i-1] - q[i+1])**2

        beta2 = (13.0 / 12.0) * (q[i] - 2.0 * q[i+1] + q[i+2])**2 + \
                (1.0 / 4.0) * (3.0 * q[i] - 4.0 * q[i+1] + q[i+2])**2

        # 
        alpha0_L = gamma0 / (epsilon + beta0)**2
        alpha1_L = gamma1 / (epsilon + beta1)**2
        alpha2_L = gamma2 / (epsilon + beta2)**2

        alpha_sum_L = alpha0_L + alpha1_L + alpha2_L

        # 
        if alpha_sum_L < 1e-40:
            w0_L = gamma0
            w1_L = gamma1
            w2_L = gamma2
        else:
            w0_L = alpha0_L / alpha_sum_L
            w1_L = alpha1_L / alpha_sum_L
            w2_L = alpha2_L / alpha_sum_L

        # 
        q_L[i] = w0_L * q0_L + w1_L * q1_L + w2_L * q2_L

        # ================================================
        # q_{i+1/2}^+ i-1, i, i+1, i+2, i+3
        # ================================================
        # i+1/2i+1

        #  = 
        # S0: {i+3, i+2, i+1} → i+1
        # S1: {i+2, i+1, i}
        # S2: {i+1, i, i-1}

        # S0: i+1
        q0_R = (2.0 * q[i+3] - 7.0 * q[i+2] + 11.0 * q[i+1]) / 6.0 if i+3 < n else 0.0

        # S1: 
        q1_R = (-q[i+2] + 5.0 * q[i+1] + 2.0 * q[i]) / 6.0 if i+2 < n else 0.0

        # S2: 
        q2_R = (2.0 * q[i+1] + 5.0 * q[i] - q[i-1]) / 6.0

        # 
        if i + 3 < n:
            beta0_R = (13.0 / 12.0) * (q[i+3] - 2.0 * q[i+2] + q[i+1])**2 + \
                      (1.0 / 4.0) * (q[i+3] - 4.0 * q[i+2] + 3.0 * q[i+1])**2
        else:
            beta0_R = 1e10  # 

        if i + 2 < n:
            beta1_R = (13.0 / 12.0) * (q[i+2] - 2.0 * q[i+1] + q[i])**2 + \
                      (1.0 / 4.0) * (q[i+2] - q[i])**2
        else:
            beta1_R = 1e10

        beta2_R = (13.0 / 12.0) * (q[i+1] - 2.0 * q[i] + q[i-1])**2 + \
                  (1.0 / 4.0) * (3.0 * q[i+1] - 4.0 * q[i] + q[i-1])**2

        # 
        alpha0_R = gamma0 / (epsilon + beta0_R)**2
        alpha1_R = gamma1 / (epsilon + beta1_R)**2
        alpha2_R = gamma2 / (epsilon + beta2_R)**2

        alpha_sum_R = alpha0_R + alpha1_R + alpha2_R

        # 
        if alpha_sum_R < 1e-40:
            w0_R = gamma0
            w1_R = gamma1
            w2_R = gamma2
        else:
            w0_R = alpha0_R / alpha_sum_R
            w1_R = alpha1_R / alpha_sum_R
            w2_R = alpha2_R / alpha_sum_R

        # 
        q_R[i] = w0_R * q0_R + w1_R * q1_R + w2_R * q2_R

    return q_L, q_R


def weno5_flux_splitting(q: np.ndarray, f: np.ndarray, alpha: float, epsilon: float = 1e-6):
    """
    WENO5 with Lax-Friedrichs flux splitting

    Args:
        q: conserved variables (array of size n)
        f: flux values f(q) (array of size n)
        alpha: max wave speed for Lax-Friedrichs splitting
        epsilon: WENO epsilon parameter

    Returns:
        f_interface: numerical flux at interfaces (array of size n-1)
    """
    n = len(q)

    # Lax-Friedrichs flux splitting
    # f^+ = 0.5 * (f + alpha * q)
    # f^- = 0.5 * (f - alpha * q)
    f_plus = 0.5 * (f + alpha * q)
    f_minus = 0.5 * (f - alpha * q)

    # WENO5 reconstruct f^+ from left and f^- from right
    fp_L, _ = weno5_reconstruct(f_plus, epsilon)
    _, fm_R = weno5_reconstruct(f_minus, epsilon)

    # Numerical flux at interfaces
    n_interfaces = min(len(fp_L), len(fm_R))
    f_interface = np.zeros(n_interfaces)
    for i in range(n_interfaces):
        f_interface[i] = fp_L[i] + fm_R[i]

    return f_interface


def test_weno5():
    """WENO5"""
    print("="*80)
    print("WENO5")
    print("="*80)

    # 15
    print("\n1: ")
    n = 100
    x = np.linspace(0, 2*np.pi, n)
    q = np.sin(x)

    # ghost cells
    q_ext = np.zeros(n + 4)
    q_ext[2:-2] = q
    q_ext[0:2] = q[-2:]  # ghost
    q_ext[-2:] = q[0:2]  # ghost

    q_L, q_R = weno5_reconstruct(q_ext)

    # 
    interior = slice(2, -2)
    print(f"  : [{q.min():.6f}, {q.max():.6f}]")
    print(f"  : [{q_L[interior].min():.6f}, {q_L[interior].max():.6f}]")
    print(f"  : [{q_R[interior].min():.6f}, {q_R[interior].max():.6f}]")

    # 2
    print("\n2: ")
    q_jump = np.ones(n)
    q_jump[n//2:] = 2.0

    q_ext = np.zeros(n + 4)
    q_ext[2:-2] = q_jump
    q_ext[0:2] = q_jump[:2]
    q_ext[-2:] = q_jump[-2:]

    q_L, q_R = weno5_reconstruct(q_ext)

    # 
    jump_idx = n // 2
    local_start = jump_idx - 3
    local_end = jump_idx + 3
    print(f"  : {q_jump[local_start:local_end]}")
    print(f"  : {q_L[local_start+2:local_end+2]}")  # +2 offset for ghost cells

    # /
    overshoot_L = np.max(q_L[interior]) - 2.0
    undershoot_L = 1.0 - np.min(q_L[interior])

    print(f"\n  :")
    print(f"    : {np.max(q_L[interior]):.6f} (: {overshoot_L:.6f})")
    print(f"    : {np.min(q_L[interior]):.6f} (: {undershoot_L:.6f})")

    if abs(overshoot_L) < 0.1 and abs(undershoot_L) < 0.1:
        print("   ")
    else:
        print("  [WARN]  ")

    print("\n" + "="*80)
    print("WENO5")
    print("="*80)


if __name__ == '__main__':
    test_weno5()
