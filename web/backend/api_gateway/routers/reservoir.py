#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Reservoir and Weir API Router (Week 3-4)
水库和堰API路由模块

对标商业软件（HEC-RAS、MIKE）的水库调度和堰流计算API

Author: HydroClaude Team
Date: 2025-11-15
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
import sys
import os

# 添加backend路径
backend_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from core.hydraulic_engine_v2 import HydraulicEngineV2

# 创建路由器
router = APIRouter(
    prefix="/reservoir",
    tags=["reservoir", "weir"],
    responses={404: {"description": "Not found"}},
)

# 全局引擎实例
engine = HydraulicEngineV2()


# ========== Pydantic数据模型 ==========

class WeirConfig(BaseModel):
    """堰配置"""
    type: str = Field(..., description="堰类型: broad_crested, sharp_crested, ogee, v_notch")
    name: str = Field(default="Weir-001", description="堰名称")
    position: float = Field(default=500.0, description="堰位置 (m)")
    width: float = Field(default=10.0, description="堰宽 (m)")
    crest_height: float = Field(default=1.5, description="堰顶高程 (m)")
    discharge_coeff: float = Field(default=1.7, description="流量系数")
    angle: Optional[float] = Field(default=90.0, description="V形堰角度 (度)")


class WeirUpDownCondition(BaseModel):
    """堰上下游条件"""
    water_depth: float = Field(..., description="水深 (m)")


class WeirSimulationRequest(BaseModel):
    """堰流仿真请求"""
    task_id: str = Field(default="weir_sim_001", description="任务ID")
    weir: WeirConfig
    upstream: WeirUpDownCondition
    downstream: WeirUpDownCondition


class CanalWithWeirRequest(BaseModel):
    """明渠+堰组合仿真请求"""
    task_id: str = Field(default="canal_weir_001", description="任务ID")
    canal: Dict[str, Any] = Field(..., description="明渠配置")
    weir: WeirConfig


class ReservoirConfig(BaseModel):
    """水库配置"""
    name: str = Field(default="Reservoir-001", description="水库名称")
    position: float = Field(default=0.0, description="位置 (m)")
    elevation: List[float] = Field(..., description="水位列表 (m)")
    area: List[float] = Field(..., description="面积列表 (m²)")
    initial_elevation: float = Field(default=15.0, description="初始水位 (m)")
    spillway_elevation: float = Field(default=25.0, description="溢洪道高程 (m)")
    spillway_width: float = Field(default=20.0, description="溢洪道宽度 (m)")


class InflowConfig(BaseModel):
    """入流配置"""
    type: str = Field(default="constant", description="入流类型: constant, hydrograph")
    value: float = Field(default=50.0, description="入流流量 (m³/s)")


class OutflowConfig(BaseModel):
    """出流配置"""
    type: str = Field(default="constant", description="出流类型: constant, gate_control")
    value: float = Field(default=30.0, description="出流流量 (m³/s)")


class SimulationConfig(BaseModel):
    """仿真配置"""
    duration: float = Field(default=86400.0, description="仿真时长 (s)")
    dt: float = Field(default=60.0, description="时间步长 (s)")


class ReservoirSimulationRequest(BaseModel):
    """水库调度仿真请求"""
    task_id: str = Field(default="reservoir_sim_001", description="任务ID")
    reservoir: ReservoirConfig
    inflow: InflowConfig
    outflow: OutflowConfig
    simulation: SimulationConfig


class InflowHydrograph(BaseModel):
    """入流过程线"""
    time: List[float] = Field(..., description="时间点列表 (s)")
    flow: List[float] = Field(..., description="流量列表 (m³/s)")


class OperationRule(BaseModel):
    """调度规则"""
    normal_level: float = Field(default=20.0, description="正常蓄水位 (m)")
    flood_limit: float = Field(default=18.0, description="汛限水位 (m)")
    dead_level: float = Field(default=10.0, description="死水位 (m)")
    max_release: float = Field(default=80.0, description="最大泄流量 (m³/s)")


