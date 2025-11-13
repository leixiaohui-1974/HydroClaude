#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""工况1: 上游大流量阶跃"""
import sys
import os

# ========== 路径设置 ==========
script_path = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(script_path))
sys.path.insert(0, project_root)


import os

# 导入run_scenario模块
exec(open(os.path.join(os.path.dirname(__file__), 'run_scenario.py'), encoding='utf-8').read())

# 工况1: 大流量阶跃
scenario1 = {
    'name': 'Scenario 01: Large Flow Step',
    'description': '''**工况类型**: 上游边界扰动（大流量）

**初始状态**: Q = 30 m^3/s
**扰动**: t=300s, Q -> 55 m^3/s (+83%)
**观测**: 泵站能力上限、水位响应、流量分配''',
    'Q_initial': 30.0,
    'Q_upstream_func': lambda t: 55.0 if t >= 300 else 30.0
}

run_scenario("scenario_01_upstream_flow_large", scenario1)
