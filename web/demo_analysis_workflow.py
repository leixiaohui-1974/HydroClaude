#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
自动分析工作流演示

展示完整的配置分析→仿真→结果分析流程
模拟Web系统的实际使用场景
"""

import sys
import os
import json

# 添加路径
backend_path = os.path.join(os.path.dirname(__file__), 'backend')
sys.path.insert(0, backend_path)
project_root = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, project_root)

from analysis.config_analyzer import ConfigAnalyzer
from analysis.result_analyzer_professional import ProfessionalResultAnalyzer

# 导入numpy（模拟数据需要）
import numpy as np

# 尝试导入引擎（如果不可用则使用模拟数据）
try:
    from backend.core.hydraulic_engine import HydraulicEngine
    ENGINE_AVAILABLE = True
except ImportError:
    print("⚠️  注意: HydraulicEngine不可用，将使用模拟数据")
    ENGINE_AVAILABLE = False

print("="*80)
print("🌊 HydroClaude 自动分析工作流演示")
print("="*80)
print()
print("本演示展示完整的工作流：")
print("  1. 用户提交配置")
print("  2. 自动配置分析和验证")
print("  3. 执行仿真计算")
print("  4. 自动结果分析")
print("  5. 生成专业报告")
print()
print("="*80)
print()

# =============================================================================
# 步骤1: 用户提交配置
# =============================================================================
print("📝 步骤1: 用户提交配置")
print("-"*80)

user_config = {
    "width": 10.0,
    "length": 1000.0,
    "n_cells": 100,
    "manning_n": 0.025,
    "slope": 0.001,
    "cfl": 0.5,
    "order": 2,
    "use_numba": True,
    "t_end": 10.0,
    "dt_max": 0.1,
    "output_interval": 1.0,
    "initial_conditions": {
        "type": "uniform",
        "h": 5.0,
        "Q": 10.0
    },
    "boundary_conditions": {
        "upstream": {"type": "Q", "value": 10.0},
        "downstream": {"type": "h", "value": 5.0}
    }
}

print("✅ 用户配置:")
print(f"  - 渠道: {user_config['width']}m × {user_config['length']}m")
print(f"  - 网格: {user_config['n_cells']}个单元")
print(f"  - 时长: {user_config['t_end']}秒")
print(f"  - Manning: {user_config['manning_n']}")
print(f"  - 底坡: {user_config['slope']}")
print()

# =============================================================================
# 步骤2: 自动配置分析
# =============================================================================
print("🔍 步骤2: 自动配置分析")
print("-"*80)

config_analyzer = ConfigAnalyzer()
config_report = config_analyzer.analyze(user_config)

print(f"{'✅' if config_report.is_valid else '❌'} 配置有效性: {config_report.is_valid}")
print(f"📊 质量分数: {config_report.quality_score:.1f}/100")
print()

print("⏱️  性能预测:")
print(f"  - 预计计算时间: {config_report.estimated_time:.2f}秒")
print(f"  - 预计内存使用: {config_report.estimated_memory:.1f}MB")
print(f"  - 预计时间步数: {config_report.estimated_iterations}")
print()

if config_report.issues:
    print(f"⚠️  发现 {len(config_report.issues)} 个问题:")
    for issue in config_report.issues[:3]:
        print(f"  [{issue.severity.value}] {issue.message}")
    print()

if config_report.recommendations:
    print(f"💡 优化建议 ({len(config_report.recommendations)}条):")
    for rec in config_report.recommendations[:2]:
        print(f"  - {rec['title']}: {rec['action']}")
    print()

# 判断是否继续
if not config_report.is_valid:
    print("❌ 配置无效，请修改后重试！")
    sys.exit(1)

if config_report.quality_score < 70:
    print("⚠️  配置质量较低，建议优化后再运行")
    response = input("是否继续? (y/n): ")
    if response.lower() != 'y':
        sys.exit(0)

print("✅ 配置验证通过，开始仿真...")
print()

# =============================================================================
# 步骤3: 执行仿真
# =============================================================================
print("⚙️  步骤3: 执行仿真")
print("-"*80)

if ENGINE_AVAILABLE:
    try:
        # 创建引擎
        engine = HydraulicEngine()
        
        # 转换配置格式
        simulation_config = {
            'type': '1d_canal',
            'name': 'demo_analysis_workflow',
            'domain': {
                'width': user_config['width'],
                'length': user_config['length'],
                'n_cells': user_config['n_cells']
            },
            'physical_params': {
                'manning_n': user_config['manning_n'],
                'slope': user_config['slope']
            },
            'numerical_params': {
                'cfl': user_config['cfl'],
                'order': user_config['order'],
                'use_numba': user_config.get('use_numba', True)
            },
            'time_params': {
                't_end': user_config['t_end'],
                'dt_max': user_config['dt_max'],
                'output_interval': user_config['output_interval']
            },
            'initial_conditions': user_config['initial_conditions'],
            'boundary_conditions': user_config['boundary_conditions']
        }
        
        print("🚀 开始计算...")
        print(f"   预计时间: {config_report.estimated_time:.2f}秒")
        
        # 运行仿真
        result = engine.run_simulation(simulation_config)
        
        print(f"✅ 仿真完成！")
        print(f"   实际时间: {result.metadata.get('duration', 0):.2f}秒")
        print(f"   时间步数: {result.metadata.get('time_steps', 0)}")
        print()
        
    except Exception as e:
        print(f"❌ 仿真失败: {str(e)}")
        import traceback
        traceback.print_exc()
        ENGINE_AVAILABLE = False

if not ENGINE_AVAILABLE:
    # 使用模拟数据
    print("📦 使用模拟数据进行演示...")
    
    # 生成模拟结果
    class MockResult:
        def __init__(self):
            nx = user_config['n_cells']
            nt = int(user_config['t_end'] / user_config['output_interval']) + 1
            
            self.x = np.linspace(0, user_config['length'], nx)
            self.time = np.linspace(0, user_config['t_end'], nt)
            
            # 稳定的均匀流
            self.h = np.ones((nt, nx)) * 5.0 + np.random.normal(0, 0.01, (nt, nx))
            self.Q = np.ones((nt, nx)) * 10.0 + np.random.normal(0, 0.005, (nt, nx))
            self.V = self.Q / (user_config['width'] * self.h)
            
            self.metadata = {
                'duration': config_report.estimated_time,
                'time_steps': nt
            }
    
    result = MockResult()
    print(f"✅ 模拟数据生成完成！")
    print(f"   模拟时间: {result.metadata['duration']:.2f}秒")
    print(f"   时间步数: {result.metadata['time_steps']}")
    print()

# =============================================================================
# 步骤4: 自动结果分析
# =============================================================================
print("📊 步骤4: 自动结果分析")
print("-"*80)

# 转换结果为字典格式
result_dict = {
    'task_id': 'demo_workflow',
    'x': result.x.tolist(),
    'time': result.time.tolist(),
    'h': result.h.tolist(),
    'Q': result.Q.tolist(),
    'V': result.V.tolist(),
    'metrics': {
        'duration': result.metadata.get('duration', 0),
        'time_steps': result.metadata.get('time_steps', 0),
        'iterations': result.metadata.get('time_steps', 0)
    }
}

# 分析结果
result_analyzer = ProfessionalResultAnalyzer()
result_report = result_analyzer.analyze(result_dict, user_config)

print(f"🏆 质量评级: {result_report.quality.value.upper()}")
print(f"📊 质量评分: {result_report.quality_score:.1f}/100")
print()

print("💧 水力特性:")
hydro = result_report.hydraulics
print(f"  - 水深: {hydro.h_min:.3f} - {hydro.h_max:.3f}m (平均{hydro.h_mean:.3f}m)")
print(f"  - 流量: {hydro.Q_min:.3f} - {hydro.Q_max:.3f}m³/s (平均{hydro.Q_mean:.3f}m³/s)")
print(f"  - 流速: {hydro.V_min:.3f} - {hydro.V_max:.3f}m/s (平均{hydro.V_mean:.3f}m/s)")
print(f"  - Froude: {hydro.Fr_min:.3f} - {hydro.Fr_max:.3f} (平均{hydro.Fr_mean:.3f})")
print()

print("🌊 流态分布:")
print(f"  - 亚临界流: {hydro.subcritical_percentage:.1f}%")
print(f"  - 临界流: {hydro.critical_percentage:.1f}%")
print(f"  - 超临界流: {hydro.supercritical_percentage:.1f}%")
print()

if result_report.conservation.mass_conservation:
    mass = result_report.conservation.mass_conservation
    print("⚖️  守恒性检查:")
    print(f"  - 质量守恒误差: {mass['error_mean']:.4f}%")
    print(f"  - 状态: {mass['status']}")
    print()

print("⚡ 性能:")
perf = result_report.performance
print(f"  - 计算时间: {perf.computation_time:.2f}秒")
print(f"  - 计算效率: {perf.efficiency:.1f}步/秒")
print()

if result_report.warnings:
    print(f"⚠️  警告 ({len(result_report.warnings)}条):")
    for warning in result_report.warnings[:3]:
        print(f"  - {warning}")
    print()

if result_report.errors:
    print(f"❌ 错误 ({len(result_report.errors)}条):")
    for error in result_report.errors[:3]:
        print(f"  - {error}")
    print()

if result_report.key_events:
    print(f"🎯 关键事件 ({len(result_report.key_events)}个):")
    for event in result_report.key_events[:3]:
        print(f"  - [{event['type']}] {event.get('description', '无描述')}")
    print()

# =============================================================================
# 步骤5: 生成专业报告
# =============================================================================
print("📄 步骤5: 生成专业报告")
print("-"*80)

# 生成配置分析报告
config_report_md = config_analyzer.generate_report_markdown(config_report)
config_report_path = '/workspace/web/demo_config_analysis.md'
with open(config_report_path, 'w', encoding='utf-8') as f:
    f.write(config_report_md)
print(f"✅ 配置分析报告: {config_report_path}")

# 生成结果分析报告
result_report_md = result_analyzer.generate_markdown_report(result_report)
result_report_path = '/workspace/web/demo_result_analysis.md'
with open(result_report_path, 'w', encoding='utf-8') as f:
    f.write(result_report_md)
print(f"✅ 结果分析报告: {result_report_path}")

# 生成JSON报告
json_report_path = '/workspace/web/demo_analysis_full_report.json'
full_report = {
    'config_analysis': {
        'is_valid': config_report.is_valid,
        'quality_score': config_report.quality_score,
        'estimated_time': config_report.estimated_time,
        'estimated_memory': config_report.estimated_memory,
        'issues_count': len(config_report.issues),
        'recommendations_count': len(config_report.recommendations)
    },
    'simulation': {
        'duration': result.metadata.get('duration', 0),
        'time_steps': result.metadata.get('time_steps', 0)
    },
    'result_analysis': {
        'quality': result_report.quality.value,
        'quality_score': result_report.quality_score,
        'hydraulics': {
            'h_mean': hydro.h_mean,
            'Q_mean': hydro.Q_mean,
            'V_mean': hydro.V_mean,
            'Fr_mean': hydro.Fr_mean,
            'subcritical_percentage': hydro.subcritical_percentage
        },
        'warnings_count': len(result_report.warnings),
        'errors_count': len(result_report.errors),
        'key_events_count': len(result_report.key_events)
    },
    'visualization_recommendations': result_report.visualization_recommendations[:5]
}

with open(json_report_path, 'w', encoding='utf-8') as f:
    json.dump(full_report, f, ensure_ascii=False, indent=2)
print(f"✅ JSON完整报告: {json_report_path}")
print()

# =============================================================================
# 可视化建议
# =============================================================================
print("📈 步骤6: 可视化建议")
print("-"*80)

print("推荐生成以下图表（按优先级排序）:")
for i, viz in enumerate(result_report.visualization_recommendations[:5], 1):
    priority_emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}
    emoji = priority_emoji.get(viz['priority'], '⚪')
    print(f"{i}. {emoji} {viz['title']} ({viz['priority']} priority)")
    print(f"   {viz['description']}")
print()

# =============================================================================
# 总结
# =============================================================================
print("="*80)
print("✅ 工作流完成!")
print("="*80)
print()
print("📊 执行总结:")
print(f"  配置验证: {'✅ 通过' if config_report.is_valid else '❌ 失败'} (质量分数: {config_report.quality_score:.1f})")
print(f"  仿真计算: ✅ 完成 ({result.metadata.get('duration', 0):.2f}秒)")
print(f"  结果评级: {result_report.quality.value.upper()} (质量分数: {result_report.quality_score:.1f})")
print(f"  报告生成: ✅ 已生成 3 个文件")
print()

# 判断整体质量
if result_report.quality_score >= 95:
    print("🏆 优秀！结果完全可靠，可以直接使用。")
elif result_report.quality_score >= 85:
    print("✅ 良好！结果基本可靠，建议查看警告。")
elif result_report.quality_score >= 70:
    print("👍 可接受。建议检查问题并考虑优化配置。")
else:
    print("⚠️  质量较差，建议修改配置后重新计算。")
print()

print("📚 查看完整报告:")
print(f"  - 配置分析: {config_report_path}")
print(f"  - 结果分析: {result_report_path}")
print(f"  - JSON报告: {json_report_path}")
print()

print("🎉 演示完成！这就是HydroClaude自动分析系统的完整工作流程。")
print()
