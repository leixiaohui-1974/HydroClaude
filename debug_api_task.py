#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
调试API任务执行
模拟后台任务执行来找到编码问题的源头
"""

import sys
import os
import io

# 添加路径
sys.path.insert(0, 'web/backend/api_gateway')
sys.path.insert(0, '.')

def run_simulation_debug():
    """调试版本的仿真任务"""
    print("[DEBUG] Starting debug simulation task...")
    
    # 屏蔽stdout/stderr
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    
    if sys.platform == 'win32':
        sys.stdout = io.StringIO()
        sys.stderr = io.StringIO()
    
    try:
        print("[DEBUG] After屏蔽stdout/stderr")
        
        # 模拟任务
        config = {
            "width": 10.0,
            "length": 1000.0,
            "n_cells": 100,
            "manning_n": 0.025,
            "slope": 0.001,
            "t_end": 10.0,
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
        
        # 恢复输出以便看到调试信息
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        print("[DEBUG] Importing engine...")
        
        # 再次屏蔽
        if sys.platform == 'win32':
            sys.stdout = io.StringIO()
            sys.stderr = io.StringIO()
        
        from core.hydraulic_engine import HydraulicEngine
        
        # 恢复
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        print("[DEBUG] Creating engine...")
        
        # 再次屏蔽
        if sys.platform == 'win32':
            sys.stdout = io.StringIO()
            sys.stderr = io.StringIO()
        
        engine = HydraulicEngine()
        
        # 恢复
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        print("[DEBUG] Running simulation...")
        
        # 再次屏蔽
        if sys.platform == 'win32':
            sys.stdout = io.StringIO()
            sys.stderr = io.StringIO()
        
        result = engine.run_canal_simulation("test-001", config)
        
        # 恢复
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        print(f"[DEBUG] Result status: {result.status}")
        
        return True
        
    except Exception as e:
        # 恢复以便看到错误
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        print(f"[ERROR] Exception occurred: {type(e).__name__}")
        print(f"[ERROR] Exception message: {repr(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr


if __name__ == "__main__":
    print("="*60)
    print(" Debug API Task Execution")
    print("="*60)
    
    success = run_simulation_debug()
    
    print("\n" + "="*60)
    if success:
        print(" Debug PASSED!")
    else:
        print(" Debug FAILED - Check error above")
    print("="*60)






