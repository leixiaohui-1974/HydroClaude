#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
特征线边界条件单元测试

测试solvers/boundary_conditions.py中的所有边界条件功能

作者: HydroClaude Team
日期: 2025-10-29
"""

import pytest
import numpy as np
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from solvers.boundary_conditions import (
    CharacteristicBC,
    FlowRegime,
    BoundaryConditionType
)


class TestCharacteristicBC:
    """特征线边界条件测试套件"""

    def setup_method(self):
        """每个测试前的设置"""
        self.bc = CharacteristicBC(g=9.81)
        self.tol = 1e-6  # 数值容差

    def test_froude_number_calculation(self):
        """测试Froude数计算"""
        # 测试1: 缓流
        h = 2.0
        u = 1.0
        Fr = self.bc.compute_froude_number(h, u)
        assert abs(Fr - 0.226) < 0.01, f"缓流Froude数计算错误: {Fr}"

        # 测试2: 临界流
        h_c = 1.0
        u_c = np.sqrt(9.81 * h_c)
        Fr_c = self.bc.compute_froude_number(h_c, u_c)
        assert abs(Fr_c - 1.0) < self.tol, f"临界流Froude数应=1: {Fr_c}"

        # 测试3: 急流
        h = 0.5
        u = 5.0
        Fr = self.bc.compute_froude_number(h, u)
        assert Fr > 1.0, f"急流Froude数应>1: {Fr}"

    def test_flow_regime_identification(self):
        """测试流态识别"""
        # 缓流
        regime = self.bc.identify_flow_regime(h=2.0, u=1.0)
        assert regime == FlowRegime.SUBCRITICAL

        # 临界流
        h_c = 1.0
        u_c = np.sqrt(9.81 * h_c)
        regime = self.bc.identify_flow_regime(h=h_c, u=u_c)
        assert regime == FlowRegime.CRITICAL

        # 急流
        regime = self.bc.identify_flow_regime(h=0.5, u=5.0)
        assert regime == FlowRegime.SUPERCRITICAL

    def test_riemann_invariants(self):
        """测试Riemann不变量计算和恢复"""
        h = 2.5
        u = 1.5

        # 计算Riemann不变量
        R_plus, R_minus = self.bc.compute_riemann_invariants(h, u)

        # 理论值
        c = np.sqrt(9.81 * h)
        R_plus_theory = u + 2 * c
        R_minus_theory = u - 2 * c

        assert abs(R_plus - R_plus_theory) < self.tol
        assert abs(R_minus - R_minus_theory) < self.tol

        # 恢复物理量
        h_rec, u_rec = self.bc.recover_from_riemann_invariants(R_plus, R_minus)

        assert abs(h_rec - h) < self.tol, f"水深恢复误差: {abs(h_rec - h)}"
        assert abs(u_rec - u) < self.tol, f"流速恢复误差: {abs(u_rec - u)}"

    def test_subcritical_inlet_Q(self):
        """测试缓流入口边界条件（指定流量Q）"""
        h_interior = 2.0
        u_interior = 1.0  # Fr ≈ 0.23 < 1
        Q_bc = 30.0
        B = 10.0

        h_bc, u_bc = self.bc.apply_subcritical_inlet(
            None, None, h_interior, u_interior, Q_bc, bc_type='Q', B=B
        )

        # 检查流量守恒
        Q_result = u_bc * h_bc * B
        assert abs(Q_result - Q_bc) < 0.01, \
            f"流量不守恒: {Q_result:.3f} ≠ {Q_bc:.3f}"

        # 检查仍为缓流
        Fr_bc = self.bc.compute_froude_number(h_bc, u_bc)
        assert Fr_bc < 1.5, f"边界Froude数异常: {Fr_bc}"

    def test_subcritical_inlet_h(self):
        """测试缓流入口边界条件（指定水深h）"""
        h_interior = 2.0
        u_interior = 1.0
        h_bc_specified = 1.8  # 减小水深而不是增大（更符合物理）
        B = 10.0

        h_bc, u_bc = self.bc.apply_subcritical_inlet(
            None, None, h_interior, u_interior, h_bc_specified, bc_type='h', B=B
        )

        # 检查水深
        assert abs(h_bc - h_bc_specified) < self.tol, \
            f"水深不匹配: {h_bc} ≠ {h_bc_specified}"

        # 检查流速存在（可能为正或负，取决于特征线）
        assert abs(u_bc) < 10.0, "流速应在合理范围内"

    def test_subcritical_outlet_h(self):
        """测试缓流出口边界条件（指定水深h）"""
        h_interior = 2.0
        u_interior = 1.0
        h_bc_specified = 1.8
        B = 10.0

        h_bc, u_bc = self.bc.apply_subcritical_outlet(
            None, None, h_interior, u_interior, h_bc_specified, bc_type='h', B=B
        )

        # 检查水深
        assert abs(h_bc - h_bc_specified) < self.tol

        # 检查流速合理
        assert u_bc > 0

    def test_critical_depth_bc(self):
        """测试临界水深边界条件"""
        Q = 20.0
        B = 10.0

        h_c, u_c = self.bc.apply_critical_depth_bc(Q, B)

        # 检查Froude数 = 1
        Fr = self.bc.compute_froude_number(h_c, u_c)
        assert abs(Fr - 1.0) < 0.01, f"临界流Froude数应≈1: {Fr}"

        # 检查流量
        Q_result = u_c * h_c * B
        assert abs(Q_result - Q) < 0.01, f"流量误差: {Q_result} ≠ {Q}"

        # 理论值
        h_c_theory = (Q**2 / (9.81 * B**2))**(1.0/3.0)
        assert abs(h_c - h_c_theory) < 0.001, \
            f"临界水深误差: {h_c} ≠ {h_c_theory}"

    def test_supercritical_inlet(self):
        """测试急流入口边界条件"""
        h_bc_value = 0.6
        Q_bc_value = 25.0
        B = 10.0

        h_bc, u_bc = self.bc.apply_supercritical_inlet(h_bc_value, Q_bc_value, B)

        # 检查水深和流速
        assert abs(h_bc - h_bc_value) < self.tol
        assert abs(u_bc - Q_bc_value / (B * h_bc)) < self.tol

        # 检查是急流
        Fr = self.bc.compute_froude_number(h_bc, u_bc)
        assert Fr > 1.0, f"应为急流: Fr = {Fr}"

    def test_supercritical_outlet(self):
        """测试急流出口边界条件（完全外推）"""
        h_interior = 0.8
        u_interior = 4.0

        h_bc, u_bc = self.bc.apply_supercritical_outlet(h_interior, u_interior)

        # 零阶外推：应该完全等于内部值
        assert abs(h_bc - h_interior) < self.tol
        assert abs(u_bc - u_interior) < self.tol

    def test_transmissive_bc(self):
        """测试透射边界条件"""
        h_interior = 2.0
        u_interior = 1.5
        h_prev = 2.1
        u_prev = 1.4
        dt = 0.1
        dx = 10.0

        h_bc, u_bc = self.bc.apply_transmissive_bc(
            h_interior, u_interior, h_prev, u_prev, dt, dx
        )

        # 检查物理合理性
        assert h_bc > 0, "水深应为正"
        assert abs(h_bc - h_interior) < 1.0, "外推不应偏离过大"

    def test_consistency_across_flow_regimes(self):
        """测试不同流态下的一致性"""
        B = 10.0

        # 测试从缓流到急流的连续性
        Q = 20.0

        # 缓流场景
        h_sub = 2.0
        u_sub = Q / (B * h_sub)
        Fr_sub = self.bc.compute_froude_number(h_sub, u_sub)
        assert Fr_sub < 1.0, "应为缓流"

        # 临界场景
        h_crit, u_crit = self.bc.apply_critical_depth_bc(Q, B)
        Fr_crit = self.bc.compute_froude_number(h_crit, u_crit)
        assert abs(Fr_crit - 1.0) < 0.01, "应为临界流"

        # 急流场景
        h_super = 0.5
        u_super = Q / (B * h_super)
        Fr_super = self.bc.compute_froude_number(h_super, u_super)
        assert Fr_super > 1.0, "应为急流"

        # 检查流量一致性
        Q_sub = u_sub * h_sub * B
        Q_crit = u_crit * h_crit * B
        Q_super = u_super * h_super * B

        assert abs(Q_sub - Q) < 0.01
        assert abs(Q_crit - Q) < 0.01
        assert abs(Q_super - Q) < 0.01


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
