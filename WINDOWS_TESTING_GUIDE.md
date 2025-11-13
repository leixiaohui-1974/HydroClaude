# HydroClaude Windows中文环境测试指南

## 📋 概述

本指南提供在Windows中文环境下对HydroClaude进行全面测试的步骤和方法。

**测试范围:**
1. ✅ 所有Examples模拟案例后台运行测试
2. ✅ Web系统端到端功能测试
3. ✅ 截图验证和问题修复

**测试环境要求:**
- 操作系统: Windows 10/11 (中文环境)
- Python: 3.9+ 
- Node.js: 18+ (用于前端)
- Chrome浏览器 + Chromedriver
- 所需Python包: numpy, matplotlib, selenium等

---

## 🚀 第一部分：环境准备

### 1.1 检查Python环境

```cmd
python --version
python -m pip --version
```

应显示 Python 3.9 或更高版本。

### 1.2 安装依赖包

```cmd
cd HydroClaude目录

# 安装核心依赖
pip install -r requirements.txt

# 安装测试依赖
pip install selenium
```

### 1.3 检查Chrome和Chromedriver

1. **安装Chrome浏览器**
   - 下载: https://www.google.com/chrome/
   - 安装后记下版本号（帮助 -> 关于Google Chrome）

2. **安装Chromedriver**
   - 下载: https://chromedriver.chromium.org/downloads
   - 选择与Chrome版本匹配的驱动
   - 解压后将`chromedriver.exe`放到PATH目录，或放到项目根目录

3. **验证安装**
   ```cmd
   chromedriver --version
   ```

---

## 📊 第二部分：后台模拟案例测试

### 2.1 快速测试（推荐先执行）

测试少量案例以验证环境：

```cmd
python comprehensive_examples_test.py --categories basic --max-tests 5
```

**预期输出:**
```
========================================
  发现测试脚本
========================================

发现测试脚本总数: 40
  - basic: 15 个脚本
  - gate_pump: 8 个脚本
  - advanced: 10 个脚本
  - special: 7 个脚本

========================================
  开始全面测试
========================================
开始时间: 2025-11-13 10:30:00
...
```

### 2.2 完整测试

测试所有案例（耗时较长，建议后台运行）：

```cmd
python comprehensive_examples_test.py --categories all
```

**参数说明:**
- `--categories`: 测试类别
  - `basic`: 基础明渠案例
  - `advanced`: 高级案例
  - `gate_pump`: 闸门泵站案例
  - `special`: 特殊案例
  - `all`: 所有案例（默认）

- `--max-tests`: 最大测试数量（用于快速验证）
- `--timeout`: 单个测试超时（秒，默认300）

**示例:**
```cmd
# 只测试基础案例
python comprehensive_examples_test.py --categories basic

# 只测试前10个案例
python comprehensive_examples_test.py --max-tests 10

# 延长超时时间到10分钟
python comprehensive_examples_test.py --timeout 600
```

### 2.3 查看测试结果

测试完成后，结果保存在：
```
test_results/examples_test_results_YYYYMMDD_HHMMSS.json
```

结果包含：
- ✅ 通过的案例列表
- ❌ 失败的案例及错误信息
- ⏱️ 每个案例的执行时间
- 📊 总体统计和成功率

---

## 🌐 第三部分：Web端到端测试

### 3.1 启动服务

**终端1 - 启动后端:**
```cmd
cd web\backend
python -m uvicorn api_gateway.main:app --host 0.0.0.0 --port 8000 --reload
```

**终端2 - 启动前端:**
```cmd
cd web\frontend
npm install    # 首次运行
npm run dev
```

等待服务启动完成：
- 后端: http://localhost:8000
- 前端: http://localhost:5173

### 3.2 运行Web测试

**新开终端3:**
```cmd
cd HydroClaude根目录
python comprehensive_web_e2e_test.py
```

