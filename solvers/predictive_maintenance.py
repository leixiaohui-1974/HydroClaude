#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""



1. 
2. RUL
3. 
4. 

: Claude
: 2025-10-23
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from enum import Enum
import warnings


class MaintenanceLevel(Enum):
    """"""
    NORMAL = ""
    MONITORING = ""
    SCHEDULED = ""
    URGENT = ""
    REPLACE = ""


class DegradationModel:
    """
    

    
    - 
    - 
    - 
    """

    @staticmethod
    def linear(t: float, initial_health: float, degradation_rate: float) -> float:
        """
        

        h(t) = h0 - k*t
        """
        return max(0, initial_health - degradation_rate * t)

    @staticmethod
    def exponential(t: float, initial_health: float, decay_rate: float) -> float:
        """
        

        h(t) = h0 * exp(-λ*t)
        """
        return initial_health * np.exp(-decay_rate * t)

    @staticmethod
    def weibull(t: float, scale: float, shape: float) -> float:
        """
        

        R(t) = exp(-(t/η)^β)
        """
        return np.exp(-(t / scale) ** shape)


class SensorHealthPredictor:
    """
    

    
    - RUL
    - 
    - 
    """

    def __init__(
        self,
        failure_threshold: float = 0.3,
        degradation_model: str = 'exponential',
        verbose: bool = True
    ):
        """
        

        Args:
            failure_threshold: 
            degradation_model: 
            verbose: 
        """
        self.failure_threshold = failure_threshold
        self.degradation_model_type = degradation_model
        self.verbose = verbose

        # 
        self.model_params = {}

    def fit_degradation_model(
        self,
        health_history: List[float],
        time_history: List[float]
    ) -> Dict:
        """
        

        Args:
            health_history: 
            time_history: 

        Returns:
            
        """
        if len(health_history) < 3:
            warnings.warn("")
            return {}

        health_array = np.array(health_history)
        time_array = np.array(time_history)

        # 
        t_normalized = time_array - time_array[0]

        if self.degradation_model_type == 'linear':
            # 
            # h(t) = h0 - k*t
            A = np.vstack([np.ones(len(t_normalized)), t_normalized]).T
            coefs, residuals, _, _ = np.linalg.lstsq(A, health_array, rcond=None)

            h0 = coefs[0]
            k = -coefs[1]  # 

            self.model_params = {
                'initial_health': h0,
                'degradation_rate': k,
                'model': 'linear'
            }

        elif self.degradation_model_type == 'exponential':
            # 
            # log(h(t)) = log(h0) - λ*t
            log_health = np.log(np.maximum(health_array, 1e-6))
            A = np.vstack([np.ones(len(t_normalized)), t_normalized]).T
            coefs, residuals, _, _ = np.linalg.lstsq(A, log_health, rcond=None)

            h0 = np.exp(coefs[0])
            lambda_decay = -coefs[1]

            self.model_params = {
                'initial_health': h0,
                'decay_rate': lambda_decay,
                'model': 'exponential'
            }

        else:
            raise ValueError(f": {self.degradation_model_type}")

        return self.model_params

    def predict_health(
        self,
        future_time: float,
        current_time: float = 0.0
    ) -> float:
        """
        

        Args:
            future_time: 
            current_time: 

        Returns:
            
        """
        if not self.model_params:
            warnings.warn("")
            return 0.5

        delta_t = future_time - current_time

        if self.model_params['model'] == 'linear':
            h0 = self.model_params['initial_health']
            k = self.model_params['degradation_rate']
            return DegradationModel.linear(delta_t, h0, k)

        elif self.model_params['model'] == 'exponential':
            h0 = self.model_params['initial_health']
            lambda_decay = self.model_params['decay_rate']
            return DegradationModel.exponential(delta_t, h0, lambda_decay)

        else:
            return 0.5

    def predict_rul(
        self,
        current_time: float,
        current_health: float
    ) -> Tuple[float, float]:
        """
        RUL

        Args:
            current_time: 
            current_health: 

        Returns:
            (RUL_mean, RUL_std): RUL
        """
        if not self.model_params:
            warnings.warn("RUL")
            return (np.inf, 0.0)

        # 
        if self.model_params['model'] == 'linear':
            k = self.model_params['degradation_rate']
            if k <= 0:
                return (np.inf, 0.0)

            # h(t) = h0 - k*t = threshold
            # t_fail = (h0 - threshold) / k
            h0 = current_health
            t_fail = (h0 - self.failure_threshold) / k

            rul_mean = max(0, t_fail)
            rul_std = rul_mean * 0.2  # 20%

        elif self.model_params['model'] == 'exponential':
            lambda_decay = self.model_params['decay_rate']
            if lambda_decay <= 0:
                return (np.inf, 0.0)

            # h(t) = h0 * exp(-λ*t) = threshold
            # t_fail = -log(threshold/h0) / λ
            h0 = current_health

            if h0 <= self.failure_threshold:
                return (0.0, 0.0)

            t_fail = -np.log(self.failure_threshold / h0) / lambda_decay

            rul_mean = max(0, t_fail)
            rul_std = rul_mean * 0.25  # 25%

        else:
            return (np.inf, 0.0)

        return (rul_mean, rul_std)

    def assess_failure_probability(
        self,
        future_time: float,
        current_time: float,
        current_health: float
    ) -> float:
        """
        

        
        P(fail at t) = Φ((threshold - h_predicted) / σ)

        Args:
            future_time: 
            current_time: 
            current_health: 

        Returns:
             (0-1)
        """
        predicted_health = self.predict_health(future_time, current_time)

        # 
        prediction_std = 0.1  # 10%

        # 
        z = (self.failure_threshold - predicted_health) / prediction_std
        failure_prob = 0.5 * (1 + np.tanh(z / np.sqrt(2)))  # 

        return np.clip(failure_prob, 0, 1)


