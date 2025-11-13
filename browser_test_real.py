#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Real Browser Testing with Screenshots
真实浏览器测试和截图
"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import os
from datetime import datetime

# 创建截图目录
SCREENSHOT_DIR = "web_test_screenshots"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# Web应用URL
FRONTEND_URL = "http://localhost:5173"
BACKEND_URL = "http://localhost:8000"

class WebTester:
    def __init__(self):
        print("=" * 80)
        print("启动浏览器测试...")
        print("=" * 80)
        
        # 配置Chrome选项
        chrome_options = Options()
        chrome_options.add_argument('--start-maximized')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        # 初始化driver
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.wait = WebDriverWait(self.driver, 10)
        
        self.issues = []
        self.screenshot_count = 0
    
    def save_screenshot(self, name):
        """保存截图"""
        self.screenshot_count += 1
        timestamp = datetime.now().strftime("%H%M%S")
        filename = f"{self.screenshot_count:02d}_{name}_{timestamp}.png"
        filepath = os.path.join(SCREENSHOT_DIR, filename)
        self.driver.save_screenshot(filepath)
        print(f"[OK] Screenshot saved: {filename}")
        return filepath
    
    def log_issue(self, severity, description, screenshot=None):
        """记录发现的问题"""
        issue = {
            "severity": severity,
            "description": description,
            "screenshot": screenshot,
            "timestamp": datetime.now().isoformat()
        }
        self.issues.append(issue)
        
        icon = "[!]" if severity == "critical" else "[*]" if severity == "warning" else "[i]"
        print(f"{icon} [{severity.upper()}] {description}")
    
    def test_1_homepage_load(self):
        """测试1: 首页加载"""
        print("\n[测试1] 首页加载测试")
        print("-" * 80)
        
        try:
            # 访问首页
            self.driver.get(FRONTEND_URL)
            time.sleep(3)  # 等待页面加载
            
            # 截图
            screenshot = self.save_screenshot("homepage")
            
            # 检查页面标题
            title = self.driver.title
            print(f"页面标题: {title}")
            
            # 检查是否有错误
            try:
                # 检查控制台错误
                logs = self.driver.get_log('browser')
                errors = [log for log in logs if log['level'] == 'SEVERE']
                if errors:
                    self.log_issue("warning", f"浏览器控制台有{len(errors)}个错误", screenshot)
                    for error in errors[:3]:  # 只显示前3个
                        print(f"  - {error['message']}")
            except:
                pass
            
            # 检查页面元素
            try:
                header = self.driver.find_element(By.TAG_NAME, "header")
                print(f"[OK] Header element found")
            except:
                self.log_issue("critical", "Header元素未找到", screenshot)
            
            print("[OK] Homepage test completed")
            
        except Exception as e:
            screenshot = self.save_screenshot("homepage_error")
            self.log_issue("critical", f"首页加载失败: {str(e)}", screenshot)
    
    def test_2_modeling_workspace(self):
        """测试2: 建模工作台"""
        print("\n[测试2] 建模工作台测试")
        print("-" * 80)
        
        try:
            # 应该已经在首页，查找建模工作台标签
            time.sleep(2)
            screenshot = self.save_screenshot("modeling_workspace")
            
            # 查找建模相关元素
            try:
                # 查找"建模工作台"文本
                elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), '建模')]")
                if elements:
                    print(f"[OK] Found {len(elements)} modeling elements")
                else:
                    self.log_issue("warning", "未找到建模相关元素", screenshot)
            except Exception as e:
                self.log_issue("warning", f"建模元素查找异常: {str(e)}", screenshot)
            
            # 查找按钮
            buttons = self.driver.find_elements(By.TAG_NAME, "button")
            print(f"页面共有 {len(buttons)} 个按钮")
            
            # 截图当前状态
            time.sleep(1)
            self.save_screenshot("modeling_interface")
            
            print("[OK] Modeling workspace test completed")
            
        except Exception as e:
            screenshot = self.save_screenshot("modeling_error")
            self.log_issue("warning", f"建模工作台测试异常: {str(e)}", screenshot)
    
    def test_3_simulation_tab(self):
        """测试3: 仿真管理标签"""
        print("\n[测试3] 仿真管理标签测试")
        print("-" * 80)
        
        try:
            # 查找仿真管理标签
            time.sleep(1)
            
            # 尝试查找并点击仿真管理标签
            try:
                tabs = self.driver.find_elements(By.CLASS_NAME, "ant-tabs-tab")
                print(f"找到 {len(tabs)} 个标签页")
                
                for tab in tabs:
                    if "仿真" in tab.text:
                        print(f"[OK] Found simulation tab: {tab.text}")
                        tab.click()
                        time.sleep(2)
                        self.save_screenshot("simulation_tab")
                        break
            except Exception as e:
                self.log_issue("warning", f"标签切换失败: {str(e)}")
            
            # 截图仿真界面
            self.save_screenshot("simulation_interface")
            
            print("[OK] Simulation test completed")
            
        except Exception as e:
            screenshot = self.save_screenshot("simulation_error")
            self.log_issue("warning", f"仿真管理测试异常: {str(e)}", screenshot)
    
    def test_4_check_console_errors(self):
        """测试4: 检查控制台错误"""
        print("\n[测试4] 控制台错误检查")
        print("-" * 80)
        
        try:
            logs = self.driver.get_log('browser')
            
            errors = [log for log in logs if log['level'] == 'SEVERE']
            warnings = [log for log in logs if log['level'] == 'WARNING']
            
            print(f"控制台错误数: {len(errors)}")
            print(f"控制台警告数: {len(warnings)}")
            
            if errors:
                screenshot = self.save_screenshot("console_errors")
                self.log_issue("warning", f"控制台有 {len(errors)} 个严重错误", screenshot)
                
                # 显示前5个错误
                for i, error in enumerate(errors[:5]):
                    print(f"\n错误 {i+1}:")
                    print(f"  级别: {error['level']}")
                    print(f"  消息: {error['message'][:200]}")
            else:
                print("[OK] No console errors")
            
        except Exception as e:
            print(f"️ 无法获取控制台日志: {str(e)}")
    
    def test_5_responsive_check(self):
        """测试5: 响应式检查"""
        print("\n[测试5] 响应式布局测试")
        print("-" * 80)
        
        try:
            # 测试不同屏幕尺寸
            sizes = [
                ("desktop", 1920, 1080),
                ("laptop", 1366, 768),
                ("tablet", 768, 1024)
            ]
            
            for name, width, height in sizes:
                self.driver.set_window_size(width, height)
                time.sleep(1)
                self.save_screenshot(f"responsive_{name}")
                print(f"[OK] {name} ({width}x{height}) screenshot saved")
            
            # 恢复最大化
            self.driver.maximize_window()
            time.sleep(1)
            
            print("[OK] Responsive test completed")
            
        except Exception as e:
            self.log_issue("warning", f"响应式测试异常: {str(e)}")
    
    def run_all_tests(self):
        """运行所有测试"""
        try:
            self.test_1_homepage_load()
            self.test_2_modeling_workspace()
            self.test_3_simulation_tab()
            self.test_4_check_console_errors()
            self.test_5_responsive_check()
            
        finally:
            # 生成测试报告
            self.generate_report()
            
            # 关闭浏览器
            print("\n" + "=" * 80)
            print("测试完成，5秒后关闭浏览器...")
            print("=" * 80)
            time.sleep(5)
            self.driver.quit()
    
    def generate_report(self):
        """生成测试报告"""
        print("\n" + "=" * 80)
        print("测试总结")
        print("=" * 80)
        
        print(f"总截图数: {self.screenshot_count}")
        print(f"发现问题数: {len(self.issues)}")
        
        if self.issues:
            print("\n发现的问题:")
            for i, issue in enumerate(self.issues, 1):
                print(f"\n问题 {i}:")
                print(f"  严重性: {issue['severity']}")
                print(f"  描述: {issue['description']}")
                if issue['screenshot']:
                    print(f"  截图: {issue['screenshot']}")
        else:
            print("\n[OK] No critical issues found!")
        
        print(f"\n所有截图保存在: {SCREENSHOT_DIR}/")
        print("=" * 80)

def main():
    """主函数"""
    tester = WebTester()
    tester.run_all_tests()

if __name__ == '__main__':
    main()

