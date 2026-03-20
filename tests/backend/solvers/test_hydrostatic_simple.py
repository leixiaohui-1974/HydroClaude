#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
简化的HydrostaticCanalSolver测试 - 快速验证

Author: HydroClaude Test Team  
Date: 2025-11-20
"""

import sys
import warnings
warnings.filterwarnings("ignore")
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver
from utils.canal_utils import compute_steady_uniform_flow
import numpy as np
import pytest


class Test简单验证:
    """简化测试，验证求解器基本功能"""
    
    def test_01_创建求解器(self):
        """测试求解器创建"""
        print("\n" + "="*70)
        print("测试 1: 创建求解器")
        print("="*70)
        
        solver = HydrostaticCanalSolver(
            length=1000.0,
            nx=100,
            B=5.0,
            S0=0.001,
            n=0.025
        )
        
        print(f"✅ 求解器创建成功")
        print(f"   长度: {solver.length} m")
        print(f"   节点数: {solver.nx}")
        print(f"   渠宽: {solver.B} m")
        
        assert solver.length == 1000.0
        assert solver.nx == 100
        
    def test_02_设置流量(self):
        """测试设置流量"""
        print("\n" + "="*70)
        print("测试 2: 设置流量")
        print("="*70)
        
        solver = HydrostaticCanalSolver(
            length=1000.0,
            nx=100,
            B=5.0,
            S0=0.001,
            n=0.025
        )
        
        Q_target = 10.0
        solver.set_Q(Q_target)
        
        print(f"✅ 流量设置成功: Q = {Q_target} m³/s")
        
        # 获取流量
        Q = solver.get_Q()
        print(f"   获取流量: Q = {np.mean(Q):.4f} m³/s")
        
        assert np.abs(np.mean(Q) - Q_target) < 0.1
        
    def test_03_稳态求解(self):
        """测试稳态求解"""
        print("\n" + "="*70)
        print("测试 3: 稳态求解")
        print("="*70)
        
        # 参数
        Q = 10.0
        B = 5.0
        S0 = 0.001
        n = 0.025
        
        # 创建求解器
        solver = HydrostaticCanalSolver(
            length=1000.0,
            nx=100,
            B=B,
            S0=S0,
            n=n
        )
        
        # 设置流量
        solver.set_Q(Q)
        
        # 计算理论水深
        h_theory = compute_steady_uniform_flow(Q, B, S0, n)
        print(f"   理论水深（Manning公式）: {h_theory:.4f} m")
        
        # 求解稳态
        print(f"   开始稳态求解...")
        result = solver.solve_steady_state(
            Q_target=Q,
            h_downstream=h_theory,  # 使用理论水深作为下游边界
            max_iterations=100,
            convergence_tol=0.01,
            verbose=False
        )
        
        print(f"   ✅ 稳态求解完成")
        print(f"   迭代次数: {result.get('iterations', 'N/A')}")
        print(f"   是否收敛: {result.get('converged', False)}")
        
        # 获取求解结果
        h = result.get('h', solver.h)
        Q_solved = solver.get_Q()
        
        h_mean = np.mean(h)
        Q_mean = np.mean(Q_solved)
        
        print(f"   求解水深: {h_mean:.4f} m")
        print(f"   求解流量: {Q_mean:.4f} m³/s")
        
        # 计算误差
        h_error = abs(h_mean - h_theory) / h_theory * 100
        Q_error = abs(Q_mean - Q) / Q * 100
        
        print(f"   水深误差: {h_error:.2f}%")
        print(f"   流量误差: {Q_error:.4f}%")
        
        # 验收标准（宽松）
        assert Q_error < 5.0, f"流量误差过大: {Q_error:.2f}%"
        assert h_error < 10.0, f"水深误差过大: {h_error:.2f}%"
        
        print(f"   ✅ 所有验收标准通过！")
        
    def test_04_水力学计算(self):
        """测试水力学计算函数"""
        print("\n" + "="*70)
        print("测试 4: 水力学计算函数")
        print("="*70)
        
        Q = 10.0
        B = 5.0
        S0 = 0.001
        n = 0.025
        
        h = compute_steady_uniform_flow(Q, B, S0, n)
        
        print(f"   流量 Q = {Q} m³/s")
        print(f"   渠宽 B = {B} m")
        print(f"   坡度 S0 = {S0}")
        print(f"   糙率 n = {n}")
        print(f"   ✅ 计算水深: h = {h:.4f} m")
        
        assert h > 0
        assert h < 10.0  # 合理范围

    def test_05_均匀目标快速返回保持均匀剖面(self):
        """当下游边界等于正常水深时，快速返回应保持物理一致的均匀流。"""
        Q = 10.0
        B = 5.0
        S0 = 0.001
        n = 0.025

        solver = HydrostaticCanalSolver(
            length=1000.0,
            nx=80,
            B=B,
            S0=S0,
            n=n,
        )

        h_normal = compute_steady_uniform_flow(Q, B, S0, n)
        result = solver.solve_steady_state(
            Q_target=Q,
            h_downstream=h_normal,
            max_iterations=50,
            convergence_tol=0.01,
            verbose=False,
        )

        assert result["converged"] is True
        assert result["iterations"] == 0
        assert np.allclose(solver.h, solver.h[0])
        assert np.mean(solver.get_Q()) == pytest.approx(Q, rel=1e-6)


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
