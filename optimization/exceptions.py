"""
自定义异常类：用于水网优化模型的错误处理
"""


class WaterNetworkError(Exception):
    """水网模型基础异常类"""

    pass


class ConfigurationError(WaterNetworkError):
    """配置错误"""

    pass


class ValidationError(WaterNetworkError):
    """验证错误"""

    pass


class TopologyError(WaterNetworkError):
    """拓扑结构错误"""

    pass


class TimeSeriesError(WaterNetworkError):
    """时间序列错误"""

    pass


class SolverError(WaterNetworkError):
    """求解器错误"""

    pass


class DataError(WaterNetworkError):
    """数据错误"""

    pass
