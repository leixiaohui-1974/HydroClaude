"""
Structures API Router - Week 1-2
水工结构API路由

提供泵站、闸门等水工结构的仿真接口
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
import uuid

# 导入引擎
import sys
from pathlib import Path
backend_path = Path(__file__).parent.parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from core.hydraulic_engine_v2 import HydraulicEngineV2

router = APIRouter(prefix="/structures", tags=["structures"])

# 全局引擎实例
engine = HydraulicEngineV2()


# ==================== Pydantic Models ====================

class PumpConfig(BaseModel):
    """泵站配置"""
    flow_rate: float = Field(10.0, description="设计流量 (m³/s)")
    head: float = Field(15.0, description="设计扬程 (m)")
    num_pumps: int = Field(1, description="泵数量")
    pump_type: str = Field("single", description="泵类型: single, parallel, series")
    name: Optional[str] = Field("Pump-001", description="泵站名称")
    position: float = Field(500.0, description="位置 (m)")


class PumpSimulationRequest(BaseModel):
    """泵站仿真请求"""
    pump: PumpConfig
    upstream: Dict[str, float] = Field({"water_level": 5.0}, description="上游条件")
    downstream: Dict[str, float] = Field({"elevation": 20.0}, description="下游条件")
    operation: Dict[str, float] = Field({"duration": 3600.0}, description="运行参数")


class GateConfig(BaseModel):
    """闸门配置"""
    type: str = Field("sluice", description="闸门类型: sluice, radial")
    width: float = Field(5.0, description="闸门宽度 (m)")
    opening: float = Field(2.0, description="开度 (m)")
    discharge_coeff: float = Field(0.6, description="流量系数")
    name: Optional[str] = Field("Gate-001", description="闸门名称")
    position: float = Field(500.0, description="位置 (m)")


class GateSimulationRequest(BaseModel):
    """闸门仿真请求"""
    gate: GateConfig
    upstream: Dict[str, float] = Field({"water_depth": 5.0}, description="上游水深")
    downstream: Dict[str, float] = Field({"water_depth": 2.0}, description="下游水深")


class CanalWithPumpRequest(BaseModel):
    """明渠+泵站组合仿真请求"""
    canal: Dict[str, Any] = Field(..., description="明渠配置")
    pump: PumpConfig


class CanalWithGateRequest(BaseModel):
    """明渠+闸门组合仿真请求"""
    canal: Dict[str, Any] = Field(..., description="明渠配置")
    gate: GateConfig


class SimulationResponse(BaseModel):
    """仿真响应"""
    task_id: str
    status: str
    time: List[float]
    x: List[float]
    h: List[List[float]]
    Q: List[List[float]]
    V: List[List[float]]
    metrics: Dict[str, Any]
    duration: float
    timestamp: str
    error: Optional[str] = None


# ==================== API Endpoints ====================

@router.post("/pump", response_model=SimulationResponse, summary="泵站仿真")
async def run_pump_simulation(request: PumpSimulationRequest):
    """
    运行泵站仿真
    
    功能：
    - 单泵/多泵运行模拟
    - 泵特性曲线计算
    - 效率分析
    - 能耗计算
    
    示例：
    ```json
    {
      "pump": {
        "flow_rate": 10.0,
        "head": 15.0,
        "num_pumps": 2,
        "pump_type": "parallel"
      },
      "upstream": {"water_level": 5.0},
      "downstream": {"elevation": 20.0},
      "operation": {"duration": 3600.0}
    }
    ```
    """
    try:
        task_id = str(uuid.uuid4())
        
        config = {
            'pump': request.pump.model_dump(),
            'upstream': request.upstream,
            'downstream': request.downstream,
            'operation': request.operation
        }
        
        result = engine.run_pump_simulation(task_id, config)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/gate", response_model=SimulationResponse, summary="闸门水力计算")
async def run_gate_simulation(request: GateSimulationRequest):
    """
    运行闸门水力计算
    
    功能：
    - 过闸流量计算
    - 流态判断（自由流/淹没流）
    - 多种闸门类型支持
    
    示例：
    ```json
    {
      "gate": {
        "type": "sluice",
        "width": 5.0,
        "opening": 2.0
      },
      "upstream": {"water_depth": 5.0},
      "downstream": {"water_depth": 2.0}
    }
    ```
    """
    try:
        task_id = str(uuid.uuid4())
        
        config = {
            'gate': request.gate.model_dump(),
            'upstream': request.upstream,
            'downstream': request.downstream
        }
        
        result = engine.run_gate_simulation(task_id, config)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/canal-with-pump", response_model=SimulationResponse, summary="明渠+泵站组合仿真")
async def run_canal_with_pump(request: CanalWithPumpRequest):
    """
    运行明渠+泵站组合仿真
    
    适用场景：
    - 灌溉渠道提水
    - 排水渠道排涝
    - 调水工程
    
    示例：
    ```json
    {
      "canal": {
        "width": 10.0,
        "length": 1000.0,
        "n_cells": 200,
        "t_end": 100.0
      },
      "pump": {
        "position": 500.0,
        "flow_rate": 5.0,
        "head": 10.0
      }
    }
    ```
    """
    try:
        task_id = str(uuid.uuid4())
        
        config = {
            'canal': request.canal,
            'pump': request.pump.model_dump()
        }
        
        result = engine.run_canal_with_pump(task_id, config)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/canal-with-gate", response_model=SimulationResponse, summary="明渠+闸门组合仿真")
async def run_canal_with_gate(request: CanalWithGateRequest):
    """
    运行明渠+闸门组合仿真
    
    适用场景：
    - 灌溉渠道流量控制
    - 水位调节
    - 分水闸
    
    示例：
    ```json
    {
      "canal": {
        "width": 10.0,
        "length": 1000.0,
        "n_cells": 200,
        "t_end": 100.0
      },
      "gate": {
        "position": 500.0,
        "width": 5.0,
        "opening": 2.0,
        "type": "sluice"
      }
    }
    ```
    """
    try:
        task_id = str(uuid.uuid4())
        
        config = {
            'canal': request.canal,
            'gate': request.gate.model_dump()
        }
        
        result = engine.run_canal_with_gate(task_id, config)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/types", summary="获取支持的结构类型")
async def get_structure_types():
    """
    获取支持的水工结构类型列表
    
    Returns:
        支持的结构类型及其说明
    """
    return {
        "structures": {
            "pump": {
                "name": "泵站",
                "types": ["single", "parallel", "series"],
                "description": "单泵、并联、串联泵站"
            },
            "gate": {
                "name": "闸门",
                "types": ["sluice", "radial"],
                "description": "滑动闸门、弧形闸门"
            }
        },
        "combinations": [
            {"name": "canal_with_pump", "description": "明渠+泵站"},
            {"name": "canal_with_gate", "description": "明渠+闸门"}
        ],
        "version": engine.version
    }


@router.get("/health", summary="健康检查")
async def health_check():
    """API健康检查"""
    return {
        "status": "healthy",
        "engine_version": engine.version,
        "available_methods": len(engine.get_engine_info()['available_methods'])
    }


# 测试数据生成器
@router.get("/test-configs", summary="获取测试配置")
async def get_test_configs():
    """获取测试用的配置示例"""
    return {
        "pump_example": {
            "pump": {
                "flow_rate": 10.0,
                "head": 15.0,
                "num_pumps": 2,
                "pump_type": "parallel"
            },
            "upstream": {"water_level": 5.0},
            "downstream": {"elevation": 20.0},
            "operation": {"duration": 3600.0}
        },
        "gate_example": {
            "gate": {
                "type": "sluice",
                "width": 5.0,
                "opening": 2.0,
                "discharge_coeff": 0.6
            },
            "upstream": {"water_depth": 5.0},
            "downstream": {"water_depth": 2.0}
        }
    }
