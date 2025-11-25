"""
稳定的浏览器截图测试 - 使用更保守的配置
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path

# 截图目录
SCREENSHOT_DIR = Path(__file__).parent.parent.parent / "e2e_screenshots" / "browser"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

REPORT_DIR = Path(__file__).parent.parent.parent / "reports" / "browser_benchmark"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

FRONTEND_URL = "http://localhost:5173"


async def run_browser_tests():
    """运行浏览器测试"""
    print("\n" + "="*70)
    print("浏览器截图测试 (稳定模式)")
    print("="*70)
    print(f"前端地址: {FRONTEND_URL}")
    print(f"截图目录: {SCREENSHOT_DIR}")

    results = {
        "test_date": datetime.now().isoformat(),
        "screenshots": [],
        "pages": [],
        "errors": [],
        "overall_score": 0
    }

    try:
        from playwright.async_api import async_playwright

        print("\n启动Playwright...")
        playwright = await async_playwright().start()

        # 使用headless shell模式，更稳定
        browser = await playwright.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--disable-software-rasterizer',
                '--single-process',  # 单进程模式，更稳定
                '--no-zygote',
            ]
        )

        print("✅ 浏览器启动成功")

        context = await browser.new_context(
            viewport={'width': 1280, 'height': 720},  # 较小的视口
            ignore_https_errors=True
        )

        page = await context.new_page()

        # 设置较长的超时
        page.set_default_timeout(30000)

        # 测试页面
        test_pages = [
            ("home", "/", "首页"),
            ("simulation", "/simulation", "仿真页面"),
            ("results", "/results", "结果页面"),
            ("about", "/about", "关于页面"),
        ]

        for page_id, path, description in test_pages:
            print(f"\n📄 测试: {description} ({path})")

            try:
                # 导航到页面
                url = f"{FRONTEND_URL}{path}"
                response = await page.goto(url, wait_until='domcontentloaded', timeout=20000)

                # 等待一下让React渲染
                await page.wait_for_timeout(2000)

                # 截图
                timestamp = datetime.now().strftime('%H%M%S')
                screenshot_path = SCREENSHOT_DIR / f"{page_id}_{timestamp}.png"

                await page.screenshot(path=str(screenshot_path))
                print(f"   📸 截图: {screenshot_path.name}")

                # 获取页面信息
                title = await page.title()
                print(f"   标题: {title}")

                # 检查React内容
                try:
                    root = await page.query_selector('#root')
                    if root:
                        html_len = len(await root.inner_html())
                        print(f"   React内容: {html_len} bytes")

                        # 检查关键元素
                        checks = {
                            "header": "header, nav, .header",
                            "main": "main, .main, [role='main']",
                            "buttons": "button",
                            "links": "a[href]",
                        }

                        found_elements = {}
                        for name, selector in checks.items():
                            elements = await page.query_selector_all(selector)
                            found_elements[name] = len(elements)

                        print(f"   元素统计: {found_elements}")

                        results["pages"].append({
                            "id": page_id,
                            "path": path,
                            "description": description,
                            "screenshot": str(screenshot_path),
                            "title": title,
                            "content_size": html_len,
                            "elements": found_elements,
                            "success": True
                        })
                    else:
                        print("   ⚠️ 未找到#root元素")
                        results["pages"].append({
                            "id": page_id,
                            "path": path,
                            "success": False,
                            "error": "No root element"
                        })
                except Exception as e:
                    print(f"   ⚠️ 内容检查失败: {e}")

                results["screenshots"].append(str(screenshot_path))

            except Exception as e:
                print(f"   ❌ 页面测试失败: {e}")
                results["errors"].append({
                    "page": page_id,
                    "error": str(e)
                })

        # 关闭浏览器
        await context.close()
        await browser.close()
        await playwright.stop()
        print("\n✅ 浏览器已关闭")

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        results["errors"].append({"error": str(e)})
        import traceback
        traceback.print_exc()

    # 计算得分
    successful_pages = [p for p in results["pages"] if p.get("success", False)]
    total_pages = len(test_pages)
    results["overall_score"] = (len(successful_pages) / total_pages * 100) if total_pages > 0 else 0

    # 打印总结
    print("\n" + "="*70)
    print("测试总结")
    print("="*70)
    print(f"  成功页面: {len(successful_pages)}/{total_pages}")
    print(f"  截图数量: {len(results['screenshots'])}")
    print(f"  错误数量: {len(results['errors'])}")
    print(f"  综合得分: {results['overall_score']:.1f}%")

    # 保存报告
    report_file = REPORT_DIR / f"browser_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n报告: {report_file}")

    # 显示截图列表
    if results["screenshots"]:
        print(f"\n截图文件:")
        for ss in results["screenshots"]:
            print(f"  📸 {ss}")

    return results


if __name__ == "__main__":
    asyncio.run(run_browser_tests())
