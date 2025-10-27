#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
情景分析管理器

快速运行多个情景并对比结果。

核心功能：
1. 批量运行情景
2. 自动对比分析
3. 生成对比图表
4. 生成分析报告

使用示例：
    >>> from scenarios import ScenarioManager
    >>> 
    >>> scenarios = {
    ...     "基准情景": {},
    ...     "增加泵站扬程": {"pump_head": 6.0},
    ...     "关小闸门": {"gate_opening": 2.5},
    ... }
    >>> 
    >>> manager = ScenarioManager("config/base.yaml")
    >>> results = manager.run_scenarios(scenarios)
    >>> manager.compare_results(results)

Author: Claude (AI Assistant)
Date: 2025-10-27
"""

import sys
import os
from typing import Dict, List, Any
import yaml
import copy

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import HydraulicModelConfig


class ScenarioManager:
    """
    情景分析管理器
    
    管理和运行多个模拟情景。
    
    使用示例：
        >>> manager = ScenarioManager("config/base.yaml")
        >>> 
        >>> scenarios = {
        ...     "基准": {},
        ...     "高水": {"downstream_depth": 3.0},
        ...     "大流量": {"upstream_flow": 15.0},
        ... }
        >>> 
        >>> results = manager.run_scenarios(scenarios)
        >>> manager.generate_comparison_report(results, "report.md")
    """
    
    def __init__(self, base_config_file: str):
        """
        初始化情景管理器
        
        Args:
            base_config_file: 基准配置文件路径
        """
        self.base_config_file = base_config_file
        
        # 加载基准配置
        with open(base_config_file, 'r', encoding='utf-8') as f:
            self.base_config = yaml.safe_load(f)
    
    def create_scenario_config(self, 
                              scenario_params: Dict[str, Any]) -> Dict:
        """
        创建情景配置
        
        基于基准配置修改参数。
        
        Args:
            scenario_params: 情景参数修改
                例如: {"pump_head": 6.0, "gate_opening": 2.5}
        
        Returns:
            config: 修改后的完整配置
        """
        # 深拷贝基准配置
        config = copy.deepcopy(self.base_config)
        
        # 应用修改
        for key, value in scenario_params.items():
            # 支持的修改类型
            if key == 'upstream_flow':
                config['boundary']['upstream']['value'] = value
            
            elif key == 'downstream_depth':
                config['boundary']['downstream']['value'] = value
            
            elif key == 'pump_head':
                # 修改第一个泵站
                for struct in config.get('structures', []):
                    if struct['type'] == 'pump':
                        struct['rated_head'] = value
                        break
            
            elif key == 'gate_opening':
                # 修改第一个闸门
                for struct in config.get('structures', []):
                    if struct['type'] == 'gate':
                        struct['opening'] = value
                        break
            
            else:
                print(f"⚠️  未知参数: {key}")
        
        return config
    
    def run_scenarios(self, 
                     scenarios: Dict[str, Dict],
                     verbose: bool = False) -> Dict[str, Dict]:
        """
        运行多个情景
        
        Args:
            scenarios: 情景字典
                格式: {"情景名": {参数修改}, ...}
            verbose: 详细输出
        
        Returns:
            results: 各情景的结果
                格式: {"情景名": result, ...}
        """
        print("="*70)
        print("批量情景分析")
        print("="*70)
        print(f"基准配置: {self.base_config_file}")
        print(f"情景数量: {len(scenarios)}")
        print("")
        
        results = {}
        
        for i, (scenario_name, scenario_params) in enumerate(scenarios.items(), 1):
            print(f"\n{'='*70}")
            print(f"运行情景 {i}/{len(scenarios)}: {scenario_name}")
            print(f"{'='*70}")
            print(f"参数修改: {scenario_params}")
            
            # 创建临时配置
            scenario_config = self.create_scenario_config(scenario_params)
            
            # 保存临时配置文件
            temp_config_file = f"config/.temp_scenario_{i}.yaml"
            with open(temp_config_file, 'w', encoding='utf-8') as f:
                yaml.dump(scenario_config, f, allow_unicode=True)
            
            try:
                # 运行模拟
                config = HydraulicModelConfig(temp_config_file)
                result = config.run_simulation(verbose=verbose)
                
                # 保存结果
                results[scenario_name] = result
                
                # 打印关键指标
                if 'error' in result:
                    print(f"✓ 流量误差: {result['error']:.4f}%")
                if 'conservation_error' in result:
                    print(f"✓ 质量守恒: {result['conservation_error']:.2e}")
            
            except Exception as e:
                print(f"✗ 失败: {e}")
                results[scenario_name] = {'error': str(e), 'failed': True}
            
            finally:
                # 删除临时文件
                if os.path.exists(temp_config_file):
                    os.remove(temp_config_file)
        
        print("\n" + "="*70)
        print("批量情景分析完成")
        print("="*70)
        print(f"成功: {sum(1 for r in results.values() if not r.get('failed', False))}/{len(scenarios)}")
        
        return results
    
    def compare_results(self, 
                       results: Dict[str, Dict],
                       save_path: Optional[str] = None):
        """
        对比分析结果
        
        Args:
            results: 各情景结果
            save_path: 保存路径（可选）
        """
        print("\n" + "="*70)
        print("情景对比分析")
        print("="*70)
        
        # 表头
        print(f"\n{'情景名':<20} {'流量误差(%)':<15} {'质量守恒':<15} {'迭代次数':<10}")
        print("-"*70)
        
        # 各情景
        for name, result in results.items():
            if result.get('failed', False):
                print(f"{name:<20} {'失败':<15}")
                continue
            
            error = result.get('error', 0)
            conservation = result.get('conservation_error', 0)
            iterations = result.get('iterations', 0)
            
            print(f"{name:<20} {error:<15.4f} {conservation:<15.2e} {iterations:<10}")
        
        print("="*70)
        
        # 生成对比报告（如果指定）
        if save_path:
            self.generate_comparison_report(results, save_path)
    
    def generate_comparison_report(self,
                                  results: Dict[str, Dict],
                                  report_path: str):
        """
        生成对比分析报告
        
        Args:
            results: 各情景结果
            report_path: 报告保存路径
        """
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# 情景对比分析报告\n\n")
            f.write(f"**基准配置**: {self.base_config_file}\n")
            f.write(f"**情景数量**: {len(results)}\n\n")
            
            f.write("## 结果对比\n\n")
            f.write("| 情景名 | 流量误差(%) | 质量守恒 | 迭代次数 | 状态 |\n")
            f.write("|--------|------------|---------|---------|------|\n")
            
            for name, result in results.items():
                if result.get('failed', False):
                    f.write(f"| {name} | - | - | - | ✗ 失败 |\n")
                else:
                    error = result.get('error', 0)
                    conservation = result.get('conservation_error', 0)
                    iterations = result.get('iterations', 0)
                    f.write(f"| {name} | {error:.4f} | {conservation:.2e} | {iterations} | ✓ 成功 |\n")
            
            f.write("\n---\n")
            f.write(f"**生成时间**: {pd.Timestamp.now()}\n")
        
        print(f"✅ 对比报告已保存: {report_path}")


# ========== 使用示例 ==========

def example_scenario_analysis():
    """情景分析示例"""
    print("\n" + "="*80)
    print("示例：情景分析")
    print("="*80)
    
    # 定义情景
    scenarios = {
        "基准情景": {},
        
        "增加泵站扬程": {
            "pump_head": 6.0  # 从5.0增加到6.0
        },
        
        "关小闸门": {
            "gate_opening": 2.5  # 从3.0减小到2.5
        },
        
        "增大流量": {
            "upstream_flow": 15.0  # 从10.0增加到15.0
        },
    }
    
    # 创建管理器
    base_config = "config/examples/gate_pump_cascade.yaml"
    
    if not os.path.exists(base_config):
        print(f"⚠️  基准配置不存在: {base_config}")
        return
    
    manager = ScenarioManager(base_config)
    
    # 运行情景
    results = manager.run_scenarios(scenarios, verbose=False)
    
    # 对比结果
    manager.compare_results(results)
    
    # 生成报告
    manager.generate_comparison_report(results, "scenario_comparison_report.md")
    
    return results


if __name__ == '__main__':
    example_scenario_analysis()
