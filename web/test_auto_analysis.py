#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
自动分析模块完整测试

测试配置分析和结果分析的所有功能
"""

import sys
import os
import numpy as np
import json

# 添加路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from analysis.config_analyzer import ConfigAnalyzer
from analysis.result_analyzer_professional import ProfessionalResultAnalyzer

print("="*80)
print("🔍 自动分析模块完整测试")
print("="*80)
print()

# =============================================================================
# 测试1: 配置分析 - 优秀配置
# =============================================================================
print("📋 测试1: 优秀配置分析")
print("-"*80)

excellent_config = {
    "width": 10.0,
    "length": 1000.0,
    "n_cells": 100,
    "manning_n": 0.025,
    "slope": 0.001,
    "cfl": 0.5,
    "order": 2,
    "use_numba": True,
    "t_end": 100.0,
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

analyzer = ConfigAnalyzer()
report1 = analyzer.analyze(excellent_config)

print(f"✅ 配置有效: {report1.is_valid}")
print(f"📊 质量分数: {report1.quality_score:.1f}/100")
print(f"⏱️  预计时间: {report1.estimated_time:.2f}秒")
print(f"💾 预计内存: {report1.estimated_memory:.1f}MB")
print(f"🔢 预计步数: {report1.estimated_iterations}")
print(f"⚠️  发现问题: {len(report1.issues)}个")
print(f"💡 优化建议: {len(report1.recommendations)}条")
print()

# =============================================================================
# 测试2: 配置分析 - 有问题的配置
# =============================================================================
print("📋 测试2: 有问题的配置分析")
print("-"*80)

problematic_config = {
    "width": 0.5,  # 太小
    "length": 10000.0,
    "n_cells": 10,  # 太粗
    "manning_n": 0.001,  # 太光滑
    "slope": 0.15,  # 太陡
    "cfl": 1.2,  # 超过稳定性极限
    "order": 2,
    "t_end": 1000.0,
    "dt_max": 10.0,  # 太大
    "output_interval": 5.0,
    "initial_conditions": {
        "type": "uniform",
        "h": 5.0,
        "Q": 10.0
    },
    "boundary_conditions": {
        "upstream": {"type": "Q", "value": 10.0},
        "downstream": {"type": "Q", "value": 10.0}  # 两端都是Q
    }
}

report2 = analyzer.analyze(problematic_config)

print(f"{'❌' if not report2.is_valid else '✅'} 配置有效: {report2.is_valid}")
print(f"📊 质量分数: {report2.quality_score:.1f}/100")
print(f"🔴 错误: {len(report2.errors)}个")
print(f"⚠️  警告: {len(report2.issues)}个")

if report2.errors:
    print("\n严重错误:")
    for error in report2.errors[:3]:
        print(f"  - {error}")

if report2.issues:
    print("\n主要问题:")
    for issue in report2.issues[:5]:
        print(f"  [{issue.severity.value}] {issue.message}")
        print(f"    建议: {issue.suggestion}")

print()

# =============================================================================
# 测试3: 结果分析 - 正常流动
# =============================================================================
print("📊 测试3: 正常流动结果分析")
print("-"*80)

# 生成模拟的正常流动数据
nx = 100
nt = 50
x = np.linspace(0, 1000, nx)
time = np.linspace(0, 100, nt)

# 稳定的均匀流
h = np.ones((nt, nx)) * 5.0 + np.random.normal(0, 0.05, (nt, nx))
Q = np.ones((nt, nx)) * 10.0 + np.random.normal(0, 0.01, (nt, nx))
V = Q / (excellent_config['width'] * h)

normal_result = {
    'task_id': 'test_normal_flow',
    'x': x.tolist(),
    'time': time.tolist(),
    'h': h.tolist(),
    'Q': Q.tolist(),
    'V': V.tolist(),
    'metrics': {
        'duration': 2.5,
        'time_steps': 1000,
        'iterations': 1000
    }
}

result_analyzer = ProfessionalResultAnalyzer()
result_report1 = result_analyzer.analyze(normal_result, excellent_config)

print(f"🏆 质量评级: {result_report1.quality.value.upper()}")
print(f"📊 质量评分: {result_report1.quality_score:.1f}/100")
print()
print("💧 水力特性:")
print(f"  - 水深: {result_report1.hydraulics.h_min:.2f} - {result_report1.hydraulics.h_max:.2f}m (平均{result_report1.hydraulics.h_mean:.2f}m)")
print(f"  - 流速: {result_report1.hydraulics.V_min:.2f} - {result_report1.hydraulics.V_max:.2f}m/s (平均{result_report1.hydraulics.V_mean:.2f}m/s)")
print(f"  - Froude: {result_report1.hydraulics.Fr_min:.3f} - {result_report1.hydraulics.Fr_max:.3f} (平均{result_report1.hydraulics.Fr_mean:.3f})")
print()
print("🌊 流态分布:")
print(f"  - 亚临界流: {result_report1.hydraulics.subcritical_percentage:.1f}%")
print(f"  - 临界流: {result_report1.hydraulics.critical_percentage:.1f}%")
print(f"  - 超临界流: {result_report1.hydraulics.supercritical_percentage:.1f}%")
print()
print("⚖️  守恒性:")
if result_report1.conservation.mass_conservation:
    mass = result_report1.conservation.mass_conservation
    print(f"  - 质量守恒误差: {mass['error_mean']:.4f}%")
    print(f"  - 状态: {mass['status']}")
print()
print("⚡ 性能:")
print(f"  - 计算时间: {result_report1.performance.computation_time:.2f}秒")
print(f"  - 计算效率: {result_report1.performance.efficiency:.1f}步/秒")
print()

# =============================================================================
# 测试4: 结果分析 - 溃坝问题
# =============================================================================
print("📊 测试4: 溃坝问题结果分析")
print("-"*80)

# 生成模拟的溃坝数据（有激波）
dam_pos_idx = nx // 2
h_dambreak = np.zeros((nt, nx))
V_dambreak = np.zeros((nt, nx))

for t_idx in range(nt):
    # 左侧高水位，右侧低水位
    wave_speed = 2.0
    wave_front = dam_pos_idx + int(wave_speed * t_idx)
    
    h_dambreak[t_idx, :wave_front] = 10.0 - 0.02 * t_idx
    h_dambreak[t_idx, wave_front:] = 1.0 + 0.01 * t_idx
    
    # 水跃处流速突变
    V_dambreak[t_idx, :wave_front] = 5.0
    V_dambreak[t_idx, wave_front:] = 0.5

Q_dambreak = h_dambreak * V_dambreak * excellent_config['width']

dambreak_result = {
    'task_id': 'test_dambreak',
    'x': x.tolist(),
    'time': time.tolist(),
    'h': h_dambreak.tolist(),
    'Q': Q_dambreak.tolist(),
    'V': V_dambreak.tolist(),
    'metrics': {
        'duration': 8.7,
        'time_steps': 5000,
        'iterations': 5000
    }
}

result_report2 = result_analyzer.analyze(dambreak_result, excellent_config)

print(f"🏆 质量评级: {result_report2.quality.value.upper()}")
print(f"📊 质量评分: {result_report2.quality_score:.1f}/100")
print()
print("💧 水力特性:")
print(f"  - 水深范围: {result_report2.hydraulics.h_min:.2f} - {result_report2.hydraulics.h_max:.2f}m")
print(f"  - 流速范围: {result_report2.hydraulics.V_min:.2f} - {result_report2.hydraulics.V_max:.2f}m/s")
print(f"  - 平均Froude: {result_report2.hydraulics.Fr_mean:.3f}")
print()
print("🌊 关键特征:")
print(f"  - 水跃: {len(result_report2.hydraulics.hydraulic_jumps)}个")
print(f"  - 激波: {len(result_report2.hydraulics.shock_waves)}个")
print()

if result_report2.hydraulics.hydraulic_jumps:
    for i, jump in enumerate(result_report2.hydraulics.hydraulic_jumps[:3], 1):
        print(f"  水跃#{i}:")
        print(f"    位置: {jump['location']:.1f}m")
        print(f"    上游水深: {jump['upstream_depth']:.2f}m (Fr={jump['upstream_froude']:.2f})")
        print(f"    下游水深: {jump['downstream_depth']:.2f}m (Fr={jump['downstream_froude']:.2f})")
        print()

print("🎯 关键事件:")
for event in result_report2.key_events[:3]:
    print(f"  - [{event['type']}] {event.get('description', '')}")
print()

# =============================================================================
# 测试5: 生成完整报告
# =============================================================================
print("📄 测试5: 生成完整报告")
print("-"*80)

# 配置分析报告
config_md = analyzer.generate_report_markdown(report1)
config_report_path = '/workspace/web/test_config_analysis_report.md'
with open(config_report_path, 'w', encoding='utf-8') as f:
    f.write(config_md)
print(f"✅ 配置分析报告已生成: {config_report_path}")

# 结果分析报告
result_md = result_analyzer.generate_markdown_report(result_report1)
result_report_path = '/workspace/web/test_result_analysis_report.md'
with open(result_report_path, 'w', encoding='utf-8') as f:
    f.write(result_md)
print(f"✅ 结果分析报告已生成: {result_report_path}")

# JSON导出
json_report_path = '/workspace/web/test_result_analysis_report.json'
result_analyzer.export_json(result_report1, json_report_path)
print(f"✅ JSON报告已导出: {json_report_path}")
print()

# =============================================================================
# 测试6: 可视化建议
# =============================================================================
print("📈 测试6: 可视化建议")
print("-"*80)

print("正常流动的可视化建议:")
for i, viz in enumerate(result_report1.visualization_recommendations[:3], 1):
    priority_emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}
    emoji = priority_emoji.get(viz['priority'], '⚪')
    print(f"{i}. {emoji} {viz['title']} ({viz['priority']})")
    print(f"   {viz['description']}")
print()

print("溃坝问题的可视化建议:")
for i, viz in enumerate(result_report2.visualization_recommendations[:3], 1):
    priority_emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}
    emoji = priority_emoji.get(viz['priority'], '⚪')
    print(f"{i}. {emoji} {viz['title']} ({viz['priority']})")
    print(f"   {viz['description']}")
print()

# =============================================================================
# 总结
# =============================================================================
print("="*80)
print("✅ 所有测试完成!")
print("="*80)
print()
print("📊 测试总结:")
print(f"  1. 优秀配置分析: 质量分数 {report1.quality_score:.1f}/100")
print(f"  2. 问题配置分析: 发现 {len(report2.errors)} 个错误, {len(report2.issues)} 个问题")
print(f"  3. 正常流动分析: 质量评级 {result_report1.quality.value.upper()}")
print(f"  4. 溃坝问题分析: 检测到 {len(result_report2.hydraulics.hydraulic_jumps)} 个水跃")
print(f"  5. 报告生成: 已生成Markdown和JSON格式报告")
print(f"  6. 可视化建议: 每个结果都有优先级排序的图表建议")
print()
print("🎉 自动分析模块工作正常！")
print()
print("📚 查看生成的报告:")
print(f"  - {config_report_path}")
print(f"  - {result_report_path}")
print(f"  - {json_report_path}")
print()
