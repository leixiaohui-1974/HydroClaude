#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
多重验证器

对模拟结果进行多级验证，确保结果质量

作者: Claude
日期: 2025-10-24
"""

import numpy as np
from typing import Dict, Optional
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.result_validator import ResultValidator
from modeling.constants import ValidationConstants


class MultiValidator:
    """
    多重验证器

    执行4级验证：
    1. 流量守恒
    2. 物理合理性
    3. 数值稳定性
    4. 结构物流量验证
    """

    def __init__(self):
        """初始化验证器"""
        self.validator = ResultValidator("多重验证")
        self.validation_results = {}
        self.all_passed = True

    def run_all_validations(self, solver, Q_target: float,
                           h_history: Optional[np.ndarray] = None) -> Dict:
        """
        运行所有验证

        Args:
            solver: HydrostaticCanalSolver实例
            Q_target: 目标流量 (m³/s)
            h_history: 水深历史（可选，用于稳定性分析）

        Returns:
            validation_results: 验证结果汇总
        """
        print("\n" + "=" * 80)
        print("多重验证开始")
        print("=" * 80)

        # 1. 流量守恒验证
        print("\n[1/4] 流量守恒验证...")
        Q = solver.hu * solver.B
        flow_result = self.validator.validate_flow_conservation(
            Q_computed=Q,
            Q_target=Q_target,
            label="全渠道"
        )
        self.validation_results['flow_conservation'] = flow_result

        # 2. 物理合理性验证
        print("\n[2/4] 物理合理性验证...")
        phys_result = self._validate_physics(solver)
        self.validation_results['physical'] = phys_result

        # 3. 数值稳定性验证
        print("\n[3/4] 数值稳定性验证...")
        stab_result = self._validate_stability(solver, h_history)
        self.validation_results['stability'] = stab_result

        # 4. 结构物验证
        print("\n[4/4] 结构物验证...")
        struct_result = self._validate_structures(solver, Q_target)
        self.validation_results['structures'] = struct_result

        # 汇总
        print("\n" + "=" * 80)
        print("验证完成")
        print("=" * 80)

        self.all_passed = all([
            flow_result['passed'],
            phys_result['passed'],
            stab_result['passed'],
            struct_result['passed']
        ])

        print(f"\n总体结果: {' 全部通过' if self.all_passed else ' 存在问题'}")

        return self.validation_results

    def _validate_physics(self, solver) -> Dict:
        """验证物理合理性"""
        h = solver.h
        u = solver.hu / solver.h
        Fr = u / np.sqrt(solver.g * h)

        # 检查（使用ValidationConstants中的阈值）
        h_positive = np.all(h > ValidationConstants.MIN_DEPTH)
        Fr_reasonable = np.all((Fr > 0) & (Fr < ValidationConstants.MAX_FROUDE_NUMBER))
        u_reasonable = np.all(np.abs(u) < ValidationConstants.MAX_VELOCITY)

        passed = h_positive and Fr_reasonable and u_reasonable

        result = {
            'h_positive': h_positive,
            'h_min': np.min(h),
            'h_max': np.max(h),
            'Fr_reasonable': Fr_reasonable,
            'Fr_min': np.min(Fr),
            'Fr_max': np.max(Fr),
            'u_reasonable': u_reasonable,
            'u_min': np.min(u),
            'u_max': np.max(u),
            'passed': passed
        }

        status = " 通过" if passed else " 未通过"
        print(f"  物理合理性: {status}")
        print(f"    水深范围: [{result['h_min']:.3f}, {result['h_max']:.3f}] m")
        print(f"    Froude数范围: [{result['Fr_min']:.3f}, {result['Fr_max']:.3f}]")
        print(f"    流速范围: [{result['u_min']:.3f}, {result['u_max']:.3f}] m/s")

        return result

    def _validate_stability(self, solver, h_history: Optional[np.ndarray]) -> Dict:
        """验证数值稳定性"""
        h = solver.h

        # 基本稳定性检查（使用ValidationConstants中的阈值）
        has_nan = np.any(np.isnan(h))
        has_inf = np.any(np.isinf(h))
        bounded = np.all((h > ValidationConstants.MIN_DEPTH) &
                        (h < ValidationConstants.MAX_DEPTH))

        # 变差检查（BV范数）
        dh = np.diff(h)
        total_variation = np.sum(np.abs(dh))
        h_mean = np.mean(h)
        tv_normalized = total_variation / (len(h) * h_mean)

        passed = (not has_nan) and (not has_inf) and bounded and \
                 (tv_normalized < ValidationConstants.MAX_TOTAL_VARIATION)

        result = {
            'has_nan': has_nan,
            'has_inf': has_inf,
            'bounded': bounded,
            'total_variation': total_variation,
            'tv_normalized': tv_normalized,
            'passed': passed
        }

        status = " 通过" if passed else " 未通过"
        print(f"  数值稳定性: {status}")
        print(f"    NaN/Inf检查: {'无' if not (has_nan or has_inf) else '存在'}")
        print(f"    有界性: {'是' if bounded else '否'}")
        print(f"    归一化总变差: {tv_normalized:.6f}")

        return result

    def _validate_structures(self, solver, Q_target: float) -> Dict:
        """验证结构物流量"""
        if not hasattr(solver, 'structure_objects') or not solver.structure_objects:
            result = {
                'n_structures': 0,
                'passed': True
            }
            print(f"  结构物验证: 无结构物，跳过")
            return result

        # 使用ResultValidator的方法
        try:
            gate_result = self.validator.validate_gate_discharge(
                solver=solver,
                gate_objects=solver.structure_objects,
                gate_indices=solver.structure_indices,
                Q_target=Q_target,
                result_h=solver.h,
                labels=[f"结构物{i+1}" for i in range(len(solver.structure_objects))]
            )
            passed = gate_result.get('all_passed', True)
        except Exception as e:
            print(f"   结构物验证失败: {e}")
            passed = False
            gate_result = {'error': str(e)}

        result = {
            'n_structures': len(solver.structure_objects),
            'details': gate_result,
            'passed': passed
        }

        return result

    def generate_report(self, filepath: str):
        """
        生成验证报告

        Args:
            filepath: 报告文件路径
        """
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("HydroClaude 多重验证报告\n")
            f.write("=" * 80 + "\n\n")

            # 1. 流量守恒
            if 'flow_conservation' in self.validation_results:
                r = self.validation_results['flow_conservation']
                f.write("1. 流量守恒验证\n")
                f.write("-" * 80 + "\n")
                f.write(f"  目标流量: {r['Q_target']:.4f} m³/s\n")
                f.write(f"  平均流量: {r['Q_mean']:.4f} m³/s\n")
                f.write(f"  相对误差: {r['error_percent']:.6f}%\n")
                f.write(f"  评级: {r['grade']}\n")
                f.write(f"  状态: {' 通过' if r['passed'] else ' 未通过'}\n\n")

            # 2. 物理合理性
            if 'physical' in self.validation_results:
                r = self.validation_results['physical']
                f.write("2. 物理合理性验证\n")
                f.write("-" * 80 + "\n")
                f.write(f"  水深范围: [{r['h_min']:.3f}, {r['h_max']:.3f}] m\n")
                f.write(f"  Froude数范围: [{r['Fr_min']:.3f}, {r['Fr_max']:.3f}]\n")
                f.write(f"  流速范围: [{r['u_min']:.3f}, {r['u_max']:.3f}] m/s\n")
                f.write(f"  状态: {' 通过' if r['passed'] else ' 未通过'}\n\n")

            # 3. 数值稳定性
            if 'stability' in self.validation_results:
                r = self.validation_results['stability']
                f.write("3. 数值稳定性验证\n")
                f.write("-" * 80 + "\n")
                f.write(f"  NaN/Inf: {'无' if not (r['has_nan'] or r['has_inf']) else '存在'}\n")
                f.write(f"  有界性: {'是' if r['bounded'] else '否'}\n")
                f.write(f"  归一化总变差: {r['tv_normalized']:.6f}\n")
                f.write(f"  状态: {' 通过' if r['passed'] else ' 未通过'}\n\n")

            # 4. 结构物
            if 'structures' in self.validation_results:
                r = self.validation_results['structures']
                f.write("4. 结构物验证\n")
                f.write("-" * 80 + "\n")
                f.write(f"  结构物数量: {r['n_structures']}\n")
                f.write(f"  状态: {' 通过' if r['passed'] else ' 未通过'}\n\n")

            # 总结
            f.write("=" * 80 + "\n")
            f.write(f"总体结果: {' 全部通过' if self.all_passed else ' 存在问题'}\n")
            f.write("=" * 80 + "\n")

        print(f"\n 验证报告已保存: {filepath}")

    def __repr__(self) -> str:
        return f"MultiValidator(passed={self.all_passed})"


if __name__ == "__main__":
    print("多重验证器模块")
    print("请通过UniversalModeler使用此模块")
