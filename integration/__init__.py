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

try:
    from .swmm_benchmark import (
        SWMMOpenChannelCase,
        build_swmm_input,
        write_swmm_input,
        extract_swmm_results,
        run_swmm_open_channel_benchmark,
    )
    __all__.extend([
        'SWMMOpenChannelCase',
        'build_swmm_input',
        'write_swmm_input',
        'extract_swmm_results',
        'run_swmm_open_channel_benchmark',
    ])
except ImportError as e:
    print(f"警告: SWMM benchmark模块导入失败: {e}")

try:
    from .hec_ras_adapter import (
        HECRASRuntimeStatus,
        detect_hec_ras_runtime,
        collect_hec_ras_case_scaffold,
        prepare_hec_ras_benchmark,
        export_hec_ras_status_json,
        run_hec_ras_mixed_flow_sample,
    )
    __all__.extend([
        'HECRASRuntimeStatus',
        'detect_hec_ras_runtime',
        'collect_hec_ras_case_scaffold',
        'prepare_hec_ras_benchmark',
        'export_hec_ras_status_json',
        'run_hec_ras_mixed_flow_sample',
    ])
except ImportError as e:
    print(f"警告: HEC-RAS集成模块导入失败: {e}")
    __all__ = []
