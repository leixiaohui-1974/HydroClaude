"""
默认配置参数管理模块

此模块集中管理所有默认参数，避免硬编码。
所有默认值都可以通过配置文件或运行时参数覆盖。
"""

from dataclasses import dataclass, field
from typing import Dict, Any


@dataclass
class OptimizationDefaults:
    """优化模型默认参数"""

    # 目标函数权重
    shortage_penalty: float = 1e5  # 缺水惩罚系数
    pump_cost: float = 200.0  # 泵站能耗成本权重
    idz_slack_penalty: float = 1e6  # IDZ模型松弛变量惩罚

    # 求解器设置
    default_solver: str = "glpk"  # 默认求解器
    solver_timeout: int = 300  # 求解器超时时间（秒）
    solver_options: Dict[str, Any] = field(default_factory=dict)  # 求解器选项

    # 数值容差
    feasibility_tolerance: float = 1e-6  # 可行性容差
    optimality_tolerance: float = 1e-6  # 最优性容差


@dataclass
class MPCDefaults:
    """MPC控制器默认参数"""

    prediction_horizon: int = 24  # 预测时域长度（时间步）
    control_horizon: int = 24  # 控制时域长度（时间步）
    sampling_time: float = 1.0  # 采样周期（小时）

    # 控制权重
    tracking_weight: float = 100.0  # 跟踪误差权重
    control_weight: float = 1.0  # 控制变化权重
    terminal_weight: float = 200.0  # 终端状态权重

    # 求解设置
    max_iterations: int = 100  # 最大迭代次数
    convergence_tolerance: float = 1e-4  # 收敛容差


@dataclass
class ControlEvaluationDefaults:
    """控制性能评价默认参数"""

    # 稳态判定
    settling_threshold: float = 0.02  # 稳态阈值（2%）
    settling_window: int = 10  # 稳态判定窗口

    # 性能权重
    tracking_weight: float = 0.6  # 跟踪性能权重
    smoothness_weight: float = 0.4  # 平滑度权重

    # 归一化阈值
    normalization_threshold_error: float = 0.05  # 误差归一化阈值
    normalization_threshold_change: float = 50.0  # 变化率归一化阈值

    # 评分等级
    score_excellent: float = 90.0  # 优秀分数线
    score_good: float = 75.0  # 良好分数线
    score_fair: float = 60.0  # 一般分数线


@dataclass
class CanalIDZDefaults:
    """渠道IDZ模型默认参数"""

    # Muskingum参数
    muskingum_k_scale: float = 2.5  # Muskingum K值缩放因子
    muskingum_x: float = 0.20  # Muskingum X权重

    # 水深约束
    depth_lower_ratio: float = 0.2  # 最小水深比例（相对目标值）
    depth_upper_ratio: float = 2.5  # 最大水深比例（相对目标值）

    # 初始条件
    initial_gate_opening: float = 0.5  # 初始闸门开度
    initial_flow: float = 20.0  # 初始流量 (m³/min)

    # 数值稳定性
    min_wave_celerity: float = 0.5  # 最小波速 (m/s)
    iteration_damping: float = 0.5  # 迭代阻尼系数
    max_iterations: int = 5  # 最大迭代次数


@dataclass
class VisualizationDefaults:
    """可视化默认参数"""

    # 图形尺寸
    figure_dpi: int = 150  # 图形DPI
    animation_dpi: int = 100  # 动画DPI
    animation_fps: int = 5  # 动画帧率

    # 颜色方案
    color_scheme: str = "default"  # 颜色方案

    # 字体设置
    font_size_title: int = 12  # 标题字体大小
    font_size_label: int = 11  # 标签字体大小
    font_size_legend: int = 9  # 图例字体大小


# 全局默认配置实例
OPTIMIZATION_DEFAULTS = OptimizationDefaults()
MPC_DEFAULTS = MPCDefaults()
CONTROL_EVALUATION_DEFAULTS = ControlEvaluationDefaults()
CANAL_IDZ_DEFAULTS = CanalIDZDefaults()
VISUALIZATION_DEFAULTS = VisualizationDefaults()


def get_default(category: str, param: str, default=None):
    """
    获取默认参数值

    Args:
        category: 参数类别 (optimization, mpc, control_evaluation, canal_idz, visualization)
        param: 参数名称
        default: 如果未找到返回的默认值

    Returns:
        参数值
    """
    category_map = {
        'optimization': OPTIMIZATION_DEFAULTS,
        'mpc': MPC_DEFAULTS,
        'control_evaluation': CONTROL_EVALUATION_DEFAULTS,
        'canal_idz': CANAL_IDZ_DEFAULTS,
        'visualization': VISUALIZATION_DEFAULTS,
    }

    config = category_map.get(category)
    if config is None:
        return default

    return getattr(config, param, default)


def update_defaults(category: str, **kwargs):
    """
    更新默认参数

    Args:
        category: 参数类别
        **kwargs: 要更新的参数
    """
    category_map = {
        'optimization': OPTIMIZATION_DEFAULTS,
        'mpc': MPC_DEFAULTS,
        'control_evaluation': CONTROL_EVALUATION_DEFAULTS,
        'canal_idz': CANAL_IDZ_DEFAULTS,
        'visualization': VISUALIZATION_DEFAULTS,
    }

    config = category_map.get(category)
    if config is None:
        raise ValueError(f"Unknown category: {category}")

    for key, value in kwargs.items():
        if hasattr(config, key):
            setattr(config, key, value)
        else:
            raise ValueError(f"Unknown parameter {key} in category {category}")


__all__ = [
    'OptimizationDefaults',
    'MPCDefaults',
    'ControlEvaluationDefaults',
    'CanalIDZDefaults',
    'VisualizationDefaults',
    'OPTIMIZATION_DEFAULTS',
    'MPC_DEFAULTS',
    'CONTROL_EVALUATION_DEFAULTS',
    'CANAL_IDZ_DEFAULTS',
    'VISUALIZATION_DEFAULTS',
    'get_default',
    'update_defaults',
]
