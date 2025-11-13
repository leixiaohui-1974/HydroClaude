#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""





: Claude
: 2025-10-22
"""

import numpy as np
from abc import ABC, abstractmethod
from typing import Union, Callable, Optional


class HydraulicStructure(ABC):
    """"""

    def __init__(self, position: float, width: float, g: float = 9.81):
        """
        Args:
            position:  (m)
            width:  (m)
            g:  (m/s²)
        """
        self.position = position
        self.width = width
        self.g = g
        self.current_time = 0.0  # 

    def update_time(self, t: float):
        """
        

        Args:
            t:  (s)
        """
        self.current_time = t

    @abstractmethod
    def calculate_discharge(self, h_upstream: float, h_downstream: float,
                          t: Optional[float] = None) -> tuple:
        """
        

        Args:
            h_upstream:  (m)
            h_downstream:  (m)
            t:  (s)

        Returns:
            (discharge, flow_type):  (m³/s) 
        """
        pass

    @abstractmethod
    def calculate_discharge_derivatives(self, h_upstream: float, h_downstream: float,
                                        t: Optional[float] = None) -> tuple:
        """
        

        Args:
            h_upstream:  (m)
            h_downstream:  (m)
            t:  (s)

        Returns:
            (dQ_dh_up, dQ_dh_down): 
        """
        pass

    @abstractmethod
    def __repr__(self) -> str:
        """"""
        pass


class SluiceGate(HydraulicStructure):
    """

    
    - : Q = Cd * B * e * √(2g * Δh)
    - : Q = Cd * B * e * √(2g * h_upstream)

    
        Cd: 
        B: 
        e: 
        Δh: 

    opening
    """

    def __init__(self, position: float, width: float,
                 opening: Union[float, Callable[[float], float]],
                 Cd: float = 0.6, g: float = 9.81,
                 submerged_threshold: float = 0.1):
        """
        Args:
            position:  (m)
            width:  (m)
            opening:  (m)   opening(t) -> float
            Cd:  (0.6)
            g:  (m/s²)
            submerged_threshold:  (m)
        """
        super().__init__(position, width, g)
        self.opening_func = opening if callable(opening) else lambda t: opening
        self.Cd = Cd
        self.submerged_threshold = submerged_threshold

    def get_opening(self, t: Optional[float] = None) -> float:
        """
        

        Args:
            t:  (s)Noneself.current_time

        Returns:
             (m)
        """
        if t is None:
            t = self.current_time
        return self.opening_func(t)

    def calculate_discharge(self, h_upstream: float, h_downstream: float,
                          t: Optional[float] = None) -> tuple:
        """
        

        Args:
            h_upstream:  (m)
            h_downstream:  (m)
            t:  (s)

        Returns:
            (discharge, flow_type):  (m³/s)  ('free'  'submerged')
        """
        # 
        e = self.get_opening(t)

        # 
        delta_h = h_upstream - h_downstream
        if h_downstream > e or delta_h < self.submerged_threshold:
            # 
            #  PRECISION FIX #1 - MINIMAL
            # 
            delta_h_min = 1e-6  # 1e-41e-6100
            delta_h_effective = max(delta_h_min, delta_h)
            discharge = self.Cd * self.width * e * np.sqrt(2 * self.g * delta_h_effective)
            flow_type = 'submerged'
        else:
            # 
            discharge = self.Cd * self.width * e * np.sqrt(2 * self.g * h_upstream)
            flow_type = 'free'

        return discharge, flow_type

    def calculate_discharge_derivatives(self, h_upstream: float, h_downstream: float,
                                        t: Optional[float] = None) -> tuple:
        """
        

        Args:
            h_upstream:  (m)
            h_downstream:  (m)
            t:  (s)

        Returns:
            (dQ_dh_up, dQ_dh_down): 
        """
        # 
        e = self.get_opening(t)

        # 
        delta_h = h_upstream - h_downstream
        if h_downstream > e or delta_h < self.submerged_threshold:
            # : Q = Cd * B * e * √(2g * Δh)
            #  Δh = max(1e-4, h_up - h_down)
            delta_h_effective = max(1e-4, delta_h)

            # dQ/dh_up = Cd * B * e * (1/2) * (2g * Δh)^(-1/2) * 2g
            #          = Cd * B * e * g / √(2g * Δh)
            # dQ/dh_down = -dQ/dh_up

            if delta_h > 1e-4:
                # 
                dQ_dh_up = self.Cd * self.width * e * self.g / np.sqrt(2 * self.g * delta_h_effective)
                dQ_dh_down = -dQ_dh_up
            else:
                # delta_h
                #  delta_h = 1e-4 
                dQ_dh_up = self.Cd * self.width * e * self.g / np.sqrt(2 * self.g * 1e-4)
                dQ_dh_down = -dQ_dh_up
        else:
            # : Q = Cd * B * e * √(2g * h_up)
            # dQ/dh_up = Cd * B * e * g / √(2g * h_up)
            # dQ/dh_down = 0 ()
            dQ_dh_up = self.Cd * self.width * e * self.g / np.sqrt(2 * self.g * h_upstream)
            dQ_dh_down = 0.0

        return dQ_dh_up, dQ_dh_down

    def __repr__(self) -> str:
        try:
            current_opening = self.get_opening()
            return (f"SluiceGate(position={self.position}m, width={self.width}m, "
                    f"opening={current_opening:.2f}m@t={self.current_time:.0f}s, Cd={self.Cd})")
        except:
            return (f"SluiceGate(position={self.position}m, width={self.width}m, "
                    f"opening=f(t), Cd={self.Cd})")


class BroadCrestedWeir(HydraulicStructure):
    """

    
    Q = Cd * B * h^(3/2) * √(2g)
    """

    def __init__(self, position: float, width: float, crest_height: float,
                 Cd: float = 0.848, g: float = 9.81):
        """
        Args:
            position:  (m)
            width:  (m)
            crest_height:  (m)
            Cd:  (0.848 for broad-crested weir)
            g:  (m/s²)
        """
        super().__init__(position, width, g)
        self.crest_height = crest_height
        self.Cd = Cd

    def calculate_discharge(self, h_upstream: float, h_downstream: float = None,
                          t: Optional[float] = None) -> tuple:
        """
        

        Args:
            h_upstream:  (m)
            h_downstream:  (m)
            t:  (s)

        Returns:
            (discharge, flow_type):  (m³/s) 
        """
        # 
        H = max(0.0, h_upstream - self.crest_height)

        if H < 1e-4:
            # 
            return 0.0, 'no_flow'

        # 
        discharge = self.Cd * self.width * (H ** 1.5) * np.sqrt(2 * self.g)

        return discharge, 'free'

    def calculate_discharge_derivatives(self, h_upstream: float, h_downstream: float = None,
                                        t: Optional[float] = None) -> tuple:
        """
        

        Args:
            h_upstream:  (m)
            h_downstream:  (m)
            t:  (s)

        Returns:
            (dQ_dh_up, dQ_dh_down): 
        """
        # 
        H = max(0.0, h_upstream - self.crest_height)

        if H < 1e-4:
            # 
            return 0.0, 0.0

        # : Q = Cd * B * H^(3/2) * √(2g)
        # dQ/dh_up = Cd * B * (3/2) * H^(1/2) * √(2g)
        dQ_dh_up = self.Cd * self.width * 1.5 * np.sqrt(H * 2 * self.g)

        # 
        dQ_dh_down = 0.0

        return dQ_dh_up, dQ_dh_down

    def __repr__(self) -> str:
        return (f"BroadCrestedWeir(position={self.position}m, width={self.width}m, "
                f"crest_height={self.crest_height}m, Cd={self.Cd})")


class Orifice(HydraulicStructure):
    """

    
    Q = Cd * A * √(2g * h)
    """

    def __init__(self, position: float, width: float, height: float,
                 bottom_elevation: float = 0.0, Cd: float = 0.61, g: float = 9.81):
        """
        Args:
            position:  (m)
            width:  (m)
            height:  (m)
            bottom_elevation:  (m)
            Cd:  (0.61)
            g:  (m/s²)
        """
        super().__init__(position, width, g)
        self.height = height
        self.bottom_elevation = bottom_elevation
        self.Cd = Cd
        self.area = width * height

    def calculate_discharge(self, h_upstream: float, h_downstream: float,
                          t: Optional[float] = None) -> tuple:
        """
        

        Args:
            h_upstream:  (m)
            h_downstream:  (m)
            t:  (s)

        Returns:
            (discharge, flow_type):  (m³/s) 
        """
        # 
        center_elevation = self.bottom_elevation + self.height / 2

        # 
        h_center_upstream = max(0.0, h_upstream - center_elevation)

        if h_center_upstream < 1e-4:
            return 0.0, 'no_flow'

        # 
        if h_downstream > (center_elevation + self.height / 2):
            # 
            h_center_downstream = h_downstream - center_elevation
            delta_h = max(1e-4, h_center_upstream - h_center_downstream)
            discharge = self.Cd * self.area * np.sqrt(2 * self.g * delta_h)
            flow_type = 'submerged'
        else:
            # 
            discharge = self.Cd * self.area * np.sqrt(2 * self.g * h_center_upstream)
            flow_type = 'free'

        return discharge, flow_type

    def calculate_discharge_derivatives(self, h_upstream: float, h_downstream: float,
                                        t: Optional[float] = None) -> tuple:
        """
        

        Args:
            h_upstream:  (m)
            h_downstream:  (m)
            t:  (s)

        Returns:
            (dQ_dh_up, dQ_dh_down): 
        """
        # 
        center_elevation = self.bottom_elevation + self.height / 2

        # 
        h_center_upstream = max(0.0, h_upstream - center_elevation)

        if h_center_upstream < 1e-4:
            return 0.0, 0.0

        # 
        if h_downstream > (center_elevation + self.height / 2):
            # : Q = Cd * A * √(2g * Δh)
            h_center_downstream = h_downstream - center_elevation
            delta_h = max(1e-4, h_center_upstream - h_center_downstream)

            # dQ/dh_up = Cd * A * g / √(2g * Δh)
            # dQ/dh_down = -dQ/dh_up
            dQ_dh_up = self.Cd * self.area * self.g / np.sqrt(2 * self.g * delta_h)
            dQ_dh_down = -dQ_dh_up
        else:
            # : Q = Cd * A * √(2g * h_center_up)
            # dQ/dh_up = Cd * A * g / √(2g * h_center_up)
            # dQ/dh_down = 0
            dQ_dh_up = self.Cd * self.area * self.g / np.sqrt(2 * self.g * h_center_upstream)
            dQ_dh_down = 0.0

        return dQ_dh_up, dQ_dh_down

    def __repr__(self) -> str:
        return (f"Orifice(position={self.position}m, width={self.width}m, "
                f"height={self.height}m, Cd={self.Cd})")


class Spillway(HydraulicStructure):
    """ - 

    
    - WESWES Standard Spillway
    - Ogee Spillway
    - 

    
    - Q = Cd * B * H^(3/2)
    - Q = Cd * B * H^(3/2) * submergence_factor

    
        Cd: WES2.1
        B: 
        H: 
    """

    def __init__(self, position: float, width: float, crest_elevation: float,
                 spillway_type: str = 'wes', Cd: float = 2.1, g: float = 9.81,
                 submergence_threshold: float = 0.67):
        """
        Args:
            position:  (m)
            width:  (m)
            crest_elevation:  (m)
            spillway_type:  ('wes', 'ogee', 'broad_crested')
            Cd: WES2.10.848
            g:  (m/s²)
            submergence_threshold: /
        """
        super().__init__(position, width, g)
        self.crest_elevation = crest_elevation
        self.spillway_type = spillway_type
        self.Cd = Cd
        self.submergence_threshold = submergence_threshold

    def calculate_discharge(self, h_upstream: float, h_downstream: float = None,
                          t: Optional[float] = None) -> tuple:
        """
        

        Args:
            h_upstream:  (m)
            h_downstream:  (m)
            t:  (s)

        Returns:
            (discharge, flow_type):  (m³/s) 
        """
        # 
        H = max(0.0, h_upstream - self.crest_elevation)

        if H < 1e-4:
            # 
            return 0.0, 'no_flow'

        # 
        if self.spillway_type in ['wes', 'ogee']:
            # WES / Q = Cd * B * H^(3/2)
            Q_free = self.Cd * self.width * (H ** 1.5)

        elif self.spillway_type == 'broad_crested':
            # Q = Cd * B * H^(3/2) * sqrt(2g)
            Q_free = self.Cd * self.width * (H ** 1.5) * np.sqrt(2 * self.g)

        else:
            raise ValueError(f"Unknown spillway type: {self.spillway_type}")

        # 
        if h_downstream is not None and h_downstream > self.crest_elevation:
            # 
            h_tail = h_downstream - self.crest_elevation
            submergence_ratio = h_tail / H

            if submergence_ratio > self.submergence_threshold:
                # 
                # VillemonteQ_submerged = Q_free * (1 - (h_tail/H)^1.5)^0.385
                submergence_factor = (1.0 - submergence_ratio ** 1.5) ** 0.385
                submergence_factor = max(0.1, submergence_factor)
                Q = Q_free * submergence_factor
                return Q, 'submerged'

        return Q_free, 'free'

    def calculate_discharge_derivatives(self, h_upstream: float,
                                        h_downstream: float = None,
                                        t: Optional[float] = None) -> tuple:
        """
        

        Args:
            h_upstream:  (m)
            h_downstream:  (m)
            t:  (s)

        Returns:
            (dQ/dh_up, dQ/dh_down): 
        """
        H = max(1e-4, h_upstream - self.crest_elevation)

        if H < 1e-4:
            return 0.0, 0.0

        # 
        if self.spillway_type in ['wes', 'ogee']:
            # Q = Cd * B * H^(3/2)
            # dQ/dH = (3/2) * Cd * B * H^(1/2)
            dQ_dH = 1.5 * self.Cd * self.width * np.sqrt(H)

        elif self.spillway_type == 'broad_crested':
            # Q = Cd * B * H^(3/2) * sqrt(2g)
            # dQ/dH = (3/2) * Cd * B * H^(1/2) * sqrt(2g)
            dQ_dH = 1.5 * self.Cd * self.width * np.sqrt(H * 2 * self.g)
        else:
            dQ_dH = 0.0

        # dQ/dh_up = dQ/dH * dH/dh_up = dQ/dH * 1
        dQ_dh_up = dQ_dH

        # 
        # 
        dQ_dh_down = 0.0

        return dQ_dh_up, dQ_dh_down

    def __repr__(self) -> str:
        return (f"Spillway(type={self.spillway_type}, position={self.position}m, "
                f"width={self.width}m, crest={self.crest_elevation}m, Cd={self.Cd})")


class Transition(HydraulicStructure):
    """ - 

    

    
    h₁ + V₁²/(2g) = h₂ + V₂²/(2g) + h_loss

     h_loss = K * (V₁ - V₂)²/(2g)
    K0.2-0.30.1-0.2
    """

    def __init__(self, position: float, width_upstream: float,
                 width_downstream: float, K_loss: float = 0.2, g: float = 9.81):
        """
        Args:
            position:  (m)
            width_upstream:  (m)
            width_downstream:  (m)
            K_loss: 0.2-0.30.1-0.2
            g:  (m/s²)
        """
        super().__init__(position, width_upstream, g)
        self.width_upstream = width_upstream
        self.width_downstream = width_downstream
        self.K_loss = K_loss

        # 
        if width_downstream > width_upstream:
            self.transition_type = 'expansion'  # 
        elif width_downstream < width_upstream:
            self.transition_type = 'contraction'  # 
        else:
            self.transition_type = 'uniform'  # 

    def calculate_discharge(self, h_upstream: float, h_downstream: float,
                          t: Optional[float] = None) -> tuple:
        """
        

        
        Q = A₁*V₁ = A₂*V₂
        E₁ = E₂ + h_loss

        Args:
            h_upstream:  (m)
            h_downstream:  (m)
            t:  (s)

        Returns:
            (discharge, flow_type):  (m³/s) 
        """
        # 
        A1 = h_upstream * self.width_upstream
        A2 = h_downstream * self.width_downstream

        if A1 < 1e-6 or A2 < 1e-6:
            return 0.0, 'no_flow'

        # 
        # Q = A*V
        # 

        # 
        E1 = h_upstream
        E2 = h_downstream + self.K_loss * 0.1  # 

        # 
        if E1 > E2:
            V1 = np.sqrt(2 * self.g * (E1 - E2))
            Q = A1 * V1
        else:
            Q = 0.0

        return Q, self.transition_type

    def calculate_discharge_derivatives(self, h_upstream: float, h_downstream: float,
                                        t: Optional[float] = None) -> tuple:
        """
        

        Args:
            h_upstream:  (m)
            h_downstream:  (m)
            t:  (s)

        Returns:
            (dQ/dh_up, dQ/dh_down): 
        """
        # 
        eps = 1e-4
        Q0 = self.calculate_discharge(h_upstream, h_downstream)[0]
        Q_up = self.calculate_discharge(h_upstream + eps, h_downstream)[0]
        Q_down = self.calculate_discharge(h_upstream, h_downstream + eps)[0]

        dQ_dh_up = (Q_up - Q0) / eps if Q0 > 1e-6 else 0.0
        dQ_dh_down = (Q_down - Q0) / eps if Q0 > 1e-6 else 0.0

        return dQ_dh_up, dQ_dh_down

    def __repr__(self) -> str:
        return (f"Transition(type={self.transition_type}, position={self.position}m, "
                f"width={self.width_upstream}m→{self.width_downstream}m, K={self.K_loss})")


class Drop(HydraulicStructure):
    """ - 

    
    

    
    Q = Cd * B * h * sqrt(2g * (h + Δz))

    
        Cd: 0.6
        B: 
        h: 
        Δz: 
    """

    def __init__(self, position: float, width: float, drop_height: float,
                 Cd: float = 0.6, g: float = 9.81):
        """
        Args:
            position:  (m)
            width:  (m)
            drop_height: / (m)
            Cd: 0.6
            g:  (m/s²)
        """
        super().__init__(position, width, g)
        self.drop_height = drop_height
        self.Cd = Cd

    def calculate_discharge(self, h_upstream: float, h_downstream: float = None,
                          t: Optional[float] = None) -> tuple:
        """
        

        Q = Cd * B * h * sqrt(2g * (h + Δz))

        Args:
            h_upstream:  (m)
            h_downstream:  (m
            t:  (s)

        Returns:
            (discharge, flow_type):  (m³/s) 
        """
        if h_upstream < 1e-4:
            return 0.0, 'no_flow'

        # 
        # Q = Cd * B * h * sqrt(2g * (h + Δz))
        total_head = h_upstream + self.drop_height
        Q = self.Cd * self.width * h_upstream * np.sqrt(2 * self.g * total_head)

        return Q, 'drop'

    def calculate_discharge_derivatives(self, h_upstream: float, h_downstream: float = None,
                                        t: Optional[float] = None) -> tuple:
        """
        

        Q = Cd * B * h * sqrt(2g * (h + Δz))
        dQ/dh = Cd * B * [sqrt(2g(h+Δz)) + h * g/sqrt(2g(h+Δz))]

        Args:
            h_upstream:  (m)
            h_downstream:  (m)
            t:  (s)

        Returns:
            (dQ/dh_up, dQ/dh_down): 
        """
        if h_upstream < 1e-4:
            return 0.0, 0.0

        h = h_upstream
        delta_z = self.drop_height
        total_head = h + delta_z

        # Q = Cd * B * h * sqrt(2g * total_head)
        # dQ/dh = Cd * B * [sqrt(2g*total_head) + h * g/sqrt(2g*total_head)]
        sqrt_term = np.sqrt(2 * self.g * total_head)
        dQ_dh_up = self.Cd * self.width * (sqrt_term + h * self.g / sqrt_term)

        # 
        dQ_dh_down = 0.0

        return dQ_dh_up, dQ_dh_down

    def __repr__(self) -> str:
        return (f"Drop(position={self.position}m, width={self.width}m, "
                f"height={self.drop_height}m, Cd={self.Cd})")


class PumpStation(HydraulicStructure):
    """

    
    
    1. 
    2. 
    3. 

    
    - Q = Q_rated
    - Q = Q_rated * (h_upstream / h_min)^0.5
    - H_pump = H_rated
    """

    def __init__(self, position: float, width: float,
                 rated_flow: float = 30.0,
                 rated_head: float = 5.0,
                 min_suction_head: float = 2.0,
                 g: float = 9.81):
        """
        Args:
            position:  (m)
            width:  (m)
            rated_flow:  (m³/s)
            rated_head:  (m)
            min_suction_head:  (m)
            g:  (m/s²)
        """
        super().__init__(position, width, g)
        self.rated_flow = rated_flow
        self.rated_head = rated_head
        self.min_suction_head = min_suction_head

        # 
        self.is_running = True

    def calculate_discharge(self, h_upstream: float, h_downstream: float,
                          t: Optional[float] = None) -> tuple:
        """
        

        
        1.  >= min_suction_headQ = Q_rated
        2.  < min_suction_headQ = Q_rated * sqrt(h_upstream / min_suction_head)
        3. 

        Args:
            h_upstream:  (m)
            h_downstream:  (m)
            t:  (s)

        Returns:
            (discharge, flow_type):  (m³/s) 
        """
        if not self.is_running:
            return 0.0, 'pump_off'

        # 
        if h_upstream < 0.1:  # 
            return 0.0, 'insufficient_water'

        if h_upstream >= self.min_suction_head:
            # 
            discharge = self.rated_flow
            flow_type = 'rated'
        else:
            # 
            # Q = Q_rated * sqrt(h_up / h_min)
            ratio = np.sqrt(h_upstream / self.min_suction_head)
            discharge = self.rated_flow * ratio
            flow_type = 'reduced'

        return discharge, flow_type

    def calculate_discharge_derivatives(self, h_upstream: float, h_downstream: float,
                                        t: Optional[float] = None) -> tuple:
        """
        

        
        1. h >= h_mindQ/dh = 0
        2. h < h_mindQ/dh_up > 0
        3. dQ/dh_down = 0

        Args:
            h_upstream:  (m)
            h_downstream:  (m)
            t:  (s)

        Returns:
            (dQ_dh_up, dQ_dh_down): 
        """
        if not self.is_running or h_upstream < 0.1:
            return 0.0, 0.0

        if h_upstream >= self.min_suction_head:
            # 
            dQ_dh_up = 0.0
        else:
            # Q = Q_rated * sqrt(h_up / h_min)
            # dQ/dh_up = Q_rated / (2 * sqrt(h_up * h_min))
            dQ_dh_up = self.rated_flow / (2.0 * np.sqrt(h_upstream * self.min_suction_head))

        # 
        dQ_dh_down = 0.0

        return dQ_dh_up, dQ_dh_down

    def set_running_state(self, is_running: bool):
        """
        

        Args:
            is_running: True=False=
        """
        self.is_running = is_running

    def get_momentum_source(self, h: float, dx: float, spread_points: int = 5) -> float:
        """
        

        
        

        ∂(hu)/∂t + ∂(hu²/h + 0.5gh²)/∂x = -ghS_f + S_pump

        S_pump = g * h * (ΔH/Δx)
        
        - ΔH = rated_head
        - Δx = spread_points * dx2-5

        Args:
            h:  (m)
            dx:  (m)
            spread_points: 

        Returns:
            S_pump:  (m/s²)
        """
        if not self.is_running:
            return 0.0

        # 
        pump_length = spread_points * dx

        # S = g * h * (ΔH / L_pump)
        # 
        S_pump = self.g * h * self.rated_head / pump_length

        return S_pump

    def __repr__(self) -> str:
        state = "ON" if self.is_running else "OFF"
        return (f"PumpStation(position={self.position}m, Q_rated={self.rated_flow}m³/s, "
                f"H_rated={self.rated_head}m, state={state})")


class PumpStationSimplified(HydraulicStructure):
    """
    
    
    1. 
    2. 
    3. 
    
    
    - 
    - 
    - 
    
    
    - 
    - 
    """
    
    def __init__(self, position: float, width: float,
                 rated_flow: float = 30.0,
                 rated_head: float = 5.0,
                 max_overload_ratio: float = 1.3,
                 min_suction_head: float = 2.0,
                 g: float = 9.81):
        """
        Args:
            position:  (m)
            width:  (m)
            rated_flow:  (m³/s)
            rated_head:  (m)
            max_overload_ratio: 
            min_suction_head:  (m)
            g:  (m/s²)
        """
        super().__init__(position, width, g)
        self.rated_flow = rated_flow
        self.rated_head = rated_head
        self.max_overload_ratio = max_overload_ratio
        self.min_suction_head = min_suction_head
        
        self.max_flow = rated_flow * max_overload_ratio
        
        # 
        self.is_running = True
        self.current_head = rated_head
        self.current_flow = rated_flow
    
    def calculate_discharge(self, h_upstream: float, h_downstream: float,
                          t: Optional[float] = None, Q_upstream: Optional[float] = None) -> tuple:
        """
        
        
        
        1. 
        2. 
        3. 
        
        Args:
            h_upstream:  (m)
            h_downstream:  (m)
            t:  (s)
            Q_upstream:  (m³/s)
        
        Returns:
            (discharge, flow_type):  (m³/s) 
        """
        if not self.is_running:
            self.current_flow = 0.0
            self.current_head = 0.0
            return 0.0, 'pump_off'
        
        # 
        if h_upstream < 0.1:
            self.current_flow = 0.0
            self.current_head = 0.0
            return 0.0, 'insufficient_water'
        
        # 
        if Q_upstream is None:
            Q_upstream = self.rated_flow
        
        #  = 
        if Q_upstream <= self.max_flow:
            # 
            discharge = Q_upstream
            
            # 
            if discharge <= self.rated_flow:
                # 
                self.current_head = self.rated_head
                flow_type = 'normal'
            else:
                # 
                # H = H_rated * (2 - Q/Q_rated)
                ratio = discharge / self.rated_flow
                self.current_head = self.rated_head * (2.0 - ratio)
                self.current_head = max(0.0, self.current_head)
                flow_type = 'overload'
        else:
            # 
            discharge = self.max_flow
            self.current_head = self.rated_head * (2.0 - self.max_overload_ratio)
            self.current_head = max(0.0, self.current_head)
            flow_type = 'max_capacity'
        
        self.current_flow = discharge
        return discharge, flow_type
    
    def calculate_discharge_derivatives(self, h_upstream: float, h_downstream: float,
                                       t: Optional[float] = None) -> tuple:
        """
        
        
        
        """
        if not self.is_running or h_upstream < 0.1:
            return 0.0, 0.0
        
        # 
        # 
        dQ_dh_up = 0.1  # 
        dQ_dh_down = 0.0  # 
        
        return dQ_dh_up, dQ_dh_down
    
    def set_running_state(self, is_running: bool):
        """"""
        self.is_running = is_running
    
    def get_current_head(self) -> float:
        """"""
        return self.current_head
    
    def __repr__(self) -> str:
        state = "ON" if self.is_running else "OFF"
        return (f"PumpStationSimplified(position={self.position}m, "
                f"Q_rated={self.rated_flow}m³/s, Q_current={self.current_flow:.1f}m³/s, "
                f"H_rated={self.rated_head}m, H_current={self.current_head:.2f}m, state={state})")


class PumpStationAdvanced(HydraulicStructure):
    """
    
    
    1.  H = f(Q)
    2. 
    3. 
    4. 
    
    
    - H_pump = a - b·Q - c·Q²
    - H_required = H_static + k·Q²
    - H_pump(Q) = H_required(Q)
    
    
    - 
    - 
    - 
    """
    
    def __init__(self, position: float, width: float,
                 rated_flow: float = 30.0,
                 rated_head: float = 5.0,
                 shutoff_head: Optional[float] = None,
                 friction_coef: float = 0.0001,
                 min_suction_head: float = 2.0,
                 g: float = 9.81):
        """
        Args:
            position:  (m)
            width:  (m)
            rated_flow:  (m³/s)
            rated_head:  (m)
            shutoff_head:  (m)1.2
            friction_coef: 
            min_suction_head:  (m)
            g:  (m/s²)
        """
        super().__init__(position, width, g)
        self.rated_flow = rated_flow
        self.rated_head = rated_head
        self.min_suction_head = min_suction_head
        self.friction_coef = friction_coef
        
        # Q=0
        if shutoff_head is None:
            self.shutoff_head = rated_head * 1.2
        else:
            self.shutoff_head = shutoff_head
        
        # 
        # H = a - b·Q - c·Q²
        # 
        #   Q = 0: H = shutoff_head
        #   Q = Q_rated: H = H_rated
        # Q = 1.5*Q_ratedH = 0.5*H_rated ()
        
        self.a = self.shutoff_head
        
        #  b  c
        # H_rated = a - b·Q_rated - c·Q_rated²
        # 0.5·H_rated = a - b·(1.5·Q_rated) - c·(1.5·Q_rated)²
        
        Q_r = rated_flow
        H_r = rated_head
        a = self.shutoff_head
        
        # 
        # H_r = a - b·Q_r - c·Q_r²  ... (1)
        # 0.5·H_r = a - b·1.5·Q_r - c·2.25·Q_r²  ... (2)
        # 
        # (1) - (2): 0.5·H_r = b·0.5·Q_r + c·1.25·Q_r²
        # → b·Q_r + 2.5·c·Q_r² = H_r
        # 
        # (1): b = (a - H_r - c·Q_r²) / Q_r
        # : (a - H_r - c·Q_r²) + 2.5·c·Q_r² = H_r
        # → a - H_r + 1.5·c·Q_r² = H_r
        # → c = (2·H_r - a) / (1.5·Q_r²)
        
        self.c = (2 * H_r - a) / (1.5 * Q_r**2)
        self.b = (a - H_r - self.c * Q_r**2) / Q_r
        
        # 
        self.is_running = True
        self.current_head = rated_head
        self.current_flow = rated_flow
        
        print(f": a={self.a:.3f}, b={self.b:.5f}, c={self.c:.7f}")
    
    def calculate_pump_head(self, Q: float) -> float:
        """
        
        H = a - b·Q - c·Q²
        """
        H = self.a - self.b * Q - self.c * Q**2
        return max(0.0, H)
    
    def calculate_required_head(self, h_upstream: float, h_downstream: float,
                               z_upstream: float, z_downstream: float, Q: float) -> float:
        """
        
        H_required = (z_down + h_down) - (z_up + h_up) + k·Q²
        """
        H_static = (z_downstream + h_downstream) - (z_upstream + h_upstream)
        H_friction = self.friction_coef * Q**2
        return H_static + H_friction
    
    def calculate_discharge(self, h_upstream: float, h_downstream: float,
                          t: Optional[float] = None, 
                          z_upstream: Optional[float] = None,
                          z_downstream: Optional[float] = None) -> tuple:
        """
        
        
        H_pump(Q) = H_required(Q)
        
        Args:
            h_upstream:  (m)
            h_downstream:  (m)
            t:  (s)
            z_upstream:  (m)
            z_downstream:  (m)
        
        Returns:
            (discharge, flow_type):  (m³/s) 
        """
        if not self.is_running:
            self.current_flow = 0.0
            self.current_head = 0.0
            return 0.0, 'pump_off'
        
        # 
        if h_upstream < 0.1:
            self.current_flow = 0.0
            self.current_head = 0.0
            return 0.0, 'insufficient_water'
        
        # 
        if z_upstream is None or z_downstream is None:
            # 
            self.current_flow = self.rated_flow
            self.current_head = self.rated_head
            return self.rated_flow, 'rated'
        
        # 
        Q = self.rated_flow  # 
        max_iterations = 20
        tolerance = 0.001
        
        for iteration in range(max_iterations):
            # 
            H_pump = self.calculate_pump_head(Q)
            
            # 
            H_required = self.calculate_required_head(
                h_upstream, h_downstream,
                z_upstream, z_downstream, Q
            )
            
            # 
            residual = H_pump - H_required
            
            if abs(residual) < tolerance:
                # 
                break
            
            # 
            dH_pump_dQ = -self.b - 2 * self.c * Q
            dH_required_dQ = 2 * self.friction_coef * Q
            dH_dQ = dH_pump_dQ - dH_required_dQ
            
            if abs(dH_dQ) < 1e-6:
                # 
                break
            
            # 
            Q_new = Q - residual / dH_dQ
            
            # 
            Q_new = max(0.0, min(Q_new, 2.0 * self.rated_flow))
            
            Q = Q_new
        
        # 
        self.current_flow = Q
        self.current_head = self.calculate_pump_head(Q)
        
        # 
        if Q <= self.rated_flow * 0.9:
            flow_type = 'low_flow'
        elif Q <= self.rated_flow * 1.1:
            flow_type = 'rated'
        else:
            flow_type = 'overload'
        
        return Q, flow_type
    
    def calculate_discharge_derivatives(self, h_upstream: float, h_downstream: float,
                                       t: Optional[float] = None) -> tuple:
        """
        
        """
        if not self.is_running or h_upstream < 0.1:
            return 0.0, 0.0
        
        # 
        dQ_dh_up = 0.5
        dQ_dh_down = 0.0
        
        return dQ_dh_up, dQ_dh_down
    
    def set_running_state(self, is_running: bool):
        """"""
        self.is_running = is_running
    
    def get_current_head(self) -> float:
        """"""
        return self.current_head
    
    def get_pump_curve_data(self, n_points: int = 50) -> tuple:
        """
        
        
        Returns:
            (Q_array, H_array): 
        """
        Q_array = np.linspace(0, 1.5 * self.rated_flow, n_points)
        H_array = np.array([self.calculate_pump_head(Q) for Q in Q_array])
        return Q_array, H_array
    
    def __repr__(self) -> str:
        state = "ON" if self.is_running else "OFF"
        return (f"PumpStationAdvanced(position={self.position}m, "
                f"Q_rated={self.rated_flow}m³/s, Q_current={self.current_flow:.1f}m³/s, "
                f"H_shutoff={self.shutoff_head:.2f}m, H_current={self.current_head:.2f}m, state={state})")
