#!/usr/bin/env python3
"""
HydroClaude 统一命令行工具

提供一站式命令行接口，整合所有HydroClaude功能。

使用方法：
    hydroclaude run <config.yaml>          # 运行模拟
    hydroclaude config create              # 创建配置
    hydroclaude validate <examples>        # 验证示例
    hydroclaude test                       # 运行测试
    hydroclaude benchmark                  # 性能测试
    hydroclaude health                     # 健康检查
    hydroclaude docs                       # 查看文档
    hydroclaude version                    # 版本信息

作者: Claude Code
创建日期: 2025-10-24
"""

import sys
import argparse
from pathlib import Path
import subprocess

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))


class HydroClaudeCLI:
    """HydroClaude命令行工具"""

    VERSION = "1.0.0"

    def __init__(self):
        self.project_root = PROJECT_ROOT

    def run_simulation(self, config_file: str, **kwargs):
        """运行模拟"""
        print(f"🚀 运行模拟: {config_file}")

        from modeling.universal_modeler import UniversalModeler

        try:
            modeler = UniversalModeler(config_file)
            results = modeler.run()

            print(f"✅ 模拟完成")
            print(f"   模拟时间: {results.get('time', [])[-1] if 'time' in results and len(results['time']) > 0 else 'N/A'} s")

            return 0
        except Exception as e:
            print(f"❌ 模拟失败: {e}")
            return 1

    def create_config(self, **kwargs):
        """创建配置文件"""
        print("📝 配置文件生成向导")

        from utils.config_generator import ConfigGenerator

        gen = ConfigGenerator()

        if kwargs.get('template'):
            # 使用模板
            template_name = kwargs['template']
            output = kwargs.get('output', 'config.yaml')

            try:
                config = gen.load_template(template_name)
                gen.save_config(config, output)
                print(f"✅ 配置已创建: {output}")
                return 0
            except Exception as e:
                print(f"❌ 创建失败: {e}")
                return 1
        else:
            # 交互式向导
            gen.interactive_wizard()
            return 0

    def validate_examples(self, **kwargs):
        """验证示例"""
        print("🔍 验证示例案例")

        cmd = [sys.executable, str(self.project_root / "examples" / "validate_new_examples.py")]

        if kwargs.get('verbose'):
            cmd.append('--verbose')
        if kwargs.get('quick'):
            cmd.append('--quick')
        if kwargs.get('report'):
            cmd.append('--report')

        result = subprocess.run(cmd)
        return result.returncode

    def run_tests(self, **kwargs):
        """运行测试"""
        print("🧪 运行测试套件")

        test_type = kwargs.get('type', 'all')

        if test_type == 'unit':
            cmd = [sys.executable, '-m', 'pytest', 'unit_tests/', '-v']
        elif test_type == 'integration':
            cmd = [sys.executable, '-m', 'pytest', 'integration_tests/', '-v']
        elif test_type == 'all':
            cmd = [sys.executable, '-m', 'pytest', 'unit_tests/', 'integration_tests/', '-v']
        else:
            print(f"❌ 未知测试类型: {test_type}")
            return 1

        if kwargs.get('coverage'):
            cmd.extend(['--cov=.', '--cov-report=html'])

        result = subprocess.run(cmd, cwd=str(self.project_root))
        return result.returncode

    def run_benchmark(self, **kwargs):
        """运行性能测试"""
        print("⚡ 运行性能基准测试")

        cmd = [sys.executable, '-m', 'utils.benchmark']

        result = subprocess.run(cmd, cwd=str(self.project_root))
        return result.returncode

    def health_check(self, **kwargs):
        """项目健康检查"""
        print("🏥 项目健康检查")

        cmd = [sys.executable, str(self.project_root / "check_project_health.py")]

        if kwargs.get('verbose'):
            cmd.append('--verbose')
        if kwargs.get('report'):
            cmd.append('--report')

        result = subprocess.run(cmd)
        return result.returncode

    def show_docs(self, **kwargs):
        """显示文档"""
        print("📚 HydroClaude 文档")
        print("\n可用文档:")
        print("  - README.md: 项目总览")
        print("  - QUICKSTART.md: 快速入门")
        print("  - DEVELOPMENT_SUMMARY.md: 开发总结")
        print("  - examples/EXAMPLES_CATALOG.md: 示例目录")
        print("  - examples/engineering_cases/README.md: 工程案例")

        doc_type = kwargs.get('type')

        if doc_type:
            doc_map = {
                'readme': 'README.md',
                'quickstart': 'QUICKSTART.md',
                'summary': 'DEVELOPMENT_SUMMARY.md',
                'examples': 'examples/EXAMPLES_CATALOG.md',
                'cases': 'examples/engineering_cases/README.md'
            }

            doc_path = self.project_root / doc_map.get(doc_type, doc_type)

            if doc_path.exists():
                print(f"\n打开文档: {doc_path}")
                # 尝试用默认程序打开
                import platform
                if platform.system() == 'Darwin':  # macOS
                    subprocess.run(['open', str(doc_path)])
                elif platform.system() == 'Windows':
                    subprocess.run(['start', str(doc_path)], shell=True)
                else:  # Linux
                    subprocess.run(['xdg-open', str(doc_path)])
            else:
                print(f"❌ 文档不存在: {doc_path}")
                return 1

        return 0

    def show_version(self):
        """显示版本信息"""
        print(f"HydroClaude v{self.VERSION}")
        print(f"Python {sys.version}")
        print(f"项目路径: {self.project_root}")
        return 0

    def list_examples(self):
        """列出所有示例"""
        print("📋 可用示例案例\n")

        examples_dir = self.project_root / "examples"

        print("工程案例:")
        cases_dir = examples_dir / "engineering_cases"
        if cases_dir.exists():
            for case in sorted(cases_dir.iterdir()):
                if case.is_dir() and case.name.startswith('case_'):
                    readme = case / "README.md"
                    if readme.exists():
                        # 读取第一行作为描述
                        with open(readme) as f:
                            title = f.readline().strip().replace('#', '').strip()
                        print(f"  - {case.name}: {title}")
                    else:
                        print(f"  - {case.name}")

        print("\n基础示例:")
        for example in sorted(examples_dir.iterdir()):
            if example.is_dir() and example.name.startswith('example_'):
                print(f"  - {example.name}")

        return 0

    def export_data(self, input_file: str, **kwargs):
        """导出数据"""
        print(f"📤 导出数据: {input_file}")

        from utils.data_exporter import DataExporter
        import numpy as np

        # 加载数据
        if not Path(input_file).exists():
            print(f"❌ 文件不存在: {input_file}")
            return 1

        try:
            data = np.load(input_file)

            exporter = DataExporter(output_dir=kwargs.get('output_dir', './'))

            formats = kwargs.get('formats', ['csv', 'json']).split(',')

            # 假设数据包含time和其他数组
            if 'time' in data:
                time = data['time']
                for key in data.keys():
                    if key != 'time':
                        files = exporter.export_time_series(
                            time, data[key],
                            filename=key,
                            formats=formats
                        )
                        print(f"✅ 导出 {key}: {list(files.keys())}")
            else:
                print("⚠️  数据中没有time字段，使用索引")

            return 0
        except Exception as e:
            print(f"❌ 导出失败: {e}")
            return 1

    def generate_report(self, **kwargs):
        """生成报告"""
        print("📊 生成报告")

        from utils.report_generator import ReportGenerator

        reporter = ReportGenerator()

        # 添加系统信息（示例）
        reporter.add_system_info('项目', 'HydroClaude')
        reporter.add_system_info('版本', self.VERSION)

        output = kwargs.get('output', 'report.html')
        format_type = kwargs.get('format', 'html')

        if format_type == 'html':
            reporter.generate_html(output)
        elif format_type == 'markdown':
            reporter.generate_markdown(output)
        else:
            print(f"❌ 未知格式: {format_type}")
            return 1

        print(f"✅ 报告已生成: {output}")
        return 0


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='HydroClaude - 水力学仿真与优化框架',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s run config.yaml                    # 运行模拟
  %(prog)s config create --template basic_canal  # 创建配置
  %(prog)s validate --report                  # 验证示例并生成报告
  %(prog)s test --type unit                   # 运行单元测试
  %(prog)s benchmark                          # 性能测试
  %(prog)s health --report                    # 健康检查
  %(prog)s list                               # 列出示例
  %(prog)s docs --type quickstart             # 查看快速入门
        """
    )

    parser.add_argument('--version', action='version', version=f'%(prog)s {HydroClaudeCLI.VERSION}')

    subparsers = parser.add_subparsers(dest='command', help='可用命令')

    # run命令
    run_parser = subparsers.add_parser('run', help='运行模拟')
    run_parser.add_argument('config', help='配置文件路径')
    run_parser.add_argument('--output-dir', help='输出目录')

    # config命令
    config_parser = subparsers.add_parser('config', help='配置文件操作')
    config_subparsers = config_parser.add_subparsers(dest='config_command')

    create_parser = config_subparsers.add_parser('create', help='创建配置文件')
    create_parser.add_argument('--template', choices=['basic_canal', 'canal_with_gate',
                                                      'canal_with_control', 'multi_structure'],
                              help='使用模板')
    create_parser.add_argument('--output', default='config.yaml', help='输出文件名')

    # validate命令
    validate_parser = subparsers.add_parser('validate', help='验证示例')
    validate_parser.add_argument('--verbose', '-v', action='store_true', help='详细输出')
    validate_parser.add_argument('--quick', '-q', action='store_true', help='快速模式')
    validate_parser.add_argument('--report', '-r', action='store_true', help='生成报告')

    # test命令
    test_parser = subparsers.add_parser('test', help='运行测试')
    test_parser.add_argument('--type', choices=['unit', 'integration', 'all'],
                           default='all', help='测试类型')
    test_parser.add_argument('--coverage', action='store_true', help='生成覆盖率报告')

    # benchmark命令
    benchmark_parser = subparsers.add_parser('benchmark', help='性能测试')

    # health命令
    health_parser = subparsers.add_parser('health', help='健康检查')
    health_parser.add_argument('--verbose', '-v', action='store_true', help='详细输出')
    health_parser.add_argument('--report', '-r', action='store_true', help='生成报告')

    # docs命令
    docs_parser = subparsers.add_parser('docs', help='查看文档')
    docs_parser.add_argument('--type', choices=['readme', 'quickstart', 'summary',
                                               'examples', 'cases'],
                           help='文档类型')

    # list命令
    list_parser = subparsers.add_parser('list', help='列出示例')

    # export命令
    export_parser = subparsers.add_parser('export', help='导出数据')
    export_parser.add_argument('input', help='输入文件(.npz)')
    export_parser.add_argument('--formats', default='csv,json', help='导出格式(逗号分隔)')
    export_parser.add_argument('--output-dir', default='./', help='输出目录')

    # report命令
    report_parser = subparsers.add_parser('report', help='生成报告')
    report_parser.add_argument('--format', choices=['html', 'markdown'], default='html')
    report_parser.add_argument('--output', default='report.html', help='输出文件')

    # version命令
    version_parser = subparsers.add_parser('version', help='版本信息')

    args = parser.parse_args()

    cli = HydroClaudeCLI()

    # 分发命令
    if args.command == 'run':
        return cli.run_simulation(args.config, output_dir=getattr(args, 'output_dir', None))

    elif args.command == 'config':
        if args.config_command == 'create':
            return cli.create_config(template=args.template, output=args.output)

    elif args.command == 'validate':
        return cli.validate_examples(verbose=args.verbose, quick=args.quick, report=args.report)

    elif args.command == 'test':
        return cli.run_tests(type=args.type, coverage=args.coverage)

    elif args.command == 'benchmark':
        return cli.run_benchmark()

    elif args.command == 'health':
        return cli.health_check(verbose=args.verbose, report=args.report)

    elif args.command == 'docs':
        return cli.show_docs(type=args.type)

    elif args.command == 'list':
        return cli.list_examples()

    elif args.command == 'export':
        return cli.export_data(args.input, formats=args.formats, output_dir=args.output_dir)

    elif args.command == 'report':
        return cli.generate_report(format=args.format, output=args.output)

    elif args.command == 'version':
        return cli.show_version()

    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
