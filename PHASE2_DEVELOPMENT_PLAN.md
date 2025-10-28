# HydroClaude Phase 2 开发计划

**阶段**: Phase 2 - 核心问题优化与功能增强  
**计划日期**: 2025-10-27  
**预计周期**: 2-4周  
**优先级**: 🔴 高

---

## 🎯 Phase 2 目标

### 核心目标
解决Phase 1遗留的3个关键问题，提升系统鲁棒性至工业应用级别。

### 具体目标

1. **网络边界条件优化** 🔴 最高优先级
   - 当前问题: 质量误差9-22%（Y-split、T-junction）
   - 目标: 质量误差<1%
   - 预计时间: 1-2周

2. **动态边界处理改进** 🔴 高优先级
   - 当前问题: 快速变化导致NaN
   - 目标: 洪水过程线稳定模拟
   - 预计时间: 1周

3. **超临界流稳定性增强** 🟡 中优先级
   - 当前问题: S0>0.004时不稳定
   - 目标: 支持S0≤0.01
   - 预计时间: 1周

---

## 📋 问题分析

### 问题1: 网络边界条件（最严重）

**现象**:
```python
# Phase 1测试结果
Y-split测试: 质量误差 -9.37%
T-junction测试: 质量误差 -21.78%
```

**原因分析**:
1. 简单流量平分不守恒
   ```python
   # 当前错误做法
   Q_branch = Q_main / 2  # 不考虑水深和下游条件
   ```

2. 节点水深传递不连续
   ```python
   # 问题: 上下游水深突变
   h_upstream = 3.0 m
   h_downstream = 1.5 m  # 突变导致数值震荡
   ```

3. 缺少守恒性约束
   - 无质量守恒检查
   - 无动量守恒考虑

**解决方案**:

✅ **方案A: 水深连续性优先（推荐）**
```python
# 核心思想: 节点水深连续，流量按水力学分配
def update_node_bc_conservative(node):
    # 1. 水深连续性
    h_node = average([h_upstream for all inflow edges])
    
    # 2. 流量守恒
    Q_in_total = sum([Q for inflow edges])
    
    # 3. 按下游阻力分配
    for outflow_edge in node.outflow_edges:
        weight = compute_hydraulic_weight(edge)
        Q_out = Q_in_total * weight
        
    # 4. 守恒性检查
    assert abs(sum(Q_out) - Q_in_total) < tolerance
```

✅ **方案B: 特征线方法**
```python
# 使用Riemann不变量处理节点
def node_riemann_solver(node):
    # 计算上游特征线
    for inflow in node.inflows:
        R_plus = compute_riemann_invariant_plus(inflow)
    
    # 计算下游特征线
    for outflow in node.outflows:
        R_minus = compute_riemann_invariant_minus(outflow)
    
    # 求解节点状态
    h_node, Q_node = solve_riemann_at_node(R_plus, R_minus)
```

**实施步骤**:
1. 实现方案A（水深连续）
2. 添加守恒性检查
3. 测试Y-split和T-junction
4. 如果仍有问题，尝试方案B

---

### 问题2: 动态边界处理

**现象**:
```python
# Phase 1洪水过程线测试
时刻 t=10s: 正常
时刻 t=50s: 出现NaN
```

**原因分析**:
1. 边界流量变化过快
   ```python
   # 三角形洪水过程线
   Q(t) = Q_base + (Q_peak - Q_base) * t / t_peak  # 线性增长
   # 问题: 相邻时刻流量差过大 → CFL条件破坏
   ```

2. 边界条件不兼容
   ```python
   # 左边界: Q=50 m³/s (突然变为100 m³/s)
   # 右边界: h=2.0 m (固定)
   # 问题: Q和h不匹配 → 数值震荡
   ```

3. 初始条件不一致
   ```python
   # 初始: Q=50, h=2.0
   # 边界突变: Q=100 (但h=2.0未变)
   # 问题: 不满足流量-水深关系
   ```

**解决方案**:

✅ **方案1: 流量限速器**
```python
class RateLimitedBC:
    def __init__(self, max_rate_change):
        self.max_rate = max_rate_change  # m³/s per second
        self.current_value = None
        
    def update(self, target_value, dt):
        if self.current_value is None:
            self.current_value = target_value
            return target_value
        
        # 限制变化率
        max_change = self.max_rate * dt
        actual_change = np.clip(
            target_value - self.current_value,
            -max_change, max_change
        )
        
        self.current_value += actual_change
        return self.current_value
```

