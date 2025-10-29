# 非恒定流计算专项开发计划

**日期**: 2025-10-29
**重要性**: ⭐⭐⭐⭐⭐ 核心功能
**当前状态**: 基础已实现，需系统增强

---

## 现状评估

### ✅ 已实现的非恒定流能力

**核心求解器**：
- Godunov FVM求解时间依赖Saint-Venant方程
- TVD-RK2时间积分（2阶精度）
- 自适应时间步长（CFL-based）
- dt_max限制器（防止不稳定）

**已验证案例**：
- ✅ MacDonald Test 3: 溃坝（Dam Break）
- ✅ 激波传播
- ✅ 时间演化到稳态

**边界条件**：
- ✅ 固定Q, h边界
- ✅ 超临界边界
- ✅ Relaxation方法（平滑强加）

### ❌ 缺失的非恒定流功能

与商业软件（HEC-RAS, MIKE 11）对比：

| 功能 | HEC-RAS | MIKE 11 | HydroClaude | 状态 |
|------|---------|---------|-------------|------|
| **基础非恒定流** | ✅ | ✅ | ✅ | 已实现 |
| **洪水演进** | ✅ | ✅ | ⚠️ 未系统测试 | 缺失 |
| **时变边界条件** | ✅ | ✅ | ❌ | 缺失 |
| **过程线输入** | ✅ | ✅ | ❌ | 缺失 |
| **闸门操作瞬态** | ✅ | ✅ | ⚠️ 代码未测试 | 缺失 |
| **泵站启停瞬态** | ✅ | ✅ | ⚠️ 代码未测试 | 缺失 |
| **潮汐模拟** | ✅ | ✅ | ❌ | 缺失 |
| **溃坝波** | ✅ | ✅ | ✅ | 已实现 |
| **风暴潮** | ✅ | ✅ | ❌ | 缺失 |
| **洪水预报** | ✅ | ✅ | ❌ | 缺失 |
| **实时同化** | ✅ | ✅ | ❌ | 缺失 |

**评估**: 基础能力30% → 目标80%+

---

## 非恒定流增强路线图

### 阶段A: 时变边界条件（2-3周）🔴 P1

#### A1. 时间序列边界条件

**功能描述**：
- 从文件读取Q(t)或h(t)时间序列
- 线性插值到当前时间
- 支持CSV、JSON格式

**实现**：
```python
class TimeSeriesBoundary:
    """时间序列边界条件"""

    def __init__(self, time_series_file, var_type='Q'):
        """
        Args:
            time_series_file: CSV文件路径
                格式: time,value
                      0,10.0
                      3600,15.0
                      7200,20.0
            var_type: 'Q' 或 'h'
        """
        self.data = pd.read_csv(time_series_file)
        self.times = self.data['time'].values
        self.values = self.data['value'].values
        self.var_type = var_type

    def get_value(self, t):
        """线性插值到时间t"""
        return np.interp(t, self.times, self.values)

# 使用示例
bc_left = {
    'type': 'Q_timeseries',
    'file': 'inflow_hydrograph.csv'
}
```

**测试案例**：
1. 阶跃流量输入（Q从10→20 m³/s瞬间变化）
2. 线性流量增长（Q从10→20 m³/s缓慢变化）
3. 洪水过程线（真实洪水数据）

**时间**: 5-6天

#### A2. 洪水过程线（Hydrograph）

**典型应用**：
```python
# 洪峰流量过程
t = [0, 1, 2, 3, 4, 5, 6, 7, 8] * 3600  # 小时转秒
Q = [50, 80, 150, 250, 200, 120, 80, 60, 50]  # m³/s

bc_upstream = {
    'type': 'hydrograph',
    'time': t,
    'discharge': Q
}
```

**测试**：
- 单峰洪水
- 双峰洪水
- 设计洪水（P=1%, 2%, 5%）

**时间**: 3-4天

#### A3. 潮汐边界条件

**理论**：
```python
# 潮汐公式（简化）
h_tide(t) = h_mean + A * sin(2π/T * t + φ)

其中:
  h_mean: 平均水位
  A: 振幅
  T: 周期（半日潮12.42h，全日潮24.84h）
  φ: 初相位
```

**实现**：
```python
class TidalBoundary:
    def __init__(self, mean_level, amplitude, period, phase=0):
        self.h0 = mean_level
        self.A = amplitude
        self.T = period
        self.phi = phase

    def get_level(self, t):
        return self.h0 + self.A * np.sin(2*np.pi/self.T * t + self.phi)

# 使用
bc_downstream = {
    'type': 'tidal',
    'mean_level': 2.0,  # m
    'amplitude': 1.5,    # m
    'period': 12.42 * 3600  # 12.42小时
}
```

