"""
Culvert Hydraulic Model

This module implements culvert hydraulics based on FHWA HDS 5
(Hydraulic Design of Highway Culverts, 3rd Edition, 2012).

Supports:
- Circular, rectangular, and arch cross-sections
- Inlet control (unsubmerged and submerged)
- Outlet control (energy equation method)
- Various inlet types with corresponding discharge coefficients
"""

import numpy as np
from typing import Tuple, Literal, Optional
from dataclasses import dataclass


@dataclass
class CulvertGeometry:
    """
    Culvert geometry parameters

    Attributes
    ----------
    shape : str
        Cross-section shape: 'circular', 'rectangular', or 'arch'
    diameter : float, optional
        Diameter for circular culverts (m)
    width : float, optional
        Width for rectangular/arch culverts (m)
    height : float, optional
        Height for rectangular/arch culverts (m)
    length : float
        Culvert length (m)
    slope : float
        Culvert slope (dimensionless, default 0.001)
    invert_elevation : float
        Inlet invert elevation (m, default 0.0)
    """
    shape: Literal['circular', 'rectangular', 'arch']
    length: float
    diameter: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None
    slope: float = 0.001
    invert_elevation: float = 0.0

    def __post_init__(self):
        """Validate geometry parameters"""
        if self.shape == 'circular':
            if self.diameter is None or self.diameter <= 0:
                raise ValueError("Circular culvert requires positive diameter")
        elif self.shape in ['rectangular', 'arch']:
            if self.width is None or self.width <= 0:
                raise ValueError(f"{self.shape} culvert requires positive width")
            if self.height is None or self.height <= 0:
                raise ValueError(f"{self.shape} culvert requires positive height")

        if self.length <= 0:
            raise ValueError("Culvert length must be positive")

    def area(self) -> float:
        """
        Calculate cross-sectional area

        Returns
        -------
        float
            Cross-sectional area (m²)
        """
        if self.shape == 'circular':
            return np.pi * (self.diameter / 2) ** 2
        elif self.shape == 'rectangular':
            return self.width * self.height
        elif self.shape == 'arch':
            # Simplified: semicircle + rectangle
            return (np.pi / 2) * (self.width / 2) ** 2 + \
                   self.width * (self.height - self.width / 2)

    def hydraulic_radius(self, depth: float) -> float:
        """
        Calculate hydraulic radius for given water depth

        Parameters
        ----------
        depth : float
            Water depth (m)

        Returns
        -------
        float
            Hydraulic radius (m)
        """
        if self.shape == 'circular':
            if depth >= self.diameter:
                # Full pipe flow
                return self.diameter / 4
            else:
                # Partially full
                theta = 2 * np.arccos(1 - 2 * depth / self.diameter)
                A = (self.diameter ** 2 / 8) * (theta - np.sin(theta))
                P = self.diameter * theta / 2
                return A / P if P > 0 else 0.0

        elif self.shape == 'rectangular':
            depth_actual = min(depth, self.height)
            A = self.width * depth_actual
            P = self.width + 2 * depth_actual
            return A / P if P > 0 else 0.0

        elif self.shape == 'arch':
            # Simplified calculation
            depth_actual = min(depth, self.height)
            A = self.width * depth_actual  # Approximate
            P = self.width + 2 * depth_actual
            return A / P if P > 0 else 0.0

    def get_characteristic_height(self) -> float:
        """Get characteristic height (diameter or height)"""
        if self.shape == 'circular':
            return self.diameter
        else:
            return self.height


