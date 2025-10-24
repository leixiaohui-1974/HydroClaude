"""
数据导出器单元测试

测试utils/data_exporter.py的所有功能
"""

import pytest
import numpy as np
import json
import csv
from pathlib import Path

from utils.data_exporter import DataExporter, quick_export_csv


class TestDataExporter:
    """数据导出器测试类"""

    def test_initialization(self, temp_output_dir):
        """测试初始化"""
        exporter = DataExporter(output_dir=temp_output_dir)
        assert exporter.output_dir == Path(temp_output_dir)
        assert exporter.output_dir.exists()

    def test_export_time_series_csv(self, data_exporter, temp_output_dir):
        """测试时间序列CSV导出"""
        time = np.linspace(0, 100, 11)
        data = {'depth': np.ones(11) * 2.0, 'flow': np.ones(11) * 10.0}

        files = data_exporter.export_time_series(
            time=time,
            data=data,
            filename='test_series',
            formats=['csv']
        )

        # 验证文件存在
        assert 'csv' in files
        csv_file = Path(files['csv'])
        assert csv_file.exists()

        # 验证CSV内容
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 11
            assert 'time' in rows[0]
            assert 'depth' in rows[0]
            assert 'flow' in rows[0]

    def test_export_time_series_json(self, data_exporter):
        """测试时间序列JSON导出"""
        time = np.linspace(0, 50, 6)
        data = {'h': np.array([2.0, 2.1, 2.2, 2.1, 2.0, 1.9])}
        metadata = {'test': 'value', 'number': 42}

        files = data_exporter.export_time_series(
            time=time,
            data=data,
            filename='test_json',
            formats=['json'],
            metadata=metadata
        )

        # 验证文件存在
        json_file = Path(files['json'])
        assert json_file.exists()

        # 验证JSON内容
        with open(json_file, 'r') as f:
            content = json.load(f)
            assert 'metadata' in content
            assert content['metadata']['test'] == 'value'
            assert 'time' in content
            assert len(content['time']) == 6
            assert 'data' in content
            assert 'h' in content['data']

    def test_export_time_series_npz(self, data_exporter):
        """测试时间序列NPZ导出"""
        time = np.linspace(0, 100, 21)
        data = {
            'depth': np.random.randn(21) + 2.0,
            'velocity': np.random.randn(21) + 1.0
        }

        files = data_exporter.export_time_series(
            time=time,
            data=data,
            filename='test_npz',
            formats=['npz']
        )

        # 验证文件存在
        npz_file = Path(files['npz'])
        assert npz_file.exists()

        # 验证NPZ内容
        loaded = np.load(npz_file)
        assert 'time' in loaded
        assert 'depth' in loaded
        assert 'velocity' in loaded
        np.testing.assert_array_equal(loaded['time'], time)

    def test_export_profile_csv(self, data_exporter):
        """测试剖面CSV导出"""
        x = np.linspace(0, 1000, 51)
        data = {
            'depth': 3.0 - 0.001 * x,
            'velocity': 1.0 + 0.0005 * x
        }

        file_path = data_exporter.export_profile(
            x=x,
            data=data,
            filename='test_profile',
            format='csv'
        )

        # 验证文件
        assert Path(file_path).exists()

        # 验证内容
        with open(file_path, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 51
            assert 'x' in rows[0]
            assert 'depth' in rows[0]
            assert 'velocity' in rows[0]

    def test_export_profile_json(self, data_exporter):
        """测试剖面JSON导出"""
        x = np.linspace(0, 500, 26)
        data = {'h': 2.5 * np.ones(26)}

        file_path = data_exporter.export_profile(
            x=x,
            data=data,
            filename='test_profile_json',
            format='json',
            metadata={'canal': 'test'}
        )

        # 验证
        with open(file_path, 'r') as f:
            content = json.load(f)
            assert 'x' in content
            assert 'data' in content
            assert 'h' in content['data']
            assert content['metadata']['canal'] == 'test'

    def test_export_summary_json(self, data_exporter):
        """测试汇总JSON导出"""
        summary = {
            'simulation': 'test',
            'max_depth': 3.5,
            'min_depth': 1.2,
            'avg_flow': 12.5
        }

        file_path = data_exporter.export_summary(
            summary_data=summary,
            filename='test_summary',
            format='json'
        )

        # 验证
        with open(file_path, 'r') as f:
            content = json.load(f)
            assert content['simulation'] == 'test'
            assert content['max_depth'] == 3.5
            assert 'export_time' in content

    def test_export_summary_txt(self, data_exporter):
        """测试汇总TXT导出"""
        summary = {'test_key': 'test_value'}

        file_path = data_exporter.export_summary(
            summary_data=summary,
            filename='test_summary_txt',
            format='txt'
        )

        # 验证
        assert Path(file_path).exists()
        with open(file_path, 'r') as f:
            content = f.read()
            assert 'test_key' in content
            assert 'test_value' in content

    def test_load_npz(self, data_exporter):
        """测试NPZ文件加载"""
        # 先导出
        time = np.linspace(0, 10, 6)
        data = {'value': np.array([1, 2, 3, 4, 5, 6])}

        files = data_exporter.export_time_series(
            time=time,
            data=data,
            filename='test_load',
            formats=['npz']
        )

        # 再加载
        loaded = DataExporter.load_npz(files['npz'])
        assert 'time' in loaded
        assert 'value' in loaded
        np.testing.assert_array_equal(loaded['time'], time)
        np.testing.assert_array_equal(loaded['value'], data['value'])

    def test_load_json(self, data_exporter):
        """测试JSON文件加载"""
        # 先导出
        time = np.linspace(0, 5, 3)
        data = {'test': np.array([10, 20, 30])}

        files = data_exporter.export_time_series(
            time=time,
            data=data,
            filename='test_load_json',
            formats=['json']
        )

        # 再加载
        loaded = DataExporter.load_json(files['json'])
        assert 'time' in loaded
        assert 'data' in loaded
        assert 'test' in loaded['data']

    def test_quick_export_csv(self, temp_output_dir):
        """测试快速导出CSV便捷函数"""
        output_file = Path(temp_output_dir) / 'quick_export.csv'

        time = np.linspace(0, 20, 5)
        depth = np.array([2.0, 2.1, 2.2, 2.1, 2.0])

        quick_export_csv(
            str(output_file),
            time=time,
            depth=depth
        )

        # 验证
        assert output_file.exists()

    def test_export_multidimensional_data(self, data_exporter):
        """测试多维数据导出"""
        time = np.linspace(0, 10, 6)
        # 2D数据: (time_steps, space_points)
        h_field = np.random.randn(6, 10) + 2.0

        files = data_exporter.export_time_series(
            time=time,
            data={'h_field': h_field},
            filename='test_2d',
            formats=['csv', 'npz']
        )

        # CSV应该能处理
        assert Path(files['csv']).exists()

        # NPZ应该保持维度
        loaded = np.load(files['npz'])
        assert loaded['h_field'].shape == (6, 10)


@pytest.mark.parametrize("format", ['csv', 'json', 'npz'])
def test_all_formats(data_exporter, format):
    """参数化测试：所有格式"""
    time = np.linspace(0, 50, 11)
    data = {'value': np.ones(11)}

    files = data_exporter.export_time_series(
        time=time,
        data=data,
        filename=f'test_{format}',
        formats=[format]
    )

    assert format in files
    assert Path(files[format]).exists()
