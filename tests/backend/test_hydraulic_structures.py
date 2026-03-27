"""
test_hydraulic_structures.py
============================
水工构筑物模块的全面测试，验证各构筑物的物理正确性。

测试覆盖：
  - SluiceGate  : 自由出流、淹没出流、全关、开度限制
  - RadialGate  : Toch 系数、淹没修正
  - PumpStation : 固定流量、H-Q 曲线、启停逻辑
  - Culvert     : 进口控制、出口控制、圆形/矩形截面
  - Spillway    : 自由出流、淹没修正、零水头
  - StructureGroup : 多构筑物聚合、源汇项
"""

import pytest
import numpy as np
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

from solvers.hydraulic_structures import (
    SluiceGate, RadialGate, PumpStation, Culvert, Spillway, StructureGroup
)


# ===========================================================================
# 1. 平板闸门（SluiceGate）
# ===========================================================================

class TestSluiceGate:

    def test_free_flow_formula(self):
        """自由出流：Q = Cd * b * a * sqrt(2g * H_up)"""
        gate = SluiceGate("G1", 0, 1, width=2.0, opening=0.5, Cd=0.61)
        h_up, h_down = 2.0, 0.1  # 下游水位很低，自由出流
        Q = gate.compute_flow(h_up, h_down)
        # 理论值
        Q_theory = 0.61 * 2.0 * 0.5 * np.sqrt(2 * 9.81 * 2.0)
        assert abs(Q - Q_theory) / Q_theory < 1e-6, \
            f"自由出流误差过大：Q={Q:.4f}, 理论={Q_theory:.4f}"

    def test_submerged_flow(self):
        """淹没出流：h_down/h_up > 0.67 时使用淹没公式"""
        gate = SluiceGate("G1", 0, 1, width=2.0, opening=0.5, Cd=0.61)
        h_up, h_down = 2.0, 1.5  # h_down/h_up = 0.75 > 0.67
        Q = gate.compute_flow(h_up, h_down)
        # 淹没出流应小于自由出流
        Q_free = gate.compute_flow(h_up, 0.1)
        assert Q < Q_free, "淹没出流应小于自由出流"
        # 验证淹没公式
        dH = h_up - h_down
        Q_theory = 0.61 * 2.0 * 0.5 * np.sqrt(2 * 9.81 * dH)
        assert abs(Q - Q_theory) / Q_theory < 1e-6

    def test_gate_closed(self):
        """闸门全关时流量为零"""
        gate = SluiceGate("G1", 0, 1, width=2.0, opening=0.0)
        Q = gate.compute_flow(2.0, 0.1)
        assert Q == 0.0

    def test_no_upstream_water(self):
        """无上游水时流量为零"""
        gate = SluiceGate("G1", 0, 1, width=2.0, opening=0.5)
        Q = gate.compute_flow(0.0, 0.0)
        assert Q == 0.0

    def test_sill_elevation(self):
        """闸底高程：有效水头 = h_up - z_sill"""
        gate_no_sill = SluiceGate("G1", 0, 1, width=1.0, opening=0.3, z_sill=0.0)
        gate_with_sill = SluiceGate("G2", 0, 1, width=1.0, opening=0.3, z_sill=0.5)
        Q1 = gate_no_sill.compute_flow(1.5, 0.0)
        Q2 = gate_with_sill.compute_flow(1.5, 0.0)
        # 有闸底高程时有效水头更小，流量更小
        assert Q2 < Q1

    def test_set_opening_dynamic(self):
        """动态修改开度"""
        gate = SluiceGate("G1", 0, 1, width=2.0, opening=0.5)
        Q1 = gate.compute_flow(2.0, 0.1)
        gate.set_opening(1.0)
        Q2 = gate.compute_flow(2.0, 0.1)
        assert Q2 > Q1, "增大开度后流量应增大"

    def test_flow_increases_with_head(self):
        """流量随上游水头单调增大"""
        gate = SluiceGate("G1", 0, 1, width=2.0, opening=0.5)
        Q_prev = 0.0
        for h_up in [0.5, 1.0, 1.5, 2.0, 3.0]:
            Q = gate.compute_flow(h_up, 0.0)
            assert Q >= Q_prev, f"h_up={h_up}: 流量未单调增大"
            Q_prev = Q

    def test_source_terms_sign(self):
        """源汇项符号：上游流出（负），下游流入（正）"""
        gate = SluiceGate("G1", 0, 1, width=2.0, opening=0.5)
        q_up, q_down = gate.get_source_terms(2.0, 0.1)
        assert q_up < 0, "上游源汇项应为负（流出）"
        assert q_down > 0, "下游源汇项应为正（流入）"
        assert abs(q_up + q_down) < 1e-10, "源汇项之和应为零（守恒）"


