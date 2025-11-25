#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PressurePipe类单元测试 - Unit Tests for PressurePipe Class

测试覆盖:
1. 基本初始化和参数验证
2. 雷诺数计算
3. 摩阻系数计算（层流和湍流）
4. Colebrook-White迭代收敛性
5. Darcy-Weisbach水头损失
6. Hazen-Williams水头损失
7. 流量反算
8. 便捷构造函数
9. 边界情况和数值稳定性

作者: HydroClaude Team
日期: 2025-10-30
"""

import pytest
import numpy as np
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from network.pressure_pipe import (
    PressurePipe,
    create_pressure_pipe,
    HAZEN_WILLIAMS_C,
    MINOR_LOSS_COEFFICIENTS
)


class TestPressurePipeInitialization:
    """测试PressurePipe初始化"""

    def test_basic_initialization(self):
        """测试基本初始化"""
        pipe = PressurePipe(
            pipe_id="P1",
            diameter=0.3,
            length=1000.0,
            roughness=0.0003
        )

        assert pipe.pipe_id == "P1"
        assert pipe.D == 0.3
        assert pipe.L == 1000.0
        assert pipe.epsilon == 0.0003
        assert pipe.formula == "darcy"
        assert pipe.K_minor == 0.0

    def test_initialization_with_minor_loss(self):
        """测试带局部损失的初始化"""
        pipe = PressurePipe(
            pipe_id="P2",
            diameter=0.5,
            length=500.0,
            roughness=0.001,
            K_minor=2.5
        )

        assert pipe.K_minor == 2.5

    def test_initialization_hazen_formula(self):
        """测试Hazen-Williams公式初始化"""
        pipe = PressurePipe(
            pipe_id="P3",
            diameter=0.4,
            length=800.0,
            roughness=0.0005,
            formula="hazen"
        )

        assert pipe.formula == "hazen"

    def test_cross_sectional_area(self):
        """测试断面积计算"""
        pipe = PressurePipe(
            pipe_id="P4",
            diameter=0.2,
            length=100.0,
            roughness=0.0001
        )

        expected_area = np.pi * (0.2 / 2.0)**2
        assert np.isclose(pipe.A, expected_area, rtol=1e-6)

    def test_relative_roughness(self):
        """测试相对粗糙度计算"""
        pipe = PressurePipe(
            pipe_id="P5",
            diameter=0.5,
            length=200.0,
            roughness=0.0005
        )

        expected_relative = 0.0005 / 0.5
        assert np.isclose(pipe.relative_roughness, expected_relative, rtol=1e-6)

    def test_invalid_diameter(self):
        """测试非法管径"""
        with pytest.raises(ValueError, match="管径必须 > 0"):
            PressurePipe("P", diameter=0, length=100, roughness=0.001)

        with pytest.raises(ValueError, match="管径必须 > 0"):
            PressurePipe("P", diameter=-0.5, length=100, roughness=0.001)

    def test_invalid_length(self):
        """测试非法长度"""
        with pytest.raises(ValueError, match="管道长度必须 > 0"):
            PressurePipe("P", diameter=0.3, length=0, roughness=0.001)

    def test_invalid_roughness(self):
        """测试非法粗糙度"""
        with pytest.raises(ValueError, match="粗糙度必须 >= 0"):
            PressurePipe("P", diameter=0.3, length=100, roughness=-0.001)

    def test_invalid_formula(self):
        """测试非法公式类型"""
        with pytest.raises(ValueError, match="公式类型必须为"):
            PressurePipe("P", diameter=0.3, length=100, roughness=0.001, formula="invalid")


class TestReynoldsNumber:
    """测试雷诺数计算"""

    def test_reynolds_zero_flow(self):
        """测试零流量"""
        pipe = PressurePipe("P", diameter=0.3, length=100, roughness=0.001)
        Re = pipe.reynolds_number(Q=0.0)
        assert Re == 0.0

    def test_reynolds_laminar_flow(self):
        """测试层流雷诺数"""
        pipe = PressurePipe("P", diameter=0.05, length=10, roughness=0.0001)

        # 极小流量产生层流 (Re < 2000)
        Q = 0.00003  # m^3/s (非常小)
        Re = pipe.reynolds_number(Q)

        assert Re > 0
        assert Re < 2000  # 层流范围

    def test_reynolds_turbulent_flow(self):
        """测试湍流雷诺数"""
        pipe = PressurePipe("P", diameter=0.3, length=100, roughness=0.001)

        # 大流量应该产生湍流 (Re > 4000)
        Q = 0.1  # m^3/s
        Re = pipe.reynolds_number(Q)

        assert Re > 4000  # 湍流范围

    def test_reynolds_formula(self):
        """测试雷诺数公式 Re = 4Q/(πDν)"""
        pipe = PressurePipe("P", diameter=0.2, length=50, roughness=0.0002)

        Q = 0.02  # m^3/s
        nu = 1.0e-6  # m^2/s
        Re = pipe.reynolds_number(Q, nu)

        # 手算验证: Re = 4*0.02/(π*0.2*1e-6)
        expected_Re = 4 * Q / (np.pi * pipe.D * nu)
        assert np.isclose(Re, expected_Re, rtol=1e-6)

    def test_reynolds_negative_flow(self):
        """测试负流量（应取绝对值）"""
        pipe = PressurePipe("P", diameter=0.3, length=100, roughness=0.001)

        Re_pos = pipe.reynolds_number(Q=0.05)
        Re_neg = pipe.reynolds_number(Q=-0.05)

        assert Re_pos == Re_neg


class TestFrictionFactorLaminar:
    """测试层流摩阻系数"""

    def test_friction_factor_formula(self):
        """测试层流公式 f = 64/Re"""
        pipe = PressurePipe("P", diameter=0.1, length=10, roughness=0.0001)

        Re = 1500  # 层流
        f = pipe.friction_factor_laminar(Re)

        expected_f = 64.0 / Re
        assert np.isclose(f, expected_f, rtol=1e-6)

    def test_friction_factor_zero_reynolds(self):
        """测试零雷诺数"""
        pipe = PressurePipe("P", diameter=0.1, length=10, roughness=0.0001)
        f = pipe.friction_factor_laminar(0)
        assert f == 0.0


class TestFrictionFactorColebrook:
    """测试Colebrook-White摩阻系数"""

    def test_colebrook_laminar_flow(self):
        """测试层流时退化到f=64/Re"""
        pipe = PressurePipe("P", diameter=0.05, length=10, roughness=0.0001)

        # 制造层流条件
        Q = 0.0002  # 很小的流量
        Re = pipe.reynolds_number(Q)

        if Re < 2000:  # 确认是层流
            f = pipe.friction_factor_colebrook(Q)
            expected_f = 64.0 / Re
            assert np.isclose(f, expected_f, rtol=1e-4)

    def test_colebrook_turbulent_convergence(self):
        """测试湍流时Colebrook迭代收敛"""
        pipe = PressurePipe("P", diameter=0.3, length=100, roughness=0.0003)

        Q = 0.1  # 湍流
        f = pipe.friction_factor_colebrook(Q)

        # 摩阻系数应该在合理范围内
        assert 0.01 < f < 0.1
        assert not np.isnan(f)
        assert not np.isinf(f)

    def test_colebrook_smooth_pipe(self):
        """测试光滑管"""
        pipe = PressurePipe("P", diameter=0.2, length=50, roughness=0.0)

        Q = 0.05
        Re = pipe.reynolds_number(Q)

        if Re > 4000:  # 湍流
            f = pipe.friction_factor_colebrook(Q)

            # 光滑管Blasius公式: f ~= 0.316/Re^0.25
            f_blasius = 0.316 / Re**0.25

            # 允许10%误差（Colebrook和Blasius略有差异）
            assert np.isclose(f, f_blasius, rtol=0.1)

    def test_colebrook_rough_pipe(self):
        """测试粗糙管"""
        pipe = PressurePipe("P", diameter=0.3, length=100, roughness=0.003)

        Q = 0.15
        f = pipe.friction_factor_colebrook(Q)

        # 粗糙管摩阻系数应该更大
        assert f > 0.02


class TestHeadLossDarcy:
    """测试Darcy-Weisbach水头损失"""

    def test_head_loss_zero_flow(self):
        """测试零流量"""
        pipe = PressurePipe("P", diameter=0.3, length=100, roughness=0.001)
        h = pipe.head_loss_darcy(Q=0.0)
        assert h == 0.0

    def test_head_loss_formula(self):
        """测试水头损失公式 h = f*(L/D)*(V^2/2g)"""
        pipe = PressurePipe("P", diameter=0.2, length=100, roughness=0.0002)

        Q = 0.03
        h = pipe.head_loss_darcy(Q)

        # 手算验证
        V = Q / pipe.A
        f = pipe.friction_factor_colebrook(Q)
        g = 9.81
        expected_h = f * (pipe.L / pipe.D) * (V**2 / (2*g))

        assert np.isclose(h, expected_h, rtol=1e-4)

    def test_head_loss_with_minor_loss(self):
        """测试包含局部损失"""
        pipe = PressurePipe("P", diameter=0.3, length=50, roughness=0.001, K_minor=1.5)

        Q = 0.08
        h_total = pipe.head_loss_darcy(Q, include_minor=True)
        h_friction = pipe.head_loss_darcy(Q, include_minor=False)

        # 总损失应该大于沿程损失
        assert h_total > h_friction

        # 局部损失应该等于 K*(V^2/2g)
        V = Q / pipe.A
        g = 9.81
        expected_minor = pipe.K_minor * (V**2 / (2*g))

        assert np.isclose(h_total - h_friction, expected_minor, rtol=1e-4)

    def test_head_loss_proportional_to_length(self):
        """测试水头损失与长度成正比"""
        pipe1 = PressurePipe("P1", diameter=0.2, length=100, roughness=0.0002)
        pipe2 = PressurePipe("P2", diameter=0.2, length=200, roughness=0.0002)

        Q = 0.05
        h1 = pipe1.head_loss_darcy(Q)
        h2 = pipe2.head_loss_darcy(Q)

        # 长度加倍，损失应该加倍
        assert np.isclose(h2 / h1, 2.0, rtol=0.01)


class TestHeadLossHazen:
    """测试Hazen-Williams水头损失"""

    def test_hazen_zero_flow(self):
        """测试零流量"""
        pipe = PressurePipe("P", diameter=0.3, length=100, roughness=0.001, formula="hazen")
        h = pipe.head_loss_hazen(Q=0.0)
        assert h == 0.0

    def test_hazen_formula(self):
        """测试Hazen-Williams公式"""
        pipe = PressurePipe("P", diameter=0.3, length=100, roughness=0.001, formula="hazen")

        Q = 0.08
        C = 130
        h = pipe.head_loss_hazen(Q, C=C)

        # 手算验证: h = 10.67*L*Q^1.852/(C^1.852*D^4.87)
        expected_h = 10.67 * pipe.L * (Q**1.852) / (C**1.852 * pipe.D**4.87)

        assert np.isclose(h, expected_h, rtol=1e-4)

    def test_hazen_different_coefficients(self):
        """测试不同C值"""
        pipe = PressurePipe("P", diameter=0.4, length=150, roughness=0.001, formula="hazen")

        Q = 0.1
        h_new = pipe.head_loss_hazen(Q, C=140)  # 新管
        h_old = pipe.head_loss_hazen(Q, C=100)  # 旧管

        # 旧管损失应该更大
        assert h_old > h_new


class TestFlowFromHeadLoss:
    """测试流量反算"""

    def test_flow_reversal_darcy(self):
        """测试Darcy公式流量反算"""
        pipe = PressurePipe("P", diameter=0.3, length=200, roughness=0.0003)

        # 正向计算
        Q_original = 0.1
        h = pipe.head_loss_darcy(Q_original)

        # 反算流量
        Q_calculated = pipe.flow_from_head_loss(h)

        # 应该接近原始流量
        assert np.isclose(Q_calculated, Q_original, rtol=0.01)

    def test_flow_reversal_hazen(self):
        """测试Hazen公式流量反算"""
        pipe = PressurePipe("P", diameter=0.4, length=300, roughness=0.001, formula="hazen")

        Q_original = 0.15
        h = pipe.head_loss_hazen(Q_original)

        Q_calculated = pipe.flow_from_head_loss(h)

        assert np.isclose(Q_calculated, Q_original, rtol=0.01)

    def test_flow_zero_head_loss(self):
        """测试零水头损失"""
        pipe = PressurePipe("P", diameter=0.3, length=100, roughness=0.001)

        Q = pipe.flow_from_head_loss(h_loss=0.0)
        assert Q == 0.0

    def test_flow_convergence(self):
        """测试迭代收敛性"""
        pipe = PressurePipe("P", diameter=0.2, length=500, roughness=0.0005)

        h = 10.0  # 较大的水头损失
        Q = pipe.flow_from_head_loss(h, tol=1e-8)

        # 验证收敛：重新计算水头损失应该接近原值
        h_check = pipe.head_loss(Q)
        assert np.isclose(h_check, h, rtol=1e-6)


class TestConvenienceFunction:
    """测试便捷构造函数"""

    def test_create_cast_iron_pipe(self):
        """测试创建铸铁管"""
        pipe = create_pressure_pipe(
            pipe_id="P1",
            diameter=0.3,
            length=100,
            material="cast_iron_new"
        )

        assert pipe.epsilon == 0.00026
        assert pipe.formula == "darcy"

    def test_create_pvc_pipe(self):
        """测试创建PVC管"""
        pipe = create_pressure_pipe(
            pipe_id="P2",
            diameter=0.2,
            length=50,
            material="pvc"
        )

        assert pipe.epsilon == 0.000015

    def test_create_concrete_pipe(self):
        """测试创建混凝土管"""
        pipe = create_pressure_pipe(
            pipe_id="P3",
            diameter=0.5,
            length=200,
            material="concrete"
        )

        assert pipe.epsilon == 0.001

    def test_create_invalid_material(self):
        """测试非法材料"""
        with pytest.raises(ValueError, match="不支持的材料类型"):
            create_pressure_pipe("P", diameter=0.3, length=100, material="unknown")


class TestProperties:
    """测试properties方法"""

    def test_properties_output_structure(self):
        """测试properties输出结构"""
        pipe = PressurePipe("P", diameter=0.3, length=100, roughness=0.001)

        Q = 0.08
        props = pipe.properties(Q)

        # 检查所有必需的键
        assert 'Q' in props
        assert 'V' in props
        assert 'Re' in props
        assert 'f' in props
        assert 'h_loss' in props
        assert 'regime' in props

    def test_properties_laminar_regime(self):
        """测试层流判断"""
        pipe = PressurePipe("P", diameter=0.05, length=10, roughness=0.0001)

        Q = 0.0001  # 很小，制造层流
        props = pipe.properties(Q)

        if props['Re'] < 2000:
            assert props['regime'] == 'laminar'

    def test_properties_turbulent_regime(self):
        """测试湍流判断"""
        pipe = PressurePipe("P", diameter=0.3, length=100, roughness=0.001)

        Q = 0.1  # 较大，制造湍流
        props = pipe.properties(Q)

        if props['Re'] > 4000:
            assert props['regime'] == 'turbulent'


class TestEdgeCases:
    """测试边界情况和数值稳定性"""

    def test_very_small_flow(self):
        """测试极小流量"""
        pipe = PressurePipe("P", diameter=0.3, length=100, roughness=0.001)

        Q = 1e-8  # 极小流量
        h = pipe.head_loss(Q)

        assert h >= 0
        assert not np.isnan(h)
        assert not np.isinf(h)

    def test_very_large_flow(self):
        """测试极大流量"""
        pipe = PressurePipe("P", diameter=0.5, length=200, roughness=0.002)

        Q = 10.0  # 极大流量
        h = pipe.head_loss(Q)

        assert h > 0
        assert not np.isnan(h)
        assert not np.isinf(h)

    def test_very_long_pipe(self):
        """测试极长管道"""
        pipe = PressurePipe("P", diameter=0.3, length=100000, roughness=0.001)

        Q = 0.05
        h = pipe.head_loss(Q)

        # 长管道应该有很大的水头损失
        assert h > 100  # 应该远大于100m

    def test_very_small_diameter(self):
        """测试极小管径"""
        pipe = PressurePipe("P", diameter=0.01, length=10, roughness=0.00001)

        Q = 0.0001
        h = pipe.head_loss(Q)

        assert h >= 0
        assert not np.isnan(h)

    def test_negative_flow_handling(self):
        """测试负流量处理（应按绝对值计算）"""
        pipe = PressurePipe("P", diameter=0.3, length=100, roughness=0.001)

        Q_pos = 0.08
        Q_neg = -0.08

        h_pos = pipe.head_loss(Q_pos)
        h_neg = pipe.head_loss(Q_neg)

        # 损失应该相同（绝对值）
        assert np.isclose(h_pos, h_neg, rtol=1e-6)


class TestDataBases:
    """测试数据库"""

    def test_hazen_c_database(self):
        """测试Hazen-Williams系数数据库"""
        assert 'cast_iron_new' in HAZEN_WILLIAMS_C
        assert 'pvc' in HAZEN_WILLIAMS_C
        assert 'concrete' in HAZEN_WILLIAMS_C

        # 检查合理值
        assert 80 < HAZEN_WILLIAMS_C['cast_iron_old'] < 120
        assert 130 < HAZEN_WILLIAMS_C['pvc'] < 160

    def test_minor_loss_database(self):
        """测试局部损失系数数据库"""
        assert 'elbow_90_smooth' in MINOR_LOSS_COEFFICIENTS
        assert 'gate_valve' in MINOR_LOSS_COEFFICIENTS
        assert 'entrance_sharp' in MINOR_LOSS_COEFFICIENTS

        # 检查合理值
        assert 0 < MINOR_LOSS_COEFFICIENTS['gate_valve'] < 1
        assert MINOR_LOSS_COEFFICIENTS['globe_valve'] > 5  # 截止阀阻力大


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
