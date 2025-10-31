# Phase 8.2 技术文档 - 湿干界面增强处理

**日期**: 2025-10-31
**阶段**: Stage 8 - Phase 8.2
**状态**: 🚧 规划中
**目标**: 解决RP5-RP7干床问题（>400% → <50%）

---

## 📊 执行摘要

基于Phase 8.1的正定性保持WENO3，进一步增强湿干界面处理，解决Stage 7中识别的RP5-RP7干床/近真空问题。

**核心成果**（预期）:
- ✅ 实现增强型湿干界面求解器（`wet_dry_enhanced_weno3.py`，~800行）
- ✅ 创建RP5-RP7干床测试套件（`test_rp567_wet_dry.py`，~450行）
- 🚧 RP5-RP7误差改进：>400% → <50%（目标）
- 🚧 消除湿干界面数值振荡
- 🚧 保持质量守恒（误差<0.1%）

---

## 🎯 问题背景

### Stage 7识别的问题

**RP5测试（左侧干床）**:
- 初值: h_L=0.0, u_L=0.0 (干), h_R=5.0, u_R=0.0 (湿)
- 精确解: 右向稀疏波，湿水向干床扩展
- **当前状态**: 误差>400%，数值振荡严重

**RP6测试（右侧干床）**:
- 初值: h_L=5.0, u_L=5.0 (湿), h_R=0.0, u_R=0.0 (干)
- 精确解: 左向稀疏波，湿水向干床扩展
- **当前状态**: 误差>400%，类似RP5

**RP7测试（近真空/双向干床）**:
- 初值: h_L=1.0, u_L=-10.0 (左), h_R=1.0, u_R=10.0 (右)
- 精确解: 双向稀疏波，中间形成真空（h=0）
- **当前状态**: 误差>400%，真空区域振荡

### 根本原因

**当前干床处理的缺陷**:
```python
# 当前实现（godunov_fvm_solver.py:1140-1141）
if h_L < eps_dry and h_R < eps_dry:
    return 0.0, 0.0  # 简单返回零通量
```

**问题**:
1. **过于简化的干床判断**: 只检查两侧都干，单侧干床未特殊处理
2. **高阶重构在界面处失效**: WENO3在h→0处产生非物理负值
3. **缺乏质量重分配机制**: 湿水进入干床时出现数值振荡
4. **波速估计不准确**: 干床处c=√(gh)=0，Davis估计失效

### 文献参考

根据国际标准文献：

**Toro (2001)** 推荐的湿干界面策略:
- 界面检测：`h < threshold`（通常10⁻⁴~10⁻⁶）
- 局部降阶：界面处使用一阶格式
- 正定性保证：确保h≥0

**Audusse et al. (2004)** "A Fast and Stable Well-Balanced Scheme":
- 水力静力重构（Hydrostatic Reconstruction）
- 专门处理湿干界面

**Kurganov & Petrova (2007)**:
- 中心格式+半离散方法
- 自然的湿干界面处理

---

## 🔬 技术方案

### 总体策略

**三层防护机制**:

```
Layer 1: 界面检测
    ↓
Layer 2: 正定性保持（Phase 8.1）
    ↓
Layer 3: 界面特殊通量
```

### Layer 1: 增强型界面检测

**目标**: 精确识别湿干界面位置

**方法**:
```python
def detect_wet_dry_interface(h: np.ndarray, threshold: float = 1e-4) -> Dict:
    """
    检测湿干界面

    返回:
    - is_interface[i]: cell i是否是界面
    - interface_type[i]: 'wet_to_dry', 'dry_to_wet', 'vacuum_forming', 'none'
    """
    n = len(h)
    is_interface = np.zeros(n, dtype=bool)
    interface_type = ['none'] * n

    for i in range(n):
        # 获取邻居
        h_left = h[i-1] if i > 0 else h[i]
        h_center = h[i]
        h_right = h[i+1] if i < n-1 else h[i]

        # 判断
        neighbors = [h_left, h_center, h_right]
        has_wet = any(h_val > threshold for h_val in neighbors)
        has_dry = any(h_val <= threshold for h_val in neighbors)

        if has_wet and has_dry:
            is_interface[i] = True

            # 判断类型
            if h_center > threshold:
                if h_left <= threshold or h_right <= threshold:
                    interface_type[i] = 'wet_to_dry'
            else:
                if h_left > threshold or h_right > threshold:
                    interface_type[i] = 'dry_to_wet'

            # 近真空检测（RP7）
            if h_center < threshold and h_left > threshold and h_right > threshold:
                interface_type[i] = 'vacuum_forming'

    return {
        'is_interface': is_interface,
        'interface_type': interface_type
    }
```

