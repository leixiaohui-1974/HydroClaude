"""
Bridge Hydraulic Model

This module implements bridge hydraulics based on:
- FHWA HDS 1 (Hydraulic Design of Safe Bridges)
- Yarnell equation for backwater
- USGS methods for bridge scour
- Momentum equation for pressure flow

Supports:
- Multiple pier configurations
- Normal bridge flow and pressure flow
- Contraction and expansion losses
- Skewed bridges
- Different pier shapes
"""

import numpy as np
from typing import Tuple, Literal, Optional, List
from dataclasses import dataclass


@dataclass
class Pier:
    """
    Bridge pier configuration

    Attributes
    ----------
    shape : str
        Pier shape: 'circular', 'rectangular', 'streamlined'
    width : float
        Pier width perpendicular to flow (m)
    length : float
        Pier length parallel to flow (m)
    count : int
        Number of piers
    """
    shape: Literal['circular', 'rectangular', 'streamlined']
    width: float
    length: Optional[float] = None  # For rectangular piers
    count: int = 1

    def __post_init__(self):
        """Validate pier parameters"""
        if self.width <= 0:
            raise ValueError("Pier width must be positive")
        if self.count < 0:
            raise ValueError("Pier count must be non-negative")
        if self.shape == 'rectangular' and self.length is None:
            raise ValueError("Rectangular pier requires length")

    def get_blockage_area(self) -> float:
        """
        Calculate total blockage area of all piers

        Returns
        -------
        float
            Total projected area (m²) - assumes constant depth
        """
        if self.shape == 'circular':
            return self.count * self.width  # Width is diameter for circular
        elif self.shape == 'rectangular':
            return self.count * self.width
        elif self.shape == 'streamlined':
            # Streamlined piers have ~0.8x blockage of rectangular
            return self.count * self.width * 0.8
        return 0.0


@dataclass
class BridgeGeometry:
    """
    Bridge geometry parameters

    Attributes
    ----------
    position : float
        Bridge position along channel (m)
    bridge_width : float
        Clear bridge opening width (m)
    deck_elevation : float
        Bridge deck bottom elevation (m)
    piers : Pier
        Pier configuration
    abutment_type : str
        'vertical' or 'sloped'
    skew_angle : float
        Bridge skew angle (degrees, 0 = perpendicular)
    contraction_coef : float
        Contraction coefficient (default 0.9)
    expansion_coef : float
        Expansion coefficient (default 0.5)
    """
    position: float
    bridge_width: float
    deck_elevation: float
    piers: Pier
    abutment_type: Literal['vertical', 'sloped'] = 'vertical'
    skew_angle: float = 0.0
    contraction_coef: float = 0.9
    expansion_coef: float = 0.5

    def __post_init__(self):
        """Validate geometry"""
        if self.bridge_width <= 0:
            raise ValueError("Bridge width must be positive")
        if not 0 <= abs(self.skew_angle) <= 45:
            raise ValueError("Skew angle should be between -45° and 45°")

    def get_effective_width(self) -> float:
        """
        Calculate effective bridge width accounting for skew

        Returns
        -------
        float
            Effective width (m)
        """
        if self.skew_angle == 0:
            return self.bridge_width
        # For skewed bridges, effective width increases
        theta_rad = np.radians(abs(self.skew_angle))
        return self.bridge_width / np.cos(theta_rad)

    def get_net_width(self, depth: float) -> float:
        """
        Calculate net bridge opening width (minus pier blockage)

        Parameters
        ----------
        depth : float
            Water depth at bridge (m)

        Returns
        -------
        float
            Net width (m)
        """
        # Total pier blockage width
        if self.piers.shape == 'circular':
            pier_blockage = self.piers.count * self.piers.width
        else:
            pier_blockage = self.piers.count * self.piers.width

        net_width = self.bridge_width - pier_blockage
        return max(net_width, 0.1)  # Ensure positive width


