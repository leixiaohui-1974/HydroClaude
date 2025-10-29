# 临界流处理使用指南

**版本**: 1.0
**日期**: 2025-10-29
**面向用户**: 工程师、研究人员

---

## 🎯 快速开始

### 什么是临界流？

临界流是指**Froude数Fr ≈ 1**的流态，此时流速接近波速。常见于：
- 堰流、闸门流
- 河道喉道处
- 断面突变处
- 坡度转折点

### 为什么需要特殊处理？

临界流在数值模拟中容易产生：
- ❌ 数值振荡
- ❌ 收敛困难
- ❌ 质量守恒恶化
- ❌ 计算不稳定

HydroClaude提供的解决方案：
- ✅ **Entropy Fix** - 平滑跨音速区域
- ✅ **临界流特殊处理** - 自适应数值耗散

---

## 📖 基本用法

### 方法1: Python代码

```python
from solvers.godunov_fvm_weno3 import GodunvFVMWENO3

# 创建求解器
solver = GodunvFVMWENO3(
    width=10.0,
    length=1000.0,
    n_cells=200,
    manning_n=0.03,
    slope=0.0,
    entropy_fix=True,              # ← 启用entropy fix
    critical_flow_treatment=True   # ← 启用临界流处理
)
```

### 方法2: 配置文件

`config.json`:
```json
{
  "solver": {
    "type": "godunov_fvm",
    "spatial_order": 3,
    "riemann_solver": "hll",
    "cfl": 0.4,
    "entropy_fix": true,
    "critical_flow_treatment": true
  }
}
```

运行：
```python
from engine.simulation_engine import SimulationEngine

engine = SimulationEngine('config.json')
engine.initialize()
engine.run()
```

---

## 🔧 配置决策树

### 我应该启用哪些功能？

```
您的问题是...

├─ 一般河道模拟（无特殊流态）
│  └─ entropy_fix=True, critical_flow_treatment=False
│     理由：基本稳定性保障，无额外耗散
│
├─ 存在临界流（堰、喉道、断面突变）
│  └─ entropy_fix=True, critical_flow_treatment=True
│     理由：需要额外耗散稳定临界流区域
│
├─ 溃坝/激波问题（无摩阻或低摩阻）
│  ├─ 真实河道（n ≥ 0.01）
│  │  └─ entropy_fix=True, critical_flow_treatment=False
│  │     理由：摩阻提供足够耗散
│  └─ 无摩阻（n=0，学术测试）
│     └─ 可能不适用WENO3，考虑其他方法
│
└─ 不确定？
   └─ 从entropy_fix=True开始
      如果出现振荡→加上critical_flow_treatment=True
```

---

## 📊 常见场景配置

### 场景1: 河道喉道临界流

**描述**: 河道收缩处产生临界流

**配置**:
```python
solver = GodunvFVMWENO3(
    width=10.0,
    length=1000.0,
    n_cells=200,
    manning_n=0.03,        # 有摩阻
    slope=0.0,
    entropy_fix=True,
    critical_flow_treatment=True  # 必需
)
```

**预期效果**:
- ✅ 喉道处Fr平滑过渡到1.0
- ✅ 无数值振荡
- ✅ 质量守恒误差 < 5%

---

### 场景2: 堰流模拟

**描述**: 宽顶堰、溢流堰

**配置**:
```python
solver = GodunvFVMWENO3(
    width=10.0,
    length=500.0,
    n_cells=100,
    manning_n=0.02,        # 中等摩阻
    slope=0.001,
    entropy_fix=True,
    critical_flow_treatment=True  # 推荐
)
```

**关键点**:
- 堰顶通常为临界流
- 需要细化网格（dx < 5m）
- CFL建议≤0.4

---

### 场景3: 有摩阻水跃（MacDonald Test 4 Realistic）

**描述**: 超临界→亚临界转换，有摩阻

**配置**:
```python
solver = GodunvFVMWENO3(
    width=10.0,
    length=1000.0,
    n_cells=200,
    manning_n=0.03,        # 关键！有摩阻
    slope=0.0,
    entropy_fix=True,
    critical_flow_treatment=True  # 推荐
)
```

