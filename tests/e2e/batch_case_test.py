#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HydroClaude 多案例批量端到端测试
Multi-Case Batch E2E Testing

一步一步测试每个案例：
1. 加载案例配置
2. 调用后端API
3. 验证结果正确性
4. 记录测试报告

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

# 配置
BACKEND_URL = "http://localhost:8001"  # 使用修复后的后端
OUTPUT_DIR = project_root / "tests" / "e2e" / "batch_test_output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class TestCase:
    """测试案例"""
    id: str
    name: str
    description: str
    config: Dict[str, Any]
    expected: Dict[str, Any] = field(default_factory=dict)
    tolerance: float = 0.05  # 5% 误差容忍度


@dataclass
class TestResult:
    """测试结果"""
    case_id: str
    case_name: str
    status: str  # passed, failed, error
    duration: float
    metrics: Dict[str, Any] = field(default_factory=dict)
    validation: Dict[str, Any] = field(default_factory=dict)
    error: str = None


class BatchTestRunner:
    """批量测试运行器"""
    
    def __init__(self, backend_url: str = BACKEND_URL):
        self.backend_url = backend_url
        self.results: List[TestResult] = []
        
    def log(self, message: str, level: str = "INFO"):
        """日志输出"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        icons = {"INFO": "[i]", "SUCCESS": "[OK]", "ERROR": "[X]", "STEP": "[>]"}
        print(f"[{timestamp}] {icons.get(level, '[?]')} {message}")
    
    def run_case(self, case: TestCase) -> TestResult:
        """运行单个测试案例"""
        self.log(f"开始测试: {case.name}", "STEP")
        start_time = time.time()
        
        try:
            # 1. 构建API请求
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
            
            # 2. 调用API
            response = requests.post(
                f"{self.backend_url}/api/structures/simulate-canal-with-structure",
                json=request,
                timeout=300  # 5分钟超时
            )
            
            if response.status_code != 200:
                return TestResult(
                    case_id=case.id,
                    case_name=case.name,
                    status="error",
                    duration=time.time() - start_time,
                    error=f"API返回状态码: {response.status_code}"
                )
            
            data = response.json()
            
            # 3. 提取结果
            results = data.get("results", data)
            metrics = results.get("metrics", {})
            
            # 4. 验证结果
            validation = self._validate_results(case, results, metrics)
            
            # 5. 返回结果
            status = "passed" if validation.get("passed", False) else "failed"
            
            result = TestResult(
                case_id=case.id,
                case_name=case.name,
                status=status,
                duration=time.time() - start_time,
                metrics=metrics,
                validation=validation
            )
            
            self.log(f"案例 {case.id}: {status.upper()} ({result.duration:.2f}s)", 
                    "SUCCESS" if status == "passed" else "ERROR")
            
            return result
            
        except Exception as e:
            return TestResult(
                case_id=case.id,
                case_name=case.name,
                status="error",
                duration=time.time() - start_time,
                error=str(e)
            )
    
    def _validate_results(self, case: TestCase, results: Dict, metrics: Dict) -> Dict[str, Any]:
        """验证结果"""
        validation = {
            "passed": True,
            "checks": []
        }
        
        # 基本检查
        if results.get("status") != "completed":
            validation["passed"] = False
            validation["checks"].append({"name": "status", "passed": False, "message": "仿真未完成"})
            return validation
        
        # 检查必需的metrics字段
        required_fields = ["max_depth", "min_depth", "max_velocity", "converged"]
        for field in required_fields:
            if field not in metrics:
                validation["passed"] = False
                validation["checks"].append({
                    "name": f"metrics.{field}",
                    "passed": False,
                    "message": f"缺少字段: {field}"
                })
        
        # 检查收敛状态
        if not metrics.get("converged", False):
            validation["passed"] = False
            validation["checks"].append({
                "name": "converged",
                "passed": False,
                "message": "仿真未收敛"
            })
        
        # 检查物理合理性
        max_depth = metrics.get("max_depth", 0)
        min_depth = metrics.get("min_depth", 0)
        
        if min_depth < 0:
            validation["passed"] = False
            validation["checks"].append({
                "name": "physical_validity",
                "passed": False,
                "message": f"负水深: {min_depth}"
            })
        elif min_depth > 0 and max_depth > 0:
            validation["checks"].append({
                "name": "physical_validity",
                "passed": True,
                "message": f"水深范围合理: [{min_depth:.3f}, {max_depth:.3f}]m"
            })
        
        # 如果有期望值，进行对比
        if case.expected:
            for key, expected_value in case.expected.items():
                actual_value = metrics.get(key)
                if actual_value is not None:
                    error = abs(actual_value - expected_value) / (expected_value + 1e-10)
                    passed = error <= case.tolerance
                    if not passed:
                        validation["passed"] = False
                    validation["checks"].append({
                        "name": key,
                        "passed": passed,
                        "expected": expected_value,
                        "actual": actual_value,
                        "error": f"{error*100:.2f}%"
                    })
        
        return validation
    
    def run_all(self, cases: List[TestCase]) -> List[TestResult]:
        """运行所有测试案例"""
        self.log(f"开始批量测试: {len(cases)} 个案例", "STEP")
        print("=" * 60)
        
        self.results = []
        for i, case in enumerate(cases, 1):
            self.log(f"[{i}/{len(cases)}] 测试案例: {case.name}")
            result = self.run_case(case)
            self.results.append(result)
            print()
        
        # 生成摘要
        self._print_summary()
        self._save_report()
        
        return self.results
    
    def _print_summary(self):
        """打印测试摘要"""
        passed = sum(1 for r in self.results if r.status == "passed")
        failed = sum(1 for r in self.results if r.status == "failed")
        errors = sum(1 for r in self.results if r.status == "error")
        total_time = sum(r.duration for r in self.results)
        
        print("\n" + "=" * 60)
        print("  测试摘要")
        print("=" * 60)
        print(f"  总案例数: {len(self.results)}")
        print(f"  通过: {passed} ({passed/len(self.results)*100:.1f}%)")
        print(f"  失败: {failed}")
        print(f"  错误: {errors}")
        print(f"  总耗时: {total_time:.1f}s")
        print("=" * 60)
    
    def _save_report(self):
        """保存测试报告"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total": len(self.results),
                "passed": sum(1 for r in self.results if r.status == "passed"),
                "failed": sum(1 for r in self.results if r.status == "failed"),
                "errors": sum(1 for r in self.results if r.status == "error")
            },
            "results": [
                {
                    "case_id": r.case_id,
                    "case_name": r.case_name,
                    "status": r.status,
                    "duration": r.duration,
                    "metrics": r.metrics,
                    "validation": r.validation,
                    "error": r.error
                }
                for r in self.results
            ]
        }
        
        report_file = OUTPUT_DIR / f"batch_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
        
        self.log(f"报告已保存: {report_file}", "SUCCESS")