class Bridge:
    """
    Bridge hydraulic calculation class

    Implements methods from FHWA HDS 1 and Yarnell (1934) for
    bridge backwater and contraction effects.

    Parameters
    ----------
    geometry : BridgeGeometry
        Bridge geometry parameters
    approach_width : float
        Channel width upstream of bridge (m)
    approach_manning_n : float
        Manning's n for approach channel
    bridge_manning_n : float
        Manning's n for bridge opening

    Examples
    --------
    >>> piers = Pier(shape='circular', width=1.0, count=3)
    >>> geom = BridgeGeometry(
    ...     position=200.0,
    ...     bridge_width=20.0,
    ...     deck_elevation=15.0,
    ...     piers=piers
    ... )
    >>> bridge = Bridge(geom, approach_width=30.0)
    >>> h_up, h_down = bridge.compute_water_surface(Q=100.0, h_normal=5.0)
    """

    def __init__(self,
                 geometry: BridgeGeometry,
                 approach_width: float,
                 approach_manning_n: float = 0.030,
                 bridge_manning_n: float = 0.013):

        self.geom = geometry
        self.approach_width = approach_width
        self.n_approach = approach_manning_n
        self.n_bridge = bridge_manning_n

        # Physical constants
        self.g = 9.81

        # Pier shape coefficients for Yarnell equation
        self._pier_k_values = {
            'circular': 0.90,
            'rectangular': 1.25,
            'streamlined': 0.80
        }

    def compute_backwater(self,
                         Q: float,
                         h_normal: float,
                         approach_velocity: Optional[float] = None) -> Tuple[float, float, str]:
        """
        Compute bridge backwater effect using Yarnell equation

        Parameters
        ----------
        Q : float
            Discharge (m³/s)
        h_normal : float
            Normal depth without bridge (m)
        approach_velocity : float, optional
            Approach velocity (m/s). If None, computed from Q and geometry

        Returns
        -------
        h_upstream : float
            Water depth upstream of bridge (m)
        h_bridge : float
            Water depth at bridge opening (m)
        flow_type : str
            'free' or 'pressure'

        Notes
        -----
        Yarnell equation (1934):
        Δh = K * (V²/(2g)) * (α + 10*V²/h_b - 0.6*(a/A_1 + 15*α⁴))

        where:
        - K: Pier shape coefficient
        - V: Approach velocity
        - α: Ratio of pier area to unobstructed area
        - a: Pier blockage area
        - A_1: Unobstructed area at bridge
        """
        # Compute approach velocity if not provided
        if approach_velocity is None:
            A_approach = self.approach_width * h_normal
            approach_velocity = Q / A_approach if A_approach > 0 else 0.0

        # Check if pressure flow (water approaches deck elevation)
        # Conservative check: if normal depth is within 80% of deck height
        deck_height_above_bed = self.geom.deck_elevation
        is_pressure_flow = h_normal > (deck_height_above_bed * 0.8)

        if is_pressure_flow:
            # Pressure flow - use momentum equation
            return self._compute_pressure_flow(Q, h_normal)

        # Free flow - use Yarnell equation
        return self._compute_free_flow_yarnell(Q, h_normal, approach_velocity)

    def _compute_free_flow_yarnell(self,
                                   Q: float,
                                   h_normal: float,
                                   V_approach: float) -> Tuple[float, float, str]:
        """
        Compute free flow backwater using Yarnell equation

        Returns
        -------
        h_upstream : float
            Upstream depth (m)
        h_bridge : float
            Depth at bridge (m)
        flow_type : str
            'free'
        """
        # Pier shape coefficient
        K = self._pier_k_values.get(self.geom.piers.shape, 1.0)

        # Bridge opening area (unobstructed)
        net_width = self.geom.get_net_width(h_normal)
        A_bridge = net_width * h_normal

        # Velocity at bridge (higher than approach due to contraction)
        if A_bridge > 0:
            V_bridge = Q / A_bridge
        else:
            V_bridge = V_approach

        # Pier blockage ratio
        a = self.geom.piers.get_blockage_area() * h_normal  # Total blockage area
        A_1 = self.geom.bridge_width * h_normal  # Total bridge area

        if A_1 > 0:
            alpha = a / A_1  # Blockage ratio
        else:
            alpha = 0.0

        # Yarnell equation terms - uses velocity at bridge, not approach
        V_head = V_bridge**2 / (2 * self.g)

        # Backwater height using Yarnell (1934) equation plus contraction loss:
        # Δh = K * (V²/2g) * [α + 10(V²/2g)/h - 0.6(a/A + 15α⁴)]
        # Plus contraction loss from approach to bridge
        if h_normal > 0:
            term1 = alpha
            term2 = 10 * V_head / h_normal  # Uses velocity head, not V²
            term3 = 0.6 * (a/A_1 + 15 * alpha**4) if A_1 > 0 else 0.0

            delta_h_yarnell = K * V_head * (term1 + term2 - term3)

            # Add contraction/entrance loss based on FHWA HDS-1
            # h_c = K_entrance * V_bridge²/(2g) where K varies with contraction severity
            V_approach_head = V_approach**2 / (2 * self.g)
            contraction_ratio = (net_width / self.approach_width) if self.approach_width > 0 else 1.0

            # K_entrance varies from 0.5 (mild) to 1.0 (severe contraction)
            # More severe contraction -> higher loss
            # Using conservative FHWA HDS-1 values for design
            K_entrance = 0.5 + 0.5 * (1.0 - contraction_ratio)
            delta_h_contraction = K_entrance * V_head

            # Total backwater (with conservative design practice multiplier)
            delta_h_total = delta_h_yarnell + delta_h_contraction

            # Apply design safety factor for uncertainty in pier drag, turbulence, etc.
            # Typical practice adds 30-50% for design conservatism
            safety_factor = 1.4
            delta_h = safety_factor * delta_h_total
        else:
            delta_h = 0.0

        # Ensure positive backwater
        delta_h = max(delta_h, 0.0)

        # Upstream depth
        h_upstream = h_normal + delta_h

        # Depth at bridge - for free flow, approximately equal to normal depth
        # The backwater is upstream of the bridge
        h_bridge = h_normal

        return h_upstream, h_bridge, 'free'

    def _compute_pressure_flow(self,
                               Q: float,
                               h_normal: float) -> Tuple[float, float, str]:
        """
        Compute pressure flow (submerged bridge deck) using orifice equation

        Returns
        -------
        h_upstream : float
            Upstream depth (m)
        h_bridge : float
            Depth at bridge (deck height)
        flow_type : str
            'pressure'
        """
        # Bridge acts like orifice when deck is submerged
        h_bridge = self.geom.deck_elevation

        # Orifice area (under deck)
        A_orifice = self.geom.get_net_width(h_bridge) * h_bridge

        # Orifice equation: Q = Cd * A * sqrt(2*g*ΔH)
        Cd = 0.8  # Discharge coefficient for submerged bridge

        if A_orifice > 0 and Q > 0:
            # Required head difference across orifice
            # Q = Cd * A * sqrt(2*g*ΔH), so ΔH = (Q/(Cd*A))^2 / (2*g)
            V_orifice = Q / A_orifice
            delta_H = V_orifice**2 / (2 * self.g * Cd**2)
            # Upstream depth is downstream depth plus head loss
            h_upstream = h_normal + delta_H
        else:
            h_upstream = h_normal * 1.2  # 20% backwater

        return h_upstream, h_bridge, 'pressure'

    def compute_scour_depth(self,
                           Q: float,
                           h_bridge: float,
                           pier_width: float,
                           d50: float = 0.001) -> float:
        """
        Estimate pier scour depth using CSU equation (HEC-18)

        Parameters
        ----------
        Q : float
            Discharge (m³/s)
        h_bridge : float
            Flow depth at bridge (m)
        pier_width : float
            Pier width (m)
        d50 : float
            Median sediment size (m), default 1mm

        Returns
        -------
        scour_depth : float
            Estimated scour depth below bed (m)

        Notes
        -----
        CSU equation (Colorado State University):
        y_s / h = 2.0 * K_1 * K_2 * K_3 * (a/h)^0.65 * Fr^0.43
        """
        # Velocity at bridge
        A_bridge = self.geom.get_net_width(h_bridge) * h_bridge
        V = Q / A_bridge if A_bridge > 0 else 0.0

        # Froude number
        Fr = V / np.sqrt(self.g * h_bridge) if h_bridge > 0 else 0.0

        # Correction factors
        K_1 = 1.0  # Pier shape (1.0 for circular, 1.1 for rectangular)
        if self.geom.piers.shape == 'rectangular':
            K_1 = 1.1
        elif self.geom.piers.shape == 'streamlined':
            K_1 = 0.9

        K_2 = 1.0  # Flow angle (1.0 for 0°, increases with angle)
        theta_rad = np.radians(abs(self.geom.skew_angle))
        K_2 = (np.cos(theta_rad) + (self.geom.piers.length/pier_width) * np.sin(theta_rad))**0.65 \
              if self.geom.piers.length else 1.0

        K_3 = 1.1  # Bed condition (1.1 for clear water scour)

        # CSU equation
        if h_bridge > 0:
            y_s = 2.0 * K_1 * K_2 * K_3 * (pier_width/h_bridge)**0.65 * Fr**0.43 * h_bridge
        else:
            y_s = 0.0

        return y_s

    def get_total_headloss(self,
                          Q: float,
                          h_upstream: float,
                          h_downstream: float) -> float:
        """
        Calculate total head loss through bridge

        Parameters
        ----------
        Q : float
            Discharge (m³/s)
        h_upstream : float
            Upstream depth (m)
        h_downstream : float
            Downstream depth (m)

        Returns
        -------
        h_loss : float
            Total head loss (m)

        Notes
        -----
        Includes:
        - Contraction loss
        - Friction loss in bridge
        - Expansion loss
        """
        # Velocities
        A_up = self.approach_width * h_upstream
        A_bridge = self.geom.get_net_width((h_upstream + h_downstream)/2) * \
                   (h_upstream + h_downstream) / 2
        A_down = self.approach_width * h_downstream

        V_up = Q / A_up if A_up > 0 else 0.0
        V_bridge = Q / A_bridge if A_bridge > 0 else 0.0
        V_down = Q / A_down if A_down > 0 else 0.0

        # Contraction loss
        h_contraction = self.geom.contraction_coef * (V_bridge**2 - V_up**2) / (2 * self.g)
        h_contraction = abs(h_contraction)

        # Friction loss (approximate - assuming short bridge length)
        # For typical highway bridges, friction loss is small
        h_friction = 0.1 * V_bridge**2 / (2 * self.g)

        # Expansion loss
        h_expansion = self.geom.expansion_coef * (V_bridge**2 - V_down**2) / (2 * self.g)
        h_expansion = abs(h_expansion)

        return h_contraction + h_friction + h_expansion

    def get_derivatives(self,
                       Q: float,
                       h_upstream: float,
                       h_downstream: float) -> Tuple[float, float]:
        """
        Compute flow derivatives for Newton solver

        Parameters
        ----------
        Q : float
            Discharge (m³/s)
        h_upstream : float
            Upstream depth (m)
        h_downstream : float
            Downstream depth (m)

        Returns
        -------
        dQ_dh_up : float
            ∂Q/∂h_upstream
        dQ_dh_down : float
            ∂Q/∂h_downstream
        """
        delta_h = 0.001

        # This is a simplification - in reality, bridge doesn't directly control Q
        # Q is determined by upstream conditions
        # Derivatives would relate to the effect on water surface

        # For now, return finite approximations
        # In practice, bridge affects h, not Q
        return 0.0, 0.0  # Bridge doesn't control discharge

    def __repr__(self) -> str:
        """String representation"""
        return (f"Bridge(position={self.geom.position}, "
                f"width={self.geom.bridge_width}, "
                f"piers={self.geom.piers.count}×{self.geom.piers.shape})")


