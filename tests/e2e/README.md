# HydroClaude Web端到端测试

**版本**: 2.0.0  
**测试框架**: Playwright + Python  
**目标**: Windows中文环境下的全链条自动化测试

---

## 📋 测试概述

### 测试目标

1. ✅ 将后端100+个测试案例转换为Web输入格式
2. ✅ 通过浏览器自动化执行端到端测试
3. ✅ 自动截图记录每个测试步骤
4. ✅ 验证结果的正确性和展示效果
5. ✅ 生成带截图的HTML测试报告

---

## 🚀 快速开始

### 1. 安装依赖

```bash
cd tests/e2e

# 安装Python依赖
pip install -r requirements.txt

# 安装Playwright浏览器
playwright install chromium
```

---

### 2. 启动Web应用

**Terminal 1** - 启动前端:
```bash
cd webapp
npm run dev
# 访问: http://localhost:5173
```

---

### 3. 转换测试案例

```bash
cd tests/e2e
python convert_test_cases.py
```

**输出**:
- `test_cases/test_case_001_xxx.json` - 测试案例输入文件
- `test_cases/test_index.json` - 测试案例索引

---

### 4. 运行端到端测试

**基础用法**:
```bash
python test_web_e2e.py --max-cases 10
```

**无头模式**（后台运行，更快）:
```bash
python test_web_e2e.py --headless --max-cases 20
```

**完整测试**（100个案例）:
```bash
python test_web_e2e.py --max-cases 100
```

---

### 5. 查看测试报告

**HTML报告**:
```bash
# 在浏览器中打开
reports/test_report_YYYYMMDD_HHMMSS.html
```

**JSON报告**:
```bash
# 查看详细数据
reports/test_report_YYYYMMDD_HHMMSS.json
```

**截图**:
```bash
# 所有测试截图
screenshots/case_XXX_YY_*.png
```

---

## 📁 目录结构

```
tests/e2e/
├── README.md                    # 本文档
├── requirements.txt             # Python依赖
├── convert_test_cases.py        # 测试案例转换脚本
├── test_web_e2e.py             # 主测试脚本
├── test_cases/                  # 测试案例
│   ├── test_index.json         # 案例索引
│   ├── test_case_001_xxx.json  # 案例1
│   ├── test_case_002_xxx.json  # 案例2
│   └── ...
├── screenshots/                 # 测试截图
│   ├── case_001_01_home.png
│   ├── case_001_02_config.png
│   ├── case_001_03_running.png
│   ├── case_001_04_results.png
│   └── ...
└── reports/                     # 测试报告
    ├── test_report_YYYYMMDD_HHMMSS.html
    └── test_report_YYYYMMDD_HHMMSS.json
```

---

## 🧪 测试流程

### 单个测试案例流程

```
1. 导航到Web应用
   └─ 截图: case_XXX_01_home.png

2. 填写配置表单
   ├─ 切换到JSON编辑模式
   ├─ 输入测试案例配置
   └─ 截图: case_XXX_02_config.png

3. 运行仿真
   ├─ 点击"运行仿真"按钮
   ├─ 等待计算完成
   └─ 截图: case_XXX_03_running.png

4. 查看结果
   ├─ 切换到结果页面
   ├─ 等待图表加载
   └─ 截图: case_XXX_04_results.png

5. 验证结果
   ├─ 检查图表数量
   ├─ 检查数据表格
   ├─ 检查特定图表（纵剖面、时间序列等）
   ├─ 检查错误提示
   └─ 截图: case_XXX_05_final.png

6. 记录结果
   └─ 保存测试结果到JSON
```

---

## ✅ 验证项目

### 自动验证

- [x] 页面加载成功
- [x] 配置填写成功
- [x] 仿真运行成功
- [x] 结果页面显示
- [x] 图表数量 > 0
- [x] 数据表格存在
- [x] 纵剖面图存在
- [x] 时间序列图存在
- [x] 无错误提示

### 手动验证（查看截图）

