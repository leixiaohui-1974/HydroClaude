#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Newton-Raphson稳态求解器（HEC-RAS风格）

核心思想：
1. 建立N×N非线性方程组（能量方程+质量守恒）
2. 用Newton-Raphson迭代全局求解
3. 无时间推进，无累积误差
4. 直接求稳态解

Author: HydroClaude Development Team
Date: 2025-10-27
Reference: HEC-RAS Hydraulic Reference Manual, Chapter 2
"""

import numpy as np
from scipy.sparse import lil_matrix, csr_matrix
from scipy.sparse.linalg import spsolve
import sys
import os

# 添加项目路径
script_path = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(script_path))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from solvers.simple_correct_solver import SimpleCorrectSolver


class NewtonSteadySolver:
    """
    Newton-Raphson稳态求解器
    
    基于HEC-RAS的Newton方法求解稳态明渠流
    
    方法：
    1. 能量方程: H[i] = H[i-1] - hf[i] + S0*dx
    2. 质量守恒: Q[i] = Q[i-1] = const
    3. Newton迭代: J * delta_h = -R
    
    优势：
    - 无时间推进
    - 无累积误差
    - 适合长渠道
    - 收敛稳定
    """
    
    def __init__(self, length, nx, B, S0, n, g=9.81):
        """
        初始化Newton稳态求解器
        
        参数:
            length: 渠道长度 (m)
            nx: 节点数
            B: 渠道宽度 (m)
            S0: 底坡
            n: Manning糙率系数
            g: 重力加速度 (m/s²)
        """
        self.length = length
        self.nx = nx
        self.B = B
        self.S0 = S0
        self.n = n
        self.g = g
        
        # 网格
        self.x = np.linspace(0, length, nx)
        self.dx = self.x[1] - self.x[0] if nx > 1 else length
        
        # 床面高程（假设均匀坡度）
        # x=0是下游（低），x=length是上游（高）
        self.z = np.linspace(0, length * S0, nx)
        
        # 结构物列表
        self.structures = []
        
        print(f"="*70)
        print(f"Newton-Raphson稳态求解器初始化")
        print(f"="*70)
        print(f"渠道长度: {length} m")
        print(f"节点数: {nx}")
        print(f"网格间距: {self.dx:.2f} m")
        print(f"渠道宽度: {B} m")
        print(f"底坡: {S0}")
        print(f"Manning糙率: {n}")
        print(f"结构物数量: {len(self.structures)}")
        print(f"="*70)
    
    def add_structure(self, structure):
        """
        添加水工结构物
        
        参数:
            structure: 结构物对象（SluiceGate, Weir等）
        """
        self.structures.append(structure)
        print(f"添加结构物: {structure.__class__.__name__} @ x={structure.position}m")
    
    def initialize_with_uniform_flow(self, Q):
        """
        使用均匀流初始化
        
        参数:
            Q: 流量 (m³/s)
        
        返回:
            h: 初始水深数组 (m)
        """
        simple_solver = SimpleCorrectSolver(
            length=self.length,
            B=self.B,
            S0=self.S0,
            n=self.n,
            nx=self.nx
        )
        
        result = simple_solver.solve_uniform_flow(Q)
        h_uniform = result['h']
        
        print(f"\n初始化: 使用均匀流解")
        print(f"  均匀流水深: {h_uniform[0]:.4f} m")
        
        return h_uniform
    
    def compute_total_head(self, h, Q):
        """
        计算总水头 H = z + h + v²/(2g)
        
        参数:
            h: 水深数组 (m)
            Q: 流量 (m³/s)
        
        返回:
            H: 总水头数组 (m)
        """
        # 流速
        v = Q / (self.B * h)
        
        # 速度水头
        v_head = v**2 / (2 * self.g)
        
        # 总水头
        H = self.z + h + v_head
        
        return H
    
    def compute_friction_slope(self, h, Q):
        """
        计算摩阻坡度（Manning公式，考虑湿周）
        
        Sf = n² * v² / R^(4/3)
        
        其中 R = A/P = B*h/(B+2*h) 为水力半径
        
        参数:
            h: 水深数组 (m)
            Q: 流量 (m³/s)
        
        返回:
            Sf: 摩阻坡度数组
        """
        # 流速
        v = Q / (self.B * h)
        
        # 水力半径（矩形渠道）
        A = self.B * h
        P = self.B + 2 * h
        R = A / P
        
        # Manning公式（精确，考虑湿周）
        Sf = self.n**2 * v**2 / (R**(4/3))
        
        return Sf
    
    def compute_residuals(self, h, Q, h_downstream):
        """
        计算残差向量 R(h)
        
        能量方程残差:
        R[i] = H[i] - H[i-1] + Sf_avg * dx - S0 * dx
        
        边界条件:
        R[0] = h[0] - h_downstream  (下游边界)
        
        参数:
            h: 水深数组 (m)
            Q: 流量 (m³/s)
            h_downstream: 下游水深 (m)
        
        返回:
            R: 残差向量
        """
        R = np.zeros(self.nx)
        
        # 计算总水头
        H = self.compute_total_head(h, Q)
        
        # 计算摩阻坡度
        Sf = self.compute_friction_slope(h, Q)
        
        # 下游边界条件（已知水深）
        R[0] = h[0] - h_downstream
        
        # 内部节点：能量方程
        for i in range(1, self.nx):
            # 平均摩阻坡度
            Sf_avg = 0.5 * (Sf[i] + Sf[i-1])
            
            # 能量方程残差
            # 沿x正方向（从下游i-1到上游i），逆流方向
            # 总水头变化: dH/dx = Sf（逆流方向，总水头增加）
            # 离散形式: H[i] - H[i-1] = Sf_avg * dx
            # 残差: R[i] = H[i] - H[i-1] - Sf_avg * dx = 0
            R[i] = H[i] - H[i-1] - Sf_avg * self.dx
        
        return R
    
    def compute_jacobian_numerical(self, h, Q, h_downstream, epsilon=1e-6):
        """
        数值计算Jacobian矩阵 J = ∂R/∂h
        
        使用有限差分：
        J[i,j] = (R[i](h[j] + ε) - R[i](h[j])) / ε
        
        参数:
            h: 水深数组 (m)
            Q: 流量 (m³/s)
            h_downstream: 下游水深 (m)
            epsilon: 有限差分步长
        
        返回:
            J: Jacobian稀疏矩阵
        """
        n = self.nx
        J = lil_matrix((n, n))
        
        # 基准残差
        R0 = self.compute_residuals(h, Q, h_downstream)
        
        # 对每个变量求偏导
        for j in range(n):
            # 扰动
            h_perturbed = h.copy()
            h_perturbed[j] += epsilon
            
            # 扰动后的残差
            R_perturbed = self.compute_residuals(h_perturbed, Q, h_downstream)
            
            # 有限差分
            dR_dh = (R_perturbed - R0) / epsilon
            
            # 只存储非零元素（稀疏矩阵）
            for i in range(n):
                if abs(dR_dh[i]) > 1e-10:
                    J[i, j] = dR_dh[i]
        
        return csr_matrix(J)
    
    def solve_steady_state(self, Q, h_downstream, max_iter=50, tol=1e-6, 
                          alpha=0.1, verbose=True):
        """
        Newton-Raphson迭代求解稳态
        
        算法:
        1. 初始化: h = 均匀流
        2. 迭代:
            a. 计算残差 R(h)
            b. 计算Jacobian J = ∂R/∂h
            c. 求解线性系统 J·Δh = -R
            d. 更新 h = h + α·Δh
            e. 检查收敛
        
        参数:
            Q: 流量 (m³/s)
            h_downstream: 下游水深 (m)
            max_iter: 最大迭代次数
            tol: 收敛容差
            alpha: 松弛因子 (0 < alpha <= 1)
            verbose: 是否打印详细信息
        
        返回:
            result: 结果字典
        """
        if verbose:
            print(f"\n{'='*70}")
            print(f"Newton-Raphson稳态求解")
            print(f"{'='*70}")
            print(f"目标流量: {Q:.2f} m³/s")
            print(f"下游水深: {h_downstream:.3f} m")
            print(f"最大迭代: {max_iter}")
            print(f"收敛容差: {tol}")
            print(f"松弛因子: {alpha}")
            print(f"{'='*70}\n")
        
        # 1. 初始化
        h = self.initialize_with_uniform_flow(Q)
        
        # 迭代历史
        residual_history = []
        
        # 2. Newton迭代
        for iter in range(max_iter):
            # 2.1 计算残差
            R = self.compute_residuals(h, Q, h_downstream)
            residual_norm = np.linalg.norm(R)
            residual_history.append(residual_norm)
            
            if verbose and (iter % 10 == 0 or iter < 5):
                print(f"Iter {iter:3d}: 残差范数 = {residual_norm:.6e}")
            
            # 2.2 检查收敛
            if residual_norm < tol:
                if verbose:
                    print(f"\n✓ 收敛！迭代次数 = {iter}")
                break
            
            # 2.3 计算Jacobian
            J = self.compute_jacobian_numerical(h, Q, h_downstream)
            
            # 2.4 求解线性系统 J·Δh = -R
            try:
                delta_h = spsolve(J, -R)
            except Exception as e:
                print(f"\n✗ 线性求解失败: {e}")
                break
            
            # 2.5 限制更新步长（避免过大更新）
            delta_h_max = np.abs(delta_h).max()
            if delta_h_max > 0.5:
                # 如果步长太大，缩小松弛因子
                alpha_adaptive = 0.5 / delta_h_max
            else:
                alpha_adaptive = alpha
            
            # 2.6 更新（带自适应松弛）
            h_new = h + alpha_adaptive * delta_h
            
            # 2.7 约束（确保正水深）
            h_new = np.maximum(h_new, 0.01)
            
            # 2.8 线搜索（确保残差下降）
            R_new = self.compute_residuals(h_new, Q, h_downstream)
            residual_norm_new = np.linalg.norm(R_new)
            
            # 如果残差增大，减小步长
            line_search_iter = 0
            while residual_norm_new > residual_norm and line_search_iter < 5:
                alpha_adaptive *= 0.5
                h_new = h + alpha_adaptive * delta_h
                h_new = np.maximum(h_new, 0.01)
                R_new = self.compute_residuals(h_new, Q, h_downstream)
                residual_norm_new = np.linalg.norm(R_new)
                line_search_iter += 1
            
            # 更新
            h = h_new
        
        else:
            # 未收敛
            if verbose:
                print(f"\n⚠ 未收敛（{max_iter}次迭代）")
        
        # 3. 计算最终结果
        H = self.compute_total_head(h, Q)
        v = Q / (self.B * h)
        Fr = v / np.sqrt(self.g * h)
        Sf = self.compute_friction_slope(h, Q)
        
        # 验证质量守恒
        Q_check = self.B * h * v
        Q_avg = Q_check.mean()
        Q_error = abs(Q_avg - Q) / Q * 100
        
        if verbose:
            print(f"\n{'='*70}")
            print(f"求解完成")
            print(f"{'='*70}")
            print(f"最终残差范数: {residual_norm:.6e}")
            print(f"迭代次数: {iter + 1}")
            print(f"平均流量: {Q_avg:.4f} m³/s")
            print(f"流量误差: {Q_error:.4f}%")
            print(f"水深范围: {h.min():.3f} - {h.max():.3f} m")
            print(f"Froude数范围: {Fr.min():.3f} - {Fr.max():.3f}")
            print(f"{'='*70}")
        
        # 返回结果
        result = {
            'x': self.x,
            'h': h,
            'z': self.z,
            'H': H,
            'v': v,
            'Fr': Fr,
            'Sf': Sf,
            'Q': Q,
            'Q_avg': Q_avg,
            'Q_error': Q_error,
            'iterations': iter + 1,
            'residual_norm': residual_norm,
            'converged': residual_norm < tol,
            'residual_history': residual_history
        }
        
        return result


def main():
    """测试Newton稳态求解器"""
    print("="*70)
    print("测试Newton-Raphson稳态求解器")
    print("="*70)
    
    # 参数
    length = 10000  # 10km长渠道（Week 2失败的场景）
    nx = 101
    B = 10.0
    S0 = 0.001
    n = 0.025
    Q = 10.0
    
    print(f"\n测试场景: MacDonald Case 1（10km长渠道）")
    print(f"  L={length}m, Q={Q}m³/s, S0={S0}, n={n}")
    
    # 创建求解器
    solver = NewtonSteadySolver(length=length, nx=nx, B=B, S0=S0, n=n)
    
    # 计算下游边界条件（均匀流水深）
    simple = SimpleCorrectSolver(length=length, B=B, S0=S0, n=n, nx=nx)
    h_ref = simple.solve_uniform_flow(Q)['h'][0]
    
    # 求解
    result = solver.solve_steady_state(Q=Q, h_downstream=h_ref, verbose=True)
    
    # 对比均匀流解析解
    h_error = np.abs(result['h'] - h_ref).max() / h_ref * 100
    
    print(f"\n与均匀流解析解对比:")
    print(f"  最大误差: {h_error:.6f}%")
    
    if h_error < 0.1:
        print(f"  ✅ 优秀！误差 < 0.1%")
    elif h_error < 1.0:
        print(f"  ✅ 良好！误差 < 1%")
    else:
        print(f"  ⚠️ 误差较大")
    
    print(f"\n{'='*70}")
    print(f"✓ Newton求解器测试完成！")
    print(f"{'='*70}")


if __name__ == '__main__':
    main()
