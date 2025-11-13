#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
配置驱动的Example测试框架

基于examples_config.yaml运行和验证examples
完全消除硬编码，使用配置文件管理

Author: Claude
Date: 2025-10-24
"""

import yaml
import subprocess
import sys
from pathlib import Path
from typing import Dict, List
import time
import json

PROJECT_ROOT = Path(__file__).parent


class ConfigDrivenTester:
    """配置驱动的测试器"""

    def __init__(self, config_file: str = "examples_config.yaml"):
        self.config_path = PROJECT_ROOT / config_file
        self.config = self.load_config()
        self.results = []

    def load_config(self) -> Dict:
        """加载配置文件"""
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config

    def run_example(self, example_config: Dict) -> Dict:
        """运行单个example"""
        example_id = example_config['id']
        example_path = PROJECT_ROOT / example_config['path']
        description = example_config.get('description', '')
        timeout = example_config.get('timeout', self.config['global']['timeout'])

        print(f"\n{'='*80}")
        print(f"测试: {example_id}")
        print(f"描述: {description}")
        print(f"路径: {example_config['path']}")
        print(f"{'='*80}")

        result = {
            'id': example_id,
            'path': str(example_config['path']),
            'description': description,
            'status': 'unknown',
            'execution_time': 0,
            'error': None
        }

        # 检查文件是否存在
        if not example_path.exists():
            print(f" 文件不存在")
            result['status'] = 'file_not_found'
            result['error'] = f"文件不存在: {example_path}"
            return result

        # 运行example
        start_time = time.time()

        try:
            process = subprocess.run(
                [sys.executable, str(example_path)],
                cwd=str(example_path.parent),
                capture_output=True,
                text=True,
                timeout=timeout
            )

            result['execution_time'] = time.time() - start_time

            if process.returncode == 0:
                print(f" 成功 ({result['execution_time']:.1f}s)")
                result['status'] = 'success'

                # 检查预期输出
                if 'expected_outputs' in example_config:
                    missing_outputs = []
                    for output in example_config['expected_outputs']:
                        output_path = PROJECT_ROOT / output
                        if not output_path.exists():
                            missing_outputs.append(output)

                    if missing_outputs:
                        print(f"️  缺失预期输出: {', '.join(missing_outputs)}")
                        result['missing_outputs'] = missing_outputs

            else:
                print(f" 失败 ({result['execution_time']:.1f}s)")
                result['status'] = 'failed'
                result['error'] = process.stderr[-500:] if process.stderr else "Unknown error"
                print(f"错误: {result['error'][:200]}")

        except subprocess.TimeoutExpired:
            result['execution_time'] = timeout
            result['status'] = 'timeout'
            result['error'] = f"超时 (>{timeout}s)"
            print(f"⏱️  超时 (>{timeout}s)")

        except Exception as e:
            result['execution_time'] = time.time() - start_time
            result['status'] = 'error'
            result['error'] = str(e)
            print(f" 异常: {e}")

        return result

    def run_category(self, category_name: str, examples: List[Dict]) -> List[Dict]:
        """运行一个类别的examples"""
        print(f"\n\n{'#'*80}")
        print(f"# 类别: {category_name} ({len(examples)} 个examples)")
        print(f"{'#'*80}")

        category_results = []
        for example in examples:
            result = self.run_example(example)
            category_results.append(result)

        return category_results

    def run_all_tests(self) -> Dict:
        """运行所有测试"""
        print(f"{'='*80}")
        print("HydroClaude Examples 配置驱动测试")
        print(f"{'='*80}")
        print(f"配置文件: {self.config_path}")
        print(f"超时设置: {self.config['global']['timeout']}s")

        all_results = {}

        # 运行各类别的examples
        categories = [
            'core_examples',
            'preissmann_examples',
            'mpc_examples',
            'advanced_examples'
        ]

        for category in categories:
            if category in self.config:
                examples = self.config[category]
                results = self.run_category(category, examples)
                all_results[category] = results

        # 处理废弃的examples
        if 'deprecated_examples' in self.config:
            print(f"\n\n{'#'*80}")
            print(f"# 废弃的Examples (需要处理)")
            print(f"{'#'*80}")

            for dep_ex in self.config['deprecated_examples']:
                print(f"\n️  {dep_ex['id']}")
                print(f"   路径: {dep_ex['path']}")
                print(f"   原因: {dep_ex['reason']}")
                print(f"   建议: {dep_ex['action']}")

        self.results = all_results
        return all_results

    def generate_report(self) -> str:
        """生成测试报告"""
        report = []
        report.append("="*80)
        report.append("HydroClaude Examples 测试报告")
        report.append("="*80)
        report.append("")

        # 统计
        total = 0
        success = 0
        failed = 0
        file_not_found = 0

        for category, results in self.results.items():
            total += len(results)
            for r in results:
                if r['status'] == 'success':
                    success += 1
                elif r['status'] == 'failed':
                    failed += 1
                elif r['status'] == 'file_not_found':
                    file_not_found += 1

        report.append(f"总计: {total} 个examples")
        report.append(f"   成功: {success}")
        report.append(f"   失败: {failed}")
        report.append(f"   文件不存在: {file_not_found}")
        if total > 0:
            report.append(f"  成功率: {success/total*100:.1f}%")
        report.append("")

        # 各类别详情
        for category, results in self.results.items():
            report.append("="*80)
            report.append(f"类别: {category}")
            report.append("="*80)
            report.append("")

            for r in results:
                status_icon = {
                    'success': '',
                    'failed': '',
                    'timeout': '⏱️',
                    'file_not_found': '',
                    'error': '️'
                }.get(r['status'], '')

                report.append(f"{status_icon} {r['id']}")
                report.append(f"   描述: {r['description']}")
                report.append(f"   路径: {r['path']}")
                report.append(f"   状态: {r['status']}")
                report.append(f"   执行时间: {r['execution_time']:.1f}s")

                if r['status'] != 'success' and r.get('error'):
                    report.append(f"   错误: {r['error'][:200]}")

                if r.get('missing_outputs'):
                    report.append(f"   ️  缺失输出: {', '.join(r['missing_outputs'])}")

                report.append("")

        return "\n".join(report)

    def save_report(self, filename: str = "example_test_report.txt"):
        """保存报告"""
        report_path = PROJECT_ROOT / filename
        report = self.generate_report()

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)

        print(f"\n 报告已保存: {report_path}")

        # 保存JSON
        json_path = PROJECT_ROOT / filename.replace('.txt', '.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)

        print(f" JSON已保存: {json_path}")

        return report_path


def main():
    """主函数"""
    tester = ConfigDrivenTester()

    # 运行所有测试
    results = tester.run_all_tests()

    # 生成报告
    tester.save_report()

    # 打印报告
    print("\n" + "="*80)
    print("测试完成！")
    print("="*80)
    print(tester.generate_report())

    return tester


if __name__ == '__main__':
    tester = main()
