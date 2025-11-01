# Stage 9: Well-Balanced格式开发计划

**日期**: 2025-10-31
**触发原因**: Case 02洪水演进案例揭示Well-Balanced需求
**目标**: 实现C-property保持能力，支持坡度河道长时间模拟

---

## 🎯 核心目标

实现**Hydrostatic Reconstruction**方法，使Godunov FVM求解器能够：
1. 精确保持静水平衡（Lake at Rest）
2. 在坡度河床上消除虚假流速
3. 支持河道洪水演进长时间模拟

---

## 📚 理论背景

### Well-Balanced属性 (C-property)

**定义**: 数值格式能够精确保持静水平衡状态：
```
η = h + z_b = constant (水面水平)
u = 0 (流速为零)
∂/∂x(gh²/2) + gh∂z_b/∂x = 0 (压力与重力精确平衡)
```

**问题**: 标准Godunov格式离散后：
- 压力项: ∂/∂x(gh²/2) 在cell界面计算
- 源项: gh∂z_b/∂x 在cell中心计算
- **不平衡**: 产生O(1)虚假流速

### Hydrostatic Reconstruction方法

**Audusse et al. (2004)**: "A Fast and Stable Well-Balanced Scheme..."

**核心思想**: 在界面处重构水深，隐式处理源项

**界面重构**:
```python
# 标准：直接使用cell值
h_L, h_R = h[i], h[i+1]

# Hydrostatic Reconstruction：考虑底高程
z_L, z_R = z_b[i], z_b[i+1]
dz = z_R - z_L

if dz > 0:  # 右侧底部更高
    h_L_star = max(0, h_L - dz)
    h_R_star = h_R
else:  # 左侧底部更高
    h_L_star = h_L
    h_R_star = max(0, h_R + dz)

# 用h_star计算通量
flux = HLL_flux(h_L_star, h_R_star, Q_L, Q_R)
```

**源项处理**:
```python
# 源项隐式包含在重构中
# 不需要显式计算gh∂z_b/∂x
S = 0  # 或者残余源项
```

---

## 🛠️ 实现计划

### Phase 9.1: 基础实现 (2天)

**任务**:
1. ✅ 在`GodunvFVMSolver.__init__`添加`well_balanced`参数
2. ✅ 实现`_hydrostatic_reconstruction()`方法
3. ✅ 修改`_compute_fluxes()`调用重构方法
4. ✅ 确保湿干界面兼容性

**代码位置**: `solvers/godunov_fvm_solver.py`

**关键方法**:
```python
def _hydrostatic_reconstruction(self, h_L, h_R, z_L, z_R, Q_L, Q_R):
    """
    Hydrostatic reconstruction for Well-Balanced property

    Args:
        h_L, h_R: 左右cell水深
        z_L, z_R: 左右cell底高程
        Q_L, Q_R: 左右cell流量

    Returns:
        h_L_star, h_R_star, Q_L_star, Q_R_star: 重构后的值
    """
    dz = z_R - z_L

    if dz > 0:
        h_L_star = max(0.0, h_L - dz)
        h_R_star = h_R
    else:
        h_L_star = h_L
        h_R_star = max(0.0, h_R + dz)

    # 流量与水深一致性调整
    if h_L > 1e-10:
        Q_L_star = Q_L * (h_L_star / h_L) if h_L_star > 1e-10 else 0.0
    else:
        Q_L_star = 0.0

    if h_R > 1e-10:
        Q_R_star = Q_R * (h_R_star / h_R) if h_R_star > 1e-10 else 0.0
    else:
        Q_R_star = 0.0

    return h_L_star, h_R_star, Q_L_star, Q_R_star
```

### Phase 9.2: 验证测试 (1天)

**测试1: Lake at Rest P0**
- 配置: 变化底高程，η = constant
- 目标: 水面扰动 < 1e-10 m
- 当前: 3.99-11.35 m ❌
- 预期: 机器精度误差 ✅

