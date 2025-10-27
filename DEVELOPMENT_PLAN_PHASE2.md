# 🎯 开发计划 Phase 2：通用水力学模型系统

**目标**：开发一个**配置文件驱动、自动化、高精度**的通用一维水力学模型系统

**核心原则**：精度 > 稳定性 > 通用性 > 易用性 > 美观

---

## 📊 当前状态评估

### ✅ 已完成（Phase 1）

```
核心算法（精度和稳定性）：
  ✅ 方案A: 0.38%精度，稳态专用
  ✅ 方案B: 0.26%精度，机器精度守恒
  ✅ 方案C: 0.10%精度，四阶精度
  ✅ 结构物模型：闸门、泵站、堰
  ✅ 14个验证测试全部通过
  ✅ 理论基础完整（11篇文献）

状态：核心已稳固 🎉
```

### ❌ 待开发（Phase 2）

```
功能扩展：
  ❌ 非恒定流（瞬态模拟）
  ❌ 配置文件驱动
  ❌ 自动化建模工具
  ❌ 结果可视化
  ❌ 情景分析框架
```

---

## 🚀 Phase 2 开发计划

### 阶段2.1：非恒定流核心（4周）⭐⭐⭐⭐⭐

**目标**：扩展到非恒定流，保持精度和稳定性

**原则**：
- ✅ 基于方案B/C（它们本来就是时间推进）
- ✅ 只做核心功能，不分散精力
- ✅ 充分验证精度和稳定性

#### Week 1-2: 方案B非恒定流扩展

```python
# 方案B已经是时间推进法，只需增强
solvers/v2_hybrid_fvfd/
  ├── unsteady_solver.py        # 新增：非恒定流求解器
  │   ├── 动态边界条件
  │   ├── 时间序列输入
  │   └── CFL自适应时间步长
  │
  └── boundary_conditions.py    # 新增：边界条件类
      ├── ConstantBC（恒定）
      ├── TimeSeriesBC（时间序列）
      └── ControlRuleBC（控制规则）
```

**验证标准**：
- ✅ 质量守恒：< 1e-10
- ✅ 激波捕捉：无振荡
- ✅ 长时间稳定性：运行24小时无发散

#### Week 3-4: 典型非恒定流场景测试

```
测试场景：
1. 闸门快速开启/关闭
2. 泵站启停
3. 洪水演进
4. 多结构联合调度

每个场景都要验证：
  - 质量守恒 < 1e-10
  - 物理合理性
  - 数值稳定性
```

**交付物**：
- ✅ 非恒定流求解器（200-300行）
- ✅ 4个典型场景测试
- ✅ 验证报告

---

### 阶段2.2：配置文件驱动（2周）⭐⭐⭐⭐⭐

**目标**：通过YAML配置文件快速建模

**设计理念**：
- 简单直观（工程师友好）
- 完整但不冗余
- 自动验证和提示

#### 配置文件格式设计

```yaml
# config/canal_network.yaml

# 1. 渠道几何（必选）
canal:
  length: 100000.0      # m
  width: 10.0           # m
  slope: 0.0001         # 无量纲
  manning: 0.025        # 糙率

# 2. 网格设置（可选，有默认值）
mesh:
  n_cells: 200          # 单元数
  refinement:           # 局部加密（可选）
    - position: 25000   # 在结构物附近加密
      factor: 4
      width: 1000

# 3. 结构物（必选）
structures:
  - type: gate          # 闸门
    name: "上游闸门"
    position: 25000.0
    width: 10.0
    opening: 3.0        # 初始开度
    
  - type: pump          # 泵站
    name: "中间泵站"
    position: 50000.0
    width: 10.0
    rated_flow: 10.0
    rated_head: 5.0
    
  - type: gate
    name: "下游闸门"
    position: 75000.0
    width: 10.0
    opening: 2.5

# 4. 边界条件
boundary:
  upstream:
    type: flow          # 流量边界
    value: 10.0         # m³/s
    # 或时间序列
    # timeseries: "data/flow_upstream.csv"
    
  downstream:
    type: depth         # 水深边界
    value: 2.0          # m

# 5. 求解器设置（可选）
solver:
  method: hybrid_fvfd   # 默认方案B
  # 或: wellbalanced_fdm (方案A), dg_high_order (方案C)
  
  steady_state:         # 稳态设置
    max_iter: 2000
    tolerance: 0.01     # %
    
  unsteady:             # 非恒定流设置（可选）
    duration: 86400     # 24小时
    dt: 1.0             # 时间步长（会自动调整）
    output_interval: 600 # 输出间隔

# 6. 输出设置（可选）
output:
  directory: "results/"
  formats: [csv, png]   # 输出格式
  variables: [h, Q, u]  # 输出变量
```

