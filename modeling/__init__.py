"""
HydroClaude 通用建模系统

提供自动化、标准化的水力学建模工具，降低建模难度

核心模块：
- ModelConfig: 配置文件管理
- GridGenerator: 网格自动剖分
- AdaptiveRefiner: 自适应网格细化
- AlgorithmSelector: 最优算法选择
- SteadyEstimator: 稳态初值估计
- MultiValidator: 结果多重验证
- UniversalModeler: 通用建模接口

作者: Claude
日期: 2025-10-24
版本: 1.0
"""

__version__ = "1.0.0"
__author__ = "Claude"

# 导入常量
from modeling.constants import (
    GridConstants,
    RefinementConstants,
    AlgorithmConstants,
    SteadyConstants,
    ValidationConstants,
    StructureConstants,
    OutputConstants,
    get_default_config
)

# 导入核心类
from modeling.config import ModelConfig
from modeling.grid_generator import GridGenerator
from modeling.adaptive_refiner import AdaptiveRefiner
from modeling.algorithm_selector import AlgorithmSelector
from modeling.steady_estimator import SteadyEstimator
from modeling.multi_validator import MultiValidator
from modeling.universal_modeler import UniversalModeler

__all__ = [
    # 常量类
    'GridConstants',
    'RefinementConstants',
    'AlgorithmConstants',
    'SteadyConstants',
    'ValidationConstants',
    'StructureConstants',
    'OutputConstants',
    'get_default_config',
    # 核心类
    'ModelConfig',
    'GridGenerator',
    'AdaptiveRefiner',
    'AlgorithmSelector',
    'SteadyEstimator',
    'MultiValidator',
    'UniversalModeler',
]
