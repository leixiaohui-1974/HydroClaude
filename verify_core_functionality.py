#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
验证核心功能的正确性
测试基础库是否工作正常
"""

import sys
import os
import subprocess
from pathlib import Path
import time

# 核心测试列表（必须100%通过）
CORE_TESTS = [
    {
        'name': '核心功能验证V2',
        'path': 'tests/core_functionality_verification_v2.py',
        'timeout': 60,
        'critical': True,
        'description': '验证HydrostaticCanalSolver基础功能'
    },
    {
        'name': 'Lake at Rest (Well-Balanced)',
        'path': 'tests/test_lake_at_rest_wb.py',
        'timeout': 60,
        'critical': True,
        'description': '验证数值格式的well-balanced特性'
    },
    {
        'name': '单闸门流动V2',
        'path': 'examples/example_01_canal_flow/scripts/07_sluice_gate_flow_v2.py',
        'timeout': 120,
        'critical': True,
        'description': '验证水工结构处理'
    },
    {
        'name': '基础均匀流V2',
        'path': 'examples/example_01_canal_flow/scripts/01_basic_v2.py',
        'timeout': 60,
        'critical': True,
        'description': '验证稳态求解'
    },
    {
        'name': '边界条件V2',
        'path': 'examples/example_01_canal_flow/scripts/04_boundary_conditions_v2.py',
        'timeout': 60,
        'critical': False,
        'description': '验证边界条件处理'
    },
]

def run_single_test(test_info):
    """运行单个测试"""
    
    test_path = Path(test_info['path'])
    
    if not test_path.exists():
        return {
            'status': 'skip',
            'message': f'文件不存在: {test_path}',
            'time': 0
        }
    
    print(f"\n{'='*70}")
    print(f"测试: {test_info['name']}")
    print(f"文件: {test_path}")
    print(f"说明: {test_info['description']}")
    print(f"{'='*70}")
    
    try:
        start_time = time.time()
        
        # 设置UTF-8环境变量
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        
        result = subprocess.run(
            [sys.executable, str(test_path)],
            capture_output=True,
            text=True,
            timeout=test_info['timeout'],
            encoding='utf-8',
            errors='ignore',
            env=env
        )
        
        elapsed = time.time() - start_time
        
        # 分析输出
        output = result.stdout + result.stderr
        
        # 查找关键指标
        has_error = False
        error_messages = []
        
        if result.returncode != 0:
            has_error = True
            error_messages.append(f"Exit code: {result.returncode}")
        
        # 查找特定错误标志
        if 'NaN' in output or 'nan' in output:
            has_error = True
            error_messages.append("检测到NaN")
        
        if 'Inf' in output or 'inf' in output:
            has_error = True
            error_messages.append("检测到Inf")
        
        if 'Error' in output or 'ERROR' in output:
            has_error = True
            error_messages.append("检测到Error")
        
        if 'Traceback' in output:
            has_error = True
            error_messages.append("检测到异常")
        
        # 查找成功标志
        success_indicators = [
            '[OK]',
            'PASS',
            '流量误差: 0.00',
            '100%通过',
        ]
        
        has_success = any(indicator in output for indicator in success_indicators)
        
        # 决定状态
        if has_error:
            status = 'FAIL'
            message = '; '.join(error_messages)
        elif has_success:
            status = 'PASS'
            message = '测试通过'
        else:
            status = 'UNKNOWN'
            message = '无法确定结果'
        
        # 打印部分输出
        print(f"\n输出摘要（最后30行）:")
        output_lines = output.split('\n')
        for line in output_lines[-30:]:
            if line.strip():
                print(f"  {line}")
        
        return {
            'status': status,
            'message': message,
            'time': elapsed,
            'output': output
        }
    
    except subprocess.TimeoutExpired:
        return {
            'status': 'TIMEOUT',
            'message': f'超时（>{test_info["timeout"]}s）',
            'time': test_info['timeout']
        }
    
    except Exception as e:
        return {
            'status': 'ERROR',
            'message': str(e),
            'time': 0
        }

def main():
    print("="*70)
    print("核心功能验证 - Core Functionality Verification")
    print("="*70)
    print("\n目标: 验证基础库是否正确工作")
    print(f"测试数量: {len(CORE_TESTS)}")
    print(f"关键测试: {sum(1 for t in CORE_TESTS if t['critical'])}")
    
    results = []
    
    for i, test in enumerate(CORE_TESTS, 1):
        print(f"\n\n[{i}/{len(CORE_TESTS)}] 运行测试...")
        
        result = run_single_test(test)
        result['name'] = test['name']
        result['critical'] = test['critical']
        results.append(result)
        
        # 实时显示结果
        status_symbol = {
            'PASS': '[OK]',
            'FAIL': '[FAIL]',
            'TIMEOUT': '[TIMEOUT]',
            'ERROR': '[ERROR]',
            'skip': '[SKIP]',
            'UNKNOWN': '[?]'
        }
        
        symbol = status_symbol.get(result['status'], '[?]')
        print(f"\n{symbol} {test['name']}: {result['message']} ({result['time']:.1f}s)")
    
    # 总结报告
    print("\n\n" + "="*70)
    print("验证结果总结")
    print("="*70)
    
    passed = sum(1 for r in results if r['status'] == 'PASS')
    failed = sum(1 for r in results if r['status'] == 'FAIL')
    other = len(results) - passed - failed
    
    print(f"\n总计: {len(results)} 个测试")
    print(f"通过: {passed}")
    print(f"失败: {failed}")
    print(f"其他: {other}")
    
    print(f"\n详细结果:")
    for r in results:
        status_str = f"[{r['status']}]".ljust(10)
        critical_str = "[关键]" if r['critical'] else "      "
        print(f"  {status_str} {critical_str} {r['name']}")
        if r['status'] != 'PASS':
            print(f"             原因: {r['message']}")
    
    # 关键测试分析
    critical_results = [r for r in results if r['critical']]
    critical_passed = sum(1 for r in critical_results if r['status'] == 'PASS')
    
    print(f"\n关键测试: {critical_passed}/{len(critical_results)} 通过")
    
    # 结论
    print(f"\n" + "="*70)
    print("结论")
    print("="*70)
    
    if critical_passed == len(critical_results):
        print("\n[OK] 所有关键测试通过！")
        print("结论: 基础库工作正常")
        print("建议: 可以继续测试复杂场景")
    elif critical_passed > 0:
        print("\n[WARN] 部分关键测试失败")
        print("结论: 基础库存在问题")
        print("建议: 需要修复失败的关键测试")
    else:
        print("\n[ERROR] 所有关键测试失败！")
        print("结论: 基础库有严重问题")
        print("建议: 必须先修复基础库")
    
    print("\n" + "="*70)
    
    return 0 if passed == len(results) else 1

if __name__ == '__main__':
    exit(main())

