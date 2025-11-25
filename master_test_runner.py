# -*- coding: utf-8 -*-
"""
master_test_runner.py

一个健壮的主运行器脚本，用于自动、顺序地执行所有测试案例，
并支持断点续传。
"""

import json
import subprocess
import os
import re
import time
import sys

INPUT_FILE = "all_test_scripts.json"
RESULTS_DIR = "batch_test_results"
BATCH_SCRIPT = "batch_test_all_cases.py"

def get_last_completed_index() -> int:
    """
    检查结果目录，找出最后一个成功完成的测试的索引。
    返回下一个应该开始的索引。
    """
    if not os.path.exists(RESULTS_DIR):
        return 0

    files = os.listdir(RESULTS_DIR)
    if not files:
        return 0

    # 从文件名如 'results_139_140.json' 中解析出起始索引
    indices = []
    for f in files:
        match = re.match(r'results_(\d+)_(\d+)\.json', f)
        if match:
            indices.append(int(match.group(1)))

    if not indices:
        return 0

    # 最后一个完成的索引是...
    last_idx = max(indices)

    # 我们应该从下一个索引开始
    return last_idx + 1


def main():
    """
    主函数，从上次中断的地方继续执行所有测试。
    """
    print("--- Master Test Runner ---")

    try:
        with open(INPUT_FILE, 'r') as f:
            all_scripts = json.load(f)
    except FileNotFoundError:
        print(f"错误: 案例列表文件 '{INPUT_FILE}' 未找到。")
        return

    total_scripts = len(all_scripts)
    start_index = get_last_completed_index()

    if start_index >= total_scripts:
        print("所有测试案例似乎都已执行完毕。")
        return

    print(f"总案例数: {total_scripts}")
    print(f"将从索引 {start_index} 开始继续测试...")

    for i in range(start_index, total_scripts):
        script_path = all_scripts[i]
        print(f"\n[{i+1}/{total_scripts}] 准备执行: {script_path}")

        # 调用批处理脚本，每次只运行一个案例
        command = [
            sys.executable,
            BATCH_SCRIPT,
            "--start", str(i),
            "--end", str(i + 1)
        ]

        try:
            # 使用 Popen 在后台运行，并等待它完成
            # 这比 run 更健壮，可以更好地处理流式输出
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace')
            stdout, stderr = process.communicate()

            if process.returncode != 0:
                print(f"  -> 执行批处理脚本时发生错误。")
                print(f"  -> STDERR: {stderr.strip()}")
            else:
                # 打印批处理脚本自身的输出
                print(stdout.strip())

        except Exception as e:
            print(f"  -> 运行主循环时发生严重错误: {e}")
            # 记录错误并尝试继续
            time.sleep(1)

    print("\n--- 所有测试案例均已执行 ---")

if __name__ == "__main__":
    main()
