"""
水网优化模型包
"""

# 导入异常类（不依赖外部库）
from .exceptions import (
    WaterNetworkError,
    ConfigurationError,
    ValidationError,
    TopologyError,
    TimeSeriesError,
    SolverError,
    DataError,
)

# 导入新增模块（不依赖外部库）
from .feasibility import (
    FeasibilityStatus,
    FeasibilityResult,
    check_solver_results,
    check_constraint_violations,
    check_problem_feasibility,
)
from .defaults import (
    OPTIMIZATION_DEFAULTS,
    MPC_DEFAULTS,
    CONTROL_EVALUATION_DEFAULTS,
    CANAL_IDZ_DEFAULTS,
    VISUALIZATION_DEFAULTS,
    get_default,
    update_defaults,
)
from .utils import (
    TimeSeriesGenerator,
    ResultExtractor,
    SolverManager,
)

# 条件导入（依赖pyomo等外部库）
__all__ = [
    # 异常
    "WaterNetworkError",
    "ConfigurationError",
    "ValidationError",
    "TopologyError",
    "TimeSeriesError",
    "SolverError",
    "DataError",
    # 可行性检查
    "FeasibilityStatus",
    "FeasibilityResult",
    "check_solver_results",
    "check_constraint_violations",
    "check_problem_feasibility",
    # 默认配置
    "OPTIMIZATION_DEFAULTS",
    "MPC_DEFAULTS",
    "CONTROL_EVALUATION_DEFAULTS",
    "CANAL_IDZ_DEFAULTS",
    "VISUALIZATION_DEFAULTS",
    "get_default",
    "update_defaults",
    # 工具
    "TimeSeriesGenerator",
    "ResultExtractor",
    "SolverManager",
]

try:
    from .water_network_generic import build_water_network_model
    from .validation import validate_network_config
    __all__.extend(["build_water_network_model", "validate_network_config"])
except ImportError:
    # pyomo等依赖未安装时，不导入这些模块
    pass
