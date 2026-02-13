"""
使用Selenium进行真实浏览器截图测试
"""

import os
import warnings
warnings.filterwarnings("ignore")
import time
from datetime import datetime
from pathlib import Path

try:
    from selenium import webdriver
    from selenium.webdriver.firefox.options import Options as FirefoxOptions
    from selenium.webdriver.firefox.service import Service as FirefoxService
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.firefox import GeckoDriverManager
except ImportError:
    import pytest
    pytest.skip("selenium not installed", allow_module_level=True)

# 截图目录
SCREENSHOT_DIR = Path(__file__).parent.parent.parent / "e2e_screenshots" / "selenium"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

FRONTEND_URL = "http://localhost:5173"


def run_selenium_tests():
    """运行Selenium截图测试"""
    print("\n" + "="*70)
    print("Selenium 浏览器截图测试")
    print("="*70)
    print(f"前端地址: {FRONTEND_URL}")
    print(f"截图目录: {SCREENSHOT_DIR}")

    # 配置Firefox无头模式
    firefox_options = FirefoxOptions()
    firefox_options.add_argument("--headless")
    firefox_options.add_argument("--width=1920")
    firefox_options.add_argument("--height=1080")
    firefox_options.add_argument("--no-sandbox")
    firefox_options.add_argument("--disable-dev-shm-usage")

    driver = None
    results = {
        "screenshots": [],
        "errors": [],
        "pages_tested": 0
    }

    try:
        print("\n启动Firefox浏览器...")
        service = FirefoxService(GeckoDriverManager().install())
        driver = webdriver.Firefox(service=service, options=firefox_options)
        driver.set_window_size(1920, 1080)
        print("✅ 浏览器启动成功")

        # 测试页面列表
        pages = [
            ("homepage", "/", "首页"),
            ("simulation", "/simulation", "仿真页面"),
            ("results", "/results", "结果页面"),
            ("about", "/about", "关于页面"),
            ("visualization", "/visualization", "可视化演示"),
        ]

        for page_id, path, description in pages:
            print(f"\n测试: {description} ({path})")
            try:
                url = f"{FRONTEND_URL}{path}"
                driver.get(url)

                # 等待页面加载
                time.sleep(3)

                # 等待React渲染
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.ID, "root"))
                    )
                except:
                    pass

                # 截图
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                screenshot_path = SCREENSHOT_DIR / f"{page_id}_{timestamp}.png"
                driver.save_screenshot(str(screenshot_path))

                # 获取页面信息
                title = driver.title
                page_source_len = len(driver.page_source)

                results["screenshots"].append({
                    "page": page_id,
                    "path": path,
                    "description": description,
                    "screenshot": str(screenshot_path),
                    "title": title,
                    "source_length": page_source_len
                })

                results["pages_tested"] += 1
                print(f"  ✅ 截图已保存: {screenshot_path.name}")
                print(f"     标题: {title}")
                print(f"     页面大小: {page_source_len} bytes")

                # 检查页面是否有实际内容
                root_element = driver.find_element(By.ID, "root")
                root_html = root_element.get_attribute("innerHTML")
                if len(root_html) > 100:
                    print(f"     React渲染: ✅ ({len(root_html)} bytes)")
                else:
                    print(f"     React渲染: ⚠️ 内容较少")

            except Exception as e:
                print(f"  ❌ 测试失败: {e}")
                results["errors"].append({
                    "page": page_id,
                    "error": str(e)
                })

    except Exception as e:
        print(f"\n❌ 浏览器启动失败: {e}")
        results["errors"].append({"error": str(e)})

    finally:
        if driver:
            driver.quit()
            print("\n浏览器已关闭")

    # 打印总结
    print("\n" + "="*70)
    print("测试总结")
    print("="*70)
    print(f"  测试页面数: {results['pages_tested']}")
    print(f"  成功截图数: {len(results['screenshots'])}")
    print(f"  错误数: {len(results['errors'])}")

    if results['screenshots']:
        print(f"\n截图文件:")
        for ss in results['screenshots']:
            print(f"  - {ss['screenshot']}")

    return results


if __name__ == "__main__":
    run_selenium_tests()
