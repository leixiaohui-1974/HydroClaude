"""
AGC (Automatic Generation Control) Module

This module implements automatic generation control for multi-unit hydropower plants,
including primary and secondary frequency control.

Key Components:
- Primary Frequency Control: Governor droop response
- Secondary Frequency Control (AGC): PI controller for ACE
- Area Control Error (ACE): ΔP_tie + 10β×Δf
- Economic Dispatch: Optimal load allocation among units

Author: HydroClaude Development Team
Date: 2025-10-22
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class FrequencyControlParams:
    """Parameters for frequency control system."""

    # System parameters
    rated_frequency: float = 50.0  # Hz (or 60.0 for North America)
    frequency_bias_factor: float = 1.0  # β, in MW/0.1Hz (typically 1% of system capacity)

    # AGC PI controller parameters
    Kp_agc: float = 50.0  # Proportional gain for ACE control
    Ki_agc: float = 10.0  # Integral gain for ACE control

    # Limits
    ace_deadband: float = 0.01  # MW, ignore ACE within this band
    max_regulation_rate: float = 5.0  # MW/s, maximum rate of AGC action

    # Tie-line control
    tie_line_scheduled: float = 0.0  # MW, scheduled tie-line flow


class PrimaryFrequencyControl:
    """
    Primary Frequency Control (一次调频)

    Implements the natural frequency response through governor droop.

    Theory:
        ΔP = -K_droop × Δf
        K_droop = P_rated / (droop × f_rated)

    where droop is typically 2-6% (0.02-0.06).
    """

    def __init__(self, unit_capacity: float, droop: float = 0.04):
        """
        Initialize primary frequency control.

        Args:
            unit_capacity: Rated capacity of the unit (MW)
            droop: Speed droop (permanent droop), typically 0.04 (4%)
        """
        self.unit_capacity = unit_capacity
        self.droop = droop

        # Calculate droop gain: ΔP / Δf
        # At 50 Hz with 4% droop: Δf = 2 Hz causes full power change
        self.K_droop = unit_capacity / (droop * 50.0)  # MW/Hz

    def calculate_power_adjustment(self, frequency_deviation: float) -> float:
        """
        Calculate power adjustment based on frequency deviation.

        Args:
            frequency_deviation: Δf in Hz (positive means over-frequency)

        Returns:
            Power adjustment in MW (negative means increase power)
        """
        # Primary control opposes frequency deviation
        # If f > f_rated (positive Δf), reduce power (negative ΔP)
        # If f < f_rated (negative Δf), increase power (positive ΔP)
        delta_P = -self.K_droop * frequency_deviation

        return delta_P


class SecondaryFrequencyControl:
    """
    Secondary Frequency Control (二次调频) - AGC

    Implements AGC using PI control to eliminate steady-state frequency error
    and maintain scheduled tie-line flow.

    Theory:
        ACE = ΔP_tie + 10β×Δf  (in MW)
        u_AGC(t) = Kp×ACE + Ki×∫ACE dt

    where:
        - ACE: Area Control Error
        - ΔP_tie: Tie-line flow deviation (actual - scheduled)
        - β: Frequency bias factor (MW/0.1Hz)
        - Δf: Frequency deviation (Hz)
    """

    def __init__(self, params: FrequencyControlParams):
        """
        Initialize AGC controller.

        Args:
            params: Frequency control parameters
        """
        self.params = params

        # PI controller state
        self.ace_integral = 0.0
        self.prev_time = None

        # Rate limiter state
        self.prev_output = 0.0

        # History for analysis
        self.ace_history = []
        self.output_history = []
        self.time_history = []

    def calculate_ace(self,
                     frequency: float,
                     tie_line_flow: float) -> float:
        """
        Calculate Area Control Error (ACE).

        Args:
            frequency: System frequency in Hz
            tie_line_flow: Actual tie-line flow in MW (positive = export)

        Returns:
            ACE in MW
        """
        # Frequency deviation
        delta_f = frequency - self.params.rated_frequency

        # Tie-line flow deviation
        delta_P_tie = tie_line_flow - self.params.tie_line_scheduled

        # ACE = ΔP_tie + 10β×Δf
        # The factor 10 converts β from MW/0.1Hz to MW/Hz
        ace = delta_P_tie + 10.0 * self.params.frequency_bias_factor * delta_f

        return ace

    def compute_control(self,
                       frequency: float,
                       tie_line_flow: float,
                       current_time: float) -> Tuple[float, float]:
        """
        Compute AGC control signal.

        Args:
            frequency: System frequency in Hz
            tie_line_flow: Actual tie-line flow in MW
            current_time: Current simulation time in seconds

        Returns:
            Tuple of (control_signal in MW, ACE in MW)
        """
        # Calculate ACE
        ace = self.calculate_ace(frequency, tie_line_flow)

        # Apply deadband
        if abs(ace) < self.params.ace_deadband:
            ace_active = 0.0
        else:
            ace_active = ace

        # Initialize time
        if self.prev_time is None:
            self.prev_time = current_time
            dt = 0.0
        else:
            dt = current_time - self.prev_time
            self.prev_time = current_time

        # PI control
        P = self.params.Kp_agc * ace_active

        if dt > 0:
            self.ace_integral += ace_active * dt
        I = self.params.Ki_agc * self.ace_integral

        output_raw = P + I

        # Rate limiter
        if dt > 0:
            max_change = self.params.max_regulation_rate * dt
            delta_output = output_raw - self.prev_output

            if abs(delta_output) > max_change:
                delta_output = np.sign(delta_output) * max_change

            output = self.prev_output + delta_output
        else:
            output = output_raw

        self.prev_output = output

        # Record history
        self.ace_history.append(ace)
        self.output_history.append(output)
        self.time_history.append(current_time)

        # The output is the total power adjustment needed from this area
        # Negative output means reduce generation (frequency too high or exporting too much)
        return output, ace

    def reset(self):
        """Reset controller state."""
        self.ace_integral = 0.0
        self.prev_time = None
        self.prev_output = 0.0
        self.ace_history = []
        self.output_history = []
        self.time_history = []


class MultiUnitCoordinator:
    """
    Multi-Unit Coordinator for Load Distribution

    Coordinates multiple generating units to:
    1. Allocate total power demand optimally (economic dispatch)
    2. Manage unit commitment (on/off scheduling)
    3. Provide spinning reserve

    Theory:
        Economic Dispatch uses equal incremental cost criterion:
        λ = dC₁/dP₁ = dC₂/dP₂ = ... = dCₙ/dPₙ

        For hydropower, we use equal incremental water consumption:
        ∂Q₁/∂P₁ = ∂Q₂/∂P₂ = ... = ∂Qₙ/∂Pₙ
    """

    def __init__(self, unit_capacities: List[float], unit_efficiencies: List[float]):
        """
        Initialize multi-unit coordinator.

        Args:
            unit_capacities: List of unit capacities in MW
            unit_efficiencies: List of unit peak efficiencies (0-1)
        """
        self.n_units = len(unit_capacities)
        self.unit_capacities = np.array(unit_capacities)
        self.unit_efficiencies = np.array(unit_efficiencies)

        # Operating constraints
        self.min_load_fraction = 0.25  # Minimum stable load (25% of capacity)
        self.max_load_fraction = 1.0  # Maximum load (100% of capacity)

    def allocate_load_equal_incremental(self,
                                       total_power: float,
                                       available_units: Optional[List[int]] = None
                                       ) -> Dict[int, float]:
        """
        Allocate load using equal incremental criterion.

        For hydropower with similar units, this approximates to equal loading
        relative to capacity (equal capacity factor).

        Args:
            total_power: Total power demand in MW
            available_units: List of available unit indices (None = all units)

        Returns:
            Dictionary mapping unit index to allocated power (MW)
        """
        if available_units is None:
            available_units = list(range(self.n_units))

        # Calculate total available capacity
        available_capacity = sum(self.unit_capacities[i] for i in available_units)

        if total_power > available_capacity:
            raise ValueError(f"Demand {total_power:.1f} MW exceeds available capacity {available_capacity:.1f} MW")

        # Equal incremental method for identical efficiency curves
        # approximates to proportional loading
        allocation = {}

        # First, check if all units can operate above minimum
        n_available = len(available_units)
        min_total = sum(self.unit_capacities[i] * self.min_load_fraction for i in available_units)

        if total_power < min_total:
            # Need to turn off some units
            # Commit only enough units to satisfy demand
            units_needed = self._select_units_to_commit(total_power, available_units)
            available_units = units_needed
            n_available = len(available_units)

        # Proportional allocation based on capacity
        total_cap = sum(self.unit_capacities[i] for i in available_units)

        for i in available_units:
            fraction = self.unit_capacities[i] / total_cap
            power = total_power * fraction

            # Enforce limits
            power = np.clip(power,
                          self.unit_capacities[i] * self.min_load_fraction,
                          self.unit_capacities[i] * self.max_load_fraction)

            allocation[i] = power

        # Turn off unavailable units
        for i in range(self.n_units):
            if i not in available_units:
                allocation[i] = 0.0

        return allocation

    def _select_units_to_commit(self,
                               demand: float,
                               available_units: List[int]) -> List[int]:
        """
        Select which units to commit to meet demand.

        Strategy: Commit largest units first (better efficiency at partial load).

        Args:
            demand: Power demand in MW
            available_units: List of available unit indices

        Returns:
            List of committed unit indices
        """
        # Sort units by capacity (largest first)
        sorted_units = sorted(available_units,
                            key=lambda i: self.unit_capacities[i],
                            reverse=True)

        committed = []
        cumulative_capacity = 0.0

        for unit_idx in sorted_units:
            committed.append(unit_idx)
            cumulative_capacity += self.unit_capacities[unit_idx]

            # Check if we have enough capacity
            min_power = sum(self.unit_capacities[i] * self.min_load_fraction
                          for i in committed)
            max_power = sum(self.unit_capacities[i] * self.max_load_fraction
                          for i in committed)

            if min_power <= demand <= max_power:
                break

        return committed

    def calculate_system_efficiency(self, allocations: Dict[int, float],
                                    net_heads: List[float]) -> float:
        """
        Calculate overall system efficiency with given load allocation.

        Args:
            allocations: Power allocation for each unit (MW)
            net_heads: Net head for each unit (m)

        Returns:
            System efficiency (0-1)
        """
        total_power = 0.0
        total_water_power = 0.0
        rho = 1000.0  # kg/m³
        g = 9.81  # m/s²

        for i in range(self.n_units):
            if allocations.get(i, 0.0) > 0:
                power = allocations[i]
                head = net_heads[i]

                # Estimate efficiency based on load fraction
                load_fraction = power / self.unit_capacities[i]

                # Simplified efficiency curve (parabolic)
                # Peak efficiency at 90% load
                eta_peak = self.unit_efficiencies[i]
                eta = eta_peak * (1.0 - 0.5 * ((load_fraction - 0.9) / 0.5) ** 2)
                eta = np.clip(eta, 0.5 * eta_peak, eta_peak)

                # Calculate flow
                flow = power * 1e6 / (eta * rho * g * head)  # m³/s

                # Water power
                water_power = rho * g * flow * head / 1e6  # MW

                total_power += power
                total_water_power += water_power

        if total_water_power > 0:
            system_efficiency = total_power / total_water_power
        else:
            system_efficiency = 0.0

        return system_efficiency

    def distribute_agc_signal(self,
                             agc_signal: float,
                             current_allocations: Dict[int, float]
                             ) -> Dict[int, float]:
        """
        Distribute AGC regulation signal among committed units.

        Args:
            agc_signal: Total AGC power adjustment needed (MW)
            current_allocations: Current power allocation for each unit

        Returns:
            Dictionary of power adjustments for each unit
        """
        # Find committed units
        committed_units = [i for i in range(self.n_units)
                         if current_allocations.get(i, 0.0) > 0]

        if not committed_units:
            return {i: 0.0 for i in range(self.n_units)}

        # Distribute proportionally to capacity
        adjustments = {}
        total_capacity = sum(self.unit_capacities[i] for i in committed_units)

        for i in committed_units:
            fraction = self.unit_capacities[i] / total_capacity
            adjustment = agc_signal * fraction

            # Check limits
            new_power = current_allocations[i] + adjustment
            min_power = self.unit_capacities[i] * self.min_load_fraction
            max_power = self.unit_capacities[i] * self.max_load_fraction

            # Limit adjustment to stay within bounds
            if new_power < min_power:
                adjustment = min_power - current_allocations[i]
            elif new_power > max_power:
                adjustment = max_power - current_allocations[i]

            adjustments[i] = adjustment

        # Turn off non-committed units
        for i in range(self.n_units):
            if i not in committed_units:
                adjustments[i] = 0.0

        return adjustments


class IntegratedAGCSystem:
    """
    Integrated AGC System for Multi-Unit Hydropower Plant

    Combines:
    - Primary frequency control (governor droop)
    - Secondary frequency control (AGC)
    - Multi-unit coordination (load allocation)
    """

    def __init__(self,
                 unit_capacities: List[float],
                 unit_efficiencies: List[float],
                 unit_droops: List[float],
                 agc_params: FrequencyControlParams):
        """
        Initialize integrated AGC system.

        Args:
            unit_capacities: List of unit capacities in MW
            unit_efficiencies: List of unit peak efficiencies (0-1)
            unit_droops: List of governor droops for each unit (typically 0.04)
            agc_params: AGC control parameters
        """
        self.n_units = len(unit_capacities)

        # Primary frequency control for each unit
        self.primary_controls = [
            PrimaryFrequencyControl(cap, droop)
            for cap, droop in zip(unit_capacities, unit_droops)
        ]

        # Secondary frequency control (AGC)
        self.agc = SecondaryFrequencyControl(agc_params)

        # Multi-unit coordinator
        self.coordinator = MultiUnitCoordinator(unit_capacities, unit_efficiencies)

        # Current state
        self.current_allocations = {i: 0.0 for i in range(self.n_units)}

    def compute_control(self,
                       frequency: float,
                       tie_line_flow: float,
                       total_demand: float,
                       current_time: float,
                       net_heads: Optional[List[float]] = None
                       ) -> Dict[int, float]:
        """
        Compute control signals for all units.

        Args:
            frequency: System frequency in Hz
            tie_line_flow: Tie-line flow in MW
            total_demand: Total power demand in MW
            current_time: Current time in seconds
            net_heads: Net head for each unit (for efficiency calculation)

        Returns:
            Dictionary of power setpoints for each unit
        """
        # 1. Base load allocation (economic dispatch)
        base_allocations = self.coordinator.allocate_load_equal_incremental(total_demand)

        # 2. Primary frequency control (automatic droop response)
        frequency_deviation = frequency - self.agc.params.rated_frequency
        primary_adjustments = {}

        for i in range(self.n_units):
            if base_allocations.get(i, 0.0) > 0:
                # Only committed units participate in primary control
                primary_adj = self.primary_controls[i].calculate_power_adjustment(frequency_deviation)
                primary_adjustments[i] = primary_adj
            else:
                primary_adjustments[i] = 0.0

        # 3. Secondary frequency control (AGC)
        agc_signal, ace = self.agc.compute_control(frequency, tie_line_flow, current_time)

        # Distribute AGC signal among committed units
        agc_adjustments = self.coordinator.distribute_agc_signal(agc_signal, base_allocations)

        # 4. Combine all control actions
        final_setpoints = {}
        for i in range(self.n_units):
            setpoint = (base_allocations.get(i, 0.0) +
                       primary_adjustments.get(i, 0.0) +
                       agc_adjustments.get(i, 0.0))

            # Enforce limits
            min_power = self.coordinator.unit_capacities[i] * self.coordinator.min_load_fraction
            max_power = self.coordinator.unit_capacities[i] * self.coordinator.max_load_fraction

            if setpoint < min_power / 2:  # Turn off if below 50% of minimum
                setpoint = 0.0
            else:
                setpoint = np.clip(setpoint, min_power, max_power)

            final_setpoints[i] = setpoint

        self.current_allocations = final_setpoints

        return final_setpoints

    def get_system_status(self) -> Dict:
        """
        Get current system status.

        Returns:
            Dictionary with system status information
        """
        total_generation = sum(self.current_allocations.values())
        committed_units = sum(1 for p in self.current_allocations.values() if p > 0)

        if len(self.agc.ace_history) > 0:
            current_ace = self.agc.ace_history[-1]
            current_agc_output = self.agc.output_history[-1]
        else:
            current_ace = 0.0
            current_agc_output = 0.0

        status = {
            'total_generation': total_generation,
            'committed_units': committed_units,
            'unit_powers': self.current_allocations.copy(),
            'current_ace': current_ace,
            'current_agc_output': current_agc_output,
        }

        return status
