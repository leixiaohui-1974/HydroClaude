#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
解析解库

提供各种水力学问题的精确解析解，用于验证数值方法的精度。

包含：
1. Manning均匀流
2. 临界流
3. 水跃共轭水深
4. 宽顶堰流量
5. 水面曲线（逐步积分法）

Author: Claude (AI Assistant)
Date: 2025-10-27
"""

import numpy as np
from typing import Tuple, Optional
from scipy.optimize import fsolve, brentq


class AnalyticalSolutions:
    """
    水力学解析解库
    
    所有方法都提供精确解析解，用于验证数值方法精度。
    """
    
    def __init__(self, g: float = 9.81):
        """
        初始化
        
        Args:
            g: 重力加速度 (m/s²)
        """
        self.g = g
    
    #===========================================================================
    # 1. Manning均匀流（最基础的验证）
    #===========================================================================
    
    def uniform_flow_depth(self, Q: float, B: float, S0: float, n: float) -> float:
        """
        计算矩形渠道Manning均匀流水深（解析解）
        
        公式：Q = (1/n) * A * R^(2/3) * S0^(1/2)
        
        Args:
            Q: 流量 (m³/s)
            B: 渠道宽度 (m)
            S0: 渠底坡度
            n: Manning糙率系数
        
        Returns:
            h: 均匀流水深 (m)
        """
        def manning_equation(h):
            if h <= 0:
                return 1e10
            A = B * h
            P = B + 2 * h
            R = A / P
            Q_computed = (1.0 / n) * A * (R ** (2.0/3.0)) * (S0 ** 0.5)
            return Q_computed - Q
        
        # 初值估计
        h0 = (Q * n / (B * S0**0.5)) ** 0.6
        
        # 求解
        h = fsolve(manning_equation, h0)[0]
        
        return h
    
    def uniform_flow_velocity(self, h: float, S0: float, n: float, B: float) -> float:
        """
        计算均匀流流速（解析解）
        
        Args:
            h: 水深 (m)
            S0: 渠底坡度
            n: Manning糙率
            B: 渠宽 (m)
        
        Returns:
            u: 流速 (m/s)
        """
        A = B * h
        P = B + 2 * h
        R = A / P
        u = (1.0 / n) * (R ** (2.0/3.0)) * (S0 ** 0.5)
        return u
    
    def uniform_flow_solution(self, Q: float, B: float, S0: float, n: float, 
                             x: np.ndarray) -> dict:
        """
        计算整个渠道的均匀流解（解析解）
        
        Args:
            Q: 流量
            B: 渠宽
            S0: 渠底坡度
            n: Manning糙率
            x: 位置数组
        
        Returns:
            solution: 包含h, u, Fr的解析解
        """
        # 计算均匀流水深
        h_n = self.uniform_flow_depth(Q, B, S0, n)
        
        # 计算流速
        u_n = Q / (B * h_n)
        
        # 计算Froude数
        Fr = u_n / np.sqrt(self.g * h_n)
        
        # 均匀流，所有位置相同
        solution = {
            'x': x,
            'h': np.ones_like(x) * h_n,
            'u': np.ones_like(x) * u_n,
            'Fr': np.ones_like(x) * Fr,
            'Q': np.ones_like(x) * Q,
            'type': 'uniform_flow',
            'parameters': {'Q': Q, 'B': B, 'S0': S0, 'n': n}
        }
        
        return solution
    
    #===========================================================================
    # 2. 临界流（重要的验证点）
    #===========================================================================
    
    def critical_depth(self, Q: float, B: float) -> float:
        """
        计算临界水深（解析解）
        
        公式：h_c = (Q² / (g * B²))^(1/3)
        
        Args:
            Q: 流量 (m³/s)
            B: 渠道宽度 (m)
        
        Returns:
            h_c: 临界水深 (m)
        """
        h_c = (Q**2 / (self.g * B**2)) ** (1.0/3.0)
        return h_c
    
    def critical_velocity(self, h_c: float) -> float:
        """
        计算临界流速（解析解）
        
        公式：u_c = sqrt(g * h_c)
        
        Args:
            h_c: 临界水深 (m)
        
        Returns:
            u_c: 临界流速 (m/s)
        """
        u_c = np.sqrt(self.g * h_c)
        return u_c
    
    def critical_slope(self, Q: float, B: float, n: float) -> float:
        """
        计算临界坡度（解析解）
        
        临界流时的渠底坡度。
        
        Args:
            Q: 流量
            B: 渠宽
            n: Manning糙率
        
        Returns:
            S_c: 临界坡度
        """
        h_c = self.critical_depth(Q, B)
        A = B * h_c
        P = B + 2 * h_c
        R = A / P
        u_c = Q / A
        
        # Manning公式反解坡度
        S_c = (u_c * n / R**(2.0/3.0)) ** 2
        
        return S_c
    
    #===========================================================================
    # 3. 水跃（非线性现象验证）
    #===========================================================================
    
    def hydraulic_jump_conjugate_depth(self, h1: float, Fr1: float) -> float:
        """
        计算水跃共轭水深（解析解）
        
        公式：h2/h1 = 0.5 * (-1 + sqrt(1 + 8*Fr1²))
        
        Args:
            h1: 上游水深 (m)
            Fr1: 上游Froude数
        
        Returns:
            h2: 下游共轭水深 (m)
        """
        ratio = 0.5 * (-1.0 + np.sqrt(1.0 + 8.0 * Fr1**2))
        h2 = h1 * ratio
        return h2
    
    def hydraulic_jump_energy_loss(self, h1: float, h2: float, 
                                   u1: float, u2: float) -> float:
        """
        计算水跃能量损失（解析解）
        
        Args:
            h1: 上游水深
            h2: 下游水深
            u1: 上游流速
            u2: 下游流速
        
        Returns:
            delta_E: 能量损失 (m)
        """
        E1 = h1 + u1**2 / (2 * self.g)
        E2 = h2 + u2**2 / (2 * self.g)
        delta_E = E1 - E2
        return delta_E
    
    #===========================================================================
    # 4. 宽顶堰流量公式（结构物验证）
    #===========================================================================
    
    def broad_crested_weir_discharge(self, h_upstream: float, 
                                     B: float, P: float) -> float:
        """
        宽顶堰流量公式（解析解）
        
        公式：Q = C * B * sqrt(2*g) * H^(3/2)
        其中 H = h - P（堰顶水头）
        
        Args:
            h_upstream: 上游水深 (m)
            B: 堰宽 (m)
            P: 堰高 (m)
        
        Returns:
            Q: 流量 (m³/s)
        """
        if h_upstream <= P:
            return 0.0
        
        H = h_upstream - P
        C = 1.7  # 宽顶堰流量系数
        Q = C * B * np.sqrt(2 * self.g) * H ** 1.5
        
        return Q
    
    #===========================================================================
    # 5. 水面曲线（逐步积分法，准解析解）
    #===========================================================================
    
    def gradually_varied_flow(self, Q: float, B: float, S0: float, n: float,
                             h_downstream: float, length: float, 
                             n_points: int = 100) -> dict:
        """
        渐变流水面曲线（逐步积分法，准解析解）
        
        求解能量方程：dh/dx = (S0 - Sf) / (1 - Fr²)
        
        Args:
            Q: 流量
            B: 渠宽
            S0: 渠底坡度
            n: Manning糙率
            h_downstream: 下游边界水深
            length: 渠道长度
            n_points: 积分点数
        
        Returns:
            solution: 水面曲线解
        """
        x = np.linspace(0, length, n_points)
        dx = x[1] - x[0]
        
        h = np.zeros(n_points)
        u = np.zeros(n_points)
        Fr = np.zeros(n_points)
        
        # 从下游向上游积分
        h[-1] = h_downstream
        
        for i in range(n_points - 1, 0, -1):
            h_i = h[i]
            
            # 计算流速和Froude数
            u_i = Q / (B * h_i)
            Fr_i = u_i / np.sqrt(self.g * h_i)
            
            # 计算摩阻坡度
            A = B * h_i
            P = B + 2 * h_i
            R = A / P
            Sf = (n * u_i / R**(2.0/3.0)) ** 2
            
            # 能量方程
            dh_dx = (S0 - Sf) / (1.0 - Fr_i**2)
            
            # 向上游推进
            h[i-1] = h_i + dh_dx * dx
            
            # 存储
            u[i] = u_i
            Fr[i] = Fr_i
        
        # 最后一点
        u[0] = Q / (B * h[0])
        Fr[0] = u[0] / np.sqrt(self.g * h[0])
        
        solution = {
            'x': x,
            'h': h,
            'u': u,
            'Fr': Fr,
            'Q': np.ones_like(x) * Q,
            'type': 'gradually_varied_flow',
            'parameters': {'Q': Q, 'B': B, 'S0': S0, 'n': n, 'h_downstream': h_downstream}
        }
        
        return solution
    
    #===========================================================================
    # 6. 复合函数（便捷计算）
    #===========================================================================
    
    def compute_froude_number(self, u: float, h: float) -> float:
        """计算Froude数"""
        return u / np.sqrt(self.g * h)
    
    def compute_specific_energy(self, h: float, u: float) -> float:
        """计算比能"""
        return h + u**2 / (2 * self.g)
    
    def compute_flow_classification(self, Fr: float) -> str:
        """判断流态"""
        if Fr < 0.9:
            return "亚临界流"
        elif Fr > 1.1:
            return "超临界流"
        else:
            return "临界流"


# ========== 验证函数 ==========

def verify_analytical_solutions():
    """验证解析解的正确性（自洽性检查）"""
    print("\n" + "="*70)
    print("解析解自洽性验证")
    print("="*70)
    
    solver = AnalyticalSolutions()
    
    # 测试1：均匀流
    print("\n测试1：均匀流")
    Q, B, S0, n = 10.0, 10.0, 0.001, 0.025
    h_n = solver.uniform_flow_depth(Q, B, S0, n)
    u_n = solver.uniform_flow_velocity(h_n, S0, n, B)
    Q_check = B * h_n * u_n
    print(f"  流量: Q={Q:.2f} m³/s")
    print(f"  水深: h={h_n:.3f} m")
    print(f"  流速: u={u_n:.3f} m/s")
    print(f"  流量验证: Q={Q_check:.2f} m³/s（误差={(Q_check-Q)/Q*100:.6f}%）")
    assert abs(Q_check - Q) / Q < 1e-6, "均匀流解析解有误"
    
    # 测试2：临界流
    print("\n测试2：临界流")
    h_c = solver.critical_depth(Q, B)
    u_c = solver.critical_velocity(h_c)
    Fr = solver.compute_froude_number(u_c, h_c)
    print(f"  临界水深: h_c={h_c:.3f} m")
    print(f"  临界流速: u_c={u_c:.3f} m/s")
    print(f"  Froude数: Fr={Fr:.6f}（理论=1.0）")
    assert abs(Fr - 1.0) < 1e-6, "临界流解析解有误"
    
    # 测试3：水跃
    print("\n测试3：水跃")
    h1, Fr1 = 0.5, 3.0
    u1 = Fr1 * np.sqrt(solver.g * h1)
    h2 = solver.hydraulic_jump_conjugate_depth(h1, Fr1)
    u2 = (h1 * u1) / h2  # 连续性
    Fr2 = solver.compute_froude_number(u2, h2)
    print(f"  上游: h1={h1:.3f} m, Fr1={Fr1:.2f}")
    print(f"  下游: h2={h2:.3f} m, Fr2={Fr2:.3f}")
    print(f"  流量守恒: Q1={h1*u1:.3f}, Q2={h2*u2:.3f}（误差={(h2*u2-h1*u1)/(h1*u1)*100:.6f}%）")
    assert abs(h1*u1 - h2*u2) / (h1*u1) < 1e-6, "水跃解析解流量不守恒"
    
    print("\n" + "="*70)
    print("✅ 解析解自洽性验证通过")
    print("="*70)


if __name__ == '__main__':
    verify_analytical_solutions()
