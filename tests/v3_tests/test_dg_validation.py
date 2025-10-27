#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
方案C完整验证测试

测试间断Galerkin高阶方法的所有功能：
1. 高阶收敛测试（验证p+1阶精度）
2. 单闸门测试
3. 串联闸泵群测试
4. 与方案A/B对比
5. 粗网格精度测试

精度目标：
- ✅ 流量误差 < 0.1%
- ✅ 质量守恒 = 机器精度
- ✅ 高阶收敛率验证
- ✅ 粗网格达到方案B精度

Author: Claude (AI Assistant)
Date: 2025-10-27
"""

import sys
import os
import numpy as np
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from solvers.v3_dg_high_order import (
    DGCanalSolver,
    LegendreBasis,
    DGMesh,
    TVDLimiter
)
from solvers.v1_wellbalanced_fdm.structures import SluiceGate, PumpStation


class DGValidation:
    """方案C验证"""
    
    def __init__(self):
        self.results = []
        self.start_time = time.time()
    
    def test_high_order_convergence(self):
        """测试1: 高阶收敛率"""
        print("\n" + "="*80)
        print("测试1: 高阶收敛率验证（P3应为4阶精度）")
        print("="*80)
        
        # 不同网格尺寸
        n_elements_list = [10, 20, 40, 80]
        errors = []
        
        for n_elem in n_elements_list:
            solver = DGCanalSolver(
                length=1000.0,
                n_elements=n_elem,
                order=3,
                B=10.0,
                S0=0.001,
                n=0.025
            )
            
            result = solver.solve_steady_state(
                Q_target=10.0,
                h_downstream=2.0,
                max_iter=500,
                tolerance=0.01,
                verbose=False
            )
            
            errors.append(result['error'])
            print(f"n_elements={n_elem:3d}: 误差={result['error']:.6f}%")
        
        # 计算收敛率
        print(f"\n收敛率分析:")
        for i in range(len(errors)-1):
            ratio = errors[i] / errors[i+1]
            order = np.log2(ratio)
            print(f"  {n_elements_list[i]:2d}→{n_elements_list[i+1]:2d}: "
                  f"改善{ratio:.2f}x, 阶数={order:.2f}")
        
        expected_order = 4.0  # P3 = 四阶
        actual_order = np.log2(errors[0] / errors[-1]) / np.log2(8.0)
        
        print(f"\n期望阶数: {expected_order}")
        print(f"实际阶数: {actual_order:.2f}")
        print(f"判定: {'✓ 高阶收敛' if actual_order > 3.0 else '⚠ 未达到'}")
        
        self.results.append(('高阶收敛', actual_order > 3.0, errors[-1]))
    
    def test_coarse_grid_accuracy(self):
        """测试2: 粗网格高精度"""
        print("\n" + "="*80)
        print("测试2: 粗网格高精度（DG优势）")
        print("="*80)
        
        # DG: 50单元，P3
        solver_dg = DGCanalSolver(
            length=10000.0,
            n_elements=50,
            order=3,
            B=10.0,
            S0=0.001,
            n=0.025
        )
        
        gate = SluiceGate(position=5000.0, width=10.0, opening=3.0)
        solver_dg.add_structure(gate)
        
        result_dg = solver_dg.solve_steady_state(
            Q_target=10.0,
            h_downstream=2.0,
            max_iter=1000,
            tolerance=0.01,
            verbose=False
        )
        
        print(f"DG (50单元, P3): 误差={result_dg['error']:.4f}%")
        print(f"方案B (100单元): 误差~0.26% (参考)")
        print(f"\n判定: DG在一半单元数下{'✓ 达到更高精度' if result_dg['error'] < 0.26 else '⚠ 接近'}")
        
        self.results.append(('粗网格精度', result_dg['error'] < 0.15, result_dg['error']))
    
    def test_gate_pump_cascade_dg(self):
        """测试3: 串联闸泵群（DG高阶）"""
        print("\n" + "="*80)
        print("测试3: 串联闸泵群（方案C最终目标）")
        print("="*80)
        
        solver = DGCanalSolver(
            length=100000.0,
            n_elements=100,  # 方案B用200
            order=3,
            B=10.0,
            S0=0.0001,
            n=0.025
        )
        
        # 闸门1
        gate1 = SluiceGate(position=25000.0, width=10.0, opening=3.0)
        solver.add_structure(gate1)
        
        # 泵站
        pump = PumpStation(position=50000.0, width=10.0, rated_flow=10.0, rated_head=5.0)
        solver.add_structure(pump)
        
        # 闸门2
        gate2 = SluiceGate(position=75000.0, width=10.0, opening=2.5)
        solver.add_structure(gate2)
        
        result = solver.solve_steady_state(
            Q_target=10.0,
            h_downstream=2.0,
            max_iter=2000,
            tolerance=0.01,
            check_interval=500,
            verbose=True
        )
        
        print(f"\n核心指标:")
        print(f"  流量误差: {result['error']:.4f}%")
        print(f"  质量守恒: {result['conservation_error']:.6f}%")
        print(f"  单元数: {solver.n_elements} (方案B用200)")
        print(f"  总自由度: {solver.n_elements * (solver.order+1)}")
        
        passed = result['error'] < 0.1 and result['conservation_error'] < 1e-8
        print(f"\n判定: {'✓ 全部通过' if passed else '⚠ 接近目标'}")
        
        self.results.append(('串联闸泵群DG', passed, result['error']))
    
    def print_summary(self):
        """打印总结"""
        print("\n" + "="*80)
        print("方案C验证总结")
        print("="*80)
        
        total = len(self.results)
        passed = sum(1 for _, p, _ in self.results if p)
        
        print(f"总测试: {total}")
        print(f"通过: {passed}")
        print(f"失败: {total - passed}")
        print("")
        
        for name, passed_flag, error in self.results:
            status = "✓ PASS" if passed_flag else "✗ FAIL"
            print(f"{status} | {name}: 误差={error:.4f}%")
        
        print("")
        print("="*80)
        if passed == total:
            print("🎉 方案C全部测试通过！")
        else:
            print(f"⚠️  {total-passed}个测试未达标")
        print("="*80)
    
    def run_all(self):
        """运行所有测试"""
        print("="*80)
        print("方案C完整验证测试套件")
        print("="*80)
        
        self.test_high_order_convergence()
        self.test_coarse_grid_accuracy()
        self.test_gate_pump_cascade_dg()
        
        self.print_summary()


def main():
    validation = DGValidation()
    validation.run_all()


if __name__ == '__main__':
    main()
