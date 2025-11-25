#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
批量转换所有测试案例

将348个后端测试案例系统化地转换为Web端可用的JSON配置文件

Author: HydroClaude Team
Date: 2025-11-15
"""

import os
import warnings
warnings.filterwarnings("ignore")
import re
import json
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime


class BatchTestCaseConverter:
    """批量测试案例转换器"""
    
    def __init__(self):
        self.root_dir = Path(__file__).parent
        self.project_root = self.root_dir.parent.parent
        self.test_cases_dir = self.root_dir / "test_cases"
        self.scan_file = self.root_dir / "all_test_cases_scan.json"
        
        # 创建目录
        self.test_cases_dir.mkdir(exist_ok=True)
        
        # 加载扫描结果
        with open(self.scan_file, 'r', encoding='utf-8') as f:
            self.scan_data = json.load(f)
        
        self.converted_count = 0
        self.failed_count = 0
        self.converted_cases = []
    
    def convert_all(self, max_per_category: int = 20):
        """
        转换所有案例
        
        Args:
            max_per_category: 每个分类最多转换多少个案例
        """
        print("="*70)
        print("🔄 批量转换所有测试案例")
        print("="*70)
        print()
        
        categories = self.scan_data['categories']
        
        # 优先级顺序
        priority_order = [
            'basic_flow',
            'structures',
            'unsteady',
            'network',
            'optimization',
            'benchmark',
            'other'
        ]
        
        for category in priority_order:
            if category not in categories:
                continue
            
            cases = categories[category]['cases']
            count = len(cases)
            
            if count == 0:
                continue
            
            print(f"\n【{category}】- 共 {count} 个案例")
            print("-" * 70)
            
            # 限制数量
            to_convert = min(count, max_per_category)
            print(f"转换前 {to_convert} 个案例...")
            
            for i, case in enumerate(cases[:to_convert], 1):
                self._convert_single_case(case, category, i)
            
            if count > to_convert:
                print(f"  ⚠️  还有 {count - to_convert} 个案例未转换")
        
        self._generate_index()
        self._generate_summary()
    
    def _convert_single_case(self, case: Dict, category: str, index: int):
        """转换单个案例"""
        try:
            file_path = self.project_root / case['file_path']
            
            if not file_path.exists():
                self.failed_count += 1
                return
            
            # 读取文件内容
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # 提取配置
            config = self._extract_config(content, case)
            
            if not config:
                self.failed_count += 1
                return
            
            # 生成JSON文件名
            safe_name = re.sub(r'[^a-z0-9_]', '_', case['file_name'].lower().replace('.py', ''))
            json_filename = f"case_{self.converted_count+1:03d}_{category}_{safe_name}.json"
            json_path = self.test_cases_dir / json_filename
            
            # 添加元数据
            config['_metadata'] = {
                'source_file': case['file_path'],
                'category': category,
                'complexity': case.get('complexity', 'medium'),
                'converted_at': datetime.now().isoformat()
            }
            
            # 保存JSON
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            self.converted_count += 1
            self.converted_cases.append({
                'id': self.converted_count,
                'name': safe_name,
                'category': category,
                'file': json_filename,
                'source': case['file_path'],
                'complexity': case.get('complexity', 'medium')
            })
            
            print(f"  ✅ [{self.converted_count:3d}] {case['file_name'][:50]}")
            
        except Exception as e:
            self.failed_count += 1
            print(f"  ❌ 转换失败: {case['file_name']} - {str(e)[:50]}")
    
    def _extract_config(self, content: str, case: Dict) -> Dict[str, Any]:
        """从代码中提取配置"""
        config = {
            "version": "2.0.0",
            "name": case['file_name'].replace('.py', ''),
            "description": case.get('description', 'No description'),
            "type": "steady_flow"
        }
        
        # 提取参数
        params = self._extract_parameters(content)
        
        # 渠道参数
        config['canal'] = {
            "length": params.get('length', 10000.0),
            "width": params.get('width', params.get('B', 10.0)),
            "slope": params.get('slope', params.get('S0', 0.001)),
            "roughness": params.get('roughness', params.get('n', 0.025)),
            "nx": params.get('nx', 500)
        }
        
        # 流量
        config['flow'] = {
            "flow_rate": params.get('flow_rate', params.get('Q', 50.0)),
            "type": "steady"
        }
        
        # 结构
        structures = []
        if case.get('has_structures'):
            # 尝试检测结构
            if 'SluiceGate' in content:
                gate_pos = params.get('gate_position', config['canal']['length'] * 0.5)
                structures.append({
                    "type": "sluice_gate",
                    "position": gate_pos,
                    "width": config['canal']['width'],
                    "opening": params.get('gate_opening', 2.0),
                    "discharge_coefficient": 0.6
                })
            
            if 'BroadCrestedWeir' in content:
                weir_pos = params.get('weir_position', config['canal']['length'] * 0.5)
                structures.append({
                    "type": "broad_crested_weir",
                    "position": weir_pos,
                    "width": config['canal']['width'],
                    "crest_height": params.get('crest_height', 0.5),
                    "discharge_coefficient": 1.7
                })
        
        config['structures'] = structures
        
        # 求解器
        config['solver'] = {
            "type": "hydrostatic",
            "max_iter": 100,
            "convergence_tol": 0.1
        }
        
        # 输出
        config['output'] = {
            "save_plots": True,
            "save_data": True,
            "formats": ["json", "csv"]
        }
        
        return config
    
    def _extract_parameters(self, content: str) -> Dict[str, float]:
        """提取数值参数"""
        params = {}
        
        # 常见参数模式
        patterns = {
            'length': r'(?:length|L)\s*=\s*([\d.]+)',
            'width': r'(?:width|B)\s*=\s*([\d.]+)',
            'slope': r'(?:slope|S0)\s*=\s*([\d.e-]+)',
            'roughness': r'(?:roughness|n)\s*=\s*([\d.]+)',
            'flow_rate': r'(?:flow_rate|Q)\s*=\s*([\d.]+)',
            'nx': r'(?:nx|n_cells)\s*=\s*(\d+)',
            'gate_opening': r'opening\s*=\s*([\d.]+)',
            'gate_position': r'position\s*=\s*([\d.]+)',
            'crest_height': r'crest_height\s*=\s*([\d.]+)',
        }
        
        for param, pattern in patterns.items():
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                try:
                    params[param] = float(match.group(1))
                except:
                    pass
        
        return params
    
    def _generate_index(self):
        """生成测试索引"""
        index = {
            "total": self.converted_count,
            "created": datetime.now().isoformat(),
            "description": "HydroClaude 完整测试案例索引 - 从348个后端案例转换",
            "categories": {},
            "cases": self.converted_cases
        }
        
        # 按分类统计
        for case in self.converted_cases:
            category = case['category']
            if category not in index['categories']:
                index['categories'][category] = {
                    'count': 0,
                    'description': self._get_category_description(category)
                }
            index['categories'][category]['count'] += 1
        
        # 保存索引
        index_file = self.test_cases_dir / "test_index_full.json"
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(index, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 索引已保存: {index_file}")
    
    def _get_category_description(self, category: str) -> str:
        """获取分类描述"""
        descriptions = {
            'basic_flow': '基础流动 - 均匀流、明渠流动基础',
            'structures': '水工结构 - 闸门、堰、泵站等',
            'network': '管网系统 - 复杂管网、树形/环形网络',
            'unsteady': '非稳态流 - 瞬态分析、水锤等',
            'optimization': '优化控制 - MPC、优化调度',
            'benchmark': '性能基准 - 算法性能测试',
            'other': '其他案例'
        }
        return descriptions.get(category, '其他')
    
    def _generate_summary(self):
        """生成转换总结"""
        print()
        print("="*70)
        print("📊 转换总结")
        print("="*70)
        print()
        print(f"扫描到的案例总数: {self.scan_data['total_cases']}")
        print(f"成功转换: {self.converted_count} 个")
        print(f"转换失败: {self.failed_count} 个")
        print(f"转换率: {self.converted_count / self.scan_data['total_cases'] * 100:.1f}%")
        print()
        
        # 按分类统计
        category_stats = {}
        for case in self.converted_cases:
            cat = case['category']
            category_stats[cat] = category_stats.get(cat, 0) + 1
        
        print("按分类统计:")
        for cat, count in sorted(category_stats.items(), key=lambda x: -x[1]):
            print(f"  {cat:20s}: {count:3d} 个")
        print()
        
        # 保存总结
        summary_file = self.root_dir / "conversion_summary.json"
        summary = {
            'timestamp': datetime.now().isoformat(),
            'total_scanned': self.scan_data['total_cases'],
            'converted': self.converted_count,
            'failed': self.failed_count,
            'conversion_rate': self.converted_count / self.scan_data['total_cases'] * 100,
            'by_category': category_stats
        }
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)


def main():
    """主函数"""
    converter = BatchTestCaseConverter()
    
    print("配置:")
    print("  - 每个分类最多转换: 20个案例")
    print("  - 优先转换: 基础流动、水工结构")
    print()
    
    # 执行转换
    converter.convert_all(max_per_category=20)
    
    print()
    print("="*70)
    print("✅ 批量转换完成")
    print("="*70)
    print()
    print("下一步:")
    print("  1. 查看转换结果: test_cases/")
    print("  2. 查看完整索引: test_cases/test_index_full.json")
    print("  3. 开始测试: python test_web_e2e.py --max-cases 20")


if __name__ == "__main__":
    main()
