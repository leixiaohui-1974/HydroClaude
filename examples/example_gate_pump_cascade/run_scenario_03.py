#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""工况3: 下游水位阶跃"""
import sys
import warnings
warnings.filterwarnings("ignore")
import os

# ========== 路径设置 ==========
script_path = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(script_path))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


import sys
import os
exec(open(os.path.join(os.path.dirname(__file__), 'run_scenario.py'), encoding='utf-8').read())

# 工况3: 下游水位阶跃
scenario3 = {
    'name': 'Scenario 03: Downstream Level Step',
    'description': '''**工况类型**: 下游边界扰动

**初始状态**: h_downstream = 2.0 m
**扰动**: t=300s, h -> 3.5 m (+1.5m)
**观测**: 回水效应、流量变化、逆向传播''',
    'Q_initial': 30.0,
    'Q_upstream_func': lambda t: 30.0,
    'h_downstream_func': lambda t: 3.5 if t >= 300 else 2.0
}

run_scenario("scenario_03_downstream_level_step", scenario3)
