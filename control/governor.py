# -*- coding: utf-8 -*-
"""
Hydraulic Turbine Governor Models
==================================

Implements turbine governors for speed/frequency control:
- PID Governor (经典PID调速器)
- Electro-hydraulic Governor (电液调速器)

Governors regulate turbine speed by adjusting guide vane opening.

Control loop:
Speed Reference → Error → PID Controller → Servo → Guide Vane → Turbine → Speed

Key components:
- PID controller (比例-积分-微分)
- Servo system (伺服系统)
- Rate limiters (速率限制)
- Dead band (死区)
- Opening limiters (开度限制)

Author: Claude
Date: 2025-10-22
"""

import numpy as np
from typing import Optional, Tuple
from abc import ABC, abstractmethod


class PIDController:
    """
    PID Controller (PID控制器)

    Standard form:
    u(t) = Kp * e(t) + Ki * ∫e(t)dt + Kd * de(t)/dt

    where:
    - e(t): error = setpoint - measurement
    - Kp: proportional gain
    - Ki: integral gain
    - Kd: derivative gain
    """

    def __init__(self, Kp: float, Ki: float, Kd: float,
                 output_min: float = -1.0, output_max: float = 1.0):
        """
        Initialize PID controller

        Args:
            Kp: Proportional gain
            Ki: Integral gain
            Kd: Derivative gain
            output_min: Minimum output limit
            output_max: Maximum output limit
        """
        self.Kp = Kp
        self.Ki = Ki
        self.Kd = Kd
        self.output_min = output_min
        self.output_max = output_max

        # State variables
        self.integral = 0.0
        self.prev_error = 0.0
        self.prev_time = 0.0

    def compute(self, setpoint: float, measurement: float,
                current_time: float) -> float:
        """
        Compute PID output

        Args:
            setpoint: Desired value (e.g., rated speed)
            measurement: Current value (e.g., actual speed)
            current_time: Current time (s)

        Returns:
            output: Control signal
        """
        # Error
        error = setpoint - measurement

        # Time step
        if self.prev_time == 0.0:
            dt = 0.0
        else:
            dt = current_time - self.prev_time

        # Proportional term
        P = self.Kp * error

        # Integral term (with anti-windup)
        if dt > 0:
            self.integral += error * dt
        I = self.Ki * self.integral

        # Derivative term
        if dt > 0:
            derivative = (error - self.prev_error) / dt
        else:
            derivative = 0.0
        D = self.Kd * derivative

        # Total output
        output = P + I + D

        # Apply limits (with anti-windup)
        if output > self.output_max:
            output = self.output_max
            # Anti-windup: stop integral growth
            if error > 0:
                self.integral -= error * dt
        elif output < self.output_min:
            output = self.output_min
            # Anti-windup: stop integral growth
            if error < 0:
                self.integral -= error * dt

        # Update state
        self.prev_error = error
        self.prev_time = current_time

        return output

    def reset(self):
        """Reset PID state"""
        self.integral = 0.0
        self.prev_error = 0.0
        self.prev_time = 0.0


class ServoSystem:
    """
    Hydraulic servo system for guide vane actuation (导叶伺服系统)

    First-order lag model:
    dy/dt = (y_command - y) / T_servo

    where:
    - y: guide vane opening (0-1)
    - y_command: commanded opening
    - T_servo: servo time constant (typically 0.1-0.5 s)
    """

    def __init__(self, time_constant: float = 0.2,
                 opening_min: float = 0.0, opening_max: float = 1.0,
                 rate_limit: float = 0.1):
        """
        Initialize servo system

        Args:
            time_constant: Servo time constant T_servo (s)
            opening_min: Minimum opening (p.u.)
            opening_max: Maximum opening (p.u.)
            rate_limit: Maximum rate of change (p.u./s)
        """
        self.T_servo = time_constant
        self.opening_min = opening_min
        self.opening_max = opening_max
        self.rate_limit = rate_limit

        # Current state
        self.opening = 0.5  # Initial opening (50%)

    def update(self, command: float, dt: float) -> float:
        """
        Update servo position

        Args:
            command: Commanded opening (p.u.)
            dt: Time step (s)

        Returns:
            opening: Actual opening (p.u.)
        """
        # Apply command limits
        command = np.clip(command, self.opening_min, self.opening_max)

        # First-order response
        if dt > 0 and self.T_servo > 0:
            # Exponential approach
            alpha = dt / self.T_servo
            delta = command - self.opening

            # Apply rate limit
            max_delta = self.rate_limit * dt
            if abs(delta) > max_delta:
                delta = np.sign(delta) * max_delta

            self.opening += delta * min(alpha, 1.0)
        else:
            self.opening = command

        # Enforce limits
        self.opening = np.clip(self.opening, self.opening_min, self.opening_max)

        return self.opening


