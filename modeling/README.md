# HydroClaude 通用建模系统

**版本**: 1.0
**作者**: Claude
**日期**: 2025-10-24

---

## 概述

HydroClaude 通用建模系统是一套**全自动化**的水力学建模工具，旨在最大限度降低建模难度，实现从配置到结果的一站式服务。

### 核心理念

> **"3行代码，完成完整建模"**

```python
from modeling.universal_modeler import UniversalModeler

modeler = UniversalModeler("config.yaml")  # 1. 加载配置
modeler.run()                               # 2. 自动运行
# 3. 完成！
```

---

## 主要功能

### 1. 自动网格生成
- ✅ **均匀网格**：指定点数或间距
- ✅ **自适应网格**：结构物附近自动加密
- ✅ **网格质量评估**：自动验证网格合理性

### 2. 自适应网格细化
- ✅ 基于梯度的细化指标
- ✅ 自动插入/移除网格点
- ✅ 多次迭代细化直至收敛

### 3. 智能算法选择
- ✅ 根据问题特征自动推荐最优算法
- ✅ CFL稳定性分析
- ✅ 精度要求匹配

### 4. 稳态初值估计
- ✅ 均匀流快速估计
- ✅ 逐渐变化流近似
- ✅ 精确稳态求解（推荐）

### 5. 多重结果验证
- ✅ 流量守恒验证
- ✅ 物理合理性检查
- ✅ 数值稳定性分析
- ✅ 结构物流量校核

### 6. 配置文件管理
- ✅ YAML格式，人类可读
- ✅ 模板自动生成
- ✅ 参数验证和错误提示

### 7. 自动化报告生成
- ✅ 纵剖面图
- ✅ 验证报告
- ✅ 数值数据导出

---

## 系统架构

```
modeling/
├── __init__.py              # 模块入口
├── config.py                # 配置管理（ModelConfig）
├── grid_generator.py        # 网格生成（GridGenerator）
├── adaptive_refiner.py      # 自适应细化（AdaptiveRefiner）
├── algorithm_selector.py    # 算法选择（AlgorithmSelector）
├── steady_estimator.py      # 稳态估计（SteadyEstimator）
├── multi_validator.py       # 多重验证（MultiValidator）
└── universal_modeler.py     # 主接口（UniversalModeler）
```

### 核心模块说明

| 模块 | 功能 | 关键方法 |
|------|------|----------|
| **ModelConfig** | 配置文件管理 | `load()`, `get_canal_params()`, `get_structures()` |
| **GridGenerator** | 网格自动生成 | `generate_uniform_grid()`, `generate_adaptive_grid()` |
| **AdaptiveRefiner** | 运行时网格细化 | `refine_grid()`, `compute_refinement_indicator()` |
| **AlgorithmSelector** | 算法智能选择 | `select_steady_solver()`, `select_unsteady_solver()` |
| **SteadyEstimator** | 初值精确估计 | `estimate_from_steady_solution()` |
| **MultiValidator** | 结果全面验证 | `run_all_validations()`, `generate_report()` |
| **UniversalModeler** | 一站式建模 | `run()` |

---

## 快速入门

### 步骤1：准备配置文件

创建 `config.yaml`：

```yaml
canal:
  length: 10000.0
  width: 10.0
  slope: 0.001
  manning_n: 0.025

grid:
  nx: 101

structures: []

boundary_conditions:
  upstream:
    type: flow
    value: 10.0
  downstream:
    type: depth
    value: 2.0

simulation:
  type: steady
  max_iterations: 5000
  convergence_tol: 0.001

output:
  directory: results
  prefix: my_simulation
  formats: [npz, png]
```

### 步骤2：编写运行脚本

创建 `run.py`：

```python
from modeling.universal_modeler import UniversalModeler

modeler = UniversalModeler("config.yaml")
modeler.run()
```

### 步骤3：运行

```bash
python run.py
```

### 步骤4：查看结果

```
results/
├── my_simulation_data.npz
├── my_simulation_profile.png
└── validation_report.txt
```

---

## 高级用法

### 1. 自适应网格

在 `config.yaml` 中启用：

```yaml
grid:
  dx_target: 200.0
  adaptive: true  # 启用自适应网格
```

