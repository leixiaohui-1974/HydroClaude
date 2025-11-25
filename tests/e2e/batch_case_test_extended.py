#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HydroClaude 扩展批量测试 - 更多案例类型
Extended Batch Testing with More Case Types

测试类型:
1. 基础明渠流动 (10个)
2. 边界条件变化 (10个)
3. 几何参数变化 (10个)
4. 物理参数变化 (10个)
5. 特殊工况 (10个)

共计50个案例

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

# 添加项目路径
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
    description: str
    config: Dict[str, Any]
    expected: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestResult:
    case_id: str
    case_name: str
    category: str
    status: str
    duration: float
    metrics: Dict[str, Any] = field(default_factory=dict)
    error: str = None


class ExtendedBatchRunner:
    def __init__(self, backend_url: str = BACKEND_URL):
        self.backend_url = backend_url
        self.results: List[TestResult] = []
        
    def log(self, msg: str, level: str = "INFO"):
        ts = datetime.now().strftime("%H:%M:%S")
        icons = {"INFO": "[i]", "SUCCESS": "[OK]", "ERROR": "[X]", "STEP": "[>]", "WARN": "[!]"}
        print(f"[{ts}] {icons.get(level, '[?]')} {msg}")
    
    def run_case(self, case: TestCase) -> TestResult:
        start = time.time()
        
        try:
            request = {
                "simulation_type": case.config.get("simulation_type", "steady"),
                "canal": {
                    "length": case.config.get("length", 1000),
                    "width": case.config.get("width", 10),
                    "slope": case.config.get("slope", 0.001),
                    "manning_n": case.config.get("manning_n", 0.015),
                    "grid_nx": case.config.get("n_cells", 100)
                },
                "structure_type": case.config.get("structure_type", "none"),
                "structure": case.config.get("structure", {"position": 0, "parameters": {}}),
                "boundaries": {
                    "upstream": case.config.get("upstream_bc", {"type": "h", "value": 5.0}),
                    "downstream": case.config.get("downstream_bc", {"type": "h", "value": 5.0})
                },
                "metadata": {"title": case.name, "description": case.description}
            }
            
            response = requests.post(
                f"{self.backend_url}/api/structures/simulate-canal-with-structure",
                json=request,
                timeout=180
            )
            
            if response.status_code != 200:
                return TestResult(case.id, case.name, case.category, "error", 
                                time.time()-start, error=f"HTTP {response.status_code}")
            
            data = response.json()
            results = data.get("results", data)
            metrics = results.get("metrics", {})
            
            # 验证
            status = "passed"
            if results.get("status") != "completed":
                status = "failed"
            elif not metrics.get("converged", False):
                status = "failed"
            elif metrics.get("min_depth", 0) < 0:
                status = "failed"
                
            return TestResult(case.id, case.name, case.category, status,
                            time.time()-start, metrics)
            
        except Exception as e:
            return TestResult(case.id, case.name, case.category, "error",
                            time.time()-start, error=str(e))
    
    def run_all(self, cases: List[TestCase]):
        self.log(f"开始扩展批量测试: {len(cases)} 个案例", "STEP")
        
        # 按类别分组
        categories = {}
        for case in cases:
            if case.category not in categories:
                categories[case.category] = []
            categories[case.category].append(case)
        
        self.results = []
        total = len(cases)
        done = 0
        
        for category, cat_cases in categories.items():
            print(f"\n{'='*60}")
            self.log(f"类别: {category} ({len(cat_cases)}个案例)", "STEP")
            print("="*60)
            
            for case in cat_cases:
                done += 1
                result = self.run_case(case)
                self.results.append(result)
                
                status_icon = "OK" if result.status == "passed" else "X"
                self.log(f"[{done}/{total}] {case.id}: {result.status.upper()} ({result.duration:.1f}s)",
                        "SUCCESS" if result.status == "passed" else "ERROR")
        
        self._print_summary()
        self._save_report()
    
    def _print_summary(self):
        passed = sum(1 for r in self.results if r.status == "passed")
        failed = sum(1 for r in self.results if r.status == "failed")
        errors = sum(1 for r in self.results if r.status == "error")
        total_time = sum(r.duration for r in self.results)
        
        print(f"\n{'='*70}")
        print("  扩展批量测试摘要")
        print("="*70)
        print(f"  总案例数: {len(self.results)}")
        print(f"  通过: {passed} ({passed/len(self.results)*100:.1f}%)")
        print(f"  失败: {failed}")
        print(f"  错误: {errors}")
        print(f"  总耗时: {total_time:.1f}s ({total_time/60:.1f}分钟)")
        
        # 按类别统计
        print(f"\n  按类别统计:")
        categories = {}
        for r in self.results:
            if r.category not in categories:
                categories[r.category] = {"passed": 0, "failed": 0, "error": 0}
            categories[r.category][r.status] += 1
        
        for cat, stats in categories.items():
            total = stats["passed"] + stats["failed"] + stats["error"]
            pct = stats["passed"] / total * 100
            print(f"    {cat}: {stats['passed']}/{total} ({pct:.0f}%)")
        
        print("="*70)
    
    def _save_report(self):
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total": len(self.results),
                "passed": sum(1 for r in self.results if r.status == "passed"),
                "failed": sum(1 for r in self.results if r.status == "failed"),
                "errors": sum(1 for r in self.results if r.status == "error")
            },
            "by_category": {},
            "results": [
                {"id": r.case_id, "name": r.case_name, "category": r.category,
                 "status": r.status, "duration": r.duration, "error": r.error}
                for r in self.results
            ]
        }
        
        for r in self.results:
            if r.category not in report["by_category"]:
                report["by_category"][r.category] = {"passed": 0, "failed": 0, "error": 0}
            report["by_category"][r.category][r.status] += 1
        
        report_file = OUTPUT_DIR / f"extended_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
        self.log(f"报告已保存: {report_file}", "SUCCESS")


