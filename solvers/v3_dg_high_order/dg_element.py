#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
DG单元和网格

DG单元：
- 存储单元的DG系数
- 提供单元内的函数值计算
- 计算单元积分

DG网格：
- 管理所有DG单元
- 处理单元间通讯
- 结构物定位

Author: Claude (AI Assistant)  
Date: 2025-10-27
"""

import numpy as np
from typing import List, Optional, Tuple
from dataclasses import dataclass

from .dg_basis import DGBasisFunctions


@dataclass
class DGElement:
    """
    DG单元
    
    每个单元存储：
    - 几何信息（边界、尺寸）
    - DG系数（u_h的展开系数）
    - 床面高程
    
    单元内解的表示：
    u_h(x) = Σ u_j * φ_j(ξ(x))
    """
    x_left: float  # 左边界
    x_right: float  # 右边界
    coeffs_h: np.ndarray  # 水深的DG系数
    coeffs_hu: np.ndarray  # 动量的DG系数
    z_bed: float  # 床面高程（单元平均）
    
    @property
    def dx(self):
        """单元尺寸"""
        return self.x_right - self.x_left
    
    @property
    def x_center(self):
        """单元中心"""
        return 0.5 * (self.x_left + self.x_right)
    
    def evaluate_at(self, 
                   x: np.ndarray,
                   dg_basis: DGBasisFunctions) -> Tuple[np.ndarray, np.ndarray]:
        """
        在点x处计算解值
        
        Args:
            x: 物理坐标
            dg_basis: DG基函数
        
        Returns:
            (h, hu): 水深和动量
        """
        # 物理到参考坐标
        xi = dg_basis.physical_to_reference(x, self.x_left, self.x_right)
        
        # 计算基函数
        phi = dg_basis.basis.evaluate(xi)
        
        # 重构解
        h = self.coeffs_h @ phi
        hu = self.coeffs_hu @ phi
        
        return h, hu
    
    def get_boundary_values(self, 
                           dg_basis: DGBasisFunctions) -> Tuple[Tuple, Tuple]:
        """
        获取单元边界值
        
        左边界：ξ = -1
        右边界：ξ = +1
        
        Args:
            dg_basis: DG基函数
        
        Returns:
            ((h_L, hu_L), (h_R, hu_R)): 左右边界值
        """
        # 边界的基函数值
        phi_left = dg_basis.basis.evaluate(np.array([-1.0]))[:, 0]
        phi_right = dg_basis.basis.evaluate(np.array([1.0]))[:, 0]
        
        # 左边界
        h_L = self.coeffs_h @ phi_left
        hu_L = self.coeffs_hu @ phi_left
        
        # 右边界
        h_R = self.coeffs_h @ phi_right
        hu_R = self.coeffs_hu @ phi_right
        
        return (h_L, hu_L), (h_R, hu_R)
    
    def compute_cell_average(self) -> Tuple[float, float]:
        """
        计算单元平均值
        
        对于正交归一化的Legendre基：
        ū = u_0 / sqrt(2)
        
        Returns:
            (h_avg, hu_avg): 平均水深和动量
        """
        # L_0的归一化系数是 sqrt(1/2)
        h_avg = self.coeffs_h[0] / np.sqrt(2.0)
        hu_avg = self.coeffs_hu[0] / np.sqrt(2.0)
        
        return h_avg, hu_avg


class DGMesh:
    """
    DG网格
    
    管理所有DG单元，提供：
    1. 单元访问
    2. 全局数据结构
    3. 结构物映射
    4. 边界条件
    
    使用示例：
        >>> mesh = DGMesh(length=10000.0, n_elements=100, order=3)
        >>> mesh.initialize_uniform_flow(h0=2.0, Q0=10.0)
        >>> 
        >>> # 访问单元
        >>> elem = mesh.elements[50]
        >>> h, hu = elem.get_boundary_values(mesh.dg_basis)
    """
    
    def __init__(self,
                 length: float = 10000.0,
                 n_elements: int = 100,
                 order: int = 3,
                 B: float = 10.0,
                 S0: float = 0.001):
        """
        初始化DG网格
        
        Args:
            length: 渠道长度
            n_elements: 单元数
            order: DG阶数
            B: 渠道宽度
            S0: 渠底坡度
        """
        self.length = length
        self.n_elements = n_elements
        self.order = order
        self.B = B
        self.S0 = S0
        
        # DG基函数
        self.dg_basis = DGBasisFunctions(order)
        
        # 创建单元
        self._create_elements()
    
    def _create_elements(self):
        """创建均匀DG单元"""
        dx = self.length / self.n_elements
        
        self.elements: List[DGElement] = []
        
        for i in range(self.n_elements):
            x_left = i * dx
            x_right = (i + 1) * dx
            x_center = 0.5 * (x_left + x_right)
            
            # 床面高程
            z_bed = (self.length - x_center) * self.S0
            
            # 初始化系数（零）
            coeffs_h = np.zeros(self.dg_basis.n_basis)
            coeffs_hu = np.zeros(self.dg_basis.n_basis)
            
            elem = DGElement(
                x_left=x_left,
                x_right=x_right,
                coeffs_h=coeffs_h,
                coeffs_hu=coeffs_hu,
                z_bed=z_bed
            )
            
            self.elements.append(elem)
    
    def initialize_uniform_flow(self, h0: float, Q0: float):
        """
        初始化为均匀流
        
        Args:
            h0: 初始水深
            Q0: 初始流量
        """
        hu0 = Q0 / self.B
        
        for elem in self.elements:
            # L_0基函数的系数
            elem.coeffs_h[0] = h0 * np.sqrt(2.0)
            elem.coeffs_hu[0] = hu0 * np.sqrt(2.0)
    
    def get_cell_averages(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        获取所有单元的平均值
        
        Returns:
            (h_avg, hu_avg): 单元平均数组
        """
        h_avg = np.zeros(self.n_elements)
        hu_avg = np.zeros(self.n_elements)
        
        for i, elem in enumerate(self.elements):
            h_avg[i], hu_avg[i] = elem.compute_cell_average()
        
        return h_avg, hu_avg
    
    def print_info(self):
        """打印网格信息"""
        print("="*60)
        print("DG网格信息")
        print("="*60)
        print(f"渠道长度: {self.length:.1f} m")
        print(f"单元数: {self.n_elements}")
        print(f"DG阶数: P{self.order} (空间精度: {self.order+1}阶)")
        print(f"每单元自由度: {self.dg_basis.n_basis}")
        print(f"总自由度: {self.n_elements * self.dg_basis.n_basis}")
        
        dx = self.elements[0].dx
        print(f"单元尺寸: {dx:.2f} m")
        print("="*60)


