#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
全面测试执行器

按顺序执行所有4周的测试，自动生成报告。

使用方法：
    python3 run_comprehensive_tests.py --week 1
    python3 run_comprehensive_tests.py --all

Author: Claude (AI Assistant)
Date: 2025-10-27
"""

import sys
import os
import argparse
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class ComprehensiveTestRunner:
    """全面测试运行器"""
    
    def __init__(self):
        """初始化"""
        self.results = {
            'start_time': datetime.now().isoformat(),
            'weeks': {}
        }
    
    def run_week1(self):
        """运行Week 1: 解析解验证"""
        print("\n" + "="*80)
        print("Week 1: 解析解验证")
        print("="*80)
        
        try:
            # 导入Week 1测试
            from tests.test_analytical_validation import AnalyticalValidationTest
            
            test = AnalyticalValidationTest()
            passed, failed = test.run_all()
            
            self.results['weeks']['week1'] = {
                'name': '解析解验证',
                'passed': passed,
                'failed': failed,
                'total': passed + failed,
                'pass_rate': passed / (passed + failed) * 100 if (passed + failed) > 0 else 0,
                'status': 'completed'
            }
            
            return passed, failed
        
        except Exception as e:
            print(f"❌ Week 1测试失败: {e}")
            import traceback
            traceback.print_exc()
            
            self.results['weeks']['week1'] = {
                'name': '解析解验证',
                'status': 'failed',
                'error': str(e)
            }
            
            return 0, 1
    
    def run_week2(self):
        """运行Week 2: 国际基准算例"""
        print("\n" + "="*80)
        print("Week 2: 国际基准算例")
        print("="*80)
        
        try:
            from tests.test_benchmark_cases import BenchmarkValidationTest
            
            test = BenchmarkValidationTest()
            passed, failed = test.run_all()
            
            self.results['weeks']['week2'] = {
                'name': '国际基准算例',
                'passed': passed,
                'failed': failed,
                'total': passed + failed,
                'pass_rate': passed / (passed + failed) * 100 if (passed + failed) > 0 else 0,
                'status': 'completed'
            }
            
            return passed, failed
        
        except Exception as e:
            print(f"❌ Week 2测试失败: {e}")
            self.results['weeks']['week2'] = {
                'name': '国际基准算例',
                'status': 'failed',
                'error': str(e)
            }
            return 0, 1
    
    def run_week3(self):
        """运行Week 3: 极端条件"""
        print("\n" + "="*80)
        print("Week 3: 极端条件与鲁棒性")
        print("="*80)
        
        try:
            from tests.test_extreme_conditions import ExtremeConditionTest
            
            test = ExtremeConditionTest()
            passed, failed = test.run_all()
            
            self.results['weeks']['week3'] = {
                'name': '极端条件',
                'passed': passed,
                'failed': failed,
                'total': passed + failed,
                'pass_rate': passed / (passed + failed) * 100 if (passed + failed) > 0 else 0,
                'status': 'completed'
            }
            
            return passed, failed
        
        except Exception as e:
            print(f"❌ Week 3测试失败: {e}")
            self.results['weeks']['week3'] = {
                'name': '极端条件',
                'status': 'failed',
                'error': str(e)
            }
            return 0, 1
    
    def run_week4(self):
        """运行Week 4: 长时间稳定性"""
        print("\n" + "="*80)
        print("Week 4: 长时间稳定性")
        print("="*80)
        
        try:
            from tests.test_long_term_stability import LongTermStabilityTest
            
            test = LongTermStabilityTest()
            passed, failed = test.run_all()
            
            self.results['weeks']['week4'] = {
                'name': '长时间稳定性',
                'passed': passed,
                'failed': failed,
                'total': passed + failed,
                'pass_rate': passed / (passed + failed) * 100 if (passed + failed) > 0 else 0,
                'status': 'completed'
            }
            
            return passed, failed
        
        except Exception as e:
            print(f"❌ Week 4测试失败: {e}")
            self.results['weeks']['week4'] = {
                'name': '长时间稳定性',
                'status': 'failed',
                'error': str(e)
            }
            return 0, 1
    
    def generate_summary_report(self):
        """生成总结报告"""
        print("\n" + "="*80)
        print("全面测试总结报告")
        print("="*80)
        
        self.results['end_time'] = datetime.now().isoformat()
        
        # 统计
        total_passed = 0
        total_failed = 0
        weeks_completed = 0
        
        for week_name, week_data in self.results['weeks'].items():
            if week_data.get('status') == 'completed':
                weeks_completed += 1
                total_passed += week_data.get('passed', 0)
                total_failed += week_data.get('failed', 0)
        
        total_tests = total_passed + total_failed
        overall_pass_rate = total_passed / total_tests * 100 if total_tests > 0 else 0
        
        # 打印总结
        print(f"\n完成周数: {weeks_completed}/4")
        print(f"总测试数: {total_tests}")
        print(f"通过: {total_passed}")
        print(f"失败: {total_failed}")
        print(f"总通过率: {overall_pass_rate:.1f}%")
        
        # 各周详情
        print("\n各周详情:")
        for week_name in ['week1', 'week2', 'week3', 'week4']:
            if week_name in self.results['weeks']:
                week_data = self.results['weeks'][week_name]
                if week_data.get('status') == 'completed':
                    print(f"  {week_data['name']}: "
                          f"{week_data['passed']}/{week_data['total']} "
                          f"({week_data['pass_rate']:.1f}%)")
                else:
                    print(f"  {week_data['name']}: ❌ 失败 - {week_data.get('error', 'Unknown')}")
            else:
                print(f"  Week {week_name[-1]}: ⏸️ 未运行")
        
        # 结论
        print("\n" + "="*80)
        if overall_pass_rate >= 95:
            print("✅ 全面验证通过！系统精度、稳定性达标。")
        elif overall_pass_rate >= 80:
            print("⚠️ 部分验证通过，需要改进。")
        else:
            print("❌ 验证失败，需要重大修复。")
        print("="*80)
        
        # 保存JSON报告
        with open('comprehensive_test_results.json', 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\n✅ 详细结果已保存: comprehensive_test_results.json")
        
        # 生成Markdown报告
        self.generate_markdown_report()
    
    def generate_markdown_report(self):
        """生成Markdown格式报告"""
        with open('COMPREHENSIVE_TEST_REPORT.md', 'w', encoding='utf-8') as f:
            f.write("# 全面测试验证报告\n\n")
            f.write(f"**测试日期**: {self.results['start_time']}\n\n")
            
            f.write("## 📊 总体结果\n\n")
            
            total_passed = sum(w.get('passed', 0) for w in self.results['weeks'].values())
            total_failed = sum(w.get('failed', 0) for w in self.results['weeks'].values())
            total_tests = total_passed + total_failed
            
            if total_tests > 0:
                f.write(f"- **总测试数**: {total_tests}\n")
                f.write(f"- **通过**: {total_passed}\n")
                f.write(f"- **失败**: {total_failed}\n")
                f.write(f"- **通过率**: {total_passed/total_tests*100:.1f}%\n\n")
            
            # 各周详情
            for week_name in ['week1', 'week2', 'week3', 'week4']:
                if week_name in self.results['weeks']:
                    week_data = self.results['weeks'][week_name]
                    f.write(f"## {week_data['name']}\n\n")
                    
                    if week_data.get('status') == 'completed':
                        f.write(f"- **状态**: ✅ 完成\n")
                        f.write(f"- **通过**: {week_data['passed']}/{week_data['total']}\n")
                        f.write(f"- **通过率**: {week_data['pass_rate']:.1f}%\n\n")
                    else:
                        f.write(f"- **状态**: ❌ 失败\n")
                        f.write(f"- **错误**: {week_data.get('error', 'Unknown')}\n\n")
            
            f.write("---\n\n")
            f.write("**自动生成** | 全面测试验证系统\n")
        
        print(f"✅ Markdown报告已保存: COMPREHENSIVE_TEST_REPORT.md")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='运行全面测试验证')
    parser.add_argument('--week', type=int, choices=[1, 2, 3, 4],
                       help='运行指定周的测试')
    parser.add_argument('--all', action='store_true',
                       help='运行所有4周的测试')
    
    args = parser.parse_args()
    
    runner = ComprehensiveTestRunner()
    
    if args.all:
        # 运行所有测试
        print("="*80)
        print("运行全部4周测试")
        print("="*80)
        
        runner.run_week1()
        runner.run_week2()
        runner.run_week3()
        runner.run_week4()
        
        runner.generate_summary_report()
    
    elif args.week:
        # 运行指定周
        if args.week == 1:
            runner.run_week1()
        elif args.week == 2:
            runner.run_week2()
        elif args.week == 3:
            runner.run_week3()
        elif args.week == 4:
            runner.run_week4()
        
        runner.generate_summary_report()
    
    else:
        # 默认运行Week 1
        print("默认运行Week 1测试（使用 --all 运行所有测试）")
        runner.run_week1()
        runner.generate_summary_report()


if __name__ == '__main__':
    main()
