"""
Water System Structures Module
水工结构模块

对标商业软件（HEC-RAS、MIKE、InfoWorks）的完整水工结构库

Author: HydroClaude Team
Date: 2025-11-15
"""

# 基础结构
from .pump_station import PumpStation, PumpType, ControlMode, PumpCurve, PumpControlRule, STANDARD_PUMP_CURVES
from .advanced_gates import (
    SluiceGate, RadialGate, VerticalLiftGate, RollerGate, FlapGate,
    GateType, FlowRegime
)
from .advanced_weirs import (
    SharpCrestedWeir, BroadCrestedWeir, VNotchWeir, 
    RectangularWeir, TrapezoidalWeir, OgeeWeir,
    WeirType
)

# 扩展结构
from .culvert import Culvert, CulvertType, CulvertFlowType
from .side_weir import SideWeir
from .storage import Storage
from .drop_structure import DropStructure
from .bridge import Bridge

__all__ = [
    # 泵站
    'PumpStation',
    'PumpType',
    'ControlMode',
    'PumpCurve',
    'PumpControlRule',
    'STANDARD_PUMP_CURVES',
    
    # 闸门
    'SluiceGate',
    'RadialGate',
    'VerticalLiftGate',
    'RollerGate',
    'FlapGate',
    'GateType',
    'FlowRegime',
    
    # 堰
    'SharpCrestedWeir',
    'BroadCrestedWeir',
    'VNotchWeir',
    'RectangularWeir',
    'TrapezoidalWeir',
    'OgeeWeir',
    'WeirType',
    
    # 扩展结构
    'Culvert',
    'CulvertType',
    'CulvertFlowType',
    'SideWeir',
    'Storage',
    'DropStructure',
    'Bridge',
]

# 版本信息
__version__ = '2.0.0'
__author__ = 'HydroClaude Team'

# 结构统计
STRUCTURE_TYPES = {
    'pump_station': 1,
    'gates': 5,
    'weirs': 6,
    'culvert': 1,
    'side_weir': 1,
    'storage': 1,
    'drop_structure': 1,
    'bridge': 1
}

TOTAL_STRUCTURES = sum(STRUCTURE_TYPES.values())  # 17种

# Print statement removed to avoid UnicodeEncodeError in Windows console
