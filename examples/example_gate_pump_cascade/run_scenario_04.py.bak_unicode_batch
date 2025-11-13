#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""工况4: 闸门开度调控"""

import sys
import os
exec(open(os.path.join(os.path.dirname(__file__), 'run_scenario.py')).read())

# 工况4: 闸门开度阶跃
scenario4 = {
    'name': 'Scenario 04: Gate Opening Control',
    'description': '''**工况类型**: 闸门调控

**初始状态**: gate1_opening = 5.0 m
**扰动**: t=300s, opening → 2.0 m (关小60%)
**观测**: 闸门上游水位上升、流量减小''',
    'Q_initial': 30.0,
    'Q_upstream_func': lambda t: 30.0,
    'gate1_opening_func': lambda t: 2.0 if t >= 300 else 5.0
}

run_scenario("scenario_04_gate_opening_control", scenario4)
