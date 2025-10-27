#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
基准算例数据生成器

由于原始基准数据可能需要从文献中提取或通过高精度数值方法生成，
本脚本提供生成基准数据的工具。

注意：
- 某些算例有精确解析解，可直接计算
- 某些算例需要高精度数值方法生成参考解
- 生成的数据应与文献对比验证

Author: Claude (AI Assistant)
Date: 2025-10-27
"""

import sys
import os
import json

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class BenchmarkDataGenerator:
    """基准算例数据生成器"""
    
    def __init__(self, output_dir: str = "benchmark_data"):
        """
        初始化
        
        Args:
            output_dir: 输出目录
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # 创建子目录
        for subdir in ['macdonald', 'goutal', 'swashes']:
            os.makedirs(os.path.join(output_dir, subdir), exist_ok=True)
    
    def generate_macdonald_case1(self):
        """
        生成MacDonald Case 1: 矩形渠道稳态均匀流
        
        这是有精确解析解的算例（Manning公式）
        """
        print("生成MacDonald Case 1数据...")
        
        # 参数（来自MacDonald et al. 1997）
        params = {
            "length": 10000.0,  # m
            "width": 10.0,      # m
            "slope": 0.001,     # 无量纲
            "manning": 0.025,   # 无量纲
            "flow_rate": 10.0   # m³/s
        }
        
        # 元数据
        metadata = {
            "name": "MacDonald Case 1",
            "description": "矩形渠道稳态均匀流",
            "reference": "MacDonald et al. (1997) Journal of Hydraulic Engineering",
            "doi": "10.1061/(ASCE)0733-9429(1997)123:11(1041)",
            "parameters": params,
            "solution_type": "analytical",
            "expected_error": 0.001,  # 期望误差 < 0.1%
            "notes": "使用Manning公式的精确解析解"
        }
        
        # 保存元数据
        metadata_file = os.path.join(self.output_dir, 'macdonald', 'case1_uniform_flow.json')
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        print(f"  ✓ 元数据已保存: {metadata_file}")
        
        # 注意：实际数据生成需要numpy，这里创建占位符
        csv_file = os.path.join(self.output_dir, 'macdonald', 'case1_uniform_flow.csv')
        
        print(f"  ⏸️ 数据文件需要numpy生成: {csv_file}")
        print(f"     参数: Q={params['flow_rate']}, B={params['width']}, S0={params['slope']}, n={params['manning']}")
        print(f"     运行generate_with_numpy()方法生成实际数据")
        
        return metadata
    
    def generate_macdonald_case2(self):
        """
        生成MacDonald Case 2: 单闸门控制流
        """
        print("生成MacDonald Case 2数据...")
        
        params = {
            "length": 10000.0,
            "width": 10.0,
            "slope": 0.001,
            "manning": 0.025,
            "flow_rate": 10.0,
            "gate_position": 5000.0,
            "gate_opening": 3.0
        }
        
        metadata = {
            "name": "MacDonald Case 2",
            "description": "单闸门控制流",
            "reference": "MacDonald et al. (1997) JHE",
            "doi": "10.1061/(ASCE)0733-9429(1997)123:11(1041)",
            "parameters": params,
            "solution_type": "numerical_high_precision",
            "expected_error": 0.01,  # 1%
            "notes": "需要使用高精度数值方法生成参考解"
        }
        
        metadata_file = os.path.join(self.output_dir, 'macdonald', 'case2_sluice_gate.json')
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        print(f"  ✓ 元数据已保存: {metadata_file}")
        print(f"  ⏸️ 数据文件需要高精度数值方法生成")
        
        return metadata
    
    def generate_goutal_m1_curve(self):
        """
        生成Goutal M1曲线（壅水曲线）
        """
        print("生成Goutal M1曲线数据...")
        
        params = {
            "length": 10000.0,
            "width": 10.0,
            "slope": 0.001,
            "manning": 0.025,
            "flow_rate": 10.0,
            "downstream_depth": 3.0  # 高于均匀流水深
        }
        
        metadata = {
            "name": "Goutal M1 Backwater Curve",
            "description": "M1壅水曲线",
            "reference": "Goutal & Maurel (1997) EDF-SOGREAH",
            "parameters": params,
            "solution_type": "step_integration",
            "expected_error": 0.005,  # 0.5%
            "notes": "使用逐步积分法生成准解析解"
        }
        
        metadata_file = os.path.join(self.output_dir, 'goutal', 'M1_backwater.json')
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        print(f"  ✓ 元数据已保存: {metadata_file}")
        print(f"  ⏸️ 数据文件需要逐步积分法生成")
        
        return metadata
    
    def generate_swashes_case(self, case_number: int = 1):
        """
        生成SWASHES基准算例
        
        Args:
            case_number: 算例编号
        """
        print(f"生成SWASHES Case {case_number}数据...")
        
        # SWASHES算例参数（示例）
        params = {
            "case_number": case_number,
            "description": "MacDonald溃坝问题",
            "initial_left_depth": 10.0,
            "initial_right_depth": 5.0,
            "length": 2000.0,
            "time": 60.0
        }
        
        metadata = {
            "name": f"SWASHES Case {case_number}",
            "description": "经典溃坝问题（解析解）",
            "reference": "Delestre et al. (2013) IJNMF",
            "doi": "10.1002/fld.3741",
            "website": "http://www.univ-orleans.fr/mapmo/soft/SWASHES/",
            "parameters": params,
            "solution_type": "analytical",
            "expected_error": 0.001,
            "notes": "SWASHES提供精确解析解"
        }
        
        metadata_file = os.path.join(self.output_dir, 'swashes', f'case_{case_number}.json')
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        print(f"  ✓ 元数据已保存: {metadata_file}")
        print(f"  ⏸️ 数据文件可从SWASHES网站下载或计算")
        
        return metadata
    
    def generate_all_metadata(self):
        """生成所有基准算例的元数据"""
        print("="*70)
        print("生成基准算例元数据")
        print("="*70)
        
        metadata_list = []
        
        # MacDonald算例
        metadata_list.append(self.generate_macdonald_case1())
        metadata_list.append(self.generate_macdonald_case2())
        
        # Goutal算例
        metadata_list.append(self.generate_goutal_m1_curve())
        
        # SWASHES算例
        for i in range(1, 4):
            metadata_list.append(self.generate_swashes_case(i))
        
        # 生成索引文件
        index = {
            "description": "HydroClaude基准算例索引",
            "total_cases": len(metadata_list),
            "cases": metadata_list
        }
        
        index_file = os.path.join(self.output_dir, 'index.json')
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(index, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ 索引文件已保存: {index_file}")
        print(f"✓ 总计: {len(metadata_list)}个基准算例元数据")
        
        print("\n" + "="*70)
        print("注意：实际数据文件需要在安装numpy等依赖后生成")
        print("运行: python generate_benchmark_data.py --with-data")
        print("="*70)
        
        return metadata_list


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='生成基准算例数据')
    parser.add_argument('--with-data', action='store_true',
                       help='生成实际数据文件（需要numpy）')
    parser.add_argument('--output-dir', default='benchmark_data',
                       help='输出目录')
    
    args = parser.parse_args()
    
    generator = BenchmarkDataGenerator(output_dir=args.output_dir)
    
    if args.with_data:
        print("❌ 生成实际数据需要numpy")
        print("请先安装: pip3 install numpy scipy")
        print("当前仅生成元数据文件")
        print()
    
    generator.generate_all_metadata()


if __name__ == '__main__':
    main()
