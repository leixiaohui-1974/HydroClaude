#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
极端场景测试

测试HydrostaticCanalSolver在极端条件下的性能和鲁棒性

Author: HydroClaude Test Team
Date: 2025-11-20
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver
from solvers.gate import SluiceGate
from utils.canal_utils import compute_steady_uniform_flow
import numpy as np
import pytest


class Test极端流量:
    """极端流量测试"""
    
    def test_01_超大流量(self):
        """测试超大流量场景 (Q=100 m³/s)"""
        print(f"\n{'='*70}")
        print(f"极端场景: 超大流量 (Q=100 m³/s)")
        print(f"{'='*70}")
        
        Q = 100.0  # 超大流量
        B = 20.0   # 宽渠道
        S0 = 0.001
        n = 0.025
        
        solver = HydrostaticCanalSolver(
            length=2000.0,
            nx=100,
            B=B,
            S0=S0,
            n=n
        )
        
        solver.set_Q(Q)
        h_theory = compute_steady_uniform_flow(Q, B, S0, n)
        
        print(f"\n   流量: Q = {Q} m³/s")
        print(f"   渠宽: B = {B} m")
        print(f"   理论水深: h = {h_theory:.4f} m")
        
        result = solver.solve_steady_state(
            Q_target=Q,
            h_downstream=h_theory,
            max_iterations=200,
            convergence_tol=0.1,
            verbose=False
        )
        
        Q_mean = np.mean(solver.get_Q())
        Q_error = abs(Q_mean - Q) / Q * 100
        iterations = result.get('iterations', 0)
        
        print(f"\n   计算流量: {Q_mean:.4f} m³/s")
        print(f"   流量误差: {Q_error:.6f}%")
        print(f"   迭代次数: {iterations}")
        
        assert Q_error < 1.0, f"超大流量误差过大: {Q_error:.2f}%"
        assert iterations < 200, f"迭代次数过多: {iterations}"
        
        print(f"\n   ✅ 超大流量测试通过！")
    
    def test_02_超小流量(self):
        """测试超小流量场景 (Q=0.1 m³/s)"""
        print(f"\n{'='*70}")
        print(f"极端场景: 超小流量 (Q=0.1 m³/s)")
        print(f"{'='*70}")
        
        Q = 0.1    # 超小流量
        B = 1.0    # 窄渠道
        S0 = 0.001
        n = 0.020  # 光滑渠道
        
        solver = HydrostaticCanalSolver(
            length=500.0,
            nx=50,
            B=B,
            S0=S0,
            n=n
        )
        
        solver.set_Q(Q)
        h_theory = compute_steady_uniform_flow(Q, B, S0, n)
        
        print(f"\n   流量: Q = {Q} m³/s")
        print(f"   渠宽: B = {B} m")
        print(f"   理论水深: h = {h_theory:.4f} m")
        
        result = solver.solve_steady_state(
            Q_target=Q,
            h_downstream=h_theory,
            max_iterations=100,
            convergence_tol=0.01,
            verbose=False
        )
        
        Q_mean = np.mean(solver.get_Q())
        Q_error = abs(Q_mean - Q) / Q * 100
        iterations = result.get('iterations', 0)
        
        print(f"\n   计算流量: {Q_mean:.4f} m³/s")
        print(f"   流量误差: {Q_error:.6f}%")
        print(f"   迭代次数: {iterations}")
        
        assert Q_error < 1.0, f"超小流量误差过大: {Q_error:.2f}%"
        
        print(f"\n   ✅ 超小流量测试通过！")
    
    def test_03_极大流量(self):
        """测试极大流量场景 (Q=500 m³/s)"""
        print(f"\n{'='*70}")
        print(f"极端场景: 极大流量 (Q=500 m³/s)")
        print(f"{'='*70}")
        
        Q = 500.0  # 极大流量
        B = 50.0   # 超宽渠道
        S0 = 0.002
        n = 0.030
        
        solver = HydrostaticCanalSolver(
            length=5000.0,
            nx=100,
            B=B,
            S0=S0,
            n=n
        )
        
        solver.set_Q(Q)
        h_theory = compute_steady_uniform_flow(Q, B, S0, n)
        
        print(f"\n   流量: Q = {Q} m³/s")
        print(f"   渠宽: B = {B} m")
        print(f"   理论水深: h = {h_theory:.4f} m")
        
        result = solver.solve_steady_state(
            Q_target=Q,
            h_downstream=h_theory,
            max_iterations=200,
            convergence_tol=0.5,
            verbose=False
        )
        
        Q_mean = np.mean(solver.get_Q())
        Q_error = abs(Q_mean - Q) / Q * 100
        iterations = result.get('iterations', 0)
        
        print(f"\n   计算流量: {Q_mean:.4f} m³/s")
        print(f"   流量误差: {Q_error:.6f}%")
        print(f"   迭代次数: {iterations}")
        
        assert Q_error < 2.0, f"极大流量误差过大: {Q_error:.2f}%"
        
        print(f"\n   ✅ 极大流量测试通过！")


