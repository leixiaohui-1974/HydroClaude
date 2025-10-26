# 目录重组计划

## 🎯 核心目标

**验证各种非恒定流工况下的模拟正确性**

每个工况输出：
1. 纵剖面动态图（水位+流量）
2. 时空演化图
3. 关键位置时间序列
4. 数据文件

## 📁 新目录结构

```
example_gate_pump_cascade/
├── README.md                          # 主说明文档
├── run_all_scenarios.py               # 一键运行所有工况
│
├── scenarios/                         # 标准化工况脚本
│   ├── scenario_01_upstream_flow_step.py      # 上游流量阶跃
│   ├── scenario_02_downstream_level_step.py   # 下游水位阶跃
│   ├── scenario_03_gate_opening_step.py       # 闸门开度阶跃
│   ├── scenario_04_pump_flow_step.py          # 泵站流量阶跃
│   ├── scenario_05_combined_disturbances.py   # 组合扰动
│   └── scenario_utils.py                      # 工具函数
│
├── results_scenarios/                 # 工况结果（新）
│   ├── scenario_01/
│   │   ├── animation_water_level.gif          # 水位动画
│   │   ├── animation_flow_rate.gif            # 流量动画
│   │   ├── spatiotemporal.png                 # 时空图
│   │   ├── time_series.png                    # 时间序列
│   │   └── data.npz                           # 数据
│   ├── scenario_02/
│   ├── scenario_03/
│   ├── scenario_04/
│   ├── scenario_05/
│   └── comparison_report.md                   # 对比报告
│
├── models/                            # 泵站模型脚本
│   ├── model_original.py              # 原始模型
│   ├── model_simplified.py            # 简化模型
│   └── model_advanced.py              # 高精度模型
│
├── docs/                              # 文档归档
│   ├── pump_models/                   # 泵站模型文档
│   ├── control_strategies/            # 控制策略文档
│   ├── verification/                  # 验证报告
│   └── archive/                       # 历史文档归档
│
└── legacy/                            # 旧文件归档（不删除）
    ├── old_tests/
    ├── old_results/
    └── old_reports/
```

## 📊 标准化工况定义

### 工况1: 上游流量阶跃
```python
初始: Q_upstream = 30 m³/s
扰动: t=300s, Q_upstream → 55 m³/s
时长: 3600s
观测: 流量波传播、水位响应、泵站工作点变化
```

### 工况2: 下游水位阶跃
```python
初始: h_downstream = 2.0 m
扰动: t=300s, h_downstream → 3.5 m
时长: 3600s
观测: 回水效应、流量变化、泵站影响
```

### 工况3: 闸门开度阶跃
```python
初始: gate1_opening = 0.7 m
扰动: t=300s, gate1_opening → 1.2 m
时长: 3600s
观测: 局部水位变化、流量调节、上下游影响
```

### 工况4: 泵站流量阶跃
```python
初始: pump_rated_flow = 30 m³/s
扰动: t=300s, pump_rated_flow → 40 m³/s
时长: 3600s
观测: 泵站上游水位、流量传播、能量变化
```

### 工况5: 组合扰动
```python
t=300s: Q_upstream → 55 m³/s
t=600s: gate1_opening → 1.2 m
t=900s: h_downstream → 3.5 m
时长: 1800s
观测: 多重扰动叠加效应
```

## 🎬 标准化动画输出

每个工况生成2个动画：

### 动画1: 水位纵剖面
```
- Y轴: 水位高程（包含完整渠底）
- X轴: 距离
- 时间: 动态演化
- 显示: 水面线、渠底线、闸门位置、泵站位置
```

### 动画2: 流量纵剖面
```
- Y轴: 流量
- X轴: 距离
- 时间: 动态演化
- 显示: 流量分布、闸门/泵站位置
```

## 📝 输出规范

### 文件命名
```
scenario_XX/
  ├── animation_water_level.gif        # 水位动画
  ├── animation_flow_rate.gif          # 流量动画
  ├── spatiotemporal_water.png         # 水位时空图
  ├── spatiotemporal_flow.png          # 流量时空图
  ├── time_series_key_points.png       # 关键点时间序列
  ├── steady_state_profile.png         # 稳态纵剖面
  └── data.npz                         # 完整数据
```

### 数据格式
```python
data.npz 包含:
  - x: 空间坐标
  - time: 时间点
  - h_history: 水深历史
  - q_history: 流量历史
  - z: 渠底高程
  - gate_positions: 闸门位置
  - pump_position: 泵站位置
  - scenario_description: 工况描述
```

## 🔧 需要清理的文件

### 保留文件（核心）
```
✓ gate_pump_cascade_system.py         # 原始模型
✓ gate_pump_cascade_simplified.py     # 简化模型
✓ gate_pump_cascade_advanced.py       # 高精度模型
✓ compare_all_models.py                # 模型对比
✓ test_pump_models.py                  # 泵站测试
✓ PUMP_MODELS_DEVELOPMENT_SUMMARY.md   # 泵站开发文档
✓ PROJECT_COMPLETION_SUMMARY.md        # 项目总结
✓ MANUAL_INSPECTION_CHECKLIST.md      # 检查清单
```

### 归档文件（legacy/）
```
→ test_disturbances_simple.py
→ test_unsteady_simple.py
→ test_unsteady_complete.py
→ test_comprehensive_disturbances.py
→ analyze_*.py
→ run_*_optimized_system.py
→ generate_complete_comparison.py
→ 所有旧的MD报告（除核心文档外）
→ 所有result_场景*.png
→ control_strategies/ 整个目录
```

### 删除文件（冗余）
```
✗ config_*.yaml（已过时）
✗ *_FAILURE_*.md（失败诊断，已解决）
✗ *_BUG_*.md（Bug报告，已修复）
✗ *_ISSUE_*.md（问题报告，已解决）
```

## 📋 实施步骤

1. ✅ 创建新目录结构
2. ✅ 编写标准化工况脚本（5个）
3. ✅ 运行所有工况，生成动画
4. ✅ 创建对比报告
5. ✅ 移动旧文件到归档
6. ✅ 更新主README
7. ✅ 提交到git

## 🎯 最终效果

```bash
# 用户只需运行一个命令
python run_all_scenarios.py

# 生成清晰的输出
results_scenarios/
  ├── scenario_01/ (7个文件)
  ├── scenario_02/ (7个文件)
  ├── scenario_03/ (7个文件)
  ├── scenario_04/ (7个文件)
  ├── scenario_05/ (7个文件)
  └── comparison_report.md

# 总计：35个文件 + 1个报告
```

## ✅ 验证标准

每个工况必须：
1. ✓ 生成清晰的水位动画（渠底完整显示）
2. ✓ 生成清晰的流量动画
3. ✓ 数值稳定（无NaN、无Inf）
4. ✓ 物理合理（质量守恒、能量守恒）
5. ✓ 视觉清晰（色彩、标签、图例）

---

**预计完成时间**: 约1小时  
**预计文件数**: 35个结果文件 + 5个脚本 + 1个主文档
