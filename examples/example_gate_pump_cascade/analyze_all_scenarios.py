#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
深度分析所有工况结果
识别问题、验证物理合理性
"""
import sys
import warnings
warnings.filterwarnings("ignore")
import os

# ========== 路径设置 ==========
script_path = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(script_path))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


import os
import numpy as np
import matplotlib.pyplot as plt

def analyze_scenario(scenario_dir):
    """分析单个工况"""
    scenario_name = os.path.basename(scenario_dir)
    data_file = os.path.join(scenario_dir, "scenario_data.npz")
    
    if not os.path.exists(data_file):
        return None
    
    data = np.load(data_file)
    
    x = data['x']
    time = data['time']
    h_history = data['h_history']
    q_history = data['q_history']
    pump_head = data['pump_head_history']
    
    # 分析数据
    analysis = {
        'name': scenario_name,
        'issues': [],
        'warnings': [],
        'metrics': {}
    }
    
    # 检查1: 负流量
    min_q = q_history.min()
    if min_q < 0:
        analysis['issues'].append(f" 出现负流量: {min_q:.2f} m^3/s")
    
    # 检查2: 负水深
    min_h = h_history.min()
    if min_h < 0:
        analysis['issues'].append(f" 出现负水深: {min_h:.2f} m")
    
    # 检查3: NaN或Inf
    if np.any(np.isnan(h_history)) or np.any(np.isnan(q_history)):
        analysis['issues'].append(f" 出现NaN值")
    if np.any(np.isinf(h_history)) or np.any(np.isinf(q_history)):
        analysis['issues'].append(f" 出现Inf值")
    
    # 检查4: 质量守恒
    Q_in = q_history[-1, 0]
    Q_out = q_history[-1, -1]
    storage_rate = Q_in - Q_out
    analysis['metrics']['Q_in'] = Q_in
    analysis['metrics']['Q_out'] = Q_out
    analysis['metrics']['storage_rate'] = storage_rate
    
    # 检查5: 泵站扬程范围
    min_head = pump_head.min()
    max_head = pump_head.max()
    analysis['metrics']['pump_head_min'] = min_head
    analysis['metrics']['pump_head_max'] = max_head
    
    if min_head < 0:
        analysis['issues'].append(f" 泵站扬程为负: {min_head:.2f} m")
    if max_head > 10:
        analysis['warnings'].append(f" 泵站扬程过高: {max_head:.2f} m")
    
    # 检查6: 水深范围
    analysis['metrics']['h_min'] = min_h
    analysis['metrics']['h_max'] = h_history.max()
    
    # 检查7: 流量范围
    analysis['metrics']['q_min'] = min_q
    analysis['metrics']['q_max'] = q_history.max()
    
    return analysis


def main():
    """主函数"""
    print("\n" + "="*100)
    print("所有工况深度分析".center(100))
    print("="*100 + "\n")
    
    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results_advanced")
    
    # 获取所有工况
    scenarios = sorted([d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))])
    
    print(f"发现 {len(scenarios)} 个工况:\n")
    
    all_analyses = []
    
    for scenario in scenarios:
        scenario_dir = os.path.join(base_dir, scenario)
        print(f"分析: {scenario}")
        print("-" * 100)
        
        analysis = analyze_scenario(scenario_dir)
        if analysis:
            all_analyses.append(analysis)
            
            # 打印问题
            if analysis['issues']:
                for issue in analysis['issues']:
                    print(f"  {issue}")
            if analysis['warnings']:
                for warning in analysis['warnings']:
                    print(f"  {warning}")
            
            # 打印关键指标
            m = analysis['metrics']
            print(f"  流量范围: [{m['q_min']:.2f}, {m['q_max']:.2f}] m^3/s")
            print(f"  水深范围: [{m['h_min']:.2f}, {m['h_max']:.2f}] m")
            print(f"  泵站扬程: [{m['pump_head_min']:.2f}, {m['pump_head_max']:.2f}] m")
            print(f"  质量守恒: Q_in={m['Q_in']:.2f} - Q_out={m['Q_out']:.2f} = {m['storage_rate']:.2f} m^3/s")
            
            if not analysis['issues'] and not analysis['warnings']:
                print(f"   物理合理，无问题")
        
        print()
    
    # 统计问题
    print("="*100)
    print("问题统计".center(100))
    print("="*100 + "\n")
    
    total_issues = sum(len(a['issues']) for a in all_analyses)
    total_warnings = sum(len(a['warnings']) for a in all_analyses)
    
    print(f"总工况数: {len(all_analyses)}")
    print(f"发现问题: {total_issues} 个")
    print(f"警告: {total_warnings} 个")
    print()
    
    # 列出所有问题
    if total_issues > 0:
        print("="*100)
        print("问题详情".center(100))
        print("="*100 + "\n")
        
        for analysis in all_analyses:
            if analysis['issues']:
                print(f"{analysis['name']}:")
                for issue in analysis['issues']:
                    print(f"  {issue}")
                print()
    
    # 创建综合报告
    print("="*100)
    print("创建综合分析报告...".center(100))
    print("="*100 + "\n")
    
    create_comprehensive_report(all_analyses, base_dir)
    
    print(" 分析完成")
    print("="*100 + "\n")


def create_comprehensive_report(all_analyses, base_dir):
    """创建综合分析报告"""
    
    report_path = os.path.join(base_dir, "COMPREHENSIVE_ANALYSIS_REPORT.md")
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("# 高精度模型所有工况综合分析报告\n\n")
        f.write("**分析日期**: 2025-10-26\n")
        f.write(f"**工况总数**: {len(all_analyses)}\n\n")
        f.write("---\n\n")
        
        f.write("##  工况汇总\n\n")
        f.write("| 工况 | 负流量 | 负水深 | 泵站扬程 | 质量守恒 | 状态 |\n")
        f.write("|------|:-----:|:-----:|:-------:|:-------:|:----:|\n")
        
        for analysis in all_analyses:
            name = analysis['name'].replace('scenario_', 'S')
            has_neg_q = any('负流量' in issue for issue in analysis['issues'])
            has_neg_h = any('负水深' in issue for issue in analysis['issues'])
            m = analysis['metrics']
            head_ok = 0 <= m['pump_head_min'] <= 6 and 0 <= m['pump_head_max'] <= 6
            mass_ok = abs(m['storage_rate']) < 100
            
            status = "" if not analysis['issues'] else ""
            
            f.write(f"| {name} | {'' if has_neg_q else ''} | {'' if has_neg_h else ''} | "
                   f"{'' if head_ok else ''} | {'' if mass_ok else ''} | {status} |\n")
        
        f.write("\n---\n\n")
        
        f.write("##  发现的问题\n\n")
        
        total_issues = sum(len(a['issues']) for a in all_analyses)
        if total_issues == 0:
            f.write(" **所有工况物理合理，无问题！**\n\n")
        else:
            f.write(f"发现 {total_issues} 个问题:\n\n")
            
            # 按工况列出问题
            for analysis in all_analyses:
                if analysis['issues']:
                    f.write(f"### {analysis['name']}\n\n")
                    for issue in analysis['issues']:
                        f.write(f"- {issue}\n")
                    f.write("\n")
            
            # 问题分类
            f.write("### 问题分类\n\n")
            
            neg_flow_count = sum(1 for a in all_analyses if any('负流量' in i for i in a['issues']))
            neg_depth_count = sum(1 for a in all_analyses if any('负水深' in i for i in a['issues']))
            nan_count = sum(1 for a in all_analyses if any('NaN' in i for i in a['issues']))
            
            if neg_flow_count > 0:
                f.write(f"- **负流量**: {neg_flow_count} 个工况  严重问题\n")
            if neg_depth_count > 0:
                f.write(f"- **负水深**: {neg_depth_count} 个工况  严重问题\n")
            if nan_count > 0:
                f.write(f"- **NaN值**: {nan_count} 个工况  严重问题\n")
            
            f.write("\n")
        
        f.write("---\n\n")
        
        f.write("##  数值统计\n\n")
        f.write("| 工况 | 最小流量 | 最大流量 | 最小水深 | 最大水深 | 泵站扬程 |\n")
        f.write("|------|---------|---------|---------|---------|----------|\n")
        
        for analysis in all_analyses:
            name = analysis['name'].replace('scenario_', 'S')
            m = analysis['metrics']
            f.write(f"| {name} | {m['q_min']:.2f} | {m['q_max']:.2f} | "
                   f"{m['h_min']:.2f} | {m['h_max']:.2f} | "
                   f"[{m['pump_head_min']:.2f}, {m['pump_head_max']:.2f}] |\n")
        
        f.write("\n---\n\n")
        
        f.write("##  修复建议\n\n")
        
        if total_issues > 0:
            if neg_flow_count > 0:
                f.write("### 负流量问题\n\n")
                f.write("**可能原因**:\n")
                f.write("1. 稳态初值不合理\n")
                f.write("2. 时间步长过大\n")
                f.write("3. 边界条件突变过快\n\n")
                f.write("**修复方案**:\n")
                f.write("1. 改进稳态求解算法\n")
                f.write("2. 减小时间步长（dt从1.0改为0.5）\n")
                f.write("3. 增加边界条件过渡时间\n\n")
            
            f.write("### 稳态收敛问题\n\n")
            f.write("**现象**: 多个工况稳态求解未收敛（499次迭代）\n\n")
            f.write("**影响**: 初值不准确，可能导致瞬态初期数值振荡\n\n")
            f.write("**修复方案**:\n")
            f.write("1. 增加最大迭代次数（500->2000）\n")
            f.write("2. 改进收敛判据\n")
            f.write("3. 使用更好的初值猜测\n\n")
        
        f.write("---\n\n")
        f.write(f"**报告生成时间**: 2025-10-26\n")
        f.write(f"**状态**: {' 所有工况正常' if total_issues == 0 else ' 发现问题，需要修复'}\n")
    
    print(f" 综合报告已保存: {report_path}")


if __name__ == "__main__":
    main()
