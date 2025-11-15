#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
直接测试所有案例 - 绕过API，直接使用引擎
生成完整的测试结果，用于前端加载
"""

import sys
import os
sys.path.insert(0, '/workspace/web/backend')

from core.hydraulic_engine import HydraulicEngine
import json
from datetime import datetime

# 定义测试案例
TEST_CASES = [
    {
        "id": "tc1",
        "name": "静态均匀流",
        "config": {
            "width": 10.0, "length": 1000.0, "n_cells": 100,
            "manning_n": 0.025, "slope": 0.001, "t_end": 10.0, "dt_max": 0.1,
            "initial_conditions": {"type": "uniform", "h": 5.0, "Q": 0.0},
            "boundary_conditions": {
                "upstream": {"type": "h", "value": 5.0},
                "downstream": {"type": "h", "value": 5.0}
            }
        }
    },
    {
        "id": "tc2",
        "name": "均匀流动",
        "config": {
            "width": 10.0, "length": 1000.0, "n_cells": 100,
            "manning_n": 0.025, "slope": 0.001, "t_end": 10.0, "dt_max": 0.1,
            "initial_conditions": {"type": "uniform", "h": 5.0, "Q": 10.0},
            "boundary_conditions": {
                "upstream": {"type": "Q", "value": 10.0},
                "downstream": {"type": "h", "value": 5.0}
            }
        }
    },
    {
        "id": "tc3",
        "name": "浅层流动",
        "config": {
            "width": 10.0, "length": 1000.0, "n_cells": 100,
            "manning_n": 0.025, "slope": 0.001, "t_end": 10.0, "dt_max": 0.1,
            "initial_conditions": {"type": "uniform", "h": 1.0, "Q": 5.0},
            "boundary_conditions": {
                "upstream": {"type": "Q", "value": 5.0},
                "downstream": {"type": "h", "value": 1.0}
            }
        }
    },
    {
        "id": "tc4",
        "name": "深层流动",
        "config": {
            "width": 10.0, "length": 1000.0, "n_cells": 100,
            "manning_n": 0.025, "slope": 0.001, "t_end": 10.0, "dt_max": 0.1,
            "initial_conditions": {"type": "uniform", "h": 10.0, "Q": 20.0},
            "boundary_conditions": {
                "upstream": {"type": "Q", "value": 20.0},
                "downstream": {"type": "h", "value": 10.0}
            }
        }
    },
    {
        "id": "tc5",
        "name": "大流量",
        "config": {
            "width": 10.0, "length": 1000.0, "n_cells": 100,
            "manning_n": 0.025, "slope": 0.001, "t_end": 10.0, "dt_max": 0.1,
            "initial_conditions": {"type": "uniform", "h": 5.0, "Q": 50.0},
            "boundary_conditions": {
                "upstream": {"type": "Q", "value": 50.0},
                "downstream": {"type": "h", "value": 5.0}
            }
        }
    },
]

def main():
    print("="*80)
    print("  HydroClaude Web - 完整测试所有案例")
    print("="*80)
    print(f"\n开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"测试案例数: {len(TEST_CASES)}")
    
    engine = HydraulicEngine()
    results = []
    passed = 0
    failed = 0
    
    for i, test_case in enumerate(TEST_CASES, 1):
        print(f"\n[{i}/{len(TEST_CASES)}] {test_case['name']}...")
        
        try:
            result = engine.run_canal_simulation(test_case['name'], test_case['config'])
            
            if result.status == 'completed':
                error = result.metrics['mass_conservation_error']
                converged = result.metrics['converged']
                
                test_result = {
                    "id": test_case['id'],
                    "name": test_case['name'],
                    "status": "success",
                    "metrics": {
                        "mass_error": error,
                        "converged": converged,
                        "mean_depth": result.metrics['mean_depth_final'],
                        "max_velocity": result.metrics['max_velocity'],
                        "duration": result.duration
                    }
                }
                
                if converged and error < 0.01:
                    print(f"  ✅ 通过 - 误差: {error:.6f}%, 收敛: {converged}")
                    passed += 1
                else:
                    print(f"  ⚠️  完成但不达标 - 误差: {error:.6f}%, 收敛: {converged}")
                    failed += 1
            else:
                test_result = {
                    "id": test_case['id'],
                    "name": test_case['name'],
                    "status": "failed",
                    "error": str(result.error)
                }
                print(f"  ❌ 失败: {result.error}")
                failed += 1
                
            results.append(test_result)
            
        except Exception as e:
            print(f"  ❌ 异常: {e}")
            results.append({
                "id": test_case['id'],
                "name": test_case['name'],
                "status": "error",
                "error": str(e)
            })
            failed += 1
    
    # 保存结果
    output_file = '/workspace/web/测试结果_完整.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total": len(TEST_CASES),
            "passed": passed,
            "failed": failed,
            "success_rate": passed / len(TEST_CASES) * 100,
            "results": results
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*80}")
    print(f"测试完成!")
    print(f"  总数: {len(TEST_CASES)}")
    print(f"  通过: {passed}")
    print(f"  失败: {failed}")
    print(f"  成功率: {passed/len(TEST_CASES)*100:.1f}%")
    print(f"\n结果已保存到: {output_file}")
    print("="*80)
    
    return 0 if failed == 0 else 1

if __name__ == '__main__':
    sys.exit(main())
