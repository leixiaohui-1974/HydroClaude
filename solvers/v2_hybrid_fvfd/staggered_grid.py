#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
交错网格管理系统

交错网格（Staggered Grid）是处理对流-扩散问题的标准方法，
特别适合浅水方程这类双曲型守恒律。

网格布局：
```
    h[0]       h[1]       h[2]       h[3]       h[4]
     o----------o----------o----------o----------o      单元中心（h, A）
     |    c[0]  |    c[1]  |    c[2]  |    c[3]  |      控制体积
    Q[0]      Q[1]      Q[2]      Q[3]      Q[4]       单元界面（Q, u）
```

变量位置：
- h（水深）: 单元中心（cell center）
- Q（流量）: 单元界面（cell face/interface）
- A（面积）: 单元中心
- u（流速）: 单元界面

优势：
1. 自然满足质量守恒（FV连续性方程）
2. 避免压力振荡（checkerboard oscillation）
3. 适合处理间断（结构物、激波）
4. 与商业软件（MIKE 11）一致

参考：
- Stelling & Duinmeijer (2003) "Numerical Simulation of 3D Quasi-Hydrostatic, 
  Free-Surface Flows", JHE
- Casulli & Stelling (2011) "Semi-implicit subgrid modelling"

Author: Claude (AI Assistant)
Date: 2025-10-27
"""

import numpy as np
from typing import Tuple, Optional, List
from enum import Enum
from dataclasses import dataclass


class GridType(Enum):
    """网格类型"""
    UNIFORM = "uniform"      # 均匀网格
    NONUNIFORM = "nonuniform"  # 非均匀网格
    ADAPTIVE = "adaptive"    # 自适应网格（预留）


@dataclass
class GridMetrics:
    """网格度量信息"""
    # 单元中心
    x_center: np.ndarray  # 单元中心位置
    dx_center: np.ndarray  # 单元尺寸
    
    # 单元界面
    x_face: np.ndarray     # 界面位置
    dx_face: np.ndarray    # 界面间距
    
    # 网格信息
    n_cells: int           # 单元数
    n_faces: int           # 界面数
    grid_type: GridType    # 网格类型
    
    def __repr__(self):
        return (f"GridMetrics(n_cells={self.n_cells}, n_faces={self.n_faces}, "
                f"type={self.grid_type.value})")


class StaggeredGrid:
    """
    交错网格管理器
    
    负责：
    1. 网格生成（均匀/非均匀）
    2. 变量定位（中心/界面）
    3. 插值操作（中心↔界面）
    4. 梯度计算
    5. 结构物位置映射
    
    使用示例：
        >>> grid = StaggeredGrid(length=10000.0, n_cells=100)
        >>> 
        >>> # 初始化变量
        >>> h = np.ones(grid.n_cells) * 2.0  # 单元中心
        >>> Q = np.ones(grid.n_faces) * 10.0  # 单元界面
        >>> 
        >>> # 插值
        >>> h_at_faces = grid.interpolate_center_to_face(h)
        >>> Q_at_centers = grid.interpolate_face_to_center(Q)
    """
    
    def __init__(self,
                 length: float = 10000.0,
                 n_cells: int = 100,
                 x_centers: Optional[np.ndarray] = None):
        """
        初始化交错网格
        
        Args:
            length: 渠道长度 (m)
            n_cells: 单元数（单元中心数）
            x_centers: 自定义单元中心位置（可选，用于非均匀网格）
        """
        self.length = length
        self.n_cells = n_cells
        self.n_faces = n_cells + 1  # 界面数 = 单元数 + 1
        
        if x_centers is not None:
            # 非均匀网格
            self._setup_nonuniform_grid(x_centers)
        else:
            # 均匀网格
            self._setup_uniform_grid()
        
        # 计算度量信息
        self.metrics = self._compute_metrics()
    
    def _setup_uniform_grid(self):
        """设置均匀网格"""
        # 单元尺寸
        dx = self.length / self.n_cells
        
        # 单元中心位置
        self.x_center = np.linspace(dx/2, self.length - dx/2, self.n_cells)
        self.dx_center = np.ones(self.n_cells) * dx
        
        # 单元界面位置
        self.x_face = np.linspace(0, self.length, self.n_faces)
        self.dx_face = np.ones(self.n_faces - 1) * dx
        
        self.grid_type = GridType.UNIFORM
    
    def _setup_nonuniform_grid(self, x_centers: np.ndarray):
        """设置非均匀网格"""
        self.x_center = x_centers
        self.n_cells = len(x_centers)
        self.n_faces = self.n_cells + 1
        
        # 计算单元界面位置（中点）
        self.x_face = np.zeros(self.n_faces)
        self.x_face[0] = 0.0  # 左边界
        self.x_face[-1] = self.length  # 右边界
        
        # 内部界面：相邻单元中心的中点
        for i in range(1, self.n_faces - 1):
            self.x_face[i] = 0.5 * (self.x_center[i-1] + self.x_center[i])
        
        # 计算单元尺寸
        self.dx_center = np.zeros(self.n_cells)
        for i in range(self.n_cells):
            self.dx_center[i] = self.x_face[i+1] - self.x_face[i]
        
        # 界面间距
        self.dx_face = np.diff(self.x_center)
        
        self.grid_type = GridType.NONUNIFORM
    
    def _compute_metrics(self) -> GridMetrics:
        """计算网格度量信息"""
        return GridMetrics(
            x_center=self.x_center,
            dx_center=self.dx_center,
            x_face=self.x_face,
            dx_face=self.dx_face,
            n_cells=self.n_cells,
            n_faces=self.n_faces,
            grid_type=self.grid_type
        )
    
    def interpolate_center_to_face(self, 
                                   field_center: np.ndarray,
                                   method: str = 'linear') -> np.ndarray:
        """
        从单元中心插值到单元界面
        
        h[i] (中心) → h[i+1/2] (界面)
        
        Args:
            field_center: 单元中心上的场 (n_cells,)
            method: 插值方法
                - 'linear': 线性插值（默认）
                - 'upwind': 迎风插值
        
        Returns:
            field_face: 单元界面上的场 (n_faces,)
        """
        assert len(field_center) == self.n_cells
        
        field_face = np.zeros(self.n_faces)
        
        if method == 'linear':
            # 边界：直接复制
            field_face[0] = field_center[0]
            field_face[-1] = field_center[-1]
            
            # 内部界面：线性插值
            for i in range(1, self.n_faces - 1):
                field_face[i] = 0.5 * (field_center[i-1] + field_center[i])
        
        elif method == 'upwind':
            # 迎风插值（需要流向信息，这里简化为线性）
            field_face = self.interpolate_center_to_face(field_center, 'linear')
        
        return field_face
    
    def interpolate_face_to_center(self,
                                   field_face: np.ndarray,
                                   method: str = 'linear') -> np.ndarray:
        """
        从单元界面插值到单元中心
        
        Q[i+1/2] (界面) → Q[i] (中心)
        
        Args:
            field_face: 单元界面上的场 (n_faces,)
            method: 插值方法
        
        Returns:
            field_center: 单元中心上的场 (n_cells,)
        """
        assert len(field_face) == self.n_faces
        
        field_center = np.zeros(self.n_cells)
        
        if method == 'linear':
            # 中心 = 左右界面的平均
            for i in range(self.n_cells):
                field_center[i] = 0.5 * (field_face[i] + field_face[i+1])
        
        return field_center
    
    def compute_gradient_at_face(self, field_center: np.ndarray) -> np.ndarray:
        """
        计算单元界面处的梯度
        
        ∂h/∂x|_{i+1/2} = (h[i+1] - h[i]) / dx
        
        Args:
            field_center: 单元中心上的场
        
        Returns:
            gradient: 界面处的梯度
        """
        gradient = np.zeros(self.n_faces)
        
        # 内部界面
        for i in range(1, self.n_faces - 1):
            dx = self.x_center[i] - self.x_center[i-1]
            gradient[i] = (field_center[i] - field_center[i-1]) / dx
        
        # 边界（单侧差分）
        gradient[0] = gradient[1]
        gradient[-1] = gradient[-2]
        
        return gradient
    
    def compute_gradient_at_center(self, field_face: np.ndarray) -> np.ndarray:
        """
        计算单元中心处的梯度
        
        ∂Q/∂x|_i = (Q[i+1/2] - Q[i-1/2]) / dx
        
        Args:
            field_face: 单元界面上的场
        
        Returns:
            gradient: 中心处的梯度
        """
        gradient = np.zeros(self.n_cells)
        
        for i in range(self.n_cells):
            gradient[i] = (field_face[i+1] - field_face[i]) / self.dx_center[i]
        
        return gradient
    
    def find_cell_index(self, x: float) -> int:
        """
        查找包含位置x的单元索引
        
        Args:
            x: 位置 (m)
        
        Returns:
            i: 单元索引（0 到 n_cells-1）
        """
        # 使用二分搜索
        i = np.searchsorted(self.x_face, x) - 1
        i = max(0, min(i, self.n_cells - 1))
        return i
    
    def find_face_index(self, x: float) -> int:
        """
        查找最近的界面索引
        
        Args:
            x: 位置 (m)
        
        Returns:
            i: 界面索引（0 到 n_faces-1）
        """
        i = np.argmin(np.abs(self.x_face - x))
        return i
    
    def refine_at_structures(self,
                            structure_positions: List[float],
                            refinement_factor: int = 4,
                            refinement_width: float = 1000.0) -> 'StaggeredGrid':
        """
        在结构物附近进行网格加密
        
        Args:
            structure_positions: 结构物位置列表
            refinement_factor: 加密倍数
            refinement_width: 加密区域宽度
        
        Returns:
            refined_grid: 加密后的网格
        """
        # 生成自适应网格中心位置
        x_centers_refined = []
        
        # 基础网格
        dx_base = self.length / self.n_cells
        
        for i in range(self.n_cells):
            x_center = self.x_center[i]
            
            # 检查是否在结构物附近
            near_structure = any(
                abs(x_center - pos) < refinement_width 
                for pos in structure_positions
            )
            
            if near_structure:
                # 加密区域：细分单元
                dx_refined = dx_base / refinement_factor
                x_left = x_center - dx_base / 2
                for j in range(refinement_factor):
                    x_refined = x_left + (j + 0.5) * dx_refined
                    x_centers_refined.append(x_refined)
            else:
                # 粗糙区域：保持原单元
                x_centers_refined.append(x_center)
        
        # 创建新的网格
        x_centers_array = np.array(x_centers_refined)
        return StaggeredGrid(self.length, len(x_centers_array), x_centers_array)
    
    def print_info(self):
        """打印网格信息"""
        print("="*60)
        print("交错网格信息")
        print("="*60)
        print(f"网格类型: {self.grid_type.value}")
        print(f"渠道长度: {self.length:.1f} m")
        print(f"单元数: {self.n_cells}")
        print(f"界面数: {self.n_faces}")
        print(f"单元尺寸: dx_min={self.dx_center.min():.2f} m, "
              f"dx_max={self.dx_center.max():.2f} m, "
              f"dx_avg={self.dx_center.mean():.2f} m")
        print("")
        print("变量定位:")
        print("  - 水深h、面积A: 单元中心 (n_cells个)")
        print("  - 流量Q、流速u: 单元界面 (n_faces个)")
        print("="*60)


# ========== 测试代码 ==========

def test_staggered_grid():
    """测试交错网格"""
    print("\n" + "="*70)
    print("测试: 交错网格管理器")
    print("="*70)
    
    # 测试1：均匀网格
    print("\n测试1: 均匀网格")
    print("-"*70)
    grid = StaggeredGrid(length=10000.0, n_cells=10)
    grid.print_info()
    
    print("单元中心位置:", grid.x_center[:5], "...")
    print("单元界面位置:", grid.x_face[:5], "...")
    
    # 测试2：插值
    print("\n测试2: 插值操作")
    print("-"*70)
    h_center = np.ones(grid.n_cells) * 2.0
    h_center[5] = 3.0  # 中间一个单元水深较大
    
    h_face = grid.interpolate_center_to_face(h_center)
    print(f"中心水深 (前5个): {h_center[:5]}")
    print(f"界面水深 (前5个): {h_face[:5]}")
    
    # 测试3：梯度
    print("\n测试3: 梯度计算")
    print("-"*70)
    grad_face = grid.compute_gradient_at_face(h_center)
    print(f"界面梯度 (中间5个): {grad_face[4:9]}")
    print(f"最大梯度: {grad_face.max():.4f}")
    
    # 测试4：结构物定位
    print("\n测试4: 结构物位置查找")
    print("-"*70)
    x_gate = 5000.0
    cell_idx = grid.find_cell_index(x_gate)
    face_idx = grid.find_face_index(x_gate)
    print(f"闸门位置: {x_gate} m")
    print(f"所在单元: {cell_idx} (中心@{grid.x_center[cell_idx]:.1f}m)")
    print(f"最近界面: {face_idx} (位置@{grid.x_face[face_idx]:.1f}m)")
    
    print("\n" + "="*70)
    print("✓ 交错网格测试完成")
    print("="*70)


if __name__ == '__main__':
    test_staggered_grid()