**测试2: Lake at Rest P0缓坡**
- 配置: 2m凸起，线性坡度
- 目标: 静水保持
- 当前: 3.99 m扰动 ❌
- 预期: < 1e-10 m ✅

**测试3: Lake at Rest P0陡坡**
- 配置: 5m台阶
- 目标: 静水保持（即使不连续）
- 当前: 11.35 m扰动 ❌
- 预期: < 1e-8 m ✅

**测试脚本**: `tests/test_lake_at_rest_wb.py`

### Phase 9.3: 案例验证 (1天)

**Case 02: 河道洪水演进**
- 配置: S₀=0.0005, L=50km
- 当前: t=1.0h NaN ❌
- 目标: 完整18h模拟 ✅

**性能指标**:
- ✅ 无NaN
- ✅ 洪峰削减分析
- ✅ 6面板可视化
- ✅ 物理结果合理

---

## 📊 技术挑战

### 挑战1: 湿干界面兼容性

**问题**: Hydrostatic Reconstruction可能与Phase 8.2的WD-Enhanced冲突

**解决方案**:
- 在干床处(h < h_dry)，跳过重构
- 保持PP-WENO3的正定性
- 测试溃坝案例确保兼容

### 挑战2: 正定性保持

**问题**: 重构后h_star可能为负

**解决方案**:
- `h_star = max(0, h - dz)`
- 在极端情况下限制流量
- 与limiter协调

### 挑战3: 激波捕捉能力

**问题**: Well-Balanced可能影响激波分辨率

**解决方案**:
- 仅在缓流区域(Fr < 0.5)应用
- 激波区域保持标准格式
- 自适应切换策略（可选）

---

## 🔬 测试策略

### 测试层次

**Level 1: 单元测试**
- Lake at Rest P0系列
- 各种底高程配置
- 干床/湿床边界

**Level 2: 基准测试**
- MacDonald斜坡测试
- Thacker旋转流
- 与解析解对比

**Level 3: 工程案例**
- Case 02 洪水演进
- 潮汐河口（如有）
- 水库调度（如有）

### 成功标准

| 测试 | 指标 | 目标值 | 当前值 |
|------|------|--------|--------|
| Lake at Rest P0.1 | 水面扰动 | < 1e-10 m | ~1e-14 m ✅ |
| Lake at Rest P0.2 | 水面扰动 | < 1e-10 m | 3.99 m ❌ |
| Lake at Rest P0.3 | 水面扰动 | < 1e-8 m | 11.35 m ❌ |
| Case 02 洪水演进 | 稳定时间 | 18 hours | 1.0 h ❌ |
| Case 01 溃坝 | 稳定时间 | 5 s | 7.4 s ✅ |

---

## 📐 实现细节

### GodunvFVMSolver修改

**1. 初始化参数**:
```python
def __init__(self, ..., well_balanced=False):
    self.well_balanced = well_balanced
```

**2. 通量计算修改**:
```python
def _compute_fluxes(self, h, Q, dt):
    fluxes_h = np.zeros(self.n_cells + 1)
    fluxes_Q = np.zeros(self.n_cells + 1)

    for i in range(self.n_cells + 1):
        # 获取左右状态
        h_L, h_R = ...
        Q_L, Q_R = ...

        if self.well_balanced:
            # Hydrostatic Reconstruction
            z_L = self.z_b[max(0, i-1)]
            z_R = self.z_b[min(self.n_cells-1, i)]
            h_L, h_R, Q_L, Q_R = self._hydrostatic_reconstruction(
                h_L, h_R, z_L, z_R, Q_L, Q_R
            )

        # HLL Riemann solver
        fluxes_h[i], fluxes_Q[i] = self._hll_flux(h_L, h_R, Q_L, Q_R)

    return fluxes_h, fluxes_Q
```

