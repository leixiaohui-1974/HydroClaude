#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Anderson加速算法

用于加速固定点迭代的收敛
比Aitken加速更适合非线性问题

作者: Claude
日期: 2025-10-22
"""

import numpy as np
from typing import Optional, Deque
from collections import deque


class AndersonAcceleration:
    """
    Anderson加速算法

    对于固定点迭代 x = g(x)，加速收敛

    原理：
    - 保存最近m个迭代的历史
    - 使用历史构造优化的下一步
    - 最小化残差的线性组合

    参考文献：
    Walker, H. F., & Ni, P. (2011). Anderson acceleration for
    fixed-point iterations. SIAM J. Numer. Anal., 49(4), 1715-1735.
    """

    def __init__(self,
                 m: int = 5,
                 beta: float = 1.0,
                 reg: float = 1e-8,
                 restart: bool = True):
        """
        Args:
            m: 历史深度（保存最近m个迭代）
            beta: 松弛参数（0-1），1表示无松弛
            reg: 正则化参数（避免数值不稳定）
            restart: 是否自动重启（当检测到发散时）
        """
        self.m = m
        self.beta = beta
        self.reg = reg
        self.restart = restart

        # 历史数据
        self.x_history: Deque = deque(maxlen=m)
        self.f_history: Deque = deque(maxlen=m)

        # 统计信息
        self.iteration = 0
        self.restart_count = 0

    def reset(self):
        """重置历史"""
        self.x_history.clear()
        self.f_history.clear()
        self.iteration = 0

    def compute_acceleration(self,
                            x_current: np.ndarray,
                            x_next: np.ndarray) -> np.ndarray:
        """
        计算Anderson加速后的下一步

        Args:
            x_current: 当前迭代值
            x_next: 固定点迭代的下一步（未加速）

        Returns:
            x_accelerated: 加速后的下一步
        """
        self.iteration += 1

        # 计算残差：f = g(x) - x = x_next - x_current
        f_current = x_next - x_current

        # 确保是数组（处理标量情况）
        x_current_arr = np.atleast_1d(x_current)
        f_current_arr = np.atleast_1d(f_current)

        # 添加到历史
        self.x_history.append(x_current_arr.copy())
        self.f_history.append(f_current_arr.copy())

        # 历史深度
        mk = len(self.x_history)

        if mk == 1:
            # 第一次迭代，无历史，直接返回
            return x_next

        # 构造残差差分矩阵
        # F = [f_{k-mk+1} - f_k, f_{k-mk+2} - f_k, ..., f_{k-1} - f_k]
        F = np.column_stack([
            self.f_history[i] - f_current_arr
            for i in range(mk - 1)
        ])

        # 求解最小二乘问题：min ||F·α||²
        # 使用QR分解（更稳定）
        try:
            # 添加正则化
            FtF = F.T @ F + self.reg * np.eye(mk - 1)
            Ftf = F.T @ f_current_arr

            # 求解
            alpha = np.linalg.solve(FtF, Ftf)

        except np.linalg.LinAlgError:
            # 如果求解失败，重启
            if self.restart:
                self.reset()
                self.restart_count += 1
            return x_next

        # 构造加速解
        # x_{k+1} = (1 - β)·x_k + β·(Σ γ_i·x_i)
        # 其中 γ_0 = 1 - Σα_i, γ_i = α_{i-1} (i≥1)

        gamma = np.zeros(mk)
        gamma[0] = 1.0 - np.sum(alpha)
        gamma[1:] = alpha

        # 加权平均
        x_bar = sum(gamma[i] * self.x_history[i] for i in range(mk))
        f_bar = sum(gamma[i] * self.f_history[i] for i in range(mk))

        # 加速解
        x_accelerated = x_bar + self.beta * f_bar

        # 如果输入是标量，返回标量
        if np.isscalar(x_current) or x_current.shape == ():
            return x_accelerated[0]

        return x_accelerated

    def get_statistics(self) -> dict:
        """获取统计信息"""
        return {
            'iterations': self.iteration,
            'restarts': self.restart_count,
            'history_depth': len(self.x_history),
            'max_depth': self.m
        }


def test_anderson_acceleration():
    """测试Anderson加速"""
    print("=" * 80)
    print("Anderson加速算法测试")
    print("=" * 80)

    # 测试问题：求解 x = cos(x)
    # 固定点迭代：x_{k+1} = cos(x_k)

    def fixed_point_iteration(x):
        """固定点迭代函数：g(x) = cos(x)"""
        return np.cos(x)

    # 解析解（近似）
    x_exact = 0.7390851332151607  # cos(x) = x 的解

    print("\n测试问题：求解 x = cos(x)")
    print(f"解析解: x ≈ {x_exact:.10f}")
    print()

    # 测试1：不使用加速
    print("测试1：标准固定点迭代（无加速）")
    print("-" * 80)

    x = 0.5  # 初值
    errors_no_accel = []

    for i in range(50):
        x_next = fixed_point_iteration(x)
        error = abs(x_next - x_exact)
        errors_no_accel.append(error)

        if i < 10 or i % 10 == 0:
            print(f"  Iter {i}: x = {x:.10f}, error = {error:.3e}")

        if error < 1e-10:
            print(f"  收敛于第 {i} 次迭代")
            break

        x = x_next

    # 测试2：使用Anderson加速
    print("\n测试2：Anderson加速")
    print("-" * 80)

    x = 0.5  # 初值
    anderson = AndersonAcceleration(m=5, beta=1.0)
    errors_anderson = []

    for i in range(50):
        x_next = fixed_point_iteration(x)
        x_accel = anderson.compute_acceleration(x, x_next)

        error = abs(x_accel - x_exact)
        errors_anderson.append(error)

        if i < 10 or i % 10 == 0:
            print(f"  Iter {i}: x = {x_accel:.10f}, error = {error:.3e}")

        if error < 1e-10:
            print(f"  收敛于第 {i} 次迭代")
            stats = anderson.get_statistics()
            print(f"  重启次数: {stats['restarts']}")
            break

        x = x_accel

    # 对比
    print("\n" + "=" * 80)
    print("性能对比")
    print("=" * 80)

    # 找到两种方法达到相同精度的迭代次数
    target_error = 1e-6

    iter_no_accel = next((i for i, e in enumerate(errors_no_accel) if e < target_error), len(errors_no_accel))
    iter_anderson = next((i for i, e in enumerate(errors_anderson) if e < target_error), len(errors_anderson))

    print(f"\n达到误差 < {target_error:.0e} 的迭代次数：")
    print(f"  无加速: {iter_no_accel} 次")
    print(f"  Anderson加速: {iter_anderson} 次")

    if iter_anderson < iter_no_accel:
        improvement = (iter_no_accel - iter_anderson) / iter_no_accel * 100
        print(f"  改善: {improvement:.1f}%")

    print("\n" + "=" * 80)


def test_anderson_on_nonlinear_system():
    """测试Anderson加速在非线性系统上的效果"""
    print("\n\n" + "=" * 80)
    print("Anderson加速 - 非线性系统测试")
    print("=" * 80)

    # 测试问题：求解非线性方程组
    # x1 = 0.5 * (x1 + x2)
    # x2 = 0.5 * (x1^2 + x2^2)

    def g(x):
        """固定点迭代函数"""
        x1, x2 = x
        return np.array([
            0.5 * (x1 + x2),
            0.5 * (x1**2 + x2**2)
        ])

    # 解析解（数值求解）
    from scipy.optimize import fsolve
    x_exact = fsolve(lambda x: g(x) - x, [0.5, 0.5])

    print(f"\n解析解: x = [{x_exact[0]:.6f}, {x_exact[1]:.6f}]")
    print()

    # 测试1：无加速
    print("测试1：标准固定点迭代")
    print("-" * 80)

    x = np.array([0.5, 0.5])

    for i in range(30):
        x_next = g(x)
        error = np.linalg.norm(x_next - x_exact)

        if i < 10 or i % 5 == 0:
            print(f"  Iter {i}: error = {error:.3e}")

        if error < 1e-8:
            print(f"  收敛于第 {i} 次迭代")
            break

        x = x_next

    # 测试2：Anderson加速
    print("\n测试2：Anderson加速")
    print("-" * 80)

    x = np.array([0.5, 0.5])
    anderson = AndersonAcceleration(m=3, beta=1.0)

    for i in range(30):
        x_next = g(x)
        x_accel = anderson.compute_acceleration(x, x_next)

        error = np.linalg.norm(x_accel - x_exact)

        if i < 10 or i % 5 == 0:
            print(f"  Iter {i}: error = {error:.3e}")

        if error < 1e-8:
            print(f"  收敛于第 {i} 次迭代")
            stats = anderson.get_statistics()
            print(f"  重启次数: {stats['restarts']}")
            break

        x = x_accel

    print("\n" + "=" * 80)


if __name__ == "__main__":
    test_anderson_acceleration()
    test_anderson_on_nonlinear_system()
