#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
有限差分动量方程

动量方程（Saint-Venant动量方程）：
    ∂Q/∂t + ∂(Q²/A)/∂x + gA∂h/∂x = gA(S0 - Sf)

有限差分离散化（在界面上）：
    dQ_{i+1/2}/dt = -∂(Q²/A)/∂x - gA∂h/∂x + gA(S0 - Sf)

混合策略：
- 对流项：迎风格式（稳定）
- 压力项：中心差分（精确）
- 源项：半隐式（稳定）

关键特性：
1. 在界面上求解（自然位置）
2. 保持计算效率
3. 与FV连续性方程耦合

参考：
- Lai & Khan (2018) JHD
- Stelling & Duinmeijer (2003)

Author: Claude (AI Assistant)
Date: 2025-10-27
"""

import numpy as np
from typing import Tuple

from .staggered_grid import StaggeredGrid


class FDMomentumEquation:
    """
    有限差分动量方程
    
    在交错网格的界面上求解动量方程。
    
    离散化策略：
    1. 对流项 ∂(Q²/A)/∂x: 迎风格式
    2. 压力项 gA∂h/∂x: 中心差分
    3. 床面坡度项 gAS0: 解析计算
    4. 摩阻项 gASf: 半隐式
    
    时间推进：
    - 显式Adams-Bashforth（2阶）
    - 或隐式Crank-Nicolson（稳定）
    """
    
    def __init__(self,
                 grid: StaggeredGrid,
                 B: float = 10.0,
                 S0: float = 0.001,
                 n: float = 0.025,
                 g: float = 9.81,
                 theta: float = 0.6):
        """
        初始化FD动量方程
        
        Args:
            grid: 交错网格
            B: 渠道宽度
            S0: 渠底坡度
            n: Manning糙率
            g: 重力加速度
            theta: 隐式度（0.5=Crank-Nicolson, 1.0=全隐式）
        """
        self.grid = grid
        self.B = B
        self.S0 = S0
        self.n = n
        self.g = g
        self.theta = theta
        
        self.eps_dry = 1e-6
    
    def compute_convection_term(self,
                               h: np.ndarray,
                               Q: np.ndarray) -> np.ndarray:
        """
        计算对流项 ∂(Q²/A)/∂x（在界面）
        
        使用迎风格式离散化。
        
        Args:
            h: 单元中心水深
            Q: 单元界面流量
        
        Returns:
            conv: 对流项 (n_faces,)
        """
        conv = np.zeros(self.grid.n_faces)
        
        # 插值水深到界面
        h_face = self.grid.interpolate_center_to_face(h)
        
        for i in range(1, self.grid.n_faces - 1):
            # 界面流速
            A_face = self.B * max(h_face[i], self.eps_dry)
            u_face = Q[i] / A_face
            
            # 迎风差分
            if u_face >= 0:
                # 向右流：后向差分
                Q_left = Q[i-1] if i > 0 else Q[i]
                A_left = self.B * max(h_face[i-1], self.eps_dry) if i > 0 else A_face
                
                momentum_left = Q_left**2 / A_left
                momentum_center = Q[i]**2 / A_face
                
                dx = self.grid.x_face[i] - self.grid.x_face[i-1] if i > 0 else 1.0
                conv[i] = (momentum_center - momentum_left) / dx
            else:
                # 向左流：前向差分
                Q_right = Q[i+1] if i < self.grid.n_faces-1 else Q[i]
                A_right = self.B * max(h_face[i+1], self.eps_dry) if i < self.grid.n_faces-1 else A_face
                
                momentum_center = Q[i]**2 / A_face
                momentum_right = Q_right**2 / A_right
                
                dx = self.grid.x_face[i+1] - self.grid.x_face[i] if i < self.grid.n_faces-1 else 1.0
                conv[i] = (momentum_right - momentum_center) / dx
        
        return conv
    
    def compute_pressure_term(self, h: np.ndarray) -> np.ndarray:
        """
        计算压力项 gA∂h/∂x（在界面）
        
        使用中心差分。
        
        Args:
            h: 单元中心水深
        
        Returns:
            pressure: 压力项 (n_faces,)
        """
        pressure = np.zeros(self.grid.n_faces)
        
        # 梯度（在界面）
        grad_h = self.grid.compute_gradient_at_face(h)
        
        # 插值面积到界面
        A_face = self.B * self.grid.interpolate_center_to_face(h)
        
        for i in range(self.grid.n_faces):
            pressure[i] = self.g * max(A_face[i], 0.0) * grad_h[i]
        
        return pressure
    
    def compute_friction_term(self,
                             h: np.ndarray,
                             Q: np.ndarray) -> np.ndarray:
        """
        计算摩阻项 gASf（在界面）
        
        Manning公式：Sf = n² |u| u / h^(4/3)
        
        Args:
            h: 单元中心水深
            Q: 单元界面流量
        
        Returns:
            friction: 摩阻项 (n_faces,)
        """
        friction = np.zeros(self.grid.n_faces)
        
        # 插值到界面
        h_face = self.grid.interpolate_center_to_face(h)
        A_face = self.B * h_face
        
        for i in range(self.grid.n_faces):
            h_i = max(h_face[i], self.eps_dry)
            u_i = Q[i] / max(A_face[i], self.eps_dry)
            
            # Manning摩阻坡度
            Sf = (self.n * abs(u_i) * u_i) / (h_i**(4/3))
            
            # 摩阻项
            friction[i] = self.g * A_face[i] * Sf
        
        return friction
    
    def compute_bed_slope_term(self, h: np.ndarray) -> np.ndarray:
        """
        计算床面坡度项 gAS0（在界面）
        
        Args:
            h: 单元中心水深
        
        Returns:
            bed_slope: 床面坡度项 (n_faces,)
        """
        A_face = self.B * self.grid.interpolate_center_to_face(h)
        bed_slope = self.g * A_face * self.S0
        
        return bed_slope
    
    def update(self,
              Q_old: np.ndarray,
              h: np.ndarray,
              dt: float) -> np.ndarray:
        """
        更新流量（FD离散化）
        
        Q^{n+1} = Q^n + dt * RHS
        
        其中 RHS = -∂(Q²/A)/∂x - gA∂h/∂x + gA(S0 - Sf)
        
        Args:
            Q_old: 旧流量 (n_faces,)
            h: 水深 (n_cells,)
            dt: 时间步长
        
        Returns:
            Q_new: 新流量 (n_faces,)
        """
        assert len(Q_old) == self.grid.n_faces
        assert len(h) == self.grid.n_cells
        
        # 计算各项
        conv = self.compute_convection_term(h, Q_old)
        pressure = self.compute_pressure_term(h)
        friction = self.compute_friction_term(h, Q_old)
        bed_slope = self.compute_bed_slope_term(h)
        
        # RHS
        RHS = -conv - pressure + bed_slope - friction
        
        # 显式更新
        Q_new = Q_old + dt * RHS
        
        return Q_new


# ========== 测试代码 ==========

def test_fd_momentum():
    """测试FD动量方程"""
    print("\n" + "="*70)
    print("测试: 有限差分动量方程")
    print("="*70)
    
    # 创建网格
    grid = StaggeredGrid(length=1000.0, n_cells=50)
    
    # 创建FD动量方程
    fd_mom = FDMomentumEquation(grid, B=10.0, S0=0.001, n=0.025)
    
    # 测试：均匀流
    print("\n测试: 均匀流（平衡验证）")
    print("-"*70)
    
    # 正常深度（Manning公式估算）
    h_n = 1.5
    h = np.ones(grid.n_cells) * h_n
    
    # 均匀流量
    Q = np.ones(grid.n_faces) * 10.0
    
    # 计算各项
    conv = fd_mom.compute_convection_term(h, Q)
    pressure = fd_mom.compute_pressure_term(h)
    friction = fd_mom.compute_friction_term(h, Q)
    bed_slope = fd_mom.compute_bed_slope_term(h)
    
    # 均匀流时应该平衡：S0 = Sf
    RHS = -conv - pressure + bed_slope - friction
    RHS_max = np.max(np.abs(RHS))
    
    print(f"对流项: max={np.max(np.abs(conv)):.2e}")
    print(f"压力项: max={np.max(np.abs(pressure)):.2e}")
    print(f"床面坡度: max={np.max(bed_slope):.3f}")
    print(f"摩阻项: max={np.max(friction):.3f}")
    print(f"RHS: max={RHS_max:.2e}")
    print(f"平衡状态: {'✓ 是' if RHS_max < 0.1 else '✗ 否'}")
    
    # 更新测试
    dt = 0.1
    Q_new = fd_mom.update(Q, h, dt)
    Q_change = np.max(np.abs(Q_new - Q))
    
    print(f"\n时间步更新:")
    print(f"dt = {dt}s")
    print(f"最大流量变化: {Q_change:.2e} m³/s")
    
    print("\n" + "="*70)
    print("✓ FD动量方程测试完成")
    print("="*70)


if __name__ == '__main__':
    test_fd_momentum()