### Layer 2: 正定性保持集成

**基础**: 复用Phase 8.1的`PositivityPreservingWENO3`

**增强**:
- 在湿干界面处更激进的限制（θ_min更大）
- 界面处强制使用一阶格式

```python
def compute_positivity_limiter_enhanced(self, h, ..., interface_info):
    """
    增强型正定性保持限制器

    在湿干界面处：
    - 强制 θ <= 0.3（最多30%高阶）
    - 或完全降为一阶（θ=0）
    """
    # 基础限制器（Phase 8.1）
    theta = super().compute_positivity_limiter(h, ...)

    # 界面增强
    is_interface = interface_info['is_interface']

    for i in range(len(theta)):
        if is_interface[i] or (i > 0 and is_interface[i-1]):
            # 湿干界面：强制更低的θ
            theta[i] = min(theta[i], 0.3)  # 最多30%高阶

            # 真空形成区域：完全降为一阶
            if interface_info['interface_type'][i] == 'vacuum_forming':
                theta[i] = 0.0

    return theta
```

### Layer 3: 界面特殊通量

**目标**: 湿干界面使用稳健的通量计算

**策略A: 修正HLL通量**（推荐）
```python
def hll_flux_wet_dry(self, h_L, Q_L, h_R, Q_R, eps_dry=1e-6):
    """
    湿干界面修正HLL通量

    参考: Toro (2001), Section 5.4
    """
    # 干床检测
    dry_L = h_L < eps_dry
    dry_R = h_R < eps_dry

    # Case 1: 两侧都干
    if dry_L and dry_R:
        return 0.0, 0.0

    # Case 2: 左干右湿（RP5类型）
    if dry_L and not dry_R:
        # 只使用右状态
        u_R = Q_R / (self.B * max(h_R, eps_dry))
        c_R = np.sqrt(self.g * h_R)

        # 波速
        S_R = u_R + 2*c_R  # 稀疏波前沿

        if S_R <= 0:
            # 超音速向左（不应该发生）
            F_h = Q_R
            F_Q = Q_R**2 / (self.B * h_R) + 0.5 * self.g * h_R**2 * self.B
        else:
            # 干床情况：零通量
            F_h = 0.0
            F_Q = 0.0

        return F_h, F_Q

    # Case 3: 左湿右干（RP6类型）
    if not dry_L and dry_R:
        # 只使用左状态
        u_L = Q_L / (self.B * max(h_L, eps_dry))
        c_L = np.sqrt(self.g * h_L)

        # 波速
        S_L = u_L - 2*c_L  # 稀疏波前沿

        if S_L >= 0:
            # 超音速向右（不应该发生）
            F_h = Q_L
            F_Q = Q_L**2 / (self.B * h_L) + 0.5 * self.g * h_L**2 * self.B
        else:
            # 干床情况：零通量
            F_h = 0.0
            F_Q = 0.0

        return F_h, F_Q

    # Case 4: 两侧都湿（使用标准HLL）
    return self._hll_flux_standard(h_L, Q_L, h_R, Q_R)
```

**策略B: 水力静力重构**（备选）
```python
def hydrostatic_reconstruction(self, h_L, z_L, h_R, z_R):
    """
    水力静力重构（Audusse et al. 2004）

    优点：自然处理湿干界面
    缺点：实现复杂
    """
    # 重构水位
    eta_L = h_L + z_L
    eta_R = h_R + z_R

    # 修正水深
    h_L_star = max(0, eta_L - max(z_L, z_R))
    h_R_star = max(0, eta_R - max(z_L, z_R))

    # 使用修正水深计算通量
    return self.hll_flux_wet_dry(h_L_star, Q_L, h_R_star, Q_R)
```

---

## 💻 代码实现

### 1. 核心求解器类

**文件**: `solvers/wet_dry_enhanced_weno3.py` (~800行)

**类层次**:
```
GodunvFVMSolver (祖父类)
    ↓
GodunvFVMWENO3 (父父类)
    ↓
PositivityPreservingWENO3 (父类, Phase 8.1)
    ↓
WetDryEnhancedWENO3 (本Phase实现) ⭐
```

