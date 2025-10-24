"""
Pytest配置和fixtures

提供共享的测试fixture
"""

import pytest
import numpy as np
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def simple_canal_params():
    """简单渠道参数"""
    return {
        'length': 1000.0,
        'nx': 101,
        'B': 10.0,
        'S0': 0.001,
        'n': 0.025,
        'g': 9.81
    }


@pytest.fixture
def sample_grid():
    """示例网格"""
    return np.linspace(0, 1000, 101)


@pytest.fixture
def sample_water_depth():
    """示例水深数据"""
    return np.ones(101) * 2.0


@pytest.fixture
def sample_flow():
    """示例流量数据"""
    return np.ones(101) * 10.0


@pytest.fixture
def temp_output_dir(tmp_path):
    """临时输出目录"""
    output_dir = tmp_path / "test_results"
    output_dir.mkdir()
    return str(output_dir)


@pytest.fixture
def canal_solver(simple_canal_params):
    """预配置的渠道求解器"""
    from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver

    solver = HydrostaticCanalSolver(**simple_canal_params)
    solver.Q_in = 10.0
    solver.h_downstream = 2.0

    return solver


@pytest.fixture
def data_exporter(temp_output_dir):
    """数据导出器实例"""
    from utils.data_exporter import DataExporter
    return DataExporter(output_dir=temp_output_dir)
