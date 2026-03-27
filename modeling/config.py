#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
配置文件管理模块

支持YAML格式配置文件的加载、验证和管理

作者: Claude
日期: 2025-10-24
"""

import yaml
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
import numpy as np


class ModelConfig:
    """
    模型配置管理器

    支持从YAML文件加载配置，包括：
    - 渠道参数
    - 结构物配置
    - 网格设置
    - 算法参数
    - 边界条件
    - 输出设置
    """

    def __init__(self, config_file: Optional[str] = None):
        """
        初始化配置管理器

        Args:
            config_file: 配置文件路径（YAML格式）
        """
        self.config_file = config_file
        self.config = {}

        if config_file:
            self.load(config_file)

    def load(self, config_file: str):
        """
        从YAML文件加载配置

        Args:
            config_file: YAML配置文件路径
        """
        config_path = Path(config_file)

        if not config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_file}")

        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

        self.config_file = str(config_path)

        # 验证配置
        self._validate()

        # 处理相对路径
        self._process_paths()

    def _validate(self):
        """验证配置文件的完整性"""
        required_sections = ['canal', 'simulation']

        for section in required_sections:
            if section not in self.config:
                raise ValueError(f"配置文件缺少必需的节: {section}")

        # 验证渠道参数
        canal = self.config['canal']
        required_canal_params = ['length', 'width', 'slope', 'manning_n']
        for param in required_canal_params:
            if param not in canal:
                raise ValueError(f"渠道参数缺少: {param}")

    def _process_paths(self):
        """处理配置中的相对路径"""
        if self.config_file:
            config_dir = Path(self.config_file).parent

            # 处理输出路径
            if 'output' in self.config and 'directory' in self.config['output']:
                output_dir = self.config['output']['directory']
                if not Path(output_dir).is_absolute():
                    self.config['output']['directory'] = str(config_dir / output_dir)

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值（支持点号分隔的嵌套键）

        Args:
            key: 配置键（如 'canal.length' 或 'simulation.dt'）
            default: 默认值

        Returns:
            配置值
        """
        keys = key.split('.')
        value = self.config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value: Any):
        """
        设置配置值（支持点号分隔的嵌套键）

        Args:
            key: 配置键
            value: 配置值
        """
        keys = key.split('.')
        config = self.config

        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value

    def get_canal_params(self) -> Dict[str, float]:
        """获取渠道参数"""
        canal = self.config['canal']
        return {
            'length': float(canal['length']),
            'B': float(canal['width']),
            'S0': float(canal['slope']),
            'n': float(canal['manning_n']),
            'g': float(canal.get('gravity', 9.81))
        }

    def get_structures(self) -> List[Dict]:
        """获取结构物配置"""
        return self.config.get('structures', [])

    def get_grid_config(self) -> Dict:
        """获取网格配置"""
        grid = self.config.get('grid', {})
        return {
            'nx': grid.get('nx', None),
            'dx_target': grid.get('dx_target', None),
            'adaptive': grid.get('adaptive', False),
            'refine_threshold': grid.get('refine_threshold', 0.1),
            'coarsen_threshold': grid.get('coarsen_threshold', 0.01)
        }

    def get_simulation_config(self) -> Dict:
        """获取仿真配置"""
        sim = self.config['simulation']
        # 返回所有simulation配置，不只是固定字段
        result = {
            'type': sim.get('type', 'steady'),
            'dt': sim.get('dt', 0.5),
            'total_time': sim.get('total_time', 3600),
            'save_interval': sim.get('save_interval', 60),
            'convergence_tol': sim.get('convergence_tol', 0.001),
            'max_iterations': sim.get('max_iterations', 5000)
        }
        # 添加其他可选配置（如control, time_varying_bc, preissmann_max_iter等）
        for key in sim:
            if key not in result:
                result[key] = sim[key]
        return result

    def get_boundary_conditions(self) -> Dict:
        """获取边界条件"""
        bc = self.config.get('boundary_conditions', {})
        
        # 支持嵌套格式 (upstream: {type, value}) 和 扁平格式 (upstream_type, upstream_value)
        upstream = bc.get('upstream', {})
        downstream = bc.get('downstream', {})
        
        if isinstance(upstream, dict):
            u_type = upstream.get('type', bc.get('upstream_type', 'flow'))
            u_val = upstream.get('value', bc.get('upstream_value', 10.0))
        else:
            u_type = bc.get('upstream_type', 'flow')
            u_val = bc.get('upstream_value', 10.0)
            
        if isinstance(downstream, dict):
            d_type = downstream.get('type', bc.get('downstream_type', 'depth'))
            d_val = downstream.get('value', bc.get('downstream_value', 2.0))
        else:
            d_type = bc.get('downstream_type', 'depth')
            d_val = bc.get('downstream_value', 2.0)
            
        return {
            'upstream_type': u_type,
            'upstream_value': float(u_val),
            'downstream_type': d_type,
            'downstream_value': float(d_val)
        }

    def get_output_config(self) -> Dict:
        """获取输出配置"""
        output = self.config.get('output', {})
        return {
            'directory': output.get('directory', './results'),
            'prefix': output.get('prefix', 'model'),
            'formats': output.get('formats', ['png', 'npz']),
            'create_animation': output.get('create_animation', False),
            'validation_report': output.get('validation_report', True)
        }

    def save(self, output_file: str):
        """
        保存配置到文件

        Args:
            output_file: 输出文件路径
        """
        with open(output_file, 'w', encoding='utf-8') as f:
            yaml.dump(self.config, f, default_flow_style=False, allow_unicode=True)

    def __repr__(self) -> str:
        return f"ModelConfig(file='{self.config_file}')"


