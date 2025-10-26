# 泵站模型综合分析报告

**日期**: 2025-10-26  
**问题**: 泵站流量模型不合理，未考虑泵前水位对流量的影响  
**严重程度**: 🚨 **高** - 违反真实泵站工作原理

---

## 📊 问题现象总结

### 1. 计算结果异常

| 位置 | 初始工况 | 最终工况 (t=3600s) | 变化 |
|------|---------|------------------|------|
| 区域平均 (40-50km) | h=3.337m, Q=30.00m³/s | h=3.598m, Q=53.08m³/s | ✓ 正常响应 |
| 紧邻泵前 (49.8km) | h=3.307m, Q=30.00m³/s | h=3.307m, Q=30.00m³/s | ❌ 完全不变 |
| 泵站处 (50.0km) | h=3.327m, Q=30.00m³/s | h=3.327m, Q=30.00m³/s | ❌ 完全不变 |
| 泵后 (50.2km) | h=3.347m, Q=30.00m³/s | h=3.347m, Q=30.00m³/s | ❌ 完全不变 |

**核心矛盾**：
- 上游（40-50km）：流量增加到53 m³/s，水深增加0.26m ✓
- 泵前（49.8km）：流量和水深**完全不变** ❌
- 中间25 m³/s流量消失，违反质量守恒

### 2. 物理不合理性

```
流量传播被阻断：
  上游 (49.6km): 52.53 m³/s ──┐
                               │ 
                               ├─ [泵站墙] ─ 阻断25 m³/s
                               │
  泵站 (50.0km): 30.00 m³/s ──┘

应该的情况：
  上游流量增加 → 泵前水位上升 → 泵流量增加 → 新平衡
```

---

## 🔍 根本原因：模型设计缺陷

### 当前模型（简化）

```python
class PumpStation:
    def calculate_discharge(self, h_upstream, h_downstream, t=None):
        """
        当前模型：固定流量输出
        """
        if h_upstream >= self.min_suction_head:
            discharge = self.rated_flow  # ← 问题：始终=30 m³/s
            flow_type = 'rated'
        else:
            discharge = self.rated_flow * sqrt(h_upstream / self.min_suction_head)
            flow_type = 'reduced'
        
        return discharge, flow_type
```

**问题**：
1. ❌ 流量不随泵前水位变化
2. ❌ 流量不随系统阻力变化
3. ❌ 忽略了泵特性曲线
4. ❌ 忽略了管路特性曲线

---

## 💡 真实泵站工作原理

### 1. 泵特性曲线

真实离心泵在固定转速下的特性：

```
扬程 H (m)
  ^
  |     
6 +     *  ← Q=0, H=H_0 (关阀扬程)
  |       *
  |         *
5 +           * ← Q=30, H=5 (额定点)
  |             *
  |               *
4 +                 * ← Q=40, H降低
  |                   *
  |                     *
  +────────────────────────> 流量 Q (m³/s)
  0   10   20   30   40   50
```

**数学表达**：
```
H_pump = H_0 - a·Q - b·Q²
H_pump = 6.0 - 0.01·Q - 0.0033·Q²  (示例)
```

### 2. 管路特性曲线

系统所需扬程：

```
H_required = H_static + H_friction

其中：
  H_static = (z_bed_after + h_after) - (z_bed_before + h_before)
           = 底床高差 + 水位差
  
  H_friction = k·Q²  (沿程和局部损失)
```

**关键**：`H_required` 随 `h_before` 变化！

### 3. 工作点确定

工作点 = 泵特性曲线 ∩ 管路特性曲线

```
求解： H_pump(Q) = H_required(Q)
```

### 4. 变工况运行（核心）

**当泵前水位升高时**：

```
初始状态：
  h_before = 3.3 m
  H_static = 5.0 m (底床高差)
  H_required = 5.0 + k·Q²
  工作点：Q ≈ 30 m³/s

泵前水位升高后（h_before = 3.8 m）：
  H_static = 5.0 - (3.8 - 3.3) = 4.5 m  ← 所需扬程降低！
  H_required = 4.5 + k·Q²
  
  求解：6.0 - 0.01·Q - 0.0033·Q² = 4.5 + k·Q²
  → Q ≈ 37 m³/s  ← 流量增加！
```

