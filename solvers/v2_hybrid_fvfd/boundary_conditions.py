#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
边界条件类

支持多种边界条件类型：
1. 恒定值（ConstantBC）
2. 时间序列（TimeSeriesBC）
3. 控制规则（ControlRuleBC）

用于非恒定流模拟。

Author: Claude (AI Assistant)
Date: 2025-10-27
"""

import numpy as np
from typing import Optional, Callable, Union
from abc import ABC, abstractmethod


class BoundaryCondition(ABC):
    """边界条件基类"""
    
    def __init__(self, bc_type: str):
        """
        初始化边界条件
        
        Args:
            bc_type: 边界条件类型 ('flow' 或 'depth')
        """
        if bc_type not in ['flow', 'depth']:
            raise ValueError(f"边界条件类型必须是'flow'或'depth'，得到：{bc_type}")
        
        self.bc_type = bc_type
    
    @abstractmethod
    def get_value(self, t: float) -> float:
        """
        获取时刻t的边界条件值
        
        Args:
            t: 时间 (s)
        
        Returns:
            value: 边界条件值
        """
        pass
    
    def __repr__(self):
        return f"{self.__class__.__name__}(type={self.bc_type})"


class ConstantBC(BoundaryCondition):
    """
    恒定边界条件
    
    最简单的边界条件，值不随时间变化。
    
    使用示例：
        >>> bc = ConstantBC(bc_type='flow', value=10.0)
        >>> Q = bc.get_value(t=100.0)  # 任何时刻都是10.0
    """
    
    def __init__(self, bc_type: str, value: float):
        """
        初始化恒定边界条件
        
        Args:
            bc_type: 'flow' 或 'depth'
            value: 恒定值（流量m³/s 或 水深m）
        """
        super().__init__(bc_type)
        self.value = value
    
    def get_value(self, t: float) -> float:
        """返回恒定值"""
        return self.value
    
    def __repr__(self):
        return f"ConstantBC(type={self.bc_type}, value={self.value})"


class TimeSeriesBC(BoundaryCondition):
    """
    时间序列边界条件
    
    从时间序列数据插值获取边界条件值。
    
    支持：
    - 线性插值
    - 外推处理（超出范围时使用边界值）
    
    使用示例：
        >>> times = [0, 3600, 7200]  # 0h, 1h, 2h
        >>> values = [10.0, 15.0, 12.0]
        >>> bc = TimeSeriesBC(bc_type='flow', times=times, values=values)
        >>> Q = bc.get_value(t=1800)  # 0.5h时的流量（插值）
    """
    
    def __init__(self, 
                 bc_type: str, 
                 times: np.ndarray, 
                 values: np.ndarray,
                 interpolation: str = 'linear'):
        """
        初始化时间序列边界条件
        
        Args:
            bc_type: 'flow' 或 'depth'
            times: 时间数组 (s)
            values: 对应的值数组
            interpolation: 插值方法（'linear'或'nearest'）
        """
        super().__init__(bc_type)
        
        self.times = np.asarray(times)
        self.values = np.asarray(values)
        
        if len(self.times) != len(self.values):
            raise ValueError("times和values长度必须相同")
        
        if len(self.times) < 2:
            raise ValueError("时间序列至少需要2个点")
        
        # 确保时间递增
        if not np.all(np.diff(self.times) > 0):
            raise ValueError("时间序列必须递增")
        
        self.interpolation = interpolation
    
    def get_value(self, t: float) -> float:
        """
        通过插值获取时刻t的值
        
        Args:
            t: 时间 (s)
        
        Returns:
            value: 插值后的边界条件值
        """
        # 超出范围：使用边界值（不外推）
        if t <= self.times[0]:
            return self.values[0]
        if t >= self.times[-1]:
            return self.values[-1]
        
        # 线性插值
        if self.interpolation == 'linear':
            return np.interp(t, self.times, self.values)
        
        # 最近邻插值
        elif self.interpolation == 'nearest':
            idx = np.argmin(np.abs(self.times - t))
            return self.values[idx]
        
        else:
            raise ValueError(f"不支持的插值方法: {self.interpolation}")
    
    @classmethod
    def from_csv(cls, bc_type: str, filename: str, 
                 time_col: str = 'time', 
                 value_col: str = 'value'):
        """
        从CSV文件加载时间序列
        
        Args:
            bc_type: 'flow' 或 'depth'
            filename: CSV文件路径
            time_col: 时间列名
            value_col: 数值列名
        
        Returns:
            bc: TimeSeriesBC实例
        """
        import pandas as pd
        
        df = pd.read_csv(filename)
        times = df[time_col].values
        values = df[value_col].values
        
        return cls(bc_type, times, values)
    
    def __repr__(self):
        return (f"TimeSeriesBC(type={self.bc_type}, "
                f"n_points={len(self.times)}, "
                f"t_range=[{self.times[0]:.1f}, {self.times[-1]:.1f}])")


class ControlRuleBC(BoundaryCondition):
    """
    控制规则边界条件
    
    根据系统状态动态计算边界条件。
    
    使用示例：
        >>> def control_func(t, system_state):
        ...     # 根据系统状态计算流量
        ...     if system_state['h_upstream'] > 3.0:
        ...         return 15.0  # 增加流量
        ...     else:
        ...         return 10.0  # 正常流量
        >>> 
        >>> bc = ControlRuleBC(bc_type='flow', rule=control_func)
        >>> Q = bc.get_value(t=100.0, system_state={'h_upstream': 3.5})
    """
    
    def __init__(self, bc_type: str, rule: Callable):
        """
        初始化控制规则边界条件
        
        Args:
            bc_type: 'flow' 或 'depth'
            rule: 控制规则函数
                  签名: rule(t: float, system_state: dict) -> float
        """
        super().__init__(bc_type)
        self.rule = rule
    
    def get_value(self, t: float, system_state: Optional[dict] = None) -> float:
        """
        根据控制规则计算边界条件值
        
        Args:
            t: 时间 (s)
            system_state: 系统状态字典（可选）
        
        Returns:
            value: 计算得到的边界条件值
        """
        if system_state is None:
            system_state = {}
        
        return self.rule(t, system_state)
    
    def __repr__(self):
        return f"ControlRuleBC(type={self.bc_type})"


class BoundaryManager:
    """
    边界条件管理器
    
    管理上游和下游边界条件。
    
    使用示例：
        >>> manager = BoundaryManager()
        >>> manager.set_upstream(ConstantBC('flow', 10.0))
        >>> manager.set_downstream(ConstantBC('depth', 2.0))
        >>> 
        >>> Q_upstream = manager.get_upstream_value(t=100.0)
        >>> h_downstream = manager.get_downstream_value(t=100.0)
    """
    
    def __init__(self):
        """初始化边界条件管理器"""
        self.upstream_bc: Optional[BoundaryCondition] = None
        self.downstream_bc: Optional[BoundaryCondition] = None
    
    def set_upstream(self, bc: BoundaryCondition):
        """设置上游边界条件"""
        self.upstream_bc = bc
    
    def set_downstream(self, bc: BoundaryCondition):
        """设置下游边界条件"""
        self.downstream_bc = bc
    
    def get_upstream_value(self, t: float, system_state: Optional[dict] = None) -> float:
        """
        获取上游边界条件值
        
        Args:
            t: 时间
            system_state: 系统状态（用于控制规则）
        
        Returns:
            value: 边界条件值
        """
        if self.upstream_bc is None:
            raise ValueError("上游边界条件未设置")
        
        if isinstance(self.upstream_bc, ControlRuleBC):
            return self.upstream_bc.get_value(t, system_state)
        else:
            return self.upstream_bc.get_value(t)
    
    def get_downstream_value(self, t: float, system_state: Optional[dict] = None) -> float:
        """
        获取下游边界条件值
        
        Args:
            t: 时间
            system_state: 系统状态（用于控制规则）
        
        Returns:
            value: 边界条件值
        """
        if self.downstream_bc is None:
            raise ValueError("下游边界条件未设置")
        
        if isinstance(self.downstream_bc, ControlRuleBC):
            return self.downstream_bc.get_value(t, system_state)
        else:
            return self.downstream_bc.get_value(t)
    
    def __repr__(self):
        return (f"BoundaryManager(\n"
                f"  upstream={self.upstream_bc},\n"
                f"  downstream={self.downstream_bc}\n"
                f")")


# ========== 测试代码 ==========

def test_boundary_conditions():
    """测试边界条件类"""
    print("\n" + "="*70)
    print("测试: 边界条件类")
    print("="*70)
    
    # 测试1: 恒定边界条件
    print("\n测试1: 恒定边界条件")
    print("-"*70)
    bc_const = ConstantBC(bc_type='flow', value=10.0)
    print(f"边界条件: {bc_const}")
    print(f"t=0s: {bc_const.get_value(0):.2f} m³/s")
    print(f"t=1000s: {bc_const.get_value(1000):.2f} m³/s")
    print(f"t=10000s: {bc_const.get_value(10000):.2f} m³/s")
    print("✓ 恒定值测试通过")
    
    # 测试2: 时间序列边界条件
    print("\n测试2: 时间序列边界条件")
    print("-"*70)
    times = np.array([0, 3600, 7200, 10800])  # 0h, 1h, 2h, 3h
    values = np.array([10.0, 15.0, 12.0, 10.0])
    bc_ts = TimeSeriesBC(bc_type='flow', times=times, values=values)
    print(f"边界条件: {bc_ts}")
    
    test_times = [0, 1800, 3600, 5400, 7200, 12000]
    print("时间序列插值:")
    for t in test_times:
        value = bc_ts.get_value(t)
        print(f"  t={t:5.0f}s ({t/3600:.2f}h): Q={value:.2f} m³/s")
    print("✓ 时间序列测试通过")
    
    # 测试3: 控制规则边界条件
    print("\n测试3: 控制规则边界条件")
    print("-"*70)
    
    def my_control_rule(t, system_state):
        """示例控制规则：根据上游水深调整流量"""
        h = system_state.get('h_upstream', 2.0)
        if h > 3.0:
            return 15.0  # 水位高，增加流量
        elif h < 1.5:
            return 5.0   # 水位低，减小流量
        else:
            return 10.0  # 正常流量
    
    bc_control = ControlRuleBC(bc_type='flow', rule=my_control_rule)
    print(f"边界条件: {bc_control}")
    
    test_states = [
        {'h_upstream': 1.0},
        {'h_upstream': 2.0},
        {'h_upstream': 3.5},
    ]
    print("控制规则响应:")
    for state in test_states:
        Q = bc_control.get_value(t=0, system_state=state)
        print(f"  h={state['h_upstream']:.1f}m → Q={Q:.1f} m³/s")
    print("✓ 控制规则测试通过")
    
    # 测试4: 边界条件管理器
    print("\n测试4: 边界条件管理器")
    print("-"*70)
    manager = BoundaryManager()
    manager.set_upstream(bc_const)
    manager.set_downstream(ConstantBC('depth', 2.0))
    print(f"管理器: {manager}")
    
    Q = manager.get_upstream_value(t=100)
    h = manager.get_downstream_value(t=100)
    print(f"上游流量: {Q:.2f} m³/s")
    print(f"下游水深: {h:.2f} m")
    print("✓ 管理器测试通过")
    
    print("\n" + "="*70)
    print("✓ 所有边界条件测试通过")
    print("="*70)


if __name__ == '__main__':
    test_boundary_conditions()
