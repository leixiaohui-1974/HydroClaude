#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
检查OpenAPI规范，查看实际注册的路由
"""

import requests
import json

BACKEND_URL = "http://localhost:8000"

print("=" * 80)
print("Checking OpenAPI Specification")
print("=" * 80)

try:
    response = requests.get(f"{BACKEND_URL}/openapi.json")
    spec = response.json()
    
    print(f"\nAPI Title: {spec.get('info', {}).get('title')}")
    print(f"Version: {spec.get('info', {}).get('version')}")
    
    paths = spec.get('paths', {})
    print(f"\nTotal Endpoints: {len(paths)}")
    print("\nRegistered Endpoints:")
    print("-" * 80)
    
    for path, methods in sorted(paths.items()):
        for method in methods.keys():
            if method != 'parameters':
                print(f"  {method.upper():8} {path}")
    
    print("\n" + "=" * 80)
    print("Analysis")
    print("=" * 80)
    
    api_v1_paths = [p for p in paths.keys() if p.startswith('/api/v1')]
    print(f"\n/api/v1 endpoints: {len(api_v1_paths)}")
    for p in api_v1_paths:
        print(f"  - {p}")
    
    if not api_v1_paths:
        print("\n[PROBLEM] No /api/v1 endpoints found!")
        print("This explains why frontend is getting 404 errors.")
    
    # Save full spec for reference
    with open('openapi_spec.json', 'w', encoding='utf-8') as f:
        json.dump(spec, f, indent=2, ensure_ascii=False)
    print("\nFull spec saved to: openapi_spec.json")
    
except Exception as e:
    print(f"\n[ERROR] {e}")
    import traceback
    traceback.print_exc()







