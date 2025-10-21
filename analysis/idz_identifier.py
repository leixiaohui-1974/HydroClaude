#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
IDZ传递函数参数辨识模块

IDZ传递函数模型:
    G(s) = K * exp(-τ*s) / (T*s + 1)

其中:
    K: 稳态增益
    τ: 时滞 (seconds)
    T: 时间常数 (seconds)

作者: Claude
日期: 2025-10-21
"""

import numpy as np
from scipy.optimize import curve_fit
from typing import Dict, Tuple, Optional


class IDZIdentifier:
    """
    IDZ传递函数参数辨识器

    用于从阶跃响应数据中识别IDZ模型参数
    """

    @staticmethod
    def idz_response(t: np.ndarray, K: float, tau: float, T: float) -> np.ndarray:
        """
        IDZ传递函数的阶跃响应

        传递函数: G(s) = K * exp(-τ*s) / (T*s + 1)
        阶跃响应: y(t) = K * (1 - exp(-(t-τ)/T)) * u(t-τ)

        Args:
            t: 时间数组 (s)
            K: 稳态增益
            tau: 时滞 (s)
            T: 时间常数 (s)

        Returns:
            阶跃响应数组
        """
        response = np.zeros_like(t)
        mask = t >= tau
        response[mask] = K * (1 - np.exp(-(t[mask] - tau) / T))
        return response

    @staticmethod
    def estimate_parameters(t: np.ndarray, y: np.ndarray,
                           initial_guess: Optional[list] = None) -> Tuple[np.ndarray, float]:
        """
        从阶跃响应数据估计IDZ参数

        使用非线性最小二乘法拟合阶跃响应曲线

        Args:
            t: 时间序列数组
            y: 响应数据数组（阶跃响应）
            initial_guess: 初始猜测 [K, tau, T] (可选)

        Returns:
            (params, r_squared):
                - params: [K, tau, T] 参数数组
                - r_squared: 拟合质量指标 R²
        """
        # 数据预处理：去除初始值偏移
        y_baseline = np.mean(y[:min(10, len(y)//10)])  # 前10%数据的平均值作为基线
        y_data = y - y_baseline

        # 估计稳态增益K（使用后10%数据）
        n_last = max(10, len(y_data) // 10)
        K_est = np.mean(y_data[-n_last:])

        # 估计时滞tau（响应达到10%时的时间）
        if abs(K_est) > 1e-10:
            if K_est > 0:
                idx_10 = np.where(y_data >= 0.1 * K_est)[0]
            else:
                idx_10 = np.where(y_data <= 0.1 * K_est)[0]

            if len(idx_10) > 0:
                tau_est = t[idx_10[0]]
            else:
                tau_est = 0.0
        else:
            tau_est = 0.0

        # 估计时间常数T（从10%上升到63.2%的时间差）
        if abs(K_est) > 1e-10:
            if K_est > 0:
                idx_63 = np.where(y_data >= 0.632 * K_est)[0]
            else:
                idx_63 = np.where(y_data <= 0.632 * K_est)[0]

            if len(idx_63) > 0:
                T_est = t[idx_63[0]] - tau_est
            else:
                T_est = (t[-1] - tau_est) / 3  # 经验值
        else:
            T_est = (t[-1] - tau_est) / 3

        T_est = max(1.0, T_est)  # 确保T > 0

        # 使用初始猜测或估计值
        if initial_guess is None:
            initial_guess = [K_est, tau_est, T_est]

        # 优化拟合
        try:
            # 设置参数边界
            if K_est > 0:
                K_bounds = (0.5 * K_est, 1.5 * K_est)
            else:
                K_bounds = (1.5 * K_est, 0.5 * K_est)

            bounds = ([K_bounds[0], 0, 0.1],
                     [K_bounds[1], min(tau_est + 100, t[-1]/2), min(500, t[-1])])

            params, _ = curve_fit(IDZIdentifier.idz_response, t, y_data,
                                 p0=initial_guess, bounds=bounds,
                                 maxfev=5000)

            # 计算拟合质量（R²决定系数）
            y_fit = IDZIdentifier.idz_response(t, *params)
            ss_res = np.sum((y_data - y_fit) ** 2)  # 残差平方和
            ss_tot = np.sum((y_data - np.mean(y_data)) ** 2)  # 总平方和
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 1e-10 else 0.0

            return params, r_squared

        except Exception as e:
            # 拟合失败时返回初始估计
            print(f"    ⚠️  参数拟合失败: {e}")
            print(f"    使用初始估计: K={K_est:.6f}, tau={tau_est:.2f}, T={T_est:.2f}")
            return np.array(initial_guess), 0.0

    @staticmethod
    def identify_all_directions(time: np.ndarray, data_dict: Dict[str, np.ndarray],
                               verbose: bool = True) -> Dict:
        """
        辨识4个方向的传递函数参数

        Args:
            time: 时间序列数组
            data_dict: 数据字典，必须包含:
                - 'Q_upstream': 上游流量时间序列
                - 'h_upstream': 上游水深时间序列
                - 'Q_downstream': 下游流量时间序列
                - 'h_downstream': 下游水深时间序列
            verbose: 是否打印详细信息

        Returns:
            包含4个方向参数的字典，每个方向包含 K, tau, T, R2, name
        """
        results = {}

        # 方向1: 上游流量 → 下游水深
        if verbose:
            print("  方向1: Q_upstream → h_downstream")
        params1, r2_1 = IDZIdentifier.estimate_parameters(
            time, data_dict['h_downstream'])
        results['Q_to_h'] = {
            'K': params1[0],
            'tau': params1[1],
            'T': params1[2],
            'R2': r2_1,
            'name': 'Q_upstream → h_downstream',
            'description': '上游流量扰动对下游水深的影响'
        }
        if verbose:
            print(f"    K={params1[0]:.6f}, tau={params1[1]:.2f}s, "
                  f"T={params1[2]:.2f}s, R²={r2_1:.4f}")

        # 方向2: 上游流量 → 下游流量
        if verbose:
            print("  方向2: Q_upstream → Q_downstream")
        params2, r2_2 = IDZIdentifier.estimate_parameters(
            time, data_dict['Q_downstream'])
        results['Q_to_Q'] = {
            'K': params2[0],
            'tau': params2[1],
            'T': params2[2],
            'R2': r2_2,
            'name': 'Q_upstream → Q_downstream',
            'description': '上游流量扰动对下游流量的影响'
        }
        if verbose:
            print(f"    K={params2[0]:.6f}, tau={params2[1]:.2f}s, "
                  f"T={params2[2]:.2f}s, R²={r2_2:.4f}")

        # 方向3: 下游水深 → 上游水深（回水效应）
        if verbose:
            print("  方向3: h_downstream → h_upstream (回水效应)")
        params3, r2_3 = IDZIdentifier.estimate_parameters(
            time, data_dict['h_upstream'])
        results['h_to_h'] = {
            'K': params3[0],
            'tau': params3[1],
            'T': params3[2],
            'R2': r2_3,
            'name': 'h_downstream → h_upstream',
            'description': '下游水深扰动对上游水深的回水效应'
        }
        if verbose:
            print(f"    K={params3[0]:.6f}, tau={params3[1]:.2f}s, "
                  f"T={params3[2]:.2f}s, R²={r2_3:.4f}")

        # 方向4: 下游水深 → 上游流量
        if verbose:
            print("  方向4: h_downstream → Q_upstream (反馈)")
        params4, r2_4 = IDZIdentifier.estimate_parameters(
            time, data_dict['Q_upstream'])
        results['h_to_Q'] = {
            'K': params4[0],
            'tau': params4[1],
            'T': params4[2],
            'R2': r2_4,
            'name': 'h_downstream → Q_upstream',
            'description': '下游水深扰动对上游流量的反馈影响'
        }
        if verbose:
            print(f"    K={params4[0]:.6f}, tau={params4[1]:.2f}s, "
                  f"T={params4[2]:.2f}s, R²={r2_4:.4f}")

        return results

    @staticmethod
    def print_summary(results: Dict, method_name: str = ""):
        """
        打印辨识结果摘要

        Args:
            results: identify_all_directions返回的结果字典
            method_name: 方法名称（用于标题）
        """
        print("\n" + "=" * 80)
        if method_name:
            print(f"IDZ参数辨识结果 - {method_name}")
        else:
            print("IDZ参数辨识结果")
        print("=" * 80)

        print(f"\n{'方向':<40} {'K':>10} {'τ(s)':>10} {'T(s)':>10} {'R²':>10}")
        print("-" * 80)

        for key, data in results.items():
            print(f"{data['name']:<40} {data['K']:>10.6f} {data['tau']:>10.2f} "
                  f"{data['T']:>10.2f} {data['R2']:>10.4f}")

        print("=" * 80)

        # 评价
        print("\n拟合质量评价:")
        for key, data in results.items():
            r2 = data['R2']
            if r2 >= 0.95:
                quality = "优秀 ✅"
            elif r2 >= 0.85:
                quality = "良好 ✓"
            elif r2 >= 0.70:
                quality = "一般 ~"
            else:
                quality = "较差 ✗"

            print(f"  {data['name']:<40} R²={r2:.4f} ({quality})")

    @staticmethod
    def compare_methods(results_dict: Dict[str, Dict]):
        """
        对比多个方法的辨识结果

        Args:
            results_dict: 多个方法的结果字典
                格式: {'method_name': identify_all_directions_result, ...}
        """
        print("\n" + "=" * 100)
        print("不同数值方法的IDZ参数对比")
        print("=" * 100)

        directions = ['Q_to_h', 'Q_to_Q', 'h_to_h', 'h_to_Q']
        direction_names = {
            'Q_to_h': 'Q→h',
            'Q_to_Q': 'Q→Q',
            'h_to_h': 'h→h (回水)',
            'h_to_Q': 'h→Q (反馈)'
        }

        for direction in directions:
            print(f"\n{'方向: ' + direction_names[direction]}")
            print("-" * 100)
            print(f"{'方法':<20} {'K':>12} {'τ(s)':>12} {'T(s)':>12} {'R²':>12}")
            print("-" * 100)

            for method_name, results in results_dict.items():
                if direction in results:
                    data = results[direction]
                    print(f"{method_name:<20} {data['K']:>12.6f} {data['tau']:>12.2f} "
                          f"{data['T']:>12.2f} {data['R2']:>12.4f}")

        print("=" * 100)


if __name__ == '__main__':
    # 测试IDZ识别器
    print("=== IDZ参数辨识器测试 ===\n")

    # 生成测试数据（模拟阶跃响应）
    t = np.linspace(0, 500, 1000)
    K_true = 0.12
    tau_true = 100
    T_true = 20

    # 理论响应
    y_true = IDZIdentifier.idz_response(t, K_true, tau_true, T_true)

    # 添加噪声
    np.random.seed(42)
    y_noisy = y_true + np.random.normal(0, 0.001, len(t))

    # 参数辨识
    params, r2 = IDZIdentifier.estimate_parameters(t, y_noisy)

    print("真实参数:")
    print(f"  K = {K_true}")
    print(f"  τ = {tau_true} s")
    print(f"  T = {T_true} s")

    print("\n辨识结果:")
    print(f"  K = {params[0]:.6f} (误差: {abs(params[0]-K_true)/K_true*100:.2f}%)")
    print(f"  τ = {params[1]:.2f} s (误差: {abs(params[1]-tau_true)/tau_true*100:.2f}%)")
    print(f"  T = {params[2]:.2f} s (误差: {abs(params[2]-T_true)/T_true*100:.2f}%)")
    print(f"  R² = {r2:.6f}")

    if r2 > 0.99:
        print("\n✅ 辨识精度优秀")
    elif r2 > 0.95:
        print("\n✓ 辨识精度良好")
    else:
        print("\n⚠️  辨识精度一般")
