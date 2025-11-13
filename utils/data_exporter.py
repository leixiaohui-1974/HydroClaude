#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据导出工具

支持将仿真结果导出为多种格式：
- CSV: 表格数据，易于在Excel中查看
- JSON: 结构化数据，易于程序读取
- NumPy: .npz格式，高性能数据存储
- HDF5: 大规模数据集存储（可选）

作者: Claude
日期: 2025-10-24
"""

import numpy as np
import json
import csv
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from datetime import datetime


class DataExporter:
    """
    数据导出工具类

    使用示例:
    ```python
    exporter = DataExporter(output_dir='results')

    # 导出时间序列数据
    exporter.export_time_series(
        time=t_history,
        data={'h': h_history, 'Q': Q_history},
        filename='simulation',
        formats=['csv', 'json', 'npz']
    )

    # 导出剖面数据
    exporter.export_profile(
        x=x_grid,
        data={'h': h_final, 'v': v_final},
        filename='profile',
        format='csv'
    )
    ```
    """

    def __init__(self, output_dir: str = 'results'):
        """
        初始化导出器

        Args:
            output_dir: 输出目录
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export_time_series(
        self,
        time: np.ndarray,
        data: Dict[str, np.ndarray],
        filename: str = 'time_series',
        formats: List[str] = ['csv'],
        metadata: Optional[Dict] = None
    ) -> Dict[str, str]:
        """
        导出时间序列数据

        Args:
            time: 时间数组 (n_steps,)
            data: 数据字典，键为变量名，值为数组 (n_steps, ...) 或 (n_steps,)
            filename: 文件名（不含扩展名）
            formats: 导出格式列表 ['csv', 'json', 'npz']
            metadata: 元数据（可选）

        Returns:
            导出文件路径字典 {format: file_path}
        """
        exported_files = {}

        if 'csv' in formats:
            file_path = self._export_time_series_csv(time, data, filename)
            exported_files['csv'] = file_path

        if 'json' in formats:
            file_path = self._export_time_series_json(time, data, filename, metadata)
            exported_files['json'] = file_path

        if 'npz' in formats:
            file_path = self._export_time_series_npz(time, data, filename, metadata)
            exported_files['npz'] = file_path

        return exported_files

    def _export_time_series_csv(
        self,
        time: np.ndarray,
        data: Dict[str, np.ndarray],
        filename: str
    ) -> str:
        """导出为CSV格式"""
        file_path = self.output_dir / f"{filename}.csv"

        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            # 处理多维数据
            headers = ['time']
            data_arrays = []

            for key, values in data.items():
                if values.ndim == 1:
                    # 一维数据
                    headers.append(key)
                    data_arrays.append(values)
                elif values.ndim == 2:
                    # 二维数据：为每一列创建一个header
                    n_cols = values.shape[1]
                    for i in range(n_cols):
                        headers.append(f"{key}_{i}")
                        data_arrays.append(values[:, i])
                else:
                    # 更高维数据：展平处理
                    flat = values.reshape(len(time), -1)
                    for i in range(flat.shape[1]):
                        headers.append(f"{key}_{i}")
                        data_arrays.append(flat[:, i])

            # 写入header
            writer.writerow(headers)

            # 写入数据
            for i in range(len(time)):
                row = [time[i]]
                for arr in data_arrays:
                    row.append(arr[i])
                writer.writerow(row)

        return str(file_path)

    def _export_time_series_json(
        self,
        time: np.ndarray,
        data: Dict[str, np.ndarray],
        filename: str,
        metadata: Optional[Dict] = None
    ) -> str:
        """导出为JSON格式"""
        file_path = self.output_dir / f"{filename}.json"

        # 构建JSON结构
        json_data = {
            'metadata': metadata or {},
            'time': time.tolist(),
            'data': {}
        }

        # 添加导出时间
        json_data['metadata']['export_time'] = datetime.now().isoformat()
        json_data['metadata']['n_steps'] = len(time)

        # 转换数据
        for key, values in data.items():
            json_data['data'][key] = values.tolist()

        # 写入文件
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)

        return str(file_path)

    def _export_time_series_npz(
        self,
        time: np.ndarray,
        data: Dict[str, np.ndarray],
        filename: str,
        metadata: Optional[Dict] = None
    ) -> str:
        """导出为NumPy .npz格式（压缩）"""
        file_path = self.output_dir / f"{filename}.npz"

        # 准备保存的数据
        save_dict = {'time': time}
        save_dict.update(data)

        # 添加元数据（转为JSON字符串）
        if metadata:
            save_dict['metadata_json'] = np.array([json.dumps(metadata)])

        # 保存（压缩格式）
        np.savez_compressed(file_path, **save_dict)

        return str(file_path)

    def export_profile(
        self,
        x: np.ndarray,
        data: Dict[str, np.ndarray],
        filename: str = 'profile',
        format: str = 'csv',
        metadata: Optional[Dict] = None
    ) -> str:
        """
        导出空间剖面数据

        Args:
            x: 空间坐标数组 (nx,)
            data: 数据字典，键为变量名，值为数组 (nx,)
            filename: 文件名（不含扩展名）
            format: 导出格式 'csv', 'json', 或 'npz'
            metadata: 元数据（可选）

        Returns:
            导出文件路径
        """
        if format == 'csv':
            return self._export_profile_csv(x, data, filename)
        elif format == 'json':
            return self._export_profile_json(x, data, filename, metadata)
        elif format == 'npz':
            return self._export_profile_npz(x, data, filename, metadata)
        else:
            raise ValueError(f"不支持的格式: {format}")

    def _export_profile_csv(
        self,
        x: np.ndarray,
        data: Dict[str, np.ndarray],
        filename: str
    ) -> str:
        """导出剖面为CSV格式"""
        file_path = self.output_dir / f"{filename}.csv"

        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            # Header
            headers = ['x'] + list(data.keys())
            writer.writerow(headers)

            # 数据行
            for i in range(len(x)):
                row = [x[i]]
                for key in data.keys():
                    row.append(data[key][i])
                writer.writerow(row)

        return str(file_path)

    def _export_profile_json(
        self,
        x: np.ndarray,
        data: Dict[str, np.ndarray],
        filename: str,
        metadata: Optional[Dict] = None
    ) -> str:
        """导出剖面为JSON格式"""
        file_path = self.output_dir / f"{filename}.json"

        json_data = {
            'metadata': metadata or {},
            'x': x.tolist(),
            'data': {key: values.tolist() for key, values in data.items()}
        }

        json_data['metadata']['export_time'] = datetime.now().isoformat()
        json_data['metadata']['nx'] = len(x)

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)

        return str(file_path)

    def _export_profile_npz(
        self,
        x: np.ndarray,
        data: Dict[str, np.ndarray],
        filename: str,
        metadata: Optional[Dict] = None
    ) -> str:
        """导出剖面为NumPy .npz格式"""
        file_path = self.output_dir / f"{filename}.npz"

        save_dict = {'x': x}
        save_dict.update(data)

        if metadata:
            save_dict['metadata_json'] = np.array([json.dumps(metadata)])

        np.savez_compressed(file_path, **save_dict)

        return str(file_path)

    def export_summary(
        self,
        summary_data: Dict[str, Any],
        filename: str = 'summary',
        format: str = 'json'
    ) -> str:
        """
        导出汇总信息

        Args:
            summary_data: 汇总数据字典
            filename: 文件名
            format: 格式 ('json' 或 'txt')

        Returns:
            导出文件路径
        """
        if format == 'json':
            file_path = self.output_dir / f"{filename}.json"

            # 添加导出时间
            summary_data['export_time'] = datetime.now().isoformat()

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(summary_data, f, indent=2, ensure_ascii=False)

        elif format == 'txt':
            file_path = self.output_dir / f"{filename}.txt"

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write("仿真结果汇总\n")
                f.write("=" * 80 + "\n\n")

                for key, value in summary_data.items():
                    f.write(f"{key}: {value}\n")

                f.write("\n" + "=" * 80 + "\n")
                f.write(f"导出时间: {datetime.now().isoformat()}\n")

        else:
            raise ValueError(f"不支持的格式: {format}")

        return str(file_path)

    @staticmethod
    def load_npz(file_path: str) -> Dict[str, np.ndarray]:
        """
        加载.npz文件

        Args:
            file_path: 文件路径

        Returns:
            数据字典
        """
        data = np.load(file_path, allow_pickle=True)

        result = {}
        for key in data.files:
            if key == 'metadata_json':
                # 解析元数据
                result['metadata'] = json.loads(str(data[key][0]))
            else:
                result[key] = data[key]

        return result

    @staticmethod
    def load_json(file_path: str) -> Dict:
        """
        加载JSON文件

        Args:
            file_path: 文件路径

        Returns:
            数据字典
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)


# 便捷函数
def quick_export_csv(output_file: str, **data_arrays):
    """
    快速导出数据到CSV

    示例:
    ```python
    quick_export_csv(
        'results/simulation.csv',
        time=t_array,
        depth=h_array,
        flow=Q_array
    )
    ```
    """
    exporter = DataExporter(output_dir=Path(output_file).parent)

    # 提取时间数组
    if 'time' in data_arrays:
        time = data_arrays.pop('time')
    elif 'x' in data_arrays:
        # 空间剖面
        x = data_arrays.pop('x')
        return exporter.export_profile(x, data_arrays, Path(output_file).stem, format='csv')
    else:
        raise ValueError("必须提供 'time' 或 'x' 数组")

    return exporter.export_time_series(time, data_arrays, Path(output_file).stem, formats=['csv'])


if __name__ == "__main__":
    # 测试示例
    print("数据导出工具测试")
    print()

    # 创建测试数据
    time = np.linspace(0, 100, 101)
    h = 2.0 + 0.5 * np.sin(2 * np.pi * time / 50)
    Q = 10.0 + 2.0 * np.cos(2 * np.pi * time / 50)

    # 创建导出器
    exporter = DataExporter(output_dir='test_export')

    # 导出时间序列
    print("导出时间序列数据...")
    files = exporter.export_time_series(
        time=time,
        data={'depth': h, 'flow': Q},
        filename='test_time_series',
        formats=['csv', 'json', 'npz'],
        metadata={'description': '测试数据', 'units': {'depth': 'm', 'flow': 'm³/s'}}
    )

    for fmt, path in files.items():
        print(f"   {fmt.upper()}: {path}")

    # 导出空间剖面
    print("\n导出空间剖面数据...")
    x = np.linspace(0, 1000, 101)
    h_profile = 3.0 - 0.001 * x
    v_profile = 1.0 + 0.0005 * x

    file = exporter.export_profile(
        x=x,
        data={'depth': h_profile, 'velocity': v_profile},
        filename='test_profile',
        format='csv'
    )
    print(f"   CSV: {file}")

    # 导出汇总
    print("\n导出汇总信息...")
    summary = {
        '仿真名称': '测试仿真',
        '时间步数': 101,
        '网格点数': 101,
        '最大水深': float(h.max()),
        '最小水深': float(h.min()),
        '平均流量': float(Q.mean())
    }

    file = exporter.export_summary(summary, filename='test_summary', format='json')
    print(f"   JSON: {file}")

    print("\n 测试完成！")
