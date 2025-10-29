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

from .drop import (
    Drop,
    DropGeometry,
    create_drop_structure
)

from .flow_measurement import (
    RectangularWeir,
    RectangularWeirGeometry,
    TriangularWeir,
    TriangularWeirGeometry,
    ParshallFlume,
    ParshallFlumeGeometry,
    create_rectangular_weir,
    create_triangular_weir,
    create_parshall_flume
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
    # Drop
    'Drop',
    'DropGeometry',
    'create_drop_structure',
    # Flow Measurement
    'RectangularWeir',
    'RectangularWeirGeometry',
    'TriangularWeir',
    'TriangularWeirGeometry',
    'ParshallFlume',
    'ParshallFlumeGeometry',
    'create_rectangular_weir',
    'create_triangular_weir',
    'create_parshall_flume',
]
