# 📋 配置文件使用指南

**版本**: 2.2.0  
**日期**: 2025-10-27

---

## 🎯 快速开始

### 3行代码完成模拟！

```python
from config import HydraulicModelConfig

config = HydraulicModelConfig("config/examples/simple_canal.yaml")
result = config.run_simulation()
```

就这么简单！

---

## 📂 配置文件格式

### 完整示例

```yaml
# 1. 渠道几何参数（必需）
canal:
  length: 10000.0       # 渠道长度 (m)
  width: 10.0           # 渠道宽度 (m)
  slope: 0.001          # 渠底坡度（无量纲）
  manning: 0.025        # Manning糙率系数

# 2. 网格设置（可选）
mesh:
  n_cells: 200          # 单元数（默认200）
  
  # 局部加密（可选）
  refinement:
    - position: 5000    # 加密位置
      factor: 4         # 加密倍数
      width: 1000       # 加密区域宽度

# 3. 结构物（可选，但通常需要）
structures:
  - type: gate          # 闸门
    name: "上游闸"
    position: 2500.0
    width: 10.0
    opening: 3.0
    
  - type: pump          # 泵站
    name: "提升泵站"
    position: 5000.0
    width: 10.0
    rated_flow: 10.0
    rated_head: 5.0
    
  - type: weir          # 堰
    name: "溢流堰"
    position: 7500.0
    width: 10.0
    crest_height: 0.5

# 4. 边界条件（必需）
boundary:
  upstream:
    type: flow          # 'flow' 或 'depth'
    value: 10.0         # 常数值
    # 或使用时间序列
    # timeseries: "data/upstream.csv"
    
  downstream:
    type: depth
    value: 2.0

# 5. 求解器设置（可选）
solver:
  method: hybrid_fvfd   # wellbalanced_fdm, hybrid_fvfd, dg_high_order
  
  steady_state:         # 稳态设置
    max_iter: 2000
    tolerance: 0.01     # %
    
  unsteady:             # 非恒定流设置
    enable: false       # true启用非恒定流
    duration: 86400     # 模拟时长(s)
    dt: 1.0             # 时间步长
    cfl: 0.3
    output_interval: 600

# 6. 输出设置（可选）
output:
  directory: "results/"
  prefix: "simulation"
  formats: [csv, png]
  variables: [h, Q, u, eta]
  plots: [profile, timeseries, convergence]

# 7. 验证设置（可选）
validation:
  check_mass_conservation: true
  tolerance: 1.0e-10
```

---

## 📚 字段说明

### 1. canal（必需）

| 字段 | 类型 | 说明 | 单位 | 范围 |
|------|------|------|------|------|
| length | float | 渠道长度 | m | > 0 |
| width | float | 渠道宽度 | m | > 0 |
| slope | float | 渠底坡度 | - | ≥ 0 |
| manning | float | Manning糙率 | - | > 0 |

**典型值**：
- 混凝土渠道：n = 0.012-0.018
- 土渠（良好）：n = 0.020-0.025
- 天然河道：n = 0.025-0.035

---

### 2. structures（可选）

#### 闸门 (gate)

```yaml
- type: gate
  name: "闸门名称"
  position: 5000.0      # m
  width: 10.0           # m
  opening: 3.0          # m（开度）
```

#### 泵站 (pump)

```yaml
- type: pump
  name: "泵站名称"
  position: 5000.0
  width: 10.0
  rated_flow: 10.0      # m³/s（设计流量）
  rated_head: 5.0       # m（设计扬程）
  efficiency: 0.80      # 可选，默认0.80
```

#### 堰 (weir)

```yaml
- type: weir
  name: "堰名称"
  position: 5000.0
  width: 10.0
  crest_height: 0.5     # m（堰顶高度）
```

---

### 3. boundary（必需）

#### 流量边界

```yaml
upstream:
  type: flow
  value: 10.0           # 恒定流量
  # 或
  timeseries: "data/flow.csv"  # 时间序列
```

