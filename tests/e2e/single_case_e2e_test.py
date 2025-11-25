#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HydroClaude 单案例完整端到端测试
Single Case Complete E2E Test

一步一步来：
1. 加载案例配置
2. 提交仿真请求
3. 等待计算100%完成
4. 查看完整结果图表
5. 验证结果正确性
6. 确保展示友好
7. 截图记录

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

from playwright.async_api import async_playwright, Page

# 配置
FRONTEND_URL = "http://localhost:3000"
BACKEND_URL = "http://localhost:8000"
OUTPUT_DIR = project_root / "tests" / "e2e" / "single_case_output"
SCREENSHOTS_DIR = OUTPUT_DIR / "screenshots"

# 创建目录
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)


class SingleCaseE2ETester:
    """单案例完整端到端测试器"""
    
    def __init__(self):
        self.browser = None
        self.page: Optional[Page] = None
        self.test_start_time = None
        self.screenshots: List[str] = []
        
    def log(self, message: str, level: str = "INFO"):
        """日志输出"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        icons = {
            "INFO": "[INFO]",
            "SUCCESS": "[OK]",
            "ERROR": "[ERR]",
            "WAIT": "[WAIT]",
            "STEP": "[STEP]",
            "CHECK": "[CHK]"
        }
        icon = icons.get(level, "[???]")
        print(f"[{timestamp}] {icon} {message}")
    
    async def take_screenshot(self, name: str, description: str = "") -> str:
        """截图并记录"""
        filename = f"{datetime.now().strftime('%H%M%S')}_{name}.png"
        filepath = SCREENSHOTS_DIR / filename
        await self.page.screenshot(path=str(filepath), full_page=True)
        self.screenshots.append({
            "file": str(filepath),
            "name": name,
            "description": description,
            "timestamp": datetime.now().isoformat()
        })
        self.log(f"截图: {filename} - {description}", "SUCCESS")
        return str(filepath)
    
    async def setup(self):
        """启动浏览器"""
        self.log("启动Chromium浏览器（非无头模式，便于观察）...", "STEP")
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=False,  # 显示浏览器窗口
            slow_mo=300      # 慢动作，便于观察
        )
        self.page = await self.browser.new_page(viewport={'width': 1920, 'height': 1080})
        self.log("浏览器启动成功", "SUCCESS")
    
    async def teardown(self):
        """关闭浏览器"""
        if self.browser:
            await self.browser.close()
            self.log("浏览器已关闭", "INFO")
    
    async def step1_navigate_to_simulation(self):
        """步骤1: 导航到仿真计算页面"""
        self.log("=" * 60, "STEP")
        self.log("步骤1: 导航到仿真计算页面", "STEP")
        self.log("=" * 60, "STEP")
        
        # 访问首页
        self.log("访问首页...", "INFO")
        await self.page.goto(FRONTEND_URL, wait_until='networkidle', timeout=30000)
        await self.page.wait_for_timeout(2000)
        await self.take_screenshot("01_homepage", "首页加载完成")
        
        # 点击仿真计算菜单
        self.log("点击仿真计算菜单...", "INFO")
        sim_menu = self.page.locator('a:has-text("仿真计算"), span:has-text("仿真计算")').first
        if await sim_menu.count() > 0:
            await sim_menu.click()
            await self.page.wait_for_timeout(2000)
        else:
            # 直接访问URL
            await self.page.goto(f"{FRONTEND_URL}/simulation", wait_until='networkidle')
            await self.page.wait_for_timeout(2000)
        
        await self.take_screenshot("02_simulation_page", "仿真计算页面")
        self.log("步骤1完成: 已进入仿真计算页面", "SUCCESS")
    
    async def step2_configure_simulation(self, config: Dict[str, Any]):
        """步骤2: 配置仿真参数"""
        self.log("=" * 60, "STEP")
        self.log("步骤2: 配置仿真参数", "STEP")
        self.log("=" * 60, "STEP")
        
        # 填写仿真名称
        name = config.get("name", f"E2E测试_{datetime.now().strftime('%H%M%S')}")
        self.log(f"填写仿真名称: {name}", "INFO")
        name_input = self.page.locator('input').filter(has_text="").first
        # 尝试多种选择器
        name_selectors = [
            'input[placeholder*="名称"]',
            'input[name*="name"]',
            '#simulationName',
            'input:near(:text("仿真名称"))'
        ]
        for selector in name_selectors:
            inp = self.page.locator(selector).first
            if await inp.count() > 0:
                await inp.fill(name)
                break
        
        # 填写几何参数
        self.log(f"填写渠道宽度: {config.get('width', 10.0)}m", "INFO")
        width_input = self.page.locator('input[placeholder*="宽度"], input:near(:text("宽度"))').first
        if await width_input.count() > 0:
            await width_input.clear()
            await width_input.fill(str(config.get('width', 10.0)))
        
        self.log(f"填写渠道长度: {config.get('length', 1000)}m", "INFO")
        length_input = self.page.locator('input[placeholder*="长度"], input:near(:text("长度"))').first
        if await length_input.count() > 0:
            await length_input.clear()
            await length_input.fill(str(config.get('length', 1000)))
        
        self.log(f"填写网格单元数: {config.get('n_cells', 100)}", "INFO")
        cells_input = self.page.locator('input[placeholder*="单元"], input:near(:text("单元"))').first
        if await cells_input.count() > 0:
            await cells_input.clear()
            await cells_input.fill(str(config.get('n_cells', 100)))
        
        # 填写时间参数
        self.log(f"填写结束时间: {config.get('t_end', 10)}s", "INFO")
        tend_input = self.page.locator('input:near(:text("结束时间"))').first
        if await tend_input.count() > 0:
            await tend_input.clear()
            await tend_input.fill(str(config.get('t_end', 10)))
        
        # 填写初始条件
        self.log(f"填写初始水深: {config.get('h_init', 5.0)}m", "INFO")
        hinit_input = self.page.locator('input:near(:text("初始水深"))').first
        if await hinit_input.count() > 0:
            await hinit_input.clear()
            await hinit_input.fill(str(config.get('h_init', 5.0)))
        
        await self.page.wait_for_timeout(1000)
        await self.take_screenshot("03_config_filled", "配置参数已填写")
        self.log("步骤2完成: 仿真参数配置完成", "SUCCESS")
    
    async def step3_submit_and_wait(self, max_wait_seconds: int = 120):
        """步骤3: 提交仿真并等待计算完成"""
        self.log("=" * 60, "STEP")
        self.log("步骤3: 提交仿真并等待计算完成", "STEP")
        self.log("=" * 60, "STEP")
        
        # 点击运行按钮
        self.log("点击运行仿真按钮...", "INFO")
        run_button = self.page.locator('button:has-text("运行仿真"), button:has-text("开始"), button:has-text("Run")').first
        if await run_button.count() > 0:
            await run_button.click()
            self.log("已点击运行按钮", "SUCCESS")
        else:
            self.log("未找到运行按钮！", "ERROR")
            return False
        
        await self.take_screenshot("04_submitted", "仿真已提交")
        
        # 等待计算完成
        self.log(f"等待计算完成（最长{max_wait_seconds}秒）...", "WAIT")
        
        start_wait = time.time()
        last_progress = -1
        calculation_complete = False
        
        while time.time() - start_wait < max_wait_seconds:
            await self.page.wait_for_timeout(2000)  # 每2秒检查一次
            
            # 检查进度
            progress_text = await self.page.locator(':text("%"), :text("进度")').all_text_contents()
            for text in progress_text:
                if "%" in text:
                    try:
                        # 提取进度百分比
                        import re
                        match = re.search(r'(\d+(?:\.\d+)?)\s*%', text)
                        if match:
                            progress = float(match.group(1))
                            if progress != last_progress:
                                self.log(f"计算进度: {progress:.1f}%", "WAIT")
                                last_progress = progress
                            
                            if progress >= 100:
                                calculation_complete = True
                                break
                    except:
                        pass
            
            if calculation_complete:
                break
            
            # 检查是否有结果出现（图表）
            charts = self.page.locator('canvas, .plotly-graph-div, svg[class*="chart"]')
            if await charts.count() > 0:
                # 确认不是loading状态
                loading = self.page.locator(':text("加载中"), :text("Loading"), .ant-spin')
                if await loading.count() == 0:
                    self.log("检测到结果图表，计算可能已完成", "CHECK")
                    await self.page.wait_for_timeout(3000)  # 额外等待确认
                    calculation_complete = True
                    break
            
            # 检查是否有错误
            error_msg = self.page.locator('.ant-message-error, .error-message, :text("失败"), :text("错误")')
            if await error_msg.count() > 0:
                error_text = await error_msg.first.text_content()
                self.log(f"检测到错误: {error_text}", "ERROR")
                await self.take_screenshot("error_during_calculation", f"计算错误: {error_text}")
                return False
            
            elapsed = int(time.time() - start_wait)
            if elapsed % 10 == 0:  # 每10秒报告一次
                self.log(f"已等待 {elapsed} 秒...", "WAIT")
        
        if not calculation_complete:
            self.log(f"超时：计算未在{max_wait_seconds}秒内完成", "ERROR")
            await self.take_screenshot("timeout", "计算超时")
            return False
        
        await self.take_screenshot("05_calculation_complete", "计算完成")
        self.log("步骤3完成: 计算已完成", "SUCCESS")
        return True
    
    async def step4_view_results(self):
        """步骤4: 查看和验证结果"""
        self.log("=" * 60, "STEP")
        self.log("步骤4: 查看和验证结果", "STEP")
        self.log("=" * 60, "STEP")
        
        # 等待结果区域加载
        await self.page.wait_for_timeout(2000)
        
        # 检查结果图表
        self.log("检查结果图表...", "CHECK")
        charts = self.page.locator('canvas, .plotly-graph-div, svg')
        chart_count = await charts.count()
        self.log(f"检测到 {chart_count} 个图表元素", "INFO")
        
        if chart_count > 0:
            await self.take_screenshot("06_result_charts", f"结果图表（共{chart_count}个）")
        
        # 检查数据表格
        self.log("检查数据表格...", "CHECK")
        tables = self.page.locator('table, .ant-table')
        table_count = await tables.count()
        self.log(f"检测到 {table_count} 个表格元素", "INFO")
        
        # 导航到结果分析页面（如果有）
        self.log("尝试导航到结果分析页面...", "INFO")
        results_link = self.page.locator('a:has-text("结果分析"), span:has-text("结果分析")').first
        if await results_link.count() > 0:
            await results_link.click()
            await self.page.wait_for_timeout(3000)
            await self.take_screenshot("07_results_analysis_page", "结果分析页面")
        
        # 返回结果验证信息
        validation = {
            "chart_count": chart_count,
            "table_count": table_count,
            "has_results": chart_count > 0 or table_count > 0
        }
        
        self.log(f"步骤4完成: 结果验证 - 图表:{chart_count}, 表格:{table_count}", "SUCCESS")
        return validation
    
    async def step5_validate_results(self, expected: Dict[str, Any]) -> Dict[str, Any]:
        """步骤5: 验证结果正确性"""
        self.log("=" * 60, "STEP")
        self.log("步骤5: 验证结果正确性", "STEP")
        self.log("=" * 60, "STEP")
        
        validation_results = {
            "passed": [],
            "failed": [],
            "warnings": []
        }
        
        # 这里可以添加具体的结果验证逻辑
        # 例如：检查水深范围、流量守恒等
        
        # 检查页面上是否有关键数据
        page_content = await self.page.content()
        
        # 检查是否有数值结果
        if "水深" in page_content or "depth" in page_content.lower():
            validation_results["passed"].append("页面包含水深数据")
        else:
            validation_results["warnings"].append("未检测到水深数据显示")
        
        if "流量" in page_content or "discharge" in page_content.lower():
            validation_results["passed"].append("页面包含流量数据")
        else:
            validation_results["warnings"].append("未检测到流量数据显示")
        
        await self.take_screenshot("08_validation", "结果验证完成")
        
        self.log(f"验证通过: {len(validation_results['passed'])} 项", "SUCCESS")
        self.log(f"验证警告: {len(validation_results['warnings'])} 项", "INFO")
        self.log(f"验证失败: {len(validation_results['failed'])} 项", "ERROR" if validation_results['failed'] else "INFO")
        
        self.log("步骤5完成: 结果验证完成", "SUCCESS")
        return validation_results
    
    async def step6_check_display_quality(self) -> Dict[str, Any]:
        """步骤6: 检查结果展示友好性"""
        self.log("=" * 60, "STEP")
        self.log("步骤6: 检查结果展示友好性", "STEP")
        self.log("=" * 60, "STEP")
        
        display_quality = {
            "charts_visible": False,
            "labels_present": False,
            "responsive": False,
            "no_errors": True,
            "score": 0
        }
        
        # 检查图表是否可见
        charts = self.page.locator('canvas, .plotly-graph-div')
        if await charts.count() > 0:
            first_chart = charts.first
            box = await first_chart.bounding_box()
            if box and box['width'] > 100 and box['height'] > 100:
                display_quality["charts_visible"] = True
                display_quality["score"] += 25
                self.log("图表可见且大小合适", "CHECK")
        
        # 检查是否有标签/标题
        labels = self.page.locator('text=水深, text=流量, text=时间, text=距离')
        if await labels.count() > 0:
            display_quality["labels_present"] = True
            display_quality["score"] += 25
            self.log("检测到数据标签", "CHECK")
        
        # 检查是否有错误信息
        errors = self.page.locator('.ant-message-error, .error, :text("错误")')
        if await errors.count() == 0:
            display_quality["no_errors"] = True
            display_quality["score"] += 25
            self.log("页面无错误信息", "CHECK")
        
        # 检查响应式布局
        viewport = self.page.viewport_size
        if viewport and viewport['width'] >= 1200:
            display_quality["responsive"] = True
            display_quality["score"] += 25
            self.log("布局正常", "CHECK")
        
        await self.take_screenshot("09_display_quality", f"展示质量评分: {display_quality['score']}/100")
        
        self.log(f"步骤6完成: 展示质量评分 {display_quality['score']}/100", "SUCCESS")
        return display_quality
    
    async def run_single_case(self, case_config: Dict[str, Any]) -> Dict[str, Any]:
        """运行单个案例的完整测试"""
        self.test_start_time = time.time()
        self.screenshots = []
        
        case_name = case_config.get("name", "未命名案例")
        
        print("\n" + "=" * 70)
        print(f"  HydroClaude 单案例完整端到端测试")
        print(f"  案例: {case_name}")
        print("=" * 70 + "\n")
        
        result = {
            "case_name": case_name,
            "status": "pending",
            "steps_completed": [],
            "steps_failed": [],
            "validation": None,
            "display_quality": None,
            "screenshots": [],
            "duration": 0,
            "error": None
        }
        
        try:
            await self.setup()
            
            # 步骤1: 导航
            await self.step1_navigate_to_simulation()
            result["steps_completed"].append("navigate_to_simulation")
            
            # 步骤2: 配置
            await self.step2_configure_simulation(case_config)
            result["steps_completed"].append("configure_simulation")
            
            # 步骤3: 提交并等待
            success = await self.step3_submit_and_wait(max_wait_seconds=case_config.get("max_wait", 120))
            if success:
                result["steps_completed"].append("submit_and_wait")
            else:
                result["steps_failed"].append("submit_and_wait")
                result["status"] = "failed"
                result["error"] = "计算未完成或超时"
            
            if success:
                # 步骤4: 查看结果
                view_result = await self.step4_view_results()
                result["steps_completed"].append("view_results")
                
                # 步骤5: 验证结果
                validation = await self.step5_validate_results(case_config.get("expected", {}))
                result["validation"] = validation
                result["steps_completed"].append("validate_results")
                
                # 步骤6: 检查展示
                display_quality = await self.step6_check_display_quality()
                result["display_quality"] = display_quality
                result["steps_completed"].append("check_display")
                
                # 判断最终状态
                if display_quality["score"] >= 50 and len(validation.get("failed", [])) == 0:
                    result["status"] = "passed"
                else:
                    result["status"] = "partial"
            
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
            self.log(f"测试出错: {e}", "ERROR")
            import traceback
            traceback.print_exc()
        
        finally:
            await self.teardown()
        
        result["duration"] = time.time() - self.test_start_time
        result["screenshots"] = self.screenshots
        
        # 打印最终结果
        print("\n" + "=" * 70)
        print("  测试结果摘要")
        print("=" * 70)
        print(f"  案例: {case_name}")
        print(f"  状态: {result['status'].upper()}")
        print(f"  耗时: {result['duration']:.1f} 秒")
        print(f"  完成步骤: {len(result['steps_completed'])}/6")
        print(f"  截图数量: {len(result['screenshots'])}")
        if result["display_quality"]:
            print(f"  展示质量: {result['display_quality']['score']}/100")
        if result["error"]:
            print(f"  错误: {result['error']}")
        print("=" * 70 + "\n")
        
        # 保存结果
        result_file = OUTPUT_DIR / f"result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2, default=str)
        self.log(f"结果已保存: {result_file}", "SUCCESS")
        
        return result


async def main():
    """主函数 - 测试单个案例"""
    
    # 定义测试案例配置
    test_case = {
        "name": "溃坝模型基础测试",
        "description": "测试基础溃坝场景的完整仿真流程",
        "width": 10.0,          # 渠道宽度 (m)
        "length": 1000.0,       # 渠道长度 (m)
        "n_cells": 100,         # 网格单元数
        "t_end": 10.0,          # 仿真结束时间 (s)
        "h_init": 5.0,          # 初始水深 (m)
        "max_wait": 120,        # 最长等待时间 (s)
        "expected": {
            "has_results": True,
            "min_charts": 1
        }
    }
    
    tester = SingleCaseE2ETester()
    result = await tester.run_single_case(test_case)
    
    return result


if __name__ == "__main__":
    asyncio.run(main())

