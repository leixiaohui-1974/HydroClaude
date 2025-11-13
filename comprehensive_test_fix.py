#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
综合测试修复工具
自动化诊断和修复测试案例中的常见问题

Author: HydroClaude Dev Team
Date: 2025-11-13
"""

import os
import sys
import json
import re
from pathlib import Path
from typing import List, Dict, Set
import shutil
from datetime import datetime

# 项目根目录
PROJECT_ROOT = Path(__file__).parent
TESTS_DIR = PROJECT_ROOT / "tests"
EXAMPLES_DIR = PROJECT_ROOT / "examples"
BACKUP_DIR = PROJECT_ROOT / "backups" / f"fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

class ComprehensiveTestFixer:
    """综合测试修复器"""
    
    def __init__(self):
        self.fixes_applied = 0
        self.files_modified = 0
        self.issues_found = {
            'missing_sys_path': [],
            'unicode_issues': [],
            'import_errors': [],
            'timeout_risks': [],
            'deprecated_imports': []
        }
    
    def scan_all_test_files(self) -> List[Path]:
        """扫描所有测试文件"""
        test_files = []
        
        # 扫描tests目录
        if TESTS_DIR.exists():
            test_files.extend(TESTS_DIR.rglob("*.py"))
        
        # 扫描examples目录
        if EXAMPLES_DIR.exists():
            test_files.extend(EXAMPLES_DIR.rglob("*.py"))
        
        return test_files
    
    def check_sys_path(self, content: str, file_path: Path) -> bool:
        """检查是否有正确的sys.path设置"""
        # 检查是否已经有sys.path设置
        if 'sys.path.insert' in content or 'sys.path.append' in content:
            return True
        
        # 检查是否有从项目导入
        imports = re.findall(r'from\s+(solvers|utils|models|network|control|physics|engine)\s+import', content)
        if imports:
            self.issues_found['missing_sys_path'].append(str(file_path))
            return False
        
        return True
    
    def check_unicode_issues(self, content: str, file_path: Path) -> List[str]:
        """检查Unicode字符问题"""
        problematic_chars = []
        
        # 常见的Unicode字符
        unicode_patterns = [
            (r'✓', '[OK]'),
            (r'✅', '[OK]'),
            (r'❌', '[FAIL]'),
            (r'⚠️', '[WARN]'),
            (r'ℹ️', '[INFO]'),
            (r'📊', '[CHART]'),
            (r'🎯', '[TARGET]'),
            (r'═+', '='),
            (r'─+', '-'),
        ]
        
        for pattern, replacement in unicode_patterns:
            if re.search(pattern, content):
                problematic_chars.append(pattern)
        
        if problematic_chars:
            self.issues_found['unicode_issues'].append({
                'file': str(file_path),
                'chars': problematic_chars
            })
        
        return problematic_chars
    
    def check_deprecated_imports(self, content: str, file_path: Path) -> List[str]:
        """检查废弃的导入"""
        deprecated = []
        
        deprecated_patterns = [
            'from solvers.single_canal_solver import SingleCanalSolver',
            'from solvers.canal_solver import CanalSolver',
        ]
        
        for pattern in deprecated_patterns:
            if pattern in content:
                deprecated.append(pattern)
                self.issues_found['deprecated_imports'].append({
                    'file': str(file_path),
                    'import': pattern
                })
        
        return deprecated
    
    def check_timeout_risk(self, content: str, file_path: Path) -> bool:
        """检查超时风险"""
        # 检查大网格 + 长时间模拟
        n_cells_match = re.search(r'n_cells\s*=\s*(\d+)', content)
        t_end_match = re.search(r't_end\s*=\s*([\d.]+)', content)
        
        if n_cells_match and t_end_match:
            n_cells = int(n_cells_match.group(1))
            t_end = float(t_end_match.group(1))
            
            # 如果网格数 > 1000 且模拟时间 > 100s，标记为高风险
            if n_cells > 1000 and t_end > 100:
                self.issues_found['timeout_risks'].append({
                    'file': str(file_path),
                    'n_cells': n_cells,
                    't_end': t_end
                })
                return True
        
        return False
    
    def fix_file(self, file_path: Path, dry_run: bool = False) -> Dict:
        """修复单个文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            changes = []
            
            # 1. 修复sys.path问题
            if not self.check_sys_path(content, file_path):
                # 在文件开头添加sys.path设置
                lines = content.split('\n')
                insert_pos = 0
                
                # 找到第一个import语句之前
                for i, line in enumerate(lines):
                    if line.strip() and not line.strip().startswith('#') and not line.strip().startswith('"""'):
                        if 'import' in line:
                            insert_pos = i
                            break
                
                sys_path_block = [
                    "import sys",
                    "import os",
                    "",
                    "# 添加项目根目录到sys.path",
                    "script_path = os.path.abspath(__file__)",
                    "project_root = os.path.dirname(os.path.dirname(script_path)) if 'tests' in script_path or 'examples' in script_path else os.path.dirname(script_path)",
                    "if project_root not in sys.path:",
                    "    sys.path.insert(0, project_root)",
                    ""
                ]
                
                lines = lines[:insert_pos] + sys_path_block + lines[insert_pos:]
                content = '\n'.join(lines)
                changes.append("Added sys.path configuration")
            
            # 2. 修复Unicode字符
            unicode_chars = self.check_unicode_issues(content, file_path)
            if unicode_chars:
                replacements = {
                    '\u2713': '[OK]',
                    '\u2705': '[OK]',
                    '\u274c': '[FAIL]',
                    '\u26a0\ufe0f': '[WARN]',
                    '\u2139\ufe0f': '[INFO]',
                    '\U0001f4ca': '[CHART]',
                    '\U0001f3af': '[TARGET]',
                }
                
                for char, replacement in replacements.items():
                    if char in content:
                        content = content.replace(char, replacement)
                        changes.append(f"Replaced Unicode char with '{replacement}'")
            
            # 3. 修复废弃导入
            deprecated = self.check_deprecated_imports(content, file_path)
            if deprecated:
                # 替换为推荐的导入
                content = content.replace(
                    'from solvers.single_canal_solver import SingleCanalSolver',
                    '# DEPRECATED: Use HydrostaticCanalSolver instead\n# from solvers.single_canal_solver import SingleCanalSolver'
                )
                content = content.replace(
                    'from solvers.canal_solver import CanalSolver',
                    '# DEPRECATED: Use HydrostaticCanalSolver instead\n# from solvers.canal_solver import CanalSolver'
                )
                changes.append("Commented out deprecated imports")
            
            # 如果有修改，保存文件
            if content != original_content and not dry_run:
                # 创建备份
                backup_path = BACKUP_DIR / file_path.relative_to(PROJECT_ROOT)
                backup_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file_path, backup_path)
                
                # 保存修改
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                self.files_modified += 1
                self.fixes_applied += len(changes)
            
            return {
                'success': True,
                'changes': changes,
                'file': str(file_path)
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'file': str(file_path)
            }
    
    def generate_report(self) -> str:
        """生成修复报告"""
        report = []
        report.append("=" * 80)
        report.append("综合测试修复报告 - Comprehensive Test Fix Report")
        report.append("=" * 80)
        report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        report.append("## 修复统计")
        report.append(f"- 修改文件数: {self.files_modified}")
        report.append(f"- 应用修复数: {self.fixes_applied}")
        report.append("")
        
        report.append("## 发现的问题")
        report.append(f"- 缺少sys.path配置: {len(self.issues_found['missing_sys_path'])}个文件")
        report.append(f"- Unicode编码问题: {len(self.issues_found['unicode_issues'])}个文件")
        report.append(f"- 废弃导入: {len(self.issues_found['deprecated_imports'])}个文件")
        report.append(f"- 超时风险: {len(self.issues_found['timeout_risks'])}个文件")
        report.append("")
        
        # 详细列表
        if self.issues_found['missing_sys_path']:
            report.append("### 缺少sys.path配置的文件:")
            for file in self.issues_found['missing_sys_path'][:10]:
                report.append(f"  - {file}")
            if len(self.issues_found['missing_sys_path']) > 10:
                report.append(f"  ... 还有 {len(self.issues_found['missing_sys_path']) - 10} 个文件")
            report.append("")
        
        if self.issues_found['timeout_risks']:
            report.append("### 可能超时的文件:")
            for item in self.issues_found['timeout_risks'][:5]:
                report.append(f"  - {item['file']}")
                report.append(f"    网格数: {item['n_cells']}, 模拟时间: {item['t_end']}s")
            report.append("")
        
        report.append("=" * 80)
        return '\n'.join(report)
    
    def run(self, dry_run: bool = False):
        """运行修复"""
        print("=" * 80)
        print("综合测试修复工具 - Comprehensive Test Fixer")
        print("=" * 80)
        print(f"模式: {'DRY RUN (扫描)' if dry_run else 'APPLY FIXES (修复)'}")
        print("")
        
        # 扫描所有文件
        print("[1/3] 扫描测试文件...")
        test_files = self.scan_all_test_files()
        print(f"[OK] 找到 {len(test_files)} 个Python文件")
        print("")
        
        # 分析文件
        print("[2/3] 分析问题...")
        for file_path in test_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                self.check_sys_path(content, file_path)
                self.check_unicode_issues(content, file_path)
                self.check_deprecated_imports(content, file_path)
                self.check_timeout_risk(content, file_path)
            except Exception as e:
                print(f"[WARN] 无法读取 {file_path}: {e}")
        
        print("[OK] 分析完成")
        print("")
        
        # 应用修复
        if not dry_run:
            print("[3/3] 应用修复...")
            BACKUP_DIR.mkdir(parents=True, exist_ok=True)
            
            for file_path in test_files:
                has_issues = (
                    str(file_path) in self.issues_found['missing_sys_path'] or
                    any(str(file_path) == item['file'] for item in self.issues_found['unicode_issues']) or
                    any(str(file_path) == item['file'] for item in self.issues_found['deprecated_imports'])
                )
                
                if has_issues:
                    result = self.fix_file(file_path, dry_run=dry_run)
                    if result['success'] and result['changes']:
                        print(f"[OK] {file_path.relative_to(PROJECT_ROOT)}")
                        for change in result['changes']:
                            print(f"     - {change}")
        else:
            print("[3/3] 跳过修复（DRY RUN模式）")
        
        print("")
        print(self.generate_report())
        
        # 保存报告
        report_path = PROJECT_ROOT / "test_results" / "comprehensive_fix_report.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(self.generate_report())
        
        print(f"\n[OK] 报告已保存: {report_path}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='综合测试修复工具')
    parser.add_argument('--dry-run', action='store_true', help='仅扫描，不应用修复')
    parser.add_argument('--apply', action='store_true', help='应用修复')
    
    args = parser.parse_args()
    
    fixer = ComprehensiveTestFixer()
    fixer.run(dry_run=not args.apply)


if __name__ == '__main__':
    main()

