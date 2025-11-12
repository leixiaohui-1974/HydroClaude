#!/usr/bin/env python3
"""
手动浏览器测试 - 非headless模式，添加调试信息
"""

from playwright.sync_api import sync_playwright
import time

def manual_test():
    with sync_playwright() as p:
        # 使用非headless模式以便调试
        browser = p.chromium.launch(
            headless=True,  # 保持headless因为是远程环境
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        
        # 启用控制台消息捕获
        page = context.new_page()
        
        console_messages = []
        errors = []
        
        page.on("console", lambda msg: console_messages.append(f"[{msg.type}] {msg.text}"))
        page.on("pageerror", lambda err: errors.append(str(err)))
        
        print("=== 访问页面 ===")
        page.goto("http://localhost:5174", wait_until="networkidle")
        time.sleep(3)
        
        print(f"\n=== 页面标题: {page.title()} ===")
        print(f"=== 当前URL: {page.url} ===")
        
        # 检查标签
        print("\n=== 检查标签元素 ===")
        modeling_tab = page.locator('[role="tab"]:has-text("建模工作台")')
        simulation_tab = page.locator('[role="tab"]:has-text("仿真管理")')
        
        print(f"建模工作台标签数: {modeling_tab.count()}")
        print(f"仿真管理标签数: {simulation_tab.count()}")
        
        if modeling_tab.count() > 0:
            print(f"建模工作台可见: {modeling_tab.first.is_visible()}")
            print(f"建模工作台类名: {modeling_tab.first.get_attribute('class')}")
            
        if simulation_tab.count() > 0:
            print(f"仿真管理可见: {simulation_tab.first.is_visible()}")
            print(f"仿真管理类名: {simulation_tab.first.get_attribute('class')}")
        
        # 点击仿真管理
        print("\n=== 点击仿真管理标签 ===")
        if simulation_tab.count() > 0:
            simulation_tab.first.click()
            time.sleep(5)
            
            print(f"点击后URL: {page.url}")
            print(f"点击后标题: {page.title()}")
            
            # 检查激活状态
            print(f"\n建模工作台激活: {'aria-selected=\"true\"' in (modeling_tab.first.get_attribute('aria-selected') or '')}")
            print(f"仿真管理激活: {'aria-selected=\"true\"' in (simulation_tab.first.get_attribute('aria-selected') or '')}")
            
            # 检查页面内容
            body_text = page.locator('body').inner_text()
            print(f"\n页面包含'组件库': {'组件库' in body_text}")
            print(f"页面包含'仿真配置': {'仿真配置' in body_text}")
            print(f"页面包含'单场景结果': {'单场景结果' in body_text}")
            
        # 打印控制台消息
        print("\n=== 控制台消息 ===")
        if console_messages:
            for msg in console_messages[-10:]:
                print(msg)
        else:
            print("无控制台消息")
            
        # 打印错误
        print("\n=== JavaScript错误 ===")
        if errors:
            for err in errors:
                print(err)
        else:
            print("无JavaScript错误")
            
        browser.close()

if __name__ == "__main__":
    manual_test()