#### 实现代码

```python
# config/config_parser.py
class HydraulicModelConfig:
    """配置文件解析器"""
    
    def __init__(self, config_file: str):
        self.config = self.load_yaml(config_file)
        self.validate()  # 自动验证
    
    def build_model(self):
        """一键创建模型"""
        solver = self.create_solver()
        self.add_structures(solver)
        self.set_boundaries(solver)
        return solver
    
    def run_simulation(self):
        """一键运行"""
        model = self.build_model()
        
        if self.is_steady_state():
            result = model.solve_steady_state(...)
        else:
            result = model.solve_unsteady(...)
        
        self.save_results(result)
        self.plot_results(result)
        
        return result
```

**使用示例**（目标）：

```python
# 超简单使用
from config import HydraulicModelConfig

config = HydraulicModelConfig("config/my_canal.yaml")
result = config.run_simulation()  # 完成！

# 就这么简单！
```

**交付物**：
- ✅ 配置文件格式规范（文档）
- ✅ 配置解析器（300行）
- ✅ 自动化建模工具（200行）
- ✅ 3个示例配置文件

---

### 阶段2.3：结果可视化（1周）⭐⭐⭐⭐

**目标**：自动生成清晰的结果图表

**原则**：
- 标准图表（工程常用）
- 自动美化
- 一键生成

#### 核心图表

```python
# visualization/auto_plot.py

class ResultVisualizer:
    """结果自动可视化"""
    
    def plot_all(self, result):
        """生成所有标准图表"""
        self.plot_profile()      # 纵断面图
        self.plot_timeseries()   # 时间序列
        self.plot_structures()   # 结构物状态
        self.plot_convergence()  # 收敛历史
        self.create_report()     # 生成报告

# 标准图表：
1. 水面线纵断面图
   - X轴：距离
   - Y轴：水位（水深+床面高程）
   - 显示：闸门、泵站位置

2. 流量分布图
   - 验证质量守恒

3. 时间历程图（非恒定流）
   - 关键点的h、Q随时间变化

4. 结构物运行图
   - 闸门开度、泵站流量随时间变化

5. 收敛历史
   - 迭代次数 vs 误差
```

**交付物**：
- ✅ 可视化工具（200行）
- ✅ 5种标准图表
- ✅ 自动报告生成

---

### 阶段2.4：情景分析框架（1周）⭐⭐⭐

**目标**：快速运行多个情景对比

```python
# scenarios/scenario_manager.py

# 定义多个情景
scenarios = {
    "基准情景": {
        "gate1_opening": 3.0,
        "pump_head": 5.0,
    },
    "增加泵站扬程": {
        "gate1_opening": 3.0,
        "pump_head": 6.0,  # 增加1m
    },
    "关小闸门": {
        "gate1_opening": 2.5,  # 减小0.5m
        "pump_head": 5.0,
    },
}

# 自动运行并对比
manager = ScenarioManager(base_config="config/base.yaml")
results = manager.run_scenarios(scenarios)
manager.compare_results(results)  # 自动生成对比图表
```

---

## 📅 详细时间表

```
Week 1-2:   非恒定流核心开发
Week 3-4:   非恒定流验证测试
Week 5-6:   配置文件系统开发
Week 7:     可视化工具开发
Week 8:     情景分析框架
─────────────────────────────
总计:       8周（2个月）
```

---

## 🎯 开发优先级（重要！）

### 🔴 核心优先级（必须保证）

```
1. 精度       ⭐⭐⭐⭐⭐ (最高)
2. 稳定性     ⭐⭐⭐⭐⭐ (最高)
3. 守恒性     ⭐⭐⭐⭐⭐ (最高)
4. 非恒定流   ⭐⭐⭐⭐⭐ (核心功能)
5. 配置驱动   ⭐⭐⭐⭐  (易用性核心)
```

### 🟡 辅助优先级（重要但不紧急）

```
6. 可视化     ⭐⭐⭐    (有就更好)
7. 情景分析   ⭐⭐⭐    (有就更好)
8. 文档美化   ⭐⭐      (可以慢慢来)
9. GUI界面    ⭐        (完全不急)
```

