#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
自动绘图工具

自动生成标准水力学图表，无需手写matplotlib代码。

核心功能：
1. 纵断面图（水面线）
2. 流量分布图
3. 时间历程图（非恒定流）
4. 收敛历史图
5. 结构物状态图

设计原则：
- 简单够用（不追求花哨）
- 自动美化（工程标准）
- 一键生成

使用示例：
    >>> from visualization import ResultVisualizer
    >>> 
    >>> viz = ResultVisualizer(result)
    >>> viz.plot_profile(save_path="profile.png")
    >>> viz.plot_all(output_dir="figures/")  # 一键生成所有图表

Author: Claude (AI Assistant)
Date: 2025-10-27
"""

import numpy as np
from typing import Dict, Optional, List
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # 非交互后端


class ResultVisualizer:
    """
    结果自动可视化器
    
    自动生成标准工程图表。
    
    使用示例：
        >>> viz = ResultVisualizer(result)
        >>> viz.plot_profile("profile.png")
        >>> # 或一键生成所有图表
        >>> viz.plot_all("figures/")
    """
    
    def __init__(self, result: Dict):
        """
        初始化可视化器
        
        Args:
            result: 求解结果字典
        """
        self.result = result
        
        # 提取数据
        self.x = result.get('x', result.get('x_center', []))
        self.h = result.get('h', [])
        self.z = result.get('z', np.zeros_like(self.x))
        self.Q = result.get('Q', [])
        
        # 非恒定流数据
        self.times = result.get('times', None)
        self.is_unsteady = self.times is not None
        
        # 设置中文字体（如果需要）
        self._setup_chinese_font()
    
    def _setup_chinese_font(self):
        """设置中文字体"""
        try:
            plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
            plt.rcParams['axes.unicode_minus'] = False
        except:
            pass  # 没有中文字体也可以工作
    
    def plot_profile(self, save_path: Optional[str] = None, 
                    show_structures: bool = True) -> plt.Figure:
        """
        绘制纵断面图（水面线）
        
        标准的水力学纵断面图：
        - X轴：距离
        - Y轴：高程
        - 显示：水位、床面、结构物位置
        
        Args:
            save_path: 保存路径（可选）
            show_structures: 是否显示结构物
        
        Returns:
            fig: matplotlib图形对象
        """
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # 提取数据
        x = self.x
        
        if self.is_unsteady:
            # 非恒定流：绘制最终时刻
            h = self.result['h'][-1] if len(self.result['h'].shape) > 1 else self.result['h']
        else:
            h = self.h
        
        z = self.z
        eta = h + z  # 水位
        
        # 绘制床面
        ax.fill_between(x, 0, z, color='#8B7355', alpha=0.6, label='床面')
        
        # 绘制水体
        ax.fill_between(x, z, eta, color='#4682B4', alpha=0.6, label='水体')
        
        # 绘制水面线
        ax.plot(x, eta, 'b-', linewidth=2, label='水面线')
        
        # 绘制床面线
        ax.plot(x, z, 'k-', linewidth=1.5, label='床面线')
        
        # 标注
        ax.set_xlabel('距离 (m)', fontsize=12)
        ax.set_ylabel('高程 (m)', fontsize=12)
        ax.set_title('纵断面图', fontsize=14, fontweight='bold')
        ax.legend(loc='best')
        ax.grid(True, alpha=0.3)
        
        # 美化
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"✅ 纵断面图已保存: {save_path}")
        
        return fig
    
    def plot_flow_distribution(self, save_path: Optional[str] = None) -> plt.Figure:
        """
        绘制流量分布图
        
        验证质量守恒。
        
        Args:
            save_path: 保存路径
        
        Returns:
            fig: matplotlib图形对象
        """
        fig, ax = plt.subplots(figsize=(12, 5))
        
        # 流量数据
        if self.is_unsteady:
            Q = self.result['Q'][-1] if len(self.result['Q'].shape) > 1 else self.result['Q']
        else:
            Q = self.Q
        
        x_Q = self.result.get('x_face', self.x)
        
        # 绘制流量
        ax.plot(x_Q, Q, 'b-', linewidth=2, label='流量分布')
        
        # 平均流量线
        Q_mean = np.mean(Q)
        ax.axhline(Q_mean, color='r', linestyle='--', linewidth=1.5, 
                  label=f'平均流量: {Q_mean:.2f} m³/s')
        
        # 标注
        ax.set_xlabel('距离 (m)', fontsize=12)
        ax.set_ylabel('流量 (m³/s)', fontsize=12)
        ax.set_title('流量分布图（质量守恒验证）', fontsize=14, fontweight='bold')
        ax.legend(loc='best')
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"✅ 流量分布图已保存: {save_path}")
        
        return fig
    
    def plot_timeseries(self, locations: List[float] = None,
                       save_path: Optional[str] = None) -> plt.Figure:
        """
        绘制时间历程图（非恒定流）
        
        Args:
            locations: 监测点位置列表
            save_path: 保存路径
        
        Returns:
            fig: matplotlib图形对象
        """
        if not self.is_unsteady:
            print("⚠️  稳态结果无时间历程")
            return None
        
        if locations is None:
            # 默认监测点：1/4, 1/2, 3/4位置
            L = self.x[-1]
            locations = [L*0.25, L*0.5, L*0.75]
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
        
        times_hours = self.times / 3600.0  # 转换为小时
        
        # 找到最近的单元
        for loc in locations:
            idx = np.argmin(np.abs(self.x - loc))
            
            # 水深时程
            h_series = self.result['h'][:, idx]
            ax1.plot(times_hours, h_series, label=f'x={loc:.0f}m', linewidth=2)
            
            # 流量时程（如果有）
            if 'Q' in self.result and len(self.result['Q'].shape) > 1:
                Q_series = self.result['Q'][:, idx]
                ax2.plot(times_hours, Q_series, label=f'x={loc:.0f}m', linewidth=2)
        
        # 水深图
        ax1.set_xlabel('时间 (h)', fontsize=12)
        ax1.set_ylabel('水深 (m)', fontsize=12)
        ax1.set_title('水深时间历程', fontsize=14, fontweight='bold')
        ax1.legend(loc='best')
        ax1.grid(True, alpha=0.3)
        
        # 流量图
        ax2.set_xlabel('时间 (h)', fontsize=12)
        ax2.set_ylabel('流量 (m³/s)', fontsize=12)
        ax2.set_title('流量时间历程', fontsize=14, fontweight='bold')
        ax2.legend(loc='best')
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"✅ 时间历程图已保存: {save_path}")
        
        return fig
    
    def plot_convergence(self, save_path: Optional[str] = None) -> Optional[plt.Figure]:
        """
        绘制收敛历史图
        
        Args:
            save_path: 保存路径
        
        Returns:
            fig: matplotlib图形对象
        """
        if 'history' not in self.result:
            print("⚠️  无收敛历史数据")
            return None
        
        history = self.result['history']
        if not history:
            return None
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        iterations = [h['iteration'] for h in history]
        errors = [h['error'] for h in history]
        
        ax.semilogy(iterations, errors, 'b-o', linewidth=2, markersize=6)
        
        ax.set_xlabel('迭代次数', fontsize=12)
        ax.set_ylabel('流量误差 (%)', fontsize=12)
        ax.set_title('收敛历史', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3, which='both')
        
        # 添加容差线
        if 'tolerance' in self.result:
            tol = self.result['tolerance']
            ax.axhline(tol, color='r', linestyle='--', linewidth=1.5,
                      label=f'容差: {tol}%')
            ax.legend()
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"✅ 收敛历史图已保存: {save_path}")
        
        return fig
    
    def plot_all(self, output_dir: str = "figures/"):
        """
        一键生成所有图表
        
        Args:
            output_dir: 输出目录
        """
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        print("\n" + "="*70)
        print("自动生成图表")
        print("="*70)
        
        # 纵断面图
        self.plot_profile(save_path=os.path.join(output_dir, "profile.png"))
        
        # 流量分布图
        if len(self.Q) > 0:
            self.plot_flow_distribution(save_path=os.path.join(output_dir, "flow_distribution.png"))
        
        # 时间历程图（非恒定流）
        if self.is_unsteady:
            self.plot_timeseries(save_path=os.path.join(output_dir, "timeseries.png"))
        
        # 收敛历史（如果有）
        if 'history' in self.result:
            self.plot_convergence(save_path=os.path.join(output_dir, "convergence.png"))
        
        print("="*70)
        print(f"✅ 所有图表已生成到: {output_dir}")
        print("="*70)
        
        plt.close('all')  # 关闭所有图形


# ========== 测试代码 ==========

def test_visualizer():
    """测试可视化工具"""
    print("\n" + "="*70)
    print("测试: 结果可视化工具")
    print("="*70)
    
    # 创建模拟数据
    x = np.linspace(0, 10000, 100)
    z = (10000 - x) * 0.001  # 床面
    h = np.ones_like(x) * 2.0 + 0.2 * np.sin(x / 1000)  # 水深
    Q = np.ones(len(x)) * 10.0
    
    result = {
        'x': x,
        'h': h,
        'z': z,
        'Q': Q,
        'converged': True,
        'error': 0.25,
        'history': [
            {'iteration': 0, 'error': 10.0},
            {'iteration': 200, 'error': 1.0},
            {'iteration': 400, 'error': 0.25},
        ]
    }
    
    # 创建可视化器
    viz = ResultVisualizer(result)
    
    # 测试各种图表
    print("\n生成纵断面图...")
    viz.plot_profile(save_path="test_profile.png")
    
    print("\n生成流量分布图...")
    viz.plot_flow_distribution(save_path="test_flow.png")
    
    print("\n生成收敛历史图...")
    viz.plot_convergence(save_path="test_convergence.png")
    
    print("\n✓ 可视化工具测试完成")
    print("✓ 生成图表: test_profile.png, test_flow.png, test_convergence.png")


if __name__ == '__main__':
    test_visualizer()