**测试流程:**
1. 自动打开Chrome浏览器
2. 访问 http://localhost:5173
3. 依次测试各个功能模块
4. 自动截图记录
5. 检查控制台错误
6. 生成测试报告

### 3.3 测试内容

测试脚本会执行以下7项测试：

| 测试项 | 说明 | 验证内容 |
|--------|------|----------|
| 01 | 首页加载 | 页面能否正常打开 |
| 02 | 建模工作台 | 组件面板、工具栏 |
| 03 | 仿真管理工作台 | 标签切换、页面加载 |
| 04 | 仿真配置表单 | 表单填写、参数修改 |
| 05 | 运行仿真 | 提交仿真、查看结果 |
| 06 | UI元素交互 | 按钮点击、标签切换 |
| 07 | 控制台错误 | JavaScript错误检查 |

### 3.4 查看测试结果

**截图位置:**
```
web_test_screenshots_final/
├── 01_homepage_HHMMSS.png
├── 02_modeling_initial_HHMMSS.png
├── 03_simulation_workspace_HHMMSS.png
├── ...
└── test_results_YYYYMMDD_HHMMSS.json
```

**结果JSON:**
```json
{
  "test_time": "2025-11-13T10:30:00",
  "total_tests": 7,
  "total_screenshots": 15,
  "results": [
    {
      "test_id": "01",
      "name": "首页加载",
      "status": "passed",
      "duration": 3.2,
      "screenshots": ["..."],
      "notes": ["页面标题: HydroClaude Web"]
    },
    ...
  ]
}
```

---

## 🔧 第四部分：问题修复

### 4.1 常见问题

#### 问题1: GBK编码错误
```
UnicodeEncodeError: 'gbk' codec can't encode character '\u1f680'
```

**原因:** Windows中文环境下，默认使用GBK编码，无法显示emoji等特殊字符。

**解决方案:**
1. 测试脚本已自动处理（使用UTF-8输出）
2. 后端代码使用了output_suppressor抑制输出
3. 如仍出现问题，设置环境变量：
   ```cmd
   set PYTHONIOENCODING=utf-8
   set PYTHONUTF8=1
   ```

#### 问题2: Chromedriver版本不匹配
```
SessionNotCreatedException: Chrome version mismatch
```

**解决方案:**
1. 检查Chrome版本: 帮助 -> 关于Google Chrome
2. 下载匹配版本的chromedriver
3. 或使用webdriver-manager自动管理：
   ```cmd
   pip install webdriver-manager
   ```

#### 问题3: 端口被占用
```
OSError: [WinError 10048] 通常每个套接字地址只允许使用一次
```

**解决方案:**
```cmd
# 查看端口占用
netstat -ano | findstr :8000
netstat -ano | findstr :5173

# 结束进程
taskkill /PID 进程ID /F
```

#### 问题4: 模块导入失败
```
ModuleNotFoundError: No module named 'numpy'
```

**解决方案:**
```cmd
pip install numpy matplotlib scipy pandas
```

### 4.2 已知的后端问题

根据之前的测试，发现以下问题：

**仿真提交返回错误**
- 现象: 点击"运行仿真"后显示"提交失败: [object Object]"
- 原因: 后端异步任务执行时出现错误
- 建议: 查看uvicorn控制台输出的详细错误信息

---

## 📈 第五部分：测试报告

### 5.1 生成测试报告

测试完成后，可以查看以下文件：

**后台测试结果:**
```
test_results/examples_test_results_YYYYMMDD_HHMMSS.json
```

**Web测试结果:**
```
web_test_screenshots_final/test_results_YYYYMMDD_HHMMSS.json
```

### 5.2 阅读测试报告

测试报告包含：

1. **测试概况**
   - 测试时间、环境信息
   - 总测试数、通过率

2. **详细结果**
   - 每个测试的状态（passed/failed/timeout）
   - 执行时间
   - 错误信息（如有）

3. **截图证据**（Web测试）
   - 每个步骤的界面截图
   - 错误发生时的界面状态

