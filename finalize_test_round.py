#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试完成后的最终处理
生成完整报告、对比分析、优化建议
"""
import json
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict

def parse_test_log():
    """解析第二轮测试日志"""
    log_file = Path("test_results/batch_test_output_v2.txt")
    
    if not log_file.exists():
        print("[ERROR] Log file not found")
        return None
    
    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # 提取所有测试结果
    results = []
    
    # 使用正则表达式提取每个测试块
    pattern = r'\[(\d+)/541\]\s+.*?ID:\s*([^\n]+).*?文件:\s*([^\n]+).*?状态:\s*(通过 PASS|失败 FAIL)'
    matches = re.finditer(pattern, content, re.DOTALL)
    
    for match in matches:
        test_num = int(match.group(1))
        test_id = match.group(2).strip()
        file_path = match.group(3).strip()
        status = 'success' if 'PASS' in match.group(4) else 'failed'
        
        results.append({
            'number': test_num,
            'id': test_id,
            'file': file_path,
            'status': status
        })
    
    return results

def load_round1_results():
    """加载第一轮结果"""
    results_file = Path("test_results/batch_test_results.json")
    
    if not results_file.exists():
        return {}
    
    with open(results_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    round1 = {}
    for result in data.get('results', []):
        test_id = result.get('id', '')
        round1[test_id] = result['status']
    
    return round1

def compare_rounds(round1, round2_results):
    """对比两轮结果"""
    improved = []
    regressed = []
    still_passing = []
    still_failing = []
    
    for r2 in round2_results:
        test_id = r2['id']
        r2_status = r2['status']
        
        if test_id in round1:
            r1_status = round1[test_id]
            
            if r1_status == 'failed' and r2_status == 'success':
                improved.append(r2)
            elif r1_status == 'success' and r2_status == 'failed':
                regressed.append(r2)
            elif r1_status == 'success' and r2_status == 'success':
                still_passing.append(r2)
            elif r1_status == 'failed' and r2_status == 'failed':
                still_failing.append(r2)
    
    return {
        'improved': improved,
        'regressed': regressed,
        'still_passing': still_passing,
        'still_failing': still_failing
    }

def generate_final_report(round2_results, comparison):
    """生成最终报告"""
    total = len(round2_results)
    passed = sum(1 for r in round2_results if r['status'] == 'success')
    failed = total - passed
    pass_rate = passed / total * 100 if total > 0 else 0
    
    report = f"""# 第二轮测试最终报告
# Round 2 Test Final Report

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**测试完成**: {'是' if total >= 541 else '否 (进行中)'}

---

## 📊 总体结果

### 基本统计
```
总测试数: {total}
通过: {passed} ({pass_rate:.1f}%)
失败: {failed} ({(failed/total*100):.1f}%)
```

### 与第一轮对比
```
第一轮: 106/541 (19.6%)
第二轮: {passed}/{total} ({pass_rate:.1f}%)
变化: {(pass_rate - 19.6):+.1f}%
```

---

## 🔄 详细对比分析

### 改进的测试（第一轮失败→第二轮成功）
**数量**: {len(comparison['improved'])} 个

"""
    
    if comparison['improved']:
        report += "**示例**:\n"
        for test in comparison['improved'][:10]:
            report += f"- {test['file']}\n"
        if len(comparison['improved']) > 10:
            report += f"- ... 还有 {len(comparison['improved']) - 10} 个\n"
    
    report += f"""

### 退步的测试（第一轮成功→第二轮失败）
**数量**: {len(comparison['regressed'])} 个

"""
    
    if comparison['regressed']:
        report += "**示例**:\n"
        for test in comparison['regressed'][:10]:
            report += f"- {test['file']}\n"
        if len(comparison['regressed']) > 10:
            report += f"- ... 还有 {len(comparison['regressed']) - 10} 个\n"
    
    report += f"""

### 持续通过
**数量**: {len(comparison['still_passing'])} 个

### 持续失败
**数量**: {len(comparison['still_failing'])} 个

---

## 🎯 修复效果评估

### 净改进
```
改进的测试: {len(comparison['improved'])} 个
退步的测试: {len(comparison['regressed'])} 个
净改进: {len(comparison['improved']) - len(comparison['regressed']):+d} 个
```

### 效果判断
"""
    
    net_improvement = len(comparison['improved']) - len(comparison['regressed'])
    
    if net_improvement > 10:
        report += "✅ **优秀** - 修复效果显著\n"
    elif net_improvement > 5:
        report += "✅ **良好** - 修复效果明显\n"
    elif net_improvement > 0:
        report += "✅ **有效** - 修复有积极作用\n"
    elif net_improvement == 0:
        report += "⚠️ **中性** - 修复效果持平\n"
    else:
        report += "❌ **退步** - 修复引入了新问题\n"
    
    report += f"""

---

## 📈 通过率趋势

