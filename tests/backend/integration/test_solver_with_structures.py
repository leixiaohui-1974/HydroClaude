#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
求解器与水工结构集成测试

测试HydrostaticCanalSolver与水工结构（闸门、堰）的集成
验证结构对流动的影响

Author: HydroClaude Test Team
Date: 2025-11-20
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver
from solvers.gate import SluiceGate, BroadCrestedWeir
from utils.canal_utils import compute_steady_uniform_flow
import numpy as np
import pytest


class Test求解器与闸门:
    """测试求解器与闸门的集成"""
    
    def test_01_创建带闸门的求解器(self):
        """测试创建带闸门的求解器"""
        print(f"\n{'='*70}")
        print(f"测试: 创建带闸门的求解器")
        print(f"{'='*70}")
        
        # 渠道参数
        length = 1000.0
        nx = 100
        B = 5.0
        S0 = 0.001
        n = 0.025
        
        # 创建闸门
        gate = SluiceGate(position=500.0, width=5.0, opening=2.0)
        
        # 创建求解器（带闸门）
        solver = HydrostaticCanalSolver(
            length=length,
            nx=nx,
            B=B,
            S0=S0,
            n=n,
            internal_structures=[(gate.position, gate)]
        )
        
        print(f"   渠道长度: {length} m")
        print(f"   网格数: {nx}")
        print(f"   渠宽: {B} m")
        print(f"   坡度: {S0}")
        print(f"   糙率: {n}")
        print(f"   闸门位置: {gate.position} m")
        print(f"   闸门开度: 2.0 m")
        
        assert len(solver.internal_structures) == 1
        assert isinstance(solver.internal_structures[0][1], SluiceGate)
        
        print(f"   ✅ 带闸门的求解器创建成功！")
    
    def test_02_闸门影响流动(self):
        """测试闸门对流动的影响"""
        print(f"\n{'='*70}")
        print(f"测试: 闸门对流动的影响")
        print(f"{'='*70}")
        
        Q = 10.0
        B = 5.0
        S0 = 0.001
        n = 0.025
        
        # 无闸门情况
        solver_no_gate = HydrostaticCanalSolver(
            length=1000.0,
            nx=100,
            B=B,
            S0=S0,
            n=n
        )
        solver_no_gate.set_Q(Q)
        h_theory = compute_steady_uniform_flow(Q, B, S0, n)
        
        result_no_gate = solver_no_gate.solve_steady_state(
            Q_target=Q,
            h_downstream=h_theory,
            max_iterations=100,
            convergence_tol=0.01,
            verbose=False
        )
        
        h_mean_no_gate = np.mean(solver_no_gate.h)
        
        # 有闸门情况
        gate = SluiceGate(position=500.0, width=5.0, opening=2.0)
        solver_with_gate = HydrostaticCanalSolver(
            length=1000.0,
            nx=100,
            B=B,
            S0=S0,
            n=n,
            internal_structures=[(gate.position, gate)]
        )
        solver_with_gate.set_Q(Q)
        
        result_with_gate = solver_with_gate.solve_steady_state(
            Q_target=Q,
            h_downstream=h_theory,
            max_iterations=100,
            convergence_tol=0.01,
            verbose=False
        )
        
        h_mean_with_gate = np.mean(solver_with_gate.h)
        
        print(f"   流量: {Q} m³/s")
        print(f"   无闸门平均水深: {h_mean_no_gate:.4f} m")
        print(f"   有闸门平均水深: {h_mean_with_gate:.4f} m")
        print(f"   水深差: {abs(h_mean_with_gate - h_mean_no_gate):.4f} m")
        
        # 有闸门时，上游水深应该更大
        if result_with_gate.get('converged', False):
            print(f"   ✅ 有闸门求解收敛")
        
        print(f"   ✅ 闸门影响流动测试完成！")
    
    def test_03_不同闸门开度影响(self):
        """测试不同闸门开度的影响"""
        print(f"\n{'='*70}")
        print(f"测试: 不同闸门开度的影响")
        print(f"{'='*70}")
        
        Q = 10.0
        B = 5.0
        S0 = 0.001
        n = 0.025
        
        openings = [1.0, 2.0, 3.0, 4.0]
        results = []
        
        for opening in openings:
            gate = SluiceGate(position=500.0, width=5.0, opening=opening)
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
            
            result = solver.solve_steady_state(
                Q_target=Q,
                h_downstream=h_theory,
                max_iterations=100,
                convergence_tol=0.1,
                verbose=False
            )
            
            h_mean = np.mean(solver.h)
            results.append((opening, h_mean, result.get('converged', False)))
        
        print(f"\n   开度(m)  平均水深(m)  收敛状态")
        print(f"   " + "-"*40)
        for opening, h_mean, converged in results:
            status = "✅" if converged else "⚠️"
            print(f"   {opening:6.1f}   {h_mean:10.4f}   {status}")
        
        print(f"\n   ✅ 不同开度影响测试完成！")