class ReservoirOperationRequest(BaseModel):
    """水库优化调度请求"""
    task_id: str = Field(default="reservoir_op_001", description="任务ID")
    reservoir: ReservoirConfig
    inflow_hydrograph: InflowHydrograph
    operation_rule: OperationRule


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


# ========== API端点 ==========

@router.post("/weir", response_model=SimulationResponse, summary="堰流仿真")
async def simulate_weir(request: WeirSimulationRequest):
    """
    运行堰流计算
    
    支持堰类型：
    - broad_crested: 宽顶堰
    - sharp_crested: 尖顶堰（薄壁堰）
    - ogee: 溢流堰
    - v_notch: V形堰
    
    功能：
    - 自由流/淹没流判断
    - 流量系数计算
    - 过堰流量计算
    """
    try:
        config = {
            'weir': request.weir.dict(),
            'upstream': request.upstream.dict(),
            'downstream': request.downstream.dict()
        }
        
        result = engine.run_weir_simulation(request.task_id, config)
        
        if result.status == 'failed':
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.error
            )
        
        return SimulationResponse(**result.__dict__)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/canal-with-weir", response_model=SimulationResponse, summary="明渠+堰组合仿真")
async def simulate_canal_with_weir(request: CanalWithWeirRequest):
    """
    运行明渠+堰组合仿真
    
    适用场景：
    - 测流堰
    - 溢流堰
    - 跌水堰
    
    计算流程：
    1. 运行明渠水动力仿真
    2. 在堰位置计算过堰流量
    3. 分析堰对水面线的影响
    """
    try:
        config = {
            'canal': request.canal,
            'weir': request.weir.dict()
        }
        
        result = engine.run_canal_with_weir(request.task_id, config)
        
        if result.status == 'failed':
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.error
            )
        
        return SimulationResponse(**result.__dict__)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/simulation", response_model=SimulationResponse, summary="水库调度仿真")
async def simulate_reservoir(request: ReservoirSimulationRequest):
    """
    运行水库调度仿真
    
    功能：
    - 水位-库容关系
    - 入流-出流平衡
    - 水位演算
    - 滞洪演算
    - 溢流计算
    
    对标商业软件：
    - HEC-RAS: Storage Area
    - MIKE: Basin
    """
    try:
        config = {
            'reservoir': request.reservoir.dict(),
            'inflow': request.inflow.dict(),
            'outflow': request.outflow.dict(),
            'simulation': request.simulation.dict()
        }
        
        result = engine.run_reservoir_simulation(request.task_id, config)
        
        if result.status == 'failed':
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.error
            )
        
        return SimulationResponse(**result.__dict__)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/operation", response_model=SimulationResponse, summary="水库优化调度")
async def optimize_reservoir_operation(request: ReservoirOperationRequest):
    """
    运行水库优化调度
    
    功能：
    - 防洪调度
    - 兴利调度
    - 多目标优化
    - 调度规则
    
    调度策略：
    - 超过汛限水位 → 加大泄流
    - 低于死水位 → 减小泄流
    - 正常运行 → 入流=出流
    """
    try:
        config = {
            'reservoir': request.reservoir.dict(),
            'inflow_hydrograph': request.inflow_hydrograph.dict(),
            'operation_rule': request.operation_rule.dict()
        }
        
        result = engine.run_reservoir_operation(request.task_id, config)
        
        if result.status == 'failed':
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.error
            )
        
        return SimulationResponse(**result.__dict__)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/weir-types", summary="获取支持的堰类型")
