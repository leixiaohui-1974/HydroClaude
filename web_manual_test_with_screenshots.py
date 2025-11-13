#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HydroClaude Web界面手动测试辅助脚本
打开浏览器并提供测试指导，保存截图

Author: HydroClaude Team
Date: 2025-11-12
"""

import sys
import os
import time
import webbrowser
from pathlib import Path
from datetime import datetime


def main():
    """主函数"""
    print("=" * 80)
    print("HydroClaude Web界面测试辅助工具")
    print("=" * 80)
    print()
    
    # 创建截图目录
    screenshots_dir = Path('web_test_screenshots')
    screenshots_dir.mkdir(exist_ok=True)
    print(f"截图保存目录: {screenshots_dir.absolute()}")
    print()
    
    # 检查服务
    print("步骤1: 检查服务状态...")
    print("-" * 80)
    
    try:
        import requests
        
        # 检查后端
        try:
            resp = requests.get('http://localhost:8000/health', timeout=2)
            if resp.status_code == 200:
                print("  [OK] 后端服务运行正常 (http://localhost:8000)")
            else:
                print("  [WARNING] 后端服务响应异常")
        except:
            print("  [ERROR] 后端服务未运行!")
            print("  请先启动后端: cd web && ./start_servers.sh")
            print()
        
        # 检查前端
        try:
            resp = requests.get('http://localhost:5173', timeout=2)
            if resp.status_code == 200:
                print("  [OK] 前端服务运行正常 (http://localhost:5173)")
            else:
                print("  [WARNING] 前端服务响应异常")
        except:
            print("  [ERROR] 前端服务未运行!")
            print("  请先启动前端: cd web && ./start_servers.sh")
            print()
    
    except ImportError:
        print("  [INFO] requests库未安装，跳过自动检查")
        print("  请手动确认服务已启动")
    
    print()
    
    # 显示测试步骤
    print("步骤2: 浏览器测试步骤")
    print("-" * 80)
    print()
    print("即将打开浏览器，请按照以下步骤进行测试:")
    print()
    print("[ ] 1. 首页加载")
    print("    - 确认页面正常加载（无白屏）")
    print("    - 按F12查看控制台，确认无错误")
    print("    - 截图保存: 01_homepage.png")
    print()
    print("[ ] 2. 模型编辑器")
    print("    - 查找并填写输入框（渠道长度、宽度等）")
    print("    - 测试输入验证")
    print("    - 截图保存: 02_model_editor.png")
    print()
    print("[ ] 3. 添加结构（如闸门）")
    print("    - 点击添加按钮")
    print("    - 填写参数")
    print("    - 截图保存: 03_add_structure.png")
    print()
    print("[ ] 4. 运行仿真")
    print("    - 点击运行按钮")
    print("    - 观察进度")
    print("    - 截图保存: 04_running.png, 05_complete.png")
    print()
    print("[ ] 5. 查看结果")
    print("    - 检查图表渲染")
    print("    - 测试图表交互")
    print("    - 截图保存: 06_results.png")
    print()
    print("[ ] 6. 导出功能")
    print("    - 测试导出按钮")
    print("    - 截图保存: 07_export.png")
    print()
    print("[ ] 7. 错误处理")
    print("    - 输入无效数据测试")
    print("    - 截图保存: 08_error_handling.png")
    print()
    
    # 生成测试清单文件
    checklist_path = screenshots_dir / 'test_checklist.txt'
    with open(checklist_path, 'w', encoding='utf-8') as f:
        f.write("HydroClaude Web UI 测试清单\n")
        f.write("=" * 80 + "\n")
        f.write(f"测试日期: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("测试步骤:\n\n")
        f.write("[ ] 1. 首页加载 - 截图: 01_homepage.png\n")
        f.write("    - 页面正常加载\n")
        f.write("    - 无控制台错误\n\n")
        f.write("[ ] 2. 模型编辑器 - 截图: 02_model_editor.png\n")
        f.write("    - 输入框可用\n")
        f.write("    - 验证功能正常\n\n")
        f.write("[ ] 3. 添加结构 - 截图: 03_add_structure.png\n")
        f.write("    - 按钮可点击\n")
        f.write("    - 表单正常\n\n")
        f.write("[ ] 4. 运行仿真 - 截图: 04_running.png, 05_complete.png\n")
        f.write("    - 仿真可启动\n")
        f.write("    - 进度正常显示\n")
        f.write("    - 结果正确返回\n\n")
        f.write("[ ] 5. 查看结果 - 截图: 06_results.png\n")
        f.write("    - 图表渲染正常\n")
        f.write("    - 数据显示正确\n\n")
        f.write("[ ] 6. 导出功能 - 截图: 07_export.png\n")
        f.write("    - 导出按钮可用\n")
        f.write("    - 文件下载成功\n\n")
        f.write("[ ] 7. 错误处理 - 截图: 08_error_handling.png\n")
        f.write("    - 错误提示清晰\n")
        f.write("    - 用户友好\n\n")
        f.write("-" * 80 + "\n")
        f.write("测试结论:\n")
        f.write("  总体评价: [ 优秀 / 良好 / 一般 / 较差 ]\n")
        f.write("  主要问题: \n\n")
        f.write("  改进建议: \n\n")
    
    print(f"测试清单已生成: {checklist_path.absolute()}")
    print()
    
    # 询问是否打开浏览器
    print("=" * 80)
    input("按Enter键打开浏览器开始测试...")
    
    # 打开浏览器
    url = "http://localhost:5173"
    print(f"\n正在打开浏览器: {url}")
    webbrowser.open(url)
    
    print()
    print("=" * 80)
    print("浏览器已打开！")
    print()
    print("提示:")
    print("  - 按照上面的步骤逐步测试")
    print("  - 使用Windows截图工具（Win + Shift + S）保存截图")
    print(f"  - 将截图保存到: {screenshots_dir.absolute()}")
    print(f"  - 完成后填写测试清单: {checklist_path.absolute()}")
    print()
    print("测试完成后，请查看:")
    print("  - TEST_EXECUTION_SUMMARY.md - 测试总结")
    print("  - COMPREHENSIVE_TEST_PLAN.md - 完整测试方案")
    print("=" * 80)


if __name__ == '__main__':
    main()







