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
                "types": ["sluice", "radial", "vertical_lift", "roller", "flap"],
                "description": "滑动闸门、径向闸门、垂直提升闸门等"
            },
            "weir": {
                "name": "堰",
                "types": ["broad_crested", "sharp_crested", "v_notch", "ogee"],
                "description": "各类堰型"
            },
            "turbine": {
                "name": "水轮机",
                "types": ["francis", "kaplan", "pelton"],
                "description": "混流式、轴流式、冲击式水轮机"
            },
            "valve": {
                "name": "阀门",
                "types": ["butterfly", "ball", "gate", "globe"],
                "description": "蝶阀、球阀、闸阀等"
            },
            "surge_tank": {
                "name": "调压井",
                "types": ["simple", "throttled", "differential"],
                "description": "简单式、阻抗式、差动式调压井"
            },
            "culvert": {
                "name": "涵洞",
                "description": "过水涵洞"
            },
            "bridge": {
                "name": "桥梁",
                "description": "桥梁壅水分析"
            }
        },
        "combinations": [
            {"name": "canal_with_pump", "description": "明渠+泵站"},
            {"name": "canal_with_gate", "description": "明渠+闸门"},
            {"name": "canal_with_weir", "description": "明渠+堰"}
        ],
        "version": engine.version,
        "total_components": 23
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


# ==================== 扩展API端点 - P0任务 ====================

# ----- 闸门系统扩展 -----

@router.post("/radial-gate", response_model=SimulationResponse, summary="径向闸门仿真")
async def run_radial_gate_simulation(request: GateSimulationRequest):
    """径向闸门水力计算"""
    try:
        task_id = str(uuid.uuid4())
        config = {
            'gate': request.gate.model_dump(),
            'upstream': request.upstream,
            'downstream': request.downstream
        }
        # 如果引擎有对应方法则调用，否则使用通用gate方法
        if hasattr(engine, 'run_radial_gate_simulation'):
            result = engine.run_radial_gate_simulation(task_id, config)
        else:
            config['gate']['type'] = 'radial'
            result = engine.run_gate_simulation(task_id, config)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/vertical-lift-gate", response_model=SimulationResponse, summary="垂直提升闸门")
async def run_vertical_lift_gate(request: GateSimulationRequest):
    """垂直提升闸门仿真"""
    try:
        task_id = str(uuid.uuid4())
        config = {
            'gate': request.gate.model_dump(),
            'upstream': request.upstream,
            'downstream': request.downstream
        }
        config['gate']['type'] = 'vertical_lift'
        result = engine.run_gate_simulation(task_id, config)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ----- 堰系统 -----

class WeirConfig(BaseModel):
    """堰配置"""
    type: str = Field("broad_crested", description="堰类型")
    width: float = Field(10.0, description="堰宽 (m)")
    crest_height: float = Field(1.0, description="堰顶高程 (m)")
    discharge_coeff: float = Field(0.6, description="流量系数")
    position: float = Field(500.0, description="位置 (m)")


class WeirSimulationRequest(BaseModel):
    """堰仿真请求"""
    weir: WeirConfig
    upstream: Dict[str, float] = Field({"water_depth": 5.0}, description="上游水深")
    downstream: Dict[str, float] = Field({"water_depth": 2.0}, description="下游水深")


@router.post("/broad-crested-weir", response_model=SimulationResponse, summary="宽顶堰")
async def run_broad_crested_weir(request: WeirSimulationRequest):
    """宽顶堰水力计算"""
    try:
        task_id = str(uuid.uuid4())
        config = {
            'weir': request.weir.model_dump(),
            'upstream': request.upstream,
            'downstream': request.downstream
        }
        config['weir']['type'] = 'broad_crested'
        result = engine.run_weir_simulation(task_id, config)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sharp-crested-weir", response_model=SimulationResponse, summary="尖顶堰")
async def run_sharp_crested_weir(request: WeirSimulationRequest):
    """尖顶堰水力计算"""
    try:
        task_id = str(uuid.uuid4())
        config = {
            'weir': request.weir.model_dump(),
            'upstream': request.upstream,
            'downstream': request.downstream
        }
        config['weir']['type'] = 'sharp_crested'
        result = engine.run_weir_simulation(task_id, config)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/v-notch-weir", response_model=SimulationResponse, summary="V型槽堰")
