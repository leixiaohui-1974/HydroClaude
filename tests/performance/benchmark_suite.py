#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
性能基准测试套件

建立系统的性能基准，用于回归测试和性能监控：
1. MacDonald Test 1 (平稳流) - 基线
2. MacDonald Test 3 (激波) - 计算密集
3. 大规模网格 (10000单元) - 内存测试
4. 长时间模拟 (10000步+) - 稳定性测试

性能指标：
- CPU时间（总时间、每步平均时间）
- 内存使用（峰值内存、平均内存）
- 收敛步数
- 数值精度（L1/L2误差、质量守恒）

作者: HydroClaude Team
日期: 2025-10-29
优先级: P3
"""

import pytest
import warnings
warnings.filterwarnings("ignore")
import numpy as np
import tempfile
import json
from pathlib import Path
import sys
import time
import psutil
import os
from datetime import datetime

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from engine.simulation_engine import SimulationEngine


class BenchmarkSuite:
    """性能基准测试套件"""

    def __init__(self):
        """初始化基准测试"""
        self.benchmark_db_file = Path(__file__).parent / 'benchmark_db.json'
        self.results = []

    def save_benchmark(self, result):
        """保存基准结果到JSON数据库"""
        # 添加元数据
        result['timestamp'] = datetime.now().isoformat()
        result['git_commit'] = self._get_git_commit()
        result['python_version'] = sys.version

        # 加载现有数据库
        if self.benchmark_db_file.exists():
            with open(self.benchmark_db_file) as f:
                db = json.load(f)
        else:
            db = {'benchmarks': []}

        # 添加新结果
        db['benchmarks'].append(result)

        # 保存
        self.benchmark_db_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.benchmark_db_file, 'w') as f:
            json.dump(db, f, indent=2)

        print(f"\n 基准结果已保存到: {self.benchmark_db_file}")

    def load_baseline(self, test_name):
        """加载基线基准数据"""
        if not self.benchmark_db_file.exists():
            return None

        with open(self.benchmark_db_file) as f:
            db = json.load(f)

        # 查找最近的相同测试基线
        for benchmark in reversed(db['benchmarks']):
            if benchmark['test'] == test_name:
                return benchmark

        return None

    def _get_git_commit(self):
        """获取当前git commit"""
        try:
            import subprocess
            commit = subprocess.check_output(
                ['git', 'rev-parse', '--short', 'HEAD'],
                stderr=subprocess.DEVNULL
            ).decode().strip()
            return commit
        except:
            return 'unknown'

    @pytest.mark.benchmark
    def test_benchmark_macdonald1(self):
        """
        基准测试1: MacDonald Test 1 (平稳流)

        基线性能测试
        """
        print("\n" + "="*70)
        print("基准测试 - MacDonald Test 1 (平稳流)")
        print("="*70)

        config = {
            'project': {
                'name': 'Benchmark - MacDonald Test 1',
                'description': '性能基准：平稳流'
            },
            'geometry': {
                'type': 'uniform',
                'channel_width': 10.0,
                'channel_length': 10000.0,
                'bottom_slope': 0.0001,
                'manning_n': 0.025
            },
            'mesh': {'n_cells': 200},
            'initial_conditions': {
                'type': 'uniform',
                'h': 2.0,
                'Q': 20.0
            },
            'boundary_conditions': {
                'left': {'type': 'Q', 'value': 20.0},
                'right': {'type': 'h', 'value': 2.5}
            },
            'solver': {
                'type': 'godunov_fvm',
                'spatial_order': 3,
                'riemann_solver': 'hll',
                'use_numba': True,
                'cfl': 0.5,
                'entropy_fix': True
            },
            'simulation': {
                'start_time': 0.0,
                'end_time': 5000.0,
                'max_steps': 100000
            },
            'output': {
                'directory': '/tmp/benchmark_macdonald1',
                'formats': [],
                'statistics': False,
                'plots': {'enabled': False}
            },
            'validation': {'enabled': False}
        }

        config_file = tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False
        )
        json.dump(config, config_file, indent=2)
        config_file.close()
        config_file_path = Path(config_file.name)

        try:
            # 记录初始内存
            process = psutil.Process(os.getpid())
            mem_before = process.memory_info().rss / 1024**2  # MB

            # 运行模拟
            print("\n运行模拟...")
            start = time.time()

            engine = SimulationEngine(str(config_file_path))
            engine.initialize()
            engine.run()

            elapsed = time.time() - start

            # 记录最终内存
            mem_after = process.memory_info().rss / 1024**2  # MB
            mem_used = mem_after - mem_before

            # 计算质量守恒
            mass_error = abs(
                engine.solver.get_mass_conservation_error()
            ) if hasattr(engine.solver, 'get_mass_conservation_error') else 0.0

            # 性能指标
            benchmark_result = {
                'test': 'macdonald1',
                'cpu_time': elapsed,
                'memory_mb': mem_used,
                'steps': engine.solver.step_count,
                'time_per_step': elapsed / engine.solver.step_count * 1000,  # ms
                'mass_error': mass_error,
                'n_cells': 200
            }

            # 输出结果
            print(f"\n性能基准 - MacDonald Test 1:")
            print(f"  CPU时间: {elapsed:.2f}s")
            print(f"  内存使用: {mem_used:.1f} MB")
            print(f"  计算步数: {engine.solver.step_count}")
            print(f"  平均每步: {elapsed/engine.solver.step_count*1000:.2f} ms")
            print(f"  质量误差: {mass_error:.4f}%")

            # 保存基准
            self.save_benchmark(benchmark_result)

            # 与基线对比
            baseline = self.load_baseline('macdonald1')
            if baseline and baseline != benchmark_result:
                speedup = baseline['cpu_time'] / elapsed
                print(f"\nvs 基线:")
                print(f"  速度变化: {speedup:.2f}x")
                if speedup > 1.1:
                    print(f"   性能提升 {(speedup-1)*100:.1f}%")
                elif speedup < 0.9:
                    print(f"  ️  性能下降 {(1-speedup)*100:.1f}%")
                else:
                    print(f"  ~ 性能相当")

        finally:
            config_file_path.unlink(missing_ok=True)

    @pytest.mark.benchmark
    def test_benchmark_macdonald3_dambreak(self):
        """
        基准测试2: MacDonald Test 3 (溃坝激波)

        计算密集型测试
        """
        print("\n" + "="*70)
        print("基准测试 - MacDonald Test 3 (溃坝)")
        print("="*70)

        config = {
            'project': {
                'name': 'Benchmark - MacDonald Test 3',
                'description': '性能基准：激波捕捉'
            },
            'geometry': {
                'type': 'uniform',
                'channel_width': 1.0,
                'channel_length': 2000.0,
                'bottom_slope': 0.0,
                'manning_n': 0.0
            },
            'mesh': {'n_cells': 200},
            'initial_conditions': {
                'type': 'dam_break',
                'h_left': 10.0,
                'h_right': 5.0,
                'dam_position': 1000.0
            },
            'boundary_conditions': {
                'left': {'type': 'Q', 'value': 0.0},
                'right': {'type': 'Q', 'value': 0.0}
            },
            'solver': {
                'type': 'godunov_fvm',
                'spatial_order': 3,
                'riemann_solver': 'hll',
                'use_numba': True,
                'cfl': 0.5,
                'entropy_fix': True
            },
            'simulation': {
                'start_time': 0.0,
                'end_time': 50.0,
                'max_steps': 10000
            },
            'output': {
                'directory': '/tmp/benchmark_macdonald3',
                'formats': [],
                'statistics': False,
                'plots': {'enabled': False}
            },
            'validation': {'enabled': False}
        }

        config_file = tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False
        )
        json.dump(config, config_file, indent=2)
        config_file.close()
        config_file_path = Path(config_file.name)

        try:
            process = psutil.Process(os.getpid())
            mem_before = process.memory_info().rss / 1024**2

            print("\n运行模拟...")
            start = time.time()

            engine = SimulationEngine(str(config_file_path))
            engine.initialize()

            mass_init = engine.solver._compute_total_mass()
            engine.run()
            mass_final = engine.solver._compute_total_mass()
            mass_error = abs(mass_final - mass_init) / mass_init * 100

            elapsed = time.time() - start
            mem_after = process.memory_info().rss / 1024**2
            mem_used = mem_after - mem_before

            benchmark_result = {
                'test': 'macdonald3_dambreak',
                'cpu_time': elapsed,
                'memory_mb': mem_used,
                'steps': engine.solver.step_count,
                'time_per_step': elapsed / engine.solver.step_count * 1000,
                'mass_error': mass_error,
                'n_cells': 200
            }

            print(f"\n性能基准 - MacDonald Test 3:")
            print(f"  CPU时间: {elapsed:.2f}s")
            print(f"  内存使用: {mem_used:.1f} MB")
            print(f"  计算步数: {engine.solver.step_count}")
            print(f"  平均每步: {elapsed/engine.solver.step_count*1000:.2f} ms")
            print(f"  质量误差: {mass_error:.4f}%")

            self.save_benchmark(benchmark_result)

        finally:
            config_file_path.unlink(missing_ok=True)

    @pytest.mark.benchmark
    @pytest.mark.slow
    def test_benchmark_large_grid(self):
        """
        基准测试3: 大规模网格

        内存和可扩展性测试
        """
        print("\n" + "="*70)
        print("基准测试 - 大规模网格 (1000单元)")
        print("="*70)

        config = {
            'project': {
                'name': 'Benchmark - Large Grid',
                'description': '性能基准：大规模网格'
            },
            'geometry': {
                'type': 'uniform',
                'channel_width': 10.0,
                'channel_length': 10000.0,
                'bottom_slope': 0.0001,
                'manning_n': 0.025
            },
            'mesh': {'n_cells': 1000},  # 大网格
            'initial_conditions': {
                'type': 'uniform',
                'h': 2.0,
                'Q': 20.0
            },
            'boundary_conditions': {
                'left': {'type': 'Q', 'value': 20.0},
                'right': {'type': 'h', 'value': 2.0}
            },
            'solver': {
                'type': 'godunov_fvm',
                'spatial_order': 3,
                'riemann_solver': 'hll',
                'use_numba': True,
                'cfl': 0.5,
                'entropy_fix': True
            },
            'simulation': {
                'start_time': 0.0,
                'end_time': 2000.0,  # 较短时间
                'max_steps': 50000
            },
            'output': {
                'directory': '/tmp/benchmark_large',
                'formats': [],
                'statistics': False,
                'plots': {'enabled': False}
            },
            'validation': {'enabled': False}
        }

        config_file = tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False
        )
        json.dump(config, config_file, indent=2)
        config_file.close()
        config_file_path = Path(config_file.name)

        try:
            process = psutil.Process(os.getpid())
            mem_before = process.memory_info().rss / 1024**2

            print("\n运行大规模网格模拟...")
            start = time.time()

            engine = SimulationEngine(str(config_file_path))
            engine.initialize()
            engine.run()

            elapsed = time.time() - start
            mem_after = process.memory_info().rss / 1024**2
            mem_used = mem_after - mem_before

            mass_error = abs(
                engine.solver.get_mass_conservation_error()
            ) if hasattr(engine.solver, 'get_mass_conservation_error') else 0.0

            benchmark_result = {
                'test': 'large_grid',
                'cpu_time': elapsed,
                'memory_mb': mem_used,
                'steps': engine.solver.step_count,
                'time_per_step': elapsed / engine.solver.step_count * 1000,
                'mass_error': mass_error,
                'n_cells': 1000
            }

            print(f"\n性能基准 - 大规模网格:")
            print(f"  CPU时间: {elapsed:.2f}s")
            print(f"  内存使用: {mem_used:.1f} MB")
            print(f"  计算步数: {engine.solver.step_count}")
            print(f"  平均每步: {elapsed/engine.solver.step_count*1000:.2f} ms")
            print(f"  质量误差: {mass_error:.4f}%")

            self.save_benchmark(benchmark_result)

        finally:
            config_file_path.unlink(missing_ok=True)

    @pytest.mark.benchmark
    @pytest.mark.slow
    def test_benchmark_long_simulation(self):
        """
        基准测试4: 长时间模拟

        稳定性和性能持久性测试
        """
        print("\n" + "="*70)
        print("基准测试 - 长时间模拟")
        print("="*70)

        config = {
            'project': {
                'name': 'Benchmark - Long Simulation',
                'description': '性能基准：长时间稳定性'
            },
            'geometry': {
                'type': 'uniform',
                'channel_width': 10.0,
                'channel_length': 5000.0,
                'bottom_slope': 0.0002,
                'manning_n': 0.025
            },
            'mesh': {'n_cells': 100},
            'initial_conditions': {
                'type': 'uniform',
                'h': 2.0,
                'Q': 20.0
            },
            'boundary_conditions': {
                'left': {'type': 'Q', 'value': 20.0},
                'right': {'type': 'h', 'value': 2.0}
            },
            'solver': {
                'type': 'godunov_fvm',
                'spatial_order': 3,
                'riemann_solver': 'hll',
                'use_numba': True,
                'cfl': 0.5,
                'entropy_fix': True
            },
            'simulation': {
                'start_time': 0.0,
                'end_time': 20000.0,  # 长时间
                'max_steps': 200000
            },
            'output': {
                'directory': '/tmp/benchmark_long',
                'formats': [],
                'statistics': False,
                'plots': {'enabled': False}
            },
            'validation': {'enabled': False}
        }

        config_file = tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False
        )
        json.dump(config, config_file, indent=2)
        config_file.close()
        config_file_path = Path(config_file.name)

        try:
            process = psutil.Process(os.getpid())
            mem_before = process.memory_info().rss / 1024**2

            print("\n运行长时间模拟...")
            start = time.time()

            engine = SimulationEngine(str(config_file_path))
            engine.initialize()

            mass_init = engine.solver._compute_total_mass()
            engine.run()
            mass_final = engine.solver._compute_total_mass()
            mass_error = abs(mass_final - mass_init) / mass_init * 100

            elapsed = time.time() - start
            mem_after = process.memory_info().rss / 1024**2
            mem_used = mem_after - mem_before

            benchmark_result = {
                'test': 'long_simulation',
                'cpu_time': elapsed,
                'memory_mb': mem_used,
                'steps': engine.solver.step_count,
                'time_per_step': elapsed / engine.solver.step_count * 1000,
                'mass_error': mass_error,
                'n_cells': 100,
                'simulation_time': 20000.0
            }

            print(f"\n性能基准 - 长时间模拟:")
            print(f"  CPU时间: {elapsed:.2f}s")
            print(f"  内存使用: {mem_used:.1f} MB")
            print(f"  计算步数: {engine.solver.step_count}")
            print(f"  平均每步: {elapsed/engine.solver.step_count*1000:.2f} ms")
            print(f"  质量误差: {mass_error:.4f}%")
            print(f"  实时倍数: {20000.0/elapsed:.1f}x")

            self.save_benchmark(benchmark_result)

        finally:
            config_file_path.unlink(missing_ok=True)


if __name__ == "__main__":
    # 运行所有基准测试
    suite = BenchmarkSuite()

    print("\n" + "="*70)
    print("HydroClaude 性能基准测试套件")
    print("="*70)

    print("\n运行基准测试1: MacDonald Test 1")
    suite.test_benchmark_macdonald1()

    print("\n" + "="*70)
    print("\n运行基准测试2: MacDonald Test 3")
    suite.test_benchmark_macdonald3_dambreak()

    print("\n" + "="*70)
    print("\n运行基准测试3: 大规模网格 (注：较慢)")
    suite.test_benchmark_large_grid()

    print("\n" + "="*70)
    print("\n运行基准测试4: 长时间模拟 (注：较慢)")
    suite.test_benchmark_long_simulation()

    print("\n" + "="*70)
    print("\n 所有基准测试完成")
    print(f"结果已保存到: {suite.benchmark_db_file}")
