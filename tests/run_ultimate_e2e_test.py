#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HydroClaude 终极端到端测试运行脚本

运行方式:
  python tests/run_ultimate_e2e_test.py           # 运行全部测试
  python tests/run_ultimate_e2e_test.py --quick   # 快速测试（仅后端）
  python tests/run_ultimate_e2e_test.py --backend # 仅后端测试
  python tests/run_ultimate_e2e_test.py --frontend # 仅前端测试
  python tests/run_ultimate_e2e_test.py --api     # 仅API测试
"""

import sys
import asyncio
from pathlib import Path

# 添加项目根目录
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def print_banner():
    """打印横幅"""
    print("""
========================================================================
    HydroClaude Ultimate E2E Test Suite v2.0
========================================================================

    Coverage:
    [+] Backend Solvers: HydrostaticCanalSolver, GodunvFVMSolver, Hardy-Cross
    [+] Hydraulic Structures: 14 types (gates/weirs/pumps/turbines/valves/bridges...)
    [+] API Endpoints: structures/simulations/analysis/test-cases
    [+] Dual Frontend: webapp (5173) + web/frontend (3000)
    [+] Commercial Benchmarks: HEC-RAS, MIKE11, EPANET, HAMMER
    [+] Standard Cases: 111 test scenarios

========================================================================
""")

async def run_quick_test():
    """快速测试（仅后端核心功能）"""
    from tests.e2e.ultimate_e2e_test import UltimateE2ETester
    
    tester = UltimateE2ETester()
    print("\n[*] Running Quick Test (Backend Core Only)...")
    results = tester.test_backend_solvers()
    
    passed = sum(1 for r in results if r.status == "passed")
    failed = sum(1 for r in results if r.status == "failed")
    
    print(f"\n[RESULTS] Quick Test: Passed {passed}/{len(results)}, Failed {failed}")
    
    for r in results:
        icon = "[PASS]" if r.status == "passed" else "[FAIL]" if r.status == "failed" else "[SKIP]"
        print(f"   {icon} {r.name}: {r.status} ({r.duration:.2f}s)")
        if r.error:
            print(f"        Error: {r.error[:100]}...")

async def run_backend_test():
    """后端测试"""
    from tests.e2e.ultimate_e2e_test import UltimateE2ETester
    
    tester = UltimateE2ETester()
    print("\n[*] Running Backend Tests...")
    
    all_results = []
    
    # 求解器测试
    print("\n[1/3] Solver Tests...")
    all_results.extend(tester.test_backend_solvers())
    
    # 商业对标测试
    print("\n[2/3] Commercial Benchmark Tests...")
    all_results.extend(tester.test_commercial_benchmarks())
    
    # 标准案例测试
    print("\n[3/3] Standard Case Tests...")
    all_results.extend(tester.test_standard_cases())
    
    # 打印结果
    print_results_summary(all_results)

async def run_api_test():
    """API测试"""
    from tests.e2e.ultimate_e2e_test import UltimateE2ETester
    
    tester = UltimateE2ETester()
    print("\n[*] Running API Tests...")
    results = tester.test_api_endpoints()
    print_results_summary(results)

async def run_frontend_test():
    """前端测试"""
    from tests.e2e.ultimate_e2e_test import UltimateE2ETester
    
    tester = UltimateE2ETester()
    print("\n[*] Running Frontend Tests...")
    
    all_results = []
    
    # webapp前端测试
    print("\n[1/2] webapp Frontend Test (localhost:5173)...")
    webapp_results = await tester.test_frontend_browser()
    all_results.extend(webapp_results)
    
    # web/frontend测试
    print("\n[2/2] web/frontend Test (localhost:3000)...")
    web_frontend_results = await tester.test_web_frontend_browser()
    all_results.extend(web_frontend_results)
    
    print_results_summary(all_results)

async def run_full_test():
    """完整测试"""
    from tests.e2e.ultimate_e2e_test import UltimateE2ETester
    
    tester = UltimateE2ETester()
    await tester.run_all_tests()

def print_results_summary(results):
    """打印结果摘要"""
    passed = sum(1 for r in results if r.status == "passed")
    failed = sum(1 for r in results if r.status == "failed")
    skipped = sum(1 for r in results if r.status == "skipped")
    
    print("\n" + "=" * 70)
    print("TEST RESULTS SUMMARY")
    print("=" * 70)
    print(f"   Total: {len(results)}")
    print(f"   [PASS] Passed: {passed}")
    print(f"   [FAIL] Failed: {failed}")
    print(f"   [SKIP] Skipped: {skipped}")
    print("=" * 70)
    
    if failed > 0:
        print("\nFailed Tests:")
        for r in results:
            if r.status == "failed":
                print(f"   - {r.name}")
                if r.error:
                    print(f"     Error: {r.error[:80]}...")

def main():
    """主函数"""
    print_banner()
    
    # 解析命令行参数
    args = sys.argv[1:]
    
    if "--quick" in args:
        asyncio.run(run_quick_test())
    elif "--backend" in args:
        asyncio.run(run_backend_test())
    elif "--api" in args:
        asyncio.run(run_api_test())
    elif "--frontend" in args:
        asyncio.run(run_frontend_test())
    else:
        # 运行完整测试
        asyncio.run(run_full_test())

if __name__ == "__main__":
    main()

