#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Anderson加速参数调优

测试不同参数组合在闸门问题上的表现
目标：找到最优的(m, beta, reg)参数

作者: Claude
日期: 2025-10-22
"""

import numpy as np
import time
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from structures.sluice_gate import SluiceGate
from structures.weir import Weir
from structures.orifice import Orifice
from solvers.canal_solver import CanalSolver
from solvers.anderson_acceleration import AndersonAcceleration


def test_anderson_parameters():
    """
    测试Anderson加速参数的影响

    参数网格：
    - m: 历史深度 [3, 5, 7, 10]
    - beta: 松弛因子 [0.5, 0.7, 0.9, 1.0]
    - reg: 正则化 [1e-10, 1e-8, 1e-6]
    """

    print("=" * 100)
    print("Anderson加速参数调优")
    print("=" * 100)
    print()

    # 渠道参数
    length = 10000.0
    nx = 301
    B = 10.0
    S0 = 0.0005
    n = 0.025

    # 测试场景
    scenarios = []

    # 场景1：单闸门
    gate1 = SluiceGate(B=B, e=5.0, Cd=0.6)
    scenarios.append({
        'name': '单闸门',
        'structures': [{'x': 5000.0, 'structure': gate1}],
        'Q_target': 10.0
    })

    # 场景2：三闸门串联
    gate1 = SluiceGate(B=B, e=4.5, Cd=0.6)
    gate2 = SluiceGate(B=B, e=4.0, Cd=0.6)
    gate3 = SluiceGate(B=B, e=5.0, Cd=0.6)
    scenarios.append({
        'name': '三闸门',
        'structures': [
            {'x': 2500.0, 'structure': gate1},
            {'x': 5000.0, 'structure': gate2},
            {'x': 7500.0, 'structure': gate3}
        ],
        'Q_target': 10.0
    })

    # 场景3：混合结构
    gate = SluiceGate(B=B, e=3.5, Cd=0.6)
    weir = Weir(B=B, P=0.5, Cd=0.5)
    orifice = Orifice(B_orifice=4.0, H_orifice=2.0, z_bottom=0.2, Cd=0.6)
    scenarios.append({
        'name': '混合结构',
        'structures': [
            {'x': 2500.0, 'structure': gate},
            {'x': 5000.0, 'structure': weir},
            {'x': 7500.0, 'structure': orifice}
        ],
        'Q_target': 10.0
    })

    # 参数网格
    m_values = [3, 5, 7, 10]
    beta_values = [0.5, 0.7, 0.9, 1.0]
    reg_values = [1e-10, 1e-8, 1e-6]

    # 对于每个场景，测试参数组合
    for scenario in scenarios:
        print("\n" + "=" * 100)
        print(f"场景: {scenario['name']}")
        print("=" * 100)
        print()

        results = []

        # 基准：无Anderson加速（当前自适应Aitken）
        print("基准测试（自适应Aitken加速）...")
        solver = CanalSolver(
            length=length,
            nx=nx,
            B=B,
            S0=S0,
            n=n
        )
        for struct_info in scenario['structures']:
            solver.add_structure(struct_info['x'], struct_info['structure'])

        # 初始化为恒定均匀流
        h_init, Q_init = solver.compute_uniform_flow(scenario['Q_target'])
        solver.set_initial_conditions(h_init, Q_init)

        start_time = time.time()
        success = solver.solve_steady_state(
            Q_target=scenario['Q_target'],
            max_iter=20000,
            tol=0.01,
            adaptive_relax=True,
            verbose=False
        )
        elapsed = time.time() - start_time

        Q_avg = np.mean([solver.Q[idx] for idx in solver.structure_indices])
        error = abs(Q_avg - scenario['Q_target']) / scenario['Q_target'] * 100

        baseline_result = {
            'method': 'Baseline (Aitken)',
            'converged': success,
            'iterations': solver.steady_iteration_count,
            'error': error,
            'time': elapsed
        }
        results.append(baseline_result)

        print(f"  收敛: {'✓' if success else '✗'}")
        print(f"  迭代: {solver.steady_iteration_count}")
        print(f"  误差: {error:.4f}%")
        print(f"  时间: {elapsed:.4f}s")
        print()

        # 测试Anderson加速参数组合（选择性测试，避免过多组合）
        # 策略：固定两个参数，变化一个参数

        # 1. 测试m的影响（固定beta=1.0, reg=1e-8）
        print("测试历史深度m的影响（beta=1.0, reg=1e-8）")
        print("-" * 100)
        for m in m_values:
            print(f"  m={m}...", end=' ', flush=True)

            # 这里我们需要修改CanalSolver以支持Anderson加速
            # 由于当前CanalSolver没有集成Anderson，我们先记录参数
            # 实际测试将在集成后进行

            # 占位符：假设已集成
            result = {
                'method': f'Anderson(m={m})',
                'converged': None,
                'iterations': None,
                'error': None,
                'time': None,
                'params': {'m': m, 'beta': 1.0, 'reg': 1e-8}
            }
            results.append(result)
            print("待集成")

        # 2. 测试beta的影响（固定m=5, reg=1e-8）
        print("\n测试松弛因子beta的影响（m=5, reg=1e-8）")
        print("-" * 100)
        for beta in beta_values:
            print(f"  beta={beta}...", end=' ', flush=True)
            result = {
                'method': f'Anderson(β={beta})',
                'converged': None,
                'iterations': None,
                'error': None,
                'time': None,
                'params': {'m': 5, 'beta': beta, 'reg': 1e-8}
            }
            results.append(result)
            print("待集成")

        # 3. 测试reg的影响（固定m=5, beta=1.0）
        print("\n测试正则化reg的影响（m=5, beta=1.0）")
        print("-" * 100)
        for reg in reg_values:
            print(f"  reg={reg}...", end=' ', flush=True)
            result = {
                'method': f'Anderson(reg={reg})',
                'converged': None,
                'iterations': None,
                'error': None,
                'time': None,
                'params': {'m': 5, 'beta': 1.0, 'reg': reg}
            }
            results.append(result)
            print("待集成")

        print("\n" + "-" * 100)
        print("注意：Anderson加速参数测试需要先集成到CanalSolver")
        print("当前仅显示基准结果（自适应Aitken加速）")
        print("-" * 100)


def create_anderson_integrated_solver():
    """
    创建集成Anderson加速的求解器版本

    这是一个原型，展示如何将Anderson加速集成到固定点迭代中
    """

    print("\n" + "=" * 100)
    print("Anderson加速集成原型")
    print("=" * 100)
    print()

    print("集成策略：")
    print("1. 在_apply_internal_bc中，将Q值视为固定点迭代变量")
    print("2. 使用Anderson加速替代当前的Aitken加速")
    print("3. 保存历史Q值和残差，构造加速步")
    print()

    print("伪代码：")
    print("""
    class CanalSolverWithAnderson(CanalSolver):
        def __init__(self, ..., anderson_m=5, anderson_beta=1.0, anderson_reg=1e-8):
            super().__init__(...)
            self.anderson = AndersonAcceleration(m=anderson_m, beta=anderson_beta, reg=anderson_reg)

        def _apply_internal_bc_anderson(self, ...):
            # 对于每个结构节点
            for idx in structure_indices:
                # 当前Q值
                Q_current = self.Q[idx]

                # 计算目标Q值（固定点函数 g(Q)）
                Q_target = structure.calculate_discharge(h_up, h_down)

                # Anderson加速
                if iter_count > 0:
                    Q_next = self.anderson.compute_acceleration(Q_current, Q_target)
                else:
                    Q_next = Q_target  # 第一次迭代

                # 更新
                self.Q[idx] = Q_next
    """)
    print()

    print("关键设计决策：")
    print("1. Anderson加速应用于整个Q向量还是单个结构节点？")
    print("   建议：应用于整个Q向量，保持全局一致性")
    print()
    print("2. 如何处理多个结构的耦合？")
    print("   建议：将所有结构节点的Q值打包为一个向量，统一加速")
    print()
    print("3. 何时重启Anderson加速？")
    print("   建议：检测残差上升时自动重启")
    print()


def demonstrate_anderson_acceleration():
    """
    演示Anderson加速在简单固定点问题上的效果
    """

    print("\n" + "=" * 100)
    print("Anderson加速演示：简单固定点迭代")
    print("=" * 100)
    print()

    # 问题：求解 x = cos(x)
    print("问题: x = cos(x)")
    print()

    # 方法1：普通固定点迭代
    print("方法1：普通固定点迭代")
    x = 1.0
    for i in range(20):
        x_new = np.cos(x)
        residual = abs(x_new - x)
        x = x_new
        if i % 5 == 0:
            print(f"  迭代 {i:2d}: x={x:.8f}, 残差={residual:.2e}")
        if residual < 1e-10:
            break
    print(f"  收敛: {i+1}次迭代")
    print()

    # 方法2：Anderson加速
    print("方法2：Anderson加速（m=5）")
    anderson = AndersonAcceleration(m=5, beta=1.0, reg=1e-8)
    x = 1.0
    for i in range(20):
        x_current = x
        x_next = np.cos(x_current)

        # 使用Anderson加速
        if i > 0:
            x = anderson.compute_acceleration(x_current, x_next)
        else:
            x = x_next

        residual = abs(x - x_current)
        if i % 5 == 0:
            print(f"  迭代 {i:2d}: x={x:.8f}, 残差={residual:.2e}")
        if residual < 1e-10:
            break
    print(f"  收敛: {i+1}次迭代")
    print()

    # 方法3：Anderson加速（m=3, beta=0.5）
    print("方法3：Anderson加速（m=3, beta=0.5，更保守）")
    anderson = AndersonAcceleration(m=3, beta=0.5, reg=1e-8)
    x = 1.0
    for i in range(20):
        x_current = x
        x_next = np.cos(x_current)

        # 使用Anderson加速
        if i > 0:
            x = anderson.compute_acceleration(x_current, x_next)
        else:
            x = x_next

        residual = abs(x - x_current)
        if i % 5 == 0:
            print(f"  迭代 {i:2d}: x={x:.8f}, 残差={residual:.2e}")
        if residual < 1e-10:
            break
    print(f"  收敛: {i+1}次迭代")
    print()


if __name__ == '__main__':
    # 演示Anderson加速基本效果
    demonstrate_anderson_acceleration()

    # 展示集成策略
    create_anderson_integrated_solver()

    # 参数调优测试（需要先集成）
    test_anderson_parameters()

    print("\n" + "=" * 100)
    print("总结")
    print("=" * 100)
    print()
    print("下一步工作：")
    print("1. 创建CanalSolverWithAnderson类，集成Anderson加速")
    print("2. 实现向量化的Anderson加速（处理多个结构节点）")
    print("3. 运行完整的参数调优测试")
    print("4. 与基准方法（Aitken加速）进行性能对比")
    print()
    print("预期收益：")
    print("- Anderson加速理论上优于Aitken（使用更多历史信息）")
    print("- 对于强非线性问题，可能有10-30%的加速")
    print("- 需要仔细调优参数以避免数值不稳定")
    print()