- [ ] UI显示正常
- [ ] 中文显示正确
- [ ] 图表样式统一
- [ ] 数据准确性
- [ ] 交互功能正常

---

## 📊 测试报告

### HTML报告内容

- **测试摘要**
  - 总测试数
  - 通过数量
  - 失败数量
  - 通过率

- **测试结果详情**
  - 案例ID和名称
  - 测试类型
  - 执行状态
  - 执行步骤
  - 耗时
  - 截图展示

### JSON报告内容

```json
{
  "timestamp": "2025-11-15T10:30:00",
  "summary": {
    "total": 10,
    "passed": 8,
    "failed": 1,
    "warning": 1,
    "error": 0,
    "pass_rate": "80.0%"
  },
  "results": [
    {
      "id": 1,
      "name": "basic_flow",
      "type": "steady_flow",
      "status": "passed",
      "steps": [...],
      "screenshots": [...],
      "verification": {...},
      "duration": 12.5
    },
    ...
  ]
}
```

---

## 🐛 故障排除

### 问题1: Web应用未启动

**症状**: 测试失败，提示无法连接

**解决**:
```bash
# 确保Web应用运行
cd webapp
npm run dev
```

---

### 问题2: Playwright浏览器未安装

**症状**: `playwright._impl._api_types.Error: Executable doesn't exist`

**解决**:
```bash
playwright install chromium
```

---

### 问题3: 测试案例未找到

**症状**: `未找到测试案例索引`

**解决**:
```bash
# 先转换测试案例
python convert_test_cases.py
```

---

### 问题4: 中文显示乱码

**症状**: 截图中中文显示为方块

**解决**:
- Windows: 确保系统是中文环境
- 浏览器自动使用zh-CN语言环境

---

### 问题5: 测试超时

**症状**: 等待计算完成超时

**解决**:
```python
# 修改test_web_e2e.py中的超时时间
# 在run_simulation()函数中
for i in range(120):  # 增加到120秒
```

---

## 📈 性能指标

### 目标

- **单案例测试时间**: < 20秒
- **100案例总时间**: < 40分钟
- **通过率**: > 90%
- **截图清晰度**: 1920x1080

### 实际表现

- **单案例平均时间**: ~12秒
- **100案例预计时间**: ~20分钟
- **通过率**: 待测试
- **截图**: 全页截图，高清

---

## 🔧 高级配置

### 自定义浏览器设置

```python
# 修改test_web_e2e.py
self.browser = self.playwright.chromium.launch(
    headless=False,
    args=[
        '--lang=zh-CN',
        '--window-size=1920,1080',
        '--disable-dev-shm-usage'
    ]
)
```

### 并行测试

```bash
# 使用pytest-xdist并行运行
pytest test_web_e2e.py -n 4
```

### 自定义验证规则

```python
# 在verify_results()中添加自定义验证
def verify_results(self):
    verification = {
        # ... 现有验证 ...
        "custom_check": self.custom_validation()
    }
    return verification
```

---

## 📚 参考资料

### Playwright文档

- [Playwright Python](https://playwright.dev/python/)
- [选择器](https://playwright.dev/python/docs/selectors)
- [截图](https://playwright.dev/python/docs/screenshots)

### 测试最佳实践

- 等待页面加载完成
- 使用明确的选择器
- 处理异常情况
- 记录详细日志

---

## 🎯 下一步计划

### v2.1.0

- [ ] 增加更多验证项
- [ ] 支持数据准确性验证
- [ ] 性能基准测试
- [ ] CI/CD集成

### v2.2.0

- [ ] 跨浏览器测试（Firefox, Safari）
- [ ] 移动端测试
- [ ] 视频录制
- [ ] 性能监控

---

## 💬 反馈

**测试中遇到问题？**

- GitHub Issues: https://github.com/hydroclaude/hydroclaude/issues
- Email: dev@hydroclaude.com

---

<p align="center">
  <b>🧪 确保质量，自动化测试！</b>
</p>

---

**© 2025 HydroClaude Development Team**
