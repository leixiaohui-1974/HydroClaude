#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""工况5: 极端流量测试"""

import sys
import os
exec(open(os.path.join(os.path.dirname(__file__), 'run_scenario.py')).read())

# 工况5: 极端流量
scenario5 = {
    'name': 'Scenario 05: Extreme Flow Test',
    'description': '''**工况类型**: 极端流量扰动

**初始状态**: Q = 30 m³/s
**扰动**: t=300s, Q → 60 m³/s (+100%)
**观测**: 泵站严重超载、数值稳定性''',
    'Q_initial': 30.0,
    'Q_upstream_func': lambda t: 60.0 if t >= 300 else 30.0
}

run_scenario("scenario_05_extreme_flow", scenario5)
