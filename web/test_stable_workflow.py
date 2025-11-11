#!/usr/bin/env python3
"""
稳定的完整工作流测试
使用更保守的参数确保数值稳定性
"""

import requests
import json
import time

API_BASE = "http://localhost:8000"
API_V1 = f"{API_BASE}/api/v1"

def test_stable_simulation():
    """测试数值稳定的仿真配置"""
    print("=" * 80)
    print("稳定工作流测试 - 使用保守参数")
    print("=" * 80)

    # 使用更保守的配置
    stable_config = {
        "name": "稳定性测试 - 小流量稳态流",
        "description": "测试数值稳定性",
        "config": {
            "width": 10.0,
            "length": 1000.0,
            "n_cells": 100,
            "t_end": 30.0,  # 缩短模拟时间
            "cfl": 0.3,     # 降低CFL数提高稳定性
            "slope": 0.001,
            "manning_n": 0.025,
            "order": 1,     # 使用1阶格式提高稳定性
            "use_numba": True,
            "well_balanced": False,  # 底坡不大，不需要Well-Balanced
            "initial_conditions": {
                "type": "uniform",
                "h": 5.0,
                "Q": 20.0   # 使用较小的初始流量
            },
            "boundary_conditions": {
                "left": {
                    "type": "Q",
                    "value": 20.0   # 保持与初始流量一致
                },
                "right": {
                    "type": "h",
                    "value": 5.0    # 保持与初始水深一致
                }
            }
        }
    }

    print(f"\n配置参数:")
    print(f"  网格数: {stable_config['config']['n_cells']}")
    print(f"  模拟时间: {stable_config['config']['t_end']}s")
    print(f"  CFL数: {stable_config['config']['cfl']}")
    print(f"  精度: {stable_config['config']['order']}阶")
    print(f"  初始流量: {stable_config['config']['initial_conditions']['Q']} m³/s")

    # 1. 创建仿真
    print(f"\n[1/4] 创建仿真任务...")
    response = requests.post(
        f"{API_V1}/simulations",
        json=stable_config,
        timeout=10
    )

    if response.status_code != 201:
        print(f"❌ 创建失败: {response.status_code}")
        print(response.text)
        return False

    task_data = response.json()
    task_id = task_data['task_id']
    print(f"✅ 任务创建成功: {task_id[:8]}...")

    # 2. 等待完成
    print(f"\n[2/4] 等待仿真完成...")
    max_wait = 60
    wait_time = 0
    interval = 2

    while wait_time < max_wait:
        status_response = requests.get(
            f"{API_V1}/simulations/{task_id}/status",
            timeout=5
        )
        status_data = status_response.json()
        status = status_data['status']
        progress = status_data.get('progress', 0)

        print(f"  状态: {status:12s} 进度: {progress:5.1f}%", end='\r')

        if status == 'completed':
            duration = status_data.get('duration', 0)
            print(f"\n✅ 仿真完成! 耗时: {duration:.3f}秒")
            break
        elif status == 'failed':
            error = status_data.get('error', 'Unknown')
            print(f"\n❌ 仿真失败: {error}")
            return False

        time.sleep(interval)
        wait_time += interval

    if wait_time >= max_wait:
        print(f"\n❌ 超时（{max_wait}秒）")
        return False

    # 3. 获取结果
    print(f"\n[3/4] 获取仿真结果...")
    results_response = requests.get(
        f"{API_V1}/simulations/{task_id}/results",
        timeout=10
    )

    if results_response.status_code != 200:
        print(f"❌ 获取结果失败: {results_response.status_code}")
        return False

    results = results_response.json()
    print(f"✅ 结果获取成功")

    # 4. 验证结果
    print(f"\n[4/4] 验证结果数据...")

    # 检查必要字段
    required_fields = ['x', 'time', 'h', 'Q', 'V', 'metrics', 'status']
    missing_fields = [f for f in required_fields if f not in results]

    if missing_fields:
        print(f"❌ 缺少字段: {missing_fields}")
        return False

    print(f"✅ 数据结构完整")
    print(f"  时间步数: {len(results['time'])}")
    print(f"  空间点数: {len(results['x'])}")

    # 检查物理指标
    metrics = results['metrics']

    print(f"\n物理指标:")
    print(f"  质量守恒误差: {metrics.get('mass_conservation_error', 0)*100:.6f}%")
    print(f"  最大Froude数: {metrics.get('max_froude', 0):.4f}")
    print(f"  最小水深: {metrics.get('min_depth', 0):.4f} m")
    print(f"  最大水深: {metrics.get('max_depth', 0):.4f} m")
    print(f"  平均流量(终态): {metrics.get('mean_discharge_final', 0):.4f} m³/s")

    # 验证物理合理性
    mass_error = abs(metrics.get('mass_conservation_error', 1.0))
    max_froude = metrics.get('max_froude', 0)
    min_depth = metrics.get('min_depth', -1)

    checks = [
        ("质量守恒", mass_error < 0.05, f"{mass_error*100:.4f}%"),
        ("Froude数合理", 0 < max_froude < 2.0, f"{max_froude:.4f}"),
        ("水深非负", min_depth >= 0, f"{min_depth:.4f} m"),
    ]

    print(f"\n验证检查:")
    all_passed = True
    for name, passed, value in checks:
        status = "✅" if passed else "❌"
        print(f"  {status} {name}: {value}")
        if not passed:
            all_passed = False

    return all_passed


def main():
    print("\n" + "=" * 80)
    print("HydroClaude Web - 稳定工作流测试")
    print("=" * 80)
    print(f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"API: {API_BASE}")

    # 健康检查
    print(f"\n[0] 健康检查...")
    try:
        health = requests.get(f"{API_BASE}/health", timeout=5).json()
        print(f"✅ 后端正常: {health.get('service')}")
    except Exception as e:
        print(f"❌ 后端异常: {e}")
        return 1

    # 运行测试
    success = test_stable_simulation()

    # 总结
    print("\n" + "=" * 80)
    if success:
        print("🎉 测试通过！工作流正常运行")
        print("=" * 80)
        return 0
    else:
        print("⚠️  测试失败，请检查上述错误")
        print("=" * 80)
        return 1


if __name__ == "__main__":
    exit(main())
