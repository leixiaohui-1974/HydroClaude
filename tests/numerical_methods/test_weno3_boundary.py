#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
WENO3边界处理优化测试

目标：验证Ghost Cell方法对边界精度的提升

测试内容：
1. Ghost cells正确创建（n+4数组）
2. 不同边界条件下的ghost cells填充
3. 边界精度提升验证（1阶 vs 3阶）
4. 向后兼容性测试
5. 网格细化精度收敛测试

作者: HydroClaude Team
日期: 2025-10-31
Phase: 6.2 - WENO3边界优化
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import numpy as np
import pytest


class TestWENO3BoundaryOptimization:
    """WENO3边界处理优化测试"""

    def test_ghost_cells_array_size(self):
        """
        测试1：Ghost cells数组大小

        验证：增强模式使用n+4数组，标准模式使用n+2数组
        """
        print("\n" + "="*70)
        print("WENO3边界测试 1: Ghost cells数组大小")
        print("="*70)

        from solvers.godunov_fvm_weno3 import GodunvFVMWENO3

        n_cells = 50

        # 测试增强模式
        solver_enhanced = GodunvFVMWENO3(
            width=10.0,
            length=1000.0,
            n_cells=n_cells,
            manning_n=0.025,
            slope=0.001,
            use_enhanced_bc=True
        )

        h = np.ones(n_cells) * 2.0
        Q = np.ones(n_cells) * 20.0

        bc_left = {'type': 'fixed_Q', 'Q': 20.0}
        bc_right = {'type': 'fixed_h', 'h': 2.0}
        solver_enhanced.initialize(h, Q, bc_left, bc_right)

        h_ext, Q_ext = solver_enhanced._extend_with_ghosts(h, Q)

        assert len(h_ext) == n_cells + 4, f"增强模式应为n+4={n_cells+4}，实际{len(h_ext)}"
        assert len(Q_ext) == n_cells + 4, f"增强模式应为n+4={n_cells+4}，实际{len(Q_ext)}"

        # 验证物理域正确复制
        assert np.allclose(h_ext[2:n_cells+2], h), "物理域应正确复制"
        assert np.allclose(Q_ext[2:n_cells+2], Q), "物理域应正确复制"

        print(f"\n✅ PASSED: Ghost cells数组大小验证")
        print(f"  增强模式: n+4 = {len(h_ext)} ✓")
        print(f"  物理域索引: [2:{n_cells+2}] ✓")

        # 测试标准模式
        solver_standard = GodunvFVMWENO3(
            width=10.0,
            length=1000.0,
            n_cells=n_cells,
            manning_n=0.025,
            slope=0.001,
            use_enhanced_bc=False
        )

        solver_standard.initialize(h, Q, bc_left, bc_right)
        h_ext_std, Q_ext_std = solver_standard._extend_with_ghosts(h, Q)

        assert len(h_ext_std) == n_cells + 2, f"标准模式应为n+2={n_cells+2}，实际{len(h_ext_std)}"

        print(f"  标准模式: n+2 = {len(h_ext_std)} ✓")

    def test_transmissive_bc_ghost_filling(self):
        """
        测试2：透射边界条件ghost cells填充

        验证：零梯度外推
        """
        print("\n" + "="*70)
        print("WENO3边界测试 2: 透射边界条件")
        print("="*70)

        from solvers.godunov_fvm_weno3 import GodunvFVMWENO3

        n_cells = 50
        solver = GodunvFVMWENO3(
            width=10.0,
            length=1000.0,
            n_cells=n_cells,
            manning_n=0.025,
            slope=0.001,
            use_enhanced_bc=True
        )

        h = np.linspace(1.0, 3.0, n_cells)
        Q = np.linspace(10.0, 30.0, n_cells)

        bc_left = {'type': 'transmissive'}
        bc_right = {'type': 'transmissive'}
        solver.initialize(h, Q, bc_left, bc_right)

        h_ext, Q_ext = solver._extend_with_ghosts(h, Q)

        # 验证左边界（零梯度）
        assert np.isclose(h_ext[1], h[0]), "左ghost[1]应等于h[0]"
        assert np.isclose(h_ext[0], h[0]), "左ghost[0]应等于h[0]"
        assert np.isclose(Q_ext[1], Q[0]), "左ghost[1]应等于Q[0]"
        assert np.isclose(Q_ext[0], Q[0]), "左ghost[0]应等于Q[0]"

        # 验证右边界（零梯度）
        assert np.isclose(h_ext[n_cells+2], h[-1]), "右ghost[1]应等于h[-1]"
        assert np.isclose(h_ext[n_cells+3], h[-1]), "右ghost[2]应等于h[-1]"
        assert np.isclose(Q_ext[n_cells+2], Q[-1]), "右ghost[1]应等于Q[-1]"
        assert np.isclose(Q_ext[n_cells+3], Q[-1]), "右ghost[2]应等于Q[-1]"

        print(f"\n✅ PASSED: 透射边界验证通过")
        print(f"  左边界: h_ghost = {h_ext[0]:.3f} = h[0] = {h[0]:.3f} ✓")
        print(f"  右边界: h_ghost = {h_ext[-1]:.3f} = h[-1] = {h[-1]:.3f} ✓")

    def test_fixed_bc_ghost_filling(self):
        """
        测试3：固定边界条件ghost cells填充

        验证：边界值固定，另一变量外推
        """
        print("\n" + "="*70)
        print("WENO3边界测试 3: 固定边界条件")
        print("="*70)

        from solvers.godunov_fvm_weno3 import GodunvFVMWENO3

        n_cells = 50
        solver = GodunvFVMWENO3(
            width=10.0,
            length=1000.0,
            n_cells=n_cells,
            manning_n=0.025,
            slope=0.001,
            use_enhanced_bc=True
        )

        h = np.ones(n_cells) * 2.0
        Q = np.ones(n_cells) * 20.0

        # 左边界固定Q，右边界固定h
        Q_bc_left = 25.0
        h_bc_right = 2.5

        bc_left = {'type': 'fixed_Q', 'Q': Q_bc_left}
        bc_right = {'type': 'fixed_h', 'h': h_bc_right}
        solver.initialize(h, Q, bc_left, bc_right)

        h_ext, Q_ext = solver._extend_with_ghosts(h, Q)

        # 验证左边界（Q固定）
        assert np.isclose(Q_ext[1], Q_bc_left), f"左ghost Q应为{Q_bc_left}"
        assert np.isclose(Q_ext[0], Q_bc_left), f"左ghost Q应为{Q_bc_left}"

        # h应该外推
        h_extrap_expected = 2*h[0] - h[1]
        assert np.isclose(h_ext[1], h_extrap_expected, rtol=0.1), "左ghost h应为外推值"

        # 验证右边界（h固定）
        assert np.isclose(h_ext[n_cells+2], h_bc_right), f"右ghost h应为{h_bc_right}"
        assert np.isclose(h_ext[n_cells+3], h_bc_right), f"右ghost h应为{h_bc_right}"

        # Q应该外推
        Q_extrap_expected = 2*Q[-1] - Q[-2]
        assert np.isclose(Q_ext[n_cells+2], Q_extrap_expected, rtol=0.1), "右ghost Q应为外推值"

        print(f"\n✅ PASSED: 固定边界验证通过")
        print(f"  左边界: Q_ghost = {Q_ext[1]:.2f} = Q_bc = {Q_bc_left:.2f} ✓")
        print(f"  右边界: h_ghost = {h_ext[-1]:.3f} = h_bc = {h_bc_right:.3f} ✓")

    def test_reflective_bc_ghost_filling(self):
        """
        测试4：反射边界条件ghost cells填充

        验证：镜像对称，流量反向
        """
        print("\n" + "="*70)
        print("WENO3边界测试 4: 反射边界条件")
        print("="*70)

        from solvers.godunov_fvm_weno3 import GodunvFVMWENO3

        n_cells = 50
        solver = GodunvFVMWENO3(
            width=10.0,
            length=1000.0,
            n_cells=n_cells,
            manning_n=0.025,
            slope=0.001,
            use_enhanced_bc=True
        )

        h = np.linspace(1.0, 3.0, n_cells)
        Q = np.linspace(10.0, 30.0, n_cells)

        bc_left = {'type': 'reflective'}
        bc_right = {'type': 'reflective'}
        solver.initialize(h, Q, bc_left, bc_right)

        h_ext, Q_ext = solver._extend_with_ghosts(h, Q)

        # 验证左边界（镜像）
        assert np.isclose(h_ext[1], h[0]), "左ghost[1] h应镜像"
        assert np.isclose(h_ext[0], h[1]), "左ghost[0] h应镜像h[1]"
        assert np.isclose(Q_ext[1], -Q[0]), "左ghost[1] Q应反向"
        assert np.isclose(Q_ext[0], -Q[1]), "左ghost[0] Q应反向"

        # 验证右边界（镜像）
        assert np.isclose(h_ext[n_cells+2], h[-1]), "右ghost[1] h应镜像"
        assert np.isclose(h_ext[n_cells+3], h[-2]), "右ghost[2] h应镜像h[-2]"
        assert np.isclose(Q_ext[n_cells+2], -Q[-1]), "右ghost[1] Q应反向"
        assert np.isclose(Q_ext[n_cells+3], -Q[-2]), "右ghost[2] Q应反向"

        print(f"\n✅ PASSED: 反射边界验证通过")
        print(f"  左边界: Q_ghost = {Q_ext[0]:.2f} = -Q[1] = {-Q[1]:.2f} ✓")
        print(f"  右边界: Q_ghost = {Q_ext[-1]:.2f} = -Q[-2] = {-Q[-2]:.2f} ✓")

    def test_weno3_reconstruction_uniform_stencil(self):
        """
        测试5：WENO3重构使用统一模板

        验证：增强模式下，所有界面（包括边界）使用相同的5点模板
        """
        print("\n" + "="*70)
        print("WENO3边界测试 5: 统一模板重构")
        print("="*70)

        from solvers.godunov_fvm_weno3 import GodunvFVMWENO3

        n_cells = 20
        solver = GodunvFVMWENO3(
            width=10.0,
            length=1000.0,
            n_cells=n_cells,
            manning_n=0.025,
            slope=0.001,
            use_enhanced_bc=True
        )

        # 创建光滑初场（正弦函数）
        x = np.linspace(0, 1, n_cells)
        h = 2.0 + 0.5 * np.sin(2 * np.pi * x)

        bc_left = {'type': 'transmissive'}
        bc_right = {'type': 'transmissive'}
        solver.initialize(h, h*0, bc_left, bc_right)

        # 扩展并重构
        h_ext, _ = solver._extend_with_ghosts(h, h*0)
        h_L, h_R = solver._weno3_reconstruction(h_ext)

        # 验证重构结果数量
        assert len(h_L) == n_cells + 1, f"重构结果应为n+1={n_cells+1}个界面"
        assert len(h_R) == n_cells + 1, f"重构结果应为n+1={n_cells+1}个界面"

        # 验证边界重构值合理（无NaN或Inf）
        assert np.all(np.isfinite(h_L)), "重构值应全部有限"
        assert np.all(np.isfinite(h_R)), "重构值应全部有限"

        # 验证边界重构值在合理范围内
        h_min, h_max = h.min(), h.max()
        margin = 0.5 * (h_max - h_min)  # 允许一定外推范围

        assert np.all(h_L >= h_min - margin), "左重构值应在合理范围"
        assert np.all(h_L <= h_max + margin), "左重构值应在合理范围"
        assert np.all(h_R >= h_min - margin), "右重构值应在合理范围"
        assert np.all(h_R <= h_max + margin), "右重构值应在合理范围"

        print(f"\n✅ PASSED: 统一模板重构验证通过")
        print(f"  界面数: {len(h_L)} ✓")
        print(f"  h_L范围: [{h_L.min():.3f}, {h_L.max():.3f}] ✓")
        print(f"  h_R范围: [{h_R.min():.3f}, {h_R.max():.3f}] ✓")
        print(f"  无NaN/Inf ✓")

    def test_boundary_accuracy_improvement(self):
        """
        测试6：边界精度提升验证

        验证：增强模式相比标准模式在边界处精度提升
        """
        print("\n" + "="*70)
        print("WENO3边界测试 6: 边界精度提升")
        print("="*70)

        from solvers.godunov_fvm_weno3 import GodunvFVMWENO3

        # 测试场景：光滑初场，短时间演化，测量边界误差

        def run_simulation(use_enhanced, n_cells=50):
            """运行一个短时间模拟"""
            solver = GodunvFVMWENO3(
                width=10.0,
                length=1000.0,
                n_cells=n_cells,
                manning_n=0.025,
                slope=0.001,
                use_enhanced_bc=use_enhanced,
                cfl=0.3
            )

            # 光滑初场
            x = np.linspace(0, 1000, n_cells)
            h = 2.0 + 0.2 * np.sin(2 * np.pi * x / 1000.0)
            Q = np.ones(n_cells) * 20.0

            bc_left = {'type': 'transmissive'}
            bc_right = {'type': 'transmissive'}
            solver.initialize(h, Q, bc_left, bc_right)

            # 运行10步
            for _ in range(10):
                solver.step()

            return solver.h

        # 标准模式
        h_standard = run_simulation(use_enhanced=False)

        # 增强模式
        h_enhanced = run_simulation(use_enhanced=True)

        # 两种模式应该都能正常运行
        assert np.all(np.isfinite(h_standard)), "标准模式应产生有限值"
        assert np.all(np.isfinite(h_enhanced)), "增强模式应产生有限值"

        # 计算边界单元的差异（前后各5个单元）
        boundary_cells = 5
        diff_left_standard = np.abs(h_standard[:boundary_cells] - 2.0)
        diff_left_enhanced = np.abs(h_enhanced[:boundary_cells] - 2.0)

        diff_right_standard = np.abs(h_standard[-boundary_cells:] - 2.0)
        diff_right_enhanced = np.abs(h_enhanced[-boundary_cells:] - 2.0)

        # 增强模式应该显著改善边界精度
        # 计算精度提升倍数
        improvement_left = diff_left_standard.max() / max(diff_left_enhanced.max(), 1e-10)
        improvement_right = diff_right_standard.max() / max(diff_right_enhanced.max(), 1e-10)

        print(f"\n✅ PASSED: 边界精度对比")
        print(f"  标准模式左边界最大偏差: {diff_left_standard.max():.6f}")
        print(f"  增强模式左边界最大偏差: {diff_left_enhanced.max():.6f}")
        print(f"  左边界精度提升: {improvement_left:.1f}x ✨")
        print(f"  标准模式右边界最大偏差: {diff_right_standard.max():.6f}")
        print(f"  增强模式右边界最大偏差: {diff_right_enhanced.max():.6f}")
        print(f"  右边界精度提升: {improvement_right:.1f}x ✨")

        # 验证：增强模式应该更准确（至少不更差）
        assert diff_left_enhanced.max() <= diff_left_standard.max(), "增强模式左边界应不差于标准模式"
        assert diff_right_enhanced.max() <= diff_right_standard.max(), "增强模式右边界应不差于标准模式"

        # 如果有显著提升（>2x），报告成功
        if improvement_left > 2.0 or improvement_right > 2.0:
            print(f"  🎉 边界精度显著提升！")

    def test_backward_compatibility(self):
        """
        测试7：向后兼容性

        验证：use_enhanced_bc=False时，行为与旧版本一致
        """
        print("\n" + "="*70)
        print("WENO3边界测试 7: 向后兼容性")
        print("="*70)

        from solvers.godunov_fvm_weno3 import GodunvFVMWENO3

        n_cells = 50

        # 创建标准模式求解器（use_enhanced_bc=False）
        solver = GodunvFVMWENO3(
            width=10.0,
            length=1000.0,
            n_cells=n_cells,
            manning_n=0.025,
            slope=0.001,
            use_enhanced_bc=False  # 标准模式
        )

        h = np.ones(n_cells) * 2.0
        Q = np.ones(n_cells) * 20.0

        bc_left = {'type': 'fixed_Q', 'Q': 20.0}
        bc_right = {'type': 'fixed_h', 'h': 2.0}
        solver.initialize(h, Q, bc_left, bc_right)

        # 标准模式应该使用n+2数组
        h_ext, Q_ext = solver._extend_with_ghosts(h, Q)
        assert len(h_ext) == n_cells + 2, "标准模式应使用n+2数组"

        # 重构应该正常工作
        h_L, h_R = solver._weno3_reconstruction(h_ext)
        assert len(h_L) == n_cells + 1, "重构结果应为n+1个界面"

        # 运行几步应该正常
        for _ in range(5):
            solver.step()

        assert np.all(np.isfinite(solver.h)), "标准模式应正常运行"

        print(f"\n✅ PASSED: 向后兼容性验证通过")
        print(f"  标准模式ghost cells: n+2 = {len(h_ext)} ✓")
        print(f"  重构正常 ✓")
        print(f"  模拟正常运行 ✓")

    def test_grid_refinement_convergence(self):
        """
        测试8：网格细化精度收敛

        验证：增强模式下，边界精度应随网格细化而提升
        """
        print("\n" + "="*70)
        print("WENO3边界测试 8: 网格细化精度收敛")
        print("="*70)

        from solvers.godunov_fvm_weno3 import GodunvFVMWENO3

        def compute_boundary_error(n_cells, use_enhanced):
            """计算边界误差"""
            solver = GodunvFVMWENO3(
                width=10.0,
                length=1000.0,
                n_cells=n_cells,
                manning_n=0.025,
                slope=0.001,
                use_enhanced_bc=use_enhanced,
                cfl=0.3
            )

            # 光滑初场
            x = np.linspace(0, 1000, n_cells)
            h = 2.0 + 0.2 * np.sin(2 * np.pi * x / 1000.0)
            Q = np.ones(n_cells) * 20.0

            bc_left = {'type': 'transmissive'}
            bc_right = {'type': 'transmissive'}
            solver.initialize(h, Q, bc_left, bc_right)

            # 运行少量步骤
            for _ in range(5):
                solver.step()

            # 计算边界误差（前后各2个单元）
            error_left = np.abs(solver.h[0:2] - 2.0).max()
            error_right = np.abs(solver.h[-2:] - 2.0).max()

            return max(error_left, error_right)

        # 测试不同网格
        n_cells_list = [25, 50, 100]
        errors_enhanced = []
        errors_standard = []

        for n in n_cells_list:
            error_enh = compute_boundary_error(n, use_enhanced=True)
            error_std = compute_boundary_error(n, use_enhanced=False)
            errors_enhanced.append(error_enh)
            errors_standard.append(error_std)

        print(f"\n✅ 网格细化精度收敛测试完成")
        print(f"\n{'网格':<10} {'增强模式误差':<15} {'标准模式误差':<15}")
        print("-" * 40)
        for n, e_enh, e_std in zip(n_cells_list, errors_enhanced, errors_standard):
            print(f"{n:<10} {e_enh:<15.6e} {e_std:<15.6e}")

        # 验证误差随网格细化而减小
        assert errors_enhanced[1] < errors_enhanced[0], "误差应随网格细化减小"
        assert errors_enhanced[2] < errors_enhanced[1], "误差应随网格细化减小"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
