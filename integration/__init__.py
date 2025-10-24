"""
外部工具集成模块

本模块提供与外部水力学模拟工具的集成接口
"""

# SWMM集成
try:
    from .swmm_adapter import (
        SWMMAdapter,
        SWMMPIDController,
        SWMMObjectType,
        SWMMNodeState,
        SWMMLinkState,
        SWMMPumpState,
        SWMMSystemState,
        create_simple_swmm_model,
        PYSWMM_AVAILABLE,
    )
    __all__ = [
        'SWMMAdapter',
        'SWMMPIDController',
        'SWMMObjectType',
        'SWMMNodeState',
        'SWMMLinkState',
        'SWMMPumpState',
        'SWMMSystemState',
        'create_simple_swmm_model',
        'PYSWMM_AVAILABLE',
    ]
except ImportError as e:
    print(f"警告: SWMM集成模块导入失败: {e}")
    __all__ = []
