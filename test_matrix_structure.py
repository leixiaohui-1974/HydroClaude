#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
检查Preis

smann v2的矩阵结构
"""

import numpy as np
import sys
sys.path.insert(0, '/workspace')

from physics.numerical_methods.preissmann_solver_v2 import PreissmannSolverV2

def test_matrix_structure():
    """测试矩阵结构"""
    
    print("="*80)
    print("测试Preissmann v2矩阵结构")
    print("="*80)
    
    # 简单配置
    n_cells = 3  # 3个单元
    n_nodes = n_cells + 1  # 4个节点
    
    print(f"\n配置:")
    print(f"  单元数: {n_cells}")
    print(f"  节点数: {n_nodes}")
    print(f"  未知数: 2*{n_nodes} = {2*n_nodes}")
    
    # 参数
    dx = 100.0
    width = 10.0
    manning_n = 0.025
    slope = 0.001
    dt = 60.0
    g = 9.81
    
    # 初始条件
    h = np.ones(n_nodes) * 2.0
    Q = np.zeros(n_nodes)
    
    # 边界条件
    bc = {
        'upstream_level': 2.0,
        'downstream_level': 2.0
    }
    
    # 创建求解器
    solver = PreissmannSolverV2(verbose=False)
    
    # 构建系统
    J, R = solver._build_system(
        h, Q, h, Q,  # old = new（初始状态）
        dt, dx, width, manning_n, slope, g,
        bc, n_nodes, n_cells
    )
    
    print(f"\n矩阵尺寸:")
    print(f"  J: {J.shape}")
    print(f"  R: {R.shape}")
    
    # 转换为密集矩阵查看
    J_dense = J.toarray()
    
    print(f"\nJacobian矩阵非零元素分布:")
    print(f"  总非零元素: {np.count_nonzero(J_dense)}")
    print(f"  每行非零元素数:")
    for i in range(2*n_nodes):
        n_nonzero = np.count_nonzero(J_dense[i, :])
        print(f"    方程{i}: {n_nonzero}个非零元素", end='')
        if n_nonzero == 0:
            print(" ❌ 全零行！")
        elif n_nonzero == 1:
            print(f" (对角元素={J_dense[i, i]:.3f})")
        else:
            print()
    
    # 检查矩阵条件数
    from numpy.linalg import cond
    try:
        condition_number = cond(J_dense)
        print(f"\n矩阵条件数: {condition_number:.2e}")
        if condition_number > 1e10:
            print("  ⚠️ 条件数过大，矩阵接近奇异")
    except:
        print("\n矩阵奇异，无法计算条件数")
    
    # 检查行列式
    from numpy.linalg import det
    try:
        determinant = det(J_dense)
        print(f"行列式: {determinant:.6e}")
        if abs(determinant) < 1e-10:
            print("  ❌ 行列式接近0，矩阵奇异")
    except:
        print("无法计算行列式")
    
    # 打印矩阵结构（仅显示非零位置）
    print(f"\nJacobian矩阵结构 (X=非零, .=零):")
    print("  " + "".join([f"{i%10}" for i in range(2*n_nodes)]))
    for i in range(2*n_nodes):
        row_str = "".join(['X' if J_dense[i,j] != 0 else '.' for j in range(2*n_nodes)])
        eq_type = ""
        if i == 0:
            eq_type = " (上游h BC)"
        elif i == n_cells:
            eq_type = " (下游h BC)"
        elif 0 < i < n_cells:
            eq_type = f" (连续方程,单元{i})"
        elif i == n_nodes:
            eq_type = " (上游Q BC)"
        elif i == 2*n_nodes-1:
            eq_type = " (下游Q BC)"
        elif n_nodes < i < 2*n_nodes-1:
            eq_type = f" (动量方程,单元{i-n_nodes})"
        
        print(f"{i:2d} {row_str}{eq_type}")
    
    print(f"\n残差向量R:")
    for i in range(2*n_nodes):
        print(f"  R[{i}] = {R[i]:.6e}")
    
    # 尝试求解
    print(f"\n尝试求解...")
    try:
        from scipy.sparse.linalg import spsolve
        dx_vec = spsolve(J.tocsr(), -R)
        print(f"✅ 求解成功")
        print(f"  ||dx|| = {np.linalg.norm(dx_vec):.6e}")
    except Exception as e:
        print(f"❌ 求解失败: {e}")


if __name__ == "__main__":
    test_matrix_structure()
