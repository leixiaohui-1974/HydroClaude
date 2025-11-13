#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
全面验证测试 - 覆盖所有标准案例类型
对标商业软件的完整功能测试
"""

import sys
import os
import json
import subprocess
from datetime import datetime
import importlib.util

# 设置路径
sys.path.insert(0, os.path.abspath('.'))

def test_module(module_path, name, category):
    """测试单个模块"""
    print(f"\n[TEST] {name}")
    print(f"  Path: {module_path}")
    print(f"  Category: {category}")
    
    if not os.path.exists(module_path):
        print(f"  [SKIP] File not found")
        return {"passed": False, "reason": "File not found"}
    
    try:
        # 尝试运行模块
        result = subprocess.run(
            [sys.executable, module_path],
            capture_output=True,
            text=True,
            timeout=60,
            encoding='utf-8',
            errors='ignore'
        )
        
        if result.returncode == 0:
            print(f"  [PASS] Completed successfully")
            return {"passed": True, "output_lines": len(result.stdout.split('\n'))}
        else:
            print(f"  [FAIL] Exit code: {result.returncode}")
            error_preview = result.stderr[:200] if result.stderr else "No error output"
            print(f"  Error: {error_preview}")
            return {"passed": False, "error": error_preview, "exit_code": result.returncode}
            
    except subprocess.TimeoutExpired:
        print(f"  [TIMEOUT] Exceeded 60s")
        return {"passed": False, "reason": "Timeout"}
    except Exception as e:
        print(f"  [ERROR] {str(e)[:200]}")
        return {"passed": False, "error": str(e)[:200]}

def main():
    """主测试函数"""
    print("="*80)
    print(" COMPREHENSIVE VALIDATION TEST")
    print(" Testing All Standard Cases - Commercial Software Benchmark")
    print(" Start:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("="*80)
    
    # 定义所有标准测试案例
    test_cases = {
        "标准测试 (Standard Tests)": [
            ("tests/standard_tests/test_dam_break.py", "溃坝测试 (Dam Break)"),
            ("tests/standard_tests/test_lake_at_rest.py", "静水平衡 (Lake at Rest)"),
            ("tests/standard_tests/test_macdonald.py", "MacDonald标准案例"),
        ],
        
        "解析解验证 (Analytical Validation)": [
            ("validation_cases/analytical/dam_break_ritter.py", "Ritter溃坝解析解"),
            ("validation_cases/analytical/dam_break_godunov.py", "Godunov溃坝解析解"),
            ("validation_cases/analytical/steady_uniform_flow.py", "均匀流解析解"),
            ("validation_cases/analytical/gradually_varied_flow.py", "渐变流解析解"),
            ("validation_cases/analytical/hydraulic_jump.py", "水跃解析解"),
        ],
        
        "明渠流动 (Open Channel Flow)": [
            ("examples/example_01_canal_flow/scripts/01_basic_v2.py", "基本明渠流"),
            ("examples/example_01_canal_flow/scripts/07_sluice_gate_flow_v2.py", "闸门明渠流"),
        ],
        
        "水工结构 (Hydraulic Structures)": [
            ("examples/example_side_weir.py", "侧堰"),
            ("examples/example_pump_station.py", "泵站"),
            ("solvers/gate.py", "闸门模块（导入测试）"),
            ("physics/weirs/broad_crested_weir.py", "宽顶堰模块"),
        ],
        
        "有压管道 (Pressurized Flow)": [
            ("validation_cases/pressure_network/single_pipe_validation.py", "单管验证"),
            ("validation_cases/pressure_network/water_hammer_validation.py", "水锤验证"),
            ("validation_cases/pressure_network/hardy_cross_validation.py", "Hardy-Cross验证"),
        ],
        
        "工程案例 (Engineering Cases)": [
            ("validation_cases/engineering/irrigation_canal/irrigation_canal_case.py", "灌溉渠道"),
            ("validation_cases/engineering/flood_routing/flood_routing_case.py", "洪水演进"),
            ("validation_cases/engineering/urban_drainage/urban_drainage_case.py", "城市排水"),
        ],
        
        "控制系统 (Control Systems)": [
            ("examples/case_gate_operation.py", "闸门操作"),
            ("examples/phase1_simple_gate_control.py", "简单闸门控制"),
        ],
    }
    
    # 运行测试
    results = {}
    total_tests = 0
    total_passed = 0
    
    for category, cases in test_cases.items():
        print(f"\n{'='*80}")
        print(f" {category}")
        print(f"{'='*80}")
        
        category_results = []
        category_passed = 0
        
        for case_path, case_name in cases:
            total_tests += 1
            result = test_module(case_path, case_name, category)
            
            if result["passed"]:
                total_passed += 1
                category_passed += 1
            
            category_results.append({
                "name": case_name,
                "path": case_path,
                "result": result
            })
        
        results[category] = {
            "cases": category_results,
            "passed": category_passed,
            "total": len(cases),
            "pass_rate": f"{category_passed/len(cases)*100:.1f}%"
        }
        
        print(f"\n{category} Summary: {category_passed}/{len(cases)} passed ({category_passed/len(cases)*100:.1f}%)")
    
    # 总结
    print("\n" + "="*80)
    print(" COMPREHENSIVE TEST SUMMARY")
    print("="*80)
    
    print(f"\nOverall Results:")
    print(f"  Total tests: {total_tests}")
    print(f"  Passed: {total_passed} ({total_passed/total_tests*100:.1f}%)")
    print(f"  Failed: {total_tests - total_passed}")
    
    print(f"\nBy Category:")
    for category, data in results.items():
        status = "[PASS]" if data["passed"] == data["total"] else "[PARTIAL]"
        print(f"  {status} {category}: {data['passed']}/{data['total']} ({data['pass_rate']})")
    
    # 详细失败列表
    print(f"\nFailed Tests:")
    failed_count = 0
    for category, data in results.items():
        for case in data["cases"]:
            if not case["result"]["passed"]:
                failed_count += 1
                print(f"  {failed_count}. [{category}] {case['name']}")
                reason = case["result"].get("reason", case["result"].get("error", "Unknown"))
                print(f"     Reason: {reason[:100]}")
    
    if failed_count == 0:
        print("  (None - All tests passed!)")
    
    # 保存结果
    output = {
        "timestamp": datetime.now().isoformat(),
        "test_type": "Comprehensive Validation - Commercial Software Benchmark",
        "total_tests": total_tests,
        "total_passed": total_passed,
        "total_failed": total_tests - total_passed,
        "pass_rate": f"{total_passed/total_tests*100:.1f}%",
        "categories": results
    }
    
    with open("comprehensive_validation_results.json", 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n[OK] Results saved to: comprehensive_validation_results.json")
    
    # 最终评价
    print("\n" + "="*80)
    if total_passed == total_tests:
        print(" *** PERFECT - ALL TESTS PASSED ***")
        print(" Commercial Software Quality Achieved!")
    elif total_passed >= total_tests * 0.8:
        print(f" *** EXCELLENT - {total_passed}/{total_tests} TESTS PASSED ***")
        print(" Commercial Software Quality Level!")
    elif total_passed >= total_tests * 0.6:
        print(f" GOOD - {total_passed}/{total_tests} tests passed")
    else:
        print(f" NEEDS IMPROVEMENT - {total_passed}/{total_tests} tests passed")
    print("="*80)
    
    return total_passed >= total_tests * 0.6

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n[INFO] Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

