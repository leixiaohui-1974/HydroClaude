#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试闸门流量对水深的导数计算

调试为什么数值微分计算出零导数

作者: Claude
日期: 2025-10-22
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from solvers.gate import SluiceGate

def test_gate_derivatives():
    """测试闸门流量对水深的导数"""

    print("=" * 100)
    print("闸门流量导数测试")
    print("=" * 100)
    print()

    # 创建闸门
    B = 10.0
    e = 5.0
    gate = SluiceGate(position=50.0, width=B, opening=e, Cd=0.6)

    # 测试场景：均匀流初值（delta_h = 0）
    h_up = 0.9298
    h_down = 0.9298

    print(f"闸门参数:")
    print(f"  宽度 B = {B} m")
    print(f"  开度 e = {e} m")
    print(f"  Cd = {gate.Cd}")
    print(f"  淹没阈值 = {gate.submerged_threshold} m")
    print()

    print(f"水深条件:")
    print(f"  上游水深 h_up = {h_up:.4f} m")
    print(f"  下游水深 h_down = {h_down:.4f} m")
    print(f"  水位差 Δh = {h_up - h_down:.6f} m")
    print()

    # 计算基准流量
    Q_0, flow_type = gate.calculate_discharge(h_up, h_down, t=0.0)
    print(f"基准流量 Q_0 = {Q_0:.6f} m³/s, 流态 = {flow_type}")
    print()

    # 测试不同的eps值
    eps_values = [1e-6, 1e-5, 1e-4, 1e-3, 1e-2]

    print("=" * 100)
    print("数值微分测试（扰动h_upstream）")
    print("=" * 100)
    print(f"{'eps':<15} {'Q(h+eps)':<20} {'dQ/dh_up':<20} {'说明':<30}")
    print("-" * 100)

    for eps in eps_values:
        Q_h_up_plus, flow_type_plus = gate.calculate_discharge(h_up + eps, h_down, t=0.0)
        dQ_dh_up = (Q_h_up_plus - Q_0) / eps

        # 理论导数（解析）
        delta_h_eff = max(1e-4, h_up - h_down)
        if flow_type == 'submerged':
            # Q = Cd * B * e * sqrt(2g * delta_h_eff)
            # dQ/dh_up = Cd * B * e * (1/2) * (2g * delta_h_eff)^(-1/2) * 2g
            #          = Cd * B * e * g / sqrt(2g * delta_h_eff)
            dQ_dh_up_analytic = gate.Cd * B * e * gate.g / np.sqrt(2 * gate.g * delta_h_eff)
        else:
            # Q = Cd * B * e * sqrt(2g * h_up)
            dQ_dh_up_analytic = gate.Cd * B * e * gate.g / np.sqrt(2 * gate.g * h_up)

        note = ""
        if dQ_dh_up == 0:
            note = "❌ 导数为零（max截断）"
        elif abs(dQ_dh_up - dQ_dh_up_analytic) / dQ_dh_up_analytic < 0.01:
            note = "✓ 导数正确"
        else:
            note = f"⚠ 误差{abs(dQ_dh_up - dQ_dh_up_analytic) / dQ_dh_up_analytic * 100:.1f}%"

        print(f"{eps:<15.2e} {Q_h_up_plus:<20.6f} {dQ_dh_up:<20.6f} {note:<30}")

    print()
    print("=" * 100)
    print("数值微分测试（扰动h_downstream）")
    print("=" * 100)
    print(f"{'eps':<15} {'Q(h_down+eps)':<20} {'dQ/dh_down':<20} {'说明':<30}")
    print("-" * 100)

    for eps in eps_values:
        Q_h_down_plus, flow_type_plus = gate.calculate_discharge(h_up, h_down + eps, t=0.0)
        dQ_dh_down = (Q_h_down_plus - Q_0) / eps

        # 理论导数（解析）
        delta_h_eff = max(1e-4, h_up - h_down)
        if flow_type == 'submerged':
            # Q = Cd * B * e * sqrt(2g * delta_h_eff)
            # dQ/dh_down = Cd * B * e * (1/2) * (2g * delta_h_eff)^(-1/2) * 2g * (-1)
            #            = -Cd * B * e * g / sqrt(2g * delta_h_eff)
            dQ_dh_down_analytic = -gate.Cd * B * e * gate.g / np.sqrt(2 * gate.g * delta_h_eff)
        else:
            dQ_dh_down_analytic = 0.0  # 自由出流不依赖下游水深

        note = ""
        if dQ_dh_down == 0:
            note = "❌ 导数为零（max截断）"
        elif abs(dQ_dh_down - dQ_dh_down_analytic) < 1e-6:
            note = "✓ 导数正确"
        else:
            note = f"⚠ 误差{abs(dQ_dh_down - dQ_dh_down_analytic):.2e}"

        print(f"{eps:<15.2e} {Q_h_down_plus:<20.6f} {dQ_dh_down:<20.6f} {note:<30}")

    print()
    print("=" * 100)
    print("问题诊断")
    print("=" * 100)
    print()
    print("根本原因：")
    print("  calculate_discharge 中使用了 max(1e-4, delta_h) 来避免负值或零")
    print("  当 delta_h < 1e-4 时，微小扰动 eps=1e-6 被截断，导致数值微分失败")
    print()
    print("解决方案：")
    print("  方案1：使用更大的扰动 eps（如 1e-3），但精度较低")
    print("  方案2：解析计算导数（推荐）")
    print("  方案3：改进 calculate_discharge，避免硬截断")
    print()


if __name__ == '__main__':
    test_gate_derivatives()