class Governor(ABC):
    """
    Base class for hydraulic turbine governors

    All governors must implement:
    - compute_control(): Compute control action
    - update(): Update governor state
    """

    def __init__(self, rated_speed: float, dead_band: float = 0.0):
        """
        Base governor initialization

        Args:
            rated_speed: Rated turbine speed (rpm)
            dead_band: Dead band for speed deviation (rpm)
        """
        self.rated_speed = rated_speed
        self.dead_band = dead_band

    @abstractmethod
    def compute_control(self, speed: float, speed_ref: float, time: float) -> float:
        """
        Compute control action

        Args:
            speed: Current turbine speed (rpm)
            speed_ref: Reference speed (rpm)
            time: Current time (s)

        Returns:
            command: Opening command (p.u.)
        """
        pass

    @abstractmethod
    def update(self, dt: float) -> dict:
        """
        Update governor state

        Args:
            dt: Time step (s)

        Returns:
            state: Governor state dictionary
        """
        pass

    def apply_dead_band(self, error: float) -> float:
        """
        Apply dead band to error signal

        Args:
            error: Raw error signal (rpm)

        Returns:
            error_db: Error after dead band (rpm)
        """
        if abs(error) < self.dead_band:
            return 0.0
        elif error > 0:
            return error - self.dead_band
        else:
            return error + self.dead_band


class PIDGovernor(Governor):
    """
    PID Governor for hydraulic turbines (PID调速器)

    Components:
    - PID controller for speed regulation
    - Hydraulic servo system
    - Rate and position limiters
    - Dead band

    Typical parameters:
    - Kp: 5.0 - 20.0 (permanent droop bp = 1/Kp)
    - Ki: 0.5 - 2.0
    - Kd: 0.1 - 1.0
    - T_servo: 0.1 - 0.5 s
    """

    def __init__(self, rated_speed: float, Kp: float = 10.0,
                 Ki: float = 1.0, Kd: float = 0.5, T_servo: float = 0.2,
                 dead_band: float = 0.0, rate_limit: float = 0.1,
                 opening_min: float = 0.05, opening_max: float = 1.0):
        """
        Initialize PID governor

        Args:
            rated_speed: Rated turbine speed (rpm)
            Kp: Proportional gain (permanent droop bp = 1/Kp)
            Ki: Integral gain
            Kd: Derivative gain
            T_servo: Servo time constant (s)
            dead_band: Dead band (rpm)
            rate_limit: Maximum opening rate (p.u./s)
            opening_min: Minimum opening (p.u.)
            opening_max: Maximum opening (p.u.)
        """
        super().__init__(rated_speed, dead_band)

        # PID controller (operates on per-unit speed deviation)
        self.pid = PIDController(
            Kp=Kp,
            Ki=Ki,
            Kd=Kd,
            output_min=-1.0,
            output_max=1.0
        )

        # Servo system
        self.servo = ServoSystem(
            time_constant=T_servo,
            opening_min=opening_min,
            opening_max=opening_max,
            rate_limit=rate_limit
        )

        # Governor parameters
        self.Kp = Kp
        self.Ki = Ki
        self.Kd = Kd
        self.T_servo = T_servo
        self.opening_min = opening_min
        self.opening_max = opening_max

        # Calculate permanent droop
        self.permanent_droop = 1.0 / Kp if Kp > 0 else 0.0

        # State
        self.speed_setpoint = rated_speed
        self.opening_command = 0.5  # Initial command
        self.current_time = 0.0

    def compute_control(self, speed: float, speed_ref: float, time: float) -> float:
        """
        Compute PID control action

        Args:
            speed: Current speed (rpm)
            speed_ref: Reference speed (rpm)
            time: Current time (s)

        Returns:
            command: Opening command (p.u.)
        """
        self.speed_setpoint = speed_ref
        self.current_time = time

        # Per-unit speed
        speed_pu = speed / self.rated_speed
        speed_ref_pu = speed_ref / self.rated_speed

        # Speed error (in rpm)
        error_rpm = speed_ref - speed

        # Apply dead band
        error_db = self.apply_dead_band(error_rpm)

        # Per-unit error for PID
        error_pu = error_db / self.rated_speed

        # PID output (increment to opening)
        pid_output = self.pid.compute(0.0, -error_pu, time)

        # Opening command (baseline + PID adjustment)
        # For speed control: if speed is low, increase opening
        # error_pu > 0 means speed_ref > speed, so we need more opening
        self.opening_command = 0.5 + pid_output

        return self.opening_command

    def update(self, dt: float) -> dict:
        """
        Update servo system

        Args:
            dt: Time step (s)

        Returns:
            state: Governor state
        """
        # Update servo
        actual_opening = self.servo.update(self.opening_command, dt)

        state = {
            'opening_command': self.opening_command,
            'actual_opening': actual_opening,
            'speed_setpoint': self.speed_setpoint,
            'pid_integral': self.pid.integral,
            'permanent_droop': self.permanent_droop
        }

        return state

    def reset(self):
        """Reset governor to initial state"""
        self.pid.reset()
        self.servo.opening = 0.5
        self.opening_command = 0.5

    def __repr__(self):
        return (f"PIDGovernor(rated_speed={self.rated_speed:.0f}rpm, "
                f"Kp={self.Kp:.1f}, Ki={self.Ki:.1f}, Kd={self.Kd:.1f}, "
                f"bp={self.permanent_droop:.2%}, T_servo={self.T_servo:.2f}s)")


