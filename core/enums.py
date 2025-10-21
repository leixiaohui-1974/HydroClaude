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

class BoundaryType(Enum):
    """边界类型"""
    UPSTREAM = "upstream"      # 上游边界
    DOWNSTREAM = "downstream"  # 下游边界
    INTERNAL = "internal"      # 内边界
