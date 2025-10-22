"""
通用工具模块

提供时间序列生成、结果提取、求解器管理等通用功能。
"""

from typing import Dict, List, Any, Optional, Callable
import numpy as np
from pyomo.environ import SolverFactory, value
from datetime import datetime, timedelta

from .exceptions import SolverError
from .defaults import OPTIMIZATION_DEFAULTS
from .feasibility import check_solver_results


class TimeSeriesGenerator:
    """时间序列生成器"""

    @staticmethod
    def create_periods(num_periods: int, prefix: str = "t", start_index: int = 0) -> List[str]:
        """
        创建时间周期标识符

        Args:
            num_periods: 周期数量
            prefix: 前缀
            start_index: 起始索引

        Returns:
            时间周期列表
        """
        return [f"{prefix}{i:02d}" for i in range(start_index, start_index + num_periods)]

    @staticmethod
    def create_datetime_periods(
        start_time: datetime,
        num_periods: int,
        step_hours: float = 1.0
    ) -> List[str]:
        """
        创建基于日期时间的周期

        Args:
            start_time: 起始时间
            num_periods: 周期数量
            step_hours: 时间步长（小时）

        Returns:
            时间周期列表（ISO格式字符串）
        """
        periods = []
        for i in range(num_periods):
            dt = start_time + timedelta(hours=i * step_hours)
            periods.append(dt.isoformat())
        return periods

    @staticmethod
    def constant(value: float, num_periods: int) -> List[float]:
        """
        生成常数序列

        Args:
            value: 常数值
            num_periods: 周期数量

        Returns:
            常数值列表
        """
        return [value] * num_periods

    @staticmethod
    def sinusoidal(
        base: float,
        amplitude: float,
        num_periods: int,
        frequency: float = 1.0,
        phase: float = 0.0,
        noise_std: float = 0.0
    ) -> List[float]:
        """
        生成正弦曲线序列

        Args:
            base: 基础值
            amplitude: 振幅
            num_periods: 周期数量
            frequency: 频率（周期数）
            phase: 相位
            noise_std: 噪声标准差

        Returns:
            正弦曲线值列表
        """
        values = []
        for i in range(num_periods):
            value = base + amplitude * np.sin(2 * np.pi * frequency * i / num_periods + phase)
            if noise_std > 0:
                value += np.random.randn() * noise_std
            values.append(value)
        return values

    @staticmethod
    def step_change(
        initial_value: float,
        final_value: float,
        num_periods: int,
        change_start: int,
        change_duration: Optional[int] = None
    ) -> List[float]:
        """
        生成阶跃变化序列

        Args:
            initial_value: 初始值
            final_value: 最终值
            num_periods: 总周期数
            change_start: 变化开始时刻
            change_duration: 变化持续时间（None表示永久变化）

        Returns:
            阶跃变化值列表
        """
        values = [initial_value] * num_periods

        if change_duration is None:
            # 永久变化
            for i in range(change_start, num_periods):
                values[i] = final_value
        else:
            # 临时变化
            change_end = min(change_start + change_duration, num_periods)
            for i in range(change_start, change_end):
                values[i] = final_value

        return values

    @staticmethod
    def piecewise(
        values_list: List[float],
        durations: List[int]
    ) -> List[float]:
        """
        生成分段常数序列

        Args:
            values_list: 各段的值
            durations: 各段的持续时间

        Returns:
            分段常数值列表
        """
        if len(values_list) != len(durations):
            raise ValueError("values_list和durations长度必须相同")

        result = []
        for value, duration in zip(values_list, durations):
            result.extend([value] * duration)
        return result


