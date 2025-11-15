#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试覆盖分析 - 查漏补缺
Analyze Test Coverage - Find Gaps

分析已有测试案例的覆盖情况，找出缺失的测试场景

Author: HydroClaude Team
Date: 2025-11-15
"""

import sys
import os
import json
from pathlib import Path
from typing import Dict, List, Set

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestCoverageAnalyzer:
    """测试覆盖分析器"""
    
    def __init__(self):
        # 定义完整的组件清单（30种）
        self.all_components = {
            # 闸门（5种）
            'gates': ['SluiceGate', 'RadialGate', 'VerticalLiftGate', 'RollerGate', 'FlapGate'],
            # 泵站（1种）
            'pumps': ['PumpStation'],
            # 阀门（7种）
            'valves': ['ButterflyValve', 'BallValve', 'GateValve', 'GlobeValve', 
                      'CheckValve', 'NeedleValve', 'ConeValve'],
            # 水轮机（3种）
            'turbines': ['FrancisTurbine', 'KaplanTurbine', 'PeltonTurbine'],
            # 河管渠（5种）
            'channels': ['River', 'Canal', 'Pipe', 'Tunnel', 'Penstock'],
            # 库湖池（3种）
            'reservoirs': ['Reservoir', 'Lake', 'StorageBasin'],
            # 堰（6种）
            'weirs': ['SharpCrestedWeir', 'BroadCrestedWeir', 'VNotchWeir', 
                     'RectangularWeir', 'TrapezoidalWeir', 'OgeeWeir'],
            # 其他（6种）
            'others': ['Culvert', 'SideWeir', 'DropStructure', 'Bridge', 
                      'SurgeTank', 'HydropowerStation']
        }
        
        # 定义测试场景类型
        self.scenario_types = [
            'basic_function',      # 基础功能
            'multi_component',     # 多组件
            'cascade_system',      # 梯级系统
            'network_system',      # 管网系统
            'real_time_control',   # 实时控制
            'optimization',        # 优化调度
            'extreme_condition',   # 极端工况
            'long_term_simulation',# 长期模拟
            'emergency_response',  # 应急响应
            'integrated_system'    # 综合系统
        ]
        
        self.covered_components = set()
        self.covered_scenarios = set()
        self.test_files_by_component = {}
    
    def analyze_existing_tests(self):
        """分析已有测试案例"""
        print("\n" + "="*80)
        print("分析已有测试覆盖情况")
        print("="*80)
        
        # 扫描测试文件
        test_paths = [
            project_root / 'examples',
            project_root / 'tests',
            project_root / 'web' / 'backend' / 'examples'
        ]
        
        for path in test_paths:
            if path.exists():
                self._scan_directory(path)
        
        # 统计覆盖情况
        self._calculate_coverage()
    
    def _scan_directory(self, directory: Path):
        """扫描目录"""
        for py_file in directory.rglob("*.py"):
            if '.bak' in str(py_file) or '__pycache__' in str(py_file):
                continue
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read().lower()
                    
                    # 检查组件覆盖
                    for category, components in self.all_components.items():
                        for component in components:
                            if component.lower() in content:
                                self.covered_components.add(component)
                                if component not in self.test_files_by_component:
                                    self.test_files_by_component[component] = []
                                self.test_files_by_component[component].append(py_file.name)
                    
                    # 检查场景覆盖
                    for scenario in self.scenario_types:
                        keywords = scenario.replace('_', ' ').split()
                        if any(kw in content for kw in keywords):
                            self.covered_scenarios.add(scenario)
            except:
                pass
    
    def _calculate_coverage(self):
        """计算覆盖率"""
        print("\n1️⃣ 组件覆盖分析")
        print("-"*80)
        
        all_components_flat = []
        for components in self.all_components.values():
            all_components_flat.extend(components)
        
        total_components = len(all_components_flat)
        covered_count = len(self.covered_components)
        
        print(f"总组件数: {total_components}")
        print(f"已覆盖: {covered_count} ({covered_count/total_components*100:.1f}%)")
        print(f"未覆盖: {total_components - covered_count}")
        
        # 按类别统计
        print("\n按类别覆盖率:")
        for category, components in self.all_components.items():
            covered = sum(1 for c in components if c in self.covered_components)
            total = len(components)
            rate = covered/total*100 if total > 0 else 0
            status = "✅" if rate >= 80 else "⚠️" if rate >= 50 else "❌"
            print(f"  {status} {category:<15} {covered}/{total} ({rate:.1f}%)")
        
        # 场景覆盖
        print("\n2️⃣ 场景覆盖分析")
        print("-"*80)
        covered_scenario_count = len(self.covered_scenarios)
        total_scenarios = len(self.scenario_types)
        print(f"总场景数: {total_scenarios}")
        print(f"已覆盖: {covered_scenario_count} ({covered_scenario_count/total_scenarios*100:.1f}%)")
        
        for scenario in self.scenario_types:
            status = "✅" if scenario in self.covered_scenarios else "❌"
            print(f"  {status} {scenario}")
    
    def find_missing_tests(self) -> Dict:
        """找出缺失的测试"""
        print("\n" + "="*80)
        print("🔍 查漏补缺 - 缺失的测试案例")
        print("="*80)
        
        missing = {
            'components': [],
            'scenarios': [],
            'combinations': []
        }
        
        # 1. 缺失的组件测试
        print("\n❌ 缺失的组件测试:")
        print("-"*80)
        
        for category, components in self.all_components.items():
            missing_in_category = [c for c in components if c not in self.covered_components]
            if missing_in_category:
                print(f"\n{category}:")
                for component in missing_in_category:
                    print(f"  ❌ {component} - 需要基础功能测试")
                    missing['components'].append({
                        'component': component,
                        'category': category,
                        'priority': 'high' if category in ['gates', 'channels', 'reservoirs'] else 'medium'
                    })
        
        # 2. 缺失的场景测试
        print("\n❌ 缺失的场景测试:")
        print("-"*80)
        
        missing_scenarios = [s for s in self.scenario_types if s not in self.covered_scenarios]
        if missing_scenarios:
            for scenario in missing_scenarios:
                print(f"  ❌ {scenario}")
                missing['scenarios'].append({
                    'scenario': scenario,
                    'priority': 'high' if 'extreme' in scenario or 'emergency' in scenario else 'medium'
                })
        else:
            print("  ✅ 所有场景类型都有覆盖")
        
        # 3. 缺失的组合测试
        print("\n❌ 缺失的重要组合测试:")
        print("-"*80)
        
        important_combinations = [
            (['Reservoir', 'Canal', 'SluiceGate'], '水库-渠道-闸门灌溉系统'),
            (['Reservoir', 'Penstock', 'FrancisTurbine'], '水库-钢管-水轮机发电系统'),
            (['Pipe', 'PumpStation', 'Valve'], '管道-泵站-阀门供水系统'),
            (['River', 'Bridge', 'Weir'], '河道-桥梁-堰防洪系统'),
            (['Reservoir', 'SurgeTank', 'HydropowerStation'], '水库-调压井-水电站'),
            (['Canal', 'SideWeir', 'Reservoir'], '渠道-侧堰-调蓄池'),
            (['Pipe', 'Valve', 'ButterflyValve', 'CheckValve'], '复杂阀门系统'),
        ]
        
        for components, description in important_combinations:
            all_present = all(any(c in comp for comp in components) 
                            for c in self.covered_components)
            if not all_present:
                print(f"  ❌ {description}")
                print(f"     组件: {', '.join(components)}")
                missing['combinations'].append({
                    'components': components,
                    'description': description,
                    'priority': 'high'
                })
        
        return missing
    
    def generate_test_plan(self, missing: Dict):
        """生成测试补充计划"""
        print("\n" + "="*80)
        print("📋 测试补充计划")
        print("="*80)
        
        # 统计
        total_missing = (len(missing['components']) + 
                        len(missing['scenarios']) + 
                        len(missing['combinations']))
        
        print(f"\n需要补充的测试数量: {total_missing}")
        print(f"  - 组件测试: {len(missing['components'])}")
        print(f"  - 场景测试: {len(missing['scenarios'])}")
        print(f"  - 组合测试: {len(missing['combinations'])}")
        
        # 优先级分组
        high_priority = []
        medium_priority = []
        
        for item in missing['components']:
            if item['priority'] == 'high':
                high_priority.append(f"组件: {item['component']}")
            else:
                medium_priority.append(f"组件: {item['component']}")
        
        for item in missing['scenarios']:
            if item['priority'] == 'high':
                high_priority.append(f"场景: {item['scenario']}")
            else:
                medium_priority.append(f"场景: {item['scenario']}")
        
        for item in missing['combinations']:
            if item['priority'] == 'high':
                high_priority.append(f"组合: {item['description']}")
        
        print(f"\n🔴 高优先级 ({len(high_priority)}项):")
        for i, item in enumerate(high_priority[:10], 1):
            print(f"  {i}. {item}")
        
        print(f"\n🟡 中优先级 ({len(medium_priority)}项):")
        for i, item in enumerate(medium_priority[:10], 1):
            print(f"  {i}. {item}")
        
        # 保存到JSON
        output = {
            'summary': {
                'total_missing': total_missing,
                'components': len(missing['components']),
                'scenarios': len(missing['scenarios']),
                'combinations': len(missing['combinations'])
            },
            'high_priority': high_priority,
            'medium_priority': medium_priority,
            'detailed': missing
        }
        
        with open('test_gap_analysis.json', 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ 详细分析已保存到: test_gap_analysis.json")
    
    def generate_coverage_report(self):
        """生成覆盖报告"""
        print("\n" + "="*80)
        print("📊 测试覆盖报告")
        print("="*80)
        
        # 组件覆盖矩阵
        print("\n组件覆盖矩阵:")
        print("-"*80)
        print(f"{'类别':<15} {'已覆盖组件':<50} {'覆盖率':<10}")
        print("-"*80)
        
        for category, components in self.all_components.items():
            covered_list = [c for c in components if c in self.covered_components]
            covered_count = len(covered_list)
            total_count = len(components)
            rate = covered_count/total_count*100 if total_count > 0 else 0
            
            covered_str = ', '.join(covered_list[:3])
            if len(covered_list) > 3:
                covered_str += f"... (+{len(covered_list)-3})"
            
            print(f"{category:<15} {covered_str:<50} {rate:.1f}%")
        
        # 详细的组件测试文件
        print("\n详细的组件测试分布:")
        print("-"*80)
        
        for component in sorted(self.covered_components):
            files = self.test_files_by_component.get(component, [])
            print(f"  {component}: {len(files)} 个测试文件")
    
    def run_analysis(self):
        """运行完整分析"""
        print("\n" + "🔍"*40)
        print("测试覆盖分析 - 查漏补缺".center(80))
        print("🔍"*40)
        
        # 1. 分析已有测试
        self.analyze_existing_tests()
        
        # 2. 找出缺失
        missing = self.find_missing_tests()
        
        # 3. 生成测试计划
        self.generate_test_plan(missing)
        
        # 4. 生成覆盖报告
        self.generate_coverage_report()
        
        # 5. 总结
        all_components_flat = []
        for components in self.all_components.values():
            all_components_flat.extend(components)
        
        total = len(all_components_flat)
        covered = len(self.covered_components)
        
        print("\n" + "🎯"*40)
        print(f"覆盖率: {covered}/{total} ({covered/total*100:.1f}%)".center(80))
        print(f"需补充: {total-covered} 个组件测试".center(80))
        print("🎯"*40)


if __name__ == "__main__":
    analyzer = TestCoverageAnalyzer()
    analyzer.run_analysis()
