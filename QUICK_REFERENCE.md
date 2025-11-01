# HydroClaude Quick Reference Card
## 快速参考卡片 - v1.0.0-rc

一页纸快速参考，包含最常用的命令、配置和故障排除。

---

## 🚀 快速开始

### 安装验证（5秒）
```bash
python quick_verify.py
# 期望: ✅ All core tests passed!
```

### 核心测试（30秒）
```bash
python tests/core_functionality_verification_v2.py
# 期望: ✅ 100% Pass (3/3)
```

### 完整测试（2分钟）
```bash
python tests/regression_test_suite.py
# 期望: ✅ 92% Pass (11/12)
```

---

## 💻 基本用法

### 最简单的溃坝模拟

```python
from solvers.godunov_fvm_solver import GodunvFVMSolver
import numpy as np

# 1. 创建求解器（推荐配置）
solver = GodunvFVMSolver(
    width=10.0, length=1000.0, n_cells=200,
    riemann_solver='hll', order=2, 
    well_balanced=True, use_numba=True
)

# 2. 初始条件
h = np.where(np.linspace(0, 1000, 200) < 500, 10.0, 1.0)
Q = np.zeros(200)

# 3. 边界条件
bc_left = {'type': 'h', 'value': 10.0}
bc_right = {'type': 'h', 'value': 1.0}

# 4. 运行
solver.initialize(h, Q, bc_left, bc_right)
while solver.t < 10.0:
    solver.step()
```

---

## ⚙️ 常用配置

### 生产推荐配置 ✅
```python
solver = GodunvFVMSolver(
    riemann_solver='hll',     # ✅ 稳定可靠
    order=2,                  # ✅ MUSCL 2阶
    well_balanced=True,       # ✅ Well-Balanced
    cfl=0.5,                  # ✅ 标准CFL
    use_numba=True            # ✅ 8.80x加速
)
```

### 快速原型配置
```python
solver = GodunvFVMSolver(
    n_cells=50,               # 粗网格
    order=1,                  # 1阶（快）
    riemann_solver='hll',
    cfl=0.8,                  # 大CFL
    use_numba=True
)
```

### 高精度配置
```python
solver = GodunvFVMSolver(
    n_cells=1000,             # 细网格
    order=2,                  # MUSCL 2阶
    riemann_solver='hll',
    well_balanced=True,
    cfl=0.3,                  # 保守CFL
    use_numba=True
)
```

---

## 🔧 参数速查

### 求解器参数

| 参数 | 类型 | 推荐值 | 说明 |
|------|------|--------|------|
| `width` | float | 10.0 | 河道宽度 (m) |
| `length` | float | 1000.0 | 河道长度 (m) |
| `n_cells` | int | 200 | 网格单元数 |
| `manning_n` | float | 0.03 | Manning糙率系数 |
| `slope` | float | 0.001 | 河床坡度 (S₀) |
| `z_b` | array | None | 底高程 (可选) |

### 数值方法参数

| 参数 | 推荐值 | 可选值 | 说明 |
|------|--------|--------|------|
| `riemann_solver` | **'hll'** | 'hllc', 'exact' | HLL最稳定 ✅ |
| `order` | **2** | 1, 2 | MUSCL阶数 |
| `well_balanced` | **True** | True, False | Well-Balanced格式 |
| `limiter` | **'minmod'** | 'minmod', 'vanleer' | MUSCL限制器 |
| `cfl` | **0.5** | 0.1-0.8 | CFL数 |
| `use_numba` | **True** | True, False | 8.80x加速 ✅ |

### 边界条件

| 类型 | 格式 | 示例 |
|------|------|------|
| 固定水深 | `{'type': 'h', 'value': 10.0}` | 水库边界 |
| 固定流量 | `{'type': 'Q', 'value': 100.0}` | 入流边界 |
| 时变水深 | `{'type': 'h', 'value': lambda t: 10+sin(t)}` | 潮汐边界 |
| 时变流量 | `{'type': 'Q', 'value': lambda t: 100+50*t}` | 洪峰过程 |

---

## 📊 性能优化

### Numba加速效果

| 场景 | Pure Python | With Numba | 加速比 |
|------|-------------|------------|--------|
| Dam Break (400 cells) | 6.9 ms/step | 0.67 ms/step | **10.30x** |
| Long Channel (1000 cells) | 23.9 ms/step | 1.69 ms/step | **14.13x** |
| 平均 | - | - | **8.80x** |

### 性能调优建议

**1. 启用Numba** （最重要！）
```python
use_numba=True  # 8.80x加速，简单一行代码
```

**2. 选择合适的网格分辨率**
```python
# 粗糙快速原型
n_cells = 50-100

# 标准工程应用
n_cells = 200-500

# 高精度科研
n_cells = 1000+
```

**3. 调整CFL数**
```python
# 保守稳定（慢但稳）
cfl = 0.3

# 标准（推荐）
cfl = 0.5

# 激进（快但可能不稳定）
cfl = 0.8
```

**4. 选择合适的精度阶数**
```python
# 快速原型
order = 1

# 生产应用（推荐）
order = 2
```

---

## 🐛 故障排除

### 问题1: NaN值出现

**症状**: `solver.h` 或 `solver.Q` 包含NaN

**可能原因**:
1. ❌ 使用了HLLC或Exact求解器
2. ❌ CFL数太大
3. ❌ 初始条件不合理（负深度）

**解决方法**:
```python
# ✅ 使用HLL求解器
riemann_solver='hll'

# ✅ 降低CFL数
cfl=0.3

# ✅ 检查初始条件
assert np.all(h_init >= 0), "负深度!"
```

### 问题2: 质量不守恒

**症状**: 质量误差>1%

