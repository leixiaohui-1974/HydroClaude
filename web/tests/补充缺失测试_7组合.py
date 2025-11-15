#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
补充缺失的7个组合测试
Supplement Missing Combination Tests

根据覆盖分析，补充以下组合：
1. 水库-渠道-闸门灌溉系统
2. 水库-管道-水轮机发电系统
3. 河道-泵站-堰调蓄系统
4. 渠道-涵洞-闸门排水系统
5. 管道-阀门-水泵调压系统
6. 水库-渠道-侧堰分流系统
7. 河道-桥梁-跌水结构系统

Author: HydroClaude Team
Date: 2025-11-15
"""

import sys
import os
from pathlib import Path
import numpy as np

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def test_reservoir_channel_gate_irrigation():
    """测试1: 水库-渠道-闸门灌溉系统"""
    print("\n" + "="*80)
    print("测试1: 水库-渠道-闸门灌溉系统")
    print("="*80)
    
    from web.backend.core.structures.storage import Storage
    from web.backend.core.structures.channel import Channel, ChannelType, CrossSectionShape
    from web.backend.core.structures.advanced_gates import SluiceGate
    
    # 1. 水库
    print("\n步骤1: 创建水库")
    reservoir = Storage(
        name="Irrigation-Reservoir",
        position=0.0,
        elevation=[100, 105, 110, 115, 120],
        area=[10000, 15000, 22000, 30000, 40000],
        initial_elevation=115.0
    )
    print(f"  水库: {reservoir.name}")
    print(f"  初始水位: {reservoir.current_elevation:.2f}m")
    print(f"  初始容积: {reservoir.get_volume(reservoir.current_elevation)/1000:.0f} 千m³")
    
    # 2. 输水渠道
    print("\n步骤2: 创建输水渠道")
    channel = Channel(
        name="Main-Canal",
        channel_type=ChannelType.CANAL,
        length=5000.0,
        shape=CrossSectionShape.TRAPEZOIDAL,
        width=5.0,
        side_slope=2.0,  # 1:2边坡
        manning_n=0.025,
        slope=0.0005
    )
    print(f"  渠道: {channel.name}")
    print(f"  渠底宽: {channel.width}m")
    print(f"  边坡: 1:{channel.side_slope}")
    
    # 3. 控制闸门
    print("\n步骤3: 创建控制闸门")
    gate = SluiceGate(
        name="Control-Gate",
        width=5.0,
        opening=2.0
    )
    print(f"  闸门: {gate.name}")
    print(f"  闸孔宽: {gate.width}m")
    print(f"  开度: {gate.opening}m")
    
    # 场景: 灌溉取水过程
    print("\n场景: 灌溉取水过程")
    
    # 设计流量
    Q_design = 10.0  # m³/s
    print(f"  设计流量: {Q_design}m³/s")
    
    # 计算渠道所需水深
    h_channel = channel.compute_normal_depth(Q_design)
    print(f"  渠道水深: {h_channel:.2f}m")
    
    # 计算闸门下泄流量
    h_upstream = reservoir.current_elevation - 100.0  # 相对水深
    Q_gate, regime = gate.compute_discharge(h_upstream, opening=gate.opening)
    print(f"  闸门流量: {Q_gate:.2f}m³/s ({regime})")
    
    # 水力计算
    A = channel.compute_area(h_channel)
    P = channel.compute_wetted_perimeter(h_channel)
    R = channel.compute_hydraulic_radius(h_channel)
    Fr = channel.compute_froude_number(Q_design, h_channel)
    h_loss = channel.compute_headloss(Q_design, h_channel)
    
    print(f"  过流面积: {A:.2f}m²")
    print(f"  水力半径: {R:.2f}m")
    print(f"  Froude数: {Fr:.3f} ({'缓流' if Fr < 1 else '急流'})")
    print(f"  沿程损失: {h_loss:.2f}m")
    
    # 模拟一天的灌溉
    print("\n一天灌溉模拟:")
    dt = 3600.0  # 1小时
    for hour in range(0, 13, 4):
        # 白天灌溉，夜间停止
        Q_out = Q_design if 6 <= hour <= 18 else 0
        new_elev, _ = reservoir.route(0, Q_out, dt)
        V = reservoir.get_volume(new_elev)
        print(f"  {hour}:00 - 水位={new_elev:.2f}m, 容积={V/1000:.0f}千m³, 出流={Q_out}m³/s")
    
    print("\n✅ 水库-渠道-闸门灌溉系统测试完成")
    return True


def test_reservoir_pipe_turbine_hydropower():
    """测试2: 水库-管道-水轮机发电系统"""
    print("\n" + "="*80)
    print("测试2: 水库-管道-水轮机发电系统")
    print("="*80)
    
    from web.backend.core.structures.storage import Storage
    from web.backend.core.structures.channel import Channel, ChannelType, CrossSectionShape
    from web.backend.core.structures.turbine import Turbine, TurbineType, TurbineCharacteristics
    
    # 1. 上游水库
    print("\n步骤1: 创建上游水库")
    reservoir = Storage(
        name="Upper-Reservoir",
        position=0.0,
        elevation=[200, 210, 220, 230, 240],
        area=[50000, 65000, 82000, 100000, 120000],
        initial_elevation=230.0
    )
    print(f"  水库: {reservoir.name}")
    print(f"  初始水位: {reservoir.current_elevation:.2f}m")
    
    # 2. 压力管道（引水隧洞）
    print("\n步骤2: 创建压力管道")
    penstock = Channel(
        name="Penstock",
        position=1000.0,
        channel_type=ChannelType.PENSTOCK,
        section_shape=CrossSectionShape.CIRCULAR,
        diameter=3.0,
        roughness=0.014,
        slope=0.2,  # 20%坡度
        length=1000.0
    )
    print(f"  管道: {penstock.name}")
    print(f"  直径: {penstock.diameter}m")
    print(f"  长度: {penstock.length}m")
    
    # 3. 水轮机
    print("\n步骤3: 创建水轮机")
    turbine_char = TurbineCharacteristics(
        rated_head=180.0,
        rated_flow=30.0,
        rated_power=50.0,
        rated_efficiency=0.93,
        rated_speed=150.0,
        min_head=120.0,
        max_head=220.0
    )
    
    turbine = Turbine(
        name="Francis-Turbine",
        position=2000.0,
        turbine_type=TurbineType.FRANCIS,
        characteristics=turbine_char
    )
    print(f"  水轮机: {turbine.name}")
    print(f"  额定水头: {turbine.char.rated_head}m")
    print(f"  额定流量: {turbine.char.rated_flow}m³/s")
    print(f"  额定功率: {turbine.char.rated_power}MW")
    
    # 场景: 发电运行
    print("\n场景: 发电运行")
    
    # 水头计算
    tailwater_level = 50.0  # 尾水位
    H_gross = reservoir.current_elevation - tailwater_level
    print(f"  毛水头: {H_gross:.2f}m")
    
    # 管道损失
    Q = turbine.char.rated_flow
    h_loss = penstock.compute_headloss(Q, penstock.diameter/2)
    H_net = H_gross - h_loss
    print(f"  管道损失: {h_loss:.2f}m")
    print(f"  净水头: {H_net:.2f}m")
    
    # 水轮机出力
    P, eta = turbine.compute_power(H_net, Q)
    print(f"  发电功率: {P:.2f}MW")
    print(f"  水轮机效率: {eta*100:.1f}%")
    
    # 运行曲线
    print("\n不同负荷下运行:")
    for load in [0.4, 0.6, 0.8, 1.0]:
        Q_load = turbine.char.rated_flow * load
        P_load, eta_load = turbine.compute_power(H_net, Q_load)
        print(f"  负荷={load*100:.0f}%: Q={Q_load:.1f}m³/s, P={P_load:.2f}MW, η={eta_load*100:.1f}%")
    
    print("\n✅ 水库-管道-水轮机发电系统测试完成")
    return True


def test_river_pump_weir_regulation():
    """测试3: 河道-泵站-堰调蓄系统"""
    print("\n" + "="*80)
    print("测试3: 河道-泵站-堰调蓄系统")
    print("="*80)
    
    from web.backend.core.structures.channel import Channel, ChannelType, CrossSectionShape
    from web.backend.core.structures.pump_station import PumpStation, PumpType, PumpCurve, ControlMode
    from web.backend.core.structures.weir import BroadCrestedWeir
    
    # 1. 河道
    print("\n步骤1: 创建河道")
    river = Channel(
        name="Main-River",
        position=0.0,
        channel_type=ChannelType.RIVER,
        section_shape=CrossSectionShape.NATURAL,
        bottom_width=30.0,
        side_slope=3.0,
        roughness=0.035,
        slope=0.0001,
        length=10000.0
    )
    print(f"  河道: {river.name}")
    print(f"  河宽: {river.bottom_width}m")
    
    # 2. 泵站
    print("\n步骤2: 创建泵站")
    pump_curve = PumpCurve(
        Q_data=[0, 5, 10, 15, 20],
        H_data=[30, 28, 25, 20, 12],
        efficiency_data=[0, 0.7, 0.85, 0.82, 0.65]
    )
    
    pump_station = PumpStation(
        name="Drainage-Pump",
        position=5000.0,
        pump_type=PumpType.CENTRIFUGAL,
        num_pumps=3,
        pump_curve=pump_curve,
        control_mode=ControlMode.MANUAL
    )
    print(f"  泵站: {pump_station.name}")
    print(f"  泵数: {pump_station.num_pumps}")
    print(f"  控制: {pump_station.control_mode.value}")
    
    # 3. 溢流堰
    print("\n步骤3: 创建溢流堰")
    weir = BroadCrestedWeir(
        name="Overflow-Weir",
        position=8000.0,
        width=20.0,
        crest_height=5.0
    )
    print(f"  堰: {weir.name}")
    print(f"  堰顶宽: {weir.width}m")
    print(f"  堰顶高程: {weir.crest_height}m")
    
    # 场景: 洪水调节
    print("\n场景: 洪水调节")
    
    # 河道来流
    Q_flood = 150.0  # m³/s
    h_river = river.compute_normal_depth(Q_flood)
    print(f"  洪峰流量: {Q_flood}m³/s")
    print(f"  河道水深: {h_river:.2f}m")
    
    # 泵站排水
    Q_pump = pump_station.compute_total_flow(25.0)
    print(f"  泵站排水: {Q_pump:.2f}m³/s")
    
    # 堰顶溢流
    h_weir = h_river - weir.crest_height
    Q_weir = weir.compute_discharge(max(h_weir, 0))
    print(f"  堰顶水头: {h_weir:.2f}m")
    print(f"  溢流流量: {Q_weir:.2f}m³/s")
    
    # 水量平衡
    Q_total_out = Q_pump + Q_weir
    print(f"  总出流: {Q_total_out:.2f}m³/s")
    print(f"  水量平衡: {'平衡' if abs(Q_flood - Q_total_out) < 10 else '不平衡'}")
    
    print("\n✅ 河道-泵站-堰调蓄系统测试完成")
    return True


def test_canal_culvert_gate_drainage():
    """测试4: 渠道-涵洞-闸门排水系统"""
    print("\n" + "="*80)
    print("测试4: 渠道-涵洞-闸门排水系统")
    print("="*80)
    
    from web.backend.core.structures.channel import Channel, ChannelType, CrossSectionShape
    from web.backend.core.structures.culvert import Culvert
    from web.backend.core.structures.gate import SluiceGate
    
    # 1. 排水渠道
    print("\n步骤1: 创建排水渠道")
    canal = Channel(
        name="Drainage-Canal",
        position=0.0,
        channel_type=ChannelType.CANAL,
        section_shape=CrossSectionShape.RECTANGULAR,
        bottom_width=3.0,
        roughness=0.02,
        slope=0.001,
        length=2000.0
    )
    print(f"  渠道: {canal.name}")
    print(f"  宽度: {canal.bottom_width}m")
    
    # 2. 涵洞
    print("\n步骤2: 创建涵洞")
    culvert = Culvert(
        name="Road-Culvert",
        position=1000.0,
        width=2.5,
        height=2.0,
        length=30.0,
        roughness=0.015
    )
    print(f"  涵洞: {culvert.name}")
    print(f"  尺寸: {culvert.width}m × {culvert.height}m")
    print(f"  长度: {culvert.length}m")
    
    # 3. 控制闸门
    print("\n步骤3: 创建控制闸门")
    gate = SluiceGate(
        name="Outlet-Gate",
        position=2000.0,
        width=3.0,
        opening=1.5
    )
    print(f"  闸门: {gate.name}")
    print(f"  开度: {gate.opening}m")
    
    # 场景: 暴雨排水
    print("\n场景: 暴雨排水")
    
    # 进水流量
    Q_in = 15.0  # m³/s
    print(f"  进水流量: {Q_in}m³/s")
    
    # 渠道水深
    h_canal = canal.compute_normal_depth(Q_in)
    print(f"  渠道水深: {h_canal:.2f}m")
    
    # 涵洞过流
    h_up = 3.0  # 上游水深
    h_down = 1.5  # 下游水深
    Q_culvert, flow_type = culvert.compute_discharge(h_up, h_down)
    print(f"  涵洞流量: {Q_culvert:.2f}m³/s ({flow_type})")
    
    # 闸门下泄
    Q_gate, regime = gate.compute_discharge(h_canal, opening=gate.opening)
    print(f"  闸门流量: {Q_gate:.2f}m³/s ({regime})")
    
    # 系统效率
    efficiency = min(Q_culvert, Q_gate) / Q_in * 100
    print(f"  系统排水效率: {efficiency:.1f}%")
    
    print("\n✅ 渠道-涵洞-闸门排水系统测试完成")
    return True


def test_pipe_valve_pump_pressure():
    """测试5: 管道-阀门-水泵调压系统"""
    print("\n" + "="*80)
    print("测试5: 管道-阀门-水泵调压系统")
    print("="*80)
    
    from web.backend.core.structures.channel import Channel, ChannelType, CrossSectionShape
    from web.backend.core.structures.valve import Valve, ValveType
    from web.backend.core.structures.pump_station import PumpStation, PumpType, PumpCurve, ControlMode
    
    # 1. 输水管道
    print("\n步骤1: 创建输水管道")
    pipe = Channel(
        name="Water-Supply-Pipe",
        position=0.0,
        channel_type=ChannelType.PIPE,
        section_shape=CrossSectionShape.CIRCULAR,
        diameter=0.8,
        roughness=0.012,
        slope=0.01,
        length=5000.0
    )
    print(f"  管道: {pipe.name}")
    print(f"  直径: {pipe.diameter}m")
    print(f"  长度: {pipe.length}m")
    
    # 2. 调节阀门
    print("\n步骤2: 创建调节阀门")
    valve = Valve(
        name="Pressure-Control-Valve",
        position=2500.0,
        valve_type=ValveType.BUTTERFLY,
        diameter=0.8
    )
    print(f"  阀门: {valve.name}")
    print(f"  类型: {valve.valve_type.value}")
    
    # 3. 增压泵站
    print("\n步骤3: 创建增压泵站")
    pump_curve = PumpCurve(
        Q_data=[0, 0.2, 0.4, 0.6, 0.8, 1.0],
        H_data=[60, 58, 54, 48, 40, 28],
        efficiency_data=[0, 0.6, 0.8, 0.85, 0.82, 0.7]
    )
    
    pump = PumpStation(
        name="Booster-Pump",
        position=5000.0,
        pump_type=PumpType.CENTRIFUGAL,
        num_pumps=2,
        pump_curve=pump_curve,
        control_mode=ControlMode.MANUAL
    )
    print(f"  泵站: {pump.name}")
    print(f"  泵数: {pump.num_pumps}")
    
    # 场景: 压力调节
    print("\n场景: 压力调节")
    
    # 设计流量
    Q = 0.5  # m³/s
    print(f"  设计流量: {Q}m³/s")
    
    # 管道损失
    h_pipe = pipe.compute_headloss(Q, pipe.diameter/2)
    print(f"  管道损失: {h_pipe:.2f}m")
    
    # 阀门调节
    print("\n阀门开度调节:")
    for opening in [0.4, 0.6, 0.8, 1.0]:
        valve.opening = opening
        h_valve = valve.compute_headloss(Q, opening)
        print(f"  开度={opening*100:.0f}%: 阀门损失={h_valve:.2f}m")
    
    # 泵站扬程
    H_pump = pump.compute_total_head(Q)
    print(f"\n泵站扬程: {H_pump:.2f}m")
    
    # 系统水头平衡
    H_total = H_pump - h_pipe - valve.compute_headloss(Q)
    print(f"系统剩余水头: {H_total:.2f}m")
    
    print("\n✅ 管道-阀门-水泵调压系统测试完成")
    return True


def test_reservoir_canal_sideweir_diversion():
    """测试6: 水库-渠道-侧堰分流系统"""
    print("\n" + "="*80)
    print("测试6: 水库-渠道-侧堰分流系统")
    print("="*80)
    
    from web.backend.core.structures.storage import Storage
    from web.backend.core.structures.channel import Channel, ChannelType, CrossSectionShape
    from web.backend.core.structures.side_weir import SideWeir
    
    # 1. 调节水库
    print("\n步骤1: 创建调节水库")
    reservoir = Storage(
        name="Regulating-Reservoir",
        position=0.0,
        elevation=[80, 85, 90, 95, 100],
        area=[20000, 28000, 38000, 50000, 65000],
        initial_elevation=92.0
    )
    print(f"  水库: {reservoir.name}")
    print(f"  水位: {reservoir.current_elevation:.2f}m")
    
    # 2. 主渠道
    print("\n步骤2: 创建主渠道")
    main_canal = Channel(
        name="Main-Canal",
        position=1000.0,
        channel_type=ChannelType.CANAL,
        section_shape=CrossSectionShape.TRAPEZOIDAL,
        bottom_width=6.0,
        side_slope=2.0,
        roughness=0.025,
        slope=0.0003,
        length=8000.0
    )
    print(f"  主渠: {main_canal.name}")
    print(f"  底宽: {main_canal.bottom_width}m")
    
    # 3. 侧堰分流
    print("\n步骤3: 创建侧堰")
    side_weir = SideWeir(
        name="Diversion-SideWeir",
        position=5000.0,
        length=30.0,
        crest_elevation=2.0
    )
    print(f"  侧堰: {side_weir.name}")
    print(f"  长度: {side_weir.length}m")
    print(f"  堰顶高程: {side_weir.crest_elevation}m")
    
    # 场景: 灌溉分水
    print("\n场景: 灌溉分水")
    
    # 主渠来流
    Q_main = 25.0  # m³/s
    h_main = main_canal.compute_normal_depth(Q_main)
    print(f"  主渠流量: {Q_main}m³/s")
    print(f"  主渠水深: {h_main:.2f}m")
    
    # 侧堰分流
    Q_divert = side_weir.compute_discharge(h_main)
    print(f"  侧堰分流: {Q_divert:.2f}m³/s")
    
    # 下游剩余
    Q_downstream = Q_main - Q_divert
    print(f"  下游流量: {Q_downstream:.2f}m³/s")
    print(f"  分流比: {Q_divert/Q_main*100:.1f}%")
    
    # 不同水深下的分流
    print("\n不同水深下分流:")
    for h in [2.5, 3.0, 3.5, 4.0]:
        Q_div = side_weir.compute_discharge(h)
        ratio = Q_div / Q_main * 100 if Q_main > 0 else 0
        print(f"  水深={h:.1f}m: 分流={Q_div:.2f}m³/s ({ratio:.1f}%)")
    
    print("\n✅ 水库-渠道-侧堰分流系统测试完成")
    return True


def test_river_bridge_dropstructure():
    """测试7: 河道-桥梁-跌水结构系统"""
    print("\n" + "="*80)
    print("测试7: 河道-桥梁-跌水结构系统")
    print("="*80)
    
    from web.backend.core.structures.channel import Channel, ChannelType, CrossSectionShape
    from web.backend.core.structures.bridge import Bridge
    from web.backend.core.structures.drop_structure import DropStructure
    
    # 1. 上游河道
    print("\n步骤1: 创建上游河道")
    river_upstream = Channel(
        name="Upstream-River",
        position=0.0,
        channel_type=ChannelType.RIVER,
        section_shape=CrossSectionShape.NATURAL,
        bottom_width=40.0,
        side_slope=3.0,
        roughness=0.035,
        slope=0.0002,
        length=5000.0
    )
    print(f"  河道: {river_upstream.name}")
    print(f"  河宽: {river_upstream.bottom_width}m")
    
    # 2. 桥梁
    print("\n步骤2: 创建桥梁")
    bridge = Bridge(
        name="Highway-Bridge",
        position=2500.0,
        width=40.0,
        pier_width=2.0,
        num_piers=3,
        deck_elevation=15.0
    )
    print(f"  桥梁: {bridge.name}")
    print(f"  桥宽: {bridge.width}m")
    print(f"  桥墩数: {bridge.num_piers}")
    
    # 3. 跌水结构
    print("\n步骤3: 创建跌水结构")
    drop = DropStructure(
        name="Energy-Dissipator",
        position=3500.0,
        width=35.0,
        drop_height=3.0
    )
    print(f"  跌水: {drop.name}")
    print(f"  跌差: {drop.drop_height}m")
    
    # 4. 下游河道
    print("\n步骤4: 创建下游河道")
    river_downstream = Channel(
        name="Downstream-River",
        position=4000.0,
        channel_type=ChannelType.RIVER,
        section_shape=CrossSectionShape.NATURAL,
        bottom_width=40.0,
        side_slope=3.0,
        roughness=0.035,
        slope=0.0002,
        length=5000.0
    )
    print(f"  河道: {river_downstream.name}")
    
    # 场景: 洪水演进
    print("\n场景: 洪水演进")
    
    # 上游来流
    Q_flood = 200.0  # m³/s
    h_up = river_upstream.compute_normal_depth(Q_flood)
    print(f"  洪峰流量: {Q_flood}m³/s")
    print(f"  上游水深: {h_up:.2f}m")
    
    # 桥梁壅水
    h_bridge = bridge.compute_afflux(Q_flood, h_up)
    print(f"  桥梁壅水: {h_bridge:.2f}m")
    print(f"  桥下水深: {h_up + h_bridge:.2f}m")
    
    # 跌水消能
    h_down_drop, energy_loss = drop.compute_downstream_depth(Q_flood, h_up)
    print(f"  跌水消能: {energy_loss:.2f}m")
    print(f"  跌后水深: {h_down_drop:.2f}m")
    
    # 下游水深
    h_down = river_downstream.compute_normal_depth(Q_flood)
    print(f"  下游水深: {h_down:.2f}m")
    
    # 水面线计算
    print("\n水面线:")
    positions = [0, 2500, 3500, 4000, 9000]
    elevations = [
        100.0,
        100.0 + 2500*river_upstream.slope + h_bridge,
        100.0 + 3500*river_upstream.slope - drop.drop_height,
        100.0 + 3500*river_upstream.slope - drop.drop_height,
        100.0 + 3500*river_upstream.slope - drop.drop_height + 5000*river_downstream.slope
    ]
    
    for pos, elev in zip(positions, elevations):
        print(f"  x={pos}m: z={elev:.2f}m")
    
    print("\n✅ 河道-桥梁-跌水结构系统测试完成")
    return True


def run_all_tests():
    """运行所有组合测试"""
    print("\n" + "🎯"*40)
    print("补充缺失的7个组合测试".center(80))
    print("🎯"*40)
    
    results = []
    
    # 测试1: 水库-渠道-闸门灌溉
    try:
        success = test_reservoir_channel_gate_irrigation()
        results.append(("水库-渠道-闸门灌溉", success))
    except Exception as e:
        print(f"\n❌ 测试1失败: {str(e)}")
        import traceback
        traceback.print_exc()
        results.append(("水库-渠道-闸门灌溉", False))
    
    # 测试2: 水库-管道-水轮机发电
    try:
        success = test_reservoir_pipe_turbine_hydropower()
        results.append(("水库-管道-水轮机发电", success))
    except Exception as e:
        print(f"\n❌ 测试2失败: {str(e)}")
        import traceback
        traceback.print_exc()
        results.append(("水库-管道-水轮机发电", False))
    
    # 测试3: 河道-泵站-堰调蓄
    try:
        success = test_river_pump_weir_regulation()
        results.append(("河道-泵站-堰调蓄", success))
    except Exception as e:
        print(f"\n❌ 测试3失败: {str(e)}")
        import traceback
        traceback.print_exc()
        results.append(("河道-泵站-堰调蓄", False))
    
    # 测试4: 渠道-涵洞-闸门排水
    try:
        success = test_canal_culvert_gate_drainage()
        results.append(("渠道-涵洞-闸门排水", success))
    except Exception as e:
        print(f"\n❌ 测试4失败: {str(e)}")
        import traceback
        traceback.print_exc()
        results.append(("渠道-涵洞-闸门排水", False))
    
    # 测试5: 管道-阀门-水泵调压
    try:
        success = test_pipe_valve_pump_pressure()
        results.append(("管道-阀门-水泵调压", success))
    except Exception as e:
        print(f"\n❌ 测试5失败: {str(e)}")
        import traceback
        traceback.print_exc()
        results.append(("管道-阀门-水泵调压", False))
    
    # 测试6: 水库-渠道-侧堰分流
    try:
        success = test_reservoir_canal_sideweir_diversion()
        results.append(("水库-渠道-侧堰分流", success))
    except Exception as e:
        print(f"\n❌ 测试6失败: {str(e)}")
        import traceback
        traceback.print_exc()
        results.append(("水库-渠道-侧堰分流", False))
    
    # 测试7: 河道-桥梁-跌水结构
    try:
        success = test_river_bridge_dropstructure()
        results.append(("河道-桥梁-跌水结构", success))
    except Exception as e:
        print(f"\n❌ 测试7失败: {str(e)}")
        import traceback
        traceback.print_exc()
        results.append(("河道-桥梁-跌水结构", False))
    
    # 生成报告
    print("\n" + "="*80)
    print("测试结果总结".center(80))
    print("="*80)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status} - {test_name}")
    
    print("-"*80)
    print(f"总计: {passed}/{total} 通过 ({passed/total*100:.1f}%)")
    
    print("\n" + "🎉"*40)
    if passed == total:
        print("✅ 所有组合测试通过！".center(80))
    else:
        print(f"⚠️  {total-passed}个测试失败".center(80))
    print("🎉"*40)
    
    return passed, total


if __name__ == "__main__":
    passed, total = run_all_tests()
    exit(0 if passed == total else 1)
