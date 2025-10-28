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

__all__ = [
    'Culvert',
    'CulvertGeometry',
    'create_circular_culvert',
    'create_rectangular_culvert',
]