class ElectroHydraulicGovernor(Governor):
    """
    Electro-hydraulic governor (电液调速器)

    More advanced than PID, with:
    - Electronic speed sensor
    - Digital controller
    - Electro-hydraulic converter
    - Position feedback

    This is a simplified model using cascaded control.
    """

    def __init__(self, rated_speed: float, Kp: float = 15.0,
                 Ki: float = 1.5, Kd: float = 0.3, T_servo: float = 0.15,
                 dead_band: float = 0.1, rate_limit: float = 0.15):
        """
        Initialize electro-hydraulic governor

        Args:
            rated_speed: Rated speed (rpm)
            Kp, Ki, Kd: PID gains (typically higher than mechanical governor)
            T_servo: Servo time constant (faster than mechanical)
            dead_band: Dead band (rpm)
            rate_limit: Rate limit (p.u./s, faster than mechanical)
        """
        super().__init__(rated_speed, dead_band)

        # Outer loop: speed control
        self.speed_controller = PIDController(
            Kp=Kp, Ki=Ki, Kd=Kd,
            output_min=-1.0, output_max=1.0
        )

        # Inner loop: position control (faster)
        self.position_controller = PIDController(
            Kp=20.0, Ki=5.0, Kd=0.1,
            output_min=-1.0, output_max=1.0
        )

        # Servo
        self.servo = ServoSystem(
            time_constant=T_servo,
            opening_min=0.05,
            opening_max=1.0,
            rate_limit=rate_limit
        )

        self.Kp = Kp
        self.Ki = Ki
        self.Kd = Kd
        self.permanent_droop = 1.0 / Kp if Kp > 0 else 0.0

        # State
        self.speed_setpoint = rated_speed
        self.position_setpoint = 0.5
        self.current_time = 0.0

    def compute_control(self, speed: float, speed_ref: float, time: float) -> float:
        """
        Compute cascaded control action

        Args:
            speed: Current speed (rpm)
            speed_ref: Reference speed (rpm)
            time: Current time (s)

        Returns:
            command: Opening command (p.u.)
        """
        self.speed_setpoint = speed_ref
        self.current_time = time

        # Outer loop: speed error
        error_rpm = speed_ref - speed
        error_db = self.apply_dead_band(error_rpm)
        error_pu = error_db / self.rated_speed

        # Speed controller output = position setpoint change
        speed_output = self.speed_controller.compute(0.0, -error_pu, time)

        # Position setpoint
        self.position_setpoint = 0.5 + speed_output
        self.position_setpoint = np.clip(self.position_setpoint, 0.05, 1.0)

        return self.position_setpoint

    def update(self, dt: float) -> dict:
        """Update servo system"""
        actual_opening = self.servo.update(self.position_setpoint, dt)

        state = {
            'position_setpoint': self.position_setpoint,
            'actual_opening': actual_opening,
            'speed_setpoint': self.speed_setpoint,
            'permanent_droop': self.permanent_droop
        }

        return state

    def reset(self):
        """Reset governor"""
        self.speed_controller.reset()
        self.position_controller.reset()
        self.servo.opening = 0.5
        self.position_setpoint = 0.5

    def __repr__(self):
        return (f"ElectroHydraulicGovernor(rated_speed={self.rated_speed:.0f}rpm, "
                f"Kp={self.Kp:.1f}, bp={self.permanent_droop:.2%})")


