#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Batch Test All Cases - 批量测试所有案例
对541个测试案例进行批量验证

功能:
1. 加载所有541个测试案例
2. 逐个运行测试
3. 验证结果正确性
4. 生成详细报告
5. 记录失败案例

Author: HydroClaude Team
Date: 2025-11-13
"""

import sys
import os
import json
import subprocess
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple
import traceback

# 项目根目录
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# 加载测试案例目录
CATALOG_FILE = PROJECT_ROOT / "web" / "backend" / "data" / "test_cases_catalog.json"
RESULTS_DIR = PROJECT_ROOT / "test_results"
RESULTS_DIR.mkdir(exist_ok=True)


class TestResult:
    """测试结果"""
    def __init__(self, case_id: str, case_name: str):
        self.case_id = case_id
        self.case_name = case_name
        self.status = "pending"  # pending, running, passed, failed, error
        self.duration = 0.0
        self.error_message = ""
        self.start_time = None
        self.end_time = None
    
    def to_dict(self):
        return {
            'case_id': self.case_id,
            'case_name': self.case_name,
            'status': self.status,
            'duration': self.duration,
            'error_message': self.error_message,
            'start_time': str(self.start_time) if self.start_time else None,
            'end_time': str(self.end_time) if self.end_time else None
        }


class BatchTester:
    """批量测试器"""
    
    def __init__(self):
        self.catalog = self.load_catalog()
        self.results: List[TestResult] = []
        self.total_cases = 0
        self.passed_cases = 0
        self.failed_cases = 0
        self.error_cases = 0
        self.start_time = None
        self.end_time = None
    
    def load_catalog(self) -> Dict:
        """加载测试案例目录"""
        if not CATALOG_FILE.exists():
            print(f"错误: 找不到测试案例目录文件: {CATALOG_FILE}")
            print("请先运行: python web/backend/test_case_manager.py")
            sys.exit(1)
        
        with open(CATALOG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def run_all_tests(self):
        """运行所有测试"""
        print("="*80)
        print(" 批量测试所有案例 - Batch Test All Cases ".center(80))
        print("="*80)
        print()
        
        test_cases = self.catalog.get('testCases', [])
        self.total_cases = len(test_cases)
        
        print(f"总共找到 {self.total_cases} 个测试案例")
        print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        self.start_time = datetime.now()
        
        for idx, test_case in enumerate(test_cases, 1):
            self.run_single_test(test_case, idx)
        
        self.end_time = datetime.now()
        self.generate_report()
    
    def run_single_test(self, test_case: Dict, index: int):
        """运行单个测试"""
        metadata = test_case.get('metadata', {})
        case_id = metadata.get('id', 'unknown')
        case_name = metadata.get('name', 'Unknown Test')
        file_path = test_case.get('sourcePath', '')
        
        result = TestResult(case_id, case_name)
        result.start_time = datetime.now()
        
        print(f"[{index}/{self.total_cases}] 测试: {case_name}")
        print(f"    ID: {case_id}")
        print(f"    文件: {file_path}")
        
        if not file_path:
            result.status = "error"
            result.error_message = "No source file path"
            print(f"    状态: 错误 - 没有源文件路径")
            self.error_cases += 1
            self.results.append(result)
            print()
            return
        
        full_path = PROJECT_ROOT / file_path
        
        if not full_path.exists():
            result.status = "error"
            result.error_message = f"File not found: {full_path}"
            print(f"    状态: 错误 - 文件不存在")
            self.error_cases += 1
            self.results.append(result)
            print()
            return
        
        # 运行测试
        try:
            result.status = "running"
            start = time.time()
            
            # 运行Python文件
            process = subprocess.Popen(
                [sys.executable, str(full_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            
            # 设置超时时间为60秒
            try:
                stdout, stderr = process.communicate(timeout=60)
                returncode = process.returncode
            except subprocess.TimeoutExpired:
                process.kill()
                result.status = "failed"
                result.error_message = "Timeout (>60s)"
                print(f"    状态: 失败 - 超时")
                self.failed_cases += 1
                result.duration = 60.0
                result.end_time = datetime.now()
                self.results.append(result)
                print()
                return
            
            result.duration = time.time() - start
            result.end_time = datetime.now()
            
            # 检查返回码
            if returncode == 0:
                result.status = "passed"
                print(f"    状态: 通过 PASS (耗时: {result.duration:.2f}s)")
                self.passed_cases += 1
            else:
                result.status = "failed"
                result.error_message = f"Exit code: {returncode}"
                if stderr:
                    # 只保存前500个字符的错误信息
                    result.error_message += f"\n{stderr[:500]}"
                print(f"    状态: 失败 FAIL (错误码: {returncode})")
                self.failed_cases += 1
        
        except Exception as e:
            result.status = "error"
            result.error_message = str(e)
            result.duration = time.time() - start if 'start' in locals() else 0
            result.end_time = datetime.now()
            print(f"    状态: 错误 - {str(e)}")
            self.error_cases += 1
        
        self.results.append(result)
        print()
    
    def generate_report(self):
        """生成测试报告"""
        print()
        print("="*80)
        print(" 测试完成 - Test Complete ".center(80))
        print("="*80)
        print()
        
        total_duration = (self.end_time - self.start_time).total_seconds()
        
        print(f"总测试案例: {self.total_cases}")
        print(f"通过: {self.passed_cases} ({self.passed_cases/self.total_cases*100:.1f}%)")
        print(f"失败: {self.failed_cases} ({self.failed_cases/self.total_cases*100:.1f}%)")
        print(f"错误: {self.error_cases} ({self.error_cases/self.total_cases*100:.1f}%)")
        print(f"总耗时: {total_duration:.1f}秒 ({total_duration/60:.1f}分钟)")
        print()
        
        # 保存详细报告
        report = {
            'summary': {
                'total': self.total_cases,
                'passed': self.passed_cases,
                'failed': self.failed_cases,
                'error': self.error_cases,
                'pass_rate': f"{self.passed_cases/self.total_cases*100:.1f}%",
                'total_duration': total_duration,
                'start_time': str(self.start_time),
                'end_time': str(self.end_time)
            },
            'results': [r.to_dict() for r in self.results]
        }
        
        report_file = RESULTS_DIR / f"batch_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"详细报告已保存到: {report_file}")
        
        # 生成失败案例列表
        failed_results = [r for r in self.results if r.status in ['failed', 'error']]
        if failed_results:
            print()
            print("="*80)
            print(" 失败案例列表 - Failed Cases ".center(80))
            print("="*80)
            print()
            
            for r in failed_results:
                print(f"[{r.status.upper()}] {r.case_name}")
                print(f"    ID: {r.case_id}")
                print(f"    错误: {r.error_message[:200]}")
                print()
            
            failed_file = RESULTS_DIR / f"failed_cases_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(failed_file, 'w', encoding='utf-8') as f:
                f.write("Failed Test Cases\n")
                f.write("="*80 + "\n\n")
                for r in failed_results:
                    f.write(f"[{r.status.upper()}] {r.case_name}\n")
                    f.write(f"    ID: {r.case_id}\n")
                    f.write(f"    Error: {r.error_message}\n\n")
            
            print(f"失败案例已保存到: {failed_file}")
        
        # 生成Markdown报告
        self.generate_markdown_report()
    
    def generate_markdown_report(self):
        """生成Markdown格式报告"""
        md_file = RESULTS_DIR / f"batch_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write("# Batch Test Report - 批量测试报告\n\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("---\n\n")
            
            f.write("## Summary / 总结\n\n")
            f.write(f"- **Total Cases / 总案例数:** {self.total_cases}\n")
            f.write(f"- **Passed / 通过:** {self.passed_cases} ({self.passed_cases/self.total_cases*100:.1f}%)\n")
            f.write(f"- **Failed / 失败:** {self.failed_cases} ({self.failed_cases/self.total_cases*100:.1f}%)\n")
            f.write(f"- **Error / 错误:** {self.error_cases} ({self.error_cases/self.total_cases*100:.1f}%)\n")
            
            total_duration = (self.end_time - self.start_time).total_seconds()
            f.write(f"- **Total Duration / 总耗时:** {total_duration:.1f}s ({total_duration/60:.1f}min)\n")
            f.write(f"- **Start Time / 开始时间:** {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"- **End Time / 结束时间:** {self.end_time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("---\n\n")
            
            # 按分类统计
            f.write("## Results by Category / 按分类统计\n\n")
            category_stats = {}
            for r in self.results:
                # 从case_id中提取分类
                parts = r.case_id.split('-')
                category = parts[0] if parts else 'unknown'
                
                if category not in category_stats:
                    category_stats[category] = {'total': 0, 'passed': 0, 'failed': 0, 'error': 0}
                
                category_stats[category]['total'] += 1
                if r.status == 'passed':
                    category_stats[category]['passed'] += 1
                elif r.status == 'failed':
                    category_stats[category]['failed'] += 1
                else:
                    category_stats[category]['error'] += 1
            
            f.write("| Category | Total | Passed | Failed | Error | Pass Rate |\n")
            f.write("|----------|-------|--------|--------|-------|----------|\n")
            for cat, stats in sorted(category_stats.items()):
                pass_rate = stats['passed'] / stats['total'] * 100 if stats['total'] > 0 else 0
                f.write(f"| {cat} | {stats['total']} | {stats['passed']} | {stats['failed']} | {stats['error']} | {pass_rate:.1f}% |\n")
            
            f.write("\n---\n\n")
            
            # 失败案例详情
            failed_results = [r for r in self.results if r.status in ['failed', 'error']]
            if failed_results:
                f.write("## Failed Cases / 失败案例\n\n")
                for r in failed_results:
                    f.write(f"### [{r.status.upper()}] {r.case_name}\n\n")
                    f.write(f"- **ID:** `{r.case_id}`\n")
                    f.write(f"- **Duration:** {r.duration:.2f}s\n")
                    f.write(f"- **Error:**\n```\n{r.error_message}\n```\n\n")
            
            f.write("---\n\n")
            f.write("*Generated by HydroClaude Batch Tester*\n")
        
        print(f"Markdown报告已保存到: {md_file}")


def main():
    """主函数"""
    try:
        tester = BatchTester()
        tester.run_all_tests()
        
        # 返回非零退出码如果有失败
        if tester.failed_cases > 0 or tester.error_cases > 0:
            sys.exit(1)
        
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n发生错误: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

