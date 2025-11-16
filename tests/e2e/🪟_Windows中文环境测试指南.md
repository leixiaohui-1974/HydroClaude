# 🪟 HydroClaude Windows中文环境测试指南

**版本**: 2.0.0  
**日期**: 2025-11-15  
**状态**: ✅ 完整方案

---

## 🎯 测试目标

在**Windows 10/11 中文环境**下，对HydroClaude Web系统进行端到端测试：
- ✅ 验证**中文界面**显示正常
- ✅ 验证**中文输入**功能正常
- ✅ 验证**111个测试案例**系统功能和引擎正确性
- ✅ 生成**中文测试报告**

---

## 📋 环境要求

### 系统要求

```
操作系统:    Windows 10/11 (64位)
语言:        简体中文
显示设置:    中文界面
区域设置:    中国 (zh-CN)
时区:        UTC+8 (北京时间)
```

---

### 软件要求

```
必需软件:
  ✅ Python 3.8+
  ✅ Node.js 18+
  ✅ Git (可选)
  ✅ Chrome/Edge浏览器

Python包:
  ✅ playwright
  ✅ pytest
  ✅ pandas
  ✅ numpy

Node.js包:
  ✅ react
  ✅ vite
  ✅ ant-design
```

---

## 🚀 快速开始

### 步骤1: 环境检查

打开**Windows PowerShell**或**命令提示符 (CMD)**：

```cmd
:: 检查Python版本
python --version

:: 检查Node.js版本
node --version

:: 检查npm版本
npm --version
```

**预期输出**:
```
Python 3.8+ 
Node.js 18+
npm 9+
```

---

### 步骤2: 安装依赖

```cmd
:: 2.1 安装Python测试依赖
cd tests\e2e
pip install -r requirements.txt

:: 2.2 安装Playwright浏览器
playwright install chromium

:: 2.3 安装Web应用依赖 (如果还没装)
cd ..\..\webapp
npm install
```

**重要提示**: 确保在中文Windows环境下执行，避免编码问题。

---

### 步骤3: 启动Web应用

**打开第一个命令提示符窗口**:

```cmd
:: 进入webapp目录
cd webapp

:: 启动开发服务器
npm run dev
```

**预期输出**:
```
  VITE v4.x.x  ready in xxx ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
```

**保持此窗口打开！**

---

### 步骤4: 运行测试

**打开第二个命令提示符窗口**:

```cmd
:: 进入测试目录
cd tests\e2e

:: 方式1: 快速测试 (1个案例)
python quick_test.py

:: 方式2: 测试20个案例
python test_web_e2e.py --max-cases 20

:: 方式3: 一键完整测试 (111个案例)
run_full_test.bat 111
```

---

## 📝 一键测试脚本

### run_full_test.bat (已优化)

```batch
@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

echo ======================================================================
echo 🧪 HydroClaude Windows中文环境测试
echo ======================================================================
echo.

:: 获取参数
set MAX_CASES=%1
if "%MAX_CASES%"=="" set MAX_CASES=20

echo 配置:
echo   • 测试案例数: %MAX_CASES%个
echo   • 环境: Windows中文
echo   • 浏览器: Chromium (zh-CN)
echo.

:: 1. 检查环境
echo [1/5] 检查环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python未安装
    echo    请从 https://www.python.org/downloads/ 下载安装
    goto :error
)
echo ✅ Python已安装

:: 2. 检查Web应用
echo.
echo [2/5] 检查Web应用...
curl -s http://localhost:5173 >nul 2>&1
if errorlevel 1 (
    echo ⚠️  Web应用未运行
    echo    请在另一个窗口运行: cd webapp ^&^& npm run dev
    echo.
    choice /C YN /M "是否继续 (可能导致测试失败)"
    if errorlevel 2 goto :error
) else (
    echo ✅ Web应用运行中 (localhost:5173)
)

:: 3. 检查测试案例
echo.
echo [3/5] 检查测试案例...
if not exist "test_cases\test_index_full.json" (
    echo ❌ 测试案例索引不存在
    echo    请先运行: python convert_all_test_cases.py
    goto :error
)
echo ✅ 找到测试案例索引

:: 4. 运行测试
echo.
echo [4/5] 开始测试...
echo ======================================================================
python test_web_e2e.py --max-cases %MAX_CASES%
set TEST_EXIT=%errorlevel%

:: 5. 显示结果
echo.
echo [5/5] 测试完成
if %TEST_EXIT%==0 (
    echo ✅ 测试成功完成
) else (
    echo ⚠️  测试过程中出现错误 (退出码: %TEST_EXIT%)
)

:: 打开报告
echo.
echo 正在打开测试报告...
for /f "delims=" %%i in ('dir /b /od reports\test_report_*.html 2^>nul') do set LATEST_REPORT=%%i
if defined LATEST_REPORT (
    start "" "reports\%LATEST_REPORT%"
    echo ✅ 已打开: reports\%LATEST_REPORT%
) else (
    echo ⚠️  未找到HTML报告
)

echo.
echo ======================================================================
echo 🎉 测试流程完成
echo ======================================================================
echo.
echo 报告位置:
echo   • HTML报告: reports\test_report_*.html
echo   • JSON报告: reports\test_report_*.json
echo   • 截图: screenshots\case_*\
echo.
pause
exit /b %TEST_EXIT%

:error
echo.
echo ❌ 测试终止
pause
exit /b 1
```

