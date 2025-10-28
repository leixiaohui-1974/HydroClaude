#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
水力计算工具库 - Phase 1工程实用工具

提供常用的水力计算功能：
1. Q-h关系曲线生成
2. Froude数计算和流态判别
3. 临界水深计算
4. 比能计算
5. 水跃参数计算
6. 渠道过流能力计算

基于Phase 0验证的稳定算法

作者: HydroClaude Team
日期: 2025-10-27
"""

import numpy as np
import matplotlib.pyplot as plt
from typing import Tuple, Optional, List
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.canal_utils import compute_steady_uniform_flow, compute_critical_depth, compute_froude_number


class HydraulicTools:
    """水力计算工具类"""
    
    def __init__(self, g: float = 9.81):
        """初始化"""
        self.g = g
    
    def generate_rating_curve(
        self,
        width: float,
        slope: float,
        manning_n: float,
        Q_range: Tuple[float, float] = (10.0, 150.0),
        n_points: int = 20
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        生成Q-h关系曲线（rating curve）
        
        Args:
            width: 渠道宽度(m)
            slope: 底坡
            manning_n: 曼宁系数
            Q_range: 流量范围(m³/s)
            n_points: 计算点数
            
        Returns:
            (Q_array, h_array): 流量和对应水深数组
        """
        Q_min, Q_max = Q_range
        Q_array = np.linspace(Q_min, Q_max, n_points)
        h_array = np.zeros(n_points)
        
        for i, Q in enumerate(Q_array):
            h_array[i] = compute_steady_uniform_flow(Q, width, slope, manning_n)
        
        return Q_array, h_array
    
    def compute_froude_curve(
        self,
        width: float,
        h_range: Tuple[float, float],
        Q: float,
        n_points: int = 50
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        计算不同水深下的Froude数
        
        Args:
            width: 渠道宽度(m)
            h_range: 水深范围(m)
            Q: 流量(m³/s)
            n_points: 计算点数
            
        Returns:
            (h_array, Fr_array): 水深和对应Froude数数组
        """
        h_min, h_max = h_range
        h_array = np.linspace(h_min, h_max, n_points)
        Fr_array = np.zeros(n_points)
        
        for i, h in enumerate(h_array):
            A = width * h
            v = Q / A
            Fr_array[i] = v / np.sqrt(self.g * h)
        
        return h_array, Fr_array
    
    def compute_specific_energy(
        self,
        width: float,
        Q: float,
        h_array: np.ndarray
    ) -> np.ndarray:
        """
        计算比能E = h + v²/(2g)
        
        Args:
            width: 渠道宽度(m)
            Q: 流量(m³/s)
            h_array: 水深数组(m)
            
        Returns:
            E_array: 比能数组(m)
        """
        E_array = np.zeros_like(h_array)
        
        for i, h in enumerate(h_array):
            A = width * h
            v = Q / A
            E_array[i] = h + v**2 / (2 * self.g)
        
        return E_array
    
    def compute_hydraulic_jump(
        self,
        width: float,
        h1: float,
        Q: float
    ) -> dict:
        """
        计算水跃参数
        
        Args:
            width: 渠道宽度(m)
            h1: 跃前水深(m)
            Q: 流量(m³/s)
            
        Returns:
            跃后参数字典
        """
        A1 = width * h1
        v1 = Q / A1
        Fr1 = v1 / np.sqrt(self.g * h1)
        
        # 跃后水深（矩形渠道）
        h2 = h1 / 2 * (-1 + np.sqrt(1 + 8 * Fr1**2))
        
        # 跃后流速
        A2 = width * h2
        v2 = Q / A2
        Fr2 = v2 / np.sqrt(self.g * h2)
        
        # 能量损失
        E1 = h1 + v1**2 / (2 * self.g)
        E2 = h2 + v2**2 / (2 * self.g)
        delta_E = E1 - E2
        
        # 水跃长度（经验公式）
        L_jump = 6.0 * (h2 - h1)
        
        return {
            'h1': h1,
            'h2': h2,
            'v1': v1,
            'v2': v2,
            'Fr1': Fr1,
            'Fr2': Fr2,
            'E1': E1,
            'E2': E2,
            'delta_E': delta_E,
            'L_jump': L_jump,
            'efficiency': (E2 / E1) * 100
        }
    
    def compute_channel_capacity(
        self,
        width: float,
        h_max: float,
        slope: float,
        manning_n: float
    ) -> dict:
        """
        计算渠道过流能力
        
        Args:
            width: 渠道宽度(m)
            h_max: 最大设计水深(m)
            slope: 底坡
            manning_n: 曼宁系数
            
        Returns:
            过流能力参数字典
        """
        # 最大流量（曼宁公式）
        A = width * h_max
        P = width + 2 * h_max
        R = A / P
        Q_max = (1.0 / manning_n) * A * R**(2/3) * np.sqrt(slope)
        
        # 平均流速
        v_max = Q_max / A
        
        # Froude数
        Fr = v_max / np.sqrt(self.g * h_max)
        
        # 流态判别
        if Fr < 1.0:
            flow_regime = "亚临界流"
        elif Fr > 1.0:
            flow_regime = "超临界流"
        else:
            flow_regime = "临界流"
        
        # 单宽流量
        q = Q_max / width
        
        return {
            'Q_max': Q_max,
            'v_max': v_max,
            'Fr': Fr,
            'flow_regime': flow_regime,
            'q': q,
            'A': A,
            'R': R
        }
    
    def plot_rating_curve(
        self,
        width: float,
        slope: float,
        manning_n: float,
        Q_range: Tuple[float, float] = (10.0, 150.0),
        save_path: Optional[str] = None
    ):
        """绘制Q-h关系曲线"""
        Q, h = self.generate_rating_curve(width, slope, manning_n, Q_range)
        
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(Q, h, 'b-', linewidth=2, marker='o', markersize=5)
        ax.set_xlabel('Discharge Q (m³/s)', fontsize=12)
        ax.set_ylabel('Depth h (m)', fontsize=12)
        ax.set_title('Rating Curve (Q-h Relationship)', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        
        # 添加注释
        textstr = f'Width: {width}m\nSlope: {slope}\nManning n: {manning_n}'
        ax.text(0.05, 0.95, textstr, transform=ax.transAxes, fontsize=10,
                verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"Rating curve saved: {save_path}")
        
        return fig, ax
    
    def plot_froude_analysis(
        self,
        width: float,
        Q: float,
        h_range: Tuple[float, float],
        save_path: Optional[str] = None
    ):
        """绘制Froude数分析图"""
        h, Fr = self.compute_froude_curve(width, h_range, Q)
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
        
        # Froude数曲线
        ax1.plot(h, Fr, 'b-', linewidth=2)
        ax1.axhline(y=1.0, color='r', linestyle='--', linewidth=2, label='临界流(Fr=1)')
        ax1.fill_between(h, 0, Fr, where=(Fr<1), alpha=0.3, color='blue', label='亚临界流')
        ax1.fill_between(h, Fr, 2, where=(Fr>1), alpha=0.3, color='red', label='超临界流')
        ax1.set_xlabel('Depth h (m)', fontsize=12)
        ax1.set_ylabel('Froude Number', fontsize=12)
        ax1.set_title('Froude Number vs Depth', fontsize=13, fontweight='bold')
        ax1.legend(fontsize=10)
        ax1.grid(True, alpha=0.3)
        ax1.set_ylim([0, 2])
        
        # 比能曲线
        E = self.compute_specific_energy(width, Q, h)
        h_c = compute_critical_depth(Q, width)
        E_min = 1.5 * h_c
        
        ax2.plot(E, h, 'b-', linewidth=2)
        ax2.axhline(y=h_c, color='r', linestyle='--', linewidth=2, label=f'临界水深({h_c:.2f}m)')
        ax2.axvline(x=E_min, color='g', linestyle='--', linewidth=2, label=f'最小比能({E_min:.2f}m)')
        ax2.set_xlabel('Specific Energy E (m)', fontsize=12)
        ax2.set_ylabel('Depth h (m)', fontsize=12)
        ax2.set_title('Specific Energy Curve', fontsize=13, fontweight='bold')
        ax2.legend(fontsize=10)
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"Froude analysis saved: {save_path}")
        
        return fig, (ax1, ax2)


# ========== 示例和测试 ==========

if __name__ == "__main__":
    print("="*80)
    print("🛠️ 水力计算工具库 - 示例")
    print("="*80)
    
    tools = HydraulicTools()
    
    # 示例1: Q-h关系曲线
    print("\n【示例1】Q-h关系曲线")
    print("-"*80)
    
    width = 10.0
    slope = 0.001
    manning_n = 0.025
    
    Q, h = tools.generate_rating_curve(width, slope, manning_n, Q_range=(20, 120), n_points=10)
    
    print(f"\n渠道参数:")
    print(f"  宽度: {width}m")
    print(f"  底坡: {slope}")
    print(f"  糙率: {manning_n}")
    
    print(f"\nQ-h关系:")
    print(f"{'Q(m³/s)':<12} {'h(m)':<10} {'v(m/s)':<10} {'Fr':<10}")
    print("-"*50)
    for i in range(len(Q)):
        v = Q[i] / (width * h[i])
        Fr = v / np.sqrt(9.81 * h[i])
        print(f"{Q[i]:<12.1f} {h[i]:<10.3f} {v:<10.3f} {Fr:<10.3f}")
    
    # 示例2: Froude数分析
    print(f"\n【示例2】Froude数和流态分析")
    print("-"*80)
    
    Q_test = 50.0
    h_test = 2.5
    
    A = width * h_test
    v = Q_test / A
    Fr = v / np.sqrt(9.81 * h_test)
    h_c = compute_critical_depth(Q_test, width)
    
    print(f"\n流况:")
    print(f"  流量: {Q_test}m³/s")
    print(f"  水深: {h_test}m")
    print(f"  流速: {v:.3f}m/s")
    print(f"  Froude数: {Fr:.3f}")
    print(f"  临界水深: {h_c:.3f}m")
    
    if Fr < 1.0:
        print(f"  流态: 亚临界流 ✅")
    elif Fr > 1.0:
        print(f"  流态: 超临界流 ⚠️")
    else:
        print(f"  流态: 临界流")
    
    # 示例3: 水跃计算
    print(f"\n【示例3】水跃参数计算")
    print("-"*80)
    
    h1_jump = 1.0  # 跃前水深
    Q_jump = 50.0
    
    jump_params = tools.compute_hydraulic_jump(width, h1_jump, Q_jump)
    
    print(f"\n跃前:")
    print(f"  水深: {jump_params['h1']:.3f}m")
    print(f"  流速: {jump_params['v1']:.3f}m/s")
    print(f"  Froude数: {jump_params['Fr1']:.3f}")
    
    print(f"\n跃后:")
    print(f"  水深: {jump_params['h2']:.3f}m")
    print(f"  流速: {jump_params['v2']:.3f}m/s")
    print(f"  Froude数: {jump_params['Fr2']:.3f}")
    
    print(f"\n水跃特性:")
    print(f"  能量损失: {jump_params['delta_E']:.3f}m")
    print(f"  水跃长度: {jump_params['L_jump']:.3f}m")
    print(f"  能量效率: {jump_params['efficiency']:.1f}%")
    
    # 示例4: 渠道过流能力
    print(f"\n【示例4】渠道过流能力")
    print("-"*80)
    
    h_max = 3.0
    
    capacity = tools.compute_channel_capacity(width, h_max, slope, manning_n)
    
    print(f"\n设计参数:")
    print(f"  最大水深: {h_max}m")
    
    print(f"\n过流能力:")
    print(f"  最大流量: {capacity['Q_max']:.2f}m³/s")
    print(f"  最大流速: {capacity['v_max']:.3f}m/s")
    print(f"  Froude数: {capacity['Fr']:.3f}")
    print(f"  流态: {capacity['flow_regime']}")
    print(f"  单宽流量: {capacity['q']:.3f}m²/s")
    
    # 生成图表
    print(f"\n生成可视化...")
    
    tools.plot_rating_curve(width, slope, manning_n, Q_range=(20, 120),
                           save_path='/workspace/hydraulic_rating_curve.png')
    
    tools.plot_froude_analysis(width, Q_test, h_range=(0.5, 4.0),
                              save_path='/workspace/hydraulic_froude_analysis.png')
    
    print(f"\n" + "="*80)
    print(f"✅ 水力计算工具库示例完成！")
    print(f"="*80)