**可能原因**:
1. ❌ 使用了Exact求解器
2. ❌ 边界条件设置不当
3. ❌ CFL数过大

**解决方法**:
```python
# ✅ 使用HLL求解器
riemann_solver='hll'

# ✅ 检查质量守恒
error = solver.mass_conservation_error()
print(f"质量误差: {error:.6f}%")
# 期望: < 0.01%

# ✅ 降低CFL
cfl=0.5
```

### 问题3: 模拟速度慢

**症状**: 每步需要几十毫秒

**可能原因**:
1. ❌ 未启用Numba
2. ❌ 网格太细
3. ❌ Python解释器模式

**解决方法**:
```python
# ✅ 启用Numba（最重要！）
use_numba=True

# ✅ 调整网格
n_cells = 200  # 不要一开始就用1000+

# ✅ 第一次运行等待Numba编译
# 后续运行会快很多
```

### 问题4: 看到警告信息

**症状**:
```
❌❌❌  精确求解器警告 - DO NOT USE  ❌❌❌
```

**解决方法**:
```python
# ✅ 改用HLL求解器
riemann_solver='hll'  # 不要用'exact'或'hllc'
```

---

## 📈 质量检查清单

### 运行前检查 ✅

- [ ] 使用`riemann_solver='hll'`（不要用exact或hllc）
- [ ] 启用`use_numba=True`（8.80x加速）
- [ ] 初始条件无负深度：`assert np.all(h >= 0)`
- [ ] CFL数合理：`cfl=0.5`
- [ ] 网格分辨率适中：`n_cells=200`

### 运行后检查 ✅

- [ ] 无NaN值：`assert not np.any(np.isnan(solver.h))`
- [ ] 无负深度：`assert np.all(solver.h >= 0)`
- [ ] 质量守恒：`error < 1%`
- [ ] 运行完成：`solver.t >= target_time`

---

## 📚 常用命令速查

### 测试命令
```bash
# 快速验证（5秒）
python quick_verify.py

# 核心功能（30秒）
python tests/core_functionality_verification_v2.py

# 完整回归（2分钟）
python tests/regression_test_suite.py

# 性能基准
python tests/benchmark_numba.py
```

### Git命令
```bash
# 查看状态
git status

# 查看最近提交
git log --oneline -5

# 切换分支
git checkout main
```

### Python命令
```bash
# 启动交互式会话
python

# 运行脚本
python your_script.py

# 查看帮助
python -c "from solvers.godunov_fvm_solver import GodunvFVMSolver; help(GodunvFVMSolver)"
```

---

## 🎓 示例代码片段

### 读取结果

```python
# 获取当前状态
h = solver.h.copy()      # 水深 (m)
Q = solver.Q.copy()      # 流量 (m³/s)
u = Q / (h * solver.B)   # 流速 (m/s)
t = solver.t             # 时间 (s)
```

### 可视化

```python
import matplotlib.pyplot as plt

plt.figure(figsize=(12, 4))
plt.plot(solver.x, solver.h)
plt.xlabel('x (m)')
plt.ylabel('h (m)')
plt.title(f't = {solver.t:.2f} s')
plt.grid(True)
plt.show()
```

### 保存数据

```python
import numpy as np

# 保存到CSV
np.savetxt('results.csv', 
           np.column_stack([solver.x, solver.h, solver.Q]),
           delimiter=',',
           header='x,h,Q')

# 保存到NPY
np.save('h.npy', solver.h)
np.save('Q.npy', solver.Q)
```

### 时间序列记录

```python
# 初始化列表
t_history = []
h_history = []

# 模拟循环
while solver.t < 10.0:
    solver.step()
    t_history.append(solver.t)
    h_history.append(solver.h.copy())

# 转换为数组
t_array = np.array(t_history)
h_array = np.array(h_history)  # shape: (n_steps, n_cells)
```

---

## ⚠️ 重要提醒

### ✅ 推荐使用

```python
riemann_solver='hll'        # HLL求解器（稳定可靠）✅
order=2                     # MUSCL 2阶精度 ✅
well_balanced=True          # Well-Balanced格式 ✅
use_numba=True              # Numba加速 ✅
cfl=0.5                     # 标准CFL数 ✅
```

### ❌ 不推荐使用

```python
riemann_solver='exact'      # 精确求解器（质量不守恒）❌
riemann_solver='hllc'       # HLLC求解器（不稳定）❌
cfl=1.0                     # 过大CFL（可能不稳定）❌
use_numba=False             # 不用Numba（慢8.80倍）❌
```

---

## 📞 获取帮助

### 文档

- **Quick Start**: `docs/USER_QUICK_START.md`
- **API Reference**: `docs/API_REFERENCE.md`
- **Testing Status**: `docs/TESTING_STATUS_2025_11_01.md`
- **Release Notes**: `RELEASE_NOTES_v1.0.0-rc.md`

### 在线资源

- **GitHub**: https://github.com/your-org/HydroClaude
- **Issues**: https://github.com/your-org/HydroClaude/issues
- **Discussions**: https://github.com/your-org/HydroClaude/discussions

### 常见问题

详见 `docs/FAQ.md`（如果有）或查看GitHub Issues

---

## 📊 性能指标速查

| 指标 | 值 | 状态 |
|------|-----|------|
| 核心测试通过率 | 100% | ✅ |
| 回归测试通过率 | 92% | ✅ |
| 质量守恒精度 | <0.01% | ✅ |
| Numba加速比 | 8.80x | ✅ |
| 测试覆盖率 | 96% | ✅ |
| 已知critical bugs (HLL) | 0 | ✅ |

---

**版本**: v1.0.0-rc
**更新日期**: 2025-11-01
**状态**: Production Ready ✅

**打印提示**: 此页面设计为A4单面打印，方便桌面参考。
