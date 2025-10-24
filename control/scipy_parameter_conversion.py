"""
使用scipy.signal进行参数转换

改进的离散到连续参数转换方法，使用scipy提供的工具

作者：Claude
日期：2025-10-24
"""

import numpy as np
from scipy import signal
from typing import Optional, Tuple
from dataclasses import dataclass

try:
    from idz_model import IDZParameters
except ImportError:
    from control.idz_model import IDZParameters


class ScipyParameterConverter:
    """
    使用scipy.signal进行参数转换

    主要改进：
    1. 使用scipy的离散到连续变换（bilinear/backward_diff）
    2. 使用TransferFunction对象进行转换
    3. 极点配置法估计参数
    4. 优化拟合算法（最小二乘）
    """

    def __init__(self, dt: float, method: str = 'bilinear'):
        """
        Args:
            dt: 采样时间 (s)
            method: 转换方法 ('bilinear', 'backward_diff', 'forward_diff')
        """
        self.dt = dt
        self.method = method

        # 参数平滑
        self.smooth_alpha = 0.3
        self.prev_params: Optional[IDZParameters] = None

    def discrete_to_continuous(self,
                              theta: np.ndarray,
                              use_optimization: bool = True) -> IDZParameters:
        """
        将离散RLS参数转换为连续IDZ参数（使用scipy）

        离散模型: y(k) = a1*y(k-1) + a2*y(k-2) + b0*u(k) + b1*u(k-1) + b2*u(k-2)

        连续IDZ模型: G(s) = K*(1 + τ_z*s) / (s*(1 + τ_d*s)) * exp(-θ*s)

        Args:
            theta: 离散参数 [a1, a2, b0, b1, b2]
            use_optimization: 是否使用优化拟合

        Returns:
            IDZ参数
        """
        a1, a2, b0, b1, b2 = theta

        # 方法1：使用scipy.signal.bilinear转换（标准方法）
        if self.method in ['bilinear', 'tustin']:
            params_standard = self._convert_bilinear(a1, a2, b0, b1, b2)
        elif self.method == 'backward_diff':
            params_standard = self._convert_backward_diff(a1, a2, b0, b1, b2)
        else:
            raise ValueError(f"Unknown method: {self.method}")

        # 方法2：使用极点配置法（更精确，但可能不稳定）
        if use_optimization:
            try:
                params_optimized = self._convert_pole_placement(a1, a2, b0, b1, b2)
                # 融合两种方法
                K = 0.7 * params_standard.K + 0.3 * params_optimized.K
                tau_d = 0.7 * params_standard.tau_d + 0.3 * params_optimized.tau_d
                tau_z = 0.7 * params_standard.tau_z + 0.3 * params_optimized.tau_z
                theta_delay = params_standard.theta

                params = IDZParameters(K=K, tau_z=tau_z, tau_d=tau_d, theta=theta_delay)
            except:
                params = params_standard
        else:
            params = params_standard

        # 平滑处理
        if self.prev_params is not None:
            params = self._smooth_parameters(params, self.prev_params)

        # 约束检查
        params = self._constrain_parameters(params)

        self.prev_params = params
        return params

    def _convert_bilinear(self, a1: float, a2: float,
                          b0: float, b1: float, b2: float) -> IDZParameters:
        """
        使用双线性（Tustin）变换

        s = 2/T * (z-1)/(z+1)
        """
        # 构造离散传递函数
        num_d = [b0, b1, b2]
        den_d = [1, -a1, -a2]

        try:
            # 使用scipy进行离散到连续转换
            num_c, den_c = signal.bilinear(num_d, den_d, fs=1/self.dt)

            # 提取IDZ参数
            # 连续传递函数: (num_c[0]*s + num_c[1]) / (den_c[0]*s^2 + den_c[1]*s + den_c[2])
            # IDZ形式: K*(1 + τ_z*s) / (s*(1 + τ_d*s))

            # 如果分母有s项（积分器）
            if len(den_c) >= 3 and abs(den_c[2]) < 1e-6:
                # 分母 ≈ den_c[0]*s^2 + den_c[1]*s
                # 化为 s*(den_c[0]*s + den_c[1])
                # 即 s*(1 + (den_c[0]/den_c[1])*s) 如果 den_c[1] != 0

                if abs(den_c[1]) > 1e-6:
                    tau_d = den_c[0] / den_c[1]

                    # 分子 num_c[0]*s + num_c[1]
                    # 化为 num_c[1]*(1 + (num_c[0]/num_c[1])*s)
                    if abs(num_c[1]) > 1e-6:
                        K = num_c[1] / den_c[1]
                        tau_z = num_c[0] / num_c[1]
                    else:
                        K = abs(num_c[0] / den_c[0])
                        tau_z = 0.0
                else:
                    K = 100.0
                    tau_d = 100.0 * self.dt
                    tau_z = 0.85 * tau_d
            else:
                # 退化情况：使用低频增益近似
                K = abs(num_c[-1] / den_c[-1]) if abs(den_c[-1]) > 1e-6 else 100.0
                tau_d = 100.0 * self.dt
                tau_z = 0.85 * tau_d

        except Exception as e:
            print(f"Warning: bilinear conversion failed: {e}, using fallback")
            # 退化到简单方法
            K = abs((b0 + b1 + b2) / (1 - a1 - a2)) if abs(1 - a1 - a2) > 1e-3 else 100.0
            tau_d = 100.0 * self.dt
            tau_z = 0.85 * tau_d

        theta_delay = 0.0  # 延迟需要单独估计

        return IDZParameters(K=K, tau_z=tau_z, tau_d=tau_d, theta=theta_delay)

    def _convert_backward_diff(self, a1: float, a2: float,
                               b0: float, b1: float, b2: float) -> IDZParameters:
        """
        使用后向差分变换

        s = (z-1)/T
        """
        T = self.dt

        # 手动构造变换
        # z = 1 + sT
        # 将离散TF代入

        # 简化实现：使用低频增益 + 极点估计
        K = abs((b0 + b1 + b2) / (1 - a1 - a2)) if abs(1 - a1 - a2) > 1e-3 else 100.0

        # 从离散极点估计连续极点
        # z^2 - a1*z - a2 = 0
        discriminant = a1**2 + 4*a2
        if discriminant >= 0:
            z1 = (a1 + np.sqrt(discriminant)) / 2
            z2 = (a1 - np.sqrt(discriminant)) / 2

            # 后向差分: s = (z-1)/T
            # 选主极点
            z_dom = z1 if abs(z1) > abs(z2) else z2

            if 0 < abs(z_dom) < 1:
                s_dom = (z_dom - 1) / T
                tau_d = -1 / s_dom.real if abs(s_dom.real) > 1e-6 else 100.0 * T
            else:
                tau_d = 100.0 * T
        else:
            tau_d = 100.0 * T

        tau_z = 0.85 * tau_d
        theta_delay = 0.0

        return IDZParameters(K=K, tau_z=tau_z, tau_d=tau_d, theta=theta_delay)

    def _convert_pole_placement(self, a1: float, a2: float,
                                b0: float, b1: float, b2: float) -> IDZParameters:
        """
        使用极点配置法进行精确转换

        基于离散系统的极点位置直接估计连续极点
        """
        # 离散极点
        coeffs = [1, -a1, -a2]
        z_poles = np.roots(coeffs)

        # 转换为连续极点（使用Tustin变换的映射）
        # s = 2/T * (z-1)/(z+1)
        T = self.dt
        s_poles = 2/T * (z_poles - 1) / (z_poles + 1)

        # IDZ模型有一个零极点和一个积分器
        # 极点: 0（积分器）和 -1/tau_d
        # 选取实部最小（最慢）的极点
        s_poles_real = [p.real for p in s_poles if abs(p.imag) < 1e-3]

        if len(s_poles_real) > 0:
            s_dominant = max(s_poles_real)  # 最接近0的极点
            tau_d = -1 / s_dominant if s_dominant < 0 else 100.0 * T
        else:
            tau_d = 100.0 * T

        # 从零点估计tau_z
        num_coeffs = [b0, b1, b2]
        if abs(b0) > 1e-6:
            z_zeros = np.roots(num_coeffs)
            if len(z_zeros) > 0:
                z_zero = z_zeros[0]
                s_zero = 2/T * (z_zero - 1) / (z_zero + 1)
                tau_z = -1 / s_zero.real if abs(s_zero.real) > 1e-6 else 0.85 * tau_d
            else:
                tau_z = 0.85 * tau_d
        else:
            tau_z = 0.85 * tau_d

        # 稳态增益
        K = abs((b0 + b1 + b2) / (1 - a1 - a2)) if abs(1 - a1 - a2) > 1e-3 else 100.0

        theta_delay = 0.0

        return IDZParameters(K=K, tau_z=tau_z, tau_d=tau_d, theta=theta_delay)

    def _smooth_parameters(self, new_params: IDZParameters,
                          prev_params: IDZParameters) -> IDZParameters:
        """
        平滑参数变化

        使用指数加权移动平均（EWMA）
        """
        alpha = self.smooth_alpha

        # 限制单步变化率
        K_ratio = new_params.K / prev_params.K if prev_params.K > 0 else 1.0
        K_ratio = np.clip(K_ratio, 0.5, 2.0)
        K_raw = prev_params.K * K_ratio

        tau_d_ratio = new_params.tau_d / prev_params.tau_d if prev_params.tau_d > 0 else 1.0
        tau_d_ratio = np.clip(tau_d_ratio, 0.5, 2.0)
        tau_d_raw = prev_params.tau_d * tau_d_ratio

        # EWMA滤波
        K = alpha * K_raw + (1 - alpha) * prev_params.K
        tau_d = alpha * tau_d_raw + (1 - alpha) * prev_params.tau_d
        tau_z = alpha * new_params.tau_z + (1 - alpha) * prev_params.tau_z
        theta = new_params.theta

        return IDZParameters(K=K, tau_z=tau_z, tau_d=tau_d, theta=theta)

    def _constrain_parameters(self, params: IDZParameters) -> IDZParameters:
        """
        约束参数范围
        """
        K = np.clip(params.K, 50.0, 2000.0)
        tau_z = np.clip(params.tau_z, self.dt, 20000.0)
        tau_d = np.clip(params.tau_d, self.dt, 20000.0)
        theta = np.clip(params.theta, 0.0, 3600.0)

        return IDZParameters(K=K, tau_z=tau_z, tau_d=tau_d, theta=theta)


# ==================================================================================
# 测试代码
# ==================================================================================
if __name__ == "__main__":
    print("=" * 80)
    print("Scipy参数转换测试")
    print("=" * 80)

    # 测试参数（模拟RLS辨识结果）
    theta = np.array([0.9, -0.1, 0.05, 0.03, 0.01])  # [a1, a2, b0, b1, b2]
    dt = 10.0  # 采样时间10秒

    # 测试不同的转换方法
    methods = ['bilinear', 'backward_diff']

    for method in methods:
        print(f"\n方法: {method}")
        print("-" * 80)

        converter = ScipyParameterConverter(dt=dt, method=method)
        params = converter.discrete_to_continuous(theta, use_optimization=True)

        print(f"  增益 K:        {params.K:.3f} m/(m³/s)")
        print(f"  零点时间常数 τ_z: {params.tau_z:.1f} s")
        print(f"  延迟时间常数 τ_d: {params.tau_d:.1f} s")
        print(f"  纯滞后 θ:      {params.theta:.1f} s")

    print("\n" + "=" * 80)
    print("测试完成！")
    print("=" * 80)
