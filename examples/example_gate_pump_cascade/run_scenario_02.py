#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""工况2: 上游中等流量阶跃"""

import os

# 导入run_scenario模块
exec(open(os.path.join(os.path.dirname(__file__), 'run_scenario.py')).read())

# 工况2: 中等流量阶跃
scenario2 = {
    'name': 'Scenario 02: Medium Flow Step',
    'description': '''**工况类型**: 上游边界扰动（中等幅度）

**初始状态**: Q = 30 m³/s
**扰动**: t=300s, Q → 42 m³/s (+40%)
**观测**: 泵站在能力范围内的响应、工作点求解''',
    'Q_initial': 30.0,
    'Q_upstream_func': lambda t: 42.0 if t >= 300 else 30.0
}

run_scenario("scenario_02_upstream_flow_medium", scenario2)