# ========== 测试代码 ==========

def test_dg_element():
    """测试DG单元"""
    print("\n" + "="*70)
    print("测试: DG单元")
    print("="*70)
    
    dg_basis = DGBasisFunctions(order=2)  # P2
    
    # 创建单元
    elem = DGElement(
        x_left=0.0,
        x_right=10.0,
        coeffs_h=np.array([2.0, 0.1, -0.05]) * np.sqrt(2.0),  # 带扰动
        coeffs_hu=np.array([1.0, 0.0, 0.0]) * np.sqrt(2.0),
        z_bed=1.0
    )
    
    print(f"单元: [{elem.x_left}, {elem.x_right}]")
    print(f"中心: {elem.x_center}")
    print(f"尺寸: {elem.dx}")
    
    # 边界值
    (h_L, hu_L), (h_R, hu_R) = elem.get_boundary_values(dg_basis)
    print(f"\n边界值:")
    print(f"  左: h={h_L:.3f}, hu={hu_L:.3f}")
    print(f"  右: h={h_R:.3f}, hu={hu_R:.3f}")
    
    # 平均值
    h_avg, hu_avg = elem.compute_cell_average()
    print(f"\n单元平均:")
    print(f"  h_avg={h_avg:.3f}, hu_avg={hu_avg:.3f}")
    
    print("\n" + "="*70)
    print("✓ DG单元测试完成")
    print("="*70)


def test_dg_mesh():
    """测试DG网格"""
    print("\n" + "="*70)
    print("测试: DG网格")
    print("="*70)
    
    mesh = DGMesh(length=1000.0, n_elements=10, order=3)
    mesh.print_info()
    
    # 初始化
    mesh.initialize_uniform_flow(h0=2.0, Q0=10.0)
    
    # 获取平均值
    h_avg, hu_avg = mesh.get_cell_averages()
    
    print(f"\n初始化后:")
    print(f"平均水深: {h_avg[0]:.3f} m")
    print(f"平均动量: {hu_avg[0]:.3f} m²/s")
    print(f"所有单元一致: {'✓ 是' if np.std(h_avg) < 1e-10 else '✗ 否'}")
    
    print("\n" + "="*70)
    print("✓ DG网格测试完成")
    print("="*70)


if __name__ == '__main__':
    test_dg_element()
    test_dg_mesh()
