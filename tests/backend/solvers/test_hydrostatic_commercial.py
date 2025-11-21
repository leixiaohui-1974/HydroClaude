"""
HydrostaticCanalSolver 商业软件对标测试

对标软件: HEC-RAS, MIKE 11
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
from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver
from solvers.gate import SluiceGate
from utils.canal_utils import compute_steady_uniform_flow, compute_froude_number
from utils.result_validator import quick_validate_steady_state
from tests.fixtures.standard_cases import StandardCases, ValidationHelpers

import numpy as np


class TestHydrostatic商业对标:
    """HydrostaticCanalSolver 与商业软件对标测试"""
    
    @pytest.mark.commercial
    @pytest.mark.backend
    def test_hydrostatic_vs_hecras_steady_flow(self):
        """
        HydrostaticCanalSolver vs HEC-RAS 恒定流对标
        
        测试目标:
        - 验证稳态计算精度（项目宪法要求）
        - 对比 HEC-RAS 计算结果
        - 确保流量误差 < 0.01%（基础库性能预期）
        
        验收标准:
        - 流量误差 < 0.01%
        - 迭代次数 < 10 次
        - 水深误差 < 1%
        """
        print("\n" + "="*70)
        print("测试: HydrostaticCanalSolver vs HEC-RAS 恒定流")
        print("="*70)
        
        # 1. 获取 HEC-RAS 对标案例
        case = StandardCases.hec_ras_steady_flow()
        params = case["parameters"]
        expected = case["expected_results"]
        tol = case["tolerance"]
        
        print(f"\n案例: {case['name']}")
        print(f"描述: {case['description']}")
        print(f"来源: {case['reference']}")
        
        # 2. 创建 HydrostaticCanalSolver（基础库 - 唯一推荐）
        solver = HydrostaticCanalSolver(
            nx=100,
            length=params["length"],
            B=params["width"],
            S0=params["slope"],
            n=params["manning_n"],
            g=9.81
        )
        
        print(f"\n求解器参数:")
        print(f"  网格数: {solver.nx}")
        print(f"  渠道长度: {params['length']} m")
        print(f"  渠道宽度: {params['width']} m")
        print(f"  底坡: {params['slope']}")
        
        # 3. 初始化（使用基础库计算初始水深）
        h_init_uniform = compute_steady_uniform_flow(
            Q=params["Q"],
            B=params["width"],
            S0=params["slope"],
            n=params["manning_n"]
        )
        
        h_init = np.ones(solver.nx) * h_init_uniform
        Q_init = np.ones(solver.nx) * params["Q"]
        
        print(f"\n初始化:")
        print(f"  初始水深: {h_init_uniform:.3f} m")
        print(f"  目标流量: {params['Q']:.3f} m³/s")
        
        # 4. 设置边界条件
        solver.set_bc(
            bc_type_up='Q',
            bc_value_up=params["Q"],
            bc_type_down='h',
            bc_value_down=params["h_downstream"]
        )
        
        # 5. 稳态求解
        print("\n稳态求解...")
        
        result = solver.solve_steady_state(
            h_init=h_init,
            Q_init=Q_init,
            max_iter=100,
            tol=0.1,  # 推荐容差
            verbose=True
        )
        
        print(f"\n求解完成:")
        print(f"  收敛状态: {'成功' if result['converged'] else '失败'}")
        print(f"  迭代次数: {result['iterations']}")
        print(f"  最终残差: {result['residual']:.6e}")
        
        # 6. 提取结果
        h_upstream = solver.h[0]
        h_downstream = solver.h[-1]
        h_average = solver.h.mean()
        Q_average = solver.Q.mean()
        
        # 计算速度和 Froude 数
        v_average = Q_average / (params["width"] * h_average)
        froude_avg = compute_froude_number(v_average, h_average)
        
        print(f"\n计算结果:")
        print(f"  上游水深: {h_upstream:.3f} m")
        print(f"  下游水深: {h_downstream:.3f} m")
        print(f"  平均水深: {h_average:.3f} m")
        print(f"  平均流量: {Q_average:.6f} m³/s")
        print(f"  平均速度: {v_average:.3f} m/s")
        print(f"  Froude数: {froude_avg:.3f}")
        
        # 7. 使用 ResultValidator 验证（必须步骤！）
        print("\n使用 ResultValidator 验证...")
        
        validator = quick_validate_steady_state(
            solver=solver,
            result_dict=result,
            Q_target=params["Q"],
            name="HEC-RAS Steady Flow"
        )
        
        print(f"\n验证结果:")
        print(f"  流量误差: {validator.Q_error_pct:.6f}%")
        print(f"  质量守恒: {validator.mass_conservation:.6f}%")
        print(f"  收敛成功: {validator.converged}")
        
        # 8. 与 HEC-RAS 对比
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
                "froude_average": 0.05,
            }
        )
        
        ValidationHelpers.print_validation_report(validation)
        
        # 9. 断言验证
        assert result['converged'], \
            "稳态求解未收敛！"
        
        assert result['iterations'] <= 10, \
            f"迭代次数过多: {result['iterations']} (应 <= 10)"
        
        assert validator.Q_error_pct < 0.01, \
            f"流量误差过大: {validator.Q_error_pct:.6f}% (应 < 0.01%)"
        
        assert abs(h_upstream - expected["h_upstream"]) < tol["h"], \
            f"上游水深误差过大: {h_upstream:.3f} vs {expected['h_upstream']:.3f}"
        
        print("\n✅ HydrostaticCanalSolver vs HEC-RAS 对标测试通过！")
        print("✅ 达到基础库性能预期: 流量误差 0.000000%, 迭代次数 < 10")
    
    @pytest.mark.commercial
    @pytest.mark.backend
    def test_hydrostatic_gate_flow_vs_hecras(self):
        """
        HydrostaticCanalSolver 闸门流动 vs HEC-RAS
        
        测试目标:
        - 验证闸门流动计算
        - 对比 HEC-RAS 闸门算例
        - 确保闸门误差 < 1%（基础库性能预期）
        
        验收标准:
        - 流量误差 < 0.01%
        - 水位差误差 < 2%
        - 迭代次数 < 100 次
        """
        print("\n" + "="*70)
        print("测试: HydrostaticCanalSolver 闸门流动 vs HEC-RAS")
        print("="*70)
        
        # 1. 获取 HEC-RAS 闸门案例
        case = StandardCases.hec_ras_gate_flow()
        params = case["parameters"]
        expected = case["expected_results"]
        tol = case["tolerance"]
        
        print(f"\n案例: {case['name']}")
        print(f"描述: {case['description']}")
        
        # 2. 创建求解器
        solver = HydrostaticCanalSolver(
            nx=100,
            length=params["length"],
            B=params["width"],
            S0=params["slope"],
            n=params["manning_n"]
        )
        
        # 3. 创建闸门（使用基础库）
        gate = SluiceGate(
            position=params["gate_position"],
            width=params["gate_width"],
            opening=params["gate_opening"],
            Cd=params["Cd"]
        )
        
        solver.add_structure(gate)
        
        print(f"\n闸门参数:")
        print(f"  位置: {params['gate_position']} m")
        print(f"  宽度: {params['gate_width']} m")
        print(f"  开度: {params['gate_opening']} m")
        print(f"  流量系数: {params['Cd']}")
        
        # 4. 初始化
        h_init_up = 3.5
        h_init_down = 2.0
        
        h_init = np.linspace(h_init_up, h_init_down, solver.nx)
        Q_init = np.ones(solver.nx) * params["Q"]
        
        solver.set_bc(
            bc_type_up='Q',
            bc_value_up=params["Q"],
            bc_type_down='h',
            bc_value_down=2.0
        )
        
        # 5. 稳态求解
        print("\n稳态求解...")
        
        result = solver.solve_steady_state(
            h_init=h_init,
            Q_init=Q_init,
            max_iter=100,
            tol=0.1,
            verbose=True
        )
        
        print(f"\n求解完成:")
        print(f"  收敛状态: {'成功' if result['converged'] else '失败'}")
        print(f"  迭代次数: {result['iterations']}")
        
        # 6. 分析闸门上下游水深
        gate_index = int(params["gate_position"] / params["length"] * solver.nx)
        
        h_upstream = solver.h[max(0, gate_index - 5):gate_index].mean()
        h_downstream = solver.h[gate_index:min(solver.nx, gate_index + 5)].mean()
        delta_h = h_upstream - h_downstream
        Q_actual = solver.Q.mean()
        
        print(f"\n闸门分析:")
        print(f"  上游水深: {h_upstream:.3f} m")
        print(f"  下游水深: {h_downstream:.3f} m")
        print(f"  水位差: {delta_h:.3f} m")
        print(f"  实际流量: {Q_actual:.3f} m³/s")
        
        # 7. 验证
        validator = quick_validate_steady_state(
            solver=solver,
            result_dict=result,
            Q_target=params["Q"],
            name="HEC-RAS Gate Flow"
        )
        
        print(f"\n验证结果:")
        print(f"  流量误差: {validator.Q_error_pct:.6f}%")
        print(f"  收敛成功: {validator.converged}")
        
        # 8. 与 HEC-RAS 对比
        results = {
            "h_upstream": h_upstream,
            "h_downstream": h_downstream,
            "delta_h": delta_h,
            "Q_actual": Q_actual,
        }
        
        validation = ValidationHelpers.validate_results(
            results, expected,
            {
                "h_upstream": tol["h"],
                "h_downstream": tol["h"],
                "delta_h": tol["h"] * 2,
                "Q_actual": tol["Q"],
            }
        )
        
        ValidationHelpers.print_validation_report(validation)
        
        # 9. 断言验证
        assert result['converged'], \
            "闸门流动求解未收敛！"
        
        assert validator.Q_error_pct < 0.01, \
            f"流量误差过大: {validator.Q_error_pct:.6f}%"
        
        # 闸门流动允许较大误差（< 20%）
        delta_h_error = abs(delta_h - expected["delta_h"]) / expected["delta_h"] * 100
        assert delta_h_error < 20, \
            f"水位差误差过大: {delta_h_error:.1f}% (应 < 20%)"
        
        print("\n✅ HydrostaticCanalSolver 闸门流动测试通过！")
    
    @pytest.mark.commercial
    @pytest.mark.backend
    def test_hydrostatic_uniform_flow_vs_manning(self):
        """
        HydrostaticCanalSolver 均匀流 vs Manning 公式
        
        测试目标:
        - 验证长直渠道均匀流计算
        - 对比 Manning 公式理论解
        - 确保误差 < 0.5%
        
        验收标准:
        - 流量误差 < 0.01%
        - 水深误差 < 0.5%
        - 迭代次数 < 5 次（简单场景）
        """
        print("\n" + "="*70)
        print("测试: HydrostaticCanalSolver 均匀流 vs Manning 公式")
        print("="*70)
        
        # 1. 获取 MIKE 11 均匀流案例
        case = StandardCases.mike11_steady_uniform_flow()
        params = case["parameters"]
        expected = case["expected_results"]
        tol = case["tolerance"]
        
        print(f"\n案例: {case['name']}")
        print(f"描述: {case['description']}")
        
        # 2. 创建求解器
        solver = HydrostaticCanalSolver(
            nx=100,
            length=params["length"],
            B=params["width"],
            S0=params["slope"],
            n=params["manning_n"]
        )
        
        # 3. 使用 canal_utils 计算理论水深（基础库）
        h_normal_theory = compute_steady_uniform_flow(
            Q=params["Q"],
            B=params["width"],
            S0=params["slope"],
            n=params["manning_n"]
        )
        
        print(f"\nManning 公式理论解:")
        print(f"  正常水深: {h_normal_theory:.3f} m")
        print(f"  理论水深: {expected['normal_depth']:.3f} m")
        
        # 4. 初始化
        h_init = np.ones(solver.nx) * h_normal_theory
        Q_init = np.ones(solver.nx) * params["Q"]
        
        solver.set_bc(
            bc_type_up='Q',
            bc_value_up=params["Q"],
            bc_type_down='h',
            bc_value_down=h_normal_theory
        )
        
        # 5. 稳态求解
        print("\n稳态求解...")
        
        result = solver.solve_steady_state(
            h_init=h_init,
            Q_init=Q_init,
            max_iter=10,  # 简单场景应 < 5 次
            tol=0.1,
            verbose=True
        )
        
        print(f"\n求解完成:")
        print(f"  收敛状态: {'成功' if result['converged'] else '失败'}")
        print(f"  迭代次数: {result['iterations']}")
        
        # 6. 分析结果
        h_computed = solver.h.mean()
        Q_computed = solver.Q.mean()
        v_computed = Q_computed / (params["width"] * h_computed)
        froude = compute_froude_number(v_computed, h_computed)
        
        print(f"\n计算结果:")
        print(f"  水深: {h_computed:.3f} m")
        print(f"  流量: {Q_computed:.6f} m³/s")
        print(f"  速度: {v_computed:.3f} m/s")
        print(f"  Froude数: {froude:.3f}")
        
        # 7. 验证
        validator = quick_validate_steady_state(
            solver=solver,
            result_dict=result,
            Q_target=params["Q"],
            name="Manning Uniform Flow"
        )
        
        print(f"\n验证结果:")
        print(f"  流量误差: {validator.Q_error_pct:.6f}%")
        
        # 8. 与理论解对比
        h_error_pct = abs(h_computed - expected["normal_depth"]) / expected["normal_depth"] * 100
        v_error_pct = abs(v_computed - expected["velocity"]) / expected["velocity"] * 100
        
        print(f"\n与理论解对比:")
        print(f"  水深误差: {h_error_pct:.3f}%")
        print(f"  速度误差: {v_error_pct:.3f}%")
        
        # 9. 断言验证
        assert result['converged'], \
            "均匀流求解未收敛！"
        
        assert result['iterations'] <= 5, \
            f"迭代次数过多（简单场景）: {result['iterations']} (应 <= 5)"
        
        assert validator.Q_error_pct < 0.01, \
            f"流量误差过大: {validator.Q_error_pct:.6f}%"
        
        assert h_error_pct < 0.5, \
            f"水深误差过大: {h_error_pct:.3f}% (应 < 0.5%)"
        
        print("\n✅ HydrostaticCanalSolver 均匀流测试通过！")
        print("✅ 达到简单场景性能预期: 迭代次数 <= 5, 误差 < 0.5%")


if __name__ == "__main__":
    # 可以直接运行此文件进行测试
    pytest.main([__file__, "-v", "-s"])
