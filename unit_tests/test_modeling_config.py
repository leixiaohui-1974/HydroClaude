"""
建模配置模块单元测试

测试modeling/config.py的功能
"""

import pytest
import yaml
from pathlib import Path

from modeling.config import ModelConfig


class TestModelConfig:
    """建模配置测试类"""

    @pytest.fixture
    def sample_config_file(self, tmp_path):
        """创建示例配置文件"""
        config_data = {
            'project': {
                'name': 'Test Project',
                'description': 'Test Description'
            },
            'canal': {
                'length': 1000.0,
                'width': 10.0,
                'slope': 0.001,
                'manning_n': 0.025,
                'initial_depth': 2.0
            },
            'grid': {
                'nx': 101,
                'adaptive': False
            },
            'boundary': {
                'upstream': {'type': 'flow', 'value': 10.0},
                'downstream': {'type': 'depth', 'value': 2.0}
            },
            'simulation': {
                'mode': 'steady'
            },
            'output': {
                'directory': 'results',
                'verbose': True
            }
        }

        config_file = tmp_path / 'test_config.yaml'
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)

        return str(config_file)

    def test_load_config(self, sample_config_file):
        """测试配置加载"""
        config = ModelConfig(sample_config_file)
        assert config.config is not None
        assert 'canal' in config.config
        assert 'simulation' in config.config

    def test_get_canal_params(self, sample_config_file):
        """测试获取渠道参数"""
        config = ModelConfig(sample_config_file)
        canal_params = config.get_canal_params()

        assert canal_params['length'] == 1000.0
        assert canal_params['B'] == 10.0
        assert canal_params['S0'] == 0.001
        assert canal_params['n'] == 0.025
        assert canal_params['h0'] == 2.0

    def test_get_grid_config(self, sample_config_file):
        """测试获取网格配置"""
        config = ModelConfig(sample_config_file)
        grid_config = config.get_grid_config()

        assert grid_config['nx'] == 101
        assert grid_config['adaptive'] == False

    def test_get_boundary_conditions(self, sample_config_file):
        """测试获取边界条件"""
        config = ModelConfig(sample_config_file)
        boundary = config.get_boundary_conditions()

        assert boundary['upstream']['type'] == 'flow'
        assert boundary['upstream']['value'] == 10.0
        assert boundary['downstream']['type'] == 'depth'
        assert boundary['downstream']['value'] == 2.0

    def test_get_simulation_config(self, sample_config_file):
        """测试获取仿真配置"""
        config = ModelConfig(sample_config_file)
        sim_config = config.get_simulation_config()

        assert sim_config['mode'] == 'steady'

    def test_get_output_config(self, sample_config_file):
        """测试获取输出配置"""
        config = ModelConfig(sample_config_file)
        output_config = config.get_output_config()

        assert 'directory' in output_config
        assert output_config['verbose'] == True

    def test_get_with_dot_notation(self, sample_config_file):
        """测试点号分隔键访问"""
        config = ModelConfig(sample_config_file)

        # 测试嵌套访问
        name = config.get('project.name')
        assert name == 'Test Project'

        length = config.get('canal.length')
        assert length == 1000.0

    def test_get_with_default(self, sample_config_file):
        """测试默认值"""
        config = ModelConfig(sample_config_file)

        # 不存在的键应返回默认值
        value = config.get('nonexistent.key', default=42)
        assert value == 42

    def test_missing_required_section(self, tmp_path):
        """测试缺少必需节的配置"""
        # 创建不完整的配置
        incomplete_config = {
            'canal': {
                'length': 1000.0,
                'width': 10.0,
                'slope': 0.001,
                'manning_n': 0.025
            }
            # 缺少simulation节
        }

        config_file = tmp_path / 'incomplete.yaml'
        with open(config_file, 'w') as f:
            yaml.dump(incomplete_config, f)

        # 应该抛出异常
        with pytest.raises(ValueError, match="缺少必需的节"):
            ModelConfig(str(config_file))

    def test_missing_canal_parameter(self, tmp_path):
        """测试缺少渠道参数"""
        # 缺少manning_n
        incomplete_canal = {
            'canal': {
                'length': 1000.0,
                'width': 10.0,
                'slope': 0.001
                # 缺少manning_n
            },
            'simulation': {
                'mode': 'steady'
            }
        }

        config_file = tmp_path / 'incomplete_canal.yaml'
        with open(config_file, 'w') as f:
            yaml.dump(incomplete_canal, f)

        # 应该抛出异常
        with pytest.raises(ValueError, match="渠道参数缺少"):
            ModelConfig(str(config_file))
