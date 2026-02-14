#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
变坡度支持验证测试

目标：验证求解器对变坡度(S0数组)的支持

测试内容：
1. 恒定坡度兼容性测试（标量S0）
2. 变坡度数组测试（数组S0）
3. 缓坡到陡坡转换
4. 阶梯状坡度
5. 底床高程计算验证

作者: HydroClaude Team
日期: 2025-10-31
"""

import sys
import warnings
warnings.filterwarnings("ignore")
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import numpy as np
import pytest


class TestVariableSlope:
    """变坡度支持验证测试"""

    def test_uniform_slope_compatibility(self):
        """
        测试1：恒定坡度兼容性

        验证：标量S0输入仍然正常工作（向后兼容）
        """
        print("\n" + "="*70)
        print("变坡度 Test 1: 恒定坡度兼容性（标量S0）")
        print("="*70)

        from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver

        # 使用标量S0（传统用法）
        S0_scalar = 0.001
        solver = HydrostaticCanalSolver(
            length=1000.0,
            nx=51,
            B=10.0,
            S0=S0_scalar,  # 标量
            n=0.025
        )

        # 验证
        assert solver.is_uniform_slope, "应该识别为恒定坡度"
        assert solver.S0_scalar == S0_scalar, "S0_scalar应该正确保存"
        assert len(solver.S0) == 50, "S0数组长度应为nx-1"
        assert np.allclose(solver.S0, S0_scalar), "S0数组应全部等于标量值"

        # 验证底床高程（线性下降）
        z_expected = -S0_scalar * solver.x
        assert np.allclose(solver.z, z_expected, atol=1e-10), "底床高程应线性变化"

        print(f"\n PASSED: 标量S0兼容性验证通过")
        print(f"  S0 = {S0_scalar}")
        print(f"  S0数组长度 = {len(solver.S0)}")
        print(f"  底床高程范围: {solver.z[0]:.3f} to {solver.z[-1]:.3f}m")

    def test_variable_slope_array(self):
        """
        测试2：变坡度数组输入

        验证：S0数组输入正确处理
        """
        print("\n" + "="*70)
        print("变坡度 Test 2: 变坡度数组输入")
        print("="*70)

        from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver

        nx = 51
        # 创建变坡度数组
        S0_array = np.linspace(0.001, 0.005, nx - 1)  # 从0.001渐变到0.005

        solver = HydrostaticCanalSolver(
            length=1000.0,
            nx=nx,
            B=10.0,
            S0=S0_array,  # 数组
            n=0.025
        )

        # 验证
        assert not solver.is_uniform_slope, "应该识别为变坡度"
        assert np.allclose(solver.S0, S0_array), "S0数组应正确保存"
        assert abs(solver.S0_scalar - np.mean(S0_array)) < 1e-10, "S0_scalar应为平均值"

        # 验证底床高程递减
        z_diff = np.diff(solver.z)
        assert np.all(z_diff < 0), "底床高程应向下游递减"

        print(f"\n PASSED: 变坡度数组验证通过")
        print(f"  S0范围: {S0_array[0]:.6f} to {S0_array[-1]:.6f}")
        print(f"  S0平均: {solver.S0_scalar:.6f}")
        print(f"  底床高程范围: {solver.z[0]:.3f} to {solver.z[-1]:.3f}m")

    def test_mild_to_steep_transition(self):
        """
        测试3：缓坡到陡坡转换

        场景：上游缓坡，下游陡坡（阶跃变化）
        验证：底床高程计算正确
        """
        print("\n" + "="*70)
        print("变坡度 Test 3: 缓坡->陡坡转换")
        print("="*70)

        from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver

        nx = 101
        # 上游50单元缓坡，下游50单元陡坡
        S0_array = np.concatenate([
            np.ones(50) * 0.0005,  # 缓坡 (1:2000)
            np.ones(50) * 0.01     # 陡坡 (1:100)
        ])

        solver = HydrostaticCanalSolver(
            length=1000.0,
            nx=nx,
            B=10.0,
            S0=S0_array,
            n=0.025
        )

        # 验证坡度分段
        assert np.allclose(solver.S0[:50], 0.0005), "上游应为缓坡"
        assert np.allclose(solver.S0[50:], 0.01), "下游应为陡坡"

        # 验证底床高程连续性
        z_diff = np.diff(solver.z)
        assert np.all(z_diff < 0), "底床高程应连续下降"

        # 计算两段的高程降落
        dx = solver.dx_local[0]
        drop_upstream = 0.0005 * dx * 50
        drop_downstream = 0.01 * dx * 50
        total_drop = drop_upstream + drop_downstream

        assert abs(solver.z[-1] - solver.z[0] + total_drop) < 1e-10, "总高程降落应正确"

        print(f"\n PASSED: 缓坡->陡坡转换验证通过")
        print(f"  上游坡度: S0 = {0.0005} (1:2000)")
        print(f"  下游坡度: S0 = {0.01} (1:100)")
        print(f"  上游高程降: {drop_upstream:.3f}m")
        print(f"  下游高程降: {drop_downstream:.3f}m")
        print(f"  总高程降: {total_drop:.3f}m")
        print(f"  实际高程降: {solver.z[0] - solver.z[-1]:.3f}m")

    def test_stepped_slope(self):
        """
        测试4：阶梯状坡度

        场景：多段不同坡度
        验证：复杂坡度变化
        """
        print("\n" + "="*70)
        print("变坡度 Test 4: 阶梯状坡度")
        print("="*70)

        from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver

        nx = 101
        # 创建5段不同坡度
        S0_array = np.concatenate([
            np.ones(20) * 0.001,   # 段1
            np.ones(20) * 0.002,   # 段2
            np.ones(20) * 0.0015,  # 段3
            np.ones(20) * 0.003,   # 段4
            np.ones(20) * 0.0005   # 段5
        ])

        solver = HydrostaticCanalSolver(
            length=1000.0,
            nx=nx,
            B=10.0,
            S0=S0_array,
            n=0.025
        )

        # 验证各段坡度
        assert np.allclose(solver.S0[:20], 0.001), "段1坡度"
        assert np.allclose(solver.S0[20:40], 0.002), "段2坡度"
        assert np.allclose(solver.S0[40:60], 0.0015), "段3坡度"
        assert np.allclose(solver.S0[60:80], 0.003), "段4坡度"
        assert np.allclose(solver.S0[80:], 0.0005), "段5坡度"

        # 验证底床高程单调递减
        assert np.all(np.diff(solver.z) < 0), "底床高程应单调递减"

        print(f"\n PASSED: 阶梯状坡度验证通过")
        print(f"  段1: S0 = 0.001")
        print(f"  段2: S0 = 0.002")
        print(f"  段3: S0 = 0.0015")
        print(f"  段4: S0 = 0.003")
        print(f"  段5: S0 = 0.0005")

    def test_bed_elevation_accuracy(self):
        """
        测试5：底床高程计算精度

        验证：底床高程计算的数值精度
        """
        print("\n" + "="*70)
        print("变坡度 Test 5: 底床高程计算精度")
        print("="*70)

        from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver

        # 测试case 1: 恒定坡度
        S0_const = 0.001
        solver1 = HydrostaticCanalSolver(
            length=1000.0,
            nx=101,
            B=10.0,
            S0=S0_const,
            n=0.025
        )

        # 手动计算底床高程
        x = solver1.x
        z_expected = -S0_const * x

        error = np.abs(solver1.z - z_expected)
        max_error = np.max(error)

        assert max_error < 1e-12, f"恒定坡度：底床高程误差应为机器精度，实际{max_error:.2e}"

        # 测试case 2: 线性变化坡度
        nx = 101
        S0_linear = np.linspace(0.001, 0.005, nx - 1)

        solver2 = HydrostaticCanalSolver(
            length=1000.0,
            nx=nx,
            B=10.0,
            S0=S0_linear,
            n=0.025
        )

        # 手动计算底床高程
        dx = solver2.dx_local[0]
        z_manual = np.zeros(nx)
        z_manual[0] = 0.0
        for i in range(nx - 1):
            z_manual[i + 1] = z_manual[i] - S0_linear[i] * dx

        error2 = np.abs(solver2.z - z_manual)
        max_error2 = np.max(error2)

        assert max_error2 < 1e-12, f"变坡度：底床高程误差应为机器精度，实际{max_error2:.2e}"

        print(f"\n PASSED: 底床高程计算精度验证通过")
        print(f"  恒定坡度最大误差: {max_error:.2e}")
        print(f"  变坡度最大误差: {max_error2:.2e}")

    def test_invalid_slope_array_length(self):
        """
        测试6：无效坡度数组长度

        验证：错误的数组长度应抛出异常
        """
        print("\n" + "="*70)
        print("变坡度 Test 6: 无效坡度数组长度")
        print("="*70)

        from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver

        nx = 51
        # 错误长度的S0数组
        S0_wrong = np.ones(60)  # 应该是50

        with pytest.raises(ValueError, match="S0"):
            solver = HydrostaticCanalSolver(
                length=1000.0,
                nx=nx,
                B=10.0,
                S0=S0_wrong,
                n=0.025
            )

        print(f"\n PASSED: 正确检测并抛出异常")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
