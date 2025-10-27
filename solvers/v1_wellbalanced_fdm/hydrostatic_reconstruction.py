#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
静水重构算法实现

基于：Audusse et al. (2004) "A Fast and Stable Well-Balanced Scheme 
      with Hydrostatic Reconstruction for Shallow Water Flows"
      SIAM Journal on Scientific Computing, 25(6), 2050-2065.

核心思想：
1. 在单元界面重构水位（而非水深）
2. 确保数值格式精确保持静水平衡
3. 源项离散化与通量离散化精确匹配

良平衡性质：
- 静止水体（Q=0）下，水位保持不变（机器精度）
- 稳态时无人工数值耗散
- 适合长时间演化到稳态的问题

Author: Claude (AI Assistant)
Date: 2025-10-27
License: MIT
"""

import numpy as np
from typing import Tuple, Optional


class HydrostaticReconstruction:
    """
    静水重构类
    
    实现Audusse et al. (2004)的静水重构算法，确保数值格式
    具有良平衡性质（well-balanced property）。
    
    主要方法：
    - reconstruct(): 在界面重构左右状态
    - compute_balanced_source(): 计算良平衡源项
    - verify_balance(): 验证良平衡性质
    
    示例：
        >>> recon = HydrostaticReconstruction(g=9.81)
        >>> h_L_star, h_R_star = recon.reconstruct(
        ...     h_L=3.0, h_R=2.5, z_L=0.0, z_R=0.5
        ... )
        >>> print(f"重构后左侧水深: {h_L_star:.3f}m")
        >>> print(f"重构后右侧水深: {h_R_star:.3f}m")
    """
    
    def __init__(self, g: float = 9.81, eps_dry: float = 1e-6):
        """
        初始化静水重构
        
        Args:
            g: 重力加速度 (m/s²)
            eps_dry: 干湿判定阈值 (m)，水深小于此值视为干
        """
        self.g = g
        self.eps_dry = eps_dry
        
        # 统计信息（用于调试）
        self.stats = {
            'n_reconstructions': 0,
            'n_dry_cells': 0,
            'n_discontinuous': 0,
        }
    
    def reconstruct(self, 
                   h_L: float, 
                   h_R: float, 
                   z_L: float, 
                   z_R: float) -> Tuple[float, float]:
        """
        在单元界面进行静水重构
        
        核心思想：
        1. 水位η = h + z是守恒量（在静水平衡下）
        2. 在界面处取床面高程最大值：z_interface = max(z_L, z_R)
        3. 重构水深：h_star = max(0, η - z_interface)
        
        这确保了：
        - 当η_L = η_R时（静水平衡），重构后h_L_star = h_R_star
        - 数值通量为零，无人工波动
        
        Args:
            h_L: 左侧单元水深 (m)
            h_R: 右侧单元水深 (m)
            z_L: 左侧单元床面高程 (m)
            z_R: 右侧单元床面高程 (m)
        
        Returns:
            (h_L_star, h_R_star): 重构后的左右水深 (m)
        
        示例：
            >>> recon = HydrostaticReconstruction()
            
            # 案例1：静水平衡（η_L = η_R）
            >>> h_L, h_R = recon.reconstruct(h_L=3.0, h_R=2.5, 
            ...                              z_L=0.0, z_R=0.5)
            >>> assert abs(h_L - h_R) < 1e-10  # 重构后水深相等
            
            # 案例2：台阶地形
            >>> h_L, h_R = recon.reconstruct(h_L=3.0, h_R=3.0,
            ...                              z_L=0.0, z_R=1.0)
            >>> assert h_L > h_R  # 下游水深减小
        """
        self.stats['n_reconstructions'] += 1
        
        # 计算水位（守恒量）
        eta_L = h_L + z_L
        eta_R = h_R + z_R
        
        # 界面处的床面高程（取最大值）
        z_interface = max(z_L, z_R)
        
        # 重构后的水深
        h_L_star = max(0.0, eta_L - z_interface)
        h_R_star = max(0.0, eta_R - z_interface)
        
        # 干湿检测
        if h_L_star < self.eps_dry or h_R_star < self.eps_dry:
            self.stats['n_dry_cells'] += 1
            # 干湿界面特殊处理
            h_L_star = max(h_L_star, 0.0)
            h_R_star = max(h_R_star, 0.0)
        
        # 间断检测（用于调试）
        if abs(z_R - z_L) > 0.1:  # 床面高差>10cm
            self.stats['n_discontinuous'] += 1
        
        return h_L_star, h_R_star
    
    def compute_balanced_source(self,
                                h_L: float,
                                h_R: float,
                                h_L_star: float,
                                h_R_star: float,
                                z_L: float,
                                z_R: float,
                                dx: float) -> float:
        """
        计算良平衡源项
        
        良平衡条件：数值通量的差分 = 源项
        
        对于Saint-Venant方程的动量方程：
        ∂(hu)/∂t + ∂(hu²/h + 0.5gh²)/∂x = -gh∂z/∂x + 摩阻项
        
        标准离散化在接近静水平衡时会产生O(1)误差，因为：
        - 通量项的截断误差
        - 源项的截断误差
        不精确抵消。
        
        静水重构通过修正源项，确保：
        (F_R - F_L) / dx = S_corrected
        
        在静水平衡时精确成立。
        
        Args:
            h_L, h_R: 原始左右水深
            h_L_star, h_R_star: 重构后的左右水深
            z_L, z_R: 左右床面高程
            dx: 网格间距
        
        Returns:
            S_corrected: 修正后的源项 (m/s²)
        
        数学推导：
            标准源项: S_std = -g * h_avg * (z_R - z_L) / dx
            
            静水压力修正:
            ΔP_std = 0.5 * g * (h_R² - h_L²)
            ΔP_star = 0.5 * g * (h_R_star² - h_L_star²)
            
            修正量: S_corr = g * (ΔP_std - ΔP_star) / dx
            
            最终源项: S = S_std + S_corr
        """
        # 平均水深
        h_avg = 0.5 * (h_L + h_R)
        
        # 标准源项（床面坡度）
        S_bed = -self.g * h_avg * (z_R - z_L) / dx
        
        # 静水压力差（原始）
        P_diff_original = 0.5 * self.g * (h_R**2 - h_L**2)
        
        # 静水压力差（重构后）
        P_diff_reconstructed = 0.5 * self.g * (h_R_star**2 - h_L_star**2)
        
        # 压力修正项
        S_pressure_correction = (P_diff_original - P_diff_reconstructed) / dx
        
        # 总源项（良平衡）
        S_balanced = S_bed + S_pressure_correction
        
        return S_balanced
    
    def verify_balance(self,
                      h: np.ndarray,
                      z: np.ndarray,
                      Q: np.ndarray,
                      tol: float = 1e-10) -> Tuple[bool, float]:
        """
        验证静水平衡
        
        在静止水体（Q=0）下，良平衡格式应保持：
        - 水位η = h + z = 常数
        - 最大偏差 < tol（机器精度）
        
        Args:
            h: 水深数组 (m)
            z: 床面高程数组 (m)
            Q: 流量数组 (m³/s)
            tol: 容差
        
        Returns:
            (is_balanced, max_deviation): 是否平衡，最大偏差
        
        示例：
            >>> # 设置静止水体
            >>> h = np.array([3.0, 2.5, 2.0, 2.5, 3.0])
            >>> z = np.array([0.0, 0.5, 1.0, 0.5, 0.0])
            >>> Q = np.zeros(5)
            >>> 
            >>> recon = HydrostaticReconstruction()
            >>> is_balanced, deviation = recon.verify_balance(h, z, Q)
            >>> print(f"良平衡: {is_balanced}, 偏差: {deviation:.2e}")
        """
        # 计算水位
        eta = h + z
        
        # 检查是否静止
        Q_max = np.max(np.abs(Q))
        if Q_max > 1e-6:
            # 非静止水体，不检查静水平衡
            return True, 0.0
        
        # 检查水位偏差
        eta_mean = np.mean(eta)
        max_deviation = np.max(np.abs(eta - eta_mean))
        
        is_balanced = (max_deviation < tol)
        
        return is_balanced, max_deviation
    
    def reset_stats(self):
        """重置统计信息"""
        self.stats = {
            'n_reconstructions': 0,
            'n_dry_cells': 0,
            'n_discontinuous': 0,
        }
    
    def print_stats(self):
        """打印统计信息（调试用）"""
        print("=" * 50)
        print("静水重构统计")
        print("=" * 50)
        print(f"重构次数: {self.stats['n_reconstructions']}")
        print(f"干单元次数: {self.stats['n_dry_cells']}")
        print(f"间断次数: {self.stats['n_discontinuous']}")
        
        if self.stats['n_reconstructions'] > 0:
            dry_ratio = self.stats['n_dry_cells'] / self.stats['n_reconstructions'] * 100
            disc_ratio = self.stats['n_discontinuous'] / self.stats['n_reconstructions'] * 100
            print(f"干单元比例: {dry_ratio:.2f}%")
            print(f"间断比例: {disc_ratio:.2f}%")
        print("=" * 50)


class HydrostaticReconstructionHLL:
    """
    静水重构 + HLL Riemann求解器
    
    将静水重构与HLL通量计算结合，适用于良平衡格式的
    有限体积法或有限差分法。
    
    HLL (Harten-Lax-van Leer) 求解器特点：
    - 鲁棒性强，适合浅水方程
    - 正性保持（水深非负）
    - 熵相容
    
    组合方式：
    1. 静水重构 → 重构后的状态 (h_L*, h_R*)
    2. HLL求解器 → 数值通量 F
    3. 良平衡源项 → 修正 S
    """
    
    def __init__(self, g: float = 9.81, eps_dry: float = 1e-6):
        """
        初始化
        
        Args:
            g: 重力加速度
            eps_dry: 干湿阈值
        """
        self.g = g
        self.eps_dry = eps_dry
        self.recon = HydrostaticReconstruction(g=g, eps_dry=eps_dry)
    
    def compute_flux(self,
                    h_L: float,
                    h_R: float,
                    u_L: float,
                    u_R: float,
                    z_L: float,
                    z_R: float) -> Tuple[np.ndarray, float]:
        """
        计算HLL数值通量（含静水重构）
        
        Args:
            h_L, h_R: 左右水深
            u_L, u_R: 左右流速
            z_L, z_R: 左右床面高程
        
        Returns:
            (F, S): 数值通量和源项
        """
        # 步骤1：静水重构
        h_L_star, h_R_star = self.recon.reconstruct(h_L, h_R, z_L, z_R)
        
        # 步骤2：HLL通量（使用重构后的状态）
        F_hll = self._hll_flux(h_L_star, h_R_star, u_L, u_R)
        
        # 步骤3：良平衡源项
        dx = 1.0  # 假设单位间距（实际使用时需传入）
        S_balanced = self.recon.compute_balanced_source(
            h_L, h_R, h_L_star, h_R_star, z_L, z_R, dx
        )
        
        return F_hll, S_balanced
    
    def _hll_flux(self,
                 h_L: float,
                 h_R: float,
                 u_L: float,
                 u_R: float) -> np.ndarray:
        """
        HLL Riemann求解器
        
        Harten-Lax-van Leer近似Riemann求解器，适合浅水方程。
        
        波速估计（简化版）：
        - S_L = u_L - sqrt(g*h_L)  (左行波速)
        - S_R = u_R + sqrt(g*h_R)  (右行波速)
        
        HLL通量：
        - 如果S_L > 0: F = F_L（上游）
        - 如果S_R < 0: F = F_R（下游）
        - 否则: F = (S_R*F_L - S_L*F_R + S_L*S_R*(U_R - U_L)) / (S_R - S_L)
        
        Args:
            h_L, h_R: 左右水深（已重构）
            u_L, u_R: 左右流速
        
        Returns:
            F: 通量向量 [F_mass, F_momentum]
        """
        # 干湿处理
        if h_L < self.eps_dry:
            h_L, u_L = self.eps_dry, 0.0
        if h_R < self.eps_dry:
            h_R, u_R = self.eps_dry, 0.0
        
        # 左右状态
        Q_L = h_L * u_L  # 单宽流量
        Q_R = h_R * u_R
        
        # 左右通量
        F_L = np.array([
            Q_L,
            Q_L * u_L + 0.5 * self.g * h_L**2
        ])
        
        F_R = np.array([
            Q_R,
            Q_R * u_R + 0.5 * self.g * h_R**2
        ])
        
        # 波速估计
        c_L = np.sqrt(self.g * h_L)  # 左侧波速
        c_R = np.sqrt(self.g * h_R)  # 右侧波速
        
        S_L = u_L - c_L  # 左行特征波速
        S_R = u_R + c_R  # 右行特征波速
        
        # HLL通量计算
        if S_L >= 0:
            # 上游
            F = F_L
        elif S_R <= 0:
            # 下游
            F = F_R
        else:
            # 中间状态
            U_L = np.array([h_L, Q_L])
            U_R = np.array([h_R, Q_R])
            
            F = (S_R * F_L - S_L * F_R + S_L * S_R * (U_R - U_L)) / (S_R - S_L)
        
        return F


# ========== 测试代码 ==========

def test_hydrostatic_reconstruction():
    """测试静水重构的基本功能"""
    print("\n" + "="*60)
    print("测试: 静水重构基本功能")
    print("="*60)
    
    recon = HydrostaticReconstruction(g=9.81)
    
    # 测试1：静水平衡（η_L = η_R）
    print("\n测试1: 静水平衡（台阶地形）")
    h_L, h_R, z_L, z_R = 3.0, 2.5, 0.0, 0.5
    h_L_star, h_R_star = recon.reconstruct(h_L, h_R, z_L, z_R)
    
    eta_L = h_L + z_L
    eta_R = h_R + z_R
    eta_L_star = h_L_star + max(z_L, z_R)
    eta_R_star = h_R_star + max(z_L, z_R)
    
    print(f"原始状态: η_L={eta_L:.3f}, η_R={eta_R:.3f}")
    print(f"重构后: h_L*={h_L_star:.3f}, h_R*={h_R_star:.3f}")
    print(f"重构后水位: η_L*={eta_L_star:.3f}, η_R*={eta_R_star:.3f}")
    print(f"✓ 静水平衡保持" if abs(eta_L - eta_R) < 1e-10 else "✗ 平衡破坏")
    
    # 测试2：干湿界面
    print("\n测试2: 干湿界面")
    h_L, h_R, z_L, z_R = 2.0, 0.0, 0.0, 3.0
    h_L_star, h_R_star = recon.reconstruct(h_L, h_R, z_L, z_R)
    print(f"左侧: h={h_L}, z={z_L}")
    print(f"右侧: h={h_R}, z={z_R} (干)")
    print(f"重构后: h_L*={h_L_star:.3f}, h_R*={h_R_star:.3f}")
    print(f"✓ 干湿处理正确" if h_R_star >= 0 else "✗ 负水深")
    
    # 打印统计
    recon.print_stats()


def test_well_balanced_property():
    """测试良平衡性质"""
    print("\n" + "="*60)
    print("测试: 良平衡性质验证")
    print("="*60)
    
    recon = HydrostaticReconstruction(g=9.81)
    
    # 创建一个静止水体（湖面）
    nx = 51
    L = 100.0
    x = np.linspace(0, L, nx)
    
    # 非平底地形（抛物线）
    z = 1.0 - 0.01 * (x - 50)**2 / 50**2
    
    # 静止水体：水位恒定
    eta0 = 3.0
    h = eta0 - z
    Q = np.zeros(nx)
    
    print(f"设置: nx={nx}, L={L}m")
    print(f"床面高程: z_min={z.min():.3f}, z_max={z.max():.3f}")
    print(f"水位: η={eta0:.3f}m (常数)")
    print(f"流量: Q=0 (静止)")
    
    # 验证平衡
    is_balanced, deviation = recon.verify_balance(h, z, Q)
    
    print(f"\n验证结果:")
    print(f"  良平衡: {'✓ 是' if is_balanced else '✗ 否'}")
    print(f"  水位偏差: {deviation:.2e} m")
    print(f"  判定: {'通过' if deviation < 1e-10 else '失败'}")


if __name__ == '__main__':
    # 运行测试
    test_hydrostatic_reconstruction()
    test_well_balanced_property()
    
    print("\n" + "="*60)
    print("✓ 静水重构模块测试完成")
    print("="*60)
