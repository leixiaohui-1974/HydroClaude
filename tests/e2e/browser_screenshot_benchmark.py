"""
HydroClaude UI 浏览器截图对标测试

使用 Playwright 进行真实浏览器测试
对每个页面进行截图，基于实际UI进行评估

Author: HydroClaude Test Team
Date: 2025-11-25
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

# 截图目录
SCREENSHOT_DIR = Path(__file__).parent.parent.parent / "e2e_screenshots" / "ui_benchmark"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

# 报告目录
REPORT_DIR = Path(__file__).parent.parent.parent / "reports" / "browser_benchmark"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

# URL配置
FRONTEND_URL = "http://localhost:5173"


class UIScreenshotBenchmark:
    """基于浏览器截图的UI对标评估"""

    def __init__(self):
        self.results = {
            "test_date": datetime.now().isoformat(),
            "frontend_url": FRONTEND_URL,
            "screenshots": [],
            "pages_tested": [],
            "features_found": {},
            "issues_found": [],
            "scores": {}
        }
        self.browser = None
        self.context = None
        self.page = None

    async def setup(self):
        """初始化浏览器"""
        try:
            from playwright.async_api import async_playwright

            self.playwright = await async_playwright().start()
            # 尝试使用 Chromium，如果失败则使用 Firefox
            try:
                self.browser = await self.playwright.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
                )
            except Exception as e:
                print(f"Chromium 启动失败，尝试 Firefox: {e}")
                self.browser = await self.playwright.firefox.launch(headless=True)

            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080}
            )
            self.page = await self.context.new_page()
            print("✅ 浏览器初始化成功")
            return True
        except Exception as e:
            print(f"❌ 浏览器初始化失败: {e}")
            return False

    async def teardown(self):
        """关闭浏览器"""
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()

    async def take_screenshot(self, name: str, description: str) -> str:
        """截取当前页面截图"""
        filename = f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        filepath = SCREENSHOT_DIR / filename

        await self.page.screenshot(path=str(filepath), full_page=True)

        self.results["screenshots"].append({
            "name": name,
            "description": description,
            "file": str(filepath),
            "timestamp": datetime.now().isoformat()
        })

        print(f"  📸 截图已保存: {filename}")
        return str(filepath)

    async def check_element_exists(self, selector: str, description: str) -> bool:
        """检查元素是否存在"""
        try:
            element = await self.page.wait_for_selector(selector, timeout=5000)
            exists = element is not None
            return exists
        except Exception:
            return False

    async def test_homepage(self) -> Dict:
        """测试首页"""
        print("\n" + "="*60)
        print("测试: 首页 (Home Page)")
        print("="*60)

        results = {
            "page": "homepage",
            "url": FRONTEND_URL,
            "features": {},
            "score": 0,
            "max_score": 0
        }

        try:
            await self.page.goto(FRONTEND_URL, timeout=30000)
            await self.page.wait_for_load_state('networkidle', timeout=10000)

            # 截图
            await self.take_screenshot("homepage", "首页完整截图")

            # 检查关键元素
            checks = [
                ("header", "header, [data-testid='header'], .header, nav", "页面头部"),
                ("sidebar", "[data-testid='sidebar'], .sidebar, aside, nav", "侧边栏导航"),
                ("main_content", "main, [role='main'], .main-content, #root > div", "主要内容区"),
                ("title", "h1, .title, [data-testid='title']", "页面标题"),
                ("navigation", "nav, .nav, [role='navigation']", "导航菜单"),
                ("buttons", "button, .btn, [role='button']", "操作按钮"),
                ("cards", ".card, [data-testid='card'], article", "信息卡片"),
                ("footer", "footer, .footer", "页面底部")
            ]

            for check_id, selector, description in checks:
                exists = await self.check_element_exists(selector, description)
                results["features"][check_id] = exists
                results["max_score"] += 1
                if exists:
                    results["score"] += 1
                    print(f"  ✅ {description}: 存在")
                else:
                    print(f"  ❌ {description}: 缺失")

            # 获取页面内容分析
            content = await self.page.content()

            # 检查React是否正确渲染
            root_div = await self.page.query_selector('#root')
            if root_div:
                inner_html = await root_div.inner_html()
                if len(inner_html) > 100:
                    results["features"]["react_rendered"] = True
                    results["score"] += 1
                    print(f"  ✅ React 组件渲染: 成功")
                else:
                    results["features"]["react_rendered"] = False
                    print(f"  ⚠️ React 组件渲染: 内容较少")
            results["max_score"] += 1

        except Exception as e:
            print(f"  ❌ 测试失败: {e}")
            results["error"] = str(e)

        self.results["pages_tested"].append(results)
        return results

    async def test_simulation_page(self) -> Dict:
        """测试仿真页面"""
        print("\n" + "="*60)
        print("测试: 仿真页面 (Simulation Page)")
        print("="*60)

        results = {
            "page": "simulation",
            "url": f"{FRONTEND_URL}/simulation",
            "features": {},
            "score": 0,
            "max_score": 0
        }

        try:
            await self.page.goto(f"{FRONTEND_URL}/simulation", timeout=30000)
            await self.page.wait_for_load_state('networkidle', timeout=10000)

            # 截图
            await self.take_screenshot("simulation_page", "仿真页面完整截图")

            # 检查仿真页面关键元素
            checks = [
                ("config_form", "form, .form, [data-testid='config-form']", "配置表单"),
                ("input_fields", "input, textarea, select", "输入字段"),
                ("run_button", "button[type='submit'], .run-button, [data-testid='run']", "运行按钮"),
                ("results_area", ".results, [data-testid='results'], .output", "结果显示区"),
                ("charts", "canvas, svg, .chart, .recharts", "图表组件"),
                ("parameters", ".parameters, .params, [data-testid='parameters']", "参数面板"),
            ]

            for check_id, selector, description in checks:
                exists = await self.check_element_exists(selector, description)
                results["features"][check_id] = exists
                results["max_score"] += 1
                if exists:
                    results["score"] += 1
                    print(f"  ✅ {description}: 存在")
                else:
                    print(f"  ❌ {description}: 缺失")

        except Exception as e:
            print(f"  ❌ 测试失败: {e}")
            results["error"] = str(e)

        self.results["pages_tested"].append(results)
        return results

    async def test_results_page(self) -> Dict:
        """测试结果页面"""
        print("\n" + "="*60)
        print("测试: 结果页面 (Results Page)")
        print("="*60)

        results = {
            "page": "results",
            "url": f"{FRONTEND_URL}/results",
            "features": {},
            "score": 0,
            "max_score": 0
        }

        try:
            await self.page.goto(f"{FRONTEND_URL}/results", timeout=30000)
            await self.page.wait_for_load_state('networkidle', timeout=10000)

            # 截图
            await self.take_screenshot("results_page", "结果页面完整截图")

            # 检查结果页面关键元素
            checks = [
                ("data_table", "table, .table, [role='table']", "数据表格"),
                ("charts", "canvas, svg, .chart, .recharts", "图表展示"),
                ("export_button", "[data-testid='export'], .export, button:has-text('Export')", "导出按钮"),
                ("filters", ".filter, [data-testid='filter'], select", "筛选控件"),
                ("pagination", ".pagination, [aria-label='pagination']", "分页控件"),
            ]

            for check_id, selector, description in checks:
                exists = await self.check_element_exists(selector, description)
                results["features"][check_id] = exists
                results["max_score"] += 1
                if exists:
                    results["score"] += 1
                    print(f"  ✅ {description}: 存在")
                else:
                    print(f"  ❌ {description}: 缺失")

        except Exception as e:
            print(f"  ❌ 测试失败: {e}")
            results["error"] = str(e)

        self.results["pages_tested"].append(results)
        return results

    async def test_about_page(self) -> Dict:
        """测试关于页面"""
        print("\n" + "="*60)
        print("测试: 关于页面 (About Page)")
        print("="*60)

        results = {
            "page": "about",
            "url": f"{FRONTEND_URL}/about",
            "features": {},
            "score": 0,
            "max_score": 0
        }

        try:
            await self.page.goto(f"{FRONTEND_URL}/about", timeout=30000)
            await self.page.wait_for_load_state('networkidle', timeout=10000)

            # 截图
            await self.take_screenshot("about_page", "关于页面完整截图")

            # 检查关于页面关键元素
            checks = [
                ("title", "h1, h2, .title", "页面标题"),
                ("description", "p, .description, article", "项目描述"),
                ("version_info", ".version, [data-testid='version']", "版本信息"),
                ("features_list", "ul, ol, .features", "功能列表"),
            ]

            for check_id, selector, description in checks:
                exists = await self.check_element_exists(selector, description)
                results["features"][check_id] = exists
                results["max_score"] += 1
                if exists:
                    results["score"] += 1
                    print(f"  ✅ {description}: 存在")
                else:
                    print(f"  ❌ {description}: 缺失")

        except Exception as e:
            print(f"  ❌ 测试失败: {e}")
            results["error"] = str(e)

        self.results["pages_tested"].append(results)
        return results

    async def test_responsive_design(self) -> Dict:
        """测试响应式设计"""
        print("\n" + "="*60)
        print("测试: 响应式设计 (Responsive Design)")
        print("="*60)

        results = {
            "page": "responsive",
            "viewports": [],
            "score": 0,
            "max_score": 0
        }

        viewports = [
            {"name": "desktop", "width": 1920, "height": 1080},
            {"name": "tablet", "width": 768, "height": 1024},
            {"name": "mobile", "width": 375, "height": 667}
        ]

        try:
            for vp in viewports:
                await self.page.set_viewport_size({"width": vp["width"], "height": vp["height"]})
                await self.page.goto(FRONTEND_URL, timeout=30000)
                await self.page.wait_for_load_state('networkidle', timeout=10000)

                # 截图
                await self.take_screenshot(f"responsive_{vp['name']}", f"{vp['name']} 视图 ({vp['width']}x{vp['height']})")

                # 检查内容是否正常显示
                content_visible = await self.check_element_exists("#root > *", "主要内容")

                results["viewports"].append({
                    "name": vp["name"],
                    "width": vp["width"],
                    "height": vp["height"],
                    "content_visible": content_visible
                })

                results["max_score"] += 1
                if content_visible:
                    results["score"] += 1
                    print(f"  ✅ {vp['name']} ({vp['width']}x{vp['height']}): 正常显示")
                else:
                    print(f"  ❌ {vp['name']} ({vp['width']}x{vp['height']}): 显示异常")

            # 恢复默认视口
            await self.page.set_viewport_size({"width": 1920, "height": 1080})

        except Exception as e:
            print(f"  ❌ 测试失败: {e}")
            results["error"] = str(e)

        self.results["pages_tested"].append(results)
        return results

    async def test_navigation_flow(self) -> Dict:
        """测试导航流程"""
        print("\n" + "="*60)
        print("测试: 导航流程 (Navigation Flow)")
        print("="*60)

        results = {
            "page": "navigation",
            "links_tested": [],
            "score": 0,
            "max_score": 0
        }

        try:
            await self.page.goto(FRONTEND_URL, timeout=30000)
            await self.page.wait_for_load_state('networkidle', timeout=10000)

            # 查找所有导航链接
            nav_links = await self.page.query_selector_all('a[href], nav a, .nav a, [role="link"]')
            print(f"  发现 {len(nav_links)} 个导航链接")

            # 截图导航菜单
            await self.take_screenshot("navigation_menu", "导航菜单截图")

            # 测试前几个链接
            tested_count = 0
            for link in nav_links[:5]:
                try:
                    href = await link.get_attribute('href')
                    text = await link.inner_text()

                    if href and not href.startswith('#') and not href.startswith('http'):
                        results["max_score"] += 1

                        # 点击链接
                        await link.click()
                        await self.page.wait_for_load_state('networkidle', timeout=5000)

                        current_url = self.page.url
                        results["links_tested"].append({
                            "text": text.strip(),
                            "href": href,
                            "navigated_to": current_url,
                            "success": True
                        })
                        results["score"] += 1
                        print(f"  ✅ 导航到 '{text.strip()}' ({href}): 成功")

                        tested_count += 1
                        if tested_count >= 3:
                            break

                        # 返回首页
                        await self.page.goto(FRONTEND_URL, timeout=30000)
                        await self.page.wait_for_load_state('networkidle', timeout=10000)
                        nav_links = await self.page.query_selector_all('a[href], nav a, .nav a')

                except Exception as e:
                    print(f"  ⚠️ 导航测试异常: {e}")

        except Exception as e:
            print(f"  ❌ 测试失败: {e}")
            results["error"] = str(e)

        self.results["pages_tested"].append(results)
        return results

    def calculate_overall_score(self) -> float:
        """计算总体评分"""
        total_score = 0
        total_max = 0

        for page_result in self.results["pages_tested"]:
            total_score += page_result.get("score", 0)
            total_max += page_result.get("max_score", 0)

        if total_max == 0:
            return 0

        percentage = (total_score / total_max) * 100
        self.results["scores"] = {
            "total_score": total_score,
            "max_score": total_max,
            "percentage": percentage
        }

        return percentage

    def generate_report(self):
        """生成测试报告"""
        # JSON报告
        json_file = REPORT_DIR / f"browser_benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        print(f"\n📄 JSON报告: {json_file}")

        # HTML报告
        html_file = REPORT_DIR / f"browser_benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        html_content = self._generate_html_report()
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"📄 HTML报告: {html_file}")

        return json_file, html_file

    def _generate_html_report(self) -> str:
        """生成HTML报告"""
        screenshots_html = ""
        for ss in self.results["screenshots"]:
            screenshots_html += f"""
            <div class="screenshot-card">
                <h4>{ss['name']}</h4>
                <p>{ss['description']}</p>
                <img src="{ss['file']}" alt="{ss['name']}" style="max-width: 100%; border: 1px solid #ddd; border-radius: 4px;">
            </div>
            """

        pages_html = ""
        for page in self.results["pages_tested"]:
            features_html = ""
            for feat, exists in page.get("features", {}).items():
                status = "✅" if exists else "❌"
                features_html += f"<li>{status} {feat}</li>"

            score_pct = (page.get("score", 0) / page.get("max_score", 1)) * 100 if page.get("max_score", 0) > 0 else 0
            pages_html += f"""
            <div class="page-card">
                <h4>{page['page']}</h4>
                <p>评分: {page.get('score', 0)}/{page.get('max_score', 0)} ({score_pct:.1f}%)</p>
                <ul>{features_html}</ul>
            </div>
            """

        overall = self.results.get("scores", {})

        return f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>HydroClaude 浏览器UI对标测试报告</title>
    <style>
        body {{ font-family: system-ui, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; background: #f5f5f5; }}
        .header {{ background: linear-gradient(135deg, #2196f3 0%, #1976d2 100%); color: white; padding: 30px; border-radius: 10px; margin-bottom: 20px; }}
        .card {{ background: white; border-radius: 10px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .screenshot-card {{ display: inline-block; margin: 10px; padding: 15px; background: #fafafa; border-radius: 8px; max-width: 400px; vertical-align: top; }}
        .page-card {{ margin: 10px 0; padding: 15px; background: #f9f9f9; border-radius: 8px; }}
        .score-bar {{ background: #e0e0e0; border-radius: 10px; height: 20px; overflow: hidden; }}
        .score-fill {{ height: 100%; background: #4caf50; border-radius: 10px; }}
        ul {{ list-style: none; padding-left: 0; }}
        li {{ padding: 5px 0; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>HydroClaude 浏览器UI对标测试报告</h1>
        <p>测试日期: {self.results['test_date']}</p>
        <p>综合评分: <strong>{overall.get('percentage', 0):.1f}%</strong> ({overall.get('total_score', 0)}/{overall.get('max_score', 0)})</p>
    </div>

    <div class="card">
        <h2>综合评分</h2>
        <div class="score-bar">
            <div class="score-fill" style="width: {overall.get('percentage', 0)}%"></div>
        </div>
        <p>{overall.get('percentage', 0):.1f}%</p>
    </div>

    <div class="card">
        <h2>页面测试结果</h2>
        {pages_html}
    </div>

    <div class="card">
        <h2>截图 ({len(self.results['screenshots'])} 张)</h2>
        {screenshots_html}
    </div>
</body>
</html>
"""

    async def run_all_tests(self):
        """运行所有测试"""
        print("\n" + "="*70)
        print("HydroClaude 浏览器UI对标测试")
        print("="*70)
        print(f"前端地址: {FRONTEND_URL}")
        print(f"截图目录: {SCREENSHOT_DIR}")

        if not await self.setup():
            print("\n❌ 无法启动浏览器，测试终止")
            return None

        try:
            # 运行各项测试
            await self.test_homepage()
            await self.test_simulation_page()
            await self.test_results_page()
            await self.test_about_page()
            await self.test_responsive_design()
            await self.test_navigation_flow()

            # 计算总分
            overall_score = self.calculate_overall_score()

            # 生成报告
            json_file, html_file = self.generate_report()

            # 打印总结
            print("\n" + "="*70)
            print("测试总结")
            print("="*70)
            print(f"  页面测试数: {len(self.results['pages_tested'])}")
            print(f"  截图数量: {len(self.results['screenshots'])}")
            print(f"  综合评分: {overall_score:.1f}%")

            scores = self.results.get("scores", {})
            print(f"  得分: {scores.get('total_score', 0)}/{scores.get('max_score', 0)}")

            # 商业软件对比
            print("\n商业软件对标:")
            thresholds = {
                "HEC-RAS": 50,
                "MIKE 11": 55,
                "EPANET": 45,
                "HAMMER": 45
            }

            for software, threshold in thresholds.items():
                status = "✅ 达标" if overall_score >= threshold else "❌ 未达标"
                print(f"  vs {software}: {status} (阈值: {threshold}%, 实际: {overall_score:.1f}%)")

            return self.results

        finally:
            await self.teardown()


async def main():
    """主函数"""
    benchmark = UIScreenshotBenchmark()
    results = await benchmark.run_all_tests()
    return results


if __name__ == "__main__":
    asyncio.run(main())
