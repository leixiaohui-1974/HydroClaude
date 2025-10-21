import numpy as np
from enum import Enum
from dataclasses import dataclass
from typing import List

class IntelligenceLevel(Enum):
    """智能化等级"""
    L0_MANUAL = 0          # 人工控制
    L1_ASSISTED = 1        # 辅助控制
    L2_SUPERVISED = 2      # 监督控制
    L3_AUTONOMOUS = 3      # 自主控制
    L4_PREDICTIVE = 4      # 预测控制
    L5_COGNITIVE = 5       # 认知智能

@dataclass
class PerformanceMetrics:
    """性能指标"""
    # 控制性能
    tracking_error_rmse: float = 0.0
    settling_time: float = 0.0
    overshoot: float = 0.0

    # 安全性
    constraint_violations: int = 0
    safety_margin: float = 0.0

    # 经济性
    total_energy: float = 0.0
    water_loss: float = 0.0

    # 鲁棒性
    disturbance_rejection: float = 0.0
    fault_tolerance: float = 0.0

    # 智能化
    prediction_accuracy: float = 0.0
    adaptation_speed: float = 0.0

    def compute_intelligence_level(self) -> IntelligenceLevel:
        """计算智能化等级"""
        score = 0

        # 基础控制性能（20分）
        if self.tracking_error_rmse < 0.5:
            score += 20
        elif self.tracking_error_rmse < 1.0:
            score += 15
        elif self.tracking_error_rmse < 2.0:
            score += 10

        # 安全性（20分）
        if self.constraint_violations == 0:
            score += 20
        elif self.constraint_violations < 5:
            score += 10

        # 经济性（20分）
        if self.total_energy < 1000:
            score += 20
        elif self.total_energy < 2000:
            score += 15

        # 鲁棒性（20分）
        if self.disturbance_rejection > 0.8:
            score += 20
        elif self.disturbance_rejection > 0.6:
            score += 15

        # 智能化（20分）
        if self.prediction_accuracy > 0.9:
            score += 10
        if self.adaptation_speed > 0.8:
            score += 10

        # 评级
        if score >= 90:
            return IntelligenceLevel.L5_COGNITIVE
        elif score >= 75:
            return IntelligenceLevel.L4_PREDICTIVE
        elif score >= 60:
            return IntelligenceLevel.L3_AUTONOMOUS
        elif score >= 40:
            return IntelligenceLevel.L2_SUPERVISED
        elif score >= 20:
            return IntelligenceLevel.L1_ASSISTED
        else:
            return IntelligenceLevel.L0_MANUAL

class PerformanceEvaluator:
    """性能评价器"""

    def __init__(self):
        self.metrics = PerformanceMetrics()
        self.history = []

    def evaluate(self, plant_history: List, twin_history: List,
                control_history: List, disturbances: List) -> PerformanceMetrics:
        """评价性能"""

        # 1. 控制性能
        self._evaluate_control_performance(plant_history, twin_history)

        # 2. 安全性
        self._evaluate_safety(plant_history)

        # 3. 经济性
        self._evaluate_economy(plant_history)

        # 4. 鲁棒性
        self._evaluate_robustness(plant_history, disturbances)

        # 5. 智能化
        self._evaluate_intelligence(plant_history, twin_history)

        self.history.append(self.metrics)
        return self.metrics

    def _evaluate_control_performance(self, plant_history: List, twin_history: List):
        """评价控制性能"""
        if not plant_history:
            return

        # 跟踪误差
        errors = []
        for p_state, t_state in zip(plant_history, twin_history):
            for comp_name in p_state.keys():
                if comp_name in t_state:
                    error = abs(p_state[comp_name].volume - t_state[comp_name].volume)
                    errors.append(error)

        self.metrics.tracking_error_rmse = np.sqrt(np.mean(np.array(errors)**2))

    def _evaluate_safety(self, plant_history: List):
        """评价安全性"""
        violations = 0
        margins = []

        for states in plant_history:
            for comp_name, state in states.items():
                # 检查水位是否超限（简化）
                if state.level > 10 or state.level < 1:
                    violations += 1
                margin = min(10 - state.level, state.level - 1)
                margins.append(margin)

        self.metrics.constraint_violations = violations
        self.metrics.safety_margin = np.mean(margins) if margins else 0

    def _evaluate_economy(self, plant_history: List):
        """评价经济性"""
        total_energy = 0
        for states in plant_history:
            for state in states.values():
                total_energy += state.power / 3600  # kWh

        self.metrics.total_energy = total_energy

    def _evaluate_robustness(self, plant_history: List, disturbances: List):
        """评价鲁棒性"""
        if not disturbances:
            self.metrics.disturbance_rejection = 1.0
            return

        # 简化：计算扰动前后的状态变化
        pre_disturbance_std = 1.0
        post_disturbance_std = 1.0

        if len(plant_history) > 10:
            volumes = [[s.volume for s in states.values()] for states in plant_history]
            pre_disturbance_std = np.std(volumes[:len(volumes)//2])
            post_disturbance_std = np.std(volumes[len(volumes)//2:])

        rejection = pre_disturbance_std / (post_disturbance_std + 1e-6)
        self.metrics.disturbance_rejection = min(1.0, rejection)

    def _evaluate_intelligence(self, plant_history: List, twin_history: List):
        """评价智能化"""
        # 预测准确度
        if len(plant_history) > 1 and len(twin_history) > 1:
            pred_errors = []
            for p, t in zip(plant_history[-10:], twin_history[-10:]):
                for name in p.keys():
                    if name in t:
                        pred_errors.append(abs(p[name].volume - t[name].volume))

            if pred_errors:
                max_error = max(pred_errors)
                self.metrics.prediction_accuracy = 1.0 / (1.0 + max_error)

        # 自适应速度（简化）
        self.metrics.adaptation_speed = 0.8