✅ **方案2: 边界条件兼容性检查**
```python
def check_bc_compatibility(bc_left, bc_right, solver):
    """检查左右边界是否兼容"""
    if bc_left['type'] == 'Q' and bc_right['type'] == 'h':
        # 计算Q对应的水深
        Q = bc_left['value']
        h_required = compute_h_for_Q(Q, solver.manning_n, solver.slope)
        h_boundary = bc_right['value']
        
        # 检查兼容性
        error = abs(h_required - h_boundary) / h_required
        if error > 0.1:  # 10%容差
            warnings.warn(f"边界条件不兼容: Q={Q} → h={h_required:.2f}, 但边界h={h_boundary:.2f}")
            # 自动调整右边界
            bc_right['value'] = h_required
```

✅ **方案3: 渐变初始化**
```python
def initialize_with_ramp(solver, Q_initial, Q_target, ramp_steps=100):
    """用渐变过程初始化，避免突变"""
    # 初始稳态
    solver.initialize_steady_state(Q_initial)
    
    # 渐变到目标流量
    for i in range(ramp_steps):
        Q_current = Q_initial + (Q_target - Q_initial) * i / ramp_steps
        bc_left['value'] = Q_current
        solver.step()
```

**实施步骤**:
1. 实现流量限速器
2. 添加边界兼容性检查
3. 实现渐变初始化
4. 测试洪水过程线

---

### 问题3: 超临界流稳定性

**现象**:
```python
# Phase 1测试结果
S0 = 0.001: 稳定 ✅
S0 = 0.002: 稳定 ✅
S0 = 0.004: NaN ❌
```

**原因分析**:
1. 激波捕捉不足
   - Order 1有数值耗散，但超临界流中激波太强
   - Minmod限制器过于耗散

2. 干床处理不当
   ```python
   # 超临界流 → 水深很浅 → 接近干床
   h < 0.01 m → 数值不稳定
   ```

3. 边界条件类型不当
   ```python
   # 超临界流: Fr > 1
   # 下游边界条件不应指定h（应该让信息自然流出）
   bc_right = {'type': 'h', 'value': h_uniform}  # 错误！
   ```

**解决方案**:

✅ **方案1: HLLC用于超临界流**
```python
def select_riemann_solver(solver):
    """根据Froude数选择求解器"""
    Fr = compute_froude_number(solver.h, solver.Q, solver.width)
    
    if np.mean(Fr) > 0.8:  # 接近或超临界
        return 'HLLC'  # 更精确
    else:
        return 'HLL'   # 更稳定
```

✅ **方案2: 改进干床处理**
```python
def compute_flux_with_dry_bed_fix(h_L, h_R, Q_L, Q_R):
    """改进的通量计算，处理干床"""
    h_threshold = 1e-3  # 1mm
    
    # 左侧干床
    if h_L < h_threshold:
        return compute_flux_from_right(h_R, Q_R)
    
    # 右侧干床
    if h_R < h_threshold:
        return compute_flux_from_left(h_L, Q_L)
    
    # 正常计算
    return hll_flux(h_L, h_R, Q_L, Q_R)
```

✅ **方案3: 超临界边界条件**
```python
def get_supercritical_bc(Fr):
    """超临界流的边界条件"""
    if Fr > 1.0:
        # 超临界: 所有信息从上游传来
        return {
            'left': {'type': 'Q', 'value': Q},  # 指定流量
            'right': {'type': 'free'}            # 自由出流
        }
    else:
        # 亚临界: 常规处理
        return {
            'left': {'type': 'Q', 'value': Q},
            'right': {'type': 'h', 'value': h}
        }
```

**实施步骤**:
1. 实现自动Riemann求解器选择
2. 改进干床处理
3. 实现超临界边界条件
4. 测试S0=0.004, 0.006, 0.01

---

## 🗓️ 开发时间线

### 第1周: 网络边界条件优化

**Day 1-2**: 实现水深连续方案
- 修改`godunov_fvm_network.py`中的`_update_boundary_conditions`
- 实现水深连续性算法
- 添加流量守恒检查

**Day 3-4**: 测试和调试
- Y-split测试（目标<1%）
- T-junction测试（目标<1%）
- 复杂网络测试

**Day 5**: 文档和总结
- 更新使用指南
- 创建验证报告

### 第2周: 动态边界处理

**Day 1-2**: 实现流量限速器
- 创建`RateLimitedBC`类
- 集成到求解器
- 边界兼容性检查

**Day 3-4**: 测试洪水过程线
- 三角形洪水过程线
- 梯形洪水过程线
- 实际洪水数据

**Day 5**: 优化和文档

### 第3-4周: 超临界流稳定性

**Day 1-3**: 实现改进方案
- 自动Riemann选择
- 干床处理改进
- 超临界边界条件