**物理过程**：
1. 上游来水增加 (30→55 m³/s)
2. 泵前水位开始上升
3. 泵吸入条件改善，所需扬程降低
4. 工作点沿泵曲线向右移动
5. 泵流量增加 (30→约37 m³/s)
6. 达到新平衡：
   - 泵前蓄水 (水位升高)
   - 泵流量增加但不足以完全传递所有流量
   - 多余流量继续蓄在上游

---

## 📐 正确的泵站模型

### 方案A：完整泵特性曲线模型（推荐）

```python
class PumpStation:
    def __init__(self, ...):
        # 泵特性曲线系数
        self.H_shutoff = rated_head * 1.2  # 关阀扬程
        self.a = 0.01   # 线性系数
        self.b = 0.0033  # 二次系数
        
    def calculate_pump_head(self, Q):
        """
        根据流量计算泵提供的扬程
        H = H_0 - a·Q - b·Q²
        """
        return self.H_shutoff - self.a * Q - self.b * Q**2
    
    def calculate_required_head(self, h_before, h_after, z_before, z_after, Q):
        """
        计算系统所需扬程
        """
        H_static = (z_after + h_after) - (z_before + h_before)
        H_friction = self.friction_coef * Q**2
        return H_static + H_friction
    
    def calculate_discharge(self, h_upstream, h_downstream, 
                          z_upstream, z_downstream, t=None):
        """
        求解工作点：H_pump(Q) = H_required(Q)
        """
        # 迭代求解
        Q = self.rated_flow  # 初值
        
        for iteration in range(20):
            H_pump = self.calculate_pump_head(Q)
            H_req = self.calculate_required_head(
                h_upstream, h_downstream, 
                z_upstream, z_downstream, Q
            )
            
            # 牛顿迭代
            dH = H_pump - H_req
            if abs(dH) < 0.001:
                break
            
            # 更新流量
            dH_dQ_pump = -self.a - 2*self.b*Q
            dH_dQ_req = 2*self.friction_coef*Q
            dH_dQ = dH_dQ_pump - dH_dQ_req
            
            Q = Q - dH / dH_dQ
            Q = max(0, min(Q, self.max_flow))  # 限制范围
        
        return Q, 'operating'
```

### 方案B：简化耦合模型（快速修复）

```python
class PumpStation:
    def calculate_discharge(self, h_upstream, h_downstream, 
                          Q_upstream, t=None):
        """
        简化模型：流量跟随上游，扬程调整
        """
        # 泵流量 = 上游流量（质量守恒）
        Q_pump = Q_upstream
        
        # 限制在合理范围内
        Q_max = self.rated_flow * 1.3  # 允许超载30%
        if Q_pump > Q_max:
            Q_pump = Q_max
            # 超出部分会导致泵前水位上升
        
        # 根据流量计算扬程
        if Q_pump <= self.rated_flow:
            H_pump = self.rated_head
        else:
            # 超额定流量时，扬程降低
            ratio = Q_pump / self.rated_flow
            H_pump = self.rated_head * (2.0 - ratio)
            H_pump = max(0, H_pump)
        
        self.current_head = H_pump
        return Q_pump, 'operating'
```

---

## 📊 预期结果对比

### 当前模型（错误）

| 时刻 | 泵前h | 泵前Q | 泵站Q | 泵后Q | 说明 |
|------|-------|-------|-------|-------|------|
| t=0s | 3.307 | 30 | 30 | 30 | 初始稳态 |
| t=3600s | 3.307 | 30 | 30 | 30 | ❌ 完全不变 |

### 完整模型（正确）

| 时刻 | 泵前h | 泵前Q | 泵站Q | 泵后Q | 说明 |
|------|-------|-------|-------|-------|------|
| t=0s | 3.307 | 30 | 30 | 30 | 初始稳态 |
| t=1800s | 3.55 | 38 | 38 | 38 | ✓ 泵前水位升高，流量增加 |
| t=3600s | 3.75 | 40 | 40 | 40 | ✓ 继续调整，趋于稳定 |

