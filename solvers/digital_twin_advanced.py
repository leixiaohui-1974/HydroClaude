#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""



1. 
2. 
3. 
4. 
5. 

: Claude
: 2025-10-23
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Callable
import copy
import warnings
from enum import Enum

from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver


class SensorStatus(Enum):
    """"""
    NORMAL = ""
    DEGRADED = ""
    FAILED = ""
    OFFLINE = ""


class AdvancedSensor:
    """
    

    
    - 
    - 
    - 
    - 
    """

    def __init__(
        self,
        name: str,
        sensor_type: str,
        location_idx: int,
        noise_std: float = 0.01,
        failure_detection_threshold: float = 3.0,
        bias: float = 0.0
    ):
        """
        Args:
            name: 
            sensor_type:  ('water_level', 'flow_rate', 'velocity')
            location_idx: 
            noise_std: 
            failure_detection_threshold: σ
            bias: 
        """
        self.name = name
        self.sensor_type = sensor_type
        self.location_idx = location_idx
        self.noise_std = noise_std
        self.initial_noise_std = noise_std
        self.failure_threshold = failure_detection_threshold
        self.bias = bias

        # 
        self.status = SensorStatus.NORMAL
        self.health_score = 1.0  # 0-11

        # 
        self.innovation_history = []  # 
        self.measurement_count = 0
        self.anomaly_count = 0

        # 
        self.adaptive_noise = True
        self.noise_history = []

    def measure(
        self,
        true_value: float,
        add_noise: bool = True,
        add_bias: bool = True
    ) -> Optional[float]:
        """
        

        Args:
            true_value: 
            add_noise: 
            add_bias: 

        Returns:
            None
        """
        if self.status == SensorStatus.OFFLINE or self.status == SensorStatus.FAILED:
            return None

        measurement = true_value

        if add_bias:
            measurement += self.bias

        if add_noise:
            # 
            effective_noise = self.noise_std / np.sqrt(self.health_score)
            noise = np.random.normal(0, effective_noise)
            measurement += noise

        self.measurement_count += 1

        return measurement

    def update_innovation(
        self,
        innovation: float,
        predicted_uncertainty: float
    ):
        """
        

        Args:
            innovation:  - 
            predicted_uncertainty: σ
        """
        self.innovation_history.append(innovation)

        # 100
        if len(self.innovation_history) > 100:
            self.innovation_history.pop(0)

        # 
        normalized_innovation = abs(innovation) / (predicted_uncertainty + 1e-6)

        if normalized_innovation > self.failure_threshold:
            self.anomaly_count += 1

            # 
            if len(self.innovation_history) >= 5:
                recent_innovations = self.innovation_history[-5:]
                if all(abs(inn) / (predicted_uncertainty + 1e-6) > self.failure_threshold * 0.7
                      for inn in recent_innovations):
                    self.status = SensorStatus.FAILED
                    self.health_score = 0.0
                else:
                    self.status = SensorStatus.DEGRADED
                    self.health_score = 0.5
        else:
            # 
            if self.status != SensorStatus.FAILED:
                self.status = SensorStatus.NORMAL
                self.health_score = min(1.0, self.health_score + 0.1)

        # 
        if self.adaptive_noise and len(self.innovation_history) >= 10:
            # 
            estimated_noise = np.std(self.innovation_history[-10:])
            self.noise_std = 0.9 * self.noise_std + 0.1 * estimated_noise
            self.noise_history.append(self.noise_std)

    def get_reliability_weight(self) -> float:
        """
        

        Returns:
             (0-1)
        """
        if self.status == SensorStatus.OFFLINE or self.status == SensorStatus.FAILED:
            return 0.0
        elif self.status == SensorStatus.DEGRADED:
            return 0.3
        else:
            return self.health_score

    def reset_anomaly_counter(self):
        """"""
        self.anomaly_count = 0

    def get_diagnostics(self) -> Dict:
        """"""
        return {
            'name': self.name,
            'status': self.status.value,
            'health_score': self.health_score,
            'measurement_count': self.measurement_count,
            'anomaly_count': self.anomaly_count,
            'anomaly_rate': self.anomaly_count / max(1, self.measurement_count),
            'current_noise_std': self.noise_std,
            'initial_noise_std': self.initial_noise_std
        }


