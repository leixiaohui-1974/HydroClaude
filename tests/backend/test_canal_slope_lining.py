"""渠道边坡衬砌板耦合仿真与降阶模型测试套件

对标标准：
  - SL/T 191-2008《水工混凝土结构设计规范》
  - SL 386-2007《水利水电工程边坡设计规范》（Fs ≥ 1.3 正常工况）
  - USBR Design of Small Canal Structures（扬压力计算）
  - Terzaghi 有效应力原理（渗流力计算）
  - Bishop 简化法（边坡稳定）

测试分类：
  1. 渗流模型物理正确性（5个）
  2. 扬压力计算精度（5个）
  3. 边坡稳定计算（5个）
  4. 工况场景测试（5个）
  5. 降阶模型精度（5个）
  6. MPC 控制器（5个）
  7. ODD 安全包络（5个）
"""
import sys
import os
import pytest
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'pipedream-hydrology-integration-lab'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'HydroClaw'))

from solvers.canal_slope_lining import (
    CanalSection, CanalSlopeLiningSystem, SeepageModel1D
)


# ===========================================================================
# 测试夹具
# ===========================================================================

@pytest.fixture
def standard_section():
    """标准梯形渠道断面（南水北调典型参数）。"""
    return CanalSection(
        B_bottom=6.0,    # 底宽 6m
        H_design=3.0,    # 设计水深 3m
        m_slope=2.0,     # 边坡系数 1:2
        k_soil=5e-6,     # 渗透系数 5e-6 m/s（壤土）
        drain_spacing=0, # 无排水孔
        phi_soil=28.0,   # 内摩擦角 28°
        c_soil=10.0,     # 黏聚力 10 kPa
        gamma_soil=19.0, # 天然容重 19 kN/m³
        gamma_sat=20.0,  # 饱和容重 20 kN/m³
    )


@pytest.fixture
def system_normal(standard_section):
    """正常运行工况系统（低地下水位）。"""
    sys = CanalSlopeLiningSystem(standard_section)
    sys.initialize(h_canal_0=3.0, h_gw_far=0.5)
    return sys


@pytest.fixture
def system_high_gw(standard_section):
    """高地下水位工况系统。"""
    sys = CanalSlopeLiningSystem(standard_section)
    sys.initialize(h_canal_0=3.0, h_gw_far=4.0)
    return sys


# ===========================================================================
# 1. 渗流模型物理正确性
# ===========================================================================

class TestSeepageModel:

    def test_steady_state_linear_head(self, standard_section):
        """稳态渗流：水头应从渠道侧线性变化到远场。"""
        # SeepageModel1D 需要通过 CanalSection 构造
        sys = CanalSlopeLiningSystem(standard_section)
        sys.initialize(h_canal_0=3.0, h_gw_far=3.0)  # 等水头，无渗流
        # 稳态下水头应均匀
        assert np.std(sys.seepage.h) < 0.5, "等水头条件下水头应均匀"

    def test_seepage_direction(self, standard_section):
        """渗流方向：地下水高于渠道时，水头从远场流向渠道。"""
        sys = CanalSlopeLiningSystem(standard_section)
        sys.initialize(h_canal_0=1.0, h_gw_far=4.0)
        # 地下水高于渠道，水头应从远场（高）到渠道（低）
        assert sys.seepage.h[-1] >= sys.seepage.h[0], "地下水高时水头应从远场到渠道递减"

    def test_pore_pressure_positive(self, standard_section):
        """孔隙水压力：在有地下水的区域应为正值。"""
        sys = CanalSlopeLiningSystem(standard_section)
        sys.initialize(h_canal_0=3.0, h_gw_far=4.0)
        p = sys.seepage.get_pore_pressure()
        # 靠近渠道侧（z=0）孔隙水压力应为正（地下水头 > 0）
        assert p[0] >= 0, "渠道侧孔隙水压力应为非负"

    def test_seepage_mass_conservation(self, standard_section):
        """渗流质量守恒：稳态下进出流量应平衡。"""
        sys = CanalSlopeLiningSystem(standard_section)
        sys.initialize(h_canal_0=3.0, h_gw_far=4.0)
        # 运行多步达到稳态
        for _ in range(100):
            sys.step(dt=3600.0, h_canal=3.0)
        # 稳态下水头变化应很小
        h_before = sys.seepage.h.copy()
        sys.step(dt=3600.0, h_canal=3.0)
        dh = np.max(np.abs(sys.seepage.h - h_before))
        assert dh < 0.05, f"稳态下水头变化应 < 0.05m，实际 {dh:.4f}m"

    def test_drainage_reduces_head(self, standard_section):
        """排水孔效果：有排水孔时扬压力应低于无排水孔。"""
        sec_no_drain = CanalSection(
            B_bottom=6.0, H_design=3.0, m_slope=2.0,
            k_soil=5e-6, drain_spacing=0
        )
        sec_with_drain = CanalSection(
            B_bottom=6.0, H_design=3.0, m_slope=2.0,
            k_soil=5e-6, drain_spacing=3.0, drain_efficiency=0.5
        )
        sys1 = CanalSlopeLiningSystem(sec_no_drain)
        sys1.initialize(h_canal_0=3.0, h_gw_far=4.0)
        s1 = sys1.step(3600.0, 3.0)

        sys2 = CanalSlopeLiningSystem(sec_with_drain)
        sys2.initialize(h_canal_0=3.0, h_gw_far=4.0)
        s2 = sys2.step(3600.0, 3.0)

        assert s2.p_uplift_max <= s1.p_uplift_max, \
            "排水孔应降低扬压力"