# ===========================================================================
# 2. 弧形闸门（RadialGate）
# ===========================================================================

class TestRadialGate:

    def test_toch_cd_at_zero(self):
        """a/H → 0 时 Cd → 0.61"""
        gate = RadialGate("R1", 0, 1, width=2.0, opening=0.01)
        Cd = gate._toch_cd(0.01)
        assert abs(Cd - 0.61) < 0.01

    def test_flow_less_than_sluice_for_large_opening(self):
        """大开度时弧形闸门流量应与平板闸门接近"""
        radial = RadialGate("R1", 0, 1, width=2.0, opening=0.3)
        sluice = SluiceGate("S1", 0, 1, width=2.0, opening=0.3, Cd=0.61)
        Q_r = radial.compute_flow(2.0, 0.0)
        Q_s = sluice.compute_flow(2.0, 0.0)
        # 两者应在同一量级（Toch 系数与 0.61 接近）
        assert abs(Q_r - Q_s) / Q_s < 0.2

    def test_submerged_reduces_flow(self):
        """淹没条件下流量应减小"""
        gate = RadialGate("R1", 0, 1, width=2.0, opening=0.5)
        Q_free = gate.compute_flow(2.0, 0.1)
        Q_sub  = gate.compute_flow(2.0, 1.6)
        assert Q_sub < Q_free


# ===========================================================================
# 3. 泵站（PumpStation）
# ===========================================================================

class TestPumpStation:

    def test_constant_flow_when_running(self):
        """运行时输出设计流量"""
        pump = PumpStation("P1", 0, 1, Q_design=1.5, h_start=0.5, h_stop=0.1)
        # 手动启动
        pump._running = True
        Q = pump.compute_flow(0.8, 0.0)
        assert abs(Q - 1.5) < 1e-10

    def test_start_stop_logic(self):
        """启停逻辑：h_up > h_start 启动，h_up < h_stop 停止"""
        pump = PumpStation("P1", 0, 1, Q_design=1.0, h_start=0.5, h_stop=0.1)
        # 初始未运行
        assert not pump.is_running
        # 水位低于启泵水位，不启动
        Q = pump.compute_flow(0.3, 0.0)
        assert Q == 0.0
        assert not pump.is_running
        # 水位超过启泵水位，启动
        Q = pump.compute_flow(0.6, 0.0)
        assert Q == 1.0
        assert pump.is_running
        # 水位降至停泵水位以上，继续运行（滞回）
        Q = pump.compute_flow(0.2, 0.0)
        assert pump.is_running  # 还未到停泵水位
        # 水位降至停泵水位以下，停止
        Q = pump.compute_flow(0.05, 0.0)
        assert not pump.is_running
        assert Q == 0.0

    def test_multiple_pumps(self):
        """多台泵并联：流量翻倍"""
        pump1 = PumpStation("P1", 0, 1, Q_design=1.0, h_start=0.3, n_pumps=1)
        pump2 = PumpStation("P2", 0, 1, Q_design=1.0, h_start=0.3, n_pumps=3)
        pump1._running = True
        pump2._running = True
        Q1 = pump1.compute_flow(0.5, 0.0)
        Q2 = pump2.compute_flow(0.5, 0.0)
        assert abs(Q2 - 3 * Q1) < 1e-10

    def test_hq_curve(self):
        """H-Q 曲线插值：扬程越大流量越小"""
        hq = [(0.0, 2.0), (2.0, 1.5), (4.0, 1.0), (6.0, 0.0)]
        pump = PumpStation("P1", 0, 1, Q_design=2.0, h_start=0.1, hq_curve=hq)
        pump._running = True
        Q_low  = pump.compute_flow(1.0, 1.0)   # 净扬程 0 → Q=2.0
        Q_mid  = pump.compute_flow(1.0, 3.0)   # 净扬程 2 → Q=1.5
        Q_high = pump.compute_flow(1.0, 5.0)   # 净扬程 4 → Q=1.0
        assert Q_low > Q_mid > Q_high, "H-Q 曲线：扬程越大流量越小"
        assert abs(Q_low - 2.0) < 1e-10
        assert abs(Q_mid - 1.5) < 1e-10
        assert abs(Q_high - 1.0) < 1e-10

    def test_pump_source_terms_direction(self):
        """泵站源汇项：从上游（低水位）抽水到下游（高水位）"""
        pump = PumpStation("P1", 0, 1, Q_design=1.0, h_start=0.3)
        pump._running = True
        q_up, q_down = pump.get_source_terms(0.5, 2.0)
        assert q_up < 0   # 上游流出
        assert q_down > 0  # 下游流入


