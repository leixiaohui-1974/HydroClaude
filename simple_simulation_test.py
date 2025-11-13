#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
简化的仿真测试 - 直接调用引擎，避开logger
"""

import sys
import os

# 设置环境变量，禁用logger的emoji
os.environ['PYTHONIOENCODING'] = 'utf-8'

# 添加项目路径
project_root = os.path.abspath('.')
sys.path.insert(0, project_root)

# 重定向stdout到文件，避免控制台编码问题
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 导入引擎
from web.backend.core.hydraulic_engine import HydraulicEngine

def test_simple_simulation():
    """测试简单仿真"""
    print("\n" + "="*60)
    print(" Direct Engine Test")
    print("="*60)
    
    # 创建引擎
    engine = HydraulicEngine()
    
    # 配置
    config = {
        "width": 10.0,
        "length": 1000.0,
        "n_cells": 100,
        "manning_n": 0.025,
        "slope": 0.001,
        "t_end": 100.0,
        "dt_max": 0.5,
        "output_interval": 10.0,
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
    
    print("\n[1] Starting simulation...")
    print(f"    Config: width={config['width']}m, length={config['length']}m")
    
    try:
        # 运行仿真
        result = engine.run_canal_simulation("test-001", config)
        
        print(f"\n[2] Simulation completed")
        print(f"    Status: {result.status}")
        print(f"    Duration: {result.duration:.2f}s")
        
        if result.status == "completed":
            print(f"\n[3] Results:")
            print(f"    Time points: {len(result.time)}")
            print(f"    Space points: {len(result.x)}")
            print(f"    Max depth: {result.metrics.get('max_depth', 0):.3f}m")
            print(f"    Max velocity: {result.metrics.get('max_velocity', 0):.3f}m/s")
            print(f"    Converged: {result.metrics.get('converged', False)}")
            print(f"    Mass error: {result.metrics.get('mass_conservation_error', 0):.6e}")
            print("\n[OK] Test PASSED")
            return True
        else:
            print(f"\n[!] Simulation failed: {result.error}")
            return False
            
    except Exception as e:
        print(f"\n[X] Exception: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_simple_simulation()
    sys.exit(0 if success else 1)