### 历史数据
```
第一轮: 19.6%
第二轮: {pass_rate:.1f}%
```

### 改进幅度
```
绝对改进: {(pass_rate - 19.6):+.1f}%
相对改进: {((pass_rate - 19.6) / 19.6 * 100):+.1f}%
```

---

## 🚀 下一步建议

### 基于当前结果

"""
    
    if pass_rate >= 25:
        report += """✅ **通过率≥25%** - 修复非常成功

建议行动:
1. 分析剩余失败的测试
2. 识别Top失败模式
3. 制定第三轮优化计划
4. 目标: 30-35%通过率
5. 开始Web系统集成测试
"""
    elif pass_rate >= 20:
        report += """✅ **通过率20-25%** - 修复成功

建议行动:
1. 继续当前修复策略
2. 分析失败模式并针对性优化
3. 目标: 25-30%通过率
4. 准备Web系统集成
"""
    elif pass_rate >= 19.6:
        report += """⚠️ **通过率19.6-20%** - 小幅改进

建议行动:
1. 分析哪些修复有效，哪些无效
2. 优化修复策略
3. 目标: 25%通过率
"""
    else:
        report += """❌ **通过率<19.6%** - 修复效果不佳

建议行动:
1. 回滚部分或全部修改
2. 重新分析问题
3. 制定更保守的修复策略
"""
    
    report += """

---

## 📋 执行清单

### 立即执行
- [ ] 查看完整对比分析
  ```bash
  cat test_results/round2_final_report.md
  ```

- [ ] 分析失败模式
  ```bash
  python analyze_failure_patterns.py
  ```

- [ ] 识别优化机会
  ```bash
  python optimize_failing_scenarios.py
  ```

### 后续工作
- [ ] 制定第三轮修复计划
- [ ] 执行针对性优化
- [ ] 运行第三轮测试
- [ ] Web系统集成测试

---

**Generated by HydroClaude Test System**
**Last Updated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    return report

def main():
    print("="*70)
    print("测试结果最终处理 - Finalize Test Round")
    print("="*70)
    
    print("\n[1/4] 解析第二轮测试日志...")
    round2_results = parse_test_log()
    
    if not round2_results:
        print("[ERROR] 无法解析测试日志")
        return
    
    print(f"[OK] 解析了 {len(round2_results)} 个测试结果")
    
    print("\n[2/4] 加载第一轮结果...")
    round1 = load_round1_results()
    print(f"[OK] 加载了 {len(round1)} 个第一轮结果")
    
    print("\n[3/4] 对比分析...")
    comparison = compare_rounds(round1, round2_results)
    
    print(f"\n对比结果:")
    print(f"  改进: {len(comparison['improved'])} 个")
    print(f"  退步: {len(comparison['regressed'])} 个")
    print(f"  持续通过: {len(comparison['still_passing'])} 个")
    print(f"  持续失败: {len(comparison['still_failing'])} 个")
    
    net = len(comparison['improved']) - len(comparison['regressed'])
    print(f"  净改进: {net:+d} 个")
    
    print("\n[4/4] 生成最终报告...")
    report = generate_final_report(round2_results, comparison)
    
    # 保存报告
    report_file = Path("test_results/round2_final_report.md")
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"[OK] 报告已保存: {report_file}")
    
    # 保存对比数据
    comparison_data = {
        'round2_total': len(round2_results),
        'round2_passed': sum(1 for r in round2_results if r['status'] == 'success'),
        'round1_passed': 106,
        'round1_total': 541,
        'improved_count': len(comparison['improved']),
        'regressed_count': len(comparison['regressed']),
        'net_improvement': net,
        'improved_tests': [t['id'] for t in comparison['improved']],
        'regressed_tests': [t['id'] for t in comparison['regressed']]
    }
    
    with open('test_results/round2_comparison.json', 'w', encoding='utf-8') as f:
        json.dump(comparison_data, f, indent=2, ensure_ascii=False)
    
    print("[OK] 对比数据已保存: test_results/round2_comparison.json")
    
    # 显示摘要
    passed = sum(1 for r in round2_results if r['status'] == 'success')
    total = len(round2_results)
    pass_rate = passed / total * 100
    
    print("\n" + "="*70)
    print("最终结果摘要")
    print("="*70)
    print(f"\n第二轮: {passed}/{total} ({pass_rate:.1f}%)")
    print(f"第一轮: 106/541 (19.6%)")
    print(f"变化: {(pass_rate - 19.6):+.1f}%")
    
    if pass_rate >= 19.6:
        print("\n✅ 修复成功！通过率提升")
    else:
        print("\n⚠️ 需要调整策略")
    
    print("\n" + "="*70)
    print("下一步:")
    print("  1. 查看完整报告: cat test_results/round2_final_report.md")
    print("  2. 分析失败模式: python analyze_failure_patterns.py")
    print("  3. 制定优化计划")
    print("="*70 + "\n")

if __name__ == '__main__':
    main()

