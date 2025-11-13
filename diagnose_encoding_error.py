#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
诊断编码错误的源头
"""

import sys
import os
import traceback

# 添加路径
sys.path.insert(0, os.path.abspath('.'))

# 直接导入和测试
def test_engine():
    """测试引擎导入和初始化"""
    print("Step 1: Importing HydraulicEngine...")
    from web.backend.core.hydraulic_engine import HydraulicEngine
    print("  [OK] Import successful")
    
    print("\nStep 2: Creating engine instance...")
    engine = HydraulicEngine()
    print("  [OK] Engine created")
    
    print("\nStep 3: Running simple simulation...")
    config = {
        "width": 10.0,
        "length": 1000.0,
        "n_cells": 100,
        "manning_n": 0.025,
        "slope": 0.001,
        "t_end": 10.0,  # 短时间测试
        "dt_max": 0.5,
        "output_interval": 5.0,
        "cfl": 0.5,
        "order": 2,
        "use_numba": True,
        "initial_conditions": {
            "type": "uniform",
            "h": 3.0,
            "Q": 100.0
        },
        "boundary_conditions": {
            "upstream": {"type": "Q", "value": 100.0},
            "downstream": {"type": "h", "value": 3.0}
        }
    }
    
    try:
        result = engine.run_canal_simulation("test-001", config)
        print(f"  [OK] Simulation completed: {result.status}")
        print(f"  Duration: {result.duration:.2f}s")
        return True
    except Exception as e:
        print(f"  [ERROR] Simulation failed: {e}")
        print("\nFull traceback:")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("="*60)
    print(" Encoding Error Diagnosis")
    print("="*60)
    
    success = test_engine()
    
    print("\n" + "="*60)
    if success:
        print(" Test PASSED - No encoding errors!")
    else:
        print(" Test FAILED - Check traceback above")
    print("="*60)






