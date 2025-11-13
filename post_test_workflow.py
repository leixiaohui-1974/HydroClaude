#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试完成后自动化处理工作流
Post-Test Automated Workflow

测试完成后自动执行分析、修复、报告生成等一系列操作。
Automatically executes analysis, fixes, report generation after test completion.

Usage:
    python post_test_workflow.py

Author: HydroClaude Team
Date: 2025-11-13
"""

import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent
RESULTS_DIR = PROJECT_ROOT / "test_results"


class PostTestWorkflow:
    """自动化测试后处理工作流"""
    
    def __init__(self):
        self.steps = [
            ("检查测试完成状态", self.check_completion),
            ("分析测试结果", self.analyze_results),
            ("自动修复问题", self.fix_issues),
            ("生成汇总报告", self.generate_summary),
            ("验证修复效果", self.verify_fixes),
            ("清理临时文件", self.cleanup)
        ]
        self.results = {}
        
    def run(self):
        """执行完整工作流"""
        print("\n" + "="*70)
        print(" Post-Test Automated Workflow ".center(70, "="))
        print("="*70 + "\n")
        
        start_time = time.time()
        
        for i, (name, func) in enumerate(self.steps, 1):
            print(f"\n[Step {i}/{len(self.steps)}] {name}")
            print("-" * 70)
            
            try:
                result = func()
                self.results[name] = {"status": "success", "result": result}
                print(f"✓ {name} - 完成")
            except Exception as e:
                self.results[name] = {"status": "failed", "error": str(e)}
                print(f"✗ {name} - 失败: {e}")
                
                # 询问是否继续
                response = input("\n是否继续下一步？ (y/n): ")
                if response.lower() != 'y':
                    print("\n工作流中止。")
                    break
        
        elapsed = time.time() - start_time
        
        # 打印最终报告
        self.print_final_report(elapsed)
    
    def check_completion(self):
        """检查测试是否完成"""
        results_json = RESULTS_DIR / "batch_test_results.json"
        
        if not results_json.exists():
            raise FileNotFoundError("测试结果文件不存在，请先运行批量测试")
        
        import json
        with open(results_json, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        total = len(data.get('results', []))
        print(f"  发现 {total} 个测试结果")
        
        if total < 541:
            print(f"  警告: 测试可能未完成 ({total}/541)")
        
        return {"total_cases": total}
    
    def analyze_results(self):
        """分析测试结果"""
        print("  运行结果分析器...")
        
        analyzer_script = PROJECT_ROOT / "analyze_test_results.py"
        
        if not analyzer_script.exists():
            raise FileNotFoundError("分析脚本不存在")
        
        result = subprocess.run(
            [sys.executable, str(analyzer_script)],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"分析失败: {result.stderr[:200]}")
        
        print("  ✓ 分析报告已生成: test_results/batch_test_analysis.md")
        
        return {"returncode": result.returncode}
    
    def fix_issues(self):
        """自动修复常见问题"""
        print("  运行自动修复工具...")
        
        fixer_script = PROJECT_ROOT / "fix_test_import_issues.py"
        
        if not fixer_script.exists():
            print("  跳过: 修复脚本不存在")
            return {"status": "skipped"}
        
        # 先干运行查看会修复什么
        print("  执行干运行...")
        result_dry = subprocess.run(
            [sys.executable, str(fixer_script), "--directory", "tests"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        print(f"  发现 {result_dry.stdout.count('Would fix')} 个需要修复的文件")
        
        # 询问是否应用修复
        response = input("\n  是否应用修复？ (y/n): ")
        
        if response.lower() == 'y':
            print("  应用修复...")
            result = subprocess.run(
                [sys.executable, str(fixer_script), "--apply", "--directory", "tests"],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            
            if result.returncode == 0:
                print("  ✓ 修复已应用")
                return {"status": "applied", "output": result.stdout[:500]}
            else:
                print(f"  ✗ 修复失败: {result.stderr[:200]}")
                return {"status": "failed", "error": result.stderr[:200]}
        else:
            print("  跳过修复")
            return {"status": "skipped"}
    
    def generate_summary(self):
        """生成汇总报告"""
        print("  生成最终汇总报告...")
        
        analysis_file = RESULTS_DIR / "batch_test_analysis.md"
        
        if not analysis_file.exists():
            print("  警告: 分析报告不存在")
            return {"status": "no_analysis"}
        
        # 读取分析报告的关键指标
        with open(analysis_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 提取关键信息
        import re
        
        total_match = re.search(r'总计测试案例.*?(\d+)', content)
        passed_match = re.search(r'通过.*?(\d+).*?\(([0-9.]+)%\)', content)
        failed_match = re.search(r'失败.*?(\d+).*?\(([0-9.]+)%\)', content)
        
        summary = {
            "total": int(total_match.group(1)) if total_match else 0,
            "passed": int(passed_match.group(1)) if passed_match else 0,
            "pass_rate": float(passed_match.group(2)) if passed_match else 0,
            "failed": int(failed_match.group(1)) if failed_match else 0
        }
        
        print(f"\n  测试汇总:")
        print(f"    总计: {summary['total']}")
        print(f"    通过: {summary['passed']} ({summary['pass_rate']:.1f}%)")
        print(f"    失败: {summary['failed']}")
        
        return summary
    
    def verify_fixes(self):
        """验证修复效果"""
        print("  验证修复效果...")
        
        quick_test = PROJECT_ROOT / "quick_test_sample.py"
        
        if not quick_test.exists():
            print("  跳过: 快速测试脚本不存在")
            return {"status": "skipped"}
        
        response = input("\n  是否运行快速验证测试（5个随机案例）？ (y/n): ")
        
        if response.lower() == 'y':
            print("  运行快速测试...")
            result = subprocess.run(
                [sys.executable, str(quick_test)],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=60
            )
            
            # 分析输出
            passed = result.stdout.count('PASS')
            failed = result.stdout.count('FAIL')
            
            print(f"  快速测试结果: {passed} 通过, {failed} 失败")
            
            return {
                "status": "completed",
                "passed": passed,
                "failed": failed
            }
        else:
            print("  跳过验证")
            return {"status": "skipped"}
    
    def cleanup(self):
        """清理临时文件"""
        print("  清理临时文件...")
        
        # 列出可清理的文件
        temp_files = [
            RESULTS_DIR / "batch_test_output.txt.bak",
            PROJECT_ROOT / "test_fixes_backup" / "*.bak"
        ]
        
        cleaned = 0
        for pattern in temp_files:
            if pattern.exists():
                # 这里只是示例，实际不删除
                print(f"    发现: {pattern}")
                cleaned += 1
        
        if cleaned == 0:
            print("  无需清理")
        else:
            print(f"  发现 {cleaned} 个可清理文件（未删除）")
        
        return {"cleaned_count": cleaned}
    
    def print_final_report(self, elapsed_time):
        """打印最终报告"""
        print("\n" + "="*70)
        print(" Workflow Complete Summary ".center(70, "="))
        print("="*70 + "\n")
        
        print(f"总耗时: {elapsed_time:.1f} 秒\n")
        
        print("步骤执行结果:")
        for name, result in self.results.items():
            status = result.get('status', 'unknown')
            icon = "✓" if status == "success" else "✗"
            print(f"  {icon} {name}: {status}")
        
        print("\n" + "="*70)
        print("\n下一步建议:")
        print("  1. 查看详细分析报告: test_results/batch_test_analysis.md")
        print("  2. 如果通过率低于90%，查看失败案例并修复")
        print("  3. 启动Web界面测试: cd web/frontend && npm run dev")
        print("  4. 访问: http://localhost:3000")
        print("\n" + "="*70 + "\n")


def main():
    """主函数"""
    workflow = PostTestWorkflow()
    
    try:
        workflow.run()
    except KeyboardInterrupt:
        print("\n\n工作流被用户中断。")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n工作流异常: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()


