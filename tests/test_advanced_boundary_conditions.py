"""
高级边界条件集成测试

验证
1. 时变边界条件在求解器中的应用
2. Rating Curve边界条件
3. 潮汐边界条件
4. 洪水过程线
5. 水工建筑物堰闸边界

Phase 2.4 - Task 2.4.4

作者: HydroClaude Team
日期: 2025-10-29
"""

import pytest
import numpy as np
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from physics.advanced_boundary_conditions import (
    TimeDependentBC,
    RatingCurveBC,
    TidalBC,
    HydrographBC,
    create_constant_bc
)
from physics.hydraulic_structures import (
    BroadCrestedWeir,
    SharpCrestedWeir,
    SluiceGate,
    Orifice,
    create_weir_bc
)


@pytest.mark.p1
def test_time_dependent_bc_creation():
    """测试时变边界条件创建"""
    time = np.array([0, 1800, 3600, 5400, 7200])
    flow = np.array([10, 30, 50, 40, 20])

    bc = TimeDependentBC(time, flow, name="Test BC")

    # 验证插值
    assert bc(0) == pytest.approx(10.0)
    assert bc(3600) == pytest.approx(50.0)
    assert bc(7200) == pytest.approx(20.0)

    # 测试中间点插值
    assert bc(1800) == pytest.approx(30.0)
    assert bc(900) == pytest.approx(20.0)  # 线性插值 (10+30)/2

    print(" 时变边界条件创建测试通过")


@pytest.mark.p1
def test_time_dependent_bc_extrapolation():
    """测试时变边界条件外推"""
    time = np.array([1000, 2000, 3000])
    values = np.array([10, 20, 30])

    # constant外推
    bc_const = TimeDependentBC(time, values, extrapolate='constant')
    assert bc_const(0) == pytest.approx(10.0)  # 使用第一个值
    assert bc_const(4000) == pytest.approx(30.0)  # 使用最后一个值

    # linear外推
    bc_linear = TimeDependentBC(time, values, extrapolate='linear')
    assert bc_linear(0) == pytest.approx(0.0)  # 线性外推
    assert bc_linear(4000) == pytest.approx(40.0)  # 线性外推

    print(" 时变边界条件外推测试通过")


@pytest.mark.p1
def test_rating_curve_bc():
    """测试Rating Curve边界条件"""
    h_data = np.array([0.5, 1.0, 1.5, 2.0, 2.5])
    Q_data = np.array([5, 15, 30, 50, 75])

    rating = RatingCurveBC(h_data, Q_data, name="Test Rating")

    # 测试h->Q
    assert rating.get_Q(0.5) == pytest.approx(5.0)
    assert rating.get_Q(2.0) == pytest.approx(50.0)
    assert rating.get_Q(1.25) == pytest.approx(22.5, abs=0.1)  # 插值

    # 测试Q->h
    assert rating.get_h(5.0) == pytest.approx(0.5)
    assert rating.get_h(50.0) == pytest.approx(2.0)

    print(" Rating Curve边界条件测试通过")


@pytest.mark.p2
def test_tidal_bc():
    """测试潮汐边界条件"""
    tidal = TidalBC(
        period=12*3600,  # 12小时周期
        amplitude=2.0,
        mean_level=3.0,
        phase=0.0,
        duration=24*3600
    )

    # 测试关键时刻余弦函数phase=0时t=0为高潮
    assert tidal(0) == pytest.approx(5.0, abs=0.1)  # 高潮mean + amplitude
    assert tidal(3*3600) == pytest.approx(3.0, abs=0.1)  # 平潮pi/2
    assert tidal(6*3600) == pytest.approx(1.0, abs=0.1)  # 低潮mean - amplitudepi
    assert tidal(9*3600) == pytest.approx(3.0, abs=0.1)  # 平潮3pi/2
    assert tidal(12*3600) == pytest.approx(5.0, abs=0.1)  # 回到高潮2pi

    print(" 潮汐边界条件测试通过")


@pytest.mark.p2
def test_flood_hydrograph_triangular():
    """测试三角形洪水过程线"""
    flood = HydrographBC.triangular(
        base_flow=10.0,
        peak_flow=100.0,
        time_to_peak=2*3600,
        time_to_base=8*3600
    )

    # 测试关键时刻
    assert flood(0) == pytest.approx(10.0)  # 基流
    assert flood(2*3600) == pytest.approx(100.0)  # 洪峰
    assert flood(8*3600) == pytest.approx(10.0)  # 退至基流

    # 测试涨洪段
    assert flood(1*3600) == pytest.approx(55.0, abs=1.0)  # 中间

    print(" 三角形洪水过程线测试通过")


@pytest.mark.p2
def test_flood_hydrograph_trapezoidal():
    """测试梯形洪水过程线"""
    flood = HydrographBC.trapezoidal(
        base_flow=10.0,
        peak_flow=100.0,
        time_to_peak=2*3600,
        peak_duration=2*3600,
        time_to_base=10*3600
    )

    # 测试关键时刻
    assert flood(0) == pytest.approx(10.0)
    assert flood(2*3600) == pytest.approx(100.0)  # 洪峰开始
    assert flood(4*3600) == pytest.approx(100.0)  # 洪峰持续
    assert flood(10*3600) == pytest.approx(10.0)  # 退至基流

    print(" 梯形洪水过程线测试通过")


