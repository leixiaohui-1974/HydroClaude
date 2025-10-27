# 📖 HydroClaude完整使用指南

**目标读者**：水利工程师、研究人员  
**前置知识**：基本的Python和YAML语法  
**学习时间**：30分钟

---

## 🎯 系统概述

HydroClaude是一个**高精度、全自动化的一维明渠水力学模拟系统**。

### 核心特点

- ✅ **高精度**：流量误差0.10-0.38%（商业软件级别）
- ✅ **通用性**：支持稳态+非恒定流
- ✅ **自动化**：配置文件驱动，一键运行
- ✅ **易用性**：3行代码或1行命令完成模拟

---

## 🚀 快速开始（3分钟）

### 方式1：Python API（3行代码）

```python
from config import HydraulicModelConfig

config = HydraulicModelConfig("config/examples/simple_canal.yaml")
result = config.run_simulation()
```

### 方式2：命令行（1行命令）

```bash
python3 run_simulation.py config/examples/simple_canal.yaml
```

**完成！** 自动生成结果和图表。

---

## 📁 配置文件详解

### 最小配置（25行）

```yaml
# my_canal.yaml

canal:
  length: 10000
  width: 10
  slope: 0.001
  manning: 0.025

structures:
  - type: gate
    position: 5000
    opening: 3.0

boundary:
  upstream: {type: flow, value: 10.0}
  downstream: {type: depth, value: 2.0}

solver: {method: hybrid_fvfd}
output: {directory: "results/"}
```

### 运行

```bash
python3 run_simulation.py my_canal.yaml
```

---

## 🔧 常用场景

### 场景1：简单明渠（无结构物）

```yaml
canal: {length: 10000, width: 10, slope: 0.001, manning: 0.025}
structures: []  # 无结构物
boundary:
  upstream: {type: flow, value: 10.0}
  downstream: {type: depth, value: 2.0}
solver: {method: hybrid_fvfd}
```

**用途**：学习系统、验证均匀流

---

### 场景2：单闸门控制

```yaml
structures:
  - type: gate
    name: "控制闸"
    position: 5000
    width: 10
    opening: 3.0  # 闸门开度
```

**用途**：闸门设计、流量控制

---

### 场景3：泵站系统

```yaml
structures:
  - type: pump
    name: "提升泵站"
    position: 5000
    width: 10
    rated_flow: 10.0   # 设计流量
    rated_head: 5.0    # 设计扬程
```

**用途**：泵站设计、能耗分析

---

### 场景4：串联闸泵群（核心）

```yaml
structures:
  - {type: gate, position: 25000, opening: 3.0}
  - {type: pump, position: 50000, rated_head: 5.0}
  - {type: gate, position: 75000, opening: 2.5}
```

**用途**：复杂水网、联合调度

---

### 场景5：非恒定流（洪水）

```yaml
solver:
  method: hybrid_fvfd
  unsteady:
    enable: true
    duration: 86400    # 24小时
    output_interval: 600  # 每10分钟输出

boundary:
  upstream:
    type: flow
    timeseries: "data/flood_hydrograph.csv"
```

**用途**：洪水演进、应急响应

---

## 📊 求解器选择

### 方案A：快速设计（推荐初学者）

```yaml
solver:
  method: wellbalanced_fdm
```

**特点**：
- 精度：0.38%
- 速度：最快（~9秒/100km）
- 适合：工程设计、快速评估

---

### 方案B：精确模拟（推荐）

```yaml
solver:
  method: hybrid_fvfd
```

**特点**：
- 精度：0.26%
- 守恒：机器精度（< 1e-12）
- 适合：详细设计、精确模拟

**默认选择！**

---

### 方案C：极端精度（高级）

```yaml
solver:
  method: dg_high_order
  order: 3  # P3，四阶精度
```

**特点**：
- 精度：0.10%（最高）
- 阶数：四阶空间+时间
- 适合：学术研究、极端精度需求

---

## 🎨 结果可视化

### 自动绘图

在配置文件中启用：

```yaml
output:
  directory: "results/"
  formats: [csv, png]
  plots:
    - profile        # 纵断面图
    - flow           # 流量分布图
    - timeseries     # 时间历程（非恒定流）
    - convergence    # 收敛历史
```

### 手动绘图

```python
from visualization import ResultVisualizer

viz = ResultVisualizer(result)
viz.plot_profile("profile.png")
viz.plot_all("figures/")  # 一键生成所有图表
```

---

## 🔄 情景分析

### 批量运行情景

```python
from scenarios import ScenarioManager

# 定义情景
scenarios = {
    "基准情景": {},
    "增加泵站扬程": {"pump_head": 6.0},
    "关小闸门": {"gate_opening": 2.5},
    "增大流量": {"upstream_flow": 15.0},
}

# 批量运行
manager = ScenarioManager("config/examples/gate_pump_cascade.yaml")
results = manager.run_scenarios(scenarios)

# 自动对比
manager.compare_results(results)
manager.generate_comparison_report(results, "comparison.md")
```

