#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
动态边界条件工具

解决Phase 1问题：快速变化的边界条件导致NaN

核心功能：
1. 流量限速器（RateLimitedBC）
2. 边界条件兼容性检查
3. 渐变初始化

作者: HydroClaude Team
日期: 2025-10-27
"""

import numpy as np
from typing import Dict, Optional
import warnings
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class RateLimitedBC:
    """
    流量限速器
    
    限制边界条件的变化率，避免突变导致数值不稳定
    
    使用方法:
    ```python
    bc = RateLimitedBC(max_rate=10.0)  # 最大10 m³/s per second
    
    for t in time_steps:
        Q_target = get_target_flow(t)
        Q_actual = bc.update(Q_target, dt)
        solver.bc_left = {'type': 'Q', 'value': Q_actual}
    ```
    """
    
    def __init__(self, max_rate: float):
        """
        初始化流量限速器
        
        Args:
            max_rate: 最大变化率 (单位/秒)，如10 m³/s per second
        """
        self.max_rate = max_rate
        self.current_value = None
        self.initialized = False
        
        print(f" 流量限速器初始化: 最大变化率={max_rate} 单位/s")
    
    def update(self, target_value: float, dt: float) -> float:
        """
        更新边界条件，限制变化率
        
        Args:
            target_value: 目标值
            dt: 时间步长(s)
        
        Returns:
            实际值（限速后）
        """
        if not self.initialized or self.current_value is None:
            self.current_value = target_value
            self.initialized = True
            return target_value
        
        # 计算变化量
        delta = target_value - self.current_value
        
        # 限制变化率
        max_delta = self.max_rate * dt
        if abs(delta) > max_delta:
            delta = np.sign(delta) * max_delta
        
        # 更新当前值
        self.current_value += delta
        
        return self.current_value
    
    def reset(self, value: float):
        """重置到指定值"""
        self.current_value = value
        self.initialized = True
    
    def get_current(self) -> Optional[float]:
        """获取当前值"""
        return self.current_value


def check_bc_compatibility(
    bc_left: Dict,
    bc_right: Dict,
    width: float,
    slope: float,
    manning_n: float,
    g: float = 9.81
) -> Dict:
    """
    检查左右边界条件的兼容性
    
    对于稳态流，Q和h必须满足曼宁公式关系
    
    Args:
        bc_left: 左边界条件 {'type': 'Q'/'h', 'value': float}
        bc_right: 右边界条件 {'type': 'Q'/'h', 'value': float}
        width: 渠道宽度(m)
        slope: 底坡
        manning_n: 曼宁系数
        g: 重力加速度
    
    Returns:
        {
            'compatible': bool,
            'error': float,  # 相对误差%
            'message': str
        }
    """
    from utils.canal_utils import compute_steady_uniform_flow
    
    result = {
        'compatible': True,
        'error': 0.0,
        'message': 'OK'
    }
    
    # 情况1: 左边Q，右边h
    if bc_left['type'] == 'Q' and bc_right['type'] == 'h':
        Q = bc_left['value']
        h_boundary = bc_right['value']
        
        # 计算Q对应的均匀流水深
        h_required = compute_steady_uniform_flow(Q, width, slope, manning_n)
        
        # 检查兼容性
        error = abs(h_required - h_boundary) / h_required * 100
        
        if error > 10:  # 10%容差
            result['compatible'] = False
            result['error'] = error
            result['message'] = (
                f"边界不兼容: Q={Q:.1f} m³/s 需要 h={h_required:.2f}m, "
                f"但右边界h={h_boundary:.2f}m, 误差={error:.1f}%"
            )
            warnings.warn(result['message'])
        else:
            result['error'] = error
            result['message'] = f"边界基本兼容, 误差={error:.1f}%"
    
    # 情况2: 左边h，右边Q
    elif bc_left['type'] == 'h' and bc_right['type'] == 'Q':
        h_boundary = bc_left['value']
        Q = bc_right['value']
        
        h_required = compute_steady_uniform_flow(Q, width, slope, manning_n)
        error = abs(h_required - h_boundary) / h_required * 100
        
        if error > 10:
            result['compatible'] = False
            result['error'] = error
            result['message'] = (
                f"边界不兼容: Q={Q:.1f} m³/s 需要 h={h_required:.2f}m, "
                f"但左边界h={h_boundary:.2f}m, 误差={error:.1f}%"
            )
            warnings.warn(result['message'])
        else:
            result['error'] = error
            result['message'] = f"边界基本兼容, 误差={error:.1f}%"
    
    return result


def create_flood_hydrograph(
    Q_base: float,
    Q_peak: float,
    t_rise: float,
    t_total: float,
    dt: float = 1.0,
    shape: str = 'triangular'
) -> np.ndarray:
    """
    创建洪水过程线
    
    Args:
        Q_base: 基流(m³/s)
        Q_peak: 峰值流量(m³/s)
        t_rise: 上升时间(s)
        t_total: 总时间(s)
        dt: 时间步长(s)
        shape: 形状 ('triangular', 'trapezoidal')
    
    Returns:
        Q(t): 流量时间序列
    """
    t = np.arange(0, t_total, dt)
    Q = np.zeros_like(t)
    
    if shape == 'triangular':
        # 三角形: 线性上升，线性下降
        for i, ti in enumerate(t):
            if ti < t_rise:
                Q[i] = Q_base + (Q_peak - Q_base) * (ti / t_rise)
            else:
                t_fall = t_total - t_rise
                Q[i] = Q_peak - (Q_peak - Q_base) * ((ti - t_rise) / t_fall)
                Q[i] = max(Q[i], Q_base)
    
    elif shape == 'trapezoidal':
        # 梯形: 上升-平台-下降
        t_platform = 0.2 * t_total  # 平台期
        t_fall = t_total - t_rise - t_platform
        
        for i, ti in enumerate(t):
            if ti < t_rise:
                # 上升段
                Q[i] = Q_base + (Q_peak - Q_base) * (ti / t_rise)
            elif ti < t_rise + t_platform:
                # 平台段
                Q[i] = Q_peak
            else:
                # 下降段
                Q[i] = Q_peak - (Q_peak - Q_base) * ((ti - t_rise - t_platform) / t_fall)
                Q[i] = max(Q[i], Q_base)
    
    return Q


if __name__ == '__main__':
    print("=" * 80)
    print("动态边界条件工具测试")
    print("=" * 80)
    
    # 测试1: 流量限速器
    print("\n【测试1】流量限速器")
    print("-" * 80)
    
    bc = RateLimitedBC(max_rate=10.0)
    
    # 模拟突变：50 → 100 m³/s
    dt = 1.0
    target_values = [50, 100, 100, 100, 50]
    
    print("\n模拟流量突变（50 → 100 → 50）:")
    print(f"{'时间(s)':<10} {'目标值':<10} {'实际值':<10} {'变化率':<10}")
    print("-" * 50)
    
    prev = 50.0
    for i, target in enumerate(target_values):
        t = i * dt
        actual = bc.update(target, dt)
        rate = (actual - prev) / dt
        print(f"{t:<10.1f} {target:<10.1f} {actual:<10.2f} {rate:<10.2f}")
        prev = actual
    
    # 测试2: 边界兼容性
    print("\n\n【测试2】边界条件兼容性")
    print("-" * 80)
    
    bc_left = {'type': 'Q', 'value': 50.0}
    bc_right = {'type': 'h', 'value': 2.5}
    
    result = check_bc_compatibility(
        bc_left, bc_right,
        width=10.0, slope=0.001, manning_n=0.025
    )
    
    print(f"\n边界条件:")
    print(f"  左: Q = {bc_left['value']} m³/s")
    print(f"  右: h = {bc_right['value']} m")
    print(f"\n兼容性检查:")
    print(f"  兼容: {' 是' if result['compatible'] else ' 否'}")
    print(f"  误差: {result['error']:.2f}%")
    print(f"  消息: {result['message']}")
    
    # 测试3: 洪水过程线
    print("\n\n【测试3】洪水过程线生成")
    print("-" * 80)
    
    Q = create_flood_hydrograph(
        Q_base=30.0,
        Q_peak=100.0,
        t_rise=3600.0,  # 1小时上升
        t_total=10800.0,  # 3小时总时长
        dt=600.0,  # 10分钟间隔
        shape='triangular'
    )
    
    print(f"\n三角形洪水过程线:")
    print(f"  基流: 30 m³/s")
    print(f"  峰值: 100 m³/s")
    print(f"  上升时间: 1小时")
    print(f"  总时长: 3小时")
    print(f"\n前10个时刻:")
    for i in range(min(10, len(Q))):
        t_min = i * 10
        print(f"  t={t_min:4d}min: Q={Q[i]:6.2f} m³/s")
    
    print("\n" + "=" * 80)
    print(" 动态边界条件工具测试完成")
    print("=" * 80)
