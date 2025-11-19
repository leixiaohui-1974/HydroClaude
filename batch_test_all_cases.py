# -*- coding: utf-8 -*-
"""
batch_test_all_cases.py

一个自动化脚本，用于批量执行在 `all_test_scripts.json` 中找到的所有测试案例。
支持分批执行和断点续传。
"""

import json
import subprocess
import time
from datetime import datetime
import os
import argparse

# --- 配置 ---
INPUT_FILE = "all_test_scripts.json"
# 输出将按批次保存
OUTPUT_DIR = "batch_test_results"
TIMEOUT_SECONDS = 60
DEFAULT_ENCODING = 'utf-8'

def run_script(script_path: str) -> dict:
    """在一个独立的子进程中运行单个Python脚本。"""
    start_time = time.time()
    status = "unknown"
    stdout = ""
    stderr = ""
    return_code = -1

    env = os.environ.copy()
    env['PYTHONPATH'] = '.'

    try:
        result = subprocess.run(
            ["python3", script_path],
            capture_output=True, text=True, encoding=DEFAULT_ENCODING,
            errors='replace', timeout=TIMEOUT_SECONDS, env=env, check=False
        )
        return_code = result.returncode
        stdout = result.stdout
        stderr = result.stderr
        status = "pass" if return_code == 0 else "fail"
    except subprocess.TimeoutExpired as e:
        status = "timeout"
        stdout = e.stdout or ""
        stderr = e.stderr or f"Process timed out after {TIMEOUT_SECONDS} seconds."
    except Exception as e:
        status = "error"
        stderr = f"An unexpected error occurred: {e}"

    duration = time.time() - start_time
    
    return {
        "script_path": script_path, "status": status, "return_code": return_code,
        "duration_seconds": round(duration, 2), "stdout": stdout.strip(), "stderr": stderr.strip(),
    }

def main():
    """主函数：读取脚本列表，执行指定批次的任务，并保存结果。"""
    parser = argparse.ArgumentParser(description="分批次运行测试案例。")
    parser.add_argument('--start', type=int, required=True, help='起始索引 (包含)')
    parser.add_argument('--end', type=int, required=True, help='结束索引 (不包含)')
    args = parser.parse_args()

    # 确保输出目录存在
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    output_file = os.path.join(OUTPUT_DIR, f'results_{args.start}_{args.end}.json')

    print(f"开始批量测试 (批次: {args.start}-{args.end})...")

    try:
        with open(INPUT_FILE, 'r', encoding=DEFAULT_ENCODING) as f:
            all_scripts = json.load(f)
    except FileNotFoundError:
        print(f"错误: 输入文件 '{INPUT_FILE}' 未找到。")
        return

    # 获取当前批次的脚本
    scripts_to_run = all_scripts[args.start:args.end]
    total_batch_scripts = len(scripts_to_run)
    
    if total_batch_scripts == 0:
        print("此批次没有脚本需要运行。")
        return

    print(f"本批次共 {total_batch_scripts} 个脚本待测试。")
    
    batch_results = []
    start_time = time.time()

    for i, script_path in enumerate(scripts_to_run):
        print(f"[{i+1}/{total_batch_scripts} (全局索引 {args.start + i})] 正在运行: {script_path} ...", end="", flush=True)
        result = run_script(script_path)
        batch_results.append(result)
        print(f" -> {result['status'].upper()} ({result['duration_seconds']:.2f}s)")

    batch_duration = time.time() - start_time

    summary = {
        "metadata": {
            "batch_start_index": args.start,
            "batch_end_index": args.end,
            "test_run_at": datetime.now().isoformat(),
            "batch_duration_seconds": round(batch_duration, 2),
            "total_scripts_in_batch": total_batch_scripts,
        },
        "results": batch_results
    }

    with open(output_file, 'w', encoding=DEFAULT_ENCODING) as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"\n批次 {args.start}-{args.end} 测试完成！结果已保存到: {output_file}")

if __name__ == "__main__":
    main()
