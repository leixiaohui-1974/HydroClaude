# HydroClaude 项目深度全面测试方案
**制定日期**: 2025-11-12
**版本**: 1.0

---

## 📋 测试目标

### 主要目标
1. **后台算法测试**: 验证所有核心算法和求解器的正确性
2. **Web界面测试**: 验证前后端集成和所有功能模块的可用性
3. **端到端测试**: 完整工作流的验证
4. **性能测试**: 确保系统响应时间和计算效率
5. **兼容性测试**: 验证浏览器兼容性

### 测试范围
- ✅ 核心求解器（GodunvFVMSolver, HydrostaticCanalSolver, Preissmann）
- ✅ 水工结构（闸门、堰、泵站）
- ✅ Web API接口
- ✅ 前端UI组件
- ✅ 数据库集成
- ✅ 可视化功能
- ✅ 文件导入导出

---

## 🏗️ 测试架构

### Phase 1: 后台算法测试（预计30分钟）
```
├── 1.1 核心求解器测试
│   ├── GodunvFVMSolver (非恒定流)
│   ├── HydrostaticCanalSolver (稳态流)
│   └── Preissmann (非恒定流)
├── 1.2 水工结构测试
│   ├── 闸门流量计算
│   ├── 堰流量计算
│   └── 边界条件处理
├── 1.3 水力学工具测试
│   ├── 均匀流计算
│   ├── 临界水深计算
│   └── Froude数计算
└── 1.4 验证工具测试
    ├── ResultValidator
    └── 流量守恒验证
```

### Phase 2: Web后端测试（预计20分钟）
```
├── 2.1 API服务测试
│   ├── 健康检查接口
│   ├── 引擎信息接口
│   └── CORS配置验证
├── 2.2 仿真API测试
│   ├── 创建仿真
│   ├── 运行仿真
│   ├── 查询结果
│   └── 删除仿真
├── 2.3 数据库集成测试
│   ├── 模型保存
│   ├── 模型读取
│   └── 数据持久化
└── 2.4 异常处理测试
    ├── 无效输入
    ├── 边界情况
    └── 错误恢复
```

### Phase 3: Web前端测试（预计25分钟）
```
├── 3.1 页面加载测试
│   ├── 首页加载
│   ├── 资源加载
│   └── 样式渲染
├── 3.2 功能模块测试
│   ├── 模型编辑器
│   │   ├── 参数输入
│   │   ├── 结构添加
│   │   └── 配置保存
│   ├── 仿真运行
│   │   ├── 参数配置
│   │   ├── 开始仿真
│   │   └── 进度显示
│   ├── 结果可视化
│   │   ├── 图表渲染
│   │   ├── 数据展示
│   │   └── 交互功能
│   └── 数据管理
│       ├── 导入配置
│       ├── 导出结果
│       └── 历史记录
├── 3.3 UI交互测试
│   ├── 按钮点击
│   ├── 表单验证
│   ├── 导航切换
│   └── 响应式布局
└── 3.4 错误处理测试
    ├── 网络错误提示
    ├── 验证错误提示
    └── 用户友好提示
```

### Phase 4: 端到端集成测试（预计15分钟）
```
└── 4.1 完整工作流
    ├── 场景1: 基础渠道流动
    │   ├── 创建模型
    │   ├── 运行仿真
    │   ├── 查看结果
    │   └── 导出数据
    ├── 场景2: 含闸门的渠道
    │   ├── 添加闸门结构
    │   ├── 配置开度
    │   ├── 运行仿真
    │   └── 验证流量
    └── 场景3: 非恒定流
        ├── 配置时变边界
        ├── 运行动态仿真
        ├── 查看演化过程
        └── 分析结果
```

---

## 🔧 测试工具和环境

### 测试工具
- **Python测试**: pytest, unittest
- **Web API测试**: httpx, requests
- **浏览器测试**: Selenium WebDriver (Chrome)
- **截图工具**: selenium screenshot
- **性能监控**: time, psutil

### 环境要求
- Python 3.8+
- Node.js 16+
- Chrome浏览器
- 后端服务: http://localhost:8000
- 前端服务: http://localhost:5173

---

## 📝 测试用例清单

### 1. 后台算法测试用例

#### 1.1 GodunvFVMSolver测试
```python
测试用例 1.1.1: 静止水体测试
- 输入: h=10m (均匀), Q=0
- 预期: 质量误差 < 0.001%, 水深保持10m
- 优先级: 高

测试用例 1.1.2: Dam Break测试
- 输入: h_left=10m, h_right=1m
- 预期: 质量误差 < 1%, 波前位置误差 < 20%
- 优先级: 高

测试用例 1.1.3: 稳态均匀流测试
- 输入: Q=50m³/s, S0=0.001, n=0.025
- 预期: 水深误差 < 1%, 流量误差 < 0.1%
- 优先级: 高
```