---

## 🧪 测试场景

### 场景1: 快速验证 (1案例, 1分钟)

**目的**: 快速验证测试框架和环境

```cmd
cd tests\e2e
python quick_test.py
```

**验证项**:
- ✅ 浏览器能否启动 (中文环境)
- ✅ Web应用是否可访问
- ✅ 配置页面是否正常
- ✅ JSON编辑器是否工作
- ✅ 仿真是否能运行
- ✅ 结果页面是否显示
- ✅ 中文字符是否正常显示

---

### 场景2: 分类测试 (20案例, 5分钟)

**目的**: 按分类测试，验证不同类型案例

```cmd
:: 基础流动
python test_web_e2e.py --category basic_flow

:: 水工结构
python test_web_e2e.py --category structures

:: 管网系统
python test_web_e2e.py --category network
```

---

### 场景3: 完整测试 (111案例, 30分钟)

**目的**: 全面验证所有功能

```cmd
run_full_test.bat 111
```

**测试覆盖**:
- ✅ 111个测试案例
- ✅ 7大分类
- ✅ 双重验证 (UI + 计算)
- ✅ 完整截图记录
- ✅ HTML中文报告

---

## 📊 中文环境特殊验证

### 1. 中文显示验证

**验证项**:
```
✅ 页面标题显示中文
✅ 导航菜单显示中文
✅ 按钮文字显示中文
✅ 表单标签显示中文
✅ 错误提示显示中文
✅ 图表标签显示中文
✅ 数据表头显示中文
```

---

### 2. 中文输入验证

**验证项**:
```
✅ JSON编辑器支持中文注释
✅ 配置表单支持中文输入
✅ 搜索框支持中文搜索
✅ 文件名支持中文
```

---

### 3. 中文编码验证

**验证项**:
```
✅ 测试报告中文不乱码
✅ 日志文件中文正常
✅ 截图文件名中文正常
✅ JSON文件中文保存正确
```

---

## 🔧 常见问题

### 问题1: 中文乱码

**症状**: 控制台或报告显示乱码

**解决方案**:
```cmd
:: 在脚本开头添加
chcp 65001

:: 或在Python脚本中设置
import sys
sys.stdout.reconfigure(encoding='utf-8')
```

---

### 问题2: Playwright未安装

**症状**: 
```
Error: Executable doesn't exist at ...
```

**解决方案**:
```cmd
pip install playwright
playwright install chromium
```

---

### 问题3: Web应用未运行

**症状**:
```
Connection refused: localhost:5173
```

**解决方案**:
```cmd
:: 打开新的命令提示符
cd webapp
npm run dev

:: 等待显示
➜ Local: http://localhost:5173/
```

---

### 问题4: 端口被占用

**症状**:
```
Port 5173 is already in use
```

**解决方案**:
```cmd
:: 方式1: 杀掉占用进程
netstat -ano | findstr :5173
taskkill /F /PID <PID>

:: 方式2: 使用其他端口
npm run dev -- --port 5174
```

---

### 问题5: 权限问题

**症状**:
```
Access denied
Permission denied
```