**测试案例**：
- 潮汐进退（河口区域）
- 感潮河段流动
- 潮汐与河流流量耦合

**时间**: 4-5天

**小计**: 阶段A时间 = **12-15天**

---

### 阶段B: 瞬态过程模拟（2-3周）🔴 P1

#### B1. 闸门操作瞬态

**物理过程**：
1. 闸门突然开启（0→全开）
2. 闸门缓慢开启（0→全开，10分钟）
3. 闸门突然关闭（全开→0）
4. 闸门调节（开度随时间变化）

**实现**：
```python
class GateOperation:
    """闸门时变操作"""

    def __init__(self, gate, operation_schedule):
        """
        Args:
            gate: Gate对象
            operation_schedule: 操作时间表
                [(t1, opening1), (t2, opening2), ...]
                例如: [(0, 0.0), (300, 1.0), (600, 0.5)]
                      t=0s: 全关
                      t=300s: 全开
                      t=600s: 半开
        """
        self.gate = gate
        self.schedule = operation_schedule

    def get_opening(self, t):
        """插值当前时刻的开度"""
        times = [s[0] for s in self.schedule]
        openings = [s[1] for s in self.schedule]
        return np.interp(t, times, openings)
```

**测试案例**：
1. 闸门突开（负波传播）
2. 闸门突关（正波传播）
3. 闸门启闭瞬态（完整过程）

**时间**: 5-6天

#### B2. 泵站启停瞬态

**物理过程**：
- 泵站启动：Q从0快速上升到额定流量
- 泵站停止：Q快速下降到0
- 泵站调节：变频调速

**实现**：
```python
class PumpOperation:
    """泵站时变操作"""

    def __init__(self, pump, start_time, stop_time, ramp_time=60):
        """
        Args:
            pump: Pump对象
            start_time: 启动时间（s）
            stop_time: 停止时间（s）
            ramp_time: 启动/停止过渡时间（s）
        """
        self.pump = pump
        self.t_start = start_time
        self.t_stop = stop_time
        self.ramp = ramp_time

    def get_discharge(self, t):
        """计算当前流量（考虑启停过渡）"""
        if t < self.t_start:
            return 0.0
        elif t < self.t_start + self.ramp:
            # 启动过渡
            ratio = (t - self.t_start) / self.ramp
            return self.pump.Q_rated * ratio
        elif t < self.t_stop:
            # 正常运行
            return self.pump.Q_rated
        elif t < self.t_stop + self.ramp:
            # 停止过渡
            ratio = 1.0 - (t - self.t_stop) / self.ramp
            return self.pump.Q_rated * ratio
        else:
            return 0.0
```

**测试案例**：
1. 单泵启动瞬态
2. 多泵顺序启动
3. 泵站紧急停机
4. 泵站优化调度（最小水位波动）

**时间**: 5-6天

#### B3. 联合调度瞬态

**场景**: 闸泵联合调度
```python
# 典型调度策略
t=0s:     闸门全关，泵站停止
t=300s:   泵站1启动（流量上升）
t=600s:   泵站2启动（流量继续上升）
t=900s:   闸门开始开启（流量补充）
t=1200s:  闸门全开，泵站1停止
t=1500s:  闸门关闭，泵站2停止
```

**测试**：
- 水位控制效果
- 流量平滑过渡
- 能量消耗优化

**时间**: 4-5天

**小计**: 阶段B时间 = **14-17天**

---

### 阶段C: 洪水模拟专项（2-3周）🟡 P2

#### C1. 洪水演进

**场景**：
- 上游洪峰传播
- 河道调蓄作用
- 洪水波速计算

**测试案例**：
1. **理论验证**: Kinematic wave解析解
   ```python
   c = dQ/dA  # 波速
   t_peak_下游 = t_peak_上游 + L/c
   ```

2. **真实河道**: 某河段100km洪水演进
   - 上游：洪峰Q=5000 m³/s
   - 河道：不规则断面，Manning n=0.035
   - 下游：自由出流
   - 模拟：48小时

3. **多支流汇流**:
   - 主河道 + 2条支流
   - 不同时刻到达的洪峰
   - 汇流节点水位变化

**时间**: 7-8天

#### C2. 溃坝波模拟

**当前**: Test 3已验证，但需增强

**增强内容**：
1. 不同溃坝形式：
   - 瞬时溃决（instantaneous failure）
   - 渐进溃决（progressive failure）
   - 部分溃决（partial breach）

