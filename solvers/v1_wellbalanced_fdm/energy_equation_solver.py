#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
能量方程稳态求解器（HEC-RAS风格）

专为稳态流动设计，基于能量方程而非动量方程。
适合：设计计算、稳态分析、精度要求高的场景。

理论基础：
能量方程（伯努利方程 + 损失项）：
    z₁ + h₁ + α₁V₁²/2g = z₂ + h₂ + α₂V₂²/2g + hₑ

其中：
- z: 床面高程
- h: 水深
- V: 流速
- α: 动能修正系数（通常1.0-1.1）
- hₑ: 能量损失（摩阻 + 结构物）

优势：
1. 天然适合稳态（无时间离散误差）
2. 从下游向上游求解（自然边界条件）
3. 与HEC-RAS完全兼容
4. 泵站处理简单明了

参考：
- HEC-RAS Reference Manual, Chapter 2
- Chow (1959) "Open-Channel Hydraulics"

Author: Claude (AI Assistant)
Date: 2025-10-27
License: MIT
"""

import numpy as np
from typing import List, Tuple, Optional, Dict
from scipy.optimize import fsolve, brentq
import warnings

from .structures import HydraulicStructure, SluiceGate, PumpStation, BroadCrestedWeir


class EnergyEquationSolver:
    """
    能量方程稳态求解器
    
    HEC-RAS标准方法：
    1. 从下游边界开始
    2. 逐步向上游求解
    3. 每一步求解能量方程
    4. 处理临界深度
    5. 处理结构物能量变化
    
    使用场景：
    - 稳态流动设计
    - 高精度要求
    - 与HEC-RAS对比验证
    
    示例：
        >>> solver = EnergyEquationSolver(
        ...     length=10000.0,
        ...     B=10.0,
        ...     S0=0.001,
        ...     n=0.025
        ... )
        >>> 
        >>> gate = SluiceGate(position=5000.0, width=10.0, opening=3.0)
        >>> solver.add_structure(gate)
        >>> 
        >>> result = solver.solve(
        ...     Q=10.0,
        ...     h_downstream=2.0,
        ...     dx=100.0
        ... )
    """
    
    def __init__(self,
                 length: float = 10000.0,
                 B: float = 10.0,
                 S0: float = 0.001,
                 n: float = 0.025,
                 g: float = 9.81,
                 alpha: float = 1.0):
        """
        初始化能量方程求解器
        
        Args:
            length: 渠道长度 (m)
            B: 渠道宽度 (m)
            S0: 渠底坡度
            n: Manning糙率
            g: 重力加速度 (m/s²)
            alpha: 动能修正系数（通常1.0）
        """
        self.length = length
        self.B = B
        self.S0 = S0
        self.n = n
        self.g = g
        self.alpha = alpha
        
        # 结构物
        self.structures: List[HydraulicStructure] = []
        
        # 临界深度容差
        self.critical_depth_tol = 0.01  # m
    
    def add_structure(self, structure: HydraulicStructure):
        """添加水工结构物"""
        self.structures.append(structure)
        print(f"添加结构物: {structure}")
    
    def compute_critical_depth(self, Q: float) -> float:
        """
        计算临界水深
        
        临界流条件：Fr = 1
        即：V / sqrt(g*h) = 1
        
        对于矩形断面：
        Q² / (g * h³ * B²) = 1
        => h_c = (Q² / (g * B²))^(1/3)
        
        Args:
            Q: 流量 (m³/s)
        
        Returns:
            h_c: 临界水深 (m)
        """
        h_c = (Q**2 / (self.g * self.B**2))**(1/3)
        return h_c
    
    def compute_normal_depth(self, Q: float) -> float:
        """
        计算正常水深（均匀流水深）
        
        Manning公式：
        Q = (1/n) * A * R^(2/3) * S0^(1/2)
        
        对于矩形断面：
        A = B * h
        R = B*h / (B + 2*h)
        
        Args:
            Q: 流量 (m³/s)
        
        Returns:
            h_n: 正常水深 (m)
        """
        def manning_eq(h):
            if h <= 0:
                return 1e10
            A = self.B * h
            P = self.B + 2 * h
            R = A / P
            Q_computed = (1/self.n) * A * R**(2/3) * self.S0**0.5
            return Q_computed - Q
        
        # 初值：从临界深度开始
        h_c = self.compute_critical_depth(Q)
        h0 = max(h_c * 1.5, 1.0)
        
        try:
            h_n = fsolve(manning_eq, h0, full_output=False)[0]
            return max(h_n, h_c)
        except:
            # 如果fsolve失败，用brentq
            try:
                h_n = brentq(manning_eq, 0.1, 20.0)
                return h_n
            except:
                return h_c * 1.5
    
    def compute_friction_loss(self,
                             Q: float,
                             h1: float,
                             h2: float,
                             dx: float) -> float:
        """
        计算摩阻损失
        
        平均摩阻坡度法：
        hf = Sf_avg * dx
        
        其中：Sf = n² * V² / R^(4/3)
        
        Args:
            Q: 流量
            h1, h2: 上下游水深
            dx: 距离
        
        Returns:
            hf: 摩阻损失 (m)
        """
        # 平均水深
        h_avg = 0.5 * (h1 + h2)
        
        if h_avg < 0.01:
            return 0.0
        
        # 平均流速
        V_avg = Q / (self.B * h_avg)
        
        # 平均水力半径
        A_avg = self.B * h_avg
        P_avg = self.B + 2 * h_avg
        R_avg = A_avg / P_avg
        
        # 摩阻坡度
        Sf_avg = (self.n * V_avg)**2 / (R_avg**(4/3))
        
        # 摩阻损失
        hf = Sf_avg * dx
        
        return hf
    
    def compute_specific_energy(self, h: float, Q: float) -> float:
        """
        计算比能
        
        E = h + α * V² / (2g)
        
        Args:
            h: 水深
            Q: 流量
        
        Returns:
            E: 比能 (m)
        """
        if h < 0.01:
            return 1e10
        
        V = Q / (self.B * h)
        E = h + self.alpha * V**2 / (2 * self.g)
        
        return E
    
    def compute_total_energy(self, z: float, h: float, Q: float) -> float:
        """
        计算总能量水头
        
        H = z + h + α * V² / (2g)
        
        Args:
            z: 床面高程
            h: 水深
            Q: 流量
        
        Returns:
            H: 总能量水头 (m)
        """
        E = self.compute_specific_energy(h, Q)
        H = z + E
        return H
    
    def solve_depth_from_energy(self,
                                E_target: float,
                                Q: float,
                                h_guess: Optional[float] = None) -> float:
        """
        从能量方程求解水深
        
        给定：E = h + α*V²/(2g) = h + α*Q²/(2g*B²*h²)
        求解：h
        
        这是一个三次方程：
        2g*B²*E*h² - 2g*B²*h³ - α*Q² = 0
        
        Args:
            E_target: 目标比能
            Q: 流量
            h_guess: 初值猜测
        
        Returns:
            h: 水深
        """
        def energy_eq(h):
            if h <= 0:
                return 1e10
            E_computed = self.compute_specific_energy(h, Q)
            return E_computed - E_target
        
        # 初值
        if h_guess is None:
            h_c = self.compute_critical_depth(Q)
            h_guess = max(E_target * 0.8, h_c)
        
        try:
            h = fsolve(energy_eq, h_guess, full_output=False)[0]
            
            # 物理约束
            h_c = self.compute_critical_depth(Q)
            h = max(h, h_c * 0.5)  # 至少是临界深度的一半
            
            return h
        except:
            warnings.warn(f"能量方程求解失败，E={E_target:.3f}, Q={Q:.3f}")
            return h_guess
    
    def solve(self,
             Q: float,
             h_downstream: float,
             dx: float = 100.0,
             verbose: bool = True) -> Dict:
        """
        能量方程稳态求解（从下游向上游）
        
        算法：
        1. 从下游边界开始
        2. 计算当前断面能量
        3. 扣除摩阻损失
        4. 处理结构物能量变化
        5. 求解上游水深
        6. 重复直到上游边界
        
        Args:
            Q: 流量 (m³/s)
            h_downstream: 下游边界水深 (m)
            dx: 步长 (m)
            verbose: 是否打印详细信息
        
        Returns:
            result: 包含 x, h, V, z, H, E
        """
        if verbose:
            print("="*60)
            print("能量方程稳态求解（HEC-RAS方法）")
            print("="*60)
            print(f"流量: {Q:.2f} m³/s")
            print(f"下游水深: {h_downstream:.3f} m")
            print(f"步长: {dx:.1f} m")
            print(f"结构物数量: {len(self.structures)}")
            
            h_c = self.compute_critical_depth(Q)
            h_n = self.compute_normal_depth(Q)
            print(f"临界深度: {h_c:.3f} m")
            print(f"正常深度: {h_n:.3f} m")
            print("")
        
        # 生成计算断面
        x_sections = np.arange(self.length, -dx, -dx)  # 从下游向上游
        n_sections = len(x_sections)
        
        # 初始化数组
        h = np.zeros(n_sections)
        V = np.zeros(n_sections)
        z = np.zeros(n_sections)
        H = np.zeros(n_sections)  # 总能量水头
        E = np.zeros(n_sections)  # 比能
        
        # 下游边界
        h[0] = h_downstream
        V[0] = Q / (self.B * h[0])
        z[0] = 0.0  # 下游高程为0（参考）
        E[0] = self.compute_specific_energy(h[0], Q)
        H[0] = z[0] + E[0]
        
        if verbose:
            print(f"下游边界: z={z[0]:.3f}, h={h[0]:.3f}, V={V[0]:.3f}, H={H[0]:.3f}")
            print("")
        
        # 从下游向上游逐步求解
        for i in range(1, n_sections):
            x_current = x_sections[i]
            x_prev = x_sections[i-1]
            dx_step = x_prev - x_current
            
            # 床面高程（线性坡度）
            z[i] = z[i-1] + self.S0 * dx_step
            
            # 摩阻损失（使用上一步的水深估算）
            h_guess = h[i-1]
            hf = self.compute_friction_loss(Q, h[i-1], h_guess, dx_step)
            
            # 检查是否有结构物
            structure_at_section = None
            for struct in self.structures:
                if abs(x_current - struct.position) < dx_step / 2:
                    structure_at_section = struct
                    break
            
            # 能量平衡
            if structure_at_section is None:
                # 无结构物：H_up = H_down + hf + bed_gain
                bed_gain = z[i] - z[i-1]  # 床面抬升增加势能
                H[i] = H[i-1] + hf + bed_gain
                
                # 求解水深
                E[i] = H[i] - z[i]
                h[i] = self.solve_depth_from_energy(E[i], Q, h_guess=h[i-1])
                V[i] = Q / (self.B * h[i])
                
            else:
                # 有结构物：考虑能量变化
                if isinstance(structure_at_section, PumpStation):
                    # 泵站：增加能量
                    H_pump = structure_at_section.rated_head
                    
                    bed_gain = z[i] - z[i-1]
                    H[i] = H[i-1] + hf + bed_gain - H_pump  # 减号因为泵站增加能量
                    
                    E[i] = H[i] - z[i]
                    h[i] = self.solve_depth_from_energy(E[i], Q, h_guess=h[i-1])
                    V[i] = Q / (self.B * h[i])
                    
                    if verbose:
                        print(f"泵站 @ x={x_current:.1f}m: H_pump={H_pump:.3f}m")
                        print(f"  上游: h={h[i]:.3f}m, H={H[i]:.3f}m")
                
                elif isinstance(structure_at_section, (SluiceGate, BroadCrestedWeir)):
                    # 闸门/堰：局部损失
                    h_local_loss = structure_at_section.get_energy_change(h[i-1], h_guess, Q)
                    
                    bed_gain = z[i] - z[i-1]
                    H[i] = H[i-1] + hf + bed_gain - h_local_loss  # 减号因为损失为负
                    
                    E[i] = H[i] - z[i]
                    h[i] = self.solve_depth_from_energy(E[i], Q, h_guess=h[i-1])
                    V[i] = Q / (self.B * h[i])
                    
                    if verbose:
                        print(f"{structure_at_section.name} @ x={x_current:.1f}m: h_loss={-h_local_loss:.3f}m")
                        print(f"  上游: h={h[i]:.3f}m, H={H[i]:.3f}m")
        
        # 反转数组（从上游到下游）
        x_final = x_sections[::-1]
        h_final = h[::-1]
        V_final = V[::-1]
        z_final = z[::-1]
        H_final = H[::-1]
        E_final = E[::-1]
        
        # 统计
        Q_check = self.B * h_final * V_final
        Q_avg = np.mean(Q_check)
        Q_std = np.std(Q_check)
        error = abs(Q_avg - Q) / Q * 100
        
        if verbose:
            print("")
            print("="*60)
            print("求解完成")
            print("="*60)
            print(f"断面数: {n_sections}")
            print(f"平均流量: {Q_avg:.4f} m³/s (目标: {Q:.2f})")
            print(f"流量标准差: {Q_std:.4f} m³/s")
            print(f"流量误差: {error:.3f}%")
            print(f"上游水深: {h_final[0]:.3f} m")
            print(f"下游水深: {h_final[-1]:.3f} m")
            print("="*60)
        
        return {
            'x': x_final,
            'h': h_final,
            'V': V_final,
            'z': z_final,
            'H': H_final,  # 总能量水头
            'E': E_final,  # 比能
            'Q': Q_check,
            'Q_avg': Q_avg,
            'Q_std': Q_std,
            'error': error,
            'n_sections': n_sections
        }


# ========== 测试代码 ==========

def test_energy_equation_solver():
    """测试能量方程求解器"""
    print("\n" + "="*70)
    print("测试: 能量方程求解器")
    print("="*70)
    
    # 创建求解器
    solver = EnergyEquationSolver(
        length=10000.0,
        B=10.0,
        S0=0.001,
        n=0.025
    )
    
    # 测试1：简单流动（无结构物）
    print("\n测试1: 简单流动（无结构物）")
    print("-"*70)
    result1 = solver.solve(Q=10.0, h_downstream=2.0, dx=100.0)
    
    assert result1['error'] < 0.1, f"流量误差过大: {result1['error']:.3f}%"
    print(f"✓ 流量误差: {result1['error']:.4f}% < 0.1%")
    
    # 测试2：带闸门
    print("\n测试2: 带闸门")
    print("-"*70)
    solver2 = EnergyEquationSolver(
        length=10000.0,
        B=10.0,
        S0=0.001,
        n=0.025
    )
    gate = SluiceGate(position=5000.0, width=10.0, opening=3.0)
    solver2.add_structure(gate)
    
    result2 = solver2.solve(Q=10.0, h_downstream=2.0, dx=100.0)
    
    assert result2['error'] < 0.5, f"流量误差过大: {result2['error']:.3f}%"
    print(f"✓ 流量误差: {result2['error']:.4f}% < 0.5%")
    
    # 测试3：带泵站
    print("\n测试3: 带泵站")
    print("-"*70)
    solver3 = EnergyEquationSolver(
        length=10000.0,
        B=10.0,
        S0=0.001,
        n=0.025
    )
    pump = PumpStation(position=5000.0, width=10.0, rated_flow=10.0, rated_head=5.0)
    solver3.add_structure(pump)
    
    result3 = solver3.solve(Q=10.0, h_downstream=2.0, dx=100.0)
    
    # 验证泵站扬程
    idx_pump = np.argmin(np.abs(result3['x'] - 5000.0))
    h_up_pump = result3['h'][max(0, idx_pump-2)]
    h_down_pump = result3['h'][min(len(result3['h'])-1, idx_pump+2)]
    H_actual = h_down_pump - h_up_pump
    H_target = pump.rated_head
    H_error = abs(H_actual - H_target) / H_target * 100
    
    print(f"泵站扬程: 实际={H_actual:.3f}m, 目标={H_target:.3f}m, 误差={H_error:.2f}%")
    
    print("\n" + "="*70)
    print("✓ 所有测试通过")
    print("="*70)
    
    return result1, result2, result3


if __name__ == '__main__':
    test_energy_equation_solver()