**注意**:
- ✅ n ≥ 0.01: 可以使用
- ❌ n = 0 (无摩阻): 不推荐，会发散

---

### 场景4: 一般河道（无临界流）

**描述**: 缓流或急流，无流态转换

**配置**:
```python
solver = GodunvFVMWENO3(
    width=10.0,
    length=1000.0,
    n_cells=100,
    manning_n=0.03,
    slope=0.001,
    entropy_fix=True,
    critical_flow_treatment=False  # 不需要
)
```

**理由**:
- 无临界流→不需要额外耗散
- 减少计算开销（虽然很小）
- 保持解的精度

---

### 场景5: 溃坝问题（有摩阻）

**描述**: 初始静止水体，突然溃坝

**配置**:
```python
solver = GodunvFVMWENO3(
    width=10.0,
    length=2000.0,
    n_cells=200,
    manning_n=0.025,       # 有摩阻
    slope=0.0,
    entropy_fix=True,
    critical_flow_treatment=False  # 通常不需要
)
```

**说明**:
- 溃坝波前可能短暂经过Fr=1
- 但主要是激波传播，不是临界流问题
- entropy_fix足够

---

## 🔍 诊断工具

### 如何判断是否有临界流？

```python
# 运行模拟后
Fr = solver.compute_froude_number()

# 统计
print(f"Fr范围: [{Fr.min():.3f}, {Fr.max():.3f}]")

# 检测临界流
is_critical = solver.is_critical_flow(Fr, threshold=0.1)
n_critical = np.sum(is_critical)
print(f"临界流单元: {n_critical}/{len(Fr)} ({n_critical/len(Fr)*100:.1f}%)")

# 流态分布
regime = solver.get_flow_regime(Fr)
print(f"亚临界: {np.sum(regime==0)}")
print(f"临界:   {np.sum(regime==1)}")
print(f"超临界: {np.sum(regime==2)}")
```

**输出示例**:
```
Fr范围: [0.234, 1.087]
临界流单元: 15/200 (7.5%)
亚临界: 150
临界:   15
超临界: 35
```

**解释**:
- Fr最大值接近1 → 有临界流
- 7.5%单元处于临界流 → 需要特殊处理
- **建议**: 启用`critical_flow_treatment=True`

---

### 如何判断数值是否稳定？

```python
# 质量守恒
mass_error = solver.get_mass_conservation_error()
print(f"质量误差: {abs(mass_error):.2f}%")

# 时间步长
print(f"当前dt: {solver.dt:.6f}s")

# 检查负水深
if np.any(solver.h < 0):
    print("⚠️ 警告：存在负水深！")
else:
    print("✓ 无负水深")

# 检查NaN
if np.any(np.isnan(solver.h)) or np.any(np.isnan(solver.Q)):
    print("❌ 错误：出现NaN！")
else:
    print("✓ 无NaN")
```

**健康标准**:
- ✅ 质量误差 < 5%
- ✅ dt保持在合理范围（> 1e-6s）
- ✅ 无负水深
- ✅ 无NaN

---

## ⚠️ 故障排除

### 问题1: 出现NaN

**症状**:
```
RuntimeWarning: invalid value encountered in divide
质量误差: nan%
```

**原因**: 数值发散，通常在临界流或激波处

**解决方案**:
```python
# 1. 启用临界流处理
critical_flow_treatment=True

# 2. 增加摩阻（如果合理）
manning_n=0.03  # 而非0.0

# 3. 降低CFL
cfl=0.3  # 而非0.5

# 4. 细化网格
n_cells=400  # 而非200
```

---

### 问题2: 数值振荡

**症状**:
```
水深剖面有明显的高频振荡
```

**原因**: 临界流或激波附近的数值不稳定

