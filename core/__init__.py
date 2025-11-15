#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HydroClaude Core Modules
核心模块包

包含:
- config_parser: 配置文件解析器
- simulation_engine: 仿真引擎
- output_manager: 输出管理器
"""

__version__ = "1.0.0"
__author__ = "HydroClaude Development Team"

from .config_parser import ConfigParser
from .simulation_engine import SimulationEngine
from .output_manager import OutputManager

__all__ = [
    'ConfigParser',
    'SimulationEngine',
    'OutputManager'
]