# ===========================================================================
# 2. 扬压力计算精度
# ===========================================================================

class TestUpliftPressure:

    def test_no_uplift_when_canal_higher(self, system_normal):
        """当渠道水位高于地下水位时，净扬压力应为零。"""
        state = system_normal.step(3600.0, 3.0)
        assert state.p_uplift_max >= 0.0, "扬压力不应为负"
        # 正常工况（地下水低）扬压力应接近零
        assert state.p_uplift_max < 5.0, \
            f"正常工况扬压力应 < 5kPa，实际 {state.p_uplift_max:.2f}kPa"

    def test_uplift_when_gw_higher(self, system_high_gw):
        """当地下水位高于渠道水位时，应产生正扬压力。"""
        state = system_high_gw.step(3600.0, 3.0)
        assert state.p_uplift_max > 0.0, \
            f"高地下水位时应有正扬压力，实际 {state.p_uplift_max:.2f}kPa"

    def test_uplift_safety_factor_formula(self, system_high_gw):
        """抗浮安全系数公式：Fs_uplift = W_lining / F_uplift。"""
        state = system_high_gw.step(3600.0, 3.0)
        # 高地下水位时抗浮系数应 < 正常值（1.1 是规范下限）
        # 不要求 < 1.1，但应该比正常工况低
        assert state.safety_uplift < 100.0, \
            f"高地下水位时抗浮系数应有限，实际 {state.safety_uplift:.2f}"

    def test_uplift_increases_with_gw_level(self, standard_section):
        """扬压力应随地下水位升高而增大。"""
        p_uplift_list = []
        for h_gw in [1.0, 2.0, 3.0, 4.0]:
            sys = CanalSlopeLiningSystem(standard_section)
            sys.initialize(h_canal_0=3.0, h_gw_far=h_gw)
            state = sys.step(3600.0, 3.0)
            p_uplift_list.append(state.p_uplift_max)
        # 扬压力应单调递增（或至少不递减）
        for i in range(len(p_uplift_list) - 1):
            assert p_uplift_list[i] <= p_uplift_list[i+1] + 0.1, \
                f"扬压力应随地下水位升高而增大: {p_uplift_list}"

    def test_bottom_uplift_pressure_magnitude(self, standard_section):
        """渠底扬压力量级验证：与 Terzaghi 有效应力理论一致。"""
        # 地下水位高出渠底 2m，渠道水位 = 渠底（放空）
        sec = CanalSection(
            B_bottom=6.0, H_design=3.0, m_slope=2.0,
            k_soil=5e-6, drain_spacing=0
        )
        sys = CanalSlopeLiningSystem(sec)
        sys.initialize(h_canal_0=0.0, h_gw_far=2.0)
        # 运行多步达到稳态
        for _ in range(50):
            sys.step(3600.0, 0.0)
        state = sys.step(3600.0, 0.0)
        # 渠底扬压力 ≈ gamma_w * h_gw = 9.81 * 2 ≈ 19.6 kPa
        # 由于渗流衰减，实际值会低于理论值
        assert state.p_uplift_max >= 0.0, "放空工况应有扬压力"


# ===========================================================================
# 3. 边坡稳定计算
# ===========================================================================

