#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Network and Complex System API Router (Week 5-6)
管网和复杂系统API路由模块

对标商业软件（EPANET、WaterCAD）的管网和组合系统API

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
    prefix="/network",
    tags=["network", "complex_system"],
    responses={404: {"description": "Not found"}},
)

# 全局引擎实例
engine = HydraulicEngineV2()


# ========== Pydantic数据模型 ==========

class PipeConfig(BaseModel):
    """管道配置"""
    name: str = Field(default="Pipe-001", description="管道名称")
    length: float = Field(default=1000.0, description="长度 (m)")
    diameter: float = Field(default=1.0, description="直径 (m)")
    roughness: float = Field(default=0.025, description="粗糙度")
    slope: float = Field(default=0.001, description="底坡")
    formula: str = Field(default="manning", description="计算公式: manning, darcy, hazen_williams")


class FlowConfig(BaseModel):
    """流量配置"""
    discharge: float = Field(..., description="流量 (m³/s)")
    upstream_pressure: float = Field(default=100.0, description="上游压力 (kPa)")


class PipeFlowRequest(BaseModel):
    """管道流动请求"""
    task_id: str = Field(default="pipe_flow_001", description="任务ID")
    pipe: PipeConfig
    flow: FlowConfig


class NodeConfig(BaseModel):
    """节点配置"""
    id: str = Field(..., description="节点ID")
    elevation: float = Field(..., description="高程 (m)")
    demand: float = Field(default=0.0, description="需水量 (m³/s)")


class PipeSegment(BaseModel):
    """管段配置"""
    id: str = Field(..., description="管段ID")
    from_node: str = Field(..., description="起始节点", alias="from")
    to_node: str = Field(..., description="终止节点", alias="to")
    length: float = Field(..., description="长度 (m)")
    diameter: float = Field(..., description="直径 (m)")


class SourceConfig(BaseModel):
    """水源配置"""
    node: str = Field(..., description="水源节点ID")
    head: float = Field(..., description="总水头 (m)")


class NetworkSimulationRequest(BaseModel):
    """管网仿真请求"""
    task_id: str = Field(default="network_sim_001", description="任务ID")
    nodes: List[NodeConfig]
    pipes: List[PipeSegment]
    source: SourceConfig


class ComponentConfig(BaseModel):
    """组件配置"""
    type: str = Field(..., description="组件类型: pump, pipe, storage, weir, etc.")
    config: Dict[str, Any] = Field(default={}, description="组件参数")


class ConnectionConfig(BaseModel):
    """连接配置"""
    from_component: int = Field(..., description="源组件索引", alias="from")
    to_component: int = Field(..., description="目标组件索引", alias="to")


class OperationConfig(BaseModel):
    """运行配置"""
    duration: float = Field(default=3600.0, description="仿真时长 (s)")
    timestep: float = Field(default=60.0, description="时间步长 (s)")


class ComplexSystemRequest(BaseModel):
    """复杂系统请求"""
    task_id: str = Field(default="complex_system_001", description="任务ID")
    components: List[ComponentConfig]
    connections: List[ConnectionConfig]
    operation: OperationConfig


class ObjectivesConfig(BaseModel):
    """优化目标配置"""
    minimize_cost: bool = Field(default=True, description="最小化成本")
    maximize_reliability: bool = Field(default=False, description="最大化可靠性")
    minimize_energy: bool = Field(default=False, description="最小化能耗")


class ConstraintsConfig(BaseModel):
    """约束条件配置"""
    min_pressure: float = Field(default=20.0, description="最小压力 (m)")
    max_flow: float = Field(default=50.0, description="最大流量 (m³/s)")
    emergency_storage: float = Field(default=500.0, description="应急储备 (m³)")


class ForecastConfig(BaseModel):
    """预测配置"""
    demand: List[float] = Field(..., description="需求预测 (m³/s)")
    horizon: int = Field(default=24, description="预测时长 (小时)")


