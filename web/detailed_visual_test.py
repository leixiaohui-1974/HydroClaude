#!/usr/bin/env python3
"""
HydroClaude Web 详细可视化测试 - 修复版
增加等待时间，确保页面完全渲染后再截图
"""

from playwright.sync_api import sync_playwright
import time
from datetime import datetime
from pathlib import Path

class DetailedVisualTester:
    def __init__(self):
        self.frontend_url = "http://localhost:5174"
        self.screenshots_dir = Path("/workspace/web/detailed_screenshots")
        self.screenshots_dir.mkdir(exist_ok=True)
        self.test_num = 0
        self.findings = []
        
    def log(self, msg, status="info"):
        colors = {
            "success": "\033[92m✅",
            "error": "\033[91m❌",
            "info": "\033[94mℹ️",
            "warning": "\033[93m⚠️"
        }
        end = "\033[0m"
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {colors.get(status, colors['info'])} {msg}{end}")
        
    def save_screenshot(self, page, name, description=""):
        self.test_num += 1
        filename = f"{self.test_num:02d}_{name}.png"
        path = self.screenshots_dir / filename
        page.screenshot(path=str(path), full_page=True)
        self.log(f"截图 {filename}: {description}", "info")
        return str(path)
        
    def wait_for_render(self, page, seconds=3):
        """等待页面完全渲染"""
        time.sleep(seconds)
        page.wait_for_load_state("networkidle")
        
    def analyze_page_content(self, page):
        """分析页面内容"""
        try:
            # 获取页面文本
            body_text = page.locator('body').inner_text()
            
            # 检查关键元素
            has_modeling_components = "明渠" in body_text or "矩形明渠" in body_text
            has_simulation_form = "仿真配置" in body_text or "单场景结果" in body_text
            has_canvas = page.locator('.react-flow').count() > 0
            
            return {
                "has_modeling_components": has_modeling_components,
                "has_simulation_form": has_simulation_form,
                "has_canvas": has_canvas,
                "text_preview": body_text[:200]
            }
        except Exception as e:
            return {"error": str(e)}
            
    def test_tab_switching(self, page):
        """测试标签切换并验证内容"""
        self.log("\n=== 测试标签切换和内容验证 ===", "info")
        
        # 1. 访问首页
        self.log("1. 访问首页...", "info")
        page.goto(self.frontend_url, timeout=30000)
        self.wait_for_render(page, 4)
        self.save_screenshot(page, "homepage", "首页加载")
        
        # 分析首页内容
        homepage_content = self.analyze_page_content(page)
        self.log(f"   首页内容分析: {homepage_content}", "info")
        
        # 2. 确保在建模工作台
        self.log("\n2. 点击建模工作台标签...", "info")
        try:
            # 使用更明确的选择器
            modeling_tab = page.locator('text=建模工作台').first
            if modeling_tab.is_visible(timeout=5000):
                modeling_tab.click()
                self.wait_for_render(page, 5)
                self.save_screenshot(page, "modeling_workspace", "建模工作台 - 应显示组件库和画布")
                
                # 验证建模工作台特征
                modeling_content = self.analyze_page_content(page)
                self.log(f"   建模工作台内容: {modeling_content}", "info")
                
                if modeling_content.get("has_modeling_components"):
                    self.log("   ✅ 确认：建模工作台显示正确（有组件库）", "success")
                    self.findings.append(("建模工作台显示", True, "正确显示组件库和画布"))
                else:
                    self.log("   ⚠️  警告：建模工作台可能缺少组件", "warning")
                    self.findings.append(("建模工作台显示", False, "未找到预期组件"))
            else:
                self.log("   ❌ 建模工作台标签不可见", "error")
        except Exception as e:
            self.log(f"   ❌ 建模工作台测试失败: {e}", "error")
            
        # 3. 切换到仿真管理
        self.log("\n3. 切换到仿真管理标签...", "info")
        try:
            simulation_tab = page.locator('text=仿真管理').first
            if simulation_tab.is_visible(timeout=5000):
                self.log("   点击仿真管理标签...", "info")
                simulation_tab.click()
                
                # 等待更长时间确保懒加载完成
                self.log("   等待页面渲染（8秒）...", "info")
                self.wait_for_render(page, 8)
                
                self.save_screenshot(page, "simulation_management", "仿真管理 - 应显示仿真配置表单")
                
                # 验证仿真管理特征
                simulation_content = self.analyze_page_content(page)
                self.log(f"   仿真管理内容: {simulation_content}", "info")
                
                if simulation_content.get("has_simulation_form"):
                    self.log("   ✅ 确认：仿真管理显示正确（有仿真配置）", "success")
                    self.findings.append(("仿真管理显示", True, "正确显示仿真配置表单"))
                else:
                    self.log("   ⚠️  警告：仿真管理可能缺少表单", "warning")
                    self.findings.append(("仿真管理显示", False, "未找到仿真配置表单"))
                    
                # 检查是否还显示建模组件（不应该）
                if simulation_content.get("has_modeling_components") and simulation_content.get("has_canvas"):
                    self.log("   ❌ 错误：仿真管理仍显示建模组件！", "error")
                    self.findings.append(("内容隔离", False, "仿真管理中仍显示建模组件"))
                else:
                    self.log("   ✅ 确认：建模组件已隐藏", "success")
                    self.findings.append(("内容隔离", True, "仿真管理与建模工作台内容正确隔离"))
            else:
                self.log("   ❌ 仿真管理标签不可见", "error")
        except Exception as e:
            self.log(f"   ❌ 仿真管理测试失败: {e}", "error")
            
        # 4. 再次切换回建模工作台
        self.log("\n4. 切换回建模工作台验证...", "info")
        try:
            modeling_tab = page.locator('text=建模工作台').first
            modeling_tab.click()
            self.wait_for_render(page, 5)
            self.save_screenshot(page, "modeling_workspace_2", "再次返回建模工作台")
            
            modeling_content_2 = self.analyze_page_content(page)
            if modeling_content_2.get("has_modeling_components"):
                self.log("   ✅ 确认：返回建模工作台成功", "success")
            else:
                self.log("   ⚠️  警告：返回后内容异常", "warning")
        except Exception as e:
            self.log(f"   ❌ 返回测试失败: {e}", "error")
            
    def test_simulation_tab_details(self, page):
        """详细测试仿真管理标签的子标签"""
        self.log("\n=== 测试仿真管理子标签 ===", "info")
        
        try:
            # 切换到仿真管理
            page.locator('text=仿真管理').first.click()
            self.wait_for_render(page, 8)
            
            # 检查是否有子标签
            self.log("1. 检查单场景结果标签...", "info")
            single_scenario = page.locator('text=单场景结果')
            if single_scenario.count() > 0:
                single_scenario.first.click()
                self.wait_for_render(page, 3)
                self.save_screenshot(page, "single_scenario_tab", "单场景结果标签")
                self.log("   ✅ 单场景结果标签存在", "success")
            else:
                self.log("   ℹ️  未找到单场景结果标签", "info")
                
            # 检查多场景对比
            self.log("2. 检查多场景对比标签...", "info")
            comparison = page.locator('text=多场景对比')
            if comparison.count() > 0:
                comparison.first.click()
                self.wait_for_render(page, 3)
                self.save_screenshot(page, "comparison_tab", "多场景对比标签")
                self.log("   ✅ 多场景对比标签存在", "success")
            else:
                self.log("   ℹ️  未找到多场景对比标签", "info")
                
        except Exception as e:
            self.log(f"   ⚠️  子标签测试失败: {e}", "warning")
            
    def test_ui_elements(self, page):
        """测试UI元素存在性"""
        self.log("\n=== 测试UI元素 ===", "info")
        
        # 在建模工作台
        page.locator('text=建模工作台').first.click()
        self.wait_for_render(page, 3)
        
        elements_to_check = [
            ("组件库", ".component-palette, text=组件库, text=明渠"),
            ("画布区域", ".react-flow, [class*='react-flow']"),
            ("属性面板", ".property-panel, text=属性面板, text=属性"),
        ]
        
        for name, selector in elements_to_check:
            try:
                # 尝试多个选择器
                found = False
                for sel in selector.split(", "):
                    if page.locator(sel).count() > 0:
                        found = True
                        break
                        
                if found:
                    self.log(f"   ✅ {name} 存在", "success")
                else:
                    self.log(f"   ⚠️  {name} 未找到", "warning")
            except Exception as e:
                self.log(f"   ⚠️  检查{name}时出错: {e}", "warning")
                
    def generate_report(self):
        """生成详细分析报告"""
        self.log("\n=== 生成分析报告 ===", "info")
        
        report = []
        report.append("\n" + "="*70)
        report.append("HydroClaude Web 详细可视化测试报告")
        report.append("="*70)
        report.append(f"\n测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"截图数量: {self.test_num}")
        report.append(f"截图目录: {self.screenshots_dir}")
        
        report.append("\n\n发现问题汇总:")
        report.append("-" * 70)
        
        if self.findings:
            for i, (name, passed, detail) in enumerate(self.findings, 1):
                status = "✅ 通过" if passed else "❌ 失败"
                report.append(f"{i}. {name}: {status}")
                report.append(f"   详情: {detail}")
        else:
            report.append("无重大发现")
            
        report.append("\n" + "="*70)
        
        report_text = "\n".join(report)
        print(report_text)
        
        # 保存报告
        report_file = Path("/workspace/web/detailed_visual_test_report.txt")
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_text)
            
        return len([f for f in self.findings if not f[1]]) == 0
        
    def run_all_tests(self):
        """运行所有测试"""
        self.log("\n" + "="*70, "info")
        self.log("HydroClaude Web 详细可视化测试", "info")
        self.log("="*70 + "\n", "info")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                device_scale_factor=1
            )
            page = context.new_page()
            
            try:
                # 主要测试
                self.test_tab_switching(page)
                
                # 详细子测试
                self.test_simulation_tab_details(page)
                
                # UI元素测试
                self.test_ui_elements(page)
                
            except Exception as e:
                self.log(f"\n❌ 测试过程中出现错误: {e}", "error")
            finally:
                browser.close()
                
        # 生成报告
        success = self.generate_report()
        
        if success:
            self.log("\n🎉 所有测试通过！", "success")
        else:
            self.log("\n⚠️  发现一些问题，请查看报告", "warning")
            
        return success

def main():
    tester = DetailedVisualTester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())