# ===========================================================================
# 4. 涵洞（Culvert）
# ===========================================================================

class TestCulvert:

    def test_circular_full_section(self):
        """圆形截面满管面积和水力半径"""
        culvert = Culvert("C1", 0, 1, shape='circular', diameter_or_height=1.0)
        A_theory = np.pi * 1.0**2 / 4.0
        R_theory = 1.0 / 4.0
        assert abs(culvert._A_full - A_theory) < 1e-10
        assert abs(culvert._R_full - R_theory) < 1e-10

    def test_rectangular_full_section(self):
        """矩形截面满管面积和水力半径"""
        culvert = Culvert("C1", 0, 1, shape='rectangular',
                          diameter_or_height=1.0, width=2.0)
        A_theory = 1.0 * 2.0
        P_theory = 2.0 * (1.0 + 2.0)
        R_theory = A_theory / P_theory
        assert abs(culvert._A_full - A_theory) < 1e-10
        assert abs(culvert._R_full - R_theory) < 1e-10

    def test_flow_increases_with_head(self):
        """流量随上游水头单调增大"""
        culvert = Culvert("C1", 0, 1, shape='circular',
                          diameter_or_height=1.0, length=10.0)
        Q_prev = 0.0
        for h_up in [0.5, 1.0, 2.0, 3.0, 5.0]:
            Q = culvert.compute_flow(h_up, 0.0)
            assert Q >= Q_prev, f"h_up={h_up}: 流量未单调增大"
            Q_prev = Q

    def test_no_flow_without_head(self):
        """无水头差时无流量"""
        culvert = Culvert("C1", 0, 1, shape='circular', diameter_or_height=1.0)
        Q = culvert.compute_flow(0.0, 0.0)
        assert Q == 0.0

    def test_outlet_control_dominates_long_culvert(self):
        """长涵洞（摩擦损失大）出口控制占主导"""
        short = Culvert("C_short", 0, 1, shape='circular',
                        diameter_or_height=1.0, length=5.0, n_manning=0.013)
        long_ = Culvert("C_long",  0, 1, shape='circular',
                        diameter_or_height=1.0, length=100.0, n_manning=0.013)
        Q_short = short.compute_flow(3.0, 0.0)
        Q_long  = long_.compute_flow(3.0, 0.0)
        assert Q_long < Q_short, "长涵洞流量应小于短涵洞"

    def test_multiple_barrels(self):
        """多孔涵洞：流量等比例增大"""
        c1 = Culvert("C1", 0, 1, shape='circular',
                     diameter_or_height=1.0, n_barrels=1)
        c3 = Culvert("C3", 0, 1, shape='circular',
                     diameter_or_height=1.0, n_barrels=3)
        Q1 = c1.compute_flow(2.0, 0.0)
        Q3 = c3.compute_flow(2.0, 0.0)
        assert abs(Q3 - 3 * Q1) < 1e-10

    def test_inlet_elevation(self):
        """进口底高程：有效水头 = h_up - z_in"""
        c_flat = Culvert("C1", 0, 1, shape='circular',
                         diameter_or_height=1.0, z_in=0.0)
        c_raised = Culvert("C2", 0, 1, shape='circular',
                           diameter_or_height=1.0, z_in=0.5)
        Q1 = c_flat.compute_flow(2.0, 0.0)
        Q2 = c_raised.compute_flow(2.0, 0.0)
        assert Q2 < Q1, "进口高程越高，有效水头越小，流量越小"


# ===========================================================================
# 5. 溢洪道（Spillway）
# ===========================================================================