**关键特性**:
1. 集成Phase 8.1正定性保持
2. 增强型界面检测
3. 界面特殊通量
4. 质量守恒监控

### 2. 核心方法

#### `_compute_rhs()` 覆盖
```python
def _compute_rhs(self, h: np.ndarray, Q: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    计算右端项（带湿干界面增强）
    """
    # Step 0: 检测湿干界面
    interface_info = self._detect_wet_dry_interface(h)

    # Step 1: 计算标准WENO3通量（继承自父类）
    F_h_weno, F_Q_weno = self._compute_weno3_flux(h, Q)

    # Step 2: 计算一阶通量（继承自Phase 8.1）
    F_h_first, F_Q_first = self._compute_first_order_flux(h, Q)

    # Step 3: 在湿干界面处使用特殊通量
    F_h_wd, F_Q_wd = self._compute_wet_dry_flux(h, Q, interface_info)

    # Step 4: 计算增强型正定性保持限制系数
    theta = self._compute_positivity_limiter_enhanced(
        h, Q, F_h_weno, F_Q_weno, F_h_first, F_Q_first, interface_info
    )

    # Step 5: 混合通量（三种通量）
    n = len(h)
    F_h = np.zeros(n + 1)
    F_Q = np.zeros(n + 1)

    for i in range(n + 1):
        # 判断界面
        is_wd_interface = self._is_interface_face(i, interface_info)

        if is_wd_interface:
            # 湿干界面：使用特殊通量
            F_h[i] = F_h_wd[i]
            F_Q[i] = F_Q_wd[i]
        else:
            # 非界面：使用正定性保持混合通量（Phase 8.1）
            F_h[i] = theta[i] * F_h_weno[i] + (1-theta[i]) * F_h_first[i]
            F_Q[i] = theta[i] * F_Q_weno[i] + (1-theta[i]) * F_Q_first[i]

    # Step 6: 计算时间导数
    dh_dt = np.zeros(n)
    dQ_dt = np.zeros(n)

    for i in range(n):
        dh_dt[i] = -(F_h[i+1] - F_h[i]) / self.dx
        dQ_dt[i] = -(F_Q[i+1] - F_Q[i]) / self.dx
        dQ_dt[i] += self._compute_source_term(h[i], Q[i], i)

    return dh_dt, dQ_dt
```

#### 界面检测
```python
def _detect_wet_dry_interface(self, h: np.ndarray) -> Dict:
    """检测湿干界面"""
    # （见"技术方案"部分的完整实现）
    pass
```

#### 界面特殊通量
```python
def _compute_wet_dry_flux(
    self, h: np.ndarray, Q: np.ndarray, interface_info: Dict
) -> Tuple[np.ndarray, np.ndarray]:
    """
    计算湿干界面特殊通量
    """
    n = len(h)
    F_h = np.zeros(n + 1)
    F_Q = np.zeros(n + 1)

    for i in range(n + 1):
        # 获取界面左右状态
        h_L, Q_L, h_R, Q_R = self._get_interface_states(i, h, Q)

        # 使用修正HLL通量
        F_h[i], F_Q[i] = self._hll_flux_wet_dry(h_L, Q_L, h_R, Q_R)

    return F_h, F_Q
```

### 3. 质量守恒监控

```python
def _check_mass_conservation(self):
    """
    检查质量守恒

    干床问题容易出现质量损失
    """
    total_mass = np.sum(self.h * self.dx * self.B)

    if not hasattr(self, 'initial_mass'):
        self.initial_mass = total_mass
        self.mass_history = [total_mass]
    else:
        self.mass_history.append(total_mass)

        # 计算相对误差
        mass_error = abs(total_mass - self.initial_mass) / self.initial_mass * 100

        if mass_error > 1.0:  # >1%
            print(f"⚠️ 警告：质量损失 {mass_error:.2f}% 在 t={self.t:.4f}s")
```

### 4. 统计信息

```python
def get_statistics(self) -> Dict:
    """获取统计信息"""
    stats = super().get_statistics()  # Phase 8.1统计

    # 添加湿干界面统计
    stats['wet_dry_interface_activations'] = self.wd_activations
    stats['interface_flux_usage_rate'] = self.wd_activations / self.step_count
    stats['mass_conservation_error'] = self._compute_mass_error()

    return stats
```

---

## 🧪 测试框架

### RP5-RP7测试套件

**文件**: `tests/verification/test_rp567_wet_dry.py` (~450行)

