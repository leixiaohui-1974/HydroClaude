#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
调试Preissmann求解器的Jacobian矩阵问题
"""

import numpy as np
from scipy.sparse import lil_matrix
import sys
import os


# Add project root to Python path
script_path = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(script_path))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def test_jacobian_structure():
    """测试Jacobian矩阵结构"""
    
    print("="*80)
    print("测试Jacobian矩阵结构")
    print("="*80)
    
    # 参数
    n_cells = 5  # 5个单元 -> 6个节点
    n_nodes = n_cells + 1
    
    print(f"\n配置:")
    print(f"  单元数: {n_cells}")
    print(f"  节点数: {n_nodes}")
    print(f"  未知数: 2*{n_nodes} = {2*n_nodes} (h和Q各{n_nodes}个)")
    print(f"  方程数: 2*{n_nodes} = {2*n_nodes}")
    
    # 方程结构
    print(f"\n方程结构:")
    print(f"  连续方程: {n_cells}个 (针对单元)")
    print(f"  动量方程: {n_cells}个 (针对单元)")
    print(f"  边界条件: 4个 (上下游各2个)")
    print(f"  总计: {n_cells} + {n_cells} + 4 = {2*n_cells + 4}")
    print(f"  但未知数: {2*n_nodes} = {2*(n_cells+1)}")
    
    print(f"\n 问题：方程数({2*n_cells + 4}) != 未知数({2*n_nodes})")
    
    # 正确的结构
    print(f"\n正确的结构应该是:")
    print(f"  对于n_cells个单元，有n_cells+1个节点")
    print(f"  未知数: 2*(n_cells+1)")
    print(f"  内部方程: 2*n_cells (连续+动量)")
    print(f"  边界方程: 2 (上游) + 2 (下游) = 4")
    print(f"  但这样方程数={2*n_cells + 4} != 未知数={2*(n_cells+1)} = {2*n_cells + 2}")
    
    print(f"\n 解决方案：")
    print(f"  方案1: 连续方程针对内部节点i=1...n_cells-1 ({n_cells-1}个)")
    print(f"       动量方程针对内部节点i=1...n_cells-1 ({n_cells-1}个)")
    print(f"       边界方程: 4个")
    print(f"       总计: {2*(n_cells-1) + 4} = {2*n_cells + 2} = 2*(n_cells+1) ")
    
    print(f"\n  方案2: 连续方程针对所有单元i=0...n_cells-1 ({n_cells}个)")
    print(f"       动量方程针对所有单元i=0...n_cells-1 ({n_cells}个)")
    print(f"       但边界条件覆盖其中2个方程")
    print(f"       实际独立方程: {2*n_cells} ≠ {2*n_nodes}")
    print(f"        这个方案不对！")
    
    print("\n"+"="*80)
    print("结论：Preissmann格式的方程/未知数匹配需要仔细设计！")
    print("="*80)


def test_boundary_condition_application():
    """测试边界条件应用"""
    
    print("\n"+"="*80)
    print("测试边界条件应用逻辑")
    print("="*80)
    
    n_cells = 3
    n_nodes = n_cells + 1  # 4个节点
    
    print(f"\n配置: {n_cells}个单元, {n_nodes}个节点")
    print(f"节点索引: 0, 1, 2, 3")
    print(f"单元索引: [0,1], [1,2], [2,3]")
    
    print(f"\n变量索引:")
    print(f"  h[0], h[1], h[2], h[3]  <- 水深")
    print(f"  Q[0], Q[1], Q[2], Q[3]  <- 流量")
    
    print(f"\n方程索引（2*n_nodes={2*n_nodes}）:")
    for i in range(n_nodes):
        print(f"  方程 {i}: 关于节点{i}的某个方程（连续或边界）")
    for i in range(n_nodes):
        print(f"  方程 {n_nodes+i}: 关于节点{i}的某个方程（动量或边界）")
    
    print(f"\n边界条件（示例：上游固定水位和流量，下游固定水位）:")
    print(f"  上游 h[0] = h_bc  -> 方程0")
    print(f"  上游 Q[0] = Q_bc  -> 方程{n_nodes}")
    print(f"  下游 h[3] = h_bc  -> 方程{n_nodes-1}")
    print(f"  下游 Q[3] 自由    -> 从动量方程推导")
    
    print(f"\n内部方程:")
    print(f"  连续方程针对单元[1,2]和[2,3] ({n_cells-1}个)")
    print(f"  动量方程针对单元[1,2]和[2,3] ({n_cells-1}个)")
    
    print(f"\n总计方程:")
    print(f"  边界: 3个（h[0], Q[0], h[3]）")
    print(f"  内部: 2*(n_cells-1) = {2*(n_cells-1)}个")
    print(f"  总计: 3 + {2*(n_cells-1)} = {3 + 2*(n_cells-1)}")
    print(f"  未知数: {2*n_nodes}")
    print(f"   不匹配！")
    
    print(f"\n 正确方案：边界条件必须是2+2=4个")
    print(f"  上游: h[0]固定 + Q[0]固定  OR  h[0]固定 + 动量方程  等")
    print(f"  下游: h[n-1]固定 + 动量方程  OR  其他组合")
    print(f"  内部: 连续和动量方程 2*(n_cells-1)个")
    print(f"  总计: 4 + 2*(n_cells-1) = {4 + 2*(n_cells-1)} = 2*n_cells+2 = 2*(n_cells+1) ")


if __name__ == "__main__":
    test_jacobian_structure()
    test_boundary_condition_application()
    
    print("\n"+"="*80)
    print("关键发现：")
    print("  1. 方程数必须 = 未知数 = 2*(n_cells+1)")
    print("  2. 内部方程 2*(n_cells-1) + 边界方程4 = 2*n_cells+2 ")
    print("  3. 连续/动量方程只针对内部单元[1, n_cells-1]")
    print("  4. 边界单元[0,1]和[n_cells-1, n_cells]由边界条件决定")
    print("="*80)