class TestSpillway:

    def test_free_flow_formula(self):
        """自由出流：Q = Cw * L * H^1.5"""
        sp = Spillway("S1", 0, 1, length=10.0, z_crest=1.0, Cd=0.848)
        h_up = 2.0  # H = h_up - z_crest = 1.0
        Q = sp.compute_flow(h_up, 0.0)
        Q_theory = sp.Cw * 10.0 * 1.0**1.5
        assert abs(Q - Q_theory) / Q_theory < 1e-6

    def test_zero_flow_below_crest(self):
        """水位低于堰顶时流量为零"""
        sp = Spillway("S1", 0, 1, length=10.0, z_crest=1.0)
        Q = sp.compute_flow(0.8, 0.0)
        assert Q == 0.0

    def test_submerged_reduces_flow(self):
        """淹没时流量减小"""
        sp = Spillway("S1", 0, 1, length=10.0, z_crest=0.0)
        Q_free = sp.compute_flow(2.0, 0.0)
        Q_sub  = sp.compute_flow(2.0, 1.5)
        assert Q_sub < Q_free

    def test_flow_increases_with_head(self):
        """流量随水头单调增大（H^1.5 关系）"""
        sp = Spillway("S1", 0, 1, length=5.0, z_crest=0.0)
        Q_prev = 0.0
        for h_up in [0.5, 1.0, 1.5, 2.0, 3.0]:
            Q = sp.compute_flow(h_up, 0.0)
            assert Q >= Q_prev
            Q_prev = Q

    def test_cw_coefficient(self):
        """验证 Cw = Cd * sqrt(2g) * (2/3)^1.5"""
        sp = Spillway("S1", 0, 1, length=1.0, z_crest=0.0, Cd=0.848)
        Cw_theory = 0.848 * np.sqrt(2 * 9.81) * (2.0/3.0)**1.5
        assert abs(sp.Cw - Cw_theory) < 1e-10


# ===========================================================================
# 6. 构筑物组合管理器（StructureGroup）
# ===========================================================================

class TestStructureGroup:

    def test_add_and_count(self):
        """添加构筑物并计数"""
        group = StructureGroup(n_nodes=10)
        group.add(SluiceGate("G1", 0, 1, width=2.0, opening=0.5))
        group.add(PumpStation("P1", 2, 3, Q_design=1.0, h_start=0.3))
        assert len(group) == 2

    def test_source_terms_aggregation(self):
        """多构筑物源汇项正确聚合到节点"""
        group = StructureGroup(n_nodes=5)
        gate = SluiceGate("G1", 0, 1, width=2.0, opening=0.5, Cd=0.61)
        group.add(gate)

        h = np.array([2.0, 0.1, 0.5, 0.5, 0.5])
        q_src = group.compute_source_terms(h)

        Q = gate.compute_flow(2.0, 0.1)
        assert abs(q_src[0] - (-Q)) < 1e-10  # 上游流出
        assert abs(q_src[1] - (+Q)) < 1e-10  # 下游流入
        # 其他节点为零
        assert np.all(q_src[2:] == 0.0)

    def test_multiple_structures_same_node(self):
        """同一节点有多个构筑物时源汇项叠加"""
        group = StructureGroup(n_nodes=5)
        group.add(SluiceGate("G1", 0, 1, width=1.0, opening=0.5))
        group.add(SluiceGate("G2", 0, 2, width=1.0, opening=0.5))

        h = np.array([2.0, 0.1, 0.1, 0.5, 0.5])
        q_src = group.compute_source_terms(h)

        # 节点 0 应有两个流出项
        Q1 = SluiceGate("G1", 0, 1, width=1.0, opening=0.5).compute_flow(2.0, 0.1)
        Q2 = SluiceGate("G2", 0, 2, width=1.0, opening=0.5).compute_flow(2.0, 0.1)
        assert abs(q_src[0] - (-(Q1 + Q2))) < 1e-10

    def test_get_all_flows(self):
        """get_all_flows 返回正确的流量字典"""
        group = StructureGroup(n_nodes=5)
        gate = SluiceGate("Gate_A", 0, 1, width=2.0, opening=0.5)
        group.add(gate)

        h = np.array([2.0, 0.1, 0.5, 0.5, 0.5])
        flows = group.get_all_flows(h)

        assert "Gate_A" in flows
        Q_expected = gate.compute_flow(2.0, 0.1)
        assert abs(flows["Gate_A"] - Q_expected) < 1e-10

    def test_node_index_out_of_range(self):
        """节点索引越界时抛出 ValueError"""
        group = StructureGroup(n_nodes=5)
        with pytest.raises(ValueError):
            group.add(SluiceGate("G1", 0, 10, width=1.0, opening=0.5))

    def test_chain_add(self):
        """链式添加构筑物"""
        group = (StructureGroup(n_nodes=10)
                 .add(SluiceGate("G1", 0, 1, width=1.0, opening=0.3))
                 .add(Spillway("S1", 2, 3, length=5.0, z_crest=1.0)))
        assert len(group) == 2