### 简化耦合模型（改进）

| 时刻 | 泵前h | 泵前Q | 泵站Q | 泵后Q | 说明 |
|------|-------|-------|-------|-------|------|
| t=0s | 3.307 | 30 | 30 | 30 | 初始稳态 |
| t=1800s | 3.80 | 42 | 39 | 39 | ✓ 泵站部分传递流量 |
| t=3600s | 4.20 | 45 | 39 | 39 | ✓ 超出能力，泵前蓄水 |

**物理解释**：
- 上游来55 m³/s
- 泵站最大能力约39 m³/s (1.3×30)
- 多余16 m³/s导致泵前持续蓄水
- 泵前水位持续上升

---

## 🎯 修复建议

### 优先级1：立即修复（简化模型）

修改 `solvers/gate.py` 中的 `PumpStation.calculate_discharge` 方法：

```python
def calculate_discharge(self, h_upstream, h_downstream, 
                      Q_upstream, t=None):
    """添加Q_upstream参数，使流量能够跟随上游"""
    
    # 质量守恒：泵流量跟随上游流量
    Q_pump = Q_upstream
    
    # 限制最大流量（防止泵过载）
    Q_max = self.rated_flow * 1.3
    if Q_pump > Q_max:
        Q_pump = Q_max
    
    return Q_pump, 'operating'
```

### 优先级2：中期优化（完整模型）

实现完整的泵-管路系统模型：
1. 泵特性曲线：`H = H_0 - a·Q - b·Q²`
2. 管路特性：`H = H_static(h) + k·Q²`
3. 迭代求解工作点
4. 考虑泵效率、气蚀等

### 优先级3：长期完善（高级功能）

1. 多台泵并联/串联
2. 变频调速控制
3. 泵启停过程模拟
4. 效率优化控制

---

## 📈 理论泵特性曲线

根据分析，建议的泵特性曲线（额定30 m³/s，5 m扬程）：

```
Q (m³/s)  |  H (m)  |  η (%)  |  说明
----------|---------|---------|------------------
   0      |  6.00   |   0     | 关阀
  10      |  5.70   |  60     | 小流量
  20      |  5.30   |  80     | 接近额定
  30      |  5.00   |  90     | 额定点 ← 设计工况
  35      |  4.50   |  88     | 轻微超载
  40      |  3.80   |  82     | 超载
  45      |  2.90   |  70     | 严重超载
  50      |  1.80   |  50     | 接近失速
```

**关键点**：
- 额定点：Q=30, H=5.0, 效率最高
- 允许范围：20-40 m³/s
- 超过40 m³/s会导致扬程和效率急剧下降

---

## 🔬 物理验证

### 能量方程检查

对于真实泵站：

```
上游断面能量 E1 = z1 + h1 + v1²/(2g)
下游断面能量 E2 = z2 + h2 + v2²/(2g)

泵站提供的能量：
E_pump = H_pump·g = (E2 + E_loss) - E1

当Q增加时：
  • E_loss增加（摩阻损失 ∝ Q²）
  • H_pump降低（泵特性曲线）
  • 平衡点向右移动
```

### 质量守恒检查

```
∂h/∂t + ∂Q/∂x = 0

在泵站处：
  Q_out ≈ Q_in（忽略泵体积的蓄水）
```

当前模型违反了这个基本原理。

---

## 📝 总结

### 问题严重性

🚨 **高**：
1. 违反质量守恒
2. 违反真实泵站工作原理
3. 导致泵站完全阻断流量传播
4. 使瞬态模拟结果不可信

### 用户问题的正确性

用户的质疑**完全正确**：

> "按照泵站特性曲线，泵前水位增加，即便泵站转速没有变化，也可以改变泵站出口流量"

这正是真实泵站的工作原理！当前模型忽略了这个重要机制。

### 修复路径

1. **短期**（1-2天）：实现简化耦合模型，使流量能传递
2. **中期**（1周）：实现完整泵特性曲线模型
3. **长期**（1月）：添加高级功能（变频、多泵等）

---

**报告完成**: 2025-10-26  
**建议**: 优先实现简化耦合模型，快速恢复物理合理性