**Day 4-5**: 测试
- S0=0.004, 0.006, 0.01
- Fr=1.0附近测试
- 极端工况

**Day 6-7**: 综合测试和文档

---

## 📊 成功标准

### 网络边界条件
- ✅ Y-split质量误差 < 1%
- ✅ T-junction质量误差 < 1%
- ✅ 复杂网络质量误差 < 2%
- ✅ 无NaN崩溃

### 动态边界处理
- ✅ 洪水过程线稳定模拟
- ✅ Q变化率≤50 m³/s/s 稳定
- ✅ 无边界不兼容警告
- ✅ 质量误差 < 2%

### 超临界流
- ✅ S0≤0.01 稳定
- ✅ Fr≤2.0 稳定
- ✅ 干床处理正确
- ✅ 质量误差 < 3%

---

## 🔧 技术方案汇总

### 核心算法改进

1. **守恒性节点算法**
   ```python
   # 核心: 水深连续 + 流量守恒
   h_node = avg(h_upstream)
   Q_total = sum(Q_in)
   Q_out[i] = Q_total * weight[i]
   assert sum(Q_out) == Q_total
   ```

2. **流量限速器**
   ```python
   # 核心: 限制边界条件变化率
   dQ/dt ≤ max_rate
   ```

3. **超临界边界**
   ```python
   # 核心: Fr>1时使用自由出流
   if Fr > 1: bc_right = 'free'
   ```

### 辅助功能

1. **守恒性检查器**
   ```python
   def check_mass_conservation(network):
       mass_in = sum(Q at sources)
       mass_out = sum(Q at sinks)
       error = abs(mass_in - mass_out) / mass_in
       return error
   ```

2. **边界兼容性检查**
   ```python
   def check_bc_compatibility(bc_left, bc_right):
       # 检查Q-h关系是否满足
       pass
   ```

3. **Froude数监控**
   ```python
   def monitor_froude(solver):
       Fr = compute_froude(solver)
       if max(Fr) > 0.9:
           switch_to_HLLC()
   ```

---

## 📈 预期成果

### 性能提升

| 指标 | Phase 1 | Phase 2目标 |
|------|---------|-----------|
| 网络质量误差 | 9-22% | <1% ✅ |
| 动态边界稳定性 | NaN | 稳定 ✅ |
| 超临界流支持 | S0<0.002 | S0≤0.01 ✅ |
| 综合成功率 | 92% | >95% ✅ |

### 新增功能

1. ✅ 守恒性网络求解器
2. ✅ 动态边界条件支持
3. ✅ 超临界流处理
4. ✅ 边界兼容性检查
5. ✅ 流量限速器

### 文档

1. ✅ Phase 2开发总结
2. ✅ 网络求解器使用指南
3. ✅ 动态边界使用指南
4. ✅ 超临界流最佳实践
5. ✅ Phase 2验证报告

---

## 🎯 里程碑

### Milestone 1: 网络边界优化完成（第1周）
- 质量误差<1%
- Y-split和T-junction稳定

### Milestone 2: 动态边界改进完成（第2周）
- 洪水过程线稳定
- 无NaN崩溃

### Milestone 3: 超临界流增强完成（第3周）
- S0≤0.01稳定
- Fr≤2.0稳定

### Milestone 4: Phase 2完成（第4周）
- 所有测试通过
- 文档完整
- 综合验证报告

---

## 🚧 风险和挑战

### 风险1: 网络守恒性难以保证
**缓解措施**:
- 使用特征线方法（备选方案B）
- 引入松弛因子
- 迭代求解节点状态

### 风险2: 动态边界仍然不稳定
**缓解措施**:
- 进一步降低CFL
- 使用隐式边界处理
- 引入缓冲区

### 风险3: 超临界流需要更高阶格式
**缓解措施**:
- 使用WENO重构（长期）
- 改进限制器
- 局部网格加密

---

## 📚 参考资料

### 网络求解
1. Toro - Riemann Solvers (Ch. 14: Networks)
2. LeVeque - Finite Volume Methods (Ch. 17: Networks)

### 动态边界
1. HEC-RAS User Manual - Dynamic Boundaries
2. MIKE 11 - Time Series Input

### 超临界流
1. Chaudhry - Open-Channel Flow (Ch. 12: Supercritical)
2. Chanson - Hydraulics of Open Channel Flow (Ch. 8)

---

## ✅ Phase 2 启动

**开始日期**: 2025-10-27  
**预计完成**: 2025-11-24  
**第一步**: 优化网络边界条件

---

**Generated by**: HydroClaude Development Team  
**Date**: 2025-10-27  
**Status**: 🚀 **Phase 2 启动！**