### 2. 复杂结构物配置

```yaml
structures:
  - type: sluice_gate
    position: 5000.0
    opening: 1.5
    Cd: 0.6

  - type: pump_station
    position: 10000.0
    rated_flow: 30.0
    rated_head: 5.0
    min_suction_head: 2.0

  - type: weir
    position: 15000.0
    crest_height: 1.0
    Cd: 0.4
```

### 3. 分步建模（插入自定义分析）

```python
from modeling.universal_modeler import UniversalModeler

modeler = UniversalModeler("config.yaml")

# 步骤1：设置结构物
modeler.setup_structures()

# 步骤2：生成网格
x = modeler.setup_grid()

# 【自定义】分析网格质量
import matplotlib.pyplot as plt
plt.plot(x, 'o-')
plt.title("Grid Distribution")
plt.show()

# 步骤3-7：继续建模
modeler.setup_solver(x)
modeler.select_algorithm()
modeler.run_steady_simulation()
modeler.validate_results()
modeler.generate_outputs()
```

### 4. 访问中间结果

```python
modeler = UniversalModeler("config.yaml")
modeler.run()

# 访问求解器
solver = modeler.solver
print(f"水深范围: [{solver.h.min():.2f}, {solver.h.max():.2f}] m")

# 访问稳态结果
result = modeler.steady_result
print(f"收敛状态: {result['converged']}")
print(f"迭代次数: {result['iterations']}")

# 访问验证结果
validation = modeler.multi_validator.validation_results
print(f"流量守恒: {validation['flow_conservation']['status']}")
```

---

## 配置文件详解

### 必需字段

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `canal.length` | float | 渠道长度 (m) | 10000.0 |
| `canal.width` | float | 渠道宽度 (m) | 10.0 |
| `canal.slope` | float | 渠底坡度 | 0.001 |
| `canal.manning_n` | float | Manning糙率 | 0.025 |
| `boundary_conditions` | dict | 边界条件 | 见下文 |
| `simulation.type` | str | 模拟类型 | steady/unsteady |

### 边界条件配置

**上游边界**（二选一）：
- `type: flow` + `value: 10.0` → 流量边界
- `type: depth` + `value: 2.0` → 水深边界

**下游边界**（二选一）：
- `type: depth` + `value: 2.0` → 水深边界（推荐）
- `type: flow` + `value: 10.0` → 流量边界

### 网格配置选项

**方式1：指定点数**
```yaml
grid:
  nx: 101
```

**方式2：指定间距**（推荐）
```yaml
grid:
  dx_target: 100.0
```

**方式3：自适应网格**
```yaml
grid:
  dx_target: 200.0
  adaptive: true
```

### 结构物类型

#### 1. 闸门 (sluice_gate)
```yaml
- type: sluice_gate
  position: 5000.0    # 位置 (m)
  opening: 1.5        # 开度 (m)
  width: 10.0         # 宽度 (m)，可选
  Cd: 0.6             # 流量系数，可选
```

#### 2. 泵站 (pump_station)
```yaml
- type: pump_station
  position: 10000.0
  rated_flow: 30.0        # 额定流量 (m³/s)
  rated_head: 5.0         # 额定扬程 (m)
  min_suction_head: 2.0   # 最小吸入水头 (m)
```

#### 3. 堰 (weir)
```yaml
- type: weir
  position: 15000.0
  crest_height: 1.0  # 堰顶高程 (m)
  Cd: 0.4            # 流量系数，可选
```

#### 4. 孔口 (orifice)
```yaml
- type: orifice
  position: 20000.0
  opening: 0.5           # 开度 (m)
  invert_level: 0.0      # 底高程 (m)
  Cd: 0.6                # 流量系数，可选
```

---

## 验证标准

系统自动执行4级验证：

### 级别1：流量守恒
- ✅ 优秀：误差 < 1%
- ⚠️ 良好：误差 < 5%
- ❌ 不合格：误差 ≥ 5%

### 级别2：物理合理性
- 水深 > 0
- 0 < Froude数 < 3
- 流速 < 10 m/s

### 级别3：数值稳定性
- 无 NaN/Inf
- 水深有界变化（BV范数）

### 级别4：结构物流量
- 结构物处流量与目标流量一致
- 误差 < 5%