class SensorNetwork:
    """
    

    
    - 
    - 
    - 
    - 
    """

    def __init__(self):
        self.sensors: Dict[str, AdvancedSensor] = {}
        self.sensor_groups: Dict[str, List[str]] = {}  # 

    def add_sensor(
        self,
        sensor: AdvancedSensor
    ):
        """"""
        self.sensors[sensor.name] = sensor

        # 
        if sensor.sensor_type not in self.sensor_groups:
            self.sensor_groups[sensor.sensor_type] = []
        self.sensor_groups[sensor.sensor_type].append(sensor.name)

    def get_sensor(self, name: str) -> Optional[AdvancedSensor]:
        """"""
        return self.sensors.get(name)

    def get_healthy_sensors(self) -> List[AdvancedSensor]:
        """"""
        return [s for s in self.sensors.values()
                if s.status not in [SensorStatus.FAILED, SensorStatus.OFFLINE]]

    def get_network_health(self) -> float:
        """
        

        Returns:
             (0-1)
        """
        if not self.sensors:
            return 0.0

        total_health = sum(s.health_score for s in self.sensors.values())
        return total_health / len(self.sensors)

    def get_coverage_map(self, nx: int) -> np.ndarray:
        """
        

        Args:
            nx: 

        Returns:
            coverage: 
        """
        coverage = np.zeros(nx)

        for sensor in self.get_healthy_sensors():
            coverage[sensor.location_idx] += 1

        return coverage

    def diagnose(self) -> Dict:
        """"""
        diagnostics = {
            'total_sensors': len(self.sensors),
            'healthy_sensors': len([s for s in self.sensors.values()
                                   if s.status == SensorStatus.NORMAL]),
            'degraded_sensors': len([s for s in self.sensors.values()
                                    if s.status == SensorStatus.DEGRADED]),
            'failed_sensors': len([s for s in self.sensors.values()
                                  if s.status == SensorStatus.FAILED]),
            'network_health': self.get_network_health(),
            'sensor_details': [s.get_diagnostics() for s in self.sensors.values()]
        }

        return diagnostics