---

## ⚠️ 开发原则（避免过去的问题）

### ✅ DO（应该做）

```
1. 聚焦核心
   - 先保证非恒定流的精度和稳定性
   - 配置文件越简单越好
   - 可视化够用就行

2. 充分测试
   - 每个新功能都要测试
   - 质量守恒必须 < 1e-10
   - 长时间稳定性必须验证

3. 渐进开发
   - 先非恒定流，再配置文件
   - 先基本功能，再扩展功能
   - 每步都验证后再继续

4. 保持简单
   - 代码简洁易懂
   - 配置文件直观
   - 接口简单明了
```

### ❌ DON'T（不应该做）

```
1. ❌ 不要做复杂的GUI（浪费时间）
2. ❌ 不要做花哨的可视化（够用就行）
3. ❌ 不要做太多"锦上添花"功能
4. ❌ 不要在精度稳定前做其他功能
5. ❌ 不要追求"大而全"（聚焦核心）
```

---

## 📊 成功标准

### Phase 2 完成标准

```
核心功能：
  ✅ 非恒定流求解器（质量守恒 < 1e-10）
  ✅ 4个典型场景验证通过
  ✅ 配置文件系统（YAML）
  ✅ 一键建模和运行
  ✅ 基本可视化（5种图表）

质量指标：
  ✅ 非恒定流精度：与理论解误差 < 0.5%
  ✅ 质量守恒：< 1e-10
  ✅ 长时间稳定：24小时无发散
  ✅ 配置文件：< 100行完成建模

易用性：
  ✅ 3行代码完成模拟
  ✅ 自动生成图表和报告
  ✅ 完整的示例
```

---

## 🎯 当前最紧急任务

### 立即开始（本周）

**任务1：验证Phase 1成果**
```bash
# 确保现有代码稳固
./run_validation.sh
```

**任务2：设计配置文件格式**
```yaml
# 画出配置文件的草图
# 越简单越好，但要完整
```

**任务3：规划非恒定流API**
```python
# 设计非恒定流的接口
# 保持与稳态API一致
```

---

## 💡 推荐的开发路径

### 路径1：保守稳健（推荐）⭐⭐⭐⭐⭐

```
Week 1-4:  非恒定流（基于方案B）
           - 充分测试验证
           - 确保精度和稳定性
           
Week 5-6:  配置文件系统
           - 设计简洁格式
           - 实现解析器
           
Week 7-8:  基本可视化 + 示例
           - 5种标准图表
           - 3个完整示例
           
完成后再考虑其他功能
```

### 路径2：快速迭代（激进）

```
Week 1-2:  非恒定流最小实现
Week 3-4:  配置文件最小实现
Week 5-6:  集成测试 + 修复问题
Week 7-8:  可视化 + 文档

风险：可能精度/稳定性不够
```

**建议**：选择路径1，稳扎稳打！

---

## 📚 参考资料

### 非恒定流理论

1. **Toro (2001)** - "Shock-Capturing Methods"
2. **HEC-RAS User Manual** - Unsteady Flow
3. **SWMM Manual** - Dynamic Wave Routing

### 配置文件设计

参考：
- HEC-RAS项目文件格式
- SWMM inp文件格式
- YAML最佳实践

---

## ✅ 检查清单

开始Phase 2之前：

- [ ] Phase 1代码已验证（运行测试）
- [ ] 理解三个方案的原理
- [ ] 明确Phase 2目标和范围
- [ ] 设计好配置文件格式草图
- [ ] 规划好非恒定流API
- [ ] 时间和资源充足

---

## 🎊 总结

**核心目标**：
```
通用一维水力学模型系统
= 高精度核心（Phase 1已完成）✅
+ 非恒定流扩展（Phase 2.1）
+ 配置文件驱动（Phase 2.2）
+ 自动化工具（Phase 2.3-2.4）
```

**开发原则**：
```
精度 > 稳定性 > 通用性 > 易用性 > 美观
```

**时间规划**：
```
Phase 2: 8周（2个月）
```

**成功关键**：
```
1. 聚焦核心（精度+稳定性）
2. 避免分散精力
3. 充分测试验证
4. 保持简单
```

---

**准备好开始Phase 2了吗？** 🚀

建议：先验证Phase 1，再开始非恒定流开发！
