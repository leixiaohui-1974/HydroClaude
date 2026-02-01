#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地化气象订正和多要素冰情预测测试

测试内容：
1. 卡尔曼滤波偏差校正
2. MOS统计回归校正
3. 空间插值
4. 多要素水温预测
5. 封冻概率计算
6. 冰厚预测
7. 综合冰情预测

作者: HydroClaude Team
日期: 2025-11-02
"""

import numpy as np
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from solvers.local_weather_correction import (
    KalmanBiasCorrector, MOSCorrector, SpatialInterpolator,
    LightweightWeatherCorrector, IcePeriodWeatherService,
    JINGSHI_MONITORING_STATIONS, MonitoringStation, RealtimeObservation
)
from solvers.multi_factor_ice_predictor import (
    WaterTemperatureModel, FreezingCriteriaModel, IceThicknessModel,
    MultiFactorIcePredictor, MultiFactorObservation,
    IceEventType, FreezingMode
)


class TestKalmanBiasCorrector:
    """卡尔曼滤波偏差校正测试"""

    def test_initialization(self):
        """测试初始化"""
        kalman = KalmanBiasCorrector(n_stations=14)
        assert kalman.n_stations == 14
        assert len(kalman.x) == 14
        assert len(kalman.P) == 14
        print("✓ 卡尔曼滤波初始化正确")

    def test_single_update(self):
        """测试单次更新"""
        kalman = KalmanBiasCorrector(n_stations=14)

        # 预报值比观测值高2度
        forecast = 5.0
        observed = 3.0

        corrected = kalman.update(0, forecast, observed)

        # 校正后应该更接近观测值
        assert abs(corrected - observed) < abs(forecast - observed)
        print(f"✓ 单次更新: 预报{forecast}°C, 观测{observed}°C, 校正后{corrected:.2f}°C")

    def test_convergence(self):
        """测试偏差估计收敛"""
        kalman = KalmanBiasCorrector(n_stations=1)

        # 持续偏高2度的预报
        true_bias = 2.0
        for _ in range(50):
            forecast = 5.0 + true_bias
            observed = 5.0
            kalman.update(0, forecast, observed)

        # 偏差估计应该接近真实偏差
        estimated_bias, _ = kalman.get_bias_estimate(0)
        assert abs(estimated_bias - true_bias) < 0.3
        print(f"✓ 偏差收敛: 真实偏差{true_bias}°C, 估计偏差{estimated_bias:.2f}°C")

    def test_batch_update(self):
        """测试批量更新"""
        kalman = KalmanBiasCorrector(n_stations=14)

        forecast = np.random.normal(-5, 3, 14)
        observed = forecast - 1.5  # 预报偏高1.5度

        corrected = kalman.batch_update(forecast, observed)

        # 校正后的均方误差应该减小
        mse_before = np.mean((forecast - observed)**2)
        mse_after = np.mean((corrected - observed)**2)
        assert mse_after < mse_before
        print(f"✓ 批量更新: MSE从{mse_before:.2f}降至{mse_after:.2f}")


class TestMOSCorrector:
    """MOS统计回归校正测试"""

    def test_sample_collection(self):
        """测试样本收集"""
        mos = MOSCorrector(n_stations=14, min_samples=10)

        # 添加样本
        for i in range(20):
            mos.add_sample(0, float(i), float(i) * 0.9 + 1)

        assert len(mos.history[0]['forecast']) == 20
        print("✓ 样本收集正确")

    def test_linear_regression(self):
        """测试线性回归拟合"""
        mos = MOSCorrector(n_stations=1, min_samples=10)

        # 添加线性关系的样本: y = 0.8x + 2
        for x in np.linspace(-10, 10, 30):
            y = 0.8 * x + 2 + np.random.normal(0, 0.5)
            mos.add_sample(0, x, y)

        # 拟合
        success = mos.fit(0)
        assert success

        # 检查系数
        stats = mos.get_correction_stats(0)
        assert abs(stats['a'] - 0.8) < 0.2
        assert abs(stats['b'] - 2.0) < 1.0
        print(f"✓ 线性回归: a={stats['a']:.3f} (期望0.8), b={stats['b']:.3f} (期望2.0)")

    def test_correction(self):
        """测试校正效果"""
        mos = MOSCorrector(n_stations=1, min_samples=10)

        # 训练数据
        for x in np.linspace(-10, 10, 50):
            y = 0.9 * x + 1
            mos.add_sample(0, x, y)

        mos.fit(0)

        # 测试校正
        test_x = 5.0
        expected_y = 0.9 * 5.0 + 1
        corrected = mos.correct(0, test_x)

        assert abs(corrected - expected_y) < 0.5
        print(f"✓ MOS校正: 输入{test_x}, 校正后{corrected:.2f}, 期望{expected_y:.2f}")


class TestSpatialInterpolator:
    """空间插值测试"""

    def test_idw_interpolation(self):
        """测试反距离加权插值"""
        interpolator = SpatialInterpolator(JINGSHI_MONITORING_STATIONS)

        # 各站点值
        values = np.linspace(-10, -5, 14)

        # 插值到中间位置
        target = np.array([100.0])  # 100km处
        result = interpolator.idw_interpolate(values, target)

        # 结果应该在范围内
        assert values.min() <= result[0] <= values.max()
        print(f"✓ IDW插值: 100km处温度估计{result[0]:.2f}°C")

    def test_grid_interpolation(self):
        """测试网格插值"""
        interpolator = SpatialInterpolator(JINGSHI_MONITORING_STATIONS)

        values = np.linspace(-10, -5, 14)
        grid = interpolator.interpolate_to_grid(values, n_cells=217)

        assert len(grid) == 217
        assert not np.any(np.isnan(grid))
        print(f"✓ 网格插值: 217个网格点, 范围{grid.min():.2f}~{grid.max():.2f}°C")


class TestLightweightWeatherCorrector:
    """轻量级气象校正系统测试"""

    def test_full_correction(self):
        """测试完整校正流程"""
        corrector = LightweightWeatherCorrector()

        forecast = {
            'T_air': np.random.normal(-5, 2, 14),
            'T_water': np.random.normal(2, 0.5, 14)
        }
        observed = {
            'T_air': forecast['T_air'] - 1.5,
            'T_water': forecast['T_water'] - 0.3
        }

        # 校正
        corrected = corrector.correct_forecast(forecast, observed, 'T_air')

        # 校正后误差应减小
        error_before = np.mean(np.abs(forecast['T_air'] - observed['T_air']))
        error_after = np.mean(np.abs(corrected - observed['T_air']))

        assert error_after < error_before
        print(f"✓ 完整校正: 误差从{error_before:.2f}°C降至{error_after:.2f}°C")

    def test_interpolation_pipeline(self):
        """测试校正+插值流程"""
        corrector = LightweightWeatherCorrector()

        forecast = {'T_air': np.full(14, -5.0)}
        observed = {'T_air': np.full(14, -6.0)}

        grid = corrector.correct_and_interpolate(
            forecast, observed, 'T_air', n_cells=217
        )

        assert len(grid) == 217
        print(f"✓ 校正+插值: 网格平均温度{np.mean(grid):.2f}°C")


class TestWaterTemperatureModel:
    """水温预测模型测试"""

    def test_heat_flux_calculation(self):
        """测试热通量计算"""
        model = WaterTemperatureModel(K_wa=18.0)

        Q_net, components = model.compute_heat_flux(
            T_water=2.0,
            T_air=-10.0,
            wind_speed=5.0,
            humidity=0.6,
            solar_radiation=100.0,
            cloud_cover=0.3
        )

        # 冬季应该是净散热（负值）
        assert Q_net < 0
        print(f"✓ 热通量计算: 净热通量{Q_net:.1f} W/m²")
        print(f"  太阳辐射: {components['Q_solar']:.1f} W/m²")
        print(f"  蒸发散热: {components['Q_evap']:.1f} W/m²")

    def test_temperature_prediction(self):
        """测试水温预测"""
        model = WaterTemperatureModel()

        # 创建72小时预报
        observations = []
        for h in range(72):
            obs = MultiFactorObservation(
                timestamp=datetime.now() + timedelta(hours=h),
                station_id="test",
                chainage=0,
                T_air=-10.0,
                wind_speed=5.0,
                wind_direction=270,
                humidity=0.6,
                solar_radiation=100 if 8 <= h % 24 <= 16 else 0,
                rainfall=0,
                cloud_cover=0.3,
                T_water=0,
                water_level=3.0,
                velocity=0.3,
                discharge=100,
                depth=3.0
            )
            observations.append(obs)

        T_pred, uncertainty = model.predict(
            T_water_init=3.0,
            observations=observations,
            forecast_hours=72
        )

        # 水温应该下降
        assert T_pred[-1] < T_pred[0]
        print(f"✓ 水温预测: {T_pred[0]:.2f}°C → {T_pred[-1]:.2f}°C (72小时)")


class TestFreezingCriteriaModel:
    """封冻判据模型测试"""

    def test_froude_calculation(self):
        """测试Froude数计算"""
        model = FreezingCriteriaModel()

        Fr = model.compute_froude(velocity=0.35, depth=3.0)
        assert 0 < Fr < 0.1
        print(f"✓ Froude数: V=0.35m/s, h=3.0m, Fr={Fr:.4f}")

    def test_freezing_mode(self):
        """测试封冻方式判断"""
        model = FreezingCriteriaModel()

        # 低流速 - 立封
        mode1 = model.determine_freezing_mode(velocity=0.25, depth=3.0)
        assert mode1 == FreezingMode.STANDING

        # 中等流速 - 挤封
        mode2 = model.determine_freezing_mode(velocity=0.40, depth=3.0)
        assert mode2 == FreezingMode.JUXTAPOSITION

        print(f"✓ 封冻方式: V=0.25→{mode1.value}, V=0.40→{mode2.value}")

    def test_freezing_probability(self):
        """测试封冻概率计算"""
        model = FreezingCriteriaModel()

        # 高风险条件
        prob_high = model.compute_freezing_probability(
            T_water=0.5, T_air=-15, velocity=0.3, depth=3.0,
            wind_speed=3.0, consecutive_cold_days=5, month=1
        )

        # 低风险条件
        prob_low = model.compute_freezing_probability(
            T_water=5.0, T_air=0, velocity=0.5, depth=3.0,
            wind_speed=8.0, consecutive_cold_days=0, month=11
        )

        assert prob_high > prob_low
        print(f"✓ 封冻概率: 高风险{prob_high:.1%}, 低风险{prob_low:.1%}")


class TestIceThicknessModel:
    """冰厚预测模型测试"""

    def test_ice_growth(self):
        """测试冰厚增长"""
        model = IceThicknessModel()

        h_ice = 0.05  # 初始5cm
        for _ in range(24):  # 24小时
            h_ice = model.predict(
                dt=3600,
                h_ice_current=h_ice,
                T_air=-15.0,
                T_water=0.0,
                velocity=0.3,
                wind_speed=3.0
            )

        assert h_ice > 0.05
        print(f"✓ 冰厚增长: 5cm → {h_ice*100:.2f}cm (24小时, -15°C)")

    def test_velocity_effect(self):
        """测试流速对冰厚的影响"""
        model = IceThicknessModel()

        # 低流速
        h_low_v = 0.05
        for _ in range(24):
            h_low_v = model.predict(3600, h_low_v, -15, 0.0, 0.2, 3.0)

        # 高流速
        h_high_v = 0.05
        for _ in range(24):
            h_high_v = model.predict(3600, h_high_v, -15, 0.0, 0.5, 3.0)

        # 高流速应该抑制冰厚增长
        assert h_low_v > h_high_v
        print(f"✓ 流速影响: 低流速{h_low_v*100:.2f}cm > 高流速{h_high_v*100:.2f}cm")


class TestMultiFactorIcePredictor:
    """多要素冰情预测测试"""

    def test_full_prediction(self):
        """测试完整预测流程"""
        predictor = MultiFactorIcePredictor()

        # 当前观测
        current = [
            MultiFactorObservation(
                timestamp=datetime.now(),
                station_id=f"JK{i:02d}",
                chainage=i * 15.5,
                T_air=-5.0,
                wind_speed=3.0,
                wind_direction=270,
                humidity=0.6,
                solar_radiation=100,
                rainfall=0,
                cloud_cover=0.3,
                T_water=2.0,
                water_level=3.0,
                velocity=0.35,
                discharge=200,
                depth=3.0
            )
            for i in range(14)
        ]

        # 未来预报
        forecast = [
            MultiFactorObservation(
                timestamp=datetime.now() + timedelta(hours=h),
                station_id="forecast",
                chainage=100,
                T_air=-10.0 - h * 0.1,
                wind_speed=4.0,
                wind_direction=270,
                humidity=0.55,
                solar_radiation=100 if 8 <= h % 24 <= 16 else 0,
                rainfall=0,
                cloud_cover=0.4,
                T_water=1.5,
                water_level=3.0,
                velocity=0.35,
                discharge=200,
                depth=3.0
            )
            for h in range(72)
        ]

        result = predictor.predict(current, forecast)

        assert len(result.T_water_forecast) == 72
        assert len(result.ice_probability) == 72
        assert result.risk_level >= 0
        assert result.Q_recommended is not None

        print("✓ 完整预测:")
        print(f"  风险等级: {result.risk_level}")
        print(f"  建议流量: {result.Q_recommended:.1f} m³/s")
        print(f"  水温预测: {result.T_water_forecast[0]:.2f}°C → {result.T_water_forecast[-1]:.2f}°C")


class TestIcePeriodWeatherService:
    """冰期气象服务测试"""

    def test_water_temperature_estimation(self):
        """测试水温估计"""
        service = IcePeriodWeatherService()

        T_air_forecast = np.linspace(-5, -15, 72)
        T_water_current = np.full(14, 3.0)

        T_water_forecast = service.estimate_water_temperature(
            T_air_forecast, T_water_current, hours_ahead=72
        )

        assert T_water_forecast.shape == (72, 14)
        assert np.mean(T_water_forecast[-1]) < np.mean(T_water_forecast[0])
        print(f"✓ 水温估计: {np.mean(T_water_forecast[0]):.2f}°C → {np.mean(T_water_forecast[-1]):.2f}°C")

    def test_ice_risk_assessment(self):
        """测试冰情风险评估"""
        service = IcePeriodWeatherService()

        T_water_forecast = np.zeros((72, 14))
        T_water_forecast[:24] = 2.0
        T_water_forecast[24:48] = 1.0
        T_water_forecast[48:] = 0.5

        T_air_forecast = np.linspace(-5, -20, 72)

        risk = service.assess_ice_risk(T_water_forecast, T_air_forecast)

        assert 'risk_level' in risk
        assert 'risk_message' in risk
        print(f"✓ 风险评估: 等级{risk['risk_level']}, {risk['risk_message']}")


def run_all_tests():
    """运行所有测试"""
    print("=" * 80)
    print("  本地化气象订正和多要素冰情预测测试")
    print("=" * 80)

    test_classes = [
        TestKalmanBiasCorrector,
        TestMOSCorrector,
        TestSpatialInterpolator,
        TestLightweightWeatherCorrector,
        TestWaterTemperatureModel,
        TestFreezingCriteriaModel,
        TestIceThicknessModel,
        TestMultiFactorIcePredictor,
        TestIcePeriodWeatherService,
    ]

    total = 0
    passed = 0

    for test_class in test_classes:
        print(f"\n{'='*40}")
        print(f"测试类: {test_class.__name__}")
        print(f"{'='*40}")

        instance = test_class()
        for method in dir(instance):
            if method.startswith('test_'):
                total += 1
                try:
                    getattr(instance, method)()
                    passed += 1
                except Exception as e:
                    print(f"✗ {method} 失败: {e}")

    print("\n" + "=" * 80)
    print(f"  测试结果: {passed}/{total} 通过")
    print("=" * 80)

    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