2. 下游影响分析：
   - 波前到达时间
   - 最大水深包络线
   - 淹没范围

3. 实际案例：
   - 板桥水库溃坝（1975）
   - Malpasset Dam（1959）

**时间**: 5-6天

#### C3. 防洪调度

**功能**：
- 水库防洪调度规则
- 闸门开度优化
- 削峰效果评估

**实现**：
```python
class FloodControlStrategy:
    """防洪调度策略"""

    def __init__(self, reservoir, control_levels):
        """
        Args:
            control_levels: 控制水位
                {
                    'flood_limit': 145.0,   # 防洪限制水位
                    'warning': 148.0,       # 警戒水位
                    'danger': 150.0,        # 危险水位
                    'design_flood': 152.0   # 设计洪水位
                }
        """
        self.reservoir = reservoir
        self.levels = control_levels

    def get_release(self, h_current, Q_inflow):
        """决策泄流量"""
        if h_current < self.levels['flood_limit']:
            # 蓄水期：最小下泄
            return self.min_release()
        elif h_current < self.levels['warning']:
            # 正常期：加大下泄
            return Q_inflow * 0.8
        elif h_current < self.levels['danger']:
            # 警戒期：等量下泄
            return Q_inflow
        else:
            # 危险期：最大下泄
            return self.max_release()
```

**测试**：
- 单库防洪调度
- 梯级水库联合调度
- 防洪效果对比（调度 vs 不调度）

**时间**: 6-7天

**小计**: 阶段C时间 = **18-21天**

---

### 阶段D: 高级非恒定流功能（3-4周）🟡 P3

#### D1. 非恒定流数值方法增强

**当前问题**：
- 时间精度：TVD-RK2（2阶）
- 可能的改进：RK3, RK4（3-4阶）

**增强方案**：
```python
# RK4时间积分（4阶精度）
k1 = dt * L(U_n)
k2 = dt * L(U_n + 0.5*k1)
k3 = dt * L(U_n + 0.5*k2)
k4 = dt * L(U_n + k3)
U_{n+1} = U_n + (k1 + 2*k2 + 2*k3 + k4) / 6
```

**时间**: 4-5天

#### D2. 隐式时间积分

**目的**: 允许更大时间步长

**方法**:
- 隐式Euler
- Crank-Nicolson
- θ-method

**优点**:
- 无条件稳定（不受CFL限制）
- 适合缓变流

**缺点**:
- 需要求解非线性方程组
- 计算成本高

**时间**: 8-10天

#### D3. 自适应网格细化（AMR）

**目的**: 激波处自动加密

**实现**：
```python
# 检测激波位置
def detect_shock(h):
    dh = np.diff(h)
    shock_indicator = np.abs(dh) / h[:-1]
    return shock_indicator > threshold

# 局部细化
if detect_shock(solver.h):
    solver.refine_mesh(region)
```

**时间**: 10-12天

**小计**: 阶段D时间 = **22-27天**

---

## 测试案例库

### 标准测试（验证）

| 编号 | 名称 | 类型 | 解析解 | 难度 |
|------|------|------|--------|------|
| U-1 | 溃坝波 | 激波 | Ritter解 | ⭐⭐ |
| U-2 | 洪水演进 | 扩散波 | Kinematic wave | ⭐⭐⭐ |
| U-3 | 闸门突开 | 负波 | 特征线法 | ⭐⭐⭐ |
| U-4 | 潮汐传播 | 周期流 | 调和分析 | ⭐⭐⭐ |
| U-5 | 泵站启动 | 瞬态 | 无解析解 | ⭐⭐⭐⭐ |
| U-6 | 梯级调度 | 联合运行 | 无解析解 | ⭐⭐⭐⭐ |

### 实际案例（验证）

1. **长江1998年洪水** 🇨🇳
   - 区间：宜昌-武汉
   - 数据：实测洪水过程
   - 验证：与实测对比

2. **黄河小浪底调度** 🇨🇳
   - 场景：调水调沙
   - 闸门操作：复杂时变
   - 验证：运行数据

3. **Mississippi River Flood** 🇺🇸
   - 历史洪水：1993, 2011
   - HEC-RAS对比验证

4. **Rhine River Flood** 🇪🇺
   - MIKE 11对比验证

---

## 与商业软件对比

### HEC-RAS非恒定流模块

**能力**：
- 完整的非恒定流求解
- 内边界（闸、堰、泵）
- 外边界（Q(t), h(t), Rating curve）
- 冰塞/冰盖
- 泥沙输移（非恒定）

**验证**：
- RD-52技术报告
- 数千个实际工程案例

**HydroClaude差距**: 大（30% vs 90%）

