"""
模型验证指标模块

提供多种模型拟合度评估指标，用于评估在线辨识的IDZ模型质量。

支持的指标：
- R² (决定系数 / Coefficient of Determination)
- VAF (方差解释度 / Variance Accounted For)
- FIT (拟合百分比 / Fit Percentage)
- RMSE (均方根误差 / Root Mean Square Error)
- MAE (平均绝对误差 / Mean Absolute Error)
- NRMSE (归一化均方根误差 / Normalized RMSE)

作者：HydroClaude Team
日期：2025-10-24
"""

import numpy as np
from typing import Tuple, Dict, Optional
from dataclasses import dataclass


@dataclass
class ValidationMetrics:
    """模型验证指标数据类"""
    r_squared: float  # R² 决定系数 (-∞, 1], 1为完美拟合
    vaf: float  # VAF 方差解释度 (-∞, 100], 100为完美拟合
    fit: float  # FIT 拟合百分比 (-∞, 100], 100为完美拟合
    rmse: float  # RMSE 均方根误差, 越小越好
    mae: float  # MAE 平均绝对误差, 越小越好
    nrmse: float  # NRMSE 归一化均方根误差 [0, ∞), 越小越好

    def __str__(self) -> str:
        """格式化输出"""
        return (
            f"模型验证指标:\n"
            f"  R²    = {self.r_squared:.4f}  (1.0为完美)\n"
            f"  VAF   = {self.vaf:.2f}%  (100%为完美)\n"
            f"  FIT   = {self.fit:.2f}%  (100%为完美)\n"
            f"  RMSE  = {self.rmse:.4f}\n"
            f"  MAE   = {self.mae:.4f}\n"
            f"  NRMSE = {self.nrmse:.4f}  (0.0为完美)"
        )

    def is_good_fit(self, r2_threshold: float = 0.7,
                    vaf_threshold: float = 70.0) -> bool:
        """
        判断模型拟合是否良好

        Args:
            r2_threshold: R²阈值（默认0.7）
            vaf_threshold: VAF阈值（默认70%）

        Returns:
            是否为良好拟合
        """
        return self.r_squared >= r2_threshold and self.vaf >= vaf_threshold


