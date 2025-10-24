#!/usr/bin/env python3
"""
快速验证脚本 - 测试所有新增案例

本脚本快速测试本版本新增的所有示例案例，确保它们正常工作。

运行方式：
    python examples/validate_new_examples.py

或者：
    cd examples && python validate_new_examples.py
"""

import sys
import os
from pathlib import Path
import subprocess
import time
from typing import List, Tuple, Dict

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class Colors:
    """终端颜色"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    """打印标题"""
    print()
    print("=" * 80)
    print(f"{Colors.BOLD}{text}{Colors.ENDC}")
    print("=" * 80)
    print()


def print_success(text: str):
    """打印成功信息"""
    print(f"{Colors.GREEN}✓{Colors.ENDC} {text}")


def print_error(text: str):
    """打印错误信息"""
    print(f"{Colors.RED}✗{Colors.ENDC} {text}")


def print_warning(text: str):
    """打印警告信息"""
    print(f"{Colors.YELLOW}⚠{Colors.ENDC} {text}")


def print_info(text: str):
    """打印信息"""
    print(f"{Colors.BLUE}ℹ{Colors.ENDC} {text}")


def run_test(name: str, command: List[str], cwd: Path = None, timeout: int = 120) -> Tuple[bool, float, str]:
    """
    运行单个测试

    Args:
        name: 测试名称
        command: 命令列表
        cwd: 工作目录
        timeout: 超时时间（秒）

    Returns:
        (success, elapsed_time, error_message)
    """
    print(f"\n{Colors.BOLD}测试: {name}{Colors.ENDC}")
    print(f"命令: {' '.join(command)}")

    start_time = time.time()

    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout
        )

        elapsed = time.time() - start_time

        if result.returncode == 0:
            print_success(f"通过 ({elapsed:.1f}s)")
            return True, elapsed, ""
        else:
            error_msg = result.stderr[-500:] if result.stderr else result.stdout[-500:]
            print_error(f"失败 ({elapsed:.1f}s)")
            print(f"错误信息: {error_msg}")
            return False, elapsed, error_msg

    except subprocess.TimeoutExpired:
        elapsed = time.time() - start_time
        print_error(f"超时 ({timeout}s)")
        return False, elapsed, f"Timeout after {timeout}s"

    except Exception as e:
        elapsed = time.time() - start_time
        print_error(f"异常 ({elapsed:.1f}s)")
        print(f"异常信息: {e}")
        return False, elapsed, str(e)


def main():
    """主函数"""

    print_header("HydroClaude 新增案例快速验证")

    print("本脚本将测试以下新增案例：")
    print()
    print("1. 工程案例库（3个）")
    print("2. 控制系统示例（2个）")
    print("3. 闸泵控制策略（3个）")
    print("4. 结构类型展示（1个）")
    print("5. 时变边界条件（3个）")
    print()
    print("总计: 12个测试")
    print()

    input("按Enter开始测试...")

    # 定义所有测试
    tests = [
        # 工程案例库
        {
            'category': '工程案例库',
            'tests': [
                {
                    'name': 'Case 1: 灌溉渠道设计',
                    'command': ['python', 'run.py'],
                    'cwd': project_root / 'examples/engineering_cases/case_01_irrigation_design',
                    'timeout': 30
                },
                {
                    'name': 'Case 2: 防洪应急响应',
                    'command': ['python', 'run.py'],
                    'cwd': project_root / 'examples/engineering_cases/case_02_flood_emergency',
                    'timeout': 60
                },
                {
                    'name': 'Case 3: 多闸门协同控制',
                    'command': ['python', 'run.py'],
                    'cwd': project_root / 'examples/engineering_cases/case_03_multi_gate_control',
                    'timeout': 120
                }
            ]
        },

        # 控制系统示例
        {
            'category': '控制系统示例',
            'tests': [
                {
                    'name': 'PID水位控制',
                    'command': ['python', '-m', 'modeling.universal_modeler',
                               'examples/example_control/config_pid_water_level.yaml'],
                    'cwd': project_root,
                    'timeout': 60
                },
                {
                    'name': 'MPC水位控制（调优版）',
                    'command': ['python', '-m', 'modeling.universal_modeler',
                               'examples/example_control/config_mpc_tuned.yaml'],
                    'cwd': project_root,
                    'timeout': 60
                }
            ]
        },

        # 闸泵控制策略
        {
            'category': '闸泵控制策略',
            'tests': [
                {
                    'name': 'Strategy 1: PID扰动响应',
                    'command': ['python', 'run_01_pid_disturbance.py'],
                    'cwd': project_root / 'examples/example_gate_pump_cascade/control_strategies',
                    'timeout': 60
                },
                {
                    'name': 'Strategy 2: MPC预测控制',
                    'command': ['python', 'run_02_mpc_predictive.py'],
                    'cwd': project_root / 'examples/example_gate_pump_cascade/control_strategies',
                    'timeout': 60
                },
                {
                    'name': 'Strategy 3: 分层控制',
                    'command': ['python', 'run_03_hierarchical.py'],
                    'cwd': project_root / 'examples/example_gate_pump_cascade/control_strategies',
                    'timeout': 60
                }
            ]
        },

        # 结构类型展示
        {
            'category': '结构类型展示',
            'tests': [
                {
                    'name': '7种结构类型综合展示',
                    'command': ['python', 'run.py'],
                    'cwd': project_root / 'examples/example_structure_showcase',
                    'timeout': 30
                }
            ]
        },

        # 时变边界条件
        {
            'category': '时变边界条件',
            'tests': [
                {
                    'name': 'Sinusoidal（正弦波动）',
                    'command': ['python', '-m', 'modeling.universal_modeler',
                               'examples/example_time_varying_bc/config_sinusoidal.yaml'],
                    'cwd': project_root,
                    'timeout': 60
                },
                {
                    'name': 'Step（阶跃变化）',
                    'command': ['python', '-m', 'modeling.universal_modeler',
                               'examples/example_time_varying_bc/config_step.yaml'],
                    'cwd': project_root,
                    'timeout': 60
                },
                {
                    'name': 'Linear（线性变化）',
                    'command': ['python', '-m', 'modeling.universal_modeler',
                               'examples/example_time_varying_bc/config_linear.yaml'],
                    'cwd': project_root,
                    'timeout': 60
                }
            ]
        }
    ]

    # 运行所有测试
    results: Dict[str, List[Tuple[str, bool, float]]] = {}
    total_tests = 0
    passed_tests = 0
    total_time = 0.0

    for category_info in tests:
        category = category_info['category']
        print_header(f"测试类别: {category}")

        results[category] = []

        for test in category_info['tests']:
            total_tests += 1
            success, elapsed, error = run_test(
                test['name'],
                test['command'],
                test.get('cwd'),
                test.get('timeout', 120)
            )

            results[category].append((test['name'], success, elapsed))
            total_time += elapsed

            if success:
                passed_tests += 1

    # 打印总结
    print_header("测试总结")

    print(f"总测试数: {total_tests}")
    print(f"通过: {passed_tests}")
    print(f"失败: {total_tests - passed_tests}")
    print(f"成功率: {passed_tests/total_tests*100:.1f}%")
    print(f"总耗时: {total_time:.1f}s")
    print()

    # 按类别显示结果
    print("按类别统计:")
    print()
    for category, category_results in results.items():
        passed = sum(1 for _, success, _ in category_results if success)
        total = len(category_results)
        print(f"{category}: {passed}/{total} 通过")

        for name, success, elapsed in category_results:
            status = f"{Colors.GREEN}✓{Colors.ENDC}" if success else f"{Colors.RED}✗{Colors.ENDC}"
            print(f"  {status} {name} ({elapsed:.1f}s)")
        print()

    # 最终结果
    if passed_tests == total_tests:
        print_success(f"所有{total_tests}个测试通过！ 🎉")
        return 0
    else:
        print_error(f"{total_tests - passed_tests}个测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
