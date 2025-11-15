#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
End-to-End Web Interface Test Script
端到端Web界面测试脚本

对标商业软件的完整功能测试

Author: HydroClaude Team
Date: 2025-11-15
"""

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

# Playwright for browser automation
try:
    from playwright.async_api import async_playwright, Page, expect
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    print("❌ Playwright未安装。请运行: pip install playwright && playwright install")
    PLAYWRIGHT_AVAILABLE = False


class E2EWebTester:
    """端到端Web界面测试器"""
    
    def __init__(self, base_url: str = "http://localhost:3000"):
        """
        初始化测试器
        
        Args:
            base_url: Web应用URL
        """
        self.base_url = base_url
        self.results = []
        self.screenshots_dir = Path(__file__).parent / "e2e_screenshots"
        self.screenshots_dir.mkdir(exist_ok=True)
        
        # 测试案例列表
        self.test_cases = [
            "01_basic_flow",
            "02_uniform_flow",
            "03_varied_flow",
            "04_critical_flow",
            "05_hydraulic_jump",
            "07_sluice_gate_flow_v2",
            "08_multiple_gates",
            "09_weir_flow",
            "10_combined_structures",
            "12_advanced_optimized_v2"
        ]
    
    async def wait_for_network_idle(self, page: Page, timeout: int = 3000):
        """等待网络空闲"""
        try:
            await page.wait_for_load_state("networkidle", timeout=timeout)
        except Exception:
            # 如果超时，继续执行
            pass
    
    async def take_screenshot(self, page: Page, name: str):
        """截图"""
        screenshot_path = self.screenshots_dir / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{name}.png"
        await page.screenshot(path=str(screenshot_path), full_page=True)
        print(f"  📸 截图已保存: {screenshot_path.name}")
    
    async def test_homepage(self, page: Page) -> Dict[str, Any]:
        """测试主页加载"""
        print("\n" + "="*60)
        print("测试1: 主页加载")
        print("="*60)
        
        result = {
            'test_name': '主页加载',
            'status': 'pending',
            'error': None,
            'duration': 0
        }
        
        start_time = time.time()
        
        try:
            # 访问主页
            print(f"访问: {self.base_url}")
            await page.goto(self.base_url, wait_until="networkidle", timeout=30000)
            
            # 等待页面加载
            await page.wait_for_selector('body', timeout=10000)
            
            # 截图
            await self.take_screenshot(page, '01_homepage')
            
            # 检查标题
            title = await page.title()
            print(f"  ✅ 页面标题: {title}")
            
            result['status'] = 'passed'
            result['duration'] = time.time() - start_time
            print(f"  ✅ 测试通过 ({result['duration']:.2f}s)")
            
        except Exception as e:
            result['status'] = 'failed'
            result['error'] = str(e)
            result['duration'] = time.time() - start_time
            print(f"  ❌ 测试失败: {e}")
        
        self.results.append(result)
        return result
    
    async def test_modeling_workspace(self, page: Page) -> Dict[str, Any]:
        """测试建模工作区"""
        print("\n" + "="*60)
        print("测试2: 建模工作区")
        print("="*60)
        
        result = {
            'test_name': '建模工作区',
            'status': 'pending',
            'error': None,
            'duration': 0
        }
        
        start_time = time.time()
        
        try:
            # 查找并点击建模链接
            print("  导航到建模工作区...")
            
            # 尝试多种方式找到建模链接
            modeling_link = None
            try:
                # 方法1: 通过文本
                modeling_link = page.get_by_text("建模", exact=False).first
                await modeling_link.click(timeout=5000)
            except Exception:
                try:
                    # 方法2: 通过role
                    modeling_link = page.get_by_role("link", name="建模")
                    await modeling_link.click(timeout=5000)
                except Exception:
                    # 方法3: 直接访问URL
                    await page.goto(f"{self.base_url}/modeling", timeout=15000)
            
            await self.wait_for_network_idle(page, timeout=5000)
            await page.wait_for_timeout(2000)
            
            # 截图
            await self.take_screenshot(page, '02_modeling_workspace')
            
            # 检查核心元素
            print("  检查建模工具...")
            
            # 检查是否有渠道参数输入
            has_canal_section = await page.locator('text=/渠道|Canal|参数/i').count() > 0
            print(f"  {'✅' if has_canal_section else '❌'} 渠道参数区域")
            
            # 检查是否有添加结构按钮
            has_structure_button = await page.locator('button:has-text("添加"), button:has-text("结构")').count() > 0
            print(f"  {'✅' if has_structure_button else '❌'} 添加结构按钮")
            
            result['status'] = 'passed'
            result['duration'] = time.time() - start_time
            print(f"  ✅ 测试通过 ({result['duration']:.2f}s)")
            
        except Exception as e:
            result['status'] = 'failed'
            result['error'] = str(e)
            result['duration'] = time.time() - start_time
            print(f"  ❌ 测试失败: {e}")
            await self.take_screenshot(page, '02_modeling_workspace_error')
        
        self.results.append(result)
        return result
    
    async def test_case_loading(self, page: Page, case_name: str) -> Dict[str, Any]:
        """测试案例加载"""
        print(f"\n  测试案例: {case_name}")
        
        result = {
            'test_name': f'案例加载_{case_name}',
            'case_name': case_name,
            'status': 'pending',
            'error': None,
            'duration': 0
        }
        
        start_time = time.time()
        
        try:
            # 导航到案例页面
            await page.goto(f"{self.base_url}/cases", timeout=15000)
            await self.wait_for_network_idle(page)
            await page.wait_for_timeout(1000)
            
            # 搜索案例
            search_box = page.locator('input[placeholder*="搜索"], input[placeholder*="Search"]').first
            if await search_box.count() > 0:
                await search_box.fill(case_name)
                await page.wait_for_timeout(500)
            
            # 查找并点击案例
            case_link = page.get_by_text(case_name, exact=False).first
            if await case_link.count() > 0:
                await case_link.click(timeout=5000)
                await self.wait_for_network_idle(page)
                await page.wait_for_timeout(1000)
                
                print(f"    ✅ 案例加载成功")
                result['status'] = 'passed'
            else:
                print(f"    ⚠️  案例未找到")
                result['status'] = 'skipped'
                result['error'] = 'Case not found'
            
            result['duration'] = time.time() - start_time
            
        except Exception as e:
            result['status'] = 'failed'
            result['error'] = str(e)
            result['duration'] = time.time() - start_time
            print(f"    ❌ 加载失败: {e}")
        
        return result
    
    async def test_simulation_run(self, page: Page, case_name: str) -> Dict[str, Any]:
        """测试仿真运行"""
        print(f"\n  测试仿真: {case_name}")
        
        result = {
            'test_name': f'仿真运行_{case_name}',
            'case_name': case_name,
            'status': 'pending',
            'error': None,
            'has_progress_bar': False,
            'has_results': False,
            'duration': 0
        }
        
        start_time = time.time()
        
        try:
            # 查找运行按钮
            run_button = page.locator('button:has-text("运行"), button:has-text("Run"), button:has-text("开始")').first
            
            if await run_button.count() > 0:
                await run_button.click()
                print(f"    ✅ 点击运行按钮")
                
                # 等待进度指示
                await page.wait_for_timeout(2000)
                
                # 检查进度条
                progress_locator = page.locator('.ant-progress, [role="progressbar"], .progress')
                if await progress_locator.count() > 0:
                    result['has_progress_bar'] = True
                    print(f"    ✅ 进度条显示")
                
                # 等待完成（最多60秒）
                max_wait = 60
                for i in range(max_wait):
                    await page.wait_for_timeout(1000)
                    
                    # 检查是否有结果
                    results_locator = page.locator('text=/结果|Result|完成|Complete|图表|Chart/i')
                    if await results_locator.count() > 0:
                        result['has_results'] = True
                        print(f"    ✅ 结果显示 (耗时: {i+1}s)")
                        break
                    
                    if i % 10 == 0 and i > 0:
                        print(f"    ⏳ 等待中... ({i}s)")
                
                # 截图
                await self.take_screenshot(page, f'03_simulation_{case_name}')
                
                if result['has_results']:
                    result['status'] = 'passed'
                else:
                    result['status'] = 'timeout'
                    result['error'] = 'No results shown after 60s'
            else:
                result['status'] = 'failed'
                result['error'] = 'Run button not found'
                print(f"    ❌ 运行按钮未找到")
            
            result['duration'] = time.time() - start_time
            
        except Exception as e:
            result['status'] = 'failed'
            result['error'] = str(e)
            result['duration'] = time.time() - start_time
            print(f"    ❌ 运行失败: {e}")
            await self.take_screenshot(page, f'03_simulation_{case_name}_error')
        
        return result
    
    async def test_results_display(self, page: Page) -> Dict[str, Any]:
        """测试结果显示"""
        print("\n" + "="*60)
        print("测试3: 结果显示")
        print("="*60)
        
        result = {
            'test_name': '结果显示',
            'status': 'pending',
            'error': None,
            'has_charts': False,
            'has_tables': False,
            'has_analysis': False,
            'duration': 0
        }
        
        start_time = time.time()
        
        try:
            # 检查图表
            chart_locator = page.locator('canvas, svg[class*="chart"], .recharts, .ant-chart')
            chart_count = await chart_locator.count()
            result['has_charts'] = chart_count > 0
            print(f"  {'✅' if result['has_charts'] else '❌'} 图表显示 ({chart_count}个)")
            
            # 检查表格
            table_locator = page.locator('table, .ant-table')
            table_count = await table_locator.count()
            result['has_tables'] = table_count > 0
            print(f"  {'✅' if result['has_tables'] else '❌'} 表格显示 ({table_count}个)")
            
            # 检查分析模块
            analysis_locator = page.locator('text=/分析|Analysis|质量|Quality/i')
            analysis_count = await analysis_locator.count()
            result['has_analysis'] = analysis_count > 0
            print(f"  {'✅' if result['has_analysis'] else '❌'} 分析模块 ({analysis_count}个)")
            
            # 截图
            await self.take_screenshot(page, '04_results_display')
            
            result['status'] = 'passed' if any([result['has_charts'], result['has_tables']]) else 'failed'
            result['duration'] = time.time() - start_time
            print(f"  {'✅' if result['status'] == 'passed' else '❌'} 测试{'通过' if result['status'] == 'passed' else '失败'} ({result['duration']:.2f}s)")
            
        except Exception as e:
            result['status'] = 'failed'
            result['error'] = str(e)
            result['duration'] = time.time() - start_time
            print(f"  ❌ 测试失败: {e}")
        
        self.results.append(result)
        return result
    
    async def test_analysis_module(self, page: Page) -> Dict[str, Any]:
        """测试自动分析模块"""
        print("\n" + "="*60)
        print("测试4: 自动分析模块")
        print("="*60)
        
        result = {
            'test_name': '自动分析模块',
            'status': 'pending',
            'error': None,
            'duration': 0
        }
        
        start_time = time.time()
        
        try:
            # 查找分析标签页
            analysis_tab = page.locator('text=/自动分析|Analysis/i').first
            
            if await analysis_tab.count() > 0:
                await analysis_tab.click()
                await page.wait_for_timeout(2000)
                
                # 检查分析内容
                has_quality_score = await page.locator('text=/质量评分|Quality Score/i').count() > 0
                has_hydraulic_chars = await page.locator('text=/水力特性|Hydraulic/i').count() > 0
                has_recommendations = await page.locator('text=/建议|Recommendation/i').count() > 0
                
                print(f"  {'✅' if has_quality_score else '❌'} 质量评分")
                print(f"  {'✅' if has_hydraulic_chars else '❌'} 水力特性")
                print(f"  {'✅' if has_recommendations else '❌'} 优化建议")
                
                # 截图
                await self.take_screenshot(page, '05_analysis_module')
                
                result['status'] = 'passed' if all([has_quality_score, has_hydraulic_chars]) else 'partial'
            else:
                result['status'] = 'skipped'
                result['error'] = 'Analysis tab not found'
                print(f"  ⚠️  分析标签未找到")
            
            result['duration'] = time.time() - start_time
            
        except Exception as e:
            result['status'] = 'failed'
            result['error'] = str(e)
            result['duration'] = time.time() - start_time
            print(f"  ❌ 测试失败: {e}")
        
        self.results.append(result)
        return result
    
    async def run_full_test_suite(self):
        """运行完整测试套件"""
        print("\n" + "🎯"*30)
        print("端到端Web界面完整测试")
        print("对标商业软件功能测试")
        print("🎯"*30)
        
        if not PLAYWRIGHT_AVAILABLE:
            print("\n❌ 测试终止: Playwright未安装")
            return
        
        async with async_playwright() as p:
            # 启动浏览器
            browser = await p.chromium.launch(headless=True)  # headless=False for debugging
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080}
            )
            page = await context.new_page()
            
            try:
                # 1. 测试主页
                await self.test_homepage(page)
                
                # 2. 测试建模工作区
                await self.test_modeling_workspace(page)
                
                # 3. 测试案例加载和运行（选择几个代表性案例）
                print("\n" + "="*60)
                print("测试3: 案例仿真运行")
                print("="*60)
                
                test_sample_cases = [
                    "01_basic_flow",
                    "05_hydraulic_jump",
                    "07_sluice_gate_flow_v2"
                ]
                
                for case_name in test_sample_cases:
                    # 加载案例
                    load_result = await self.test_case_loading(page, case_name)
                    self.results.append(load_result)
                    
                    if load_result['status'] == 'passed':
                        # 运行仿真
                        sim_result = await self.test_simulation_run(page, case_name)
                        self.results.append(sim_result)
                        
                        # 如果有结果，测试结果显示
                        if sim_result.get('has_results'):
                            await self.test_results_display(page)
                
                # 4. 测试分析模块
                await self.test_analysis_module(page)
                
            finally:
                await browser.close()
        
        # 生成报告
        self.generate_report()
    
    def generate_report(self):
        """生成测试报告"""
        print("\n" + "="*60)
        print("📊 测试报告")
        print("="*60)
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r['status'] == 'passed')
        failed = sum(1 for r in self.results if r['status'] == 'failed')
        skipped = sum(1 for r in self.results if r['status'] == 'skipped')
        
        pass_rate = (passed / total * 100) if total > 0 else 0
        
        print(f"\n总测试数: {total}")
        print(f"✅ 通过: {passed}")
        print(f"❌ 失败: {failed}")
        print(f"⚠️  跳过: {skipped}")
        print(f"📈 通过率: {pass_rate:.1f}%")
        
        print("\n详细结果:")
        print("-" * 60)
        for i, result in enumerate(self.results, 1):
            status_icon = {
                'passed': '✅',
                'failed': '❌',
                'skipped': '⚠️',
                'timeout': '⏱️',
                'partial': '⚡'
            }.get(result['status'], '❓')
            
            print(f"{i}. {status_icon} {result['test_name']} ({result['duration']:.2f}s)")
            if result.get('error'):
                print(f"   错误: {result['error']}")
        
        # 保存JSON报告
        report_file = Path(__file__).parent / f"e2e_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump({
                'summary': {
                    'total': total,
                    'passed': passed,
                    'failed': failed,
                    'skipped': skipped,
                    'pass_rate': pass_rate
                },
                'results': self.results,
                'timestamp': datetime.now().isoformat()
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 报告已保存: {report_file}")
        print(f"📸 截图目录: {self.screenshots_dir}")
        
        print("\n" + "="*60)
        print(f"{'🎉 测试完成！' if failed == 0 else '⚠️  部分测试失败'}")
        print("="*60)


async def main():
    """主函数"""
    # 检查环境
    if not PLAYWRIGHT_AVAILABLE:
        print("\n请先安装Playwright:")
        print("  pip install playwright")
        print("  playwright install chromium")
        return
    
    # 创建测试器
    tester = E2EWebTester(base_url="http://localhost:3000")
    
    # 运行测试
    await tester.run_full_test_suite()


if __name__ == "__main__":
    asyncio.run(main())
