# Phase 9.2 Well-Balanced优化 - HLLC求解器开发报告
## 开发状态：进行中 (85% → 90%)

**日期**: 2025-10-31
**阶段**: Phase 9.2 Well-Balanced Optimization
**完成度**: 90% (HLLC实现完成，但需调试)

---

## 📊 执行摘要

### 目标
实现HLLC (HLL with Contact) Riemann求解器以减少数值耗散，使Lake at Rest测试从~2m扰动提升到机器精度(<1e-10m)。

### 完成内容
1. ✅ 创建HLLC Riemann求解器模块 (`solvers/riemann_hllc.py`, 430行)
2. ✅ 集成HLLC到GodunvFVMSolver
3. ✅ 创建Lake at Rest对比测试
4. ⚠️ 发现HLLC实现存在bug (表现比HLL差)

### 当前状态
**Phase 9.2**: 85% → 90% (实现完成但未达到性能目标)

---

## 🎯 技术实现

### 1. HLLC Riemann求解器模块

**文件**: `solvers/riemann_hllc.py` (430行)

#### 核心函数

##### `hllc_flux_numba()`
```python
@njit
def hllc_flux_numba(h_L, Q_L, h_R, Q_R, B, g, eps_dry):
    """
    HLLC Riemann求解器 - 三波模型

    波速:
    - S_L: 左波速
    - S_star: 接触波速 (HLLC关键)
    - S_R: 右波速

    四个区域: L, L*, R*, R
    """
```

**理论基础**:
- Toro (2009) "Riemann Solvers", Chapter 10.3
- 接触波速 S_star 由动量守恒推导
- 星区状态由Rankine-Hugoniot条件确定

**实现特点**:
- Numba JIT编译优化
- 自动回退到HLL (分母接近零时)
- 干床处理
- 四区域通量选择

##### `hllc_flux_with_source_numba()`
```python
@njit
def hllc_flux_with_source_numba(h_L, Q_L, z_b_L, h_R, Q_R, z_b_R, B, g, eps_dry):
    """
    HLLC + Well-Balanced源项处理

    专门用于Well-Balanced格式
    结合水静力重构方法
    """
```

##### `compute_all_hllc_fluxes_numba()`
批量计算所有界面HLLC通量的Numba优化版本。

#### 验证函数

##### `validate_hllc_properties()`
测试HLLC求解器基本性质:
1. Lake at Rest (均匀水深) ✅ PASS
2. 对称性 ⚠️ (测试设计问题)
3. 干床 ✅ PASS

##### `compare_hll_vs_hllc()`
对比HLL和HLLC求解器差异。

---

### 2. 集成到GodunvFVMSolver

#### 导入HLLC模块
```python
# solvers/godunov_fvm_solver.py line 41-49
from .riemann_hllc import (
    hllc_flux_numba,
    compute_all_hllc_fluxes_numba
)
HLLC_AVAILABLE = True
```

#### 移除旧的HLLC禁用
```python
# 旧代码 (line 267-291): NotImplementedError - HLLC临时禁用
# 新代码 (line 277-284): HLLC已重新实现，启用
if self.riemann_solver == 'hllc' and not HLLC_AVAILABLE:
    raise ImportError("HLLC求解器需要riemann_hllc模块")
```

#### 更新_hllc_flux方法
```python
# 旧代码: 100行复杂实现 (有bug)
# 新代码: 简单包装到新模块
def _hllc_flux(self, h_L, Q_L, h_R, Q_R):
    return hllc_flux_numba(h_L, Q_L, h_R, Q_R, self.B, self.g, self.eps_dry)
```

#### 添加Numba快速路径
```python
# line 647, 860: 支持HLLC的Numba加速
if self.use_numba and (self.riemann_solver == 'hll' or self.riemann_solver == 'hllc'):
    ...
    if self.riemann_solver == 'hllc':
        # HLLC通量计算
        for i in range(len(h_L)):
            F_h[i], F_Q[i] = hllc_flux_numba(...)
```

