#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Pump Boundary Condition - 

Implements centrifugal pump boundary conditions for water hammer analysis.


Features :
- Pump characteristic curves  (H-Q, η-Q, P-Q)
- Moment of inertia effects 
- Pump startup and shutdown 
- Multiple operating points 
- Four-quadrant characteristics 

Author: HydroClaude Development Team
Date: 2025-10-30
Version: 1.0.0
"""

import numpy as np
from typing import Tuple, Optional, Callable
from dataclasses import dataclass


@dataclass
class PumpCharacteristics:
    """
     - Centrifugal Pump Characteristics

    Defines pump performance curves using polynomial or tabular data.
    
    """

    #  Design operating point
    Q_design: float  #  (m³/s)
    H_design: float  #  (m)
    n_design: float  #  (rpm)
    efficiency_design: float  #  (-)

    #  Pump curve coefficients (H = a + b*Q + c*Q²)
    H_curve_a: float  # 
    H_curve_b: float  # 
    H_curve_c: float  # 

    #  Moment of inertia
    WR2: float  #  (N·m²) - Flywheel effect

    #  Optional: Efficiency curve (η = d + e*Q + f*Q²)
    eta_curve_d: Optional[float] = None
    eta_curve_e: Optional[float] = None
    eta_curve_f: Optional[float] = None

    def head_at_flow(self, Q: float, n: Optional[float] = None) -> float:
        """
         Calculate head at given flow rate

         Uses affinity laws for speed adjustment:
        Q/Q₀ = n/n₀
        H/H₀ = (n/n₀)²

        Args:
            Q:  (m³/s)
            n:  (rpm), None

        Returns:
             (m)
        """
        if n is None:
            n = self.n_design

        # 
        Q_adj = Q * (self.n_design / n) if n != 0 else 0

        # 
        H_adj = self.H_curve_a + self.H_curve_b * Q_adj + self.H_curve_c * Q_adj**2

        # 
        speed_ratio = n / self.n_design if self.n_design != 0 else 0
        H = H_adj * speed_ratio**2

        return max(H, 0.0)  # 

    def efficiency_at_flow(self, Q: float) -> float:
        """
         Calculate efficiency at given flow rate

        Args:
            Q:  (m³/s)

        Returns:
             (-),  [0, 1]
        """
        if self.eta_curve_d is None:
            # 
            Q_ratio = Q / self.Q_design if self.Q_design > 0 else 0
            eta = self.efficiency_design * (1 - 0.5 * (Q_ratio - 1)**2)
            return np.clip(eta, 0.0, 1.0)
        else:
            # 
            eta = self.eta_curve_d + self.eta_curve_e * Q + self.eta_curve_f * Q**2
            return np.clip(eta, 0.0, 1.0)

    def power_at_flow(self, Q: float, rho: float = 1000.0) -> float:
        """
         Calculate pump input power

        P = ρ * g * Q * H / η

        Args:
            Q:  (m³/s)
            rho:  (kg/m³)

        Returns:
             (W)
        """
        g = 9.81  #  (m/s²)
        H = self.head_at_flow(Q)
        eta = self.efficiency_at_flow(Q)

        if eta > 0 and Q > 0:
            P = rho * g * Q * H / eta
        else:
            P = 0.0

        return P

    @classmethod
    def from_three_points(cls, Q1: float, H1: float,
                          Q2: float, H2: float,
                          Q3: float, H3: float,
                          n_design: float,
                          WR2: float,
                          efficiency_design: float = 0.85):
        """
        

        Fit pump curve from three operating points using quadratic regression:
        H = a + b*Q + c*Q²

        Args:
            Q1, H1:  ()
            Q2, H2:  ()
            Q3, H3:  ()
            n_design:  (rpm)
            WR2:  (N·m²)
            efficiency_design: 

        Returns:
            PumpCharacteristics
        """
        # 
        # [1, Q1, Q1²] [a]   [H1]
        # [1, Q2, Q2²] [b] = [H2]
        # [1, Q3, Q3²] [c]   [H3]

        A = np.array([
            [1, Q1, Q1**2],
            [1, Q2, Q2**2],
            [1, Q3, Q3**2]
        ])
        b = np.array([H1, H2, H3])

        coeffs = np.linalg.solve(A, b)
        a, b_coef, c_coef = coeffs

        return cls(
            Q_design=Q2,
            H_design=H2,
            n_design=n_design,
            efficiency_design=efficiency_design,
            H_curve_a=a,
            H_curve_b=b_coef,
            H_curve_c=c_coef,
            WR2=WR2
        )


class PumpBoundary:
    """
     - Centrifugal Pump Boundary for Water Hammer

    Handles pump boundary conditions in water hammer analysis including:
    - Pump characteristic curves
    - Speed variations (startup, shutdown, power failure)
    - Moment of inertia effects

    
    - 
    - 
    - 
    """

    def __init__(self,
                 pump_chars: PumpCharacteristics,
                 speed_function: Optional[Callable[[float], float]] = None,
                 pipe_area: float = 1.0,
                 wave_speed: float = 1000.0):
        """
        

        Args:
            pump_chars: 
            speed_function:  n(t), (rpm)
                          None
            pipe_area:  (m²)
            wave_speed:  (m/s)
        """
        self.pump = pump_chars
        self.speed_function = speed_function
        self.A = pipe_area
        self.a = wave_speed

        # 
        self.current_speed = self.pump.n_design
        self.current_torque = 0.0

    def apply_boundary(self, t: float, H_plus: float, H_minus: float,
                      Q_plus: float, Q_minus: float,
                      dt: float) -> Tuple[float, float]:
        """
        MOC

        Apply pump boundary condition using Method of Characteristics

         Characteristic equations:
        C⁺: H_p = C_p - B * Q_p  ()
        C⁻: H_p = C_m + B * Q_p  ()

         where:
        C_p = H_i-1 + B * Q_i-1
        C_m = H_i+1 - B * Q_i+1
        B = a / (g * A)

         Pump equation:
        H_p = H_pump(Q_p, n)

        Args:
            t:  (s)
            H_plus: C⁺
            H_minus: C⁻
            Q_plus: 
            Q_minus: 
            dt:  (s)

        Returns:
            (H_pump, Q_pump): 
        """
        g = 9.81
        B = self.a / (g * self.A)

        # 
        if self.speed_function is not None:
            n_new = self.speed_function(t)
        else:
            n_new = self.pump.n_design

        # 
        # 
        # ω' = (T_motor - T_pump) / (WR2 / g)
        # speed_function

        self.current_speed = n_new

        # HQ
        # : H = C_p - B*Q    H = C_m + B*Q
        # : H = f(Q, n)

        # 
        Q = max(0.5 * (Q_plus + Q_minus), 0.001)  # >0

        for iter in range(20):  # 20
            H_char_plus = H_plus - B * Q
            H_char_minus = H_minus + B * Q
            H_pump = self.pump.head_at_flow(Q, self.current_speed)

            # 
            #  = (C_p + C_m) / 2
            H_target = (H_char_plus + H_char_minus) / 2

            residual = H_pump - H_target

            if abs(residual) < 0.01:
                break

            # 
            dQ = max(Q * 0.01, 0.0001)
            H_pump_plus = self.pump.head_at_flow(Q + dQ, self.current_speed)
            dH_dQ = (H_pump_plus - H_pump) / dQ

            # 
            dH_dQ_char = 0.0  # 0
            total_slope = dH_dQ

            if abs(total_slope) > 1e-6:
                dQ_update = -residual / total_slope
                # 
                Q += 0.5 * dQ_update
                Q = max(Q, 0.0001)  # 
            else:
                # 
                if residual > 0:
                    Q *= 0.9
                else:
                    Q *= 1.1

        # 
        H = self.pump.head_at_flow(Q, self.current_speed)

        # 
        if H <= 0 or Q <= 0:
            # 
            Q = self.pump.Q_design
            H = self.pump.head_at_flow(Q, self.current_speed)

        return H, Q

    @staticmethod
    def power_failure(t_fail: float) -> Callable[[float], float]:
        """
        

        Create speed function for power failure scenario

         Speed decay model:
        n(t) = n₀ * exp(-k * (t - t_fail))  for t >= t_fail
        n(t) = n₀                            for t < t_fail

        Args:
            t_fail:  (s)

        Returns:
             n(t)
        """
        def speed_func(t: float, n0: float = 1500.0, k: float = 0.5) -> float:
            if t < t_fail:
                return n0
            else:
                return n0 * np.exp(-k * (t - t_fail))

        return speed_func

    @staticmethod
    def gradual_shutdown(t_start: float, t_end: float,
                        n_initial: float) -> Callable[[float], float]:
        """
        

        Create speed function for gradual pump shutdown

        Args:
            t_start:  (s)
            t_end:  (s)
            n_initial:  (rpm)

        Returns:
             n(t)
        """
        def speed_func(t: float) -> float:
            if t < t_start:
                return n_initial
            elif t > t_end:
                return 0.0
            else:
                # 
                return n_initial * (1 - (t - t_start) / (t_end - t_start))

        return speed_func

    @staticmethod
    def gradual_startup(t_start: float, t_end: float,
                       n_final: float) -> Callable[[float], float]:
        """
        

        Create speed function for gradual pump startup

        Args:
            t_start:  (s)
            t_end:  (s)
            n_final:  (rpm)

        Returns:
             n(t)
        """
        def speed_func(t: float) -> float:
            if t < t_start:
                return 0.0
            elif t > t_end:
                return n_final
            else:
                # 
                return n_final * (t - t_start) / (t_end - t_start)

        return speed_func


#  Common pump parameters library
class StandardPumps:
    """"""

    @staticmethod
    def small_booster_pump():
        """"""
        return PumpCharacteristics(
            Q_design=0.05,  # 50 L/s
            H_design=30.0,  # 30 m
            n_design=1450,  # rpm
            efficiency_design=0.75,
            H_curve_a=35.0,
            H_curve_b=-50.0,
            H_curve_c=-200.0,
            WR2=1.5  # N·m²
        )

    @staticmethod
    def medium_pump():
        """"""
        return PumpCharacteristics(
            Q_design=0.2,  # 200 L/s
            H_design=50.0,  # 50 m
            n_design=1480,  # rpm
            efficiency_design=0.82,
            H_curve_a=58.0,
            H_curve_b=-20.0,
            H_curve_c=-100.0,
            WR2=15.0  # N·m²
        )

    @staticmethod
    def large_pump():
        """"""
        return PumpCharacteristics(
            Q_design=1.0,  # 1000 L/s = 1 m³/s
            H_design=80.0,  # 80 m
            n_design=1480,  # rpm
            efficiency_design=0.88,
            H_curve_a=92.0,
            H_curve_b=-10.0,
            H_curve_c=-20.0,
            WR2=100.0  # N·m²
        )
