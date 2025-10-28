#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
配置文件解析器

负责读取、验证和解析JSON配置文件

作者: HydroClaude Team
日期: 2025-10-28
"""

import json
import os
from typing import Dict, Any, Optional, List
from pathlib import Path


class ConfigValidationError(Exception):
    """配置验证错误"""
    pass


class ConfigParser:
    """
    配置文件解析器

    功能：
    1. 读取JSON配置文件
    2. 验证配置完整性和一致性
    3. 提供默认值
    4. 返回标准化配置字典
    """

    # 必需字段定义
    REQUIRED_FIELDS = {
        'project': ['name'],
        'geometry': ['type'],
        'mesh': ['n_cells'],
        'solver': ['type'],
        'initial_conditions': ['type'],
        'boundary_conditions': ['left', 'right'],
        'simulation': ['end_time']
    }

    # 默认值
    DEFAULTS = {
        'geometry': {
            'channel_width': 10.0,
            'channel_length': 1000.0,
            'bottom_slope': 0.0,
            'manning_n': 0.025,
            'cross_sections': None
        },
        'mesh': {
            'cell_distribution': 'uniform',
            'refinement_regions': []
        },
        'solver': {
            'type': 'godunov_fvm',
            'spatial_order': 2,
            'time_integration': 'tvd_rk2',
            'riemann_solver': 'hll',
            'use_numba': True,
            'well_balanced': False,
            'cfl': 0.5,
            'eps_dry': 1e-6
        },
        'simulation': {
            'start_time': 0.0,
            'max_steps': 10000000,
            'output_interval': 1.0,
            'checkpoint_interval': 10.0
        },
        'output': {
            'directory': './results',
            'formats': ['csv'],
            'variables': ['h', 'Q', 'u'],
            'statistics': True,
            'plots': {
                'enabled': True,
                'format': 'png',
                'dpi': 300
            }
        },
        'validation': {
            'enabled': False,
            'analytical_solution': None,
            'tolerance': {
                'h_rmse': 0.5,
                'Q_rmse': 10.0,
                'mass_error': 0.1
            }
        },
        'logging': {
            'level': 'INFO',
            'file': './logs/simulation.log',
            'console': True
        }
    }

    def __init__(self, config_file: str):
        """
        初始化配置解析器

        Args:
            config_file: 配置文件路径
        """
        self.config_file = Path(config_file)
        if not self.config_file.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_file}")

        self.config = None
        self.errors = []
        self.warnings = []

    def parse(self) -> Dict[str, Any]:
        """
        解析配置文件

        Returns:
            标准化的配置字典

        Raises:
            ConfigValidationError: 配置验证失败
        """
        # 1. 读取JSON
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        except json.JSONDecodeError as e:
            raise ConfigValidationError(f"JSON格式错误: {e}")

        # 2. 验证必需字段
        self._validate_required_fields()

        # 3. 应用默认值
        self._apply_defaults()

        # 4. 验证数据类型和范围
        self._validate_types_and_ranges()

        # 5. 验证一致性
        self._validate_consistency()

        # 6. 检查文件路径
        self._check_file_paths()

        # 如果有错误，抛出异常
        if self.errors:
            error_msg = "\n".join(self.errors)
            raise ConfigValidationError(f"配置验证失败:\n{error_msg}")

        # 打印警告
        if self.warnings:
            print("⚠️  配置警告:")
            for warning in self.warnings:
                print(f"  - {warning}")

        return self.config

    def _validate_required_fields(self):
        """验证必需字段"""
        for section, fields in self.REQUIRED_FIELDS.items():
            if section not in self.config:
                self.errors.append(f"缺少必需section: {section}")
                continue

            for field in fields:
                if field not in self.config[section]:
                    self.errors.append(f"缺少必需字段: {section}.{field}")

    def _apply_defaults(self):
        """应用默认值"""
        for section, defaults in self.DEFAULTS.items():
            if section not in self.config:
                self.config[section] = {}

            for key, default_value in defaults.items():
                if key not in self.config[section]:
                    self.config[section][key] = default_value
                    if isinstance(default_value, dict):
                        # 递归应用嵌套默认值
                        for subkey, subvalue in default_value.items():
                            if subkey not in self.config[section][key]:
                                self.config[section][key][subkey] = subvalue

    def _validate_types_and_ranges(self):
        """验证数据类型和范围"""
        # 网格数必须为正整数
        if 'mesh' in self.config and 'n_cells' in self.config['mesh']:
            n_cells = self.config['mesh']['n_cells']
            if not isinstance(n_cells, int) or n_cells <= 0:
                self.errors.append("mesh.n_cells必须为正整数")

        # CFL必须在(0, 1]范围内
        if 'solver' in self.config and 'cfl' in self.config['solver']:
            cfl = self.config['solver']['cfl']
            if not isinstance(cfl, (int, float)) or cfl <= 0 or cfl > 1.0:
                self.errors.append("solver.cfl必须在(0, 1]范围内")

        # 时间参数
        if 'simulation' in self.config:
            sim = self.config['simulation']
            if 'end_time' in sim and 'start_time' in sim:
                if sim['end_time'] <= sim['start_time']:
                    self.errors.append("simulation.end_time必须大于start_time")

        # Riemann求解器类型
        if 'solver' in self.config and 'riemann_solver' in self.config['solver']:
            valid_solvers = ['hll', 'hllc']
            if self.config['solver']['riemann_solver'] not in valid_solvers:
                self.errors.append(f"solver.riemann_solver必须是{valid_solvers}之一")

        # 几何类型
        if 'geometry' in self.config and 'type' in self.config['geometry']:
            valid_geom_types = ['uniform', 'variable', 'from_file']
            if self.config['geometry']['type'] not in valid_geom_types:
                self.errors.append(f"geometry.type必须是{valid_geom_types}之一")

    def _validate_consistency(self):
        """验证配置一致性"""
        # 如果几何类型是from_file，必须提供cross_sections
        if 'geometry' in self.config and 'type' in self.config['geometry']:
            if self.config['geometry']['type'] == 'from_file':
                if not self.config['geometry'].get('cross_sections'):
                    self.errors.append("geometry.type='from_file'时必须提供cross_sections路径")

        # 如果启用验证，必须指定解析解类型
        if 'validation' in self.config and 'enabled' in self.config['validation']:
            if self.config['validation']['enabled']:
                if not self.config['validation'].get('analytical_solution'):
                    self.warnings.append("validation.enabled=true但未指定analytical_solution")

        # 输出间隔不应大于模拟时间
        if 'simulation' in self.config:
            sim = self.config['simulation']
            if all(k in sim for k in ['output_interval', 'end_time', 'start_time']):
                if sim['output_interval'] > (sim['end_time'] - sim['start_time']):
                    self.warnings.append("output_interval大于模拟时长，可能只有一个输出")

    def _check_file_paths(self):
        """检查文件路径是否存在"""
        # 断面文件
        if 'geometry' in self.config and 'type' in self.config['geometry']:
            if self.config['geometry']['type'] == 'from_file':
                path = self.config['geometry'].get('cross_sections')
                if path and not Path(path).exists():
                    self.errors.append(f"断面文件不存在: {path}")

        # 初始条件文件
        if 'initial_conditions' in self.config and 'type' in self.config['initial_conditions']:
            if self.config['initial_conditions']['type'] == 'from_file':
                path = self.config['initial_conditions'].get('file')
                if path and not Path(path).exists():
                    self.errors.append(f"初始条件文件不存在: {path}")

    def get_project_info(self) -> Dict[str, str]:
        """获取项目信息"""
        if not self.config:
            raise RuntimeError("请先调用parse()方法")
        return self.config['project']

    def get_solver_config(self) -> Dict[str, Any]:
        """获取求解器配置"""
        if not self.config:
            raise RuntimeError("请先调用parse()方法")
        return self.config['solver']

    def get_simulation_config(self) -> Dict[str, Any]:
        """获取模拟配置"""
        if not self.config:
            raise RuntimeError("请先调用parse()方法")
        return self.config['simulation']

    def summary(self) -> str:
        """生成配置摘要"""
        if not self.config:
            return "配置尚未解析"

        lines = []
        lines.append("=" * 80)
        lines.append("配置文件摘要")
        lines.append("=" * 80)

        # 项目信息
        proj = self.config['project']
        lines.append(f"\n项目: {proj['name']}")
        if 'description' in proj:
            lines.append(f"描述: {proj['description']}")

        # 几何
        geom = self.config['geometry']
        lines.append(f"\n几何:")
        lines.append(f"  类型: {geom['type']}")
        if geom['type'] == 'uniform':
            lines.append(f"  渠宽: {geom['channel_width']} m")
            lines.append(f"  渠长: {geom['channel_length']} m")
            lines.append(f"  坡度: {geom['bottom_slope']}")
        lines.append(f"  Manning系数: {geom['manning_n']}")

        # 网格
        mesh = self.config['mesh']
        lines.append(f"\n网格:")
        lines.append(f"  单元数: {mesh['n_cells']}")
        if geom['type'] == 'uniform':
            dx = geom['channel_length'] / mesh['n_cells']
            lines.append(f"  dx: {dx:.3f} m")

        # 求解器
        solver = self.config['solver']
        lines.append(f"\n求解器:")
        lines.append(f"  类型: {solver['type']}")
        lines.append(f"  Riemann求解器: {solver['riemann_solver'].upper()}")
        lines.append(f"  空间精度: {solver['spatial_order']}阶")
        lines.append(f"  CFL: {solver['cfl']}")
        lines.append(f"  Numba加速: {'启用' if solver['use_numba'] else '禁用'}")

        # 初始条件
        ic = self.config['initial_conditions']
        lines.append(f"\n初始条件:")
        lines.append(f"  类型: {ic['type']}")
        if ic['type'] == 'dam_break':
            lines.append(f"  左侧水深: {ic.get('h_left', 'N/A')} m")
            lines.append(f"  右侧水深: {ic.get('h_right', 'N/A')} m")

        # 模拟
        sim = self.config['simulation']
        lines.append(f"\n模拟:")
        lines.append(f"  开始时间: {sim['start_time']} s")
        lines.append(f"  结束时间: {sim['end_time']} s")
        lines.append(f"  输出间隔: {sim['output_interval']} s")

        # 输出
        out = self.config['output']
        lines.append(f"\n输出:")
        lines.append(f"  目录: {out['directory']}")
        lines.append(f"  格式: {', '.join(out['formats'])}")
        lines.append(f"  变量: {', '.join(out['variables'])}")

        lines.append("\n" + "=" * 80)

        return "\n".join(lines)


if __name__ == '__main__':
    # 测试配置解析器
    print("配置解析器测试\n")

    # 创建测试配置文件
    test_config = {
        "project": {
            "name": "测试模拟",
            "description": "配置解析器测试"
        },
        "geometry": {
            "type": "uniform",
            "channel_width": 10.0,
            "channel_length": 1000.0,
            "bottom_slope": 0.001
        },
        "mesh": {
            "n_cells": 100
        },
        "solver": {
            "riemann_solver": "hll"
        },
        "initial_conditions": {
            "type": "uniform",
            "h": 2.0,
            "Q": 20.0
        },
        "boundary_conditions": {
            "left": {"type": "Q", "value": 20.0},
            "right": {"type": "h", "value": 2.0}
        },
        "simulation": {
            "end_time": 100.0
        }
    }

    # 保存测试配置
    test_file = '/tmp/test_config.json'
    with open(test_file, 'w') as f:
        json.dump(test_config, f, indent=2)

    # 解析
    try:
        parser = ConfigParser(test_file)
        config = parser.parse()
        print(parser.summary())
        print("\n✅ 配置解析成功！")
    except ConfigValidationError as e:
        print(f"\n❌ 配置验证失败:\n{e}")
