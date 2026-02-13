#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HydroClaude 单案例耐心测试
一步一步来，等待计算真正完成

Author: HydroClaude Test Team
Date: 2025-11-25
"""

import os
import sys
import json
import time
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from playwright.async_api import async_playwright, Page, expect
except ImportError:
    import pytest
    pytest.skip("playwright not installed", allow_module_level=True)

# 配置
FRONTEND_URL = "http://localhost:3000"
BACKEND_URL = "http://localhost:8000"
OUTPUT_DIR = project_root / "tests" / "e2e" / "patient_test_output"
SCREENSHOTS_DIR = OUTPUT_DIR / "screenshots"

# 创建目录
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)


class PatientE2ETester:
    """耐心的端到端测试器 - 一步一步来"""
    
    def __init__(self):
        self.browser = None
        self.page: Optional[Page] = None
        self.screenshots: List[str] = []
        self.step_count = 0
        
    def log(self, message: str, level: str = "INFO"):
        """日志输出"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        icons = {
            "INFO": "[i]",
            "SUCCESS": "[OK]",
            "ERROR": "[X]",
            "WAIT": "[~]",
            "STEP": "[>]",
            "CHECK": "[?]"
        }
        icon = icons.get(level, "[?]")
        print(f"[{timestamp}] {icon} {message}")
    
    async def screenshot(self, name: str) -> str:
        """截图"""
        self.step_count += 1
        filename = f"{self.step_count:02d}_{name}.png"
        filepath = SCREENSHOTS_DIR / filename
        await self.page.screenshot(path=str(filepath), full_page=True)
        self.screenshots.append(str(filepath))
        self.log(f"Screenshot saved: {filename}", "SUCCESS")
        return str(filepath)
    
    async def setup(self):
        """启动浏览器"""
        self.log("启动浏览器...", "STEP")
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=False,  # 显示浏览器
            slow_mo=500      # 慢动作，便于观察
        )
        self.page = await self.browser.new_page(viewport={'width': 1600, 'height': 900})
        
        # 捕获控制台消息
        self.console_logs = []
        self.page.on("console", lambda msg: self.console_logs.append(f"[{msg.type}] {msg.text}"))
        self.page.on("pageerror", lambda exc: self.console_logs.append(f"[ERROR] {exc}"))
        
        self.log("浏览器已启动", "SUCCESS")
    
    async def teardown(self):
        """关闭浏览器"""
        if self.browser:
            await asyncio.sleep(3)  # 等待3秒让用户看到结果
            await self.browser.close()
            self.log("浏览器已关闭", "INFO")
    
    async def step_1_go_to_simulation(self):
        """步骤1: 导航到仿真计算页面"""
        print("\n" + "=" * 60)
        self.log("步骤1: 导航到仿真计算页面", "STEP")
        print("=" * 60)
        
        # 访问首页
        self.log("访问首页...", "INFO")
        await self.page.goto(FRONTEND_URL, wait_until='networkidle', timeout=60000)
        await self.page.wait_for_timeout(2000)
        await self.screenshot("homepage")
        
        # 查找并点击仿真菜单
        self.log("查找仿真计算菜单...", "INFO")
        
        # 尝试多种选择器
        selectors = [
            'a:has-text("仿真计算")',
            'span:has-text("仿真计算")',
            '[href*="simulation"]',
            '.ant-menu-item:has-text("仿真")',
        ]
        
        for selector in selectors:
            menu = self.page.locator(selector).first
            if await menu.count() > 0:
                self.log(f"找到菜单: {selector}", "SUCCESS")
                await menu.click()
                await self.page.wait_for_timeout(2000)
                break
        else:
            # 直接访问URL
            self.log("尝试直接访问URL...", "INFO")
            await self.page.goto(f"{FRONTEND_URL}/simulation", wait_until='networkidle')
            await self.page.wait_for_timeout(2000)
        
        await self.screenshot("simulation_page")
        self.log("步骤1完成", "SUCCESS")
    
    async def step_2_fill_config(self):
        """步骤2: 填写仿真配置"""
        print("\n" + "=" * 60)
        self.log("步骤2: 填写仿真配置", "STEP")
        print("=" * 60)
        
        # 检查是否有配置表单
        form = self.page.locator('form').first
        if await form.count() == 0:
            self.log("未找到配置表单！", "ERROR")
            return False
        
        self.log("找到配置表单", "SUCCESS")
        
        # 使用默认值，只需要确认表单存在
        # 表单已经有默认值，无需填写
        self.log("使用默认配置参数", "INFO")
        
        await self.screenshot("config_ready")
        self.log("步骤2完成", "SUCCESS")
        return True
    
    async def step_3_run_simulation(self):
        """步骤3: 运行仿真"""
        print("\n" + "=" * 60)
        self.log("步骤3: 运行仿真", "STEP")
        print("=" * 60)
        
        # 查找运行按钮
        run_button_selectors = [
            'button:has-text("运行仿真")',
            'button:has-text("Run")',
            'button:has-text("开始")',
            'button[type="submit"]'
        ]
        
        run_button = None
        for selector in run_button_selectors:
            btn = self.page.locator(selector).first
            if await btn.count() > 0:
                run_button = btn
                self.log(f"找到运行按钮: {selector}", "SUCCESS")
                break
        
        if not run_button:
            self.log("未找到运行按钮！", "ERROR")
            return False
        
        # 点击运行
        self.log("点击运行按钮...", "INFO")
        await run_button.click()
        await self.screenshot("simulation_submitted")
        
        self.log("仿真已提交", "SUCCESS")
        return True
    
    async def step_4_wait_for_completion(self, max_wait: int = 180):
        """步骤4: 等待计算完成"""
        print("\n" + "=" * 60)
        self.log(f"步骤4: 等待计算完成（最长{max_wait}秒）", "STEP")
        print("=" * 60)
        
        start_time = time.time()
        last_screenshot_time = start_time
        
        while time.time() - start_time < max_wait:
            elapsed = int(time.time() - start_time)
            
            # 检查是否有错误消息
            error_selectors = [
                '.ant-message-error',
                '.ant-alert-error',
                ':text("失败")',
                ':text("错误")'
            ]
            
            for selector in error_selectors:
                error = self.page.locator(selector).first
                if await error.count() > 0:
                    error_text = await error.text_content()
                    self.log(f"检测到错误: {error_text}", "ERROR")
                    await self.screenshot("error_detected")
                    
                    # 如果是超时错误，继续等待
                    if "timeout" in error_text.lower():
                        self.log("超时错误，但继续等待...", "WAIT")
                        continue
                    return False
            
            # 检查是否有进度显示
            progress_text = ""
            progress_selectors = [
                '.ant-progress-text',
                ':text("%")',
                '.ant-spin-text'
            ]
            
            for selector in progress_selectors:
                prog = self.page.locator(selector).first
                if await prog.count() > 0:
                    try:
                        progress_text = await prog.text_content()
                        if progress_text:
                            self.log(f"进度: {progress_text}", "WAIT")
                    except:
                        pass
                    break
            
            # 检查是否有成功消息
            success_selectors = [
                '.ant-message-success',
                ':text("仿真完成")',
                ':text("完成")'
            ]
            
            for selector in success_selectors:
                success = self.page.locator(selector).first
                if await success.count() > 0:
                    self.log("检测到成功消息！", "SUCCESS")
                    await self.screenshot("simulation_complete")
                    return True
            
            # 检查是否有结果图表
            chart_selectors = [
                'canvas',
                '.plotly-graph-div',
                '.recharts-wrapper',
                'svg[class*="chart"]'
            ]
            
            charts_found = 0
            for selector in chart_selectors:
                charts = self.page.locator(selector)
                charts_found += await charts.count()
            
            if charts_found > 0:
                # 检查加载状态
                loading = self.page.locator('.ant-spin, :text("加载中"), :text("Loading")')
                if await loading.count() == 0:
                    self.log(f"检测到{charts_found}个结果图表，计算可能已完成", "CHECK")
                    await self.page.wait_for_timeout(2000)  # 等待渲染完成
                    await self.screenshot("results_detected")
                    return True
            
            # 每30秒截图一次
            if time.time() - last_screenshot_time > 30:
                await self.screenshot(f"waiting_{elapsed}s")
                last_screenshot_time = time.time()
            
            # 每5秒输出等待信息
            if elapsed % 5 == 0 and elapsed > 0:
                self.log(f"已等待 {elapsed} 秒...", "WAIT")
            
            await self.page.wait_for_timeout(1000)
        
        self.log(f"超时: 计算未在{max_wait}秒内完成", "ERROR")
        await self.screenshot("timeout")
        return False
    
    async def step_5_check_results(self):
        """步骤5: 检查结果"""
        print("\n" + "=" * 60)
        self.log("步骤5: 检查仿真结果", "STEP")
        print("=" * 60)
        
        # 等待更长时间让React渲染结果
        self.log("等待结果渲染...", "WAIT")
        await self.page.wait_for_timeout(5000)
        
        # 滚动页面查看完整内容
        self.log("滚动页面查看完整内容...", "INFO")
        await self.page.evaluate("window.scrollTo(0, 0)")
        await self.page.wait_for_timeout(500)
        await self.screenshot("results_top")
        
        await self.page.evaluate("window.scrollTo(0, 500)")
        await self.page.wait_for_timeout(500)
        await self.screenshot("results_middle")
        
        await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await self.page.wait_for_timeout(500)
        await self.screenshot("results_bottom")
        
        # 打印控制台日志
        self.log("浏览器控制台日志:", "INFO")
        for log in self.console_logs[-30:]:  # 最后30条
            print(f"  {log}")
        
        # 统计结果元素
        results = {
            "charts": 0,
            "tables": 0,
            "metrics": 0
        }
        
        # 检查图表
        chart_selectors = ['canvas', '.plotly-graph-div', '.recharts-wrapper']
        for selector in chart_selectors:
            count = await self.page.locator(selector).count()
            results["charts"] += count
        self.log(f"检测到 {results['charts']} 个图表", "INFO")
        
        # 检查表格
        table_selectors = ['table', '.ant-table']
        for selector in table_selectors:
            count = await self.page.locator(selector).count()
            results["tables"] += count
        self.log(f"检测到 {results['tables']} 个表格", "INFO")
        
        # 检查数值指标
        metrics_selectors = [
            ':text("水深")',
            ':text("流量")',
            ':text("速度")',
            ':text("depth")',
            ':text("discharge")'
        ]
        for selector in metrics_selectors:
            count = await self.page.locator(selector).count()
            results["metrics"] += count
        self.log(f"检测到 {results['metrics']} 个数值指标", "INFO")
        
        await self.screenshot("results_overview")
        
        # 尝试导航到结果分析页
        results_link = self.page.locator('a:has-text("结果分析"), span:has-text("结果分析")').first
        if await results_link.count() > 0:
            self.log("导航到结果分析页...", "INFO")
            await results_link.click()
            await self.page.wait_for_timeout(2000)
            await self.screenshot("results_analysis_page")
        
        has_results = results["charts"] > 0 or results["tables"] > 0
        self.log(f"步骤5完成: 结果检查 {'通过' if has_results else '失败'}", 
                "SUCCESS" if has_results else "ERROR")
        
        return results
    
    async def run(self):
        """运行完整测试"""
        print("\n" + "=" * 70)
        print("  HydroClaude 单案例耐心测试")
        print("  一步一步来，等待计算真正完成")
        print("=" * 70 + "\n")
        
        start_time = time.time()
        result = {
            "status": "pending",
            "steps": [],
            "results": None,
            "duration": 0
        }
        
        try:
            await self.setup()
            
            # 步骤1: 导航
            await self.step_1_go_to_simulation()
            result["steps"].append({"name": "navigate", "status": "done"})
            
            # 步骤2: 配置
            if await self.step_2_fill_config():
                result["steps"].append({"name": "config", "status": "done"})
            else:
                result["steps"].append({"name": "config", "status": "failed"})
                result["status"] = "failed"
                return result
            
            # 步骤3: 运行
            if await self.step_3_run_simulation():
                result["steps"].append({"name": "run", "status": "done"})
            else:
                result["steps"].append({"name": "run", "status": "failed"})
                result["status"] = "failed"
                return result
            
            # 步骤4: 等待完成
            if await self.step_4_wait_for_completion(max_wait=180):
                result["steps"].append({"name": "wait", "status": "done"})
            else:
                result["steps"].append({"name": "wait", "status": "timeout"})
                result["status"] = "timeout"
                return result
            
            # 步骤5: 检查结果
            check_result = await self.step_5_check_results()
            result["results"] = check_result
            result["steps"].append({"name": "check", "status": "done"})
            
            if check_result["charts"] > 0:
                result["status"] = "passed"
            else:
                result["status"] = "no_results"
                
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
            self.log(f"测试出错: {e}", "ERROR")
            import traceback
            traceback.print_exc()
            await self.screenshot("error")
        
        finally:
            result["duration"] = time.time() - start_time
            await self.teardown()
        
        # 打印结果
        print("\n" + "=" * 70)
        print("  测试结果")
        print("=" * 70)
        print(f"  状态: {result['status'].upper()}")
        print(f"  耗时: {result['duration']:.1f}秒")
        print(f"  步骤: {len([s for s in result['steps'] if s['status'] == 'done'])}/{len(result['steps'])}")
        print(f"  截图: {len(self.screenshots)}")
        if result["results"]:
            print(f"  图表: {result['results']['charts']}")
            print(f"  表格: {result['results']['tables']}")
        print("=" * 70 + "\n")
        
        # 保存结果
        result_file = OUTPUT_DIR / f"result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2, default=str)
        self.log(f"结果已保存: {result_file}", "SUCCESS")
        
        return result


async def main():
    tester = PatientE2ETester()
    result = await tester.run()
    return result


if __name__ == "__main__":
    asyncio.run(main())