# Utility functions
def calculate_permanent_droop(Kp: float) -> float:
    """
    Calculate permanent droop (调差率) from proportional gain

    bp = 1 / Kp

    Typical values:
    - Isolated system: bp = 2-4% (Kp = 25-50)
    - Grid-connected: bp = 4-6% (Kp = 16-25)

    Args:
        Kp: Proportional gain

    Returns:
        bp: Permanent droop (as fraction, e.g., 0.04 = 4%)
    """
    return 1.0 / Kp if Kp > 0 else 0.0


def calculate_proportional_gain(bp: float) -> float:
    """
    Calculate proportional gain from permanent droop

    Kp = 1 / bp

    Args:
        bp: Permanent droop (as fraction)

    Returns:
        Kp: Proportional gain
    """
    return 1.0 / bp if bp > 0 else 0.0


if __name__ == "__main__":
    print("=" * 80)
    print("GOVERNOR MODULE")
    print("=" * 80)

    # Example 1: PID Governor
    print("\nExample 1: PID Governor")
    print("-" * 80)

    pid_gov = PIDGovernor(
        rated_speed=250.0,  # 250 rpm
        Kp=10.0,            # bp = 10%
        Ki=1.0,
        Kd=0.5,
        T_servo=0.2,
        dead_band=0.5       # 0.5 rpm dead band
    )

    print(pid_gov)
    print(f"Permanent droop: {pid_gov.permanent_droop:.1%}")

    # Simulate step response
    print("\nStep response (speed drop from 250 to 245 rpm):")
    print("-" * 80)

    speed_ref = 250.0
    speed = 245.0  # 5 rpm drop (2% speed deviation)
    time = 0.0
    dt = 0.1  # 100 ms time step

    for i in range(5):
        # Compute control
        command = pid_gov.compute_control(speed, speed_ref, time)

        # Update servo
        state = pid_gov.update(dt)

        print(f"t={time:.1f}s: speed={speed:.1f}rpm, "
              f"command={command:.3f}, actual={state['actual_opening']:.3f}")

        # Simple speed recovery (for demo)
        speed += (state['actual_opening'] - 0.5) * 20 * dt

        time += dt

    # Example 2: Electro-hydraulic Governor
    print("\n\nExample 2: Electro-Hydraulic Governor")
    print("-" * 80)

    eh_gov = ElectroHydraulicGovernor(
        rated_speed=250.0,
        Kp=15.0,    # bp = 6.67%
        Ki=1.5,
        Kd=0.3,
        T_servo=0.15
    )

    print(eh_gov)
    print(f"Permanent droop: {eh_gov.permanent_droop:.1%}")

    # Example 3: Droop calculation
    print("\n\nExample 3: Droop Calculations")
    print("-" * 80)

    test_cases = [
        (4.0, "Isolated system"),
        (6.0, "Grid-connected"),
        (10.0, "High droop")
    ]

    print(f"{'Kp':>6} {'Droop (bp)':>12} {'Application':>20}")
    print("-" * 80)
    for Kp, application in test_cases:
        bp = calculate_permanent_droop(Kp)
        print(f"{Kp:>6.1f} {bp*100:>11.1f}% {application:>20}")

    print("\n" + "=" * 80)
    print("Module loaded successfully!")
    print("=" * 80)
