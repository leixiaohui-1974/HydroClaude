#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
API Integration Test - 测试案例集成API测试
验证后端API是否正常工作

Features tested:
1. GET /api/v1/test-cases/ - 获取测试案例列表
2. GET /api/v1/test-cases/statistics - 获取统计信息
3. GET /api/v1/test-cases/search - 搜索测试案例
4. GET /api/v1/test-cases/categories - 获取分类信息

Author: HydroClaude Team
Date: 2025-11-13
"""

import requests
import json
import time


def test_api():
    """测试API功能"""
    base_url = "http://localhost:8000"
    
    print("="*70)
    print(" API Integration Test - 测试案例集成API测试 ".center(70))
    print("="*70)
    print()
    
    # 等待服务器启动
    print("Waiting for server to start...")
    for i in range(10):
        try:
            response = requests.get(f"{base_url}/", timeout=2)
            print("[OK] Server is running!")
            break
        except requests.exceptions.RequestException:
            print(f"  Attempt {i+1}/10: Server not ready yet...")
            time.sleep(2)
    else:
        print("[ERROR] Server failed to start!")
        return
    
    print()
    
    # Test 1: 获取统计信息
    print("Test 1: GET /api/v1/test-cases/statistics")
    print("-" * 70)
    try:
        response = requests.get(f"{base_url}/api/v1/test-cases/statistics")
        if response.status_code == 200:
            data = response.json()
            print("[OK] Success!")
            print(f"  Total Cases: {data.get('total', 0)}")
            print(f"  Categories: {len(data.get('categories', {}))}")
            print(f"  Difficulties: {data.get('difficulty', {})}")
            print(f"  Top Tags: {list(data.get('topTags', {}).keys())[:5]}")
        else:
            print(f"[ERROR] Failed with status {response.status_code}")
            print(f"  Response: {response.text}")
    except Exception as e:
        print(f"[ERROR] Error: {e}")
    
    print()
    
    # Test 2: 获取案例列表（前10个）
    print("Test 2: GET /api/v1/test-cases?limit=10")
    print("-" * 70)
    try:
        response = requests.get(f"{base_url}/api/v1/test-cases/?limit=10")
        if response.status_code == 200:
            data = response.json()
            print("[OK] Success!")
            print(f"  Total: {data.get('total', 0)}")
            print(f"  Returned: {len(data.get('cases', []))}")
            if data.get('cases'):
                first_case = data['cases'][0]
                print(f"  First Case:")
                print(f"    - ID: {first_case.get('metadata', {}).get('id', 'N/A')}")
                print(f"    - Name: {first_case.get('metadata', {}).get('name', 'N/A')}")
                print(f"    - Category: {first_case.get('metadata', {}).get('category', 'N/A')}")
        else:
            print(f"[ERROR] Failed with status {response.status_code}")
            print(f"  Response: {response.text}")
    except Exception as e:
        print(f"[ERROR] Error: {e}")
    
    print()
    
    # Test 3: 搜索测试案例
    print("Test 3: GET /api/v1/test-cases/search?q=dam")
    print("-" * 70)
    try:
        response = requests.get(f"{base_url}/api/v1/test-cases/search?q=dam")
        if response.status_code == 200:
            data = response.json()
            print("[OK] Success!")
            print(f"  Found: {data.get('total', 0)} cases")
            if data.get('cases'):
                for i, case in enumerate(data['cases'][:3], 1):
                    print(f"  {i}. {case.get('metadata', {}).get('name', 'N/A')} "
                          f"({case.get('metadata', {}).get('category', 'N/A')})")
        else:
            print(f"[ERROR] Failed with status {response.status_code}")
            print(f"  Response: {response.text}")
    except Exception as e:
        print(f"[ERROR] Error: {e}")
    
    print()
    
    # Test 4: 获取分类信息
    print("Test 4: GET /api/v1/test-cases/categories")
    print("-" * 70)
    try:
        response = requests.get(f"{base_url}/api/v1/test-cases/categories")
        if response.status_code == 200:
            data = response.json()
            print("[OK] Success!")
            print(f"  Categories:")
            for cat, count in list(data.items())[:10]:
                print(f"    - {cat}: {count} cases")
        else:
            print(f"[ERROR] Failed with status {response.status_code}")
            print(f"  Response: {response.text}")
    except Exception as e:
        print(f"[ERROR] Error: {e}")
    
    print()
    
    # Test 5: 按分类筛选
    print("Test 5: GET /api/v1/test-cases?category=dam_break&limit=5")
    print("-" * 70)
    try:
        response = requests.get(f"{base_url}/api/v1/test-cases/?category=dam_break&limit=5")
        if response.status_code == 200:
            data = response.json()
            print("[OK] Success!")
            print(f"  Dam Break Cases: {data.get('total', 0)}")
            for i, case in enumerate(data.get('cases', []), 1):
                print(f"  {i}. {case.get('metadata', {}).get('name', 'N/A')}")
        else:
            print(f"[ERROR] Failed with status {response.status_code}")
            print(f"  Response: {response.text}")
    except Exception as e:
        print(f"[ERROR] Error: {e}")
    
    print()
    print("="*70)
    print(" All Tests Completed! ".center(70))
    print("="*70)


if __name__ == '__main__':
    test_api()

