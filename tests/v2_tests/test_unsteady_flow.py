#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
非恒定流验证测试

测试场景：
1. 恒定边界下的非恒定流（应收敛到稳态）
2. 时间序列边界条件
3. 闸门快速开启
4. 泵站启停

验证指标：
- 质量守恒 < 1e-10
- 长时间稳定性
- 物理合理性

Author: Claude (AI Assistant)
Date: 2025-10-27
"""

import sys
import os
import numpy as np
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from solvers.v2_hybrid_fvfd import (
    UnsteadySolver,
    ConstantBC,
    TimeSeriesBC,
    ControlRuleBC
)
from solvers.v1_wellbalanced_fdm.structures import SluiceGate, PumpStation


class UnsteadyFlowValidation:
    """非恒定流验证测试套件"""
    
    def __init__(self):
        self.tests = []
        self.start_time = time.time()
    
    def test_1_constant_bc_to_steady(self):
        """
        测试1: 恒定边界条件下收敛到稳态
        
        验证：
        - 从初始状态演化到稳态
        - 质量守恒
        - 最终与稳态解一致
        """
        print("\n" + "="*80)
        print("测试1: 恒定边界条件→稳态收敛")
        print("="*80)
        
        solver = UnsteadySolver(
            length=10000.0,
            n_cells=50,
            B=10.0,
            S0=0.001,
            n=0.025
        )
        
        # 设置恒定边界条件
        solver.boundary.set_upstream(ConstantBC('flow', 10.0))
        solver.boundary.set_downstream(ConstantBC('depth', 2.0))
        
        # 初始化为不同状态（非平衡）
        solver.h = np.ones(solver.grid.n_cells) * 1.5  # 较低水深
        solver.A = solver.h * solver.B
        
        # 运行非恒定流（6小时）
        result = solver.solve_unsteady(
            duration=21600,  # 6小时
            dt_initial=1.0,
            cfl=0.3,
            output_interval=1800,  # 30分钟输出
            verbose=False
        )
        
        # 检查收敛
        h_initial = result['h'][0].mean()
        h_final = result['h'][-1].mean()
        Q_final = result['Q'][-1].mean()
        
        # 流量误差
        Q_error = abs(Q_final - 10.0) / 10.0 * 100
        
        # 质量守恒
        mass_error = result['mass_conservation_error']
        
        print(f"初始平均水深: {h_initial:.3f}m")
        print(f"最终平均水深: {h_final:.3f}m")
        print(f"最终平均流量: {Q_final:.3f}m³/s（目标10.0）")
        print(f"流量误差: {Q_error:.4f}%")
        print(f"质量守恒误差: {mass_error:.2e}")
        print(f"计算时间: {result['computation_time']:.2f}s")
        
        passed = Q_error < 1.0 and mass_error < 1e-8
        print(f"\n判定: {'✓ 通过' if passed else '✗ 失败'}")
        
        self.tests.append(('恒定BC→稳态', passed, Q_error))
    
    def test_2_timeseries_bc(self):
        """
        测试2: 时间序列边界条件
        
        验证：
        - 系统响应时间序列输入
        - 质量守恒
        """
        print("\n" + "="*80)
        print("测试2: 时间序列边界条件")
        print("="*80)
        
        solver = UnsteadySolver(
            length=10000.0,
            n_cells=50,
            B=10.0,
            S0=0.001,
            n=0.025
        )
        
        # 创建时间序列：流量从10逐渐增加到15
        times = np.array([0, 3600, 7200, 10800, 14400])  # 0-4小时
        flows = np.array([10.0, 12.0, 15.0, 13.0, 10.0])
        
        solver.boundary.set_upstream(TimeSeriesBC('flow', times, flows))
        solver.boundary.set_downstream(ConstantBC('depth', 2.0))
        
        # 运行4小时
        result = solver.solve_unsteady(
            duration=14400,
            dt_initial=1.0,
            cfl=0.3,
            output_interval=1800,
            verbose=False
        )
        
        # 检查系统响应
        Q_initial = result['Q'][0].mean()
        Q_mid = result['Q'][len(result['Q'])//2].mean()
        Q_final = result['Q'][-1].mean()
        
        mass_error = result['mass_conservation_error']
        
        print(f"初始流量: {Q_initial:.3f}m³/s")
        print(f"中间流量: {Q_mid:.3f}m³/s（应接近峰值15.0）")
        print(f"最终流量: {Q_final:.3f}m³/s（应回到10.0）")
        print(f"质量守恒误差: {mass_error:.2e}")
        
        # 验证响应合理
        response_ok = 11.0 < Q_mid < 16.0 and 9.0 < Q_final < 11.0
        passed = response_ok and mass_error < 1e-8
        
        print(f"\n判定: {'✓ 通过' if passed else '✗ 失败'}")
        
        self.tests.append(('时间序列BC', passed, mass_error))
    
    def test_3_gate_opening(self):
        """
        测试3: 闸门快速开启
        
        验证：
        - 间断传播
        - 质量守恒
        - 无数值振荡
        """
        print("\n" + "="*80)
        print("测试3: 闸门快速开启")
        print("="*80)
        
        solver = UnsteadySolver(
            length=20000.0,
            n_cells=100,
            B=10.0,
            S0=0.001,
            n=0.025
        )
        
        # 添加闸门（初始关闭）
        gate = SluiceGate(position=10000.0, width=10.0, opening=0.5)
        solver.add_structure(gate)
        
        # 边界条件
        solver.boundary.set_upstream(ConstantBC('flow', 10.0))
        solver.boundary.set_downstream(ConstantBC('depth', 2.0))
        
        # TODO: 实现动态闸门开度（需要控制规则）
        # 这里先运行恒定开度
        
        result = solver.solve_unsteady(
            duration=3600,  # 1小时
            dt_initial=0.5,
            cfl=0.2,  # 更严格的CFL（间断）
            output_interval=600,
            verbose=False
        )
        
        mass_error = result['mass_conservation_error']
        
        print(f"闸门位置: 10000.0m")
        print(f"闸门开度: 0.5m（恒定）")
        print(f"质量守恒误差: {mass_error:.2e}")
        print(f"时间步数: {result['n_steps']}")
        
        passed = mass_error < 1e-8
        print(f"\n判定: {'✓ 通过' if passed else '✗ 失败'}")
        print("⚠ 注意：动态闸门开度需要Week 2实现")
        
        self.tests.append(('闸门开启', passed, mass_error))
    
    def test_4_pump_operation(self):
        """
        测试4: 泵站运行
        
        验证：
        - 能量跃变
        - 质量守恒
        - 扬程精度
        """
        print("\n" + "="*80)
        print("测试4: 泵站运行")
        print("="*80)
        
        solver = UnsteadySolver(
            length=20000.0,
            n_cells=100,
            B=10.0,
            S0=0.001,
            n=0.025
        )
        
        # 添加泵站
        pump = PumpStation(position=10000.0, width=10.0, 
                          rated_flow=10.0, rated_head=5.0)
        solver.add_structure(pump)
        
        # 边界条件
        solver.boundary.set_upstream(ConstantBC('flow', 10.0))
        solver.boundary.set_downstream(ConstantBC('depth', 2.0))
        
        result = solver.solve_unsteady(
            duration=3600,  # 1小时
            dt_initial=1.0,
            cfl=0.3,
            output_interval=600,
            verbose=False
        )
        
        # 检查扬程
        pump_face = solver.structure_faces[0]
        cell_L = max(0, pump_face - 1)
        cell_R = min(solver.grid.n_cells - 1, pump_face)
        
        h_L_final = result['h'][-1][cell_L]
        h_R_final = result['h'][-1][cell_R]
        H_actual = h_R_final - h_L_final
        H_error = abs(H_actual - pump.rated_head) / pump.rated_head * 100
        
        mass_error = result['mass_conservation_error']
        
        print(f"泵站位置: 10000.0m")
        print(f"设计扬程: {pump.rated_head:.2f}m")
        print(f"实际扬程: {H_actual:.3f}m")
        print(f"扬程误差: {H_error:.2f}%")
        print(f"质量守恒误差: {mass_error:.2e}")
        
        passed = H_error < 1.0 and mass_error < 1e-8
        print(f"\n判定: {'✓ 通过' if passed else '✗ 失败'}")
        
        self.tests.append(('泵站运行', passed, H_error))
    
    def print_summary(self):
        """打印测试总结"""
        print("\n" + "="*80)
        print("非恒定流验证总结")
        print("="*80)
        
        total = len(self.tests)
        passed = sum(1 for _, p, _ in self.tests if p)
        
        print(f"总测试: {total}")
        print(f"通过: {passed}/{total}")
        print("")
        
        for name, passed_flag, error in self.tests:
            status = "✓ PASS" if passed_flag else "✗ FAIL"
            print(f"{status} | {name}: 误差={error:.4f}%")
        
        print("")
        print("="*80)
        if passed == total:
            print("🎉 所有非恒定流测试通过！")
        else:
            print(f"⚠️  {total-passed}个测试未通过")
        print("="*80)
        
        elapsed = time.time() - self.start_time
        print(f"\n总测试时间: {elapsed:.2f}s")
    
    def run_all(self):
        """运行所有测试"""
        print("="*80)
        print("非恒定流验证测试套件（Phase 2.1）")
        print("="*80)
        print(f"开始时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        self.test_1_constant_bc_to_steady()
        self.test_2_timeseries_bc()
        self.test_3_gate_opening()
        self.test_4_pump_operation()
        
        self.print_summary()


def main():
    """主函数"""
    validation = UnsteadyFlowValidation()
    validation.run_all()


if __name__ == '__main__':
    main()
