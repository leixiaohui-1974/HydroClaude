# -*- coding: utf-8 -*-
"""
Structures API Router - Final Refactoring with Service Layer
水工结构API路由

提供独立的物理模型计算和完整的组合仿真能力。
"""
import time
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
import uuid
from datetime import datetime

import sys
from pathlib import Path

# 确保项目根目录在sys.path中
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 导入新的独立物理模型
from web.backend.api_gateway.models import get_pump_model, get_gate_model, get_weir_model, get_turbine_model, get_valve_model
# 导入新的仿真服务
from web.backend.services.simulation_service import simulation_service


router = APIRouter(tags=["structures"])


# ==================== Pydantic Models ====================

# ----- 通用响应模型 -----
class CalculationResponse(BaseModel):
    """独立的物理模型计算的响应"""
    task_id: str
    status: str
    calculation_time_ms: float
    timestamp: str
    metrics: Dict[str, Any]
    error: Optional[str] = None

class ComplexSimulationResponse(BaseModel):
    """完整的、复杂的仿真（例如渠道+结构）的响应"""
    # 这个模型应该与 core.simulation_engine.py 的输出兼容
    # 为了简化，我们暂时返回一个通用的字典
    task_id: str
    status: str
    simulation_time_ms: float
    timestamp: str
    results: Dict[str, Any]
    error: Optional[str] = None


# ----- 独立计算请求模型 -----
class PumpConfig(BaseModel):
    pump_type: str = Field("single", description="泵类型: single, parallel, series")
    rated_flow: float = Field(10.0, description="单泵额定流量 (m³/s)")
    rated_head: float = Field(15.0, description="单泵额定扬程 (m)")
    num_pumps: int = Field(1, description="泵数量")

class PumpCalculationRequest(BaseModel):
    pump: PumpConfig
    system_head: float = Field(..., description="系统总扬程 (m)")

class GateConfig(BaseModel):
    type: str = Field("sluice", description="闸门类型: sluice, radial")
    width: float = Field(5.0, description="宽度 (m)")
    opening: float = Field(2.0, description="开度 (m)")
    discharge_coeff: float = Field(0.6, description="流量系数")

class GateCalculationRequest(BaseModel):
    gate: GateConfig
    upstream_depth: float = Field(..., description="上游水深 (m)")
    downstream_depth: float = Field(..., description="下游水深 (m)")

# ... (其他独立计算模型保持不变) ...
class WeirConfig(BaseModel):
    type: str = Field("broad_crested", description="堰类型: broad_crested, sharp_crested, v_notch")
    crest_height: float = Field(1.0, description="堰顶高程 (m)")
    discharge_coeff: float = Field(0.6, description="流量系数")
    width: Optional[float] = Field(None, description="堰宽 (m)")
    angle_deg: Optional[float] = Field(None, description="V型堰夹角 (度)")

class WeirCalculationRequest(BaseModel):
    weir: WeirConfig
    upstream_depth: float = Field(..., description="上游水深 (m)")
    downstream_depth: float = Field(..., description="下游水深 (m)")

class TurbineConfig(BaseModel):
    type: str = Field("francis", description="水轮机类型")
    rated_power: float = Field(50.0, description="额定功率 (MW)")
    rated_head: float = Field(100.0, description="额定水头 (m)")
    rated_flow: float = Field(60.0, description="额定流量 (m³/s)")

class TurbineCalculationRequest(BaseModel):
    turbine: TurbineConfig
    current_head: float = Field(..., description="当前工作水头 (m)")
    current_flow: float = Field(..., description="当前工作流量 (m³/s)")

class ValveConfig(BaseModel):
    type: str = Field("butterfly", description="阀门类型")
    diameter: float = Field(1.0, description="直径 (m)")

class ValveCalculationRequest(BaseModel):
    valve: ValveConfig
    upstream_pressure: float = Field(..., description="上游压力 (Pa)")
    downstream_pressure: float = Field(..., description="下游压力 (Pa)")
    opening_percent: float = Field(100.0, description="开度 (%)")


# ----- 组合仿真请求模型 -----
class CanalConfig(BaseModel):
    length: float = Field(1000.0, description="渠道长度 (m)")
    width: float = Field(10.0, description="宽度 (m)")
    slope: float = Field(0.001, description="坡度")
    manning_n: float = Field(0.015, description="曼宁系数")
    grid_nx: int = Field(101, description="空间网格点数")

