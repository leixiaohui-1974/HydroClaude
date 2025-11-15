#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Pump Station Module
泵站模块

对标商业软件（HEC-RAS、MIKE）的泵站功能

Author: HydroClaude Team
Date: 2025-11-15
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class PumpType(Enum):
    """泵站类型"""
    SINGLE = "single"      # 单泵
    PARALLEL = "parallel"  # 并联
    SERIES = "series"      # 串联


class ControlMode(Enum):
    """控制模式"""
    MANUAL = "manual"          # 手动
    AUTO_LEVEL = "auto_level"  # 自动水位控制
    AUTO_FLOW = "auto_flow"    # 自动流量控制
    SCHEDULE = "schedule"      # 时间表控制


@dataclass
class PumpCurve:
    """
    泵特性曲线
    
    Q-H关系：Q = a + b*H + c*H^2
    或者使用查表法
    """
    # 方法1：多项式系数
    coefficients: Optional[Tuple[float, float, float]] = None  # (a, b, c)
    
    # 方法2：数据点
    Q_data: Optional[List[float]] = None  # 流量数据点 (m³/s)
    H_data: Optional[List[float]] = None  # 扬程数据点 (m)
    
    # 效率曲线（可选）
    efficiency_data: Optional[List[float]] = None  # 效率 (0-1)
    
    # 运行范围
    Q_min: float = 0.0    # 最小流量 (m³/s)
    Q_max: float = 100.0  # 最大流量 (m³/s)
    H_min: float = 0.0    # 最小扬程 (m)
    H_max: float = 50.0   # 最大扬程 (m)


@dataclass
class PumpControlRule:
    """泵控制规则"""
    # 启动条件
    start_level: Optional[float] = None      # 启动水位 (m)
    start_flow: Optional[float] = None       # 启动流量 (m³/s)
    start_time: Optional[float] = None       # 启动时间 (s)
    
    # 停止条件
    stop_level: Optional[float] = None       # 停止水位 (m)
    stop_flow: Optional[float] = None        # 停止流量 (m³/s)
    stop_time: Optional[float] = None        # 停止时间 (s)
    
    # 控制参数
    hysteresis: float = 0.1   # 迟滞带 (m or m³/s)
    min_run_time: float = 60.0  # 最小运行时间 (s)
    min_off_time: float = 60.0  # 最小停机时间 (s)