# ===========================================================================
# 7. 物理场景综合验证
# ===========================================================================

class TestPhysicalScenarios:

    def test_gate_reservoir_drawdown(self):
        """
        场景：水库放水——闸门控制水库出流
        验证：随着上游水位下降，流量单调减小
        """
        gate = SluiceGate("Reservoir_Gate", 0, 1, width=5.0, opening=0.8, Cd=0.61)
        h_levels = np.linspace(3.0, 0.1, 20)
        Q_values = [gate.compute_flow(h, 0.0) for h in h_levels]
        # 流量应单调减小（允许最后几个接近零的情况）
        for i in range(len(Q_values) - 1):
            assert Q_values[i] >= Q_values[i+1] - 1e-10

    def test_pump_drainage_scenario(self):
        """
        场景：城市内涝排水——泵站将低洼区水排入河道
        验证：泵站在水位超过启泵水位后持续运行，水位下降后停止
        """
        pump = PumpStation("Drainage_Pump", 0, 1,
                           Q_design=0.5, h_start=0.4, h_stop=0.1)
        h_sequence = [0.2, 0.3, 0.45, 0.6, 0.35, 0.15, 0.08]
        expected_running = [False, False, True, True, True, True, False]

        for h, expected in zip(h_sequence, expected_running):
            pump.compute_flow(h, 2.0)  # 下游河道水位 2.0 m
            assert pump.is_running == expected, \
                f"h={h}: 泵运行状态应为 {expected}，实际为 {pump.is_running}"

    def test_culvert_under_road(self):
        """
        场景：公路涵洞过流——验证涵洞在不同水头下的流量合理性
        直径 1.2m，长 20m，Manning n=0.013
        """
        culvert = Culvert("Road_Culvert", 0, 1,
                          shape='circular', diameter_or_height=1.2,
                          length=20.0, n_manning=0.013, Ke=0.5)
        # 上游水深 2.0m（超过管径），下游 0.3m
        Q = culvert.compute_flow(2.0, 0.3)
        # 合理范围：1~5 m³/s（直径 1.2m 涵洞的典型流量）
        assert 0.5 < Q < 10.0, f"涵洞流量不合理：Q={Q:.3f} m³/s"

    def test_spillway_flood_routing(self):
        """
        场景：水库溢洪道——验证流量随水位的 H^1.5 关系
        """
        sp = Spillway("Dam_Spillway", 0, 1, length=20.0, z_crest=10.0, Cd=0.848)

        H_values = [0.5, 1.0, 2.0]  # 堰上水头
        Q_values = [sp.compute_flow(10.0 + H, 0.0) for H in H_values]

        # 验证 H^1.5 关系：Q2/Q1 ≈ (H2/H1)^1.5
        ratio_Q = Q_values[1] / Q_values[0]
        ratio_H = (H_values[1] / H_values[0])**1.5
        assert abs(ratio_Q - ratio_H) / ratio_H < 1e-6, \
            f"H^1.5 关系验证失败：Q比={ratio_Q:.4f}, H^1.5比={ratio_H:.4f}"

    def test_combined_structures_mass_conservation(self):
        """
        场景：闸门 + 溢洪道组合——验证源汇项总和为零（守恒）
        """
        group = StructureGroup(n_nodes=4)
        group.add(SluiceGate("G1", 0, 1, width=3.0, opening=0.6))
        group.add(Spillway("S1", 0, 2, length=10.0, z_crest=0.5))

        h = np.array([3.0, 0.2, 0.1, 0.5])
        q_src = group.compute_source_terms(h)

        # 所有节点源汇项之和应为零（守恒）
        assert abs(np.sum(q_src)) < 1e-10, \
            f"源汇项总和不为零：{np.sum(q_src):.2e}"