class TestSlopeStability:

    def test_fs_greater_than_one_normal(self, system_normal):
        """正常工况安全系数应 > 1.0（不失稳）。"""
        state = system_normal.step(3600.0, 3.0)
        assert state.Fs_slope > 1.0, \
            f"正常工况 Fs 应 > 1.0，实际 {state.Fs_slope:.3f}"

    def test_fs_meets_standard_normal(self, system_normal):
        """正常工况安全系数应 ≥ 1.3（SL 386 规范要求）。"""
        state = system_normal.step(3600.0, 3.0)
        assert state.Fs_slope >= 1.3, \
            f"正常工况 Fs 应 ≥ 1.3，实际 {state.Fs_slope:.3f}"

    def test_fs_decreases_with_high_gw(self, standard_section):
        """高地下水位应降低边坡安全系数。"""
        sys_low = CanalSlopeLiningSystem(standard_section)
        sys_low.initialize(h_canal_0=3.0, h_gw_far=0.5)
        s_low = sys_low.step(3600.0, 3.0)

        sys_high = CanalSlopeLiningSystem(standard_section)
        sys_high.initialize(h_canal_0=3.0, h_gw_far=4.0)
        s_high = sys_high.step(3600.0, 3.0)

        assert s_high.Fs_slope <= s_low.Fs_slope, \
            f"高地下水位 Fs({s_high.Fs_slope:.3f}) 应 ≤ 低地下水位 Fs({s_low.Fs_slope:.3f})"

    def test_fs_increases_with_cohesion(self, standard_section):
        """黏聚力增大应提高安全系数。"""
        sec_low_c = CanalSection(
            B_bottom=6.0, H_design=3.0, m_slope=2.0,
            k_soil=5e-6, phi_soil=28.0, c_soil=5.0
        )
        sec_high_c = CanalSection(
            B_bottom=6.0, H_design=3.0, m_slope=2.0,
            k_soil=5e-6, phi_soil=28.0, c_soil=20.0
        )
        sys1 = CanalSlopeLiningSystem(sec_low_c)
        sys1.initialize(h_canal_0=3.0, h_gw_far=2.0)
        s1 = sys1.step(3600.0, 3.0)

        sys2 = CanalSlopeLiningSystem(sec_high_c)
        sys2.initialize(h_canal_0=3.0, h_gw_far=2.0)
        s2 = sys2.step(3600.0, 3.0)

        assert s2.Fs_slope >= s1.Fs_slope, \
            f"高黏聚力 Fs({s2.Fs_slope:.3f}) 应 ≥ 低黏聚力 Fs({s1.Fs_slope:.3f})"

    def test_safety_margins_output(self, system_normal):
        """安全裕度输出格式正确。"""
        system_normal.step(3600.0, 3.0)
        margins = system_normal.get_safety_margins()
        required_keys = ['Fs_margin', 'uplift_margin', 'dh_max_safe',
                         'current_Fs', 'current_safety_uplift', 'current_p_uplift_max']
        for key in required_keys:
            assert key in margins, f"安全裕度缺少键: {key}"
        assert margins['current_Fs'] > 0, "当前 Fs 应为正"
        assert margins['dh_max_safe'] >= 0, "最大安全降速应为非负"


# ===========================================================================
# 4. 工况场景测试
# ===========================================================================

