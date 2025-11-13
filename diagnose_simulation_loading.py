#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
诊断仿真页面loading问题
"""

import requests
import json

BACKEND_URL = "http://localhost:8000"

print("=" * 80)
print("Diagnosing Simulation Page Loading Issue")
print("=" * 80)

# 测试1: 健康检查
print("\n[Test 1] Health Check...")
try:
    response = requests.get(f"{BACKEND_URL}/health", timeout=5)
    print(f"  Status: {response.status_code}")
    print(f"  Response: {response.json()}")
except Exception as e:
    print(f"  [ERROR] {e}")

# 测试2: 根路径
print("\n[Test 2] Root endpoint...")
try:
    response = requests.get(f"{BACKEND_URL}/", timeout=5)
    print(f"  Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"  Message: {data.get('message')}")
        print(f"  Version: {data.get('version')}")
except Exception as e:
    print(f"  [ERROR] {e}")

# 测试3: Engine Info
print("\n[Test 3] Engine Info endpoint...")
try:
    response = requests.get(f"{BACKEND_URL}/api/v1/engine/info", timeout=5)
    print(f"  Status: {response.status_code}")
    if response.status_code == 200:
        print(f"  Response: {json.dumps(response.json(), indent=2)}")
    else:
        print(f"  Error: {response.text}")
except Exception as e:
    print(f"  [ERROR] {e}")

# 测试4: List Simulations
print("\n[Test 4] List Simulations...")
try:
    response = requests.get(f"{BACKEND_URL}/api/v1/simulations", timeout=5)
    print(f"  Status: {response.status_code}")
    if response.status_code == 200:
        sims = response.json()
        print(f"  Simulations count: {len(sims)}")
    else:
        print(f"  Error: {response.text}")
except Exception as e:
    print(f"  [ERROR] {e}")

# 测试5: 列出所有可用端点
print("\n[Test 5] Try to discover endpoints...")
common_paths = [
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api",
    "/api/v1",
]

for path in common_paths:
    try:
        response = requests.get(f"{BACKEND_URL}{path}", timeout=2)
        if response.status_code != 404:
            print(f"  {path} -> {response.status_code}")
    except:
        pass

print("\n" + "=" * 80)
print("Diagnosis Complete")
print("=" * 80)

print("\nRecommendations:")
print("1. If /api/v1/engine/info returns 404:")
print("   -> Check routers are registered in main.py")
print("2. Check browser console for JavaScript errors")
print("3. Check browser Network tab for failed API calls")