class MaintenanceAdvisor:
    """
    

    
    - RUL
    - 
    - 

    
    """

    def __init__(
        self,
        rul_critical: float = 30.0,    # 30
        rul_warning: float = 90.0,     # 90
        health_critical: float = 0.3,
        health_warning: float = 0.5,
        verbose: bool = True
    ):
        """
        

        Args:
            rul_critical: RUL
            rul_warning: RUL
            health_critical: 
            health_warning: 
            verbose: 
        """
        self.rul_critical = rul_critical
        self.rul_warning = rul_warning
        self.health_critical = health_critical
        self.health_warning = health_warning
        self.verbose = verbose

    def generate_recommendation(
        self,
        sensor_name: str,
        current_health: float,
        rul_mean: float,
        rul_std: float,
        failure_prob_30d: float
    ) -> Dict:
        """
        

        Args:
            sensor_name: 
            current_health: 
            rul_mean: RUL
            rul_std: RUL
            failure_prob_30d: 30

        Returns:
            
        """
        recommendation = {
            'sensor': sensor_name,
            'current_health': current_health,
            'rul_mean': rul_mean,
            'rul_std': rul_std,
            'failure_prob_30d': failure_prob_30d,
            'maintenance_level': MaintenanceLevel.NORMAL,
            'actions': [],
            'urgency': 0.0  # 0-1
        }

        # 
        if current_health < self.health_critical or rul_mean < self.rul_critical:
            # 
            recommendation['maintenance_level'] = MaintenanceLevel.URGENT
            recommendation['urgency'] = 0.9
            recommendation['actions'].extend([
                f"[WARN] {current_health:.2f}",
                f"[WARN] {self.rul_critical}{rul_mean:.1f}±{rul_std:.1f}",
                ": ",
                ": "
            ])

        elif current_health < self.health_warning or rul_mean < self.rul_warning:
            # 
            recommendation['maintenance_level'] = MaintenanceLevel.SCHEDULED
            recommendation['urgency'] = 0.6
            recommendation['actions'].extend([
                f" {current_health:.2f}",
                f" {rul_mean:.1f}",
                f": {int(rul_mean * 0.5)}",
                ": "
            ])

        elif failure_prob_30d > 0.1:
            # 
            recommendation['maintenance_level'] = MaintenanceLevel.MONITORING
            recommendation['urgency'] = 0.3
            recommendation['actions'].extend([
                f"[CHART] 30: {failure_prob_30d:.1%}",
                ": ",
                ": "
            ])

        else:
            # 
            recommendation['maintenance_level'] = MaintenanceLevel.NORMAL
            recommendation['urgency'] = 0.0
            recommendation['actions'].append("[OK] ")

        return recommendation

    def generate_report(
        self,
        sensor_recommendations: List[Dict]
    ) -> str:
        """
        

        Args:
            sensor_recommendations: 

        Returns:
            
        """
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("")
        report_lines.append("=" * 80)
        report_lines.append("")

        # 
        sorted_recs = sorted(sensor_recommendations, key=lambda x: x['urgency'], reverse=True)

        # 
        urgent_count = sum(1 for r in sorted_recs if r['maintenance_level'] == MaintenanceLevel.URGENT)
        scheduled_count = sum(1 for r in sorted_recs if r['maintenance_level'] == MaintenanceLevel.SCHEDULED)
        monitoring_count = sum(1 for r in sorted_recs if r['maintenance_level'] == MaintenanceLevel.MONITORING)
        normal_count = sum(1 for r in sorted_recs if r['maintenance_level'] == MaintenanceLevel.NORMAL)

        report_lines.append(":")
        report_lines.append(f"  : {len(sorted_recs)}")
        report_lines.append(f"   : {urgent_count}")
        report_lines.append(f"   : {scheduled_count}")
        report_lines.append(f"  [CHART] : {monitoring_count}")
        report_lines.append(f"  [OK] : {normal_count}")
        report_lines.append("")

        # 
        if urgent_count + scheduled_count > 0:
            report_lines.append(":")
            report_lines.append("")

            for rec in sorted_recs:
                if rec['maintenance_level'] in [MaintenanceLevel.URGENT, MaintenanceLevel.SCHEDULED]:
                    report_lines.append(f": {rec['sensor']}")
                    report_lines.append(f"  : {rec['maintenance_level'].value}")
                    report_lines.append(f"  : {rec['current_health']:.2f}")
                    report_lines.append(f"  : {rec['rul_mean']:.1f}±{rec['rul_std']:.1f} ")
                    report_lines.append(f"  30: {rec['failure_prob_30d']:.1%}")
                    report_lines.append("  :")
                    for action in rec['actions']:
                        report_lines.append(f"    {action}")
                    report_lines.append("")

        report_lines.append("=" * 80)

        return "\n".join(report_lines)


