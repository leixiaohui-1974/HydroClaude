#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
快速测试脚本 - 测试单个案例

用于快速验证测试框架是否正常工作

Author: HydroClaude Team
Date: 2025-11-15
"""

import sys
import time
from pathlib import Path

# 导入主测试模块
from test_web_e2e import WebE2ETester


def quick_test():
    """快速测试"""
    print("="*60)
    print("🚀 HydroClaude 快速测试")
    print("="*60)
    print()
    
    # 创建测试器
    tester = WebE2ETester(headless=False)
    
    # 检查测试案例
    test_cases = tester.load_test_cases()
    if not test_cases:
        print("❌ 未找到测试案例")
        print("   请先运行: python convert_test_cases.py")
        return
    
    print(f"✅ 找到 {len(test_cases)} 个测试案例")
    print(f"📋 测试第1个案例: {test_cases[0]['name']}")
    print()
    
    # 设置浏览器
    print("🌐 启动浏览器...")
    tester.setup_browser()
    
    try:
        # 测试第一个案例
        result = tester.test_single_case(test_cases[0])
        
        # 显示结果
        print()
        print("="*60)
        print("📊 测试结果")
        print("="*60)
        print(f"状态: {result['status']}")
        print(f"耗时: {result['duration']:.2f}秒")
        print()
        print("执行步骤:")
        for step in result['steps']:
            print(f"  {step}")
        print()
        print("截图文件:")
        for screenshot in result['screenshots']:
            print(f"  {Path(screenshot).name}")
        print()
        
        if result['status'] == 'passed':
            print("✅ 快速测试通过！")
            print()
            print("下一步:")
            print("  运行完整测试: python test_web_e2e.py --max-cases 10")
            print("  或使用一键脚本: run_full_test.bat 10")
        else:
            print("❌ 快速测试失败")
            print()
            if result.get('error'):
                print(f"错误: {result['error']}")
            print()
            print("故障排除:")
            print("  1. 确保Web应用运行: cd webapp && npm run dev")
            print("  2. 检查测试案例配置")
            print("  3. 查看截图了解失败原因")
    
    finally:
        # 关闭浏览器
        tester.teardown_browser()
    
    print()
    print("="*60)


if __name__ == "__main__":
    quick_test()
