#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
性能基准测试

系统化测试不同规模问题的求解性能
"""

import sys
sys.path.insert(0, '/workspace')

import numpy as np
import time
import json
from datetime import datetime

from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver
from solvers.gate import SluiceGate
from utils.canal_utils import compute_steady_uniform_flow


class PerformanceBenchmark:
    """性能基准测试"""
    
    def __init__(self):
        self.results = []
    
    def benchmark_case(self, name, create_solver_func, solve_func, category="general"):
        """运行单个基准测试"""
        print(f"\n{'='*80}")
        print(f"基准测试: {name}")
        print(f"分类: {category}")
        print(f"{'='*80}")
        
        # 创建求解器
        start_setup = time.time()
        solver = create_solver_func()
        setup_time = time.time() - start_setup
        
        print(f"求解器设置时间: {setup_time*1000:.2f} ms")
        
        # 求解
        start_solve = time.time()
        result = solve_func(solver)
        solve_time = time.time() - start_solve
        
        converged = result.get('converged', False)
        iterations = result.get('iterations', 0)
        
        # 计算性能指标
        nx = solver.nx
        n_cells = nx - 1
        
        # 每次迭代的平均时间
        time_per_iteration = (solve_time / iterations * 1000) if iterations > 0 else solve_time * 1000
        
        # 每个单元的时间
        time_per_cell = (solve_time / n_cells * 1e6) if n_cells > 0 else 0  # microseconds
        
        print(f"\n性能指标:")
        print(f"  网格规模: {nx} 节点")
        print(f"  求解时间: {solve_time*1000:.2f} ms")
        print(f"  迭代次数: {iterations}")
        print(f"  每次迭代: {time_per_iteration:.2f} ms")
        print(f"  每单元时间: {time_per_cell:.2f} μs")
        print(f"  收敛: {'✅ 是' if converged else '❌ 否'}")
        
        # 保存结果
        benchmark_result = {
            'name': name,
            'category': category,
            'nx': nx,
            'setup_time_ms': setup_time * 1000,
            'solve_time_ms': solve_time * 1000,
            'iterations': iterations,
            'time_per_iteration_ms': time_per_iteration,
            'time_per_cell_us': time_per_cell,
            'converged': converged,
            'throughput_cells_per_sec': n_cells / solve_time if solve_time > 0 else 0
        }
        
        self.results.append(benchmark_result)
        
        return benchmark_result
    
    def generate_report(self):
        """生成性能报告"""
        print("\n" + "="*80)
        print("性能基准测试报告")
        print("="*80)
        
        # 按分类统计
        categories = {}
        for result in self.results:
            cat = result.get('category', 'general')
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(result)
        
        # 打印各分类结果
        for cat, results in categories.items():
            print(f"\n{cat}:")
            print(f"{'案例':<30} {'规模':<10} {'求解时间':<12} {'迭代':<6} {'收敛'}")
            print("-"*80)
            
            for res in results:
                name = res['name'][:29]
                nx = res['nx']
                solve_time = res['solve_time_ms']
                iterations = res['iterations']
                converged = "✅" if res['converged'] else "❌"
                
                print(f"{name:<30} {nx:<10} {solve_time:>10.2f} ms {iterations:<6} {converged}")
        
        # 总体统计
        print(f"\n总体统计:")
        total_tests = len(self.results)
        avg_solve_time = np.mean([r['solve_time_ms'] for r in self.results])
        avg_iterations = np.mean([r['iterations'] for r in self.results])
        success_rate = sum(1 for r in self.results if r['converged']) / total_tests * 100
        
        print(f"  测试案例数: {total_tests}")
        print(f"  平均求解时间: {avg_solve_time:.2f} ms")
        print(f"  平均迭代次数: {avg_iterations:.1f}")
        print(f"  收敛成功率: {success_rate:.1f}%")
        
        # 性能等级
        print(f"\n性能等级:")
        if avg_solve_time < 10:
            print(f"  ⭐⭐⭐⭐⭐ 极快 (< 10 ms)")
        elif avg_solve_time < 50:
            print(f"  ⭐⭐⭐⭐ 很快 (< 50 ms)")
        elif avg_solve_time < 200:
            print(f"  ⭐⭐⭐ 快速 (< 200 ms)")
        else:
            print(f"  ⭐⭐ 中等")
        
        # 保存JSON报告
        report_path = f'/workspace/validation_cases/results/performance_benchmark_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(report_path, 'w') as f:
            json.dump({
                'summary': {
                    'total_tests': total_tests,
                    'avg_solve_time_ms': avg_solve_time,
                    'avg_iterations': avg_iterations,
                    'success_rate': success_rate
                },
                'results': self.results
            }, f, indent=2)
        
        print(f"\n✅ 详细报告已保存: {report_path}")


# ==================== 基准测试案例定义 ====================

def bench_small_uniform():
    """小规模均匀流"""
    def create():
        return HydrostaticCanalSolver(length=1000.0, nx=51, B=5.0, S0=0.001, n=0.025)
    
    def solve(solver):
        Q = 10.0
        h = compute_steady_uniform_flow(Q, solver.B, solver.S0, solver.n)
        return solver.solve_steady_state(Q_target=Q, h_downstream=h, max_iterations=100)
    
    return create, solve


def bench_medium_uniform():
    """中等规模均匀流"""
    def create():
        return HydrostaticCanalSolver(length=5000.0, nx=201, B=10.0, S0=0.0008, n=0.025)
    
    def solve(solver):
        Q = 50.0
        h = compute_steady_uniform_flow(Q, solver.B, solver.S0, solver.n)
        return solver.solve_steady_state(Q_target=Q, h_downstream=h, max_iterations=100)
    
    return create, solve


def bench_large_uniform():
    """大规模均匀流"""
    def create():
        return HydrostaticCanalSolver(length=20000.0, nx=501, B=20.0, S0=0.0005, n=0.020)
    
    def solve(solver):
        Q = 200.0
        h = compute_steady_uniform_flow(Q, solver.B, solver.S0, solver.n)
        return solver.solve_steady_state(Q_target=Q, h_downstream=h, max_iterations=100)
    
    return create, solve


def bench_very_large_uniform():
    """超大规模均匀流"""
    def create():
        return HydrostaticCanalSolver(length=50000.0, nx=1001, B=30.0, S0=0.0003, n=0.020)
    
    def solve(solver):
        Q = 300.0
        h = compute_steady_uniform_flow(Q, solver.B, solver.S0, solver.n)
        return solver.solve_steady_state(Q_target=Q, h_downstream=h, max_iterations=100)
    
    return create, solve


def bench_backwater():
    """壅水曲线"""
    def create():
        return HydrostaticCanalSolver(length=10000.0, nx=301, B=15.0, S0=0.0005, n=0.025)
    
    def solve(solver):
        Q = 100.0
        h = compute_steady_uniform_flow(Q, solver.B, solver.S0, solver.n)
        return solver.solve_steady_state(Q_target=Q, h_downstream=h*1.8, max_iterations=150)
    
    return create, solve


def bench_single_gate():
    """单闸门"""
    def create():
        gate = SluiceGate(position=1000.0, width=10.0, opening=2.5)
        return HydrostaticCanalSolver(
            length=2000.0, nx=201, B=10.0, S0=0.0008, n=0.025,
            internal_structures=[(1000.0, gate)]
        )
    
    def solve(solver):
        Q = 30.0
        h = compute_steady_uniform_flow(Q, solver.B, solver.S0, solver.n)
        return solver.solve_steady_state(Q_target=Q, h_downstream=h*1.3, max_iterations=150)
    
    return create, solve


def bench_multiple_gates():
    """多闸门"""
    def create():
        gate1 = SluiceGate(position=1000.0, width=12.0, opening=3.0)
        gate2 = SluiceGate(position=2000.0, width=12.0, opening=2.8)
        gate3 = SluiceGate(position=3000.0, width=12.0, opening=3.0)
        return HydrostaticCanalSolver(
            length=4000.0, nx=401, B=12.0, S0=0.001, n=0.022,
            internal_structures=[
                (1000.0, gate1),
                (2000.0, gate2),
                (3000.0, gate3)
            ]
        )
    
    def solve(solver):
        Q = 50.0
        h = compute_steady_uniform_flow(Q, solver.B, solver.S0, solver.n)
        return solver.solve_steady_state(Q_target=Q, h_downstream=h*1.4, max_iterations=150)
    
    return create, solve


def bench_steep_slope():
    """陡坡（超临界）"""
    def create():
        return HydrostaticCanalSolver(length=1000.0, nx=101, B=6.0, S0=0.01, n=0.020)
    
    def solve(solver):
        Q = 30.0
        h = compute_steady_uniform_flow(Q, solver.B, solver.S0, solver.n)
        return solver.solve_steady_state(Q_target=Q, h_downstream=h*0.9, max_iterations=100)
    
    return create, solve


def bench_low_flow():
    """小流量"""
    def create():
        return HydrostaticCanalSolver(length=1000.0, nx=101, B=3.0, S0=0.002, n=0.030)
    
    def solve(solver):
        Q = 1.0
        h = compute_steady_uniform_flow(Q, solver.B, solver.S0, solver.n)
        return solver.solve_steady_state(Q_target=Q, h_downstream=h, max_iterations=100)
    
    return create, solve


def bench_high_flow():
    """大流量"""
    def create():
        return HydrostaticCanalSolver(length=8000.0, nx=301, B=40.0, S0=0.0002, n=0.018)
    
    def solve(solver):
        Q = 500.0
        h = compute_steady_uniform_flow(Q, solver.B, solver.S0, solver.n)
        return solver.solve_steady_state(Q_target=Q, h_downstream=h*1.2, max_iterations=150)
    
    return create, solve


def main():
    """主函数"""
    print("="*80)
    print("HydroClaude 性能基准测试")
    print("="*80)
    print("\n目标：系统化测试不同规模问题的求解性能")
    
    benchmark = PerformanceBenchmark()
    
    # 基础规模测试
    print("\n" + "="*80)
    print("1. 基础规模测试")
    print("="*80)
    
    create, solve = bench_small_uniform()
    benchmark.benchmark_case("小规模均匀流(L=1km, nx=51)", create, solve, "基础规模")
    
    create, solve = bench_medium_uniform()
    benchmark.benchmark_case("中等规模均匀流(L=5km, nx=201)", create, solve, "基础规模")
    
    create, solve = bench_large_uniform()
    benchmark.benchmark_case("大规模均匀流(L=20km, nx=501)", create, solve, "基础规模")
    
    create, solve = bench_very_large_uniform()
    benchmark.benchmark_case("超大规模均匀流(L=50km, nx=1001)", create, solve, "基础规模")
    
    # 复杂场景测试
    print("\n" + "="*80)
    print("2. 复杂场景测试")
    print("="*80)
    
    create, solve = bench_backwater()
    benchmark.benchmark_case("壅水曲线(L=10km)", create, solve, "复杂场景")
    
    create, solve = bench_single_gate()
    benchmark.benchmark_case("单闸门(L=2km)", create, solve, "复杂场景")
    
    create, solve = bench_multiple_gates()
    benchmark.benchmark_case("三闸门串联(L=4km)", create, solve, "复杂场景")
    
    # 特殊条件测试
    print("\n" + "="*80)
    print("3. 特殊条件测试")
    print("="*80)
    
    create, solve = bench_steep_slope()
    benchmark.benchmark_case("陡坡超临界流(S0=1%)", create, solve, "特殊条件")
    
    create, solve = bench_low_flow()
    benchmark.benchmark_case("小流量(Q=1m³/s)", create, solve, "特殊条件")
    
    create, solve = bench_high_flow()
    benchmark.benchmark_case("大流量(Q=500m³/s)", create, solve, "特殊条件")
    
    # 生成报告
    benchmark.generate_report()
    
    print("\n" + "="*80)
    print("性能基准测试完成！")
    print("="*80)


if __name__ == '__main__':
    main()