**3. 源项修改**:
```python
def _compute_source_terms(self, h, Q):
    if self.well_balanced:
        # 源项已隐式处理，仅保留摩擦项
        S_h = np.zeros(self.n_cells)
        S_Q = -self._compute_friction_source(h, Q)
    else:
        # 标准源项
        S_h = np.zeros(self.n_cells)
        S_Q = -self.g * h * self.dz_b_dx - self._compute_friction_source(h, Q)

    return S_h, S_Q
```

### 向后兼容

**确保现有功能不受影响**:
- `well_balanced=False` (默认): 保持原有行为
- 所有Phase 8测试应继续通过
- 文档更新反映新参数

---

## 📅 时间表

| Phase | 任务 | 预计时间 | 状态 |
|-------|------|---------|------|
| **9.1** | **基础实现** | **2天** | ⏳ |
| 9.1.1 | 添加well_balanced参数 | 0.5h | ⏳ |
| 9.1.2 | 实现_hydrostatic_reconstruction() | 2h | ⏳ |
| 9.1.3 | 修改_compute_fluxes() | 1h | ⏳ |
| 9.1.4 | 修改_compute_source_terms() | 1h | ⏳ |
| 9.1.5 | 湿干界面兼容性测试 | 2h | ⏳ |
| **9.2** | **验证测试** | **1天** | ⏳ |
| 9.2.1 | 实现Lake at Rest测试脚本 | 2h | ⏳ |
| 9.2.2 | 运行P0.1-P0.3测试 | 1h | ⏳ |
| 9.2.3 | 调试与优化 | 3h | ⏳ |
| **9.3** | **案例验证** | **1天** | ⏳ |
| 9.3.1 | 修改Case 02启用WB | 0.5h | ⏳ |
| 9.3.2 | 运行18h洪水演进 | 1h | ⏳ |
| 9.3.3 | 结果分析与可视化 | 2h | ⏳ |
| 9.3.4 | 文档更新 | 2h | ⏳ |
| **总计** | | **4天** | |

---

## 📖 参考文献

### 核心论文

1. **Audusse et al. (2004)**
   "A Fast and Stable Well-Balanced Scheme with Hydrostatic Reconstruction for Shallow Water Flows"
   SIAM Journal on Scientific Computing, 25(6), 2050-2065

2. **Bermudez & Vazquez (1994)**
   "Upwind methods for hyperbolic conservation laws with source terms"
   Computers & Fluids, 23(8), 1049-1071

3. **Liang & Marche (2009)**
   "Numerical resolution of well-balanced shallow water equations with complex source terms"
   Advances in Water Resources, 32(6), 873-884

### 开源实现参考

- **GeoClaw** (Clawpack): `src/2d/shallow/step2.f90`
- **ANUGA**: `shallow_water_domain.py`
- **Basilisk**: `saint-venant.h`

---

## ✅ 验收标准

### 必要条件

1. ✅ Lake at Rest P0.2: 水面扰动 < 1e-10 m
2. ✅ Lake at Rest P0.3: 水面扰动 < 1e-8 m
3. ✅ Case 02 洪水演进: 完整18h模拟无NaN
4. ✅ Case 01 溃坝: 保持Phase 8.2性能（≥7.4s）

### 充分条件

5. ✅ MacDonald斜坡测试: 与解析解误差 < 1%
6. ✅ Thacker旋转流: 周期误差 < 0.1%
7. ✅ 文档完善: 理论推导+实现说明+使用示例

---

## 🚀 启动

**下一步**:
1. 创建`tests/test_lake_at_rest_wb.py`测试框架
2. 在`godunov_fvm_solver.py`添加well_balanced参数
3. 实现_hydrostatic_reconstruction()方法

**预计完成时间**: 2025-11-04

---

**文档版本**: 1.0
**作者**: HydroClaude Team
**更新时间**: 2025-10-31

**🤖 Generated with Claude Code**
**Co-Authored-By**: Claude <noreply@anthropic.com>
