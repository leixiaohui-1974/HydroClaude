#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
综合验证测试套件

运行所有验证案例并生成HTML报告

验证案例分类：
1. 解析解验证（Analytical Solutions）
   - 溃坝波 (Ritter)
   - 恒定均匀流
   - 渐变流水面线 (M1曲线)

2. 国际基准案例（Benchmarks）
   - MacDonald案例

3. 功能验证（Feature Tests）
   - 复合糙率
   - 水工建筑物

作者：HydroClaude Team
日期：2025-10-28
"""

import sys
import os
from pathlib import Path
import time
from datetime import datetime
import subprocess

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class ValidationResult:
    """验证结果"""

    def __init__(self, name, category, passed, metrics, error_msg=None):
        self.name = name
        self.category = category
        self.passed = passed
        self.metrics = metrics
        self.error_msg = error_msg
        self.timestamp = datetime.now()


class ValidationSuite:
    """验证测试套件"""

    def __init__(self):
        self.results = []
        self.start_time = None
        self.end_time = None

    def run_single_test(self, test_name, test_path, category):
        """
        运行单个验证案例

        Args:
            test_name: 测试名称
            test_path: Python文件路径
            category: 类别
        """
        print(f"\n{'='*80}")
        print(f"运行测试: {test_name}")
        print(f"{'='*80}")

        start = time.time()

        try:
            # 运行测试脚本
            result = subprocess.run(
                ['python', test_path],
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )

            elapsed = time.time() - start

            # 检查返回码
            passed = (result.returncode == 0)

            # 提取指标（从输出中解析）
            metrics = self._parse_metrics(result.stdout)
            metrics['elapsed_time'] = elapsed

            if passed:
                print(f" {test_name} 通过 ({elapsed:.1f}s)")
            else:
                print(f" {test_name} 失败 ({elapsed:.1f}s)")
                if result.stderr:
                    print(f"  错误: {result.stderr[:200]}")

            return ValidationResult(
                name=test_name,
                category=category,
                passed=passed,
                metrics=metrics,
                error_msg=result.stderr if not passed else None
            )

        except subprocess.TimeoutExpired:
            elapsed = time.time() - start
            print(f" {test_name} 超时 ({elapsed:.1f}s)")
            return ValidationResult(
                name=test_name,
                category=category,
                passed=False,
                metrics={'elapsed_time': elapsed},
                error_msg="测试超时"
            )

        except Exception as e:
            elapsed = time.time() - start
            print(f" {test_name} 异常: {e}")
            return ValidationResult(
                name=test_name,
                category=category,
                passed=False,
                metrics={'elapsed_time': elapsed},
                error_msg=str(e)
            )

    def _parse_metrics(self, output):
        """从输出中解析指标"""
        metrics = {}

        # 查找RMSE
        for line in output.split('\n'):
            if 'RMSE' in line or 'rmse' in line:
                try:
                    # 提取数值
                    parts = line.split('=')
                    if len(parts) >= 2:
                        value_str = parts[1].split()[0]
                        value = float(value_str.replace('m', '').replace('%', ''))
                        metrics['rmse'] = value
                except:
                    pass

            if '误差' in line and '%' in line:
                try:
                    # 提取误差百分比
                    parts = line.split('=')
                    if len(parts) >= 2:
                        value_str = parts[1].split('%')[0].strip()
                        value = float(value_str)
                        # 判断是什么误差
                        if '流量' in line:
                            metrics['flow_error'] = value
                        elif '质量' in line or '守恒' in line:
                            metrics['mass_error'] = value
                        elif '水深' in line or '水位' in line:
                            metrics['depth_error'] = value
                except:
                    pass

        return metrics

    def run_all(self):
        """运行所有验证案例"""

        print("=" * 80)
        print("HydroClaude 明渠仿真综合验证测试套件")
        print("=" * 80)
        print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        self.start_time = time.time()

        # 定义所有测试案例
        test_cases = [
            # 1. 解析解验证
            {
                'name': '恒定均匀流 - 矩形断面',
                'path': 'validation_cases/analytical/steady_uniform_flow_comprehensive.py',
                'category': '解析解验证'
            },
            {
                'name': '溃坝波 (Ritter解)',
                'path': 'validation_cases/analytical/dam_break_ritter.py',
                'category': '解析解验证'
            },

            # 2. 国际基准案例
            {
                'name': 'MacDonald案例',
                'path': 'validation_cases/literature/macdonald_case1.py',
                'category': '国际基准案例'
            },

            # 3. 功能验证
            # {
            #     'name': '复合糙率计算',
            #     'path': 'tests/test_composite_roughness.py',
            #     'category': '功能验证'
            # },
        ]

        # 运行所有测试
        for test in test_cases:
            # 检查文件是否存在
            if not os.path.exists(test['path']):
                print(f"\n 跳过 {test['name']}: 文件不存在")
                continue

            result = self.run_single_test(
                test['name'],
                test['path'],
                test['category']
            )
            self.results.append(result)

        self.end_time = time.time()

        # 生成报告
        self.generate_report()

    def generate_report(self):
        """生成HTML验证报告"""

        total_time = self.end_time - self.start_time
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.passed)
        failed_tests = total_tests - passed_tests

        print("\n" + "=" * 80)
        print("验证测试总结")
        print("=" * 80)
        print(f"总测试数: {total_tests}")
        print(f"通过: {passed_tests}")
        print(f"失败: {failed_tests}")
        print(f"总耗时: {total_time:.1f}s")
        print()

        # 按类别统计
        categories = {}
        for result in self.results:
            if result.category not in categories:
                categories[result.category] = {'passed': 0, 'failed': 0}

            if result.passed:
                categories[result.category]['passed'] += 1
            else:
                categories[result.category]['failed'] += 1

        print("分类统计:")
        for cat, stats in categories.items():
            total = stats['passed'] + stats['failed']
            print(f"  {cat:20s}: {stats['passed']}/{total} 通过")

        print()

        # 详细结果
        print("详细结果:")
        for result in self.results:
            status = " 通过" if result.passed else " 失败"
            elapsed = result.metrics.get('elapsed_time', 0)
            print(f"  {result.name:40s}: {status:10s} ({elapsed:.1f}s)")

            # 显示关键指标
            if 'flow_error' in result.metrics:
                print(f"    流量误差: {result.metrics['flow_error']:.3f}%")
            if 'mass_error' in result.metrics:
                print(f"    质量守恒误差: {result.metrics['mass_error']:.4f}%")
            if 'rmse' in result.metrics:
                print(f"    RMSE: {result.metrics['rmse']:.4f}")

        print("=" * 80)

        # 生成HTML报告
        html_content = self._generate_html()

        with open('validation_report.html', 'w', encoding='utf-8') as f:
            f.write(html_content)

        print(f"\n HTML验证报告已生成: validation_report.html")

        # 判断整体是否通过
        if failed_tests == 0:
            print("\n 所有验证测试通过!")
            return True
        else:
            print(f"\n {failed_tests} 个验证测试失败!")
            return False

    def _generate_html(self):
        """生成HTML报告内容"""

        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.passed)
        failed_tests = total_tests - passed_tests
        pass_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0

        # HTML模板
        html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HydroClaude 验证报告</title>
    <style>
        body {{
            font-family: Arial, 'Microsoft YaHei', sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 20px;
            margin: 30px 0;
        }}
        .metric-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }}
        .metric-card.passed {{
            background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
        }}
        .metric-card.failed {{
            background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
        }}
        .metric-card h3 {{
            margin: 0;
            font-size: 2em;
        }}
        .metric-card p {{
            margin: 5px 0 0 0;
            opacity: 0.9;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #3498db;
            color: white;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
        .status-pass {{
            color: #27ae60;
            font-weight: bold;
        }}
        .status-fail {{
            color: #e74c3c;
            font-weight: bold;
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            text-align: center;
            color: #7f8c8d;
        }}
        .progress-bar {{
            width: 100%;
            height: 30px;
            background-color: #ecf0f1;
            border-radius: 15px;
            overflow: hidden;
            margin: 20px 0;
        }}
        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #43e97b 0%, #38f9d7 100%);
            transition: width 0.3s ease;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>HydroClaude 明渠仿真验证报告</h1>
        <p><strong>生成时间:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

        <div class="summary">
            <div class="metric-card">
                <h3>{total_tests}</h3>
                <p>总测试数</p>
            </div>
            <div class="metric-card passed">
                <h3>{passed_tests}</h3>
                <p>通过</p>
            </div>
            <div class="metric-card failed">
                <h3>{failed_tests}</h3>
                <p>失败</p>
            </div>
            <div class="metric-card">
                <h3>{pass_rate:.1f}%</h3>
                <p>通过率</p>
            </div>
        </div>

        <h2>通过率</h2>
        <div class="progress-bar">
            <div class="progress-fill" style="width: {pass_rate}%;"></div>
        </div>

        <h2>详细结果</h2>
        <table>
            <thead>
                <tr>
                    <th>测试名称</th>
                    <th>类别</th>
                    <th>状态</th>
                    <th>耗时(s)</th>
                    <th>关键指标</th>
                </tr>
            </thead>
            <tbody>
"""

        # 添加每个测试结果
        for result in self.results:
            status_class = "status-pass" if result.passed else "status-fail"
            status_text = " 通过" if result.passed else " 失败"
            elapsed = result.metrics.get('elapsed_time', 0)

            # 提取关键指标
            key_metrics = []
            if 'flow_error' in result.metrics:
                key_metrics.append(f"流量误差: {result.metrics['flow_error']:.3f}%")
            if 'mass_error' in result.metrics:
                key_metrics.append(f"质量守恒: {result.metrics['mass_error']:.4f}%")
            if 'rmse' in result.metrics:
                key_metrics.append(f"RMSE: {result.metrics['rmse']:.4f}")

            metrics_str = "<br>".join(key_metrics) if key_metrics else "-"

            html += f"""
                <tr>
                    <td>{result.name}</td>
                    <td>{result.category}</td>
                    <td class="{status_class}">{status_text}</td>
                    <td>{elapsed:.1f}</td>
                    <td>{metrics_str}</td>
                </tr>
"""

        html += """
            </tbody>
        </table>

        <div class="footer">
            <p>🤖 Generated with <a href="https://claude.com/claude-code">Claude Code</a></p>
            <p>HydroClaude - Commercial-Grade Open Channel Flow Simulation</p>
        </div>
    </div>
</body>
</html>
"""

        return html


def main():
    """主函数"""
    suite = ValidationSuite()
    success = suite.run_all()

    import sys
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
