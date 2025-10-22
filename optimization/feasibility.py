"""
优化问题可行性检查模块

提供MPC求解前后的可行性检查，确保不会输出不可行的结果。
"""

from typing import Dict, Any, Tuple, Optional
from enum import Enum
import warnings


class FeasibilityStatus(Enum):
    """可行性状态"""
    FEASIBLE = "feasible"  # 可行
    INFEASIBLE = "infeasible"  # 不可行
    UNKNOWN = "unknown"  # 未知


class FeasibilityResult:
    """可行性检查结果"""

    def __init__(
        self,
        status: FeasibilityStatus,
        message: str = "",
        details: Optional[Dict[str, Any]] = None
    ):
        self.status = status
        self.message = message
        self.details = details or {}

    @property
    def is_feasible(self) -> bool:
        """是否可行"""
        return self.status == FeasibilityStatus.FEASIBLE

    def __repr__(self):
        return f"FeasibilityResult(status={self.status.value}, message='{self.message}')"


def check_solver_results(results, model) -> FeasibilityResult:
    """
    检查求解器结果的可行性

    Args:
        results: Pyomo求解器结果
        model: Pyomo模型

    Returns:
        FeasibilityResult: 可行性检查结果
    """
    from pyomo.opt import TerminationCondition, SolverStatus

    # 检查求解器状态
    if not hasattr(results, 'solver'):
        return FeasibilityResult(
            FeasibilityStatus.UNKNOWN,
            "无法获取求解器状态"
        )

    termination = results.solver.termination_condition
    solver_status = results.solver.status

    # 最优解 - 可行
    if termination == TerminationCondition.optimal:
        return FeasibilityResult(
            FeasibilityStatus.FEASIBLE,
            "求解器返回最优解",
            {"termination": str(termination), "status": str(solver_status)}
        )

    # 不可行
    if termination in [
        TerminationCondition.infeasible,
        TerminationCondition.infeasibleOrUnbounded
    ]:
        return FeasibilityResult(
            FeasibilityStatus.INFEASIBLE,
            f"求解器判定问题不可行: {termination}",
            {"termination": str(termination), "status": str(solver_status)}
        )

    # 其他终止条件（超时、迭代限制等）- 视为未知
    if termination in [
        TerminationCondition.maxTimeLimit,
        TerminationCondition.maxIterations,
        TerminationCondition.maxEvaluations
    ]:
        # 检查是否有可行解
        if solver_status == SolverStatus.ok or solver_status == SolverStatus.warning:
            return FeasibilityResult(
                FeasibilityStatus.FEASIBLE,
                f"求解器在限制条件下终止但找到可行解: {termination}",
                {"termination": str(termination), "status": str(solver_status)}
            )
        else:
            return FeasibilityResult(
                FeasibilityStatus.UNKNOWN,
                f"求解器在限制条件下终止，未找到可行解: {termination}",
                {"termination": str(termination), "status": str(solver_status)}
            )

    # 其他未知情况
    return FeasibilityResult(
        FeasibilityStatus.UNKNOWN,
        f"未知的求解器终止条件: {termination}",
        {"termination": str(termination), "status": str(solver_status)}
    )


def check_constraint_violations(
    model,
    tolerance: float = 1e-6
) -> Tuple[bool, Dict[str, Any]]:
    """
    检查约束是否被违反

    Args:
        model: Pyomo模型
        tolerance: 容差

    Returns:
        (是否全部满足, 违反约束的详细信息)
    """
    from pyomo.environ import Constraint, value

    violations = []

    # 检查所有约束
    for constraint in model.component_objects(ctype=Constraint, active=True):
        for index in constraint:
            con = constraint[index]
            if con.active:
                try:
                    # 获取约束的值
                    body_value = value(con.body)

                    # 检查下界
                    if con.lower is not None:
                        lower_value = value(con.lower)
                        if body_value < lower_value - tolerance:
                            violations.append({
                                'constraint': str(constraint),
                                'index': str(index),
                                'type': 'lower_bound',
                                'value': body_value,
                                'bound': lower_value,
                                'violation': lower_value - body_value
                            })

                    # 检查上界
                    if con.upper is not None:
                        upper_value = value(con.upper)
                        if body_value > upper_value + tolerance:
                            violations.append({
                                'constraint': str(constraint),
                                'index': str(index),
                                'type': 'upper_bound',
                                'value': body_value,
                                'bound': upper_value,
                                'violation': body_value - upper_value
                            })

                except Exception as e:
                    # 无法评估约束，记录警告
                    warnings.warn(f"无法评估约束 {constraint}[{index}]: {e}")

    all_satisfied = len(violations) == 0
    details = {
        'num_violations': len(violations),
        'violations': violations[:10] if violations else []  # 最多返回前10个
    }

    return all_satisfied, details


def check_problem_feasibility(config: Dict[str, Any]) -> FeasibilityResult:
    """
    预先检查问题配置的基本可行性（不求解优化问题）

    Args:
        config: 网络配置

    Returns:
        FeasibilityResult: 可行性检查结果
    """
    issues = []

    # 检查时间序列
    periods = config.get('horizon', {}).get('periods', [])
    if not periods:
        issues.append("时间序列为空")

    # 检查节点
    nodes = config.get('nodes', [])
    if not nodes:
        issues.append("节点列表为空")

    # 检查边
    edges = config.get('edges', [])
    if not edges:
        issues.append("边列表为空")

    # 检查基本的供需平衡（启发式）
    total_inflow = 0.0
    total_demand = 0.0

    for node in nodes:
        node_id = node.get('id')
        attr = node.get('attributes', {}) or {}
        misc = attr.get('misc', {})

        # 计算入流
        inflow_key = misc.get('inflow_series')
        if inflow_key:
            series = config.get('series', {}).get(inflow_key, {})
            values = series.get('values', [])
            if values:
                total_inflow += sum(values)

        # 计算需求
        demand_key = attr.get('demand_profile') or misc.get('demand_series')
        if demand_key:
            series = config.get('series', {}).get(demand_key, {})
            values = series.get('values', [])
            if values:
                total_demand += sum(values)

    # 简单的供需平衡检查
    if total_demand > 0 and total_inflow > 0:
        if total_demand > total_inflow * 1.5:  # 需求远大于供给
            issues.append(
                f"需求({total_demand:.1f})可能超过供给({total_inflow:.1f})，"
                "问题可能不可行或需要缺水松弛"
            )

    # 检查状态初始值是否在范围内
    for node in nodes:
        states = node.get('states', {}) or {}
        for state_name, state_spec in states.items():
            initial = state_spec.get('initial', 0.0)
            bounds = state_spec.get('bounds')
            if bounds:
                lower, upper = bounds
                if lower is not None and initial < lower:
                    issues.append(
                        f"节点 {node.get('id')} 状态 {state_name} 初始值 {initial} "
                        f"低于下界 {lower}"
                    )
                if upper is not None and initial > upper:
                    issues.append(
                        f"节点 {node.get('id')} 状态 {state_name} 初始值 {initial} "
                        f"超过上界 {upper}"
                    )

    if issues:
        return FeasibilityResult(
            FeasibilityStatus.UNKNOWN,
            "配置可能存在问题",
            {"issues": issues}
        )
    else:
        return FeasibilityResult(
            FeasibilityStatus.FEASIBLE,
            "配置基本检查通过"
        )


__all__ = [
    'FeasibilityStatus',
    'FeasibilityResult',
    'check_solver_results',
    'check_constraint_violations',
    'check_problem_feasibility',
]