class ResultExtractor:
    """优化结果提取器"""

    @staticmethod
    def extract_node_states(
        model,
        node_ids: Optional[List[str]] = None,
        state_names: Optional[List[str]] = None
    ) -> Dict[str, Dict[str, List[float]]]:
        """
        提取节点状态

        Args:
            model: Pyomo模型
            node_ids: 节点ID列表（None表示所有节点）
            state_names: 状态名称列表（None表示所有状态）

        Returns:
            {node_id: {state_name: [values_over_time]}}
        """
        if not hasattr(model, 'state_index') or not hasattr(model, 'state'):
            return {}

        periods = list(model.T)
        results = {}

        for node_id, state_name in model.state_index:
            if node_ids is not None and node_id not in node_ids:
                continue
            if state_names is not None and state_name not in state_names:
                continue

            if node_id not in results:
                results[node_id] = {}

            values = [value(model.state[(node_id, state_name), t]) for t in periods]
            results[node_id][state_name] = values

        return results

    @staticmethod
    def extract_edge_flows(
        model,
        edge_ids: Optional[List[str]] = None
    ) -> Dict[str, List[float]]:
        """
        提取边流量

        Args:
            model: Pyomo模型
            edge_ids: 边ID列表（None表示所有边）

        Returns:
            {edge_id: [flows_over_time]}
        """
        if not hasattr(model, 'flow'):
            return {}

        periods = list(model.T)
        results = {}

        for edge_id in model.E:
            if edge_ids is not None and edge_id not in edge_ids:
                continue

            flows = [value(model.flow[edge_id, t]) for t in periods]
            results[edge_id] = flows

        return results

    @staticmethod
    def extract_shortages(model) -> Dict[str, List[float]]:
        """
        提取缺水量

        Args:
            model: Pyomo模型

        Returns:
            {node_id: [shortages_over_time]}
        """
        if not hasattr(model, 'shortage') or not hasattr(model, 'shortage_nodes'):
            return {}

        periods = list(model.T)
        results = {}

        for node_id in model.shortage_nodes:
            shortages = [value(model.shortage[node_id, t]) for t in periods]
            results[node_id] = shortages

        return results

    @staticmethod
    def extract_objective_components(model) -> Dict[str, float]:
        """
        提取目标函数组成部分

        Args:
            model: Pyomo模型

        Returns:
            目标函数各组成部分的值
        """
        results = {}

        if hasattr(model, 'obj'):
            results['total_objective'] = value(model.obj)

        if hasattr(model, 'total_energy_cost'):
            results['energy_cost'] = value(model.total_energy_cost)

        if hasattr(model, 'total_shortage_volume'):
            results['shortage_volume'] = value(model.total_shortage_volume)

        if hasattr(model, 'total_shortage_penalty'):
            results['shortage_penalty'] = value(model.total_shortage_penalty)

        return results


class SolverManager:
    """求解器管理器"""

    def __init__(
        self,
        solver_name: Optional[str] = None,
        solver_options: Optional[Dict[str, Any]] = None,
        check_feasibility: bool = True
    ):
        """
        初始化求解器管理器

        Args:
            solver_name: 求解器名称（None使用默认）
            solver_options: 求解器选项
            check_feasibility: 是否检查可行性
        """
        self.solver_name = solver_name or OPTIMIZATION_DEFAULTS.default_solver
        self.solver_options = solver_options or {}
        self.check_feasibility = check_feasibility

        # 创建求解器
        self.solver = SolverFactory(self.solver_name)
        if not self.solver.available(exception_flag=False):
            raise SolverError(f"求解器 {self.solver_name} 不可用")

    def solve(
        self,
        model,
        tee: bool = False,
        raise_on_infeasible: bool = True
    ) -> Any:
        """
        求解模型

        Args:
            model: Pyomo模型
            tee: 是否显示求解器输出
            raise_on_infeasible: 不可行时是否抛出异常

        Returns:
            求解结果

        Raises:
            SolverError: 求解失败或不可行
        """
        try:
            results = self.solver.solve(model, tee=tee, options=self.solver_options)

            if self.check_feasibility:
                feasibility_result = check_solver_results(results, model)

                if not feasibility_result.is_feasible:
                    if raise_on_infeasible:
                        raise SolverError(
                            f"求解失败: {feasibility_result.message}\n"
                            f"详细信息: {feasibility_result.details}"
                        )

            return results

        except SolverError:
            raise
        except Exception as e:
            raise SolverError(f"求解过程发生错误: {str(e)}") from e

    def solve_with_callback(
        self,
        model,
        callback: Optional[Callable] = None,
        tee: bool = False
    ) -> Any:
        """
        求解模型并执行回调

        Args:
            model: Pyomo模型
            callback: 求解后的回调函数 callback(model, results)
            tee: 是否显示求解器输出

        Returns:
            求解结果
        """
        results = self.solve(model, tee=tee)

        if callback:
            callback(model, results)

        return results


__all__ = [
    'TimeSeriesGenerator',
    'ResultExtractor',
    'SolverManager',
]
