# Stage 6 数值方法完善 - 技术方案

**制定日期**: 2025-10-31
**目标**: 提升数值稳定性和精度，完善核心数值方法
**预计时间**: 6-8周

---

## 📊 当前状态评估

### 测试通过情况（2025-10-31）

| 测试类别 | 通过率 | 详情 |
|---------|--------|------|
| **MacDonald标准测试** | 5/6 (83%) | Test 4无摩阻水跃已知限制 |
| **Well-Balanced验证** | 4/4 (100%) | ✅ 机器精度级别 (~1e-14) |
| **混合流态处理** | 3/4 (75%) | 1个测试需要变坡度支持 |
| **干湿界面处理** | 5/5 (100%) | ✅ 全部通过 |
| **总计** | **21/24 (87.5%)** | **3个有意跳过** |

### 核心优势

✅ **已实现**：
- 严格Well-Balanced格式（机器精度）
- HLL/HLLC Riemann求解器
- Preissmann隐式时间推进
- 干湿界面处理（实际工程场景）
- WENO3/MUSCL高阶格式

### 主要限制

⚠️ **待改进**：
1. 不支持变坡度（S0数组）
2. 无摩阻强水跃数值振荡
3. WENO3边界处理可优化
4. 混合流态求解器待专门实现

---

## 🎯 Phase 6.1: 变坡度支持 (优先级最高)

### 问题描述

当前`HydrostaticCanalSolver`只支持标量`S0`（恒定坡度），无法模拟：
- 缓坡到陡坡转换
- 天然河道（变坡度）
- 梯级渠道
- 跌水/陡坡组合

### 技术方案

#### 1. 扩展数据结构 (1-2天)

```python
class HydrostaticCanalSolver:
    def __init__(self, ..., S0, ...):
        """
        Args:
            S0: 底坡 (float或ndarray)
                - float: 恒定坡度
                - ndarray: 变坡度 (长度=nx-1，每个单元的坡度)
        """
        # 标准化为数组
        if isinstance(S0, (int, float)):
            self.S0 = np.ones(nx-1) * float(S0)
        else:
            self.S0 = np.asarray(S0)
            assert len(self.S0) == nx-1, "S0数组长度应为nx-1"
```

#### 2. 修改底床高程计算 (1天)

```python
def compute_bed_elevation(self):
    """计算底床高程"""
    z_bed = np.zeros(self.nx)
    z_bed[0] = 0.0  # 起点高程

    # 累积坡度
    for i in range(self.nx-1):
        z_bed[i+1] = z_bed[i] - self.S0[i] * self.dx[i]

    return z_bed
```

#### 3. 修改静水重构 (2-3天)

```python
def compute_hydrostatic_reconstruction(self, i):
    """单元i的静水重构"""
    # 左右界面的底床高程
    z_L = self.z_bed[i]
    z_R = self.z_bed[i+1]
    z_interface = 0.5 * (z_L + z_R)

    # 水面高程
    eta_L = z_L + self.h[i]
    eta_R = z_R + self.h[i+1]

    # 重构水深
    h_L_star = max(0.0, eta_L - z_interface)
    h_R_star = max(0.0, eta_R - z_interface)

    return h_L_star, h_R_star
```

#### 4. 修改源项计算 (1-2天)

```python
def compute_source_term(self, i):
    """计算源项（摩阻+重力）"""
    # 摩阻项
    S_f = self.compute_friction_slope(i)

    # 重力项（使用局部坡度）
    S_0_local = self.S0[i]

    # 总源项
    S_total = self.B * self.g * self.h[i] * (S_0_local - S_f)

    return S_total
```

#### 5. 测试验证 (2-3天)

创建新测试：
```python
def test_variable_slope_canal():
    """测试变坡度渠道"""
    # 上游缓坡，下游陡坡
    S0_array = np.concatenate([
        np.ones(50) * 0.0005,  # 缓坡
        np.ones(50) * 0.01     # 陡坡
    ])

    solver = HydrostaticCanalSolver(
        length=1000.0,
        nx=101,
        B=10.0,
        S0=S0_array,  # 变坡度
        n=0.025
    )

    # 验证流态转换
    ...
```

### 预期收益

✅ 启用`test_subcritical_to_supercritical`测试
✅ 支持天然河道建模
✅ 提升工程适用性

### 工作量估计

- **开发**: 5-7天
- **测试**: 2-3天
- **文档**: 1天
- **总计**: 8-11天

---

## 🎯 Phase 6.2: WENO3边界处理优化 (次优先级)

### 问题描述

WENO3在边界处插值精度下降到一阶。

### 技术方案

#### 1. Ghost Cell方法 (2-3天)

```python
def apply_ghost_cells(self):
    """在边界外添加虚拟单元"""
    h_ext = np.zeros(self.nx + 4)  # 左右各2个ghost cells
    h_ext[2:-2] = self.h

    # 左边界
    if self.bc_left == BoundaryType.TRANSMISSIVE:
        h_ext[0] = h_ext[2]
        h_ext[1] = h_ext[2]
    elif self.bc_left == BoundaryType.REFLECTIVE:
        h_ext[0] = h_ext[4]
        h_ext[1] = h_ext[3]

    # 右边界（类似）
    ...

    return h_ext
```

#### 2. 高阶边界外推 (1-2天)

```python
def extrapolate_boundary(self, u, order=2):
    """高阶外推边界值"""
    if order == 2:
        # 二阶外推: u[-1] = 2*u[0] - u[1]
        u_left = 2*u[0] - u[1]
        u_right = 2*u[-1] - u[-2]
    elif order == 3:
        # 三阶外推: u[-1] = 3*u[0] - 3*u[1] + u[2]
        u_left = 3*u[0] - 3*u[1] + u[2]
        u_right = 3*u[-1] - 3*u[-2] + u[-3]

    return u_left, u_right
```

