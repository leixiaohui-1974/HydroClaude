# HydroClaude Web界面测试执行指南

**日期**: 2025-11-12  
**目的**: 完成Web前端界面的完整测试并生成截图报告

---

## 🚀 快速开始（3步完成）

### 步骤1: 启动服务（2个终端窗口）

**终端1 - 启动后端**:
```bash
cd E:\OneDrive\Documents\GitHub\Test\HydroClaude\web\backend\api_gateway
python main.py
```
保持这个窗口运行。

**终端2 - 启动前端**:
```bash
cd E:\OneDrive\Documents\GitHub\Test\HydroClaude\web\frontend
npm run dev
```
保持这个窗口运行。

等待20秒，确保两个服务都启动完成。

### 步骤2: 验证服务

打开浏览器，访问：
- 后端: http://localhost:8000/health （应显示 "healthy"）
- 前端: http://localhost:5173 （应显示HydroClaude界面）

### 步骤3: 运行自动化测试

**终端3 - 运行测试**:
```bash
cd E:\OneDrive\Documents\GitHub\Test\HydroClaude
python web_browser_test_selenium.py
```

如果Selenium不可用，请按照下面的手动测试步骤进行。

---

## 📋 手动测试步骤（详细版）

### 前置条件检查

- [ ] 后端服务运行中 (http://localhost:8000)
- [ ] 前端服务运行中 (http://localhost:5173)
- [ ] Chrome浏览器已安装
- [ ] 截图工具准备好 (Win + Shift + S)

### 测试步骤

#### Test 1: 首页加载 ✅

**操作**:
1. 打开浏览器: http://localhost:5173
2. 等待页面完全加载（3-5秒）
3. 按F12打开开发者工具
4. 查看Console标签，确认无红色错误

**验证点**:
- [ ] 页面正常显示（无白屏）
- [ ] 没有控制台错误
- [ ] 页面标题正确显示
- [ ] Logo/Header可见

**截图**: 使用 Win + Shift + S 保存为 `web_test_screenshots/01_homepage.png`

---

#### Test 2: 模型编辑器 ✅

**操作**:
1. 查找页面上的输入框
2. 尝试输入数值（例如：渠道长度 = 10000）
3. 测试输入验证（输入无效值，如负数）

**验证点**:
- [ ] 输入框可见且可编辑
- [ ] 输入验证工作正常
- [ ] 标签清晰易懂
- [ ] 单位显示正确

**截图**: 保存为 `web_test_screenshots/02_model_editor_empty.png`

输入一些数值后再截图: `web_test_screenshots/02_model_editor_filled.png`

---

#### Test 3: 添加结构（闸门/堰） ✅

**操作**:
1. 查找"添加结构"或"Add Structure"按钮
2. 点击按钮
3. 填写结构参数
4. 确认添加

**验证点**:
- [ ] 按钮可点击
- [ ] 对话框/表单正常显示
- [ ] 所有字段可编辑
- [ ] 确认按钮有效

**截图**: 
- 添加前: `web_test_screenshots/03_add_structure_button.png`
- 对话框: `web_test_screenshots/03_add_structure_dialog.png`
- 添加后: `web_test_screenshots/03_add_structure_complete.png`

---

#### Test 4: 配置仿真参数 ✅

**操作**:
1. 查找仿真配置区域
2. 设置仿真参数（网格数、时间步等）
3. 确认参数有效

**验证点**:
- [ ] 配置选项清晰
- [ ] 默认值合理
- [ ] 参数可修改
- [ ] 有帮助文本/提示

**截图**: 保存为 `web_test_screenshots/04_simulation_config.png`

---

#### Test 5: 运行仿真 ✅

**操作**:
1. 点击"运行仿真"或"Run Simulation"按钮
2. 观察进度指示
3. 等待完成（通常10-30秒）

**验证点**:
- [ ] 仿真可以启动
- [ ] 进度条/指示器正常显示
- [ ] 没有错误提示
- [ ] 完成后有明确提示

**截图**: 
- 运行中: `web_test_screenshots/05_simulation_running.png`
- 完成后: `web_test_screenshots/05_simulation_complete.png`

---

#### Test 6: 查看结果 - 图表 ✅

**操作**:
1. 查看仿真结果
2. 检查水深剖面图
3. 检查流量分布图
4. 测试图表交互（缩放、平移、悬停）

**验证点**:
- [ ] 图表正确渲染
- [ ] 数据合理（无异常值）
- [ ] 交互功能正常
- [ ] 图例清晰
- [ ] 坐标轴标签正确

**截图**: 
- 水深剖面: `web_test_screenshots/06_result_profile.png`
- 流量分布: `web_test_screenshots/06_result_flow.png`
- 交互演示: `web_test_screenshots/06_result_interaction.png`

---

#### Test 7: 查看结果 - 数据表 ✅

**操作**:
1. 切换到数据表视图
2. 浏览数据
3. 测试排序功能（如果有）

**验证点**:
- [ ] 数据表正确显示
- [ ] 数值精度合理
- [ ] 列标题清晰
- [ ] 数据可浏览

**截图**: 保存为 `web_test_screenshots/07_result_data_table.png`

---

#### Test 8: 导出功能 ✅

**操作**:
1. 点击导出按钮
2. 选择导出格式（JSON/CSV/图片）
3. 确认下载

**验证点**:
- [ ] 导出按钮可用
- [ ] 格式选择清晰
- [ ] 文件可以下载
- [ ] 文件内容正确

**截图**: 
- 导出对话框: `web_test_screenshots/08_export_dialog.png`
- 成功提示: `web_test_screenshots/08_export_success.png`

---

#### Test 9: 错误处理 ✅

**操作**:
1. 输入无效数据（负数、超大值）
2. 尝试在不完整配置下运行仿真
3. 观察错误提示

**验证点**:
- [ ] 错误提示清晰
- [ ] 用户友好的消息
- [ ] 指出具体问题
- [ ] 提供解决建议

**截图**: 
- 输入验证错误: `web_test_screenshots/09_error_validation.png`
- 仿真错误: `web_test_screenshots/09_error_simulation.png`

---

#### Test 10: 完整工作流 ✅

**操作**:
从头到尾完成一次完整的仿真：
1. 创建新模型
2. 配置参数
3. 添加结构
4. 运行仿真
5. 查看结果
6. 导出数据

**验证点**:
- [ ] 整个流程流畅
- [ ] 无卡顿
- [ ] 无崩溃
- [ ] 结果正确

**截图**: 保存为 `web_test_screenshots/10_complete_workflow.png`

---

## 📊 测试结果记录

### 测试环境
- 操作系统: Windows 10
- 浏览器: Chrome ____版本
- 后端版本: ____
- 前端版本: ____
- 测试日期: 2025-11-12

### 测试统计

| 测试项 | 状态 | 备注 |
|--------|------|------|
| 1. 首页加载 | [ ] PASS / [ ] FAIL | |
| 2. 模型编辑器 | [ ] PASS / [ ] FAIL | |
| 3. 添加结构 | [ ] PASS / [ ] FAIL | |
| 4. 配置仿真 | [ ] PASS / [ ] FAIL | |
| 5. 运行仿真 | [ ] PASS / [ ] FAIL | |
| 6. 查看结果-图表 | [ ] PASS / [ ] FAIL | |
| 7. 查看结果-数据 | [ ] PASS / [ ] FAIL | |
| 8. 导出功能 | [ ] PASS / [ ] FAIL | |
| 9. 错误处理 | [ ] PASS / [ ] FAIL | |
| 10. 完整工作流 | [ ] PASS / [ ] FAIL | |

**总计**: ___/10 通过

### 发现的问题

1. **问题描述**: _______________________________
   - 严重程度: [ ] 高 / [ ] 中 / [ ] 低
   - 复现步骤: _______________________________
   - 截图: _______________________________

2. **问题描述**: _______________________________
   - 严重程度: [ ] 高 / [ ] 中 / [ ] 低
   - 复现步骤: _______________________________
   - 截图: _______________________________

3. **问题描述**: _______________________________
   - 严重程度: [ ] 高 / [ ] 中 / [ ] 低
   - 复现步骤: _______________________________
   - 截图: _______________________________

### 改进建议

1. _______________________________
2. _______________________________
3. _______________________________

### 总体评价

- UI设计: [ ] 优秀 / [ ] 良好 / [ ] 一般 / [ ] 较差
- 功能完整性: [ ] 优秀 / [ ] 良好 / [ ] 一般 / [ ] 较差
- 易用性: [ ] 优秀 / [ ] 良好 / [ ] 一般 / [ ] 较差
- 性能: [ ] 优秀 / [ ] 良好 / [ ] 一般 / [ ] 较差
- 稳定性: [ ] 优秀 / [ ] 良好 / [ ] 一般 / [ ] 较差

**推荐度**: [ ] 强烈推荐 / [ ] 推荐 / [ ] 一般 / [ ] 不推荐

**整体评分**: ___/100

---

## 🔧 故障排查

### 问题1: 服务无法启动

**症状**: 端口被占用或服务报错

**解决方案**:
```bash
# 检查端口占用
netstat -ano | findstr "8000"
netstat -ano | findstr "5173"

# 停止占用进程
taskkill /PID <进程ID> /F

# 重新启动服务
```

### 问题2: 页面白屏

**症状**: 浏览器显示空白页

**解决方案**:
1. 按F12查看控制台错误
2. 确认前端服务正在运行
3. 清除浏览器缓存 (Ctrl + Shift + Delete)
4. 刷新页面 (Ctrl + F5)

### 问题3: 仿真失败

**症状**: 点击运行后报错

**解决方案**:
1. 检查输入参数是否合理
2. 查看浏览器控制台的Network标签
3. 确认后端API正常运行
4. 检查后端日志输出

### 问题4: Selenium无法运行

**症状**: 自动化测试失败

**解决方案**:
```bash
# 安装依赖
pip install selenium webdriver-manager requests

# 更新Chrome浏览器到最新版本

# 手动下载ChromeDriver
# 放到系统PATH目录
```

---

## 📁 输出文件清单

测试完成后，应该有以下文件：

### 截图文件（至少10张）
```
web_test_screenshots/
├── 01_homepage.png
├── 02_model_editor_empty.png
├── 02_model_editor_filled.png
├── 03_add_structure_button.png
├── 03_add_structure_dialog.png
├── 03_add_structure_complete.png
├── 04_simulation_config.png
├── 05_simulation_running.png
├── 05_simulation_complete.png
├── 06_result_profile.png
├── 06_result_flow.png
├── 06_result_interaction.png
├── 07_result_data_table.png
├── 08_export_dialog.png
├── 08_export_success.png
├── 09_error_validation.png
├── 09_error_simulation.png
├── 10_complete_workflow.png
└── test_results.json (如果使用自动化)
```

### 测试报告
```
- WEB_TEST_EXECUTION_GUIDE.md (本文档)
- web_test_screenshots/test_checklist.txt (测试清单)
- web_test_screenshots/test_results.json (自动化结果)
```

---

## ✅ 完成后的步骤

1. **整理截图**
   - 确认所有截图都已保存
   - 检查截图质量和清晰度
   - 重命名不规范的文件

2. **填写测试报告**
   - 完成上面的"测试结果记录"部分
   - 记录所有发现的问题
   - 提供改进建议

3. **更新最终报告**
   - 编辑 `FINAL_TEST_REPORT_2025-11-12.md`
   - 更新Web测试部分的状态
   - 添加测试结论

4. **提交测试成果**
   - 将所有截图和报告整理到一个目录
   - 创建测试总结文档
   - 分享给团队审阅

---

## 📞 需要帮助？

如果遇到问题，请参考：
- `COMPREHENSIVE_TEST_PLAN.md` - 完整测试方案
- `TEST_EXECUTION_SUMMARY.md` - 执行总结
- `FINAL_TEST_REPORT_2025-11-12.md` - 最终报告
- `web/README.md` - Web系统文档

---

**祝测试顺利！** 🎉

如果有任何问题或需要协助，请随时联系开发团队。







