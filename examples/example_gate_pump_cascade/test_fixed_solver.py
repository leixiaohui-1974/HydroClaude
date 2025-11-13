#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试修复后的求解器
"""

import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# 导入run_scenario模块
exec(open(os.path.join(os.path.dirname(__file__), 'run_scenario.py')).read())

# 工况2: 中等流量阶跃
scenario2 = {
    'name': 'Scenario 02: Medium Flow Step (Fixed)',
    'description': '''**工况类型**: 上游边界扰动（中等幅度）

**初始状态**: Q = 30 m^3/s
**扰动**: t=300s, Q -> 42 m^3/s (+40%)
**修复**: dt=0.5s, 稳态迭代2000次''',
    'Q_initial': 30.0,
    'Q_upstream_func': lambda t: 42.0 if t >= 300 else 30.0
}

run_scenario("scenario_02_upstream_flow_medium_fixed", scenario2)
