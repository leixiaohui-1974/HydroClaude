#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
性能优化模块测试
Test Performance Optimization Module

验证Numba JIT加速函数的正确性

Author: HydroClaude Team
Date: 2025-10-30
"""
import sys
import os

# ========== 路径设置 ==========
script_path = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(script_path))
sys.path.insert(0, project_root)


import pytest
import numpy as np

from network.pressure_pipe import PressurePipe
from utils.performance import (
    reynolds_number_jit,
    friction_factor_colebrook_jit,
    head_loss_darcy_jit,
    head_loss_complete_jit
)


class TestReynoldsNumberJIT:
    """测试雷诺数计算的JIT版本"""

    def test_reynolds_number_accuracy(self):
        """测试雷诺数计算准确性"""
        # 创建管道
        pipe = PressurePipe('test', 0.3, 100, 0.00026)

        # 测试流量范围
        Q_values = [0.01, 0.05, 0.1, 0.5, 1.0]

        for Q in Q_values:
            # 原始版本
            Re_orig = pipe.reynolds_number(Q)

            # JIT版本
            Re_jit = reynolds_number_jit(Q, pipe.D, pipe.A, 1.0e-6)

            # 验证精度
            assert abs(Re_orig - Re_jit) < 1e-6, \
                f"雷诺数不一致: Q={Q}, Re_orig={Re_orig}, Re_jit={Re_jit}"

    def test_zero_flow(self):
        """测试零流量"""
        Re = reynolds_number_jit(0.0, 0.3, 0.07, 1.0e-6)
        assert Re == 0.0


class TestFrictionFactorColebrookJIT:
    """测试Colebrook-White摩阻系数的JIT版本"""

    def test_friction_factor_accuracy(self):
        """测试摩阻系数计算准确性"""
        # 创建管道
        pipe = PressurePipe('test', 0.3, 100, 0.00026)

        # 测试流量范围
        Q_values = [0.01, 0.05, 0.1, 0.5, 1.0]

        for Q in Q_values:
            # 原始版本
            f_orig = pipe.friction_factor_colebrook(Q)

            # JIT版本
            f_jit = friction_factor_colebrook_jit(Q, pipe.D, pipe.epsilon, 10, 1e-6)

            # 验证相对误差 < 0.1%
            rel_error = abs(f_orig - f_jit) / f_orig
            assert rel_error < 1e-3, \
                f"摩阻系数误差过大: Q={Q}, f_orig={f_orig}, f_jit={f_jit}, err={rel_error:.2%}"

    def test_laminar_flow(self):
        """测试层流情况"""
        # Re < 2000的情况
        Q = 0.0001  # 很小的流量
        pipe = PressurePipe('test', 0.3, 100, 0.00026)

        f_orig = pipe.friction_factor_colebrook(Q)
        f_jit = friction_factor_colebrook_jit(Q, pipe.D, pipe.epsilon, 10, 1e-6)

        # 层流: f = 64/Re
        assert abs(f_orig - f_jit) < 1e-6

    def test_smooth_pipe(self):
        """测试光滑管"""
        # 粗糙度为0
        Q = 0.1
        D = 0.3
        epsilon = 0.0

        pipe = PressurePipe('test', D, 100, epsilon)

        f_orig = pipe.friction_factor_colebrook(Q)
        f_jit = friction_factor_colebrook_jit(Q, D, epsilon, 10, 1e-6)

        # 光滑管应该相等（Blasius公式）
        assert abs(f_orig - f_jit) < 1e-6


class TestHeadLossDarcyJIT:
    """测试Darcy水头损失的JIT版本"""

    def test_head_loss_accuracy(self):
        """测试水头损失计算准确性"""
        # 参数
        Q = 0.1
        f = 0.02
        L = 100.0
        D = 0.3
        g = 9.81
        A = np.pi * (D / 2.0)**2

        # 原始计算
        V = Q / A
        h_orig = f * (L / D) * (V**2) / (2.0 * g)

        # JIT版本
        h_jit = head_loss_darcy_jit(Q, f, L, D)

        # 验证
        assert abs(h_orig - h_jit) < 1e-10

    def test_zero_flow(self):
        """测试零流量"""
        h = head_loss_darcy_jit(0.0, 0.02, 100.0, 0.3)
        assert h == 0.0


class TestHeadLossCompleteJIT:
    """测试完整水头损失的JIT版本"""

    def test_head_loss_complete_accuracy(self):
        """测试完整水头损失计算准确性"""
        # 创建管道
        pipe = PressurePipe('test', 0.3, 100, 0.00026, K_minor=0.5)

        # 测试流量范围
        Q_values = [0.01, 0.05, 0.1, 0.5, 1.0]

        for Q in Q_values:
            # 原始版本
            h_orig = pipe.head_loss(Q)

            # JIT版本
            h_jit = head_loss_complete_jit(
                Q, pipe.D, pipe.L, pipe.epsilon, pipe.K_minor, 10, 1e-6
            )

            # 验证相对误差 < 0.5%
            rel_error = abs(h_orig - h_jit) / h_orig if h_orig > 0 else 0
            assert rel_error < 5e-3, \
                f"水头损失误差过大: Q={Q}, h_orig={h_orig}, h_jit={h_jit}, err={rel_error:.2%}"

    def test_no_minor_loss(self):
        """测试无局部损失"""
        pipe = PressurePipe('test', 0.3, 100, 0.00026, K_minor=0.0)
        Q = 0.1

        h_orig = pipe.head_loss(Q)
        h_jit = head_loss_complete_jit(Q, pipe.D, pipe.L, pipe.epsilon, 0.0, 10, 1e-6)

        # 无局部损失时应该完全相等
        rel_error = abs(h_orig - h_jit) / h_orig
        assert rel_error < 1e-3

    def test_with_minor_loss(self):
        """测试包含局部损失"""
        pipe = PressurePipe('test', 0.3, 100, 0.00026, K_minor=1.5)
        Q = 0.1

        h_orig = pipe.head_loss(Q)
        h_jit = head_loss_complete_jit(Q, pipe.D, pipe.L, pipe.epsilon, 1.5, 10, 1e-6)

        # 包含局部损失时应该相等
        rel_error = abs(h_orig - h_jit) / h_orig
        assert rel_error < 1e-3


class TestPerformanceConsistency:
    """测试性能优化后的一致性"""

    def test_multiple_pipes(self):
        """测试多个管道的一致性"""
        # 创建不同参数的管道
        pipe_params = [
            (0.2, 50, 0.00026),
            (0.3, 100, 0.00026),
            (0.5, 200, 0.001),
            (0.8, 500, 0.0015),
        ]

        Q = 0.15

        for D, L, epsilon in pipe_params:
            pipe = PressurePipe('test', D, L, epsilon)

            h_orig = pipe.head_loss(Q)
            h_jit = head_loss_complete_jit(Q, D, L, epsilon, 0.0, 10, 1e-6)

            rel_error = abs(h_orig - h_jit) / h_orig if h_orig > 0 else 0
            assert rel_error < 1e-3, \
                f"管道 D={D}, L={L}: 误差={rel_error:.2%}"

    def test_flow_range(self):
        """测试大范围流量的一致性"""
        pipe = PressurePipe('test', 0.3, 100, 0.00026)

        # 从很小到很大的流量
        Q_values = np.logspace(-3, 0, 20)  # 0.001 到 1.0

        for Q in Q_values:
            h_orig = pipe.head_loss(Q)
            h_jit = head_loss_complete_jit(Q, pipe.D, pipe.L, pipe.epsilon, 0.0, 10, 1e-6)

            if h_orig > 1e-6:  # 避免除零
                rel_error = abs(h_orig - h_jit) / h_orig
                assert rel_error < 1e-2, \
                    f"流量 Q={Q}: 误差={rel_error:.2%}"


class TestPerformanceImprovement:
    """测试性能提升"""

    def test_jit_is_faster(self):
        """验证JIT版本确实更快"""
        import time

        pipe = PressurePipe('test', 0.3, 100, 0.00026)
        Q_values = np.linspace(0.01, 1.0, 100)

        # 原始版本
        start = time.time()
        for Q in Q_values:
            _ = pipe.head_loss(Q)
        time_orig = time.time() - start

        # JIT版本
        start = time.time()
        for Q in Q_values:
            _ = head_loss_complete_jit(Q, pipe.D, pipe.L, pipe.epsilon, 0.0, 10, 1e-6)
        time_jit = time.time() - start

        speedup = time_orig / time_jit if time_jit > 0 else 0

        print(f"\n性能测试: 原始={time_orig:.4f}s, JIT={time_jit:.4f}s, 加速={speedup:.1f}x")

        # JIT应该显著更快（至少2x）
        assert speedup > 2.0, f"JIT加速不足: {speedup:.1f}x"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
