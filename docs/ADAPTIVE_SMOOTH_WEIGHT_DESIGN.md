# 自适应平滑权重设计文档

**目标**: 根据局部流动状态动态调整smooth_weight，实现1.0-1.5%误差

**作者**: Claude
**日期**: 2025-10-23

---

## 设计原理

### 基本思想

当前固定smooth_weight = 0.55的问题：
- 在高残差区域（闸门附近）可能仍需更多平滑
- 在低残差区域（远离闸门）过度平滑破坏守恒性

**自适应策略**：
```
smooth_weight(x, t) = f(local_residual, distance_to_gate, flow_state)
```

---

## 算法设计

### 方案1: 基于残差的自适应 (Residual-Based Adaptive)

#### 公式

```python
# 计算局部残差
residual = |Q_target - Q_current| / Q_target

# 自适应权重
if residual > high_threshold (e.g., 0.05):
    smooth_weight = 0.70  # 高平滑，优先稳定性
elif residual > medium_threshold (e.g., 0.02):
    smooth_weight = 0.55  # 中等平滑（当前最优值）
else:
    smooth_weight = 0.30  # 低平滑，保持守恒性
```

#### 优点
- 简单直观
- 快速响应局部问题
- 计算开销小

#### 缺点
- 阶梯函数可能导致不连续

---

### 方案2: 距离加权自适应 (Distance-Weighted Adaptive)

#### 公式

```python
# 计算到最近闸门的距离
d = min(|x - x_gate_i| for all gates)

# 距离衰减函数
decay = exp(-d / L_char)  # L_char = 100-200m

# 自适应权重
smooth_weight_base = 0.30  # 远场基础值
smooth_weight_gate = 0.70  # 闸门附近峰值
smooth_weight = smooth_weight_base + (smooth_weight_gate - smooth_weight_base) * decay
```

#### 优点
- 平滑过渡，无不连续
- 物理意义明确（闸门影响范围）
- 可预测性好

#### 缺点
- 需要预设特征长度L_char
- 不考虑实际流动状态

---

### 方案3: 混合自适应 (Hybrid Adaptive) ⭐ 推荐

结合残差和距离的优点：

#### 公式

```python
# 1. 距离因子
d = min(|x - x_gate_i| for all gates)
distance_factor = exp(-d / L_char)  # 范围 [0, 1]

# 2. 残差因子
residual = |Q_target - Q_current| / Q_target
residual_factor = tanh(residual / residual_scale)  # 平滑饱和

# 3. 组合权重
smooth_weight_min = 0.25  # 远场最小值
smooth_weight_max = 0.75  # 近场最大值

# 加权组合
alpha = 0.6  # 距离的权重
beta = 0.4   # 残差的权重

combined_factor = alpha * distance_factor + beta * residual_factor
smooth_weight = smooth_weight_min + (smooth_weight_max - smooth_weight_min) * combined_factor
```

#### 优点
- 结合两者优点
- 平滑连续
- 自适应性强

#### 缺点
- 参数较多（但可调优）

---

## 实现策略

### 参数配置

```python
class AdaptiveSmoothConfig:
    """自适应平滑配置"""

    # 模式选择
    mode: str = 'hybrid'  # 'fixed', 'residual', 'distance', 'hybrid'

    # 权重范围
    smooth_weight_min: float = 0.25
    smooth_weight_max: float = 0.75

    # 距离参数
    characteristic_length: float = 150.0  # 特征长度 (m)

    # 残差参数
    residual_scale: float = 0.03  # 残差归一化尺度

    # 混合参数（仅hybrid模式）
    alpha: float = 0.6  # 距离因子权重
    beta: float = 0.4   # 残差因子权重
```

### 集成到CanalSolver

#### 新增方法

```python
def _compute_adaptive_smooth_weight(self, idx: int, Q_target: float, Q_current: float) -> float:
    """
    计算自适应平滑权重

    Args:
        idx: 网格点索引
        Q_target: 目标流量
        Q_current: 当前流量

    Returns:
        smooth_weight: 自适应平滑权重 [0, 1]
    """
    pass
```

#### 修改_apply_internal_bc

在平滑步骤中调用自适应权重计算：

```python
# 原来的代码
smooth_weight = self.smooth_weight  # 固定值

# 改为
smooth_weight = self._compute_adaptive_smooth_weight(idx-1, Q_gate_new, self.Q[idx-1])
```

---

## 实现计划

### Step 1: 添加配置类

文件: `solvers/adaptive_smooth_config.py`

### Step 2: 修改CanalSolver

文件: `solvers/canal_solver.py`
- 添加adaptive_smooth_config参数
- 实现_compute_adaptive_smooth_weight方法
- 修改_apply_internal_bc调用

### Step 3: 测试验证

创建测试脚本比较：
1. 固定smooth_weight = 0.55
2. 自适应smooth_weight (residual模式)
3. 自适应smooth_weight (distance模式)
4. 自适应smooth_weight (hybrid模式)

---

## 预期效果

| 方法 | 预期最大误差 | 预期闸门误差 | 优势 |
|------|-------------|-------------|------|
| 固定(0.55) | 2.32% | 1.95% | 基准 |
| 残差自适应 | 1.5-2.0% | 1.2-1.5% | 快速响应 |
| 距离自适应 | 1.3-1.8% | 1.0-1.3% | 平滑分布 |
| 混合自适应 | **1.0-1.5%** | **0.8-1.2%** | 最佳平衡 ⭐ |

---

## 向后兼容性

保持完全兼容：

```python
# 默认行为（不传adaptive_smooth_config）
solver = CanalSolver(smooth_weight=0.55)  # 固定模式

# 启用自适应
config = AdaptiveSmoothConfig(mode='hybrid')
solver = CanalSolver(adaptive_smooth_config=config)  # 自适应模式
```

---

**下一步**: 实现代码并测试验证