def get_test_cases() -> List[TestCase]:
    """定义测试案例"""
    cases = []
    
    # 案例1: 均匀流基础测试
    cases.append(TestCase(
        id="TC001",
        name="均匀流基础测试",
        description="测试基础均匀流场景",
        config={
            "length": 1000, "width": 10, "n_cells": 100,
            "slope": 0.001, "manning_n": 0.015,
            "upstream_bc": {"type": "h", "value": 5.0},
            "downstream_bc": {"type": "h", "value": 5.0}
        },
        expected={"converged": True}
    ))
    
    # 案例2: 高流量测试
    cases.append(TestCase(
        id="TC002",
        name="高流量输入测试",
        description="测试大流量边界条件",
        config={
            "length": 1000, "width": 10, "n_cells": 100,
            "slope": 0.001, "manning_n": 0.015,
            "upstream_bc": {"type": "Q", "value": 100.0},
            "downstream_bc": {"type": "h", "value": 3.0}
        },
        expected={"converged": True}
    ))
    
    # 案例3: 陡坡测试
    cases.append(TestCase(
        id="TC003",
        name="陡坡渠道测试",
        description="测试陡坡条件下的水流",
        config={
            "length": 1000, "width": 10, "n_cells": 100,
            "slope": 0.01, "manning_n": 0.015,
            "upstream_bc": {"type": "h", "value": 5.0},
            "downstream_bc": {"type": "h", "value": 3.0}
        },
        expected={"converged": True}
    ))
    
    # 案例4: 糙率测试
    cases.append(TestCase(
        id="TC004",
        name="高糙率渠道测试",
        description="测试高糙率对水流的影响",
        config={
            "length": 1000, "width": 10, "n_cells": 100,
            "slope": 0.001, "manning_n": 0.05,
            "upstream_bc": {"type": "Q", "value": 50.0},
            "downstream_bc": {"type": "h", "value": 4.0}
        },
        expected={"converged": True}
    ))
    
    # 案例5: 长渠道测试
    cases.append(TestCase(
        id="TC005",
        name="长渠道测试",
        description="测试5km长渠道",
        config={
            "length": 5000, "width": 15, "n_cells": 200,
            "slope": 0.0005, "manning_n": 0.02,
            "upstream_bc": {"type": "Q", "value": 80.0},
            "downstream_bc": {"type": "h", "value": 4.0}
        },
        expected={"converged": True}
    ))
    
    # 案例6: 窄渠道测试
    cases.append(TestCase(
        id="TC006",
        name="窄渠道测试",
        description="测试2m宽窄渠道",
        config={
            "length": 500, "width": 2, "n_cells": 100,
            "slope": 0.002, "manning_n": 0.015,
            "upstream_bc": {"type": "Q", "value": 10.0},
            "downstream_bc": {"type": "h", "value": 2.0}
        },
        expected={"converged": True}
    ))
    
    # 案例7: 宽渠道测试
    cases.append(TestCase(
        id="TC007",
        name="宽渠道测试",
        description="测试50m宽渠道",
        config={
            "length": 2000, "width": 50, "n_cells": 150,
            "slope": 0.001, "manning_n": 0.02,
            "upstream_bc": {"type": "Q", "value": 500.0},
            "downstream_bc": {"type": "h", "value": 5.0}
        },
        expected={"converged": True}
    ))
    
    # 案例8: 精细网格测试
    cases.append(TestCase(
        id="TC008",
        name="精细网格测试",
        description="测试500个网格单元",
        config={
            "length": 1000, "width": 10, "n_cells": 500,
            "slope": 0.001, "manning_n": 0.015,
            "upstream_bc": {"type": "h", "value": 5.0},
            "downstream_bc": {"type": "h", "value": 5.0}
        },
        expected={"converged": True}
    ))
    
    # 案例9: 粗糙网格测试
    cases.append(TestCase(
        id="TC009",
        name="粗糙网格测试",
        description="测试20个网格单元",
        config={
            "length": 1000, "width": 10, "n_cells": 20,
            "slope": 0.001, "manning_n": 0.015,
            "upstream_bc": {"type": "h", "value": 5.0},
            "downstream_bc": {"type": "h", "value": 5.0}
        },
        expected={"converged": True}
    ))
    
    # 案例10: 边界水头差测试
    cases.append(TestCase(
        id="TC010",
        name="水头差驱动流测试",
        description="测试上下游水头差驱动的水流",
        config={
            "length": 1000, "width": 10, "n_cells": 100,
            "slope": 0.0, "manning_n": 0.015,
            "upstream_bc": {"type": "h", "value": 8.0},
            "downstream_bc": {"type": "h", "value": 4.0}
        },
        expected={"converged": True}
    ))
    
    return cases


def main():
    """主函数"""
    print("\n" + "=" * 70)
    print("  HydroClaude 多案例批量端到端测试")
    print("  一步一步测试每个案例")
    print("=" * 70 + "\n")
    
    # 获取测试案例
    cases = get_test_cases()
    
    # 运行测试
    runner = BatchTestRunner()
    results = runner.run_all(cases)
    
    return results


if __name__ == "__main__":
    main()

