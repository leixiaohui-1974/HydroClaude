#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
整理examples目录的脚本
- 清理重复文件
- 统一目录结构
- 运行所有示例并生成结果
"""

import os
import sys
import shutil
from pathlib import Path
import json

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))


class ExampleOrganizer:
    """示例目录整理器"""

    def __init__(self, examples_root):
        self.examples_root = Path(examples_root)
        self.report = {
            'cleaned': [],
            'organized': [],
            'errors': []
        }

    def create_standard_structure(self, example_dir):
        """为每个example创建标准目录结构"""
        subdirs = ['outputs', 'outputs/figures', 'outputs/animations', 'outputs/data', 'docs']

        for subdir in subdirs:
            (example_dir / subdir).mkdir(parents=True, exist_ok=True)

        # 如果没有code目录，创建一个
        if not (example_dir / 'code').exists():
            (example_dir / 'code').mkdir(exist_ok=True)

    def clean_example_01(self):
        """清理example_01的重复文件"""
        example_01 = self.examples_root / 'example_01_canal_flow'

        print(f"\n{'='*80}")
        print("清理 example_01_canal_flow")
        print('='*80)

        # 1. 删除_deprecated目录
        deprecated_dir = example_01 / 'code' / '_deprecated'
        if deprecated_dir.exists():
            print(f"删除废弃文件目录: {deprecated_dir}")
            shutil.rmtree(deprecated_dir)
            self.report['cleaned'].append(str(deprecated_dir))

        # 2. 移动测试脚本到tests目录
        tests_dir = example_01 / 'tests'
        tests_dir.mkdir(exist_ok=True)

        test_scripts = list(example_01.glob('test_*.py')) + list(example_01.glob('analyze_*.py'))
        for script in test_scripts:
            dest = tests_dir / script.name
            print(f"移动测试脚本: {script.name} -> tests/")
            shutil.move(str(script), str(dest))
            self.report['cleaned'].append(f"Moved {script.name}")

        # 3. 整理示例脚本
        # 保留code/目录下的核心脚本，移动根目录的example脚本到archive
        archive_dir = example_01 / 'archive'
        archive_dir.mkdir(exist_ok=True)

        example_scripts = [f for f in example_01.glob('example_*.py') if f.is_file()]
        for script in example_scripts:
            dest = archive_dir / script.name
            print(f"归档示例脚本: {script.name} -> archive/")
            shutil.move(str(script), str(dest))
            self.report['cleaned'].append(f"Archived {script.name}")

        print(f" example_01 清理完成")
        return True

    def organize_all_examples(self):
        """整理所有example目录"""
        print(f"\n{'='*80}")
        print("整理所有example目录结构")
        print('='*80)

        example_dirs = sorted([d for d in self.examples_root.glob('example_*') if d.is_dir()])

        for example_dir in example_dirs:
            print(f"\n处理: {example_dir.name}")

            # 创建标准目录结构
            self.create_standard_structure(example_dir)

            # 移动现有的输出文件
            self._organize_outputs(example_dir)

            self.report['organized'].append(example_dir.name)
            print(f"   目录结构已标准化")

    def _organize_outputs(self, example_dir):
        """整理输出文件到outputs目录"""
        outputs_dir = example_dir / 'outputs'

        # 移动figures目录
        old_figures = example_dir / 'figures'
        if old_figures.exists() and old_figures != outputs_dir / 'figures':
            for fig in old_figures.glob('*'):
                if fig.suffix in ['.png', '.jpg', '.jpeg']:
                    shutil.move(str(fig), str(outputs_dir / 'figures' / fig.name))
                elif fig.suffix in ['.gif']:
                    shutil.move(str(fig), str(outputs_dir / 'animations' / fig.name))
            if not any(old_figures.iterdir()):
                old_figures.rmdir()

        # 移动reports目录
        old_reports = example_dir / 'reports'
        if old_reports.exists():
            # 移动reports/figures下的图片
            reports_figures = old_reports / 'figures'
            if reports_figures.exists():
                for fig in reports_figures.glob('*'):
                    if fig.suffix in ['.png', '.jpg', '.jpeg']:
                        shutil.move(str(fig), str(outputs_dir / 'figures' / fig.name))
                    elif fig.suffix in ['.gif']:
                        shutil.move(str(fig), str(outputs_dir / 'animations' / fig.name))

    def identify_core_scripts(self):
        """识别每个example的核心脚本"""
        print(f"\n{'='*80}")
        print("识别核心示例脚本")
        print('='*80)

        core_scripts = {}
        example_dirs = sorted([d for d in self.examples_root.glob('example_*') if d.is_dir()])

        for example_dir in example_dirs:
            scripts = []

            # 优先选择code/目录下的脚本
            code_dir = example_dir / 'code'
            if code_dir.exists():
                code_scripts = [f for f in code_dir.glob('*.py')
                               if f.name not in ['__init__.py']
                               and not f.name.startswith('test_')]
                scripts.extend(code_scripts)

            # 如果code/目录没有脚本，查找根目录
            if not scripts:
                root_scripts = [f for f in example_dir.glob('*.py')
                               if f.name not in ['__init__.py']
                               and not f.name.startswith('test_')
                               and 'enhanced' not in f.name]
                scripts.extend(root_scripts[:1])  # 只取第一个

            core_scripts[example_dir.name] = scripts

            if scripts:
                print(f"\n{example_dir.name}:")
                for s in scripts:
                    print(f"  - {s.relative_to(example_dir)}")
            else:
                print(f"\n{example_dir.name}:   未找到核心脚本")

        return core_scripts

    def save_report(self):
        """保存整理报告"""
        report_file = self.examples_root / 'organization_report.json'
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(self.report, f, indent=2, ensure_ascii=False)

        print(f"\n{'='*80}")
        print(f"整理报告已保存到: {report_file}")
        print('='*80)
        print(f"清理项: {len(self.report['cleaned'])}")
        print(f"整理项: {len(self.report['organized'])}")
        print(f"错误数: {len(self.report['errors'])}")


def main():
    """主函数"""
    examples_root = Path(__file__).parent

    organizer = ExampleOrganizer(examples_root)

    # 1. 清理example_01
    organizer.clean_example_01()

    # 2. 整理所有example的目录结构
    organizer.organize_all_examples()

    # 3. 识别核心脚本
    core_scripts = organizer.identify_core_scripts()

    # 4. 保存报告
    organizer.save_report()

    print(f"\n{'='*80}")
    print(" 目录整理完成！")
    print('='*80)

    return core_scripts


if __name__ == '__main__':
    main()
