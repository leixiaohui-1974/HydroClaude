#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
预测性维护

功能：
1. 传感器健康退化模型
2. 剩余使用寿命（RUL）预测
3. 维护建议生成
4. 故障风险评估

作者: Claude
日期: 2025-10-23
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from enum import Enum
import warnings


class MaintenanceLevel(Enum):
    """维护级别"""
    NORMAL = "正常运行"
    MONITORING = "加强监控"
    SCHEDULED = "计划维护"
    URGENT = "紧急维修"
    REPLACE = "需要更换"


class DegradationModel:
    """
    退化模型

    支持多种退化模型：
    - 线性退化
    - 指数退化
    - 威布尔退化
    """

    @staticmethod
    def linear(t: float, initial_health: float, degradation_rate: float) -> float:
        """
        线性退化模型

        h(t) = h0 - k*t
        """
        return max(0, initial_health - degradation_rate * t)

    @staticmethod
    def exponential(t: float, initial_health: float, decay_rate: float) -> float:
        """
        指数退化模型

        h(t) = h0 * exp(-λ*t)
        """
        return initial_health * np.exp(-decay_rate * t)

    @staticmethod
    def weibull(t: float, scale: float, shape: float) -> float:
        """
        威布尔退化模型（通过可靠度函数）

        R(t) = exp(-(t/η)^β)
        """
        return np.exp(-(t / scale) ** shape)


class SensorHealthPredictor:
    """
    传感器健康预测器

    基于历史健康评分预测：
    - 剩余使用寿命（RUL）
    - 故障概率
    - 维护建议
    """

    def __init__(
        self,
        failure_threshold: float = 0.3,
        degradation_model: str = 'exponential',
        verbose: bool = True
    ):
        """
        初始化健康预测器

        Args:
            failure_threshold: 故障阈值（健康评分）
            degradation_model: 退化模型类型
            verbose: 是否输出详细信息
        """
        self.failure_threshold = failure_threshold
        self.degradation_model_type = degradation_model
        self.verbose = verbose

        # 模型参数
        self.model_params = {}

    def fit_degradation_model(
        self,
        health_history: List[float],
        time_history: List[float]
    ) -> Dict:
        """
        拟合退化模型

        Args:
            health_history: 健康评分历史
            time_history: 时间历史

        Returns:
            模型参数
        """
        if len(health_history) < 3:
            warnings.warn("数据点太少，无法可靠拟合")
            return {}

        health_array = np.array(health_history)
        time_array = np.array(time_history)

        # 归一化时间
        t_normalized = time_array - time_array[0]

        if self.degradation_model_type == 'linear':
            # 最小二乘拟合
            # h(t) = h0 - k*t
            A = np.vstack([np.ones(len(t_normalized)), t_normalized]).T
            coefs, residuals, _, _ = np.linalg.lstsq(A, health_array, rcond=None)

            h0 = coefs[0]
            k = -coefs[1]  # 退化率（正值）

            self.model_params = {
                'initial_health': h0,
                'degradation_rate': k,
                'model': 'linear'
            }

        elif self.degradation_model_type == 'exponential':
            # 对数线性拟合
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
            raise ValueError(f"不支持的退化模型: {self.degradation_model_type}")

        return self.model_params

    def predict_health(
        self,
        future_time: float,
        current_time: float = 0.0
    ) -> float:
        """
        预测未来健康评分

        Args:
            future_time: 未来时间点
            current_time: 当前时间

        Returns:
            预测的健康评分
        """
        if not self.model_params:
            warnings.warn("模型未拟合，返回默认值")
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
        预测剩余使用寿命（RUL）

        Args:
            current_time: 当前时间
            current_health: 当前健康评分

        Returns:
            (RUL_mean, RUL_std): 平均RUL和标准差
        """
        if not self.model_params:
            warnings.warn("模型未拟合，无法预测RUL")
            return (np.inf, 0.0)

        # 寻找健康评分降至阈值的时间
        if self.model_params['model'] == 'linear':
            k = self.model_params['degradation_rate']
            if k <= 0:
                return (np.inf, 0.0)

            # h(t) = h0 - k*t = threshold
            # t_fail = (h0 - threshold) / k
            h0 = current_health
            t_fail = (h0 - self.failure_threshold) / k

            rul_mean = max(0, t_fail)
            rul_std = rul_mean * 0.2  # 假设20%不确定性

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
            rul_std = rul_mean * 0.25  # 假设25%不确定性

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
        评估未来故障概率

        使用正态分布近似：
        P(fail at t) = Φ((threshold - h_predicted) / σ)

        Args:
            future_time: 未来时间点
            current_time: 当前时间
            current_health: 当前健康评分

        Returns:
            故障概率 (0-1)
        """
        predicted_health = self.predict_health(future_time, current_time)

        # 估计预测不确定性
        prediction_std = 0.1  # 假设10%不确定性

        # 标准正态累积分布
        z = (self.failure_threshold - predicted_health) / prediction_std
        failure_prob = 0.5 * (1 + np.tanh(z / np.sqrt(2)))  # 近似

        return np.clip(failure_prob, 0, 1)