**解决方案**:
- 右键以**管理员身份运行**命令提示符
- 检查防火墙设置
- 检查杀毒软件设置

---

## 📈 测试报告

### HTML报告 (中文)

**位置**: `reports\test_report_YYYYMMDD_HHMMSS.html`

**包含内容**:
```
📊 测试摘要 (中文)
  • 总计、通过、失败
  • 通过率、平均得分
  • 评级分布

📋 按分类统计 (中文)
  • 基础流动
  • 水工结构
  • 管网系统
  • ... 等7大类

🔬 水力学验证 (中文)
  • 流量守恒
  • Manning方程
  • Froude数
  • 能量方程
  • 边界条件
  • 结构水力学

🖼️ 截图展示
  • 每案例5-6张
  • 配置、运行、结果
  • 点击查看大图

📝 详细结果
  • 每个案例详情
  • 执行步骤
  • 验证结果
  • 得分和评级
```

---

### 截图目录

**位置**: `screenshots\`

**结构**:
```
screenshots\
├── case_001\
│   ├── 01_config_initial.png
│   ├── 02_json_editor.png
│   ├── 03_config_filled.png
│   ├── 04_running.png
│   ├── 05_results.png
│   └── 06_verification.png
├── case_002\
│   └── ...
└── ...
```

---

## ✅ 验证清单

### 测试前检查

- [ ] Windows 10/11 中文系统
- [ ] Python 3.8+ 已安装
- [ ] Node.js 18+ 已安装
- [ ] 依赖包已安装
- [ ] Playwright浏览器已安装
- [ ] Web应用能正常启动
- [ ] 测试案例已转换 (111个)

---

### 测试中检查

- [ ] 浏览器能自动启动
- [ ] 中文界面显示正常
- [ ] 配置页面能加载
- [ ] JSON编辑器能使用
- [ ] 仿真能成功运行
- [ ] 结果页面能显示
- [ ] 图表能正确渲染
- [ ] 截图能正常保存

---

### 测试后检查

- [ ] 测试报告已生成
- [ ] 中文内容无乱码
- [ ] 截图文件完整
- [ ] 通过率达标 (≥80%)
- [ ] 平均得分合格 (≥85分)
- [ ] 水力学验证通过
- [ ] 无严重错误

---

## 🎯 成功标准

### 必须达到

```
✅ 测试环境: Windows中文
✅ 通过率: ≥ 80%
✅ 平均得分: ≥ 85分
✅ 流量误差: < 1%
✅ 收敛成功率: 100%
✅ 中文显示: 无乱码
✅ 报告完整: HTML+JSON+截图
```

---

### 期望达到

```
✅ 通过率: ≥ 90%
✅ 平均得分: ≥ 90分
✅ A级案例: ≥ 70%
✅ 所有分类通过率: > 80%
✅ 测试速度: < 30秒/案例
```

---

## 📞 支持

### 遇到问题？

1. **查看日志**
   - `test_web_e2e.log`
   - 控制台输出
   - 浏览器开发者工具

2. **查看文档**
   - `README.md`
   - `tests/e2e/README.md`
   - 本指南

3. **查看示例**
   - `screenshots/` 目录
   - `reports/` 目录
   - 成功的测试报告

---

## 🎉 总结

### Windows中文环境测试方案

✅ **完整的测试流程**
- 环境检查
- 依赖安装
- 一键测试
- 报告生成

✅ **中文支持**
- 中文界面显示
- 中文字符编码
- 中文报告生成
- 中文截图文件名

✅ **111个测试案例**
- 7大分类
- 全面覆盖
- 双重验证
- 完整报告

✅ **易用性**
- 一键脚本
- 批处理文件
- 详细文档
- 问题排查

---

<p align="center">
  <b>━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</b>
</p>

<p align="center">
  <b>🪟 Windows中文环境测试指南</b>
</p>

<p align="center">
  <b>111个案例 | 7大分类 | 完整中文支持</b>
</p>

<p align="center">
  <i>简单 | 快速 | 可靠</i>
</p>

<p align="center">
  <b>━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</b>
</p>

---

**© 2025 HydroClaude Development Team**  
**Date: 2025-11-15**  
**Version: 2.0.0**  
**Status: ✅ Windows中文环境测试方案完成**