### MIKE 11非恒定流模块

**能力**：
- HD模块（水动力）
- AD模块（对流扩散）
- WQ模块（水质）
- ST模块（泥沙）
- ECO Lab模块（生态）

**HydroClaude差距**: 很大（仅HD基础）

---

## 优先级建议

### P0 - 立即实现（阻塞）

❌ 无（当前Test 4修复是P0）

### P1 - 高优先级（1-2月）

1. ✅ **阶段A**: 时变边界条件（2-3周）
   - 非恒定流的基础
   - 用户最常需要
   - 实现相对简单

2. ✅ **阶段B**: 闸泵瞬态（2-3周）
   - 工程应用核心
   - 代码已有基础
   - 需要验证测试

### P2 - 中优先级（2-4月）

3. ✅ **阶段C**: 洪水模拟（2-3周）
   - 防洪应用
   - 展示非恒定流能力

### P3 - 低优先级（4-6月）

4. ⏸️ **阶段D**: 高级方法（3-4周）
   - 学术研究
   - 性能优化
   - 非必需

---

## 时间规划

### 快速增强（1个月）
```
Week 1-2: 阶段A（时变BC）
Week 3-4: 阶段B（闸泵瞬态）
交付：核心非恒定流功能 60%
```

### 完整实现（2个月）
```
Month 1: 阶段A + B
Month 2: 阶段C（洪水模拟）
交付：非恒定流功能 80%
```

### 全面增强（3个月）
```
Month 1-2: 同上
Month 3: 阶段D（高级方法）
交付：非恒定流功能 90%
```

---

## 与主路线图的整合

**主路线图**: `DEVELOPMENT_ROADMAP_2025_10_29.md`

**整合方式**：

| 主路线图阶段 | 非恒定流内容 | 时间 |
|-------------|-------------|------|
| 阶段0 (100%测试) | 溃坝测试增强 | +2天 |
| 阶段1 (数值方法) | 无特殊内容 | 0天 |
| 阶段2 (几何+物理) | **阶段A (时变BC)** | +15天 |
| 阶段2 (几何+物理) | **阶段B (闸泵瞬态)** | +17天 |
| 阶段3 (管网) | 管网非恒定流 | 包含在内 |
| 阶段4 (V&V) | **阶段C (洪水案例)** | +21天 |
| 阶段5 (高级) | **阶段D (高级方法)** | +27天 |

**总增加时间**: 约2.5个月（如果全部实现）

**建议**:
- 阶段A+B（P1）集成到主路线图阶段2 ✅
- 阶段C（P2）集成到主路线图阶段4 ✅
- 阶段D（P3）可选 ⏸️

---

## 成功标准

### 最小成功（1个月）

- ✅ 时变边界条件（Q(t), h(t)）
- ✅ 洪水过程线输入
- ✅ 闸门时变操作
- ✅ 5个非恒定流测试案例

### 完整成功（2个月）

- ✅ 以上全部
- ✅ 泵站启停瞬态
- ✅ 潮汐边界条件
- ✅ 洪水演进模拟
- ✅ 10个验证案例
- ✅ 与HEC-RAS对比

### 商业级（3个月）

- ✅ 以上全部
- ✅ 实际工程案例验证（3个以上）
- ✅ 完整非恒定流V&V报告
- ✅ 用户手册（非恒定流专章）

---

## 结论

### 回答用户问题

**Q: "你的计划里面包括非恒定流计算吗？"**

**A: 包括，但不够系统和明确！**

**当前状态**：
- ✅ 核心能力已有（Godunov FVM求解非恒定S-V方程）
- ✅ 溃坝测试已验证
- ❌ 时变边界条件缺失（关键！）
- ❌ 洪水模拟未系统测试
- ❌ 闸泵瞬态未验证

**补充内容**（本文档）：
- 4个阶段专项增强（A-D）
- 6个标准测试 + 4个实际案例
- 1-3个月完整实现
- 从30%提升到90%功能

**建议行动**：
1. 立即：完成Test 4（阶段0）
2. 然后：实现阶段A（时变BC，2-3周）✅ P1
3. 接着：实现阶段B（闸泵瞬态，2-3周）✅ P1
4. 最后：实现阶段C（洪水案例，2-3周）🟡 P2

**预期效果**：
2个月后，HydroClaude的非恒定流计算能力将达到商业软件的80%水平！

---

**文档版本**: 1.0
**创建日期**: 2025-10-29
**状态**: 补充计划
**优先级**: P1（阶段A+B）

**集成到**: `DEVELOPMENT_ROADMAP_2025_10_29.md` 阶段2
