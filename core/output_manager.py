#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
输出管理器 (Output Manager)

功能:
1. 标准化结果输出
2. 生成各种格式（JSON, CSV, HDF5）
3. 生成图表
4. 生成验证报告
5. 生成Web仪表板

Author: HydroClaude Development Team
Date: 2025-11-15
"""

import json
import os
import numpy as np
import pandas as pd
from typing import Dict, Any, List
import sys

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

try:
    import h5py
    HAS_HDF5 = True
except ImportError:
    HAS_HDF5 = False


class OutputManager:
    """
    输出管理器
    
    负责将标准化结果保存为各种格式，并生成可视化
    """
    
    def __init__(self, config: Dict[str, Any], results: Dict[str, Any], verbose: bool = False):
        """
        初始化输出管理器
        
        Args:
            config: 配置字典
            results: 标准化结果字典（通用数据模型）
            verbose: 是否输出详细信息
        """
        self.config = config
        self.results = results
        self.verbose = verbose
        
        # 输出目录
        self.output_dir = config['output']['directory']
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 子目录
        self.data_dir = os.path.join(self.output_dir, 'data')
        self.plots_dir = os.path.join(self.output_dir, 'plots')
        self.reports_dir = os.path.join(self.output_dir, 'reports')
        self.web_dir = os.path.join(self.output_dir, 'web')
        
        for d in [self.data_dir, self.plots_dir, self.reports_dir, self.web_dir]:
            os.makedirs(d, exist_ok=True)
    
    def save_all(self):
        """保存所有输出"""
        if self.verbose:
            print("\n" + "=" * 80)
            print("保存结果")
            print("=" * 80)
        
        # 1. 保存JSON
        if 'json' in self.config['output']['formats']:
            if self.verbose:
                print("\n1. 保存JSON...")
            self.save_json()
        
        # 2. 保存CSV
        if 'csv' in self.config['output']['formats']:
            if self.verbose:
                print("\n2. 保存CSV...")
            self.save_csv()
        
        # 3. 保存HDF5
        if 'hdf5' in self.config['output']['formats']:
            if self.verbose:
                print("\n3. 保存HDF5...")
            self.save_hdf5()
        
        # 4. 生成图表
        if self.config['output']['plots']['enabled']:
            if self.verbose:
                print("\n4. 生成图表...")
            self.generate_plots()
        
        # 5. 生成验证报告
        if self.verbose:
            print("\n5. 生成验证报告...")
        self.generate_validation_report()
        
        # 6. 生成Web仪表板
        if self.verbose:
            print("\n6. 生成Web仪表板...")
        self.generate_web_dashboard()
        
        # 7. 生成汇总文件
        if self.verbose:
            print("\n7. 生成文件清单...")
        self.generate_file_manifest()
        
        if self.verbose:
            print(f"\n✅ 所有输出已保存到: {self.output_dir}")
            print("=" * 80)
    
    def save_json(self):
        """保存JSON格式结果"""
        json_file = os.path.join(self.output_dir, 'results.json')
        
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        if self.verbose:
            print(f"  ✅ {json_file}")
    
    def save_csv(self):
        """保存CSV格式数据"""
        variables = self.results['variables']
        geometry = self.results['geometry']
        
        x = np.array(geometry['dimensions']['spatial']['values'])
        is_steady = self.results['simulation']['type'] == 'steady'
        
        if is_steady:
            # 稳态：空间剖面
            data = {'Distance_m': x}
            
            for var_name, var_data in variables.items():
                var_array = np.array(var_data['data'])
                if var_array.ndim == 2:
                    var_array = var_array[0, :]  # 取第一个（唯一）时间步
                data[f"{var_data['name']}_{var_data['unit']}"] = var_array
            
            df = pd.DataFrame(data)
            csv_file = os.path.join(self.data_dir, 'spatial_profile.csv')
            df.to_csv(csv_file, index=False, encoding='utf-8-sig')
            
            if self.verbose:
                print(f"  ✅ {csv_file}")
        
        else:
            # 非恒定流：时间序列 + 空间剖面
            t = np.array(geometry['dimensions']['temporal']['values'])
            
            # 1. 空间剖面（最后时刻）
            data = {'Distance_m': x}
            for var_name, var_data in variables.items():
                var_array = np.array(var_data['data'])
                data[f"{var_data['name']}_{var_data['unit']}"] = var_array[-1, :]
            
            df = pd.DataFrame(data)
            csv_file = os.path.join(self.data_dir, 'spatial_profile_final.csv')
            df.to_csv(csv_file, index=False, encoding='utf-8-sig')
            
            if self.verbose:
                print(f"  ✅ {csv_file}")
            
            # 2. 时间序列（几个关键位置）
            n_x = len(x)
            locations = [0, n_x // 2, n_x - 1]  # 上游、中游、下游
            location_names = ['Upstream', 'Middle', 'Downstream']
            
            data = {'Time_s': t}
            for i, (loc, name) in enumerate(zip(locations, location_names)):
                for var_name, var_data in variables.items():
                    var_array = np.array(var_data['data'])
                    data[f"{name}_{var_data['name']}_{var_data['unit']}"] = var_array[:, loc]
            
            df = pd.DataFrame(data)
            csv_file = os.path.join(self.data_dir, 'time_series.csv')
            df.to_csv(csv_file, index=False, encoding='utf-8-sig')
            
            if self.verbose:
                print(f"  ✅ {csv_file}")
    
    def save_hdf5(self):
        """保存HDF5格式数据"""
        if not HAS_HDF5:
            if self.verbose:
                print("  ⚠️  未安装h5py，跳过HDF5输出")
            return
        
        hdf5_file = os.path.join(self.data_dir, 'results.h5')
        
        with h5py.File(hdf5_file, 'w') as f:
            # 元数据
            meta = f.create_group('metadata')
            meta.attrs['title'] = self.results['metadata']['title']
            meta.attrs['simulation_type'] = self.results['simulation']['type']
            
            # 几何
            geom = f.create_group('geometry')
            geom.create_dataset('x', data=np.array(self.results['geometry']['dimensions']['spatial']['values']))
            
            if 'temporal' in self.results['geometry']['dimensions']:
                geom.create_dataset('t', data=np.array(self.results['geometry']['dimensions']['temporal']['values']))
            
            if 'bed_elevation' in self.results['geometry']['properties']:
                geom.create_dataset('bed_elevation', data=np.array(self.results['geometry']['properties']['bed_elevation']))
            
            # 变量
            vars_group = f.create_group('variables')
            for var_name, var_data in self.results['variables'].items():
                ds = vars_group.create_dataset(var_name, data=np.array(var_data['data']))
                ds.attrs['name'] = var_data['name']
                ds.attrs['unit'] = var_data['unit']
                ds.attrs['symbol'] = var_data['symbol']
        
        if self.verbose:
            print(f"  ✅ {hdf5_file}")
    
    def generate_plots(self):
        """生成图表"""
        if not HAS_MATPLOTLIB:
            if self.verbose:
                print("  ⚠️  未安装matplotlib，跳过图表生成")
            return
        
        plot_types = self.config['output']['plots'].get('types', ['profile'])
        
        if 'profile' in plot_types:
            self._plot_longitudinal_profile()
        
        if 'time_series' in plot_types:
            self._plot_time_series()
        
        if 'animation' in plot_types:
            if self.verbose:
                print("  ⚠️  动画生成功能开发中...")
    
    def _plot_longitudinal_profile(self):
        """绘制纵剖面图"""
        geometry = self.results['geometry']
        variables = self.results['variables']
        
        x = np.array(geometry['dimensions']['spatial']['values'])
        h = np.array(variables['depth']['data'])
        Q = np.array(variables['flow']['data'])
        
        # 取最后时刻（或唯一时刻）
        if h.ndim == 2:
            h = h[-1, :]
            Q = Q[-1, :]
        
        # 计算水面线
        if 'bed_elevation' in geometry['properties']:
            z_bed = np.array(geometry['properties']['bed_elevation'])
            z_surface = z_bed + h
        else:
            # 简单估算
            S0 = geometry['properties']['slope']
            length = geometry['properties']['length']
            z_bed = (length - x) * S0
            z_surface = z_bed + h
        
        fig, axes = plt.subplots(2, 1, figsize=(14, 10))
        
        # 子图1: 水面线
        ax1 = axes[0]
        ax1.fill_between(x, z_bed, z_surface, color='cyan', alpha=0.5, label='Water')
        ax1.plot(x, z_surface, 'b-', linewidth=2.5, label='Water Surface')
        ax1.plot(x, z_bed, 'k-', linewidth=2, label='Bed Level')
        ax1.set_xlabel('Distance (m)', fontsize=12)
        ax1.set_ylabel('Elevation (m)', fontsize=12)
        ax1.set_title(f'{self.results["metadata"]["title"]} - Longitudinal Profile', 
                      fontsize=14, fontweight='bold')
        ax1.grid(True, alpha=0.3)
        ax1.legend(fontsize=11)
        
        # 子图2: 流量分布
        ax2 = axes[1]
        Q_mean = np.mean(Q)
        Q_error_pct = np.abs(Q - Q_mean) / Q_mean * 100
        
        ax2.plot(x, Q, 'g-', linewidth=2.5, label='Flow Rate')
        ax2.axhline(y=Q_mean, color='k', linestyle=':', alpha=0.5, 
                   label=f'Average ({Q_mean:.2f} m³/s)')
        ax2.set_xlabel('Distance (m)', fontsize=12)
        ax2.set_ylabel('Flow Rate (m³/s)', fontsize=12)
        ax2.set_title(f'Flow Distribution (Max Error: {np.max(Q_error_pct):.6f}%)', 
                      fontsize=14, fontweight='bold')
        ax2.grid(True, alpha=0.3)
        ax2.legend(fontsize=11)
        
        plt.tight_layout()
        plot_file = os.path.join(self.plots_dir, 'longitudinal_profile.png')
        plt.savefig(plot_file, dpi=150, bbox_inches='tight')
        plt.close(fig)
        
        if self.verbose:
            print(f"  ✅ {plot_file}")
    
    def _plot_time_series(self):
        """绘制时间序列图"""
        if self.results['simulation']['type'] == 'steady':
            return
        
        geometry = self.results['geometry']
        variables = self.results['variables']
        
        t = np.array(geometry['dimensions']['temporal']['values'])
        x = np.array(geometry['dimensions']['spatial']['values'])
        h = np.array(variables['depth']['data'])
        Q = np.array(variables['flow']['data'])
        
        # 选择3个位置
        n_x = len(x)
        locations = [0, n_x // 2, n_x - 1]
        location_names = ['Upstream', 'Middle', 'Downstream']
        
        fig, axes = plt.subplots(2, 1, figsize=(14, 10))
        
        # 子图1: 水深演化
        ax1 = axes[0]
        for loc, name in zip(locations, location_names):
            ax1.plot(t, h[:, loc], linewidth=2, label=f'{name} (x={x[loc]:.0f}m)', alpha=0.8)
        ax1.set_xlabel('Time (s)', fontsize=12)
        ax1.set_ylabel('Water Depth (m)', fontsize=12)
        ax1.set_title('Water Depth Evolution', fontsize=14, fontweight='bold')
        ax1.grid(True, alpha=0.3)
        ax1.legend(fontsize=11)
        
        # 子图2: 流量演化
        ax2 = axes[1]
        for loc, name in zip(locations, location_names):
            ax2.plot(t, Q[:, loc], linewidth=2, label=f'{name} (x={x[loc]:.0f}m)', alpha=0.8)
        ax2.set_xlabel('Time (s)', fontsize=12)
        ax2.set_ylabel('Flow Rate (m³/s)', fontsize=12)
        ax2.set_title('Flow Rate Evolution', fontsize=14, fontweight='bold')
        ax2.grid(True, alpha=0.3)
        ax2.legend(fontsize=11)
        
        plt.tight_layout()
        plot_file = os.path.join(self.plots_dir, 'time_series.png')
        plt.savefig(plot_file, dpi=150, bbox_inches='tight')
        plt.close(fig)
        
        if self.verbose:
            print(f"  ✅ {plot_file}")
    
    def generate_validation_report(self):
        """生成验证报告"""
        report_file = os.path.join(self.reports_dir, 'validation_report.txt')
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("HydroClaude 验证报告\n")
            f.write("=" * 80 + "\n\n")
            
            # 基本信息
            f.write("【仿真信息】\n")
            f.write(f"标题: {self.results['metadata']['title']}\n")
            f.write(f"类型: {self.results['simulation']['type']}\n")
            f.write(f"状态: {self.results['simulation']['status']}\n")
            f.write(f"计算时间: {self.results['simulation']['duration_seconds']:.2f} 秒\n\n")
            
            # 收敛信息（稳态）
            if 'convergence' in self.results['simulation']:
                conv = self.results['simulation']['convergence']
                f.write("【收敛信息】\n")
                f.write(f"收敛: {'是' if conv['converged'] else '否'}\n")
                f.write(f"迭代次数: {conv['iterations']}\n")
                f.write(f"最终残差: {conv['final_residual']:.6f}\n\n")
            
            # 验证结果
            if 'validation' in self.results:
                val = self.results['validation']
                f.write("【验证结果】\n\n")
                
                if 'mass_conservation' in val:
                    mc = val['mass_conservation']
                    f.write("质量守恒:\n")
                    f.write(f"  绝对误差: {mc['error_absolute']:.6e}\n")
                    f.write(f"  相对误差: {mc['error_percent']:.6f}%\n")
                    f.write(f"  评级: {mc['grade']}\n\n")
                
                if 'overall_score' in val:
                    f.write(f"总体评分: {val['overall_score']:.1f}\n")
                    f.write(f"总体评级: {val['overall_grade']}\n\n")
            
            # 统计摘要
            f.write("【变量统计】\n\n")
            for var_name, var_data in self.results['variables'].items():
                if 'statistics' in var_data:
                    stats = var_data['statistics']
                    f.write(f"{var_data['name']} ({var_data['unit']}):\n")
                    f.write(f"  最小值: {stats['min']:.6f}\n")
                    f.write(f"  最大值: {stats['max']:.6f}\n")
                    f.write(f"  平均值: {stats['mean']:.6f}\n")
                    f.write(f"  标准差: {stats['std']:.6f}\n\n")
            
            f.write("=" * 80 + "\n")
            f.write("报告生成完成\n")
            f.write("=" * 80 + "\n")
        
        if self.verbose:
            print(f"  ✅ {report_file}")
    
    def generate_web_dashboard(self):
        """生成Web仪表板（简化版）"""
        # 保存一个简单的HTML文件，显示结果摘要
        html_file = os.path.join(self.web_dir, 'index.html')
        
        html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HydroClaude 结果查看器 - {self.results['metadata']['title']}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        .info-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }}
        .info-card {{
            background: #ecf0f1;
            padding: 20px;
            border-radius: 6px;
            border-left: 4px solid #3498db;
        }}
        .info-card h3 {{
            margin: 0 0 10px 0;
            color: #34495e;
            font-size: 14px;
            text-transform: uppercase;
        }}
        .info-card .value {{
            font-size: 24px;
            font-weight: bold;
            color: #2c3e50;
        }}
        .section {{
            margin: 30px 0;
        }}
        .section h2 {{
            color: #2c3e50;
            border-bottom: 2px solid #bdc3c7;
            padding-bottom: 8px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #3498db;
            color: white;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: bold;
        }}
        .badge-success {{ background-color: #27ae60; color: white; }}
        .badge-info {{ background-color: #3498db; color: white; }}
        .badge-warning {{ background-color: #f39c12; color: white; }}
        .img-container {{
            margin: 20px 0;
            text-align: center;
        }}
        .img-container img {{
            max-width: 100%;
            border: 1px solid #ddd;
            border-radius: 4px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🌊 HydroClaude 结果查看器</h1>
        
        <div class="info-grid">
            <div class="info-card">
                <h3>仿真标题</h3>
                <div class="value">{self.results['metadata']['title']}</div>
            </div>
            <div class="info-card">
                <h3>仿真类型</h3>
                <div class="value">{'稳态' if self.results['simulation']['type'] == 'steady' else '非恒定流'}</div>
            </div>
            <div class="info-card">
                <h3>计算时间</h3>
                <div class="value">{self.results['simulation']['duration_seconds']:.2f}s</div>
            </div>
            <div class="info-card">
                <h3>状态</h3>
                <div class="value">
                    <span class="badge badge-success">✅ {self.results['simulation']['status']}</span>
                </div>
            </div>
        </div>
"""
        
        # 添加收敛信息
        if 'convergence' in self.results['simulation']:
            conv = self.results['simulation']['convergence']
            html_content += f"""
        <div class="section">
            <h2>📊 收敛信息</h2>
            <table>
                <tr>
                    <th>项目</th>
                    <th>值</th>
                </tr>
                <tr>
                    <td>收敛状态</td>
                    <td><span class="badge badge-{'success' if conv['converged'] else 'warning'}">
                        {'✅ 已收敛' if conv['converged'] else '⚠️ 未收敛'}</span></td>
                </tr>
                <tr>
                    <td>迭代次数</td>
                    <td>{conv['iterations']}</td>
                </tr>
                <tr>
                    <td>最终残差</td>
                    <td>{conv['final_residual']:.6f}</td>
                </tr>
            </table>
        </div>
"""
        
        # 添加统计信息
        html_content += """
        <div class="section">
            <h2>📈 变量统计</h2>
            <table>
                <thead>
                    <tr>
                        <th>变量</th>
                        <th>最小值</th>
                        <th>最大值</th>
                        <th>平均值</th>
                        <th>标准差</th>
                    </tr>
                </thead>
                <tbody>
"""
        
        for var_name, var_data in self.results['variables'].items():
            if 'statistics' in var_data:
                stats = var_data['statistics']
                html_content += f"""
                    <tr>
                        <td>{var_data['name']} ({var_data['unit']})</td>
                        <td>{stats['min']:.6f}</td>
                        <td>{stats['max']:.6f}</td>
                        <td>{stats['mean']:.6f}</td>
                        <td>{stats['std']:.6f}</td>
                    </tr>
"""
        
        html_content += """
                </tbody>
            </table>
        </div>
"""
        
        # 添加图表（如果存在）
        if os.path.exists(os.path.join(self.plots_dir, 'longitudinal_profile.png')):
            html_content += """
        <div class="section">
            <h2>📉 纵剖面图</h2>
            <div class="img-container">
                <img src="../plots/longitudinal_profile.png" alt="Longitudinal Profile">
            </div>
        </div>
"""
        
        if os.path.exists(os.path.join(self.plots_dir, 'time_series.png')):
            html_content += """
        <div class="section">
            <h2>⏱️ 时间序列</h2>
            <div class="img-container">
                <img src="../plots/time_series.png" alt="Time Series">
            </div>
        </div>
"""
        
        # 添加文件下载链接
        html_content += """
        <div class="section">
            <h2>💾 下载数据</h2>
            <ul>
                <li><a href="../results.json" download>results.json</a> - 完整结果（JSON格式）</li>
                <li><a href="../data/spatial_profile.csv" download>spatial_profile.csv</a> - 空间剖面数据</li>
                <li><a href="../reports/validation_report.txt" download>validation_report.txt</a> - 验证报告</li>
            </ul>
        </div>
"""
        
        html_content += """
        <footer style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; text-align: center; color: #7f8c8d;">
            <p>Powered by <strong>HydroClaude</strong> v1.0.0</p>
            <p>Commercial-Grade Open Source Hydraulics Software</p>
        </footer>
    </div>
</body>
</html>
"""
        
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        if self.verbose:
            print(f"  ✅ {html_file}")
    
    def generate_file_manifest(self):
        """生成文件清单"""
        manifest_file = os.path.join(self.output_dir, 'FILES.txt')
        
        files = {
            '结果文件': [],
            '数据文件': [],
            '图表文件': [],
            '报告文件': [],
            'Web文件': []
        }
        
        # 扫描目录
        if os.path.exists(os.path.join(self.output_dir, 'results.json')):
            files['结果文件'].append('results.json')
        
        for f in os.listdir(self.data_dir):
            files['数据文件'].append(f'data/{f}')
        
        for f in os.listdir(self.plots_dir):
            files['图表文件'].append(f'plots/{f}')
        
        for f in os.listdir(self.reports_dir):
            files['报告文件'].append(f'reports/{f}')
        
        for f in os.listdir(self.web_dir):
            files['Web文件'].append(f'web/{f}')
        
        with open(manifest_file, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("HydroClaude 输出文件清单\n")
            f.write("=" * 80 + "\n\n")
            
            for category, file_list in files.items():
                if file_list:
                    f.write(f"【{category}】\n")
                    for file in file_list:
                        f.write(f"  - {file}\n")
                    f.write("\n")
            
            f.write("=" * 80 + "\n")
        
        if self.verbose:
            print(f"  ✅ {manifest_file}")


def main():
    """测试输出管理器"""
    import json
    import argparse
    
    parser = argparse.ArgumentParser(description='测试输出管理器')
    parser.add_argument('results', type=str, help='结果JSON文件路径')
    parser.add_argument('config', type=str, help='配置文件路径')
    parser.add_argument('-v', '--verbose', action='store_true', help='详细输出')
    
    args = parser.parse_args()
    
    # 读取结果
    with open(args.results, 'r', encoding='utf-8') as f:
        results = json.load(f)
    
    # 读取配置
    with open(args.config, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # 创建输出管理器
    output_manager = OutputManager(config, results, verbose=args.verbose)
    output_manager.save_all()


if __name__ == '__main__':
    main()
