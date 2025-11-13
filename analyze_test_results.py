#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试结果分析工具
Test Results Analyzer

分析batch_test_all_cases.py的输出，生成详细的统计报告。
Analyzes the output from batch_test_all_cases.py and generates detailed statistics.

Author: HydroClaude Team
Date: 2025-11-13
"""

import json
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Tuple
import sys

# ============================================================================
# Configuration
# ============================================================================

PROJECT_ROOT = Path(__file__).parent
TEST_RESULTS_DIR = PROJECT_ROOT / "test_results"
CATALOG_PATH = PROJECT_ROOT / "web" / "backend" / "data" / "test_cases_catalog.json"


# ============================================================================
# Result Analyzer
# ============================================================================

class TestResultAnalyzer:
    def __init__(self, results_json_path: Path, catalog_path: Path):
        self.results_json_path = results_json_path
        self.catalog_path = catalog_path
        self.results = []
        self.catalog = {}
        self.stats = {
            'total': 0,
            'passed': 0,
            'failed': 0,
            'errored': 0,
            'timeout': 0,
            'pass_rate': 0.0,
            'total_duration': 0.0,
            'avg_duration': 0.0
        }
        self.category_stats = defaultdict(lambda: {
            'total': 0, 'passed': 0, 'failed': 0, 'errored': 0, 'timeout': 0
        })
        self.failure_patterns = defaultdict(int)
        
    def load_data(self):
        """Load test results and catalog"""
        if self.results_json_path.exists():
            with open(self.results_json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.results = data.get('results', [])
        else:
            print(f"[WARNING] Results file not found: {self.results_json_path}")
            return False
        
        if self.catalog_path.exists():
            with open(self.catalog_path, 'r', encoding='utf-8') as f:
                catalog_data = json.load(f)
                # Create a mapping from case_id to category
                for case in catalog_data.get('testCases', []):
                    case_id = case.get('metadata', {}).get('id')
                    category = case.get('metadata', {}).get('category', 'Unknown')
                    if case_id:
                        self.catalog[case_id] = category
        
        return True
    
    def analyze(self):
        """Perform comprehensive analysis"""
        if not self.results:
            print("[ERROR] No test results to analyze.")
            return
        
        self.stats['total'] = len(self.results)
        
        for result in self.results:
            status = result.get('status', 'unknown')
            duration = result.get('duration', 0)
            case_id = result.get('case_id', 'unknown')
            error_msg = result.get('error_message', '')
            
            # Update overall stats
            if status == 'passed':
                self.stats['passed'] += 1
            elif status == 'failed':
                self.stats['failed'] += 1
            elif status == 'timeout':
                self.stats['timeout'] += 1
            else:
                self.stats['errored'] += 1
            
            self.stats['total_duration'] += duration
            
            # Update category stats
            category = self.catalog.get(case_id, 'Unknown')
            self.category_stats[category]['total'] += 1
            if status == 'passed':
                self.category_stats[category]['passed'] += 1
            elif status == 'failed':
                self.category_stats[category]['failed'] += 1
            elif status == 'timeout':
                self.category_stats[category]['timeout'] += 1
            else:
                self.category_stats[category]['errored'] += 1
            
            # Analyze failure patterns
            if status in ['failed', 'error', 'timeout']:
                pattern = self._extract_error_pattern(error_msg)
                self.failure_patterns[pattern] += 1
        
        # Calculate derived stats
        if self.stats['total'] > 0:
            self.stats['pass_rate'] = (self.stats['passed'] / self.stats['total']) * 100
            self.stats['avg_duration'] = self.stats['total_duration'] / self.stats['total']
    
    def _extract_error_pattern(self, error_msg: str) -> str:
        """Extract common error patterns from error messages"""
        if not error_msg:
            return "No error message"
        
        # Check for common error patterns
        if "ModuleNotFoundError" in error_msg:
            # Extract the module name
            match = re.search(r"No module named '([^']+)'", error_msg)
            if match:
                return f"ModuleNotFoundError: {match.group(1)}"
            return "ModuleNotFoundError"
        
        if "ImportError" in error_msg:
            return "ImportError"
        
        if "FileNotFoundError" in error_msg:
            return "FileNotFoundError"
        
        if "TimeoutExpired" in error_msg or "timed out" in error_msg.lower():
            return "Timeout"
        
        if "Exit code:" in error_msg:
            return "Non-zero exit code"
        
        if "UnicodeEncodeError" in error_msg or "gbk" in error_msg.lower():
            return "Encoding Error"
        
        # Return first line of error as pattern
        first_line = error_msg.split('\n')[0][:100]
        return first_line
    
    def generate_report(self, output_path: Path):
        """Generate a comprehensive Markdown report"""
        report_lines = []
        
        # Header
        report_lines.append("# HydroClaude 批量测试结果分析报告")
        report_lines.append("# Batch Test Results Analysis Report")
        report_lines.append("")
        report_lines.append(f"**生成时间 / Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"**测试案例总数 / Total Cases**: {self.stats['total']}")
        report_lines.append("")
        report_lines.append("---")
        report_lines.append("")
        
        # Overall Statistics
        report_lines.append("## 📊 总体统计 / Overall Statistics")
        report_lines.append("")
        report_lines.append("```")
        report_lines.append(f"总计测试案例 / Total Cases:     {self.stats['total']}")
        report_lines.append(f"通过 / Passed:                  {self.stats['passed']} ({self.stats['passed']/self.stats['total']*100:.1f}%)")
        report_lines.append(f"失败 / Failed:                  {self.stats['failed']} ({self.stats['failed']/self.stats['total']*100:.1f}%)")
        report_lines.append(f"错误 / Error:                   {self.stats['errored']} ({self.stats['errored']/self.stats['total']*100:.1f}%)")
        report_lines.append(f"超时 / Timeout:                 {self.stats['timeout']} ({self.stats['timeout']/self.stats['total']*100:.1f}%)")
        report_lines.append("")
        report_lines.append(f"通过率 / Pass Rate:             {self.stats['pass_rate']:.2f}%")
        report_lines.append(f"总耗时 / Total Duration:        {self.stats['total_duration']:.2f}s ({self.stats['total_duration']/60:.1f} min)")
        report_lines.append(f"平均耗时 / Avg Duration:        {self.stats['avg_duration']:.2f}s")
        report_lines.append("```")
        report_lines.append("")
        
        # Visual representation
        report_lines.append("### 状态分布 / Status Distribution")
        report_lines.append("")
        report_lines.append("```")
        passed_bar = "█" * int(self.stats['passed'] / self.stats['total'] * 50)
        failed_bar = "█" * int(self.stats['failed'] / self.stats['total'] * 50)
        errored_bar = "█" * int(self.stats['errored'] / self.stats['total'] * 50)
        report_lines.append(f"PASS:  {passed_bar} {self.stats['passed']}")
        report_lines.append(f"FAIL:  {failed_bar} {self.stats['failed']}")
        report_lines.append(f"ERROR: {errored_bar} {self.stats['errored']}")
        report_lines.append("```")
        report_lines.append("")
        report_lines.append("---")
        report_lines.append("")
        
        # Category Statistics
        report_lines.append("## 📁 分类统计 / Category Statistics")
        report_lines.append("")
        report_lines.append("| Category / 分类 | Total / 总数 | Passed / 通过 | Failed / 失败 | Error / 错误 | Timeout / 超时 | Pass Rate / 通过率 |")
        report_lines.append("|----------------|-------------|--------------|--------------|-------------|---------------|------------------|")
        
        for category in sorted(self.category_stats.keys()):
            stats = self.category_stats[category]
            total = stats['total']
            passed = stats['passed']
            failed = stats['failed']
            errored = stats['errored']
            timeout = stats['timeout']
            pass_rate = (passed / total * 100) if total > 0 else 0
            
            report_lines.append(
                f"| {category} | {total} | {passed} | {failed} | {errored} | {timeout} | {pass_rate:.1f}% |"
            )
        
        report_lines.append("")
        report_lines.append("---")
        report_lines.append("")
        
        # Failure Patterns
        report_lines.append("## 🔍 失败模式分析 / Failure Pattern Analysis")
        report_lines.append("")
        report_lines.append("### Top 10 失败原因 / Top 10 Failure Reasons")
        report_lines.append("")
        
        sorted_patterns = sorted(
            self.failure_patterns.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        report_lines.append("| Rank | Error Pattern / 错误模式 | Count / 次数 | Percentage / 百分比 |")
        report_lines.append("|------|------------------------|------------|-------------------|")
        
        total_failures = self.stats['failed'] + self.stats['errored'] + self.stats['timeout']
        for i, (pattern, count) in enumerate(sorted_patterns, 1):
            percentage = (count / total_failures * 100) if total_failures > 0 else 0
            report_lines.append(f"| {i} | {pattern[:60]} | {count} | {percentage:.1f}% |")
        
        report_lines.append("")
        report_lines.append("---")
        report_lines.append("")
        
        # Failed Test Cases
        report_lines.append("## ❌ 失败的测试案例 / Failed Test Cases")
        report_lines.append("")
        
        failed_cases = [r for r in self.results if r.get('status') in ['failed', 'error', 'timeout']]
        
        if failed_cases:
            report_lines.append(f"Total failed cases: {len(failed_cases)}")
            report_lines.append("")
            report_lines.append("<details>")
            report_lines.append("<summary>点击展开失败案例列表 / Click to expand failed cases list</summary>")
            report_lines.append("")
            
            for case in failed_cases[:50]:  # Limit to first 50
                case_id = case.get('case_id', 'unknown')
                case_name = case.get('case_name', 'Unknown')
                status = case.get('status', 'unknown')
                error = case.get('error_message', 'No error message')[:200]
                
                report_lines.append(f"### {case_name}")
                report_lines.append(f"- **ID**: {case_id}")
                report_lines.append(f"- **Status**: {status}")
                report_lines.append(f"- **Error**: {error}...")
                report_lines.append("")
            
            if len(failed_cases) > 50:
                report_lines.append(f"... and {len(failed_cases) - 50} more failed cases.")
                report_lines.append("")
            
            report_lines.append("</details>")
        else:
            report_lines.append("No failed cases! All tests passed!")
        
        report_lines.append("")
        report_lines.append("---")
        report_lines.append("")
        
        # Recommendations
        report_lines.append("## 💡 建议 / Recommendations")
        report_lines.append("")
        
        if "ModuleNotFoundError" in str(self.failure_patterns):
            report_lines.append("### 1. 修复模块导入问题 / Fix Module Import Issues")
            report_lines.append("")
            report_lines.append("多个测试案例因为`ModuleNotFoundError`失败。建议：")
            report_lines.append("- 检查Python路径配置")
            report_lines.append("- 统一使用绝对导入或相对导入")
            report_lines.append("- 添加`sys.path`配置到测试文件")
            report_lines.append("")
        
        if self.stats['pass_rate'] < 50:
            report_lines.append("### 2. 通过率较低 / Low Pass Rate")
            report_lines.append("")
            report_lines.append("当前通过率低于50%。建议：")
            report_lines.append("- 优先修复高频失败原因")
            report_lines.append("- 检查测试环境配置")
            report_lines.append("- 验证依赖库版本")
            report_lines.append("")
        
        if self.stats['timeout'] > 0:
            report_lines.append("### 3. 超时案例 / Timeout Cases")
            report_lines.append("")
            report_lines.append(f"有{self.stats['timeout']}个案例超时。建议：")
            report_lines.append("- 增加超时时间限制")
            report_lines.append("- 优化算法性能")
            report_lines.append("- 检查是否有死循环")
            report_lines.append("")
        
        report_lines.append("---")
        report_lines.append("")
        report_lines.append("## 📝 总结 / Summary")
        report_lines.append("")
        
        if self.stats['pass_rate'] >= 90:
            report_lines.append("✅ **优秀 / Excellent**: 通过率超过90%，系统质量很高！")
        elif self.stats['pass_rate'] >= 70:
            report_lines.append("⚠️ **良好 / Good**: 通过率在70-90%之间，还有改进空间。")
        elif self.stats['pass_rate'] >= 50:
            report_lines.append("⚠️ **一般 / Fair**: 通过率在50-70%之间，需要重点关注失败案例。")
        else:
            report_lines.append("❌ **需要改进 / Needs Improvement**: 通过率低于50%，需要优先修复主要问题。")
        
        report_lines.append("")
        report_lines.append("---")
        report_lines.append("")
        report_lines.append(f"**报告生成完成 / Report Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Write report
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_lines))
        
        print(f"\n[SUCCESS] Report generated: {output_path}")
    
    def print_summary(self):
        """Print a quick summary to console"""
        print("\n" + "="*70)
        print(" TEST RESULTS SUMMARY ".center(70))
        print("="*70)
        print(f"\nTotal Cases:   {self.stats['total']}")
        print(f"Passed:        {self.stats['passed']} ({self.stats['pass_rate']:.2f}%)")
        print(f"Failed:        {self.stats['failed']}")
        print(f"Errored:       {self.stats['errored']}")
        print(f"Timeout:       {self.stats['timeout']}")
        print(f"\nTotal Duration: {self.stats['total_duration']:.2f}s ({self.stats['total_duration']/60:.1f} min)")
        print(f"Avg Duration:   {self.stats['avg_duration']:.2f}s")
        print("\n" + "="*70)
        
        print("\nTop 5 Failure Patterns:")
        sorted_patterns = sorted(
            self.failure_patterns.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        for i, (pattern, count) in enumerate(sorted_patterns, 1):
            print(f"  {i}. [{count}x] {pattern[:60]}")
        
        print("\n" + "="*70 + "\n")


# ============================================================================
# Main Function
# ============================================================================

def main():
    print("="*70)
    print(" HydroClaude Test Results Analyzer ".center(70))
    print("="*70)
    
    results_json = TEST_RESULTS_DIR / "batch_test_results.json"
    report_md = TEST_RESULTS_DIR / "batch_test_analysis.md"
    
    analyzer = TestResultAnalyzer(results_json, CATALOG_PATH)
    
    print("\n[1/3] Loading test results...")
    if not analyzer.load_data():
        print("[ERROR] Failed to load test results.")
        sys.exit(1)
    
    print(f"[OK] Loaded {len(analyzer.results)} test results.")
    
    print("\n[2/3] Analyzing results...")
    analyzer.analyze()
    print("[OK] Analysis complete.")
    
    print("\n[3/3] Generating report...")
    analyzer.generate_report(report_md)
    
    # Print summary
    analyzer.print_summary()
    
    print(f"\nDetailed report saved to: {report_md}")
    print("\nDone!")


if __name__ == '__main__':
    main()