class IntegratedOperationRequest(BaseModel):
    """综合调度请求"""
    task_id: str = Field(default="integrated_op_001", description="任务ID")
    system: Dict[str, Any]
    objectives: ObjectivesConfig
    constraints: ConstraintsConfig
    forecast: ForecastConfig


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

@router.post("/pipe-flow", response_model=SimulationResponse, summary="管道流动计算")
async def simulate_pipe_flow(request: PipeFlowRequest):
    """
    运行管道流动计算
    
    支持计算公式：
    - Manning公式
    - Darcy-Weisbach公式
    - Hazen-Williams公式
    
    功能：
    - 满流/非满流判断
    - 水头损失计算
    - 压力分布
    - Reynolds数计算
    """
    try:
        config = {
            'pipe': request.pipe.dict(),
            'flow': request.flow.dict()
        }
        
        result = engine.run_pipe_flow(request.task_id, config)
        
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


@router.post("/simulation", response_model=SimulationResponse, summary="管网仿真")
async def simulate_network(request: NetworkSimulationRequest):
    """
    运行管网仿真
    
    功能：
    - 多管段连接
    - 节点水头平衡
    - Hardy-Cross法
    - 流量分配
    - 压力分布
    
    对标商业软件：
    - EPANET: Network Solver
    - WaterCAD: Pipe Network Analysis
    """
    try:
        config = {
            'nodes': [node.dict() for node in request.nodes],
            'pipes': [pipe.dict() for pipe in request.pipes],
            'source': request.source.dict()
        }
        
        result = engine.run_network_simulation(request.task_id, config)
        
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


@router.post("/complex-system", response_model=SimulationResponse, summary="复杂系统仿真")
async def simulate_complex_system(request: ComplexSystemRequest):
    """
    运行复杂组合系统仿真
    
    适用场景：
    - 泵站+管网+水池组合
    - 串并联系统
    - 多级提升
    - 联合调度
    
    支持组件：
    - pump: 泵站
    - pipe: 管道
    - storage: 调蓄池
    - weir: 堰
    - gate: 闸门
    - reservoir: 水库
    """
    try:
        config = {
            'components': [comp.dict() for comp in request.components],
            'connections': [conn.dict() for conn in request.connections],
            'operation': request.operation.dict()
        }
        
        result = engine.run_complex_system(request.task_id, config)
        
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


@router.post("/integrated-operation", response_model=SimulationResponse, summary="综合调度优化")
async def optimize_integrated_operation(request: IntegratedOperationRequest):
    """
    运行综合调度优化
    
    功能：
    - 多目标优化（经济、安全、环境）
    - 实时调度
    - 预测调度
    - 应急响应
    
    优化目标：
    - 最小化运行成本
    - 最大化供水可靠性
    - 最小化能源消耗
    
    约束条件：
    - 最小压力保障
    - 最大流量限制
    - 应急储备要求
    """
    try:
        config = {
            'system': request.system,
            'objectives': request.objectives.dict(),
            'constraints': request.constraints.dict(),
            'forecast': request.forecast.dict()
        }
        
        result = engine.run_integrated_operation(request.task_id, config)
        
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


@router.get("/formulas", summary="获取支持的管道计算公式")
async def get_pipe_formulas():
    """获取支持的管道水力计算公式列表"""
    return {
        "formulas": [
            {
                "name": "manning",
                "full_name": "Manning公式",
                "description": "明渠/管道均匀流计算，适用于重力流",
                "formula": "Q = (1/n) * A * R^(2/3) * S^(1/2)",
                "parameters": ["n (糙率)", "A (面积)", "R (水力半径)", "S (坡度)"]
            },
            {
                "name": "darcy",
                "full_name": "Darcy-Weisbach公式",
                "description": "压力管道水头损失计算，理论基础最严密",
                "formula": "hf = f * (L/D) * (V²/2g)",
                "parameters": ["f (摩阻系数)", "L (长度)", "D (直径)", "V (流速)"]
            },
            {
                "name": "hazen_williams",
                "full_name": "Hazen-Williams公式",
                "description": "给水管网常用，计算简便",
                "formula": "hf = 10.67 * Q^1.852 / (C^1.852 * D^4.87) * L",
                "parameters": ["C (Hazen-Williams系数)", "Q (流量)", "D (直径)", "L (长度)"]
            }
        ],
        "total": 3
    }