class PredictiveMaintenanceSystem:
    """
    

    
    - 
    - RUL
    - 
    """

    def __init__(
        self,
        failure_threshold: float = 0.3,
        degradation_model: str = 'exponential',
        verbose: bool = True
    ):
        """"""
        self.predictor = SensorHealthPredictor(
            failure_threshold=failure_threshold,
            degradation_model=degradation_model,
            verbose=verbose
        )

        self.advisor = MaintenanceAdvisor(verbose=verbose)

        self.sensor_predictors: Dict[str, SensorHealthPredictor] = {}
        self.verbose = verbose

    def add_sensor_history(
        self,
        sensor_name: str,
        health_history: List[float],
        time_history: List[float]
    ):
        """
        

        Args:
            sensor_name: 
            health_history: 
            time_history: 
        """
        predictor = SensorHealthPredictor(
            failure_threshold=self.predictor.failure_threshold,
            degradation_model=self.predictor.degradation_model_type,
            verbose=False
        )

        predictor.fit_degradation_model(health_history, time_history)
        self.sensor_predictors[sensor_name] = predictor

        if self.verbose:
            print(f" {sensor_name} ")

    def analyze_all_sensors(
        self,
        current_time: float
    ) -> List[Dict]:
        """
        

        Args:
            current_time: 

        Returns:
            
        """
        recommendations = []

        for sensor_name, predictor in self.sensor_predictors.items():
            # 
            current_health = predictor.model_params.get('initial_health', 1.0)

            # RUL
            rul_mean, rul_std = predictor.predict_rul(current_time, current_health)

            # 30
            failure_prob_30d = predictor.assess_failure_probability(
                future_time=current_time + 30,
                current_time=current_time,
                current_health=current_health
            )

            # 
            rec = self.advisor.generate_recommendation(
                sensor_name=sensor_name,
                current_health=current_health,
                rul_mean=rul_mean,
                rul_std=rul_std,
                failure_prob_30d=failure_prob_30d
            )

            recommendations.append(rec)

        return recommendations

    def generate_maintenance_report(
        self,
        current_time: float
    ) -> str:
        """
        

        Args:
            current_time: 

        Returns:
            
        """
        recommendations = self.analyze_all_sensors(current_time)
        report = self.advisor.generate_report(recommendations)

        return report
