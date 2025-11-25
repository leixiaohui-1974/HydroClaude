#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HydrostaticCanalSolver 多场景测试

测试不同流量、坡度、糙率等参数组合
验证求解器的鲁棒性和精度

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


class Test多场景验证:
    """测试多种参数组合"""
    
    @pytest.mark.parametrize("Q,B,S0,n", [
        (5.0, 3.0, 0.001, 0.020),    # 小流量
        (10.0, 5.0, 0.001, 0.025),   # 中等流量
        (20.0, 8.0, 0.001, 0.030),   # 大流量
        (15.0, 6.0, 0.0005, 0.025),  # 缓坡
        (15.0, 6.0, 0.002, 0.025),   # 陡坡
    ])
    def test_不同参数组合(self, Q, B, S0, n):
        """测试不同的流量、渠宽、坡度、糙率组合"""
        print(f"\n{'='*70}")
        print(f"测试参数: Q={Q} m³/s, B={B} m, S0={S0}, n={n}")
        print(f"{'='*70}")
        
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
        print(f"   理论水深: {h_theory:.4f} m")
        
        # 求解
        result = solver.solve_steady_state(
            Q_target=Q,
            h_downstream=h_theory,
            max_iterations=100,
            convergence_tol=0.01,
            verbose=False
        )
        
        # 获取结果
        h = result.get('h', solver.h)
        Q_solved = solver.get_Q()
        
        h_mean = np.mean(h)
        Q_mean = np.mean(Q_solved)
        
        # 计算误差
        h_error = abs(h_mean - h_theory) / h_theory * 100
        Q_error = abs(Q_mean - Q) / Q * 100
        
        print(f"   求解水深: {h_mean:.4f} m")
        print(f"   求解流量: {Q_mean:.4f} m³/s")
        print(f"   水深误差: {h_error:.2f}%")
        print(f"   流量误差: {Q_error:.4f}%")
        print(f"   收敛: {result.get('converged', False)}")
        
        # 断言
        assert Q_error < 5.0, f"流量误差过大: {Q_error:.2f}%"
        assert h_error < 10.0, f"水深误差过大: {h_error:.2f}%"
        assert result.get('converged', False), "未收敛"
        
        print(f"   ✅ 测试通过！")
    
    def test_小流量场景(self):
        """测试小流量（Q < 5 m³/s）"""
        print(f"\n{'='*70}")
        print(f"测试: 小流量场景")
        print(f"{'='*70}")
        
        Q = 2.0
        B = 2.0
        S0 = 0.001
        n = 0.020
        
        solver = HydrostaticCanalSolver(
            length=500.0,
            nx=50,
            B=B,
            S0=S0,
            n=n
        )
        
        solver.set_Q(Q)
        h_theory = compute_steady_uniform_flow(Q, B, S0, n)
        
        print(f"   流量: {Q} m³/s")
        print(f"   理论水深: {h_theory:.4f} m")
        
        result = solver.solve_steady_state(
            Q_target=Q,
            h_downstream=h_theory,
            max_iterations=100,
            convergence_tol=0.01,
            verbose=False
        )
        
        h_mean = np.mean(result.get('h', solver.h))
        Q_mean = np.mean(solver.get_Q())
        
        Q_error = abs(Q_mean - Q) / Q * 100
        
        print(f"   求解水深: {h_mean:.4f} m")
        print(f"   求解流量: {Q_mean:.4f} m³/s")
        print(f"   流量误差: {Q_error:.4f}%")
        
        assert Q_error < 5.0
        print(f"   ✅ 小流量场景测试通过！")
    
    def test_大流量场景(self):
        """测试大流量（Q > 50 m³/s）"""
        print(f"\n{'='*70}")
        print(f"测试: 大流量场景")
        print(f"{'='*70}")
        
        Q = 50.0
        B = 15.0
        S0 = 0.001
        n = 0.030
        
        solver = HydrostaticCanalSolver(
            length=2000.0,
            nx=200,
            B=B,
            S0=S0,
            n=n
        )
        
        solver.set_Q(Q)
        h_theory = compute_steady_uniform_flow(Q, B, S0, n)
        
        print(f"   流量: {Q} m³/s")
        print(f"   理论水深: {h_theory:.4f} m")
        
        result = solver.solve_steady_state(
            Q_target=Q,
            h_downstream=h_theory,
            max_iterations=100,
            convergence_tol=0.01,
            verbose=False
        )
        
        h_mean = np.mean(result.get('h', solver.h))
        Q_mean = np.mean(solver.get_Q())
        
        Q_error = abs(Q_mean - Q) / Q * 100
        
        print(f"   求解水深: {h_mean:.4f} m")
        print(f"   求解流量: {Q_mean:.4f} m³/s")
        print(f"   流量误差: {Q_error:.4f}%")
        
        assert Q_error < 5.0
        print(f"   ✅ 大流量场景测试通过！")
    
    def test_缓坡渠道(self):
        """测试缓坡渠道（S0 < 0.0005）"""
        print(f"\n{'='*70}")
        print(f"测试: 缓坡渠道")
        print(f"{'='*70}")
        
        Q = 10.0
        B = 5.0
        S0 = 0.0002  # 非常缓的坡度
        n = 0.025
        
        solver = HydrostaticCanalSolver(
            length=1000.0,
            nx=100,
            B=B,
            S0=S0,
            n=n
        )
        
        solver.set_Q(Q)
        h_theory = compute_steady_uniform_flow(Q, B, S0, n)
        
        print(f"   坡度: {S0} (缓坡)")
        print(f"   理论水深: {h_theory:.4f} m")
        
        result = solver.solve_steady_state(
            Q_target=Q,
            h_downstream=h_theory,
            max_iterations=100,
            convergence_tol=0.01,
            verbose=False
        )
        
        h_mean = np.mean(result.get('h', solver.h))
        Q_mean = np.mean(solver.get_Q())
        
        Q_error = abs(Q_mean - Q) / Q * 100
        
        print(f"   求解水深: {h_mean:.4f} m")
        print(f"   流量误差: {Q_error:.4f}%")
        
        assert Q_error < 5.0
        print(f"   ✅ 缓坡渠道测试通过！")
    
    def test_陡坡渠道(self):
        """测试陡坡渠道（S0 > 0.005）"""
        print(f"\n{'='*70}")
        print(f"测试: 陡坡渠道")
        print(f"{'='*70}")
        
        Q = 10.0
        B = 5.0
        S0 = 0.01  # 较陡的坡度
        n = 0.025
        
        solver = HydrostaticCanalSolver(
            length=1000.0,
            nx=100,
            B=B,
            S0=S0,
            n=n
        )
        
        solver.set_Q(Q)
        h_theory = compute_steady_uniform_flow(Q, B, S0, n)
        
        print(f"   坡度: {S0} (陡坡)")
        print(f"   理论水深: {h_theory:.4f} m")
        
        result = solver.solve_steady_state(
            Q_target=Q,
            h_downstream=h_theory,
            max_iterations=100,
            convergence_tol=0.01,
            verbose=False
        )
        
        h_mean = np.mean(result.get('h', solver.h))
        Q_mean = np.mean(solver.get_Q())
        
        Q_error = abs(Q_mean - Q) / Q * 100
        
        print(f"   求解水深: {h_mean:.4f} m")
        print(f"   流量误差: {Q_error:.4f}%")
        
        assert Q_error < 5.0
        print(f"   ✅ 陡坡渠道测试通过！")
    
    def test_窄渠道(self):
        """测试窄渠道（B < 3m）"""
        print(f"\n{'='*70}")
        print(f"测试: 窄渠道")
        print(f"{'='*70}")
        
        Q = 5.0
        B = 2.0  # 窄渠道
        S0 = 0.001
        n = 0.025
        
        solver = HydrostaticCanalSolver(
            length=1000.0,
            nx=100,
            B=B,
            S0=S0,
            n=n
        )
        
        solver.set_Q(Q)
        h_theory = compute_steady_uniform_flow(Q, B, S0, n)
        
        print(f"   渠宽: {B} m (窄渠道)")
        print(f"   理论水深: {h_theory:.4f} m")
        print(f"   水深/渠宽比: {h_theory/B:.2f}")
        
        result = solver.solve_steady_state(
            Q_target=Q,
            h_downstream=h_theory,
            max_iterations=100,
            convergence_tol=0.01,
            verbose=False
        )
        
        h_mean = np.mean(result.get('h', solver.h))
        Q_mean = np.mean(solver.get_Q())
        
        Q_error = abs(Q_mean - Q) / Q * 100
        
        print(f"   求解水深: {h_mean:.4f} m")
        print(f"   流量误差: {Q_error:.4f}%")
        
        assert Q_error < 5.0
        print(f"   ✅ 窄渠道测试通过！")
    
    def test_宽渠道(self):
        """测试宽渠道（B > 20m）"""
        print(f"\n{'='*70}")
        print(f"测试: 宽渠道")
        print(f"{'='*70}")
        
        Q = 30.0
        B = 25.0  # 宽渠道
        S0 = 0.001
        n = 0.025
        
        solver = HydrostaticCanalSolver(
            length=1000.0,
            nx=100,
            B=B,
            S0=S0,
            n=n
        )
        
        solver.set_Q(Q)
        h_theory = compute_steady_uniform_flow(Q, B, S0, n)
        
        print(f"   渠宽: {B} m (宽渠道)")
        print(f"   理论水深: {h_theory:.4f} m")
        print(f"   水深/渠宽比: {h_theory/B:.2f}")
        
        result = solver.solve_steady_state(
            Q_target=Q,
            h_downstream=h_theory,
            max_iterations=100,
            convergence_tol=0.01,
            verbose=False
        )
        
        h_mean = np.mean(result.get('h', solver.h))
        Q_mean = np.mean(solver.get_Q())
        
        Q_error = abs(Q_mean - Q) / Q * 100
        
        print(f"   求解水深: {h_mean:.4f} m")
        print(f"   流量误差: {Q_error:.4f}%")
        
        assert Q_error < 5.0
        print(f"   ✅ 宽渠道测试通过！")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