class StructureInCanal(BaseModel):
    position: float = Field(..., description="结构在渠道中的位置 (m)")
    parameters: Dict[str, Any] = Field(..., description="结构的物理参数")

class BoundaryConditions(BaseModel):
    upstream: Dict[str, Any] = Field(..., description="上游边界条件, e.g., {'type': 'Q', 'value': 50.0}")
    downstream: Dict[str, Any] = Field(..., description="下游边界条件, e.g., {'type': 'h', 'value': 2.0}")

class ComplexSimulationRequest(BaseModel):
    simulation_type: str = Field("steady", description="仿真类型: 'steady' 或 'unsteady'")
    canal: CanalConfig
    structure_type: str = Field(..., description="结构类型, e.g., 'sluice_gate', 'pump'")
    structure: StructureInCanal
    boundaries: BoundaryConditions
    metadata: Dict[str, str] = {"title": "API-driven Simulation"}


# ==================== API Endpoints: 独立计算 ====================

@router.post("/pump", response_model=CalculationResponse, summary="泵站性能计算")
async def run_pump_calculation(request: PumpCalculationRequest):
    start_time = time.time()
    try:
        pump_model = get_pump_model(
            pump_type=request.pump.pump_type, flow_rate=request.pump.rated_flow,
            head=request.pump.rated_head, num_pumps=request.pump.num_pumps
        )
        metrics = pump_model.calculate_performance(request.system_head)
        return CalculationResponse(
            task_id=str(uuid.uuid4()), status='completed',
            calculation_time_ms=(time.time() - start_time) * 1000,
            timestamp=datetime.now().isoformat(), metrics=metrics, error=metrics.get("error")
        )
    except Exception as e: raise HTTPException(status_code=400, detail=str(e))

@router.post("/gate", response_model=CalculationResponse, summary="闸门水力计算")
async def run_gate_calculation(request: GateCalculationRequest):
    start_time = time.time()
    try:
        gate_model = get_gate_model(
            gate_type=request.gate.type, width=request.gate.width,
            opening=request.gate.opening, discharge_coeff=request.gate.discharge_coeff
        )
        metrics = gate_model.calculate_discharge(request.upstream_depth, request.downstream_depth)
        return CalculationResponse(
            task_id=str(uuid.uuid4()), status='completed',
            calculation_time_ms=(time.time() - start_time) * 1000,
            timestamp=datetime.now().isoformat(), metrics=metrics, error=metrics.get("error")
        )
    except Exception as e: raise HTTPException(status_code=400, detail=str(e))

@router.post("/weir", response_model=CalculationResponse, summary="堰水力计算")
async def run_weir_calculation(request: WeirCalculationRequest):
    start_time = time.time()
    try:
        params = request.weir.model_dump()
        weir_model = get_weir_model(weir_type=request.weir.type, **params)
        metrics = weir_model.calculate_discharge(request.upstream_depth, request.downstream_depth)
        return CalculationResponse(
            task_id=str(uuid.uuid4()), status='completed',
            calculation_time_ms=(time.time() - start_time) * 1000,
            timestamp=datetime.now().isoformat(), metrics=metrics, error=metrics.get("error")
        )
    except Exception as e: raise HTTPException(status_code=400, detail=str(e))

@router.post("/turbine", response_model=CalculationResponse, summary="水轮机性能计算")
async def run_turbine_calculation(request: TurbineCalculationRequest):
    start_time = time.time()
    try:
        turbine_model = get_turbine_model(
            turbine_type=request.turbine.type, rated_power=request.turbine.rated_power,
            rated_head=request.turbine.rated_head, rated_flow=request.turbine.rated_flow
        )
        metrics = turbine_model.calculate_performance(request.current_head, request.current_flow)
        return CalculationResponse(
            task_id=str(uuid.uuid4()), status='completed',
            calculation_time_ms=(time.time() - start_time) * 1000,
            timestamp=datetime.now().isoformat(), metrics=metrics, error=metrics.get("error")
        )
    except Exception as e: raise HTTPException(status_code=400, detail=str(e))