def create_template_config(output_file: str):
    """
    创建模板配置文件

    Args:
        output_file: 输出文件路径
    """
    template = {
        'canal': {
            'length': 10000.0,
            'width': 10.0,
            'slope': 0.0001,
            'manning_n': 0.025,
            'gravity': 9.81
        },
        'structures': [
            {
                'type': 'sluice_gate',
                'position': 5000.0,
                'width': 10.0,
                'opening': 2.0,
                'Cd': 0.6
            }
        ],
        'grid': {
            'nx': None,  # 自动计算
            'dx_target': 50.0,  # 目标网格间距 (m)
            'adaptive': True,  # 启用自适应网格
            'refine_threshold': 0.1,  # 细化阈值
            'coarsen_threshold': 0.01  # 粗化阈值
        },
        'simulation': {
            'type': 'steady',  # steady 或 unsteady
            'dt': 0.5,  # 时间步长 (s)
            'total_time': 3600,  # 总模拟时间 (s)
            'save_interval': 60,  # 保存间隔 (s)
            'convergence_tol': 0.001,  # 收敛容差
            'max_iterations': 5000  # 最大迭代次数
        },
        'boundary_conditions': {
            'upstream_type': 'flow',  # flow 或 depth
            'upstream_value': 10.0,  # m³/s 或 m
            'downstream_type': 'depth',  # flow 或 depth
            'downstream_value': 2.0  # m³/s 或 m
        },
        'output': {
            'directory': './results',
            'prefix': 'model',
            'formats': ['png', 'npz'],
            'create_animation': False,
            'validation_report': True
        },
        'algorithm': {
            'auto_select': True,  # 自动选择最优算法
            'steady_solver': 'preissmann',  # preissmann 或 explicit
            'unsteady_solver': 'preissmann',
            'theta': 0.6,  # Preissmann权重因子
            'omega': 0.95  # 松弛因子
        }
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        yaml.dump(template, f, default_flow_style=False, allow_unicode=True)

    print(f" 模板配置文件已创建: {output_file}")


if __name__ == "__main__":
    # 测试：创建模板配置
    create_template_config("model_config_template.yaml")

    # 测试：加载配置
    config = ModelConfig("model_config_template.yaml")
    print(config)
    print(f"渠道长度: {config.get('canal.length')} m")
    print(f"仿真类型: {config.get('simulation.type')}")
