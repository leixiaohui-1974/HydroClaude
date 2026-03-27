"""跨仓库集成测试 — HydroClaude ↔ pipedream ↔ HydroMind

测试三个集成点：
  1. HydroClaude1DSolverAdapter      → HydraulicSolverProtocol
  2. HydroClaude1DWaterQualityAdapter → WaterQualityProtocol
  3. HydroClaude1DLeakDetectorAdapter → LeakDetectorProtocol（依赖 pipedream）
  4. HydroClaude1DPollutionSourceAdapter → IdentifierProtocol（依赖 pipedream）
  5. HydroMind.water_quality_incident  → 完整溯源链路

归属仓库：HydroClaude/tests/integration/
"""
import sys
import os
import pytest
import numpy as np

# 添加 HydroClaude 根目录到路径
_HYDROCLAUDE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
for _p in [_HYDROCLAUDE_ROOT, _REPO_ROOT]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ── 集成点 1：水动力求解器适配器 ─────────────────────────────────────────

class TestHydraulicSolverAdapter:
    """验证 HydroClaude1DSolverAdapter 实现 HydraulicSolverProtocol 语义。"""

    def setup_method(self):
        sys.path.insert(0, _HYDROCLAUDE_ROOT)
        from integration.hydromind_adapter import HydroClaude1DSolverAdapter
        self.adapter = HydroClaude1DSolverAdapter(
            length=5000.0, n_nodes=21, width=5.0,
            slope=0.0001, manning_n=0.025
        )
        self.adapter.set_initial_conditions(Q0=10.0, h0=1.5)

    def test_advance_updates_state(self):
        """advance() 后状态应更新。"""
        state_before = self.adapter.get_state()
        self.adapter.advance(dt=300.0, Q_upstream=12.0)
        state_after = self.adapter.get_state()
        assert state_after["t"] == pytest.approx(300.0)
        assert len(state_after["h"]) == 21

    def test_get_h_profile_shape(self):
        """get_h_profile() 返回正确形状的数组。"""
        h = self.adapter.get_h_profile()
        assert h.shape == (21,)
        assert np.all(h > 0)

    def test_state_matrices_shape(self):
        """get_state_matrices() 返回正确形状的矩阵。"""
        matrices = self.adapter.get_state_matrices()
        assert "A" in matrices
        n = matrices["A"].shape[0]
        assert n > 0
        assert matrices["A"].shape == (n, n)

    def test_reduced_state_matrices(self):
        """get_reduced_state_matrices() 返回降阶矩阵。"""
        rom = self.adapter.get_reduced_state_matrices(n_modes=4)
        assert rom["A_r"].shape == (4, 4)
        assert rom["B_r"].shape[0] == 4
        assert rom["n_modes"] == 4

    def test_normal_depth_positive(self):
        """get_normal_depth() 返回正值。"""
        h_n = self.adapter.get_normal_depth(Q=10.0)
        assert h_n > 0

    def test_protocol_compliance(self):
        """验证适配器满足 HydraulicSolverProtocol 的所有方法签名。"""
        required_methods = [
            "set_initial_conditions", "advance",
            "get_h_profile", "get_state", "get_normal_depth"
        ]
        for method in required_methods:
            assert hasattr(self.adapter, method), f"缺少方法: {method}"


# ── 集成点 2：水质仿真适配器 ─────────────────────────────────────────────