class PumpStation:
    """
    泵站类
    
    功能：
    1. 单泵/多泵运行
    2. 泵特性曲线
    3. 自动控制
    4. 效率计算
    5. 启停记录
    
    参考商业软件：
    - HEC-RAS: Pump Station
    - MIKE: Pump Structure
    - InfoWorks: Pump
    """
    
    def __init__(
        self,
        name: str,
        position: float,
        pump_curve: PumpCurve,
        pump_type: PumpType = PumpType.SINGLE,
        num_pumps: int = 1,
        control_mode: ControlMode = ControlMode.MANUAL,
        control_rule: Optional[PumpControlRule] = None
    ):
        """
        初始化泵站
        
        Args:
            name: 泵站名称
            position: 位置 (m)
            pump_curve: 泵特性曲线
            pump_type: 泵站类型
            num_pumps: 泵数量
            control_mode: 控制模式
            control_rule: 控制规则
        """
        self.name = name
        self.position = position
        self.pump_curve = pump_curve
        self.pump_type = pump_type
        self.num_pumps = num_pumps
        self.control_mode = control_mode
        self.control_rule = control_rule or PumpControlRule()
        
        # 运行状态
        self.is_running = [False] * num_pumps
        self.current_flow = [0.0] * num_pumps
        self.current_head = [0.0] * num_pumps
        self.current_efficiency = [0.0] * num_pumps
        
        # 运行记录
        self.start_times = [0.0] * num_pumps
        self.stop_times = [0.0] * num_pumps
        self.total_run_time = [0.0] * num_pumps
        self.total_volume = [0.0] * num_pumps
        
        # 插值函数（如果使用数据点）
        if pump_curve.Q_data and pump_curve.H_data:
            self._build_interpolation()
    
    def _build_interpolation(self):
        """构建插值函数"""
        from scipy.interpolate import interp1d
        
        # Q-H插值
        self.Q_to_H = interp1d(
            self.pump_curve.Q_data,
            self.pump_curve.H_data,
            kind='cubic',
            fill_value='extrapolate'
        )
        
        # 如果有效率数据
        if self.pump_curve.efficiency_data:
            self.Q_to_eff = interp1d(
                self.pump_curve.Q_data,
                self.pump_curve.efficiency_data,
                kind='cubic',
                fill_value='extrapolate'
            )
    
    def compute_head(self, Q: float) -> float:
        """
        根据流量计算扬程
        
        Args:
            Q: 流量 (m³/s)
            
        Returns:
            扬程 (m)
        """
        # 检查范围
        Q = np.clip(Q, self.pump_curve.Q_min, self.pump_curve.Q_max)
        
        if self.pump_curve.coefficients:
            # 使用多项式
            a, b, c = self.pump_curve.coefficients
            H = a + b * Q + c * Q**2
        elif hasattr(self, 'Q_to_H'):
            # 使用插值
            H = float(self.Q_to_H(Q))
        else:
            # 默认线性关系
            H = self.pump_curve.H_max - (Q / self.pump_curve.Q_max) * (self.pump_curve.H_max - self.pump_curve.H_min)
        
        # 限制范围
        H = np.clip(H, self.pump_curve.H_min, self.pump_curve.H_max)
        
        return H
    
    def compute_flow(self, H: float) -> float:
        """
        根据扬程计算流量（反向计算）
        
        Args:
            H: 扬程 (m)
            
        Returns:
            流量 (m³/s)
        """
        if self.pump_curve.coefficients:
            # 求解二次方程 c*Q^2 + b*Q + (a-H) = 0
            a, b, c = self.pump_curve.coefficients
            if abs(c) < 1e-10:
                # 线性
                Q = (H - a) / b if abs(b) > 1e-10 else 0.0
            else:
                # 二次
                discriminant = b**2 - 4*c*(a-H)
                if discriminant >= 0:
                    Q = (-b + np.sqrt(discriminant)) / (2*c)
                else:
                    Q = 0.0
        elif hasattr(self, 'Q_to_H'):
            # 使用反向插值（数值求解）
            from scipy.optimize import fsolve
            Q = fsolve(lambda q: self.Q_to_H(q) - H, self.pump_curve.Q_max/2)[0]
        else:
            # 线性反算
            Q = (self.pump_curve.H_max - H) / (self.pump_curve.H_max - self.pump_curve.H_min) * self.pump_curve.Q_max
        
        # 限制范围
        Q = np.clip(Q, self.pump_curve.Q_min, self.pump_curve.Q_max)
        
        return Q
    
    def compute_efficiency(self, Q: float) -> float:
        """
        计算效率
        
        Args:
            Q: 流量 (m³/s)
            
        Returns:
            效率 (0-1)
        """
        if hasattr(self, 'Q_to_eff'):
            eff = float(self.Q_to_eff(Q))
        else:
            # 默认抛物线效率曲线，最高效率在额定流量附近
            Q_rated = (self.pump_curve.Q_min + self.pump_curve.Q_max) / 2
            # 效率在额定流量时为0.85，边界为0.6
            eff = 0.85 - 0.25 * ((Q - Q_rated) / (self.pump_curve.Q_max - Q_rated))**2
        
        return np.clip(eff, 0.0, 1.0)
    
    def update_control(
        self,
        current_time: float,
        water_level_upstream: float,
        water_level_downstream: float,
        flow_rate: float
    ):
        """
        更新控制状态
        
        Args:
            current_time: 当前时间 (s)
            water_level_upstream: 上游水位 (m)
            water_level_downstream: 下游水位 (m)
            flow_rate: 当前流量 (m³/s)
        """
        if self.control_mode == ControlMode.MANUAL:
            # 手动模式，不自动控制
            return
        
        rule = self.control_rule
        
        for i in range(self.num_pumps):
            # 检查是否正在运行
            if self.is_running[i]:
                # 检查停止条件
                should_stop = False
                
                # 运行时间检查
                run_time = current_time - self.start_times[i]
                if run_time < rule.min_run_time:
                    # 未达到最小运行时间
                    continue
                
                # 水位控制
                if self.control_mode == ControlMode.AUTO_LEVEL and rule.stop_level is not None:
                    if water_level_upstream <= rule.stop_level - rule.hysteresis:
                        should_stop = True
                
                # 流量控制
                if self.control_mode == ControlMode.AUTO_FLOW and rule.stop_flow is not None:
                    if flow_rate <= rule.stop_flow - rule.hysteresis:
                        should_stop = True
                
                if should_stop:
                    self.stop_pump(i, current_time)
            
            else:
                # 检查启动条件
                should_start = False
                
                # 停机时间检查
                if self.stop_times[i] > 0:
                    off_time = current_time - self.stop_times[i]
                    if off_time < rule.min_off_time:
                        # 未达到最小停机时间
                        continue
                
                # 水位控制
                if self.control_mode == ControlMode.AUTO_LEVEL and rule.start_level is not None:
                    if water_level_upstream >= rule.start_level + rule.hysteresis:
                        should_start = True
                
                # 流量控制
                if self.control_mode == ControlMode.AUTO_FLOW and rule.start_flow is not None:
                    if flow_rate >= rule.start_flow + rule.hysteresis:
                        should_start = True
                
                if should_start:
                    self.start_pump(i, current_time)
    
    def start_pump(self, pump_index: int, current_time: float):
        """启动泵"""
        if pump_index < self.num_pumps and not self.is_running[pump_index]:
            self.is_running[pump_index] = True
            self.start_times[pump_index] = current_time
            print(f"泵站 {self.name} 泵 #{pump_index+1} 启动 @ t={current_time:.1f}s")
    
    def stop_pump(self, pump_index: int, current_time: float):
        """停止泵"""
        if pump_index < self.num_pumps and self.is_running[pump_index]:
            self.is_running[pump_index] = False
            self.stop_times[pump_index] = current_time
            
            # 累计运行时间
            if self.start_times[pump_index] > 0:
                self.total_run_time[pump_index] += current_time - self.start_times[pump_index]
            
            print(f"泵站 {self.name} 泵 #{pump_index+1} 停止 @ t={current_time:.1f}s")
    
    def get_total_flow(self, head_difference: float) -> float:
        """
        获取总流量（所有运行中的泵）
        
        Args:
            head_difference: 水头差 (m)
            
        Returns:
            总流量 (m³/s)
        """
        total_Q = 0.0
        
        for i, running in enumerate(self.is_running):
            if running:
                # 根据水头差计算单泵流量
                Q = self.compute_flow(head_difference)
                
                # 并联：流量相加
                if self.pump_type == PumpType.PARALLEL:
                    total_Q += Q
                # 串联：流量相同，扬程相加（这里简化处理）
                elif self.pump_type == PumpType.SERIES:
                    total_Q = Q
                # 单泵
                else:
                    total_Q = Q
                    break
                
                # 记录单泵流量
                self.current_flow[i] = Q
                self.current_head[i] = self.compute_head(Q)
                self.current_efficiency[i] = self.compute_efficiency(Q)
        
        return total_Q
    
    def get_status(self) -> Dict:
        """获取运行状态"""
        return {
            'name': self.name,
            'position': self.position,
            'num_pumps': self.num_pumps,
            'running_pumps': sum(self.is_running),
            'is_running': self.is_running,
            'current_flow': self.current_flow,
            'current_head': self.current_head,
            'current_efficiency': self.current_efficiency,
            'total_run_time': self.total_run_time,
            'total_flow': sum(self.current_flow)
        }


