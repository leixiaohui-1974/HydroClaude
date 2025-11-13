#!/usr/bin/env python
"""
HydroClaude CLI Tool

方便的命令行工具，用于运行示例、测试和管理HydroClaude系统

作者: HydroClaude Team
日期: 2025-10-22
"""

import sys
import os
import argparse
from pathlib import Path


class HydroClaudeCLI:
    """HydroClaude命令行工具"""

    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.examples_dir = self.base_dir / "examples"

        # 可用的示例
        self.examples = {
            '17': {
                'name': '单水库基础仿真',
                'dir': 'example_17_reservoir_basic',
                'script': 'demo_reservoir.py',
                'description': '学习水库基本概念和物理仿真'
            },
            '18': {
                'name': '三级梯级水电站',
                'dir': 'example_18_cascade_hydropower',
                'script': 'demo_cascade.py',
                'description': '梯级水库联合优化调度'
            },
            '19': {
                'name': '长距离调水工程',
                'dir': 'example_19_water_transfer',
                'script': 'demo_water_transfer.py',
                'description': '跨流域调水工程优化'
            },
            '20': {
                'name': '城市供水管网',
                'dir': 'example_20_urban_water_supply',
                'script': 'demo_urban_supply.py',
                'description': '多水源城市供水优化'
            },
            '21': {
                'name': '灌区配水优化',
                'dir': 'example_21_irrigation_optimization',
                'script': 'demo_irrigation.py',
                'description': '多作物轮灌优化调度'
            }
        }

    def list_examples(self):
        """列出所有可用示例"""
        print("=" * 80)
        print("HydroClaude 可用示例")
        print("=" * 80)
        print()

        for num, info in sorted(self.examples.items()):
            print(f"示例 {num}: {info['name']}")
            print(f"  描述: {info['description']}")
            print(f"  位置: examples/{info['dir']}")
            print()

        print("使用方法:")
        print("  python hydro_cli.py run <示例编号>")
        print("  例如: python hydro_cli.py run 17")
        print()

    def run_example(self, example_num: str):
        """运行指定示例"""
        if example_num not in self.examples:
            print(f"错误: 示例 {example_num} 不存在")
            print("请使用 'python hydro_cli.py list' 查看可用示例")
            return False

        info = self.examples[example_num]
        example_path = self.examples_dir / info['dir'] / info['script']

        if not example_path.exists():
            print(f"错误: 示例文件不存在: {example_path}")
            return False

        print("=" * 80)
        print(f"运行示例 {example_num}: {info['name']}")
        print("=" * 80)
        print()

        # 切换到示例目录
        os.chdir(example_path.parent)

        # 运行示例
        try:
            with open(example_path, 'r', encoding='utf-8') as f:
                code = f.read()

            exec(code, {'__name__': '__main__'})
            return True

        except Exception as e:
            print(f"\n运行失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def check_environment(self):
        """检查环境依赖"""
        print("=" * 80)
        print("检查环境依赖")
        print("=" * 80)
        print()

        required_packages = [
            ('numpy', '数值计算'),
            ('scipy', '科学计算'),
            ('matplotlib', '可视化'),
            ('pyomo', '优化建模（可选）'),
            ('pandas', '数据处理（可选）')
        ]

        all_good = True

        for package, description in required_packages:
            try:
                __import__(package)
                print(f" {package:15s} - {description}")
            except ImportError:
                print(f" {package:15s} - {description} [未安装]")
                all_good = False

        print()

        if all_good:
            print(" 所有依赖已安装")
        else:
            print(" 部分依赖未安装")
            print("\n安装方法:")
            print("  pip install -r requirements_reservoir.txt")

        print()

    def run_tests(self):
        """运行测试套件"""
        print("=" * 80)
        print("运行测试套件")
        print("=" * 80)
        print()

        test_file = self.base_dir / "tests" / "test_reservoir.py"

        if not test_file.exists():
            print(f"错误: 测试文件不存在: {test_file}")
            return False

        print(f"运行: {test_file}")
        print()

        try:
            os.chdir(self.base_dir)
            import subprocess
            result = subprocess.run(
                [sys.executable, str(test_file)],
                capture_output=False,
                text=True
            )
            return result.returncode == 0

        except Exception as e:
            print(f"测试运行失败: {e}")
            return False

    def show_info(self):
        """显示系统信息"""
        print("=" * 80)
        print("HydroClaude 系统信息")
        print("=" * 80)
        print()

        print(f"版本: v2.0.0")
        print(f"安装位置: {self.base_dir}")
        print(f"Python版本: {sys.version}")
        print()

        print(f"可用示例数: {len(self.examples)}")
        print(f"核心组件: 水库、梯级、优化调度")
        print()

        print("文档:")
        docs = [
            ('docs/EXAMPLES_GUIDE.md', '示例应用指南'),
            ('docs/INTEGRATION_DESIGN.md', '融合架构设计'),
            ('physics/README_RESERVOIR.md', 'API文档')
        ]

        for doc, desc in docs:
            doc_path = self.base_dir / doc
            status = "" if doc_path.exists() else ""
            print(f"  {status} {doc:40s} - {desc}")

        print()

    def show_help(self):
        """显示帮助信息"""
        print("""
HydroClaude CLI Tool - 命令行工具

用法:
  python hydro_cli.py <命令> [参数]

命令:
  list              列出所有可用示例
  run <编号>        运行指定编号的示例
  check             检查环境依赖
  test              运行测试套件
  info              显示系统信息
  help              显示此帮助信息

示例:
  python hydro_cli.py list
  python hydro_cli.py run 17
  python hydro_cli.py check
  python hydro_cli.py test

更多信息:
  查看文档: docs/EXAMPLES_GUIDE.md
  GitHub: https://github.com/leixiaohui-1974/HydroClaude
""")


def main():
    """主函数"""
    cli = HydroClaudeCLI()

    if len(sys.argv) < 2:
        cli.show_help()
        return

    command = sys.argv[1].lower()

    if command == 'list':
        cli.list_examples()

    elif command == 'run':
        if len(sys.argv) < 3:
            print("错误: 请指定示例编号")
            print("使用方法: python hydro_cli.py run <编号>")
            return
        example_num = sys.argv[2]
        cli.run_example(example_num)

    elif command == 'check':
        cli.check_environment()

    elif command == 'test':
        cli.run_tests()

    elif command == 'info':
        cli.show_info()

    elif command in ['help', '-h', '--help']:
        cli.show_help()

    else:
        print(f"错误: 未知命令 '{command}'")
        print("使用 'python hydro_cli.py help' 查看帮助")


if __name__ == "__main__":
    main()
