#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Week 1：解析解自动验证测试

与精确解析解对比，验证数值方法的基本正确性和精度。

测试场景：
1. 均匀流（20个工况）
2. 临界流（10个工况）
3. 渐变流（5个工况）

验证指标：
- 水深误差 < 0.1%
- 流速误差 < 0.1%
- Froude数误差 < 0.5%
- 质量守恒 < 1e-12

Author: Claude (AI Assistant)
Date: 2025-10-27
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

# 导入解析解库
try:
    from tests.analytical_solutions import AnalyticalSolutions
except ImportError:
    from analytical_solutions import AnalyticalSolutions

# 导入求解器
from solvers.v2_hybrid_fvfd import HybridCanalSolver
from solvers.v1_wellbalanced_fdm import EnergyEquationSolver


class AnalyticalValidationTest:
    """解析解验证测试类"""
    
    def __init__(self):
        """初始化"""
        self.analytical = AnalyticalSolutions()
        self.test_results = []
        
        # 误差容限
        self.tolerances = {
            'depth': 0.001,      # 0.1%
            'velocity': 0.001,   # 0.1%
            'froude': 0.005,     # 0.5%
            'conservation': 1e-12  # 机器精度
        }
    
    #===========================================================================
    # 测试1：均匀流精度验证（最基础）
    #===========================================================================
    
    def test_uniform_flow_accuracy(self):
        """
        测试1：均匀流精度
        
        测试矩阵：
        - 流量: 5个水平（1, 5, 10, 50, 100 m³/s）
        - 坡度: 4个水平（0.0001, 0.001, 0.005, 0.01）
        - 糙率: 2个水平（0.015, 0.030）
        
        总计: 5×4×2 = 40个工况
        """
        print("\n" + "="*80)
        print("测试1：均匀流精度验证（与Manning解析解对比）")
        print("="*80)
        
        # 测试参数
        Q_values = [1.0, 5.0, 10.0, 50.0, 100.0]
        S0_values = [0.0001, 0.001, 0.005, 0.01]
        n_values = [0.015, 0.030]
        
        B = 10.0  # 渠宽
        length = 10000.0  # 10km
        
        passed = 0
        failed = 0
        
        for Q in Q_values:
            for S0 in S0_values:
                for n in n_values:
                    # ===== 解析解 =====
                    h_analytical = self.analytical.uniform_flow_depth(Q, B, S0, n)
                    u_analytical = self.analytical.uniform_flow_velocity(h_analytical, S0, n, B)
                    Fr_analytical = self.analytical.compute_froude_number(u_analytical, h_analytical)
                    
                    # ===== 数值解（方案B）=====
                    try:
                        solver = HybridCanalSolver(
                            length=length,
                            n_cells=100,
                            B=B,
                            S0=S0,
                            n=n
                        )
                        
                        result = solver.solve_steady_state(
                            Q_target=Q,
                            h_downstream=h_analytical,  # 使用解析解作为边界
                            max_iter=1000,
                            tolerance=0.01,
                            verbose=False
                        )
                        
                        # 取中点的值（远离边界）
                        mid_idx = len(result['h']) // 2
                        h_numerical = result['h'][mid_idx]
                        Q_numerical = result['Q'][mid_idx] if 'Q' in result else Q
                        u_numerical = Q_numerical / (B * h_numerical)
                        Fr_numerical = self.analytical.compute_froude_number(u_numerical, h_numerical)
                        
                        # ===== 计算误差 =====
                        error_h = abs(h_numerical - h_analytical) / h_analytical
                        error_u = abs(u_numerical - u_analytical) / u_analytical
                        error_Fr = abs(Fr_numerical - Fr_analytical) / Fr_analytical
                        error_Q = abs(Q_numerical - Q) / Q
                        
                        # ===== 判定 =====
                        test_passed = (
                            error_h < self.tolerances['depth'] and
                            error_u < self.tolerances['velocity'] and
                            error_Fr < self.tolerances['froude'] and
                            error_Q < self.tolerances['conservation']
                        )
                        
                        if test_passed:
                            status = "✓ PASS"
                            passed += 1
                        else:
                            status = "✗ FAIL"
                            failed += 1
                        
                        # 记录结果
                        self.test_results.append({
                            'test': 'uniform_flow',
                            'Q': Q,
                            'S0': S0,
                            'n': n,
                            'error_h': error_h * 100,
                            'error_u': error_u * 100,
                            'error_Fr': error_Fr * 100,
                            'error_Q': error_Q * 100,
                            'passed': test_passed,
                            'status': status
                        })
                        
                        # 打印（仅显示失败或关键案例）
                        if not test_passed or Q in [1.0, 100.0]:
                            print(f"{status} | Q={Q:5.1f}, S0={S0:.4f}, n={n:.3f} | "
                                  f"h_err={error_h*100:.3f}%, u_err={error_u*100:.3f}%, "
                                  f"Fr_err={error_Fr*100:.3f}%, Q_err={error_Q*100:.6f}%")
                    
                    except Exception as e:
                        print(f"✗ FAIL | Q={Q:5.1f}, S0={S0:.4f}, n={n:.3f} | 异常: {str(e)[:50]}")
                        failed += 1
                        self.test_results.append({
                            'test': 'uniform_flow',
                            'Q': Q,
                            'S0': S0,
                            'n': n,
                            'passed': False,
                            'status': '✗ FAIL',
                            'error': str(e)
                        })
        
        total = passed + failed
        print(f"\n总计: {total}个工况，通过: {passed}，失败: {failed}")
        print(f"通过率: {passed/total*100:.1f}%")
        
        return passed, failed
    
    #===========================================================================
    # 测试2：临界流验证
    #===========================================================================
    
    def test_critical_flow_accuracy(self):
        """
        测试2：临界流精度
        
        临界坡度渠道，Fr应精确等于1.0
        
        测试矩阵：
        - 流量: 10个水平（1-100 m³/s）
        
        验证：Fr数误差 < 0.5%
        """
        print("\n" + "="*80)
        print("测试2：临界流验证（Froude数应=1.0）")
        print("="*80)
        
        Q_values = np.logspace(0, 2, 10)  # 1-100 m³/s
        B = 10.0
        n = 0.025
        length = 10000.0
        
        passed = 0
        failed = 0
        
        for Q in Q_values:
            # 计算临界坡度
            S_c = self.analytical.critical_slope(Q, B, n)
            
            # 解析解
            h_c = self.analytical.critical_depth(Q, B)
            u_c = self.analytical.critical_velocity(h_c)
            Fr_analytical = 1.0  # 临界流Fr=1.0
            
            # 数值解
            try:
                solver = HybridCanalSolver(
                    length=length,
                    n_cells=100,
                    B=B,
                    S0=S_c,
                    n=n
                )
                
                result = solver.solve_steady_state(
                    Q_target=Q,
                    h_downstream=h_c,
                    max_iter=1000,
                    tolerance=0.01,
                    verbose=False
                )
                
                # 取中点
                mid_idx = len(result['h']) // 2
                h_numerical = result['h'][mid_idx]
                u_numerical = Q / (B * h_numerical)
                Fr_numerical = self.analytical.compute_froude_number(u_numerical, h_numerical)
                
                # 误差
                error_Fr = abs(Fr_numerical - 1.0)
                error_h = abs(h_numerical - h_c) / h_c
                
                # 判定
                test_passed = error_Fr < self.tolerances['froude']
                
                if test_passed:
                    status = "✓ PASS"
                    passed += 1
                else:
                    status = "✗ FAIL"
                    failed += 1
                
                print(f"{status} | Q={Q:6.2f} | Fr={Fr_numerical:.4f} (理论=1.0000) | "
                      f"Fr_err={error_Fr*100:.3f}%, h_err={error_h*100:.3f}%")
                
                self.test_results.append({
                    'test': 'critical_flow',
                    'Q': Q,
                    'Fr_numerical': Fr_numerical,
                    'error_Fr': error_Fr * 100,
                    'error_h': error_h * 100,
                    'passed': test_passed,
                    'status': status
                })
            
            except Exception as e:
                print(f"✗ FAIL | Q={Q:6.2f} | 异常: {str(e)[:50]}")
                failed += 1
        
        total = passed + failed
        print(f"\n总计: {total}个工况，通过: {passed}，失败: {failed}")
        print(f"通过率: {passed/total*100:.1f}%")
        
        return passed, failed
    
    #===========================================================================
    # 测试3：渐变流水面曲线
    #===========================================================================
    
    def test_gradually_varied_flow(self):
        """
        测试3：渐变流水面曲线
        
        与逐步积分法（准解析解）对比
        """
        print("\n" + "="*80)
        print("测试3：渐变流水面曲线（与逐步积分法对比）")
        print("="*80)
        
        # 测试工况
        Q = 10.0
        B = 10.0
        S0 = 0.001
        n = 0.025
        length = 10000.0
        
        # 均匀流水深（用作参考）
        h_n = self.analytical.uniform_flow_depth(Q, B, S0, n)
        
        # 下游边界：高于均匀流（M1曲线）
        h_downstream = h_n * 1.5
        
        # 解析解（逐步积分）
        analytical_solution = self.analytical.gradually_varied_flow(
            Q, B, S0, n, h_downstream, length, n_points=100
        )
        
        # 数值解
        try:
            solver = HybridCanalSolver(
                length=length,
                n_cells=100,
                B=B,
                S0=S0,
                n=n
            )
            
            result = solver.solve_steady_state(
                Q_target=Q,
                h_downstream=h_downstream,
                max_iter=2000,
                tolerance=0.01,
                verbose=False
            )
            
            # 对比关键点的水深
            comparison_points = [0.1, 0.3, 0.5, 0.7, 0.9]  # 相对位置
            
            print(f"\n关键点对比（渠道总长{length}m）：")
            print(f"{'位置(m)':<10} {'解析解(m)':<12} {'数值解(m)':<12} {'误差(%)':<10}")
            print("-" * 50)
            
            max_error = 0.0
            for rel_pos in comparison_points:
                x_pos = rel_pos * length
                
                # 解析解（插值）
                idx_ana = int(rel_pos * len(analytical_solution['h']))
                h_ana = analytical_solution['h'][idx_ana]
                
                # 数值解（插值）
                idx_num = int(rel_pos * len(result['h']))
                h_num = result['h'][idx_num]
                
                # 误差
                error = abs(h_num - h_ana) / h_ana * 100
                max_error = max(max_error, error)
                
                print(f"{x_pos:<10.0f} {h_ana:<12.4f} {h_num:<12.4f} {error:<10.3f}")
            
            # 判定
            test_passed = max_error < 1.0  # 渐变流容差放宽到1%
            status = "✓ PASS" if test_passed else "✗ FAIL"
            
            print(f"\n{status} | 最大误差: {max_error:.3f}% (容差=1.0%)")
            
            self.test_results.append({
                'test': 'gradually_varied_flow',
                'max_error': max_error,
                'passed': test_passed,
                'status': status
            })
            
            return (1, 0) if test_passed else (0, 1)
        
        except Exception as e:
            print(f"✗ FAIL | 异常: {str(e)}")
            return (0, 1)
    
    #===========================================================================
    # 生成详细报告
    #===========================================================================
    
    def generate_report(self, output_file: str = "week1_analytical_validation_report.md"):
        """
        生成详细的测试报告
        
        Args:
            output_file: 报告文件名
        """
        print("\n" + "="*80)
        print("生成Week 1测试报告")
        print("="*80)
        
        # 统计
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r['passed'])
        failed_tests = total_tests - passed_tests
        pass_rate = passed_tests / total_tests * 100 if total_tests > 0 else 0
        
        # 生成Markdown报告
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# Week 1: 解析解验证报告\n\n")
            f.write(f"**测试日期**: 2025-10-27\n")
            f.write(f"**测试目的**: 与精确解析解对比，验证数值方法基本正确性\n\n")
            
            f.write("## 📊 总体结果\n\n")
            f.write(f"- **总测试数**: {total_tests}\n")
            f.write(f"- **通过**: {passed_tests}\n")
            f.write(f"- **失败**: {failed_tests}\n")
            f.write(f"- **通过率**: {pass_rate:.1f}%\n\n")
            
            if pass_rate >= 95:
                f.write("✅ **结论**: 精度验证通过，数值方法正确性得到确认。\n\n")
            elif pass_rate >= 80:
                f.write("⚠️ **结论**: 大部分测试通过，但需要改进。\n\n")
            else:
                f.write("❌ **结论**: 大量测试失败，数值方法存在严重问题。\n\n")
            
            # 均匀流测试详情
            uniform_tests = [r for r in self.test_results if r['test'] == 'uniform_flow']
            if uniform_tests:
                f.write("## 测试1：均匀流精度\n\n")
                f.write(f"**测试数量**: {len(uniform_tests)}\n")
                passed_uniform = sum(1 for r in uniform_tests if r['passed'])
                f.write(f"**通过**: {passed_uniform}/{len(uniform_tests)}\n\n")
                
                f.write("### 失败案例\n\n")
                failed_uniform = [r for r in uniform_tests if not r['passed']]
                if failed_uniform:
                    f.write("| Q | S0 | n | h_err(%) | u_err(%) | Fr_err(%) |\n")
                    f.write("|---|----|----|----------|----------|----------|\n")
                    for r in failed_uniform[:10]:  # 仅显示前10个
                        f.write(f"| {r['Q']} | {r['S0']} | {r['n']} | "
                               f"{r.get('error_h', 0):.3f} | {r.get('error_u', 0):.3f} | "
                               f"{r.get('error_Fr', 0):.3f} |\n")
                else:
                    f.write("无失败案例。\n")
                f.write("\n")
            
            # 临界流测试详情
            critical_tests = [r for r in self.test_results if r['test'] == 'critical_flow']
            if critical_tests:
                f.write("## 测试2：临界流验证\n\n")
                f.write(f"**测试数量**: {len(critical_tests)}\n")
                passed_critical = sum(1 for r in critical_tests if r['passed'])
                f.write(f"**通过**: {passed_critical}/{len(critical_tests)}\n\n")
                
                # Froude数统计
                Fr_errors = [abs(r.get('Fr_numerical', 1.0) - 1.0) for r in critical_tests]
                if Fr_errors:
                    f.write(f"**Fr数最大误差**: {max(Fr_errors)*100:.3f}%\n")
                    f.write(f"**Fr数平均误差**: {np.mean(Fr_errors)*100:.3f}%\n\n")
            
            # 渐变流测试详情
            gvf_tests = [r for r in self.test_results if r['test'] == 'gradually_varied_flow']
            if gvf_tests:
                f.write("## 测试3：渐变流水面曲线\n\n")
                for r in gvf_tests:
                    f.write(f"**最大误差**: {r.get('max_error', 0):.3f}%\n")
                    f.write(f"**状态**: {r['status']}\n\n")
            
            f.write("---\n\n")
            f.write("**自动生成** | Week 1: 解析解验证\n")
        
        print(f"✅ 报告已保存: {output_file}")
    
    #===========================================================================
    # 运行所有测试
    #===========================================================================
    
    def run_all(self):
        """运行所有Week 1测试"""
        print("\n" + "="*80)
        print("Week 1: 解析解自动验证测试")
        print("目标: 与精确解析解对比，验证数值方法基本正确性")
        print("="*80)
        
        # 测试1：均匀流
        p1, f1 = self.test_uniform_flow_accuracy()
        
        # 测试2：临界流
        p2, f2 = self.test_critical_flow_accuracy()
        
        # 测试3：渐变流
        p3, f3 = self.test_gradually_varied_flow()
        
        # 总结
        total_passed = p1 + p2 + p3
        total_failed = f1 + f2 + f3
        total = total_passed + total_failed
        
        print("\n" + "="*80)
        print("Week 1 总结")
        print("="*80)
        print(f"总测试: {total}")
        print(f"通过: {total_passed}")
        print(f"失败: {total_failed}")
        print(f"通过率: {total_passed/total*100:.1f}%")
        
        if total_passed / total >= 0.95:
            print("\n✅ Week 1 验证通过！数值方法精度满足要求。")
        elif total_passed / total >= 0.80:
            print("\n⚠️ Week 1 部分通过，需要改进。")
        else:
            print("\n❌ Week 1 验证失败，需要修复核心问题。")
        
        # 生成报告
        self.generate_report()
        
        return total_passed, total_failed


def main():
    """主函数"""
    test = AnalyticalValidationTest()
    passed, failed = test.run_all()
    
    # 返回状态码
    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
