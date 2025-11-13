#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
对比两轮测试结果，识别哪些测试的状态发生了变化
"""
import json
import re
from pathlib import Path
from collections import defaultdict

def parse_round1_results():
    """解析第一轮测试结果（来自JSON）"""
    results_file = Path("test_results/batch_test_results.json")
    
    if not results_file.exists():
        print("[ERROR] Round 1 results not found")
        return {}
    
    with open(results_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    results = {}
    for item in data.get('results', []):
        test_id = item.get('id', item.get('file_path', ''))
        results[test_id] = {
            'status': item['status'],
            'file': item.get('file_path', '')
        }
    
    return results

def parse_round2_results():
    """解析第二轮测试结果（来自日志文件）"""
    log_file = Path("test_results/batch_test_output_v2.txt")
    
    if not log_file.exists():
        print("[ERROR] Round 2 log not found")
        return {}
    
    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # 提取测试结果
    # 格式示例：[1/541] 名称: XXX
    #          ID: tests-xxx
    #          文件: tests\xxx.py
    #          状态: 通过 PASS 或 失败 FAIL
    
    results = {}
    
    # 按块分割
    blocks = re.split(r'\[\d+/541\]', content)
    
    for block in blocks[1:]:  # 跳过第一个空块
        # 提取ID
        id_match = re.search(r'ID:\s*([^\n]+)', block)
        if not id_match:
            continue
        
        test_id = id_match.group(1).strip()
        
        # 提取文件
        file_match = re.search(r'文件:\s*([^\n]+)', block)
        file_path = file_match.group(1).strip() if file_match else ''
        
        # 提取状态
        if 'PASS' in block:
            status = 'success'
        elif 'FAIL' in block:
            status = 'failed'
        else:
            status = 'unknown'
        
        results[test_id] = {
            'status': status,
            'file': file_path
        }
    
    return results

def compare_results(round1, round2):
    """对比两轮结果"""
    
    # 分类
    improved = []  # 第一轮失败，第二轮成功
    regressed = []  # 第一轮成功，第二轮失败
    still_passing = []  # 两轮都成功
    still_failing = []  # 两轮都失败
    new_tests = []  # 只在第二轮中出现
    
    # 对比
    for test_id in round2:
        r2_status = round2[test_id]['status']
        
        if test_id in round1:
            r1_status = round1[test_id]['status']
            
            if r1_status == 'failed' and r2_status == 'success':
                improved.append(test_id)
            elif r1_status == 'success' and r2_status == 'failed':
                regressed.append(test_id)
            elif r1_status == 'success' and r2_status == 'success':
                still_passing.append(test_id)
            elif r1_status == 'failed' and r2_status == 'failed':
                still_failing.append(test_id)
        else:
            new_tests.append(test_id)
    
    return {
        'improved': improved,
        'regressed': regressed,
        'still_passing': still_passing,
        'still_failing': still_failing,
        'new_tests': new_tests
    }

def main():
    print("="*70)
    print("两轮测试结果对比 - Test Rounds Comparison")
    print("="*70)
    
    print("\n[1/3] 加载第一轮结果...")
    round1 = parse_round1_results()
    print(f"[OK] 第一轮: {len(round1)} 个测试")
    
    print("\n[2/3] 加载第二轮结果...")
    round2 = parse_round2_results()
    print(f"[OK] 第二轮: {len(round2)} 个测试")
    
    print("\n[3/3] 对比分析...")
    comparison = compare_results(round1, round2)
    
    # 显示结果
    print("\n" + "="*70)
    print("对比结果 - Comparison Results")
    print("="*70)
    
    print(f"\n✅ 改进的测试（第一轮失败→第二轮成功）: {len(comparison['improved'])} 个")
    if comparison['improved']:
        print("   前5个:")
        for test_id in comparison['improved'][:5]:
            print(f"   - {test_id}")
        if len(comparison['improved']) > 5:
            print(f"   ... 还有 {len(comparison['improved']) - 5} 个")
    
    print(f"\n❌ 退步的测试（第一轮成功→第二轮失败）: {len(comparison['regressed'])} 个")
    if comparison['regressed']:
        print("   前5个:")
        for test_id in comparison['regressed'][:5]:
            print(f"   - {test_id}")
        if len(comparison['regressed']) > 5:
            print(f"   ... 还有 {len(comparison['regressed']) - 5} 个")
    
    print(f"\n✅ 持续通过: {len(comparison['still_passing'])} 个")
    print(f"❌ 持续失败: {len(comparison['still_failing'])} 个")
    
    # 计算净改进
    net_improvement = len(comparison['improved']) - len(comparison['regressed'])
    
    print("\n" + "="*70)
    print("总结 - Summary")
    print("="*70)
    print(f"\n净改进: {net_improvement:+d} 个测试")
    
    if net_improvement > 0:
        print(f"[OK] 修复效果积极！改进了 {net_improvement} 个测试")
    elif net_improvement < 0:
        print(f"[WARN] 修复引入了问题！退步了 {abs(net_improvement)} 个测试")
        print(f"       建议回滚并重新制定修复策略")
    else:
        print(f"[INFO] 修复效果中性，改进和退步持平")
    
    # 保存详细对比
    output = {
        'comparison_time': str(Path("test_results/batch_test_output_v2.txt").stat().st_mtime),
        'round1_total': len(round1),
        'round2_total': len(round2),
        'improved': comparison['improved'],
        'regressed': comparison['regressed'],
        'still_passing': comparison['still_passing'],
        'still_failing': comparison['still_failing'],
        'net_improvement': net_improvement
    }
    
    with open('test_results/comparison_report.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n[OK] 详细对比已保存: test_results/comparison_report.json")
    print("")

if __name__ == '__main__':
    main()

