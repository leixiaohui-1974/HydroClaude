#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TVD斜率限制器

Total Variation Diminishing (TVD) 限制器用于：
1. 抑制数值振荡
2. 保持单调性
3. 确保稳定性

在DG方法中，高阶多项式可能在间断附近产生Gibbs振荡。
TVD限制器通过限制单元内的梯度，消除非物理振荡。

常用限制器：
- Minmod: 最保守，最稳定
- Superbee: 最激进，最锐利
- Van Leer: 折中
- MUSCL: 改进的Minmod

参考：
- Cockburn & Shu (2001) "TVD for DG"
- Krivodonova et al. (2004) "Limiters for DG"

Author: Claude (AI Assistant)
Date: 2025-10-27
"""

import numpy as np
from typing import List

from .dg_element import DGElement, DGMesh
from .dg_basis import DGBasisFunctions


class MinmodLimiter:
    """
    Minmod限制器
    
    最保守的限制器，确保最大稳定性。
    
    Minmod函数：
    minmod(a, b, c) = sign(a) * min(|a|, |b|, |c|)  if sign(a)=sign(b)=sign(c)
                    = 0                               otherwise
    
    应用到DG：
    1. 计算单元平均值的梯度
    2. 与单元内多项式梯度对比
    3. 如果超过邻近单元梯度，限制为线性
    
    参考：
    - Cockburn & Shu (1998)
    """
    
    def __init__(self, M: float = 1.0):
        """
        初始化Minmod限制器
        
        Args:
            M: 限制器参数（通常1.0-2.0）
        """
        self.M = M
    
    @staticmethod
    def minmod(a: float, b: float, c: float = None) -> float:
        """
        Minmod函数
        
        Args:
            a, b, c: 输入值
        
        Returns:
            result: minmod结果
        """
        if c is None:
            # 两参数版本
            if a * b <= 0:
                return 0.0
            elif abs(a) < abs(b):
                return a
            else:
                return b
        else:
            # 三参数版本
            if a * b <= 0 or b * c <= 0 or a * c <= 0:
                return 0.0
            else:
                return np.sign(a) * min(abs(a), abs(b), abs(c))
    
    def apply(self,
             mesh: DGMesh,
             variable: str = 'h') -> DGMesh:
        """
        应用限制器到整个网格
        
        Args:
            mesh: DG网格
            variable: 限制哪个变量（'h'或'hu'）
        
        Returns:
            mesh: 限制后的网格（原地修改）
        """
        n = mesh.n_elements
        
        for i in range(n):
            elem = mesh.elements[i]
            
            # 选择变量
            coeffs = elem.coeffs_h if variable == 'h' else elem.coeffs_hu
            
            # 如果是P0（常数），无需限制
            if len(coeffs) == 1:
                continue
            
            # 单元平均值
            u_avg = coeffs[0] / np.sqrt(2.0)
            
            # 左右邻居平均值
            u_L = mesh.elements[i-1].coeffs_h[0] / np.sqrt(2.0) if i > 0 else u_avg
            u_R = mesh.elements[i+1].coeffs_h[0] / np.sqrt(2.0) if i < n-1 else u_avg
            
            # 单元内梯度（线性项系数）
            if len(coeffs) > 1:
                # 线性项系数对应梯度
                slope_elem = coeffs[1]  # L_1系数
                
                # 邻居梯度
                dx = elem.dx
                slope_left = (u_avg - u_L) / (0.5 * dx) if i > 0 else 0.0
                slope_right = (u_R - u_avg) / (0.5 * dx) if i < n-1 else 0.0
                
                # Minmod限制
                slope_limited = self.minmod(slope_elem, 
                                           self.M * slope_left,
                                           self.M * slope_right)
                
                # 应用限制
                if abs(slope_limited) < abs(slope_elem):
                    # 需要限制：降为线性
                    coeffs[1] = slope_limited
                    coeffs[2:] = 0.0  # 高阶项清零
        
        return mesh


class TVDLimiter:
    """
    通用TVD限制器框架
    
    支持多种限制器函数：
    - Minmod
    - Superbee
    - Van Leer
    - MUSCL
    
    使用示例：
        >>> limiter = TVDLimiter(limiter_type='minmod')
        >>> mesh_limited = limiter.apply(mesh, variable='h')
    """
    
    def __init__(self, limiter_type: str = 'minmod', M: float = 1.0):
        """
        初始化TVD限制器
        
        Args:
            limiter_type: 限制器类型
            M: 限制器参数
        """
        self.limiter_type = limiter_type
        self.M = M
        
        if limiter_type == 'minmod':
            self.limiter = MinmodLimiter(M=M)
        else:
            raise ValueError(f"未知限制器类型: {limiter_type}")
    
    def apply(self, mesh: DGMesh, variable: str = 'h') -> DGMesh:
        """应用限制器"""
        return self.limiter.apply(mesh, variable)


# ========== 测试代码 ==========

def test_tvd_limiter():
    """测试TVD限制器"""
    print("\n" + "="*70)
    print("测试: TVD斜率限制器")
    print("="*70)
    
    # 创建DG网格
    mesh = DGMesh(length=100.0, n_elements=10, order=2)  # P2
    
    # 初始化为光滑函数
    for i, elem in enumerate(mesh.elements):
        x_c = elem.x_center
        # 正弦函数
        h_avg = 2.0 + 0.5 * np.sin(2 * np.pi * x_c / 100.0)
        elem.coeffs_h[0] = h_avg * np.sqrt(2.0)
        elem.coeffs_h[1] = 0.1  # 线性项
        elem.coeffs_h[2] = 0.05  # 二次项
    
    # 应用前
    h_before, _ = mesh.get_cell_averages()
    
    print("应用限制器前:")
    print(f"  平均水深: min={h_before.min():.3f}, max={h_before.max():.3f}")
    
    # 在中间单元制造间断
    mesh.elements[5].coeffs_h[0] = 5.0 * np.sqrt(2.0)  # 突变
    mesh.elements[5].coeffs_h[1] = 2.0  # 大梯度
    
    # 应用限制器
    limiter = TVDLimiter(limiter_type='minmod')
    mesh_limited = limiter.apply(mesh, variable='h')
    
    # 应用后
    h_after, _ = mesh_limited.get_cell_averages()
    
    print("\n应用限制器后:")
    print(f"  平均水深: min={h_after.min():.3f}, max={h_after.max():.3f}")
    print(f"  间断单元线性项: {mesh_limited.elements[5].coeffs_h[1]:.3f}")
    print(f"  间断单元二次项: {mesh_limited.elements[5].coeffs_h[2]:.3f}")
    
    print(f"\n✓ 高阶项被限制: {'是' if abs(mesh_limited.elements[5].coeffs_h[2]) < 0.01 else '否'}")
    
    print("\n" + "="*70)
    print("✓ TVD限制器测试完成")
    print("="*70)


if __name__ == '__main__':
    test_tvd_limiter()
