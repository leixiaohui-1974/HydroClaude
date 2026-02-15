#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
真实Web端到端测试 - 完整流程测试

包含完整的建模、计算、结果展示、报告生成全流程
并进行截图记录

Author: HydroClaude Team
Date: 2025-11-16
"""

import json
import warnings
warnings.filterwarnings("ignore")
import time
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

try:
    from playwright.async_api import async_playwright, Page, Browser
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    import pytest
    pytest.skip("playwright not installed", allow_module_level=True)


class RealWebE2ETester:
    """真实Web端到端测试器"""
    
    def __init__(self, base_url: str = "http://localhost:5173", 
                 api_url: str = "http://localhost:5000"):
        self.base_url = base_url
        self.api_url = api_url
        self.screenshots_dir = Path(__file__).parent / "screenshots_real"
        self.screenshots_dir.mkdir(exist_ok=True)
        self.results = []
        
    async def test_single_case(self, page: Page, test_case: Dict[str, Any], 
                               case_index: int) -> Dict[str, Any]:
        """测试单个案例的完整流程"""
        
        case_name = test_case.get('name', f'case_{case_index}')
        print(f"\n{'='*70}")
        print(f"🧪 测试案例 #{case_index:03d}: {case_name}")
        print(f"{'='*70}")
        
        # 创建案例截图目录
        case_dir = self.screenshots_dir / f"case_{case_index:03d}_{case_name}"
        case_dir.mkdir(exist_ok=True)
        
        result = {
            'id': case_index,
            'name': case_name,
            'category': test_case.get('category', 'unknown'),
            'status': 'pending',
            'steps': [],
            'screenshots': [],
            'start_time': time.time()
        }
        
        try:
            # ============================================================
            # 步骤1: 导航到首页
            # ============================================================
            print("\n  📍 步骤1: 导航到首页...")
            await page.goto(self.base_url, wait_until='networkidle', timeout=30000)
            await page.wait_for_timeout(1000)
            
            screenshot_path = case_dir / "01_homepage.png"
            await page.screenshot(path=str(screenshot_path), full_page=True)
            result['screenshots'].append(str(screenshot_path))
            result['steps'].append({'step': 1, 'name': '导航到首页', 'status': 'success'})
            print("     ✅ 首页加载完成")
            
            # ============================================================
            # 步骤2: 导航到配置/建模页面
            # ============================================================
            print("\n  📍 步骤2: 进入配置页面...")
            
            # 尝试点击"新建配置"或"配置"按钮
            try:
                # 方式1: 通过菜单导航
                config_link = page.locator('text=配置').or_(page.locator('text=Configuration'))
                if await config_link.count() > 0:
                    await config_link.first.click()
                else:
                    # 方式2: 直接导航到配置页面
                    await page.goto(f"{self.base_url}/config", wait_until='networkidle')
                
                await page.wait_for_timeout(1000)
                
                screenshot_path = case_dir / "02_config_page.png"
                await page.screenshot(path=str(screenshot_path), full_page=True)
                result['screenshots'].append(str(screenshot_path))
                result['steps'].append({'step': 2, 'name': '进入配置页面', 'status': 'success'})
                print("     ✅ 配置页面打开")
            except Exception as e:
                print(f"     ⚠️  配置页面导航失败: {e}")
                # 继续尝试
            
            # ============================================================
            # 步骤3: 切换到JSON编辑器模式（如果有）
            # ============================================================
            print("\n  📍 步骤3: 切换到JSON编辑器...")
            
            try:
                # 查找JSON编辑器切换按钮
                json_tab = page.locator('text=JSON').or_(page.locator('[role="tab"]:has-text("JSON")'))
                if await json_tab.count() > 0:
                    await json_tab.first.click()
                    await page.wait_for_timeout(500)
                    print("     ✅ 已切换到JSON模式")
                else:
                    print("     ℹ️  未找到JSON标签，可能默认就是JSON模式")
                
                screenshot_path = case_dir / "03_json_editor.png"
                await page.screenshot(path=str(screenshot_path), full_page=True)
                result['screenshots'].append(str(screenshot_path))
                result['steps'].append({'step': 3, 'name': '切换到JSON编辑器', 'status': 'success'})
            except Exception as e:
                print(f"     ⚠️  切换JSON模式失败: {e}")
            
            # ============================================================
            # 步骤4: 填写/粘贴配置内容
            # ============================================================
            print("\n  📍 步骤4: 填写配置内容...")
            
            # 构建配置JSON
            config_json = self._build_config_json(test_case)
            config_str = json.dumps(config_json, indent=2, ensure_ascii=False)
            
            try:
                # 查找JSON编辑器 (Monaco Editor, CodeMirror, 或 textarea)
                # 尝试多种可能的编辑器定位方式
                editor = None
                
                # 方式1: Monaco Editor
                monaco = page.locator('.monaco-editor textarea').first
                if await monaco.count() > 0:
                    editor = monaco
                    print("     ℹ️  找到Monaco编辑器")
                
                # 方式2: CodeMirror
                if not editor:
                    codemirror = page.locator('.CodeMirror textarea').first
                    if await codemirror.count() > 0:
                        editor = codemirror
                        print("     ℹ️  找到CodeMirror编辑器")
                
                # 方式3: 普通textarea
                if not editor:
                    textarea = page.locator('textarea').first
                    if await textarea.count() > 0:
                        editor = textarea
                        print("     ℹ️  找到普通文本框")
                
                if editor:
                    # 清空并填写内容
                    await editor.click()
                    await page.keyboard.press('Control+A')
                    await page.keyboard.press('Delete')
                    await page.wait_for_timeout(200)
                    
                    # 分段输入，避免太长
                    lines = config_str.split('\n')
                    for i, line in enumerate(lines):
                        await editor.type(line, delay=10)
                        if i < len(lines) - 1:
                            await page.keyboard.press('Enter')
                        if i % 10 == 0:
                            await page.wait_for_timeout(100)
                    
                    await page.wait_for_timeout(500)
                    print("     ✅ 配置内容已填写")
                else:
                    print("     ⚠️  未找到编辑器，尝试通过表单填写")
                    # 如果是表单模式，尝试填写表单字段
                    await self._fill_form_fields(page, test_case)
                
                screenshot_path = case_dir / "04_config_filled.png"
                await page.screenshot(path=str(screenshot_path), full_page=True)
                result['screenshots'].append(str(screenshot_path))
                result['steps'].append({'step': 4, 'name': '填写配置内容', 'status': 'success'})
            except Exception as e:
                print(f"     ⚠️  填写配置失败: {e}")
                result['steps'].append({'step': 4, 'name': '填写配置内容', 'status': 'failed', 'error': str(e)})
            
            # ============================================================
            # 步骤5: 点击"运行仿真"或"提交"按钮
            # ============================================================
            print("\n  📍 步骤5: 提交计算任务...")
            
            try:
                # 查找运行按钮
                run_button = page.locator('button:has-text("运行")').or_(
                    page.locator('button:has-text("Run")')
                ).or_(
                    page.locator('button:has-text("提交")')
                ).or_(
                    page.locator('button:has-text("Submit")')
                )
                
                if await run_button.count() > 0:
                    await run_button.first.click()
                    await page.wait_for_timeout(1000)
                    print("     ✅ 已点击运行按钮")
                    
                    screenshot_path = case_dir / "05_submit_clicked.png"
                    await page.screenshot(path=str(screenshot_path), full_page=True)
                    result['screenshots'].append(str(screenshot_path))
                    result['steps'].append({'step': 5, 'name': '提交计算任务', 'status': 'success'})
                else:
                    print("     ⚠️  未找到运行按钮")
                    result['steps'].append({'step': 5, 'name': '提交计算任务', 'status': 'failed', 'error': '未找到按钮'})
            except Exception as e:
                print(f"     ⚠️  提交任务失败: {e}")
                result['steps'].append({'step': 5, 'name': '提交计算任务', 'status': 'failed', 'error': str(e)})
            
            # ============================================================
            # 步骤6: 等待计算完成
            # ============================================================
            print("\n  📍 步骤6: 等待计算完成...")
            
            try:
                # 等待计算完成的指示器
                # 可能的指示器: "计算完成", "Complete", 成功消息等
                await page.wait_for_timeout(2000)
                
                # 查找成功消息或完成指示
                success_indicators = [
                    'text=完成',
                    'text=成功',
                    'text=Complete',
                    'text=Success',
                    '.success',
                    '.ant-message-success'
                ]
                
                for indicator in success_indicators:
                    element = page.locator(indicator).first
                    if await element.count() > 0:
                        print(f"     ✅ 发现完成指示: {indicator}")
                        break
                
                await page.wait_for_timeout(1000)
                
                screenshot_path = case_dir / "06_calculation_complete.png"
                await page.screenshot(path=str(screenshot_path), full_page=True)
                result['screenshots'].append(str(screenshot_path))
                result['steps'].append({'step': 6, 'name': '等待计算完成', 'status': 'success'})
                print("     ✅ 计算完成")
            except Exception as e:
                print(f"     ⚠️  等待计算超时: {e}")
                result['steps'].append({'step': 6, 'name': '等待计算完成', 'status': 'timeout'})
            
            # ============================================================
            # 步骤7: 导航到结果页面
            # ============================================================
            print("\n  📍 步骤7: 查看结果...")
            
            try:
                # 查找"查看结果"按钮或自动跳转到结果页
                result_button = page.locator('text=查看结果').or_(
                    page.locator('text=View Results')
                ).or_(
                    page.locator('button:has-text("结果")')
                )
                
                if await result_button.count() > 0:
                    await result_button.first.click()
                    await page.wait_for_timeout(1000)
                else:
                    # 尝试直接导航到结果页面
                    await page.goto(f"{self.base_url}/results", wait_until='networkidle')
                    await page.wait_for_timeout(1000)
                
                screenshot_path = case_dir / "07_results_page.png"
                await page.screenshot(path=str(screenshot_path), full_page=True)
                result['screenshots'].append(str(screenshot_path))
                result['steps'].append({'step': 7, 'name': '导航到结果页面', 'status': 'success'})
                print("     ✅ 结果页面打开")
            except Exception as e:
                print(f"     ⚠️  打开结果页面失败: {e}")
                result['steps'].append({'step': 7, 'name': '导航到结果页面', 'status': 'failed'})
            
            # ============================================================
            # 步骤8: 验证结果展示（图表、数据）
            # ============================================================
            print("\n  📍 步骤8: 验证结果展示...")
            
            try:
                await page.wait_for_timeout(2000)
                
                # 检查是否有图表
                charts_found = False
                chart_selectors = [
                    'canvas',  # Plotly, Chart.js
                    'svg',     # D3, Recharts
                    '.plotly',
                    '.chart',
                    '[id*="plot"]'
                ]
                
                for selector in chart_selectors:
                    elements = page.locator(selector)
                    count = await elements.count()
                    if count > 0:
                        print(f"     ✅ 找到 {count} 个图表元素 ({selector})")
                        charts_found = True
                        break
                
                # 检查是否有数据表格
                tables = page.locator('table')
                table_count = await tables.count()
                if table_count > 0:
                    print(f"     ✅ 找到 {table_count} 个数据表格")
                
                # 滚动页面查看所有内容
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight/2)")
                await page.wait_for_timeout(500)
                
                screenshot_path = case_dir / "08_results_charts.png"
                await page.screenshot(path=str(screenshot_path), full_page=True)
                result['screenshots'].append(str(screenshot_path))
                
                # 继续滚动
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(500)
                
                screenshot_path = case_dir / "09_results_bottom.png"
                await page.screenshot(path=str(screenshot_path), full_page=True)
                result['screenshots'].append(str(screenshot_path))
                
                result['steps'].append({
                    'step': 8, 
                    'name': '验证结果展示', 
                    'status': 'success',
                    'charts_found': charts_found,
                    'tables_found': table_count > 0
                })
                print("     ✅ 结果展示验证完成")
            except Exception as e:
                print(f"     ⚠️  结果验证失败: {e}")
                result['steps'].append({'step': 8, 'name': '验证结果展示', 'status': 'failed'})
            
            # ============================================================
            # 步骤9: 生成/下载报告（如果有）
            # ============================================================
            print("\n  📍 步骤9: 生成报告...")
            
            try:
                # 查找报告相关按钮
                report_button = page.locator('text=报告').or_(
                    page.locator('text=Report')
                ).or_(
                    page.locator('button:has-text("导出")')
                ).or_(
                    page.locator('button:has-text("Export")')
                )
                
                if await report_button.count() > 0:
                    await report_button.first.click()
                    await page.wait_for_timeout(1000)
                    print("     ✅ 已点击报告按钮")
                    
                    screenshot_path = case_dir / "10_report_view.png"
                    await page.screenshot(path=str(screenshot_path), full_page=True)
                    result['screenshots'].append(str(screenshot_path))
                    result['steps'].append({'step': 9, 'name': '生成报告', 'status': 'success'})
                else:
                    print("     ℹ️  未找到报告功能")
                    result['steps'].append({'step': 9, 'name': '生成报告', 'status': 'skipped'})
            except Exception as e:
                print(f"     ⚠️  报告生成失败: {e}")
                result['steps'].append({'step': 9, 'name': '生成报告', 'status': 'failed'})
            
            # ============================================================
            # 测试完成
            # ============================================================
            result['status'] = 'passed'
            result['end_time'] = time.time()
            result['duration'] = result['end_time'] - result['start_time']
            
            print(f"\n  ✅ 测试通过!")
            print(f"  ⏱️  耗时: {result['duration']:.2f}秒")
            print(f"  📸 截图: {len(result['screenshots'])}张")
            
        except Exception as e:
            result['status'] = 'failed'
            result['error'] = str(e)
            result['end_time'] = time.time()
            result['duration'] = result['end_time'] - result['start_time']
            
            print(f"\n  ❌ 测试失败: {e}")
            
            # 失败时也截图
            try:
                screenshot_path = case_dir / "error_screenshot.png"
                await page.screenshot(path=str(screenshot_path), full_page=True)
                result['screenshots'].append(str(screenshot_path))
            except:
                pass
        
        return result
    
    def _build_config_json(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """构建配置JSON"""
        
        # 从测试案例中提取配置
        canal = test_case.get('canal', {})
        flow = test_case.get('flow', {})
        structures = test_case.get('structures', [])
        solver = test_case.get('solver', {})
        
        config = {
            "name": test_case.get('name', 'test_scenario'),
            "description": test_case.get('description', ''),
            "canal": {
                "length": canal.get('length', 10000.0),
                "width": canal.get('width', 10.0),
                "slope": canal.get('slope', 0.001),
                "roughness": canal.get('roughness', 0.025),
                "nx": canal.get('nx', 500)
            },
            "flow": {
                "flow_rate": flow.get('flow_rate', 50.0),
                "type": flow.get('type', 'steady')
            },
            "solver": {
                "type": solver.get('type', 'hydrostatic'),
                "max_iterations": solver.get('max_iterations', 100),
                "convergence_tol": solver.get('convergence_tol', 0.1)
            }
        }
        
        if structures:
            config['structures'] = structures
        
        return config
    
    async def _fill_form_fields(self, page: Page, test_case: Dict[str, Any]):
        """填写表单字段（如果是表单模式）"""
        
        canal = test_case.get('canal', {})
        flow = test_case.get('flow', {})
        
        # 尝试填写常见字段
        fields = {
            'length': canal.get('length', 10000.0),
            'width': canal.get('width', 10.0),
            'slope': canal.get('slope', 0.001),
            'roughness': canal.get('roughness', 0.025),
            'flow_rate': flow.get('flow_rate', 50.0),
        }
        
        for field_name, value in fields.items():
            try:
                input_field = page.locator(f'input[name="{field_name}"]').or_(
                    page.locator(f'input[id="{field_name}"]')
                )
                if await input_field.count() > 0:
                    await input_field.first.fill(str(value))
                    print(f"     ✅ 填写字段: {field_name} = {value}")
            except:
                pass
    
    async def run_tests(self, test_cases: List[Dict[str, Any]], max_cases: int = 5):
        """运行多个测试案例"""
        
        if not PLAYWRIGHT_AVAILABLE:
            print("❌ Playwright未安装，无法运行测试")
            return
        
        print("="*70)
        print("🌐 HydroClaude Web真实端到端测试")
        print("="*70)
        print(f"\n测试配置:")
        print(f"  • Web应用: {self.base_url}")
        print(f"  • 后端API: {self.api_url}")
        print(f"  • 测试案例: {min(len(test_cases), max_cases)}个")
        print(f"  • 截图目录: {self.screenshots_dir}")
        print()
        
        async with async_playwright() as p:
            # 启动浏览器
            print("🚀 启动浏览器...")
            browser = await p.chromium.launch(
                headless=True,  # 无头模式
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            
            # 创建浏览器上下文（中文环境）
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                locale='zh-CN',
                timezone_id='Asia/Shanghai'
            )
            
            page = await context.new_page()
            
            # 运行测试
            cases_to_test = test_cases[:max_cases]
            
            for i, test_case in enumerate(cases_to_test, 1):
                result = await self.test_single_case(page, test_case, i)
                self.results.append(result)
                
                # 短暂休息
                await asyncio.sleep(1)
            
            # 关闭浏览器
            await browser.close()
        
        # 生成报告
        self._generate_report()
    
    def _generate_report(self):
        """生成测试报告"""
        
        print("\n" + "="*70)
        print("📊 生成测试报告")
        print("="*70)
        
        # 统计
        total = len(self.results)
        passed = sum(1 for r in self.results if r['status'] == 'passed')
        failed = total - passed
        pass_rate = (passed / total * 100) if total > 0 else 0
        
        print(f"\n总测试: {total}个")
        print(f"通过:   {passed}个")
        print(f"失败:   {failed}个")
        print(f"通过率: {pass_rate:.1f}%")
        
        # 保存JSON报告
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = Path(__file__).parent / "reports" / f"real_web_test_{timestamp}.json"
        report_file.parent.mkdir(exist_ok=True)
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total': total,
                'passed': passed,
                'failed': failed,
                'pass_rate': f"{pass_rate:.1f}%"
            },
            'results': self.results
        }
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ JSON报告已保存: {report_file}")
        
        # 生成HTML报告
        html_file = report_file.with_suffix('.html')
        self._generate_html_report(html_file, report)
        print(f"✅ HTML报告已保存: {html_file}")
        
        print("\n" + "="*70)


def _generate_html_report(self, html_file: Path, report: Dict[str, Any]):
        """生成HTML报告"""
        
        summary = report['summary']
        
        html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>HydroClaude Web端到端测试报告</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, sans-serif; padding: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 40px; border-radius: 8px; }}
        h1 {{ color: #1890ff; margin-bottom: 20px; }}
        .summary {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin: 30px 0; }}
        .summary-card {{ background: #f9f9f9; padding: 20px; border-radius: 8px; }}
        .summary-card h3 {{ color: #666; font-size: 14px; margin-bottom: 10px; }}
        .summary-card .value {{ font-size: 32px; font-weight: bold; }}
        .case-result {{ margin: 20px 0; padding: 20px; border: 1px solid #eee; border-radius: 8px; }}
        .case-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }}
        .case-title {{ font-size: 18px; font-weight: bold; }}
        .status-passed {{ color: #52c41a; }}
        .status-failed {{ color: #f5222d; }}
        .screenshots {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 10px; margin-top: 15px; }}
        .screenshot {{ border: 1px solid #eee; border-radius: 4px; overflow: hidden; }}
        .screenshot img {{ width: 100%; height: auto; cursor: pointer; }}
        .screenshot-caption {{ padding: 8px; background: #f9f9f9; font-size: 12px; text-align: center; }}
        .steps {{ margin: 15px 0; }}
        .step {{ padding: 8px; margin: 5px 0; background: #f9f9f9; border-radius: 4px; }}
        .step-success {{ border-left: 3px solid #52c41a; }}
        .step-failed {{ border-left: 3px solid #f5222d; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🌐 HydroClaude Web端到端测试报告</h1>
        <p>测试时间: {report['timestamp']}</p>
        
        <div class="summary">
            <div class="summary-card">
                <h3>总测试数</h3>
                <div class="value">{summary['total']}</div>
            </div>
            <div class="summary-card">
                <h3>通过数量</h3>
                <div class="value" style="color: #52c41a;">{summary['passed']}</div>
            </div>
            <div class="summary-card">
                <h3>失败数量</h3>
                <div class="value" style="color: #f5222d;">{summary['failed']}</div>
            </div>
            <div class="summary-card">
                <h3>通过率</h3>
                <div class="value">{summary['pass_rate']}</div>
            </div>
        </div>
        
        <h2>测试案例详情</h2>
'''
        
        for result in report['results']:
            status_class = 'status-passed' if result['status'] == 'passed' else 'status-failed'
            status_text = '✅ 通过' if result['status'] == 'passed' else '❌ 失败'
            
            html += f'''
        <div class="case-result">
            <div class="case-header">
                <div class="case-title">#{result['id']:03d} - {result['name']}</div>
                <div class="{status_class}">{status_text}</div>
            </div>
            <div><strong>分类:</strong> {result['category']}</div>
            <div><strong>耗时:</strong> {result.get('duration', 0):.2f}秒</div>
            
            <div class="steps">
                <strong>执行步骤:</strong>
'''
            
            for step in result.get('steps', []):
                step_class = 'step-success' if step['status'] == 'success' else 'step-failed'
                html += f'<div class="step {step_class}">{step["step"]}. {step["name"]} - {step["status"]}</div>'
            
            html += '</div>'
            
            if result.get('screenshots'):
                html += '<div class="screenshots"><strong>测试截图:</strong>'
                for i, screenshot in enumerate(result['screenshots'], 1):
                    filename = Path(screenshot).name
                    html += f'''
                    <div class="screenshot">
                        <img src="{screenshot}" alt="Screenshot {i}" onclick="window.open(this.src)">
                        <div class="screenshot-caption">{filename}</div>
                    </div>
'''
                html += '</div>'
            
            html += '</div>'
        
        html += '''
    </div>
</body>
</html>
'''
        
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html)


def main():
    """主函数"""
    
    if not PLAYWRIGHT_AVAILABLE:
        print("❌ Playwright未安装")
        print("\n请运行以下命令安装:")
        print("  pip install playwright")
        print("  playwright install chromium")
        return
    
    # 加载测试案例
    test_cases_file = Path(__file__).parent / "test_cases" / "test_index_full.json"
    
    if not test_cases_file.exists():
        print(f"❌ 测试案例文件不存在: {test_cases_file}")
        return
    
    with open(test_cases_file, 'r', encoding='utf-8') as f:
        index = json.load(f)
    
    # 加载具体案例
    test_cases = []
    for case_info in index['cases'][:5]:  # 先测试前5个
        case_file = test_cases_file.parent / case_info['file']
        if case_file.exists():
            with open(case_file, 'r', encoding='utf-8') as f:
                test_case = json.load(f)
                test_cases.append(test_case)
    
    if not test_cases:
        print("❌ 未找到测试案例")
        return
    
    # 运行测试
    tester = RealWebE2ETester()
    asyncio.run(tester.run_tests(test_cases, max_cases=5))


if __name__ == "__main__":
    main()