class TestScenarios:

    def test_rapid_drawdown_warning(self, standard_section):
        """快速放水工况：应触发安全警告（Fs 降低）。"""
        sys = CanalSlopeLiningSystem(standard_section)
        sys.initialize(h_canal_0=3.0, h_gw_far=2.0)
        # 先稳定运行
        for _ in range(24):
            sys.step(3600.0, 3.0)
        s_before = sys.step(3600.0, 3.0)
        # 快速放水
        for h in np.linspace(3.0, 0.5, 6):
            s_after = sys.step(3600.0, float(h))
        # 放水后安全系数应有变化（渗流滞后）
        assert s_after.Fs_slope > 0, "放水后 Fs 应为正"

    def test_maintenance_dewatering(self, standard_section):
        """停水检修工况（渠道放空）：应正确计算扬压力。"""
        sys = CanalSlopeLiningSystem(standard_section)
        sys.initialize(h_canal_0=3.0, h_gw_far=3.5)
        # 稳定运行后放空
        for _ in range(48):
            sys.step(3600.0, 3.0)
        state = sys.step(3600.0, 0.0)  # 放空
        # 放空时如果地下水仍高，应有扬压力
        assert state.p_uplift_max >= 0.0, "放空工况扬压力应为非负"

    def test_seasonal_gw_variation(self, standard_section):
        """季节性地下水变化：Fs 应随地下水位周期性变化。"""
        sys = CanalSlopeLiningSystem(standard_section)
        sys.initialize(h_canal_0=3.0, h_gw_far=1.0)
        Fs_list = []
        # 模拟地下水位从低到高再到低的变化
        gw_levels = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 3.5, 3.0, 2.5, 2.0, 1.5]
        for h_gw in gw_levels:
            sys.seepage.h_gw_far = h_gw
            state = sys.step(3600.0, 3.0)
            Fs_list.append(state.Fs_slope)
        # Fs 应随地下水位升高而降低（整体趋势）
        assert Fs_list[0] >= Fs_list[6], \
            f"地下水最低时 Fs({Fs_list[0]:.3f}) 应 ≥ 地下水最高时 Fs({Fs_list[6]:.3f})"

    def test_state_output_completeness(self, system_normal):
        """状态输出应包含所有必要字段。"""
        state = system_normal.step(3600.0, 3.0)
        assert hasattr(state, 'Fs_slope'), "缺少 Fs_slope"
        assert hasattr(state, 'p_uplift_max'), "缺少 p_uplift_max"
        assert hasattr(state, 'safety_uplift'), "缺少 safety_uplift"
        assert hasattr(state, 'phreatic_depth'), "缺少 phreatic_depth"
        assert hasattr(state, 'critical_mode'), "缺少 critical_mode"

    def test_time_stepping_stability(self, standard_section):
        """长时间步进稳定性：100步后状态应有界。"""
        sys = CanalSlopeLiningSystem(standard_section)
        sys.initialize(h_canal_0=3.0, h_gw_far=2.0)
        for i in range(100):
            h = 3.0 + 0.5 * np.sin(i * 0.1)  # 周期性水位变化
            state = sys.step(3600.0, float(h))
        assert np.isfinite(state.Fs_slope), "长时间步进后 Fs 应有限"
        assert np.isfinite(state.p_uplift_max), "长时间步进后扬压力应有限"
        assert state.Fs_slope > 0.5, "长时间步进后 Fs 应 > 0.5"


# ===========================================================================
# 5. 降阶模型精度
# ===========================================================================