**测试流程**:
1. 运行原始WENO3（参考基准）
2. 运行Phase 8.1 PP-WENO3（对比）
3. 运行Phase 8.2湿干增强WENO3（目标）
4. 对比误差、稳定性和质量守恒

**关键函数**:
```python
def run_dry_bed_simulation(
    solver_class,
    h_L, u_L, h_R, u_R,
    test_name: str,
    n_cells: int = 500,
    t_end: float = 1.0,
    cfl: float = 0.2,
    **solver_kwargs
) -> Dict:
    """
    运行干床模拟

    返回:
    - 数值解
    - 精确解
    - 误差指标
    - 质量守恒误差
    - 统计信息
    """
    pass

def plot_dry_bed_comparison(results: list, save_path: str = None):
    """
    绘制对比图

    6个子图：
    1. 水深对比（RP5）
    2. 水深对比（RP6）
    3. 水深对比（RP7）
    4. 误差对比（柱状图）
    5. 质量守恒（时间序列）
    6. 界面激活率
    """
    pass
```

---

## 📊 预期性能

### 目标指标

| 测试 | 原始WENO3 | Phase 8.1 PP-WENO3 | Phase 8.2 湿干增强 | 改进幅度 |
|------|-----------|--------------------|--------------------|----------|
| **RP5** | >400% | ~300% | **<50%** | 87% ↓ |
| **RP6** | >400% | ~300% | **<50%** | 87% ↓ |
| **RP7** | >400% | ~250% | **<50%** | 87% ↓ |
| **质量守恒** | >1% | ~0.5% | **<0.1%** | 90% ↓ |
| **正定性** | 偶尔h<0 | h≥0 ✅ | h≥0 ✅ | 100% ✅ |

### 性能开销

**预期**:
- 计算时间增加: <30%（相对原始WENO3）
- 内存占用: +5%（界面检测数组）
- 界面检测开销: ~5%总时间

---

## 🎓 使用示例

### 基础使用

```python
from solvers.wet_dry_enhanced_weno3 import WetDryEnhancedWENO3

# 创建求解器
solver = WetDryEnhancedWENO3(
    width=10.0,
    length=100.0,
    n_cells=500,
    manning_n=0.0,
    slope=0.0,
    cfl=0.2,
    eps_pp=1e-10,          # 正定性保持阈值（Phase 8.1）
    theta_min=0.0,         # 最小限制系数
    wet_dry_threshold=1e-4,  # 湿干界面阈值（Phase 8.2）
    use_pp=True,           # 启用正定性保持
    use_wd_flux=True       # 启用湿干界面特殊通量
)

# 设置初值（RP5: 左干右湿）
h_L, u_L = 0.0, 0.0
h_R, u_R = 5.0, 0.0
x_dam = 50.0

x = solver.x
h_init = np.where(x <= x_dam, h_L, h_R)
Q_init = solver.B * np.where(x <= x_dam, h_L * u_L, h_R * u_R)

bc_left = {'type': 'transmissive'}
bc_right = {'type': 'transmissive'}
solver.initialize(h_init, Q_init, bc_left, bc_right)

# 运行
while solver.t < t_end:
    solver.step()

# 获取统计信息
stats = solver.get_statistics()
print(f"界面通量激活率: {stats['interface_flux_usage_rate']*100:.1f}%")
print(f"质量守恒误差: {stats['mass_conservation_error']:.4f}%")
```

### 运行测试

```bash
# 完整RP5-RP7对比测试
python tests/verification/test_rp567_wet_dry.py

# 预期输出：
# RP5-RP7干床测试：湿干增强WENO3 vs 原始WENO3
# ...
# RP5: 原始 >400% → PP-WENO3 ~300% → 湿干增强 XX%
# RP6: 原始 >400% → PP-WENO3 ~300% → 湿干增强 XX%
# RP7: 原始 >400% → PP-WENO3 ~250% → 湿干增强 XX%
# ✅ 全部达标！(<50%)
```

---

## 🔍 调试和诊断

### 诊断工具

```python
solver.print_wet_dry_statistics()
```

输出：
```
==================================================
湿干界面统计
==================================================
总时间步数: 500
正定性保持激活: 150 (30.0%)
界面通量激活: 80 (16.0%)
界面类型分布:
  - wet_to_dry: 45 (56.3%)
  - dry_to_wet: 30 (37.5%)
  - vacuum_forming: 5 (6.2%)
质量守恒误差: 0.05%
==================================================
```

