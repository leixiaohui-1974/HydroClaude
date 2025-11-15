#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
补充缺失的5个组件测试
Supplement Missing Component Tests

根据覆盖分析，补充以下组件：
1. StorageBasin (调蓄池) - 高优先级
2. GlobeValve (截止阀)
3. NeedleValve (针阀)
4. ConeValve (锥阀)
5. HydropowerStation (完整水电站)

Author: HydroClaude Team
Date: 2025-11-15
"""

import sys
import os
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def test_storage_basin():
    """测试1: StorageBasin (调蓄池) - 高优先级"""
    print("\n" + "="*80)
    print("测试1: StorageBasin (调蓄池)")
    print("="*80)
    
    from web.backend.core.structures.storage import Storage
    
    # 创建调蓄池
    basin = Storage(
        name="Urban-Detention-Basin",
        position=1000.0,
        elevation=[0, 2, 4, 6, 8, 10],
        area=[500, 800, 1200, 1800, 2500, 3500]
    )
    
    print(f"调蓄池: {basin.name}")
    print(f"初始容积: {basin.current_volume:.2f} m³")
    
    # 场景1: 雨水入流
    print("\n场景1: 雨水入流调蓄")
    Q_in = 50.0  # m³/s
    Q_out = 20.0  # m³/s
    dt = 600.0  # 10分钟
    
    for i in range(5):
        new_elev, Q_total_out = basin.route(Q_in, Q_out, dt)
        V = basin.get_volume(new_elev)
        print(f"  时段{i+1}: 水位={new_elev:.2f}m, 容积={V:.0f}m³, 总出流={Q_total_out:.2f}m³/s")
    
    # 场景2: 排空调蓄池
    print("\n场景2: 排空调蓄池")
    for i in range(3):
        new_elev, Q_total_out = basin.route(0, 30.0, dt)
        V = basin.get_volume(new_elev)
        print(f"  时段{i+1}: 水位={new_elev:.2f}m, 容积={V:.0f}m³, 出流={Q_total_out:.2f}m³/s")
    
    # 场景3: 溢流计算
    print("\n场景3: 溢流计算")
    # 设置溢洪道参数
    basin.spillway_elevation = 8.0
    basin.spillway_width = 10.0
    basin.current_elevation = 9.0  # 超过溢洪道高程
    Q_spillway = basin.compute_spillway_flow()
    print(f"  当前水位={basin.current_elevation:.2f}m, 溢洪道高程={basin.spillway_elevation:.2f}m")
    print(f"  溢流流量: {Q_spillway:.2f} m³/s")
    
    print("\n✅ StorageBasin测试完成")
    return True


def test_globe_valve():
    """测试2: GlobeValve (截止阀)"""
    print("\n" + "="*80)
    print("测试2: GlobeValve (截止阀)")
    print("="*80)
    
    from web.backend.core.structures.valve import Valve, ValveType
    
    # 创建截止阀
    valve = Valve(
        name="Globe-Valve-001",
        position=500.0,
        valve_type=ValveType.GLOBE,
        diameter=0.3
    )
    
    print(f"阀门: {valve.name}")
    print(f"类型: {valve.valve_type.value}")
    print(f"直径: {valve.diameter}m")
    
    # 场景1: 不同开度的流量系数
    print("\n场景1: 开度-流量系数特性")
    for opening in [0.2, 0.4, 0.6, 0.8, 1.0]:
        Cv = valve.get_flow_coefficient(opening)
        print(f"  开度={opening*100:.0f}%: Cv={Cv:.3f}")
    
    # 场景2: 水头损失计算
    print("\n场景2: 不同流量的水头损失")
    valve.opening = 0.8
    for Q in [5.0, 10.0, 15.0, 20.0]:
        h_loss = valve.compute_headloss(Q)
        print(f"  Q={Q:.1f}m³/s: h_loss={h_loss:.3f}m")
    
    # 场景3: 过流能力计算
    print("\n场景3: 过流能力")
    valve.opening = 1.0
    h_upstream = 100.0  # m
    h_downstream = 95.0  # m (水头差5m)
    Q = valve.compute_discharge(h_upstream, h_downstream)
    print(f"  上游水头={h_upstream}m, 下游水头={h_downstream}m")
    print(f"  水头差={h_upstream-h_downstream}m: Q={Q:.2f}m³/s")
    
    # 场景4: 启闭过程模拟
    print("\n场景4: 启闭过程")
    valve.opening = 0.0
    target_opening = 1.0
    total_time = 60.0  # 60秒内全开
    
    for t in [0, 15, 30, 45, 60]:
        # 手动计算开度
        progress = min(t / total_time, 1.0)
        valve.opening = progress * target_opening
        print(f"  t={t}s: 开度={valve.opening*100:.1f}%")
    
    print("\n✅ GlobeValve测试完成")
    return True


def test_needle_valve():
    """测试3: NeedleValve (针阀)"""
    print("\n" + "="*80)
    print("测试3: NeedleValve (针阀)")
    print("="*80)
    
    from web.backend.core.structures.valve import Valve, ValveType
    
    # 创建针阀
    valve = Valve(
        name="Needle-Valve-001",
        position=800.0,
        valve_type=ValveType.NEEDLE,
        diameter=0.15
    )
    
    print(f"阀门: {valve.name}")
    print(f"类型: {valve.valve_type.value} (精细调节)")
    print(f"直径: {valve.diameter}m")
    
    # 场景1: 精细调节特性
    print("\n场景1: 精细调节特性（小开度范围）")
    for opening in [0.05, 0.10, 0.15, 0.20, 0.25]:
        Cv = valve.get_flow_coefficient(opening)
        valve.opening = opening
        # 100kPa ≈ 10.2m水头
        delta_h = 100.0 * 0.102
        Q = valve.compute_discharge(delta_h, 0)
        print(f"  开度={opening*100:.1f}%: Cv={Cv:.4f}, Q={Q:.3f}m³/s")
    
    # 场景2: 高压调节
    print("\n场景2: 高压条件下调节")
    valve.opening = 0.3
    # kPa 转换为 m 水柱: 1 kPa ≈ 0.102 m
    for p_kpa in [100, 200, 300, 400, 500]:
        delta_h = p_kpa * 0.102  # kPa → m
        Q = valve.compute_discharge(delta_h, 0)
        print(f"  压差={p_kpa}kPa ({delta_h:.1f}m): Q={Q:.2f}m³/s")
    
    # 场景3: 空化风险评估
    print("\n场景3: 空化风险评估")
    valve.opening = 0.5
    h_up = 500.0 * 0.102  # 500kPa → m
    h_down = 200.0 * 0.102  # 200kPa → m
    Q = valve.compute_discharge(h_up, h_down, 0.5)
    print(f"  开度=50%, 上游水头={h_up:.1f}m, 下游水头={h_down:.1f}m")
    print(f"  计算流量: {Q:.2f}m³/s")
    # 简单判断：如果水头差过大，有空化风险
    cavitation_risk = (h_up - h_down) > 50.0
    print(f"  空化风险: {'高' if cavitation_risk else '低'}")
    
    print("\n✅ NeedleValve测试完成")
    return True


def test_cone_valve():
    """测试4: ConeValve (锥阀)"""
    print("\n" + "="*80)
    print("测试4: ConeValve (锥阀)")
    print("="*80)
    
    from web.backend.core.structures.valve import Valve, ValveType
    
    # 创建锥阀
    valve = Valve(
        name="Cone-Valve-001",
        position=1200.0,
        valve_type=ValveType.CONE,
        diameter=0.8
    )
    
    print(f"阀门: {valve.name}")
    print(f"类型: {valve.valve_type.value} (快开型)")
    print(f"直径: {valve.diameter}m")
    
    # 场景1: 快开特性
    print("\n场景1: 快开流量特性")
    for opening in [0.1, 0.2, 0.3, 0.4, 0.5]:
        Cv = valve.get_flow_coefficient(opening)
        relative_flow = Cv / valve.cv_full_open
        print(f"  开度={opening*100:.0f}%: 相对流量={relative_flow*100:.1f}%")
    
    # 场景2: 大流量通过
    print("\n场景2: 大流量通过能力")
    valve.opening = 1.0
    for Q in [50, 100, 150, 200]:
        h_loss = valve.compute_headloss(Q)
        print(f"  Q={Q}m³/s: h_loss={h_loss:.2f}m")
    
    # 场景3: 快速启闭
    print("\n场景3: 快速启闭（应急场景）")
    valve.opening = 1.0
    valve.closing_time = 10.0  # 10秒快速关闭
    
    print(f"  初始开度: {valve.opening*100:.0f}%")
    target_opening = 0.0
    total_time = 10.0
    
    for i in range(6):
        t = i * 2
        # 手动计算关闭过程
        progress = min(t / total_time, 1.0)
        valve.opening = 1.0 - progress  # 从1.0到0.0
        print(f"  t={t}s: 开度={valve.opening*100:.1f}%")
    
    print("\n✅ ConeValve测试完成")
    return True


def test_hydropower_station_integrated():
    """测试5: HydropowerStation (完整水电站)"""
    print("\n" + "="*80)
    print("测试5: HydropowerStation (完整水电站集成)")
    print("="*80)
    
    from web.backend.core.structures.hydropower_station import (
        HydropowerStation, HydropowerConfig
    )
    from web.backend.core.structures.turbine import (
        Turbine, TurbineType, TurbineCharacteristics
    )
    from web.backend.core.structures.valve import Valve, ValveType
    
    # 创建水轮机
    turbine_char = TurbineCharacteristics(
        rated_head=100.0,
        rated_flow=50.0,
        rated_power=45.0,
        rated_efficiency=0.92,
        rated_speed=150.0,
        min_head=60.0,
        max_head=130.0
    )
    
    turbine = Turbine(
        name="Main-Turbine",
        position=2000.0,
        turbine_type=TurbineType.FRANCIS,
        characteristics=turbine_char
    )
    
    # 创建阀门
    valve = Valve(
        name="Inlet-Valve",
        position=1500.0,
        valve_type=ValveType.BUTTERFLY,
        diameter=2.0
    )
    valve.set_opening(0.9, 60.0)
    
    # 创建水电站配置
    config = HydropowerConfig(
        name="Demo-Hydropower-Plant",
        installed_capacity=50.0,
        num_units=1,
        normal_water_level=200.0,
        dead_water_level=150.0,
        design_water_level=205.0,
        intake_elevation=195.0,
        tailrace_elevation=50.0,
        penstock_length=1000.0,
        penstock_diameter=2.5
    )
    
    # 创建水电站
    station = HydropowerStation(
        config=config,
        turbines=[turbine],
        valves=[valve]
    )
    
    print(f"水电站: {station.config.name}")
    print(f"装机容量: {station.config.installed_capacity}MW")
    print(f"机组数: {station.config.num_units}")
    
    # 场景1: 正常发电
    print("\n场景1: 正常发电工况")
    station.current_reservoir_level = 200.0
    Q = 50.0
    
    H_gross = station.compute_gross_head()
    headloss = station.compute_headloss(Q)
    H_net = station.compute_net_head(Q)
    result = station.compute_station_output(target_flow=Q)
    
    print(f"  毛水头: {H_gross:.2f}m")
    print(f"  总损失: {headloss['total']:.2f}m")
    print(f"  净水头: {H_net:.2f}m")
    print(f"  出力: {result['power']:.2f}MW")
    print(f"  效率: {result['efficiency']*100:.1f}%")
    
    # 场景2: 不同负荷运行
    print("\n场景2: 不同负荷下运行")
    for load_factor in [0.3, 0.5, 0.7, 0.9, 1.0]:
        Q_load = 50.0 * load_factor
        result_load = station.compute_station_output(target_flow=Q_load)
        print(f"  负荷率={load_factor*100:.0f}%: Q={Q_load:.1f}m³/s, P={result_load['power']:.2f}MW")
    
    # 场景3: 年发电量估算
    print("\n场景3: 年发电量估算")
    # 构造流量历时曲线 [(Q, 保证率%)]
    flow_duration = [
        (60.0, 0), (55.0, 20), (50.0, 40), (45.0, 60), (40.0, 80), (35.0, 100)
    ]
    annual_result = station.estimate_annual_energy(flow_duration)
    print(f"  年发电量: {annual_result['annual_energy']/1000:.2f} GWh")
    print(f"  年利用小时数: {annual_result['utilization_hours']:.0f} h")
    print(f"  负荷因子: {annual_result['load_factor']*100:.1f}%")
    
    # 场景4: 经济运行优化
    print("\n场景4: 经济运行优化")
    available_flow = 60.0
    optimal_result = station.optimize_operation(available_flow)
    print(f"  可用流量: {available_flow}m³/s")
    if optimal_result:
        print(f"  最优机组数: {optimal_result['num_units']}")
        print(f"  单机流量: {optimal_result['flow_per_unit']:.2f}m³/s")
        print(f"  总出力: {optimal_result['total_power']:.2f}MW")
        print(f"  最优效率: {optimal_result['efficiency']*100:.1f}%")
    
    print("\n✅ HydropowerStation集成测试完成")
    return True


def run_all_tests():
    """运行所有补充测试"""
    print("\n" + "🎯"*40)
    print("补充缺失的5个组件测试".center(80))
    print("🎯"*40)
    
    results = []
    
    # 测试1: StorageBasin
    try:
        success = test_storage_basin()
        results.append(("StorageBasin", success))
    except Exception as e:
        print(f"\n❌ StorageBasin测试失败: {str(e)}")
        results.append(("StorageBasin", False))
    
    # 测试2: GlobeValve
    try:
        success = test_globe_valve()
        results.append(("GlobeValve", success))
    except Exception as e:
        print(f"\n❌ GlobeValve测试失败: {str(e)}")
        results.append(("GlobeValve", False))
    
    # 测试3: NeedleValve
    try:
        success = test_needle_valve()
        results.append(("NeedleValve", success))
    except Exception as e:
        print(f"\n❌ NeedleValve测试失败: {str(e)}")
        results.append(("NeedleValve", False))
    
    # 测试4: ConeValve
    try:
        success = test_cone_valve()
        results.append(("ConeValve", success))
    except Exception as e:
        print(f"\n❌ ConeValve测试失败: {str(e)}")
        results.append(("ConeValve", False))
    
    # 测试5: HydropowerStation
    try:
        success = test_hydropower_station_integrated()
        results.append(("HydropowerStation", success))
    except Exception as e:
        print(f"\n❌ HydropowerStation测试失败: {str(e)}")
        results.append(("HydropowerStation", False))
    
    # 生成报告
    print("\n" + "="*80)
    print("测试结果总结".center(80))
    print("="*80)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for component, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status} - {component}")
    
    print("-"*80)
    print(f"总计: {passed}/{total} 通过 ({passed/total*100:.1f}%)")
    
    print("\n" + "🎉"*40)
    if passed == total:
        print("✅ 所有组件测试通过！".center(80))
    else:
        print(f"⚠️  {total-passed}个测试失败".center(80))
    print("🎉"*40)


if __name__ == "__main__":
    run_all_tests()
