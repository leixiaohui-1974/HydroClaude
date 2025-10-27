#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
间断Galerkin基函数

DG方法的核心：在每个单元内用多项式基函数展开解。

基函数选择：Legendre多项式
- 正交性好
- 数值稳定
- 标准参考单元 ξ ∈ [-1, 1]

阶数：
- P0: 常数（分片常数，等价于FV）
- P1: 线性（二阶精度）
- P2: 二次（三阶精度）
- P3: 三次（四阶精度）
- P4: 四次（五阶精度）

DG解的表示：
    u_h(x, t) = Σ_{j=0}^p u_j(t) * φ_j(ξ(x))

其中：
- u_j(t): 时间相关系数
- φ_j(ξ): Legendre基函数
- ξ(x): 物理坐标到参考坐标的映射

参考：
- Cockburn & Shu (1998) "Runge-Kutta DG"
- Hesthaven & Warburton (2008) "Nodal DG Methods"

Author: Claude (AI Assistant)
Date: 2025-10-27
"""

import numpy as np
from typing import Tuple, List
from scipy.special import legendre
from scipy.integrate import quadrature


class LegendreBasis:
    """
    Legendre多项式基函数
    
    标准Legendre多项式定义在 ξ ∈ [-1, 1]：
    - L_0(ξ) = 1
    - L_1(ξ) = ξ
    - L_2(ξ) = (3ξ² - 1) / 2
    - L_3(ξ) = (5ξ³ - 3ξ) / 2
    - L_4(ξ) = (35ξ⁴ - 30ξ² + 3) / 8
    
    正交性质：
    ∫_{-1}^{1} L_i(ξ) L_j(ξ) dξ = 0  if i ≠ j
                                   = 2/(2i+1)  if i = j
    
    使用示例：
        >>> basis = LegendreBasis(order=3)  # P3（四阶精度）
        >>> xi = np.linspace(-1, 1, 100)
        >>> phi = basis.evaluate(xi)  # shape: (4, 100)
    """
    
    def __init__(self, order: int = 3):
        """
        初始化Legendre基函数
        
        Args:
            order: 多项式阶数（0-4）
                - 0: P0，常数
                - 1: P1，线性
                - 2: P2，二次
                - 3: P3，三次（推荐）
                - 4: P4，四次
        """
        self.order = order
        self.n_basis = order + 1  # 基函数个数
        
        # 预计算Legendre多项式
        self.legendre_polys = [legendre(i) for i in range(self.n_basis)]
        
        # 正交归一化系数
        self.norm_factors = np.array([np.sqrt((2*i + 1) / 2.0) 
                                     for i in range(self.n_basis)])
    
    def evaluate(self, xi: np.ndarray) -> np.ndarray:
        """
        计算基函数值
        
        Args:
            xi: 参考坐标 ∈ [-1, 1]，可以是标量或数组
        
        Returns:
            phi: 基函数值，shape (n_basis, len(xi))
        """
        xi = np.atleast_1d(xi)
        phi = np.zeros((self.n_basis, len(xi)))
        
        for i in range(self.n_basis):
            # 归一化Legendre多项式
            phi[i] = self.norm_factors[i] * self.legendre_polys[i](xi)
        
        return phi
    
    def evaluate_derivative(self, xi: np.ndarray) -> np.ndarray:
        """
        计算基函数导数 dφ/dξ
        
        Legendre多项式导数公式：
        dL_n/dξ = n * L_{n-1} + ξ * dL_{n-1}/dξ
        
        Args:
            xi: 参考坐标
        
        Returns:
            dphi_dxi: 导数值，shape (n_basis, len(xi))
        """
        xi = np.atleast_1d(xi)
        dphi = np.zeros((self.n_basis, len(xi)))
        
        for i in range(self.n_basis):
            # 使用scipy的导数函数
            deriv_poly = self.legendre_polys[i].deriv()
            dphi[i] = self.norm_factors[i] * deriv_poly(xi)
        
        return dphi
    
    def mass_matrix(self) -> np.ndarray:
        """
        计算质量矩阵 M_ij = ∫ φ_i φ_j dξ
        
        对于正交归一化的Legendre基：
        M_ij = δ_ij（单位矩阵）
        
        Returns:
            M: 质量矩阵 (n_basis, n_basis)
        """
        # 正交归一化 → 单位矩阵
        return np.eye(self.n_basis)
    
    def stiffness_matrix(self) -> np.ndarray:
        """
        计算刚度矩阵 K_ij = ∫ φ_i dφ_j/dξ dξ
        
        Returns:
            K: 刚度矩阵 (n_basis, n_basis)
        """
        K = np.zeros((self.n_basis, self.n_basis))
        
        # 数值积分（Gauss-Legendre）
        xi_quad, w_quad = np.polynomial.legendre.leggauss(self.order + 2)
        
        phi = self.evaluate(xi_quad)
        dphi = self.evaluate_derivative(xi_quad)
        
        for i in range(self.n_basis):
            for j in range(self.n_basis):
                integrand = phi[i] * dphi[j]
                K[i, j] = np.sum(w_quad * integrand)
        
        return K


class DGBasisFunctions:
    """
    DG基函数管理器
    
    提供：
    1. 基函数计算
    2. 质量/刚度矩阵
    3. 数值积分（Gauss点和权重）
    4. 坐标变换
    
    使用示例：
        >>> dg_basis = DGBasisFunctions(order=3)
        >>> 
        >>> # 在物理单元 [x_L, x_R] 上计算
        >>> x = np.linspace(x_L, x_R, 10)
        >>> xi = dg_basis.physical_to_reference(x, x_L, x_R)
        >>> phi = dg_basis.basis.evaluate(xi)
    """
    
    def __init__(self, order: int = 3):
        """
        初始化DG基函数
        
        Args:
            order: 多项式阶数（推荐3）
        """
        self.order = order
        self.n_basis = order + 1
        
        # Legendre基
        self.basis = LegendreBasis(order)
        
        # 预计算积分点和权重
        self.xi_quad, self.w_quad = np.polynomial.legendre.leggauss(order + 2)
        
        # 预计算矩阵
        self.M = self.basis.mass_matrix()
        self.K = self.basis.stiffness_matrix()
        self.M_inv = np.linalg.inv(self.M)
    
    @staticmethod
    def physical_to_reference(x: np.ndarray, 
                             x_left: float, 
                             x_right: float) -> np.ndarray:
        """
        物理坐标到参考坐标的映射
        
        x ∈ [x_L, x_R] → ξ ∈ [-1, 1]
        
        ξ = 2 * (x - x_L) / (x_R - x_L) - 1
        
        Args:
            x: 物理坐标
            x_left, x_right: 单元边界
        
        Returns:
            xi: 参考坐标
        """
        dx = x_right - x_left
        xi = 2.0 * (x - x_left) / dx - 1.0
        return xi
    
    @staticmethod
    def reference_to_physical(xi: np.ndarray,
                             x_left: float,
                             x_right: float) -> np.ndarray:
        """
        参考坐标到物理坐标的映射
        
        ξ ∈ [-1, 1] → x ∈ [x_L, x_R]
        
        x = x_L + (x_R - x_L) * (ξ + 1) / 2
        
        Args:
            xi: 参考坐标
            x_left, x_right: 单元边界
        
        Returns:
            x: 物理坐标
        """
        dx = x_right - x_left
        x = x_left + dx * (xi + 1.0) / 2.0
        return x
    
    def project(self, 
                func: callable,
                x_left: float,
                x_right: float) -> np.ndarray:
        """
        将函数投影到DG空间
        
        u_j = (u, φ_j) / (φ_j, φ_j)
        
        使用Gauss积分计算内积。
        
        Args:
            func: 待投影函数 f(x)
            x_left, x_right: 单元边界
        
        Returns:
            coeffs: DG系数 (n_basis,)
        """
        # Gauss积分点（物理坐标）
        x_quad = self.reference_to_physical(self.xi_quad, x_left, x_right)
        
        # 函数值
        f_quad = np.array([func(x) for x in x_quad])
        
        # 基函数值
        phi_quad = self.basis.evaluate(self.xi_quad)
        
        # 计算系数
        coeffs = np.zeros(self.n_basis)
        dx = x_right - x_left
        
        for j in range(self.n_basis):
            # 内积（数值积分）
            integrand = f_quad * phi_quad[j]
            coeffs[j] = 0.5 * dx * np.sum(self.w_quad * integrand)
        
        # 除以质量矩阵（正交归一化时为1）
        coeffs = self.M_inv @ coeffs
        
        return coeffs


# ========== 测试代码 ==========

def test_legendre_basis():
    """测试Legendre基函数"""
    print("\n" + "="*70)
    print("测试: Legendre基函数")
    print("="*70)
    
    # 测试P3基函数
    basis = LegendreBasis(order=3)
    
    print(f"阶数: {basis.order}")
    print(f"基函数个数: {basis.n_basis}")
    
    # 计算基函数值
    xi = np.linspace(-1, 1, 5)
    phi = basis.evaluate(xi)
    
    print(f"\n基函数值 (在5个点):")
    for i in range(basis.n_basis):
        print(f"  φ_{i}: {phi[i]}")
    
    # 正交性验证
    print(f"\n正交性验证:")
    xi_dense = np.linspace(-1, 1, 1000)
    phi_dense = basis.evaluate(xi_dense)
    
    for i in range(basis.n_basis):
        for j in range(i, basis.n_basis):
            # 数值积分
            integrand = phi_dense[i] * phi_dense[j]
            integral = np.trapz(integrand, xi_dense)
            
            expected = 1.0 if i == j else 0.0
            error = abs(integral - expected)
            
            if error < 0.01:
                print(f"  ∫ φ_{i} φ_{j} dξ = {integral:.4f} "
                      f"(期望: {expected:.1f}) ✓")
    
    # 质量矩阵
    M = basis.mass_matrix()
    print(f"\n质量矩阵:")
    print(M)
    print(f"对角化: {'✓ 是' if np.allclose(M, np.eye(basis.n_basis)) else '✗ 否'}")
    
    print("\n" + "="*70)
    print("✓ Legendre基函数测试完成")
    print("="*70)


def test_dg_basis_functions():
    """测试DG基函数管理器"""
    print("\n" + "="*70)
    print("测试: DG基函数管理器")
    print("="*70)
    
    dg_basis = DGBasisFunctions(order=3)
    
    print(f"阶数: {dg_basis.order}")
    print(f"基函数个数: {dg_basis.n_basis}")
    print(f"积分点数: {len(dg_basis.xi_quad)}")
    
    # 测试坐标变换
    print(f"\n坐标变换测试:")
    x_L, x_R = 0.0, 10.0
    x_test = np.array([0.0, 2.5, 5.0, 7.5, 10.0])
    xi_test = dg_basis.physical_to_reference(x_test, x_L, x_R)
    x_back = dg_basis.reference_to_physical(xi_test, x_L, x_R)
    
    print(f"物理坐标: {x_test}")
    print(f"参考坐标: {xi_test}")
    print(f"反变换: {x_back}")
    print(f"误差: {np.max(np.abs(x_test - x_back)):.2e}")
    
    # 测试函数投影
    print(f"\n函数投影测试:")
    
    def test_func(x):
        return np.sin(2 * np.pi * x / 10.0)
    
    coeffs = dg_basis.project(test_func, x_L, x_R)
    print(f"DG系数: {coeffs}")
    
    # 重构函数
    x_eval = np.linspace(x_L, x_R, 50)
    xi_eval = dg_basis.physical_to_reference(x_eval, x_L, x_R)
    phi_eval = dg_basis.basis.evaluate(xi_eval)
    
    f_reconstructed = coeffs @ phi_eval
    f_exact = np.array([test_func(x) for x in x_eval])
    
    error = np.max(np.abs(f_reconstructed - f_exact))
    print(f"重构误差: {error:.2e}")
    print(f"判定: {'✓ 精确' if error < 0.01 else '⚠ 误差较大'}")
    
    print("\n" + "="*70)
    print("✓ DG基函数管理器测试完成")
    print("="*70)


if __name__ == '__main__':
    test_legendre_basis()
    test_dg_basis_functions()
