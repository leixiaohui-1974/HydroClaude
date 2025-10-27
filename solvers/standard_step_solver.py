#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
标准步法求解器（Standard Step Method）

用于计算渐变流水面曲线（Gradually Varied Flow）

核心思想:
1. 基于能量方程的逐段计算
2. 从已知边界逐步推进
3. 使用优化方法求解每个断面水深
4. 适用于所有类型的水面曲线（M1, M2, S1, S2等）

Author: HydroClaude Development Team
Date: 2025-10-27
Reference: Chaudhry (2008) Open-Channel Flow, Chapter 5
"""

import numpy as np
from scipy.optimize import minimize_scalar, brentq
import sys
import os

# 添加项目路径
script_path = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(script_path))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


class StandardStepSolver:
    """
    标准步法求解器（经典方法）
    
    基于能量方程逐段计算渐变流水面曲线
    
    方法:
    1. 从已知边界开始（下游或上游）
    2. 逐断面求解能量方程
    3. 能量方程: H₂ = H₁ - Sf·Δx
    
    优势:
    - 支持所有类型渐变流
    - 精度高
    - 稳定可靠
    """
    
    def __init__(self, B, S0, n, g=9.81):
        """
        初始化标准步法求解器
        
        参数:
            B: 渠道宽度 (m)
            S0: 渠底坡度
            n: Manning糙率系数
            g: 重力加速度 (m/s²)
        """
        self.B = B
        self.S0 = S0
        self.n = n
        self.g = g
        
        print(f"="*70)
        print(f"标准步法求解器初始化")
        print(f"="*70)
        print(f"渠道宽度: {B} m")
        print(f"底坡: {S0}")
        print(f"Manning糙率: {n}")
        print(f"="*70)
    
    def compute_total_head(self, h, Q, z=0):
        """
        计算总水头 H = z + h + v²/(2g)
        
        参数:
            h: 水深 (m)
            Q: 流量 (m³/s)
            z: 床面高程 (m)
        
        返回:
            H: 总水头 (m)
        """
        v = Q / (self.B * h)
        v_head = v**2 / (2 * self.g)
        H = z + h + v_head
        return H
    
    def compute_friction_slope(self, h, Q):
        """
        计算摩阻坡度（Manning公式，考虑湿周）
        
        Sf = n² * v² / R^(4/3)
        
        参数:
            h: 水深 (m)
            Q: 流量 (m³/s)
        
        返回:
            Sf: 摩阻坡度
        """
        v = Q / (self.B * h)
        A = self.B * h
        P = self.B + 2 * h
        R = A / P
        Sf = self.n**2 * v**2 / (R**(4/3))
        return Sf
    
    def compute_normal_depth(self, Q):
        """
        计算正常水深（均匀流水深）
        
        参数:
            Q: 流量 (m³/s)
        
        返回:
            h_n: 正常水深 (m)
        """
        def manning_eq(h):
            if h <= 0:
                return 1e10
            A = self.B * h
            P = self.B + 2 * h
            R = A / P
            Q_calc = (1.0 / self.n) * A * (R ** (2.0/3.0)) * (self.S0 ** 0.5)
            return Q_calc - Q
        
        h0 = (Q * self.n / (self.B * self.S0**0.5)) ** 0.6
        from scipy.optimize import fsolve
        h_n = fsolve(manning_eq, h0)[0]
        
        return h_n
    
    def compute_critical_depth(self, Q):
        """
        计算临界水深
        
        Fr = 1时的水深
        
        参数:
            Q: 流量 (m³/s)
        
        返回:
            h_c: 临界水深 (m)
        """
        # Fr² = v² / (g*h) = Q² / (g*B²*h³) = 1
        # h_c³ = Q² / (g*B²)
        h_c = (Q**2 / (self.g * self.B**2)) ** (1/3)
        return h_c
    
    def solve_gvf(self, Q, positions, h_boundary, boundary_type='downstream', 
                  verbose=True):
        """
        求解渐变流水面曲线（Gradually Varied Flow）
        
        使用标准步法从边界逐步推进
        
        参数:
            Q: 流量 (m³/s)
            positions: 计算位置数组 (m)，从下游到上游
            h_boundary: 边界水深 (m)
            boundary_type: 'downstream' 或 'upstream'
            verbose: 是否打印详细信息
        
        返回:
            result: 结果字典
        """
        if verbose:
            print(f"\n{'='*70}")
            print(f"标准步法求解渐变流")
            print(f"{'='*70}")
            print(f"流量: {Q:.2f} m³/s")
            print(f"计算点数: {len(positions)}")
            print(f"边界条件: {boundary_type}, h={h_boundary:.3f}m")
            print(f"{'='*70}\n")
        
        # 床面高程（x方向从下游到上游，z从低到高）
        z = (positions - positions[0]) * self.S0
        
        # 初始化
        h = np.zeros(len(positions))
        
        if boundary_type == 'downstream':
            # 从下游向上游推进
            h[0] = h_boundary
            
            for i in range(1, len(positions)):
                dx = positions[i] - positions[i-1]
                h[i] = self.solve_step_upstream(
                    h_prev=h[i-1],
                    z_prev=z[i-1],
                    z_curr=z[i],
                    dx=dx,
                    Q=Q
                )
        
        else:  # upstream
            # 从上游向下游推进
            h[-1] = h_boundary
            
            for i in range(len(positions)-2, -1, -1):
                dx = positions[i+1] - positions[i]
                h[i] = self.solve_step_downstream(
                    h_next=h[i+1],
                    z_next=z[i+1],
                    z_curr=z[i],
                    dx=dx,
                    Q=Q
                )
        
        # 计算其他变量
        v = Q / (self.B * h)
        Fr = v / np.sqrt(self.g * h)
        Sf = np.array([self.compute_friction_slope(h[i], Q) for i in range(len(h))])
        H = z + h + v**2 / (2 * self.g)
        
        if verbose:
            print(f"\n{'='*70}")
            print(f"求解完成")
            print(f"{'='*70}")
            print(f"水深范围: {h.min():.3f} - {h.max():.3f} m")
            print(f"Froude数范围: {Fr.min():.3f} - {Fr.max():.3f}")
            print(f"{'='*70}")
        
        result = {
            'x': positions,
            'h': h,
            'z': z,
            'H': H,
            'v': v,
            'Fr': Fr,
            'Sf': Sf,
            'Q': Q
        }
        
        return result
    
    def solve_step_upstream(self, h_prev, z_prev, z_curr, dx, Q):
        """
        从下游断面向上游推进一步
        
        能量方程: H_curr = H_prev - Sf_avg * dx
        
        参数:
            h_prev: 下游断面水深 (m)
            z_prev: 下游床面高程 (m)
            z_curr: 当前床面高程 (m)
            dx: 步长 (m)
            Q: 流量 (m³/s)
        
        返回:
            h_curr: 当前断面水深 (m)
        """
        def energy_residual(h):
            """能量方程残差"""
            if h <= 0.01:
                return 1e10
            
            # 上游总水头
            H_curr = self.compute_total_head(h, Q, z_curr)
            
            # 下游总水头
            H_prev = self.compute_total_head(h_prev, Q, z_prev)
            
            # 平均摩阻坡度
            Sf_prev = self.compute_friction_slope(h_prev, Q)
            Sf_curr = self.compute_friction_slope(h, Q)
            Sf_avg = 0.5 * (Sf_prev + Sf_curr)
            
            # 能量方程: H_curr = H_prev + Sf_avg * dx
            # （向上游推进，逆流方向，总水头增加）
            residual = H_curr - H_prev - Sf_avg * dx
            
            return residual**2
        
        # 使用优化方法求解（带约束，确保正水深）
        result = minimize_scalar(
            energy_residual,
            bounds=(0.01, max(20.0, 3*h_prev)),
            method='bounded'
        )
        
        return result.x
    
    def solve_step_downstream(self, h_next, z_next, z_curr, dx, Q):
        """
        从上游断面向下游推进一步
        
        能量方程: H_curr = H_next + Sf_avg * dx
        
        参数:
            h_next: 上游断面水深 (m)
            z_next: 上游床面高程 (m)
            z_curr: 当前床面高程 (m)
            dx: 步长 (m)
            Q: 流量 (m³/s)
        
        返回:
            h_curr: 当前断面水深 (m)
        """
        def energy_residual(h):
            """能量方程残差"""
            if h <= 0.01:
                return 1e10
            
            # 当前总水头
            H_curr = self.compute_total_head(h, Q, z_curr)
            
            # 上游总水头
            H_next = self.compute_total_head(h_next, Q, z_next)
            
            # 平均摩阻坡度
            Sf_next = self.compute_friction_slope(h_next, Q)
            Sf_curr = self.compute_friction_slope(h, Q)
            Sf_avg = 0.5 * (Sf_next + Sf_curr)
            
            # 能量方程: H_curr = H_next + Sf_avg * dx
            # （向下游，总水头减少，但这里dx是负的）
            residual = H_curr - H_next - Sf_avg * dx
            
            return residual**2
        
        # 使用优化方法求解
        result = minimize_scalar(
            energy_residual,
            bounds=(0.01, max(20.0, 3*h_next)),
            method='bounded'
        )
        
        return result.x


def main():
    """测试标准步法求解器"""
    print("="*70)
    print("测试标准步法求解器")
    print("="*70)
    
    # 参数
    B = 10.0
    S0 = 0.001
    n = 0.025
    Q = 10.0
    length = 10000
    
    print(f"\n测试场景: Goutal M1壅水曲线")
    print(f"  L={length}m, Q={Q}m³/s, S0={S0}, n={n}")
    
    # 创建求解器
    solver = StandardStepSolver(B=B, S0=S0, n=n)
    
    # 计算正常水深和临界水深
    h_n = solver.compute_normal_depth(Q)
    h_c = solver.compute_critical_depth(Q)
    
    print(f"\n特征水深:")
    print(f"  正常水深 h_n: {h_n:.4f} m")
    print(f"  临界水深 h_c: {h_c:.4f} m")
    
    # 下游边界（大于正常水深，形成M1壅水曲线）
    h_downstream = 2.5  # Goutal M1的下游水深
    
    print(f"  下游边界: {h_downstream:.4f} m")
    print(f"  类型: {'M1壅水曲线' if h_downstream > h_n else 'M2降水曲线'}")
    
    # 计算位置
    positions = np.linspace(0, length, 100)
    
    # 求解
    result = solver.solve_gvf(
        Q=Q,
        positions=positions,
        h_boundary=h_downstream,
        boundary_type='downstream',
        verbose=True
    )
    
    # 显示结果
    print(f"\n水面曲线:")
    print(f"  下游h: {result['h'][0]:.3f} m")
    print(f"  中游h: {result['h'][len(result['h'])//2]:.3f} m")
    print(f"  上游h: {result['h'][-1]:.3f} m")
    print(f"  h变化: {result['h'][-1] - result['h'][0]:.3f} m")
    
    print(f"\n{'='*70}")
    print(f"✓ 标准步法测试完成！")
    print(f"{'='*70}")


if __name__ == '__main__':
    main()