async def get_weir_types():
    """获取支持的堰类型列表"""
    return {
        "weir_types": [
            {
                "type": "broad_crested",
                "name": "宽顶堰",
                "description": "堰顶较宽，水流达到临界流，适用于大流量",
                "discharge_coeff_range": [1.6, 1.7]
            },
            {
                "type": "sharp_crested",
                "name": "尖顶堰（薄壁堰）",
                "description": "堰顶尖锐，流量公式精确，常用于测流",
                "discharge_coeff_range": [1.7, 1.84]
            },
            {
                "type": "ogee",
                "name": "溢流堰",
                "description": "优化堰面曲线，泄流能力强，用于水坝溢洪道",
                "discharge_coeff_range": [1.8, 2.2]
            },
            {
                "type": "v_notch",
                "name": "V形堰",
                "description": "三角形缺口，小流量测量精度高",
                "angle_range": [30, 120]
            }
        ],
        "total": 4
    }


@router.get("/health", summary="健康检查")
async def health_check():
    """API健康检查"""
    return {
        "status": "healthy",
        "module": "reservoir_and_weir",
        "engine_version": engine.version,
        "available_endpoints": [
            "/reservoir/weir",
            "/reservoir/canal-with-weir",
            "/reservoir/simulation",
            "/reservoir/operation",
            "/reservoir/weir-types",
            "/reservoir/test-configs"
        ]
    }


@router.get("/test-configs", summary="获取测试配置")
async def get_test_configs():
    """获取测试配置示例"""
    return {
        "weir_example": {
            "task_id": "weir_test_001",
            "weir": {
                "type": "broad_crested",
                "name": "Test-Weir",
                "position": 500.0,
                "width": 10.0,
                "crest_height": 1.5,
                "discharge_coeff": 1.7
            },
            "upstream": {"water_depth": 3.0},
            "downstream": {"water_depth": 1.0}
        },
        "reservoir_example": {
            "task_id": "reservoir_test_001",
            "reservoir": {
                "name": "Test-Reservoir",
                "position": 0.0,
                "elevation": [0, 10, 20, 30],
                "area": [0, 1000, 4000, 9000],
                "initial_elevation": 15.0,
                "spillway_elevation": 25.0,
                "spillway_width": 20.0
            },
            "inflow": {"type": "constant", "value": 50.0},
            "outflow": {"type": "constant", "value": 30.0},
            "simulation": {"duration": 86400.0, "dt": 60.0}
        },
        "canal_with_weir_example": {
            "task_id": "canal_weir_test_001",
            "canal": {
                "length": 1000.0,
                "width": 10.0,
                "slope": 0.001,
                "manning_n": 0.025,
                "initial_conditions": {"type": "uniform", "h": 3.0, "Q": 50.0}
            },
            "weir": {
                "type": "broad_crested",
                "position": 500.0,
                "width": 10.0,
                "crest_height": 1.5,
                "discharge_coeff": 1.7
            }
        },
        "reservoir_operation_example": {
            "task_id": "reservoir_op_test_001",
            "reservoir": {
                "name": "Test-Reservoir",
                "position": 0.0,
                "elevation": [0, 10, 20, 30],
                "area": [0, 1000, 4000, 9000],
                "initial_elevation": 15.0,
                "spillway_elevation": 25.0,
                "spillway_width": 20.0
            },
            "inflow_hydrograph": {
                "time": [0, 3600, 7200, 10800, 14400],
                "flow": [30, 80, 120, 60, 30]
            },
            "operation_rule": {
                "normal_level": 20.0,
                "flood_limit": 18.0,
                "dead_level": 10.0,
                "max_release": 100.0
            }
        }
    }


if __name__ == '__main__':
    print("Reservoir & Weir API Router (Week 3-4)")
    print("="*60)
    print(f"引擎版本: {engine.version}")
    print(f"可用端点数: 7")
    print("\n✅ 堰类型:")
    print("  - broad_crested (宽顶堰)")
    print("  - sharp_crested (尖顶堰)")
    print("  - ogee (溢流堰)")
    print("  - v_notch (V形堰)")
    print("\n✅ 水库功能:")
    print("  - 水位演算")
    print("  - 滞洪演算")
    print("  - 优化调度")
    print("  - 溢流计算")
    print("\n" + "="*60)
