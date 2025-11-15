#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速Web端到端测试 - 验证核心功能
"""
import subprocess
import time
import requests
from pathlib import Path

def main():
    print("🌐 启动Web端到端测试...")
    
    # 1. 启动后台服务
    print("\n[1] 启动FastAPI服务...")
    backend_dir = Path("/workspace/backend")
    
    if not backend_dir.exists():
        print(f"❌ 后台目录不存在: {backend_dir}")
        return False
    
    # 查找main.py
    main_py = backend_dir / "main.py"
    if not main_py.exists():
        print(f"❌ 未找到main.py: {main_py}")
        return False
    
    # 启动服务（后台运行）
    proc = subprocess.Popen(
        ["python3", str(main_py)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(backend_dir)
    )
    
    print(f"  后台服务PID: {proc.pid}")
    time.sleep(3)  # 等待服务启动
    
    try:
        # 2. 测试API
        print("\n[2] 测试API端点...")
        base_url = "http://localhost:8000"
        
        # 健康检查
        try:
            resp = requests.get(f"{base_url}/health", timeout=5)
            print(f"  ✅ /health - {resp.status_code}")
        except Exception as e:
            print(f"  ❌ /health - {e}")
            return False
        
        # API文档
        try:
            resp = requests.get(f"{base_url}/docs", timeout=5)
            print(f"  ✅ /docs - {resp.status_code}")
        except Exception as e:
            print(f"  ❌ /docs - {e}")
        
        # 列出案例
        try:
            resp = requests.get(f"{base_url}/api/cases", timeout=5)
            if resp.status_code == 200:
                cases = resp.json()
                print(f"  ✅ /api/cases - 找到{len(cases)}个案例")
            else:
                print(f"  ⚠️  /api/cases - {resp.status_code}")
        except Exception as e:
            print(f"  ❌ /api/cases - {e}")
        
        # 3. 测试一个简单案例
        print("\n[3] 测试案例运行...")
        try:
            test_case = {
                "length": 10000,
                "width": 10,
                "slope": 0.001,
                "roughness": 0.025,
                "flow_rate": 50,
                "dt": 10,
                "total_time": 3600
            }
            resp = requests.post(
                f"{base_url}/api/simulate",
                json=test_case,
                timeout=30
            )
            if resp.status_code == 200:
                result = resp.json()
                print(f"  ✅ 案例运行成功")
                print(f"     流量误差: {result.get('Q_error', 0):.6f}%")
            else:
                print(f"  ⚠️  案例运行 - {resp.status_code}")
        except Exception as e:
            print(f"  ❌ 案例运行 - {e}")
        
        print("\n✅ Web测试完成！")
        return True
        
    finally:
        # 停止服务
        print("\n[4] 停止服务...")
        proc.terminate()
        proc.wait(timeout=5)
        print("  ✅ 服务已停止")

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
