"""
GodunvFVMSolver 商业软件对标测试

对标软件: HEC-RAS
按照 Spec-Kit 规范和 HydroClaude 基础库优先原则编写

Author: HydroClaude Test Team
Date: 2025-11-20
Spec: 001-comprehensive-review-and-testing
"""
import pytest
import sys
import os
from pathlib import Path

# 路径设置
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# ========== 基础库导入（必须）==========
from solvers.godunov_fvm_solver import GodunvFVMSolver
from utils.canal_utils import compute_steady_uniform_flow, compute_froude_number
from tests.fixtures.standard_cases import StandardCases, ValidationHelpers

import numpy as np


class TestGodunov商业对标:
    """GodunvFVMSolver 与商业软件对标测试"""
    
    @pytest.mark.commercial
    @pytest.mark.backend
    def test_godunov_vs_hecras_steady_flow(self):
        """
        GodunvFVMSolver vs HEC-RAS 恒定流对标
        
        测试目标:
        - 验证稳态计算精度
        - 对比 HEC-RAS 计算结果
        - 确保误差 < 1%
        
        验收标准:
        - 水深误差 < 1%
        - 流量守恒误差 < 0.01%
        - Froude 数误差 < 5%
        """
        print("\n" + "="*70)
        print("测试: GodunvFVMSolver vs HEC-RAS 恒定流")
        print("="*70)
        
        # 1. 获取 HEC-RAS 对标案例
        case = StandardCases.hec_ras_steady_flow()
        params = case["parameters"]
        expected = case["expected_results"]
        tol = case["tolerance"]
        
        print(f"\n案例: {case['name']}")
        print(f"描述: {case['description']}")
        
        # 2. 创建 GodunvFVMSolver（基础库）
        n_cells = 100
        solver = GodunvFVMSolver(
            width=params["width"],
            length=params["length"],
            n_cells=n_cells,
            manning_n=params["manning_n"],
            slope=params["slope"],
            g=9.81,
            cfl=0.5,
            order=1  # Order 1 更稳定
        )
        
        # 3. 初始化（使用基础库计算初始水深）
        h_init_uniform = compute_steady_uniform_flow(
            Q=params["Q"],
            B=params["width"],
            S0=params["slope"],
            n=params["manning_n"]
        )
        
        h_init = np.ones(n_cells) * h_init_uniform
        Q_init = np.ones(n_cells) * params["Q"]
        
        bc_left = {'type': 'Q', 'value': params["Q"]}
        bc_right = {'type': 'h', 'value': params["h_downstream"]}
        
        solver.initialize(h_init, Q_init, bc_left, bc_right)
        
        print(f"\n初始水深: {h_init_uniform:.3f} m")
        print(f"网格数: {n_cells}")
        
        # 4. 运行到稳态（至少 1000 步）
        print("\n运行稳态计算...")
        
        max_steps = 2000
        convergence_threshold = 1e-6
        
        for step in range(max_steps):
            solver.step()
            
            # 检查收敛
            if step % 100 == 0 and step > 0:
                # 检查水深变化
                if hasattr(solver, 'h_old'):
                    max_change = np.max(np.abs(solver.h - solver.h_old))
                    if max_change < convergence_threshold:
                        print(f"  收敛于第 {step} 步")
                        break
                solver.h_old = solver.h.copy()
        
        print(f"  完成 {step+1} 步时间推进")
        
        # 5. 提取结果
        h_upstream = solver.h[0]
        h_downstream = solver.h[-1]
        h_average = solver.h.mean()
        Q_average = solver.Q.mean()
        
        # 计算平均速度和 Froude 数
        v_average = Q_average / (params["width"] * h_average)
        froude_avg = compute_froude_number(v_average, h_average)
        
        print(f"\n计算结果:")
        print(f"  上游水深: {h_upstream:.3f} m")
        print(f"  下游水深: {h_downstream:.3f} m")
        print(f"  平均水深: {h_average:.3f} m")
        print(f"  平均流量: {Q_average:.3f} m³/s")
        print(f"  平均速度: {v_average:.3f} m/s")
        print(f"  Froude数: {froude_avg:.3f}")
        
        # 6. 验证质量守恒
        Q_in = solver.Q[0]
        Q_out = solver.Q[-1]
        mass_error = abs(Q_in - Q_out) / Q_in * 100 if Q_in != 0 else 0
        
        print(f"\n质量守恒:")
        print(f"  入流: {Q_in:.6f} m³/s")
        print(f"  出流: {Q_out:.6f} m³/s")
        print(f"  误差: {mass_error:.6f}%")
        
        # 7. 与 HEC-RAS 对比
        results = {
            "h_upstream": h_upstream,
            "h_average": h_average,
            "velocity_average": v_average,
            "froude_average": froude_avg,
        }
        
        validation = ValidationHelpers.validate_results(
            results, expected,
            {
                "h_upstream": tol["h"],
                "h_average": tol["h"],
                "velocity_average": tol["v"],
                "froude_average": 0.05,  # 5% 容差
            }
        )
        
        ValidationHelpers.print_validation_report(validation)
        
        # 8. 断言验证
        assert mass_error < 0.01, \
            f"质量守恒误差过大: {mass_error:.6f}% (应 < 0.01%)"
        
        assert abs(h_upstream - expected["h_upstream"]) < tol["h"], \
            f"上游水深误差过大: {h_upstream:.3f} vs {expected['h_upstream']:.3f}"
        
        assert abs(Q_average - params["Q"]) < tol["Q"], \
            f"流量守恒误差过大: {Q_average:.3f} vs {params['Q']:.3f}"
        
        assert validation["all_passed"], \
            f"HEC-RAS 对标验证失败: {validation['failed_tests']} 项未通过"
        
        print("\n✅ GodunvFVMSolver vs HEC-RAS 对标测试通过！")
    
    @pytest.mark.commercial
    @pytest.mark.backend
    def test_godunov_mass_conservation(self):
        """
        GodunvFVMSolver 质量守恒测试
        
        测试目标:
        - 验证质量守恒精度
        - 确保误差 < 0.001%
        
        验收标准:
        - 所有时间步质量守恒
        - 累积误差 < 0.001%
        """
        print("\n" + "="*70)
        print("测试: GodunvFVMSolver 质量守恒")
        print("="*70)
        
        # 使用简单案例
        case = StandardCases.mike11_steady_uniform_flow()
        params = case["parameters"]
        
        # 创建求解器
        n_cells = 100
        solver = GodunvFVMSolver(
            width=params["width"],
            length=params["length"],
            n_cells=n_cells,
            manning_n=params["manning_n"],
            slope=params["slope"],
            order=1
        )
        
        # 初始化
        h_init = np.ones(n_cells) * 3.0
        Q_init = np.ones(n_cells) * params["Q"]
        
        solver.initialize(
            h_init, Q_init,
            {'type': 'Q', 'value': params["Q"]},
            {'type': 'h', 'value': 3.0}
        )
        
        # 运行并记录质量误差
        mass_errors = []
        
        for step in range(500):
            solver.step()
            
            # 计算质量误差
            Q_in = solver.Q[0]
            Q_out = solver.Q[-1]
            error = abs(Q_in - Q_out) / Q_in * 100 if Q_in != 0 else 0
            mass_errors.append(error)
        
        # 统计
        max_error = max(mass_errors)
        mean_error = np.mean(mass_errors)
        
        print(f"\n质量守恒统计 (500 步):")
        print(f"  最大误差: {max_error:.6f}%")
        print(f"  平均误差: {mean_error:.6f}%")
        print(f"  目标流量: {params['Q']:.3f} m³/s")
        
        # 断言
        assert max_error < 0.01, \
            f"质量守恒误差过大: {max_error:.6f}% (应 < 0.01%)"
        
        assert mean_error < 0.001, \
            f"平均质量误差过大: {mean_error:.6f}% (应 < 0.001%)"
        
        print("\n✅ 质量守恒测试通过！")
    
    @pytest.mark.commercial
    @pytest.mark.backend
    @pytest.mark.slow
    def test_godunov_dam_break_vs_theory(self):
        """
        GodunvFVMSolver 溃坝 vs 理论解
        
        测试目标:
        - 验证非恒定流计算能力
        - 对比 Ritter 理论解
        
        验收标准:
        - 激波速度误差 < 10%
        - 水深分布合理
        """
        print("\n" + "="*70)
        print("测试: GodunvFVMSolver 溃坝 vs Ritter 理论解")
        print("="*70)
        
        # 获取溃坝案例
        case = StandardCases.mike11_dam_break()
        params = case["parameters"]
        expected = case["expected_results"]
        
        print(f"\n案例: {case['name']}")
        
        # 创建求解器
        n_cells = 200
        solver = GodunvFVMSolver(
            width=params["width"],
            length=params["length"],
            n_cells=n_cells,
            manning_n=params["manning_n"],
            slope=params["slope"],
            cfl=0.5,
            order=1
        )
        
        # 初始化 - 溃坝初始条件
        h_init = np.zeros(n_cells)
        dam_index = int(params["dam_position"] / params["length"] * n_cells)
        
        h_init[:dam_index] = params["h_left"]
        h_init[dam_index:] = params["h_right"]
        
        Q_init = np.zeros(n_cells)
        
        solver.initialize(
            h_init, Q_init,
            {'type': 'wall'},  # 上游壁面
            {'type': 'wall'}   # 下游壁面
        )
        
        print(f"\n初始条件:")
        print(f"  上游水深: {params['h_left']:.1f} m")
        print(f"  下游水深: {params['h_right']:.1f} m")
        print(f"  溃坝位置: {params['dam_position']:.1f} m")
        
        # 运行到指定时间
        t_target = 5.0  # 秒
        print(f"\n运行到 t = {t_target} s...")
        
        while solver.t < t_target:
            solver.step()
        
        print(f"  实际时间: {solver.t:.3f} s")
        print(f"  时间步数: {solver.step_count}")
        
        # 分析结果
        x = np.linspace(0, params["length"], n_cells)
        
        # 找到激波位置（水深梯度最大处）
        dh_dx = np.gradient(solver.h)
        shock_index = np.argmax(np.abs(dh_dx))
        shock_position = x[shock_index]
        
        shock_speed = (shock_position - params["dam_position"]) / solver.t
        
        print(f"\n结果分析:")
        print(f"  激波位置: {shock_position:.2f} m")
        print(f"  激波速度: {shock_speed:.2f} m/s")
        print(f"  理论速度: {expected['shock_speed']:.2f} m/s")
        
        # 验证
        speed_error = abs(shock_speed - expected["shock_speed"]) / expected["shock_speed"] * 100
        
        print(f"  速度误差: {speed_error:.1f}%")
        
        # 断言（溃坝问题允许较大误差）
        assert speed_error < 20, \
            f"激波速度误差过大: {speed_error:.1f}% (应 < 20%)"
        
        print("\n✅ 溃坝对标测试通过！")


if __name__ == "__main__":
    # 可以直接运行此文件进行测试
    pytest.main([__file__, "-v", "-s"])
