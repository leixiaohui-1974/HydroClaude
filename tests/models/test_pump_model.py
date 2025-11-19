# -*- coding: utf-8 -*-
"""
单元测试: tests/models/test_pump_model.py
"""
import pytest
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from models.pump import SinglePumpModel, ParallelPumpsModel, SeriesPumpsModel, get_pump_model

# ==================== 测试 SinglePumpModel ====================

def test_single_pump_at_rated_head():
    """测试单泵在额定扬程下的性能"""
    pump = SinglePumpModel(flow_rate=10.0, head=15.0)
    result = pump.calculate_performance(system_head=15.0)

    assert result["flow_rate"] == pytest.approx(10.0)
    assert result["head"] == 15.0
    assert result["error"] is None
    # 理论功率 P = (1000 * 9.81 * 10.0 * 15.0) / 0.85 / 1000 = 1731 kW
    assert result["power_kw"] == pytest.approx(1731.17, rel=1e-2)

def test_single_pump_below_rated_head():
    """测试单泵在低于额定扬程下的性能（流量应增加）"""
    pump = SinglePumpModel(flow_rate=10.0, head=15.0)
    result = pump.calculate_performance(system_head=12.0)

    assert result["flow_rate"] > 10.0
    assert result["head"] == 12.0
    assert result["error"] is None

def test_single_pump_above_rated_head():
    """测试单泵在高于额定扬程下的性能（流量应减少）"""
    pump = SinglePumpModel(flow_rate=10.0, head=15.0)
    result = pump.calculate_performance(system_head=18.0)

    assert result["flow_rate"] < 10.0
    assert result["head"] == 18.0
    assert result["error"] is None

def test_single_pump_shutdown_head():
    """测试系统扬程超过泵的关死扬程"""
    pump = SinglePumpModel(flow_rate=10.0, head=15.0)
    shutdown_head = 1.3 * 15.0
    result = pump.calculate_performance(system_head=shutdown_head + 1.0)

    assert result["flow_rate"] == 0.0
    assert result["power_kw"] == 0.0
    assert result["error"] is not None

# ==================== 测试 ParallelPumpsModel ====================

def test_parallel_pumps():
    """测试并联泵组的性能（流量加倍）"""
    pumps = ParallelPumpsModel(flow_rate=10.0, head=15.0, num_pumps=2)
    result = pumps.calculate_performance(system_head=15.0)

    assert result["flow_rate"] == pytest.approx(20.0)
    assert result["head"] == 15.0
    assert result["num_pumps"] == 2
    assert result["power_kw"] == pytest.approx(1731.17 * 2, rel=1e-2)

# ==================== 测试 SeriesPumpsModel ====================

def test_series_pumps():
    """测试串联泵组的性能（扬程加倍）"""
    pumps = SeriesPumpsModel(flow_rate=10.0, head=15.0, num_pumps=2)
    # 在串联情况下，如果要达到额定流量10.0，系统扬程需要是额定扬程的2倍
    system_head_for_rated_flow = 15.0 * 2
    result = pumps.calculate_performance(system_head=system_head_for_rated_flow)

    # 因为等效单泵扬程是 30/2=15，所以单泵流量是10
    assert result["flow_rate"] == pytest.approx(10.0)
    assert result["head"] == system_head_for_rated_flow
    assert result["num_pumps"] == 2
    # 每个泵工作在 (10, 15) 点, 功率是 1731.17, 总功率 * 2
    assert result["power_kw"] == pytest.approx(1731.17 * 2, rel=1e-2)


# ==================== 测试工厂函数和异常 ====================

def test_get_pump_model_factory():
    """测试泵模型工厂函数"""
    single = get_pump_model("single", flow_rate=1, head=1, num_pumps=1)
    assert isinstance(single, SinglePumpModel)

    parallel = get_pump_model("parallel", flow_rate=1, head=1, num_pumps=2)
    assert isinstance(parallel, ParallelPumpsModel)

    series = get_pump_model("series", flow_rate=1, head=1, num_pumps=2)
    assert isinstance(series, SeriesPumpsModel)

    with pytest.raises(ValueError):
        get_pump_model("unknown", flow_rate=1, head=1, num_pumps=1)

def test_invalid_pump_parameters():
    """测试无效的泵初始化参数"""
    with pytest.raises(ValueError):
        SinglePumpModel(flow_rate=-1, head=10)
    with pytest.raises(ValueError):
        ParallelPumpsModel(flow_rate=1, head=1, num_pumps=0)
