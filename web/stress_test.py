#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
压力测试和并发测试
测试API在高负载下的稳定性
"""

import requests
import json
import time
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

API_BASE = "http://localhost:8000"

class APIStressTester:
    def __init__(self):
        self.results = {
            'success': 0,
            'failed': 0,
            'total_time': 0,
            'errors': []
        }
        self.lock = threading.Lock()
    
    def single_request(self, endpoint, method="GET", payload=None):
        """单次请求"""
        try:
            start = time.time()
            if method == "GET":
                response = requests.get(f"{API_BASE}{endpoint}", timeout=5)
            else:
                response = requests.post(f"{API_BASE}{endpoint}", json=payload, timeout=5)
            elapsed = time.time() - start
            
            with self.lock:
                self.results['total_time'] += elapsed
                if response.status_code == 200:
                    self.results['success'] += 1
                    return True, elapsed
                else:
                    self.results['failed'] += 1
                    self.results['errors'].append({
                        'endpoint': endpoint,
                        'status': response.status_code,
                        'error': response.text[:100]
                    })
                    return False, elapsed
        except Exception as e:
            with self.lock:
                self.results['failed'] += 1
                self.results['errors'].append({
                    'endpoint': endpoint,
                    'error': str(e)
                })
            return False, 0
    
    def concurrent_test(self, endpoint, method, payload, num_requests, num_workers):
        """并发测试"""
        print(f"\n{'='*70}")
        print(f"并发测试: {endpoint}")
        print(f"请求数: {num_requests}, 并发数: {num_workers}")
        print(f"{'='*70}")
        
        self.results = {'success': 0, 'failed': 0, 'total_time': 0, 'errors': []}
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [
                executor.submit(self.single_request, endpoint, method, payload)
                for _ in range(num_requests)
            ]
            
            for future in as_completed(futures):
                pass
        
        total_time = time.time() - start_time
        
        print(f"\n结果:")
        print(f"  总请求数: {num_requests}")
        print(f"  成功: {self.results['success']}")
        print(f"  失败: {self.results['failed']}")
        print(f"  成功率: {self.results['success']/num_requests*100:.1f}%")
        print(f"  总耗时: {total_time:.2f}秒")
        print(f"  平均响应时间: {self.results['total_time']/num_requests*1000:.2f}ms")
        print(f"  QPS: {num_requests/total_time:.1f}")
        
        if self.results['errors']:
            print(f"\n错误详情 (前3个):")
            for err in self.results['errors'][:3]:
                print(f"  - {err}")
        
        return self.results['success'] == num_requests


def test_basic_stability():
    """基础稳定性测试 - 重复调用相同端点"""
    print("\n" + "="*70)
    print("测试1: 基础稳定性 - 健康检查端点")
    print("="*70)
    
    tester = APIStressTester()
    success = tester.concurrent_test(
        endpoint="/health",
        method="GET",
        payload=None,
        num_requests=50,
        num_workers=10
    )
    
    return success


def test_pump_stress():
    """泵站端点压力测试"""
    print("\n" + "="*70)
    print("测试2: 泵站仿真压力测试")
    print("="*70)
    
    payload = {
        "pump": {"flow_rate": 10.0, "head": 15.0, "num_pumps": 2, "pump_type": "parallel"},
        "upstream": {"water_level": 5.0},
        "downstream": {"elevation": 20.0},
        "operation": {"duration": 100.0}
    }
    
    tester = APIStressTester()
    success = tester.concurrent_test(
        endpoint="/api/structures/pump",
        method="POST",
        payload=payload,
        num_requests=30,
        num_workers=5
    )
    
    return success


def test_mixed_endpoints():
    """混合端点测试 - 模拟真实使用"""
    print("\n" + "="*70)
    print("测试3: 混合端点并发测试")
    print("="*70)
    
    endpoints = [
        ("/health", "GET", None),
        ("/api/structures/types", "GET", None),
        ("/api/structures/version", "GET", None),
        ("/api/structures/pump", "POST", {
            "pump": {"flow_rate": 10.0, "head": 15.0},
            "upstream": {"water_level": 5.0},
            "downstream": {"elevation": 20.0},
            "operation": {"duration": 100}
        }),
        ("/api/structures/gate", "POST", {
            "gate": {"type": "sluice", "width": 10.0, "opening": 2.0},
            "upstream": {"water_depth": 5.0},
            "downstream": {"water_depth": 2.0}
        }),
    ]
    
    tester = APIStressTester()
    tester.results = {'success': 0, 'failed': 0, 'total_time': 0, 'errors': []}
    
    start_time = time.time()
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = []
        for _ in range(20):  # 每个端点调用20次
            for endpoint, method, payload in endpoints:
                futures.append(
                    executor.submit(tester.single_request, endpoint, method, payload)
                )
        
        for future in as_completed(futures):
            pass
    
    total_time = time.time() - start_time
    total_requests = len(endpoints) * 20
    
    print(f"\n结果:")
    print(f"  总请求数: {total_requests}")
    print(f"  成功: {tester.results['success']}")
    print(f"  失败: {tester.results['failed']}")
    print(f"  成功率: {tester.results['success']/total_requests*100:.1f}%")
    print(f"  总耗时: {total_time:.2f}秒")
    print(f"  平均响应时间: {tester.results['total_time']/total_requests*1000:.2f}ms")
    print(f"  整体QPS: {total_requests/total_time:.1f}")
    
    return tester.results['success'] == total_requests


def test_edge_cases():
    """边界条件测试"""
    print("\n" + "="*70)
    print("测试4: 边界条件和错误处理")
    print("="*70)
    
    test_cases = [
        {
            "name": "无效参数",
            "endpoint": "/api/structures/pump",
            "payload": {"pump": {"flow_rate": -10}},  # 负流量
            "expect_error": True
        },
        {
            "name": "缺少必填字段",
            "endpoint": "/api/structures/pump",
            "payload": {"pump": {}},  # 缺少参数
            "expect_error": True
        },
        {
            "name": "不存在的端点",
            "endpoint": "/api/structures/nonexistent",
            "payload": {},
            "expect_error": True
        },
        {
            "name": "正常请求",
            "endpoint": "/api/structures/pump",
            "payload": {
                "pump": {"flow_rate": 10.0, "head": 15.0},
                "upstream": {"water_level": 5.0},
                "downstream": {"elevation": 20.0},
                "operation": {"duration": 100}
            },
            "expect_error": False
        }
    ]
    
    passed = 0
    for test in test_cases:
        try:
            response = requests.post(
                f"{API_BASE}{test['endpoint']}",
                json=test['payload'],
                timeout=5
            )
            
            is_error = response.status_code != 200
            if is_error == test['expect_error']:
                print(f"  ✅ {test['name']}: 符合预期 (状态码={response.status_code})")
                passed += 1
            else:
                print(f"  ❌ {test['name']}: 不符合预期 (状态码={response.status_code})")
        except Exception as e:
            if test['expect_error']:
                print(f"  ✅ {test['name']}: 符合预期 (异常: {type(e).__name__})")
                passed += 1
            else:
                print(f"  ❌ {test['name']}: 不符合预期 (异常: {e})")
    
    print(f"\n通过率: {passed}/{len(test_cases)} ({passed/len(test_cases)*100:.1f}%)")
    return passed == len(test_cases)


def main():
    print("="*70)
    print("🧪 HydroClaude API 压力测试和稳定性验证")
    print("="*70)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"目标: {API_BASE}")
    
    # 检查服务器
    try:
        response = requests.get(f"{API_BASE}/health", timeout=2)
        if response.status_code == 200:
            print("✅ 服务器正在运行\n")
        else:
            print("❌ 服务器异常")
            return False
    except:
        print("❌ 服务器未运行")
        return False
    
    # 运行测试
    results = []
    
    # 测试1: 基础稳定性
    results.append(("基础稳定性", test_basic_stability()))
    
    # 测试2: 泵站压力测试
    results.append(("泵站压力", test_pump_stress()))
    
    # 测试3: 混合端点
    results.append(("混合端点", test_mixed_endpoints()))
    
    # 测试4: 边界条件
    results.append(("边界条件", test_edge_cases()))
    
    # 总结
    print("\n" + "="*70)
    print("📊 压力测试总结")
    print("="*70)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    print(f"\n总测试数: {total}")
    print(f"通过: {passed}")
    print(f"失败: {total - passed}")
    print(f"通过率: {passed/total*100:.1f}%")
    
    print("\n详细结果:")
    for name, success in results:
        status = "✅" if success else "❌"
        print(f"  {status} {name}")
    
    print("\n" + "="*70)
    if passed == total:
        print("🎉 所有压力测试通过！系统稳定可靠！")
    else:
        print(f"⚠️ {total-passed}个测试失败")
    print("="*70)
    
    return passed == total


if __name__ == '__main__':
    import sys
    success = main()
    sys.exit(0 if success else 1)
