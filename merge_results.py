# -*- coding: utf-8 -*-
"""
merge_results.py

将 batch_test_results/ 目录下的所有分批测试结果合并成一个单一的JSON文件。
"""

import json
import os
from datetime import datetime

RESULTS_DIR = "batch_test_results"
FINAL_OUTPUT_FILE = "final_batch_test_results.json"

def merge_results():
    """
    合并所有批次的结果文件。
    """
    print("开始合并所有批次的测试结果...")

    if not os.path.exists(RESULTS_DIR):
        print(f"错误: 结果目录 '{RESULTS_DIR}' 不存在。")
        return

    all_results = []
    total_scripts = 0

    # 获取所有结果文件并按数字顺序排序
    result_files = sorted(
        [f for f in os.listdir(RESULTS_DIR) if f.startswith('results_') and f.endswith('.json')],
        key=lambda x: int(x.split('_')[1])
    )

    for filename in result_files:
        filepath = os.path.join(RESULTS_DIR, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                batch_res = data.get("results", [])
                all_results.extend(batch_res)
                total_scripts += len(batch_res)
        except (json.JSONDecodeError, KeyError) as e:
            print(f"警告: 无法解析文件 {filename} 或文件格式不正确: {e}")

    print(f"成功合并了 {len(result_files)} 个批次的文件，总共包含 {total_scripts} 个案例结果。")

    # 构建最终的摘要对象
    final_summary = {
        "metadata": {
            "report_generated_at": datetime.now().isoformat(),
            "total_scripts_analyzed": len(all_results),
        },
        "results": all_results
    }

    # 保存最终的合并文件
    with open(FINAL_OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(final_summary, f, indent=2, ensure_ascii=False)

    print(f"最终结果报告已成功生成: {FINAL_OUTPUT_FILE}")

if __name__ == "__main__":
    merge_results()