@router.get("/health", summary="健康检查")
async def health_check():
    """API健康检查"""
    return {
        "status": "healthy",
        "module": "network_and_complex_system",
        "engine_version": engine.version,
        "available_endpoints": [
            "/network/pipe-flow",
            "/network/simulation",
            "/network/complex-system",
            "/network/integrated-operation",
            "/network/formulas",
            "/network/test-configs"
        ]
    }


@router.get("/test-configs", summary="获取测试配置")
async def get_test_configs():
    """获取测试配置示例"""
    return {
        "pipe_flow_example": {
            "task_id": "pipe_flow_test_001",
            "pipe": {
                "name": "Test-Pipe",
                "length": 1000.0,
                "diameter": 1.0,
                "roughness": 0.025,
                "slope": 0.001,
                "formula": "manning"
            },
            "flow": {
                "discharge": 1.5,
                "upstream_pressure": 100.0
            }
        },
        "network_example": {
            "task_id": "network_test_001",
            "nodes": [
                {"id": "N1", "elevation": 100.0, "demand": 0.0},
                {"id": "N2", "elevation": 95.0, "demand": 0.5},
                {"id": "N3", "elevation": 90.0, "demand": 0.3}
            ],
            "pipes": [
                {"id": "P1", "from": "N1", "to": "N2", "length": 500.0, "diameter": 0.5},
                {"id": "P2", "from": "N2", "to": "N3", "length": 400.0, "diameter": 0.4}
            ],
            "source": {
                "node": "N1",
                "head": 120.0
            }
        },
        "complex_system_example": {
            "task_id": "complex_test_001",
            "components": [
                {"type": "pump", "config": {"flow_rate": 10.0, "head": 20.0}},
                {"type": "pipe", "config": {"length": 500.0, "diameter": 0.8}},
                {"type": "storage", "config": {"initial_volume": 1000.0, "initial_elevation": 10.0}}
            ],
            "connections": [
                {"from": 0, "to": 1},
                {"from": 1, "to": 2}
            ],
            "operation": {
                "duration": 3600.0,
                "timestep": 60.0
            }
        },
        "integrated_operation_example": {
            "task_id": "integrated_op_test_001",
            "system": {
                "pumps": [{"id": "P1", "capacity": 10.0}],
                "reservoirs": [{"id": "R1", "capacity": 5000.0}],
                "network": {}
            },
            "objectives": {
                "minimize_cost": True,
                "maximize_reliability": False,
                "minimize_energy": True
            },
            "constraints": {
                "min_pressure": 20.0,
                "max_flow": 50.0,
                "emergency_storage": 500.0
            },
            "forecast": {
                "demand": [10, 15, 20, 25, 20, 15, 10],
                "horizon": 7
            }
        }
    }


if __name__ == '__main__':
    print("Network & Complex System API Router (Week 5-6)")
    print("="*60)
    print(f"引擎版本: {engine.version}")
    print(f"可用端点数: 6")
    print("\n✅ 功能模块:")
    print("  1. 管道流动计算 (Manning/Darcy/Hazen-Williams)")
    print("  2. 管网仿真 (Hardy-Cross)")
    print("  3. 复杂组合系统 (多组件)")
    print("  4. 综合调度优化 (多目标)")
    print("\n✅ 对标商业软件:")
    print("  - EPANET: 管网水力分析")
    print("  - WaterCAD: 给水管网设计")
    print("  - InfoWorks: 城市排水系统")
    print("\n" + "="*60)
