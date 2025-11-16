#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Web端到端自动化测试

使用Playwright进行浏览器自动化测试

Author: HydroClaude Team
Date: 2025-11-15
"""

import json
import time
import sys
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

import pytest
from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext


class WebE2ETester:
    """Web端到端测试器"""
    
    def __init__(self, headless: bool = False):
        self.headless = headless
        self.base_url = "http://localhost:5173"
        self.test_cases_dir = Path(__file__).parent / "test_cases"
        self.screenshots_dir = Path(__file__).parent / "screenshots"
        self.reports_dir = Path(__file__).parent / "reports"
        
        # 确保目录存在
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        
        self.results = []
    
    def setup_browser(self):
        """设置浏览器"""
        self.playwright = sync_playwright().start()
        
        # 使用Chromium，支持中文
        self.browser = self.playwright.chromium.launch(
            headless=self.headless,
            args=['--lang=zh-CN']
        )
        
        # 创建上下文，设置中文环境
        self.context = self.browser.new_context(
            locale='zh-CN',
            timezone_id='Asia/Shanghai',
            viewport={'width': 1920, 'height': 1080}
        )
        
        self.page = self.context.new_page()
    
    def teardown_browser(self):
        """关闭浏览器"""
        if hasattr(self, 'page'):
            self.page.close()
        if hasattr(self, 'context'):
            self.context.close()
        if hasattr(self, 'browser'):
            self.browser.close()
        if hasattr(self, 'playwright'):
            self.playwright.stop()
    
    def load_test_cases(self) -> List[Dict[str, Any]]:
        """加载测试案例"""
        index_file = self.test_cases_dir / "test_index.json"
        
        if not index_file.exists():
            print("⚠️  未找到测试案例索引，请先运行 convert_test_cases.py")
            return []
        
        with open(index_file, 'r', encoding='utf-8') as f:
            index = json.load(f)
        
        test_cases = []
        for case_info in index["cases"]:
            case_file = self.test_cases_dir / case_info["file"]
            if case_file.exists():
                with open(case_file, 'r', encoding='utf-8') as f:
                    case_data = json.load(f)
                    case_data["id"] = case_info["id"]
                    test_cases.append(case_data)
        
        return test_cases
    
    def navigate_to_app(self):
        """导航到应用"""
        print(f"  🌐 访问: {self.base_url}")
        self.page.goto(self.base_url, wait_until='networkidle')
        time.sleep(2)  # 等待应用加载
    
    def take_screenshot(self, name: str):
        """截图"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{name}_{timestamp}.png"
        filepath = self.screenshots_dir / filename
        self.page.screenshot(path=str(filepath), full_page=True)
        print(f"  📸 截图: {filename}")
        return filepath
    
    def fill_config_form(self, test_case: Dict[str, Any]):
        """填写配置表单"""
        print("  📝 填写配置表单...")
        
        # 点击配置标签
        try:
            config_tab = self.page.locator('text=配置')
            if config_tab.is_visible():
                config_tab.click()
                time.sleep(1)
        except Exception as e:
            print(f"    ⚠️  点击配置标签失败: {e}")
        
        # 等待表单加载
        time.sleep(1)
        
        # 填写参数（使用JSON编辑模式更可靠）
        try:
            # 切换到JSON模式
            json_mode_btn = self.page.locator('text=JSON编辑')
            if json_mode_btn.is_visible():
                json_mode_btn.click()
                time.sleep(1)
            
            # 找到JSON编辑器
            monaco_editor = self.page.locator('.monaco-editor')
            if monaco_editor.is_visible():
                # 清空并输入新配置
                config_json = json.dumps(test_case, ensure_ascii=False, indent=2)
                
                # 使用Monaco API设置内容
                self.page.evaluate(f"""
                    const editor = monaco.editor.getModels()[0];
                    if (editor) {{
                        editor.setValue({json.dumps(config_json)});
                    }}
                """)
                
                time.sleep(1)
                print("    ✅ 配置已填写")
            else:
                print("    ⚠️  未找到JSON编辑器")
        
        except Exception as e:
            print(f"    ⚠️  填写配置失败: {e}")
    
    def run_simulation(self):
        """运行仿真"""
        print("  🚀 运行仿真...")
        
        try:
            # 查找并点击"运行仿真"按钮
            run_button = self.page.locator('button:has-text("运行仿真")')
            if run_button.is_visible():
                run_button.click()
                print("    ✅ 已点击运行按钮")
            else:
                # 尝试其他可能的按钮文本
                run_button = self.page.locator('button:has-text("开始")')
                if run_button.is_visible():
                    run_button.click()
            
            # 等待计算完成（最多60秒）
            print("    ⏳ 等待计算完成...")
            time.sleep(5)  # 初始等待
            
            # 检查是否完成
            for i in range(55):
                # 查找成功提示或结果页面
                if self.page.locator('text=计算完成').is_visible() or \
                   self.page.locator('text=结果').is_visible():
                    print("    ✅ 计算完成")
                    return True
                time.sleep(1)
            
            print("    ⚠️  计算超时")
            return False
        
        except Exception as e:
            print(f"    ❌ 运行失败: {e}")
            return False
    
    def view_results(self):
        """查看结果"""
        print("  📊 查看结果...")
        
        try:
            # 点击结果标签
            results_tab = self.page.locator('text=结果')
            if results_tab.is_visible():
                results_tab.click()
                time.sleep(2)
                print("    ✅ 进入结果页面")
                return True
            else:
                print("    ⚠️  未找到结果标签")
                return False
        
        except Exception as e:
            print(f"    ❌ 查看结果失败: {e}")
            return False
    
    def verify_results(self) -> Dict[str, Any]:
        """验证结果"""
        print("  ✅ 验证结果...")
        
        verification = {
            "has_charts": False,
            "has_data_table": False,
            "has_profile_plot": False,
            "has_time_series": False,
            "error_messages": []
        }
        
        try:
            # 检查图表
            charts = self.page.locator('.plotly')
            chart_count = charts.count()
            verification["has_charts"] = chart_count > 0
            print(f"    📊 找到 {chart_count} 个图表")
            
            # 检查数据表格
            tables = self.page.locator('table')
            table_count = tables.count()
            verification["has_data_table"] = table_count > 0
            print(f"    📋 找到 {table_count} 个表格")
            
            # 检查特定图表类型
            if self.page.locator('text=纵剖面').is_visible():
                verification["has_profile_plot"] = True
                print("    ✅ 找到纵剖面图")
            
            if self.page.locator('text=时间序列').is_visible():
                verification["has_time_series"] = True
                print("    ✅ 找到时间序列图")
            
            # 检查错误信息
            error_elements = self.page.locator('.ant-message-error')
            if error_elements.is_visible():
                verification["error_messages"].append("发现错误提示")
                print("    ⚠️  发现错误提示")
        
        except Exception as e:
            verification["error_messages"].append(str(e))
            print(f"    ❌ 验证失败: {e}")
        
        return verification
    
    def test_single_case(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """测试单个案例"""
        case_id = test_case.get("id", 0)
        case_name = test_case.get("name", "unknown")
        
        print(f"\n{'='*60}")
        print(f"🧪 测试案例 #{case_id}: {case_name}")
        print(f"{'='*60}")
        
        result = {
            "id": case_id,
            "name": case_name,
            "type": test_case.get("type", "unknown"),
            "status": "pending",
            "steps": [],
            "screenshots": [],
            "verification": {},
            "error": None,
            "duration": 0
        }
        
        start_time = time.time()
        
        try:
            # 步骤1: 导航到应用
            self.navigate_to_app()
            result["steps"].append("✅ 应用加载")
            screenshot = self.take_screenshot(f"case_{case_id:03d}_01_home")
            result["screenshots"].append(str(screenshot))
            
            # 步骤2: 填写配置
            self.fill_config_form(test_case)
            result["steps"].append("✅ 配置填写")
            screenshot = self.take_screenshot(f"case_{case_id:03d}_02_config")
            result["screenshots"].append(str(screenshot))
            
            # 步骤3: 运行仿真
            if self.run_simulation():
                result["steps"].append("✅ 仿真运行")
                screenshot = self.take_screenshot(f"case_{case_id:03d}_03_running")
                result["screenshots"].append(str(screenshot))
            else:
                result["steps"].append("❌ 仿真失败")
                result["status"] = "failed"
                return result
            
            # 步骤4: 查看结果
            if self.view_results():
                result["steps"].append("✅ 结果显示")
                screenshot = self.take_screenshot(f"case_{case_id:03d}_04_results")
                result["screenshots"].append(str(screenshot))
            else:
                result["steps"].append("❌ 结果显示失败")
                result["status"] = "failed"
                return result
            
            # 步骤5: 验证结果
            verification = self.verify_results()
            result["verification"] = verification
            
            if verification["has_charts"] and not verification["error_messages"]:
                result["steps"].append("✅ 结果验证")
                result["status"] = "passed"
            else:
                result["steps"].append("⚠️  结果验证部分通过")
                result["status"] = "warning"
            
            # 最终截图
            screenshot = self.take_screenshot(f"case_{case_id:03d}_05_final")
            result["screenshots"].append(str(screenshot))
        
        except Exception as e:
            result["error"] = str(e)
            result["status"] = "error"
            result["steps"].append(f"❌ 错误: {e}")
            print(f"  ❌ 测试失败: {e}")
            
            # 错误截图
            try:
                screenshot = self.take_screenshot(f"case_{case_id:03d}_error")
                result["screenshots"].append(str(screenshot))
            except:
                pass
        
        finally:
            result["duration"] = time.time() - start_time
        
        return result
    
    def run_all_tests(self, max_cases: int = 10):
        """运行所有测试"""
        print("\n" + "="*60)
        print("🧪 开始Web端到端测试")
        print("="*60)
        
        # 加载测试案例
        test_cases = self.load_test_cases()
        if not test_cases:
            print("❌ 没有找到测试案例")
            return
        
        print(f"📋 找到 {len(test_cases)} 个测试案例")
        print(f"🎯 执行前 {max_cases} 个案例")
        
        # 设置浏览器
        self.setup_browser()
        
        try:
            # 执行测试
            for i, test_case in enumerate(test_cases[:max_cases], 1):
                result = self.test_single_case(test_case)
                self.results.append(result)
                
                # 显示进度
                print(f"\n📊 进度: {i}/{min(max_cases, len(test_cases))}")
                print(f"   状态: {result['status']}")
                print(f"   耗时: {result['duration']:.2f}秒")
        
        finally:
            # 关闭浏览器
            self.teardown_browser()
        
        # 生成报告
        self.generate_report()
    
    def generate_report(self):
        """生成测试报告"""
        print("\n" + "="*60)
        print("📊 生成测试报告")
        print("="*60)
        
        # 统计
        total = len(self.results)
        passed = sum(1 for r in self.results if r["status"] == "passed")
        failed = sum(1 for r in self.results if r["status"] == "failed")
        warning = sum(1 for r in self.results if r["status"] == "warning")
        error = sum(1 for r in self.results if r["status"] == "error")
        
        # 保存JSON报告
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total": total,
                "passed": passed,
                "failed": failed,
                "warning": warning,
                "error": error,
                "pass_rate": f"{passed/total*100:.1f}%" if total > 0 else "0%"
            },
            "results": self.results
        }
        
        report_file = self.reports_dir / f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ JSON报告: {report_file}")
        
        # 生成HTML报告
        html_report = self.generate_html_report(report_data)
        html_file = self.reports_dir / f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_report)
        
        print(f"✅ HTML报告: {html_file}")
        
        # 打印摘要
        print(f"\n{'='*60}")
        print("📊 测试摘要")
        print(f"{'='*60}")
        print(f"总计:   {total}")
        print(f"通过:   {passed} ({passed/total*100:.1f}%)")
        print(f"失败:   {failed}")
        print(f"警告:   {warning}")
        print(f"错误:   {error}")
        print(f"{'='*60}")
    
    def generate_html_report(self, report_data: Dict[str, Any]) -> str:
        """生成HTML报告"""
        summary = report_data["summary"]
        results = report_data["results"]
        
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HydroClaude Web端到端测试报告</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Microsoft YaHei', Arial, sans-serif; background: #f5f5f5; padding: 20px; }}
        .container {{ max-width: 1400px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        h1 {{ color: #1890ff; margin-bottom: 30px; border-bottom: 3px solid #1890ff; padding-bottom: 10px; }}
        .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }}
        .summary-card {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; text-align: center; }}
        .summary-card.passed {{ background: linear-gradient(135deg, #52c41a 0%, #389e0d 100%); }}
        .summary-card.failed {{ background: linear-gradient(135deg, #ff4d4f 0%, #cf1322 100%); }}
        .summary-card h3 {{ font-size: 14px; margin-bottom: 10px; }}
        .summary-card .value {{ font-size: 32px; font-weight: bold; }}
        .test-case {{ background: #fafafa; padding: 20px; margin-bottom: 20px; border-radius: 8px; border-left: 4px solid #1890ff; }}
        .test-case.passed {{ border-left-color: #52c41a; }}
        .test-case.failed {{ border-left-color: #ff4d4f; }}
        .test-case.warning {{ border-left-color: #faad14; }}
        .test-case-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }}
        .test-case-title {{ font-size: 18px; font-weight: bold; }}
        .status {{ padding: 5px 15px; border-radius: 4px; font-size: 12px; font-weight: bold; }}
        .status.passed {{ background: #f6ffed; color: #52c41a; }}
        .status.failed {{ background: #fff1f0; color: #ff4d4f; }}
        .status.warning {{ background: #fffbe6; color: #faad14; }}
        .steps {{ margin: 15px 0; }}
        .step {{ padding: 8px 12px; margin: 5px 0; background: white; border-radius: 4px; }}
        .screenshots {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 15px; margin-top: 15px; }}
        .screenshot {{ border: 1px solid #d9d9d9; border-radius: 4px; overflow: hidden; }}
        .screenshot img {{ width: 100%; height: auto; }}
        .screenshot-caption {{ padding: 10px; background: #fafafa; font-size: 12px; color: #666; }}
        .timestamp {{ color: #999; font-size: 14px; margin-top: 30px; text-align: center; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🧪 HydroClaude Web端到端测试报告</h1>
        
        <div class="summary">
            <div class="summary-card">
                <h3>总测试数</h3>
                <div class="value">{summary["total"]}</div>
            </div>
            <div class="summary-card passed">
                <h3>通过</h3>
                <div class="value">{summary["passed"]}</div>
            </div>
            <div class="summary-card failed">
                <h3>失败</h3>
                <div class="value">{summary["failed"]}</div>
            </div>
            <div class="summary-card">
                <h3>通过率</h3>
                <div class="value">{summary["pass_rate"]}</div>
            </div>
        </div>
        
        <h2>测试结果详情</h2>
"""
        
        for result in results:
            status_class = result["status"]
            status_text = {
                "passed": "✅ 通过",
                "failed": "❌ 失败",
                "warning": "⚠️ 警告",
                "error": "💥 错误"
            }.get(status_class, "❓ 未知")
            
            html += f"""
        <div class="test-case {status_class}">
            <div class="test-case-header">
                <div class="test-case-title">
                    案例 #{result["id"]}: {result["name"]}
                </div>
                <div class="status {status_class}">{status_text}</div>
            </div>
            <div><strong>类型:</strong> {result["type"]}</div>
            <div><strong>耗时:</strong> {result["duration"]:.2f}秒</div>
            
            <div class="steps">
                <strong>执行步骤:</strong>
"""
            for step in result["steps"]:
                html += f'<div class="step">{step}</div>'
            
            html += """
            </div>
"""
            
            if result["screenshots"]:
                html += """
            <div class="screenshots">
"""
                for i, screenshot in enumerate(result["screenshots"], 1):
                    screenshot_name = Path(screenshot).name
                    html += f"""
                <div class="screenshot">
                    <img src="../screenshots/{screenshot_name}" alt="Screenshot {i}">
                    <div class="screenshot-caption">截图 {i}</div>
                </div>
"""
                html += """
            </div>
"""
            
            html += """
        </div>
"""
        
        html += f"""
        <div class="timestamp">
            生成时间: {report_data["timestamp"]}
        </div>
    </div>
</body>
</html>
"""
        
        return html


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='HydroClaude Web端到端测试')
    parser.add_argument('--headless', action='store_true', help='无头模式运行')
    parser.add_argument('--max-cases', type=int, default=10, help='最大测试案例数')
    
    args = parser.parse_args()
    
    tester = WebE2ETester(headless=args.headless)
    tester.run_all_tests(max_cases=args.max_cases)


if __name__ == "__main__":
    main()
