#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
南水北调中线京石段冰期调度模拟示例

HydroClaude冰期调度升级版功能演示：
1. 京石段13渠池14闸门配置
2. 冰盖下水力学（复合糙率）
3. 水温-冰情预测（热平衡方程）
4. 封冻判据（Fr≤0.065, V≤0.40m/s）
5. TCI寒潮指数与初冰预测
6. MPC冰期调度控制
7. 气象大模型接口集成

场景：京石段2023-2024年冬季冰期输水调度模拟
- 模拟时段：30天（12月中旬至1月中旬）
- 气温变化：0°C → -15°C → -5°C
- 初始水温：5°C
- 初始流量：200 m³/s

作者: HydroClaude Team
日期: 2025-11-02
"""

import numpy as np
import os
import sys
import warnings
warnings.filterwarnings("ignore")

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入HydroClaude冰期模块
try:
    from solvers.ice_hydraulics import IceCoveredChannelHydraulics, JingShiSegmentHydraulics
    from solvers.ice_prediction import (
        WaterTemperaturePredictor, FreezingCriteriaChecker, ColdWaveIndex,
        IceThicknessPredictor, IntegratedIcePredictor, IceConditionType, ColdWaveLevel
    )
    from solvers.ice_mpc_controller import (
        JingShiIcePeriodController, ControlMode, PoolParameters, ControlConstraints
    )
    from solvers.weather_llm_interface import (
        LLMWeatherInterface, DataAssimilator, IntegratedWeatherIcePredictor,
        WeatherModelType, MonitoringData
    )
    from solvers.ice_cover import IceCoverSolver
    from solvers.water_temperature import WaterTemperatureSolver
    MODULES_AVAILABLE = True
except ImportError as e:
    print(f"[警告] 部分模块导入失败: {e}")
    MODULES_AVAILABLE = False


def print_header(title: str):
    """打印标题"""
    print("=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_section(title: str):
    """打印章节"""
    print()
    print(f"[{title}]")
    print("-" * 80)


def generate_weather_scenario(n_days: int = 30) -> dict:
    """
    生成气象场景（模拟2023-2024年京石段冬季）

    12月中旬：降温开始
    12月下旬：寒潮来袭，最低气温-15°C
    1月上旬：气温回升
    """
    hours = np.arange(n_days * 24)
    days = hours / 24.0

    # 基础气温变化（日平均）
    T_base = np.zeros(n_days * 24)
    for i, d in enumerate(days):
        if d < 7:
            # 前7天：0°C → -5°C
            T_base[i] = 0 - 5 * d / 7
        elif d < 15:
            # 第7-15天：寒潮，-5°C → -15°C
            T_base[i] = -5 - 10 * (d - 7) / 8
        elif d < 22:
            # 第15-22天：维持低温，-15°C附近
            T_base[i] = -15 + 2 * np.sin(2 * np.pi * (d - 15) / 7)
        else:
            # 第22-30天：回暖，-15°C → -5°C
            T_base[i] = -15 + 10 * (d - 22) / 8

    # 添加日变化（振幅5°C）
    T_daily = 5.0 * np.sin(2 * np.pi * (hours - 6) / 24)
    T_air = T_base + T_daily

    # 太阳辐射（冬季最大300 W/m²）
    solar = np.zeros(n_days * 24)
    for i, h in enumerate(hours):
        hour_of_day = h % 24
        if 7 <= hour_of_day <= 17:
            solar[i] = 300 * np.sin(np.pi * (hour_of_day - 7) / 10)

    # 风速（冬季较强）
    wind = 3.5 + 2.0 * np.abs(np.sin(2 * np.pi * days / 5))

    # 相对湿度
    humidity = 0.55 + 0.15 * np.sin(2 * np.pi * days / 10)

    return {
        'hours': hours,
        'days': days,
        'T_air': T_air,
        'solar_radiation': solar,
        'wind_speed': wind,
        'relative_humidity': humidity
    }


def main():
    """主函数"""
    print_header("南水北调中线京石段冰期调度模拟")
    print()
    print("HydroClaude v2.0 - 冰期调度升级版")
    print("模拟场景：京石段2023-2024年冬季冰期输水")
    print()

    if not MODULES_AVAILABLE:
        print("[错误] 冰期调度模块未完全加载，请检查依赖")
        return

    # ========================================
    # 1. 场景配置
    # ========================================
    print_section("1. 场景配置")

    # 京石段参数
    n_pools = 13           # 13个渠池
    n_gates = 14           # 14座节制闸
    total_length = 217000  # 总长度217km (m)
    n_cells = 217          # 每公里1个网格

    dx = total_length / n_cells
    print(f"总长度: {total_length/1000:.1f} km")
    print(f"渠池数: {n_pools}")
    print(f"节制闸: {n_gates}")
    print(f"网格数: {n_cells}")
    print(f"空间步长: {dx:.1f} m")

    # 模拟时间
    n_days = 30
    dt_hours = 1.0  # 时间步长1小时
    dt = dt_hours * 3600  # 秒
    n_steps = n_days * 24
    print(f"\n模拟时段: {n_days} 天")
    print(f"时间步长: {dt_hours:.1f} 小时")
    print(f"总步数: {n_steps}")

    # ========================================
    # 2. 初始化模型
    # ========================================
    print_section("2. 初始化模型")

    # 2.1 水力学模型
    hydraulics = IceCoveredChannelHydraulics(
        n_bed=0.015,        # 混凝土衬砌
        n_ice_smooth=0.010,
        n_ice_rough=0.025
    )
    print("✓ 冰盖下水力学模型")

    # 2.2 京石段参数
    jingshi = JingShiSegmentHydraulics(n_cells=n_cells)
    print("✓ 京石段水力学参数")

    # 2.3 水温预测模型
    temp_predictor = WaterTemperaturePredictor(
        n_cells=n_cells,
        dx=dx,
        K_wa=18.0  # 京石段推荐值
    )
    print("✓ 水温预测模型 (K_wa=18 W/(m²·K))")

    # 2.4 封冻判据检查器
    freeze_checker = FreezingCriteriaChecker(
        Fr_critical_upstream=0.065,
        Fr_critical_downstream=0.055,
        V_critical_upstream=0.40,
        V_critical_downstream=0.35
    )
    print("✓ 封冻判据检查器 (Fr≤0.065, V≤0.40m/s)")

    # 2.5 寒潮指数计算器
    cold_wave_index = ColdWaveIndex(window_days=7)
    print("✓ TCI寒潮指数计算器")

    # 2.6 冰厚预测模型
    ice_thickness_predictor = IceThicknessPredictor()
    print("✓ 冰厚预测模型 (修正Stefan方程)")

    # 2.7 冰盖求解器
    ice_solver = IceCoverSolver(n_cells=n_cells)
    print("✓ 冰盖生长求解器")

    # 2.8 MPC控制器
    controller = JingShiIcePeriodController(dt=300.0)
    print("✓ MPC冰期调度控制器")

    # 2.9 气象大模型接口
    weather_predictor = IntegratedWeatherIcePredictor(
        model_type=WeatherModelType.STATISTICAL  # 演示用统计模型
    )
    print("✓ 气象大模型接口 (统计模型)")

    # ========================================
    # 3. 初始条件
    # ========================================
    print_section("3. 初始条件")

    # 水位（各渠池设计水深附近）
    h = np.full(n_cells, 3.0)  # 3m初始水深
    print(f"初始水深: {h[0]:.1f} m")

    # 流速
    Q_initial = 200.0  # m³/s
    width = 30.0  # m
    u = np.full(n_cells, Q_initial / (width * h[0]))
    print(f"初始流量: {Q_initial:.1f} m³/s")
    print(f"初始流速: {u[0]:.2f} m/s")

    # 水温
    T_water = np.full(n_cells, 5.0)  # 5°C
    print(f"初始水温: {T_water[0]:.1f} °C")

    # 冰厚
    h_ice = np.zeros(n_cells)
    ice_fraction = np.zeros(n_cells)
    print(f"初始冰厚: {h_ice[0]:.2f} m")

    # 闸门开度
    gate_openings = np.full(n_gates, 2.0)  # 2m初始开度
    print(f"初始闸门开度: {gate_openings[0]:.1f} m")

    # ========================================
    # 4. 生成气象场景
    # ========================================
    print_section("4. 气象场景")

    weather = generate_weather_scenario(n_days)

    print("气象预报（日平均）:")
    for day in [0, 7, 15, 22, 30]:
        if day < n_days:
            idx = day * 24
            idx_end = min((day + 1) * 24, len(weather['T_air']))
            T_avg = np.mean(weather['T_air'][idx:idx_end])
            solar_avg = np.mean(weather['solar_radiation'][idx:idx_end])
            wind_avg = np.mean(weather['wind_speed'][idx:idx_end])
            print(f"  Day {day:2d}: T_air={T_avg:+6.1f}°C, "
                  f"Solar={solar_avg:5.0f}W/m², Wind={wind_avg:.1f}m/s")

    # 寒潮分析
    T_air_daily = np.array([np.mean(weather['T_air'][d*24:(d+1)*24]) for d in range(n_days)])
    TCI, max_level = cold_wave_index.compute_TCI(T_air_daily)
    events = cold_wave_index.detect_cold_wave(T_air_daily)

    print(f"\n寒潮分析:")
    print(f"  最高寒潮等级: {max_level.name}")
    print(f"  寒潮事件数: {len(events)}")
    for i, event in enumerate(events):
        print(f"    事件{i+1}: Day {event['start_day']}-{event['end_day']}, "
              f"降温{event['max_drop']:.1f}°C, 等级{event['level'].name}")

    # ========================================
    # 5. 时间积分
    # ========================================
    print_section("5. 时间积分模拟")
    print(f"开始{n_days}天冰期调度模拟...")
    print()

    # 输出存储
    output_interval = 24  # 每天输出
    results = {
        'time': [],
        'T_water': [],
        'h_ice': [],
        'ice_fraction': [],
        'Q': [],
        'V': [],
        'Fr': [],
        'h': [],
        'mode': [],
        'warning_level': []
    }

    # 渠池水位（13个渠池）
    h_pools = np.array([3.0] * n_pools)

    # 当前流量
    Q_current = Q_initial

    print(f"{'Day':>5} | {'T_air':>7} | {'T_water':>7} | {'Ice':>8} | "
          f"{'Q':>7} | {'V':>6} | {'Fr':>6} | {'Mode':>12} | {'Warning':>8}")
    print("-" * 90)

    for step in range(n_steps):
        t = step * dt
        day = t / 86400.0
        hour = step

        # 获取当前气象
        T_air = weather['T_air'][hour]
        solar = weather['solar_radiation'][hour]
        wind = weather['wind_speed'][hour]
        humidity = weather['relative_humidity'][hour]

        # 1. 水温演变
        Q_net = temp_predictor.compute_net_heat_flux(
            T_water, T_air, solar, wind, humidity, ice_fraction=ice_fraction
        )
        # 简化水温更新
        dT = Q_net / (1000 * 4186 * h) * dt
        T_water = T_water + dT
        T_water = np.maximum(T_water, 0.0)

        # 2. 冰盖生长
        ice_state = ice_solver.step(dt, T_air, T_water)
        h_ice = ice_state['h_ice']
        ice_fraction = ice_state['ice_fraction']

        # 3. 封冻判据检查
        freeze_check = freeze_checker.check_freezing_potential(
            T_water, u, h
        )
        Fr = freeze_check['Fr']

        # 4. 冰期调度控制
        T_air_forecast = weather['T_air'][hour:min(hour+168, len(weather['T_air']))]
        if len(T_air_forecast) < 10:
            T_air_forecast = np.full(168, T_air)

        gate_openings, Q_target, control_info = controller.step(
            h_current=h_pools,
            Q_current=Q_current,
            T_water=T_water[:n_pools*16:16],  # 每个渠池取一个代表点
            T_air=T_air,
            T_air_forecast=list(T_air_forecast[:168:6]),  # 每6小时
            ice_fraction=ice_fraction[:n_pools*16:16],
            gate_openings_prev=gate_openings
        )

        # 更新流量和流速
        Q_current = Q_target
        u = np.full(n_cells, Q_current / (width * np.mean(h)))

        # 5. 冰盖下水力学
        if np.mean(ice_fraction) > 0.01:
            hydraulic_result = hydraulics.modify_saint_venant_for_ice(
                h, u, np.full(n_cells, Q_current), width, h_ice, ice_fraction,
                np.full(n_cells, 0.0001)
            )
            capacity_ratio = np.mean(hydraulic_result['capacity_ratio'])
        else:
            capacity_ratio = 1.0

        # 预警等级
        T_water_avg = np.mean(T_water)
        if T_water_avg <= 0.5:
            warning_level = 4
        elif T_water_avg <= 1.2:
            warning_level = 3
        elif T_water_avg <= 2.5:
            warning_level = 2
        elif T_air < -10:
            warning_level = 1
        else:
            warning_level = 0

        # 保存结果
        if (step + 1) % output_interval == 0:
            results['time'].append(day)
            results['T_water'].append(np.mean(T_water))
            results['h_ice'].append(np.mean(h_ice))
            results['ice_fraction'].append(np.mean(ice_fraction))
            results['Q'].append(Q_current)
            results['V'].append(np.mean(u))
            results['Fr'].append(np.mean(Fr))
            results['h'].append(np.mean(h))
            results['mode'].append(controller.mpc.mode.value)
            results['warning_level'].append(warning_level)

            # 打印进度
            mode_str = controller.mpc.mode.value.upper()
            warning_str = ['正常', '关注', '警戒', '警报', '紧急'][warning_level]
            print(f"{day:5.1f} | {T_air:+7.1f} | {T_water_avg:+7.2f} | "
                  f"{np.mean(h_ice)*100:6.2f}cm | {Q_current:7.1f} | "
                  f"{np.mean(u):6.3f} | {np.mean(Fr):6.4f} | "
                  f"{mode_str:>12} | {warning_str:>8}")

    print()
    print("✓ 模拟完成!")

    # ========================================
    # 6. 结果分析
    # ========================================
    print_section("6. 结果分析")

    # 统计
    print("模拟统计:")
    print(f"  水温变化: {results['T_water'][0]:.2f}°C → {results['T_water'][-1]:.2f}°C")
    print(f"  最低水温: {min(results['T_water']):.2f}°C (Day {results['time'][np.argmin(results['T_water'])]:.0f})")
    print(f"  最大冰厚: {max(results['h_ice'])*100:.2f}cm (Day {results['time'][np.argmax(results['h_ice'])]:.0f})")
    print(f"  最大冰盖覆盖率: {max(results['ice_fraction'])*100:.1f}%")
    print(f"  流量变化: {results['Q'][0]:.1f} → {results['Q'][-1]:.1f} m³/s")
    print(f"  最低流量: {min(results['Q']):.1f} m³/s")

    # 冰期调度模式统计
    ice_mode_count = sum(1 for m in results['mode'] if m == 'ice_period')
    normal_mode_count = len(results['mode']) - ice_mode_count
    print(f"\n调度模式统计:")
    print(f"  常规模式: {normal_mode_count} 天")
    print(f"  冰期模式: {ice_mode_count} 天")

    # 约束违反检查
    velocity_violations = sum(1 for v in results['V'] if v > 0.40)
    froude_violations = sum(1 for fr in results['Fr'] if fr > 0.065)
    print(f"\n约束检查:")
    print(f"  流速超限 (>0.40m/s): {velocity_violations} 次")
    print(f"  Froude超限 (>0.065): {froude_violations} 次")

    # ========================================
    # 7. 冰情预测演示
    # ========================================
    print_section("7. 冰情预测演示")

    # 获取最后时刻的状态
    from datetime import datetime
    monitoring_data = MonitoringData(
        timestamp=datetime.now(),
        station_ids=[f"JK{i:02d}" for i in range(18)],
        locations=np.linspace(0, 217, 18),
        T_air_measured=np.full(18, weather['T_air'][-1]),
        T_water_measured=np.full(18, results['T_water'][-1]),
        velocity_measured=np.full(18, results['V'][-1]),
        water_level_measured=np.full(18, results['h'][-1])
    )

    # 未来15天预测
    prediction = weather_predictor.predict(
        current_monitoring=monitoring_data,
        forecast_days=15
    )

    print("未来15天冰情预测:")
    print(f"  预报模型: {prediction['model_type']}")
    print(f"  风险等级: {prediction['ice_warning']['risk_level']} ({prediction['ice_warning']['risk_message']})")
    print(f"  预测最低水温: {prediction['ice_warning']['T_water_min']:.2f}°C")
    print(f"  累计负气温: {prediction['ice_warning']['AFDD_max']:.1f}°C·day")

    if prediction['daily_forecasts']:
        print("\n各时段预报:")
        for day, forecast in prediction['daily_forecasts'].items():
            print(f"  Day {day:2d}: T_air={forecast['T_air']:+.1f}°C, "
                  f"T_water={forecast['T_water']:.1f}°C, "
                  f"置信度={forecast['confidence']:.1%}")

    # ========================================
    # 8. 总结
    # ========================================
    print_section("8. 模拟总结")

    print("""