### 参数调整

**wet_dry_threshold（湿干界面阈值）**:
- 默认: 1e-4
- 更严格: 1e-3（更早触发）
- 更宽松: 1e-5（接近eps_dry）

**use_wd_flux（界面通量开关）**:
- True: 启用界面特殊通量
- False: 只用正定性保持（退化为Phase 8.1）

---

## 📚 参考文献

### 湿干界面方法

1. **Toro, E. F. (2001)**. *Shock-Capturing Methods for Free-Surface Shallow Flows*. Wiley, Chapter 5.
   - 标准湿干界面处理方法

2. **Audusse, E., Bouchut, F., Bristeau, M. O., Klein, R., & Perthame, B. (2004)**. "A fast and stable well-balanced scheme with hydrostatic reconstruction for shallow water flows." *SIAM Journal on Scientific Computing*, 25(6), 2050-2065.
   - 水力静力重构方法

3. **Kurganov, A., & Petrova, G. (2007)**. "A second-order well-balanced positivity preserving central-upwind scheme for the Saint-Venant system." *Communications in Mathematical Sciences*, 5(1), 133-160.
   - 中心迎风格式+湿干界面

### 正定性保持

4. **Zhang, X., & Shu, C. W. (2010)**. "Positivity-preserving high order finite difference WENO schemes." *JCP*, 229(23), 8918-8934.
   - Phase 8.1基础方法

---

## 🚀 开发计划

### Week 1: 核心实现（5天）

**Day 1-2**: 界面检测机制
- 实现`_detect_wet_dry_interface()`
- 单元测试（人工构造界面）

**Day 3-4**: 界面特殊通量
- 实现`_hll_flux_wet_dry()`
- 单元测试（RP5/RP6简单情况）

**Day 5**: 集成与基础测试
- 集成到`WetDryEnhancedWENO3`类
- 运行RP5初步测试

### Week 2: 测试与优化（5天）

**Day 6-7**: RP5-RP7完整测试
- 实现`test_rp567_wet_dry.py`
- 运行全部三个测试
- 对比可视化

**Day 8**: 参数优化
- 调整`wet_dry_threshold`
- 优化界面限制策略

**Day 9**: 质量守恒验证
- 长时间模拟测试
- 质量守恒误差分析

**Day 10**: 文档与总结
- 更新技术文档（实测结果）
- 会话总结
- Git提交

---

## 🎯 成功标准

**Phase 8.2达标条件**:
- ✅ RP5 L2误差 < 50%
- ✅ RP6 L2误差 < 50%
- ✅ RP7 L2误差 < 50%
- ✅ 质量守恒误差 < 0.1%
- ✅ h ≥ 0恒成立（继承Phase 8.1）
- ✅ 性能开销 < 30%（相对原始WENO3）

**当前状态**: 🚧 规划完成，待实现

---

## 📝 技术要点总结

### 创新点

1. **三层防护架构**
   - Layer 1: 精确界面检测
   - Layer 2: 正定性保持（继承Phase 8.1）
   - Layer 3: 界面特殊通量

2. **界面类型细分**
   - wet_to_dry: 湿→干
   - dry_to_wet: 干→湿
   - vacuum_forming: 真空形成（RP7）

3. **渐进式降阶策略**
   - 光滑区域: 完全WENO3（θ=1.0）
   - 一般界面: 混合格式（θ≈0.3）
   - 湿干界面: 特殊通量或一阶（θ=0.0）

### 技术挑战

1. **界面识别的精确性**
   - Threshold选择影响检测精度
   - 需要平衡敏感性和稳健性

2. **三种通量的协调**
   - WENO3通量、一阶通量、界面通量
   - 需要平滑过渡，避免跳变

3. **质量守恒保证**
   - 干床问题容易出现质量损失
   - 需要特别监控和修正

---

## 🔗 与其他Phase的关系

**依赖**:
- ✅ **Phase 8.1**: 正定性保持WENO3（必需）

**支持后续**:
- ➡️ **Phase 8.3**: 工程案例库（溃坝、洪水等需要干床处理）
- ➡️ **Stage 9**: 二维扩展（2D湿干界面更复杂）

---

**文档版本**: 1.0
**作者**: Claude Code (Anthropic)
**创建日期**: 2025-10-31
**下次更新**: 开始实现后

---

**🤖 Generated with Claude Code**
**Co-Authored-By: Claude <noreply@anthropic.com>**