#### 1.2 HydrostaticCanalSolver测试
```python
测试用例 1.2.1: 简单渠道稳态流
- 输入: L=10km, Q=10m³/s, S0=0.0005
- 预期: 流量误差 < 0.000001%, 迭代次数 < 5
- 优先级: 高

测试用例 1.2.2: 含单闸门流动
- 输入: 闸门位置5km, 开度5m
- 预期: 流量误差 < 0.01%, 上下游水深跃升合理
- 优先级: 高

测试用例 1.2.3: 多结构串联
- 输入: 3个闸门串联
- 预期: 流量误差 < 0.01%, 收敛稳定
- 优先级: 中
```

#### 1.3 Preissmann求解器测试
```python
测试用例 1.3.1: 非恒定流演化
- 输入: 初始h=2m, 上游Q=20m³/s变化
- 预期: 质量误差 < 40%, 稳定收敛
- 优先级: 中

测试用例 1.3.2: 边界条件测试
- 输入: 时变上游流量
- 预期: 边界处理正确，无振荡
- 优先级: 中
```

### 2. Web后端测试用例

#### 2.1 健康检查
```python
测试用例 2.1.1: GET /health
- 预期: status_code=200, status="healthy"
- 优先级: 高
```

#### 2.2 仿真API
```python
测试用例 2.2.1: POST /api/v1/simulations/run
- 输入: 基础渠道配置
- 预期: 返回simulation_id, 结果正确
- 优先级: 高

测试用例 2.2.2: GET /api/v1/simulations/{id}
- 预期: 返回完整仿真结果
- 优先级: 高

测试用例 2.2.3: 异常输入处理
- 输入: 无效参数
- 预期: 返回400错误，错误信息清晰
- 优先级: 中
```

### 3. Web前端测试用例

#### 3.1 页面加载
```python
测试用例 3.1.1: 首页加载
- 操作: 访问 http://localhost:5173
- 预期: 页面完整加载，无404错误
- 截图: homepage.png
- 优先级: 高
```

#### 3.2 模型编辑器
```python
测试用例 3.2.1: 参数输入
- 操作: 输入渠道长度、宽度等参数
- 预期: 输入框可用，验证正确
- 截图: model_editor.png
- 优先级: 高

测试用例 3.2.2: 添加闸门
- 操作: 点击"添加闸门"按钮
- 预期: 闸门表单出现，可输入参数
- 截图: add_gate.png
- 优先级: 高
```

#### 3.3 仿真运行
```python
测试用例 3.3.1: 开始仿真
- 操作: 点击"运行仿真"按钮
- 预期: 显示进度条，最终显示成功
- 截图: simulation_running.png, simulation_success.png
- 优先级: 高
```

#### 3.4 结果可视化
```python
测试用例 3.4.1: 水深剖面图
- 预期: Plotly图表正确渲染，交互功能正常
- 截图: result_profile.png
- 优先级: 高

测试用例 3.4.2: 流量分布图
- 预期: 图表显示流量分布，数值正确
- 截图: result_flow.png
- 优先级: 中
```

---

## 🚀 测试执行计划

### 阶段1: 环境准备（5分钟）
```bash
# 1. 检查Python环境
python --version
pip list | grep -E "numpy|scipy|matplotlib"

# 2. 检查Node.js环境
node --version
npm --version

# 3. 安装测试依赖
pip install pytest selenium webdriver-manager

# 4. 检查Chrome浏览器
google-chrome --version
```

### 阶段2: 后台算法测试（30分钟）
```bash
# 1. 运行核心求解器测试
pytest tests/test_solvers/ -v --tb=short

# 2. 运行水工结构测试
pytest tests/test_network/ -v --tb=short

# 3. 运行示例脚本验证
python run_example_tests.py

# 4. 生成测试报告
pytest tests/ --html=backend_test_report.html
```

### 阶段3: Web服务测试（45分钟）
```bash
# 1. 启动服务
cd web
./start_servers.sh

# 2. 等待服务就绪（15秒）
sleep 15

# 3. 运行后端API测试
python web/backend/tests/test_cases.py

# 4. 运行前端自动化测试（包含截图）
python comprehensive_web_test_with_screenshots.py

# 5. 生成完整测试报告
```

### 阶段4: 报告生成（5分钟）
```bash
# 1. 汇总所有测试结果
python generate_comprehensive_report.py

# 2. 生成可视化报告
python visualize_test_results.py

# 3. 打包测试截图
tar -czf test_screenshots.tar.gz screenshots/
```

---

## 📊 测试验收标准

### 后台算法
- ✅ 所有核心测试用例通过率 ≥ 95%
- ✅ GodunvFVMSolver质量误差 < 1%
- ✅ HydrostaticCanalSolver流量误差 < 0.01%
- ✅ 无严重性能退化（与基准对比 < 10%）

### Web后端
- ✅ 所有API端点响应正常（200或预期状态码）
- ✅ 仿真API功能完整可用
- ✅ 数据库操作无错误
- ✅ 异常处理机制有效

### Web前端
- ✅ 所有页面正常加载（无白屏、无404）
- ✅ 核心功能模块可用（编辑、运行、查看）
- ✅ 至少10个关键截图验证UI正确
- ✅ 无JavaScript控制台错误（除警告外）

### 端到端
- ✅ 至少3个完整工作流成功执行
- ✅ 数据一致性验证通过
- ✅ 用户体验流畅（无卡顿、无崩溃）

