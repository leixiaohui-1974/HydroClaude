#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Anderson


Aitken

: Claude
: 2025-10-22
"""

import numpy as np
from typing import Optional, Deque
from collections import deque


class AndersonAcceleration:
    """
    Anderson

     x = g(x)

    
    - m
    - 
    - 

    
    Walker, H. F., & Ni, P. (2011). Anderson acceleration for
    fixed-point iterations. SIAM J. Numer. Anal., 49(4), 1715-1735.
    """

    def __init__(self,
                 m: int = 5,
                 beta: float = 1.0,
                 reg: float = 1e-8,
                 restart: bool = True):
        """
        Args:
            m: m
            beta: 0-11
            reg: 
            restart: 
        """
        self.m = m
        self.beta = beta
        self.reg = reg
        self.restart = restart

        # 
        self.x_history: Deque = deque(maxlen=m)
        self.f_history: Deque = deque(maxlen=m)

        # 
        self.iteration = 0
        self.restart_count = 0

    def reset(self):
        """"""
        self.x_history.clear()
        self.f_history.clear()
        self.iteration = 0

    def compute_acceleration(self,
                            x_current: np.ndarray,
                            x_next: np.ndarray) -> np.ndarray:
        """
        Anderson

        Args:
            x_current: 
            x_next: 

        Returns:
            x_accelerated: 
        """
        self.iteration += 1

        # f = g(x) - x = x_next - x_current
        f_current = x_next - x_current

        # 
        x_current_arr = np.atleast_1d(x_current)
        f_current_arr = np.atleast_1d(f_current)

        # 
        self.x_history.append(x_current_arr.copy())
        self.f_history.append(f_current_arr.copy())

        # 
        mk = len(self.x_history)

        if mk == 1:
            # 
            return x_next

        # 
        # F = [f_{k-mk+1} - f_k, f_{k-mk+2} - f_k, ..., f_{k-1} - f_k]
        F = np.column_stack([
            self.f_history[i] - f_current_arr
            for i in range(mk - 1)
        ])

        # min ||F·α||²
        # QR
        try:
            # 
            FtF = F.T @ F + self.reg * np.eye(mk - 1)
            Ftf = F.T @ f_current_arr

            # 
            alpha = np.linalg.solve(FtF, Ftf)

        except np.linalg.LinAlgError:
            # 
            if self.restart:
                self.reset()
                self.restart_count += 1
            return x_next

        # 
        # x_{k+1} = (1 - β)·x_k + β·(Σ γ_i·x_i)
        #  γ_0 = 1 - Σα_i, γ_i = α_{i-1} (i≥1)

        gamma = np.zeros(mk)
        gamma[0] = 1.0 - np.sum(alpha)
        gamma[1:] = alpha

        # 
        x_bar = sum(gamma[i] * self.x_history[i] for i in range(mk))
        f_bar = sum(gamma[i] * self.f_history[i] for i in range(mk))

        # 
        x_accelerated = x_bar + self.beta * f_bar

        # 
        if np.isscalar(x_current) or x_current.shape == ():
            return x_accelerated[0]

        return x_accelerated

    def get_statistics(self) -> dict:
        """"""
        return {
            'iterations': self.iteration,
            'restarts': self.restart_count,
            'history_depth': len(self.x_history),
            'max_depth': self.m
        }


def test_anderson_acceleration():
    """Anderson"""
    print("=" * 80)
    print("Anderson")
    print("=" * 80)

    #  x = cos(x)
    # x_{k+1} = cos(x_k)

    def fixed_point_iteration(x):
        """g(x) = cos(x)"""
        return np.cos(x)

    # 
    x_exact = 0.7390851332151607  # cos(x) = x 

    print("\n x = cos(x)")
    print(f": x ≈ {x_exact:.10f}")
    print()

    # 1
    print("1")
    print("-" * 80)

    x = 0.5  # 
    errors_no_accel = []

    for i in range(50):
        x_next = fixed_point_iteration(x)
        error = abs(x_next - x_exact)
        errors_no_accel.append(error)

        if i < 10 or i % 10 == 0:
            print(f"  Iter {i}: x = {x:.10f}, error = {error:.3e}")

        if error < 1e-10:
            print(f"   {i} ")
            break

        x = x_next

    # 2Anderson
    print("\n2Anderson")
    print("-" * 80)

    x = 0.5  # 
    anderson = AndersonAcceleration(m=5, beta=1.0)
    errors_anderson = []

    for i in range(50):
        x_next = fixed_point_iteration(x)
        x_accel = anderson.compute_acceleration(x, x_next)

        error = abs(x_accel - x_exact)
        errors_anderson.append(error)

        if i < 10 or i % 10 == 0:
            print(f"  Iter {i}: x = {x_accel:.10f}, error = {error:.3e}")

        if error < 1e-10:
            print(f"   {i} ")
            stats = anderson.get_statistics()
            print(f"  : {stats['restarts']}")
            break

        x = x_accel

    # 
    print("\n" + "=" * 80)
    print("")
    print("=" * 80)

    # 
    target_error = 1e-6

    iter_no_accel = next((i for i, e in enumerate(errors_no_accel) if e < target_error), len(errors_no_accel))
    iter_anderson = next((i for i, e in enumerate(errors_anderson) if e < target_error), len(errors_anderson))

    print(f"\n < {target_error:.0e} ")
    print(f"  : {iter_no_accel} ")
    print(f"  Anderson: {iter_anderson} ")

    if iter_anderson < iter_no_accel:
        improvement = (iter_no_accel - iter_anderson) / iter_no_accel * 100
        print(f"  : {improvement:.1f}%")

    print("\n" + "=" * 80)


def test_anderson_on_nonlinear_system():
    """Anderson"""
    print("\n\n" + "=" * 80)
    print("Anderson - ")
    print("=" * 80)

    # 
    # x1 = 0.5 * (x1 + x2)
    # x2 = 0.5 * (x1^2 + x2^2)

    def g(x):
        """"""
        x1, x2 = x
        return np.array([
            0.5 * (x1 + x2),
            0.5 * (x1**2 + x2**2)
        ])

    # 
    from scipy.optimize import fsolve
    x_exact = fsolve(lambda x: g(x) - x, [0.5, 0.5])

    print(f"\n: x = [{x_exact[0]:.6f}, {x_exact[1]:.6f}]")
    print()

    # 1
    print("1")
    print("-" * 80)

    x = np.array([0.5, 0.5])

    for i in range(30):
        x_next = g(x)
        error = np.linalg.norm(x_next - x_exact)

        if i < 10 or i % 5 == 0:
            print(f"  Iter {i}: error = {error:.3e}")

        if error < 1e-8:
            print(f"   {i} ")
            break

        x = x_next

    # 2Anderson
    print("\n2Anderson")
    print("-" * 80)

    x = np.array([0.5, 0.5])
    anderson = AndersonAcceleration(m=3, beta=1.0)

    for i in range(30):
        x_next = g(x)
        x_accel = anderson.compute_acceleration(x, x_next)

        error = np.linalg.norm(x_accel - x_exact)

        if i < 10 or i % 5 == 0:
            print(f"  Iter {i}: error = {error:.3e}")

        if error < 1e-8:
            print(f"   {i} ")
            stats = anderson.get_statistics()
            print(f"  : {stats['restarts']}")
            break

        x = x_accel

    print("\n" + "=" * 80)


if __name__ == "__main__":
    test_anderson_acceleration()
    test_anderson_on_nonlinear_system()
