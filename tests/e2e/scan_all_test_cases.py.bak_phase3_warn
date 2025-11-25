#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
扫描并整理所有后端测试案例

系统化地从整个项目中找到所有测试案例，生成完整的测试清单

Author: HydroClaude Team
Date: 2025-11-15
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime


class TestCaseScanner:
    """测试案例扫描器"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.all_cases = []
        
        # 定义搜索路径
        self.search_paths = [
            self.project_root / "examples",
            self.project_root / "tests",
        ]
        
        # 排除路径
        self.exclude_patterns = [
            "backups",
            "__pycache__",
            ".git",
            "node_modules",
            "deprecated"
        ]
    
    def should_exclude(self, path: Path) -> bool:
        """检查路径是否应该排除"""
        path_str = str(path)
        return any(pattern in path_str for pattern in self.exclude_patterns)
    
    def scan_all_cases(self) -> List[Dict[str, Any]]:
        """扫描所有测试案例"""
        print("="*60)
        print("🔍 扫描项目中的所有测试案例")
        print("="*60)
        print()
        
        for search_path in self.search_paths:
            if not search_path.exists():
                continue
            
            print(f"📂 扫描目录: {search_path}")
            self._scan_directory(search_path)
        
        print()
        print(f"✅ 共找到 {len(self.all_cases)} 个测试案例")
        print()
        
        return self.all_cases
    
    def _scan_directory(self, directory: Path):
        """递归扫描目录"""
        try:
            for item in directory.iterdir():
                if self.should_exclude(item):
                    continue
                
                if item.is_file() and item.suffix == '.py':
                    self._analyze_python_file(item)
                elif item.is_dir():
                    self._scan_directory(item)
        except PermissionError:
            pass
    
    def _analyze_python_file(self, file_path: Path):
        """分析Python文件"""
        try:
            # 排除一些明显不是测试案例的文件
            filename = file_path.name
            if any(x in filename for x in ['__init__', 'utils', 'helper', 'config']):
                return
            
            # 只关注特定模式的文件
            if not any(x in filename for x in ['example', 'test', 'case', 'scenario', 'simulate', 'benchmark']):
                return
            
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # 提取信息
            case_info = {
                'file_path': str(file_path.relative_to(self.project_root)),
                'file_name': filename,
                'category': self._detect_category(file_path, content),
                'description': self._extract_description(content),
                'has_solver': 'HydrostaticCanalSolver' in content or 'GodunvFVMSolver' in content,
                'has_structures': any(x in content for x in ['SluiceGate', 'BroadCrestedWeir', 'Orifice', 'Pump']),
                'complexity': self._assess_complexity(content),
            }
            
            self.all_cases.append(case_info)
            
        except Exception as e:
            pass
    
    def _detect_category(self, file_path: Path, content: str) -> str:
        """检测案例分类"""
        path_str = str(file_path).lower()
        content_lower = content.lower()
        
        # 基于路径和内容判断分类
        if 'canal_flow' in path_str or 'uniform' in content_lower:
            return 'basic_flow'
        elif any(x in content_lower for x in ['gate', 'weir', 'orifice', 'pump']):
            return 'structures'
        elif 'network' in path_str or 'network' in content_lower:
            return 'network'
        elif 'unsteady' in path_str or 'transient' in content_lower:
            return 'unsteady'
        elif 'optimization' in path_str or 'control' in content_lower:
            return 'optimization'
        elif 'benchmark' in path_str:
            return 'benchmark'
        else:
            return 'other'
    
    def _extract_description(self, content: str) -> str:
        """提取描述"""
        lines = content.split('\n')
        
        # 查找文档字符串
        for i, line in enumerate(lines[:30]):  # 只看前30行
            if '"""' in line or "'''" in line:
                desc_lines = []
                for j in range(i, min(i+10, len(lines))):
                    if j > i and ('"""' in lines[j] or "'''" in lines[j]):
                        break
                    desc_lines.append(lines[j].strip())
                
                desc = ' '.join(desc_lines)
                desc = desc.replace('"""', '').replace("'''", '').strip()
                if desc and len(desc) > 10:
                    return desc[:200]
        
        # 查找注释
        for line in lines[:50]:
            if line.strip().startswith('#') and len(line.strip()) > 5:
                desc = line.strip()[1:].strip()
                if len(desc) > 10:
                    return desc[:200]
        
        return "No description"
    
    def _assess_complexity(self, content: str) -> str:
        """评估复杂度"""
        # 简单指标
        num_structures = sum(1 for x in ['SluiceGate', 'BroadCrestedWeir', 'Orifice', 'Pump'] if x in content)
        has_network = 'network' in content.lower()
        has_optimization = 'optimize' in content.lower() or 'control' in content.lower()
        
        if has_optimization or has_network:
            return 'hard'
        elif num_structures >= 2:
            return 'medium'
        else:
            return 'easy'
    
    def categorize_cases(self) -> Dict[str, List[Dict]]:
        """分类整理案例"""
        categories = {
            'basic_flow': [],
            'structures': [],
            'network': [],
            'unsteady': [],
            'optimization': [],
            'benchmark': [],
            'other': []
        }
        
        for case in self.all_cases:
            category = case.get('category', 'other')
            categories[category].append(case)
        
        return categories
    
    def generate_report(self):
        """生成报告"""
        categories = self.categorize_cases()
        
        print("="*60)
        print("📊 测试案例统计")
        print("="*60)
        print()
        
        total = 0
        for category, cases in categories.items():
            count = len(cases)
            total += count
            if count > 0:
                print(f"{category:20s}: {count:3d} 个案例")
        
        print(f"{'='*20}")
        print(f"{'总计':20s}: {total:3d} 个案例")
        print()
        
        # 显示每个分类的前5个案例
        print("="*60)
        print("📋 分类详情 (每类显示前5个)")
        print("="*60)
        print()
        
        for category, cases in categories.items():
            if len(cases) == 0:
                continue
            
            print(f"\n【{category}】({len(cases)}个)")
            print("-" * 60)
            for i, case in enumerate(cases[:5], 1):
                print(f"{i}. {case['file_name']}")
                print(f"   路径: {case['file_path']}")
                print(f"   复杂度: {case['complexity']}")
                if len(cases) > 5:
                    if i == 5:
                        print(f"   ... 还有 {len(cases)-5} 个案例")
    
    def export_to_json(self, output_file: Path):
        """导出为JSON"""
        categories = self.categorize_cases()
        
        output_data = {
            'scan_time': datetime.now().isoformat(),
            'total_cases': len(self.all_cases),
            'categories': {
                cat: {
                    'count': len(cases),
                    'cases': cases
                }
                for cat, cases in categories.items()
            },
            'summary': {
                category: len(cases)
                for category, cases in categories.items()
            }
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 已导出到: {output_file}")


def main():
    """主函数"""
    scanner = TestCaseScanner()
    
    # 扫描所有案例
    scanner.scan_all_cases()
    
    # 生成报告
    scanner.generate_report()
    
    # 导出JSON
    output_file = Path(__file__).parent / "all_test_cases_scan.json"
    scanner.export_to_json(output_file)
    
    print()
    print("="*60)
    print("✅ 扫描完成")
    print("="*60)
    print()
    print("下一步:")
    print("  1. 查看扫描结果: all_test_cases_scan.json")
    print("  2. 运行转换脚本: python convert_all_test_cases.py")
    print("  3. 开始测试: python test_web_e2e.py")


if __name__ == "__main__":
    main()