### 工作量估计

- **开发**: 3-5天
- **测试**: 2天
- **总计**: 5-7天

---

## 🎯 Phase 6.3: 混合流态专门求解器 (中期目标)

### 问题描述

无摩阻强水跃产生数值振荡（MacDonald Test 4）。

### 技术方案

#### 1. 局部Lax-Friedrichs方法 (3-4天)

```python
class MixedFlowSolver:
    """混合流态专门求解器"""

    def detect_regime_transition(self, Fr):
        """检测流态转换区域"""
        critical_zone = np.abs(Fr - 1.0) < 0.1
        return critical_zone

    def compute_llf_flux(self, h_L, h_R, hu_L, hu_R):
        """局部Lax-Friedrichs通量（Fr≈1区域）"""
        # 计算最大波速
        c_L = np.sqrt(self.g * h_L)
        c_R = np.sqrt(self.g * h_R)
        u_L = hu_L / h_L
        u_R = hu_R / h_R

        lambda_max = max(abs(u_L) + c_L, abs(u_R) + c_R)

        # LLF通量
        F_L = self.compute_flux(h_L, hu_L)
        F_R = self.compute_flux(h_R, hu_R)

        F_llf = 0.5 * (F_L + F_R) - 0.5 * lambda_max * (U_R - U_L)

        return F_llf
```

#### 2. 熵修正 (2-3天)

```python
def entropy_fix(self, lambda_wave, epsilon=0.1):
    """Harten熵修正"""
    if abs(lambda_wave) < epsilon:
        lambda_fixed = 0.5 * (lambda_wave**2 / epsilon + epsilon)
    else:
        lambda_fixed = abs(lambda_wave)

    return lambda_fixed
```

### 工作量估计

- **研究**: 3-5天
- **开发**: 5-7天
- **测试**: 3-5天
- **总计**: 11-17天

---

## 🎯 Phase 6.4: 性能优化和代码重构 (持续)

### 主要任务

1. **代码分析** (2天)
   - Profiling找出性能瓶颈
   - 内存使用优化

2. **向量化优化** (3天)
   - NumPy向量化操作
   - 减少Python循环

3. **文档完善** (2天)
   - API文档
   - 技术文档更新

---

## 📅 开发时间表

### 第1-2周：变坡度支持（最高优先级）
- [ ] Week 1: 数据结构扩展和基础实现
- [ ] Week 2: 测试和验证

### 第3周：WENO3边界优化
- [ ] Ghost cell方法实现
- [ ] 边界测试验证

### 第4-6周：混合流态求解器
- [ ] Week 4: 算法研究和设计
- [ ] Week 5: 实现和单元测试
- [ ] Week 6: 集成测试和验证

### 第7-8周：性能优化和文档
- [ ] 性能分析和优化
- [ ] 文档更新
- [ ] 发布Stage 6总结报告

---

## ✅ 成功标准

### 阶段性目标

**2周后**:
- ✅ 变坡度支持实现
- ✅ test_subcritical_to_supercritical通过
- ✅ 测试通过率 > 90%

**4周后**:
- ✅ WENO3边界优化完成
- ✅ MacDonald测试全部通过（包含Test 4）
- ✅ 混合流态求解器原型

**8周后**:
- ✅ 混合流态求解器完整实现
- ✅ 性能提升 > 20%
- ✅ 完整技术文档
- ✅ 准备进入Stage 7（国际标准测试验证）

---

## 📚 参考资料

1. **变坡度处理**
   - LeVeque (2002) - 非均匀网格和底床
   - HEC-RAS Technical Reference

2. **WENO边界处理**
   - Jiang & Shu (1996) - WENO格式
   - Shu (1998) - 高阶边界条件

3. **混合流态**
   - Toro (2009) - Riemann求解器
   - Chaudhry (2014) - 混合流态处理

4. **性能优化**
   - Python性能优化指南
   - NumPy向量化技巧

---

## 📝 风险和缓解措施

| 风险 | 影响 | 概率 | 缓解措施 |
|-----|------|------|---------|
| 变坡度实现复杂度超预期 | 中 | 低 | 分阶段实现，先简单后复杂 |
| 混合流态求解器稳定性问题 | 高 | 中 | 参考商业软件方法，充分测试 |
| 性能优化效果不明显 | 低 | 低 | Profile驱动优化，量化收益 |

---

## 🚀 下一步行动（本周）

### 立即开始（Day 1-3）

1. **实现变坡度数据结构** ✅ 高优先级
   - 修改`__init__`方法
   - 添加`S0`数组支持
   - 单元测试

2. **修改静水重构** ✅ 高优先级
   - 使用局部坡度
   - 更新源项计算

3. **创建测试用例** ✅ 高优先级
   - `test_variable_slope_uniform_flow`
   - `test_variable_slope_transition`

### 本周后期（Day 4-7）

4. **验证和调试**
   - 运行所有测试
   - 修复bug

5. **启用跳过的测试**
   - 移除`@pytest.mark.skip`
   - 验证通过

6. **文档更新**
   - 更新API文档
   - 添加使用示例

---

**立即行动**: 开始实现变坡度支持！

---

**🤖 Generated with Claude Code**
**Co-Authored-By: Claude <noreply@anthropic.com>**

---

**文档维护**: HydroClaude Development Team
**下次更新**: 完成变坡度支持后