def get_extended_cases() -> List[TestCase]:
    """定义50个扩展测试案例"""
    cases = []
    
    # ===== 类别1: 基础明渠流动 (10个) =====
    cat1 = "基础明渠流动"
    
    cases.append(TestCase("B001", "静水初始条件", cat1, "无流动的静水",
        {"length": 1000, "width": 10, "n_cells": 100, "slope": 0.0,
         "upstream_bc": {"type": "h", "value": 5.0}, "downstream_bc": {"type": "h", "value": 5.0}}))
    
    cases.append(TestCase("B002", "均匀流-低流量", cat1, "10m³/s均匀流",
        {"length": 1000, "width": 10, "n_cells": 100, "slope": 0.001,
         "upstream_bc": {"type": "Q", "value": 10.0}, "downstream_bc": {"type": "h", "value": 2.0}}))
    
    cases.append(TestCase("B003", "均匀流-中流量", cat1, "50m³/s均匀流",
        {"length": 1000, "width": 10, "n_cells": 100, "slope": 0.001,
         "upstream_bc": {"type": "Q", "value": 50.0}, "downstream_bc": {"type": "h", "value": 3.0}}))
    
    cases.append(TestCase("B004", "均匀流-高流量", cat1, "200m³/s均匀流",
        {"length": 1000, "width": 15, "n_cells": 100, "slope": 0.001,
         "upstream_bc": {"type": "Q", "value": 200.0}, "downstream_bc": {"type": "h", "value": 4.0}}))
    
    cases.append(TestCase("B005", "缓流状态", cat1, "Fr<1的缓流",
        {"length": 1000, "width": 10, "n_cells": 100, "slope": 0.0005,
         "upstream_bc": {"type": "Q", "value": 30.0}, "downstream_bc": {"type": "h", "value": 4.0}}))
    
    cases.append(TestCase("B006", "临界流附近", cat1, "接近临界状态",
        {"length": 500, "width": 5, "n_cells": 100, "slope": 0.005,
         "upstream_bc": {"type": "Q", "value": 20.0}, "downstream_bc": {"type": "h", "value": 2.0}}))
    
    cases.append(TestCase("B007", "急流状态", cat1, "Fr>1的急流",
        {"length": 500, "width": 5, "n_cells": 100, "slope": 0.02,
         "upstream_bc": {"type": "Q", "value": 30.0}, "downstream_bc": {"type": "h", "value": 1.5}}))
    
    cases.append(TestCase("B008", "壅水曲线M1", cat1, "M1型壅水",
        {"length": 1000, "width": 10, "n_cells": 100, "slope": 0.001,
         "upstream_bc": {"type": "Q", "value": 50.0}, "downstream_bc": {"type": "h", "value": 6.0}}))
    
    cases.append(TestCase("B009", "降水曲线M2", cat1, "M2型降水",
        {"length": 1000, "width": 10, "n_cells": 100, "slope": 0.001,
         "upstream_bc": {"type": "Q", "value": 50.0}, "downstream_bc": {"type": "h", "value": 2.5}}))
    
    cases.append(TestCase("B010", "混合边界", cat1, "上游流量+下游水深",
        {"length": 1000, "width": 10, "n_cells": 100, "slope": 0.001,
         "upstream_bc": {"type": "Q", "value": 80.0}, "downstream_bc": {"type": "h", "value": 4.0}}))
    
    # ===== 类别2: 边界条件变化 (10个) =====
    cat2 = "边界条件变化"
    
    for i, Q in enumerate([5, 20, 40, 60, 80, 100, 150, 200, 300, 500], 1):
        cases.append(TestCase(f"BC{i:03d}", f"流量边界Q={Q}m³/s", cat2, f"上游流量{Q}m³/s",
            {"length": 1000, "width": 10 + Q/50, "n_cells": 100, "slope": 0.001,
             "upstream_bc": {"type": "Q", "value": Q}, "downstream_bc": {"type": "h", "value": 3.0 + Q/100}}))
    
    # ===== 类别3: 几何参数变化 (10个) =====
    cat3 = "几何参数变化"
    
    # 长度变化
    for i, L in enumerate([100, 500, 1000, 2000, 5000], 1):
        cases.append(TestCase(f"G{i:03d}", f"渠道长度L={L}m", cat3, f"{L}m长渠道",
            {"length": L, "width": 10, "n_cells": min(L//10, 200), "slope": 0.001,
             "upstream_bc": {"type": "Q", "value": 50.0}, "downstream_bc": {"type": "h", "value": 3.0}}))
    
    # 宽度变化
    for i, W in enumerate([2, 5, 10, 20, 50], 1):
        cases.append(TestCase(f"G{i+5:03d}", f"渠道宽度W={W}m", cat3, f"{W}m宽渠道",
            {"length": 1000, "width": W, "n_cells": 100, "slope": 0.001,
             "upstream_bc": {"type": "Q", "value": W*5}, "downstream_bc": {"type": "h", "value": 3.0}}))
    
    # ===== 类别4: 物理参数变化 (10个) =====
    cat4 = "物理参数变化"
    
    # 坡度变化
    for i, S in enumerate([0.0001, 0.0005, 0.001, 0.002, 0.005], 1):
        cases.append(TestCase(f"P{i:03d}", f"底坡S={S}", cat4, f"底坡{S*1000}‰",
            {"length": 1000, "width": 10, "n_cells": 100, "slope": S,
             "upstream_bc": {"type": "Q", "value": 50.0}, "downstream_bc": {"type": "h", "value": 3.0}}))
    
    # 糙率变化
    for i, n in enumerate([0.01, 0.015, 0.02, 0.03, 0.05], 1):
        cases.append(TestCase(f"P{i+5:03d}", f"糙率n={n}", cat4, f"曼宁糙率{n}",
            {"length": 1000, "width": 10, "n_cells": 100, "slope": 0.001, "manning_n": n,
             "upstream_bc": {"type": "Q", "value": 50.0}, "downstream_bc": {"type": "h", "value": 3.0}}))
    
    # ===== 类别5: 特殊工况 (10个) =====
    cat5 = "特殊工况"
    
    cases.append(TestCase("S001", "极浅水流", cat5, "水深<0.5m",
        {"length": 500, "width": 20, "n_cells": 100, "slope": 0.001,
         "upstream_bc": {"type": "Q", "value": 5.0}, "downstream_bc": {"type": "h", "value": 0.3}}))
    
    cases.append(TestCase("S002", "深水流动", cat5, "水深>10m",
        {"length": 1000, "width": 50, "n_cells": 100, "slope": 0.0001,
         "upstream_bc": {"type": "h", "value": 12.0}, "downstream_bc": {"type": "h", "value": 10.0}}))
    
    cases.append(TestCase("S003", "高速水流", cat5, "流速>5m/s",
        {"length": 500, "width": 5, "n_cells": 100, "slope": 0.01,
         "upstream_bc": {"type": "Q", "value": 50.0}, "downstream_bc": {"type": "h", "value": 1.5}}))
    
    cases.append(TestCase("S004", "低速水流", cat5, "流速<0.5m/s",
        {"length": 1000, "width": 30, "n_cells": 100, "slope": 0.0001,
         "upstream_bc": {"type": "Q", "value": 10.0}, "downstream_bc": {"type": "h", "value": 5.0}}))
    
    cases.append(TestCase("S005", "大流量宽渠", cat5, "1000m³/s宽渠道",
        {"length": 2000, "width": 100, "n_cells": 150, "slope": 0.0005,
         "upstream_bc": {"type": "Q", "value": 1000.0}, "downstream_bc": {"type": "h", "value": 5.0}}))
    
    cases.append(TestCase("S006", "小流量窄渠", cat5, "1m³/s窄渠道",
        {"length": 200, "width": 1, "n_cells": 50, "slope": 0.005,
         "upstream_bc": {"type": "Q", "value": 1.0}, "downstream_bc": {"type": "h", "value": 0.5}}))
    
    cases.append(TestCase("S007", "零坡渠道", cat5, "水平渠道S=0",
        {"length": 1000, "width": 10, "n_cells": 100, "slope": 0.0,
         "upstream_bc": {"type": "h", "value": 6.0}, "downstream_bc": {"type": "h", "value": 4.0}}))
    
    cases.append(TestCase("S008", "陡坡渠道", cat5, "S=1%的陡坡",
        {"length": 500, "width": 5, "n_cells": 100, "slope": 0.01,
         "upstream_bc": {"type": "Q", "value": 20.0}, "downstream_bc": {"type": "h", "value": 1.5}}))
    
    cases.append(TestCase("S009", "粗糙底面", cat5, "n=0.1的粗糙底",
        {"length": 500, "width": 10, "n_cells": 100, "slope": 0.002, "manning_n": 0.1,
         "upstream_bc": {"type": "Q", "value": 30.0}, "downstream_bc": {"type": "h", "value": 3.0}}))
    
    cases.append(TestCase("S010", "光滑底面", cat5, "n=0.008的光滑底",
        {"length": 1000, "width": 10, "n_cells": 100, "slope": 0.001, "manning_n": 0.008,
         "upstream_bc": {"type": "Q", "value": 50.0}, "downstream_bc": {"type": "h", "value": 3.0}}))
    
    return cases


def main():
    print("\n" + "="*70)
    print("  HydroClaude 扩展批量测试 - 50个案例")
    print("  一步一步测试每个案例")
    print("="*70 + "\n")
    
    cases = get_extended_cases()
    runner = ExtendedBatchRunner()
    runner.run_all(cases)


if __name__ == "__main__":
    main()