class Culvert:
    """
    Culvert hydraulic calculation class

    Implements FHWA HDS 5 methods for both inlet control
    and outlet control conditions.

    Parameters
    ----------
    position : float
        Position along channel (m)
    geometry : CulvertGeometry
        Culvert geometry parameters
    manning_n : float
        Manning's roughness coefficient (default 0.013)
    inlet_type : str
        Inlet type: 'square_edge', 'groove_end', 'groove_headwall', 'beveled'
    entrance_loss_coef : float
        Entrance loss coefficient Ke (default 0.5)
    exit_loss_coef : float
        Exit loss coefficient (default 1.0)

    Examples
    --------
    >>> geom = CulvertGeometry(shape='circular', diameter=1.2, length=30.0)
    >>> culvert = Culvert(position=100.0, geometry=geom)
    >>> Q, control = culvert.compute_discharge(h_upstream=1.5, h_downstream=0.6)
    >>> print(f"Flow: {Q:.2f} m³/s, Control: {control}")
    """

    def __init__(self,
                 position: float,
                 geometry: CulvertGeometry,
                 manning_n: float = 0.013,
                 inlet_type: Literal['square_edge', 'groove_end',
                                     'groove_headwall', 'beveled'] = 'square_edge',
                 entrance_loss_coef: float = 0.5,
                 exit_loss_coef: float = 1.0):

        self.position = position
        self.geom = geometry
        self.n = manning_n
        self.inlet_type = inlet_type
        self.K_e = entrance_loss_coef
        self.K_exit = exit_loss_coef

        # Get discharge coefficient based on inlet type
        self.C_d = self._get_discharge_coefficient()

        # Physical constant
        self.g = 9.81

    def _get_discharge_coefficient(self) -> float:
        """
        Get discharge coefficient based on inlet type

        Returns
        -------
        float
            Discharge coefficient Cd (dimensionless)

        References
        ----------
        FHWA HDS 5, Table 5-2
        """
        coef_map = {
            'square_edge': 0.47,
            'groove_end': 0.52,
            'groove_headwall': 0.53,
            'beveled': 0.57
        }
        return coef_map.get(self.inlet_type, 0.50)

    def compute_discharge(self,
                         h_upstream: float,
                         h_downstream: float) -> Tuple[float, str]:
        """
        Compute culvert discharge

        Calculates flow under both inlet control and outlet control,
        returning the more restrictive condition.

        Parameters
        ----------
        h_upstream : float
            Upstream water depth relative to inlet invert (m)
        h_downstream : float
            Downstream water depth relative to outlet invert (m)

        Returns
        -------
        Q : float
            Discharge (m³/s)
        control_type : str
            'inlet' or 'outlet'

        Notes
        -----
        The method computes discharge for both control conditions
        and selects the one requiring higher upstream head (more restrictive).
        """
        # Compute inlet control
        Q_inlet, H_inlet = self._inlet_control(h_upstream)

        # Compute outlet control
        Q_outlet, H_outlet = self._outlet_control(h_upstream, h_downstream)

        # Select more restrictive condition (higher required head)
        if H_inlet >= H_outlet:
            return Q_inlet, 'inlet'
        else:
            return Q_outlet, 'outlet'

    def _inlet_control(self, h_upstream: float) -> Tuple[float, float]:
        """
        Inlet control calculation

        Parameters
        ----------
        h_upstream : float
            Upstream water depth (m)

        Returns
        -------
        Q : float
            Discharge (m³/s)
        H : float
            Required upstream head (m)

        Notes
        -----
        Inlet control occurs when the outlet is unsubmerged.
        Flow is calculated using orifice equation:
        Q = Cd * A * sqrt(2*g*H)

        For unsubmerged: H is measured from invert
        For submerged: H is measured to centerline
        """
        A = self.geom.area()
        D = self.geom.get_characteristic_height()

        # Absolute water surface elevation
        h_abs = h_upstream + self.geom.invert_elevation

        # Unsubmerged condition: Headwater < 1.2*D (FHWA criterion)
        if h_upstream < 1.2 * D:
            # Unsubmerged inlet control
            # Use full depth as driving head
            H = h_upstream
            if H <= 0:
                return 0.0, h_upstream

            Q = self.C_d * A * np.sqrt(2 * self.g * H)

        else:
            # Submerged inlet control
            # Head measured from centerline (FHWA method)
            H = h_upstream - D / 2
            if H <= 0:
                return 0.0, h_upstream

            Q = self.C_d * A * np.sqrt(2 * self.g * H)

        return Q, h_upstream

    def _outlet_control(self,
                       h_upstream: float,
                       h_downstream: float) -> Tuple[float, float]:
        """
        Outlet control calculation using energy equation

        Parameters
        ----------
        h_upstream : float
            Upstream water depth (m)
        h_downstream : float
            Downstream water depth (m)

        Returns
        -------
        Q : float
            Discharge (m³/s)
        H_required : float
            Required upstream head (m)

        Notes
        -----
        Energy equation:
        H_upstream = H_downstream + h_f + h_e + h_exit

        where:
        - h_f: friction loss = (n²*L*V²)/(R_h^(4/3))
        - h_e: entrance loss = K_e * V²/(2g)
        - h_exit: exit loss = K_exit * V²/(2g)
        """
        A = self.geom.area()
        L = self.geom.length
        S_0 = self.geom.slope
        D = self.geom.get_characteristic_height()

        # Initial guess for discharge
        Q_guess = 0.5

        # Iterative solution
        for iteration in range(100):
            V = Q_guess / A

            # Hydraulic radius (assume full or nearly full flow)
            R_h = self.geom.hydraulic_radius(D)

            # Friction loss (Manning's equation)
            if R_h > 0:
                h_f = (self.n ** 2 * L * V ** 2) / (R_h ** (4/3))
            else:
                h_f = 0.0

            # Entrance loss
            h_e = self.K_e * V ** 2 / (2 * self.g)

            # Exit loss
            h_exit = self.K_exit * V ** 2 / (2 * self.g)

            # Required upstream head
            H_required = h_downstream + h_f + h_e + h_exit - S_0 * L

            # Check convergence
            error = abs(H_required - h_upstream)
            if error < 0.001:
                return Q_guess, H_required

            # Update discharge guess
            if H_required > h_upstream:
                # Need less flow
                Q_guess *= 0.95
            else:
                # Can have more flow
                Q_guess *= 1.05

            # Prevent negative or zero flow
            if Q_guess < 1e-6:
                return 0.0, h_upstream

        # If not converged, return current estimate
        return Q_guess, H_required

    def compute_headloss(self, Q: float, h_downstream: float) -> float:
        """
        Compute total head loss through culvert

        Parameters
        ----------
        Q : float
            Discharge (m³/s)
        h_downstream : float
            Downstream water depth (m)

        Returns
        -------
        float
            Total head loss (m)

        Notes
        -----
        Total head loss includes:
        - Friction loss in barrel
        - Entrance loss
        - Exit loss
        """
        if Q <= 0:
            return 0.0

        A = self.geom.area()
        V = Q / A
        L = self.geom.length
        D = self.geom.get_characteristic_height()
        R_h = self.geom.hydraulic_radius(D)

        # Friction loss
        if R_h > 0:
            h_f = (self.n ** 2 * L * V ** 2) / (R_h ** (4/3))
        else:
            h_f = 0.0

        # Entrance loss
        h_e = self.K_e * V ** 2 / (2 * self.g)

        # Exit loss
        h_exit = self.K_exit * V ** 2 / (2 * self.g)

        return h_f + h_e + h_exit

    def get_derivatives(self,
                       Q: float,
                       h_upstream: float,
                       h_downstream: float) -> Tuple[float, float]:
        """
        Compute flow derivatives with respect to water depths

        Used for Newton-Raphson solver in steady-state calculations.

        Parameters
        ----------
        Q : float
            Current discharge (m³/s)
        h_upstream : float
            Upstream water depth (m)
        h_downstream : float
            Downstream water depth (m)

        Returns
        -------
        dQ_dh_up : float
            ∂Q/∂h_upstream
        dQ_dh_down : float
            ∂Q/∂h_downstream

        Notes
        -----
        Uses numerical differentiation with central differences.
        """
        delta_h = 0.001  # Small perturbation

        # Derivative with respect to upstream depth
        Q_plus_up, _ = self.compute_discharge(h_upstream + delta_h, h_downstream)
        Q_minus_up, _ = self.compute_discharge(h_upstream - delta_h, h_downstream)
        dQ_dh_up = (Q_plus_up - Q_minus_up) / (2 * delta_h)

        # Derivative with respect to downstream depth
        Q_plus_down, _ = self.compute_discharge(h_upstream, h_downstream + delta_h)
        Q_minus_down, _ = self.compute_discharge(h_upstream, h_downstream - delta_h)
        dQ_dh_down = (Q_plus_down - Q_minus_down) / (2 * delta_h)

        return dQ_dh_up, dQ_dh_down

    def __repr__(self) -> str:
        """String representation"""
        return (f"Culvert(position={self.position}, "
                f"shape={self.geom.shape}, "
                f"n={self.n}, inlet_type={self.inlet_type})")