**解决方案**:
```python
# 1. 首先启用entropy fix
entropy_fix=True

# 2. 如果仍有振荡，启用临界流处理
critical_flow_treatment=True

# 3. 如果还不行，降低WENO的epsilon
weno_epsilon=1e-5  # 默认值，可试1e-6
```

---

### 问题3: dt变得极小（dt → 0）

**症状**:
```
进度: 23.7% | t=35.52s | dt=0.0000s | 步数: 10000
（卡住不动）
```

**原因**: 强激波导致CFL条件极度限制

**解决方案**:
```python
# 1. 设置最大时间步长
dt_max=0.5  # 秒

# 2. 增加摩阻（如果合理）
manning_n=0.03

# 3. 对于无摩阻强水跃
# → 目前WENO3不适用，考虑：
#   - 使用有摩阻版本
#   - 使用更高级的方法
#   - 等待混合流态求解器（开发中）
```

---

### 问题4: 解过于光滑

**症状**:
```
激波被明显抹平，解很光滑但不准确
```

**原因**: 数值耗散过度

**解决方案**:
```python
# 1. 禁用临界流处理
critical_flow_treatment=False

# 2. 或者降低耗散强度（修改源码）
# 在_hll_flux方法中:
alpha = 0.3 * (1.0 - abs(Fr_avg - 1.0) / 0.1)  # 原为0.5

# 3. 缩小临界流检测范围
# 在is_critical_flow调用中:
is_critical_flow(Fr, threshold=0.05)  # 原为0.1
```

---

### 问题5: 质量守恒误差过大

**症状**:
```
质量误差: 15.3%  （>5%）
```

**原因**:
- 可能是数值发散的前兆
- 或边界条件设置不当

**解决方案**:
```python
# 1. 检查边界条件
print(f"左边界: {solver.bc_left}")
print(f"右边界: {solver.bc_right}")

# 2. 启用临界流处理
critical_flow_treatment=True

# 3. 检查是否有负水深或NaN
print(f"最小水深: {solver.h.min():.6f}")
print(f"是否有NaN: {np.any(np.isnan(solver.h))}")

# 4. 细化网格
n_cells *= 2  # 加倍网格数
```

---

## 📈 性能优化建议

### 1. 按需启用功能

```python
# 基准配置（最快）
entropy_fix=False, critical_flow_treatment=False

# 标准配置（推荐）
entropy_fix=True, critical_flow_treatment=False
# 性能影响：~2%

# 完整配置（有临界流时）
entropy_fix=True, critical_flow_treatment=True
# 性能影响：~5%
```

**建议**: 从标准配置开始，有问题再升级

---

### 2. 网格分辨率

```python
# 粗网格（快速预览）
n_cells = 100  # dx ~ 10m

# 标准网格（工程应用）
n_cells = 200  # dx ~ 5m

# 细网格（高精度或临界流）
n_cells = 400  # dx ~ 2.5m
```

**规则**:
- 一般流动：dx < 10m
- 临界流区域：dx < 5m
- 激波/水跃：dx < 2m

---

### 3. CFL数选择

```python
# 保守（稳定优先）
cfl = 0.3

# 标准（平衡）
cfl = 0.5

# 激进（速度优先，可能不稳定）
cfl = 0.7
```

**建议**:
- 临界流问题：CFL ≤ 0.4
- 一般问题：CFL = 0.5
- 调试时：CFL = 0.3

---

## 📚 最佳实践

### 1. 开发工作流

```
1. 粗网格 + 无特殊处理
   ↓ （快速预览）
2. 标准网格 + entropy_fix=True
   ↓ （检查是否有临界流）
3. 如有临界流 + critical_flow_treatment=True
   ↓ （验证稳定性）
4. 细化网格（如需要）
   ↓ （最终精度）
5. 生产运行
```

---

### 2. 参数记录

建议在配置文件中记录选择理由：

```json
{
  "solver": {
    "entropy_fix": true,
    "critical_flow_treatment": true,
    "_comment": "堰流模拟，堰顶存在临界流，需要特殊处理"
  }
}
```

---

### 3. 结果验证

每次模拟后检查：