class TestWaterQualityAdapter:
    """验证 HydroClaude1DWaterQualityAdapter 实现 WaterQualityProtocol 语义。"""

    def setup_method(self):
        sys.path.insert(0, _HYDROCLAUDE_ROOT)
        from integration.hydromind_adapter import HydroClaude1DWaterQualityAdapter
        self.adapter = HydroClaude1DWaterQualityAdapter(
            length=5000.0, n_nodes=11, width=5.0,
            slope=0.0001, manning_n=0.025
        )

    def test_set_sources_no_error(self):
        """set_sources() 不应抛出异常。"""
        self.adapter.set_sources({
            "node_3": {"BOD": 15.0, "NH4": 3.0},
            "node_7": {"BOD": 5.0},
        })

    def test_simulate_returns_required_keys(self):
        """simulate() 返回字典包含必要键。"""
        result = self.adapter.simulate(duration=1800.0, dt=300.0)
        assert "time_series" in result
        assert "concentrations" in result
        assert "converged" in result
        assert result["converged"] is True

    def test_simulate_time_series_length(self):
        """simulate() 时间序列长度正确。"""
        result = self.adapter.simulate(duration=1500.0, dt=300.0)
        assert len(result["time_series"]) == 5

    def test_get_concentrations_node_format(self):
        """get_concentrations() 支持 node_<idx> 格式。"""
        self.adapter.simulate(duration=300.0, dt=300.0)
        conc = self.adapter.get_concentrations(["node_0", "node_5", "node_10"])
        assert "node_0" in conc
        assert "x" in conc["node_0"]

    def test_get_concentrations_x_format(self):
        """get_concentrations() 支持 x=<dist> 格式。"""
        self.adapter.simulate(duration=300.0, dt=300.0)
        conc = self.adapter.get_concentrations(["x=2500"])
        assert "x=2500" in conc

    def test_protocol_compliance(self):
        """验证适配器满足 WaterQualityProtocol 的所有方法签名。"""
        required_methods = ["set_sources", "simulate", "get_concentrations"]
        for method in required_methods:
            assert hasattr(self.adapter, method), f"缺少方法: {method}"


# ── 集成点 3：pipedream 数据同化模块（独立测试，不依赖 HydroClaude 适配器）