# ============================================================================
# Convenience functions
# ============================================================================

def create_circular_culvert(position: float,
                           diameter: float,
                           length: float,
                           manning_n: float = 0.013,
                           inlet_type: str = 'square_edge',
                           slope: float = 0.001) -> Culvert:
    """
    Create a circular culvert

    Parameters
    ----------
    position : float
        Position along channel (m)
    diameter : float
        Culvert diameter (m)
    length : float
        Culvert length (m)
    manning_n : float
        Manning's roughness coefficient
    inlet_type : str
        Inlet type
    slope : float
        Culvert slope

    Returns
    -------
    Culvert
        Configured culvert object

    Examples
    --------
    >>> culvert = create_circular_culvert(
    ...     position=100.0,
    ...     diameter=1.2,
    ...     length=30.0
    ... )
    """
    geom = CulvertGeometry(
        shape='circular',
        diameter=diameter,
        length=length,
        slope=slope
    )
    return Culvert(position, geom, manning_n, inlet_type)


def create_rectangular_culvert(position: float,
                               width: float,
                               height: float,
                               length: float,
                               manning_n: float = 0.013,
                               inlet_type: str = 'square_edge',
                               slope: float = 0.001) -> Culvert:
    """
    Create a rectangular culvert

    Parameters
    ----------
    position : float
        Position along channel (m)
    width : float
        Culvert width (m)
    height : float
        Culvert height (m)
    length : float
        Culvert length (m)
    manning_n : float
        Manning's roughness coefficient
    inlet_type : str
        Inlet type
    slope : float
        Culvert slope

    Returns
    -------
    Culvert
        Configured culvert object

    Examples
    --------
    >>> culvert = create_rectangular_culvert(
    ...     position=100.0,
    ...     width=2.0,
    ...     height=1.5,
    ...     length=40.0
    ... )
    """
    geom = CulvertGeometry(
        shape='rectangular',
        width=width,
        height=height,
        length=length,
        slope=slope
    )
    return Culvert(position, geom, manning_n, inlet_type)


