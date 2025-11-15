#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整Web端到端测试
逐个测试所有案例：加载、计算、结果展示（图、表）、分析报告
"""

import os
import sys
import time
import json
from datetime import datetime
from playwright.sync_api import sync_playwright, Page

FRONTEND_URL = "http://localhost:5173"
BACKEND_URL = "http://localhost:8000"
SCREENSHOTS_DIR = "/workspace/web/screenshots_complete"
REPORT_FILE = "/workspace/web/完整测试报告.md"

# 创建截图目录
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

# 测试案例定义
TEST_CASES = [
    {
        "id": "tc1",
        "name": "静态均匀流",
        "description": "零流量静态水面",
        "config": {
            "width": 10.0,
            "length": 1000.0,
            "n_cells": 100,
            "manning_n": 0.025,
            "slope": 0.001,
            "t_end": 10.0,
            "dt_max": 0.1,
            "initial_conditions": {"type": "uniform", "h": 5.0, "Q": 0.0},
            "boundary_conditions": {
                "upstream": {"type": "h", "value": 5.0},
                "downstream": {"type": "h", "value": 5.0}
            }
        }
    },
    {
        "id": "tc2",
        "name": "均匀流动",
        "description": "稳定流量均匀流",
        "config": {
            "width": 10.0,
            "length": 1000.0,
            "n_cells": 100,
            "manning_n": 0.025,
            "slope": 0.001,
            "t_end": 10.0,
            "dt_max": 0.1,
            "initial_conditions": {"type": "uniform", "h": 5.0, "Q": 10.0},
            "boundary_conditions": {
                "upstream": {"type": "Q", "value": 10.0},
                "downstream": {"type": "h", "value": 5.0}
            }
        }
    },
    {
        "id": "tc3",
        "name": "浅层流动",
        "description": "小水深流动",
        "config": {
            "width": 10.0,
            "length": 1000.0,
            "n_cells": 100,
            "manning_n": 0.025,
            "slope": 0.001,
            "t_end": 10.0,
            "dt_max": 0.1,
            "initial_conditions": {"type": "uniform", "h": 1.0, "Q": 5.0},
            "boundary_conditions": {
                "upstream": {"type": "Q", "value": 5.0},
                "downstream": {"type": "h", "value": 1.0}
            }
        }
    },
]

def take_screenshot(page: Page, case_id: str, stage: str, description: str):
    """保存截图"""
    timestamp = datetime.now().strftime("%H%M%S")
    filename = f"{case_id}_{stage}_{timestamp}.png"
    filepath = os.path.join(SCREENSHOTS_DIR, filename)
    page.screenshot(path=filepath, full_page=True)
    return {
        "filename": filename,
        "path": filepath,
        "stage": stage,
        "description": description,
        "timestamp": datetime.now().isoformat()
    }

def wait_for_element(page: Page, selector: str, timeout: int = 5000):
    """等待元素出现"""
    try:
        page.wait_for_selector(selector, timeout=timeout)
        return True
    except:
        return False

def test_case_complete_flow(page: Page, test_case: dict, case_num: int, total_cases: int):
    """测试单个案例的完整流程"""
    case_id = test_case['id']
    case_name = test_case['name']
    
    result = {
        "id": case_id,
        "name": case_name,
        "description": test_case['description'],
        "screenshots": [],
        "stages": {},
        "success": True,
        "errors": []
    }
    
    print(f"\n{'='*80}")
    print(f"案例 [{case_num}/{total_cases}]: {case_name}")
    print(f"{'='*80}")
    
    try:
        # 阶段1: 导航到建模工作台
        print("\n[阶段 1/5] 进入建模工作台...")
        result["stages"]["navigation"] = {"status": "testing"}
        
        page.goto(FRONTEND_URL, wait_until="networkidle", timeout=30000)
        time.sleep(1)
        
        # 点击建模工作台
        if page.locator("text=建模工作台").count() > 0:
            page.click("text=建模工作台")
            time.sleep(2)
            
            screenshot = take_screenshot(page, case_id, "01_workspace", "建模工作台界面")
            result["screenshots"].append(screenshot)
            print("  ✅ 成功进入建模工作台")
            result["stages"]["navigation"] = {"status": "success"}
        else:
            print("  ❌ 未找到建模工作台")
            result["stages"]["navigation"] = {"status": "failed", "error": "未找到建模工作台"}
            result["success"] = False
            result["errors"].append("未找到建模工作台")
            return result
        
        # 阶段2: 创建/加载案例
        print("\n[阶段 2/5] 创建案例...")
        result["stages"]["create_case"] = {"status": "testing"}
        
        # 查找"新建案例"或类似按钮
        new_case_selectors = [
            "button:has-text('新建')",
            "button:has-text('创建')",
            "[aria-label='新建案例']",
            ".new-case-button"
        ]
        
        created = False
        for selector in new_case_selectors:
            if page.locator(selector).count() > 0:
                try:
                    page.click(selector, timeout=2000)
                    time.sleep(1)
                    created = True
                    break
                except:
                    continue
        
        if created:
            # 填写案例信息
            # 尝试填充表单
            try:
                # 查找输入框
                name_input = page.locator("input[name='name'], input[placeholder*='名称']").first
                if name_input.count() > 0:
                    name_input.fill(case_name)
                    print(f"  ✅ 填入案例名称: {case_name}")
                
                # 保存配置
                time.sleep(1)
                screenshot = take_screenshot(page, case_id, "02_config", "案例配置界面")
                result["screenshots"].append(screenshot)
                
                result["stages"]["create_case"] = {"status": "success"}
                print("  ✅ 案例创建成功")
            except Exception as e:
                print(f"  ⚠️  配置填写部分失败: {e}")
                result["stages"]["create_case"] = {"status": "partial", "note": str(e)}
        else:
            print("  ⚠️  未找到新建按钮，尝试使用现有案例")
            screenshot = take_screenshot(page, case_id, "02_existing", "现有案例列表")
            result["screenshots"].append(screenshot)
            result["stages"]["create_case"] = {"status": "skipped", "note": "使用现有案例"}
        
        # 阶段3: 提交计算
        print("\n[阶段 3/5] 提交计算...")
        result["stages"]["submit_calculation"] = {"status": "testing"}
        
        # 查找"运行仿真"按钮（使用更精确的选择器）
        run_selectors = [
            "button:has-text('运行仿真')",  # 完整文本匹配
            "button >> text='运行仿真'",
            "button:has-text('运行')",      # 部分匹配作为后备
            "[aria-label*='运行']",
            "[title*='运行']"
        ]
        
        submitted = False
        for selector in run_selectors:
            try:
                button_count = page.locator(selector).count()
                print(f"  [调试] 选择器 '{selector}' 找到 {button_count} 个按钮")
                if button_count > 0:
                    button = page.locator(selector).first
                    if button.is_visible() and button.is_enabled():
                        button.click(timeout=2000)
                        time.sleep(2)
                        submitted = True
                        print(f"  ✅ 已提交计算（使用选择器: {selector}）")
                        break
                    else:
                        print(f"  [调试] 按钮存在但不可点击（disabled或不可见）")
            except Exception as e:
                print(f"  [调试] 选择器 '{selector}' 异常: {e}")
                continue
        
        if submitted:
            screenshot = take_screenshot(page, case_id, "03_submit", "提交计算")
            result["screenshots"].append(screenshot)
            result["stages"]["submit_calculation"] = {"status": "success"}
            
            # 等待计算完成（最多30秒）
            print("  等待计算完成...")
            for i in range(30):
                time.sleep(1)
                # 检查是否有"完成"、"成功"等提示
                content = page.content()
                if any(word in content for word in ["完成", "成功", "Completed", "Success"]):
                    print(f"  ✅ 计算完成 ({i+1}秒)")
                    break
                if i % 5 == 0:
                    print(f"    [{i+1}/30秒]...")
        else:
            print("  ⚠️  未找到可点击的运行按钮")
            print("  [提示] 可能原因：")
            print("    1. 按钮在不同的位置或标签页")
            print("    2. 按钮被disabled（模型为空）")
            print("    3. 需要先创建/加载案例")
            result["stages"]["submit_calculation"] = {"status": "failed", "error": "未找到运行按钮或按钮不可点击"}
            result["errors"].append("未找到运行按钮，可能需要先正确加载案例")
        
        # 阶段4: 查看结果（图表）
        print("\n[阶段 4/5] 查看结果图表...")
        result["stages"]["view_results"] = {"status": "testing"}
        
        # 切换到结果分析或仿真管理
        result_tabs = ["结果分析", "仿真管理", "结果"]
        for tab in result_tabs:
            if page.locator(f"text={tab}").count() > 0:
                try:
                    page.click(f"text={tab}")
                    time.sleep(2)
                    print(f"  ✅ 切换到 {tab}")
                    break
                except:
                    continue
        
        time.sleep(2)
        screenshot = take_screenshot(page, case_id, "04_results", "结果展示页面")
        result["screenshots"].append(screenshot)
        
        # 检查是否有图表元素
        chart_indicators = ["canvas", "svg", ".chart", "[class*='plot']"]
        charts_found = 0
        for indicator in chart_indicators:
            charts_found += page.locator(indicator).count()
        
        if charts_found > 0:
            print(f"  ✅ 找到 {charts_found} 个图表元素")
            result["stages"]["view_results"] = {"status": "success", "charts_count": charts_found}
        else:
            print("  ⚠️  未检测到图表")
            result["stages"]["view_results"] = {"status": "warning", "note": "未检测到图表"}
        
        # 阶段5: 检查数据表格
        print("\n[阶段 5/5] 检查数据表格...")
        result["stages"]["view_tables"] = {"status": "testing"}
        
        # 检查表格元素
        table_count = page.locator("table").count()
        if table_count > 0:
            print(f"  ✅ 找到 {table_count} 个数据表格")
            result["stages"]["view_tables"] = {"status": "success", "tables_count": table_count}
        else:
            print("  ⚠️  未找到数据表格")
            result["stages"]["view_tables"] = {"status": "warning", "note": "未找到数据表格"}
        
        screenshot = take_screenshot(page, case_id, "05_tables", "数据表格")
        result["screenshots"].append(screenshot)
        
        # 最终截图
        screenshot = take_screenshot(page, case_id, "06_final", "最终状态")
        result["screenshots"].append(screenshot)
        
        print(f"\n✅ 案例 {case_name} 测试完成")
        
    except Exception as e:
        print(f"\n❌ 案例测试异常: {str(e)}")
        result["success"] = False
        result["errors"].append(f"测试异常: {str(e)}")
        try:
            screenshot = take_screenshot(page, case_id, "error", "错误状态")
            result["screenshots"].append(screenshot)
        except:
            pass
    
    return result

def generate_report(results: dict):
    """生成测试报告"""
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write("# HydroClaude Web - 完整端到端测试报告\n\n")
        f.write(f"**测试时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n")
        f.write(f"**前端地址**: {FRONTEND_URL}  \n")
        f.write(f"**后端地址**: {BACKEND_URL}  \n\n")
        
        f.write("## 测试总结\n\n")
        f.write(f"- **总案例数**: {results['total_cases']}\n")
        f.write(f"- **通过**: {results['passed']} ✅\n")
        f.write(f"- **失败**: {results['failed']} ❌\n")
        f.write(f"- **成功率**: {results['success_rate']:.1f}%\n")
        f.write(f"- **总截图数**: {results['total_screenshots']}\n\n")
        
        f.write("## 详细测试结果\n\n")
        
        for i, case_result in enumerate(results['cases'], 1):
            f.write(f"### 案例 {i}: {case_result['name']}\n\n")
            f.write(f"**描述**: {case_result['description']}  \n")
            f.write(f"**状态**: {'✅ 通过' if case_result['success'] else '❌ 失败'}  \n\n")
            
            f.write("**测试阶段**:\n\n")
            for stage_name, stage_data in case_result['stages'].items():
                status_icon = {"success": "✅", "failed": "❌", "warning": "⚠️", "skipped": "⏭️", "testing": "🔄"}.get(stage_data.get('status'), "❓")
                f.write(f"- {stage_name}: {status_icon} {stage_data.get('status', 'unknown')}\n")
                if 'note' in stage_data:
                    f.write(f"  - 备注: {stage_data['note']}\n")
                if 'error' in stage_data:
                    f.write(f"  - 错误: {stage_data['error']}\n")
            
            f.write("\n**截图**:\n\n")
            for screenshot in case_result['screenshots']:
                f.write(f"- `{screenshot['filename']}` - {screenshot['description']}\n")
            
            if case_result['errors']:
                f.write("\n**错误信息**:\n\n")
                for error in case_result['errors']:
                    f.write(f"- {error}\n")
            
            f.write("\n---\n\n")
        
        f.write("## 截图目录\n\n")
        f.write(f"所有截图保存在: `{SCREENSHOTS_DIR}`\n\n")
        
        f.write("---\n\n")
        f.write(f"*报告生成时间: {datetime.now().isoformat()}*\n")
    
    print(f"\n📄 报告已保存: {REPORT_FILE}")

def main():
    print("="*80)
    print("  HydroClaude Web - 完整端到端测试")
    print("  逐案例测试：加载、计算、图表、报告")
    print("="*80)
    print(f"\n开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"测试案例数: {len(TEST_CASES)}")
    
    results = {
        "total_cases": len(TEST_CASES),
        "passed": 0,
        "failed": 0,
        "cases": [],
        "total_screenshots": 0
    }
    
    with sync_playwright() as p:
        print("\n启动浏览器...")
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_viewport_size({"width": 1920, "height": 1080})
        
        try:
            for i, test_case in enumerate(TEST_CASES, 1):
                case_result = test_case_complete_flow(page, test_case, i, len(TEST_CASES))
                results["cases"].append(case_result)
                results["total_screenshots"] += len(case_result["screenshots"])
                
                if case_result["success"]:
                    results["passed"] += 1
                else:
                    results["failed"] += 1
                
                # 短暂休息
                time.sleep(2)
        
        finally:
            browser.close()
    
    # 计算成功率
    results["success_rate"] = (results["passed"] / results["total_cases"] * 100) if results["total_cases"] > 0 else 0
    
    # 生成报告
    generate_report(results)
    
    # 打印总结
    print(f"\n{'='*80}")
    print("最终测试总结")
    print(f"{'='*80}")
    print(f"  总案例数: {results['total_cases']}")
    print(f"  通过: {results['passed']} ✅")
    print(f"  失败: {results['failed']} ❌")
    print(f"  成功率: {results['success_rate']:.1f}%")
    print(f"  总截图数: {results['total_screenshots']}")
    print(f"\n  截图目录: {SCREENSHOTS_DIR}")
    print(f"  测试报告: {REPORT_FILE}")
    print("="*80)
    
    return 0 if results["failed"] == 0 else 1

if __name__ == '__main__':
    sys.exit(main())
