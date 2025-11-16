#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
配置文件解析器 (Config Parser)

功能:
1. 读取JSON配置文件
2. 验证配置格式
3. 填充默认值
4. 错误检查

Author: HydroClaude Development Team
Date: 2025-11-15
"""

import json
import os
from typing import Dict, Any, List, Optional
import numpy as np
from jsonschema import validate, ValidationError
import sys

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.canal_utils import compute_steady_uniform_flow


class ConfigParser:
    """配置文件解析器"""
    
    # 配置文件Schema定义（简化版，实际使用时可以更详细）
    SCHEMA = {
        "type": "object",
        "required": ["simulation", "canal", "solver"],
        "properties": {
            "metadata": {"type": "object"},
            "simulation": {
                "type": "object",
                "required": ["type", "mode"],
                "properties": {
                    "type": {"type": "string", "enum": ["steady", "unsteady"]},
                    "mode": {"type": "string", "enum": ["single_canal", "network", "coupled"]}
                }
            },
            "canal": {
                "type": "object",
                "required": ["length", "width", "slope", "manning_n"]
            },
            "solver": {
                "type": "object",
                "required": ["method"]
            }
        }
    }
    
    # 默认值
    DEFAULTS = {
        "metadata": {
            "title": "Untitled Simulation",
            "description": "",
            "author": "Unknown",
            "version": "1.0"
        },
        "canal": {
            "grid": {
                "nx": 201,
                "type": "uniform"
            }
        },
        "solver": {
            "parameters": {
                "max_iterations": 5000,
                "convergence_tol": 0.1,
                "cfl": 0.5,
                "theta": 0.6,
                "dt": 0.5
            }
        },
        "output": {
            "directory": "results/default",
            "formats": ["json", "csv"],
            "variables": ["depth", "flow", "velocity", "elevation"],
            "plots": {
                "enabled": True,
                "types": ["profile"]
            }
        }
    }
    
    def __init__(self, verbose: bool = False):
        """
        初始化配置解析器
        
        Args:
            verbose: 是否输出详细信息
        """
        self.verbose = verbose
        self.config = None
        self.config_file = None
        
    def parse(self, config_file: str) -> Dict[str, Any]:
        """
        解析配置文件
        
        Args:
            config_file: 配置文件路径
            
        Returns:
            解析后的配置字典
            
        Raises:
            FileNotFoundError: 配置文件不存在
            ValidationError: 配置验证失败
            json.JSONDecodeError: JSON格式错误
        """
        self.config_file = config_file
        
        if self.verbose:
            print(f"正在读取配置文件: {config_file}")
        
        # 1. 读取文件
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"配置文件不存在: {config_file}")
        
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 2. 验证格式
        if self.verbose:
            print("验证配置格式...")
        
        try:
            validate(instance=config, schema=self.SCHEMA)
        except ValidationError as e:
            raise ValidationError(f"配置验证失败: {e.message}")
        
        # 3. 填充默认值
        if self.verbose:
            print("填充默认值...")
        
        config = self._fill_defaults(config)
        
        # 4. 预处理和计算派生值
        if self.verbose:
            print("计算派生参数...")
        
        config = self._preprocess(config)
        
        # 5. 最终验证
        if self.verbose:
            print("执行最终验证...")
        
        self._validate_final(config)
        
        self.config = config
        
        if self.verbose:
            print("✅ 配置解析成功")
        
        return config
    
    def _fill_defaults(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """填充默认值"""
        
        # 深度合并默认值
        def deep_merge(base: dict, override: dict) -> dict:
            """深度合并字典"""
            result = base.copy()
            for key, value in override.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = deep_merge(result[key], value)
                else:
                    result[key] = value
            return result
        
        return deep_merge(self.DEFAULTS, config)
    
    def _preprocess(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        预处理配置，计算派生值
        
        例如:
        - 计算均匀流水深
        - 处理时间序列
        - 设置初始条件
        """
        
        # 计算均匀流水深（如果需要）
        canal = config['canal']
        bc = config.get('boundary_conditions', {})
        
        # 如果上游边界是流量，计算对应的均匀流水深
        if bc.get('upstream', {}).get('type') == 'flow':
            Q = bc['upstream']['value']
            B = canal['width']
            S0 = canal['slope'] if isinstance(canal['slope'], (int, float)) else np.mean(canal['slope'])
            n = canal['manning_n']
            
            h_uniform = compute_steady_uniform_flow(Q, B, S0, n)
            config['_computed'] = config.get('_computed', {})
            config['_computed']['uniform_depth'] = h_uniform
            
            # 如果下游边界要求uniform_flow，设置水深
            if bc.get('downstream', {}).get('method') == 'uniform_flow':
                config['boundary_conditions']['downstream']['value'] = h_uniform
        
        # 处理初始条件
        initial = config.get('initial_conditions', {})
        if initial.get('depth') == 'uniform_flow':
            if '_computed' in config and 'uniform_depth' in config['_computed']:
                config['initial_conditions']['_depth_value'] = config['_computed']['uniform_depth']
        
        # 处理斜率（转换为数组）
        if isinstance(canal['slope'], (int, float)):
            nx = canal['grid']['nx']
            config['canal']['_slope_array'] = np.ones(nx - 1) * canal['slope']
        else:
            config['canal']['_slope_array'] = np.array(canal['slope'])
        
        # 创建输出目录
        output_dir = config['output']['directory']
        os.makedirs(output_dir, exist_ok=True)
        config['output']['_absolute_path'] = os.path.abspath(output_dir)
        
        return config
    
    def _validate_final(self, config: Dict[str, Any]):
        """
        最终验证
        
        检查:
        - 参数范围合理性
        - 边界条件完整性
        - 结构位置合法性
        """
        
        # 检查渠道参数
        canal = config['canal']
        if canal['length'] <= 0:
            raise ValueError("渠道长度必须 > 0")
        if canal['width'] <= 0:
            raise ValueError("渠道宽度必须 > 0")
        if canal['manning_n'] <= 0:
            raise ValueError("Manning糙率必须 > 0")
        
        # 检查网格数
        nx = canal['grid']['nx']
        if nx < 3:
            raise ValueError("网格数必须 >= 3")
        
        # 检查结构位置
        structures = config.get('structures', [])
        for struct in structures:
            pos = struct['position']
            if pos < 0 or pos > canal['length']:
                raise ValueError(f"结构位置 {pos} 超出渠道范围 [0, {canal['length']}]")
        
        # 检查求解器参数
        solver = config['solver']
        method = solver['method']
        valid_methods = ['hydrostatic', 'godunov', 'preissmann']
        if method not in valid_methods:
            raise ValueError(f"未知的求解器方法: {method}. 有效值: {valid_methods}")
        
        # 检查时间参数（非恒定流）
        if config['simulation']['type'] == 'unsteady':
            if 'time' not in config['simulation']:
                raise ValueError("非恒定流仿真必须指定时间参数")
            
            time_params = config['simulation']['time']
            if time_params['end'] <= time_params['start']:
                raise ValueError("结束时间必须大于开始时间")
            if time_params['dt'] <= 0:
                raise ValueError("时间步长必须 > 0")
        
        if self.verbose:
            print("✅ 所有验证检查通过")
    
    def save_processed_config(self, output_file: str):
        """
        保存处理后的配置（用于调试和记录）
        
        Args:
            output_file: 输出文件路径
        """
        if self.config is None:
            raise RuntimeError("尚未解析任何配置")
        
        # 移除numpy数组（不能直接序列化为JSON）
        config_copy = self.config.copy()
        if '_slope_array' in config_copy.get('canal', {}):
            config_copy['canal']['_slope_array'] = config_copy['canal']['_slope_array'].tolist()
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(config_copy, f, indent=2, ensure_ascii=False)
        
        if self.verbose:
            print(f"处理后的配置已保存: {output_file}")
    
    def print_summary(self):
        """打印配置摘要"""
        if self.config is None:
            raise RuntimeError("尚未解析任何配置")
        
        config = self.config
        
        print("\n" + "=" * 80)
        print("配置摘要")
        print("=" * 80)
        
        # 元数据
        meta = config['metadata']
        print(f"\n【基本信息】")
        print(f"  标题: {meta['title']}")
        print(f"  描述: {meta['description']}")
        print(f"  作者: {meta['author']}")
        
        # 仿真类型
        sim = config['simulation']
        print(f"\n【仿真设置】")
        print(f"  类型: {sim['type']}")
        print(f"  模式: {sim['mode']}")
        
        if sim['type'] == 'unsteady':
            time = sim['time']
            print(f"  时间: {time['start']} - {time['end']} s (dt={time['dt']} s)")
        
        # 渠道参数
        canal = config['canal']
        print(f"\n【渠道参数】")
        print(f"  长度: {canal['length']} m")
        print(f"  宽度: {canal['width']} m")
        print(f"  坡度: {canal['slope']}")
        print(f"  Manning糙率: {canal['manning_n']}")
        print(f"  网格数: {canal['grid']['nx']}")
        
        # 边界条件
        if 'boundary_conditions' in config:
            bc = config['boundary_conditions']
            print(f"\n【边界条件】")
            if 'upstream' in bc:
                up = bc['upstream']
                print(f"  上游: {up['type']} = {up.get('value', 'computed')}")
            if 'downstream' in bc:
                down = bc['downstream']
                print(f"  下游: {down['type']} = {down.get('value', 'computed')}")
        
        # 水工结构
        structures = config.get('structures', [])
        if structures:
            print(f"\n【水工结构】({len(structures)}个)")
            for i, struct in enumerate(structures, 1):
                print(f"  {i}. {struct['type']} @ {struct['position']} m")
        
        # 求解器
        solver = config['solver']
        print(f"\n【求解器】")
        print(f"  方法: {solver['method']}")
        params = solver['parameters']
        if 'max_iterations' in params:
            print(f"  最大迭代: {params['max_iterations']}")
        if 'convergence_tol' in params:
            print(f"  收敛容差: {params['convergence_tol']}")
        
        # 输出
        output = config['output']
        print(f"\n【输出设置】")
        print(f"  目录: {output['directory']}")
        print(f"  格式: {', '.join(output['formats'])}")
        print(f"  变量: {', '.join(output['variables'])}")
        print(f"  绘图: {'是' if output['plots']['enabled'] else '否'}")
        
        print("\n" + "=" * 80)


def main():
    """测试配置解析器"""
    import argparse
    
    parser = argparse.ArgumentParser(description='测试配置解析器')
    parser.add_argument('config', type=str, help='配置文件路径')
    parser.add_argument('-v', '--verbose', action='store_true', help='详细输出')
    parser.add_argument('-o', '--output', type=str, help='保存处理后的配置')
    
    args = parser.parse_args()
    
    # 解析配置
    config_parser = ConfigParser(verbose=args.verbose)
    config = config_parser.parse(args.config)
    
    # 打印摘要
    config_parser.print_summary()
    
    # 保存处理后的配置
    if args.output:
        config_parser.save_processed_config(args.output)


if __name__ == '__main__':
    main()