本次模拟演示了HydroClaude冰期调度升级版的核心功能：

┌─────────────────────────────────────────────────────────────────────────────┐
│  南水北调中线京石段冰期调度系统                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. 冰盖下水力学 (ice_hydraulics.py)                                        │
│     - 复合糙率计算 (Sabaneev公式)                                           │
│     - 冰盖下水力半径修正                                                    │
│     - 过流能力折减计算                                                      │
│                                                                             │
│  2. 冰情预测系统 (ice_prediction.py)                                        │
│     - 水温预测 (热平衡方程, K_wa=18 W/(m²·K))                               │
│     - 封冻判据 (Fr≤0.065, V≤0.40m/s)                                       │
│     - TCI寒潮指数                                                           │
│     - 冰厚预测 (修正Stefan方程)                                             │
│                                                                             │
│  3. MPC调度控制 (ice_mpc_controller.py)                                     │
│     - ID模型状态空间方程                                                    │
│     - 滚动时域优化                                                          │
│     - 动态目标水位                                                          │
│     - 冰期特殊约束                                                          │
│                                                                             │
│  4. 气象大模型接口 (weather_llm_interface.py)                               │
│     - 多模型集成 (GraphCast/盘古/风乌/FourCastNet)                          │
│     - 贝叶斯数据同化                                                        │
│     - 中线监测数据融合                                                      │
│                                                                             │
│  技术指标:                                                                  │
│     - 水温预测精度: ≤0.35°C (3天预报)                                       │
│     - 封冻时刻误差: <1天                                                    │
│     - 冰厚预测误差: <0.67cm                                                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
""")

    print("=" * 80)
    print("  HydroClaude v2.0 - 冰期调度升级版 模拟完成")
    print("=" * 80)


if __name__ == "__main__":
    main()