# ============================================================================
# Validation functions
# ============================================================================

def validate_culvert_design(culvert: Culvert,
                           Q_design: float,
                           h_upstream_max: float,
                           h_downstream: float) -> dict:
    """
    Validate culvert design for given flow conditions

    Parameters
    ----------
    culvert : Culvert
        Culvert to validate
    Q_design : float
        Design discharge (m³/s)
    h_upstream_max : float
        Maximum allowable upstream depth (m)
    h_downstream : float
        Downstream water depth (m)

    Returns
    -------
    dict
        Validation results with keys:
        - 'passes': bool
        - 'Q_actual': float
        - 'h_upstream_required': float
        - 'control_type': str
        - 'headloss': float
        - 'velocity': float
        - 'message': str
    """
    # Compute actual discharge
    Q_actual, control_type = culvert.compute_discharge(h_upstream_max, h_downstream)

    # Compute head loss
    headloss = culvert.compute_headloss(Q_actual, h_downstream)

    # Compute velocity
    A = culvert.geom.area()
    velocity = Q_actual / A if A > 0 else 0.0

    # Check if design passes
    passes = Q_actual >= Q_design

    if passes:
        message = f"Design passes: Q={Q_actual:.2f} m³/s >= {Q_design:.2f} m³/s"
    else:
        message = f"Design fails: Q={Q_actual:.2f} m³/s < {Q_design:.2f} m³/s"

    return {
        'passes': passes,
        'Q_actual': Q_actual,
        'h_upstream_required': h_upstream_max,
        'control_type': control_type,
        'headloss': headloss,
        'velocity': velocity,
        'message': message
    }
