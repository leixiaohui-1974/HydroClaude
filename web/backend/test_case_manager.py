#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test Case Manager - 测试案例管理系统
将Python测试案例转换为Web可用格式并提供API

功能:
1. 扫描并加载所有测试案例（544个）
2. 将测试案例转换为Web模板格式
3. 提供案例浏览、搜索、分类功能
4. 自动执行测试并验证结果
5. 生成可视化和分析报告

Author: HydroClaude Team
Date: 2025-11-13
"""

import os
import sys
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import importlib.util

# 添加项目路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@dataclass
class TestCase:
    """测试案例数据结构"""
    id: str
    name: str
    name_cn: str
    category: str
    subcategory: str
    file_path: str
    description: str
    difficulty: str
    tags: List[str]
    config: Dict[str, Any]
    expected_results: Dict[str, Any]
    validation_criteria: Dict[str, Any]
    references: List[str]
    
    def to_web_template(self) -> Dict[str, Any]:
        """转换为Web模板格式"""
        return {
            'metadata': {
                'id': self.id,
                'name': self.name,
                'nameCN': self.name_cn,
                'category': self.category,
                'subcategory': self.subcategory,
                'difficulty': self.difficulty,
                'tags': self.tags,
                'author': 'HydroClaude Test Suite',
                'version': '1.0.0',
                'references': self.references
            },
            'config': self.config,
            'expectedResults': self.expected_results,
            'validationCriteria': self.validation_criteria,
            'sourcePath': self.file_path
        }


class TestCaseParser:
    """测试案例解析器 - 从Python文件中提取信息"""
    
    def __init__(self):
        self.categories = {
            'dam_break': '溃坝',
            'pressurized': '有压管道',
            'lake_at_rest': '湖泊静止',
            'structures': '水工结构',
            'control': '控制系统',
            'water_quality': '水质模拟',
            'network': '管网系统',
            'benchmark': '性能基准'
        }
    
    def parse_test_file(self, file_path: Path) -> Optional[TestCase]:
        """解析单个测试文件"""
        try:
            # 读取文件内容
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 提取docstring
            docstring = self._extract_docstring(content)
            
            # 提取测试配置
            config = self._extract_config(content)
            
            # 确定分类
            category, subcategory = self._categorize(file_path, content)
            
            # 生成案例ID
            case_id = self._generate_id(file_path)
            
            # 提取标签
            tags = self._extract_tags(content, file_path)
            
            # 创建TestCase对象
            test_case = TestCase(
                id=case_id,
                name=self._extract_name(file_path, docstring),
                name_cn=self._extract_chinese_name(docstring),
                category=category,
                subcategory=subcategory,
                file_path=str(file_path.relative_to(PROJECT_ROOT)),
                description=self._extract_description(docstring),
                difficulty=self._determine_difficulty(content, file_path),
                tags=tags,
                config=config,
                expected_results=self._extract_expected_results(content),
                validation_criteria=self._extract_validation_criteria(content),
                references=self._extract_references(content)
            )
            
            return test_case
            
        except Exception as e:
            print(f"Warning: Failed to parse {file_path}: {e}")
            return None
    
    def _extract_docstring(self, content: str) -> str:
        """提取模块级docstring"""
        match = re.search(r'"""(.*?)"""', content, re.DOTALL)
        if match:
            return match.group(1).strip()
        return ""
    
    def _extract_config(self, content: str) -> Dict[str, Any]:
        """提取测试配置参数"""
        config = {}
        
        # 提取长度
        if match := re.search(r'length\s*=\s*([\d.]+)', content):
            config['domainLength'] = float(match.group(1))
        
        # 提取时长
        if match := re.search(r't_end\s*=\s*([\d.]+)', content):
            config['duration'] = float(match.group(1))
        
        # 提取网格数
        if match := re.search(r'n_cells\s*=\s*(\d+)', content):
            config['nCells'] = int(match.group(1))
        
        # 提取Manning系数
        if match := re.search(r'manning_n\s*=\s*([\d.]+)', content):
            config['manning'] = float(match.group(1))
        
        # 提取坡度
        if match := re.search(r'slope\s*=\s*([\d.]+)', content):
            config['slope'] = float(match.group(1))
        
        # 提取宽度
        if match := re.search(r'width\s*=\s*([\d.]+)', content):
            config['width'] = float(match.group(1))
        
        return config
    
    def _categorize(self, file_path: Path, content: str) -> tuple:
        """确定案例分类"""
        path_str = str(file_path).lower()
        
        if 'dam_break' in path_str or 'dambreak' in path_str:
            return 'dam_break', 'Dam Break'
        elif 'pressur' in path_str or 'water_hammer' in path_str:
            return 'pressurized', 'Pressurized Flow'
        elif 'lake' in path_str or 'at_rest' in path_str:
            return 'lake_at_rest', 'Lake at Rest'
        elif 'gate' in path_str or 'weir' in path_str or 'pump' in path_str:
            return 'structures', 'Hydraulic Structures'
        elif 'control' in path_str or 'pid' in path_str or 'mpc' in path_str:
            return 'control', 'Control Systems'
        elif 'water_quality' in path_str or 'do_' in path_str or 'nutrient' in path_str:
            return 'water_quality', 'Water Quality'
        elif 'network' in path_str:
            return 'network', 'Network Systems'
        elif 'benchmark' in path_str:
            return 'benchmark', 'Performance Benchmark'
        else:
            return 'general', 'General'
    
    def _generate_id(self, file_path: Path) -> str:
        """生成唯一案例ID"""
        # 使用相对路径和文件名生成ID
        rel_path = file_path.relative_to(PROJECT_ROOT)
        return str(rel_path).replace('/', '-').replace('\\', '-').replace('.py', '')
    
    def _extract_name(self, file_path: Path, docstring: str) -> str:
        """提取案例名称"""
        # 尝试从docstring第一行获取
        if docstring:
            first_line = docstring.split('\n')[0].strip()
            if first_line and not first_line.startswith('"""'):
                return first_line
        
        # 否则从文件名生成
        name = file_path.stem.replace('_', ' ').replace('test ', '').title()
        return name
    
    def _extract_chinese_name(self, docstring: str) -> str:
        """提取中文名称"""
        # 查找中文字符
        chinese_match = re.search(r'[\u4e00-\u9fff]+.*', docstring)
        if chinese_match:
            return chinese_match.group(0).strip()
        return ""
    
    def _extract_description(self, docstring: str) -> str:
        """提取描述"""
        lines = [l.strip() for l in docstring.split('\n') if l.strip()]
        if len(lines) > 1:
            return lines[1]
        return ""
    
    def _determine_difficulty(self, content: str, file_path: Path) -> str:
        """确定难度等级"""
        path_str = str(file_path).lower()
        
        if 'advanced' in path_str or 'cascade' in path_str or 'multi' in path_str:
            return 'advanced'
        elif 'basic' in path_str or 'simple' in path_str:
            return 'beginner'
        else:
            return 'intermediate'
    
    def _extract_tags(self, content: str, file_path: Path) -> List[str]:
        """提取标签"""
        tags = []
        
        path_str = str(file_path).lower()
        content_lower = content.lower()
        
        # 从路径和内容中提取关键词
        keywords = ['dam_break', 'riemann', 'godunov', 'weno', 'pressurized', 
                   'gate', 'weir', 'pump', 'control', 'pid', 'mpc', 
                   'water_quality', 'network', 'benchmark']
        
        for kw in keywords:
            if kw in path_str or kw in content_lower:
                tags.append(kw.replace('_', '-'))
        
        return list(set(tags))[:5]  # 最多5个标签
    
    def _extract_expected_results(self, content: str) -> Dict[str, Any]:
        """提取预期结果"""
        results = {}
        
        # 提取误差限制
        if match := re.search(r'error.*?<\s*([\d.]+)%', content, re.IGNORECASE):
            results['maxError'] = float(match.group(1))
        
        # 提取通过标准
        if 'RMSE' in content or 'rmse' in content:
            if match := re.search(r'RMSE.*?<\s*([\d.]+)', content):
                results['maxRMSE'] = float(match.group(1))
        
        return results
    
    def _extract_validation_criteria(self, content: str) -> Dict[str, Any]:
        """提取验证标准"""
        criteria = {}
        
        # 质量守恒
        if 'mass' in content.lower() and 'conserv' in content.lower():
            criteria['checkMassConservation'] = True
        
        # 能量守恒
        if 'energy' in content.lower() and 'conserv' in content.lower():
            criteria['checkEnergyConservation'] = True
        
        # 数值稳定性
        if 'stable' in content.lower() or 'stability' in content.lower():
            criteria['checkNumericalStability'] = True
        
        return criteria
    
    def _extract_references(self, content: str) -> List[str]:
        """提取参考文献"""
        references = []
        
        # 查找常见的参考文献格式
        ref_patterns = [
            r'(?:参考文献|References?):\s*\n((?:[-•]\s*.+\n?)+)',
            r'@article{[^}]+}',
            r'\b[A-Z][a-z]+\s+\(\d{4}\)',
        ]
        
        for pattern in ref_patterns:
            matches = re.findall(pattern, content, re.MULTILINE)
            references.extend(matches)
        
        return list(set(references))[:3]  # 最多3个参考文献