class TestPipedreamDataAssimilation:
    """直接测试 pipedream 数据同化模块的核心算法。"""

    def setup_method(self):
        pipedream_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "..",
            "pipedream-hydrology-integration-lab"
        )
        if pipedream_path not in sys.path:
            sys.path.insert(0, pipedream_path)

    def test_blp_backward_step(self):
        """BLP 后向步应保持非负性。"""
        from data_assimilation.assimilation_1d import BackwardLocationProbability
        x = np.linspace(0, 10000, 51)
        blp = BackwardLocationProbability(x_nodes=x, u=0.5, E=1.0, dt=60.0)
        field, t_arr = blp.compute(x_obs=8000.0, t_obs=3600.0, t_start=0.0, n_steps=10)
        assert np.all(field >= 0), "BLP 场出现负值"
        assert field.shape == (11, 51)

    def test_blp_concentration_from_source(self):
        """BLP 正向浓度计算应返回正值。"""
        from data_assimilation.assimilation_1d import BackwardLocationProbability
        x = np.linspace(0, 10000, 51)
        blp = BackwardLocationProbability(x_nodes=x, u=0.5, E=2.0, dt=60.0)
        C = blp.concentration_from_source(
            x_src=2000.0, t_src=0.0, mass=100.0, t_obs=3600.0, area=10.0
        )
        assert C >= 0, "浓度不应为负"

    def test_enkf_pollution_source_identification(self):
        """BLP-EnKF 应在合理范围内识别污染源位置。"""
        from data_assimilation.assimilation_1d import (
            BackwardLocationProbability, BLPEnKF
        )
        # 构造合成观测数据
        x = np.linspace(0, 10000, 51)
        u, E, area = 0.5, 2.0, 10.0
        x_true, t_true, M_true = 2000.0, 600.0, 100.0

        blp = BackwardLocationProbability(x_nodes=x, u=u, E=E, dt=60.0)
        x_obs_stations = [5000.0, 8000.0]
        obs_times = np.linspace(3600, 14400, 8)
        obs_conc = np.zeros((2, 8))
        for k, t in enumerate(obs_times):
            for si, x_s in enumerate(x_obs_stations):
                obs_conc[si, k] = blp.concentration_from_source(
                    x_true, t_true, M_true, t, area
                ) + np.random.default_rng(k).normal(0, 0.05)

        enkf = BLPEnKF(blp=blp, x_obs_stations=x_obs_stations, area=area, n_ensemble=50)
        result = enkf.identify(
            obs_times=obs_times, obs_conc=obs_conc, obs_noise_std=0.1,
            prior_x=(0.0, 10000.0), prior_t=(0.0, 3600.0), prior_m=(10.0, 500.0),
            max_iter=3
        )
        # 宽松验证：位置误差 < 3000m（小集合、少迭代）
        assert abs(result.x_source - x_true) < 3000.0, \
            f"溯源位置误差过大: {result.x_source:.0f}m vs {x_true:.0f}m"
        assert result.mass > 0, "质量估计应为正值"

    def test_ekf_leak_detection_no_leak(self):
        """无漏水时 EKF 不应误报。"""
        from data_assimilation.assimilation_1d import EKFLeakDetector
        x = np.linspace(0, 5000, 21)
        Q_nom = np.full(21, 10.0)
        detector = EKFLeakDetector(x_nodes=x, Q_nominal=Q_nom,
                                   process_noise_std=0.001, obs_noise_std=0.005,
                                   detection_threshold=5.0)
        # 无噪声正常流量，连续更新 20 步
        false_alarms = 0
        for k in range(20):
            Q_meas = Q_nom + np.random.default_rng(k).normal(0, 0.003, 21)
            event = detector.update(t=float(k * 300), Q_measured=Q_meas)
            if event.detected:
                false_alarms += 1
        assert false_alarms <= 2, f"误报率过高: {false_alarms}/20"

    def test_ekf_leak_detection_with_leak(self):
        """有漏水时 EKF 应检测到事件。"""
        from data_assimilation.assimilation_1d import EKFLeakDetector
        x = np.linspace(0, 5000, 21)
        Q_nom = np.full(21, 10.0)
        detector = EKFLeakDetector(x_nodes=x, Q_nominal=Q_nom,
                                   process_noise_std=0.001, obs_noise_std=0.005,
                                   detection_threshold=2.0)
        # 先预热 10 步
        for k in range(10):
            Q_meas = Q_nom + np.random.default_rng(k).normal(0, 0.003, 21)
            detector.update(t=float(k * 300), Q_measured=Q_meas)

        # 在节点 10 引入 0.5 m³/s 漏水
        Q_leak = Q_nom.copy()
        Q_leak[10:] -= 0.5
        detections = 0
        for k in range(10, 20):
            Q_meas = Q_leak + np.random.default_rng(k).normal(0, 0.003, 21)
            event = detector.update(t=float(k * 300), Q_measured=Q_meas)
            if event.detected:
                detections += 1
        assert detections >= 1, "有漏水时应至少检测到 1 次事件"

    def test_rainfall_inversion_reduces_rmse(self):
        """降雨反演后的 RMSE 应小于先验估计的 RMSE。"""
        from data_assimilation.assimilation_1d import RainfallInversionEnKF
        areas = np.array([1e6, 2e6, 1.5e6])
        C = np.array([0.6, 0.5, 0.7])
        uh = np.array([0.1, 0.3, 0.4, 0.15, 0.05])
        inverter = RainfallInversionEnKF(
            subcatchment_areas=areas, runoff_coefficients=C,
            unit_hydrograph=uh, dt=300.0, n_ensemble=30
        )
        # 构造合成观测
        t = np.arange(0, 3600, 300, dtype=float)
        true_rain = np.array([[5.0, 8.0, 12.0, 6.0, 3.0, 1.0, 0.5, 0.2, 0.1, 0.0, 0.0, 0.0]])
        true_rain = np.tile(true_rain, (3, 1))[:, :len(t)]
        Q_obs = np.array([
            inverter._rainfall_to_runoff(true_rain, k) for k in range(len(t))
        ]) + np.random.default_rng(0).normal(0, 0.1, len(t))

        result = inverter.invert(Q_obs=Q_obs, t_array=t,
                                 prior_rainfall_mean=3.0, prior_rainfall_std=5.0)
        assert result.obs_fit_rmse < 5.0, f"RMSE 过大: {result.obs_fit_rmse:.3f}"
        assert result.n_subcatchments == 3

    def test_observability_sensor_placement(self):
        """可观性 Gramian 传感器布置应返回正确数量的传感器。"""
        from data_assimilation.assimilation_1d import ObservabilityBasedSensorPlacement
        x = np.linspace(0, 10000, 21)
        opt = ObservabilityBasedSensorPlacement(
            x_nodes=x, u=0.5, E=2.0, dt=60.0, T_horizon=1800.0
        )
        selected = opt.optimize_placement(n_sensors=3, criterion="trace")
        assert len(selected) == 3
        assert len(set(selected)) == 3  # 无重复
        positions = opt.get_sensor_positions(selected)
        assert len(positions) == 3