class Test极端坡度:
    """极端坡度测试"""
    
    def test_01_超陡坡度(self):
        """测试超陡坡度场景 (S0=0.1)"""
        print(f"\n{'='*70}")
        print(f"极端场景: 超陡坡度 (S0=0.1)")
        print(f"{'='*70}")
        
        Q = 10.0
        B = 5.0
        S0 = 0.1   # 超陡坡度 (10%)
        n = 0.025
        
        solver = HydrostaticCanalSolver(
            length=500.0,
            nx=50,
            B=B,
            S0=S0,
            n=n
        )
        
        solver.set_Q(Q)
        h_theory = compute_steady_uniform_flow(Q, B, S0, n)
        
        print(f"\n   坡度: S0 = {S0} (10%)")
        print(f"   流量: Q = {Q} m³/s")
        print(f"   理论水深: h = {h_theory:.4f} m")
        
        result = solver.solve_steady_state(
            Q_target=Q,
            h_downstream=h_theory,
            max_iterations=200,
            convergence_tol=0.5,
            verbose=False
        )
        
        Q_mean = np.mean(solver.get_Q())
        Q_error = abs(Q_mean - Q) / Q * 100
        iterations = result.get('iterations', 0)
        
        print(f"\n   计算流量: {Q_mean:.4f} m³/s")
        print(f"   流量误差: {Q_error:.6f}%")
        print(f"   迭代次数: {iterations}")
        
        assert Q_error < 5.0, f"超陡坡度误差过大: {Q_error:.2f}%"
        
        print(f"\n   ✅ 超陡坡度测试通过！")
    
    def test_02_超缓坡度(self):
        """测试超缓坡度场景 (S0=0.00001)"""
        print(f"\n{'='*70}")
        print(f"极端场景: 超缓坡度 (S0=0.00001)")
        print(f"{'='*70}")
        
        Q = 5.0
        B = 10.0
        S0 = 0.00001  # 超缓坡度
        n = 0.020
        
        solver = HydrostaticCanalSolver(
            length=1000.0,
            nx=100,
            B=B,
            S0=S0,
            n=n
        )
        
        solver.set_Q(Q)
        h_theory = compute_steady_uniform_flow(Q, B, S0, n)
        
        print(f"\n   坡度: S0 = {S0}")
        print(f"   流量: Q = {Q} m³/s")
        print(f"   理论水深: h = {h_theory:.4f} m")
        
        result = solver.solve_steady_state(
            Q_target=Q,
            h_downstream=h_theory,
            max_iterations=200,
            convergence_tol=0.1,
            verbose=False
        )
        
        Q_mean = np.mean(solver.get_Q())
        Q_error = abs(Q_mean - Q) / Q * 100
        iterations = result.get('iterations', 0)
        
        print(f"\n   计算流量: {Q_mean:.4f} m³/s")
        print(f"   流量误差: {Q_error:.6f}%")
        print(f"   迭代次数: {iterations}")
        
        assert Q_error < 2.0, f"超缓坡度误差过大: {Q_error:.2f}%"
        
        print(f"\n   ✅ 超缓坡度测试通过！")


