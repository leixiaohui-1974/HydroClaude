#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HydroClaude标准验证测试套件

包含国际标准测试案例和实际工程场景
用于系统化验证求解器性能
"""

import sys
sys.path.insert(0, '/workspace')

import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import json

from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver
from solvers.gate import SluiceGate, BroadCrestedWeir
from utils.canal_utils import compute_steady_uniform_flow, compute_critical_depth
from utils.result_validator import quick_validate_steady_state


class ValidationSuite:
    """标准验证测试套件"""
    
    def __init__(self):
        self.results = []
        self.summary = {
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'test_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def run_test(self, test_func, test_name, category):
        """运行单个测试"""
        print(f"\n{'='*80}")
        print(f"测试: {test_name}")
        print(f"分类: {category}")
        print(f"{'='*80}")
        
        try:
            result = test_func()
            result['test_name'] = test_name
            result['category'] = category
            result['status'] = 'PASS' if result.get('converged', False) else 'FAIL'
            self.results.append(result)
            
            if result['status'] == 'PASS':
                self.summary['passed_tests'] += 1
                print(f"\n 测试通过")
            else:
                self.summary['failed_tests'] += 1
                print(f"\n 测试失败")
            
            self.summary['total_tests'] += 1
            
        except Exception as e:
            print(f"\n 测试异常: {e}")
            self.results.append({
                'test_name': test_name,
                'category': category,
                'status': 'ERROR',
                'error': str(e)
            })
            self.summary['failed_tests'] += 1
            self.summary['total_tests'] += 1
    
    def generate_report(self):
        """生成测试报告"""
        print("\n" + "="*80)
        print("验证测试套件 - 综合报告")
        print("="*80)
        
        # 按分类统计
        categories = {}
        for result in self.results:
            cat = result.get('category', 'Unknown')
            if cat not in categories:
                categories[cat] = {'total': 0, 'passed': 0}
            categories[cat]['total'] += 1
            if result.get('status') == 'PASS':
                categories[cat]['passed'] += 1
        
        # 打印分类统计
        print(f"\n按分类统计:")
        print(f"{'分类':<20} {'通过/总数':<15} {'通过率':<10}")
        print("-"*80)
        for cat, stats in categories.items():
            pass_rate = stats['passed'] / stats['total'] * 100 if stats['total'] > 0 else 0
            print(f"{cat:<20} {stats['passed']}/{stats['total']:<14} {pass_rate:>6.1f}%")
        
        # 打印详细结果
        print(f"\n详细测试结果:")
        print(f"{'测试名称':<40} {'分类':<15} {'流量误差':<12} {'状态':<8}")
        print("-"*80)
        
        for result in self.results:
            name = result.get('test_name', 'Unknown')[:39]
            cat = result.get('category', 'Unknown')[:14]
            
            if 'validator' in result and result['validator']:
                flow_result = result['validator'].results.get('flow_conservation', {})
                flow_error = flow_result.get('error_percent', 0.0)
                error_str = f"{flow_error:.6f}%"
            else:
                error_str = "N/A"
            
            status = result.get('status', 'UNKNOWN')
            status_symbol = "" if status == 'PASS' else ""
            
            print(f"{name:<40} {cat:<15} {error_str:<12} {status_symbol} {status}")
        
        # 总体统计
        print(f"\n总体统计:")
        print(f"  总测试数: {self.summary['total_tests']}")
        print(f"  通过: {self.summary['passed_tests']}")
        print(f"  失败: {self.summary['failed_tests']}")
        print(f"  通过率: {self.summary['passed_tests']/self.summary['total_tests']*100:.1f}%")
        
        # 性能评级
        pass_rate = self.summary['passed_tests']/self.summary['total_tests']*100 if self.summary['total_tests'] > 0 else 0
        
        print(f"\n性能评级:")
        if pass_rate == 100:
            print(f"  ⭐⭐⭐⭐⭐ 完美 (Perfect)")
        elif pass_rate >= 90:
            print(f"  ⭐⭐⭐⭐ 优秀 (Excellent)")
        elif pass_rate >= 75:
            print(f"  ⭐⭐⭐ 良好 (Good)")
        elif pass_rate >= 60:
            print(f"  ⭐⭐ 可接受 (Acceptable)")
        else:
            print(f"  ⭐ 需要改进 (Needs Improvement)")
        
        # 保存JSON报告
        report_path = f'/workspace/validation_cases/results/validation_suite_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump({
                'summary': self.summary,
                'results': self.results
            }, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n 详细报告已保存: {report_path}")
        
        return self.summary


# ==================== 测试案例定义 ====================

def test_uniform_flow_mild_slope():
    """测试1: 均匀流 - 缓坡"""
    L = 1000.0
    Q = 10.0
    B = 5.0
    S0 = 0.001
    n = 0.025
    
    solver = HydrostaticCanalSolver(length=L, nx=101, B=B, S0=S0, n=n)
    
    h_uniform = compute_steady_uniform_flow(Q, B, S0, n)
    
    result = solver.solve_steady_state(
        Q_target=Q,
        h_downstream=h_uniform,
        max_iterations=100,
        convergence_tol=0.1
    )
    
    validator = quick_validate_steady_state(
        solver=solver,
        result_dict=result,
        Q_target=Q,
        name="均匀流-缓坡"
    )
    
    return {
        'converged': result.get('converged', False),
        'iterations': result.get('iterations', 0),
        'h_uniform_theory': h_uniform,
        'h_uniform_computed': np.mean(solver.h),
        'validator': validator,
        'result': result
    }


def test_uniform_flow_steep_slope():
    """测试2: 均匀流 - 陡坡（超临界）"""
    L = 500.0
    Q = 20.0
    B = 6.0
    S0 = 0.01  # 陡坡
    n = 0.020
    
    solver = HydrostaticCanalSolver(length=L, nx=101, B=B, S0=S0, n=n)
    
    h_uniform = compute_steady_uniform_flow(Q, B, S0, n)
    
    result = solver.solve_steady_state(
        Q_target=Q,
        h_downstream=h_uniform * 0.9,
        max_iterations=100,
        convergence_tol=0.1
    )
    
    validator = quick_validate_steady_state(
        solver=solver,
        result_dict=result,
        Q_target=Q,
        name="均匀流-陡坡"
    )
    
    return {
        'converged': result.get('converged', False),
        'iterations': result.get('iterations', 0),
        'validator': validator,
        'result': result
    }


def test_m1_backwater_curve():
    """测试3: M1壅水曲线"""
    L = 5000.0
    Q = 100.0
    B = 20.0
    S0 = 0.0005
    n = 0.025
    
    solver = HydrostaticCanalSolver(length=L, nx=201, B=B, S0=S0, n=n)
    
    h_uniform = compute_steady_uniform_flow(Q, B, S0, n)
    h_downstream = h_uniform * 1.8  # 下游控制产生M1
    
    result = solver.solve_steady_state(
        Q_target=Q,
        h_downstream=h_downstream,
        max_iterations=150,
        convergence_tol=0.1
    )
    
    validator = quick_validate_steady_state(
        solver=solver,
        result_dict=result,
        Q_target=Q,
        name="M1壅水曲线"
    )
    
    return {
        'converged': result.get('converged', False),
        'iterations': result.get('iterations', 0),
        'validator': validator,
        'result': result
    }


def test_single_sluice_gate():
    """测试4: 单个闸门"""
    L = 2000.0
    Q = 30.0
    B = 10.0
    S0 = 0.0008
    n = 0.025
    
    gate = SluiceGate(position=1000.0, width=B, opening=2.5)
    solver = HydrostaticCanalSolver(
        length=L, nx=201, B=B, S0=S0, n=n,
        internal_structures=[(1000.0, gate)]
    )
    
    h_uniform = compute_steady_uniform_flow(Q, B, S0, n)
    
    result = solver.solve_steady_state(
        Q_target=Q,
        h_downstream=h_uniform * 1.3,
        max_iterations=150,
        convergence_tol=0.1
    )
    
    validator = quick_validate_steady_state(
        solver=solver,
        result_dict=result,
        Q_target=Q,
        name="单闸门"
    )
    
    return {
        'converged': result.get('converged', False),
        'iterations': result.get('iterations', 0),
        'validator': validator,
        'result': result
    }


def test_multiple_gates():
    """测试5: 多个闸门（串联）"""
    L = 3000.0
    Q = 40.0
    B = 12.0
    S0 = 0.001
    n = 0.022
    
    gate1 = SluiceGate(position=1000.0, width=B, opening=3.0)
    gate2 = SluiceGate(position=2000.0, width=B, opening=2.8)
    
    solver = HydrostaticCanalSolver(
        length=L, nx=301, B=B, S0=S0, n=n,
        internal_structures=[
            (1000.0, gate1),
            (2000.0, gate2)
        ]
    )
    
    h_uniform = compute_steady_uniform_flow(Q, B, S0, n)
    
    result = solver.solve_steady_state(
        Q_target=Q,
        h_downstream=h_uniform * 1.4,
        max_iterations=150,
        convergence_tol=0.1
    )
    
    validator = quick_validate_steady_state(
        solver=solver,
        result_dict=result,
        Q_target=Q,
        name="多闸门"
    )
    
    return {
        'converged': result.get('converged', False),
        'iterations': result.get('iterations', 0),
        'validator': validator,
        'result': result
    }


def test_broad_crested_weir():
    """测试6: 宽顶堰"""
    L = 1500.0
    Q = 25.0
    B = 8.0
    S0 = 0.0006
    n = 0.020
    
    weir = BroadCrestedWeir(position=750.0, width=B, crest_height=0.5)
    solver = HydrostaticCanalSolver(
        length=L, nx=151, B=B, S0=S0, n=n,
        internal_structures=[(750.0, weir)]
    )
    
    h_uniform = compute_steady_uniform_flow(Q, B, S0, n)
    
    result = solver.solve_steady_state(
        Q_target=Q,
        h_downstream=h_uniform * 1.2,
        max_iterations=150,
        convergence_tol=0.1
    )
    
    validator = quick_validate_steady_state(
        solver=solver,
        result_dict=result,
        Q_target=Q,
        name="宽顶堰"
    )
    
    return {
        'converged': result.get('converged', False),
        'iterations': result.get('iterations', 0),
        'validator': validator,
        'result': result
    }


def test_gate_and_weir():
    """测试7: 闸门+堰组合"""
    L = 2500.0
    Q = 35.0
    B = 10.0
    S0 = 0.0007
    n = 0.023
    
    gate = SluiceGate(position=1000.0, width=B, opening=2.8)
    weir = BroadCrestedWeir(position=1800.0, width=B, crest_height=0.4)
    
    solver = HydrostaticCanalSolver(
        length=L, nx=251, B=B, S0=S0, n=n,
        internal_structures=[
            (1000.0, gate),
            (1800.0, weir)
        ]
    )
    
    h_uniform = compute_steady_uniform_flow(Q, B, S0, n)
    
    result = solver.solve_steady_state(
        Q_target=Q,
        h_downstream=h_uniform * 1.3,
        max_iterations=150,
        convergence_tol=0.1
    )
    
    validator = quick_validate_steady_state(
        solver=solver,
        result_dict=result,
        Q_target=Q,
        name="闸门+堰"
    )
    
    return {
        'converged': result.get('converged', False),
        'iterations': result.get('iterations', 0),
        'validator': validator,
        'result': result
    }


def test_large_scale_canal():
    """测试8: 大尺度渠道（长距离）"""
    L = 20000.0  # 20km
    Q = 150.0
    B = 25.0
    S0 = 0.0003
    n = 0.020
    
    solver = HydrostaticCanalSolver(length=L, nx=401, B=B, S0=S0, n=n)
    
    h_uniform = compute_steady_uniform_flow(Q, B, S0, n)
    
    result = solver.solve_steady_state(
        Q_target=Q,
        h_downstream=h_uniform * 1.5,
        max_iterations=150,
        convergence_tol=0.1
    )
    
    validator = quick_validate_steady_state(
        solver=solver,
        result_dict=result,
        Q_target=Q,
        name="大尺度渠道"
    )
    
    return {
        'converged': result.get('converged', False),
        'iterations': result.get('iterations', 0),
        'validator': validator,
        'result': result
    }


def test_low_flow():
    """测试9: 小流量"""
    L = 1000.0
    Q = 1.0  # 小流量
    B = 3.0
    S0 = 0.002
    n = 0.030
    
    solver = HydrostaticCanalSolver(length=L, nx=101, B=B, S0=S0, n=n)
    
    h_uniform = compute_steady_uniform_flow(Q, B, S0, n)
    
    result = solver.solve_steady_state(
        Q_target=Q,
        h_downstream=h_uniform,
        max_iterations=100,
        convergence_tol=0.1
    )
    
    validator = quick_validate_steady_state(
        solver=solver,
        result_dict=result,
        Q_target=Q,
        name="小流量"
    )
    
    return {
        'converged': result.get('converged', False),
        'iterations': result.get('iterations', 0),
        'validator': validator,
        'result': result
    }


def test_high_flow():
    """测试10: 大流量"""
    L = 5000.0
    Q = 500.0  # 大流量
    B = 40.0
    S0 = 0.0002
    n = 0.018
    
    solver = HydrostaticCanalSolver(length=L, nx=251, B=B, S0=S0, n=n)
    
    h_uniform = compute_steady_uniform_flow(Q, B, S0, n)
    
    result = solver.solve_steady_state(
        Q_target=Q,
        h_downstream=h_uniform * 1.2,
        max_iterations=150,
        convergence_tol=0.1
    )
    
    validator = quick_validate_steady_state(
        solver=solver,
        result_dict=result,
        Q_target=Q,
        name="大流量"
    )
    
    return {
        'converged': result.get('converged', False),
        'iterations': result.get('iterations', 0),
        'validator': validator,
        'result': result
    }


def main():
    """主函数"""
    print("="*80)
    print("HydroClaude 标准验证测试套件")
    print("="*80)
    print("\n包含:")
    print("  - 基础流动测试（均匀流、壅水曲线）")
    print("  - 水工建筑物测试（闸门、堰）")
    print("  - 复杂场景测试（多结构、大尺度）")
    print("  - 极限条件测试（小流量、大流量）")
    
    suite = ValidationSuite()
    
    # 基础流动测试
    suite.run_test(test_uniform_flow_mild_slope, "均匀流-缓坡", "基础流动")
    suite.run_test(test_uniform_flow_steep_slope, "均匀流-陡坡", "基础流动")
    suite.run_test(test_m1_backwater_curve, "M1壅水曲线", "基础流动")
    
    # 水工建筑物测试
    suite.run_test(test_single_sluice_gate, "单闸门", "水工建筑物")
    suite.run_test(test_multiple_gates, "多闸门串联", "水工建筑物")
    suite.run_test(test_broad_crested_weir, "宽顶堰", "水工建筑物")
    suite.run_test(test_gate_and_weir, "闸门+堰组合", "水工建筑物")
    
    # 复杂场景测试
    suite.run_test(test_large_scale_canal, "大尺度渠道(20km)", "复杂场景")
    
    # 极限条件测试
    suite.run_test(test_low_flow, "小流量(1m³/s)", "极限条件")
    suite.run_test(test_high_flow, "大流量(500m³/s)", "极限条件")
    
    # 生成报告
    summary = suite.generate_report()
    
    print("\n" + "="*80)
    print("验证测试套件完成！")
    print("="*80)
    
    return summary


if __name__ == '__main__':
    main()
