# -*- coding: utf-8 -*-
"""
models/__init__.py

这个文件使 'models' 目录成为一个Python包。
它还提供了一个方便的接口来访问各种物理模型的工厂函数。
"""

from .gate import get_gate_model
from .pump import get_pump_model
from .weir import get_weir_model
from .turbine import get_turbine_model
from .valve import get_valve_model

__all__ = [
    "get_gate_model",
    "get_pump_model",
    "get_weir_model",
    "get_turbine_model",
    "get_valve_model"
]
