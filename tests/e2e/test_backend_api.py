#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试后端API"""
import requests
import json

def test_backend_api():
    print("测试后端API /api/structures/simulate-canal-with-structure")
    print("=" * 60)
    
    request = {
        "simulation_type": "steady",
        "canal": {
            "length": 1000.0,
            "width": 10.0,
            "slope": 0.001,
            "manning_n": 0.015,
            "grid_nx": 100
        },
        "structure_type": "none",
        "structure": {
            "position": 0,
            "parameters": {}
        },
        "boundaries": {
            "upstream": {"type": "Q", "value": 50.0},
            "downstream": {"type": "h", "value": 3.0}
        },
        "metadata": {
            "title": "API直接测试",
            "description": "测试后端仿真API"
        }
    }
    
    print("发送请求...")
    try:
        response = requests.post(
            "http://localhost:8000/api/structures/simulate-canal-with-structure",
            json=request,
            timeout=60
        )
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"任务ID: {data.get('task_id')}")
            print(f"状态: {data.get('status')}")
            print(f"仿真时间: {data.get('simulation_time_ms', 0):.1f}ms")
            
            if data.get("results"):
                results = data["results"]
                print(f"结果包含字段: {list(results.keys())[:10]}")
                
                # 显示一些关键数据
                if "h" in results:
                    h_data = results["h"]
                    if isinstance(h_data, list) and len(h_data) > 0:
                        print(f"水深数据点数: {len(h_data)}")
                        if isinstance(h_data[0], list):
                            # 2D数据 (时间 x 空间)
                            all_h = [v for row in h_data for v in row if isinstance(v, (int, float))]
                            print(f"水深范围: [{min(all_h):.3f}, {max(all_h):.3f}] m")
                        elif isinstance(h_data[0], (int, float)):
                            print(f"水深范围: [{min(h_data):.3f}, {max(h_data):.3f}] m")
                
                if "Q" in results:
                    Q_data = results["Q"]
                    if isinstance(Q_data, list) and len(Q_data) > 0:
                        print(f"流量数据点数: {len(Q_data)}")
                        if isinstance(Q_data[0], list):
                            all_Q = [v for row in Q_data for v in row if isinstance(v, (int, float))]
                            print(f"流量范围: [{min(all_Q):.3f}, {max(all_Q):.3f}] m3/s")
                        elif isinstance(Q_data[0], (int, float)):
                            print(f"流量范围: [{min(Q_data):.3f}, {max(Q_data):.3f}] m3/s")
                
                if "metrics" in results:
                    metrics = results["metrics"]
                    print(f"\n仿真指标:")
                    for key, value in metrics.items():
                        if value is not None:
                            print(f"  {key}: {value}")
                
                # 检查前端期望的字段
                print(f"\n前端期望的字段检查:")
                required_fields = ["task_id", "status", "time", "x", "h", "Q", "V", "duration", "timestamp"]
                for field in required_fields:
                    if field in results:
                        val = results[field]
                        if isinstance(val, list):
                            print(f"  {field}: list with {len(val)} elements")
                        else:
                            print(f"  {field}: {val}")
                    else:
                        print(f"  {field}: MISSING!")
                
                required_metrics = [
                    "total_iterations", "mass_conservation_error", "converged",
                    "max_depth", "min_depth", "max_velocity", "max_froude",
                    "mean_depth_final", "mean_discharge_final"
                ]
                print(f"\n前端期望的metrics字段:")
                for metric in required_metrics:
                    if metrics.get(metric) is not None:
                        print(f"  {metric}: {metrics[metric]}")
                    else:
                        print(f"  {metric}: MISSING!")
            
            print("\n后端API正常工作!")
            return True
        else:
            print(f"错误: {response.text[:500]}")
            return False
            
    except Exception as e:
        print(f"请求失败: {e}")
        return False

if __name__ == "__main__":
    test_backend_api()

