#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
结果验证工具 - Result Validator

用于验证水力模拟结果的正确性，包括：
- 流量守恒验证
- 闸门流量验证
- 收敛性检查
- 结果质量评估
- 自动生成验证报告

Author: Claude
Date: 2025-10-23
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Any
import matplotlib.pyplot as plt


class ResultValidator:
    """结果验证器 - 用于验证水力模拟结果的正确性"""

    # 验证标准
    EXCELLENT_FLOW_ERROR = 0.01    # 优秀：< 0.01%
    GOOD_FLOW_ERROR = 0.1          # 良好：< 0.1%
    ACCEPTABLE_FLOW_ERROR = 1.0    # 可接受：< 1.0%

    EXCELLENT_GATE_ERROR = 0.5     # 优秀：< 0.5%
    GOOD_GATE_ERROR = 1.0          # 良好：< 1.0%
    ACCEPTABLE_GATE_ERROR = 5.0    # 可接受：< 5.0%

    def __init__(self, name: str = "Validation"):
        """
        初始化验证器

        Args:
            name: 验证任务名称
        """
        self.name = name
        self.results = {}
        self.passed = True
        self.messages = []

    def validate_flow_conservation(
        self,
        Q_computed: np.ndarray,
        Q_target: float,
        label: str = "Flow"
    ) -> Dict[str, Any]:
        """
        验证流量守恒

        Args:
            Q_computed: 计算得到的流量数组
            Q_target: 目标流量
            label: 标签名称

        Returns:
            验证结果字典
        """
        Q_mean = np.mean(Q_computed)
        Q_std = np.std(Q_computed)
        Q_min = np.min(Q_computed)
        Q_max = np.max(Q_computed)

        # 计算相对误差
        error_abs = abs(Q_mean - Q_target)
        error_percent = (error_abs / Q_target) * 100 if Q_target != 0 else float('inf')

        # 计算最大偏差
        max_deviation = max(abs(Q_max - Q_target), abs(Q_min - Q_target))
        max_deviation_percent = (max_deviation / Q_target) * 100 if Q_target != 0 else float('inf')

        # 评级
        if error_percent < self.EXCELLENT_FLOW_ERROR:
            grade = "优秀 (Excellent)"
            color = "green"
        elif error_percent < self.GOOD_FLOW_ERROR:
            grade = "良好 (Good)"
            color = "blue"
        elif error_percent < self.ACCEPTABLE_FLOW_ERROR:
            grade = "可接受 (Acceptable)"
            color = "orange"
        else:
            grade = "不合格 (Failed)"
            color = "red"
            self.passed = False

        result = {
            'label': label,
            'Q_target': Q_target,
            'Q_mean': Q_mean,
            'Q_std': Q_std,
            'Q_min': Q_min,
            'Q_max': Q_max,
            'error_abs': error_abs,
            'error_percent': error_percent,
            'max_deviation': max_deviation,
            'max_deviation_percent': max_deviation_percent,
            'grade': grade,
            'color': color,
            'passed': error_percent < self.ACCEPTABLE_FLOW_ERROR
        }

        self.results[f'flow_{label}'] = result

        msg = f"[{grade}] {label} 流量守恒: {error_percent:.6f}% (目标={Q_target:.4f}, 平均={Q_mean:.4f})"
        self.messages.append(msg)
        print(msg)

        return result

    def validate_gate_discharge(
        self,
        solver,
        gate_objects: List,
        gate_indices: List[int],
        Q_target: float,
        result_h: np.ndarray,
        labels: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        验证闸门流量

        Args:
            solver: 求解器对象
            gate_objects: 闸门对象列表
            gate_indices: 闸门节点索引列表
            Q_target: 目标流量
            result_h: 结果水深数组
            labels: 闸门标签列表

        Returns:
            验证结果字典
        """
        if labels is None:
            labels = [f"闸门{i+1}" for i in range(len(gate_objects))]

        gate_results = []
        all_passed = True

        for i, (idx, gate, label) in enumerate(zip(gate_indices, gate_objects, labels)):
            # 获取上下游水深
            h_up = result_h[idx - 1]
            h_down = result_h[idx + 1]

            # 计算闸门流量
            Q_gate, flow_type = gate.calculate_discharge(h_up, h_down)

            # 计算误差
            error_abs = abs(Q_gate - Q_target)
            error_percent = (error_abs / Q_target) * 100 if Q_target != 0 else float('inf')

            # 评级
            if error_percent < self.EXCELLENT_GATE_ERROR:
                grade = "优秀"
                color = "green"
            elif error_percent < self.GOOD_GATE_ERROR:
                grade = "良好"
                color = "blue"
            elif error_percent < self.ACCEPTABLE_GATE_ERROR:
                grade = "可接受"
                color = "orange"
            else:
                grade = "不合格"
                color = "red"
                all_passed = False
                self.passed = False

            gate_result = {
                'label': label,
                'index': idx,
                'h_upstream': h_up,
                'h_downstream': h_down,
                'delta_h': h_up - h_down,
                'Q_gate': Q_gate,
                'Q_target': Q_target,
                'flow_type': flow_type,
                'error_abs': error_abs,
                'error_percent': error_percent,
                'grade': grade,
                'color': color,
                'passed': error_percent < self.ACCEPTABLE_GATE_ERROR
            }

            gate_results.append(gate_result)

            msg = f"[{grade}] {label}: Q={Q_gate:.4f} m³/s (误差{error_percent:.2f}%, {flow_type})"
            self.messages.append(msg)
            print(msg)

        result = {
            'gates': gate_results,
            'all_passed': all_passed,
            'num_gates': len(gate_results),
            'avg_error': np.mean([g['error_percent'] for g in gate_results])
        }

        self.results['gates'] = result
        return result

    def validate_convergence(
        self,
        result_dict: Dict,
        max_iterations: int = 5000
    ) -> Dict[str, Any]:
        """
        验证收敛性

        Args:
            result_dict: 求解器返回的结果字典
            max_iterations: 最大迭代次数

        Returns:
            验证结果字典
        """
        converged = result_dict.get('converged', False)
        iterations = result_dict.get('iterations', 0)

        # 评估收敛速度
        if iterations <= 1:
            speed = "极快 (1次)"
            color = "green"
        elif iterations <= 10:
            speed = f"很快 ({iterations}次)"
            color = "green"
        elif iterations <= 100:
            speed = f"正常 ({iterations}次)"
            color = "blue"
        elif iterations <= 1000:
            speed = f"较慢 ({iterations}次)"
            color = "orange"
        else:
            speed = f"很慢 ({iterations}次)"
            color = "red"

        result = {
            'converged': converged,
            'iterations': iterations,
            'max_iterations': max_iterations,
            'speed': speed,
            'color': color,
            'passed': converged
        }

        if not converged:
            self.passed = False

        status = " 收敛" if converged else " 未收敛"
        msg = f"[{status}] 迭代次数: {iterations} ({speed})"
        self.messages.append(msg)
        print(msg)

        self.results['convergence'] = result
        return result

    def plot_flow_distribution(
        self,
        x: np.ndarray,
        Q: np.ndarray,
        Q_target: float,
        gate_positions: Optional[List[float]] = None,
        title: str = "Flow Distribution",
        save_path: Optional[str] = None
    ) -> plt.Figure:
        """
        绘制流量分布图

        Args:
            x: 位置坐标
            Q: 流量数组
            Q_target: 目标流量
            gate_positions: 闸门位置列表
            title: 图表标题
            save_path: 保存路径（可选）

        Returns:
            图表对象
        """
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))

        # 流量分布
        ax1.plot(x, Q, 'b-', linewidth=2.5, label='Computed Flow')
        ax1.axhline(y=Q_target, color='k', linestyle='--', linewidth=1.5,
                    label=f'Target: {Q_target:.4f} m³/s', alpha=0.7)

        if gate_positions:
            for i, pos in enumerate(gate_positions):
                ax1.axvline(x=pos, color='r', linestyle=':', alpha=0.5)
                ax1.text(pos, Q_target * 1.02, f'Gate {i+1}',
                        ha='center', fontsize=9, color='red')

        ax1.set_xlabel('Distance (m)', fontsize=12)
        ax1.set_ylabel('Flow Rate (m³/s)', fontsize=12)
        ax1.set_title(title, fontsize=14, fontweight='bold')
        ax1.legend(fontsize=11)
        ax1.grid(True, alpha=0.3)

        # 误差分布
        Q_error = np.abs(Q - Q_target) / Q_target * 100
        ax2.plot(x, Q_error, 'r-', linewidth=2, label='Relative Error')
        ax2.axhline(y=self.EXCELLENT_FLOW_ERROR, color='g', linestyle='--',
                    linewidth=1, label=f'Excellent: {self.EXCELLENT_FLOW_ERROR}%', alpha=0.7)
        ax2.axhline(y=self.GOOD_FLOW_ERROR, color='b', linestyle='--',
                    linewidth=1, label=f'Good: {self.GOOD_FLOW_ERROR}%', alpha=0.7)
        ax2.axhline(y=self.ACCEPTABLE_FLOW_ERROR, color='orange', linestyle='--',
                    linewidth=1, label=f'Acceptable: {self.ACCEPTABLE_FLOW_ERROR}%', alpha=0.7)

        if gate_positions:
            for pos in gate_positions:
                ax2.axvline(x=pos, color='r', linestyle=':', alpha=0.5)

        ax2.set_xlabel('Distance (m)', fontsize=12)
        ax2.set_ylabel('Relative Error (%)', fontsize=12)
        ax2.set_title('Flow Conservation Error', fontsize=13, fontweight='bold')
        ax2.legend(fontsize=10)
        ax2.grid(True, alpha=0.3)
        ax2.set_yscale('log')

        plt.tight_layout()

        if save_path:
            fig.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"   图表已保存: {save_path}")

        return fig

    def generate_report(self, print_report: bool = True) -> str:
        """
        生成验证报告

        Args:
            print_report: 是否打印报告

        Returns:
            报告文本
        """
        lines = []
        lines.append("=" * 80)
        lines.append(f"验证报告 - {self.name}")
        lines.append("=" * 80)
        lines.append("")

        # 总体结果
        status = " 通过" if self.passed else " 失败"
        lines.append(f"总体结果: {status}")
        lines.append("")

        # 详细消息
        lines.append("详细结果:")
        for msg in self.messages:
            lines.append(f"  {msg}")
        lines.append("")

        # 流量守恒
        if any(k.startswith('flow_') for k in self.results):
            lines.append("流量守恒验证:")
            for key, result in self.results.items():
                if key.startswith('flow_'):
                    lines.append(f"  {result['label']}:")
                    lines.append(f"    目标流量: {result['Q_target']:.4f} m³/s")
                    lines.append(f"    平均流量: {result['Q_mean']:.4f} m³/s")
                    lines.append(f"    流量范围: [{result['Q_min']:.4f}, {result['Q_max']:.4f}] m³/s")
                    lines.append(f"    相对误差: {result['error_percent']:.6f}%")
                    lines.append(f"    评级: {result['grade']}")
            lines.append("")

        # 闸门验证
        if 'gates' in self.results:
            lines.append("闸门流量验证:")
            for gate in self.results['gates']['gates']:
                lines.append(f"  {gate['label']}:")
                lines.append(f"    上游水深: {gate['h_upstream']:.4f} m")
                lines.append(f"    下游水深: {gate['h_downstream']:.4f} m")
                lines.append(f"    水位差: {gate['delta_h']:.4f} m")
                lines.append(f"    闸门流量: {gate['Q_gate']:.4f} m³/s")
                lines.append(f"    相对误差: {gate['error_percent']:.2f}%")
                lines.append(f"    流态: {gate['flow_type']}")
                lines.append(f"    评级: {gate['grade']}")
            lines.append(f"  平均误差: {self.results['gates']['avg_error']:.2f}%")
            lines.append("")

        # 收敛性
        if 'convergence' in self.results:
            conv = self.results['convergence']
            lines.append("收敛性验证:")
            lines.append(f"  状态: {'收敛' if conv['converged'] else '未收敛'}")
            lines.append(f"  迭代次数: {conv['iterations']}")
            lines.append(f"  收敛速度: {conv['speed']}")
            lines.append("")

        lines.append("=" * 80)

        report = "\n".join(lines)

        if print_report:
            print(report)

        return report

    def save_report(self, filepath: str):
        """
        保存报告到文件

        Args:
            filepath: 文件路径
        """
        report = self.generate_report(print_report=False)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f" 报告已保存: {filepath}")


# 便捷函数
def quick_validate_steady_state(
    solver,
    result_dict: Dict,
    Q_target: float,
    name: str = "Steady State Validation"
) -> ResultValidator:
    """
    快速验证稳态结果

    Args:
        solver: 求解器对象（必须有structure_indices和structure_objects属性）
        result_dict: 求解器返回的结果字典
        Q_target: 目标流量
        name: 验证名称

    Returns:
        ResultValidator对象
    """
    validator = ResultValidator(name=name)

    print(f"\n{'='*80}")
    print(f"{name}")
    print(f"{'='*80}\n")

    # 验证收敛性
    validator.validate_convergence(result_dict)

    # 验证流量守恒
    Q_computed = result_dict.get('Q', solver.hu)
    validator.validate_flow_conservation(Q_computed, Q_target, label="Overall")

    # 验证闸门流量（如果有）
    if hasattr(solver, 'structure_indices') and len(solver.structure_indices) > 0:
        print("\n闸门流量验证:")
        validator.validate_gate_discharge(
            solver=solver,
            gate_objects=solver.structure_objects,
            gate_indices=solver.structure_indices,
            Q_target=Q_target,
            result_h=result_dict.get('h', solver.h)
        )

    print()
    return validator