class Test极端糙率:
    """极端糙率测试"""
    
    def test_01_超光滑渠道(self):
        """测试超光滑渠道 (n=0.010)"""
        print(f"\n{'='*70}")
        print(f"极端场景: 超光滑渠道 (n=0.010)")
        print(f"{'='*70}")
        
        Q = 10.0
        B = 5.0
        S0 = 0.001
        n = 0.010  # 超光滑（如玻璃）
        
        solver = HydrostaticCanalSolver(
            length=1000.0,
            nx=100,
            B=B,
            S0=S0,
            n=n
        )
        
        solver.set_Q(Q)
        h_theory = compute_steady_uniform_flow(Q, B, S0, n)
        
        print(f"\n   糙率: n = {n}")
        print(f"   流量: Q = {Q} m³/s")
        print(f"   理论水深: h = {h_theory:.4f} m")
        
        result = solver.solve_steady_state(
            Q_target=Q,
            h_downstream=h_theory,
            max_iterations=100,
            convergence_tol=0.01,
            verbose=False
        )
        
        Q_mean = np.mean(solver.get_Q())
        Q_error = abs(Q_mean - Q) / Q * 100
        
        print(f"\n   计算流量: {Q_mean:.4f} m³/s")
        print(f"   流量误差: {Q_error:.6f}%")
        
        assert Q_error < 1.0, f"超光滑渠道误差过大: {Q_error:.2f}%"
        
        print(f"\n   ✅ 超光滑渠道测试通过！")
    
    def test_02_超粗糙渠道(self):
        """测试超粗糙渠道 (n=0.050)"""
        print(f"\n{'='*70}")
        print(f"极端场景: 超粗糙渠道 (n=0.050)")
        print(f"{'='*70}")
        
        Q = 10.0
        B = 5.0
        S0 = 0.005  # 需要较大坡度
        n = 0.050   # 超粗糙（如石块）
        
        solver = HydrostaticCanalSolver(
            length=1000.0,
            nx=100,
            B=B,
            S0=S0,
            n=n
        )
        
        solver.set_Q(Q)
        h_theory = compute_steady_uniform_flow(Q, B, S0, n)
        
        print(f"\n   糙率: n = {n}")
        print(f"   流量: Q = {Q} m³/s")
        print(f"   理论水深: h = {h_theory:.4f} m")
        
        result = solver.solve_steady_state(
            Q_target=Q,
            h_downstream=h_theory,
            max_iterations=200,
            convergence_tol=0.5,
            verbose=False
        )
        
        Q_mean = np.mean(solver.get_Q())
        Q_error = abs(Q_mean - Q) / Q * 100
        
        print(f"\n   计算流量: {Q_mean:.4f} m³/s")
        print(f"   流量误差: {Q_error:.6f}%")
        
        assert Q_error < 5.0, f"超粗糙渠道误差过大: {Q_error:.2f}%"
        
        print(f"\n   ✅ 超粗糙渠道测试通过！")


