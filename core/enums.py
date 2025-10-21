from enum import Enum

class ComponentType(Enum):
    """组件类型"""
    RESERVOIR = "reservoir"
    CANAL = "canal"
    PIPE = "pipe"
    PUMP = "pump"
    GATE = "gate"
    VALVE = "valve"
    TANK = "tank"

class SensorFault(Enum):
    """传感器故障类型"""
    NORMAL = "normal"
    BIAS = "bias"
    DRIFT = "drift"
    NOISE = "noise"
    STUCK = "stuck"
    INTERMITTENT = "intermittent"
    COMPLETE_FAILURE = "complete_failure"

class ActuatorFault(Enum):
    """执行器故障类型"""
    NORMAL = "normal"
    DELAY = "delay"
    SATURATION = "saturation"
    STUCK = "stuck"
    SLOW_RESPONSE = "slow_response"
    DEAD_ZONE = "dead_zone"
    HYSTERESIS = "hysteresis"

class IntelligenceLevel(Enum):
    """智能化等级"""
    L0_MANUAL = 0
    L1_ASSISTED = 1
    L2_SUPERVISED = 2
    L3_AUTONOMOUS = 3
    L4_PREDICTIVE = 4
    L5_COGNITIVE = 5

class NodeType(Enum):
    """节点类型"""
    SOURCE = "source"
    SINK = "sink"
    JUNCTION = "junction"
    BRANCH = "branch"
    MERGE = "merge"
    COMPLEX = "complex"
