#!/usr/bin/env python3
"""
错误处理测试
测试API的错误处理能力和鲁棒性
"""

import requests
import json
import time

API_BASE = "http://localhost:8000"
API_V1 = f"{API_BASE}/api/v1"

test_count = 0
passed_count = 0
failed_count = 0


def log_test(name, passed, expected, actual):
    """记录测试结果"""
    global test_count, passed_count, failed_count
    test_count += 1

    status = " PASS" if passed else " FAIL"
    print(f"{status} {name}")
    print(f"    期望: {expected}")
    print(f"    实际: {actual}")

    if passed:
        passed_count += 1
    else:
        failed_count += 1


def test_invalid_parameters():
    """测试无效参数"""
    print("\n" + "=" * 80)
    print("测试1: 无效参数处理")
    print("=" * 80)

    # 1.1 负数宽度
    print("\n[1.1] 负数宽度")
    response = requests.post(
        f"{API_V1}/simulations",
        json={
            "name": "错误测试-负数宽度",
            "config": {
                "width": -10.0,  #  无效
                "length": 1000.0,
                "n_cells": 100,
                "t_end": 10.0,
                "slope": 0.001,
                "manning_n": 0.025,
                "initial_conditions": {"type": "uniform", "h": 5.0, "Q": 0.0},
                "boundary_conditions": {
                    "left": {"type": "Q", "value": 10.0},
                    "right": {"type": "h", "value": 5.0}
                }
            }
        }
    )

    log_test(
        "负数宽度拒绝",
        response.status_code in [400, 422],
        "400/422",
        response.status_code
    )

    # 1.2 零长度
    print("\n[1.2] 零长度")
    response = requests.post(
        f"{API_V1}/simulations",
        json={
            "name": "错误测试-零长度",
            "config": {
                "width": 10.0,
                "length": 0.0,  #  无效
                "n_cells": 100,
                "t_end": 10.0,
                "slope": 0.001,
                "manning_n": 0.025,
                "initial_conditions": {"type": "uniform", "h": 5.0, "Q": 0.0},
                "boundary_conditions": {
                    "left": {"type": "Q", "value": 10.0},
                    "right": {"type": "h", "value": 5.0}
                }
            }
        }
    )

    log_test(
        "零长度拒绝",
        response.status_code in [400, 422],
        "400/422",
        response.status_code
    )

    # 1.3 过小网格数
    print("\n[1.3] 过小网格数")
    response = requests.post(
        f"{API_V1}/simulations",
        json={
            "name": "错误测试-网格数过小",
            "config": {
                "width": 10.0,
                "length": 1000.0,
                "n_cells": 5,  #  太少
                "t_end": 10.0,
                "slope": 0.001,
                "manning_n": 0.025,
                "initial_conditions": {"type": "uniform", "h": 5.0, "Q": 0.0},
                "boundary_conditions": {
                    "left": {"type": "Q", "value": 10.0},
                    "right": {"type": "h", "value": 5.0}
                }
            }
        }
    )

    log_test(
        "网格数过小拒绝",
        response.status_code in [400, 422],
        "400/422",
        response.status_code
    )

    # 1.4 负数曼宁系数
    print("\n[1.4] 负数曼宁系数")
    response = requests.post(
        f"{API_V1}/simulations",
        json={
            "name": "错误测试-负数曼宁系数",
            "config": {
                "width": 10.0,
                "length": 1000.0,
                "n_cells": 100,
                "t_end": 10.0,
                "slope": 0.001,
                "manning_n": -0.025,  #  无效
                "initial_conditions": {"type": "uniform", "h": 5.0, "Q": 0.0},
                "boundary_conditions": {
                    "left": {"type": "Q", "value": 10.0},
                    "right": {"type": "h", "value": 5.0}
                }
            }
        }
    )

    log_test(
        "负数曼宁系数拒绝",
        response.status_code in [400, 422],
        "400/422",
        response.status_code
    )


def test_missing_fields():
    """测试缺失字段"""
    print("\n" + "=" * 80)
    print("测试2: 缺失必要字段")
    print("=" * 80)

    # 2.1 缺失width
    print("\n[2.1] 缺失width字段")
    response = requests.post(
        f"{API_V1}/simulations",
        json={
            "name": "错误测试-缺失width",
            "config": {
                # "width": 10.0,  #  缺失
                "length": 1000.0,
                "n_cells": 100,
                "t_end": 10.0,
                "slope": 0.001,
                "manning_n": 0.025,
                "initial_conditions": {"type": "uniform", "h": 5.0, "Q": 0.0},
                "boundary_conditions": {
                    "left": {"type": "Q", "value": 10.0},
                    "right": {"type": "h", "value": 5.0}
                }
            }
        }
    )

    log_test(
        "缺失width拒绝",
        response.status_code in [400, 422],
        "400/422",
        response.status_code
    )

    # 2.2 缺失边界条件
    print("\n[2.2] 缺失边界条件")
    response = requests.post(
        f"{API_V1}/simulations",
        json={
            "name": "错误测试-缺失边界条件",
            "config": {
                "width": 10.0,
                "length": 1000.0,
                "n_cells": 100,
                "t_end": 10.0,
                "slope": 0.001,
                "manning_n": 0.025,
                "initial_conditions": {"type": "uniform", "h": 5.0, "Q": 0.0},
                # "boundary_conditions": {...}  #  缺失
            }
        }
    )

    log_test(
        "缺失边界条件拒绝",
        response.status_code in [400, 422],
        "400/422",
        response.status_code
    )