---

### 3. Lake at Rest对比测试

**文件**: `tests/test_hllc_lake_at_rest.py` (350行)

#### 测试1: HLL vs HLLC短时间对比 (10秒)

**配置**:
- 100单元，1m网格
- 抛物线地形 (高斯凸起，最大2m)
- 平静水面 η=10m
- Wall边界
- Well-Balanced启用

**结果** (t=10s):
| 求解器 | Max η偏差 | Mean η偏差 | Max \|Q\| |
|--------|-----------|------------|----------|
| HLL    | 0.82m     | 0.23m      | 21 m³/s  |
| HLLC   | **1.98m** | **0.54m**  | **62 m³/s** |

**结论**: ❌ **HLLC表现比HLL差141%** (异常！)

#### 测试2: HLLC长时间稳定性 (100秒)

**结果**:
- t=10s: η偏差 1.98m
- t=20s: η偏差 2.12m
- t=50s: η偏差 2.13m
- **t=63s: ❌ NaN产生，模拟崩溃**

**结论**: ❌ HLLC存在稳定性问题，最终产生NaN

---

## 🐛 发现的问题

### 问题1: HLLC数值耗散比HLL更大

**预期**: HLLC通过分辨接触波，应该比HLL数值耗散更小
**实际**: HLLC的η偏差是HLL的2.4倍 (1.98m vs 0.82m)
**影响**: 无法达到Phase 9.2的精度目标

**可能原因**:
1. S_star (接触波速) 计算公式错误
2. 星区状态 (h_star, Q_star) 计算错误
3. 通量公式中的符号错误
4. 与Well-Balanced scheme的集成问题

### 问题2: HLLC长时间运行产生NaN

**预期**: HLLC应该保持稳定
**实际**: 63秒后产生NaN，模拟崩溃
**影响**: 无法用于生产环境

**可能原因**:
1. 分母接近零但未正确处理
2. 星区深度h_star变为负数
3. 波速S_star计算溢出
4. 数值不稳定性累积

---

## 🔬 调试分析

### 通量公式检查

**动量通量** (line 72-73):
```python
F_Q_L = Q_L * u_L + 0.5 * g * h_L * h_L * B
```

**验证**:
- Q_L = h_L * B * u_L
- Q_L * u_L = h_L * B * u_L^2
- Q_L^2 / A_L = (h_L * B * u_L)^2 / (h_L * B) = h_L * B * u_L^2
- ✅ Q_L * u_L = Q_L^2 / A_L (公式正确)

### S_star公式检查

**代码** (line 84-110):
```python
numerator = (F_Q_R - F_Q_L + S_L * Q_L - S_R * Q_R)
denominator = (A_L * (S_L - u_L) - A_R * (S_R - u_R))
S_star = numerator / denominator
```

**理论公式** (Toro 2009):
```
S_star = (P_R - P_L + h_L*u_L*(S_L - u_L) - h_R*u_R*(S_R - u_R)) /
         (h_L*(S_L - u_L) - h_R*(S_R - u_R))
```

**需要验证**: 代码公式是否等价于理论公式？

### 星区状态公式检查

**代码** (line 138-140):
```python
h_L_star = h_L * (S_L - u_L) / (S_L - S_star)
Q_L_star = h_L_star * B * S_star
```

**理论** (Rankine-Hugoniot):
- ✅ h_star公式正确
- ✅ Q_star = h_star * B * S_star (星区速度为S_star)

---

## 📝 待完成工作

### P1 - 高优先级 (必须完成)

#### 1. 修复S_star计算公式
**任务**: 验证并修正接触波速计算
**方法**:
1. 手工推导S_star公式
2. 对比Toro (2009) 标准公式
3. 检查符号和系数
4. 单元测试验证

**预估**: 2-4小时

