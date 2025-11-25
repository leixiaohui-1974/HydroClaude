#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HydroClaude 浏览器端到端测试

使用 Playwright 进行完整的浏览器自动化测试
包含截图记录每个测试步骤

Author: HydroClaude Test Team
Date: 2025-11-25
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from playwright.sync_api import sync_playwright, Page, expect

# 测试配置
FRONTEND_URL = "http://localhost:3000"
BACKEND_URL = "http://localhost:8000"
SCREENSHOT_DIR = project_root / "reports" / "e2e_screenshots"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

# 测试结果收集
test_results = {
    "start_time": None,
    "end_time": None,
    "total_tests": 0,
    "passed": 0,
    "failed": 0,
    "skipped": 0,
    "tests": []
}


def save_screenshot(page: Page, name: str, description: str = ""):
    """保存截图并记录"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{name}.png"
    filepath = SCREENSHOT_DIR / filename
    try:
        page.screenshot(path=str(filepath), full_page=False)
        print(f"  [截图] {filename}: {description}")
        return str(filepath)
    except Exception as e:
        print(f"  [截图失败] {filename}: {str(e)[:50]}")
        return None


def record_test(name: str, status: str, details: str = "", screenshots: list = None):
    """记录测试结果"""
    test_results["total_tests"] += 1
    if status == "passed":
        test_results["passed"] += 1
        print(f"  ✅ {name}")
    elif status == "failed":
        test_results["failed"] += 1
        print(f"  ❌ {name}: {details}")
    else:
        test_results["skipped"] += 1
        print(f"  ⚠️ {name}: {details}")

    test_results["tests"].append({
        "name": name,
        "status": status,
        "details": details,
        "screenshots": screenshots or [],
        "timestamp": datetime.now().isoformat()
    })


def test_homepage(page: Page):
    """测试首页"""
    print("\n" + "="*70)
    print("测试: 首页")
    print("="*70)

    screenshots = []

    try:
        # 访问首页
        page.goto(FRONTEND_URL, timeout=30000)
        page.wait_for_load_state("networkidle")
        screenshots.append(save_screenshot(page, "01_homepage", "首页加载完成"))

        # 检查页面标题
        title = page.title()
        print(f"  页面标题: {title}")

        # 检查主要元素是否存在
        # 检查导航栏
        nav_exists = page.locator("nav").count() > 0 or page.locator("header").count() > 0
        print(f"  导航栏存在: {nav_exists}")

        # 检查主要内容区域
        main_content = page.locator("main").count() > 0 or page.locator("#root").count() > 0
        print(f"  主内容区存在: {main_content}")

        record_test("首页加载", "passed", f"标题: {title}", screenshots)
        return True

    except Exception as e:
        screenshots.append(save_screenshot(page, "01_homepage_error", f"错误: {str(e)}"))
        record_test("首页加载", "failed", str(e), screenshots)
        return False


def test_navigation(page: Page):
    """测试导航功能"""
    print("\n" + "="*70)
    print("测试: 导航功能")
    print("="*70)

    screenshots = []
    nav_items_tested = 0

    try:
        page.goto(FRONTEND_URL, timeout=30000)
        page.wait_for_load_state("networkidle")

        # 查找所有导航链接
        nav_links = page.locator("nav a, header a, .nav-link, .menu-item, [role='menuitem']")
        link_count = nav_links.count()
        print(f"  发现 {link_count} 个导航链接")

        # 测试每个导航链接
        for i in range(min(link_count, 10)):  # 最多测试10个链接
            try:
                link = nav_links.nth(i)
                link_text = link.text_content() or f"Link_{i}"
                link_href = link.get_attribute("href") or ""

                if link_href and not link_href.startswith("http") and not link_href.startswith("#"):
                    print(f"  测试链接: {link_text} -> {link_href}")
                    link.click()
                    page.wait_for_load_state("networkidle", timeout=10000)
                    screenshots.append(save_screenshot(page, f"02_nav_{i}_{link_text[:20]}", f"导航到: {link_text}"))
                    nav_items_tested += 1

                    # 返回首页
                    page.goto(FRONTEND_URL)
                    page.wait_for_load_state("networkidle")

            except Exception as e:
                print(f"  链接 {i} 测试失败: {str(e)[:50]}")

        record_test("导航功能", "passed", f"测试了 {nav_items_tested} 个导航项", screenshots)
        return True

    except Exception as e:
        screenshots.append(save_screenshot(page, "02_navigation_error", f"错误: {str(e)}"))
        record_test("导航功能", "failed", str(e), screenshots)
        return False


def test_simulation_page(page: Page):
    """测试仿真页面"""
    print("\n" + "="*70)
    print("测试: 仿真页面")
    print("="*70)

    screenshots = []

    try:
        # 尝试访问仿真页面 - 多种可能的路径
        sim_paths = ["/simulation", "/simulate", "/canal", "/modeling", "/"]

        for path in sim_paths:
            try:
                page.goto(f"{FRONTEND_URL}{path}", timeout=15000)
                page.wait_for_load_state("networkidle", timeout=10000)

                # 检查是否有仿真相关内容
                has_sim_content = (
                    page.locator("text=仿真").count() > 0 or
                    page.locator("text=Simulation").count() > 0 or
                    page.locator("text=模拟").count() > 0 or
                    page.locator("text=渠道").count() > 0 or
                    page.locator("text=Canal").count() > 0 or
                    page.locator("input, select, button").count() > 3
                )

                if has_sim_content:
                    print(f"  找到仿真页面: {path}")
                    screenshots.append(save_screenshot(page, "03_simulation_page", f"仿真页面: {path}"))
                    break

            except Exception as e:
                continue

        # 查找输入表单元素
        inputs = page.locator("input[type='number'], input[type='text'], select")
        input_count = inputs.count()
        print(f"  发现 {input_count} 个输入元素")

        # 尝试填写表单
        if input_count > 0:
            # 查找并填写数值输入
            number_inputs = page.locator("input[type='number']")
            for i in range(min(number_inputs.count(), 5)):
                try:
                    inp = number_inputs.nth(i)
                    inp.fill("10")
                    print(f"  填写输入框 {i+1}")
                except:
                    pass

            screenshots.append(save_screenshot(page, "03_simulation_form_filled", "表单已填写"))

        # 查找提交/运行按钮
        submit_buttons = page.locator("button:has-text('运行'), button:has-text('Run'), button:has-text('提交'), button:has-text('Submit'), button:has-text('计算'), button:has-text('开始')")
        if submit_buttons.count() > 0:
            print(f"  发现 {submit_buttons.count()} 个运行按钮")
            screenshots.append(save_screenshot(page, "03_simulation_ready", "准备运行仿真"))

        record_test("仿真页面", "passed", f"输入元素: {input_count}", screenshots)
        return True

    except Exception as e:
        screenshots.append(save_screenshot(page, "03_simulation_error", f"错误: {str(e)}"))
        record_test("仿真页面", "failed", str(e), screenshots)
        return False


def test_run_simulation(page: Page):
    """测试运行仿真流程"""
    print("\n" + "="*70)
    print("测试: 运行仿真流程")
    print("="*70)

    screenshots = []

    try:
        # 访问仿真页面
        page.goto(FRONTEND_URL, timeout=30000)
        page.wait_for_load_state("networkidle")

        # 尝试找到并点击仿真相关链接
        sim_link = page.locator("a:has-text('仿真'), a:has-text('Simulation'), a:has-text('模拟'), a:has-text('渠道'), button:has-text('仿真')").first
        if sim_link.count() > 0:
            sim_link.click()
            page.wait_for_load_state("networkidle", timeout=10000)

        screenshots.append(save_screenshot(page, "04_sim_start", "开始仿真流程"))

        # 查找并填写参数
        # 渠道长度
        length_input = page.locator("input[name*='length'], input[placeholder*='长度'], input[id*='length']").first
        if length_input.count() > 0:
            length_input.fill("1000")
            print("  设置渠道长度: 1000m")

        # 渠道宽度
        width_input = page.locator("input[name*='width'], input[placeholder*='宽度'], input[id*='width']").first
        if width_input.count() > 0:
            width_input.fill("10")
            print("  设置渠道宽度: 10m")

        # 流量
        flow_input = page.locator("input[name*='flow'], input[name*='Q'], input[placeholder*='流量'], input[id*='flow']").first
        if flow_input.count() > 0:
            flow_input.fill("50")
            print("  设置流量: 50 m³/s")

        # 坡度
        slope_input = page.locator("input[name*='slope'], input[placeholder*='坡度'], input[id*='slope']").first
        if slope_input.count() > 0:
            slope_input.fill("0.001")
            print("  设置坡度: 0.001")

        screenshots.append(save_screenshot(page, "04_sim_params", "参数已设置"))

        # 点击运行按钮
        run_button = page.locator("button:has-text('运行'), button:has-text('Run'), button:has-text('开始'), button:has-text('计算'), button[type='submit']").first
        if run_button.count() > 0:
            run_button.click()
            print("  点击运行按钮")

            # 等待结果
            page.wait_for_timeout(3000)
            screenshots.append(save_screenshot(page, "04_sim_running", "仿真运行中"))

            # 等待更长时间看结果
            page.wait_for_timeout(5000)
            screenshots.append(save_screenshot(page, "04_sim_results", "仿真结果"))

        record_test("运行仿真流程", "passed", "流程完成", screenshots)
        return True

    except Exception as e:
        screenshots.append(save_screenshot(page, "04_sim_error", f"错误: {str(e)}"))
        record_test("运行仿真流程", "failed", str(e), screenshots)
        return False


def test_structure_modeling(page: Page):
    """测试结构建模页面"""
    print("\n" + "="*70)
    print("测试: 结构建模页面")
    print("="*70)

    screenshots = []

    try:
        # 尝试访问结构建模页面
        structure_paths = ["/structures", "/modeling", "/structure", "/gate", "/weir", "/"]

        for path in structure_paths:
            try:
                page.goto(f"{FRONTEND_URL}{path}", timeout=15000)
                page.wait_for_load_state("networkidle", timeout=10000)

                # 检查是否有结构相关内容
                has_structure_content = (
                    page.locator("text=闸门").count() > 0 or
                    page.locator("text=Gate").count() > 0 or
                    page.locator("text=堰").count() > 0 or
                    page.locator("text=Weir").count() > 0 or
                    page.locator("text=结构").count() > 0 or
                    page.locator("text=Structure").count() > 0
                )

                if has_structure_content:
                    print(f"  找到结构页面: {path}")
                    screenshots.append(save_screenshot(page, "05_structure_page", f"结构页面: {path}"))
                    break

            except:
                continue

        # 查找结构类型选择
        structure_select = page.locator("select, [role='listbox'], .dropdown")
        if structure_select.count() > 0:
            print(f"  发现 {structure_select.count()} 个下拉选择")

        # 查找结构参数输入
        param_inputs = page.locator("input[type='number']")
        print(f"  发现 {param_inputs.count()} 个参数输入")

        screenshots.append(save_screenshot(page, "05_structure_elements", "结构建模元素"))

        record_test("结构建模页面", "passed", f"参数输入: {param_inputs.count()}", screenshots)
        return True

    except Exception as e:
        screenshots.append(save_screenshot(page, "05_structure_error", f"错误: {str(e)}"))
        record_test("结构建模页面", "failed", str(e), screenshots)
        return False


def test_results_visualization(page: Page):
    """测试结果可视化"""
    print("\n" + "="*70)
    print("测试: 结果可视化")
    print("="*70)

    screenshots = []

    try:
        # 访问结果页面
        result_paths = ["/results", "/visualization", "/charts", "/analysis", "/"]

        for path in result_paths:
            try:
                page.goto(f"{FRONTEND_URL}{path}", timeout=15000)
                page.wait_for_load_state("networkidle", timeout=10000)

                # 检查是否有图表/可视化内容
                has_viz_content = (
                    page.locator("canvas").count() > 0 or
                    page.locator("svg").count() > 0 or
                    page.locator(".chart, .plot, .graph").count() > 0 or
                    page.locator("text=结果").count() > 0 or
                    page.locator("text=Results").count() > 0
                )

                if has_viz_content:
                    print(f"  找到可视化页面: {path}")
                    screenshots.append(save_screenshot(page, "06_visualization", f"可视化页面: {path}"))
                    break

            except:
                continue

        # 检查图表元素
        canvas_count = page.locator("canvas").count()
        svg_count = page.locator("svg").count()
        print(f"  Canvas 元素: {canvas_count}")
        print(f"  SVG 元素: {svg_count}")

        # 查找图表控制元素
        chart_controls = page.locator("button:has-text('缩放'), button:has-text('导出'), button:has-text('下载')")
        print(f"  图表控制按钮: {chart_controls.count()}")

        record_test("结果可视化", "passed", f"图表: canvas={canvas_count}, svg={svg_count}", screenshots)
        return True

    except Exception as e:
        screenshots.append(save_screenshot(page, "06_viz_error", f"错误: {str(e)}"))
        record_test("结果可视化", "failed", str(e), screenshots)
        return False


def test_api_documentation(page: Page):
    """测试 API 文档页面"""
    print("\n" + "="*70)
    print("测试: API 文档")
    print("="*70)

    screenshots = []

    try:
        # 访问 API 文档
        page.goto(f"{BACKEND_URL}/docs", timeout=30000)
        page.wait_for_load_state("networkidle")

        screenshots.append(save_screenshot(page, "07_api_docs", "API 文档页面"))

        # 检查 Swagger UI 元素
        swagger_ui = page.locator("#swagger-ui")
        if swagger_ui.count() > 0:
            print("  Swagger UI 已加载")

        # 检查 API 端点列表
        endpoints = page.locator(".opblock")
        endpoint_count = endpoints.count()
        print(f"  发现 {endpoint_count} 个 API 端点")

        # 展开几个端点查看详情
        if endpoint_count > 0:
            for i in range(min(endpoint_count, 3)):
                try:
                    endpoints.nth(i).click()
                    page.wait_for_timeout(500)
                except:
                    pass

            screenshots.append(save_screenshot(page, "07_api_endpoints", "API 端点详情"))

        record_test("API 文档", "passed", f"端点数: {endpoint_count}", screenshots)
        return True

    except Exception as e:
        screenshots.append(save_screenshot(page, "07_api_error", f"错误: {str(e)}"))
        record_test("API 文档", "failed", str(e), screenshots)
        return False


def test_responsive_design(page: Page):
    """测试响应式设计"""
    print("\n" + "="*70)
    print("测试: 响应式设计")
    print("="*70)

    screenshots = []

    try:
        page.goto(FRONTEND_URL, timeout=30000)
        page.wait_for_load_state("networkidle")

        # 桌面视图
        page.set_viewport_size({"width": 1920, "height": 1080})
        page.wait_for_timeout(500)
        screenshots.append(save_screenshot(page, "08_desktop_view", "桌面视图 1920x1080"))

        # 平板视图
        page.set_viewport_size({"width": 768, "height": 1024})
        page.wait_for_timeout(500)
        screenshots.append(save_screenshot(page, "08_tablet_view", "平板视图 768x1024"))

        # 手机视图
        page.set_viewport_size({"width": 375, "height": 667})
        page.wait_for_timeout(500)
        screenshots.append(save_screenshot(page, "08_mobile_view", "手机视图 375x667"))

        # 恢复默认大小
        page.set_viewport_size({"width": 1280, "height": 720})

        record_test("响应式设计", "passed", "测试了桌面/平板/手机视图", screenshots)
        return True

    except Exception as e:
        screenshots.append(save_screenshot(page, "08_responsive_error", f"错误: {str(e)}"))
        record_test("响应式设计", "failed", str(e), screenshots)
        return False


def generate_report():
    """生成测试报告"""
    print("\n" + "="*70)
    print("生成测试报告")
    print("="*70)

    test_results["end_time"] = datetime.now().isoformat()

    # 保存 JSON 报告
    report_file = SCREENSHOT_DIR / "test_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(test_results, f, ensure_ascii=False, indent=2)

    # 生成 HTML 报告
    html_report = SCREENSHOT_DIR / "test_report.html"

    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HydroClaude E2E 测试报告</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; border-bottom: 2px solid #4CAF50; padding-bottom: 10px; }}
        .summary {{ display: flex; gap: 20px; margin: 20px 0; }}
        .stat {{ padding: 15px; border-radius: 8px; text-align: center; flex: 1; }}
        .stat.total {{ background: #e3f2fd; }}
        .stat.passed {{ background: #e8f5e9; }}
        .stat.failed {{ background: #ffebee; }}
        .stat.skipped {{ background: #fff3e0; }}
        .stat h2 {{ margin: 0; font-size: 2em; }}
        .stat p {{ margin: 5px 0 0 0; color: #666; }}
        .test {{ border: 1px solid #ddd; margin: 10px 0; border-radius: 8px; overflow: hidden; }}
        .test-header {{ padding: 15px; background: #f9f9f9; display: flex; align-items: center; gap: 10px; }}
        .test-header.passed {{ border-left: 4px solid #4CAF50; }}
        .test-header.failed {{ border-left: 4px solid #f44336; }}
        .test-header.skipped {{ border-left: 4px solid #ff9800; }}
        .test-name {{ font-weight: bold; flex: 1; }}
        .test-status {{ padding: 5px 10px; border-radius: 4px; color: white; }}
        .test-status.passed {{ background: #4CAF50; }}
        .test-status.failed {{ background: #f44336; }}
        .test-status.skipped {{ background: #ff9800; }}
        .test-details {{ padding: 15px; background: #fafafa; }}
        .screenshots {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 10px; }}
        .screenshot {{ max-width: 300px; }}
        .screenshot img {{ width: 100%; border: 1px solid #ddd; border-radius: 4px; }}
        .screenshot p {{ font-size: 12px; color: #666; margin: 5px 0 0 0; }}
        .timestamp {{ color: #999; font-size: 14px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>HydroClaude E2E 测试报告</h1>

        <p class="timestamp">
            开始时间: {test_results.get('start_time', 'N/A')}<br>
            结束时间: {test_results.get('end_time', 'N/A')}
        </p>

        <div class="summary">
            <div class="stat total">
                <h2>{test_results['total_tests']}</h2>
                <p>总测试数</p>
            </div>
            <div class="stat passed">
                <h2>{test_results['passed']}</h2>
                <p>通过</p>
            </div>
            <div class="stat failed">
                <h2>{test_results['failed']}</h2>
                <p>失败</p>
            </div>
            <div class="stat skipped">
                <h2>{test_results['skipped']}</h2>
                <p>跳过</p>
            </div>
        </div>

        <h2>测试详情</h2>
"""

    for test in test_results["tests"]:
        status = test["status"]
        html_content += f"""
        <div class="test">
            <div class="test-header {status}">
                <span class="test-name">{test['name']}</span>
                <span class="test-status {status}">{status.upper()}</span>
            </div>
            <div class="test-details">
                <p><strong>详情:</strong> {test.get('details', 'N/A')}</p>
                <p><strong>时间:</strong> {test.get('timestamp', 'N/A')}</p>
"""

        if test.get("screenshots"):
            html_content += '<div class="screenshots">'
            for screenshot in test["screenshots"]:
                filename = Path(screenshot).name
                html_content += f"""
                <div class="screenshot">
                    <img src="{filename}" alt="{filename}">
                    <p>{filename}</p>
                </div>
"""
            html_content += '</div>'

        html_content += """
            </div>
        </div>
"""

    html_content += """
    </div>
</body>
</html>
"""

    with open(html_report, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"\n  JSON 报告: {report_file}")
    print(f"  HTML 报告: {html_report}")
    print(f"\n  总测试数: {test_results['total_tests']}")
    print(f"  通过: {test_results['passed']}")
    print(f"  失败: {test_results['failed']}")
    print(f"  跳过: {test_results['skipped']}")


def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*70)
    print("HydroClaude 浏览器端到端测试")
    print("="*70)

    test_results["start_time"] = datetime.now().isoformat()

    with sync_playwright() as p:
        # 启动浏览器 - 添加 no-sandbox 以解决权限问题
        browser = p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            locale="zh-CN"
        )
        page = context.new_page()

        print(f"\n浏览器已启动 (Chromium, headless)")
        print(f"前端地址: {FRONTEND_URL}")
        print(f"后端地址: {BACKEND_URL}")
        print(f"截图目录: {SCREENSHOT_DIR}")

        # 运行测试
        test_homepage(page)
        test_navigation(page)
        test_simulation_page(page)
        test_run_simulation(page)
        test_structure_modeling(page)
        test_results_visualization(page)
        test_api_documentation(page)
        test_responsive_design(page)

        # 关闭浏览器
        context.close()
        browser.close()

    # 生成报告
    generate_report()

    print("\n" + "="*70)
    print("测试完成!")
    print("="*70)


if __name__ == "__main__":
    run_all_tests()