def test_nonexistent_resources():
    """测试不存在的资源"""
    print("\n" + "=" * 80)
    print("测试3: 不存在的资源")
    print("=" * 80)

    # 3.1 不存在的任务ID
    print("\n[3.1] 查询不存在的任务")
    fake_task_id = "00000000-0000-0000-0000-000000000000"
    response = requests.get(
        f"{API_V1}/simulations/{fake_task_id}/status"
    )

    log_test(
        "不存在任务返回404",
        response.status_code == 404,
        "404",
        response.status_code
    )

    # 3.2 不存在的任务结果
    print("\n[3.2] 获取不存在任务的结果")
    response = requests.get(
        f"{API_V1}/simulations/{fake_task_id}/results"
    )

    log_test(
        "不存在任务结果返回404",
        response.status_code == 404,
        "404",
        response.status_code
    )


def test_invalid_json():
    """测试无效JSON"""
    print("\n" + "=" * 80)
    print("测试4: 无效JSON格式")
    print("=" * 80)

    print("\n[4.1] 发送无效JSON")
    response = requests.post(
        f"{API_V1}/simulations",
        data="这不是有效的JSON{]",  #  无效JSON
        headers={"Content-Type": "application/json"}
    )

    log_test(
        "无效JSON拒绝",
        response.status_code in [400, 422],
        "400/422",
        response.status_code
    )


def test_boundary_values():
    """测试边界值"""
    print("\n" + "=" * 80)
    print("测试5: 边界值测试")
    print("=" * 80)

    # 5.1 极大网格数
    print("\n[5.1] 极大网格数")
    response = requests.post(
        f"{API_V1}/simulations",
        json={
            "name": "边界测试-极大网格",
            "config": {
                "width": 10.0,
                "length": 100000.0,
                "n_cells": 100000,  # 非常大
                "t_end": 10.0,
                "slope": 0.001,
                "manning_n": 0.025,
                "initial_conditions": {"type": "uniform", "h": 5.0, "Q": 0.0},
                "boundary_conditions": {
                    "left": {"type": "Q", "value": 10.0},
                    "right": {"type": "h", "value": 5.0}
                }
            }
        }
    )

    # 可能拒绝（422）或接受但排队（201）
    accepted = response.status_code == 201
    rejected = response.status_code in [400, 422]

    log_test(
        "极大网格数处理",
        accepted or rejected,
        "201（接受） 或 400/422（拒绝）",
        response.status_code
    )

    # 如果接受了，立即取消（避免长时间运行）
    if accepted:
        task_id = response.json().get('task_id')
        print(f"    注意: 大规模仿真已创建 ({task_id[:8]}...)，建议实现取消功能")


def print_summary():
    """打印测试总结"""
    print("\n" + "=" * 80)
    print("错误处理测试总结")
    print("=" * 80)

    pass_rate = (passed_count / test_count * 100) if test_count > 0 else 0

    print(f"\n总测试数: {test_count}")
    print(f" 通过: {passed_count}")
    print(f" 失败: {failed_count}")
    print(f"通过率: {pass_rate:.1f}%")

    if failed_count == 0:
        print("\n 所有错误处理测试通过！API具有良好的鲁棒性")
    else:
        print(f"\n️  有{failed_count}个测试失败，需要改进错误处理")

    print("=" * 80)


def main():
    print("\n" + "=" * 80)
    print("HydroClaude Web - 错误处理测试")
    print("=" * 80)
    print(f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"API: {API_BASE}")

    # 健康检查
    print(f"\n[0] 健康检查...")
    try:
        health = requests.get(f"{API_BASE}/health", timeout=5).json()
        print(f" 后端正常: {health.get('service')}")
    except Exception as e:
        print(f" 后端异常: {e}")
        return 1

    # 运行测试
    try:
        test_invalid_parameters()
        test_missing_fields()
        test_nonexistent_resources()
        test_invalid_json()
        test_boundary_values()
    except Exception as e:
        print(f"\n 测试执行异常: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # 打印总结
    print_summary()

    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    exit(main())
