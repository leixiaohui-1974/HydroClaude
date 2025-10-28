"""
Hydraulic Structures Module

This module contains various hydraulic structure models for
open channel and pressurized flow systems.
"""

from .culvert import (
    Culvert,
    CulvertGeometry,
    create_circular_culvert,
    create_rectangular_culvert
)

from .bridge import (
    Bridge,
    BridgeGeometry,
    Pier,
    create_simple_bridge,
    create_rectangular_pier_bridge
)

__all__ = [
    # Culvert
    'Culvert',
    'CulvertGeometry',
    'create_circular_culvert',
    'create_rectangular_culvert',
    # Bridge
    'Bridge',
    'BridgeGeometry',
    'Pier',
    'create_simple_bridge',
    'create_rectangular_pier_bridge',
]
