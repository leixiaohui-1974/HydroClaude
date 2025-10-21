"""HydroClaude异常类定义"""

class HydroClaudeException(Exception):
    """基础异常类"""
    pass

class SimulationError(HydroClaudeException):
    """仿真错误"""
    pass

class ConvergenceError(HydroClaudeException):
    """收敛错误"""
    pass

class TopologyError(HydroClaudeException):
    """拓扑错误"""
    pass

class BoundaryConditionError(HydroClaudeException):
    """边界条件错误"""
    pass

class ControllerError(HydroClaudeException):
    """控制器错误"""
    pass
