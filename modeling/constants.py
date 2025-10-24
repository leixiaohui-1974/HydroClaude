#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
通用建模系统 - 常量定义

定义所有默认值和阈值，避免硬编码

作者: Claude
日期: 2025-10-24
"""

# ============================================================================
# 网格生成常量
# ============================================================================
class GridConstants:
    """网格生成相关常量"""

    # 自适应网格默认参数
    DEFAULT_DX_MIN = 20.0           # 默认最小网格间距 (m)
    DEFAULT_DX_MAX = 200.0          # 默认最大网格间距 (m)
    DEFAULT_TRANSITION_LENGTH = 500.0  # 默认过渡区长度 (m)

    # 细化参数
    MIN_REFINEMENT_RATIO = 0.25     # 最小细化比例 (dx_min / dx_max)
    MAX_REFINEMENT_RATIO = 0.75     # 最大细化比例

    # 网格质量评分阈值
    EXCELLENT_UNIFORMITY = 0.95     # 优秀：变异系数 < 5%
    GOOD_UNIFORMITY = 0.85          # 良好：变异系数 < 15%
    ACCEPTABLE_UNIFORMITY = 0.70    # 可接受：变异系数 < 30%


# ============================================================================
# 自适应细化常量
# ============================================================================
class RefinementConstants:
    """自适应细化相关常量"""

    # 梯度指标阈值
    DEFAULT_REFINE_THRESHOLD = 0.1   # 默认细化阈值
    DEFAULT_COARSEN_THRESHOLD = 0.01 # 默认粗化阈值

    # 迭代控制
    MAX_REFINEMENT_ITERATIONS = 5    # 最大细化迭代次数
    MIN_CELL_SIZE = 10.0             # 最小单元尺寸 (m)
    MAX_CELL_SIZE = 500.0            # 最大单元尺寸 (m)

    # 收敛判定
    CONVERGENCE_TOLERANCE = 0.01     # 网格变化收敛容差


# ============================================================================
# 算法选择常量
# ============================================================================
class AlgorithmConstants:
    """算法选择相关常量"""

    # 网格分辨率阈值
    FINE_GRID_THRESHOLD = 50.0       # 细网格：dx < 50m
    MEDIUM_GRID_THRESHOLD = 100.0    # 中等网格：50m < dx < 100m
    COARSE_GRID_THRESHOLD = 200.0    # 粗网格：dx > 200m

    # Preissmann参数
    DEFAULT_THETA = 0.6              # 默认Preissmann θ
    MIN_THETA = 0.5                  # 最小θ（确保稳定性）
    MAX_THETA = 1.0                  # 最大θ（完全隐式）

    # CFL数
    DEFAULT_CFL_NUMBER = 0.5         # 默认CFL数
    SAFE_CFL_NUMBER = 0.3            # 保守CFL数（复杂问题）

    # 典型波速估计
    TYPICAL_WAVE_SPEED = 10.0        # 典型波速 (m/s)


# ============================================================================
# 稳态估计常量
# ============================================================================
class SteadyConstants:
    """稳态估计相关常量"""

    # 均匀流估计参数
    DEFAULT_FROUDE_NUMBER = 0.3      # 默认Froude数（亚临界流）
    MIN_DEPTH_RATIO = 0.1            # 最小水深比（相对于渠道宽度）
    MAX_DEPTH_RATIO = 5.0            # 最大水深比

    # 逐渐变化流参数
    GVF_STEP_RATIO = 0.01            # GVF步长比例（相对于渠长）
    GVF_MAX_ITERATIONS = 10000       # GVF最大迭代次数

    # 收敛控制
    STEADY_CONVERGENCE_TOL = 0.001   # 稳态收敛容差
    MAX_STEADY_ITERATIONS = 5000     # 最大稳态迭代次数


# ============================================================================
# 验证常量
# ============================================================================
class ValidationConstants:
    """结果验证相关常量"""

    # 流量守恒阈值（百分比）
    EXCELLENT_FLOW_ERROR = 1.0       # 优秀：< 1%
    GOOD_FLOW_ERROR = 5.0            # 良好：< 5%
    ACCEPTABLE_FLOW_ERROR = 10.0     # 可接受：< 10%

    # 物理合理性阈值
    MIN_DEPTH = 0.0                  # 最小水深 (m)
    MAX_DEPTH = 1000.0               # 最大水深 (m)
    MAX_FROUDE_NUMBER = 3.0          # 最大Froude数
    MAX_VELOCITY = 10.0              # 最大流速 (m/s)

    # 数值稳定性阈值
    MAX_TOTAL_VARIATION = 1.0        # 最大归一化总变差

    # 结构物流量验证阈值（百分比）
    STRUCTURE_FLOW_TOLERANCE = 5.0   # 结构物流量容差


# ============================================================================
# 结构物参数常量
# ============================================================================
class StructureConstants:
    """结构物相关常量"""

    # 流量系数默认值
    DEFAULT_GATE_CD = 0.6            # 闸门流量系数
    DEFAULT_WEIR_CD = 0.4            # 堰流量系数
    DEFAULT_ORIFICE_CD = 0.6         # 孔口流量系数

    # 泵站参数
    DEFAULT_MIN_SUCTION_HEAD = 2.0   # 默认最小吸入水头 (m)

    # 结构物影响范围（用于网格加密）
    STRUCTURE_INFLUENCE_LENGTH = 500.0  # 结构物影响区长度 (m)


# ============================================================================
# 输出常量
# ============================================================================
class OutputConstants:
    """输出相关常量"""

    # 默认输出格式
    DEFAULT_FORMATS = ['npz', 'png', 'txt']

    # 图片参数
    DEFAULT_DPI = 150                # 默认图片分辨率
    HIGH_DPI = 300                   # 高清图片分辨率

    # 数据保存间隔
    DEFAULT_SAVE_INTERVAL = 100      # 默认保存间隔（时间步）


# ============================================================================
# 辅助函数
# ============================================================================
def get_default_config() -> dict:
    """
    获取默认配置字典

    Returns:
        默认配置参数
    """
    return {
        'grid': {
            'dx_min': GridConstants.DEFAULT_DX_MIN,
            'dx_max': GridConstants.DEFAULT_DX_MAX,
            'transition_length': GridConstants.DEFAULT_TRANSITION_LENGTH,
        },
        'refinement': {
            'refine_threshold': RefinementConstants.DEFAULT_REFINE_THRESHOLD,
            'coarsen_threshold': RefinementConstants.DEFAULT_COARSEN_THRESHOLD,
            'max_iterations': RefinementConstants.MAX_REFINEMENT_ITERATIONS,
        },
        'algorithm': {
            'theta': AlgorithmConstants.DEFAULT_THETA,
            'cfl': AlgorithmConstants.DEFAULT_CFL_NUMBER,
        },
        'validation': {
            'flow_tolerance': ValidationConstants.ACCEPTABLE_FLOW_ERROR,
            'structure_tolerance': ValidationConstants.STRUCTURE_FLOW_TOLERANCE,
        },
        'output': {
            'formats': OutputConstants.DEFAULT_FORMATS,
            'dpi': OutputConstants.DEFAULT_DPI,
        }
    }


if __name__ == "__main__":
    print("通用建模系统常量定义")
    print(f"默认网格间距范围: [{GridConstants.DEFAULT_DX_MIN}, {GridConstants.DEFAULT_DX_MAX}] m")
    print(f"默认Preissmann θ: {AlgorithmConstants.DEFAULT_THETA}")
    print(f"默认CFL数: {AlgorithmConstants.DEFAULT_CFL_NUMBER}")
