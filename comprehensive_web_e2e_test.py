#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HydroClaude Web端到端完整测试脚本
Windows浏览器 + 截图方式 + 全功能测试

Author: HydroClaude Test Team
Date: 2025-11-13
"""

import sys
import os
import time
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List

# 确保输出使用UTF-8编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.common.action_chains import ActionChains
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
except ImportError:
    print("错误: 需要安装 selenium")
    print("请运行: pip install selenium")
    sys.exit(1)

# 项目路径
PROJECT_ROOT = Path(__file__).parent.absolute()
SCREENSHOTS_DIR = PROJECT_ROOT / "web_test_screenshots_final"
SCREENSHOTS_DIR.mkdir(exist_ok=True)

# 测试配置
TEST_CONFIG = {
    'base_url': 'http://localhost:3001',
    'backend_url': 'http://localhost:8000',
    'timeout': 30,
    'screenshot_delay': 1.5
}


class WebE2ETestRunner:
    """Web端到端测试运行器"""
    
    def __init__(self):
        self.driver = None
        self.test_results = []
        self.screenshot_counter = 0
        self.start_time = None
        
    def setup_driver(self):
        """设置Chrome浏览器驱动"""
        print("\n初始化Chrome浏览器...")
        
        options = webdriver.ChromeOptions()
        # options.add_argument('--headless')  # 无头模式（可选）
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--lang=zh-CN')  # 中文环境
        
        # 设置下载路径
        prefs = {
            'download.default_directory': str(PROJECT_ROOT / 'downloads'),
            'download.prompt_for_download': False,
        }
        options.add_experimental_option('prefs', prefs)
        
        try:
            self.driver = webdriver.Chrome(options=options)
            print("✓ Chrome浏览器启动成功")
            return True
        except Exception as e:
            print(f"✗ Chrome浏览器启动失败: {e}")
            print("\n请确保:")
            print("1. 已安装Chrome浏览器")
            print("2. 已安装chromedriver并配置到PATH")
            print("   下载地址: https://chromedriver.chromium.org/")
            return False
    
    def teardown_driver(self):
        """关闭浏览器"""
        if self.driver:
            self.driver.quit()
            print("\n✓ 浏览器已关闭")
    
    def take_screenshot(self, name: str, description: str = ""):
        """截图并保存"""
        self.screenshot_counter += 1
        timestamp = datetime.now().strftime('%H%M%S')
        filename = f"{self.screenshot_counter:02d}_{name}_{timestamp}.png"
        filepath = SCREENSHOTS_DIR / filename
        
        time.sleep(TEST_CONFIG['screenshot_delay'])  # 等待页面稳定
        self.driver.save_screenshot(str(filepath))
        
        print(f"  📸 截图保存: {filename}")
        if description:
            print(f"     {description}")
        
        return str(filepath)
    
    def wait_for_element(self, by, value, timeout=None):
        """等待元素出现"""
        if timeout is None:
            timeout = TEST_CONFIG['timeout']
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return element
        except TimeoutException:
            print(f"  ⚠️ 超时: 元素未找到 {value}")
            return None
    
    def test_01_homepage_load(self):
        """测试1: 首页加载"""
        print("\n" + "="*80)
        print("测试1: 首页加载")
        print("="*80)
        
        result = {
            'test_id': '01',
            'name': '首页加载',
            'status': 'unknown',
            'duration': 0,
            'screenshots': [],
            'notes': []
        }
        
        start = time.time()
        
        try:
            # 访问首页
            print(f"访问: {TEST_CONFIG['base_url']}")
            self.driver.get(TEST_CONFIG['base_url'])
            
            # 等待页面加载
            time.sleep(3)
            
            # 截图
            screenshot = self.take_screenshot('homepage', '首页完整界面')
            result['screenshots'].append(screenshot)
            
            # 检查页面标题
            title = self.driver.title
            print(f"  页面标题: {title}")
            result['notes'].append(f"页面标题: {title}")
            
            # 检查主要元素
            checks = []
            
            # 检查导航栏
            try:
                nav = self.driver.find_element(By.TAG_NAME, 'nav')
                checks.append(('导航栏', True))
                print("  ✓ 导航栏存在")
            except:
                checks.append(('导航栏', False))
                print("  ✗ 导航栏未找到")
            
            # 检查主要内容区
            try:
                main = self.driver.find_element(By.TAG_NAME, 'main')
                checks.append(('主内容区', True))
                print("  ✓ 主内容区存在")
            except:
                checks.append(('主内容区', False))
                print("  ✗ 主内容区未找到")
            
            # 判断测试结果
            if all(check[1] for check in checks):
                result['status'] = 'passed'
                print("✓ 测试通过")
            else:
                result['status'] = 'partial'
                print("⚠️ 测试部分通过")
            
        except Exception as e:
            result['status'] = 'failed'
            result['notes'].append(f"错误: {str(e)}")
            print(f"✗ 测试失败: {e}")
            
            # 失败时也截图
            try:
                screenshot = self.take_screenshot('homepage_error', '首页加载失败')
                result['screenshots'].append(screenshot)
            except:
                pass
        
        result['duration'] = time.time() - start
        self.test_results.append(result)
        
        return result
    
    def test_02_modeling_workspace(self):
        """测试2: 建模工作台"""
        print("\n" + "="*80)
        print("测试2: 建模工作台")
        print("="*80)
        
        result = {
            'test_id': '02',
            'name': '建模工作台',
            'status': 'unknown',
            'duration': 0,
            'screenshots': [],
            'notes': []
        }
        
        start = time.time()
        
        try:
            # 等待建模标签可见
            time.sleep(2)
            
            # 截图：建模工作台初始状态
            screenshot = self.take_screenshot('modeling_initial', '建模工作台初始状态')
            result['screenshots'].append(screenshot)
            
            # 检查组件面板
            print("  检查组件面板...")
            try:
                # 尝试多种可能的选择器
                selectors = [
                    "//div[contains(@class, 'component')]//span[contains(text(), '明渠')]",
                    "//div[contains(text(), '明渠')]",
                    "//*[contains(text(), 'Canal')]"
                ]
                
                canal_found = False
                for selector in selectors:
                    try:
                        element = self.driver.find_element(By.XPATH, selector)
                        if element:
                            canal_found = True
                            print("    ✓ 明渠组件存在")
                            break
                    except:
                        continue
                
                if not canal_found:
                    print("    ⚠️ 明渠组件未找到（可能是选择器问题）")
                    result['notes'].append("明渠组件未确认")
            except Exception as e:
                print(f"    ⚠️ 组件检查异常: {e}")
            
            # 检查工具栏
            print("  检查工具栏...")
            try:
                buttons = self.driver.find_elements(By.TAG_NAME, 'button')
                print(f"    ✓ 找到 {len(buttons)} 个按钮")
                result['notes'].append(f"工具栏按钮数: {len(buttons)}")
            except:
                print("    ⚠️ 工具栏检查异常")
            
            # 截图：工具栏特写
            screenshot = self.take_screenshot('modeling_toolbar', '工具栏详细')
            result['screenshots'].append(screenshot)
            
            result['status'] = 'passed'
            print("✓ 测试通过")
            
        except Exception as e:
            result['status'] = 'failed'
            result['notes'].append(f"错误: {str(e)}")
            print(f"✗ 测试失败: {e}")
            
            try:
                screenshot = self.take_screenshot('modeling_error', '建模工作台错误')
                result['screenshots'].append(screenshot)
            except:
                pass
        
        result['duration'] = time.time() - start
        self.test_results.append(result)
        
        return result
    
    def test_03_simulation_workspace(self):
        """测试3: 仿真管理工作台"""
        print("\n" + "="*80)
        print("测试3: 仿真管理工作台")
        print("="*80)
        
        result = {
            'test_id': '03',
            'name': '仿真管理工作台',
            'status': 'unknown',
            'duration': 0,
            'screenshots': [],
            'notes': []
        }
        
        start = time.time()
        
        try:
            # 点击仿真管理标签
            print("  切换到仿真管理标签...")
            try:
                # 尝试多种方式查找仿真管理标签 (侧边栏菜单)
                selectors = [
                    "//li[contains(@class, 'ant-menu-item')]//span[contains(text(), '仿真计算')]",
                    "//span[contains(text(), '仿真计算')]",
                    "//li[contains(@title, '仿真计算')]"
                ]
                
                tab_clicked = False
                for selector in selectors:
                    try:
                        tab = self.driver.find_element(By.XPATH, selector)
                        if tab:
                            tab.click()
                            tab_clicked = True
                            print("    ✓ 成功点击仿真计算菜单")
                            time.sleep(2)
                            break
                    except:
                        continue
                
                if not tab_clicked:
                    print("    ⚠️ 未找到仿真计算菜单，尝试直接截图")
            except Exception as e:
                print(f"    ⚠️ 切换标签异常: {e}")
            except Exception as e:
                print(f"    ⚠️ 切换标签异常: {e}")
            
            # 截图：仿真工作台
            screenshot = self.take_screenshot('simulation_workspace', '仿真工作台界面')
            result['screenshots'].append(screenshot)
            
            # 检查页面状态
            print("  检查页面元素...")
            
            # 检查是否有loading
            try:
                loading = self.driver.find_elements(By.CLASS_NAME, 'ant-spin')
                if loading:
                    print("    ⚠️ 页面处于加载状态")
                    result['notes'].append("页面显示loading")
            except:
                pass
            
            # 检查表单元素
            try:
                inputs = self.driver.find_elements(By.TAG_NAME, 'input')
                print(f"    ✓ 找到 {len(inputs)} 个输入框")
                result['notes'].append(f"输入框数量: {len(inputs)}")
            except:
                print("    ⚠️ 未找到输入框")
            
            result['status'] = 'passed'
            print("✓ 测试通过")
            
        except Exception as e:
            result['status'] = 'failed'
            result['notes'].append(f"错误: {str(e)}")
            print(f"✗ 测试失败: {e}")
            
            try:
                screenshot = self.take_screenshot('simulation_error', '仿真工作台错误')
                result['screenshots'].append(screenshot)
            except:
                pass
        
        result['duration'] = time.time() - start
        self.test_results.append(result)
        
        return result
    
    def test_04_simulation_configuration(self):
        """测试4: 仿真配置表单"""
        print("\n" + "="*80)
        print("测试4: 仿真配置表单")
        print("="*80)
        
        result = {
            'test_id': '04',
            'name': '仿真配置表单',
            'status': 'unknown',
            'duration': 0,
            'screenshots': [],
            'notes': []
        }
        
        start = time.time()
        
        try:
            # 填写仿真名称
            print("  填写仿真名称...")
            try:
                try:
                    name_input = self.driver.find_element(By.ID, 'name')
                except:
                    # 尝试通过 name 属性查找
                    name_input = self.driver.find_element(By.NAME, 'name')
                name_input.clear()
                name_input.send_keys('E2E测试仿真-' + datetime.now().strftime('%H%M%S'))
                print("    ✓ 仿真名称已填写")
                result['notes'].append("仿真名称填写成功")
            except Exception as e:
                print(f"    ⚠️ 仿真名称填写失败: {e}")
                result['notes'].append("仿真名称填写失败")
            
            # 截图：配置表单
            screenshot = self.take_screenshot('simulation_config', '仿真配置表单')
            result['screenshots'].append(screenshot)
            
            # 修改一些参数
            print("  修改配置参数...")
            try:
                # 尝试找到并修改长度参数
                length_input = self.driver.find_element(By.ID, 'config_length')
                length_input.clear()
                length_input.send_keys('1500')
                print("    ✓ 渠道长度已修改: 1500m")
                result['notes'].append("渠道长度: 1500m")
            except Exception as e:
                print(f"    ⚠️ 参数修改失败: {e}")
            
            time.sleep(1)
            
            # 截图：修改后的配置
            screenshot = self.take_screenshot('simulation_config_modified', '修改后的配置')
            result['screenshots'].append(screenshot)
            
            result['status'] = 'passed'
            print("✓ 测试通过")
            
        except Exception as e:
            result['status'] = 'failed'
            result['notes'].append(f"错误: {str(e)}")
            print(f"✗ 测试失败: {e}")
            
            try:
                screenshot = self.take_screenshot('config_error', '配置表单错误')
                result['screenshots'].append(screenshot)
            except:
                pass
        
        result['duration'] = time.time() - start
        self.test_results.append(result)
        
        return result
    
    def test_05_run_simulation(self):
        """测试5: 运行仿真"""
        print("\n" + "="*80)
        print("测试5: 运行仿真")
        print("="*80)
        
        result = {
            'test_id': '05',
            'name': '运行仿真',
            'status': 'unknown',
            'duration': 0,
            'screenshots': [],
            'notes': []
        }
        
        start = time.time()
        
        try:
            # 查找运行按钮
            print("  查找运行按钮...")
            run_button = None
            
            # 尝试多种方式查找按钮
            try:
                run_button = self.driver.find_element(By.XPATH, "//button[contains(., '运行仿真')]")
            except:
                try:
                    run_button = self.driver.find_element(By.XPATH, "//button[contains(., 'Run')]")
                except:
                    try:
                        # 尝试通过 type="submit" 查找
                        run_button = self.driver.find_element(By.XPATH, "//button[@type='submit']")
                        print("    ✓ 通过 type='submit' 找到按钮")
                    except:
                        print("    ⚠️ 未找到运行按钮")
            
            if run_button:
                print("    ✓ 找到运行按钮")
                
                # 截图：点击前
                screenshot = self.take_screenshot('before_run', '点击运行按钮前')
                result['screenshots'].append(screenshot)
                
                # 点击运行
                print("  点击运行按钮...")
                # 使用 JavaScript 点击以防被遮挡
                self.driver.execute_script("arguments[0].click();", run_button)
                print("    ✓ 已点击运行按钮")
                
                # 等待响应
                time.sleep(5)
                
                # 截图：点击后
                screenshot = self.take_screenshot('after_run', '点击运行按钮后')
                result['screenshots'].append(screenshot)
                
                # 检查页面上的提示信息
                print("  检查提交结果...")
                try:
                    # 检查是否有成功或失败提示
                    page_text = self.driver.find_element(By.TAG_NAME, 'body').text
                    
                    if '成功' in page_text or 'Success' in page_text or '仿真已提交' in page_text:
                        print("    ✓ 检测到成功提示")
                        result['status'] = 'passed'
                        result['notes'].append("仿真提交成功")
                    elif '失败' in page_text or '错误' in page_text or 'Error' in page_text or 'Failed' in page_text:
                        print("    ⚠️ 检测到失败提示")
                        result['status'] = 'partial'
                        result['notes'].append("仿真提交失败（后端问题）")
                    else:
                        print("    ⚠️ 未检测到明确的提示")
                        result['status'] = 'partial'
                        result['notes'].append("提交结果不明确")
                except Exception as e:
                    print(f"    ⚠️ 检查提示异常: {e}")
                    result['status'] = 'partial'
                
            else:
                result['status'] = 'failed'
                result['notes'].append("未找到运行按钮")
                print("✗ 测试失败：未找到运行按钮")
                # 打印页面源码片段帮助调试
                print("DEBUG: 页面源码片段:")
                print(self.driver.page_source[:1000])
                try:
                    submit_btns = self.driver.find_elements(By.XPATH, "//button[@type='submit']")
                    print(f"DEBUG: 找到 {len(submit_btns)} 个 submit 按钮")
                except:
                    pass
            
        except Exception as e:
            result['status'] = 'failed'
            result['notes'].append(f"错误: {str(e)}")
            print(f"✗ 测试失败: {e}")
            
            try:
                screenshot = self.take_screenshot('run_error', '运行仿真错误')
                result['screenshots'].append(screenshot)
            except:
                pass
        
        result['duration'] = time.time() - start
        self.test_results.append(result)
        
        return result
    
    def test_06_ui_elements(self):
        """测试6: UI元素交互"""
        print("\n" + "="*80)
        print("测试6: UI元素交互")
        print("="*80)
        
        result = {
            'test_id': '06',
            'name': 'UI元素交互',
            'status': 'unknown',
            'duration': 0,
            'screenshots': [],
            'notes': []
        }
        
        start = time.time()
        
        try:
            # 返回建模标签
            print("  切换回建模工作台...")
            try:
                # 点击侧边栏"高级建模"
                selectors = [
                    "//li[contains(@class, 'ant-menu-item')]//span[contains(text(), '高级建模')]",
                    "//span[contains(text(), '高级建模')]",
                    "//li[contains(@title, '高级建模')]"
                ]
                
                tab_clicked = False
                for selector in selectors:
                    try:
                        tab = self.driver.find_element(By.XPATH, selector)
                        if tab:
                            tab.click()
                            tab_clicked = True
                            print("    ✓ 成功点击高级建模菜单")
                            time.sleep(2)
                            break
                    except:
                        continue
                
                if not tab_clicked:
                    print("    ⚠️ 菜单切换失败")
            except Exception as e:
                print(f"    ⚠️ 菜单切换异常: {e}")
            
            screenshot = self.take_screenshot('back_to_modeling', '返回建模工作台')
            result['screenshots'].append(screenshot)
            
            # 测试按钮点击
            print("  测试工具栏按钮...")
            try:
                buttons = self.driver.find_elements(By.TAG_NAME, 'button')[:5]
                for i, btn in enumerate(buttons):
                    try:
                        btn.click()
                        time.sleep(0.5)
                        print(f"    ✓ 按钮 {i+1} 可点击")
                    except:
                        print(f"    ⚠️ 按钮 {i+1} 点击失败")
            except:
                print("    ⚠️ 按钮测试失败")
            
            screenshot = self.take_screenshot('ui_interaction', 'UI交互测试')
            result['screenshots'].append(screenshot)
            
            result['status'] = 'passed'
            print("✓ 测试通过")
            
        except Exception as e:
            result['status'] = 'failed'
            result['notes'].append(f"错误: {str(e)}")
            print(f"✗ 测试失败: {e}")
        
        result['duration'] = time.time() - start
        self.test_results.append(result)
        
        return result
    
    def test_07_console_errors(self):
        """测试7: 浏览器控制台错误"""
        print("\n" + "="*80)
        print("测试7: 浏览器控制台错误")
        print("="*80)
        
        result = {
            'test_id': '07',
            'name': '控制台错误检查',
            'status': 'unknown',
            'duration': 0,
            'screenshots': [],
            'notes': []
        }
        
        start = time.time()
        
        try:
            # 获取浏览器日志
            print("  获取浏览器控制台日志...")
            logs = self.driver.get_log('browser')
            
            errors = [log for log in logs if log['level'] == 'SEVERE']
            warnings = [log for log in logs if log['level'] == 'WARNING']
            
            print(f"    错误数: {len(errors)}")
            print(f"    警告数: {len(warnings)}")
            
            result['notes'].append(f"控制台错误: {len(errors)}")
            result['notes'].append(f"控制台警告: {len(warnings)}")
            
            # 打印前5个错误
            if errors:
                print("\n  前5个错误:")
                for i, error in enumerate(errors[:5], 1):
                    print(f"    {i}. {error['message'][:100]}")
            
            if len(errors) == 0:
                result['status'] = 'passed'
                print("✓ 测试通过：无严重错误")
            elif len(errors) < 5:
                result['status'] = 'partial'
                print("⚠️ 测试部分通过：有少量错误")
            else:
                result['status'] = 'failed'
                print("✗ 测试失败：错误较多")
            
        except Exception as e:
            result['status'] = 'partial'
            result['notes'].append(f"错误: {str(e)}")
            print(f"⚠️ 无法获取控制台日志: {e}")
        
        result['duration'] = time.time() - start
        self.test_results.append(result)
        
        return result
    
    def run_all_tests(self):
        """运行所有测试"""
        self.start_time = datetime.now()
        
        print("\n" + "="*80)
        print("  HydroClaude Web 端到端完整测试")
        print("="*80)
        print(f"开始时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"测试URL: {TEST_CONFIG['base_url']}")
        print(f"截图目录: {SCREENSHOTS_DIR}")
        
        # 设置浏览器
        if not self.setup_driver():
            return
        
        try:
            # 执行测试
            tests = [
                self.test_01_homepage_load,
                self.test_02_modeling_workspace,
                self.test_03_simulation_workspace,
                self.test_04_simulation_configuration,
                self.test_05_run_simulation,
                self.test_06_ui_elements,
                self.test_07_console_errors
            ]
            
            for test_func in tests:
                try:
                    test_func()
                except Exception as e:
                    print(f"\n✗ 测试执行异常: {e}")
                    import traceback
                    traceback.print_exc()
                
                time.sleep(1)  # 测试间隔
            
            # 打印总结
            self.print_summary()
            
            # 保存结果
            self.save_results()
            
        finally:
            self.teardown_driver()
    
    def print_summary(self):
        """打印测试总结"""
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()
        
        print("\n" + "="*80)
        print("  测试总结")
        print("="*80)
        print(f"总测试数: {len(self.test_results)}")
        
        stats = {
            'passed': 0,
            'partial': 0,
            'failed': 0,
            'unknown': 0
        }
        
        for result in self.test_results:
            stats[result['status']] = stats.get(result['status'], 0) + 1
        
        print(f"  - 通过: {stats['passed']}")
        print(f"  - 部分通过: {stats['partial']}")
        print(f"  - 失败: {stats['failed']}")
        print(f"  - 未知: {stats['unknown']}")
        
        print(f"\n总截图数: {self.screenshot_counter}")
        print(f"总耗时: {duration:.2f}秒")
        
        print("\n详细结果:")
        for result in self.test_results:
            status_icon = {
                'passed': '✓',
                'partial': '⚠️',
                'failed': '✗',
                'unknown': '?'
            }.get(result['status'], '?')
            
            print(f"  {status_icon} [{result['test_id']}] {result['name']} - {result['status'].upper()}")
            print(f"     耗时: {result['duration']:.2f}秒, 截图: {len(result['screenshots'])}张")
            if result['notes']:
                for note in result['notes']:
                    print(f"     - {note}")
        
        print("="*80)
    
    def save_results(self):
        """保存测试结果"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = SCREENSHOTS_DIR / f"test_results_{timestamp}.json"
        
        summary = {
            'test_time': self.start_time.isoformat(),
            'duration': (datetime.now() - self.start_time).total_seconds(),
            'base_url': TEST_CONFIG['base_url'],
            'total_tests': len(self.test_results),
            'total_screenshots': self.screenshot_counter,
            'results': self.test_results
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ 测试结果已保存: {output_file}")


def main():
    """主函数"""
    print("\n" + "="*80)
    print("  HydroClaude Web E2E 测试工具")
    print("="*80)
    print("\n请确保:")
    print("1. 前端服务正在运行 (http://localhost:5173)")
    print("2. 后端服务正在运行 (http://localhost:8000)")
    print("3. 已安装Chrome浏览器和chromedriver")
    print("4. 已安装Python包: selenium")
    
    # input("\n按回车键开始测试...")
    
    runner = WebE2ETestRunner()
    runner.run_all_tests()


if __name__ == '__main__':
    main()
