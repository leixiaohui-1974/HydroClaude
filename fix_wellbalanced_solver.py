#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
诊断和修复WellBalancedCanalSolver

问题: 数值发散（NaN）
目标: 稳定收敛，误差<0.5%

Author: Claude (AI Assistant)
Date: 2025-10-27
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
from solvers.v1_wellbalanced_fdm import WellBalancedCanalSolver
from solvers.simple_correct_solver import SimpleCorrectSolver
from tests.analytical_solutions import AnalyticalSolutions


def diagnose_wellbalanced_solver():
    """诊断WellBalancedCanalSolver问题"""
    print("="*70)
    print("诊断：WellBalancedCanalSolver数值稳定性")
    print("="*70)
    
    Q = 10.0
    B = 10.0
    S0 = 0.001
    n = 0.025
    
    # 解析解
    analytical = AnalyticalSolutions()
    h_analytical = analytical.uniform_flow_depth(Q, B, S0, n)
    
    print(f"\n参数: Q={Q}, B={B}, S0={S0}, n={n}")
    print(f"解析解: h={h_analytical:.4f} m")
    
    # 尝试当前实现
    print(f"\n测试当前实现:")
    try:
        solver = WellBalancedCanalSolver(
            length=10000,
            nx=101,
            B=B,
            S0=S0,
            n=n
        )
        
        result = solver.solve_steady_state(
            Q_target=Q,
            h_downstream=h_analytical,
            max_iter=100,  # 限制迭代，避免长时间等待
            tolerance=0.01
        )
        
        mid_idx = len(result['h']) // 2
        h_num = result['h'][mid_idx]
        
        if np.isnan(h_num):
            print("  ❌ 结果: NaN（数值发散）")
        else:
            error = abs(h_num - h_analytical) / h_analytical * 100
            print(f"  h = {h_num:.4f} m")
            print(f"  误差 = {error:.2f}%")
            if error < 1.0:
                print("  ✓ 结果合理")
            else:
                print("  ⚠️ 误差较大")
                
    except Exception as e:
        print(f"  ❌ 异常: {e}")


def propose_fix():
    """提出修复方案"""
    print("\n" + "="*70)
    print("修复方案")
    print("="*70)
    
    print("""
修复1: 改进初始化
--------------------------------------
使用SimpleCorrectSolver或EnergyEquationSolver初始化：

def initialize_from_correct_solver(self, Q_target, h_downstream):
    # 使用已验证的求解器初始化
    from solvers.simple_correct_solver import SimpleCorrectSolver
    simple = SimpleCorrectSolver(
        length=self.length, B=self.B, S0=self.S0, n=self.n, nx=self.nx
    )
    result = simple.solve_uniform_flow(Q_target)
    
    # 插值到当前网格
    self.h = result['h']
    self.Q = np.ones_like(self.h) * Q_target

修复2: 自适应时间步长
--------------------------------------
def compute_stable_timestep(self):
    u = self.Q / (self.B * self.h)
    c = np.sqrt(self.g * self.h)
    
    # CFL条件
    CFL = 0.2  # 保守值
    dt = CFL * self.dx / (np.abs(u) + c).max()
    
    # 限制范围
    dt = np.clip(dt, 0.01, 5.0)
    return dt

修复3: 数值稳定化
--------------------------------------
def apply_stabilization(self):
    # 限制最小水深
    self.h = np.maximum(self.h, 0.01)
    
    # 限制最大流速
    u = self.Q / (self.B * self.h)
    u_max = 10.0
    u = np.clip(u, -u_max, u_max)
    self.Q = u * self.B * self.h
    
    # 检测NaN并处理
    if np.any(np.isnan(self.h)) or np.any(np.isnan(self.Q)):
        # 重新初始化
        self.initialize_from_correct_solver(...)
        
修复4: 降低松弛因子
--------------------------------------
# 从omega=0.95降低到0.5-0.7
solver = WellBalancedCanalSolver(
    ...,
    omega=0.6  # 更保守的松弛
)
    """)


if __name__ == '__main__':
    diagnose_wellbalanced_solver()
    propose_fix()
    
    print("\n" + "="*70)
    print("下一步: 实施修复")
    print("="*70)
