#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
边界条件强制机制诊断测试

目的：检查边界条件是否在时间推进过程中被正确保持

测试策略：
1. 简单的均匀流（Q边界）
2. 简单的静水（h边界）
3. 检查每个时间步后边界值是否保持
"""

import numpy as np
import pytest
from solvers.godunov_fvm_solver import GodunvFVMSolver


class TestBoundaryEnforcement:
    """边界条件强制机制诊断测试"""

    def test_Q_boundary_enforcement(self):
        """
        测试Q边界是否被正确强制

        设置：
        - 上游：Q = 10.0 m³/s（固定）
        - 下游：h = 2.0 m（固定）
        - 检查每步后Q[0]是否保持为10.0
        """
        print("\n" + "="*80)
        print("诊断测试：Q边界强制检查")
        print("="*80)

        # 创建求解器
        solver = GodunvFVMSolver(
            width=10.0,
            length=1000.0,
            n_cells=50,
            manning_n=0.025,
            slope=0.001,
            cfl=0.5,
            order=2
        )

        # 初始化：均匀流
        h_init = np.ones(50) * 2.0
        Q_init = np.ones(50) * 10.0

        bc_left = {'type': 'Q', 'value': 10.0}
        bc_right = {'type': 'h', 'value': 2.0}

        solver.initialize(h_init, Q_init, bc_left, bc_right)

        print(f"\n初始状态:")
        print(f"  Q[0] = {solver.Q[0]:.6f} m³/s (目标: 10.0)")
        print(f"  h[-1] = {solver.h[-1]:.6f} m (目标: 2.0)")

        # 推进100步，每步检查边界
        violations = []
        for step in range(100):
            solver.step()

            # 检查边界是否被保持
            Q_error = abs(solver.Q[0] - 10.0)
            h_error = abs(solver.h[-1] - 2.0)

            if Q_error > 1e-10:
                violations.append({
                    'step': step + 1,
                    'type': 'Q',
                    'value': solver.Q[0],
                    'target': 10.0,
                    'error': Q_error
                })

            if h_error > 1e-10:
                violations.append({
                    'step': step + 1,
                    'type': 'h',
                    'value': solver.h[-1],
                    'target': 2.0,
                    'error': h_error
                })

        print(f"\n完成100步时间推进")
        print(f"  Q[0] = {solver.Q[0]:.6f} m³/s (目标: 10.0)")
        print(f"  h[-1] = {solver.h[-1]:.6f} m (目标: 2.0)")

        # 报告违规
        if violations:
            print(f"\n❌ 发现 {len(violations)} 次边界条件违规：")
            for i, v in enumerate(violations[:10]):  # 只显示前10个
                print(f"  步骤{v['step']}: {v['type']}边界 = {v['value']:.6e}, "
                      f"目标 = {v['target']:.6e}, 误差 = {v['error']:.6e}")
            if len(violations) > 10:
                print(f"  ... 还有 {len(violations) - 10} 次违规")
        else:
            print("\n✅ 所有时间步边界条件都被正确强制")

        # 断言
        assert len(violations) == 0, \
            f"边界条件在时间推进中被违反 {len(violations)} 次"

        print("\n✅ Q边界强制测试通过")

    def test_h_boundary_enforcement(self):
        """
        测试h边界是否被正确强制

        设置：
        - 上游：h = 2.0 m（固定）
        - 下游：h = 2.0 m（固定）
        - 静水，无流量
        """
        print("\n" + "="*80)
        print("诊断测试：h边界强制检查")
        print("="*80)

        solver = GodunvFVMSolver(
            width=10.0,
            length=1000.0,
            n_cells=50,
            manning_n=0.025,
            slope=0.001,
            cfl=0.5,
            order=2
        )

        # 初始化：静水
        h_init = np.ones(50) * 2.0
        Q_init = np.zeros(50)

        bc_left = {'type': 'h', 'value': 2.0}
        bc_right = {'type': 'h', 'value': 2.0}

        solver.initialize(h_init, Q_init, bc_left, bc_right)

        print(f"\n初始状态:")
        print(f"  h[0] = {solver.h[0]:.6f} m (目标: 2.0)")
        print(f"  h[-1] = {solver.h[-1]:.6f} m (目标: 2.0)")

        # 推进100步
        violations = []
        for step in range(100):
            solver.step()

            h_left_error = abs(solver.h[0] - 2.0)
            h_right_error = abs(solver.h[-1] - 2.0)

            if h_left_error > 1e-10:
                violations.append({
                    'step': step + 1,
                    'boundary': 'left',
                    'value': solver.h[0],
                    'error': h_left_error
                })

            if h_right_error > 1e-10:
                violations.append({
                    'step': step + 1,
                    'boundary': 'right',
                    'value': solver.h[-1],
                    'error': h_right_error
                })

        print(f"\n完成100步时间推进")
        print(f"  h[0] = {solver.h[0]:.6f} m (目标: 2.0)")
        print(f"  h[-1] = {solver.h[-1]:.6f} m (目标: 2.0)")

        if violations:
            print(f"\n❌ 发现 {len(violations)} 次边界条件违规")
            for v in violations[:10]:
                print(f"  步骤{v['step']}, {v['boundary']}边界: "
                      f"h = {v['value']:.6e}, 误差 = {v['error']:.6e}")
        else:
            print("\n✅ 所有时间步边界条件都被正确强制")

        assert len(violations) == 0, \
            f"h边界在时间推进中被违反 {len(violations)} 次"

        print("\n✅ h边界强制测试通过")

    def test_supercritical_boundary_enforcement(self):
        """
        测试supercritical边界是否被正确强制

        设置：
        - 上游：supercritical (h=0.5m, Q=10m³/s, Fr>1)
        - 下游：h = 2.0 m
        - 检查上游h和Q是否都被保持
        """
        print("\n" + "="*80)
        print("诊断测试：Supercritical边界强制检查")
        print("="*80)

        solver = GodunvFVMSolver(
            width=10.0,
            length=1000.0,
            n_cells=50,
            manning_n=0.0,  # 无摩阻
            slope=0.0,      # 水平床
            cfl=0.4,
            order=1         # 一阶格式（更稳定）
        )

        # 初始化（调整参数以获得Fr>1）
        h_upstream = 0.3   # 减小水深以增大Fr
        Q_upstream = 10.0
        h_downstream = 2.0

        h_init = np.linspace(h_upstream, h_downstream, 50)
        Q_init = np.ones(50) * Q_upstream

        bc_left = {'type': 'supercritical', 'h': h_upstream, 'Q': Q_upstream}
        bc_right = {'type': 'h', 'value': h_downstream}

        solver.initialize(h_init, Q_init, bc_left, bc_right)

        # 计算上游Froude数
        g = 9.81
        B = 10.0
        u_upstream = Q_upstream / (B * h_upstream)
        Fr_upstream = u_upstream / np.sqrt(g * h_upstream)

        print(f"\n上游条件:")
        print(f"  h = {h_upstream} m")
        print(f"  Q = {Q_upstream} m³/s")
        print(f"  u = {u_upstream:.2f} m/s")
        print(f"  Fr = {Fr_upstream:.2f} {'(急流 ✓)' if Fr_upstream > 1 else '(缓流 ✗)'}")

        assert Fr_upstream > 1.0, "上游必须是急流"

        # 推进50步
        h_violations = []
        Q_violations = []

        for step in range(50):
            solver.step()

            h_error = abs(solver.h[0] - h_upstream)
            Q_error = abs(solver.Q[0] - Q_upstream)

            if h_error > 1e-6:  # 放宽容差
                h_violations.append({'step': step+1, 'value': solver.h[0], 'error': h_error})

            if Q_error > 1e-6:
                Q_violations.append({'step': step+1, 'value': solver.Q[0], 'error': Q_error})

        print(f"\n完成50步时间推进")
        print(f"  h[0] = {solver.h[0]:.6f} m (目标: {h_upstream})")
        print(f"  Q[0] = {solver.Q[0]:.6f} m³/s (目标: {Q_upstream})")

        u_final = solver.Q[0] / (B * solver.h[0]) if solver.h[0] > 1e-10 else 0.0
        Fr_final = u_final / np.sqrt(g * solver.h[0]) if solver.h[0] > 1e-10 else 0.0
        print(f"  Fr[0] = {Fr_final:.2f} (目标: {Fr_upstream:.2f})")

        total_violations = len(h_violations) + len(Q_violations)

        if total_violations > 0:
            print(f"\n❌ 边界条件违规：")
            print(f"  h违规: {len(h_violations)}次")
            print(f"  Q违规: {len(Q_violations)}次")

            if h_violations:
                print(f"\n  h违规示例 (前5个):")
                for v in h_violations[:5]:
                    print(f"    步骤{v['step']}: h = {v['value']:.6f}, 误差 = {v['error']:.6e}")

            if Q_violations:
                print(f"\n  Q违规示例 (前5个):")
                for v in Q_violations[:5]:
                    print(f"    步骤{v['step']}: Q = {v['value']:.6f}, 误差 = {v['error']:.6e}")
        else:
            print("\n✅ 所有时间步边界条件都被正确强制")

        # 检查质量守恒
        mass_error = abs(solver.get_mass_conservation_error())
        print(f"\n质量守恒误差: {mass_error:.6f}%")

        # 断言
        assert total_violations == 0, \
            f"Supercritical边界被违反 {total_violations} 次"

        assert mass_error < 1.0, \
            f"质量守恒误差过大: {mass_error:.2f}%"

        print("\n✅ Supercritical边界强制测试通过")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
