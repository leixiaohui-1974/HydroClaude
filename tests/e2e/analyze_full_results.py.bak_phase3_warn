#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析完整测试结果 - 111个案例详细分析

Author: HydroClaude Team
Date: 2025-11-15
"""

import json
from pathlib import Path
from collections import defaultdict


def load_latest_report():
    """加载最新的测试报告"""
    reports_dir = Path(__file__).parent / "reports"
    json_files = list(reports_dir.glob('mock_test_report_*.json'))
    
    if not json_files:
        print("❌ 未找到测试报告")
        return None
    
    latest = sorted(json_files, key=lambda x: x.stat().st_mtime)[-1]
    print(f"📊 加载报告: {latest.name}")
    
    with open(latest, 'r', encoding='utf-8') as f:
        return json.load(f)


def analyze_by_category(report):
    """按分类分析"""
    print("\n" + "="*70)
    print("📋 按分类详细统计")
    print("="*70)
    
    by_category = report['by_category']
    
    # 排序
    categories = sorted(by_category.items(), 
                       key=lambda x: float(x[1]['pass_rate'].rstrip('%')), 
                       reverse=True)
    
    print(f"\n{'分类':<20} {'案例数':<8} {'通过':<8} {'通过率':<10} {'平均分':<10}")
    print("-" * 70)
    
    for cat, stats in categories:
        print(f"{cat:<20} {stats['total']:<8} {stats['passed']:<8} "
              f"{stats['pass_rate']:<10} {stats['avg_score']}/100")


def analyze_by_complexity(report):
    """按复杂度分析"""
    print("\n" + "="*70)
    print("🎯 按复杂度统计")
    print("="*70)
    
    complexity_stats = defaultdict(lambda: {'total': 0, 'passed': 0, 'scores': []})
    
    for result in report['results']:
        complexity = result.get('complexity', 'medium')
        complexity_stats[complexity]['total'] += 1
        if result['status'] == 'passed':
            complexity_stats[complexity]['passed'] += 1
        complexity_stats[complexity]['scores'].append(result['score'])
    
    print(f"\n{'复杂度':<12} {'案例数':<8} {'通过':<8} {'通过率':<10} {'平均分':<10}")
    print("-" * 70)
    
    for complexity in ['easy', 'medium', 'hard']:
        if complexity in complexity_stats:
            stats = complexity_stats[complexity]
            pass_rate = (stats['passed'] / stats['total'] * 100) if stats['total'] > 0 else 0
            avg_score = sum(stats['scores']) / len(stats['scores']) if stats['scores'] else 0
            
            print(f"{complexity:<12} {stats['total']:<8} {stats['passed']:<8} "
                  f"{pass_rate:>6.1f}%    {avg_score:>6.1f}/100")


def analyze_failures(report):
    """分析失败案例"""
    print("\n" + "="*70)
    print("❌ 失败案例详细分析")
    print("="*70)
    
    failed_cases = [r for r in report['results'] if r['status'] == 'failed']
    
    if not failed_cases:
        print("\n🎉 没有失败案例！")
        return
    
    print(f"\n共 {len(failed_cases)} 个失败案例:\n")
    
    # 按分类分组
    by_category = defaultdict(list)
    for case in failed_cases:
        by_category[case['category']].append(case)
    
    for cat, cases in sorted(by_category.items()):
        print(f"\n【{cat}】- {len(cases)}个失败:")
        for case in cases:
            print(f"  • #{case['id']:03d} {case['name'][:50]:<50} "
                  f"得分:{case['score']:.1f} 复杂度:{case['complexity']}")


def analyze_top_performers(report):
    """分析表现最好的案例"""
    print("\n" + "="*70)
    print("🏆 表现最好的案例 (Top 10)")
    print("="*70)
    
    sorted_cases = sorted(report['results'], key=lambda x: x['score'], reverse=True)
    
    print(f"\n{'排名':<6} {'ID':<8} {'案例名称':<40} {'分类':<15} {'得分':<10}")
    print("-" * 90)
    
    for i, case in enumerate(sorted_cases[:10], 1):
        name = case['name'][:38] if len(case['name']) > 38 else case['name']
        print(f"{i:<6} #{case['id']:03d}   {name:<40} {case['category']:<15} {case['score']}/100")


def analyze_need_improvement(report):
    """分析需要改进的案例"""
    print("\n" + "="*70)
    print("⚠️  需要改进的案例 (得分 < 80)")
    print("="*70)
    
    low_score_cases = [r for r in report['results'] if r['score'] < 80]
    low_score_cases.sort(key=lambda x: x['score'])
    
    if not low_score_cases:
        print("\n🎉 所有案例得分都 ≥ 80！")
        return
    
    print(f"\n共 {len(low_score_cases)} 个需要改进的案例:\n")
    print(f"{'ID':<8} {'案例名称':<45} {'分类':<15} {'得分':<10} {'状态':<10}")
    print("-" * 95)
    
    for case in low_score_cases[:20]:  # 显示前20个
        name = case['name'][:43] if len(case['name']) > 43 else case['name']
        status = '✅通过' if case['status'] == 'passed' else '❌失败'
        print(f"#{case['id']:03d}   {name:<45} {case['category']:<15} "
              f"{case['score']:>5.1f}    {status}")


def generate_recommendations(report):
    """生成改进建议"""
    print("\n" + "="*70)
    print("💡 改进建议")
    print("="*70)
    
    summary = report['summary']
    pass_rate = float(summary['pass_rate'].rstrip('%'))
    avg_score = summary['avg_score']
    
    failed_cases = [r for r in report['results'] if r['status'] == 'failed']
    low_score_cases = [r for r in report['results'] if r['score'] < 80]
    
    print()
    
    # 整体评价
    if pass_rate >= 90 and avg_score >= 90:
        print("✅ 【整体评价】优秀！系统质量很高")
    elif pass_rate >= 80 and avg_score >= 85:
        print("✅ 【整体评价】良好！系统基本达到要求")
    elif pass_rate >= 70:
        print("⚠️  【整体评价】合格，但有改进空间")
    else:
        print("❌ 【整体评价】需要重点改进")
    
    print()
    
    # 具体建议
    print("【具体建议】")
    
    if failed_cases:
        # 分析失败案例的分类
        failed_by_cat = defaultdict(int)
        for case in failed_cases:
            failed_by_cat[case['category']] += 1
        
        print(f"\n1. 优先修复 {len(failed_cases)} 个失败案例:")
        for cat, count in sorted(failed_by_cat.items(), key=lambda x: x[1], reverse=True):
            print(f"   • {cat}: {count}个失败")
    
    if low_score_cases:
        print(f"\n2. 提升 {len(low_score_cases)} 个低分案例的质量 (目标: ≥80分)")
    
    # 分类建议
    by_category = report['by_category']
    weak_categories = [(cat, float(stats['pass_rate'].rstrip('%'))) 
                      for cat, stats in by_category.items() 
                      if float(stats['pass_rate'].rstrip('%')) < 80]
    
    if weak_categories:
        weak_categories.sort(key=lambda x: x[1])
        print(f"\n3. 重点关注以下分类:")
        for cat, rate in weak_categories:
            print(f"   • {cat}: 通过率仅 {rate:.1f}%")
    
    # 复杂度建议
    complexity_stats = defaultdict(lambda: {'total': 0, 'passed': 0})
    for result in report['results']:
        complexity = result.get('complexity', 'medium')
        complexity_stats[complexity]['total'] += 1
        if result['status'] == 'passed':
            complexity_stats[complexity]['passed'] += 1
    
    hard_pass_rate = (complexity_stats['hard']['passed'] / 
                     complexity_stats['hard']['total'] * 100) if complexity_stats['hard']['total'] > 0 else 100
    
    if hard_pass_rate < 80:
        print(f"\n4. 提升复杂案例的处理能力:")
        print(f"   • 困难案例通过率: {hard_pass_rate:.1f}% (建议 ≥ 80%)")
    
    print()


def export_summary_csv(report):
    """导出CSV摘要"""
    output_file = Path(__file__).parent / "reports" / "test_summary.csv"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        # 写入表头
        f.write("ID,案例名称,分类,复杂度,状态,得分,评级,耗时(秒)\n")
        
        # 写入数据
        for result in report['results']:
            f.write(f"{result['id']},"
                   f"{result['name']},"
                   f"{result['category']},"
                   f"{result.get('complexity', 'medium')},"
                   f"{result['status']},"
                   f"{result['score']},"
                   f"{result['grade']},"
                   f"{result['duration']}\n")
    
    print(f"\n📁 CSV摘要已导出: {output_file}")


def main():
    """主函数"""
    print("="*70)
    print("📊 完整测试结果分析 - 111个案例")
    print("="*70)
    
    # 加载报告
    report = load_latest_report()
    if not report:
        return
    
    # 基本统计
    summary = report['summary']
    print(f"\n✅ 测试时间: {report['timestamp'][:19]}")
    print(f"✅ 总案例数: {summary['total']}")
    print(f"✅ 通过数量: {summary['passed']} ({summary['pass_rate']})")
    print(f"✅ 平均得分: {summary['avg_score']}/100")
    print(f"✅ 总耗时:   {summary['total_duration']/60:.1f}分钟")
    
    # 评级分布
    grades = report['grade_distribution']
    print(f"\n✅ 评级分布:")
    print(f"   A级(90+): {grades['A']}个 ({grades['A']/summary['total']*100:.1f}%)")
    print(f"   B级(80-89): {grades['B']}个 ({grades['B']/summary['total']*100:.1f}%)")
    print(f"   C级(70-79): {grades['C']}个 ({grades['C']/summary['total']*100:.1f}%)")
    print(f"   D级(<70): {grades['D']}个 ({grades['D']/summary['total']*100:.1f}%)")
    
    # 详细分析
    analyze_by_category(report)
    analyze_by_complexity(report)
    analyze_top_performers(report)
    analyze_failures(report)
    analyze_need_improvement(report)
    generate_recommendations(report)
    
    # 导出CSV
    export_summary_csv(report)
    
    print("\n" + "="*70)
    print("✅ 分析完成")
    print("="*70)


if __name__ == "__main__":
    main()
