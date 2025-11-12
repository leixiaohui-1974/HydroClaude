# HydroClaude Web 测试执行指南

> **文档版本**: v1.0  
> **更新日期**: 2025-11-12  
> **适用人员**: 测试工程师、开发人员、QA团队

---

## 📋 目录

1. [快速开始](#快速开始)
2. [环境准备](#环境准备)
3. [测试脚本说明](#测试脚本说明)
4. [执行测试](#执行测试)
5. [查看结果](#查看结果)
6. [故障排查](#故障排查)
7. [最佳实践](#最佳实践)

---

## 🚀 快速开始

### 5分钟快速测试

```bash
# 1. 进入web目录
cd /workspace/web

# 2. 启动服务（如果未启动）
./start_servers.sh

# 3. 等待服务就绪（约15秒）
sleep 15

# 4. 运行终极测试
python3 ultimate_test.py

# 5. 查看结果
cat ultimate_test_report.json | python3 -m json.tool
ls -lh ultimate_screenshots/
```

---

## 🔧 环境准备

### 系统要求

- **操作系统**: Linux / macOS / Windows
- **Python**: 3.10+
- **Node.js**: 16+
- **磁盘空间**: 至少500MB（用于依赖和截图）

### 安装依赖

#### 后端依赖

```bash
cd /workspace/web/backend/api_gateway
python3 -m pip install -r requirements.txt
```

关键依赖：
- `fastapi` - Web框架
- `uvicorn` - ASGI服务器
- `pydantic` - 数据验证
- `requests` - HTTP客户端

#### 前端依赖

```bash
cd /workspace/web/frontend
npm install
```

关键依赖：
- `react` - UI框架
- `vite` - 构建工具
- `antd` - UI组件库
- `react-flow` - 流程图

#### 测试依赖

```bash
# 安装Playwright
python3 -m pip install playwright

# 下载浏览器驱动
python3 -m playwright install chromium

# 安装系统依赖（Linux）
python3 -m playwright install-deps
```

---

## 📝 测试脚本说明

### 脚本层级

```
测试脚本层级（由简到繁）:
├─ manual_browser_test.py       [手动测试]
│  └─ 用途: 手动调试，查看控制台
│
├─ comprehensive_test.py         [基础测试]
│  └─ 用途: 快速验证基本功能
│
├─ advanced_test.py              [深度测试]
│  └─ 用途: 工作流、性能、压力测试
│
├─ detailed_visual_test.py       [详细可视化]
│  └─ 用途: 详细的UI和内容验证
│
├─ final_visual_verification.py [最终验证]
│  └─ 用途: 修复后的完整验证
│
└─ ultimate_test.py              [终极测试] ⭐推荐
   └─ 用途: 最全面的测试套件
```

### 各脚本详解

#### 1. `ultimate_test.py` ⭐ 推荐

**功能**: 最全面的测试套件

**测试内容**:
- ✅ 后端API全面测试（7项）
- ✅ 前端UI全面测试（12项）
- ✅ 性能测试（3项）
- ✅ 截图验证（9张）

**执行时间**: ~40秒

**输出**:
- `ultimate_test_report.json` - JSON报告
- `ultimate_screenshots/` - 截图目录

**使用方法**:
```bash
python3 ultimate_test.py
```

#### 2. `comprehensive_test.py`

**功能**: 基础功能测试

**测试内容**:
- ✅ 后端API测试（7项）
- ✅ 前端UI测试（9项）

**执行时间**: ~30秒

**使用方法**:
```bash
python3 comprehensive_test.py
```

#### 3. `advanced_test.py`

**功能**: 深度测试

**测试内容**:
- ✅ 端到端工作流（13项）
- ✅ UI交互（5项）
- ✅ 性能测试（4项）
- ✅ 压力测试（3项）
- ✅ 错误处理（3项）

**执行时间**: ~60秒

**使用方法**:
```bash
python3 advanced_test.py
```

---

## ▶️ 执行测试

### 方式1：自动化脚本（推荐）

```bash
#!/bin/bash
# 一键测试脚本

echo "=== HydroClaude Web 一键测试 ==="

# 1. 检查服务状态
echo "检查服务..."
curl -s http://127.0.0.1:8000/health > /dev/null
if [ $? -ne 0 ]; then
    echo "后端服务未运行，正在启动..."
    cd /workspace/web
    ./start_servers.sh
    sleep 15
fi

# 2. 运行测试
echo "运行测试..."
cd /workspace/web
python3 ultimate_test.py

# 3. 显示结果
echo ""
echo "=== 测试完成 ==="
echo "报告: ultimate_test_report.json"
echo "截图: ultimate_screenshots/"
```

保存为 `run_tests.sh`，然后：

```bash
chmod +x run_tests.sh
./run_tests.sh
```

### 方式2：手动执行

#### 步骤1：启动服务

```bash
cd /workspace/web

# 停止旧服务
./stop_servers.sh

# 启动新服务
./start_servers.sh

# 等待就绪
sleep 15

# 验证服务
curl http://127.0.0.1:8000/health
curl http://localhost:5174
```

#### 步骤2：运行测试

```bash
# 终极测试（推荐）
python3 ultimate_test.py

# 或者运行所有测试
python3 comprehensive_test.py
python3 advanced_test.py
python3 final_visual_verification.py
```

#### 步骤3：查看结果

```bash
# 查看JSON报告
cat ultimate_test_report.json | python3 -m json.tool

# 查看截图
ls -lh ultimate_screenshots/

# 查看所有报告
ls -lh *REPORT*.md
```

---

## 📊 查看结果

### JSON报告结构

```json
{
  "test_date": "2025-11-12T10:41:55",
  "test_type": "ultimate_comprehensive",
  "summary": {
    "total_tests": 22,
    "passed": 22,
    "failed": 0,
    "success_rate": 100.0
  },
  "details": {
    "backend": {...},
    "frontend": {...},
    "performance": {...}
  },
  "all_tests": [...],
  "screenshots": 9
}
```

### 解读测试结果

#### 成功指标

```bash
# 查看成功率
cat ultimate_test_report.json | \
  python3 -c "import sys,json; \
  d=json.load(sys.stdin); \
  print(f\"成功率: {d['summary']['success_rate']}\%\")"

# 应输出: 成功率: 100.0%
```

#### 失败分析

如果有测试失败，查看详细信息：

```python
import json

with open('ultimate_test_report.json') as f:
    report = json.load(f)

# 找出失败的测试
for test in report['all_tests']:
    if not test['passed']:
        print(f"失败测试: {test['name']}")
        print(f"详情: {test['details']}")
```

### 截图分析

```bash
# 列出所有截图
ls -lht ultimate_screenshots/*.png

# 查看特定截图（需要图像查看器）
# 建模工作台
open ultimate_screenshots/02_*modeling*.png

# 仿真管理
open ultimate_screenshots/03_*simulation*.png
```

---

## 🔍 故障排查

### 常见问题

#### 问题1：后端服务未启动

**症状**:
```
ConnectionRefusedError: [Errno 111] Connection refused
```

**解决**:
```bash
# 检查后端进程
ps aux | grep "main.py\|test_server.py"

# 重启后端
cd /workspace/web/backend/api_gateway
python3 test_server.py > /tmp/backend.log 2>&1 &

# 等待启动
sleep 5

# 验证
curl http://127.0.0.1:8000/health
```

#### 问题2：前端服务未启动

**症状**:
```
Page.goto: net::ERR_CONNECTION_REFUSED at http://localhost:5174/
```

**解决**:
```bash
# 检查前端进程
ps aux | grep vite

# 重启前端
cd /workspace/web/frontend
npm run dev > /tmp/frontend.log 2>&1 &

# 等待启动
sleep 10

# 验证
curl http://localhost:5174
```

#### 问题3：Playwright浏览器未安装

**症状**:
```
playwright._impl._api_types.Error: Executable doesn't exist
```

**解决**:
```bash
# 安装浏览器
python3 -m playwright install chromium

# 安装系统依赖（Linux）
python3 -m playwright install-deps
```

#### 问题4：截图显示相同内容

**原因**: 等待时间不足，React懒加载未完成

**解决**: 使用 `ultimate_test.py` 或 `final_visual_verification.py`，它们有足够的等待时间

#### 问题5：端口被占用

**症状**:
```
OSError: [Errno 98] Address already in use
```

**解决**:
```bash
# 查找占用端口的进程
lsof -i :8000  # 后端
lsof -i :5174  # 前端

# 杀死进程
kill -9 <PID>

# 或使用停止脚本
./stop_servers.sh
```

### 日志查看

```bash
# 后端日志
tail -f /tmp/backend_final.log

# 前端日志
tail -f /tmp/frontend_final.log

# 测试执行日志
# 测试脚本会直接输出到控制台
```

---

## 💡 最佳实践

### 测试前检查清单

```
□ 服务已启动并运行正常
□ 后端 http://127.0.0.1:8000/health 返回200
□ 前端 http://localhost:5174 可访问
□ Playwright已安装
□ 磁盘空间充足（>500MB）
□ 无其他进程占用8000和5174端口
```

### 推荐测试流程

```
开发环境测试流程:
├─ 1. 代码修改完成
├─ 2. 本地功能测试
├─ 3. 运行 comprehensive_test.py（快速验证）
├─ 4. 如通过，运行 ultimate_test.py（全面测试）
├─ 5. 查看截图验证UI
├─ 6. 提交代码
└─ 7. CI/CD自动运行测试
```

### 测试频率建议

| 测试类型 | 频率 | 时机 |
|---------|------|------|
| 基础测试 | 每次提交 | commit前 |
| 深度测试 | 每日 | 晚间构建 |
| 终极测试 | 每周 | 周五 |
| 性能测试 | 每月 | 月初 |
| 压力测试 | 每季度 | 季度初 |

### 测试环境管理

```bash
# 保持测试环境干净
# 每次测试前
./stop_servers.sh
./start_servers.sh

# 清理旧截图（可选）
rm -rf *_screenshots/

# 清理旧报告（可选）
rm -f *test_report.json
```

### CI/CD集成

#### GitHub Actions示例

```yaml
name: Web Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.12'
    
    - name: Setup Node.js
      uses: actions/setup-node@v3
      with:
        node-version: '18'
    
    - name: Install Dependencies
      run: |
        cd /workspace/web/backend/api_gateway
        pip install -r requirements.txt
        cd /workspace/web/frontend
        npm install
        pip install playwright
        playwright install chromium
        playwright install-deps
    
    - name: Start Services
      run: |
        cd /workspace/web
        ./start_servers.sh
        sleep 15
    
    - name: Run Tests
      run: |
        cd /workspace/web
        python3 ultimate_test.py
    
    - name: Upload Results
      uses: actions/upload-artifact@v3
      with:
        name: test-results
        path: |
          /workspace/web/ultimate_test_report.json
          /workspace/web/ultimate_screenshots/
```

---

## 📚 参考文档

- **API文档**: http://localhost:8000/api/docs
- **前端文档**: `/workspace/web/frontend/README.md`
- **测试报告**: `/workspace/web/FINAL_COMPREHENSIVE_REPORT.md`
- **问题修复**: `/workspace/web/ISSUE_FIX_REPORT.md`
- **浏览器测试**: `/workspace/web/BROWSER_TESTING_GUIDE.md`

---

## ❓ FAQ

### Q1: 为什么测试有时会失败？

A: 最常见的原因是服务未完全启动。建议：
- 增加等待时间（15-20秒）
- 检查服务日志
- 确认端口未被占用

### Q2: 截图为什么显示不完整？

A: 可能是懒加载未完成。解决：
- 使用 `ultimate_test.py`（已优化等待时间）
- 检查前端控制台是否有错误

### Q3: 如何只测试特定功能？

A: 可以编辑测试脚本，注释掉不需要的部分：

```python
# 在 ultimate_test.py 中
def run_all_tests(self):
    self.test_backend_comprehensive()  # 只测试后端
    # self.test_frontend_comprehensive(page)  # 注释掉前端测试
    # self.test_performance()  # 注释掉性能测试
```

### Q4: 可以在Windows上运行吗？

A: 可以，但需要：
- 安装Python 3.10+
- 安装Node.js 16+
- 使用 `python` 而不是 `python3`
- 路径分隔符改为 `\`

### Q5: 如何添加新的测试用例？

A: 在测试脚本中添加新方法：

```python
def test_my_feature(self, page):
    """测试我的新功能"""
    page.goto(self.frontend_url)
    # ... 测试逻辑 ...
    self.add_test_result("MyCategory", "MyTest", passed, "details")
```

---

## 📞 支持

如有问题，请：
1. 查看本指南的故障排查部分
2. 查看测试日志
3. 联系开发团队

---

**文档维护**: HydroClaude Development Team  
**最后更新**: 2025-11-12  
**版本**: v1.0