class AdvancedDigitalTwin:
    """
    

    
    1. 
    2. 
    3. 
    4. 
    5. 
    """

    def __init__(
        self,
        solver: HydrostaticCanalSolver,
        dt: float = 1.0,
        process_noise_std: float = 0.01,
        enable_fault_detection: bool = True,
        enable_adaptive_noise: bool = True,
        verbose: bool = True
    ):
        """
        

        Args:
            solver: 
            dt: 
            process_noise_std: 
            enable_fault_detection: 
            enable_adaptive_noise: 
            verbose: 
        """
        self.solver = solver
        self.dt = dt
        self.verbose = verbose

        # 
        self.nx = solver.nx
        self.state_dim = 2 * self.nx

        # 
        self.Q = np.eye(self.state_dim) * (process_noise_std ** 2)

        # 
        self.P = np.eye(self.state_dim) * 0.1

        # 
        self.sensor_network = SensorNetwork()

        # 
        self.enable_fault_detection = enable_fault_detection
        self.enable_adaptive_noise = enable_adaptive_noise

        # 
        self.history = {
            'time': [],
            'h': [],
            'Q': [],
            'h_std': [],
            'measurements': [],
            'innovations': [],
            'sensor_diagnostics': []
        }

    def add_sensor(
        self,
        name: str,
        sensor_type: str,
        location_idx: int,
        noise_std: float = 0.01,
        failure_threshold: float = 3.0,
        bias: float = 0.0
    ):
        """"""
        sensor = AdvancedSensor(
            name=name,
            sensor_type=sensor_type,
            location_idx=location_idx,
            noise_std=noise_std,
            failure_detection_threshold=failure_threshold,
            bias=bias
        )

        sensor.adaptive_noise = self.enable_adaptive_noise
        self.sensor_network.add_sensor(sensor)

        if self.verbose:
            print(f": {name} ({sensor_type}) @ grid {location_idx}, "
                  f"σ={noise_std:.3f}, ={failure_threshold:.1f}σ")

    def predict_step(
        self,
        Q_upstream: Optional[float] = None,
        h_downstream: Optional[float] = None
    ):
        """EKF Prediction"""
        h_pred, hu_pred = self.solver.step_preissmann(
            dt=self.dt,
            max_iter=10,
            enforce_bc=True,
            Q_in=Q_upstream,
            h_out=h_downstream
        )

        self.solver.h = h_pred
        self.solver.hu = hu_pred

        # 
        F = np.eye(self.state_dim)
        self.P = F @ self.P @ F.T + self.Q

    def update_step(
        self,
        measurements: Dict[str, float]
    ) -> Dict[str, float]:
        """
        

        
        - 
        - 
        - 
        """
        innovations = {}
        fused_successfully = []

        for sensor_name, z in measurements.items():
            sensor = self.sensor_network.get_sensor(sensor_name)

            if sensor is None:
                warnings.warn(f": {sensor_name}")
                continue

            # 
            if sensor.status == SensorStatus.FAILED or sensor.status == SensorStatus.OFFLINE:
                continue

            # 
            H = self._get_observation_matrix(sensor)

            # 
            z_pred = self._predict_measurement(sensor)

            # 
            y = z - z_pred
            innovations[sensor_name] = y

            # 
            predicted_variance = H @ self.P @ H.T + sensor.noise_std ** 2
            predicted_std = np.sqrt(predicted_variance)

            # 
            if self.enable_fault_detection:
                sensor.update_innovation(y, predicted_std)

                if sensor.status == SensorStatus.FAILED:
                    if self.verbose:
                        print(f"[WARN]  : {sensor_name} (={y:.4f}, ={predicted_std * sensor.failure_threshold:.4f})")
                    continue

            # 
            reliability = sensor.get_reliability_weight()

            if reliability < 0.1:
                continue

            # 
            R_effective = (sensor.noise_std ** 2) / reliability
            S = H @ self.P @ H.T + R_effective

            # 
            K = self.P @ H.T / S

            # 
            self.solver.h += K[:self.nx] * y * reliability
            self.solver.hu += K[self.nx:] * y * reliability

            # 
            I = np.eye(self.state_dim)
            self.P = (I - np.outer(K, H) * reliability) @ self.P

            fused_successfully.append(sensor_name)

        return innovations

    def _get_observation_matrix(self, sensor: AdvancedSensor) -> np.ndarray:
        """"""
        H = np.zeros(self.state_dim)
        idx = sensor.location_idx

        if sensor.sensor_type == 'water_level':
            H[idx] = 1.0
        elif sensor.sensor_type == 'flow_rate':
            H[self.nx + idx] = self.solver.B
        elif sensor.sensor_type == 'velocity':
            h_current = self.solver.h[idx] + 1e-6
            H[self.nx + idx] = 1.0 / h_current

        return H

    def _predict_measurement(self, sensor: AdvancedSensor) -> float:
        """"""
        idx = sensor.location_idx

        if sensor.sensor_type == 'water_level':
            return self.solver.h[idx]
        elif sensor.sensor_type == 'flow_rate':
            return self.solver.hu[idx] * self.solver.B
        elif sensor.sensor_type == 'velocity':
            h = self.solver.h[idx] + 1e-6
            return self.solver.hu[idx] / h
        else:
            raise ValueError(f": {sensor.sensor_type}")

    def run_assimilation(
        self,
        t_end: float,
        Q_upstream_func: Callable[[float], float],
        h_downstream_func: Callable[[float], float],
        measurement_func: Callable[[float], Dict[str, float]],
        assimilation_interval: int = 1,
        diagnostics_interval: int = 10
    ) -> Dict:
        """
        

        Args:
            t_end: 
            Q_upstream_func: 
            h_downstream_func: 
            measurement_func: 
            assimilation_interval: 
            diagnostics_interval: 

        Returns:
            
        """
        n_steps = int(t_end / self.dt)

        if self.verbose:
            print(f"\n{'='*60}")
            print(f"")
            print(f"{'='*60}")
            print(f": {self.dt} s")
            print(f": {n_steps}")
            print(f": {assimilation_interval} ")
            print(f": {len(self.sensor_network.sensors)}")
            print(f": {'' if self.enable_fault_detection else ''}")
            print(f": {'' if self.enable_adaptive_noise else ''}")
            print(f"{'='*60}\n")

        # 
        self.history = {
            'time': [],
            'h': [],
            'Q': [],
            'h_std': [],
            'measurements': [],
            'innovations': [],
            'sensor_diagnostics': []
        }

        for step in range(n_steps + 1):
            t_current = step * self.dt

            # 
            self.history['time'].append(t_current)
            self.history['h'].append(self.solver.h.copy())
            self.history['Q'].append(self.solver.hu * self.solver.B)

            h_var = np.diag(self.P)[:self.nx]
            h_std = np.sqrt(np.maximum(h_var, 0))
            self.history['h_std'].append(h_std)

            # 
            if self.verbose and step % diagnostics_interval == 0:
                network_health = self.sensor_network.get_network_health()
                print(f"t = {t_current:.1f} s:  = {network_health:.2%}")

            if step == n_steps:
                break

            # 
            Q_up = Q_upstream_func(t_current)
            h_down = h_downstream_func(t_current)
            self.predict_step(Q_upstream=Q_up, h_downstream=h_down)

            # 
            if step % assimilation_interval == 0:
                measurements = measurement_func(t_current)

                if measurements:
                    innovations = self.update_step(measurements)

                    self.history['measurements'].append({
                        'time': t_current,
                        'data': measurements
                    })
                    self.history['innovations'].append({
                        'time': t_current,
                        'values': innovations
                    })

            # 
            if step % diagnostics_interval == 0:
                diagnostics = self.sensor_network.diagnose()
                self.history['sensor_diagnostics'].append({
                    'time': t_current,
                    'diagnostics': diagnostics
                })

        if self.verbose:
            print(f"\n{'='*60}")
            print(f"")
            self._print_final_diagnostics()
            print(f"{'='*60}\n")

        return self.history

    def _print_final_diagnostics(self):
        """"""
        diagnostics = self.sensor_network.diagnose()

        print(f"\n:")
        print(f"  : {diagnostics['total_sensors']}")
        print(f"  : {diagnostics['healthy_sensors']}")
        print(f"  : {diagnostics['degraded_sensors']}")
        print(f"  : {diagnostics['failed_sensors']}")
        print(f"  : {diagnostics['network_health']:.2%}")

        if diagnostics['failed_sensors'] > 0:
            print(f"\n:")
            for detail in diagnostics['sensor_details']:
                if detail['status'] == SensorStatus.FAILED.value:
                    print(f"    - {detail['name']}: ={detail['anomaly_rate']:.2%}")

    def forecast(
        self,
        forecast_horizon: float,
        Q_upstream_func: Callable[[float], float],
        h_downstream_func: Callable[[float], float]
    ) -> Dict:
        """"""
        h_saved = self.solver.h.copy()
        hu_saved = self.solver.hu.copy()
        P_saved = self.P.copy()

        n_steps = int(forecast_horizon / self.dt)
        forecast_result = {
            'time': [],
            'h': [],
            'Q': [],
            'h_std': []
        }

        t_start = self.history['time'][-1] if self.history['time'] else 0.0

        for step in range(n_steps + 1):
            t = t_start + step * self.dt

            forecast_result['time'].append(t)
            forecast_result['h'].append(self.solver.h.copy())
            forecast_result['Q'].append(self.solver.hu * self.solver.B)

            h_var = np.diag(self.P)[:self.nx]
            h_std = np.sqrt(np.maximum(h_var, 0))
            forecast_result['h_std'].append(h_std)

            if step < n_steps:
                Q_up = Q_upstream_func(t)
                h_down = h_downstream_func(t)
                self.predict_step(Q_upstream=Q_up, h_downstream=h_down)

        # 
        self.solver.h = h_saved
        self.solver.hu = hu_saved
        self.P = P_saved

        return forecast_result