#### 2. 修复NaN产生问题
**任务**: 找到并修复数值不稳定性
**方法**:
1. 添加详细调试输出
2. 检查分母接近零的情况
3. 验证h_star > 0约束
4. 添加数值保护措施

**预估**: 2-4小时

#### 3. 验证与Well-Balanced的集成
**任务**: 确保HLLC与Well-Balanced scheme正确配合
**方法**:
1. 测试HLLC without Well-Balanced
2. 对比hydrostatic reconstruction前后
3. 检查源项处理
4. 验证C-property保持

**预估**: 2-4小时

### P2 - 中优先级 (改进)

#### 4. 性能优化
**任务**: 优化HLLC计算效率
**方法**:
1. 向量化批量计算
2. 减少if分支
3. 优化Numba编译

**预估**: 1-2小时

#### 5. 完善测试
**任务**: 添加更多HLLC测试
**方法**:
1. Dam break对比
2. Riemann problem对比
3. Shock tube test
4. Dry bed test

**预估**: 1-2小时

---

## 📚 参考资料

### 学术文献

1. **Toro, E.F. (2009)**. "Riemann Solvers and Numerical Methods for Fluid Dynamics", 3rd Edition, Springer, Chapter 10.
   - HLLC求解器理论基础
   - 接触波处理方法

2. **Fraccarollo, L. & Toro, E.F. (1995)**. "Experimental and numerical assessment of the shallow water model for two-dimensional dam-break type problems", Journal of Hydraulic Research, 33(6), 843-864.
   - HLLC在浅水方程中的应用

3. **Audusse, E. et al. (2004)**. "A fast and stable well-balanced scheme with hydrostatic reconstruction for shallow water flows", SIAM J. Sci. Comput., 25(6), 2050-2065.
   - Well-Balanced格式与Riemann求解器的集成

### 代码参考

- `solvers/riemann_numba.py` - HLL求解器参考实现
- `solvers/godunov_fvm_solver.py` - 求解器主体
- `tests/analyze_well_balanced_details.py` - Well-Balanced诊断工具

---

## ✅ 阶段总结

### 已完成
1. ✅ HLLC Riemann求解器模块创建 (430行)
2. ✅ 集成到GodunvFVMSolver
3. ✅ Lake at Rest对比测试创建
4. ✅ 基础验证测试通过 (均匀水深, 干床)

### 遇到的挑战
1. ❌ HLLC性能不如HLL (出乎意料)
2. ❌ 长时间运行产生NaN
3. ⚠️ S_star计算公式可能有误
4. ⚠️ 与Well-Balanced集成可能有问题

### 下一步
1. **调试S_star公式** - 最高优先级
2. **修复NaN问题** - 稳定性关键
3. **验证Well-Balanced集成** - 精度关键

### Phase 9.2 完成度
**85% → 90%** (实现完成，但未达性能目标)

**剩余工作**:
- 调试HLLC实现 (10%)
- 达到Lake at Rest机器精度 (未完成)

---

## 🎯 经验教训

### 技术洞察

1. **HLLC并非"即插即用"**
   - 理论简单，实现复杂
   - 细节决定成败

2. **Well-Balanced集成需谨慎**
   - Riemann求解器需与源项处理协调
   - 接触波分辨可能放大重构误差

3. **数值稳定性至关重要**
   - NaN通常来自分母接近零
   - 需要robust的数值保护

### 开发建议

1. **先测试基础功能**
   - 不带Well-Balanced的HLLC
   - 简单Riemann问题
   - 逐步增加复杂性

2. **详细诊断输出**
   - 记录S_L, S_star, S_R
   - 记录h_star, Q_star
   - 记录通量F_h, F_Q

3. **对比标准实现**
   - Clawpack
   - SWASHES
   - Basilisk

---

**文档版本**: 1.0
**作者**: HydroClaude Development Team
**日期**: 2025-10-31
**状态**: 开发中 - 需调试

---

**🤖 Generated with Claude Code**
**Co-Authored-By**: Claude <noreply@anthropic.com>
