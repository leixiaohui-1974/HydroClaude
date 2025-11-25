#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HydroClaude 100案例批量测试
100 Cases Batch Testing

覆盖更多参数组合和边界情况

Author: HydroClaude Test Team
Date: 2025-11-25
"""

import os
import sys
import json
import time
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
from dataclasses import dataclass, field
from itertools import product

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

BACKEND_URL = "http://localhost:8001"
OUTPUT_DIR = project_root / "tests" / "e2e" / "batch_test_output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class TestCase:
    id: str
    name: str
    category: str
    config: Dict[str, Any]


@dataclass
class TestResult:
    case_id: str
    status: str
    duration: float
    error: str = None


class FastBatchRunner:
    """快速批量测试运行器"""
    
    def __init__(self, backend_url: str = BACKEND_URL):
        self.backend_url = backend_url
        self.results: List[TestResult] = []
        
    def run_case(self, case: TestCase) -> TestResult:
        start = time.time()
        try:
            request = {
                "simulation_type": "steady",
                "canal": {
                    "length": case.config.get("L", 1000),
                    "width": case.config.get("W", 10),
                    "slope": case.config.get("S", 0.001),
                    "manning_n": case.config.get("n", 0.015),
                    "grid_nx": case.config.get("nx", 100)
                },
                "structure_type": "none",
                "structure": {"position": 0, "parameters": {}},
                "boundaries": {
                    "upstream": {"type": "Q", "value": case.config.get("Q", 50)},
                    "downstream": {"type": "h", "value": case.config.get("h_down", 3.0)}
                },
                "metadata": {"title": case.name}
            }
            
            response = requests.post(
                f"{self.backend_url}/api/structures/simulate-canal-with-structure",
                json=request, timeout=120
            )
            
            if response.status_code != 200:
                return TestResult(case.id, "error", time.time()-start, f"HTTP{response.status_code}")
            
            data = response.json()
            results = data.get("results", data)
            metrics = results.get("metrics", {})
            
            if results.get("status") == "completed" and metrics.get("converged", False):
                return TestResult(case.id, "passed", time.time()-start)
            else:
                return TestResult(case.id, "failed", time.time()-start)
                
        except Exception as e:
            return TestResult(case.id, "error", time.time()-start, str(e)[:50])
    
    def run_all(self, cases: List[TestCase]):
        print(f"\n{'='*70}")
        print(f"  HydroClaude 100案例批量测试")
        print(f"  共 {len(cases)} 个案例")
        print(f"{'='*70}\n")
        
        self.results = []
        start_time = time.time()
        
        for i, case in enumerate(cases, 1):
            result = self.run_case(case)
            self.results.append(result)
            
            # 进度条
            pct = i / len(cases) * 100
            bar = "█" * int(pct/2) + "░" * (50 - int(pct/2))
            status = "✓" if result.status == "passed" else "✗"
            print(f"\r[{bar}] {pct:5.1f}% {i}/{len(cases)} {status} {case.id}", end="", flush=True)
        
        print()
        self._print_summary(time.time() - start_time)
        self._save_report()
    
    def _print_summary(self, total_time: float):
        passed = sum(1 for r in self.results if r.status == "passed")
        failed = sum(1 for r in self.results if r.status == "failed")
        errors = sum(1 for r in self.results if r.status == "error")
        
        print(f"\n{'='*70}")
        print(f"  测试摘要")
        print(f"{'='*70}")
        print(f"  总案例: {len(self.results)}")
        print(f"  通过: {passed} ({passed/len(self.results)*100:.1f}%)")
        print(f"  失败: {failed}")
        print(f"  错误: {errors}")
        print(f"  总耗时: {total_time:.1f}s ({total_time/60:.1f}分钟)")
        print(f"  平均: {total_time/len(self.results):.2f}s/案例")
        print(f"{'='*70}")
        
        if failed > 0 or errors > 0:
            print("\n失败/错误案例:")
            for r in self.results:
                if r.status != "passed":
                    print(f"  {r.case_id}: {r.status} {r.error or ''}")
    
    def _save_report(self):
        passed = sum(1 for r in self.results if r.status == "passed")
        report = {
            "timestamp": datetime.now().isoformat(),
            "total": len(self.results),
            "passed": passed,
            "failed": sum(1 for r in self.results if r.status == "failed"),
            "errors": sum(1 for r in self.results if r.status == "error"),
            "pass_rate": f"{passed/len(self.results)*100:.1f}%",
            "results": [{"id": r.case_id, "status": r.status, "duration": r.duration, "error": r.error} 
                       for r in self.results]
        }
        
        report_file = OUTPUT_DIR / f"100cases_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\n报告: {report_file}")


def generate_100_cases() -> List[TestCase]:
    """生成100个测试案例"""
    cases = []
    idx = 0
    
    # 参数网格
    lengths = [200, 500, 1000, 2000]
    widths = [5, 10, 20]
    slopes = [0.0005, 0.001, 0.002]
    flows = [20, 50, 100]
    
    # 组合生成
    for L, W, S, Q in product(lengths, widths, slopes, flows):
        idx += 1
        h_down = max(1.5, Q / (W * 5))  # 合理的下游水深
        cases.append(TestCase(
            id=f"C{idx:03d}",
            name=f"L{L}_W{W}_S{S}_Q{Q}",
            category="参数组合",
            config={"L": L, "W": W, "S": S, "Q": Q, "h_down": h_down, "nx": min(L//5, 200)}
        ))
        
        if idx >= 100:
            break
    
    # 如果不够100个，添加特殊案例
    while idx < 100:
        idx += 1
        # 随机组合
        import random
        L = random.choice([100, 300, 800, 1500, 3000])
        W = random.choice([3, 8, 15, 30])
        S = random.choice([0.0003, 0.0008, 0.0015, 0.003])
        Q = random.choice([10, 30, 70, 150])
        h_down = max(1.0, Q / (W * 5))
        
        cases.append(TestCase(
            id=f"C{idx:03d}",
            name=f"Extra_L{L}_W{W}",
            category="额外案例",
            config={"L": L, "W": W, "S": S, "Q": Q, "h_down": h_down, "nx": min(L//5, 150)}
        ))
    
    return cases[:100]


def main():
    cases = generate_100_cases()
    runner = FastBatchRunner()
    runner.run_all(cases)


if __name__ == "__main__":
    main()

