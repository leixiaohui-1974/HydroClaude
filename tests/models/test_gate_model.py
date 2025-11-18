# -*- coding: utf-8 -*-
"""
单元测试: tests/models/test_gate_model.py
"""
import pytest
import sys
from pathlib import Path

# 将项目根目录添加到sys.path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from models.gate import SluiceGateModel, RadialGateModel, get_gate_model

# ==================== 测试 SluiceGateModel ====================

def test_sluice_gate_free_flow():
    """测试平板闸门在自由流条件下的计算"""
    gate = SluiceGateModel(width=5.0, opening=1.0, discharge_coeff=0.6)
    result = gate.calculate_discharge(upstream_depth=4.0, downstream_depth=0.8)

    assert result["flow_regime"] == "free"
    assert "discharge" in result
    # 理论计算: Q = 0.6 * 5.0 * 1.0 * sqrt(2 * 9.81 * 4.0) = 26.57
    assert result["discharge"] == pytest.approx(26.57, rel=1e-2)
    assert result["error"] is None

def test_sluice_gate_submerged_flow():
    """测试平板闸门在淹没流条件下的计算"""
    gate = SluiceGateModel(width=5.0, opening=1.0, discharge_coeff=0.6)
    result = gate.calculate_discharge(upstream_depth=4.0, downstream_depth=3.0)

    assert result["flow_regime"] == "submerged"
    # 理论计算: Q = 0.6 * 5.0 * 1.0 * sqrt(2 * 9.81 * (4.0 - 3.0)) = 13.28
    assert result["discharge"] == pytest.approx(13.28, rel=1e-2)
    assert result["error"] is None

def test_sluice_gate_no_flow_due_to_head():
    """测试平板闸门因上下游水位差不足而无流量的情况"""
    gate = SluiceGateModel(width=5.0, opening=1.0, discharge_coeff=0.6)
    result = gate.calculate_discharge(upstream_depth=3.0, downstream_depth=3.5)

    assert result["discharge"] == 0.0
    assert "submerged" in result["flow_regime"]
    assert result["error"] is not None

def test_sluice_gate_no_flow_due_to_opening():
    """测试平板闸门因上游水深小于开度而无流量的情况"""
    gate = SluiceGateModel(width=5.0, opening=1.0, discharge_coeff=0.6)
    result = gate.calculate_discharge(upstream_depth=0.9, downstream_depth=0.5)

    assert result["discharge"] == 0.0
    assert result["flow_regime"] == "no_flow"
    assert result["error"] is not None


# ==================== 测试 RadialGateModel ====================

def test_radial_gate_free_flow():
    """测试径向闸门，其逻辑当前与平板闸门相同"""
    gate = RadialGateModel(width=5.0, opening=1.0, discharge_coeff=0.65) # 使用不同的系数
    result = gate.calculate_discharge(upstream_depth=4.0, downstream_depth=0.8)

    assert result["flow_regime"] == "free"
    # 理论计算: Q = 0.65 * 5.0 * 1.0 * sqrt(2 * 9.81 * 4.0) = 28.79
    assert result["discharge"] == pytest.approx(28.79, rel=1e-2)


# ==================== 测试工厂函数 get_gate_model ====================

def test_get_gate_model_factory():
    """测试闸门模型工厂函数"""
    sluice = get_gate_model("sluice", width=2, opening=1, discharge_coeff=0.6)
    assert isinstance(sluice, SluiceGateModel)

    radial = get_gate_model("radial", width=2, opening=1, discharge_coeff=0.6)
    assert isinstance(radial, RadialGateModel)

    with pytest.raises(ValueError):
        get_gate_model("unknown_type", width=2, opening=1, discharge_coeff=0.6)


# ==================== 测试边界条件和异常 ====================

def test_invalid_gate_parameters():
    """测试无效的闸门初始化参数"""
    with pytest.raises(ValueError):
        SluiceGateModel(width=-5.0, opening=1.0, discharge_coeff=0.6)
    with pytest.raises(ValueError):
        SluiceGateModel(width=5.0, opening=0, discharge_coeff=0.6)
    with pytest.raises(ValueError):
        SluiceGateModel(width=5.0, opening=1.0, discharge_coeff=-0.6)
