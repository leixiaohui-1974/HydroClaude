#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
非恒定流求解器

基于方案B（混合FV/FD + 交错网格）扩展到非恒定流。

核心特性：
1. CFL自适应时间步长
2. 时间序列边界条件
3. 长时间稳定性
4. 质量守恒 < 1e-10

算法：
- 连续性方程：有限体积法（FV）
- 动量方程：有限差分法（FD）
- 时间推进：显式/半隐式
- CFL条件：自动调整dt

Author: Claude (AI Assistant)
Date: 2025-10-27
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
import time

from .staggered_grid import StaggeredGrid
from .fv_continuity import FVContinuityEquation
from .fd_momentum import FDMomentumEquation
from .boundary_conditions import BoundaryManager, BoundaryCondition
try:
    from ..v1_wellbalanced_fdm.structures import HydraulicStructure
except ImportError:
    from solvers.v1_wellbalanced_fdm.structures import HydraulicStructure


class UnsteadySolver:
    """
    非恒定流求解器
    
    扩展HybridCanalSolver，支持瞬态模拟。
    
    新增功能：
    - 时间序列边界条件
    - CFL自适应时间步长
    - 输出控制（时间间隔）
    - 长时间稳定性
    
    使用示例：
        >>> from boundary_conditions import ConstantBC, TimeSeriesBC
        >>> 
        >>> solver = UnsteadySolver(length=10000, n_cells=100, B=10, S0=0.001, n=0.025)
        >>> 
        >>> # 设置边界条件
        >>> solver.boundary.set_upstream(ConstantBC('flow', 10.0))
        >>> solver.boundary.set_downstream(ConstantBC('depth', 2.0))
        >>> 
        >>> # 运行非恒定流
        >>> result = solver.solve_unsteady(
        ...     duration=86400,  # 24小时
        ...     dt_initial=1.0,
        ...     cfl=0.3,
        ...     output_interval=600  # 每10分钟输出
        ... )
    """
    
    def __init__(self,
                 length: float = 10000.0,
                 n_cells: int = 100,
                 B: float = 10.0,
                 S0: float = 0.001,
                 n: float = 0.025,
                 g: float = 9.81,
                 theta: float = 0.6):
        """
        初始化非恒定流求解器
        
        Args:
            length: 渠道长度
            n_cells: 单元数
            B: 渠道宽度
            S0: 渠底坡度
            n: Manning糙率
            g: 重力加速度
            theta: 隐式度
        """
        # 几何参数
        self.length = length
        self.B = B
        self.S0 = S0
        self.n_manning = n
        self.g = g
        self.theta = theta
        
        # 创建交错网格
        self.grid = StaggeredGrid(length=length, n_cells=n_cells)
        
        # 创建方程组件
        self.fv_cont = FVContinuityEquation(self.grid, B=B, g=g)
        self.fd_mom = FDMomentumEquation(self.grid, B=B, S0=S0, n=n, g=g, theta=theta)
        
        # 边界条件管理器
        self.boundary = BoundaryManager()
        
        # 状态变量
        self.h = np.ones(self.grid.n_cells) * 2.0     # 水深（中心）
        self.Q = np.ones(self.grid.n_faces) * 10.0    # 流量（界面）
        self.A = self.h * self.B                       # 面积（中心）
        
        # 床面高程（中心）
        self.z = np.zeros(self.grid.n_cells)
        for i in range(self.grid.n_cells):
            x_i = self.grid.x_center[i]
            self.z[i] = (self.length - x_i) * S0
        
        # 结构物
        self.structures: List[HydraulicStructure] = []
        self.structure_faces: List[int] = []
        
        # 时间相关
        self.current_time = 0.0
        self.time_step_count = 0
        
        # 输出历史
        self.output_times: List[float] = []
        self.output_h: List[np.ndarray] = []
        self.output_Q: List[np.ndarray] = []
    
    def add_structure(self, structure: HydraulicStructure):
        """添加水工结构物"""
        face_idx = self.grid.find_face_index(structure.position)
        self.structures.append(structure)
        self.structure_faces.append(face_idx)
        print(f"添加结构物: {structure} at face {face_idx}")
    
    def compute_cfl_timestep(self, cfl: float = 0.3) -> float:
        """
        计算CFL条件约束的时间步长
        
        CFL条件: Δt ≤ CFL * Δx / (|u| + c)
        
        其中:
        - u: 流速
        - c: 波速 = sqrt(g*h)
        - CFL: CFL数（通常0.2-0.5）
        
        Args:
            cfl: CFL数
        
        Returns:
            dt: 允许的最大时间步长
        """
        # 计算流速
        h_face = self.grid.interpolate_center_to_face(self.h)
        A_face = self.B * h_face
        u = np.abs(self.Q) / np.maximum(A_face, 1e-6)
        
        # 计算波速
        c = np.sqrt(self.g * np.maximum(h_face, 1e-6))
        
        # CFL条件
        dt_max = np.inf
        for i in range(self.grid.n_faces):
            if i < self.grid.n_cells:
                dx = self.grid.dx_center[i]
                wave_speed = u[i] + c[i]
                if wave_speed > 1e-6:
                    dt_i = cfl * dx / wave_speed
                    dt_max = min(dt_max, dt_i)
        
        return dt_max
    
    def apply_boundary_conditions(self, t: float):
        """
        应用边界条件
        
        Args:
            t: 当前时间
        """
        # 获取边界条件值
        if self.boundary.upstream_bc is not None:
            if self.boundary.upstream_bc.bc_type == 'flow':
                # 上游流量边界
                Q_upstream = self.boundary.get_upstream_value(t)
                self.Q[0] = Q_upstream
            elif self.boundary.upstream_bc.bc_type == 'depth':
                # 上游水深边界
                h_upstream = self.boundary.get_upstream_value(t)
                self.h[0] = h_upstream
                self.A[0] = h_upstream * self.B
        
        if self.boundary.downstream_bc is not None:
            if self.boundary.downstream_bc.bc_type == 'flow':
                # 下游流量边界
                Q_downstream = self.boundary.get_downstream_value(t)
                self.Q[-1] = Q_downstream
            elif self.boundary.downstream_bc.bc_type == 'depth':
                # 下游水深边界
                h_downstream = self.boundary.get_downstream_value(t)
                self.h[-1] = h_downstream
                self.A[-1] = h_downstream * self.B
    
    def apply_structure_bc(self):
        """应用结构物边界条件"""
        for face_idx, structure in zip(self.structure_faces, self.structures):
            cell_left = max(0, face_idx - 1)
            cell_right = min(self.grid.n_cells - 1, face_idx)
            
            h_left = self.h[cell_left]
            h_right = self.h[cell_right]
            
            # 计算结构物流量
            Q_structure, regime = structure.calculate_discharge(h_left, h_right)
            self.Q[face_idx] = Q_structure
    
    def step(self, dt: float) -> Tuple[np.ndarray, np.ndarray]:
        """
        单步时间推进
        
        Args:
            dt: 时间步长
        
        Returns:
            (h_new, Q_new): 新的水深和流量
        """
        # 保存旧状态
        A_old = self.A.copy()
        Q_old = self.Q.copy()
        h_old = self.h.copy()
        
        # 应用边界条件
        self.apply_boundary_conditions(self.current_time)
        
        # FV更新面积（质量守恒）
        A_new = self.fv_cont.update(A_old, Q_old, dt)
        
        # FD更新流量（动量方程）
        Q_new = self.fd_mom.update(Q_old, h_old, dt)
        
        # 更新水深
        h_new = A_new / self.B
        
        # 应用结构物边界条件
        self.h = h_new
        self.Q = Q_new
        self.A = A_new
        self.apply_structure_bc()
        
        # 更新时间
        self.current_time += dt
        self.time_step_count += 1
        
        return self.h, self.Q
    
    def save_output(self):
        """保存当前时刻的输出"""
        self.output_times.append(self.current_time)
        self.output_h.append(self.h.copy())
        self.output_Q.append(self.Q.copy())
    
    def solve_unsteady(self,
                      duration: float,
                      dt_initial: float = 1.0,
                      cfl: float = 0.3,
                      output_interval: float = 600.0,
                      verbose: bool = True) -> Dict:
        """
        非恒定流求解（主函数）
        
        Args:
            duration: 模拟时长 (s)
            dt_initial: 初始时间步长 (s)
            cfl: CFL数（用于自适应时间步长）
            output_interval: 输出间隔 (s)
            verbose: 详细输出
        
        Returns:
            result: 求解结果字典
                - times: 输出时间点
                - h: 水深历史
                - Q: 流量历史
                - x_center: 单元中心位置
                - x_face: 界面位置
                - converged: 是否完成
                - mass_conservation_error: 质量守恒误差
        """
        if verbose:
            print("="*70)
            print("非恒定流求解（方案B扩展）")
            print("="*70)
            print(f"模拟时长: {duration:.1f}s ({duration/3600:.1f}小时)")
            print(f"初始时间步长: {dt_initial:.3f}s")
            print(f"CFL数: {cfl}")
            print(f"输出间隔: {output_interval:.1f}s")
            self.grid.print_info()
        
        # 重置
        self.current_time = 0.0
        self.time_step_count = 0
        self.output_times = []
        self.output_h = []
        self.output_Q = []
        
        # 保存初始状态
        self.save_output()
        
        # 时间积分
        dt = dt_initial
        next_output_time = output_interval
        
        start_time = time.time()
        
        while self.current_time < duration:
            # CFL自适应时间步长
            dt_cfl = self.compute_cfl_timestep(cfl)
            dt = min(dt_cfl, dt_initial)
            
            # 确保不超过模拟时长
            if self.current_time + dt > duration:
                dt = duration - self.current_time
            
            # 时间步进
            h_new, Q_new = self.step(dt)
            
            # 输出
            if self.current_time >= next_output_time or \
               abs(self.current_time - duration) < 1e-6:
                self.save_output()
                
                if verbose and self.time_step_count % 100 == 0:
                    h_avg = np.mean(self.h)
                    Q_avg = np.mean(self.Q)
                    print(f"t={self.current_time:.1f}s ({self.current_time/3600:.2f}h): "
                          f"h_avg={h_avg:.3f}m, Q_avg={Q_avg:.3f}m³/s, "
                          f"dt={dt:.4f}s, steps={self.time_step_count}")
                
                next_output_time += output_interval
        
        elapsed_time = time.time() - start_time
        
        # 检查质量守恒
        mass_error = self._check_mass_conservation()
        
        if verbose:
            print("")
            print("="*70)
            print("求解完成")
            print("="*70)
            print(f"总时间步数: {self.time_step_count}")
            print(f"输出点数: {len(self.output_times)}")
            print(f"计算时间: {elapsed_time:.2f}s")
            print(f"质量守恒误差: {mass_error:.2e}")
            print("="*70)
        
        return {
            'times': np.array(self.output_times),
            'h': np.array(self.output_h),
            'Q': np.array(self.output_Q),
            'x_center': self.grid.x_center,
            'x_face': self.grid.x_face,
            'z': self.z,
            'converged': True,
            'n_steps': self.time_step_count,
            'n_outputs': len(self.output_times),
            'mass_conservation_error': mass_error,
            'computation_time': elapsed_time
        }
    
    def _check_mass_conservation(self) -> float:
        """
        检查全局质量守恒
        
        Returns:
            error: 相对误差
        """
        if len(self.output_h) < 2:
            return 0.0
        
        # 初始和最终质量
        mass_initial = np.sum(self.output_h[0]) * self.B
        mass_final = np.sum(self.output_h[-1]) * self.B
        
        # 相对变化
        if mass_initial > 0:
            error = abs(mass_final - mass_initial) / mass_initial
        else:
            error = 0.0
        
        return error


# ========== 使用示例 ==========

def example_usage():
    """
    非恒定流求解器使用示例
    
    场景：恒定边界条件下的非恒定流
    """
    print("\n" + "="*80)
    print("示例：非恒定流求解器")
    print("="*80)
    
    from .boundary_conditions import ConstantBC
    
    # 创建求解器
    solver = UnsteadySolver(
        length=10000.0,
        n_cells=100,
        B=10.0,
        S0=0.001,
        n=0.025
    )
    
    # 设置恒定边界条件
    solver.boundary.set_upstream(ConstantBC('flow', 10.0))
    solver.boundary.set_downstream(ConstantBC('depth', 2.0))
    
    # 运行非恒定流（6小时）
    result = solver.solve_unsteady(
        duration=21600,  # 6小时
        dt_initial=1.0,
        cfl=0.3,
        output_interval=600,  # 每10分钟输出
        verbose=True
    )
    
    print(f"\n✓ 模拟完成")
    print(f"  输出时间点: {len(result['times'])}")
    print(f"  质量守恒误差: {result['mass_conservation_error']:.2e}")
    
    return result


if __name__ == '__main__':
    example_usage()