### 5.3 评估标准

**后台测试成功标准:**
- ✅ 通过率 > 90%
- ✅ 无critical错误
- ✅ 平均执行时间合理

**Web测试成功标准:**
- ✅ 所有页面正常加载
- ✅ 主要功能可用
- ✅ 无严重JavaScript错误
- ✅ UI响应流畅

---

## 📝 第六部分：完整测试流程

### 推荐的测试顺序

#### 第1步：环境验证（5分钟）
```cmd
# 1. 检查Python
python --version

# 2. 安装依赖
pip install -r requirements.txt
pip install selenium

# 3. 验证chromedriver
chromedriver --version
```

#### 第2步：快速后台测试（10-15分钟）
```cmd
# 测试5个基础案例
python comprehensive_examples_test.py --categories basic --max-tests 5
```

#### 第3步：启动Web服务（2分钟）
```cmd
# 终端1: 后端
cd web\backend
python -m uvicorn api_gateway.main:app --port 8000

# 终端2: 前端  
cd web\frontend
npm run dev
```

#### 第4步：Web功能测试（5-10分钟）
```cmd
# 终端3: 自动化测试
python comprehensive_web_e2e_test.py
```

#### 第5步：完整后台测试（30-60分钟，可选）
```cmd
# 测试所有案例
python comprehensive_examples_test.py --categories all
```

#### 第6步：查看结果和生成报告（5分钟）
- 查看 `test_results/` 目录下的JSON文件
- 查看 `web_test_screenshots_final/` 目录下的截图
- 阅读测试总结

---

## ✅ 成功标准

### 后台测试通过标准
- [ ] 基础案例通过率 ≥ 95%
- [ ] 高级案例通过率 ≥ 85%
- [ ] 无critical级别错误
- [ ] 所有v2版本脚本通过

### Web测试通过标准
- [ ] 首页正常加载（< 5秒）
- [ ] 建模工作台UI完整
- [ ] 仿真管理界面正常
- [ ] 表单可编辑和提交
- [ ] 无严重JavaScript错误（< 5个）
- [ ] 截图清晰完整（≥ 10张）

---

## 🆘 故障排除

### 测试脚本无法运行
1. 检查Python版本和依赖
2. 确认工作目录正确
3. 查看命令行输出的错误信息

### 浏览器测试失败
1. 确认Chrome和chromedriver版本匹配
2. 检查服务是否正常运行
3. 尝试手动访问 http://localhost:5173

### 案例测试超时
1. 增加超时时间：`--timeout 600`
2. 检查案例是否需要大量计算
3. 减少测试数量：`--max-tests 10`

### 编码错误（GBK）
1. 设置环境变量
   ```cmd
   set PYTHONIOENCODING=utf-8
   set PYTHONUTF8=1
   ```
2. 测试脚本已自动处理
3. 检查是否有中文路径问题

---

## 📞 技术支持

**遇到问题？**
1. 查看本指南的"问题修复"章节
2. 检查测试输出的详细错误信息
3. 查看生成的JSON结果文件

**提交Bug时请提供：**
- 操作系统版本
- Python版本
- 完整的错误信息
- 测试结果JSON文件
- 截图（如适用）

---

## 🎯 总结

使用本指南，您可以：
1. ✅ 在Windows中文环境下全面测试HydroClaude
2. ✅ 自动运行所有Examples案例
3. ✅ 使用真实浏览器测试Web系统
4. ✅ 生成详细的测试报告和截图
5. ✅ 快速发现和定位问题

**预计测试时间:**
- 快速测试: 20-30分钟
- 完整测试: 1-2小时

**生成产物:**
- ✅ Examples测试结果JSON
- ✅ Web测试结果JSON
- ✅ 10-30张UI截图
- ✅ 详细的错误日志

---

**最后更新:** 2025-11-13  
**版本:** 1.0  
**适用系统:** Windows 10/11 中文环境
