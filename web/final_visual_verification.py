#!/usr/bin/env python3
"""
最终可视化验证 - 正确的截图时机
"""

from playwright.sync_api import sync_playwright
import time
from pathlib import Path

def final_verification():
    screenshots_dir = Path("/workspace/web/final_screenshots")
    screenshots_dir.mkdir(exist_ok=True)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()
        
        print("="*70)
        print("最终可视化验证")
        print("="*70)
        
        # 1. 访问页面
        print("\n1. 加载首页...")
        page.goto("http://localhost:5174", wait_until="networkidle")
        time.sleep(3)
        page.screenshot(path=str(screenshots_dir / "01_homepage.png"), full_page=True)
        print("   ✅ 首页截图已保存")
        
        # 2. 建模工作台
        print("\n2. 建模工作台...")
        page.locator('[role="tab"]:has-text("建模工作台")').first.click()
        # 等待React Flow加载
        page.wait_for_selector('.react-flow', timeout=10000)
        time.sleep(5)
        page.screenshot(path=str(screenshots_dir / "02_modeling_workspace.png"), full_page=True)
        
        body_text = page.locator('body').inner_text()
        has_components = "明渠" in body_text or "矩形明渠" in body_text
        print(f"   建模组件可见: {has_components}")
        print("   ✅ 建模工作台截图已保存")
        
        # 3. 仿真管理 - 关键！
        print("\n3. 仿真管理...")
        page.locator('[role="tab"]:has-text("仿真管理")').first.click()
        
        print("   等待懒加载组件...")
        # 等待懒加载的Spin消失
        try:
            page.wait_for_selector('text=加载中...', state="detached", timeout=10000)
        except:
            pass
            
        # 等待仿真配置表单出现
        try:
            page.wait_for_selector('text=仿真配置', timeout=10000)
            print("   ✅ 仿真配置表单已加载")
        except:
            print("   ⚠️  仿真配置表单未找到")
            
        # 再等待一段时间确保完全渲染
        time.sleep(8)
        
        page.screenshot(path=str(screenshots_dir / "03_simulation_management.png"), full_page=True)
        
        # 验证内容
        body_text = page.locator('body').inner_text()
        has_simulation_config = "仿真配置" in body_text
        has_single_scenario = "单场景结果" in body_text
        has_modeling_components = "明渠" in body_text or "矩形明渠" in body_text
        
        print(f"   仿真配置存在: {has_simulation_config}")
        print(f"   单场景结果存在: {has_single_scenario}")
        print(f"   建模组件存在: {has_modeling_components} (应该是False)")
        
        if has_simulation_config and has_single_scenario and not has_modeling_components:
            print("   ✅ 仿真管理页面正确显示！")
        else:
            print("   ⚠️  仿真管理页面可能有问题")
            
        print("   ✅ 仿真管理截图已保存")
        
        # 4. 单场景结果标签
        print("\n4. 检查单场景结果子标签...")
        try:
            single_tab = page.locator('[role="tab"]:has-text("单场景结果")')
            if single_tab.count() > 0:
                single_tab.first.click()
                time.sleep(3)
                page.screenshot(path=str(screenshots_dir / "04_single_scenario.png"), full_page=True)
                print("   ✅ 单场景结果截图已保存")
            else:
                print("   ℹ️  单场景结果标签未找到（可能已经是默认显示）")
        except Exception as e:
            print(f"   ⚠️  单场景结果标签测试失败: {e}")
            
        # 5. 多场景对比标签
        print("\n5. 检查多场景对比子标签...")
        try:
            comparison_tab = page.locator('[role="tab"]:has-text("多场景对比")')
            if comparison_tab.count() > 0:
                comparison_tab.first.click()
                time.sleep(3)
                page.screenshot(path=str(screenshots_dir / "05_comparison.png"), full_page=True)
                print("   ✅ 多场景对比截图已保存")
            else:
                print("   ℹ️  多场景对比标签未找到")
        except Exception as e:
            print(f"   ⚠️  多场景对比标签测试失败: {e}")
            
        # 6. 返回建模工作台验证
        print("\n6. 返回建模工作台...")
        page.locator('[role="tab"]:has-text("建模工作台")').first.click()
        page.wait_for_selector('.react-flow', timeout=10000)
        time.sleep(5)
        page.screenshot(path=str(screenshots_dir / "06_back_to_modeling.png"), full_page=True)
        print("   ✅ 返回建模工作台截图已保存")
        
        browser.close()
        
        print("\n" + "="*70)
        print(f"所有截图已保存到: {screenshots_dir}")
        print("="*70)
        print("\n请查看截图验证标签切换是否正确工作！")

if __name__ == "__main__":
    final_verification()
