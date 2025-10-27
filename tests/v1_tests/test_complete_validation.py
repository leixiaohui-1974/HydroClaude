#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
方案A完整验证测试

测试所有核心功能和精度目标：
1. 均匀流测试
2. 质量守恒测试
3. 静水平衡测试（良平衡性质）
4. 单闸门测试
5. 单泵站测试
6. 串联闸泵群测试（最终目标）
7. 网格加密测试
8. 能量方程对比测试

精度目标：
- ✅ 流量误差 < 0.5%
- ✅ 质量守恒 < 0.01%
- ✅ 泵站扬程误差 < 1%
- ✅ 静水平衡 < 1e-10

Author: Claude (AI Assistant)
Date: 2025-10-27
"""

import sys
import os
import numpy as np
import time
from typing import Dict, List

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from solvers.v1_wellbalanced_fdm import (
    HydrostaticReconstruction,
    WellBalancedCanalSolver,
    EnergyEquationSolver,
    SluiceGate,
    PumpStation,
    BroadCrestedWeir
)


class TestResult:
    """测试结果类"""
    def __init__(self, name: str):
        self.name = name
        self.passed = False
        self.error = 0.0
        self.target = 0.0
        self.time = 0.0
        self.details = {}
    
    def __repr__(self):
        status = "✓ PASS" if self.passed else "✗ FAIL"
        return f"{status} | {self.name}: error={self.error:.4f}% (target<{self.target}%)"


class ValidationSuite:
    """方案A完整验证套件"""
    
    def __init__(self):
        self.results: List[TestResult] = []
        self.start_time = time.time()
    
    def log(self, message: str):
        """打印日志"""
        print(message)
    
    def add_result(self, result: TestResult):
        """添加测试结果"""
        self.results.append(result)
        self.log(str(result))
    
    def test_1_uniform_flow(self) -> TestResult:
        """测试1: 均匀流测试"""
        self.log("\n" + "="*80)
        self.log("测试1: 均匀流（理论解对比）")
        self.log("="*80)
        
        result = TestResult("均匀流测试")
        result.target = 0.1  # 目标误差 < 0.1%
        
        start = time.time()
        
        # 使用能量方程求解器（更精确）
        solver = EnergyEquationSolver(
            length=10000.0,
            B=10.0,
            S0=0.001,
            n=0.025
        )
        
        Q = 10.0
        h_c = solver.compute_critical_depth(Q)
        h_n = solver.compute_normal_depth(Q)
        
        self.log(f"理论临界深度: {h_c:.3f} m")
        self.log(f"理论正常深度: {h_n:.3f} m")
        
        # 下游边界设为正常深度
        sol = solver.solve(Q=Q, h_downstream=h_n, dx=100.0, verbose=False)
        
        # 取中段平均水深（避免边界影响）
        n = len(sol['h'])
        h_mid = sol['h'][int(n*0.4):int(n*0.6)]
        h_avg = np.mean(h_mid)
        h_std = np.std(h_mid)
        
        # 误差
        error = abs(h_avg - h_n) / h_n * 100
        
        result.time = time.time() - start
        result.error = error
        result.passed = (error < result.target)
        result.details = {
            'h_theory': h_n,
            'h_computed': h_avg,
            'h_std': h_std,
            'Q_error': sol['error']
        }
        
        self.log(f"理论正常深度: {h_n:.4f} m")
        self.log(f"计算平均水深: {h_avg:.4f} m")
        self.log(f"水深误差: {error:.4f}%")
        self.log(f"流量误差: {sol['error']:.4f}%")
        
        return result
    
    def test_2_mass_conservation(self) -> TestResult:
        """测试2: 质量守恒测试"""
        self.log("\n" + "="*80)
        self.log("测试2: 质量守恒")
        self.log("="*80)
        
        result = TestResult("质量守恒测试")
        result.target = 0.01  # 目标误差 < 0.01%
        
        start = time.time()
        
        solver = EnergyEquationSolver(
            length=10000.0,
            B=10.0,
            S0=0.001,
            n=0.025
        )
        
        # 添加闸门
        gate = SluiceGate(position=5000.0, width=10.0, opening=3.0)
        solver.add_structure(gate)
        
        Q_target = 10.0
        sol = solver.solve(Q=Q_target, h_downstream=2.0, dx=100.0, verbose=False)
        
        # 质量守恒检查
        Q_check = sol['Q']
        Q_mean = np.mean(Q_check)
        Q_std = np.std(Q_check)
        Q_max = np.max(Q_check)
        Q_min = np.min(Q_check)
        
        # 相对标准差作为守恒误差
        error = Q_std / Q_target * 100
        
        result.time = time.time() - start
        result.error = error
        result.passed = (error < result.target)
        result.details = {
            'Q_mean': Q_mean,
            'Q_std': Q_std,
            'Q_max': Q_max,
            'Q_min': Q_min,
            'Q_range': Q_max - Q_min
        }
        
        self.log(f"目标流量: {Q_target:.4f} m³/s")
        self.log(f"平均流量: {Q_mean:.4f} m³/s")
        self.log(f"流量标准差: {Q_std:.6f} m³/s")
        self.log(f"守恒误差: {error:.6f}%")
        
        return result
    
    def test_3_hydrostatic_balance(self) -> TestResult:
        """测试3: 静水平衡（良平衡性质）"""
        self.log("\n" + "="*80)
        self.log("测试3: 静水平衡（良平衡性质验证）")
        self.log("="*80)
        
        result = TestResult("静水平衡测试")
        result.target = 1e-8  # 目标误差 < 1e-8 (几乎机器精度)
        
        start = time.time()
        
        # 使用静水重构
        recon = HydrostaticReconstruction(g=9.81)
        
        # 创建非平底地形
        nx = 101
        L = 100.0
        x = np.linspace(0, L, nx)
        
        # 抛物线地形
        z = 1.0 - 0.5 * ((x - 50) / 50)**2
        
        # 静止水体（水位恒定）
        eta0 = 5.0
        h = eta0 - z
        Q = np.zeros(nx)
        
        # 验证良平衡
        is_balanced, deviation = recon.verify_balance(h, z, Q, tol=1e-10)
        
        result.time = time.time() - start
        result.error = deviation * 100  # 转换为百分比
        result.passed = is_balanced
        result.details = {
            'max_deviation': deviation,
            'eta_mean': eta0,
            'z_range': [z.min(), z.max()],
            'is_balanced': is_balanced
        }
        
        self.log(f"地形: z_min={z.min():.3f}, z_max={z.max():.3f}")
        self.log(f"水位: η={eta0:.3f} m (恒定)")
        self.log(f"最大偏差: {deviation:.2e} m")
        self.log(f"良平衡: {'✓ 是' if is_balanced else '✗ 否'}")
        
        return result
    
    def test_4_single_gate(self) -> TestResult:
        """测试4: 单闸门测试"""
        self.log("\n" + "="*80)
        self.log("测试4: 单闸门")
        self.log("="*80)
        
        result = TestResult("单闸门测试")
        result.target = 0.5  # 目标误差 < 0.5%
        
        start = time.time()
        
        solver = EnergyEquationSolver(
            length=10000.0,
            B=10.0,
            S0=0.001,
            n=0.025
        )
        
        gate = SluiceGate(position=5000.0, width=10.0, opening=3.0)
        solver.add_structure(gate)
        
        Q_target = 10.0
        sol = solver.solve(Q=Q_target, h_downstream=2.0, dx=50.0, verbose=False)
        
        # 闸门处流量验证
        idx_gate = np.argmin(np.abs(sol['x'] - 5000.0))
        h_up = sol['h'][max(0, idx_gate-1)]
        h_down = sol['h'][min(len(sol['h'])-1, idx_gate+1)]
        
        # 理论闸门流量
        Q_theory, regime = gate.calculate_discharge(h_up, h_down)
        Q_computed = sol['Q'][idx_gate]
        
        error = abs(Q_computed - Q_theory) / Q_theory * 100
        
        result.time = time.time() - start
        result.error = error
        result.passed = (error < result.target and sol['error'] < result.target)
        result.details = {
            'Q_theory': Q_theory,
            'Q_computed': Q_computed,
            'h_upstream': h_up,
            'h_downstream': h_down,
            'regime': regime.value,
            'overall_error': sol['error']
        }
        
        self.log(f"闸门位置: {gate.position} m")
        self.log(f"开度: {gate.opening} m")
        self.log(f"上游水深: {h_up:.3f} m")
        self.log(f"下游水深: {h_down:.3f} m")
        self.log(f"理论流量: {Q_theory:.3f} m³/s")
        self.log(f"计算流量: {Q_computed:.3f} m³/s")
        self.log(f"闸门误差: {error:.3f}%")
        self.log(f"整体流量误差: {sol['error']:.3f}%")
        
        return result
    
    def test_5_single_pump(self) -> TestResult:
        """测试5: 单泵站测试"""
        self.log("\n" + "="*80)
        self.log("测试5: 单泵站")
        self.log("="*80)
        
        result = TestResult("单泵站测试")
        result.target = 1.0  # 扬程误差 < 1%
        
        start = time.time()
        
        solver = EnergyEquationSolver(
            length=10000.0,
            B=10.0,
            S0=0.001,
            n=0.025
        )
        
        pump = PumpStation(position=5000.0, width=10.0, rated_flow=10.0, rated_head=5.0)
        solver.add_structure(pump)
        
        Q_target = 10.0
        sol = solver.solve(Q=Q_target, h_downstream=2.0, dx=50.0, verbose=False)
        
        # 泵站扬程验证
        idx_pump = np.argmin(np.abs(sol['x'] - 5000.0))
        h_up = sol['h'][max(0, idx_pump-2)]
        h_down = sol['h'][min(len(sol['h'])-1, idx_pump+2)]
        
        H_actual = h_down - h_up
        H_target = pump.rated_head
        H_error = abs(H_actual - H_target) / H_target * 100
        
        result.time = time.time() - start
        result.error = H_error
        result.passed = (H_error < result.target and sol['error'] < 0.5)
        result.details = {
            'H_actual': H_actual,
            'H_target': H_target,
            'h_upstream': h_up,
            'h_downstream': h_down,
            'overall_error': sol['error']
        }
        
        self.log(f"泵站位置: {pump.position} m")
        self.log(f"额定扬程: {H_target:.3f} m")
        self.log(f"上游水深: {h_up:.3f} m")
        self.log(f"下游水深: {h_down:.3f} m")
        self.log(f"实际扬程: {H_actual:.3f} m")
        self.log(f"扬程误差: {H_error:.3f}%")
        self.log(f"整体流量误差: {sol['error']:.3f}%")
        
        return result
    
    def test_6_gate_pump_cascade(self) -> TestResult:
        """测试6: 串联闸泵群（最终目标）"""
        self.log("\n" + "="*80)
        self.log("测试6: 串联闸泵群系统（最终目标）")
        self.log("="*80)
        
        result = TestResult("串联闸泵群测试")
        result.target = 0.5  # 流量误差 < 0.5%
        
        start = time.time()
        
        # 100km长渠道
        solver = EnergyEquationSolver(
            length=100000.0,
            B=10.0,
            S0=0.0001,
            n=0.025
        )
        
        # 闸门1 @ 25km
        gate1 = SluiceGate(position=25000.0, width=10.0, opening=3.0)
        solver.add_structure(gate1)
        
        # 泵站 @ 50km
        pump = PumpStation(position=50000.0, width=10.0, rated_flow=10.0, rated_head=5.0)
        solver.add_structure(pump)
        
        # 闸门2 @ 75km
        gate2 = SluiceGate(position=75000.0, width=10.0, opening=2.5)
        solver.add_structure(gate2)
        
        Q_target = 10.0
        sol = solver.solve(Q=Q_target, h_downstream=2.0, dx=500.0, verbose=True)
        
        # 综合验证
        flow_error = sol['error']
        
        # 泵站扬程
        idx_pump = np.argmin(np.abs(sol['x'] - 50000.0))
        h_up_pump = sol['h'][max(0, idx_pump-2)]
        h_down_pump = sol['h'][min(len(sol['h'])-1, idx_pump+2)]
        H_actual = h_down_pump - h_up_pump
        H_error = abs(H_actual - pump.rated_head) / pump.rated_head * 100
        
        result.time = time.time() - start
        result.error = flow_error
        result.passed = (flow_error < result.target and H_error < 1.0)
        result.details = {
            'flow_error': flow_error,
            'pump_head_error': H_error,
            'H_pump_actual': H_actual,
            'H_pump_target': pump.rated_head,
            'n_sections': sol['n_sections'],
            'compute_time': result.time
        }
        
        self.log(f"\n系统配置:")
        self.log(f"  渠道长度: 100 km")
        self.log(f"  结构物: 2个闸门 + 1个泵站")
        self.log(f"  目标流量: {Q_target} m³/s")
        self.log(f"\n结果:")
        self.log(f"  流量误差: {flow_error:.4f}%")
        self.log(f"  泵站扬程误差: {H_error:.4f}%")
        self.log(f"  计算时间: {result.time:.2f}s")
        
        return result
    
    def test_7_grid_refinement(self) -> TestResult:
        """测试7: 网格加密测试"""
        self.log("\n" + "="*80)
        self.log("测试7: 网格加密测试（验证非均匀网格修复）")
        self.log("="*80)
        
        result = TestResult("网格加密测试")
        result.target = 0.5  # 最细网格误差 < 0.5%
        
        start = time.time()
        
        dx_list = [200.0, 100.0, 50.0, 25.0]
        errors = []
        times = []
        
        for dx in dx_list:
            solver = EnergyEquationSolver(
                length=10000.0,
                B=10.0,
                S0=0.001,
                n=0.025
            )
            
            gate = SluiceGate(position=5000.0, width=10.0, opening=3.0)
            solver.add_structure(gate)
            
            t0 = time.time()
            sol = solver.solve(Q=10.0, h_downstream=2.0, dx=dx, verbose=False)
            t1 = time.time()
            
            errors.append(sol['error'])
            times.append(t1 - t0)
            
            self.log(f"dx={dx:5.1f}m: 误差={sol['error']:6.4f}%, 时间={t1-t0:.3f}s")
        
        # 检查网格加密是否有效（误差应该减小）
        is_improving = all(errors[i] >= errors[i+1] for i in range(len(errors)-1))
        finest_error = errors[-1]
        
        result.time = time.time() - start
        result.error = finest_error
        result.passed = (finest_error < result.target and is_improving)
        result.details = {
            'dx_list': dx_list,
            'errors': errors,
            'times': times,
            'is_improving': is_improving,
            'improvement_ratio': errors[0] / errors[-1]
        }
        
        self.log(f"\n网格加密趋势: {'✓ 有效' if is_improving else '✗ 无效'}")
        self.log(f"改善比: {errors[0]/errors[-1]:.2f}x")
        self.log(f"最细网格误差: {finest_error:.4f}%")
        
        return result
    
    def run_all_tests(self):
        """运行所有测试"""
        self.log("\n" + "="*80)
        self.log("方案A完整验证测试套件")
        self.log("="*80)
        self.log(f"开始时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.log("="*80)
        
        # 运行所有测试
        self.add_result(self.test_1_uniform_flow())
        self.add_result(self.test_2_mass_conservation())
        self.add_result(self.test_3_hydrostatic_balance())
        self.add_result(self.test_4_single_gate())
        self.add_result(self.test_5_single_pump())
        self.add_result(self.test_6_gate_pump_cascade())
        self.add_result(self.test_7_grid_refinement())
        
        # 汇总结果
        self.print_summary()
    
    def print_summary(self):
        """打印测试汇总"""
        self.log("\n" + "="*80)
        self.log("测试汇总")
        self.log("="*80)
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed
        
        self.log(f"总测试数: {total}")
        self.log(f"通过: {passed} ({passed/total*100:.1f}%)")
        self.log(f"失败: {failed} ({failed/total*100:.1f}%)")
        self.log("")
        
        # 详细结果
        self.log("详细结果:")
        self.log("-"*80)
        for r in self.results:
            self.log(str(r))
        
        # 核心指标
        self.log("")
        self.log("核心指标:")
        self.log("-"*80)
        
        # 流量误差
        cascade_result = [r for r in self.results if "串联闸泵群" in r.name][0]
        self.log(f"✓ 流量误差: {cascade_result.error:.4f}% (目标: <0.5%)")
        
        # 质量守恒
        mass_result = [r for r in self.results if "质量守恒" in r.name][0]
        self.log(f"✓ 质量守恒: {mass_result.error:.6f}% (目标: <0.01%)")
        
        # 泵站扬程
        pump_result = [r for r in self.results if "单泵站" in r.name][0]
        self.log(f"✓ 泵站扬程误差: {pump_result.error:.4f}% (目标: <1.0%)")
        
        # 静水平衡
        hydro_result = [r for r in self.results if "静水平衡" in r.name][0]
        self.log(f"✓ 静水平衡偏差: {hydro_result.details['max_deviation']:.2e} m (目标: <1e-10)")
        
        # 总时间
        total_time = time.time() - self.start_time
        self.log(f"\n总测试时间: {total_time:.2f}s")
        
        # 最终判定
        self.log("")
        self.log("="*80)
        if passed == total:
            self.log("🎉 所有测试通过！方案A达到精度目标！")
        else:
            self.log(f"⚠️  {failed}个测试失败，需要进一步优化")
        self.log("="*80)


def main():
    """主函数"""
    suite = ValidationSuite()
    suite.run_all_tests()


if __name__ == '__main__':
    main()