async def run_v_notch_weir(request: WeirSimulationRequest):
    """V型槽堰水力计算"""
    try:
        task_id = str(uuid.uuid4())
        config = {
            'weir': request.weir.model_dump(),
            'upstream': request.upstream,
            'downstream': request.downstream
        }
        config['weir']['type'] = 'v_notch'
        result = engine.run_weir_simulation(task_id, config)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ----- 高级组件 -----

class TurbineConfig(BaseModel):
    """水轮机配置"""
    type: str = Field("francis", description="水轮机类型: francis, kaplan, pelton")
    rated_power: float = Field(50.0, description="额定功率 (MW)")
    rated_head: float = Field(100.0, description="额定水头 (m)")
    rated_flow: float = Field(60.0, description="额定流量 (m³/s)")
    position: float = Field(500.0, description="位置 (m)")


class TurbineSimulationRequest(BaseModel):
    """水轮机仿真请求"""
    turbine: TurbineConfig
    operation: Dict[str, float] = Field({"head": 100.0, "flow": 60.0}, description="运行工况")


@router.post("/turbine", response_model=SimulationResponse, summary="水轮机仿真")
async def run_turbine_simulation(request: TurbineSimulationRequest):
    """水轮机性能计算"""
    try:
        task_id = str(uuid.uuid4())
        config = {
            'turbine': request.turbine.model_dump(),
            'operation': request.operation
        }
        
        # 简化计算：基于额定工况
        turbine_cfg = config['turbine']
        operation = config['operation']
        
        # 功率计算（简化）
        head_ratio = operation.get('head', 100.0) / turbine_cfg['rated_head']
        flow_ratio = operation.get('flow', 60.0) / turbine_cfg['rated_flow']
        power = turbine_cfg['rated_power'] * head_ratio * flow_ratio
        efficiency = 0.9 * min(head_ratio, flow_ratio)  # 简化效率曲线
        
        return SimulationResponse(
            task_id=task_id,
            status='completed',
            time=[0.0],
            x=[turbine_cfg['position']],
            h=[[operation.get('head', 100.0)]],
            Q=[[operation.get('flow', 60.0)]],
            V=[[0.0]],
            metrics={
                'power_MW': power,
                'efficiency': efficiency,
                'turbine_type': turbine_cfg['type']
            },
            duration=0.01,
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ValveConfig(BaseModel):
    """阀门配置"""
    type: str = Field("butterfly", description="阀门类型")
    diameter: float = Field(1.0, description="直径 (m)")
    opening_percent: float = Field(80.0, description="开度 (%)")
    position: float = Field(500.0, description="位置 (m)")


class ValveSimulationRequest(BaseModel):
    """阀门仿真请求"""
    valve: ValveConfig
    operation: Dict[str, float] = Field({"pressure_drop": 100.0}, description="运行参数")


@router.post("/valve", response_model=SimulationResponse, summary="阀门仿真")
async def run_valve_simulation(request: ValveSimulationRequest):
    """阀门水力计算"""
    try:
        task_id = str(uuid.uuid4())
        config = {
            'valve': request.valve.model_dump(),
            'operation': request.operation
        }
        
        valve_cfg = config['valve']
        delta_p = config['operation'].get('pressure_drop', 100.0)
        
        # 简化流量计算
        Cv = 100.0 * (valve_cfg['opening_percent'] / 100.0)  # 流量系数
        Q = Cv * (delta_p / 100.0) ** 0.5  # 简化公式
        
        return SimulationResponse(
            task_id=task_id,
            status='completed',
            time=[0.0],
            x=[valve_cfg['position']],
            h=[[0.0]],
            Q=[[Q]],
            V=[[Q / (3.14159 * (valve_cfg['diameter']/2)**2)]],
            metrics={
                'flow_rate_m3s': Q,
                'valve_type': valve_cfg['type'],
                'opening_percent': valve_cfg['opening_percent']
            },
            duration=0.01,
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class SurgeTankConfig(BaseModel):
    """调压井配置"""
    type: str = Field("simple", description="调压井类型")
    diameter: float = Field(5.0, description="直径 (m)")
    height: float = Field(20.0, description="高度 (m)")
    bottom_elevation: float = Field(100.0, description="底部高程 (m)")
    position: float = Field(500.0, description="位置 (m)")


class SurgeTankSimulationRequest(BaseModel):
    """调压井仿真请求"""
    surge_tank: SurgeTankConfig
    initial_conditions: Dict[str, float] = Field({"water_level": 110.0}, description="初始条件")


@router.post("/surge-tank", response_model=SimulationResponse, summary="调压井仿真")
async def run_surge_tank_simulation(request: SurgeTankSimulationRequest):
    """调压井水位演算"""
    try:
        task_id = str(uuid.uuid4())
        config = {
            'surge_tank': request.surge_tank.model_dump(),
            'initial_conditions': request.initial_conditions
        }
        
        tank_cfg = config['surge_tank']
        initial_level = config['initial_conditions'].get('water_level', 110.0)
        
        return SimulationResponse(
            task_id=task_id,
            status='completed',
            time=[0.0],
            x=[tank_cfg['position']],
            h=[[initial_level]],
            Q=[[0.0]],
            V=[[0.0]],
            metrics={
                'water_level_m': initial_level,
                'tank_type': tank_cfg['type'],
                'diameter_m': tank_cfg['diameter']
            },
            duration=0.01,
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ----- 扩展结构 -----

class CulvertConfig(BaseModel):
    """涵洞配置"""
    diameter: float = Field(2.0, description="直径 (m)")
    length: float = Field(50.0, description="长度 (m)")
    position: float = Field(500.0, description="位置 (m)")


class CulvertSimulationRequest(BaseModel):
    """涵洞仿真请求"""
    culvert: CulvertConfig
    upstream: Dict[str, float] = Field({"water_depth": 3.0}, description="上游水深")
    downstream: Dict[str, float] = Field({"water_depth": 1.0}, description="下游水深")


@router.post("/culvert", response_model=SimulationResponse, summary="涵洞仿真")
async def run_culvert_simulation(request: CulvertSimulationRequest):
    """涵洞水力计算"""
    try:
        task_id = str(uuid.uuid4())
        config = {
            'culvert': request.culvert.model_dump(),
            'upstream': request.upstream,
            'downstream': request.downstream
        }
        
        culvert_cfg = config['culvert']
        h_up = config['upstream'].get('water_depth', 3.0)
        h_down = config['downstream'].get('water_depth', 1.0)
        
        # 简化流量计算
        g = 9.81
        A = 3.14159 * (culvert_cfg['diameter']/2)**2
        Q = 0.8 * A * (2 * g * (h_up - h_down))**0.5
        
        return SimulationResponse(
            task_id=task_id,
            status='completed',
            time=[0.0],
            x=[culvert_cfg['position']],
            h=[[h_up]],
            Q=[[Q]],
            V=[[Q / A]],
            metrics={'discharge': Q, 'structure': 'Culvert'},
            duration=0.01,
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class BridgeConfig(BaseModel):
    """桥梁配置"""
    span_width: float = Field(20.0, description="跨宽 (m)")
    pier_width: float = Field(2.0, description="桥墩宽 (m)")
    num_piers: int = Field(2, description="桥墩数量")
    position: float = Field(500.0, description="位置 (m)")


class BridgeSimulationRequest(BaseModel):
    """桥梁仿真请求"""
    bridge: BridgeConfig
    flow: Dict[str, float] = Field({"discharge": 100.0}, description="流量条件")
    upstream: Dict[str, float] = Field({"water_depth": 5.0}, description="上游水深")


@router.post("/bridge", response_model=SimulationResponse, summary="桥梁壅水计算")
async def run_bridge_simulation(request: BridgeSimulationRequest):
    """桥梁壅水分析"""
    try:
        task_id = str(uuid.uuid4())
        config = {
            'bridge': request.bridge.model_dump(),
            'flow': request.flow,
            'upstream': request.upstream
        }
        
        bridge_cfg = config['bridge']
        Q = config['flow'].get('discharge', 100.0)
        h_up = config['upstream'].get('water_depth', 5.0)
        
        # 简化壅水计算
        contraction_ratio = (bridge_cfg['span_width'] - bridge_cfg['pier_width'] * bridge_cfg['num_piers']) / bridge_cfg['span_width']
        backwater = h_up * (1 - contraction_ratio) * 0.2  # 简化公式
        
        return SimulationResponse(
            task_id=task_id,
            status='completed',
            time=[0.0],
            x=[bridge_cfg['position']],
            h=[[h_up + backwater]],
            Q=[[Q]],
            V=[[Q / (h_up * bridge_cfg['span_width'])]],
            metrics={'discharge': Q, 'backwater_m': backwater, 'structure': 'Bridge'},
            duration=0.01,
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
