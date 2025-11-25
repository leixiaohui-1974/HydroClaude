#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HydroClaude API 端到端测试

全面测试所有 API 端点和前后端集成
不依赖浏览器，使用 httpx 进行 HTTP 请求测试

Author: HydroClaude Test Team
Date: 2025-11-25
"""

import os
import warnings
warnings.filterwarnings("ignore")
import sys
import json
import time
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Tuple

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import httpx

# 测试配置
FRONTEND_URL = "http://localhost:3000"
BACKEND_URL = "http://localhost:8000"
REPORT_DIR = project_root / "reports" / "e2e_api"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

# 测试结果
test_results = {
    "start_time": None,
    "end_time": None,
    "total_tests": 0,
    "passed": 0,
    "failed": 0,
    "tests": [],
    "api_responses": []
}


def record_test(name: str, status: str, details: str = "", response_data: Any = None):
    """记录测试结果"""
    test_results["total_tests"] += 1
    if status == "passed":
        test_results["passed"] += 1
        icon = "✅"
    else:
        test_results["failed"] += 1
        icon = "❌"

    print(f"  {icon} {name}: {details[:80]}")

    test_results["tests"].append({
        "name": name,
        "status": status,
        "details": details,
        "response": str(response_data)[:500] if response_data else None,
        "timestamp": datetime.now().isoformat()
    })


async def test_backend_health():
    """测试后端健康检查"""
    print("\n" + "="*70)
    print("测试: 后端健康检查")
    print("="*70)

    async with httpx.AsyncClient(timeout=30.0) as client:
        # 测试根端点
        try:
            response = await client.get(f"{BACKEND_URL}/")
            if response.status_code == 200:
                data = response.json()
                record_test("GET /", "passed", f"API Version: {data.get('api_version', 'unknown')}", data)
            else:
                record_test("GET /", "failed", f"Status: {response.status_code}")
        except Exception as e:
            record_test("GET /", "failed", str(e))

        # 测试 API 文档
        try:
            response = await client.get(f"{BACKEND_URL}/docs")
            if response.status_code == 200 and "swagger" in response.text.lower():
                record_test("GET /docs", "passed", "Swagger UI 可用")
            else:
                record_test("GET /docs", "failed", f"Status: {response.status_code}")
        except Exception as e:
            record_test("GET /docs", "failed", str(e))

        # 测试 OpenAPI 规格
        try:
            response = await client.get(f"{BACKEND_URL}/openapi.json")
            if response.status_code == 200:
                data = response.json()
                paths_count = len(data.get("paths", {}))
                record_test("GET /openapi.json", "passed", f"API 端点数: {paths_count}", {"paths_count": paths_count})
            else:
                record_test("GET /openapi.json", "failed", f"Status: {response.status_code}")
        except Exception as e:
            record_test("GET /openapi.json", "failed", str(e))


async def test_structures_api():
    """测试水工结构 API"""
    print("\n" + "="*70)
    print("测试: 水工结构 API")
    print("="*70)

    async with httpx.AsyncClient(timeout=30.0) as client:
        # 测试结构类型
        try:
            response = await client.get(f"{BACKEND_URL}/api/structures/types")
            if response.status_code == 200:
                data = response.json()
                record_test("GET /api/structures/types", "passed", f"结构类型: {data}", data)
            else:
                record_test("GET /api/structures/types", "failed", f"Status: {response.status_code}")
        except Exception as e:
            record_test("GET /api/structures/types", "failed", str(e))

        # 测试结构健康检查
        try:
            response = await client.get(f"{BACKEND_URL}/api/structures/health")
            if response.status_code == 200:
                record_test("GET /api/structures/health", "passed", "健康检查通过")
            else:
                record_test("GET /api/structures/health", "failed", f"Status: {response.status_code}")
        except Exception as e:
            record_test("GET /api/structures/health", "failed", str(e))

        # 测试闸门计算
        try:
            gate_data = {
                "gate_type": "sluice",
                "width": 5.0,
                "opening": 2.0,
                "upstream_depth": 5.0,
                "downstream_depth": 2.0,
                "Cd": 0.6
            }
            response = await client.post(f"{BACKEND_URL}/api/structures/gate", json=gate_data)
            if response.status_code == 200:
                data = response.json()
                record_test("POST /api/structures/gate", "passed", f"闸门流量计算成功", data)
            else:
                record_test("POST /api/structures/gate", "failed", f"Status: {response.status_code}, {response.text[:100]}")
        except Exception as e:
            record_test("POST /api/structures/gate", "failed", str(e))

        # 测试堰计算
        try:
            weir_data = {
                "weir_type": "broad_crested",
                "width": 10.0,
                "crest_height": 2.0,
                "upstream_depth": 4.0,
                "Cd": 0.385
            }
            response = await client.post(f"{BACKEND_URL}/api/structures/weir", json=weir_data)
            if response.status_code == 200:
                data = response.json()
                record_test("POST /api/structures/weir", "passed", f"堰流量计算成功", data)
            else:
                record_test("POST /api/structures/weir", "failed", f"Status: {response.status_code}, {response.text[:100]}")
        except Exception as e:
            record_test("POST /api/structures/weir", "failed", str(e))

        # 测试泵站计算
        try:
            pump_data = {
                "pump_type": "centrifugal",
                "flow_rate": 0.5,
                "head": 30.0,
                "efficiency": 0.75
            }
            response = await client.post(f"{BACKEND_URL}/api/structures/pump", json=pump_data)
            if response.status_code == 200:
                data = response.json()
                record_test("POST /api/structures/pump", "passed", f"泵站计算成功", data)
            else:
                record_test("POST /api/structures/pump", "failed", f"Status: {response.status_code}, {response.text[:100]}")
        except Exception as e:
            record_test("POST /api/structures/pump", "failed", str(e))


async def test_simulation_api():
    """测试仿真 API"""
    print("\n" + "="*70)
    print("测试: 仿真 API")
    print("="*70)

    async with httpx.AsyncClient(timeout=60.0) as client:
        # 测试同步仿真
        try:
            sim_data = {
                "length": 1000.0,
                "width": 10.0,
                "slope": 0.001,
                "manning_n": 0.025,
                "Q": 50.0,
                "h_downstream": 2.0,
                "nx": 50
            }
            response = await client.post(f"{BACKEND_URL}/api/v1/simulations-sync", json=sim_data)
            if response.status_code == 200:
                data = response.json()
                record_test("POST /api/v1/simulations-sync", "passed", f"同步仿真成功", data)
            elif response.status_code in [404, 405]:
                record_test("POST /api/v1/simulations-sync", "failed", "端点不存在")
            else:
                record_test("POST /api/v1/simulations-sync", "failed", f"Status: {response.status_code}, {response.text[:100]}")
        except Exception as e:
            record_test("POST /api/v1/simulations-sync", "failed", str(e))

        # 测试异步仿真 - 创建任务
        task_id = None
        try:
            sim_data = {
                "length": 1000.0,
                "width": 10.0,
                "slope": 0.001,
                "manning_n": 0.025,
                "Q": 50.0,
                "h_downstream": 2.0,
                "nx": 50
            }
            response = await client.post(f"{BACKEND_URL}/api/v1/simulations", json=sim_data)
            if response.status_code in [200, 201]:
                data = response.json()
                task_id = data.get("task_id")
                record_test("POST /api/v1/simulations", "passed", f"创建仿真任务: {task_id}", data)
            else:
                record_test("POST /api/v1/simulations", "failed", f"Status: {response.status_code}, {response.text[:100]}")
        except Exception as e:
            record_test("POST /api/v1/simulations", "failed", str(e))

        # 测试获取仿真状态
        if task_id:
            try:
                await asyncio.sleep(2)  # 等待任务处理
                response = await client.get(f"{BACKEND_URL}/api/v1/simulations/{task_id}/status")
                if response.status_code == 200:
                    data = response.json()
                    record_test(f"GET /api/v1/simulations/{task_id}/status", "passed", f"状态: {data.get('status', 'unknown')}", data)
                else:
                    record_test(f"GET /api/v1/simulations/{task_id}/status", "failed", f"Status: {response.status_code}")
            except Exception as e:
                record_test(f"GET /api/v1/simulations/{task_id}/status", "failed", str(e))

            # 测试获取仿真结果
            try:
                await asyncio.sleep(3)  # 等待任务完成
                response = await client.get(f"{BACKEND_URL}/api/v1/simulations/{task_id}/results")
                if response.status_code == 200:
                    data = response.json()
                    record_test(f"GET /api/v1/simulations/{task_id}/results", "passed", "获取结果成功", data)
                else:
                    record_test(f"GET /api/v1/simulations/{task_id}/results", "failed", f"Status: {response.status_code}")
            except Exception as e:
                record_test(f"GET /api/v1/simulations/{task_id}/results", "failed", str(e))

        # 测试获取仿真列表
        try:
            response = await client.get(f"{BACKEND_URL}/api/v1/simulations")
            if response.status_code == 200:
                data = response.json()
                count = len(data) if isinstance(data, list) else data.get("total", 0)
                record_test("GET /api/v1/simulations", "passed", f"仿真列表: {count} 项", data)
            else:
                record_test("GET /api/v1/simulations", "failed", f"Status: {response.status_code}")
        except Exception as e:
            record_test("GET /api/v1/simulations", "failed", str(e))


async def test_reservoir_api():
    """测试水库 API"""
    print("\n" + "="*70)
    print("测试: 水库/堰 API")
    print("="*70)

    async with httpx.AsyncClient(timeout=30.0) as client:
        # 测试健康检查
        try:
            response = await client.get(f"{BACKEND_URL}/reservoir/health")
            if response.status_code == 200:
                record_test("GET /reservoir/health", "passed", "健康检查通过")
            else:
                record_test("GET /reservoir/health", "failed", f"Status: {response.status_code}")
        except Exception as e:
            record_test("GET /reservoir/health", "failed", str(e))

        # 测试堰类型
        try:
            response = await client.get(f"{BACKEND_URL}/reservoir/weir-types")
            if response.status_code == 200:
                data = response.json()
                record_test("GET /reservoir/weir-types", "passed", f"堰类型: {data}", data)
            else:
                record_test("GET /reservoir/weir-types", "failed", f"Status: {response.status_code}")
        except Exception as e:
            record_test("GET /reservoir/weir-types", "failed", str(e))

        # 测试堰仿真
        try:
            weir_sim_data = {
                "weir_type": "broad_crested",
                "width": 10.0,
                "crest_height": 2.0,
                "upstream_head": 3.0,
                "Cd": 0.385
            }
            response = await client.post(f"{BACKEND_URL}/reservoir/weir", json=weir_sim_data)
            if response.status_code == 200:
                data = response.json()
                record_test("POST /reservoir/weir", "passed", "堰仿真成功", data)
            else:
                record_test("POST /reservoir/weir", "failed", f"Status: {response.status_code}, {response.text[:100]}")
        except Exception as e:
            record_test("POST /reservoir/weir", "failed", str(e))


async def test_network_api():
    """测试管网 API"""
    print("\n" + "="*70)
    print("测试: 管网 API")
    print("="*70)

    async with httpx.AsyncClient(timeout=30.0) as client:
        # 测试健康检查
        try:
            response = await client.get(f"{BACKEND_URL}/network/health")
            if response.status_code == 200:
                record_test("GET /network/health", "passed", "健康检查通过")
            else:
                record_test("GET /network/health", "failed", f"Status: {response.status_code}")
        except Exception as e:
            record_test("GET /network/health", "failed", str(e))

        # 测试管道计算公式
        try:
            response = await client.get(f"{BACKEND_URL}/network/formulas")
            if response.status_code == 200:
                data = response.json()
                record_test("GET /network/formulas", "passed", f"公式: {data}", data)
            else:
                record_test("GET /network/formulas", "failed", f"Status: {response.status_code}")
        except Exception as e:
            record_test("GET /network/formulas", "failed", str(e))

        # 测试管道流量计算
        try:
            pipe_data = {
                "diameter": 0.3,
                "length": 1000.0,
                "roughness": 0.0001,
                "head_loss": 5.0,
                "formula": "darcy"
            }
            response = await client.post(f"{BACKEND_URL}/network/pipe-flow", json=pipe_data)
            if response.status_code == 200:
                data = response.json()
                record_test("POST /network/pipe-flow", "passed", "管道流量计算成功", data)
            else:
                record_test("POST /network/pipe-flow", "failed", f"Status: {response.status_code}, {response.text[:100]}")
        except Exception as e:
            record_test("POST /network/pipe-flow", "failed", str(e))


async def test_analysis_api():
    """测试分析 API"""
    print("\n" + "="*70)
    print("测试: 分析 API")
    print("="*70)

    async with httpx.AsyncClient(timeout=30.0) as client:
        # 测试健康检查
        try:
            response = await client.get(f"{BACKEND_URL}/analysis/health")
            if response.status_code == 200:
                record_test("GET /analysis/health", "passed", "健康检查通过")
            else:
                record_test("GET /analysis/health", "failed", f"Status: {response.status_code}")
        except Exception as e:
            record_test("GET /analysis/health", "failed", str(e))

        # 测试配置分析
        try:
            config_data = {
                "length": 1000.0,
                "width": 10.0,
                "slope": 0.001,
                "manning_n": 0.025,
                "Q": 50.0,
                "h_downstream": 2.0
            }
            response = await client.post(f"{BACKEND_URL}/analysis/config", json=config_data)
            if response.status_code == 200:
                data = response.json()
                record_test("POST /analysis/config", "passed", "配置分析成功", data)
            else:
                record_test("POST /analysis/config", "failed", f"Status: {response.status_code}, {response.text[:100]}")
        except Exception as e:
            record_test("POST /analysis/config", "failed", str(e))


async def test_test_cases_api():
    """测试测试用例 API"""
    print("\n" + "="*70)
    print("测试: 测试用例 API")
    print("="*70)

    async with httpx.AsyncClient(timeout=30.0) as client:
        # 获取测试用例列表
        try:
            response = await client.get(f"{BACKEND_URL}/api/v1/test-cases/")
            if response.status_code == 200:
                data = response.json()
                count = len(data) if isinstance(data, list) else data.get("total", 0)
                record_test("GET /api/v1/test-cases/", "passed", f"测试用例: {count} 项", data)
            else:
                record_test("GET /api/v1/test-cases/", "failed", f"Status: {response.status_code}")
        except Exception as e:
            record_test("GET /api/v1/test-cases/", "failed", str(e))

        # 获取测试用例分类
        try:
            response = await client.get(f"{BACKEND_URL}/api/v1/test-cases/categories")
            if response.status_code == 200:
                data = response.json()
                record_test("GET /api/v1/test-cases/categories", "passed", f"分类: {data}", data)
            else:
                record_test("GET /api/v1/test-cases/categories", "failed", f"Status: {response.status_code}")
        except Exception as e:
            record_test("GET /api/v1/test-cases/categories", "failed", str(e))

        # 获取统计信息
        try:
            response = await client.get(f"{BACKEND_URL}/api/v1/test-cases/statistics")
            if response.status_code == 200:
                data = response.json()
                record_test("GET /api/v1/test-cases/statistics", "passed", "统计信息获取成功", data)
            else:
                record_test("GET /api/v1/test-cases/statistics", "failed", f"Status: {response.status_code}")
        except Exception as e:
            record_test("GET /api/v1/test-cases/statistics", "failed", str(e))


async def test_frontend():
    """测试前端"""
    print("\n" + "="*70)
    print("测试: 前端")
    print("="*70)

    async with httpx.AsyncClient(timeout=30.0) as client:
        # 测试前端首页
        try:
            response = await client.get(FRONTEND_URL)
            if response.status_code == 200:
                # 检查是否有 React 应用的特征
                has_react = "root" in response.text or "app" in response.text.lower()
                has_script = "<script" in response.text
                record_test("GET / (Frontend)", "passed", f"前端加载成功 (React: {has_react}, Script: {has_script})")
            else:
                record_test("GET / (Frontend)", "failed", f"Status: {response.status_code}")
        except Exception as e:
            record_test("GET / (Frontend)", "failed", str(e))


async def test_full_workflow():
    """测试完整工作流程"""
    print("\n" + "="*70)
    print("测试: 完整仿真工作流程")
    print("="*70)

    async with httpx.AsyncClient(timeout=60.0) as client:
        # 1. 创建渠道仿真
        print("  步骤1: 创建渠道仿真任务")
        try:
            sim_data = {
                "length": 1000.0,
                "width": 10.0,
                "slope": 0.001,
                "manning_n": 0.025,
                "Q": 50.0,
                "h_downstream": 2.0,
                "nx": 100
            }
            response = await client.post(f"{BACKEND_URL}/api/v1/simulations", json=sim_data)
            if response.status_code in [200, 201]:
                data = response.json()
                task_id = data.get("task_id")
                record_test("工作流-创建仿真", "passed", f"Task ID: {task_id}")

                # 2. 等待并检查状态
                print("  步骤2: 等待仿真完成")
                for i in range(10):
                    await asyncio.sleep(1)
                    status_response = await client.get(f"{BACKEND_URL}/api/v1/simulations/{task_id}/status")
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        status = status_data.get("status", "unknown")
                        print(f"    状态: {status}")
                        if status in ["completed", "failed"]:
                            break

                # 3. 获取结果
                print("  步骤3: 获取仿真结果")
                results_response = await client.get(f"{BACKEND_URL}/api/v1/simulations/{task_id}/results")
                if results_response.status_code == 200:
                    results = results_response.json()
                    record_test("工作流-获取结果", "passed", "仿真结果获取成功")
                else:
                    record_test("工作流-获取结果", "failed", f"Status: {results_response.status_code}")

            else:
                record_test("工作流-创建仿真", "failed", f"Status: {response.status_code}")

        except Exception as e:
            record_test("工作流-创建仿真", "failed", str(e))

        # 2. 测试带结构的渠道仿真
        print("\n  步骤4: 创建带闸门的渠道仿真")
        try:
            canal_with_gate = {
                "canal": {
                    "length": 1000.0,
                    "width": 10.0,
                    "slope": 0.001,
                    "manning_n": 0.025,
                    "Q": 50.0,
                    "h_downstream": 2.0
                },
                "structure": {
                    "type": "gate",
                    "position": 500.0,
                    "width": 10.0,
                    "opening": 2.0,
                    "Cd": 0.6
                }
            }
            response = await client.post(f"{BACKEND_URL}/api/structures/simulate-canal-with-structure", json=canal_with_gate)
            if response.status_code == 200:
                data = response.json()
                record_test("工作流-渠道+闸门仿真", "passed", "复合仿真成功", data)
            else:
                record_test("工作流-渠道+闸门仿真", "failed", f"Status: {response.status_code}, {response.text[:100]}")
        except Exception as e:
            record_test("工作流-渠道+闸门仿真", "failed", str(e))


def generate_report():
    """生成测试报告"""
    print("\n" + "="*70)
    print("生成测试报告")
    print("="*70)

    test_results["end_time"] = datetime.now().isoformat()

    # 保存 JSON 报告
    report_file = REPORT_DIR / "api_test_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(test_results, f, ensure_ascii=False, indent=2)

    # 生成 HTML 报告
    html_report = REPORT_DIR / "api_test_report.html"

    passed_rate = (test_results['passed'] / test_results['total_tests'] * 100) if test_results['total_tests'] > 0 else 0

    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HydroClaude API E2E 测试报告</title>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 0; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 16px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); }}
        h1 {{ color: #333; border-bottom: 3px solid #667eea; padding-bottom: 15px; margin-bottom: 30px; }}
        .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 20px; margin: 30px 0; }}
        .stat {{ padding: 25px; border-radius: 12px; text-align: center; transition: transform 0.3s; }}
        .stat:hover {{ transform: translateY(-5px); }}
        .stat.total {{ background: linear-gradient(135deg, #667eea, #764ba2); color: white; }}
        .stat.passed {{ background: linear-gradient(135deg, #11998e, #38ef7d); color: white; }}
        .stat.failed {{ background: linear-gradient(135deg, #eb3349, #f45c43); color: white; }}
        .stat.rate {{ background: linear-gradient(135deg, #f093fb, #f5576c); color: white; }}
        .stat h2 {{ margin: 0; font-size: 2.5em; text-shadow: 2px 2px 4px rgba(0,0,0,0.2); }}
        .stat p {{ margin: 10px 0 0 0; font-size: 1.1em; opacity: 0.9; }}
        h2 {{ color: #444; margin-top: 40px; }}
        .test {{ border: 1px solid #e0e0e0; margin: 15px 0; border-radius: 12px; overflow: hidden; transition: box-shadow 0.3s; }}
        .test:hover {{ box-shadow: 0 5px 20px rgba(0,0,0,0.1); }}
        .test-header {{ padding: 15px 20px; display: flex; align-items: center; gap: 15px; cursor: pointer; }}
        .test-header.passed {{ background: linear-gradient(90deg, #e8f5e9, white); border-left: 5px solid #4CAF50; }}
        .test-header.failed {{ background: linear-gradient(90deg, #ffebee, white); border-left: 5px solid #f44336; }}
        .test-name {{ font-weight: 600; flex: 1; color: #333; }}
        .test-status {{ padding: 6px 16px; border-radius: 20px; color: white; font-weight: 600; font-size: 0.85em; }}
        .test-status.passed {{ background: #4CAF50; }}
        .test-status.failed {{ background: #f44336; }}
        .test-details {{ padding: 20px; background: #fafafa; display: none; }}
        .test-details.show {{ display: block; }}
        .test-details p {{ margin: 8px 0; color: #555; }}
        .test-details pre {{ background: #263238; color: #aed581; padding: 15px; border-radius: 8px; overflow-x: auto; font-size: 0.9em; }}
        .timestamp {{ color: #666; font-size: 14px; margin-bottom: 20px; }}
        .progress-bar {{ height: 10px; background: #e0e0e0; border-radius: 5px; overflow: hidden; margin: 20px 0; }}
        .progress-fill {{ height: 100%; background: linear-gradient(90deg, #11998e, #38ef7d); transition: width 0.5s; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>HydroClaude API E2E 测试报告</h1>

        <p class="timestamp">
            <strong>开始时间:</strong> {test_results.get('start_time', 'N/A')}<br>
            <strong>结束时间:</strong> {test_results.get('end_time', 'N/A')}
        </p>

        <div class="progress-bar">
            <div class="progress-fill" style="width: {passed_rate}%"></div>
        </div>

        <div class="summary">
            <div class="stat total">
                <h2>{test_results['total_tests']}</h2>
                <p>总测试数</p>
            </div>
            <div class="stat passed">
                <h2>{test_results['passed']}</h2>
                <p>通过</p>
            </div>
            <div class="stat failed">
                <h2>{test_results['failed']}</h2>
                <p>失败</p>
            </div>
            <div class="stat rate">
                <h2>{passed_rate:.1f}%</h2>
                <p>通过率</p>
            </div>
        </div>

        <h2>测试详情</h2>
"""

    for i, test in enumerate(test_results["tests"]):
        status = test["status"]
        response_json = ""
        if test.get("response"):
            try:
                response_json = test["response"][:500]
            except:
                response_json = str(test.get("response", ""))[:500]

        html_content += f"""
        <div class="test" onclick="this.querySelector('.test-details').classList.toggle('show')">
            <div class="test-header {status}">
                <span class="test-name">{test['name']}</span>
                <span class="test-status {status}">{status.upper()}</span>
            </div>
            <div class="test-details">
                <p><strong>详情:</strong> {test.get('details', 'N/A')}</p>
                <p><strong>时间:</strong> {test.get('timestamp', 'N/A')}</p>
                {"<pre>" + response_json + "</pre>" if response_json else ""}
            </div>
        </div>
"""

    html_content += """
    </div>
    <script>
        // 自动展开失败的测试
        document.querySelectorAll('.test-header.failed').forEach(el => {
            el.parentElement.querySelector('.test-details').classList.add('show');
        });
    </script>
</body>
</html>
"""

    with open(html_report, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"\n  JSON 报告: {report_file}")
    print(f"  HTML 报告: {html_report}")
    print(f"\n  总测试数: {test_results['total_tests']}")
    print(f"  通过: {test_results['passed']}")
    print(f"  失败: {test_results['failed']}")
    print(f"  通过率: {passed_rate:.1f}%")


async def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*70)
    print("HydroClaude API 端到端测试")
    print("="*70)

    test_results["start_time"] = datetime.now().isoformat()

    print(f"\n后端地址: {BACKEND_URL}")
    print(f"前端地址: {FRONTEND_URL}")
    print(f"报告目录: {REPORT_DIR}")

    # 运行测试
    await test_backend_health()
    await test_structures_api()
    await test_simulation_api()
    await test_reservoir_api()
    await test_network_api()
    await test_analysis_api()
    await test_test_cases_api()
    await test_frontend()
    await test_full_workflow()

    # 生成报告
    generate_report()

    print("\n" + "="*70)
    print("测试完成!")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(run_all_tests())