class ModelValidator:
    """
    模型验证器

    用于评估在线辨识模型的质量和准确性
    """

    @staticmethod
    def compute_r_squared(y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """
        计算R² (决定系数)

        R² = 1 - SS_res / SS_tot
        其中：
        - SS_res = Σ(y_true - y_pred)²  残差平方和
        - SS_tot = Σ(y_true - ȳ)²      总平方和

        Args:
            y_true: 真实值
            y_pred: 预测值

        Returns:
            R²值，范围(-∞, 1]，1为完美拟合
        """
        y_true = np.asarray(y_true).flatten()
        y_pred = np.asarray(y_pred).flatten()

        # 残差平方和
        ss_res = np.sum((y_true - y_pred) ** 2)

        # 总平方和
        ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)

        # 防止除零
        if ss_tot < 1e-10:
            return 0.0

        r2 = 1.0 - (ss_res / ss_tot)
        return r2

    @staticmethod
    def compute_vaf(y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """
        计算VAF (方差解释度)

        VAF = (1 - var(y_true - y_pred) / var(y_true)) × 100%

        Args:
            y_true: 真实值
            y_pred: 预测值

        Returns:
            VAF值，范围(-∞, 100]，100为完美拟合
        """
        y_true = np.asarray(y_true).flatten()
        y_pred = np.asarray(y_pred).flatten()

        # 计算方差
        var_true = np.var(y_true)
        var_error = np.var(y_true - y_pred)

        # 防止除零
        if var_true < 1e-10:
            return 0.0

        vaf = (1.0 - var_error / var_true) * 100.0
        return vaf

    @staticmethod
    def compute_fit(y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """
        计算FIT (拟合百分比)

        FIT = (1 - ||y_true - y_pred|| / ||y_true - ȳ||) × 100%

        Args:
            y_true: 真实值
            y_pred: 预测值

        Returns:
            FIT值，范围(-∞, 100]，100为完美拟合
        """
        y_true = np.asarray(y_true).flatten()
        y_pred = np.asarray(y_pred).flatten()

        # 计算范数
        norm_error = np.linalg.norm(y_true - y_pred)
        norm_true = np.linalg.norm(y_true - np.mean(y_true))

        # 防止除零
        if norm_true < 1e-10:
            return 0.0

        fit = (1.0 - norm_error / norm_true) * 100.0
        return fit

    @staticmethod
    def compute_rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """
        计算RMSE (均方根误差)

        RMSE = sqrt(mean((y_true - y_pred)²))

        Args:
            y_true: 真实值
            y_pred: 预测值

        Returns:
            RMSE值，越小越好
        """
        y_true = np.asarray(y_true).flatten()
        y_pred = np.asarray(y_pred).flatten()

        rmse = np.sqrt(np.mean((y_true - y_pred) ** 2))
        return rmse

    @staticmethod
    def compute_mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """
        计算MAE (平均绝对误差)

        MAE = mean(|y_true - y_pred|)

        Args:
            y_true: 真实值
            y_pred: 预测值

        Returns:
            MAE值，越小越好
        """
        y_true = np.asarray(y_true).flatten()
        y_pred = np.asarray(y_pred).flatten()

        mae = np.mean(np.abs(y_true - y_pred))
        return mae

    @staticmethod
    def compute_nrmse(y_true: np.ndarray, y_pred: np.ndarray,
                     normalization: str = 'range') -> float:
        """
        计算NRMSE (归一化均方根误差)

        NRMSE = RMSE / normalization_factor

        Args:
            y_true: 真实值
            y_pred: 预测值
            normalization: 归一化方法
                - 'range': 使用数据范围 (max - min)
                - 'mean': 使用数据均值
                - 'std': 使用数据标准差

        Returns:
            NRMSE值，越小越好
        """
        y_true = np.asarray(y_true).flatten()
        y_pred = np.asarray(y_pred).flatten()

        rmse = ModelValidator.compute_rmse(y_true, y_pred)

        # 归一化因子
        if normalization == 'range':
            norm_factor = np.max(y_true) - np.min(y_true)
        elif normalization == 'mean':
            norm_factor = np.mean(y_true)
        elif normalization == 'std':
            norm_factor = np.std(y_true)
        else:
            raise ValueError(f"Unknown normalization method: {normalization}")

        # 防止除零
        if norm_factor < 1e-10:
            return 0.0

        nrmse = rmse / norm_factor
        return nrmse

    @classmethod
    def compute_all_metrics(cls, y_true: np.ndarray,
                           y_pred: np.ndarray) -> ValidationMetrics:
        """
        计算所有验证指标

        Args:
            y_true: 真实值
            y_pred: 预测值

        Returns:
            ValidationMetrics对象，包含所有指标
        """
        return ValidationMetrics(
            r_squared=cls.compute_r_squared(y_true, y_pred),
            vaf=cls.compute_vaf(y_true, y_pred),
            fit=cls.compute_fit(y_true, y_pred),
            rmse=cls.compute_rmse(y_true, y_pred),
            mae=cls.compute_mae(y_true, y_pred),
            nrmse=cls.compute_nrmse(y_true, y_pred, normalization='range')
        )


class OnlineModelValidator:
    """
    在线模型验证器

    用于在线辨识过程中实时评估模型质量
    支持滑动窗口验证
    """

    def __init__(self, window_size: int = 50):
        """
        初始化在线验证器

        Args:
            window_size: 滑动窗口大小
        """
        self.window_size = window_size
        self.y_true_buffer = []
        self.y_pred_buffer = []
        self.metrics_history = []

    def update(self, y_true: float, y_pred: float) -> Optional[ValidationMetrics]:
        """
        更新验证数据并计算指标

        Args:
            y_true: 真实值
            y_pred: 预测值

        Returns:
            如果窗口已满，返回ValidationMetrics，否则返回None
        """
        # 添加到缓冲区
        self.y_true_buffer.append(y_true)
        self.y_pred_buffer.append(y_pred)

        # 维持窗口大小
        if len(self.y_true_buffer) > self.window_size:
            self.y_true_buffer.pop(0)
            self.y_pred_buffer.pop(0)

        # 如果窗口已满，计算指标
        if len(self.y_true_buffer) >= self.window_size:
            metrics = ModelValidator.compute_all_metrics(
                np.array(self.y_true_buffer),
                np.array(self.y_pred_buffer)
            )
            self.metrics_history.append(metrics)
            return metrics

        return None

    def get_latest_metrics(self) -> Optional[ValidationMetrics]:
        """获取最新的验证指标"""
        if len(self.metrics_history) > 0:
            return self.metrics_history[-1]
        return None

    def reset(self):
        """重置验证器"""
        self.y_true_buffer = []
        self.y_pred_buffer = []
        self.metrics_history = []


def test_model_validator():
    """测试模型验证器"""
    print("=" * 80)
    print("模型验证指标测试")
    print("=" * 80)

    # 生成测试数据
    np.random.seed(42)
    n = 100
    t = np.linspace(0, 10, n)
    y_true = np.sin(t) + 0.1 * np.random.randn(n)

    # 测试不同质量的预测
    test_cases = {
        "完美拟合": y_true,
        "优秀拟合": y_true + 0.05 * np.random.randn(n),
        "良好拟合": y_true + 0.15 * np.random.randn(n),
        "中等拟合": y_true + 0.3 * np.random.randn(n),
        "差拟合": y_true + 0.5 * np.random.randn(n),
    }

    for name, y_pred in test_cases.items():
        print(f"\n{name}:")
        print("-" * 40)
        metrics = ModelValidator.compute_all_metrics(y_true, y_pred)
        print(metrics)
        print(f"拟合质量: {'良好' if metrics.is_good_fit() else '需改进'}")

    # 测试在线验证器
    print("\n" + "=" * 80)
    print("在线验证器测试")
    print("=" * 80)

    validator = OnlineModelValidator(window_size=20)
    y_pred_online = y_true + 0.1 * np.random.randn(n)

    for i in range(n):
        metrics = validator.update(y_true[i], y_pred_online[i])
        if metrics and i % 20 == 0:
            print(f"\n步骤 {i}:")
            print(f"  R² = {metrics.r_squared:.4f}")
            print(f"  VAF = {metrics.vaf:.2f}%")

    print("\n✅ 测试完成！")
    print("=" * 80)


if __name__ == "__main__":
    test_model_validator()
