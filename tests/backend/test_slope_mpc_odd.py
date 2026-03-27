"""渠道边坡 MPC 控制器与 ODD 安全包络测试

这些测试依赖 HydroMind(HydroClaw) 仓库中的 core.control 模块。
由于 HydroClaude 自身也有 core/ 目录，需要确保 HydroClaw 路径优先。
"""
import sys
import os
import pytest
import numpy as np

# 确保 HydroClaw 路径优先于 HydroClaude 的 core/
_hydroclaw = '/home/ubuntu/HydroClaw'
_pipedream = '/home/ubuntu/pipedream-hydrology-integration-lab'
if _hydroclaw not in sys.path:
    sys.path.insert(0, _hydroclaw)
if _pipedream not in sys.path:
    sys.path.insert(0, _pipedream)

# 强制重新加载 core 模块（避免 HydroClaude/core 的缓存污染）
import importlib
for mod_name in list(sys.modules.keys()):
    if mod_name == 'core' or mod_name.startswith('core.'):
        del sys.modules[mod_name]


def _try_import_mpc():
    """尝试导入 MPC 模块，返回 (SlopeSafetyMPC, SlopeSafetyMPCConfig, SlopeSafetyODDConstraint) 或 None。"""
    try:
        from core.control.slope_safety_mpc import (
            SlopeSafetyMPC, SlopeSafetyMPCConfig, SlopeSafetyODDConstraint
        )
        return SlopeSafetyMPC, SlopeSafetyMPCConfig, SlopeSafetyODDConstraint
    except ImportError as e:
        return None


def _try_import_fopdt():
    try:
        from reduced_order.canal_slope_rom import FOPDTModel
        return FOPDTModel
    except ImportError:
        return None


# ===========================================================================
# 6. MPC 控制器测试
# ===========================================================================

class TestSlopeSafetyMPC:

    @pytest.fixture
    def mpc_with_fopdt(self):
        result = _try_import_mpc()
        if result is None:
            pytest.skip("HydroMind MPC 模块不可用")
        SlopeSafetyMPC, SlopeSafetyMPCConfig, _ = result
        FOPDTModel = _try_import_fopdt()
        if FOPDTModel is None:
            pytest.skip("pipedream ROM 模块不可用")

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
        """MPC 应遵守放水速率约束（dh_max_drop）。"""
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
        """MPC 安全系数预测长度应等于预测时域 N_p。"""
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
# 7. ODD 安全包络测试
# ===========================================================================

class TestODDConstraint:

    @pytest.fixture
    def odd_constraint(self):
        result = _try_import_mpc()
        if result is None:
            pytest.skip("HydroMind MPC 模块不可用")
        SlopeSafetyMPC, SlopeSafetyMPCConfig, SlopeSafetyODDConstraint = result
        FOPDTModel = _try_import_fopdt()
        if FOPDTModel is None:
            pytest.skip("pipedream ROM 模块不可用")

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