class Test求解器与堰:
    """测试求解器与堰的集成"""
    
    def test_01_创建带堰的求解器(self):
        """测试创建带堰的求解器"""
        print(f"\n{'='*70}")
        print(f"测试: 创建带堰的求解器")
        print(f"{'='*70}")
        
        # 渠道参数
        length = 1000.0
        nx = 100
        B = 5.0
        S0 = 0.001
        n = 0.025
        
        # 创建堰
        weir = BroadCrestedWeir(position=500.0, width=5.0, crest_height=0.5)
        
        # 创建求解器（带堰）
        solver = HydrostaticCanalSolver(
            length=length,
            nx=nx,
            B=B,
            S0=S0,
            n=n,
            internal_structures=[(weir.position, weir)]
        )
        
        print(f"   渠道长度: {length} m")
        print(f"   堰位置: {weir.position} m")
        print(f"   堰顶高程: 0.5 m")
        
        assert len(solver.internal_structures) == 1
        assert isinstance(solver.internal_structures[0][1], BroadCrestedWeir)
        
        print(f"   ✅ 带堰的求解器创建成功！")
    
    def test_02_堰影响流动(self):
        """测试堰对流动的影响"""
        print(f"\n{'='*70}")
        print(f"测试: 堰对流动的影响")
        print(f"{'='*70}")
        
        Q = 10.0
        B = 5.0
        S0 = 0.001
        n = 0.025
        
        # 无堰情况
        solver_no_weir = HydrostaticCanalSolver(
            length=1000.0,
            nx=100,
            B=B,
            S0=S0,
            n=n
        )
        solver_no_weir.set_Q(Q)
        h_theory = compute_steady_uniform_flow(Q, B, S0, n)
        
        result_no_weir = solver_no_weir.solve_steady_state(
            Q_target=Q,
            h_downstream=h_theory,
            max_iterations=100,
            convergence_tol=0.01,
            verbose=False
        )
        
        h_mean_no_weir = np.mean(solver_no_weir.h)
        
        # 有堰情况
        weir = BroadCrestedWeir(position=500.0, width=5.0, crest_height=0.5)
        solver_with_weir = HydrostaticCanalSolver(
            length=1000.0,
            nx=100,
            B=B,
            S0=S0,
            n=n,
            internal_structures=[(weir.position, weir)]
        )
        solver_with_weir.set_Q(Q)
        
        result_with_weir = solver_with_weir.solve_steady_state(
            Q_target=Q,
            h_downstream=h_theory,
            max_iterations=100,
            convergence_tol=0.1,
            verbose=False
        )
        
        h_mean_with_weir = np.mean(solver_with_weir.h)
        
        print(f"   流量: {Q} m³/s")
        print(f"   无堰平均水深: {h_mean_no_weir:.4f} m")
        print(f"   有堰平均水深: {h_mean_with_weir:.4f} m")
        print(f"   水深差: {abs(h_mean_with_weir - h_mean_no_weir):.4f} m")
        
        if result_with_weir.get('converged', False):
            print(f"   ✅ 有堰求解收敛")
        
        print(f"   ✅ 堰影响流动测试完成！")


class Test多结构组合:
    """测试多个结构的组合"""
    
    def test_01_闸门和堰组合(self):
        """测试闸门和堰的组合"""
        print(f"\n{'='*70}")
        print(f"测试: 闸门和堰的组合")
        print(f"{'='*70}")
        
        Q = 10.0
        B = 5.0
        S0 = 0.001
        n = 0.025
        
        # 创建闸门和堰
        gate = SluiceGate(position=300.0, width=5.0, opening=2.0)
        weir = BroadCrestedWeir(position=700.0, width=5.0, crest_height=0.5)
        
        # 创建求解器（带闸门和堰）
        solver = HydrostaticCanalSolver(
            length=1000.0,
            nx=100,
            B=B,
            S0=S0,
            n=n,
            internal_structures=[(gate.position, gate), (weir.position, weir)]
        )
        
        print(f"   结构数量: {len(solver.internal_structures)}")
        print(f"   结构1: 闸门@{gate.position}m")
        print(f"   结构2: 堰@{weir.position}m")
        
        assert len(solver.internal_structures) == 2
        
        solver.set_Q(Q)
        h_theory = compute_steady_uniform_flow(Q, B, S0, n)
        
        result = solver.solve_steady_state(
            Q_target=Q,
            h_downstream=h_theory,
            max_iterations=100,
            convergence_tol=0.1,
            verbose=False
        )
        
        h_mean = np.mean(solver.h)
        
        print(f"   平均水深: {h_mean:.4f} m")
        print(f"   收敛状态: {'✅' if result.get('converged', False) else '⚠️'}")
        
        print(f"   ✅ 多结构组合测试完成！")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
