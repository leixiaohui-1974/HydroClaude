#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
时间序列分析工具

提供对非稳态仿真结果的深入分析：
- 趋势分析
- 周期性检测
- 异常检测
- 统计特征提取
- 频谱分析

作者: Claude
日期: 2025-10-24
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy import signal, stats
from typing import Dict, List, Tuple, Optional
from pathlib import Path


class TimeSeriesAnalyzer:
    """
    时间序列分析器

    使用示例:
    ```python
    analyzer = TimeSeriesAnalyzer(time=t_array, data=h_array)

    # 统计分析
    stats = analyzer.compute_statistics()

    # 趋势分析
    trend = analyzer.detect_trend()

    # 频谱分析
    frequencies, power = analyzer.compute_spectrum()

    # 生成报告
    analyzer.generate_analysis_report('analysis.png')
    ```
    """

    def __init__(self, time: np.ndarray, data: np.ndarray, name: str = "Signal"):
        """
        初始化分析器

        Args:
            time: 时间数组
            data: 数据数组
            name: 信号名称
        """
        self.time = time
        self.data = data
        self.name = name

        # 验证
        if len(time) != len(data):
            raise ValueError("时间和数据数组长度必须相同")

        # 计算采样率
        self.dt = np.mean(np.diff(time)) if len(time) > 1 else 1.0
        self.fs = 1.0 / self.dt  # 采样频率

    def compute_statistics(self) -> Dict[str, float]:
        """
        计算统计特征

        Returns:
            统计指标字典
        """
        return {
            'mean': np.mean(self.data),
            'std': np.std(self.data),
            'min': np.min(self.data),
            'max': np.max(self.data),
            'median': np.median(self.data),
            'range': np.ptp(self.data),
            'variance': np.var(self.data),
            'skewness': stats.skew(self.data),
            'kurtosis': stats.kurtosis(self.data),
            'cv': np.std(self.data) / np.mean(self.data) if np.mean(self.data) != 0 else 0
        }

    def detect_trend(self, method: str = 'linear') -> Dict:
        """
        检测趋势

        Args:
            method: 趋势检测方法 ('linear', 'polynomial', 'moving_average')

        Returns:
            趋势信息字典
        """
        if method == 'linear':
            # 线性回归
            slope, intercept, r_value, p_value, std_err = stats.linregress(self.time, self.data)
            trend_line = slope * self.time + intercept

            return {
                'method': 'linear',
                'slope': slope,
                'intercept': intercept,
                'r_squared': r_value ** 2,
                'p_value': p_value,
                'trend_line': trend_line,
                'is_significant': p_value < 0.05
            }

        elif method == 'polynomial':
            # 多项式拟合
            degree = 3
            coeffs = np.polyfit(self.time, self.data, degree)
            trend_line = np.polyval(coeffs, self.time)

            # 计算R²
            ss_res = np.sum((self.data - trend_line) ** 2)
            ss_tot = np.sum((self.data - np.mean(self.data)) ** 2)
            r_squared = 1 - (ss_res / ss_tot)

            return {
                'method': 'polynomial',
                'degree': degree,
                'coefficients': coeffs,
                'trend_line': trend_line,
                'r_squared': r_squared
            }

        elif method == 'moving_average':
            # 移动平均
            window = min(len(self.data) // 10, 50)
            trend_line = np.convolve(self.data, np.ones(window) / window, mode='same')

            return {
                'method': 'moving_average',
                'window': window,
                'trend_line': trend_line
            }

        else:
            raise ValueError(f"未知的趋势检测方法: {method}")

    def detect_outliers(self, method: str = 'iqr', threshold: float = 1.5) -> Dict:
        """
        检测异常值

        Args:
            method: 检测方法 ('iqr', 'zscore', 'mad')
            threshold: 阈值

        Returns:
            异常值信息
        """
        if method == 'iqr':
            # 四分位距法
            Q1 = np.percentile(self.data, 25)
            Q3 = np.percentile(self.data, 75)
            IQR = Q3 - Q1
            lower_bound = Q1 - threshold * IQR
            upper_bound = Q3 + threshold * IQR

            outliers_mask = (self.data < lower_bound) | (self.data > upper_bound)

        elif method == 'zscore':
            # Z分数法
            z_scores = np.abs(stats.zscore(self.data))
            outliers_mask = z_scores > threshold

        elif method == 'mad':
            # 中位数绝对偏差法
            median = np.median(self.data)
            mad = np.median(np.abs(self.data - median))
            modified_z_scores = 0.6745 * (self.data - median) / mad if mad != 0 else np.zeros_like(self.data)
            outliers_mask = np.abs(modified_z_scores) > threshold

        else:
            raise ValueError(f"未知的异常检测方法: {method}")

        outlier_indices = np.where(outliers_mask)[0]
        outlier_values = self.data[outliers_mask]
        outlier_times = self.time[outliers_mask]

        return {
            'method': method,
            'threshold': threshold,
            'n_outliers': len(outlier_indices),
            'outlier_ratio': len(outlier_indices) / len(self.data),
            'outlier_indices': outlier_indices,
            'outlier_values': outlier_values,
            'outlier_times': outlier_times
        }

    def compute_spectrum(self, method: str = 'welch') -> Tuple[np.ndarray, np.ndarray]:
        """
        计算功率谱

        Args:
            method: 方法 ('fft', 'welch')

        Returns:
            (frequencies, power)
        """
        if method == 'fft':
            # FFT
            n = len(self.data)
            fft_result = np.fft.fft(self.data - np.mean(self.data))
            power = np.abs(fft_result) ** 2 / n
            frequencies = np.fft.fftfreq(n, self.dt)

            # 只取正频率
            positive_freq_idx = frequencies > 0
            frequencies = frequencies[positive_freq_idx]
            power = power[positive_freq_idx]

        elif method == 'welch':
            # Welch方法
            frequencies, power = signal.welch(
                self.data,
                fs=self.fs,
                nperseg=min(256, len(self.data) // 4)
            )

        else:
            raise ValueError(f"未知的频谱计算方法: {method}")

        return frequencies, power

    def detect_periodicity(self) -> Dict:
        """
        检测周期性

        Returns:
            周期性信息
        """
        # 计算自相关
        autocorr = np.correlate(self.data - np.mean(self.data), self.data - np.mean(self.data), mode='full')
        autocorr = autocorr[len(autocorr) // 2:]
        autocorr = autocorr / autocorr[0]  # 归一化

        # 找峰值
        peaks, properties = signal.find_peaks(autocorr, height=0.3, distance=10)

        if len(peaks) > 0:
            # 主周期
            main_period_idx = peaks[0]
            main_period = main_period_idx * self.dt

            return {
                'is_periodic': True,
                'main_period': main_period,
                'main_period_idx': main_period_idx,
                'autocorrelation': autocorr,
                'peaks': peaks,
                'peak_heights': properties['peak_heights']
            }
        else:
            return {
                'is_periodic': False,
                'autocorrelation': autocorr
            }

    def compute_rate_of_change(self) -> np.ndarray:
        """
        计算变化率

        Returns:
            变化率数组
        """
        return np.gradient(self.data, self.time)

    def generate_analysis_report(self, output_file: str = 'analysis.png'):
        """
        生成分析报告图

        Args:
            output_file: 输出文件路径
        """
        fig, axes = plt.subplots(2, 3, figsize=(16, 10))

        # 1. 原始信号
        axes[0, 0].plot(self.time, self.data, 'b-', linewidth=1.5)
        axes[0, 0].set_xlabel('时间')
        axes[0, 0].set_ylabel(self.name)
        axes[0, 0].set_title('原始信号', fontweight='bold')
        axes[0, 0].grid(True, alpha=0.3)

        # 2. 趋势
        trend_info = self.detect_trend('linear')
        axes[0, 1].plot(self.time, self.data, 'b-', alpha=0.5, label='原始')
        axes[0, 1].plot(self.time, trend_info['trend_line'], 'r-', linewidth=2, label='趋势')
        axes[0, 1].set_xlabel('时间')
        axes[0, 1].set_ylabel(self.name)
        axes[0, 1].set_title(f'趋势分析 (R²={trend_info["r_squared"]:.3f})', fontweight='bold')
        axes[0, 1].legend()
        axes[0, 1].grid(True, alpha=0.3)

        # 3. 异常值
        outliers = self.detect_outliers('iqr')
        axes[0, 2].plot(self.time, self.data, 'b-', linewidth=1.5, label='正常')
        if outliers['n_outliers'] > 0:
            axes[0, 2].scatter(outliers['outlier_times'], outliers['outlier_values'],
                             color='red', s=50, marker='o', label=f'异常 ({outliers["n_outliers"]})')
        axes[0, 2].set_xlabel('时间')
        axes[0, 2].set_ylabel(self.name)
        axes[0, 2].set_title(f'异常检测 ({outliers["outlier_ratio"]*100:.1f}%)', fontweight='bold')
        axes[0, 2].legend()
        axes[0, 2].grid(True, alpha=0.3)

        # 4. 直方图
        axes[1, 0].hist(self.data, bins=30, alpha=0.7, color='blue', edgecolor='black')
        stats_info = self.compute_statistics()
        axes[1, 0].axvline(stats_info['mean'], color='red', linestyle='--', linewidth=2, label=f'均值={stats_info["mean"]:.2f}')
        axes[1, 0].axvline(stats_info['median'], color='green', linestyle='--', linewidth=2, label=f'中位数={stats_info["median"]:.2f}')
        axes[1, 0].set_xlabel(self.name)
        axes[1, 0].set_ylabel('频数')
        axes[1, 0].set_title('分布直方图', fontweight='bold')
        axes[1, 0].legend()
        axes[1, 0].grid(True, alpha=0.3)

        # 5. 功率谱
        frequencies, power = self.compute_spectrum('welch')
        axes[1, 1].semilogy(frequencies, power, 'b-', linewidth=1.5)
        axes[1, 1].set_xlabel('频率 (Hz)')
        axes[1, 1].set_ylabel('功率谱密度')
        axes[1, 1].set_title('频谱分析', fontweight='bold')
        axes[1, 1].grid(True, alpha=0.3)

        # 6. 自相关
        periodicity = self.detect_periodicity()
        autocorr = periodicity['autocorrelation']
        lags = np.arange(len(autocorr)) * self.dt
        axes[1, 2].plot(lags, autocorr, 'b-', linewidth=1.5)
        axes[1, 2].axhline(y=0, color='k', linestyle='--', alpha=0.3)
        if periodicity['is_periodic']:
            axes[1, 2].axvline(periodicity['main_period'], color='red', linestyle='--',
                             linewidth=2, label=f'周期={periodicity["main_period"]:.1f}')
            axes[1, 2].legend()
        axes[1, 2].set_xlabel('滞后时间')
        axes[1, 2].set_ylabel('自相关系数')
        axes[1, 2].set_title('自相关分析', fontweight='bold')
        axes[1, 2].grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        plt.close()

        return output_file


# 便捷函数
def quick_analyze(
    time: np.ndarray,
    data: np.ndarray,
    name: str = "Signal",
    output_file: str = "analysis.png"
) -> Dict:
    """
    快速分析时间序列

    Args:
        time: 时间数组
        data: 数据数组
        name: 信号名称
        output_file: 输出图片路径

    Returns:
        分析结果字典
    """
    analyzer = TimeSeriesAnalyzer(time, data, name)

    results = {
        'statistics': analyzer.compute_statistics(),
        'trend': analyzer.detect_trend('linear'),
        'outliers': analyzer.detect_outliers('iqr'),
        'periodicity': analyzer.detect_periodicity()
    }

    # 生成报告图
    analyzer.generate_analysis_report(output_file)

    return results


if __name__ == "__main__":
    # 测试示例
    print("时间序列分析工具测试")
    print()

    # 生成测试数据（带趋势、周期和噪声）
    t = np.linspace(0, 100, 1000)
    trend = 0.02 * t  # 线性趋势
    periodic = 0.5 * np.sin(2 * np.pi * t / 20)  # 周期信号
    noise = 0.1 * np.random.randn(len(t))  # 噪声
    signal_data = 2.0 + trend + periodic + noise

    # 添加几个异常值
    signal_data[100] = 5.0
    signal_data[500] = 0.5

    # 创建分析器
    analyzer = TimeSeriesAnalyzer(t, signal_data, name="测试信号")

    # 统计分析
    print("统计特征:")
    stats_result = analyzer.compute_statistics()
    for key, value in stats_result.items():
        print(f"  {key}: {value:.4f}")

    # 趋势分析
    print("\n趋势分析:")
    trend_result = analyzer.detect_trend('linear')
    print(f"  斜率: {trend_result['slope']:.6f}")
    print(f"  R²: {trend_result['r_squared']:.4f}")
    print(f"  显著性: {'是' if trend_result['is_significant'] else '否'}")

    # 异常检测
    print("\n异常检测:")
    outliers = analyzer.detect_outliers('iqr')
    print(f"  异常点数: {outliers['n_outliers']}")
    print(f"  异常比例: {outliers['outlier_ratio']*100:.2f}%")

    # 周期性检测
    print("\n周期性检测:")
    periodicity = analyzer.detect_periodicity()
    if periodicity['is_periodic']:
        print(f"  周期性: 是")
        print(f"  主周期: {periodicity['main_period']:.2f}")
    else:
        print(f"  周期性: 否")

    # 生成报告
    print("\n生成分析报告...")
    output_file = analyzer.generate_analysis_report('test_analysis.png')
    print(f"   {output_file}")

    print("\n 测试完成！")
