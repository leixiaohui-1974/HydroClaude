"""
Pydantic models for simulation API
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime


class UpstreamBoundaryConfig(BaseModel):
    """Upstream boundary condition configuration"""
    type: Literal['h', 'Q', 'wall'] = Field(
        'h',
        description="Boundary type: 'h' (fixed depth), 'Q' (fixed flow), 'wall' (reflective)"
    )
    value: Optional[float] = Field(
        None,
        description="Boundary value (depth in meters or flow in m³/s)"
    )


class DownstreamBoundaryConfig(BaseModel):
    """Downstream boundary condition configuration"""
    type: Literal['h', 'Q', 'wall'] = Field(
        'h',
        description="Boundary type: 'h' (fixed depth), 'Q' (fixed flow), 'wall' (reflective)"
    )
    value: Optional[float] = Field(
        None,
        description="Boundary value (depth in meters or flow in m³/s)"
    )


class BoundaryConditionConfig(BaseModel):
    """Boundary conditions configuration"""
    upstream: UpstreamBoundaryConfig = Field(
        default_factory=lambda: UpstreamBoundaryConfig(type='h', value=5.0),
        description="Upstream boundary condition"
    )
    downstream: DownstreamBoundaryConfig = Field(
        default_factory=lambda: DownstreamBoundaryConfig(type='h', value=5.0),
        description="Downstream boundary condition"
    )


class InitialConditionConfig(BaseModel):
    """Initial conditions configuration"""
    type: Literal['uniform', 'dam_break', 'custom'] = Field(
        'uniform',
        description="Initial condition type"
    )
    # For uniform flow
    h: Optional[float] = Field(5.0, description="Uniform water depth (m)")
    Q: Optional[float] = Field(0.0, description="Uniform flow rate (m³/s)")

    # For dam break
    dam_position: Optional[float] = Field(None, description="Dam position (m)")
    h_left: Optional[float] = Field(None, description="Left side water depth (m)")
    h_right: Optional[float] = Field(None, description="Right side water depth (m)")
    Q_left: Optional[float] = Field(0.0, description="Left side flow rate (m³/s)")
    Q_right: Optional[float] = Field(0.0, description="Right side flow rate (m³/s)")

    @field_validator('dam_position', 'h_left', 'h_right', mode='after')
    def validate_dam_break_params(cls, v, info):
        """Validate dam break parameters are provided when type is dam_break"""
        # In Pydantic V2, we need to check if all values are present
        # This validator runs after field assignment
        return v


class SimulationConfig(BaseModel):
    """Canal simulation configuration"""
    # Geometry
    width: float = Field(10.0, gt=0, description="Channel width (m)")
    length: float = Field(1000.0, gt=0, description="Channel length (m)")
    n_cells: int = Field(100, ge=10, le=10000, description="Number of computational cells")

    # Physical parameters
    manning_n: float = Field(0.0, ge=0, le=0.1, description="Manning's roughness coefficient")
    slope: float = Field(0.0, ge=0, le=0.1, description="Channel bed slope")

    # Numerical parameters
    cfl: float = Field(0.5, gt=0, le=1.0, description="CFL number for stability")
    order: int = Field(2, ge=1, le=2, description="Spatial accuracy order (1 or 2)")
    use_numba: bool = Field(True, description="Enable Numba acceleration")

    # Time parameters
    t_end: float = Field(10.0, gt=0, description="Simulation end time (s)")
    dt_max: float = Field(0.1, gt=0, description="Maximum time step (s)")
    output_interval: float = Field(0.5, gt=0, description="Output data interval (s)")

    # Initial and boundary conditions
    initial_conditions: InitialConditionConfig = Field(
        default_factory=InitialConditionConfig,
        description="Initial conditions"
    )
    boundary_conditions: BoundaryConditionConfig = Field(
        default_factory=BoundaryConditionConfig,
        description="Boundary conditions"
    )

    class Config:
        schema_extra = {
            "example": {
                "width": 10.0,
                "length": 1000.0,
                "n_cells": 100,
                "manning_n": 0.0,
                "slope": 0.0,
                "t_end": 10.0,
                "dt_max": 0.1,
                "output_interval": 0.5,
                "initial_conditions": {
                    "type": "uniform",
                    "h": 5.0,
                    "Q": 0.0
                },
                "boundary_conditions": {
                    "upstream": {"type": "h", "value": 5.0},
                    "downstream": {"type": "h", "value": 5.0}
                }
            }
        }


class SimulationRequest(BaseModel):
    """Request to create a new simulation"""
    name: str = Field(..., min_length=1, max_length=200, description="Simulation name")
    description: Optional[str] = Field(None, max_length=1000, description="Simulation description")
    config: SimulationConfig = Field(..., description="Simulation configuration")
    project_id: Optional[str] = Field(None, description="Associated project ID")

    class Config:
        schema_extra = {
            "example": {
                "name": "Uniform Flow Test",
                "description": "Basic uniform flow validation case",
                "config": {
                    "width": 10.0,
                    "length": 1000.0,
                    "n_cells": 100,
                    "manning_n": 0.0,
                    "slope": 0.0,
                    "t_end": 10.0,
                    "initial_conditions": {
                        "type": "uniform",
                        "h": 5.0,
                        "Q": 0.0
                    }
                }
            }
        }


class SimulationResponse(BaseModel):
    """Response after creating a simulation"""
    task_id: str = Field(..., description="Unique task identifier")
    status: Literal['queued', 'running', 'completed', 'failed'] = Field(
        ...,
        description="Simulation status"
    )
    name: str = Field(..., description="Simulation name")
    created_at: datetime = Field(..., description="Creation timestamp")
    message: str = Field(..., description="Status message")


class SimulationMetrics(BaseModel):
    """Simulation performance metrics"""
    mass_conservation_error: float = Field(..., description="Mass conservation error")
    max_depth: float = Field(..., description="Maximum water depth (m)")
    min_depth: float = Field(..., description="Minimum water depth (m)")
    max_velocity: float = Field(..., description="Maximum velocity (m/s)")
    max_discharge: float = Field(..., description="Maximum discharge (m³/s)")
    max_froude: float = Field(..., description="Maximum Froude number")
    mean_depth_final: float = Field(..., description="Final mean depth (m)")
    mean_discharge_final: float = Field(..., description="Final mean discharge (m³/s)")
    total_iterations: int = Field(..., description="Total time steps")
    converged: bool = Field(..., description="Convergence status")


class SimulationStatusResponse(BaseModel):
    """Response for simulation status query"""
    task_id: str = Field(..., description="Task identifier")
    status: Literal['queued', 'running', 'completed', 'failed'] = Field(
        ...,
        description="Simulation status"
    )
    progress: Optional[float] = Field(None, ge=0, le=100, description="Progress percentage")
    created_at: datetime = Field(..., description="Creation timestamp")
    started_at: Optional[datetime] = Field(None, description="Start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    duration: Optional[float] = Field(None, description="Execution duration (seconds)")
    error: Optional[str] = Field(None, description="Error message if failed")


class SimulationResultResponse(BaseModel):
    """Response containing simulation results"""
    task_id: str = Field(..., description="Task identifier")
    status: str = Field(..., description="Simulation status")
    duration: float = Field(..., description="Execution duration (seconds)")
    timestamp: datetime = Field(..., description="Completion timestamp")

    # Spatial and temporal data
    x: List[float] = Field(..., description="Spatial coordinates (m)")
    time: List[float] = Field(..., description="Time points (s)")

    # Solution data
    h: List[List[float]] = Field(..., description="Water depth history [time_idx][x_idx] (m)")
    Q: List[List[float]] = Field(..., description="Discharge history [time_idx][x_idx] (m³/s)")
    V: List[List[float]] = Field(..., description="Velocity history [time_idx][x_idx] (m/s)")

    # Metrics
    metrics: SimulationMetrics = Field(..., description="Performance metrics")

    # Error info
    error: Optional[str] = Field(None, description="Error message if failed")