---

## 🐛 故障排查指南

### 后台测试失败
```bash
# 1. 检查依赖
pip install -r requirements.txt

# 2. 检查路径
python -c "import sys; print(sys.path)"

# 3. 运行单个测试调试
pytest tests/test_xxx.py -v -s
```

### Web服务启动失败
```bash
# 1. 检查端口占用
lsof -i :8000
lsof -i :5173

# 2. 查看日志
tail -f /tmp/hydroclaude_backend.log
tail -f /tmp/hydroclaude_frontend.log

# 3. 重启服务
./stop_servers.sh
./start_servers.sh
```

### 浏览器测试失败
```bash
# 1. 检查Chrome驱动
python -c "from selenium import webdriver; webdriver.Chrome()"

# 2. 手动验证服务
curl http://localhost:8000/health
curl http://localhost:5173

# 3. 降级到手动测试
# 打开浏览器手动访问并截图
```

---

## 📂 测试输出文件

### 测试报告
```
├── COMPREHENSIVE_TEST_REPORT.md          # 综合测试报告
├── backend_test_report.html              # 后台测试HTML报告
├── backend_test_report.json              # 后台测试JSON数据
├── web_test_report.json                  # Web测试JSON数据
└── test_summary.txt                      # 测试摘要
```

### 测试截图
```
screenshots/
├── 01_homepage.png                       # 首页
├── 02_model_editor_empty.png            # 空模型编辑器
├── 03_model_editor_filled.png           # 填充后的编辑器
├── 04_add_gate_dialog.png               # 添加闸门对话框
├── 05_simulation_config.png             # 仿真配置
├── 06_simulation_running.png            # 仿真运行中
├── 07_simulation_success.png            # 仿真成功
├── 08_result_profile.png                # 结果剖面图
├── 09_result_flow.png                   # 流量分布图
├── 10_result_data_table.png             # 结果数据表
├── 11_export_dialog.png                 # 导出对话框
└── 12_error_handling.png                # 错误处理示例
```

### 测试数据
```
test_data/
├── test_config_1.json                    # 测试配置1
├── test_config_2.json                    # 测试配置2
├── test_results_1.json                   # 测试结果1
└── performance_metrics.json              # 性能指标
```

---

## 🔍 测试检查清单

### 测试前检查
- [ ] Python环境正常（3.8+）
- [ ] Node.js环境正常（16+）
- [ ] Chrome浏览器已安装
- [ ] 项目依赖已安装
- [ ] 端口8000和5173未被占用
- [ ] 测试配置文件准备完毕

### 测试中检查
- [ ] 后台所有测试用例执行完成
- [ ] Web服务成功启动
- [ ] 浏览器自动化测试运行
- [ ] 截图自动保存
- [ ] 日志文件正常记录

### 测试后检查
- [ ] 测试报告生成完整
- [ ] 截图文件齐全（≥10张）
- [ ] 通过率达标（≥95%）
- [ ] 关键功能验证通过
- [ ] 性能指标正常
- [ ] 错误已记录并分类

---

## 📈 测试指标

### 定量指标
- **测试覆盖率**: 目标 ≥ 85%
- **通过率**: 目标 ≥ 95%
- **平均响应时间**: 目标 < 2s
- **仿真计算时间**: 目标 < 30s（基础场景）

### 定性指标
- **算法正确性**: 流量误差、质量守恒
- **UI易用性**: 操作流畅性、提示清晰度
- **错误处理**: 友好提示、恢复能力
- **文档完整性**: 测试报告、截图说明

---

## 🎯 测试优先级

### P0 - 必须通过（阻塞发布）
- GodunvFVMSolver核心功能
- HydrostaticCanalSolver稳态求解
- Web API基础功能
- 前端页面加载
- 仿真运行流程

### P1 - 应该通过（影响体验）
- 水工结构计算
- 结果可视化
- 数据导入导出
- 错误提示

### P2 - 可以通过（增强功能）
- 高级求解器功能
- 复杂场景测试
- 性能优化验证
- UI美化

---

## 📝 测试执行记录

### 执行信息
- **执行人**: [待填写]
- **执行日期**: [待填写]
- **执行环境**: [待填写]
- **Python版本**: [待填写]
- **Node.js版本**: [待填写]

### 执行结果
- **后台测试**: [通过/失败]
- **Web后端测试**: [通过/失败]
- **Web前端测试**: [通过/失败]
- **端到端测试**: [通过/失败]

### 问题记录
| 序号 | 问题描述 | 严重程度 | 状态 | 备注 |
|------|---------|---------|------|------|
| 1    |         |         |      |      |
| 2    |         |         |      |      |

---

## ✅ 下一步行动

1. **立即执行**: 运行自动化测试脚本
2. **收集结果**: 汇总所有测试输出
3. **分析问题**: 对失败用例进行根因分析
4. **生成报告**: 创建完整的测试报告文档
5. **展示演示**: 准备测试结果演示材料

---

**文档维护**: HydroClaude开发团队  
**最后更新**: 2025-11-12  
**版本**: 1.0