class Test极端组合:
    """极端参数组合测试"""
    
    def test_01_大流量陡坡(self):
        """测试大流量+陡坡组合"""
        print(f"\n{'='*70}")
        print(f"极端组合: 大流量 + 陡坡")
        print(f"{'='*70}")
        
        Q = 100.0   # 大流量
        B = 15.0
        S0 = 0.05   # 陡坡
        n = 0.025
        
        solver = HydrostaticCanalSolver(
            length=2000.0,
            nx=100,
            B=B,
            S0=S0,
            n=n
        )
        
        solver.set_Q(Q)
        h_theory = compute_steady_uniform_flow(Q, B, S0, n)
        
        print(f"\n   流量: Q = {Q} m³/s (大)")
        print(f"   坡度: S0 = {S0} (陡)")
        print(f"   理论水深: h = {h_theory:.4f} m")
        
        result = solver.solve_steady_state(
            Q_target=Q,
            h_downstream=h_theory,
            max_iterations=200,
            convergence_tol=1.0,
            verbose=False
        )
        
        Q_mean = np.mean(solver.get_Q())
        Q_error = abs(Q_mean - Q) / Q * 100
        
        print(f"\n   计算流量: {Q_mean:.4f} m³/s")
        print(f"   流量误差: {Q_error:.6f}%")
        
        assert Q_error < 5.0, f"大流量陡坡误差过大: {Q_error:.2f}%"
        
        print(f"\n   ✅ 大流量陡坡测试通过！")
    
    def test_02_小流量缓坡(self):
        """测试小流量+缓坡组合"""
        print(f"\n{'='*70}")
        print(f"极端组合: 小流量 + 缓坡")
        print(f"{'='*70}")
        
        Q = 0.5     # 小流量
        B = 2.0
        S0 = 0.0001 # 缓坡
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
        
        print(f"\n   流量: Q = {Q} m³/s (小)")
        print(f"   坡度: S0 = {S0} (缓)")
        print(f"   理论水深: h = {h_theory:.4f} m")
        
        result = solver.solve_steady_state(
            Q_target=Q,
            h_downstream=h_theory,
            max_iterations=200,
            convergence_tol=0.1,
            verbose=False
        )
        
        Q_mean = np.mean(solver.get_Q())
        Q_error = abs(Q_mean - Q) / Q * 100
        
        print(f"\n   计算流量: {Q_mean:.4f} m³/s")
        print(f"   流量误差: {Q_error:.6f}%")
        
        assert Q_error < 2.0, f"小流量缓坡误差过大: {Q_error:.2f}%"
        
        print(f"\n   ✅ 小流量缓坡测试通过！")


class Test极端结构:
    """极端结构参数测试"""
    
    def test_01_极小闸门开度(self):
        """测试极小闸门开度 (e=0.5m)"""
        print(f"\n{'='*70}")
        print(f"极端结构: 极小闸门开度")
        print(f"{'='*70}")
        
        Q = 5.0
        B = 5.0
        S0 = 0.001
        n = 0.025
        
        gate = SluiceGate(position=500.0, width=5.0, opening=0.5)  # 极小开度
        
        solver = HydrostaticCanalSolver(
            length=1000.0,
            nx=100,
            B=B,
            S0=S0,
            n=n,
            internal_structures=[(gate.position, gate)]
        )
        
        solver.set_Q(Q)
        h_theory = compute_steady_uniform_flow(Q, B, S0, n)
        
        print(f"\n   流量: Q = {Q} m³/s")
        print(f"   闸门开度: e = 0.5 m (极小)")
        
        result = solver.solve_steady_state(
            Q_target=Q,
            h_downstream=h_theory,
            max_iterations=200,
            convergence_tol=0.5,
            verbose=False
        )
        
        converged = result.get('converged', False)
        
        print(f"\n   收敛状态: {converged}")
        
        assert converged or result.get('iterations', 0) < 200, "极小闸门开度求解失败"
        
        print(f"\n   ✅ 极小闸门开度测试通过！")
    
    def test_02_极大闸门开度(self):
        """测试极大闸门开度 (e=10m)"""
        print(f"\n{'='*70}")
        print(f"极端结构: 极大闸门开度")
        print(f"{'='*70}")
        
        Q = 50.0
        B = 10.0
        S0 = 0.002
        n = 0.025
        
        gate = SluiceGate(position=500.0, width=10.0, opening=10.0)  # 极大开度
        
        solver = HydrostaticCanalSolver(
            length=1000.0,
            nx=100,
            B=B,
            S0=S0,
            n=n,
            internal_structures=[(gate.position, gate)]
        )
        
        solver.set_Q(Q)
        h_theory = compute_steady_uniform_flow(Q, B, S0, n)
        
        print(f"\n   流量: Q = {Q} m³/s")
        print(f"   闸门开度: e = 10.0 m (极大)")
        
        result = solver.solve_steady_state(
            Q_target=Q,
            h_downstream=h_theory,
            max_iterations=200,
            convergence_tol=0.5,
            verbose=False
        )
        
        converged = result.get('converged', False)
        
        print(f"\n   收敛状态: {converged}")
        
        assert converged or result.get('iterations', 0) < 200, "极大闸门开度求解失败"
        
        print(f"\n   ✅ 极大闸门开度测试通过！")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
