"""
Pydantic models for API request/response schemas
"""

from .simulation import (
    SimulationConfig,
    InitialConditionConfig,
    BoundaryConditionConfig,
    UpstreamBoundaryConfig,
    DownstreamBoundaryConfig,
    SimulationRequest,
    SimulationResponse,
    SimulationStatusResponse,
    SimulationResultResponse,
    SimulationMetrics
)

__all__ = [
    'SimulationConfig',
    'InitialConditionConfig',
    'BoundaryConditionConfig',
    'UpstreamBoundaryConfig',
    'DownstreamBoundaryConfig',
    'SimulationRequest',
    'SimulationResponse',
    'SimulationStatusResponse',
    'SimulationResultResponse',
    'SimulationMetrics',
    'get_pump_model',
    'get_gate_model',
    'get_weir_model',
    'get_turbine_model',
    'get_valve_model'
]

from .factory import (
    get_pump_model,
    get_gate_model,
    get_weir_model,
    get_turbine_model,
    get_valve_model
)