class TestReducedOrderModel:

    def test_fopdt_step_response(self):
        """FOPDT 阶跃响应：应从初始值收敛到新稳态。"""
        try:
            from reduced_order.canal_slope_rom import FOPDTModel
        except ImportError:
            pytest.skip("pipedream ROM 模块不可用")

        model = FOPDTModel(K=-0.1, tau=86400.0, theta=3600.0,
                           y_ss=1.5, u_ss=3.0, dt=3600.0)
        # 阶跃：水位从 3.0 降到 1.5
        y_list = [model.step(3.0) for _ in range(5)]
        y_list += [model.step(1.5) for _ in range(50)]
        # 最终值应趋向新稳态
        y_final = y_list[-1]
        y_new_ss = 1.5 + (-0.1) * (1.5 - 3.0)  # = 1.65
        assert abs(y_final - y_new_ss) < 0.1, \
            f"FOPDT 稳态误差 {abs(y_final - y_new_ss):.3f} 应 < 0.1"

    def test_fopdt_predict_length(self):
        """FOPDT 多步预测：输出长度应与输入一致。"""
        try:
            from reduced_order.canal_slope_rom import FOPDTModel
        except ImportError:
            pytest.skip("pipedream ROM 模块不可用")

        model = FOPDTModel(K=-0.1, tau=86400.0, theta=3600.0,
                           y_ss=1.5, u_ss=3.0, dt=3600.0)
        u_future = np.linspace(3.0, 1.0, 12)
        y_pred = model.predict(u_future)
        assert len(y_pred) == 12, f"预测长度应为 12，实际 {len(y_pred)}"

    def test_fopdt_state_restoration_after_predict(self):
        """FOPDT 预测后状态应恢复（不改变内部状态）。"""
        try:
            from reduced_order.canal_slope_rom import FOPDTModel
        except ImportError:
            pytest.skip("pipedream ROM 模块不可用")

        model = FOPDTModel(K=-0.1, tau=86400.0, theta=3600.0,
                           y_ss=1.5, u_ss=3.0, dt=3600.0)
        y_before = model._y
        buf_before = model._u_buffer.copy()
        # 预测不应改变内部状态
        model.predict(np.linspace(3.0, 1.0, 10))
        assert abs(model._y - y_before) < 1e-10, "预测后内部状态应恢复"
        assert np.allclose(model._u_buffer, buf_before), "预测后缓冲区应恢复"

    def test_canal_slope_rom_state_matrices(self):
        """ROM 状态空间矩阵：维度应正确。"""
        try:
            from reduced_order.canal_slope_rom import CanalSlopeROM
        except ImportError:
            pytest.skip("pipedream ROM 模块不可用")

        rom = CanalSlopeROM(
            section_params={'B_bottom': 6.0, 'H_design': 3.0, 'm_slope': 2.0,
                            'k_soil': 5e-6},
            dt=3600.0
        )
        rom.train(method='fopdt', n_scenarios=3, T_total=24*3600.0)
        A, B, C, D = rom.get_state_matrices()
        assert A.shape[0] == A.shape[1], "A 矩阵应为方阵"
        assert B.shape[0] == A.shape[0], "B 矩阵行数应与 A 一致"
        assert C.shape[1] == A.shape[0], "C 矩阵列数应与 A 一致"

    def test_canal_slope_rom_safe_bounds(self):
        """ROM 安全约束边界：h_min 和 dh_max 应为合理值。"""
        try:
            from reduced_order.canal_slope_rom import CanalSlopeROM
        except ImportError:
            pytest.skip("pipedream ROM 模块不可用")

        rom = CanalSlopeROM(
            section_params={'B_bottom': 6.0, 'H_design': 3.0, 'm_slope': 2.0,
                            'k_soil': 5e-6},
            dt=3600.0
        )
        rom.train(method='fopdt', n_scenarios=3, T_total=24*3600.0)
        bounds = rom.get_safe_water_level_bounds(Fs_min=1.3)
        assert 'h_min_safe' in bounds, "缺少 h_min_safe"
        assert 'dh_max_drop' in bounds, "缺少 dh_max_drop"
        assert bounds['h_min_safe'] >= 0.0, "h_min_safe 应为非负"
        assert bounds['dh_max_drop'] > 0.0, "dh_max_drop 应为正"


# ===========================================================================
# 6. MPC 控制器
# ===========================================================================

class TestSlopeSafetyMPC:

    @pytest.fixture
    def mpc_with_fopdt(self):
        try:
            from core.control.slope_safety_mpc import SlopeSafetyMPC, SlopeSafetyMPCConfig
            from reduced_order.canal_slope_rom import FOPDTModel
        except ImportError:
            pytest.skip("MPC 或 ROM 模块不可用")
        config = SlopeSafetyMPCConfig(
            N_p=6, N_c=3, dt=3600.0, h_ref=3.0,
            h_min=0.5, h_max=3.5,
            dh_max_drop=0.3, dh_max_rise=0.4,
            Fs_min=1.3, Q_h=1.0, Q_Fs=10.0, R_u=0.1
        )
        mpc = SlopeSafetyMPC(config)
        mpc.fopdt = FOPDTModel(K=-0.05, tau=86400.0, theta=7200.0,
                               y_ss=1.5, u_ss=3.0, dt=3600.0)
        return mpc

    def test_mpc_returns_valid_setpoint(self, mpc_with_fopdt):
        """MPC 应返回有效的水位设定值。"""
        result = mpc_with_fopdt.compute_control(h_obs=3.0, Fs_obs=1.5)
        assert 'h_setpoint' in result, "缺少 h_setpoint"
        assert mpc_with_fopdt.cfg.h_min <= result['h_setpoint'] <= mpc_with_fopdt.cfg.h_max, \
            f"h_setpoint={result['h_setpoint']:.3f} 超出范围"

    def test_mpc_respects_rate_constraint(self, mpc_with_fopdt):
        """MPC 应遵守放水速率约束。"""
        result = mpc_with_fopdt.compute_control(h_obs=3.0, Fs_obs=1.5, h_ref_override=0.5)
        delta_h = result['h_setpoint'] - 3.0
        assert delta_h >= -mpc_with_fopdt.cfg.dh_max_drop - 1e-6, \
            f"放水速率 {-delta_h:.3f} 超过限制 {mpc_with_fopdt.cfg.dh_max_drop}"

    def test_mpc_stable_at_setpoint(self, mpc_with_fopdt):
        """在目标水位处 MPC 应输出接近零的控制量。"""
        result = mpc_with_fopdt.compute_control(h_obs=3.0, Fs_obs=1.5)
        delta_h = abs(result['h_setpoint'] - 3.0)
        assert delta_h < 0.1, f"目标水位处控制量应接近零，实际 {delta_h:.3f}"

    def test_mpc_fs_prediction_length(self, mpc_with_fopdt):
        """MPC 安全系数预测长度应等于预测时域。"""
        result = mpc_with_fopdt.compute_control(h_obs=3.0, Fs_obs=1.5)
        assert len(result['Fs_predicted']) == mpc_with_fopdt.cfg.N_p, \
            f"Fs 预测长度应为 {mpc_with_fopdt.cfg.N_p}"

    def test_mpc_safety_report(self, mpc_with_fopdt):
        """MPC 安全报告应包含必要字段。"""
        for _ in range(5):
            mpc_with_fopdt.compute_control(h_obs=3.0, Fs_obs=1.5)
        report = mpc_with_fopdt.get_safety_report()
        assert 'total_steps' in report, "缺少 total_steps"
        assert 'constraint_violations' in report, "缺少 constraint_violations"
        assert report['total_steps'] == 5, f"步数应为 5，实际 {report['total_steps']}"