**输出**：
- 自动对比表格
- 生成对比报告
- 标识最优方案

---

## ✅ 结果验证

### 检查质量指标

```python
# 运行后检查
print(f"流量误差: {result['error']:.2f}%")
# 应该 < 0.5%（方案A）或 < 0.3%（方案B）或 < 0.1%（方案C）

print(f"质量守恒: {result['conservation_error']:.2e}")
# 应该 < 1e-10

print(f"收敛: {'是' if result['converged'] else '否'}")
# 应该为True

print(f"迭代次数: {result['iterations']}")
# 应该 < 2000
```

---

## 🐛 故障排查

### 问题1：求解不收敛

**症状**：`converged: False`

**解决**：
```yaml
solver:
  steady_state:
    max_iter: 5000      # 增加迭代
    tolerance: 0.1      # 放宽容差
```

---

### 问题2：质量不守恒

**症状**：`conservation_error > 1e-8`

**检查**：
- 边界条件是否合理？
- 结构物参数是否正确？
- 使用方案B或C（本质守恒）

---

### 问题3：结果不合理

**检查**：
- Manning糙率是否合理？（0.012-0.035）
- 床面坡度是否合理？（0.0001-0.01）
- 边界条件是否物理合理？

---

## 📚 进阶使用

### 网格加密

在结构物附近自动加密：

```yaml
mesh:
  n_cells: 100
  refinement:
    - position: 5000    # 闸门位置
      factor: 4         # 加密4倍
      width: 1000       # ±500m范围
```

---

### 时间序列边界

准备CSV文件（data/flow.csv）：

```csv
time,value
0,10.0
3600,15.0
7200,12.0
10800,10.0
```

配置：

```yaml
boundary:
  upstream:
    type: flow
    timeseries: "data/flow.csv"
```

---

### 长时间模拟

```yaml
solver:
  unsteady:
    enable: true
    duration: 259200   # 72小时
    cfl: 0.3           # 自动调整dt
    output_interval: 3600  # 每小时输出
```

---

## 📖 完整示例

### 示例：设计一个串联闸泵群系统

**第1步：创建配置文件**

```yaml
# config/my_project.yaml

canal:
  length: 80000        # 80公里
  width: 12.0          # 12米宽
  slope: 0.0001        # 平坦
  manning: 0.025

structures:
  # 上游进水闸
  - type: gate
    name: "进水闸"
    position: 10000
    opening: 4.0
  
  # 中游提升泵站
  - type: pump
    name: "一级泵站"
    position: 40000
    rated_head: 5.0
  
  # 下游退水闸
  - type: gate
    name: "退水闸"
    position: 70000
    opening: 3.5

boundary:
  upstream: {type: flow, value: 15.0}      # 15 m³/s
  downstream: {type: depth, value: 2.5}    # 2.5 m

solver: {method: hybrid_fvfd}

output:
  directory: "results/my_project/"
  prefix: "design_v1"
  plots: [profile, flow, convergence]
```

**第2步：运行模拟**

```bash
python3 run_simulation.py config/my_project.yaml
```

**第3步：查看结果**

```
results/my_project/
  ├── design_v1_steady.csv         # 稳态数据
  ├── design_v1_profile.png        # 纵断面图
  ├── design_v1_flow.png           # 流量分布
  └── design_v1_convergence.png    # 收敛历史
```

**第4步：方案对比**

```python
from scenarios import ScenarioManager

scenarios = {
    "方案A：泵站5m": {"pump_head": 5.0},
    "方案B：泵站6m": {"pump_head": 6.0},
    "方案C：泵站7m": {"pump_head": 7.0},
}

manager = ScenarioManager("config/my_project.yaml")
results = manager.run_scenarios(scenarios)
manager.compare_results(results)
```

**完成！** 选择最优方案。

---

## 📞 技术支持

### 文档索引

- **快速开始**: QUICK_START.md
- **配置指南**: CONFIG_FILE_GUIDE.md
- **完整示例**: 本文档
- **技术细节**: Phase 1和Phase 2报告

### 示例配置

```
config/examples/
  ├── simple_canal.yaml          # 入门
  ├── single_gate.yaml           # 单结构物
  ├── gate_pump_cascade.yaml     # 串联系统
  └── unsteady_flood.yaml        # 非恒定流
```

### 常见问题

查看 `CONFIG_FILE_GUIDE.md` 的常见问题部分。

---

## 🎊 总结

**你现在可以**：
- ✅ 3行Python代码完成模拟
- ✅ 1行命令完成模拟
- ✅ 配置文件<100行建模
- ✅ 自动生成图表和报告
- ✅ 批量情景分析

**无需深入代码，专注工程问题！**

---

**Last Updated**: 2025-10-27  
**Status**: ✅ Ready to Use  
**Happy Simulating!** 🌊