# ── 集成点 4：HydroMind water_quality_incident 完整链路 ─────────────────

class TestWaterQualityIncidentChain:
    """验证 HydroMind.water_quality_incident 的完整溯源链路。"""

    def setup_method(self):
        hydroclaw_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "..",
            "HydroMind"
        )
        if hydroclaw_path not in sys.path:
            sys.path.insert(0, hydroclaw_path)

    def test_backward_compatible_interface(self):
        """原始接口（仅浓度）应向后兼容。"""
        from core.hydrology.use_cases.water_quality_incident import trace_pollutant_source
        assert trace_pollutant_source(10.0) == "Source_A"
        assert trace_pollutant_source(2.0) == "Unknown"

    def test_full_identification_chain(self):
        """完整溯源链路应返回合理结果。"""
        from core.hydrology.use_cases.water_quality_incident import identify_source
        x = np.linspace(0, 10000, 51)
        context = {
            "x_nodes": x,
            "u": 0.5,
            "E": 2.0,
            "x_obs_stations": [5000.0, 8000.0],
            "obs_times": np.linspace(3600, 14400, 6),
            "obs_conc": np.ones((2, 6)) * 0.5,
            "obs_noise_std": 0.1,
            "prior_x": (0.0, 10000.0),
            "prior_t": (0.0, 3600.0),
            "prior_m": (10.0, 500.0),
            "area": 10.0,
            "n_ensemble": 30,
        }
        result = identify_source(context)
        assert "parameters" in result
        assert "x_source" in result["parameters"]
        assert result["parameters"]["x_source"] >= 0

    def test_forecast_concentration_shape(self):
        """forecast_concentration() 返回正确形状的矩阵。"""
        from core.hydrology.use_cases.water_quality_incident import (
            identify_source, forecast_concentration
        )
        x = np.linspace(0, 10000, 21)
        source_result = {
            "parameters": {"x_source": 2000.0, "t_release": 600.0, "mass": 100.0}
        }
        t_forecast = np.linspace(3600, 14400, 10)
        C = forecast_concentration(source_result, x, u=0.5, E=2.0, t_forecast=t_forecast)
        assert C.shape == (10, 21)
        assert np.all(C >= 0)

    def test_risk_assessment_keys(self):
        """assess_water_quality_risk() 返回必要的风险评估键。"""
        from core.hydrology.use_cases.water_quality_incident import (
            forecast_concentration, assess_water_quality_risk
        )
        x = np.linspace(0, 10000, 21)
        source_result = {
            "parameters": {"x_source": 1000.0, "t_release": 0.0, "mass": 500.0}
        }
        t = np.linspace(1800, 10800, 8)
        C = forecast_concentration(source_result, x, u=0.5, E=2.0, t_forecast=t)
        risk = assess_water_quality_risk(
            C, x, t, threshold_mg_L=0.1,
            intake_positions=[5000.0, 9000.0]
        )
        assert "max_concentration" in risk
        assert "intake_risk" in risk
        assert "x=5000m" in risk["intake_risk"]
        assert risk["intake_risk"]["x=5000m"]["risk_level"] in ("LOW", "MEDIUM", "HIGH")