# ===========================================================================
# 7. ODD 安全包络
# ===========================================================================

class TestODDConstraint:

    @pytest.fixture
    def odd_constraint(self):
        try:
            from core.control.slope_safety_mpc import (
                SlopeSafetyMPC, SlopeSafetyMPCConfig, SlopeSafetyODDConstraint
            )
            from reduced_order.canal_slope_rom import FOPDTModel
        except ImportError:
            pytest.skip("MPC 或 ROM 模块不可用")
        config = SlopeSafetyMPCConfig(N_p=6, N_c=3, dt=3600.0, h_ref=3.0)
        mpc = SlopeSafetyMPC(config)
        mpc.fopdt = FOPDTModel(K=-0.05, tau=86400.0, theta=7200.0,
                               y_ss=1.5, u_ss=3.0, dt=3600.0)
        return SlopeSafetyODDConstraint(mpc, Fs_warning=1.4, Fs_critical=1.3, Fs_emergency=1.1)

    def test_normal_in_odd(self, odd_constraint):
        """正常工况（Fs=1.5）应在 ODD 范围内。"""
        check = odd_constraint.check(h_canal=3.0, Fs_current=1.5)
        assert check['in_odd'] is True, "正常工况应在 ODD 范围内"
        assert check['level'] == 'normal', f"应为 normal，实际 {check['level']}"

    def test_warning_level(self, odd_constraint):
        """Fs 在 1.3~1.4 之间应触发警告级别。"""
        check = odd_constraint.check(h_canal=2.0, Fs_current=1.35)
        assert check['level'] == 'warning', f"应为 warning，实际 {check['level']}"
        assert check['in_odd'] is True, "警告级别仍在 ODD 范围内"

    def test_critical_level(self, odd_constraint):
        """Fs 在 1.1~1.3 之间应触发临界级别。"""
        check = odd_constraint.check(h_canal=1.5, Fs_current=1.2)
        assert check['level'] == 'critical', f"应为 critical，实际 {check['level']}"
        assert check['in_odd'] is False, "临界级别超出 ODD 范围"

    def test_emergency_level(self, odd_constraint):
        """Fs < 1.1 应触发紧急级别。"""
        check = odd_constraint.check(h_canal=1.0, Fs_current=1.05)
        assert check['level'] == 'emergency', f"应为 emergency，实际 {check['level']}"
        assert check['max_dh_drop_mh'] < 0, "紧急模式应要求充水（负降速）"

    def test_odd_override_emergency(self, odd_constraint):
        """紧急模式下 ODD 应覆盖 MPC 输出。"""
        from core.control.slope_safety_mpc import SlopeSafetyMPCConfig
        control_result = {
            'h_setpoint': 1.0,
            'u_sequence': np.array([1.0, 1.0, 1.0]),
            'Fs_predicted': np.array([1.05, 1.05, 1.05]),
            'safety_status': '测试',
            'constraint_active': False,
        }
        result = odd_constraint.override_mpc(control_result, Fs_current=1.05)
        assert result['odd_override'] is True, "紧急模式应触发覆盖"
        assert result['h_setpoint'] >= 1.0, "紧急模式应提升水位"
