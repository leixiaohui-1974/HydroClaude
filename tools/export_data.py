#!/usr/bin/env python3
"""
HydroClaude 数据导出工具

功能: 将模拟结果导出为多种格式
- CSV格式 (时间序列数据)
- JSON格式 (完整元数据)
- 支持自定义变量选择
- 支持空间分布导出

用法:
    python tools/export_data.py simulation_results.npz --format csv
    python tools/export_data.py simulation_results.npz --format json
    python tools/export_data.py simulation_results.npz --format all

作者: HydroClaude Team
日期: 2025-11-02
版本: v1.0
"""

import numpy as np
import json
import csv
from pathlib import Path
import argparse
from datetime import datetime, timedelta

class DataExporter:
    """数据导出器"""

    def __init__(self, data_file):
        """
        初始化导出器

        Parameters:
        -----------
        data_file : str
            NPZ数据文件路径
        """
        self.data_file = Path(data_file)
        self.data = None
        self.metadata = {}

    def load_data(self):
        """加载NPZ数据"""
        print(f"加载数据: {self.data_file}")
        self.data = np.load(self.data_file)

        # 提取时间信息
        if 'times' in self.data:
            self.times = self.data['times']
            print(f"  时间点数: {len(self.times)}")

        # 列出所有变量
        variables = [key for key in self.data.keys() if key != 'times']
        print(f"  变量数: {len(variables)}")
        print(f"  变量列表: {', '.join(variables)}")
        print()

        return self.data

    def export_csv(self, output_file=None, variables=None):
        """
        导出为CSV格式

        Parameters:
        -----------
        output_file : str, optional
            输出文件路径，默认自动生成
        variables : list, optional
            要导出的变量列表，默认全部
        """
        if self.data is None:
            self.load_data()

        if output_file is None:
            output_file = self.data_file.with_suffix('.csv')
        else:
            output_file = Path(output_file)

        print(f"导出CSV格式: {output_file}")

        # 选择变量
        if variables is None:
            variables = [key for key in self.data.keys() if key != 'times']

        # 准备数据
        times = self.data.get('times', np.arange(len(self.data[variables[0]])))

        # 写入CSV
        with open(output_file, 'w', newline='') as f:
            writer = csv.writer(f)

            # 写入表头
            header = ['Time (days)'] + variables
            writer.writerow(header)

            # 写入数据
            for i, t in enumerate(times):
                row = [f'{t:.4f}']
                for var in variables:
                    if var in self.data:
                        data = self.data[var]
                        # 检查数据是否为空或索引越界
                        if len(data) == 0:
                            row.append('N/A')
                        elif i >= len(data):
                            row.append('N/A')
                        elif len(data.shape) == 1:  # 时间序列
                            row.append(f'{data[i]:.6f}')
                        else:  # 空间分布，取平均
                            row.append(f'{data[i].mean():.6f}')
                    else:
                        row.append('N/A')
                writer.writerow(row)

        print(f" CSV导出完成: {len(times)} 行, {len(variables)} 个变量")
        print()

        return output_file

    def export_json(self, output_file=None, include_arrays=False):
        """
        导出为JSON格式

        Parameters:
        -----------
        output_file : str, optional
            输出文件路径
        include_arrays : bool
            是否包含完整数组数据（大文件警告）
        """
        if self.data is None:
            self.load_data()

        if output_file is None:
            output_file = self.data_file.with_suffix('.json')
        else:
            output_file = Path(output_file)

        print(f"导出JSON格式: {output_file}")

        # 准备JSON数据
        json_data = {
            'metadata': {
                'source_file': str(self.data_file),
                'export_time': datetime.now().isoformat(),
                'variables': list(self.data.keys()),
                'n_time_points': len(self.data.get('times', [])),
            },
            'summary': {}
        }

        # 添加统计摘要
        times = self.data.get('times', None)
        if times is not None:
            json_data['summary']['time_range'] = {
                'start': float(times[0]),
                'end': float(times[-1]),
                'duration_days': float(times[-1] - times[0])
            }

        # 各变量统计
        for var in self.data.keys():
            if var == 'times':
                continue

            data = self.data[var]

            # 检查空数组
            if len(data) == 0:
                json_data['summary'][var] = {
                    'note': 'Empty array',
                    'shape': list(data.shape)
                }
                continue

            json_data['summary'][var] = {
                'mean': float(data.mean()),
                'min': float(data.min()),
                'max': float(data.max()),
                'std': float(data.std()),
                'shape': list(data.shape)
            }

            # 初始和最终值
            if len(data.shape) == 1:
                json_data['summary'][var]['initial'] = float(data[0])
                json_data['summary'][var]['final'] = float(data[-1])
            else:
                json_data['summary'][var]['initial'] = float(data[0].mean())
                json_data['summary'][var]['final'] = float(data[-1].mean())

        # 可选：包含完整数组
        if include_arrays:
            json_data['data'] = {}
            for var in self.data.keys():
                data = self.data[var]
                if len(data.shape) == 1:
                    json_data['data'][var] = data.tolist()
                else:
                    # 空间分布数据，取平均
                    json_data['data'][var] = data.mean(axis=1).tolist()
            print("  (包含完整数组数据)")

        # 写入JSON
        with open(output_file, 'w') as f:
            json.dump(json_data, f, indent=2)

        print(f" JSON导出完成")
        print()

        return output_file

    def export_spatial_csv(self, output_dir=None, time_index=-1):
        """
        导出空间分布数据为CSV

        Parameters:
        -----------
        output_dir : str, optional
            输出目录
        time_index : int
            时间索引，默认-1（最后时刻）
        """
        if self.data is None:
            self.load_data()

        if output_dir is None:
            output_dir = self.data_file.parent / 'spatial_output'
        else:
            output_dir = Path(output_dir)

        output_dir.mkdir(exist_ok=True)

        times = self.data.get('times', np.arange(100))
        time_value = times[time_index]

        print(f"导出空间分布数据: t = {time_value:.2f} days")
        print(f"输出目录: {output_dir}")

        # 对每个空间变量导出
        exported = []
        for var in self.data.keys():
            if var == 'times':
                continue

            data = self.data[var]
            if len(data.shape) <= 1:
                continue  # 跳过时间序列

            # 提取空间分布
            spatial_data = data[time_index, :]

            # 写入CSV
            output_file = output_dir / f'{var}_spatial_t{time_index:04d}.csv'
            with open(output_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Cell_Index', var])
                for i, value in enumerate(spatial_data):
                    writer.writerow([i, f'{value:.6f}'])

            exported.append(var)

        print(f" 导出了 {len(exported)} 个空间变量")
        print(f"  变量: {', '.join(exported)}")
        print()

        return output_dir


def main():
    """命令行接口"""
    parser = argparse.ArgumentParser(description='Export HydroClaude simulation results')
    parser.add_argument('input', type=str, help='Input NPZ file')
    parser.add_argument('--format', type=str, default='csv',
                       choices=['csv', 'json', 'spatial', 'all'],
                       help='Export format')
    parser.add_argument('--output', type=str, default=None,
                       help='Output file path')
    parser.add_argument('--variables', type=str, nargs='+', default=None,
                       help='Variables to export (default: all)')
    parser.add_argument('--include-arrays', action='store_true',
                       help='Include full arrays in JSON')
    parser.add_argument('--time-index', type=int, default=-1,
                       help='Time index for spatial export (default: -1, last)')

    args = parser.parse_args()

    print("=" * 70)
    print("HydroClaude 数据导出工具")
    print("=" * 70)
    print()

    # 创建导出器
    exporter = DataExporter(args.input)

    # 加载数据
    exporter.load_data()

    # 执行导出
    if args.format == 'csv' or args.format == 'all':
        exporter.export_csv(args.output, args.variables)

    if args.format == 'json' or args.format == 'all':
        exporter.export_json(args.output, args.include_arrays)

    if args.format == 'spatial' or args.format == 'all':
        exporter.export_spatial_csv(time_index=args.time_index)

    print("=" * 70)
    print("导出完成!")
    print("=" * 70)


if __name__ == '__main__':
    main()