#### 水深边界

```yaml
downstream:
  type: depth
  value: 2.0            # 恒定水深
```

---

### 4. solver（可选）

#### 求解器选择

| method | 精度 | 速度 | 适用场景 |
|--------|------|------|---------|
| wellbalanced_fdm | 0.38% | 最快 | 快速设计 |
| hybrid_fvfd | 0.26% | 中等 | 精确模拟（推荐）|
| dg_high_order | 0.10% | 较慢 | 极端精度 |

---

## 🚀 使用示例

### 示例1：简单明渠

```python
from config import HydraulicModelConfig

config = HydraulicModelConfig("config/examples/simple_canal.yaml")
result = config.run_simulation()

print(f"流量误差: {result['error']:.2f}%")
```

### 示例2：串联闸泵群

```python
config = HydraulicModelConfig("config/examples/gate_pump_cascade.yaml")
result = config.run_simulation()

# 自动生成图表和报告
```

### 示例3：非恒定流

```python
config = HydraulicModelConfig("config/examples/unsteady_flood.yaml")
result = config.run_simulation()

# 结果包含时间序列
print(f"输出时间点: {len(result['times'])}")
```

---

## 📊 输出结果

### 稳态结果

```
results/
  ├── simulation_steady.csv      # 稳态水面线数据
  │   ├── x: 位置
  │   ├── h: 水深
  │   ├── z: 床面高程
  │   ├── eta: 水位（h+z）
  │   └── Q: 流量（如有）
  │
  └── simulation_profile.png     # 纵断面图（如启用）
```

### 非恒定流结果

```
results/
  ├── simulation_timeseries.csv  # 时间序列数据
  ├── simulation_profile_*.png   # 不同时刻的纵断面
  └── simulation_animation.gif   # 动画（如启用）
```

---

## ⚙️ 高级功能

### 网格加密

在结构物附近自动加密：

```yaml
mesh:
  n_cells: 100
  refinement:
    - position: 5000    # 在闸门处加密
      factor: 4         # 加密4倍
      width: 1000       # 加密区域±500m
```

### 时间序列边界条件

准备CSV文件：

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
    timeseries: "data/upstream_flow.csv"
```

---

## ✅ 最佳实践

### 1. 从简单开始

```
第1步：simple_canal.yaml（无结构物）
第2步：single_gate.yaml（单结构物）
第3步：gate_pump_cascade.yaml（复杂系统）
```

### 2. 合理选择求解器

```
快速设计 → wellbalanced_fdm（方案A）
精确模拟 → hybrid_fvfd（方案B，推荐）
极端精度 → dg_high_order（方案C）
```

### 3. 检查结果

```python
# 运行后检查
print(f"流量误差: {result['error']:.2f}%")
print(f"质量守恒: {result['conservation_error']:.2e}")
print(f"收敛: {'是' if result['converged'] else '否'}")
```

---

## 🐛 常见问题

### Q1: 配置文件验证失败？

**检查**：
- 必需字段是否齐全（canal, boundary）
- 数值范围是否合理
- YAML语法是否正确

### Q2: 求解不收敛？

**调整**：
```yaml
solver:
  steady_state:
    max_iter: 5000      # 增加迭代次数
    tolerance: 0.1      # 放宽容差
```

### Q3: 结果不合理？

**检查**：
- 边界条件是否合理
- 结构物参数是否正确
- Manning糙率是否合适

---

## 📞 技术支持

**文档**：
- `DEVELOPMENT_PLAN_PHASE2.md` - Phase 2完整计划
- `README.md` - 项目总览
- 各方案验证报告

**示例配置**：
```
config/examples/
  ├── simple_canal.yaml          # 最简单
  ├── single_gate.yaml           # 单结构物
  ├── gate_pump_cascade.yaml     # 串联系统
  └── unsteady_flood.yaml        # 非恒定流
```

---

**Last Updated**: 2025-10-27  
**Status**: ✅ Phase 2.2 开发中
