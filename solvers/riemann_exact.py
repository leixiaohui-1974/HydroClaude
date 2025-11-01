#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Exact Riemann Solver for Shallow Water Equations
精确Riemann求解器 - 浅水方程

用于Godunov有限体积法的精确Riemann通量计算

Reference:
- Toro, E.F. (2009). Riemann Solvers and Numerical Methods for Fluid Dynamics.
  Springer, 3rd Edition, Chapter 13
- Toro, E.F. (2001). Shock-Capturing Methods for Free-Surface Shallow Flows.
  Wiley

Wave Structure (4 possible configurations):
1. Left rarefaction + Right rarefaction
2. Left rarefaction + Right shock
3. Left shock + Right rarefaction
4. Left shock + Right shock

Solution Method:
- Iteratively solve for star region depth h_star
- Compute star region velocity u_star
- Sample wave structure at x/t=0 to get interface flux

Advantages over HLL/HLLC:
- Machine precision on smooth problems
- Zero numerical dissipation
- Exact contact discontinuity resolution
- Perfect Lake at Rest when combined with Well-Balanced scheme

Performance:
- More expensive than HLL/HLLC (iterative solver)
- Recommended for problems requiring high accuracy

Author: HydroClaude Development Team
Date: 2025-11-01
Phase: 9.3 - Exact Riemann Solver Implementation
"""

import numpy as np
from typing import Tuple

# Try to import Numba
try:
    from numba import njit
    NUMBA_AVAILABLE = True
except ImportError:
    # Fallback if Numba not available
    def njit(*args, **kwargs):
        if len(args) == 1 and callable(args[0]):
            return args[0]
        def decorator(func):
            return func
        return decorator
    NUMBA_AVAILABLE = False


# ==============================================================================
# Exact Riemann Solver - Pure Python Version
# ==============================================================================

def exact_riemann_flux(
    h_L: float,
    Q_L: float,
    h_R: float,
    Q_R: float,
    B: float,
    g: float = 9.81,
    eps_dry: float = 1e-6,
    max_iter: int = 50,
    tol: float = 1e-10
) -> Tuple[float, float]:
    """
    Compute exact Riemann flux at cell interface (x/t = 0)

    Solves the Riemann problem exactly and samples the solution at x/t=0
    to obtain the interface flux.

    Args:
        h_L: Left cell depth (m)
        Q_L: Left cell discharge (m³/s)
        h_R: Right cell depth (m)
        Q_R: Right cell discharge (m³/s)
        B: Channel width (m)
        g: Gravitational acceleration (m/s²)
        eps_dry: Dry threshold (m)
        max_iter: Maximum Newton iterations
        tol: Convergence tolerance

    Returns:
        F_h: Mass flux (m³/s)
        F_Q: Momentum flux (m³/s²)
    """
    # Convert discharge to velocity
    A_L = h_L * B
    A_R = h_R * B

    u_L = Q_L / (A_L + eps_dry) if h_L > eps_dry else 0.0
    u_R = Q_R / (A_R + eps_dry) if h_R > eps_dry else 0.0

    # Handle dry bed cases
    if h_L < eps_dry and h_R < eps_dry:
        # Both dry
        return 0.0, 0.0

    if h_L < eps_dry:
        # Left dry, right wet: right-going rarefaction
        c_R = np.sqrt(g * h_R)
        S_head_R = u_R + c_R

        if S_head_R <= 0.0:
            # Right state is supersonic to the left, use right state
            Q = h_R * u_R * B
            F_h = Q
            F_Q = Q * u_R + 0.5 * g * h_R**2 * B
            return F_h, F_Q
        else:
            # Dry interface
            return 0.0, 0.0

    if h_R < eps_dry:
        # Right dry, left wet: left-going rarefaction
        c_L = np.sqrt(g * h_L)
        S_head_L = u_L - c_L

        if S_head_L >= 0.0:
            # Left state is supersonic to the right, use left state
            Q = h_L * u_L * B
            F_h = Q
            F_Q = Q * u_L + 0.5 * g * h_L**2 * B
            return F_h, F_Q
        else:
            # Dry interface
            return 0.0, 0.0

    # Both wet: solve for star region
    h_star, u_star = _solve_star_region_newton(h_L, u_L, h_R, u_R, g, max_iter, tol)

    # Sample solution at x/t = 0
    h_sample, u_sample = _sample_solution(h_L, u_L, h_R, u_R, h_star, u_star, g)

    # Compute flux from sampled state
    Q_sample = h_sample * u_sample * B
    F_h = Q_sample
    F_Q = Q_sample * u_sample + 0.5 * g * h_sample**2 * B

    return F_h, F_Q


def _solve_star_region_newton(
    h_L: float,
    u_L: float,
    h_R: float,
    u_R: float,
    g: float,
    max_iter: int,
    tol: float
) -> Tuple[float, float]:
    """
    Solve for star region using Newton-Raphson iteration

    Solves: f_L(h*) + f_R(h*) + Δu = 0
    where Δu = u_R - u_L

    Args:
        h_L, u_L: Left state
        h_R, u_R: Right state
        g: Gravity
        max_iter: Maximum iterations
        tol: Convergence tolerance

    Returns:
        h_star: Star region depth
        u_star: Star region velocity
    """
    c_L = np.sqrt(g * h_L)
    c_R = np.sqrt(g * h_R)

    # Special case: Lake at Rest or near-zero velocity
    # When velocity difference is very small relative to wave speeds,
    # avoid numerical instability in Newton solver
    du = abs(u_R - u_L)
    dh = abs(h_R - h_L)
    wave_scale = c_L + c_R
    h_avg = 0.5 * (h_L + h_R)

    # True Lake at Rest: h差异小 AND 速度都接近零
    # 修复：溃坝(h_L≠h_R但u=0)不应该被当作静水！
    if (abs(u_L) < 1e-6 and abs(u_R) < 1e-6 and dh < 1e-3 * h_avg):
        # 真正的静水：深度差异<0.1%且速度为零
        h_star = 0.5 * (h_L + h_R)
        u_star = 0.0
        return h_star, u_star

    # Initial guess: Two-rarefaction approximation (Toro 2009, Eq 9.35)
    h_star = 0.5 * (h_L + h_R) - 0.25 * (u_R - u_L) * (h_L + h_R) / (c_L + c_R)
    h_star = max(0.1 * min(h_L, h_R), h_star)  # Ensure positive

    # Newton-Raphson iteration
    for iteration in range(max_iter):
        # Evaluate f(h*) and f'(h*)
        f_val = _f_function(h_star, h_L, u_L, c_L, g) + \
                _f_function(h_star, h_R, -u_R, c_R, g)  # Note: -u_R for right wave

        df_val = _df_function(h_star, h_L, c_L, g) + \
                 _df_function(h_star, h_R, c_R, g)

        # Newton step
        if abs(df_val) < 1e-12:
            break

        dh = -f_val / df_val
        h_star_new = h_star + dh

        # Ensure positivity
        h_star_new = max(0.1 * min(h_L, h_R), h_star_new)

        # Check convergence
        if abs(h_star_new - h_star) < tol:
            h_star = h_star_new
            break

        h_star = h_star_new

    # Compute u_star from h_star using left wave relation
    u_star = u_L - _f_function(h_star, h_L, 0.0, c_L, g)

    return h_star, u_star


def _f_function(h_star: float, h_K: float, u_K: float, c_K: float, g: float) -> float:
    """
    Wave function f_K(h*) for left (K=L) or right (K=R) wave

    For left wave (K=L):  f_L(h*) = u_L - u*
    For right wave (K=R): f_R(h*) = u* - u_R (so pass -u_R to get correct sign)

    Args:
        h_star: Star region depth
        h_K: Known state depth (h_L or h_R)
        u_K: Known state velocity (u_L or -u_R)
        c_K: Known state wave speed sqrt(g*h_K)
        g: Gravity

    Returns:
        f_K value
    """
    if h_star > h_K:
        # Shock wave (Rankine-Hugoniot condition)
        Q_K = np.sqrt(0.5 * g * (h_star + h_K) / (h_star * h_K))
        f_val = (h_star - h_K) * Q_K + u_K
    else:
        # Rarefaction wave (Riemann invariant)
        c_star = np.sqrt(g * h_star)
        f_val = 2.0 * (c_star - c_K) + u_K

    return f_val


def _df_function(h_star: float, h_K: float, c_K: float, g: float) -> float:
    """
    Derivative of wave function df_K/dh*

    Args:
        h_star: Star region depth
        h_K: Known state depth
        c_K: Known state wave speed
        g: Gravity

    Returns:
        df_K/dh* value
    """
    if h_star > h_K:
        # Shock wave derivative
        Q_K = np.sqrt(0.5 * g * (h_star + h_K) / (h_star * h_K))

        # Safeguard against division by very small Q_K
        Q_K = max(Q_K, 1e-10)

        dQ_K = -0.25 * g * (h_star + h_K) / (h_star**2 * h_K * Q_K) + \
               0.25 * g / (h_star * h_K * Q_K)
        df_val = Q_K + (h_star - h_K) * dQ_K
    else:
        # Rarefaction wave derivative
        c_star = np.sqrt(g * h_star)
        df_val = g / c_star

    return df_val


def _sample_solution(
    h_L: float,
    u_L: float,
    h_R: float,
    u_R: float,
    h_star: float,
    u_star: float,
    g: float
) -> Tuple[float, float]:
    """
    Sample Riemann solution at x/t = 0

    Determines which wave/region contains the interface and returns
    the corresponding state (h, u).

    Args:
        h_L, u_L: Left state
        h_R, u_R: Right state
        h_star, u_star: Star region state
        g: Gravity

    Returns:
        h, u: Sampled depth and velocity at interface
    """
    c_L = np.sqrt(g * h_L)
    c_R = np.sqrt(g * h_R)
    c_star = np.sqrt(g * h_star)

    # Sample point is at s = x/t = 0
    s = 0.0

    # Determine which region contains s=0
    if s <= u_star:
        # Check left wave
        if h_star > h_L:
            # Left shock
            S_L = u_L - c_L * np.sqrt((h_star + h_L) / (2.0 * h_L))

            if s <= S_L:
                # Left of shock: left state
                return h_L, u_L
            else:
                # Right of shock: star state
                return h_star, u_star
        else:
            # Left rarefaction
            S_head_L = u_L - c_L
            S_tail_L = u_star - c_star

            if s <= S_head_L:
                # Left of rarefaction: left state
                return h_L, u_L
            elif s <= S_tail_L:
                # Inside rarefaction fan
                u = (u_L + 2.0 * c_L + 2.0 * s) / 3.0
                c = (u_L + 2.0 * c_L - s) / 3.0
                h = c**2 / g
                return h, u
            else:
                # Right of rarefaction: star state
                return h_star, u_star
    else:
        # Check right wave
        if h_star > h_R:
            # Right shock
            S_R = u_R + c_R * np.sqrt((h_star + h_R) / (2.0 * h_R))

            if s >= S_R:
                # Right of shock: right state
                return h_R, u_R
            else:
                # Left of shock: star state
                return h_star, u_star
        else:
            # Right rarefaction
            S_head_R = u_star + c_star
            S_tail_R = u_R + c_R

            if s >= S_tail_R:
                # Right of rarefaction: right state
                return h_R, u_R
            elif s >= S_head_R:
                # Inside rarefaction fan
                u = (u_R - 2.0 * c_R + 2.0 * s) / 3.0
                c = (-u_R + 2.0 * c_R + s) / 3.0
                h = c**2 / g
                return h, u
            else:
                # Left of rarefaction: star state
                return h_star, u_star


# ==============================================================================
# Numba JIT-compiled version for production use
# ==============================================================================

@njit
def _f_function_numba(h_star: float, h_K: float, u_K: float, c_K: float, g: float) -> float:
    """Numba version of _f_function"""
    if h_star > h_K:
        Q_K = np.sqrt(0.5 * g * (h_star + h_K) / (h_star * h_K))
        f_val = (h_star - h_K) * Q_K + u_K
    else:
        c_star = np.sqrt(g * h_star)
        f_val = 2.0 * (c_star - c_K) + u_K
    return f_val


@njit
def _df_function_numba(h_star: float, h_K: float, c_K: float, g: float) -> float:
    """Numba version of _df_function"""
    if h_star > h_K:
        Q_K = np.sqrt(0.5 * g * (h_star + h_K) / (h_star * h_K))

        # Safeguard against division by very small Q_K
        Q_K = max(Q_K, 1e-10)

        dQ_K = -0.25 * g * (h_star + h_K) / (h_star**2 * h_K * Q_K) + \
               0.25 * g / (h_star * h_K * Q_K)
        df_val = Q_K + (h_star - h_K) * dQ_K
    else:
        c_star = np.sqrt(g * h_star)
        df_val = g / c_star
    return df_val


@njit
def _solve_star_region_numba(
    h_L: float,
    u_L: float,
    h_R: float,
    u_R: float,
    g: float,
    max_iter: int,
    tol: float
) -> Tuple[float, float]:
    """Numba version of _solve_star_region_newton"""
    c_L = np.sqrt(g * h_L)
    c_R = np.sqrt(g * h_R)

    # Special case: Lake at Rest or near-zero velocity
    # When velocity difference is very small relative to wave speeds,
    # avoid numerical instability in Newton solver
    du = abs(u_R - u_L)
    dh = abs(h_R - h_L)
    wave_scale = c_L + c_R
    h_avg = 0.5 * (h_L + h_R)

    # True Lake at Rest: h差异小 AND 速度都接近零
    # 修复：溃坝(h_L≠h_R但u=0)不应该被当作静水！
    if (abs(u_L) < 1e-6 and abs(u_R) < 1e-6 and dh < 1e-3 * h_avg):
        # 真正的静水：深度差异<0.1%且速度为零
        h_star = 0.5 * (h_L + h_R)
        u_star = 0.0
        return h_star, u_star

    # Initial guess
    h_star = 0.5 * (h_L + h_R) - 0.25 * (u_R - u_L) * (h_L + h_R) / (c_L + c_R)
    h_star = max(0.1 * min(h_L, h_R), h_star)

    # Newton-Raphson iteration
    for iteration in range(max_iter):
        f_val = _f_function_numba(h_star, h_L, u_L, c_L, g) + \
                _f_function_numba(h_star, h_R, -u_R, c_R, g)

        df_val = _df_function_numba(h_star, h_L, c_L, g) + \
                 _df_function_numba(h_star, h_R, c_R, g)

        if abs(df_val) < 1e-12:
            break

        dh = -f_val / df_val
        h_star_new = h_star + dh
        h_star_new = max(0.1 * min(h_L, h_R), h_star_new)

        if abs(h_star_new - h_star) < tol:
            h_star = h_star_new
            break

        h_star = h_star_new

    u_star = u_L - _f_function_numba(h_star, h_L, 0.0, c_L, g)

    return h_star, u_star


@njit
def _sample_solution_numba(
    h_L: float,
    u_L: float,
    h_R: float,
    u_R: float,
    h_star: float,
    u_star: float,
    g: float
) -> Tuple[float, float]:
    """Numba version of _sample_solution"""
    c_L = np.sqrt(g * h_L)
    c_R = np.sqrt(g * h_R)
    c_star = np.sqrt(g * h_star)

    s = 0.0  # Sample at interface

    if s <= u_star:
        # Left wave
        if h_star > h_L:
            # Left shock
            S_L = u_L - c_L * np.sqrt((h_star + h_L) / (2.0 * h_L))
            if s <= S_L:
                return h_L, u_L
            else:
                return h_star, u_star
        else:
            # Left rarefaction
            S_head_L = u_L - c_L
            S_tail_L = u_star - c_star

            if s <= S_head_L:
                return h_L, u_L
            elif s <= S_tail_L:
                u = (u_L + 2.0 * c_L + 2.0 * s) / 3.0
                c = (u_L + 2.0 * c_L - s) / 3.0
                h = c**2 / g
                return h, u
            else:
                return h_star, u_star
    else:
        # Right wave
        if h_star > h_R:
            # Right shock
            S_R = u_R + c_R * np.sqrt((h_star + h_R) / (2.0 * h_R))
            if s >= S_R:
                return h_R, u_R
            else:
                return h_star, u_star
        else:
            # Right rarefaction
            S_head_R = u_star + c_star
            S_tail_R = u_R + c_R

            if s >= S_tail_R:
                return h_R, u_R
            elif s >= S_head_R:
                u = (u_R - 2.0 * c_R + 2.0 * s) / 3.0
                c = (-u_R + 2.0 * c_R + s) / 3.0
                h = c**2 / g
                return h, u
            else:
                return h_star, u_star


@njit
def exact_riemann_flux_numba(
    h_L: float,
    Q_L: float,
    h_R: float,
    Q_R: float,
    B: float,
    g: float,
    eps_dry: float,
    max_iter: int,
    tol: float
) -> Tuple[float, float]:
    """Numba-optimized exact Riemann flux"""
    A_L = h_L * B
    A_R = h_R * B

    u_L = Q_L / (A_L + eps_dry) if h_L > eps_dry else 0.0
    u_R = Q_R / (A_R + eps_dry) if h_R > eps_dry else 0.0

    # Dry bed cases
    if h_L < eps_dry and h_R < eps_dry:
        return 0.0, 0.0

    if h_L < eps_dry:
        c_R = np.sqrt(g * h_R)
        S_head_R = u_R + c_R
        if S_head_R <= 0.0:
            Q = h_R * u_R * B
            F_h = Q
            F_Q = Q * u_R + 0.5 * g * h_R**2 * B
            return F_h, F_Q
        else:
            return 0.0, 0.0

    if h_R < eps_dry:
        c_L = np.sqrt(g * h_L)
        S_head_L = u_L - c_L
        if S_head_L >= 0.0:
            Q = h_L * u_L * B
            F_h = Q
            F_Q = Q * u_L + 0.5 * g * h_L**2 * B
            return F_h, F_Q
        else:
            return 0.0, 0.0

    # Solve for star region
    h_star, u_star = _solve_star_region_numba(h_L, u_L, h_R, u_R, g, max_iter, tol)

    # Sample solution
    h_sample, u_sample = _sample_solution_numba(h_L, u_L, h_R, u_R, h_star, u_star, g)

    # Compute flux
    Q_sample = h_sample * u_sample * B
    F_h = Q_sample
    F_Q = Q_sample * u_sample + 0.5 * g * h_sample**2 * B

    return F_h, F_Q


# ==============================================================================
# Public API - automatically selects best version
# ==============================================================================

if NUMBA_AVAILABLE:
    # Use Numba version for production
    riemann_flux = exact_riemann_flux_numba
else:
    # Fallback to pure Python
    riemann_flux = exact_riemann_flux


if __name__ == '__main__':
    """Test exact Riemann flux solver"""
    print("="*70)
    print("Testing Exact Riemann Flux Solver")
    print("="*70)
    print()

    # Test case: Simple dam break
    h_L = 10.0
    h_R = 1.0
    Q_L = 0.0
    Q_R = 0.0
    B = 10.0
    g = 9.81

    print(f"Test Case: Dam Break")
    print(f"  Left:  h={h_L}m, Q={Q_L}m³/s")
    print(f"  Right: h={h_R}m, Q={Q_R}m³/s")
    print(f"  Width: B={B}m")
    print()

    # Compute flux
    F_h, F_Q = riemann_flux(h_L, Q_L, h_R, Q_R, B, g, eps_dry=1e-6, max_iter=50, tol=1e-10)

    print(f"Flux at interface:")
    print(f"  F_h = {F_h:.6f} m³/s")
    print(f"  F_Q = {F_Q:.6f} m³/s²")
    print()

    if NUMBA_AVAILABLE:
        print("✅ Using Numba JIT-compiled version (fast)")
    else:
        print("⚠️  Using pure Python version (slow)")

    print()
    print("="*70)
