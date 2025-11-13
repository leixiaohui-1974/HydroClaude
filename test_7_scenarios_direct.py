#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
直接测试7个场景 - 绕过Web API
"""

import sys
import os
import io
import json
from datetime import datetime

# 设置UTF-8
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 添加项目路径
project_root = os.path.abspath('.')
sys.path.insert(0, project_root)

from web.backend.core.hydraulic_engine import HydraulicEngine

# 7个测试场景
SCENARIOS = [
    {
        "name": "场景1: 基础矩形明渠流",
        "config": {
            "width": 10.0, "length": 1000.0, "n_cells": 100,
            "manning_n": 0.025, "slope": 0.001, "t_end": 100.0,
            "dt_max": 0.5, "output_interval": 10.0, "cfl": 0.5,
            "order": 2, "use_numba": True,
            "initial_conditions": {"type": "uniform", "h": 3.0, "Q": 100.0},
            "boundary_conditions": {
                "upstream": {"type": "Q", "value": 100.0},
                "downstream": {"type": "h", "value": 3.0}
            }
        }
    },
    {
        "name": "场景2: 陡坡明渠流",
        "config": {
            "width": 8.0, "length": 500.0, "n_cells": 100,
            "manning_n": 0.03, "slope": 0.01, "t_end": 50.0,
            "dt_max": 0.2, "output_interval": 5.0, "cfl": 0.5,
            "order": 2, "use_numba": True,
            "initial_conditions": {"type": "uniform", "h": 2.0, "Q": 50.0},
            "boundary_conditions": {
                "upstream": {"type": "Q", "value": 50.0},
                "downstream": {"type": "h", "value": 2.0}
            }
        }
    },
    {
        "name": "场景3: 缓坡宽渠道",
        "config": {
            "width": 20.0, "length": 1500.0, "n_cells": 150,
            "manning_n": 0.02, "slope": 0.0005, "t_end": 150.0,
            "dt_max": 0.5, "output_interval": 15.0, "cfl": 0.5,
            "order": 2, "use_numba": True,
            "initial_conditions": {"type": "uniform", "h": 4.0, "Q": 200.0},
            "boundary_conditions": {
                "upstream": {"type": "Q", "value": 200.0},
                "downstream": {"type": "h", "value": 4.0}
            }
        }
    },
    {
        "name": "场景4: 小流量窄渠道",
        "config": {
            "width": 3.0, "length": 300.0, "n_cells": 60,
            "manning_n": 0.015, "slope": 0.002, "t_end": 50.0,
            "dt_max": 0.3, "output_interval": 5.0, "cfl": 0.5,
            "order": 2, "use_numba": True,
            "initial_conditions": {"type": "uniform", "h": 1.5, "Q": 10.0},
            "boundary_conditions": {
                "upstream": {"type": "Q", "value": 10.0},
                "downstream": {"type": "h", "value": 1.5}
            }
        }
    },
    {
        "name": "场景5: 大流量宽渠道",
        "config": {
            "width": 30.0, "length": 2000.0, "n_cells": 200,
            "manning_n": 0.028, "slope": 0.0008, "t_end": 200.0,
            "dt_max": 0.5, "output_interval": 20.0, "cfl": 0.5,
            "order": 2, "use_numba": True,
            "initial_conditions": {"type": "uniform", "h": 5.0, "Q": 500.0},
            "boundary_conditions": {
                "upstream": {"type": "Q", "value": 500.0},
                "downstream": {"type": "h", "value": 5.0}
            }
        }
    },
    {
        "name": "场景6: 极缓坡流动",
        "config": {
            "width": 12.0, "length": 800.0, "n_cells": 100,
            "manning_n": 0.022, "slope": 0.0001, "t_end": 100.0,
            "dt_max": 0.5, "output_interval": 10.0, "cfl": 0.5,
            "order": 2, "use_numba": True,
            "initial_conditions": {"type": "uniform", "h": 3.5, "Q": 80.0},
            "boundary_conditions": {
                "upstream": {"type": "Q", "value": 80.0},
                "downstream": {"type": "h", "value": 3.5}
            }
        }
    },
    {
        "name": "场景7: 高糙率渠道",
        "config": {
            "width": 15.0, "length": 1200.0, "n_cells": 120,
            "manning_n": 0.04, "slope": 0.003, "t_end": 120.0,
            "dt_max": 0.5, "output_interval": 12.0, "cfl": 0.5,
            "order": 2, "use_numba": True,
            "initial_conditions": {"type": "uniform", "h": 2.5, "Q": 150.0},
            "boundary_conditions": {
                "upstream": {"type": "Q", "value": 150.0},
                "downstream": {"type": "h", "value": 2.5}
            }
        }
    }
]

def main():
    print("="*60)
    print(" Direct Engine Test - 7 Scenarios")
    print(" Time:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("="*60)
    
    engine = HydraulicEngine()
    results = []
    passed = 0
    failed = 0
    
    for i, scenario in enumerate(SCENARIOS, 1):
        print(f"\n[{i}/7] {scenario['name']}")
        print(f"    Params: width={scenario['config']['width']}m, "
              f"length={scenario['config']['length']}m, "
              f"cells={scenario['config']['n_cells']}")
        
        try:
            result = engine.run_canal_simulation(f"test-{i:02d}", scenario['config'])
            
            if result.status == 'completed':
                print(f"    [OK] Duration: {result.duration:.2f}s")
                print(f"    Max depth: {result.metrics['max_depth']:.3f}m")
                print(f"    Max velocity: {result.metrics['max_velocity']:.3f}m/s")
                print(f"    Converged: {result.metrics['converged']}")
                print(f"    Mass error: {result.metrics['mass_conservation_error']:.6e}")
                passed += 1
                results.append({
                    "name": scenario['name'],
                    "status": "passed",
                    "duration": result.duration,
                    "metrics": result.metrics
                })
            else:
                print(f"    [!] Failed: {result.error}")
                failed += 1
                results.append({
                    "name": scenario['name'],
                    "status": "failed",
                    "error": result.error
                })
        
        except Exception as e:
            print(f"    [X] Exception: {e}")
            failed += 1
            results.append({
                "name": scenario['name'],
                "status": "failed",
                "error": str(e)
            })
    
    # Summary
    print("\n" + "="*60)
    print(" Test Summary")
    print("="*60)
    print(f"Total: {len(SCENARIOS)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Success Rate: {passed/len(SCENARIOS)*100:.1f}%")
    
    # Save results
    output = {
        "test_time": datetime.now().isoformat(),
        "total": len(SCENARIOS),
        "passed": passed,
        "failed": failed,
        "success_rate": passed/len(SCENARIOS)*100,
        "scenarios": results
    }
    
    with open("direct_engine_test_results.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\n[OK] Results saved to: direct_engine_test_results.json")
    print("="*60)
    
    return passed == len(SCENARIOS)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)






