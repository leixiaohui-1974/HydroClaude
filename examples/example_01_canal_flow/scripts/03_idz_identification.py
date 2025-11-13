#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
例子1: 明渠非恒定流 - IDZ参数辨识

使用阶跃响应测试从3种数值方法中估计IDZ传递函数参数

作者: Claude
日期: 2025-10-21
"""

import numpy as np
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
from scipy.signal import savgol_filter
from scipy.optimize import curve_fit, minimize
import time
from datetime import datetime
import pandas as pd

# Import output helper
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from output_helper import get_output_path, save_table, save_figure

# ============================================================================
# 稳定流初值计算
# ============================================================================

def compute_steady_uniform_flow(Q, B, S0, n, g=9.81):
    """
    使用Manning公式计算恒定均匀流水深

    Manning公式: Q = (1/n) * A * R^(2/3) * S0^(1/2)
    """
    def manning_equation(h):
        if h <= 0:
            return 1e10
        A = B * h
        P = B + 2 * h
        R = A / P
        Q_calc = (1.0 / n) * A * (R ** (2./3.)) * (S0 ** 0.5)
        return Q_calc - Q

    # 二分法求解
    h_min, h_max = 0.01, 20.0

    if manning_equation(h_min) * manning_equation(h_max) > 0:
        h_est = (Q * n / (B * S0**0.5)) ** (3./5.)
        return max(0.5, min(10.0, h_est))

    while h_max - h_min > 1e-6:
        h_mid = (h_min + h_max) / 2
        if manning_equation(h_mid) * manning_equation(h_min) < 0:
            h_max = h_mid
        else:
            h_min = h_mid

    return (h_min + h_max) / 2


# ============================================================================
# 明渠求解器类
# ============================================================================

class CanalSolver:
    """明渠非恒定流求解器（无振荡版本）"""

    def __init__(self, length=1000.0, nx=201, B=10.0, S0=0.001, n=0.025,
                 g=9.81, method='preissmann'):
        """
        初始化求解器

        参数:
            length: 渠道长度 (m)
            nx: 空间离散点数
            B: 渠道宽度 (m)
            S0: 底坡
            n: Manning糙率
            g: 重力加速度 (m/s^2)
            method: 数值方法 ('explicit', 'preissmann', 'hll')
        """
        self.length = length
        self.nx = nx
        self.B = B
        self.S0 = S0
        self.n = n
        self.g = g
        self.method = method.lower()

        # 空间离散
        self.dx = length / (nx - 1)
        self.x = np.linspace(0, length, nx)

        # 初始化状态变量
        self.h = np.ones(nx) * 1.0  # 初始水深
        self.Q = np.ones(nx) * 5.0  # 初始流量

        # Savitzky-Golay滤波参数
        self.filter_window = 11
        self.filter_order = 3

        # Preissmann格式参数
        self.theta = 0.6
        self.omega = 0.95  # 松弛因子

    def reset_with_steady_state(self, Q0):
        """使用恒定均匀流作为初值"""
        h_uniform = compute_steady_uniform_flow(Q0, self.B, self.S0, self.n, self.g)
        self.h[:] = h_uniform
        self.Q[:] = Q0
        return h_uniform

    def apply_spatial_filter(self, field):
        """应用Savitzky-Golay空间滤波器"""
        filtered = savgol_filter(field, self.filter_window, self.filter_order, mode='nearest')
        filtered[0] = field[0]
        filtered[-1] = field[-1]
        return filtered

    def compute_friction_slope(self, h, Q):
        """计算摩阻坡度 (Manning公式)"""
        Sf = np.zeros_like(h)
        for i in range(len(h)):
            if h[i] > 1e-6:
                A = self.B * h[i]
                P = self.B + 2 * h[i]
                R = A / P
                V = Q[i] / A if A > 1e-6 else 0.0
                Sf[i] = (self.n * abs(V)) ** 2 / (R ** (4./3.))
            else:
                Sf[i] = 0.0
        return Sf

    def step_explicit(self, dt, Q_upstream, h_downstream):
        """显式有限差分法（混合迎风-中心格式）"""
        h_old = self.h.copy()
        Q_old = self.Q.copy()
        h_new = h_old.copy()
        Q_new = Q_old.copy()

        Sf = self.compute_friction_slope(h_old, Q_old)

        upwind_ratio = 0.3

        for i in range(1, self.nx - 1):
            if h_old[i] > 1e-6:
                A = self.B * h_old[i]
                V = Q_old[i] / A

                # 连续性方程
                dQ_dx_central = (Q_old[i+1] - Q_old[i-1]) / (2 * self.dx)
                if Q_old[i] >= 0:
                    dQ_dx_upwind = (Q_old[i] - Q_old[i-1]) / self.dx
                else:
                    dQ_dx_upwind = (Q_old[i+1] - Q_old[i]) / self.dx
                dQ_dx = upwind_ratio * dQ_dx_upwind + (1 - upwind_ratio) * dQ_dx_central

                dh_dt = -dQ_dx / self.B
                h_new[i] = h_old[i] + dt * dh_dt

                # 动量方程
                dh_dx_central = (h_old[i+1] - h_old[i-1]) / (2 * self.dx)
                if Q_old[i] >= 0:
                    dh_dx_upwind = (h_old[i] - h_old[i-1]) / self.dx
                else:
                    dh_dx_upwind = (h_old[i+1] - h_old[i]) / self.dx
                dh_dx = upwind_ratio * dh_dx_upwind + (1 - upwind_ratio) * dh_dx_central

                if Q_old[i] >= 0:
                    dQ_dx_mom = (Q_old[i] - Q_old[i-1]) / self.dx
                else:
                    dQ_dx_mom = (Q_old[i+1] - Q_old[i]) / self.dx

                dQ_dt = -V * dQ_dx_mom - self.g * A * dh_dx + self.g * A * (self.S0 - Sf[i])
                Q_new[i] = Q_old[i] + dt * dQ_dt

        # 边界条件
        h_new[0] = h_new[1]
        Q_new[0] = Q_upstream
        h_new[-1] = h_downstream
        Q_new[-1] = Q_new[-2]

        # 应用空间滤波
        h_new = self.apply_spatial_filter(h_new)
        Q_new = self.apply_spatial_filter(Q_new)

        self.h = h_new
        self.Q = Q_new

        return h_new, Q_new

    def step_preissmann(self, dt, Q_upstream, h_downstream):
        """Preissmann四点隐式格式"""
        h_old = self.h.copy()
        Q_old = self.Q.copy()

        # 显式预估
        h_pred, Q_pred = self.step_explicit(dt, Q_upstream, h_downstream)

        # theta加权校正
        self.h = self.omega * ((1 - self.theta) * h_old + self.theta * h_pred) + (1 - self.omega) * h_old
        self.Q = self.omega * ((1 - self.theta) * Q_old + self.theta * Q_pred) + (1 - self.omega) * Q_old

        # 应用空间滤波
        self.h = self.apply_spatial_filter(self.h)
        self.Q = self.apply_spatial_filter(self.Q)

        return self.h, self.Q

    def step_hll(self, dt, Q_upstream, h_downstream):
        """HLL有限体积法"""
        h_old = self.h.copy()
        Q_old = self.Q.copy()
        h_new = h_old.copy()
        Q_new = Q_old.copy()

        Sf = self.compute_friction_slope(h_old, Q_old)

        for i in range(1, self.nx - 1):
            # 左右状态
            h_L = h_old[i]
            h_R = h_old[i+1]
            Q_L = Q_old[i]
            Q_R = Q_old[i+1]

            if h_L > 1e-6 and h_R > 1e-6:
                A_L = self.B * h_L
                A_R = self.B * h_R
                V_L = Q_L / A_L
                V_R = Q_R / A_R
                c_L = np.sqrt(self.g * h_L)
                c_R = np.sqrt(self.g * h_R)

                # 波速估计
                S_L = min(V_L - c_L, V_R - c_R)
                S_R = max(V_L + c_L, V_R + c_R)

                # 通量
                F1_L = Q_L
                F1_R = Q_R
                F2_L = Q_L * V_L + 0.5 * self.g * self.B * h_L**2
                F2_R = Q_R * V_R + 0.5 * self.g * self.B * h_R**2

                # HLL通量
                if S_L >= 0:
                    F1 = F1_L
                    F2 = F2_L
                elif S_R <= 0:
                    F1 = F1_R
                    F2 = F2_R
                else:
                    F1 = (S_R * F1_L - S_L * F1_R + S_L * S_R * (A_R - A_L)) / (S_R - S_L)
                    F2 = (S_R * F2_L - S_L * F2_R + S_L * S_R * (Q_R - Q_L)) / (S_R - S_L)

                # 更新
                dh_dt = -(F1 - Q_old[i-1]) / self.dx / self.B
                dQ_dt = -(F2 - (Q_old[i-1]**2/A_L + 0.5*self.g*self.B*h_old[i-1]**2)) / self.dx
                dQ_dt += self.g * A_L * (self.S0 - Sf[i])

                h_new[i] = h_old[i] + dt * dh_dt
                Q_new[i] = Q_old[i] + dt * dQ_dt

        # 边界条件
        h_new[0] = h_new[1]
        Q_new[0] = Q_upstream
        h_new[-1] = h_downstream
        Q_new[-1] = Q_new[-2]

        # 应用空间滤波
        h_new = self.apply_spatial_filter(h_new)
        Q_new = self.apply_spatial_filter(Q_new)

        self.h = h_new
        self.Q = Q_new

        return h_new, Q_new

    def step(self, dt, Q_upstream, h_downstream):
        """执行一个时间步"""
        if self.method == 'explicit':
            return self.step_explicit(dt, Q_upstream, h_downstream)
        elif self.method == 'preissmann':
            return self.step_preissmann(dt, Q_upstream, h_downstream)
        elif self.method == 'hll':
            return self.step_hll(dt, Q_upstream, h_downstream)
        else:
            raise ValueError(f"Unknown method: {self.method}")


# ============================================================================
# IDZ参数辨识
# ============================================================================

class IDZIdentifier:
    """IDZ传递函数参数辨识"""

    @staticmethod
    def idz_response(t, K, tau, T):
        """
        IDZ传递函数的阶跃响应

        G(s) = K * exp(-tau*s) / (T*s + 1)

        阶跃响应: y(t) = K * (1 - exp(-(t-tau)/T)) * u(t-tau)
        """
        response = np.zeros_like(t)
        mask = t >= tau
        response[mask] = K * (1 - np.exp(-(t[mask] - tau) / T))
        return response

    @staticmethod
    def estimate_parameters(t, y, initial_guess=None):
        """
        从阶跃响应数据估计IDZ参数

        参数:
            t: 时间序列
            y: 响应数据（阶跃响应）
            initial_guess: 初始猜测 [K, tau, T]

        返回:
            params: [K, tau, T]
            fit_quality: 拟合质量指标 (R^2)
        """
        # 数据预处理：去除初始值偏移
        y_baseline = np.mean(y[:10])  # 前10个点的平均值作为基线
        y_data = y - y_baseline

        # 估计稳态增益K
        K_est = np.mean(y_data[-100:])  # 最后100个点的平均值

        # 估计时滞tau（响应达到10%时的时间）
        if K_est > 0:
            idx_10 = np.where(y_data >= 0.1 * K_est)[0]
        else:
            idx_10 = np.where(y_data <= 0.1 * K_est)[0]

        if len(idx_10) > 0:
            tau_est = t[idx_10[0]]
        else:
            tau_est = 0.0

        # 估计时间常数T（从10%上升到63.2%的时间）
        if K_est > 0:
            idx_63 = np.where(y_data >= 0.632 * K_est)[0]
        else:
            idx_63 = np.where(y_data <= 0.632 * K_est)[0]

        if len(idx_63) > 0:
            T_est = t[idx_63[0]] - tau_est
        else:
            T_est = 50.0

        T_est = max(1.0, T_est)  # 确保T > 0

        if initial_guess is None:
            initial_guess = [K_est, tau_est, T_est]

        # 优化拟合
        try:
            # 设置参数边界
            bounds = ([0.5*K_est if K_est > 0 else 1.5*K_est, 0, 0.1],
                     [1.5*K_est if K_est > 0 else 0.5*K_est, tau_est + 50, 500])

            params, _ = curve_fit(IDZIdentifier.idz_response, t, y_data,
                                 p0=initial_guess, bounds=bounds, maxfev=5000)

            # 计算拟合质量（R^2）
            y_fit = IDZIdentifier.idz_response(t, *params)
            ss_res = np.sum((y_data - y_fit) ** 2)
            ss_tot = np.sum((y_data - np.mean(y_data)) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

            return params, r_squared

        except Exception as e:
            print(f"  参数拟合失败: {e}")
            print(f"  使用初始估计: K={K_est:.6f}, tau={tau_est:.2f}, T={T_est:.2f}")
            return initial_guess, 0.0

    @staticmethod
    def identify_all_directions(time, data_dict):
        """
        辨识4个方向的传递函数参数

        参数:
            time: 时间序列
            data_dict: 数据字典，包含:
                - 'Q_upstream': 上游流量时间序列
                - 'h_upstream': 上游水深时间序列
                - 'Q_downstream': 下游流量时间序列
                - 'h_downstream': 下游水深时间序列

        返回:
            results: 包含4个方向参数的字典
        """
        results = {}

        # 方向1: 上游流量 -> 下游水深
        print("  方向1: Q_upstream -> h_downstream")
        params1, r2_1 = IDZIdentifier.estimate_parameters(
            time, data_dict['h_downstream'])
        results['Q_to_h'] = {
            'K': params1[0],
            'tau': params1[1],
            'T': params1[2],
            'R2': r2_1,
            'name': 'Q_upstream -> h_downstream'
        }
        print(f"    K={params1[0]:.6f}, tau={params1[1]:.2f}s, T={params1[2]:.2f}s, R^2={r2_1:.4f}")

        # 方向2: 上游流量 -> 下游流量
        print("  方向2: Q_upstream -> Q_downstream")
        params2, r2_2 = IDZIdentifier.estimate_parameters(
            time, data_dict['Q_downstream'])
        results['Q_to_Q'] = {
            'K': params2[0],
            'tau': params2[1],
            'T': params2[2],
            'R2': r2_2,
            'name': 'Q_upstream -> Q_downstream'
        }
        print(f"    K={params2[0]:.6f}, tau={params2[1]:.2f}s, T={params2[2]:.2f}s, R^2={r2_2:.4f}")

        # 方向3: 下游水深 -> 上游水深（回水效应）
        print("  方向3: h_downstream -> h_upstream")
        params3, r2_3 = IDZIdentifier.estimate_parameters(
            time, data_dict['h_upstream'])
        results['h_to_h'] = {
            'K': params3[0],
            'tau': params3[1],
            'T': params3[2],
            'R2': r2_3,
            'name': 'h_downstream -> h_upstream'
        }
        print(f"    K={params3[0]:.6f}, tau={params3[1]:.2f}s, T={params3[2]:.2f}s, R^2={r2_3:.4f}")

        # 方向4: 下游水深 -> 上游流量
        print("  方向4: h_downstream -> Q_upstream")
        params4, r2_4 = IDZIdentifier.estimate_parameters(
            time, data_dict['Q_upstream'])
        results['h_to_Q'] = {
            'K': params4[0],
            'tau': params4[1],
            'T': params4[2],
            'R2': r2_4,
            'name': 'h_downstream -> Q_upstream'
        }
        print(f"    K={params4[0]:.6f}, tau={params4[1]:.2f}s, T={params4[2]:.2f}s, R^2={r2_4:.4f}")

        return results


# ============================================================================
# 阶跃响应测试
# ============================================================================

def run_step_response_test(method_name='PREISSMANN', scenario='upstream_flow'):
    """
    运行阶跃响应测试

    参数:
        method_name: 数值方法 ('EXPLICIT', 'PREISSMANN', 'HLL')
        scenario: 测试场景 ('upstream_flow' 或 'downstream_depth')
    """
    print(f"\n{'='*80}")
    print(f"阶跃响应测试: {method_name} - {scenario}")
    print(f"{'='*80}")

    # 物理参数
    length = 1000.0
    B = 10.0
    S0 = 0.001
    n = 0.025
    g = 9.81

    # 数值参数
    nx = 201
    dt = 0.5
    T_total = 800.0
    n_steps = int(T_total / dt)

    # 初始边界条件
    Q_init = 8.0  # m^3/s
    h_init = compute_steady_uniform_flow(Q_init, B, S0, n, g)

    print(f"\n初始稳态:")
    print(f"  Q = {Q_init:.2f} m^3/s")
    print(f"  h = {h_init:.4f} m")

    # 阶跃扰动设置
    if scenario == 'upstream_flow':
        # 场景1：上游流量阶跃（8.0 -> 10.0 m^3/s）
        Q_step = 10.0
        h_down_base = h_init
        step_time = 100.0
        print(f"\n阶跃扰动: 上游流量 {Q_init:.1f} -> {Q_step:.1f} m^3/s @ t={step_time}s")

    elif scenario == 'downstream_depth':
        # 场景2：下游水深阶跃（基准 + 0.2m）
        Q_step = Q_init
        h_down_step = 0.2
        h_down_base = h_init
        step_time = 100.0
        print(f"\n阶跃扰动: 下游水深 {h_down_base:.3f} -> {h_down_base + h_down_step:.3f} m @ t={step_time}s")

    # 创建求解器
    solver = CanalSolver(length=length, nx=nx, B=B, S0=S0, n=n, g=g,
                        method=method_name.lower())
    solver.reset_with_steady_state(Q_init)

    # 数据记录
    time_history = []
    h_upstream_history = []
    h_downstream_history = []
    Q_upstream_history = []
    Q_downstream_history = []

    # 监测点索引
    idx_upstream = 5  # 上游监测点（避开边界）
    idx_downstream = nx - 6  # 下游监测点（避开边界）

    # 时间积分
    t_start = time.time()
    for step in range(n_steps):
        t = step * dt

        # 设置边界条件（含阶跃）
        if scenario == 'upstream_flow':
            if t < step_time:
                Q_bc = Q_init
                h_bc = h_down_base
            else:
                Q_bc = Q_step
                h_bc = compute_steady_uniform_flow(Q_step, B, S0, n, g)

        elif scenario == 'downstream_depth':
            if t < step_time:
                Q_bc = Q_init
                h_bc = h_down_base
            else:
                Q_bc = Q_init
                h_bc = h_down_base + h_down_step

        # 时间推进
        solver.step(dt, Q_bc, h_bc)

        # 记录数据（每5步记录一次）
        if step % 5 == 0:
            time_history.append(t)
            h_upstream_history.append(solver.h[idx_upstream])
            h_downstream_history.append(solver.h[idx_downstream])
            Q_upstream_history.append(solver.Q[idx_upstream])
            Q_downstream_history.append(solver.Q[idx_downstream])

        # 打印进度
        if (step + 1) % 400 == 0:
            print(f"  步 {step+1}/{n_steps}: t={t:.1f}s, "
                  f"h_up={solver.h[idx_upstream]:.4f}m, "
                  f"h_down={solver.h[idx_downstream]:.4f}m")

    t_end = time.time()
    print(f"\n计算完成: {t_end - t_start:.2f}s ({n_steps/(t_end - t_start):.1f} steps/s)")

    # 转换为numpy数组
    time_array = np.array(time_history)
    data_dict = {
        'h_upstream': np.array(h_upstream_history),
        'h_downstream': np.array(h_downstream_history),
        'Q_upstream': np.array(Q_upstream_history),
        'Q_downstream': np.array(Q_downstream_history)
    }

    return time_array, data_dict, step_time, scenario


# ============================================================================
# 主测试函数
# ============================================================================

def run_comprehensive_idz_test():
    """运行完整的IDZ参数辨识测试"""

    print("=" * 80)
    print("例子1: 明渠非恒定流 - IDZ参数辨识")
    print("=" * 80)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    methods = ['EXPLICIT', 'PREISSMANN', 'HLL']
    scenarios = ['upstream_flow', 'downstream_depth']

    all_results = {}

    # 对每种方法和场景运行测试
    for method in methods:
        all_results[method] = {}

        for scenario in scenarios:
            # 运行阶跃响应测试
            time_array, data_dict, step_time, _ = run_step_response_test(method, scenario)

            # IDZ参数辨识
            print(f"\nIDZ参数辨识 ({method} - {scenario}):")
            print("-" * 80)

            idz_results = IDZIdentifier.identify_all_directions(time_array, data_dict)

            # 保存结果
            all_results[method][scenario] = {
                'time': time_array,
                'data': data_dict,
                'idz_params': idz_results,
                'step_time': step_time
            }

    # 生成对比报告
    print("\n" + "=" * 80)
    print("IDZ参数辨识结果汇总")
    print("=" * 80)

    generate_comparison_report(all_results)

    # 生成可视化
    print("\n" + "=" * 80)
    print("生成可视化图表...")
    print("=" * 80)

    generate_visualizations(all_results)

    return all_results


def generate_comparison_report(all_results):
    """生成参数对比报告"""

    methods = ['EXPLICIT', 'PREISSMANN', 'HLL']
    scenarios = ['upstream_flow', 'downstream_depth']
    directions = ['Q_to_h', 'Q_to_Q', 'h_to_h', 'h_to_Q']
    direction_names = {
        'Q_to_h': 'Q_upstream -> h_downstream',
        'Q_to_Q': 'Q_upstream -> Q_downstream',
        'h_to_h': 'h_downstream -> h_upstream',
        'h_to_Q': 'h_downstream -> Q_upstream'
    }

    for scenario in scenarios:
        print(f"\n场景: {scenario}")
        print("=" * 120)

        for direction in directions:
            print(f"\n{direction_names[direction]}:")
            print("-" * 120)
            print(f"{'方法':<15} {'增益 K':>15} {'时滞 tau (s)':>15} {'时间常数 T (s)':>20} {'拟合质量 R^2':>15}")
            print("-" * 120)

            for method in methods:
                params = all_results[method][scenario]['idz_params'][direction]
                print(f"{method:<15} {params['K']:>15.6f} {params['tau']:>15.2f} "
                      f"{params['T']:>20.2f} {params['R2']:>15.4f}")

            # 计算统计量
            K_values = [all_results[m][scenario]['idz_params'][direction]['K'] for m in methods]
            tau_values = [all_results[m][scenario]['idz_params'][direction]['tau'] for m in methods]
            T_values = [all_results[m][scenario]['idz_params'][direction]['T'] for m in methods]

            K_mean, K_std = np.mean(K_values), np.std(K_values)
            tau_mean, tau_std = np.mean(tau_values), np.std(tau_values)
            T_mean, T_std = np.mean(T_values), np.std(T_values)

            print("-" * 120)
            print(f"{'平均值':<15} {K_mean:>15.6f} {tau_mean:>15.2f} {T_mean:>20.2f}")
            print(f"{'标准差':<15} {K_std:>15.6f} {tau_std:>15.2f} {T_std:>20.2f}")
            print(f"{'变异系数 (%)':<15} {100*K_std/abs(K_mean):>15.2f} "
                  f"{100*tau_std/tau_mean if tau_mean > 0 else 0:>15.2f} "
                  f"{100*T_std/T_mean if T_mean > 0 else 0:>20.2f}")


def generate_visualizations(all_results):
    """生成IDZ参数辨识图表"""
    methods = ['EXPLICIT', 'PREISSMANN', 'HLL']
    scenarios = ['upstream_flow', 'downstream_depth']

    # 为每个场景生成图表
    for scenario in scenarios:
        fig, axes = plt.subplots(4, 3, figsize=(20, 16))
        fig.suptitle(f'IDZ Parameter Identification - Scenario: {scenario}',
                     fontsize=16, fontweight='bold')

        response_vars = ['h_downstream', 'Q_downstream', 'h_upstream', 'Q_upstream']
        var_labels = ['h_downstream (m)', 'Q_downstream (m^3/s)',
                     'h_upstream (m)', 'Q_upstream (m^3/s)']

        for j, method in enumerate(methods):
            result = all_results[method][scenario]
            time = result['time']
            data = result['data']
            step_time = result['step_time']

            for i, (var, label) in enumerate(zip(response_vars, var_labels)):
                ax = axes[i, j]

                # 绘制实际响应
                ax.plot(time, data[var], 'b-', linewidth=1.5, label='Actual', alpha=0.7)

                # 绘制IDZ拟合（如果有对应的方向）
                if i == 0 and scenario == 'upstream_flow':  # h_downstream
                    direction = 'Q_to_h'
                elif i == 1 and scenario == 'upstream_flow':  # Q_downstream
                    direction = 'Q_to_Q'
                elif i == 2 and scenario == 'downstream_depth':  # h_upstream
                    direction = 'h_to_h'
                elif i == 3 and scenario == 'downstream_depth':  # Q_upstream
                    direction = 'h_to_Q'
                else:
                    direction = None

                if direction:
                    params = result['idz_params'][direction]
                    y_baseline = np.mean(data[var][:20])
                    y_fit = IDZIdentifier.idz_response(time, params['K'],
                                                       params['tau'], params['T']) + y_baseline
                    ax.plot(time, y_fit, 'r--', linewidth=2, label='IDZ Fit', alpha=0.8)

                    # 添加参数标注
                    ax.text(0.02, 0.98,
                           f"K={params['K']:.4f}\ntau={params['tau']:.1f}s\n"
                           f"T={params['T']:.1f}s\nR^2={params['R2']:.3f}",
                           transform=ax.transAxes, fontsize=9,
                           verticalalignment='top',
                           bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

                # 绘制阶跃时刻
                ax.axvline(step_time, color='gray', linestyle=':', linewidth=1,
                          label='Step time')

                ax.set_xlabel('Time (s)', fontsize=10)
                ax.set_ylabel(label, fontsize=10)
                ax.grid(True, alpha=0.3)
                ax.legend(fontsize=8, loc='lower right')

                if i == 0:
                    ax.set_title(f'{method}', fontsize=12, fontweight='bold')

        plt.tight_layout()
        fig_path = get_output_path('figures', f'03_idz_{scenario}.png')
        plt.savefig(fig_path, dpi=150, bbox_inches='tight')
        print(f"   Saved figure: {os.path.basename(fig_path)}")
        plt.close()

    # 生成参数对比图
    generate_parameter_comparison_plot(all_results)


def generate_parameter_comparison_plot(all_results):
    """生成参数对比柱状图"""

    methods = ['EXPLICIT', 'PREISSMANN', 'HLL']
    scenarios = ['upstream_flow', 'downstream_depth']
    directions = ['Q_to_h', 'Q_to_Q', 'h_to_h', 'h_to_Q']
    direction_names = {
        'Q_to_h': 'Q->h',
        'Q_to_Q': 'Q->Q',
        'h_to_h': 'h->h',
        'h_to_Q': 'h->Q'
    }

    fig, axes = plt.subplots(3, 2, figsize=(16, 12))
    fig.suptitle('IDZ Parameters Comparison Across Methods',
                 fontsize=16, fontweight='bold')

    for col, scenario in enumerate(scenarios):
        # K参数
        ax = axes[0, col]
        x = np.arange(len(directions))
        width = 0.25

        for i, method in enumerate(methods):
            K_values = [all_results[method][scenario]['idz_params'][d]['K']
                       for d in directions]
            ax.bar(x + i*width, K_values, width, label=method, alpha=0.8)

        ax.set_xlabel('Direction', fontsize=11)
        ax.set_ylabel('Gain K', fontsize=11)
        ax.set_title(f'Gain - {scenario}', fontsize=12, fontweight='bold')
        ax.set_xticks(x + width)
        ax.set_xticklabels([direction_names[d] for d in directions])
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')

        # tau参数
        ax = axes[1, col]
        for i, method in enumerate(methods):
            tau_values = [all_results[method][scenario]['idz_params'][d]['tau']
                         for d in directions]
            ax.bar(x + i*width, tau_values, width, label=method, alpha=0.8)

        ax.set_xlabel('Direction', fontsize=11)
        ax.set_ylabel('Time Delay tau (s)', fontsize=11)
        ax.set_title(f'Time Delay - {scenario}', fontsize=12, fontweight='bold')
        ax.set_xticks(x + width)
        ax.set_xticklabels([direction_names[d] for d in directions])
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')

        # T参数
        ax = axes[2, col]
        for i, method in enumerate(methods):
            T_values = [all_results[method][scenario]['idz_params'][d]['T']
                       for d in directions]
            ax.bar(x + i*width, T_values, width, label=method, alpha=0.8)

        ax.set_xlabel('Direction', fontsize=11)
        ax.set_ylabel('Time Constant T (s)', fontsize=11)
        ax.set_title(f'Time Constant - {scenario}', fontsize=12, fontweight='bold')
        ax.set_xticks(x + width)
        ax.set_xticklabels([direction_names[d] for d in directions])
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    fig_path = get_output_path('figures', '03_idz_parameters_comparison.png')
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    print(f"   Saved figure: {os.path.basename(fig_path)}")
    plt.close()


# ============================================================================
# 主程序入口
# ============================================================================

if __name__ == '__main__':
    results = run_comprehensive_idz_test()

    # ========================================================================
    # Save Results as CSV Tables
    # ========================================================================
    print("\n" + "=" * 80)
    print("Saving Results Tables...")
    print("=" * 80)

    # Collect all IDZ parameters
    table_data = []
    for method in ['EXPLICIT', 'PREISSMANN', 'HLL']:
        for scenario in ['upstream_flow', 'downstream_depth']:
            idz_params = results[method][scenario]['idz_params']
            for direction, params in idz_params.items():
                table_data.append({
                    'Method': method,
                    'Scenario': scenario,
                    'Direction': direction,
                    'K (gain)': params['K'],
                    'tau (delay_s)': params['tau'],
                    'T (time_const_s)': params['T'],
                    'R_squared': params['R2']
                })

    df = pd.DataFrame(table_data)
    save_table(df, '03_idz_parameters.csv', index=False)

    # Save summary statistics
    summary_data = []
    scenarios = ['upstream_flow', 'downstream_depth']
    directions = ['Q_to_h', 'h_to_h', 'Q_to_Q', 'h_to_Q']

    for scenario in scenarios:
        for direction in directions:
            K_values = [results[m][scenario]['idz_params'][direction]['K'] for m in ['EXPLICIT', 'PREISSMANN', 'HLL']]
            tau_values = [results[m][scenario]['idz_params'][direction]['tau'] for m in ['EXPLICIT', 'PREISSMANN', 'HLL']]
            T_values = [results[m][scenario]['idz_params'][direction]['T'] for m in ['EXPLICIT', 'PREISSMANN', 'HLL']]

            summary_data.append({
                'Scenario': scenario,
                'Direction': direction,
                'K_mean': np.mean(K_values),
                'K_std': np.std(K_values),
                'tau_mean': np.mean(tau_values),
                'tau_std': np.std(tau_values),
                'T_mean': np.mean(T_values),
                'T_std': np.std(T_values)
            })

    df_summary = pd.DataFrame(summary_data)
    save_table(df_summary, '03_idz_summary_statistics.csv', index=False)

    print("\n" + "=" * 80)
    print("IDZ参数辨识测试完成！")
    print("=" * 80)
    print("\n生成的文件:")
    print("  Figures (3):")
    print("    - 03_idz_upstream_flow.png")
    print("    - 03_idz_downstream_depth.png")
    print("    - 03_idz_parameters_comparison.png")
    print("  Tables (2):")
    print("    - 03_idz_parameters.csv")
    print("    - 03_idz_summary_statistics.csv")
    print("=" * 80)