```python
# 1. 质量守恒
mass_error = solver.get_mass_conservation_error()
assert abs(mass_error) < 5.0, f"质量误差过大: {mass_error:.2f}%"

# 2. 物理合理性
assert solver.h.min() >= 0, "出现负水深"
assert np.all(np.isfinite(solver.h)), "出现NaN"

# 3. Fr分布
Fr = solver.compute_froude_number()
print(f"Fr范围: [{Fr.min():.3f}, {Fr.max():.3f}]")

# 4. 可视化（如果可能）
import matplotlib.pyplot as plt
plt.plot(solver.x, solver.h, label='水深')
plt.plot(solver.x, solver.z_b, label='河床', color='brown')
plt.legend()
plt.show()
```

---

## 🎓 学习资源

### 理论学习

1. **Froude数和临界流**
   - Chow, V. T. (1959). *Open-Channel Hydraulics*. Chapter 2.

2. **数值方法**
   - Toro, E. F. (2009). *Riemann Solvers and Numerical Methods*. Chapter 6.

3. **技术文档**
   - `docs/CRITICAL_FLOW_TREATMENT_TECHNICAL_DOC.md`

### 实践教程

1. **示例脚本**
   - `tests/numerical_methods/test_critical_flow_treatment.py`
   - `tests/numerical_methods/test_froude_number.py`

2. **标准测试**
   - MacDonald Test 1-5: `tests/standard_tests/test_macdonald.py`

---

## 💡 FAQ

### Q1: entropy_fix和critical_flow_treatment有什么区别？

**A**:
- **entropy_fix**: 平滑波速估计，防止跨音速振荡（通用）
- **critical_flow_treatment**: 在临界流区域增加耗散（特定问题）

类比：
- entropy_fix = 减震器（普遍有用）
- critical_flow_treatment = 四驱系统（特殊路况才需要）

---

### Q2: 我的问题没有临界流，启用这些会影响精度吗？

**A**:
- **entropy_fix=True**: 影响极小（<0.1%），建议总是启用
- **critical_flow_treatment=True**: 如果没有临界流（Fr不接近1），自动不激活，无影响

**推荐**: 不确定时，两个都启用，安全无害

---

### Q3: 为什么MacDonald Test 4（无摩阻）会失败？

**A**:
- 无摩阻强水跃是**极端工况**
- WENO3 + 当前临界流处理**不足以**处理无粘性激波
- **解决方案**:
  - 使用有摩阻版本（n≥0.01）✅
  - 等待混合流态求解器（Phase 2.1完成目标）

**重要**: 实际工程中**总是有摩阻**，无摩阻仅用于学术验证

---

### Q4: 如何判断我的网格是否足够细？

**A**:
```python
# 运行两次：粗网格 vs 细网格
solver_coarse = GodunvFVMWENO3(n_cells=100, ...)
solver_fine = GodunvFVMWENO3(n_cells=200, ...)

# 比较关键位置的水深
# 如果差异 < 5%，说明粗网格已足够
```

**经验规则**:
- 一般问题：n_cells ≥ L/10 (m)
- 临界流：n_cells ≥ L/5
- 激波：n_cells ≥ L/2

---

### Q5: 性能影响有多大？

**A**:
```
无特殊处理:         100% (基准)
+ entropy_fix:      102% (+2%)
+ critical_flow:    105% (+5%)
```

**结论**: 性能影响可忽略（< 5%）

---

## 📞 获取帮助

### 遇到问题？

1. **检查故障排除章节** (本文档)
2. **查看技术文档** (`CRITICAL_FLOW_TREATMENT_TECHNICAL_DOC.md`)
3. **运行测试套件** (`pytest tests/numerical_methods/ -v`)
4. **提交Issue** (包含配置、错误信息、诊断输出)

### 贡献

欢迎贡献：
- 更多测试案例
- 性能优化
- 文档改进
- Bug修复

---

**文档版本**: 1.0
**最后更新**: 2025-10-29
**维护者**: HydroClaude Team

祝您模拟成功！ 🚀
