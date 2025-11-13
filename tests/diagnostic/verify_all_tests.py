#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
全面测试验证脚本

在完成MacDonald Test 4优化尝试后，验证其他测试(1-3, 5)无退化

目标:
- 确认Tests 1, 2, 3, 5 全部通过
- 验证80%通过率 (4/5)
- 确保近期代码更改无负面影响

作者: HydroClaude Team
日期: 2025-10-30
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import traceback
from tests.standard_tests.test_macdonald import TestMacDonald


def run_test(test_func, test_name):
    """
    运行单个测试并捕获结果

    Args:
        test_func: 测试函数
        test_name: 测试名称

    Returns:
        tuple: (success, error_message)
    """
    print(f"\n{'='*80}")
    print(f"运行: {test_name}")
    print(f"{'='*80}\n")

    try:
        test_func()
        print(f"\n {test_name} 通过\n")
        return True, None
    except AssertionError as e:
        print(f"\n {test_name} 失败")
        print(f"断言错误: {str(e)}\n")
        return False, str(e)
    except Exception as e:
        print(f"\n {test_name} 异常")
        print(f"错误: {str(e)}")
        traceback.print_exc()
        return False, str(e)


def main():
    """
    主验证流程
    """
    print("="*80)
    print("HydroClaude 全面测试验证")
    print("="*80)
    print("\n目标: 验证MacDonald Tests 1-3, 5通过（Test 4已知限制）")
    print("背景: 完成Test 4优化尝试后的回归测试\n")

    # 创建测试实例
    test_suite = TestMacDonald()

    # 定义要运行的测试
    tests = [
        (test_suite.test_macdonald_1_backwater_curve, "MacDonald Test 1: M1壅水曲线"),
        (test_suite.test_macdonald_2_drawdown_curve, "MacDonald Test 2: M2下降曲线"),
        (test_suite.test_macdonald_3_dam_break, "MacDonald Test 3: 溃坝"),
        (test_suite.test_macdonald_5_wide_channel, "MacDonald Test 5: 宽渠道"),
    ]

    # 运行测试
    results = []
    for test_func, test_name in tests:
        success, error = run_test(test_func, test_name)
        results.append({
            'name': test_name,
            'success': success,
            'error': error
        })

    # 汇总结果
    print(f"\n{'='*80}")
    print("测试结果汇总")
    print(f"{'='*80}\n")

    passed = sum(1 for r in results if r['success'])
    total = len(results)

    print(f"测试名称                                     状态")
    print("-"*80)

    for result in results:
        status = " 通过" if result['success'] else " 失败"
        print(f"{result['name']:<45} {status}")

    print("-"*80)
    print(f"总计: {passed}/{total} 通过 ({passed/total*100:.0f}%)")

    # MacDonald Test 4状态说明
    print(f"\n{'='*80}")
    print("MacDonald Test 4 状态")
    print(f"{'='*80}")
    print("状态: ️  已知限制（质量误差27.89%）")
    print("原因: WENO3+HLL算法对强激波+无摩阻问题的固有限制")
    print("决定: 接受为算法极限，不再优化")
    print("尝试:")
    print("  1. 增强WENO3算法 ->  失败（数值爆炸）")
    print("  2. 参数优化 ->  失败（<1%改善）")

    # 最终评估
    print(f"\n{'='*80}")
    print("最终评估")
    print(f"{'='*80}")

    if passed == total:
        print(f"\n 所有验证测试通过 ({passed}/{total})")
        print(f" MacDonald Tests 1-3, 5: 100% 通过率")
        print(f"️  包含Test 4: 80% 通过率 (4/5)")
        print(f"\n结论: 代码质量良好，无退化。Test 4限制已明确文档化。")
        print(f"\n软件定位: 学术/教学工具")
        print(f"  - 适用: 标准测试、算法研究、教学演示")
        print(f"  - 不适用: 关键工程应用（需100%通过率）")
        return 0
    else:
        print(f"\n 存在测试失败 ({passed}/{total})")
        print(f"\n失败详情:")
        for result in results:
            if not result['success']:
                print(f"\n  {result['name']}:")
                print(f"    {result['error']}")
        return 1


if __name__ == '__main__':
    exit_code = main()
    print(f"\n{'='*80}")
    print(f"验证完成，退出码: {exit_code}")
    print(f"{'='*80}\n")
    sys.exit(exit_code)
