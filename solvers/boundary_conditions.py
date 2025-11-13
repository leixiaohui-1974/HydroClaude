#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Characteristic-Based Boundary Conditions

Riemann
- Critical Flow BC
- Supercritical Flow BC
- Subcritical Flow BC
- Non-reflecting BC


- 
- Riemann
- Froude


- LeVeque (2002): Finite Volume Methods for Hyperbolic Problems
- Toro (2001): Shock-Capturing Methods for Free-Surface Shallow Flows
- Chow (1959): Open-Channel Hydraulics

: HydroClaude Team
: 2025-10-29
"""

import numpy as np
from typing import Tuple, Optional, Callable
from enum import Enum


class FlowRegime(Enum):
    """"""
    SUBCRITICAL = "subcritical"    #  (Fr < 1)
    CRITICAL = "critical"           #  (Fr ≈ 1)
    SUPERCRITICAL = "supercritical" #  (Fr > 1)


class BoundaryConditionType(Enum):
    """"""
    FIXED_DEPTH = "h"              # 
    FIXED_DISCHARGE = "Q"          # 
    CRITICAL_DEPTH = "critical"    # 
    NORMAL_DEPTH = "normal"        # 
    TRANSMISSIVE = "transmissive"  # 
    RIEMANN = "riemann"            # Riemann


class CharacteristicBC:
    """
    

    Froude

    Fr < 1:
    - : 1 → 1
    - : 1 → 1

    Fr > 1:
    - : 2 → 2
    - : 0 → 

    Fr ≈ 1:
    - 
    """

    def __init__(self, g: float = 9.81):
        """
        

        :
            g:  (m/s²)
        """
        self.g = g
        self.critical_threshold = 0.05  # Fr[1-δ, 1+δ]

    def compute_froude_number(
        self,
        h: float,
        u: float,
        g: Optional[float] = None
    ) -> float:
        """
        Froude

        Fr = u / sqrt(g*h)

        :
            h:  (m)
            u:  (m/s)
            g:  (m/s²)

        :
            Froude
        """
        if g is None:
            g = self.g

        if h < 1e-10:
            return 0.0

        return abs(u) / np.sqrt(g * h)

    def identify_flow_regime(
        self,
        h: float,
        u: float
    ) -> FlowRegime:
        """
        

        :
            h:  (m)
            u:  (m/s)

        :
            
        """
        Fr = self.compute_froude_number(h, u)

        if abs(Fr - 1.0) < self.critical_threshold:
            return FlowRegime.CRITICAL
        elif Fr < 1.0:
            return FlowRegime.SUBCRITICAL
        else:
            return FlowRegime.SUPERCRITICAL

    def compute_riemann_invariants(
        self,
        h: float,
        u: float
    ) -> Tuple[float, float]:
        """
        Riemann

        Riemann
        R+ = u + 2*sqrt(g*h)  (C+)
        R- = u - 2*sqrt(g*h)  (C-)

        
        λ+ = u + sqrt(g*h)
        λ- = u - sqrt(g*h)

        :
            h:  (m)
            u:  (m/s)

        :
            (R+, R-) Riemann
        """
        c = np.sqrt(self.g * h)  # 
        R_plus = u + 2.0 * c
        R_minus = u - 2.0 * c

        return R_plus, R_minus

    def recover_from_riemann_invariants(
        self,
        R_plus: float,
        R_minus: float
    ) -> Tuple[float, float]:
        """
        Riemann

        h = ((R+ - R-) / 4)² / g
        u = (R+ + R-) / 2

        :
            R_plus: R+ Riemann
            R_minus: R- Riemann

        :
            (h, u) 
        """
        u = 0.5 * (R_plus + R_minus)
        c = 0.25 * (R_plus - R_minus)
        h = (c * c) / self.g

        return h, u

    def apply_subcritical_inlet(
        self,
        h_ghost: float,
        u_ghost: float,
        h_interior: float,
        u_interior: float,
        bc_value: float,
        bc_type: str = 'Q',
        B: float = 1.0
    ) -> Tuple[float, float]:
        """
        

        Fr < 1
        - C+ (λ+ = u + c > 0):  → 
        - C- (λ- = u - c < 0):  → 

        1Qh

        :
            h_ghost:  (m) - 
            u_ghost:  (m/s) - 
            h_interior:  (m)
            u_interior:  (m/s)
            bc_value: 
            bc_type:  ('Q'  'h')
            B:  (m)

        :
            (h_bc, u_bc) 
        """
        # R+C+
        R_plus_interior, _ = self.compute_riemann_invariants(h_interior, u_interior)

        if bc_type == 'Q':
            # Q (m³/s)
            Q_bc = bc_value

            # 
            h_bc = h_interior

            for _ in range(20):
                u_bc = Q_bc / (B * h_bc) if h_bc > 1e-10 else 0.0
                _, R_minus_bc = self.compute_riemann_invariants(h_bc, u_bc)

                # R+_interiorR-_bc
                h_new, u_new = self.recover_from_riemann_invariants(
                    R_plus_interior, R_minus_bc
                )

                # 
                if abs(h_new - h_bc) < 1e-6:
                    break
                h_bc = 0.5 * (h_bc + h_new)

            u_bc = Q_bc / (B * h_bc) if h_bc > 1e-10 else 0.0

        elif bc_type == 'h':
            # h
            h_bc = bc_value

            # h_bcR-
            # u_bc
            u_bc = u_interior  # 

            for _ in range(20):
                _, R_minus_bc = self.compute_riemann_invariants(h_bc, u_bc)

                # R+_interiorR-_bc
                _, u_new = self.recover_from_riemann_invariants(
                    R_plus_interior, R_minus_bc
                )

                if abs(u_new - u_bc) < 1e-6:
                    break
                u_bc = 0.5 * (u_bc + u_new)

        else:
            raise ValueError(f"Unsupported bc_type: {bc_type}")

        return h_bc, u_bc

    def apply_subcritical_outlet(
        self,
        h_ghost: float,
        u_ghost: float,
        h_interior: float,
        u_interior: float,
        bc_value: float,
        bc_type: str = 'h',
        B: float = 1.0
    ) -> Tuple[float, float]:
        """
        

        Fr < 1
        - C+ (λ+ = u + c > 0):  → 
        - C- (λ- = u - c < 0):  → 

        1h

        :
            h_ghost:  (m)
            u_ghost:  (m/s)
            h_interior:  (m)
            u_interior:  (m/s)
            bc_value: 
            bc_type:  ('h'  'Q')

        :
            (h_bc, u_bc) 
        """
        # R+C+
        R_plus_interior, _ = self.compute_riemann_invariants(h_interior, u_interior)

        if bc_type == 'h':
            # h
            h_bc = bc_value

            # u_bc
            u_bc = u_interior  # 

            for _ in range(20):
                _, R_minus_bc = self.compute_riemann_invariants(h_bc, u_bc)

                # R+_interiorR-_bc
                _, u_new = self.recover_from_riemann_invariants(
                    R_plus_interior, R_minus_bc
                )

                if abs(u_new - u_bc) < 1e-6:
                    break
                u_bc = 0.5 * (u_bc + u_new)

        elif bc_type == 'Q':
            # Q
            Q_bc = bc_value

            # h_bc
            h_bc = h_interior

            for _ in range(20):
                u_bc = Q_bc / (B * h_bc) if h_bc > 1e-10 else 0.0
                _, R_minus_bc = self.compute_riemann_invariants(h_bc, u_bc)

                h_new, _ = self.recover_from_riemann_invariants(
                    R_plus_interior, R_minus_bc
                )

                if abs(h_new - h_bc) < 1e-6:
                    break
                h_bc = 0.5 * (h_bc + h_new)

            u_bc = Q_bc / (B * h_bc) if h_bc > 1e-10 else 0.0

        else:
            raise ValueError(f"Unsupported bc_type: {bc_type}")

        return h_bc, u_bc

    def apply_supercritical_inlet(
        self,
        h_bc_value: float,
        Q_bc_value: float,
        B: float = 1.0
    ) -> Tuple[float, float]:
        """
        

        Fr > 1
        - C+ (λ+ = u + c > 0): 
        - C- (λ- = u - c > 0): 

        2hQ

        :
            h_bc_value:  (m)
            Q_bc_value:  (m³/s)
            B:  (m)

        :
            (h_bc, u_bc) 
        """
        h_bc = h_bc_value
        u_bc = Q_bc_value / (B * h_bc) if h_bc > 1e-10 else 0.0

        return h_bc, u_bc

    def apply_supercritical_outlet(
        self,
        h_interior: float,
        u_interior: float
    ) -> Tuple[float, float]:
        """
        

        Fr > 1
        - C+ (λ+ = u + c > 0): 
        - C- (λ- = u - c > 0): 

        

        :
            h_interior:  (m)
            u_interior:  (m/s)

        :
            (h_bc, u_bc) 
        """
        # 
        h_bc = h_interior
        u_bc = u_interior

        return h_bc, u_bc

    def apply_critical_depth_bc(
        self,
        Q: float,
        B: float,
        g: Optional[float] = None
    ) -> Tuple[float, float]:
        """
        

        Fr = 1
         u / sqrt(g*h) = 1

        Q = u * h * B

        h_c = (Q²/(g*B²))^(1/3)

        :
            Q:  (m³/s)
            B:  (m)
            g:  (m/s²)

        :
            (h_c, u_c) 
        """
        if g is None:
            g = self.g

        # 
        h_c = (Q**2 / (g * B**2))**(1.0/3.0)

        # 
        u_c = Q / (B * h_c) if h_c > 1e-10 else 0.0

        return h_c, u_c

    def apply_transmissive_bc(
        self,
        h_interior: float,
        u_interior: float,
        h_prev: float,
        u_prev: float,
        dt: float,
        dx: float
    ) -> Tuple[float, float]:
        """
        

        
        

        ∂h/∂t + c * ∂h/∂x = 0

         c = u + sqrt(g*h) 

        :
            h_interior:  (m)
            u_interior:  (m/s)
            h_prev:  (m)
            u_prev:  (m/s)
            dt:  (s)
            dx:  (m)

        :
            (h_bc, u_bc) 
        """
        # 
        c = u_interior + np.sqrt(self.g * h_interior)

        # 
        if abs(c) > 1e-10:
            h_bc = h_prev - (c * dt / dx) * (h_interior - h_prev)
            u_bc = u_prev - (c * dt / dx) * (u_interior - u_prev)
        else:
            h_bc = h_interior
            u_bc = u_interior

        # 
        h_bc = max(h_bc, 1e-10)

        return h_bc, u_bc


def test_characteristic_bc():
    """"""
    print("="*80)
    print("")
    print("="*80)

    bc = CharacteristicBC(g=9.81)

    # 1: Froude
    print("\n1: Froude")
    h = 2.0
    u = 3.0
    Fr = bc.compute_froude_number(h, u)
    print(f"h = {h} m, u = {u} m/s")
    print(f"Fr = {Fr:.3f}")
    print(f": {bc.identify_flow_regime(h, u).value}")

    # 2: Riemann
    print("\n2: Riemann")
    R_plus, R_minus = bc.compute_riemann_invariants(h, u)
    print(f"R+ = {R_plus:.3f}")
    print(f"R- = {R_minus:.3f}")

    h_recovered, u_recovered = bc.recover_from_riemann_invariants(R_plus, R_minus)
    print(f": h = {h_recovered:.3f} m (: {abs(h_recovered-h)*100:.6f}%)")
    print(f": u = {u_recovered:.3f} m/s (: {abs(u_recovered-u)*100:.6f}%)")

    # 3: BC
    print("\n3: ")
    h_interior = 2.0
    u_interior = 1.0  # Fr = 0.23 < 1
    Q_bc = 30.0  # 
    B = 10.0

    h_bc, u_bc = bc.apply_subcritical_inlet(
        None, None, h_interior, u_interior, Q_bc, bc_type='Q', B=B
    )
    Fr_bc = bc.compute_froude_number(h_bc, u_bc)
    print(f": h = {h_interior} m, u = {u_interior} m/s, Fr = {bc.compute_froude_number(h_interior, u_interior):.3f}")
    print(f": h = {h_bc:.3f} m, u = {u_bc:.3f} m/s, Fr = {Fr_bc:.3f}")
    print(f": Q = {u_bc * h_bc * B:.3f} m³/s (: {Q_bc} m³/s)")

    # 4: BC
    print("\n4: ")
    Q = 20.0
    B = 10.0
    h_c, u_c = bc.apply_critical_depth_bc(Q, B)
    Fr_c = bc.compute_froude_number(h_c, u_c)
    print(f": h_c = {h_c:.3f} m")
    print(f": u_c = {u_c:.3f} m/s")
    print(f"Froude: Fr = {Fr_c:.3f} (≈1.0)")
    print(f": Q = {u_c * h_c * B:.3f} m³/s")

    # 5: 
    print("\n5: ")
    h_super = 0.5
    Q_super = 20.0
    u_super = Q_super / (B * h_super)
    Fr_super = bc.compute_froude_number(h_super, u_super)
    print(f": h = {h_super} m, u = {u_super:.3f} m/s, Fr = {Fr_super:.3f}")

    h_bc_super, u_bc_super = bc.apply_supercritical_inlet(h_super, Q_super, B)
    print(f": h = {h_bc_super} m, u = {u_bc_super:.3f} m/s")

    print("\n" + "="*80)
    print(" ")
    print("="*80)


if __name__ == '__main__':
    test_characteristic_bc()