# ============================================================================
# Convenience functions
# ============================================================================

def create_simple_bridge(position: float,
                        bridge_width: float,
                        deck_elevation: float,
                        pier_count: int = 2,
                        pier_width: float = 1.0,
                        approach_width: float = None,
                        skew_angle: float = 0.0) -> Bridge:
    """
    Create a simple bridge with circular piers

    Parameters
    ----------
    position : float
        Bridge position (m)
    bridge_width : float
        Clear opening width (m)
    deck_elevation : float
        Deck bottom elevation (m)
    pier_count : int
        Number of piers
    pier_width : float
        Pier diameter (m)
    approach_width : float
        Channel width upstream (m). If None, assumes = bridge_width * 1.2
    skew_angle : float
        Bridge skew angle in degrees (default 0.0)

    Returns
    -------
    Bridge
        Configured bridge object

    Examples
    --------
    >>> bridge = create_simple_bridge(
    ...     position=200.0,
    ...     bridge_width=20.0,
    ...     deck_elevation=15.0,
    ...     pier_count=3,
    ...     pier_width=1.0
    ... )
    """
    if approach_width is None:
        approach_width = bridge_width * 1.2

    piers = Pier(shape='circular', width=pier_width, count=pier_count)

    geometry = BridgeGeometry(
        position=position,
        bridge_width=bridge_width,
        deck_elevation=deck_elevation,
        piers=piers,
        skew_angle=skew_angle
    )

    return Bridge(geometry, approach_width=approach_width)


def create_rectangular_pier_bridge(position: float,
                                   bridge_width: float,
                                   deck_elevation: float,
                                   pier_count: int,
                                   pier_width: float,
                                   pier_length: float,
                                   approach_width: float = None,
                                   skew_angle: float = 0.0) -> Bridge:
    """
    Create bridge with rectangular piers

    Parameters
    ----------
    position : float
        Bridge position (m)
    bridge_width : float
        Clear opening width (m)
    deck_elevation : float
        Deck bottom elevation (m)
    pier_count : int
        Number of piers
    pier_width : float
        Pier width perpendicular to flow (m)
    pier_length : float
        Pier length parallel to flow (m)
    approach_width : float
        Channel width upstream (m)
    skew_angle : float
        Bridge skew angle (degrees)

    Returns
    -------
    Bridge
        Configured bridge object
    """
    if approach_width is None:
        approach_width = bridge_width * 1.2

    piers = Pier(
        shape='rectangular',
        width=pier_width,
        length=pier_length,
        count=pier_count
    )

    geometry = BridgeGeometry(
        position=position,
        bridge_width=bridge_width,
        deck_elevation=deck_elevation,
        piers=piers,
        skew_angle=skew_angle
    )

    return Bridge(geometry, approach_width=approach_width)
