# -*- coding: utf-8 -*-
"""
单元测试: tests/models/test_weir_model.py
"""
import pytest
import warnings
warnings.filterwarnings("ignore")
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from models.weir import BroadCrestedWeirModel, SharpCrestedWeirModel, VNotchWeirModel, get_weir_model

# ==================== 测试 BroadCrestedWeirModel ====================

def test_broad_crested_weir_free_flow():
    """测试宽顶堰在自由流条件下的计算"""
    weir = get_weir_model("broad_crested", width=10.0, crest_height=2.0, discharge_coeff=1.7)
    result = weir.calculate_discharge(upstream_depth=3.5, downstream_depth=2.1)

    head = 3.5 - 2.0  # H = 1.5m
    assert result["head"] == pytest.approx(1.5)
    assert result["flow_regime"] == "free"
    # 理论计算: Q = 1.7 * 10.0 * (1.5)^(3/2) = 31.25
    assert result["discharge"] == pytest.approx(31.25, rel=1e-2)

def test_broad_crested_weir_submerged_flow():
    """测试宽顶堰在淹没流条件下的计算"""
    weir = get_weir_model("broad_crested", width=10.0, crest_height=2.0, discharge_coeff=1.7)
    # 下游水深较高，导致淹没
    result = weir.calculate_discharge(upstream_depth=3.5, downstream_depth=3.2)

    assert result["flow_regime"] == "submerged"
    # 淹没流的流量应小于同等水头的自由流
    assert result["discharge"] < 31.25

def test_broad_crested_weir_no_flow():
    """测试上游水位低于堰顶的情况"""
    weir = get_weir_model("broad_crested", width=10.0, crest_height=2.0, discharge_coeff=1.7)
    result = weir.calculate_discharge(upstream_depth=1.9, downstream_depth=1.8)

    assert result["discharge"] == 0.0
    assert result["flow_regime"] == "no_flow"


# ==================== 测试 SharpCrestedWeirModel ====================

def test_sharp_crested_weir_free_flow():
    """测试尖顶堰的计算"""
    weir = get_weir_model("sharp_crested", width=5.0, crest_height=1.0, discharge_coeff=0.62)
    result = weir.calculate_discharge(upstream_depth=2.0, downstream_depth=0.5)

    head = 2.0 - 1.0 # H = 1.0m
    assert result["head"] == pytest.approx(1.0)
    # 修复：测试现在应该基于模型中使用的正确公式
    # 正确公式: Q = (2/3) * C_d * b * sqrt(2g) * H^(3/2)
    from math import sqrt
    expected_q = (2/3) * 0.62 * 5.0 * sqrt(2 * 9.81) * (1.0 ** 1.5)
    assert result["discharge"] == pytest.approx(expected_q, rel=1e-2)


# ==================== 测试 VNotchWeirModel ====================

def test_v_notch_weir_flow():
    """测试V型堰的计算"""
    weir = get_weir_model("v_notch", angle_deg=90, crest_height=0.5, discharge_coeff=0.58)
    result = weir.calculate_discharge(upstream_depth=1.0, downstream_depth=0.2)

    head = 1.0 - 0.5 # H = 0.5m
    assert result["head"] == pytest.approx(0.5)
    # 理论计算: Q = (8/15) * 0.58 * tan(90/2) * sqrt(2*9.81) * (0.5)^2.5 = 0.24
    from math import tan, radians, sqrt
    expected_q = (8/15) * 0.58 * tan(radians(90)/2) * sqrt(2*9.81) * (0.5**2.5)
    assert result["discharge"] == pytest.approx(expected_q, rel=1e-2)


# ==================== 测试工厂函数和异常 ====================

def test_get_weir_model_factory_and_exceptions():
    """测试堰模型工厂函数及参数校验"""
    broad = get_weir_model("broad_crested", width=1, crest_height=1, discharge_coeff=1)
    assert isinstance(broad, BroadCrestedWeirModel)

    sharp = get_weir_model("sharp_crested", width=1, crest_height=1, discharge_coeff=1)
    assert isinstance(sharp, SharpCrestedWeirModel)

    vnotch = get_weir_model("v_notch", angle_deg=90, crest_height=1, discharge_coeff=1)
    assert isinstance(vnotch, VNotchWeirModel)

    with pytest.raises(ValueError, match="不支持的堰类型"):
        get_weir_model("unknown_type")

    with pytest.raises(ValueError, match="'width' 必须为正数"):
        get_weir_model("broad_crested", width=0, crest_height=1, discharge_coeff=1)

    with pytest.raises(ValueError, match="'angle_deg' 必须在 0 到 180 度之间"):
        get_weir_model("v_notch", angle_deg=190, crest_height=1, discharge_coeff=1)
