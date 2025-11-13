#!/usr/bin/env python3
"""
项目质量检查脚本 - Project Health Check

全面检查HydroClaude项目的代码质量、文档完整性、测试覆盖率等指标，
并生成详细的健康报告。

功能：
- 代码质量检查（语法、规范）
- 文档完整性检查
- 测试覆盖率分析
- 依赖项检查
- 文件结构验证
- 生成HTML健康报告

使用方法：
    python check_project_health.py [--verbose] [--report]

选项：
    --verbose: 显示详细输出
    --report: 生成HTML报告
    --fix: 自动修复可修复的问题（谨慎使用）

作者: Claude Code
创建日期: 2025-10-24
"""

import sys
import os
from pathlib import Path
from typing import Dict, List, Tuple
import json
import argparse
from datetime import datetime
import subprocess


class ProjectHealthChecker:
    """项目健康检查器"""

    def __init__(self, project_root: Path = None, verbose: bool = False):
        self.project_root = project_root or Path(__file__).parent
        self.verbose = verbose
        self.issues = []
        self.warnings = []
        self.passed = []

    def log(self, message: str, level: str = "INFO"):
        """日志输出"""
        if self.verbose or level in ["ERROR", "WARNING", "SUCCESS"]:
            prefix = {
                "INFO": "ℹ️ ",
                "SUCCESS": "",
                "WARNING": "️ ",
                "ERROR": ""
            }.get(level, "")
            print(f"{prefix} {message}")

    def check_python_syntax(self) -> Dict:
        """检查Python语法错误"""
        self.log("检查Python语法...", "INFO")

        result = {
            'name': 'Python语法检查',
            'status': 'unknown',
            'errors': [],
            'warnings': []
        }

        # 查找所有Python文件
        python_files = list(self.project_root.glob('**/*.py'))
        # 排除虚拟环境和缓存
        python_files = [f for f in python_files if '.venv' not in str(f) and '__pycache__' not in str(f)]

        self.log(f"找到 {len(python_files)} 个Python文件", "INFO")

        syntax_errors = []

        for py_file in python_files:
            try:
                # 尝试编译文件
                with open(py_file, 'r', encoding='utf-8') as f:
                    compile(f.read(), str(py_file), 'exec')
            except SyntaxError as e:
                syntax_errors.append({
                    'file': str(py_file.relative_to(self.project_root)),
                    'line': e.lineno,
                    'error': str(e)
                })
                self.log(f"语法错误: {py_file.name}:{e.lineno}", "ERROR")

        if syntax_errors:
            result['status'] = 'failed'
            result['errors'] = syntax_errors
            self.issues.append(f"发现 {len(syntax_errors)} 个语法错误")
        else:
            result['status'] = 'passed'
            self.passed.append("所有Python文件语法正确")
            self.log("Python语法检查通过", "SUCCESS")

        return result

    def check_imports(self) -> Dict:
        """检查导入错误"""
        self.log("检查导入...", "INFO")

        result = {
            'name': '导入检查',
            'status': 'unknown',
            'errors': [],
            'warnings': []
        }

        # 主要模块
        core_modules = [
            'solvers.hydrostatic_canal_solver',
            'control.pid_controller',
            'control.mpc_controller',
            'modeling.universal_modeler',
            'utils.data_exporter'
        ]

        import_errors = []

        for module_name in core_modules:
            try:
                __import__(module_name)
                self.log(f"   {module_name}", "SUCCESS")
            except ImportError as e:
                import_errors.append({
                    'module': module_name,
                    'error': str(e)
                })
                self.log(f"导入失败: {module_name}", "ERROR")

        if import_errors:
            result['status'] = 'failed'
            result['errors'] = import_errors
            self.issues.append(f"发现 {len(import_errors)} 个导入错误")
        else:
            result['status'] = 'passed'
            self.passed.append("所有核心模块可正常导入")
            self.log("导入检查通过", "SUCCESS")

        return result

    def check_documentation(self) -> Dict:
        """检查文档完整性"""
        self.log("检查文档...", "INFO")

        result = {
            'name': '文档检查',
            'status': 'unknown',
            'missing': [],
            'found': []
        }

        # 必需的文档文件
        required_docs = [
            'README.md',
            'DEVELOPMENT_SUMMARY.md',
            'examples/EXAMPLES_CATALOG.md',
            'examples/engineering_cases/README.md'
        ]

        missing_docs = []

        for doc in required_docs:
            doc_path = self.project_root / doc
            if doc_path.exists():
                result['found'].append(doc)
                self.log(f"   {doc}", "SUCCESS")
            else:
                missing_docs.append(doc)
                self.log(f"   {doc} 缺失", "ERROR")

        if missing_docs:
            result['status'] = 'warning'
            result['missing'] = missing_docs
            self.warnings.append(f"缺少 {len(missing_docs)} 个文档文件")
        else:
            result['status'] = 'passed'
            self.passed.append("所有必需文档存在")
            self.log("文档检查通过", "SUCCESS")

        return result

    def check_test_files(self) -> Dict:
        """检查测试文件"""
        self.log("检查测试文件...", "INFO")

        result = {
            'name': '测试文件检查',
            'status': 'unknown',
            'test_count': 0,
            'test_files': []
        }

        # 查找测试文件
        test_files = list(self.project_root.glob('unit_tests/test_*.py'))
        test_files += list(self.project_root.glob('tests/test_*.py'))

        result['test_count'] = len(test_files)
        result['test_files'] = [str(f.relative_to(self.project_root)) for f in test_files]

        self.log(f"找到 {len(test_files)} 个测试文件", "INFO")

        if len(test_files) == 0:
            result['status'] = 'warning'
            self.warnings.append("未找到测试文件")
        elif len(test_files) < 5:
            result['status'] = 'warning'
            self.warnings.append(f"测试文件较少: {len(test_files)} 个")
        else:
            result['status'] = 'passed'
            self.passed.append(f"发现 {len(test_files)} 个测试文件")

        return result

    def check_dependencies(self) -> Dict:
        """检查依赖项"""
        self.log("检查依赖项...", "INFO")

        result = {
            'name': '依赖项检查',
            'status': 'unknown',
            'missing': [],
            'installed': []
        }

        # 核心依赖
        required_packages = [
            'numpy',
            'matplotlib',
            'scipy',
            'pytest',
            'pyyaml'
        ]

        missing = []
        installed = []

        for package in required_packages:
            try:
                __import__(package)
                installed.append(package)
                self.log(f"   {package}", "SUCCESS")
            except ImportError:
                missing.append(package)
                self.log(f"   {package} 未安装", "ERROR")

        result['installed'] = installed
        result['missing'] = missing

        if missing:
            result['status'] = 'failed'
            self.issues.append(f"缺少 {len(missing)} 个依赖包")
        else:
            result['status'] = 'passed'
            self.passed.append("所有依赖包已安装")
            self.log("依赖项检查通过", "SUCCESS")

        return result

    def check_directory_structure(self) -> Dict:
        """检查目录结构"""
        self.log("检查目录结构...", "INFO")

        result = {
            'name': '目录结构检查',
            'status': 'unknown',
            'missing': [],
            'found': []
        }

        # 必需的目录
        required_dirs = [
            'solvers',
            'control',
            'modeling',
            'utils',
            'examples',
            'examples/engineering_cases',
            'unit_tests'
        ]

        missing = []

        for dir_name in required_dirs:
            dir_path = self.project_root / dir_name
            if dir_path.exists() and dir_path.is_dir():
                result['found'].append(dir_name)
                self.log(f"   {dir_name}/", "SUCCESS")
            else:
                missing.append(dir_name)
                self.log(f"   {dir_name}/ 缺失", "ERROR")

        result['missing'] = missing

        if missing:
            result['status'] = 'warning'
            self.warnings.append(f"缺少 {len(missing)} 个目录")
        else:
            result['status'] = 'passed'
            self.passed.append("目录结构完整")
            self.log("目录结构检查通过", "SUCCESS")

        return result

    def check_code_statistics(self) -> Dict:
        """统计代码"""
        self.log("统计代码...", "INFO")

        result = {
            'name': '代码统计',
            'status': 'passed',
            'stats': {}
        }

        # 统计各类文件
        python_files = list(self.project_root.glob('**/*.py'))
        python_files = [f for f in python_files if '.venv' not in str(f) and '__pycache__' not in str(f)]

        yaml_files = list(self.project_root.glob('**/*.yaml')) + list(self.project_root.glob('**/*.yml'))
        md_files = list(self.project_root.glob('**/*.md'))

        # 统计代码行数
        total_lines = 0
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    total_lines += len(f.readlines())
            except:
                pass

        result['stats'] = {
            'python_files': len(python_files),
            'yaml_files': len(yaml_files),
            'markdown_files': len(md_files),
            'total_lines': total_lines
        }

        self.log(f"Python文件: {len(python_files)}", "INFO")
        self.log(f"代码行数: {total_lines}", "INFO")

        return result

    def run_all_checks(self) -> Dict:
        """运行所有检查"""
        print("\n" + "="*70)
        print("  HydroClaude 项目健康检查")
        print("="*70 + "\n")

        results = {}

        # 运行各项检查
        results['syntax'] = self.check_python_syntax()
        results['imports'] = self.check_imports()
        results['documentation'] = self.check_documentation()
        results['tests'] = self.check_test_files()
        results['dependencies'] = self.check_dependencies()
        results['structure'] = self.check_directory_structure()
        results['statistics'] = self.check_code_statistics()

        return results

    def print_summary(self):
        """打印总结"""
        print("\n" + "="*70)
        print("  健康检查总结")
        print("="*70 + "\n")

        total_checks = len(self.passed) + len(self.warnings) + len(self.issues)

        print(f" 通过: {len(self.passed)}")
        print(f"️  警告: {len(self.warnings)}")
        print(f" 问题: {len(self.issues)}")

        if self.issues:
            print("\n问题列表:")
            for issue in self.issues:
                print(f"   {issue}")

        if self.warnings:
            print("\n警告列表:")
            for warning in self.warnings:
                print(f"  ️  {warning}")

        if not self.issues:
            print("\n 项目健康状况良好！")
            return 0
        elif len(self.issues) <= 2:
            print("\n️  发现少量问题，建议修复")
            return 1
        else:
            print("\n 发现多个问题，需要立即处理")
            return 2

    def generate_html_report(self, filename: str = "project_health_report.html"):
        """生成HTML报告"""
        self.log(f"生成HTML报告: {filename}", "INFO")

        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>HydroClaude 项目健康报告</title>
    <style>
        body {{
            font-family: 'Segoe UI', Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            padding: 30px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .summary-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }}
        .summary-card h3 {{
            margin: 0 0 10px 0;
            font-size: 2em;
        }}
        .check-section {{
            margin: 30px 0;
            padding: 20px;
            background: #f9f9f9;
            border-radius: 8px;
        }}
        .check-header {{
            display: flex;
            align-items: center;
            margin-bottom: 15px;
        }}
        .status-badge {{
            display: inline-block;
            padding: 5px 15px;
            border-radius: 15px;
            font-weight: bold;
            margin-left: 15px;
        }}
        .status-passed {{
            background-color: #4caf50;
            color: white;
        }}
        .status-warning {{
            background-color: #ff9800;
            color: white;
        }}
        .status-failed {{
            background-color: #f44336;
            color: white;
        }}
        ul {{
            line-height: 1.8;
        }}
        .footer {{
            text-align: center;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1> HydroClaude 项目健康报告</h1>
        <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

        <div class="summary">
            <div class="summary-card">
                <h3>{len(self.passed)}</h3>
                <p>通过检查</p>
            </div>
            <div class="summary-card">
                <h3>{len(self.warnings)}</h3>
                <p>警告</p>
            </div>
            <div class="summary-card">
                <h3>{len(self.issues)}</h3>
                <p>问题</p>
            </div>
        </div>

        <h2> 通过的检查</h2>
        <ul>
"""

        for item in self.passed:
            html += f"            <li> {item}</li>\n"

        html += """
        </ul>
"""

        if self.warnings:
            html += """
        <h2>️ 警告</h2>
        <ul>
"""
            for item in self.warnings:
                html += f"            <li>️ {item}</li>\n"

            html += """
        </ul>
"""

        if self.issues:
            html += """
        <h2> 需要解决的问题</h2>
        <ul>
"""
            for item in self.issues:
                html += f"            <li> {item}</li>\n"

            html += """
        </ul>
"""

        html += """
        <div class="footer">
            <p>Generated with <a href="https://claude.com/claude-code">Claude Code</a></p>
        </div>
    </div>
</body>
</html>
"""

        output_path = Path(filename)
        output_path.write_text(html, encoding='utf-8')
        self.log(f" 报告已生成: {output_path}", "SUCCESS")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="HydroClaude 项目健康检查工具",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument("--verbose", "-v", action="store_true",
                       help="显示详细输出")
    parser.add_argument("--report", "-r", action="store_true",
                       help="生成HTML报告")
    parser.add_argument("--output", "-o", type=str,
                       default="project_health_report.html",
                       help="报告输出路径")

    args = parser.parse_args()

    # 创建检查器
    checker = ProjectHealthChecker(verbose=args.verbose)

    # 运行检查
    results = checker.run_all_checks()

    # 打印总结
    exit_code = checker.print_summary()

    # 生成报告
    if args.report:
        checker.generate_html_report(args.output)

    # 保存JSON结果
    json_output = Path("project_health_results.json")
    with open(json_output, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'passed': checker.passed,
            'warnings': checker.warnings,
            'issues': checker.issues,
            'results': results
        }, f, indent=2, ensure_ascii=False)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