@router.post("/valve", response_model=CalculationResponse, summary="阀门水力计算")
async def run_valve_calculation(request: ValveCalculationRequest):
    start_time = time.time()
    try:
        valve_model = get_valve_model(valve_type=request.valve.type, diameter=request.valve.diameter)
        metrics = valve_model.calculate_flow(
            upstream_pressure=request.upstream_pressure, downstream_pressure=request.downstream_pressure,
            opening_percent=request.opening_percent
        )
        return CalculationResponse(
            task_id=str(uuid.uuid4()), status='completed',
            calculation_time_ms=(time.time() - start_time) * 1000,
            timestamp=datetime.now().isoformat(), metrics=metrics, error=metrics.get("error")
        )
    except Exception as e: raise HTTPException(status_code=400, detail=str(e))


# ==================== API Endpoints: 组合仿真 (通过服务层) ====================

@router.post("/simulate-canal-with-structure", response_model=ComplexSimulationResponse, summary="渠道与单个结构组合仿真")
async def run_complex_simulation(request: ComplexSimulationRequest):
    """
    通过服务层运行一个完整的渠道+单个水工结构仿真。
    - **重构**: 这是新的、统一的组合仿真端点。
    - 它将API请求动态转换为一个完整的仿真配置文件。
    """
    start_time = time.time()
    try:
        # 1. 动态构建仿真配置字典
        config = {
            "metadata": request.metadata,
            "simulation": {
                "type": request.simulation_type,
                "mode": "standard",
                "time": { # 默认值，未来可以从API传入
                    "start": 0, "end": 3600, "dt": 1, "output_interval": 100
                }
            },
            "canal": {
                "length": request.canal.length,
                "width": request.canal.width,
                "slope": request.canal.slope,
                "manning_n": request.canal.manning_n,
                "grid": {"nx": request.canal.grid_nx}
            },
            "structures": [
                {
                    "type": request.structure_type,
                    "position": request.structure.position,
                    "parameters": request.structure.parameters
                }
            ],
            "boundary_conditions": {
                "upstream": request.boundaries.upstream,
                "downstream": request.boundaries.downstream
            },
            "initial_conditions": {
                "depth": "uniform_flow" # 让引擎自动计算
            },
            "solver": { # 默认值，未来可以从API传入
                "method": "hydrostatic",
                "parameters": {
                    "theta": 0.6, "omega": 0.95,
                    "max_iterations": 100, "convergence_tol": 1e-6
                }
            }
        }
        
        # 2. 调用服务层
        results = simulation_service.run_simulation_from_config(config)
        
        # 3. 包装响应
        status = results.get("status", "completed")
        if "error" in status:
            return ComplexSimulationResponse(
                task_id=str(uuid.uuid4()), status='failed',
                simulation_time_ms=(time.time() - start_time) * 1000,
                timestamp=datetime.now().isoformat(), results={}, error=results.get("message", "未知仿真错误")
            )

        return ComplexSimulationResponse(
            task_id=results.get("task_id"), status='completed',
            simulation_time_ms=(time.time() - start_time) * 1000,
            timestamp=datetime.now().isoformat(), results=results, error=None
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"API层发生内部错误: {e}")

@router.get("/simulation-results/{task_id}", summary="获取仿真结果")
async def get_simulation_result(task_id: str):
    """
    获取指定任务ID的仿真结果
    """
    result = simulation_service.get_simulation_result(task_id)
    if not result:
        raise HTTPException(status_code=404, detail="Result not found or task not started")
    return result

# ==================== 辅助API ====================

@router.get("/types", summary="获取支持的结构类型")
async def get_structure_types():
    return {
        "pumps": ["single", "parallel", "series"], "gates": ["sluice", "radial"],
        "weirs": ["broad_crested", "sharp_crested", "v_notch"], "turbines": ["simplified", "francis"],
        "valves": ["general", "butterfly"], "canal_structures": ["sluice_gate", "pump", "weir"]
    }

@router.get("/health", summary="健康检查")
async def health_check():
    return { "status": "healthy", "timestamp": datetime.now().isoformat(), "refactor_status": "服务层已集成" }

@router.get("/version", summary="获取版本信息")
async def get_version():
    return { "api_version": "2.2.0-service-layer", "engine_version": "V2 (via service)" }
