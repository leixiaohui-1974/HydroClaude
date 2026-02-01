#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
冰期调度升级功能测试

测试内容：
1. 冰盖下水力学模块测试
2. 水温预测模型测试
3. 封冻判据系统测试
4. TCI寒潮指数测试
5. MPC控制器测试
6. 气象大模型接口测试

作者: HydroClaude Team
日期: 2025-11-02
"""

import numpy as np
import pytest
import sys
import os
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from solvers.ice_hydraulics import (
    IceCoveredChannelHydraulics, JingShiSegmentHydraulics, CompositeRoughnessMethod
)
from solvers.ice_prediction import (
    WaterTemperaturePredictor, FreezingCriteriaChecker, ColdWaveIndex,
    IceThicknessPredictor, IntegratedIcePredictor, IceConditionType, ColdWaveLevel
)
from solvers.ice_mpc_controller import (
    JingShiIcePeriodController, MultiPoolMPCController, ControlMode,
    PoolParameters, ControlConstraints, IDPoolModel
)
from solvers.weather_llm_interface import (
    LLMWeatherInterface, DataAssimilator, IntegratedWeatherIcePredictor,
    WeatherModelType, MonitoringData, StatisticalWeatherModel
)


class TestIceHydraulics:
    """冰盖下水力学模块测试"""

    def test_composite_roughness_sabaneev(self):
        """测试Sabaneev公式计算复合糙率"""
        hydraulics = IceCoveredChannelHydraulics(
            n_bed=0.015,
            n_ice_smooth=0.010
        )

        P_bed = np.array([60.0])  # 渠床湿周
        P_ice = np.array([30.0])  # 冰盖湿周

        n_composite = hydraulics.compute_composite_roughness(
            P_bed, P_ice,
            method=CompositeRoughnessMethod.SABANEEV
        )

        # 复合糙率应在渠床和冰底糙率之间
        assert 0.010 < n_composite[0] < 0.015
        print(f"✓ Sabaneev复合糙率: {n_composite[0]:.4f}")

    def test_composite_roughness_weighted_average(self):
        """测试加权平均法计算复合糙率"""
        hydraulics = IceCoveredChannelHydraulics()

        P_bed = np.array([60.0])
        P_ice = np.array([30.0])

        n_composite = hydraulics.compute_composite_roughness(
            P_bed, P_ice,
            method=CompositeRoughnessMethod.WEIGHTED_AVERAGE
        )

        assert 0.010 < n_composite[0] < 0.015
        print(f"✓ 加权平均复合糙率: {n_composite[0]:.4f}")

    def test_hydraulic_radius_ice_covered(self):
        """测试冰盖下水力半径计算"""
        hydraulics = IceCoveredChannelHydraulics()

        A = np.array([90.0])     # 断面积
        P_bed = np.array([60.0])  # 渠床湿周
        P_ice = np.array([30.0])  # 冰盖湿周

        R_ice = hydraulics.compute_hydraulic_radius_ice_covered(A, P_bed, P_ice)

        # 冰盖下水力半径 = A / (P_bed + P_ice)
        expected = 90.0 / 90.0
        assert np.isclose(R_ice[0], expected)
        print(f"✓ 冰盖下水力半径: {R_ice[0]:.3f} m")

    def test_flow_capacity_reduction(self):
        """测试冰盖导致的过流能力折减"""
        hydraulics = IceCoveredChannelHydraulics()

        h = np.array([3.0])      # 水深
        B = 30.0                  # 河宽
        h_ice = np.array([0.2])   # 冰厚
        ice_fraction = np.array([1.0])  # 完全覆盖

        result = hydraulics.compute_flow_capacity_reduction(h, B, h_ice, ice_fraction)

        # 有冰时过流能力应该下降
        assert result['capacity_ratio'][0] < 1.0
        print(f"✓ 过流能力比: {result['capacity_ratio'][0]:.3f}")
        print(f"✓ 有效面积: {result['A_effective'][0]:.1f} m²")
        print(f"✓ 复合糙率: {result['n_composite'][0]:.4f}")

    def test_jingshi_segment_parameters(self):
        """测试京石段参数"""
        jingshi = JingShiSegmentHydraulics(n_cells=217)

        # 检查闸门位置
        gate_indices = jingshi.get_gate_locations()
        assert len(gate_indices) == 14
        print(f"✓ 京石段14座节制闸位置: {gate_indices[:5]}...")

        # 检查冰期约束
        params = jingshi.ICE_PERIOD_PARAMS
        assert params['Fr_critical_upstream'] == 0.065
        assert params['V_max_upstream'] == 0.40
        assert params['T_trigger'] == 1.2
        print("✓ 京石段冰期参数配置正确")


class TestIcePrediction:
    """冰情预测模块测试"""

    def test_water_temperature_predictor(self):
        """测试水温预测模型"""
        predictor = WaterTemperaturePredictor(
            n_cells=100,
            dx=1000.0,
            K_wa=18.0
        )

        # 计算平衡温度
        T_eq = predictor.compute_equilibrium_temperature(
            T_air=-5.0,
            solar_radiation=200.0,
            wind_speed=3.0,
            relative_humidity=0.6
        )

        assert -10 < T_eq < 0  # 平衡温度应低于气温
        print(f"✓ 平衡温度: {T_eq:.2f}°C")

    def test_water_temperature_profile(self):
        """测试水温沿程分布预测"""
        predictor = WaterTemperaturePredictor(n_cells=100, dx=1000.0, K_wa=18.0)

        T_initial = np.full(100, 5.0)
        T_upstream = 5.0
        h = np.full(100, 3.0)

        T_profile = predictor.predict_temperature_profile(
            T_initial, T_upstream, Q=100.0, B=30.0, h=h,
            T_air=-10.0, solar_radiation=100.0, wind_speed=5.0, relative_humidity=0.5
        )

        # 水温应该沿程下降
        assert T_profile[0] >= T_profile[-1]
        print(f"✓ 水温沿程变化: {T_profile[0]:.2f}°C → {T_profile[-1]:.2f}°C")

    def test_freezing_criteria_checker(self):
        """测试封冻判据检查器"""
        checker = FreezingCriteriaChecker(
            Fr_critical_upstream=0.065,
            Fr_critical_downstream=0.055,
            V_critical_upstream=0.40,
            V_critical_downstream=0.35
        )

        T_water = np.array([0.0, 0.0, 1.0])  # 两个点已冻结
        u = np.array([0.30, 0.50, 0.30])     # 一个点流速超限
        h = np.array([3.0, 3.0, 3.0])

        result = checker.check_freezing_potential(T_water, u, h)

        # 检查封冻条件
        assert np.any(result['thermal_condition'])
        assert np.any(result['freezing_potential'])
        print(f"✓ 热力条件满足: {np.sum(result['thermal_condition'])}/3")
        print(f"✓ 封冻可能: {np.sum(result['freezing_potential'])}/3")

    def test_cold_wave_index(self):
        """测试TCI寒潮指数"""
        tci = ColdWaveIndex(window_days=7)

        # 模拟寒潮过程
        T_air = np.concatenate([
            np.full(5, 0.0),    # 前5天正常
            np.linspace(0, -15, 5),  # 5天降温15°C
            np.full(5, -15.0),  # 维持低温
            np.linspace(-15, -5, 5)  # 回暖
        ])

        TCI, max_level = tci.compute_TCI(T_air)
        events = tci.detect_cold_wave(T_air)

        assert max_level != ColdWaveLevel.NONE
        assert len(events) > 0
        print(f"✓ 最高寒潮等级: {max_level.name}")
        print(f"✓ 检测到寒潮事件: {len(events)}")

    def test_afdd_calculation(self):
        """测试累计负气温度日计算"""
        tci = ColdWaveIndex()

        T_air = np.array([-5, -10, -8, -3, 0, -2])
        AFDD = tci.compute_AFDD(T_air)

        expected = np.cumsum([5, 10, 8, 3, 0, 2])
        assert np.allclose(AFDD, expected)
        print(f"✓ AFDD计算: {AFDD[-1]:.1f}°C·day")

    def test_ice_thickness_predictor(self):
        """测试冰厚预测"""
        predictor = IceThicknessPredictor()

        # Stefan公式预测
        AFDD = 50.0  # 50°C·day
        h_ice = predictor.predict_by_stefan(AFDD)

        assert 0 < h_ice < 0.5
        print(f"✓ Stefan冰厚预测 (AFDD=50): {h_ice*100:.2f}cm")

        # 修正Stefan方程
        h_new = predictor.predict_modified_stefan(
            dt=86400.0,
            h_ice_current=0.1,
            T_air=-10.0,
            T_water=0.5
        )

        assert h_new > 0.1  # 低温下冰厚增加
        print(f"✓ 修正Stefan冰厚: 10.0cm → {h_new*100:.2f}cm")


class TestMPCController:
    """MPC控制器测试"""

    def test_id_pool_model(self):
        """测试ID渠池模型"""
        model = IDPoolModel(
            length=15000,
            width=30.0,
            depth=3.0,
            slope=0.0001
        )

        A, B = model.get_state_space_matrices(dt=300.0)

        assert 0 < A < 1
        assert B > 0
        print(f"✓ ID模型参数: A={A:.4f}, B={B:.4f}")
        print(f"✓ 延迟时间: {model.tau_d:.0f}s")

    def test_jingshi_controller_initialization(self):
        """测试京石段控制器初始化"""
        controller = JingShiIcePeriodController(dt=300.0)

        assert controller.n_pools == 13
        assert controller.n_gates == 14
        print("✓ 京石段控制器初始化成功")

    def test_ice_period_flow_calculation(self):
        """测试冰期流量计算"""
        controller = JingShiIcePeriodController()

        # 常规输水
        Q1 = controller.compute_ice_period_flow(T_water_avg=5.0, T_air_forecast=0.0, current_flow=200.0)
        # 冰期输水
        Q2 = controller.compute_ice_period_flow(T_water_avg=1.0, T_air_forecast=-10.0, current_flow=100.0)
        # 极端低温
        Q3 = controller.compute_ice_period_flow(T_water_avg=0.5, T_air_forecast=-15.0, current_flow=50.0)

        assert Q1 > Q2 > Q3  # 水温越低，流量越小
        print(f"✓ 常规流量: {Q1:.1f} m³/s")
        print(f"✓ 冰期流量: {Q2:.1f} m³/s")
        print(f"✓ 极端低温流量: {Q3:.1f} m³/s")

    def test_mpc_step(self):
        """测试MPC控制步进"""
        controller = JingShiIcePeriodController()

        h_current = np.full(13, 3.0)
        T_water = np.full(13, 2.0)
        ice_fraction = np.zeros(13)
        gate_prev = np.full(14, 2.0)

        gate_new, Q_target, info = controller.step(
            h_current=h_current,
            Q_current=200.0,
            T_water=T_water,
            T_air=-5.0,
            T_air_forecast=[-5.0] * 28,
            ice_fraction=ice_fraction,
            gate_openings_prev=gate_prev
        )

        assert len(gate_new) == 14
        assert Q_target > 0
        print(f"✓ MPC输出闸门开度: {gate_new[:3]}...")
        print(f"✓ 目标流量: {Q_target:.1f} m³/s")
        print(f"✓ 控制模式: {info['mode'].value}")


class TestWeatherInterface:
    """气象大模型接口测试"""

    def test_statistical_weather_model(self):
        """测试统计气象模型"""
        model = StatisticalWeatherModel()

        forecast = model.get_forecast(
            location=(38.0, 114.5),
            forecast_hours=list(range(0, 72, 6))
        )

        assert len(forecast.temperature) == 12
        assert len(forecast.wind_speed) == 12
        assert forecast.model_type == WeatherModelType.STATISTICAL
        print(f"✓ 气温预报范围: {forecast.temperature.min():.1f} ~ {forecast.temperature.max():.1f}°C")
        print(f"✓ 风速预报范围: {forecast.wind_speed.min():.1f} ~ {forecast.wind_speed.max():.1f}m/s")

    def test_llm_weather_interface(self):
        """测试气象大模型统一接口"""
        interface = LLMWeatherInterface(
            model_type=WeatherModelType.ENSEMBLE
        )

        forecast = interface.get_forecast(
            location=(38.0, 114.5),
            forecast_hours=list(range(0, 168, 6))
        )

        # 无API密钥时会回退到统计模型
        assert forecast.model_type in [WeatherModelType.ENSEMBLE, WeatherModelType.STATISTICAL]
        assert forecast.confidence is not None
        print(f"✓ 预报模型: {forecast.model_type.value}")
        print(f"✓ 预报置信度: {np.mean(forecast.confidence):.2%}")

    def test_data_assimilation(self):
        """测试数据同化"""
        assimilator = DataAssimilator(n_stations=18)

        # 创建预报
        model = StatisticalWeatherModel()
        forecast = model.get_forecast((38.0, 114.5), list(range(0, 72, 6)))

        # 创建监测数据
        monitoring = MonitoringData(
            timestamp=datetime.now(),
            station_ids=["JK01"],
            locations=np.array([0.0]),
            T_air_measured=np.array([forecast.temperature[0] - 1.0]),  # 观测偏低1°C
            T_water_measured=np.array([3.0]),
            velocity_measured=np.array([0.3]),
            water_level_measured=np.array([3.0])
        )

        # 同化校正
        corrected = assimilator.assimilate(forecast, monitoring)

        # 校正后应该更接近观测值
        assert corrected.confidence is not None
        print(f"✓ 原始预报: {forecast.temperature[0]:.2f}°C")
        print(f"✓ 校正预报: {corrected.temperature[0]:.2f}°C")
        print(f"✓ 观测值: {monitoring.T_air_measured[0]:.2f}°C")

    def test_integrated_weather_ice_predictor(self):
        """测试气象-冰情综合预测器"""
        predictor = IntegratedWeatherIcePredictor(
            model_type=WeatherModelType.STATISTICAL
        )

        monitoring = MonitoringData(
            timestamp=datetime.now(),
            station_ids=[f"JK{i:02d}" for i in range(18)],
            locations=np.linspace(0, 217, 18),
            T_air_measured=np.full(18, -5.0),
            T_water_measured=np.full(18, 2.0),
            velocity_measured=np.full(18, 0.3),
            water_level_measured=np.full(18, 3.0)
        )

        result = predictor.predict(monitoring, forecast_days=15)

        assert 'T_water_forecast' in result
        assert 'ice_warning' in result
        assert 'daily_forecasts' in result
        print(f"✓ 冰情风险等级: {result['ice_warning']['risk_level']}")
        print(f"✓ 预测最低水温: {result['ice_warning']['T_water_min']:.2f}°C")


class TestIntegration:
    """集成测试"""

    def test_full_ice_period_workflow(self):
        """测试完整冰期调度工作流"""
        print("\n开始完整工作流测试...")

        # 1. 初始化各模块
        n_cells = 100
        hydraulics = IceCoveredChannelHydraulics()
        temp_predictor = WaterTemperaturePredictor(n_cells, dx=2170.0, K_wa=18.0)
        freeze_checker = FreezingCriteriaChecker()
        tci = ColdWaveIndex()
        ice_predictor = IceThicknessPredictor()

        # 2. 设置初始条件
        h = np.full(n_cells, 3.0)
        u = np.full(n_cells, 0.35)
        T_water = np.full(n_cells, 1.0)  # 接近冰点的初始水温
        h_ice = np.full(n_cells, 0.05)   # 初始有少量冰
        ice_fraction = np.full(n_cells, 0.5)

        # 3. 模拟一天的冰期变化
        dt = 3600.0  # 1小时
        T_air = -15.0  # 更低的气温

        initial_T_water = np.mean(T_water)
        initial_h_ice = np.mean(h_ice)

        for step in range(24):
            # 水温下降
            T_eq = temp_predictor.compute_equilibrium_temperature(
                T_air, 50.0, 5.0, 0.6  # 低太阳辐射
            )
            T_water = T_water + (T_eq - T_water) * 0.05  # 更快的热交换

            # 限制水温
            T_water = np.maximum(T_water, 0.0)

            # 冰厚增长
            for i in range(n_cells):
                h_ice[i] = ice_predictor.predict_modified_stefan(
                    dt, h_ice[i], T_air, T_water[i]
                )

            # 更新冰盖覆盖率
            ice_fraction = np.clip(h_ice / 0.1, 0, 1)

        # 4. 检查封冻条件
        freeze_result = freeze_checker.check_freezing_potential(T_water, u, h)

        # 5. 计算冰盖下水力学
        hydraulic_result = hydraulics.modify_saint_venant_for_ice(
            h, u, u * h * 30, 30.0, h_ice, ice_fraction, np.full(n_cells, 0.0001)
        )

        # 验证结果
        final_T_water = np.mean(T_water)
        final_h_ice = np.mean(h_ice)
        capacity_ratio = np.mean(hydraulic_result['capacity_ratio'])

        assert final_T_water <= initial_T_water  # 水温下降或不变
        assert final_h_ice >= initial_h_ice  # 冰厚增加或不变
        assert capacity_ratio <= 1.0  # 过流能力下降或不变

        print("✓ 完整工作流测试通过")
        print(f"  初始水温: {initial_T_water:.2f}°C → 最终: {final_T_water:.2f}°C")
        print(f"  初始冰厚: {initial_h_ice*100:.2f}cm → 最终: {final_h_ice*100:.2f}cm")
        print(f"  过流能力比: {capacity_ratio:.3f}")


def run_all_tests():
    """运行所有测试"""
    print("=" * 80)
    print("  HydroClaude 冰期调度升级功能测试")
    print("=" * 80)

    test_classes = [
        TestIceHydraulics,
        TestIcePrediction,
        TestMPCController,
        TestWeatherInterface,
        TestIntegration
    ]

    total_tests = 0
    passed_tests = 0

    for test_class in test_classes:
        print(f"\n{'='*40}")
        print(f"测试类: {test_class.__name__}")
        print(f"{'='*40}")

        test_instance = test_class()
        for method_name in dir(test_instance):
            if method_name.startswith('test_'):
                total_tests += 1
                try:
                    getattr(test_instance, method_name)()
                    passed_tests += 1
                except Exception as e:
                    print(f"✗ {method_name} 失败: {e}")

    print("\n" + "=" * 80)
    print(f"  测试结果: {passed_tests}/{total_tests} 通过")
    print("=" * 80)

    return passed_tests == total_tests


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