class MaintenanceAdvisor:
    """
    维护建议生成器

    基于：
    - 剩余使用寿命（RUL）
    - 健康评分
    - 故障概率

    生成维护建议
    """

    def __init__(
        self,
        rul_critical: float = 30.0,    # 30天
        rul_warning: float = 90.0,     # 90天
        health_critical: float = 0.3,
        health_warning: float = 0.5,
        verbose: bool = True
    ):
        """
        初始化维护建议器

        Args:
            rul_critical: RUL临界值（天）
            rul_warning: RUL警告值（天）
            health_critical: 健康评分临界值
            health_warning: 健康评分警告值
            verbose: 是否输出详细信息
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
        生成维护建议

        Args:
            sensor_name: 传感器名称
            current_health: 当前健康评分
            rul_mean: 平均RUL（天）
            rul_std: RUL标准差
            failure_prob_30d: 30天内故障概率

        Returns:
            建议字典
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

        # 决策逻辑
        if current_health < self.health_critical or rul_mean < self.rul_critical:
            # 紧急情况
            recommendation['maintenance_level'] = MaintenanceLevel.URGENT
            recommendation['urgency'] = 0.9
            recommendation['actions'].extend([
                f"⚠️ 传感器健康度严重下降（{current_health:.2f}）",
                f"⚠️ 剩余寿命不足{self.rul_critical}天（{rul_mean:.1f}±{rul_std:.1f}天）",
                "建议: 立即安排维修检查",
                "建议: 准备备用传感器"
            ])

        elif current_health < self.health_warning or rul_mean < self.rul_warning:
            # 计划维护
            recommendation['maintenance_level'] = MaintenanceLevel.SCHEDULED
            recommendation['urgency'] = 0.6
            recommendation['actions'].extend([
                f"⚡ 传感器健康度下降（{current_health:.2f}）",
                f"⚡ 剩余寿命约{rul_mean:.1f}天",
                f"建议: 计划{int(rul_mean * 0.5)}天内进行维护",
                "建议: 增加巡检频率"
            ])

        elif failure_prob_30d > 0.1:
            # 加强监控
            recommendation['maintenance_level'] = MaintenanceLevel.MONITORING
            recommendation['urgency'] = 0.3
            recommendation['actions'].extend([
                f"📊 30天故障概率: {failure_prob_30d:.1%}",
                "建议: 加强监控",
                "建议: 关注健康趋势"
            ])

        else:
            # 正常
            recommendation['maintenance_level'] = MaintenanceLevel.NORMAL
            recommendation['urgency'] = 0.0
            recommendation['actions'].append("✓ 传感器状态良好")

        return recommendation

    def generate_report(
        self,
        sensor_recommendations: List[Dict]
    ) -> str:
        """
        生成维护报告

        Args:
            sensor_recommendations: 所有传感器的建议列表

        Returns:
            格式化的报告文本
        """
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("预测性维护报告")
        report_lines.append("=" * 80)
        report_lines.append("")

        # 按紧急程度排序
        sorted_recs = sorted(sensor_recommendations, key=lambda x: x['urgency'], reverse=True)

        # 统计
        urgent_count = sum(1 for r in sorted_recs if r['maintenance_level'] == MaintenanceLevel.URGENT)
        scheduled_count = sum(1 for r in sorted_recs if r['maintenance_level'] == MaintenanceLevel.SCHEDULED)
        monitoring_count = sum(1 for r in sorted_recs if r['maintenance_level'] == MaintenanceLevel.MONITORING)
        normal_count = sum(1 for r in sorted_recs if r['maintenance_level'] == MaintenanceLevel.NORMAL)

        report_lines.append("总体概况:")
        report_lines.append(f"  传感器总数: {len(sorted_recs)}")
        report_lines.append(f"  🚨 紧急维修: {urgent_count}")
        report_lines.append(f"  ⚡ 计划维护: {scheduled_count}")
        report_lines.append(f"  📊 加强监控: {monitoring_count}")
        report_lines.append(f"  ✓ 状态良好: {normal_count}")
        report_lines.append("")

        # 详细建议
        if urgent_count + scheduled_count > 0:
            report_lines.append("需要关注的传感器:")
            report_lines.append("")

            for rec in sorted_recs:
                if rec['maintenance_level'] in [MaintenanceLevel.URGENT, MaintenanceLevel.SCHEDULED]:
                    report_lines.append(f"传感器: {rec['sensor']}")
                    report_lines.append(f"  状态: {rec['maintenance_level'].value}")
                    report_lines.append(f"  健康评分: {rec['current_health']:.2f}")
                    report_lines.append(f"  剩余寿命: {rec['rul_mean']:.1f}±{rec['rul_std']:.1f} 天")
                    report_lines.append(f"  30天故障概率: {rec['failure_prob_30d']:.1%}")
                    report_lines.append("  行动建议:")
                    for action in rec['actions']:
                        report_lines.append(f"    {action}")
                    report_lines.append("")

        report_lines.append("=" * 80)

        return "\n".join(report_lines)


class PredictiveMaintenanceSystem:
    """
    预测性维护系统

    集成：
    - 健康预测
    - RUL估计
    - 维护建议
    """

    def __init__(
        self,
        failure_threshold: float = 0.3,
        degradation_model: str = 'exponential',
        verbose: bool = True
    ):
        """初始化预测性维护系统"""
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
        添加传感器历史数据

        Args:
            sensor_name: 传感器名称
            health_history: 健康评分历史
            time_history: 时间历史（天）
        """
        predictor = SensorHealthPredictor(
            failure_threshold=self.predictor.failure_threshold,
            degradation_model=self.predictor.degradation_model_type,
            verbose=False
        )

        predictor.fit_degradation_model(health_history, time_history)
        self.sensor_predictors[sensor_name] = predictor

        if self.verbose:
            print(f"传感器 {sensor_name} 退化模型已拟合")

    def analyze_all_sensors(
        self,
        current_time: float
    ) -> List[Dict]:
        """
        分析所有传感器

        Args:
            current_time: 当前时间（天）

        Returns:
            所有传感器的建议列表
        """
        recommendations = []

        for sensor_name, predictor in self.sensor_predictors.items():
            # 获取当前健康评分（最后一个历史值）
            current_health = predictor.model_params.get('initial_health', 1.0)

            # 预测RUL
            rul_mean, rul_std = predictor.predict_rul(current_time, current_health)

            # 评估30天故障概率
            failure_prob_30d = predictor.assess_failure_probability(
                future_time=current_time + 30,
                current_time=current_time,
                current_health=current_health
            )

            # 生成建议
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
        生成维护报告

        Args:
            current_time: 当前时间（天）

        Returns:
            报告文本
        """
        recommendations = self.analyze_all_sensors(current_time)
        report = self.advisor.generate_report(recommendations)

        return report