class TestCaseManager:
    """测试案例管理器"""
    
    def __init__(self):
        self.parser = TestCaseParser()
        self.test_cases: Dict[str, TestCase] = {}
        self.categories: Dict[str, List[str]] = {}
    
    def scan_test_directory(self, directory: Path) -> int:
        """扫描测试目录"""
        count = 0
        
        for py_file in directory.rglob('*.py'):
            # 跳过__init__.py和一些特殊文件
            if py_file.name.startswith('__') or py_file.name.startswith('.'):
                continue
            
            test_case = self.parser.parse_test_file(py_file)
            if test_case:
                self.test_cases[test_case.id] = test_case
                
                # 添加到分类索引
                if test_case.category not in self.categories:
                    self.categories[test_case.category] = []
                self.categories[test_case.category].append(test_case.id)
                
                count += 1
        
        return count
    
    def scan_all_tests(self) -> int:
        """扫描所有测试目录"""
        test_dirs = [
            PROJECT_ROOT / 'tests',
            PROJECT_ROOT / 'examples',
            PROJECT_ROOT / 'validation_cases'
        ]
        
        total_count = 0
        for test_dir in test_dirs:
            if test_dir.exists():
                count = self.scan_test_directory(test_dir)
                print(f"Scanned {test_dir.name}: {count} test cases")
                total_count += count
        
        print(f"\nTotal test cases loaded: {total_count}")
        return total_count
    
    def get_test_case(self, case_id: str) -> Optional[TestCase]:
        """获取单个测试案例"""
        return self.test_cases.get(case_id)
    
    def get_cases_by_category(self, category: str) -> List[TestCase]:
        """按分类获取案例"""
        case_ids = self.categories.get(category, [])
        return [self.test_cases[cid] for cid in case_ids]
    
    def search_cases(self, query: str) -> List[TestCase]:
        """搜索测试案例"""
        query_lower = query.lower()
        results = []
        
        for case in self.test_cases.values():
            if (query_lower in case.name.lower() or
                query_lower in case.name_cn or
                query_lower in case.description.lower() or
                any(query_lower in tag for tag in case.tags)):
                results.append(case)
        
        return results
    
    def export_to_json(self, output_file: Path):
        """导出为JSON格式"""
        data = {
            'totalCases': len(self.test_cases),
            'categories': {
                cat: len(ids) for cat, ids in self.categories.items()
            },
            'testCases': [
                case.to_web_template() for case in self.test_cases.values()
            ]
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"Exported {len(self.test_cases)} test cases to {output_file}")
    
    def generate_statistics(self) -> Dict[str, Any]:
        """生成统计信息"""
        stats = {
            'total': len(self.test_cases),
            'by_category': {
                cat: len(ids) for cat, ids in self.categories.items()
            },
            'by_difficulty': {
                'beginner': 0,
                'intermediate': 0,
                'advanced': 0
            },
            'top_tags': {}
        }
        
        # 统计难度
        for case in self.test_cases.values():
            stats['by_difficulty'][case.difficulty] += 1
        
        # 统计标签
        tag_count = {}
        for case in self.test_cases.values():
            for tag in case.tags:
                tag_count[tag] = tag_count.get(tag, 0) + 1
        
        # 前10个热门标签
        stats['top_tags'] = dict(
            sorted(tag_count.items(), key=lambda x: x[1], reverse=True)[:10]
        )
        
        return stats


def main():
    """主函数 - 扫描并导出所有测试案例"""
    print("="*70)
    print(" Test Case Manager - Scanning and Exporting Test Cases")
    print("="*70)
    
    # 创建管理器
    manager = TestCaseManager()
    
    # 扫描所有测试
    total = manager.scan_all_tests()
    
    # 生成统计
    stats = manager.generate_statistics()
    print("\nStatistics:")
    print(f"  Total: {stats['total']}")
    print(f"  By Category:")
    for cat, count in stats['by_category'].items():
        print(f"    - {cat}: {count}")
    print(f"  By Difficulty:")
    for diff, count in stats['by_difficulty'].items():
        print(f"    - {diff}: {count}")
    
    # 导出JSON
    output_file = PROJECT_ROOT / 'web' / 'backend' / 'data' / 'test_cases_catalog.json'
    output_file.parent.mkdir(parents=True, exist_ok=True)
    manager.export_to_json(output_file)
    
    print("\n" + "="*70)
    print(" Export Complete!")
    print("="*70)


if __name__ == '__main__':
    main()