# 预定义常用泵曲线
STANDARD_PUMP_CURVES = {
    'small': PumpCurve(
        coefficients=(10.0, -0.1, -0.001),
        Q_min=0.0, Q_max=5.0,
        H_min=0.0, H_max=10.0
    ),
    'medium': PumpCurve(
        coefficients=(25.0, -0.2, -0.002),
        Q_min=0.0, Q_max=10.0,
        H_min=0.0, H_max=25.0
    ),
    'large': PumpCurve(
        coefficients=(50.0, -0.3, -0.003),
        Q_min=0.0, Q_max=20.0,
        H_min=0.0, H_max=50.0
    )
}


# 使用示例
if __name__ == "__main__":
    # 创建泵站
    pump = PumpStation(
        name="PS-001",
        position=500.0,
        pump_curve=STANDARD_PUMP_CURVES['medium'],
        pump_type=PumpType.PARALLEL,
        num_pumps=2,
        control_mode=ControlMode.AUTO_LEVEL,
        control_rule=PumpControlRule(
            start_level=5.0,
            stop_level=3.0,
            hysteresis=0.2
        )
    )
    
    # 测试泵特性
    print("="*60)
    print("泵站特性测试")
    print("="*60)
    
    for Q in [0, 2, 5, 8, 10]:
        H = pump.compute_head(Q)
        eff = pump.compute_efficiency(Q)
        print(f"Q={Q:.1f} m³/s -> H={H:.2f} m, η={eff*100:.1f}%")
    
    print("\n" + "="*60)
    print("控制测试")
    print("="*60)
    
    # 模拟控制
    for t in [0, 10, 20, 100, 200]:
        water_level = 4.0 + 0.01 * t  # 水位上升
        pump.update_control(t, water_level, 2.0, 5.0)
        
        status = pump.get_status()
        print(f"t={t}s, WL={water_level:.2f}m, 运行泵数: {status['running_pumps']}")
    
    print("\n" + "="*60)
    print("最终状态")
    print("="*60)
    print(pump.get_status())
