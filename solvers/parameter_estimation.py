#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""



1. Manning's n
2. 
3. -Augmented EKF
4. 

: Claude
: 2025-10-23
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Callable
import copy
import warnings

from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver


class ParameterEstimator:
    """
    

    Augmented EKF
     = [h, hu, n, leak_rate, ...]

    
    - ""
    - n(k+1) = n(k) + w_n
    - 
    """

    def __init__(
        self,
        solver: HydrostaticCanalSolver,
        dt: float = 1.0,
        estimate_roughness: bool = True,
        estimate_leakage: bool = False,
        process_noise_std: float = 0.01,
        parameter_process_noise: float = 1e-5,
        verbose: bool = True
    ):
        """
        

        Args:
            solver: 
            dt: 
            estimate_roughness: 
            estimate_leakage: 
            process_noise_std: 
            parameter_process_noise: 
            verbose: 
        """
        self.solver = solver
        self.dt = dt
        self.estimate_roughness = estimate_roughness
        self.estimate_leakage = estimate_leakage
        self.verbose = verbose

        # 
        self.nx = solver.nx
        self.state_dim = 2 * self.nx  # [h, hu]

        # 
        self.param_dim = 0
        self.param_names = []

        if estimate_roughness:
            self.param_dim += 1  # 
            self.param_names.append('roughness')

        if estimate_leakage:
            self.param_dim += self.nx  # 
            self.param_names.extend([f'leak_{i}' for i in range(self.nx)])

        # 
        self.augmented_dim = self.state_dim + self.param_dim

        # 
        Q_state = np.eye(self.state_dim) * (process_noise_std ** 2)
        Q_param = np.eye(self.param_dim) * (parameter_process_noise ** 2)
        self.Q = np.block([
            [Q_state, np.zeros((self.state_dim, self.param_dim))],
            [np.zeros((self.param_dim, self.state_dim)), Q_param]
        ])

        # 
        P_state = np.eye(self.state_dim) * 0.1
        P_param = np.eye(self.param_dim) * 0.01  # 
        self.P = np.block([
            [P_state, np.zeros((self.state_dim, self.param_dim))],
            [np.zeros((self.param_dim, self.state_dim)), P_param]
        ])

        # 
        self.parameters = {}
        if estimate_roughness:
            self.parameters['roughness'] = solver.n  # 
        if estimate_leakage:
            self.parameters['leakage'] = np.zeros(self.nx)  # 0

        # 
        self.sensors = {}

        # 
        self.current_Q_upstream = 0.0
        self.current_h_downstream = 0.0

        # 
        self.history = {
            'time': [],
            'h': [],
            'Q': [],
            'parameters': {name: [] for name in self.param_names},
            'parameter_std': {name: [] for name in self.param_names},
            'measurements': [],
            'innovations': []
        }

        if self.verbose:
            print(f":")
            print(f"  : {self.state_dim}")
            print(f"  : {self.param_dim}")
            print(f"  : {self.augmented_dim}")
            print(f"  : {', '.join(self.param_names)}")

    def add_sensor(
        self,
        name: str,
        sensor_type: str,
        location_idx: int,
        noise_std: float = 0.01
    ):
        """"""
        self.sensors[name] = {
            'type': sensor_type,
            'location': location_idx,
            'noise_std': noise_std
        }

    def _get_parameter_vector(self) -> np.ndarray:
        """"""
        params = []

        if self.estimate_roughness:
            params.append(self.parameters['roughness'])

        if self.estimate_leakage:
            params.extend(self.parameters['leakage'])

        return np.array(params)

    def _set_parameter_vector(self, param_vec: np.ndarray):
        """"""
        idx = 0

        if self.estimate_roughness:
            self.parameters['roughness'] = param_vec[idx]
            # 
            self.solver.n = max(0.01, min(0.1, param_vec[idx]))  # 
            idx += 1

        if self.estimate_leakage:
            self.parameters['leakage'] = param_vec[idx:idx + self.nx]
            idx += self.nx

    def _get_augmented_state(self) -> np.ndarray:
        """"""
        state = np.concatenate([self.solver.h, self.solver.hu])
        params = self._get_parameter_vector()
        return np.concatenate([state, params])

    def _set_augmented_state(self, aug_state: np.ndarray):
        """"""
        self.solver.h = aug_state[:self.nx]
        self.solver.hu = aug_state[self.nx:self.state_dim]
        self._set_parameter_vector(aug_state[self.state_dim:])

    def predict_step(
        self,
        Q_upstream: Optional[float] = None,
        h_downstream: Optional[float] = None
    ):
        """
        EKF

        
        
        """
        # 
        self.current_Q_upstream = Q_upstream if Q_upstream is not None else 0.0
        self.current_h_downstream = h_downstream if h_downstream is not None else 0.0

        # 
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
        # θ(k+1) = θ(k) + w_θ

        # 
        F = np.eye(self.augmented_dim)

        # 
        self.P = F @ self.P @ F.T + self.Q

    def _get_observation_matrix(self, sensor: Dict) -> np.ndarray:
        """
        

        H = [H_state | H_param]
        """
        H = np.zeros(self.augmented_dim)

        idx = sensor['location']
        sensor_type = sensor['type']

        if sensor_type == 'water_level':
            H[idx] = 1.0
        elif sensor_type == 'flow_rate':
            H[self.nx + idx] = self.solver.B
        elif sensor_type == 'velocity':
            h_current = self.solver.h[idx] + 1e-6
            H[self.nx + idx] = 1.0 / h_current

        # 
        # ∂z/∂θ ≈ [z(θ+δθ) - z(θ)] / δθ
        if self.param_dim > 0:
            param_sensitivity = self._compute_parameter_sensitivity(
                sensor,
                self.current_Q_upstream,
                self.current_h_downstream
            )
            H[self.state_dim:] = param_sensitivity

        return H

    def _compute_parameter_sensitivity(
        self,
        sensor: Dict,
        Q_upstream: float,
        h_downstream: float
    ) -> np.ndarray:
        """
        

        
         ∂(observation)/∂(parameter)

        :
            sensor: 
            Q_upstream: 
            h_downstream: 
        """
        sensitivity = np.zeros(self.param_dim)
        param_idx = 0

        # 
        h_save = self.solver.h.copy()
        hu_save = self.solver.hu.copy()

        # 
        z_base = self._predict_measurement(sensor)

        if self.estimate_roughness:
            # 
            n_base = self.solver.n

            # 1%
            delta_n = max(0.0001, abs(n_base) * 0.01)

            # 
            self.solver.n = n_base + delta_n

            # 
            try:
                h_pert, hu_pert = self.solver.step_preissmann(
                    dt=self.dt,
                    max_iter=10,
                    enforce_bc=True,
                    Q_in=Q_upstream,
                    h_out=h_downstream
                )

                # 
                self.solver.h = h_pert
                self.solver.hu = hu_pert

                # 
                z_pert = self._predict_measurement(sensor)

                # 
                sensitivity[param_idx] = (z_pert - z_base) / delta_n

            except Exception as e:
                # 
                sensitivity[param_idx] = 0.0
                if self.verbose:
                    print(f"[] : {e}")

            # 
            self.solver.n = n_base
            self.solver.h = h_save
            self.solver.hu = hu_save

            param_idx += 1

        if self.estimate_leakage:
            # 
            # : ∂h/∂t + ∂(hu)/∂x = -leak_rate

            # 
            leak_base = getattr(self.solver, 'leak_rate', np.zeros(self.nx))
            if not hasattr(self.solver, 'leak_rate'):
                # 
                self.solver.leak_rate = np.zeros(self.nx)
                leak_base = self.solver.leak_rate.copy()

            # 
            delta_leak = 1e-6  #  (m/s)

            for i in range(self.nx):
                try:
                    # 
                    h_save = self.solver.h.copy()
                    hu_save = self.solver.hu.copy()

                    # i
                    self.solver.leak_rate[i] += delta_leak

                    # 
                    # 
                    # ∂h/∂t = -∂(hu)/∂x - leak_rate
                    # : ∂(hu)/∂x = -leak_rate

                    # 
                    # Δh ≈ -leak_rate * dt
                    h_pert = self.solver.h.copy()
                    h_pert[i] -= delta_leak * self.dt  # 

                    # 
                    self.solver.h = h_pert
                    # hu

                    # 
                    z_pert = self._predict_measurement(sensor)

                    # 
                    sensitivity[param_idx] = (z_pert - z_base) / delta_leak

                except Exception as e:
                    # 
                    sensitivity[param_idx] = 0.0
                    if self.verbose:
                        print(f"[]  (i={i}): {e}")

                finally:
                    # 
                    self.solver.leak_rate[i] = leak_base[i]
                    self.solver.h = h_save
                    self.solver.hu = hu_save

                param_idx += 1

        return sensitivity

    def _predict_measurement(self, sensor: Dict) -> float:
        """"""
        idx = sensor['location']
        sensor_type = sensor['type']

        if sensor_type == 'water_level':
            return self.solver.h[idx]
        elif sensor_type == 'flow_rate':
            return self.solver.hu[idx] * self.solver.B
        elif sensor_type == 'velocity':
            h = self.solver.h[idx] + 1e-6
            return self.solver.hu[idx] / h
        else:
            raise ValueError(f": {sensor_type}")

    def update_step(
        self,
        measurements: Dict[str, float]
    ) -> Dict[str, float]:
        """
        EKF

        
        """
        innovations = {}

        for sensor_name, z in measurements.items():
            if sensor_name not in self.sensors:
                warnings.warn(f": {sensor_name}")
                continue

            sensor = self.sensors[sensor_name]

            # 
            H = self._get_observation_matrix(sensor)

            # 
            z_pred = self._predict_measurement(sensor)

            # 
            y = z - z_pred
            innovations[sensor_name] = y

            # 
            R = sensor['noise_std'] ** 2
            S = H @ self.P @ H.T + R

            # 
            K = self.P @ H.T / S

            # 
            aug_state = self._get_augmented_state()
            aug_state_new = aug_state + K * y
            self._set_augmented_state(aug_state_new)

            # 
            I = np.eye(self.augmented_dim)
            self.P = (I - np.outer(K, H)) @ self.P

        return innovations

    def run_estimation(
        self,
        t_end: float,
        Q_upstream_func: Callable[[float], float],
        h_downstream_func: Callable[[float], float],
        measurement_func: Callable[[float], Dict[str, float]],
        assimilation_interval: int = 1
    ) -> Dict:
        """
        

        Args:
            t_end: 
            Q_upstream_func: 
            h_downstream_func: 
            measurement_func: 
            assimilation_interval: 

        Returns:
            
        """
        n_steps = int(t_end / self.dt)

        if self.verbose:
            print(f"\n{'='*60}")
            print(f"")
            print(f"{'='*60}")
            print(f": {self.dt} s")
            print(f": {n_steps}")
            print(f": {', '.join(self.param_names)}")
            print(f"{'='*60}\n")

        # 
        self.history = {
            'time': [],
            'h': [],
            'Q': [],
            'parameters': {name: [] for name in self.param_names},
            'parameter_std': {name: [] for name in self.param_names},
            'measurements': [],
            'innovations': []
        }

        for step in range(n_steps + 1):
            t_current = step * self.dt

            # 
            self.history['time'].append(t_current)
            self.history['h'].append(self.solver.h.copy())
            self.history['Q'].append(self.solver.hu * self.solver.B)

            # 
            param_vec = self._get_parameter_vector()
            param_std = np.sqrt(np.diag(self.P)[self.state_dim:])

            idx = 0
            if self.estimate_roughness:
                self.history['parameters']['roughness'].append(param_vec[idx])
                self.history['parameter_std']['roughness'].append(param_std[idx])
                idx += 1

            if self.estimate_leakage:
                for i in range(self.nx):
                    self.history['parameters'][f'leak_{i}'].append(param_vec[idx])
                    self.history['parameter_std'][f'leak_{i}'].append(param_std[idx])
                    idx += 1

            # 
            if self.verbose and step % 10 == 0:
                if self.estimate_roughness:
                    n_est = self.parameters['roughness']
                    n_std = param_std[0] if self.estimate_roughness else 0
                    print(f"t = {t_current:.1f} s:  n = {n_est:.4f} ± {n_std:.4f}")

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

        if self.verbose:
            print(f"\n{'='*60}")
            print(f"")
            self._print_final_parameters()
            print(f"{'='*60}\n")

        return self.history

    def _print_final_parameters(self):
        """"""
        print(f"\n:")

        if self.estimate_roughness:
            n_est = self.parameters['roughness']
            n_history = self.history['parameters']['roughness']
            n_std_history = self.history['parameter_std']['roughness']

            n_initial = n_history[0]
            n_final = n_history[-1]
            n_std_final = n_std_history[-1]

            print(f"   n:")
            print(f"    : {n_initial:.4f}")
            print(f"    : {n_final:.4f} ± {n_std_final:.4f}")
            print(f"    : {(n_final - n_initial)/n_initial*100:+.2f}%")

        if self.estimate_leakage:
            leak_mean = np.mean(self.parameters['leakage'])
            leak_std = np.std(self.parameters['leakage'])
            print(f"  :")
            print(f"    : {leak_mean:.6f} m/s")
            print(f"    : {leak_std:.6f} m/s")

    def get_parameter_estimates(self) -> Dict:
        """"""
        estimates = {}

        param_vec = self._get_parameter_vector()
        param_std = np.sqrt(np.diag(self.P)[self.state_dim:])

        idx = 0
        if self.estimate_roughness:
            estimates['roughness'] = {
                'value': param_vec[idx],
                'std': param_std[idx]
            }
            idx += 1

        if self.estimate_leakage:
            estimates['leakage'] = {
                'value': param_vec[idx:idx + self.nx],
                'std': param_std[idx:idx + self.nx]
            }

        return estimates