@pytest.mark.p2
def test_broad_crested_weir():
    """测试宽顶堰"""
    weir = BroadCrestedWeir(
        crest_elevation=2.0,
        width=10.0,
        discharge_coeff=1.7
    )

    # 测试自由出流
    Q1 = weir.compute_discharge(h_upstream=3.0, h_downstream=None)
    # Q = C * B * H^(3/2) = 1.7 * 10 * 1^1.5 = 17
    assert Q1 == pytest.approx(17.0, abs=0.1)

    # 测试淹没出流
    Q2 = weir.compute_discharge(h_upstream=3.0, h_downstream=2.5)
    assert 0 < Q2 < Q1  # 淹没流量小于自由流量

    # 测试堰顶以下
    Q3 = weir.compute_discharge(h_upstream=1.5, h_downstream=1.0)
    assert Q3 == 0.0

    print(" 宽顶堰测试通过")


@pytest.mark.p2
def test_sharp_crested_weir():
    """测试薄壁堰"""
    weir = SharpCrestedWeir(
        crest_elevation=1.0,
        width=5.0,
        discharge_coeff=1.84
    )

    # 测试过堰流量
    Q1 = weir.compute_discharge(h_upstream=1.5)
    # Q = C * B * H^(3/2) = 1.84 * 5 * 0.5^1.5 ~= 3.25
    assert Q1 == pytest.approx(3.25, abs=0.1)

    Q2 = weir.compute_discharge(h_upstream=2.0)
    assert Q2 > Q1  # 水头越大流量越大

    print(" 薄壁堰测试通过")


@pytest.mark.p2
def test_sluice_gate():
    """测试平板闸门"""
    gate = SluiceGate(
        sill_elevation=0.0,
        width=8.0,
        opening=0.5
    )

    # 测试自由出流
    Q1 = gate.compute_discharge(h_upstream=2.0, h_downstream=0.2)
    assert Q1 > 0

    # 测试淹没出流
    Q2 = gate.compute_discharge(h_upstream=3.0, h_downstream=2.5)
    assert Q2 > 0
    # 淹没时流量取决于水头差
    Q3 = gate.compute_discharge(h_upstream=3.0, h_downstream=2.8)
    assert Q3 < Q2  # 水头差减小流量减小

    # 测试闸门关闭
    gate.set_opening(0.0)
    Q_closed = gate.compute_discharge(h_upstream=2.0, h_downstream=1.0)
    assert Q_closed == 0.0

    # 测试不同开度
    gate.set_opening(1.0)
    Q_large = gate.compute_discharge(h_upstream=2.0, h_downstream=0.5)
    gate.set_opening(0.5)
    Q_small = gate.compute_discharge(h_upstream=2.0, h_downstream=0.5)
    assert Q_large > Q_small  # 开度越大流量越大

    print(" 平板闸门测试通过")


@pytest.mark.p2
def test_orifice():
    """测试圆形孔口"""
    orifice = Orifice(
        center_elevation=1.0,
        diameter=1.5,
        discharge_coeff=0.62
    )

    # 测试自由出流
    Q1 = orifice.compute_discharge(h_upstream=2.0, h_downstream=None)
    assert Q1 > 0

    # 测试淹没出流
    Q2 = orifice.compute_discharge(h_upstream=3.0, h_downstream=1.5)
    assert Q2 > 0

    # 测试水位过低
    Q_low = orifice.compute_discharge(h_upstream=0.3, h_downstream=None)
    assert Q_low == 0.0

    print(" 圆形孔口测试通过")


@pytest.mark.p3
def test_constant_bc_helper():
    """测试常数边界条件辅助函数"""
    bc_const = create_constant_bc(25.0, name="Constant_25")

    # 任何时刻都返回相同值
    assert bc_const(0) == 25.0
    assert bc_const(1000) == 25.0
    assert bc_const(9999) == 25.0

    print(" 常数边界条件辅助函数测试通过")


@pytest.mark.p3
def test_weir_bc_creator():
    """测试堰边界条件创建函数"""
    weir = BroadCrestedWeir(crest_elevation=2.0, width=10.0)

    # 创建边界条件函数
    bc_func = create_weir_bc(weir, h_downstream=2.5)

    # 测试调用
    Q1 = bc_func(3.0)
    Q2 = weir.compute_discharge(3.0, 2.5)
    assert Q1 == pytest.approx(Q2)

    print(" 堰边界条件创建函数测试通过")


if __name__ == "__main__":
    """直接运行测试"""
    print("="*80)
    print("高级边界条件集成测试 - Phase 2.4")
    print("="*80)

    try:
        test_time_dependent_bc_creation()
        test_time_dependent_bc_extrapolation()
        test_rating_curve_bc()
        test_tidal_bc()
        test_flood_hydrograph_triangular()
        test_flood_hydrograph_trapezoidal()
        test_broad_crested_weir()
        test_sharp_crested_weir()
        test_sluice_gate()
        test_orifice()
        test_constant_bc_helper()
        test_weir_bc_creator()

        print("\n" + "="*80)
        print(" 所有高级边界条件测试通过")
        print("="*80)

        print("\n总结:")
        print("  1.  时变边界条件 - 支持插值和外推")
        print("  2.  Rating Curve - 双向插值 (h<->Q)")
        print("  3.  潮汐边界 - 余弦潮汐模型")
        print("  4.  洪水过程线 - 三角形和梯形")
        print("  5.  宽顶堰 - 自由/淹没出流")
        print("  6.  薄壁堰 - 标准公式")
        print("  7.  平板闸门 - 可调开度")
        print("  8.  圆形孔口 - 孔流计算")
        print("\n可直接用于GodunvFVMSolver的边界条件")

    except Exception as e:
        print(f"\n 测试失败: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
