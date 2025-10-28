#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
配置驱动系统测试套件

测试配置驱动仿真系统的所有组件

作者: HydroClaude Team
日期: 2025-10-28
"""

import sys
import os
from pathlib import Path
import json
import pytest
import numpy as np

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from engine.config_parser import ConfigParser
from engine.model_builder import ModelBuilder
from engine.simulation_engine import SimulationEngine


class TestConfigParser:
    """配置解析器测试"""

    def test_parse_valid_config(self):
        """测试解析有效配置"""
        config_file = project_root / 'examples/config_driven/uniform_flow.json'
        parser = ConfigParser(str(config_file))
        config = parser.parse()

        assert 'project' in config
        assert 'geometry' in config
        assert 'solver' in config
        assert config['project']['name'] == '均匀流验证 (配置驱动)'

    def test_required_fields_validation(self):
        """测试必需字段验证"""
        # 创建缺少必需字段的配置
        incomplete_config = {
            'project': {'name': 'Test'},
            'geometry': {},  # 缺少必需字段
            'mesh': {'n_cells': 100}
        }

        temp_file = Path('/tmp/test_incomplete.json')
        with open(temp_file, 'w') as f:
            json.dump(incomplete_config, f)

        parser = ConfigParser(str(temp_file))

        # 导入ConfigValidationError
        from engine.config_parser import ConfigValidationError
        with pytest.raises(ConfigValidationError):
            parser.parse()

        temp_file.unlink()

    def test_default_values(self):
        """测试默认值应用"""
        minimal_config = {
            'project': {'name': 'Test'},
            'geometry': {
                'type': 'uniform',  # 必需字段
                'channel_width': 10.0,
                'channel_length': 1000.0,
                'bottom_slope': 0.001,
                'manning_n': 0.025
            },
            'mesh': {'n_cells': 100},
            'solver': {'type': 'godunov_fvm'},
            'initial_conditions': {'type': 'uniform', 'h': 2.0, 'Q': 10.0},
            'boundary_conditions': {
                'left': {'type': 'Q', 'value': 10.0},
                'right': {'type': 'h', 'value': 2.0}
            },
            'simulation': {'end_time': 100.0}
        }

        temp_file = Path('/tmp/test_minimal.json')
        with open(temp_file, 'w') as f:
            json.dump(minimal_config, f)

        parser = ConfigParser(str(temp_file))
        config = parser.parse()

        # 检查默认值
        assert config['simulation']['start_time'] == 0.0
        assert config['solver']['cfl'] == 0.5
        assert config['output']['formats'] == ['csv']

        temp_file.unlink()


class TestModelBuilder:
    """模型构建器测试"""

    def test_build_solver_from_config(self):
        """测试从配置构建求解器"""
        config_file = project_root / 'examples/config_driven/uniform_flow.json'
        builder = ModelBuilder.from_config_file(str(config_file))
        solver = builder.build_solver()

        assert solver is not None
        assert solver.n_cells == 100
        assert solver.B == 10.0
        assert solver.L == 1000.0

    def test_initial_conditions_dam_break(self):
        """测试溃坝初始条件"""
        config_file = project_root / 'examples/config_driven/dam_break_short.json'
        builder = ModelBuilder.from_config_file(str(config_file))

        h, Q = builder._get_initial_conditions()

        assert len(h) == 200
        assert len(Q) == 200
        # 检查溃坝条件：左侧高，右侧低
        assert np.all(h[:100] > h[100:])

    def test_initial_conditions_uniform(self):
        """测试均匀流初始条件"""
        config_file = project_root / 'examples/config_driven/uniform_flow.json'
        builder = ModelBuilder.from_config_file(str(config_file))

        h, Q = builder._get_initial_conditions()

        assert len(h) == 100
        assert len(Q) == 100
        # 均匀流：所有单元相同
        assert np.allclose(h, 2.0)
        assert np.allclose(Q, 20.0)

    def test_analytical_solution_ritter(self):
        """测试Ritter解析解"""
        config_file = project_root / 'examples/config_driven/dam_break_short.json'
        builder = ModelBuilder.from_config_file(str(config_file))

        x = np.linspace(0, 2000, 200)
        t = 10.0

        h, u = builder.get_analytical_solution(t, x)

        assert len(h) == 200
        assert len(u) == 200
        # 检查物理合理性
        assert np.all(h >= 0)  # 水深非负


class TestSimulationEngine:
    """仿真引擎测试"""

    @pytest.mark.slow
    def test_run_simulation_uniform_flow(self):
        """测试运行均匀流仿真"""
        config_file = project_root / 'examples/config_driven/uniform_flow.json'
        engine = SimulationEngine(str(config_file))

        engine.initialize()
        engine.run()

        # 检查结果
        assert engine.results is not None
        assert 'final_state' in engine.results
        assert 'statistics' in engine.results

        stats = engine.results['statistics']
        assert stats['n_steps'] > 0
        assert stats['sim_time'] > 0
        assert stats['wall_time'] > 0

    @pytest.mark.slow
    def test_run_simulation_dam_break(self):
        """测试运行溃坝仿真"""
        config_file = project_root / 'examples/config_driven/dam_break_short.json'
        engine = SimulationEngine(str(config_file))

        engine.initialize()
        engine.run()

        # 检查质量守恒
        stats = engine.results['statistics']
        mass_error = stats['mass_error']
        assert abs(mass_error) < 0.1  # 质量守恒误差 < 0.1%


class TestIntegration:
    """集成测试"""

    @pytest.mark.slow
    def test_end_to_end_workflow(self):
        """测试端到端工作流"""
        config_file = project_root / 'examples/config_driven/dam_break_short.json'

        # 1. 解析配置
        parser = ConfigParser(str(config_file))
        config = parser.parse()
        assert config is not None

        # 2. 构建模型
        builder = ModelBuilder.from_config_file(str(config_file))
        solver = builder.build_solver()
        assert solver is not None

        # 3. 运行仿真
        engine = SimulationEngine(str(config_file))
        engine.initialize()
        engine.run()

        # 4. 检查输出
        output_dir = Path(config['output']['directory'])
        assert output_dir.exists()

        stats_file = output_dir / 'statistics.json'
        assert stats_file.exists()

        plots_dir = output_dir / 'plots'
        assert plots_dir.exists()
        assert (plots_dir / 'final_state.png').exists()


class TestPerformance:
    """性能测试"""

    def test_numba_acceleration(self):
        """测试Numba加速效果"""
        # 创建临时配置，分别测试启用/禁用Numba
        base_config = {
            'project': {'name': 'Numba Test'},
            'geometry': {
                'type': 'uniform',
                'channel_width': 10.0,
                'channel_length': 1000.0,
                'bottom_slope': 0.001,
                'manning_n': 0.025
            },
            'mesh': {'n_cells': 100},
            'solver': {
                'type': 'godunov_fvm',
                'use_numba': True  # 将被修改
            },
            'initial_conditions': {'type': 'uniform', 'h': 2.0, 'Q': 10.0},
            'boundary_conditions': {
                'left': {'type': 'Q', 'value': 10.0},
                'right': {'type': 'h', 'value': 2.0}
            },
            'simulation': {'end_time': 50.0},
            'output': {
                'directory': '/tmp/numba_test',
                'formats': [],
                'statistics': False,
                'plots': {'enabled': False}
            }
        }

        # 测试Numba版本
        config_numba = base_config.copy()
        config_numba['solver']['use_numba'] = True

        temp_file = Path('/tmp/test_numba.json')
        with open(temp_file, 'w') as f:
            json.dump(config_numba, f)

        engine = SimulationEngine(str(temp_file))
        engine.initialize()
        engine.run()

        wall_time_numba = engine.results['statistics']['wall_time']

        # Numba版本应该很快（< 5秒）
        assert wall_time_numba < 5.0

        temp_file.unlink()

    @pytest.mark.slow
    def test_scalability(self):
        """测试网格数可扩展性"""
        # 注意：禁用Numba以避免JIT编译缓存影响测试结果
        # Numba会在首次编译后缓存，导致后续运行更快，影响可扩展性测试
        grid_sizes = [50, 100, 200]
        wall_times = []

        for n_cells in grid_sizes:
            config = {
                'project': {'name': f'Scalability Test {n_cells}'},
                'geometry': {
                    'type': 'uniform',
                    'channel_width': 10.0,
                    'channel_length': 1000.0,
                    'bottom_slope': 0.001,
                    'manning_n': 0.025
                },
                'mesh': {'n_cells': n_cells},
                'solver': {'type': 'godunov_fvm', 'use_numba': False},
                'initial_conditions': {'type': 'uniform', 'h': 2.0, 'Q': 10.0},
                'boundary_conditions': {
                    'left': {'type': 'Q', 'value': 10.0},
                    'right': {'type': 'h', 'value': 2.0}
                },
                'simulation': {'end_time': 50.0},
                'output': {
                    'directory': f'/tmp/scalability_test_{n_cells}',
                    'formats': [],
                    'statistics': False,
                    'plots': {'enabled': False}
                }
            }

            temp_file = Path(f'/tmp/test_scale_{n_cells}.json')
            with open(temp_file, 'w') as f:
                json.dump(config, f)

            engine = SimulationEngine(str(temp_file))
            engine.initialize()
            engine.run()

            wall_times.append(engine.results['statistics']['wall_time'])
            temp_file.unlink()

        # 检查：时间应该随网格数增加（但不是线性）
        assert wall_times[1] > wall_times[0]
        assert wall_times[2] > wall_times[1]

        # 检查：可扩展性合理（200网格不应该比50网格慢20倍以上）
        # 理论上4倍网格应该慢4-8倍（考虑步数和计算量）
        assert wall_times[2] / wall_times[0] < 20.0


if __name__ == '__main__':
    # 运行测试
    pytest.main([__file__, '-v', '-s'])
