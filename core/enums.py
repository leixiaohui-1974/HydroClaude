from enum import Enum

class ComponentType(Enum):
    """组件类型枚举"""
    RESERVOIR = "reservoir"
    CANAL = "canal"
    PIPE = "pipe"
    SETTLING_BASIN = "settling_basin"
    STORAGE_TANK = "storage_tank"
    GATE = "gate"
    VALVE = "valve"
    PUMP = "pump"
    DISTRIBUTION = "distribution_point"
