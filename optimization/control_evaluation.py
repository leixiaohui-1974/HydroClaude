"""
控制效果评价模块

提供多种控制性能指标的计算方法，包括：
- 时域性能指标（IAE, ISE, ITAE, ITSE等）
- 统计性能指标（MAE, RMSE, 峰值等）
- 控制平滑度指标（TV, 变化率等）
- 综合性能评分
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Union, Optional


class ControlPerformanceEvaluator:
    """控制性能评价器"""

    def __init__(self, targets: Union[List[float], Dict[str, float]]):
        """
        Args:
            targets: 目标值
                - List: [target1, target2, ...]
                - Dict: {"variable1": target1, "variable2": target2}
        """
        if isinstance(targets, list):
            self.targets = {f"var{i+1}": t for i, t in enumerate(targets)}
        else:
            self.targets = targets

    def evaluate_time_domain(
        self,
        df: pd.DataFrame,
        time_col: str = "time",
        value_cols: Optional[List[str]] = None
    ) -> Dict[str, Dict[str, float]]:
        """
        计算时域性能指标

        Args:
            df: 数据DataFrame
            time_col: 时间列名
            value_cols: 要评估的变量列名列表

        Returns:
            {variable_name: {metric: value}}
        """
        if value_cols is None:
            value_cols = [col for col in df.columns if col != time_col]

        results = {}

        for col in value_cols:
            # 查找对应的目标值
            target = None
            for key, val in self.targets.items():
                if key in col or col in key:
                    target = val
                    break

            if target is None:
                continue

            # 计算误差
            error = df[col].values - target
            time = df[time_col].values
            dt = np.diff(time)
            dt = np.append(dt, dt[-1] if len(dt) > 0 else 1)

            # 计算各项指标
            metrics = {}

            # 1. 绝对误差积分 (IAE - Integral of Absolute Error)
            metrics['IAE'] = np.sum(np.abs(error) * dt)

            # 2. 平方误差积分 (ISE - Integral of Squared Error)
            metrics['ISE'] = np.sum(error**2 * dt)

            # 3. 时间加权绝对误差积分 (ITAE)
            metrics['ITAE'] = np.sum(time * np.abs(error) * dt)

            # 4. 时间加权平方误差积分 (ITSE)
            metrics['ITSE'] = np.sum(time * error**2 * dt)

            # 5. 平均绝对误差 (MAE)
            metrics['MAE'] = np.mean(np.abs(error))

            # 6. 均方根误差 (RMSE)
            metrics['RMSE'] = np.sqrt(np.mean(error**2))

            # 7. 最大绝对误差
            metrics['max_abs_error'] = np.max(np.abs(error))

            # 8. 最大正偏差
            metrics['max_positive_dev'] = np.max(error)

            # 9. 最大负偏差
            metrics['max_negative_dev'] = np.min(error)

            # 10. 标准差
            metrics['std'] = np.std(error)

            # 11. 方差
            metrics['variance'] = np.var(error)

            # 12. 超调量（如果有）
            overshoot = np.max(error) if np.max(error) > 0 else 0
            metrics['overshoot'] = overshoot

            # 13. 下冲量（如果有）
            undershoot = abs(np.min(error)) if np.min(error) < 0 else 0
            metrics['undershoot'] = undershoot

            results[col] = metrics

        return results

    def evaluate_control_smoothness(
        self,
        df: pd.DataFrame,
        control_cols: List[str],
        time_col: str = "time"
    ) -> Dict[str, Dict[str, float]]:
        """
        评估控制平滑度

        Args:
            df: 数据DataFrame
            control_cols: 控制变量列名列表
            time_col: 时间列名

        Returns:
            {control_name: {metric: value}}
        """
        results = {}

        for col in control_cols:
            control = df[col].values
            time = df[time_col].values
            dt = np.diff(time)
            dt = np.append(dt, dt[-1] if len(dt) > 0 else 1)

            metrics = {}

            # 1. 总变差 (Total Variation)
            changes = np.diff(control)
            metrics['TV'] = np.sum(np.abs(changes))

            # 2. 平均变化率
            metrics['avg_change_rate'] = np.mean(np.abs(changes))

            # 3. 最大变化率
            metrics['max_change_rate'] = np.max(np.abs(changes))

            # 4. 标准差
            metrics['std'] = np.std(control)

            # 5. 变化次数（方向改变）
            sign_changes = np.diff(np.sign(changes))
            metrics['direction_changes'] = np.sum(np.abs(sign_changes) > 0)

            # 6. 平滑度指标（变化的标准差）
            metrics['smoothness'] = np.std(changes)

            # 7. 控制能量
            metrics['control_energy'] = np.sum(control**2 * dt)

            # 8. 控制幅度范围
            metrics['range'] = np.max(control) - np.min(control)

            results[col] = metrics

        return results

    def evaluate_settling(
        self,
        df: pd.DataFrame,
        value_col: str,
        target: float,
        settling_threshold: float = 0.02,  # 2%误差带
        time_col: str = "time"
    ) -> Dict[str, float]:
        """
        评估调节时间和稳态性能

        Args:
            df: 数据DataFrame
            value_col: 变量列名
            target: 目标值
            settling_threshold: 稳态误差带（相对值）
            time_col: 时间列名

        Returns:
            调节时间相关指标
        """
        values = df[value_col].values
        time = df[time_col].values
        error = np.abs(values - target) / target

        # 调节时间：最后一次离开误差带的时间
        in_band = error <= settling_threshold
        if np.any(~in_band):
            # 找到最后一次在误差带外的索引
            last_out_idx = np.where(~in_band)[0][-1]
            settling_time = time[last_out_idx + 1] if last_out_idx + 1 < len(time) else time[-1]
        else:
            settling_time = time[0]  # 一直在误差带内

        # 稳态误差（后10%时间的平均误差）
        steady_start_idx = int(len(values) * 0.9)
        steady_state_error = np.mean(np.abs(values[steady_start_idx:] - target))

        return {
            'settling_time': settling_time,
            'settling_threshold': settling_threshold * 100,  # 转为百分比
            'steady_state_error': steady_state_error,
            'time_in_band_ratio': np.sum(in_band) / len(in_band)
        }

    def compute_综合评分(
        self,
        时域指标: Dict[str, Dict[str, float]],
        平滑度指标: Dict[str, Dict[str, float]],
        权重: Optional[Dict[str, float]] = None
    ) -> Dict[str, float]:
        """
        计算综合性能评分

        Args:
            时域指标: 时域性能指标
            平滑度指标: 控制平滑度指标
            权重: 各指标权重 {"tracking": 0.6, "smoothness": 0.4}

        Returns:
            综合评分结果
        """
        if 权重 is None:
            权重 = {"tracking": 0.6, "smoothness": 0.4}

        # 跟踪性能评分（基于MAE，越小越好）
        mae_values = []
        for var_metrics in 时域指标.values():
            if 'MAE' in var_metrics:
                mae_values.append(var_metrics['MAE'])

        avg_mae = np.mean(mae_values) if mae_values else 0

        # 平滑度评分（基于TV，越小越好）
        tv_values = []
        for ctrl_metrics in 平滑度指标.values():
            if 'TV' in ctrl_metrics:
                tv_values.append(ctrl_metrics['TV'])

        avg_tv = np.mean(tv_values) if tv_values else 0

        # 归一化评分（转换为0-100分，假设MAE<0.05为满分，TV<50为满分）
        tracking_score = max(0, 100 * (1 - avg_mae / 0.05))
        smoothness_score = max(0, 100 * (1 - avg_tv / 50))

        综合分数 = 权重["tracking"] * tracking_score + 权重["smoothness"] * smoothness_score

        return {
            "综合评分": 综合分数,
            "跟踪性能分": tracking_score,
            "平滑度分": smoothness_score,
            "平均MAE": avg_mae,
            "平均TV": avg_tv
        }


def print_performance_report(
    时域指标: Dict[str, Dict[str, float]],
    平滑度指标: Optional[Dict[str, Dict[str, float]]] = None,
    综合评分: Optional[Dict[str, float]] = None
) -> None:
    """
    打印性能报告

    Args:
        时域指标: 时域性能指标
        平滑度指标: 控制平滑度指标
        综合评分: 综合评分结果
    """
    print("\n" + "="*80)
    print("控制性能评价报告")
    print("="*80)

    print("\n【时域性能指标】")
    for var_name, metrics in 时域指标.items():
        print(f"\n  {var_name}:")
        print(f"    MAE (平均绝对误差):     {metrics['MAE']:.6f}")
        print(f"    RMSE (均方根误差):       {metrics['RMSE']:.6f}")
        print(f"    最大偏差:               {metrics['max_abs_error']:.6f}")
        print(f"    标准差:                 {metrics['std']:.6f}")
        print(f"    IAE (绝对误差积分):     {metrics['IAE']:.2f}")
        print(f"    ISE (平方误差积分):     {metrics['ISE']:.2f}")
        print(f"    ITAE (时间加权IAE):     {metrics['ITAE']:.2f}")

    if 平滑度指标:
        print("\n【控制平滑度指标】")
        for ctrl_name, metrics in 平滑度指标.items():
            print(f"\n  {ctrl_name}:")
            print(f"    总变差 (TV):            {metrics['TV']:.2f}")
            print(f"    平均变化率:            {metrics['avg_change_rate']:.4f}")
            print(f"    最大变化率:            {metrics['max_change_rate']:.4f}")
            print(f"    方向改变次数:          {metrics['direction_changes']}")
            print(f"    平滑度:                {metrics['smoothness']:.4f}")

    if 综合评分:
        print("\n【综合性能评分】")
        print(f"  综合评分:               {综合评分['综合评分']:.2f} / 100")
        print(f"  跟踪性能分:             {综合评分['跟踪性能分']:.2f} / 100")
        print(f"  平滑度分:               {综合评分['平滑度分']:.2f} / 100")

    print("\n" + "="*80)
