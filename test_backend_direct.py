#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
直接测试后端路由配置
"""

import sys
import os

# 添加路径
backend_path = os.path.join(os.path.dirname(__file__), 'web', 'backend')
sys.path.insert(0, backend_path)

print("=" * 80)
print("Testing Backend Configuration")
print("=" * 80)

# 测试1: 检查main.py是否可以导入
print("\n[Test 1] Import main.py...")
try:
    gateway_path = os.path.join(os.path.dirname(__file__), 'web', 'backend', 'api_gateway')
    sys.path.insert(0, gateway_path)
    from main import app
    print("[PASS] main.py imported successfully")
    print(f"  App title: {app.title}")
    print(f"  App version: {app.version}")
except Exception as e:
    print(f"[FAIL] Failed to import main.py: {e}")
    sys.exit(1)

# 测试2: 检查路由
print("\n[Test 2] Check registered routes...")
routes = []
for route in app.routes:
    if hasattr(route, 'path') and hasattr(route, 'methods'):
        routes.append({
            'path': route.path,
            'methods': list(route.methods) if route.methods else [],
            'name': route.name
        })

print(f"  Total routes: {len(routes)}")
for route in routes:
    print(f"  - {route['methods']} {route['path']} ({route['name']})")

# 测试3: 检查特定路由
print("\n[Test 3] Check specific API routes...")
api_routes = [r for r in routes if r['path'].startswith('/api/v1')]
print(f"  API routes: {len(api_routes)}")

engine_info = [r for r in routes if 'engine' in r['path']]
sim_routes = [r for r in routes if 'simulation' in r['path']]

print(f"  Engine routes: {len(engine_info)}")
for r in engine_info:
    print(f"    - {r['path']}")

print(f"  Simulation routes: {len(sim_routes)}")
for r in sim_routes:
    print(f"    - {r['path']}")

# 测试4: 测试导入simulation router
print("\n[Test 4] Test simulation router import...")
try:
    from routers import simulation_router
    print("[PASS] simulation_router imported")
    print(f"  Router prefix: {simulation_router.prefix if hasattr(simulation_router, 'prefix') else 'N/A'}")
except Exception as e:
    print(f"[FAIL] Failed to import simulation_router: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("Backend Configuration Test Complete")
print("=" * 80)