---

## 输出文件说明

### 1. 数据文件 (*.npz)

```python
import numpy as np

data = np.load("results/my_simulation_data.npz")
x = data['x']      # 网格坐标
h = data['h']      # 水深
Q = data['Q']      # 流量
result = data['result']  # 求解结果字典
```

### 2. 图片文件 (*.png)

- 纵剖面图：水位线、水深分布、流量分布

### 3. 验证报告 (validation_report.txt)

包含：
- 流量守恒验证
- 物理合理性检查
- 数值稳定性分析
- 结构物流量校核

---

## 常见问题

### Q1: 如何调整网格分辨率？

**A**: 修改 `config.yaml` 中的 `grid.dx_target` 或 `grid.nx`：

```yaml
grid:
  dx_target: 50.0  # 更细的网格（原来是200.0）
```

### Q2: 稳态求解不收敛怎么办？

**A**: 增加迭代次数或放宽容差：

```yaml
simulation:
  max_iterations: 10000    # 增加（原来是5000）
  convergence_tol: 0.01    # 放宽（原来是0.001）
```

### Q3: 如何启用自适应网格？

**A**: 设置 `grid.adaptive: true` 并确保有结构物：

```yaml
grid:
  dx_target: 200.0
  adaptive: true

structures:
  - type: sluice_gate
    position: 5000.0
    opening: 1.5
```

### Q4: 如何获取更详细的计算过程？

**A**: 使用分步建模，每步后可插入打印或分析：

```python
modeler = UniversalModeler("config.yaml")

modeler.setup_structures()
print(f"结构物数量: {len(modeler.structures)}")

x = modeler.setup_grid()
print(f"网格点数: {len(x)}")

result = modeler.run_steady_simulation()
print(f"迭代次数: {result['iterations']}")
```

### Q5: 泵站扬程不准确怎么办？

**A**: 确保使用改进的泵站实现（v3.0）。检查 `solvers/hydrostatic_canal_solver.py` 中是否有 `_apply_pump_region_constraints` 方法。

### Q6: 如何导出更多数据？

**A**: 运行后直接访问求解器：

```python
modeler = UniversalModeler("config.yaml")
modeler.run()

# 导出额外数据
solver = modeler.solver
np.savetxt("velocity.txt", solver.hu / solver.h)
np.savetxt("froude.txt", solver.hu / (solver.h * np.sqrt(9.81 * solver.h)))
```

---

## 开发规范

本系统遵循 **HydroClaude 开发指南**：

1. **库优先原则**：优先使用已有类库
   - `HydrostaticCanalSolver` → 求解器
   - `ResultValidator` → 结果验证
   - `VisualizationTemplates` → 图表生成

2. **模块化设计**：每个功能独立模块
   - 单一职责
   - 接口清晰
   - 易于测试

3. **配置驱动**：所有参数通过配置文件
   - YAML格式
   - 类型验证
   - 默认值合理

4. **文档完善**：代码即文档
   - 详细注释
   - 示例丰富
   - 用户友好

---

## 示例库

系统提供多个示例：

| 示例 | 难度 | 说明 |
|------|------|------|
| `example_simple_canal` | ⭐ | 最简单：均匀渠道 |
| `example_gate_pump_cascade` | ⭐⭐⭐ | 复杂：闸泵群系统 |

每个示例包含：
- `config_*.yaml` - 配置文件
- `run_*.py` - 运行脚本
- `README.md` - 说明文档

---

## 技术支持

- **开发指南**: `/docs/development_guide.md`
- **类库手册**: `/docs/class_library_reference.md`
- **问题反馈**: 提交 Issue

---

## 版本历史

### v1.0 (2025-10-24)
- ✅ 初始版本发布
- ✅ 完整的7模块架构
- ✅ 支持稳态模拟
- ✅ 配置文件管理
- ✅ 自动化建模流程

### 未来计划
- ⏳ 非稳态模拟支持
- ⏳ 实时控制接口
- ⏳ 更多结构物类型
- ⏳ GPU加速计算

---

## 许可证

本系统是 HydroClaude 项目的一部分。

---

**HydroClaude 通用建模系统 v1.0**
*最大限度降低建模难度，实现建模自动化*
