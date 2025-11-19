# -*- coding: utf-8 -*-
"""
analyze_results.py

读取最终的批量测试结果JSON文件，进行统计分析，
并按失败原因对案例进行分类。
"""

import json
from collections import Counter
import re

INPUT_FILE = "final_batch_test_results.json"

def analyze_failure_reason(stderr: str) -> str:
    """
    根据 stderr 内容，智能判断失败的根本原因。
    """
    if not stderr:
        return "Unknown (No stderr)"

    # 常见 Python 错误
    if "ModuleNotFoundError" in stderr:
        match = re.search(r"ModuleNotFoundError: No module named '(\w+)'", stderr)
        return f"Dependency Error: Module '{match.group(1) if match else 'unknown'}' not found"
    if "ImportError" in stderr:
        return "Dependency Error: ImportError"
    if "SyntaxError" in stderr:
        return "Code Error: SyntaxError"
    if "NameError" in stderr:
        return "Code Error: NameError"
    if "TypeError" in stderr:
        return "Code Error: TypeError"
    if "AttributeError" in stderr:
        return "Code Error: AttributeError"
    if "FileNotFoundError" in stderr:
        return "Environment Error: FileNotFoundError"

    # 中文环境相关错误
    if "UnicodeDecodeError" in stderr:
        return "Encoding Error: UnicodeDecodeError"

    # 数值计算相关错误
    if "ValueError" in stderr:
        return "Numerical Error: ValueError"
    if "ZeroDivisionError" in stderr:
        return "Numerical Error: ZeroDivisionError"
    if "OverflowError" in stderr:
        return "Numerical Error: OverflowError"
    if "numpy.linalg.LinAlgError" in stderr:
        return "Numerical Error: Linear Algebra Error (Singular Matrix)"

    # 其他
    if "Permission denied" in stderr:
        return "Environment Error: Permission Denied"

    return "Generic Runtime Error"

def main():
    """
    主分析函数
    """
    print(f"正在分析测试结果: {INPUT_FILE}")

    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"错误: 结果文件 '{INPUT_FILE}' 未找到。")
        return

    results = data.get("results", [])
    total_ran = len(results)

    if total_ran == 0:
        print("结果文件中没有找到任何测试记录。")
        return

    # 1. 总体统计
    status_counts = Counter(r['status'] for r in results)

    # 2. 失败原因分类
    failed_cases = [r for r in results if r['status'] == 'fail']
    failure_reasons = Counter(analyze_failure_reason(r['stderr']) for r in failed_cases)

    # --- 生成 Markdown 报告 ---

    print("\n\n--- HydroClaude 项目深度测试分析报告 ---\n")

    print("## 1. 总体测试结果摘要\n")
    print(f"- **总执行案例数**: {total_ran}")
    pass_count = status_counts.get('pass', 0)
    fail_count = status_counts.get('fail', 0)
    timeout_count = status_counts.get('timeout', 0)
    error_count = status_counts.get('error', 0)

    pass_rate = (pass_count / total_ran) * 100 if total_ran > 0 else 0

    print(f"- **成功 (Pass)**: {pass_count} ({pass_rate:.2f}%)")
    print(f"- **失败 (Fail)**: {fail_count}")
    print(f"- **超时 (Timeout)**: {timeout_count}")
    print(f"- **执行错误 (Error)**: {error_count}")
    print("\n---\n")

    print("## 2. 失败案例根本原因分析\n")
    print("本分析仅针对状态为 'fail' 的案例。\n")

    if not failure_reasons:
        print("没有状态为 'fail' 的案例可供分析。\n")
    else:
        print("| 根本原因分类 | 数量 |")
        print("| :--- | :--- |")
        for reason, count in failure_reasons.most_common():
            print(f"| {reason} | {count} |")
        print("\n")

    # 打印一些具体的失败案例样本，以便快速诊断
    print("### 2.1. 失败案例样本\n")
    for reason, _ in failure_reasons.most_common(3): # 只看最高频的3种
        print(f"**类型: {reason}**\n")
        # 找到属于该原因的第一个案例
        sample_case = next((case for case in failed_cases if analyze_failure_reason(case['stderr']) == reason), None)
        if sample_case:
            print(f"- **案例路径**: `{sample_case['script_path']}`")
            print("- **错误日志 (stderr)**:")
            print("```")
            print(sample_case['stderr'][:1000]) # 最多打印1000个字符
            print("```\n")

    print("---\n")
    print("分析完成。请将以上内容复制到 `PROJECT_ANALYSIS_REPORT.md` 中。")

if __name__ == "__main__":
    main()
