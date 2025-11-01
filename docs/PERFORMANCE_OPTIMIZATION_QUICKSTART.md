# HydroClaude 性能优化快速入门
## Numba JIT 加速 - 8-14倍性能提升

---

## 🚀 快速开始 (30秒)

### 安装Numba

```bash
pip install numba
```

### 验证安装

```bash
python -c "import numba; print(f'✅ Numba {numba.__version__} ready!')"
```

### 运行基准测试

```bash
python tests/numba_performance_validation.py
```

**预期输出**:
```
Average Speedup: 8.80x
Max Speedup: 14.13x
✅ Numba JIT Optimization Validated!
```

**就这么简单!** 🎉 你的HydroClaude现在快了8-14倍!

---

## 📊 性能对比

### 实测加速比

| 场景 | 无Numba | 有Numba | 加速 | 场景描述 |
|------|---------|---------|------|----------|
| **长渠道流动** | 23.9 ms/step | 1.7 ms/step | **14.1x** ⚡⚡⚡ | 1000单元, 2阶MUSCL |
| **溃坝模拟** | 6.9 ms/step | 0.7 ms/step | **10.3x** ⚡⚡ | 400单元, 激波捕捉 |
| **静水平衡** | 2.0 ms/step | 1.0 ms/step | **2.0x** ⚡ | 100单元, Well-Balanced |

### 实际应用示例

**场景**: 10公里河道洪水模拟, 1000单元, 3小时模拟时长

**无Numba**:
- 时间步: ~3000步
- 步均耗时: 23.9 ms
- 总耗时: **71.7秒** (~1.2分钟)

**有Numba**:
- 时间步: ~3000步
- 步均耗时: 1.7 ms
- 总耗时: **5.1秒**

**节省时间**: **66.6秒** (快14倍) ⚡

---

## 🔧 使用方法

### 方法1: 自动启用 (推荐)

安装Numba后,HydroClaude会自动启用JIT加速:

```python
from solvers.godunov_fvm_solver import GodunvFVMSolver

# Numba会自动启用 (如果已安装)
solver = GodunvFVMSolver(
    width=10.0,
    length=1000.0,
    n_cells=100,
    manning_n=0.03,
    slope=0.001
)

print(f"Numba启用: {solver.use_numba}")  # True (如果已安装Numba)
```

### 方法2: 显式控制

```python
# 强制启用Numba (如果未安装会警告)
solver = GodunvFVMSolver(..., use_numba=True)

# 强制禁用Numba (用于调试)
solver = GodunvFVMSolver(..., use_numba=False)
```

### 方法3: 环境检测

```python
from solvers.godunov_fvm_solver import NUMBA_AVAILABLE

if NUMBA_AVAILABLE:
    print("✅ Numba可用 - 高性能模式")
    # 运行大规模模拟
else:
    print("⚠️  Numba不可用 - 回退到纯Python")
    # 运行小规模模拟或安装Numba
```

---

## 🎯 适用场景

### 最适合Numba的场景 (10x+加速)

1. **大网格模拟** (>500单元)
   - 示例: 长河道、大型渠系
   - 加速比: 10-14x

2. **长时间模拟** (>100步)
   - 示例: 24小时洪水演进
   - 加速比: 10-14x

3. **二阶精度** (MUSCL重构)
   - 示例: 高精度激波捕捉
   - 加速比: 12-14x

4. **复杂Riemann求解器**
   - 示例: HLL, HLLC, Entropy修正
   - 加速比: 10-12x

### 中等收益场景 (2-5x加速)

1. **小网格** (50-500单元)
   - 加速比: 2-5x

2. **短时间模拟** (10-100步)
   - 加速比: 2-5x (首次运行可能更慢,因为JIT编译)

3. **一阶精度**
   - 加速比: 2-3x

### 低收益场景 (<2x加速)

1. **极小网格** (<50单元)
   - 加速比: 1-2x
   - 原因: JIT编译开销占主导

2. **单次运行**
   - 加速比: 0.5-1.5x (可能更慢!)
   - 原因: 包含JIT编译时间
   - 建议: 使用预热run或Numba缓存

---

## ⚡ 性能调优技巧

### 技巧1: 使用Numba缓存 (推荐)

Numba默认启用缓存,第二次运行会复用已编译的代码:

```python
# 第一次运行 - 包含编译 (~1-2秒编译开销)
solver.step()

# 后续运行 - 使用缓存 (10x+加速)
for _ in range(1000):
    solver.step()
```

### 技巧2: 预热优化

对于批量模拟,先做一次预热:

```python
# 预热 (触发JIT编译)
warmup_solver = GodunvFVMSolver(..., use_numba=True)
warmup_solver.initialize(...)
for _ in range(10):
    warmup_solver.step()

# 正式模拟 (已编译, 直接快速执行)
for scenario in scenarios:
    solver = GodunvFVMSolver(..., use_numba=True)
    solver.initialize(...)
    solver.run(...)  # 立即获得10x加速
```

### 技巧3: 并行化 (高级)

对于多个独立模拟,使用`multiprocessing`:

```python
from multiprocessing import Pool

def run_simulation(params):
    solver = GodunvFVMSolver(**params, use_numba=True)
    # ... 运行模拟
    return results

# 8核并行 × 10x Numba加速 = 80x总加速!
with Pool(8) as pool:
    results = pool.map(run_simulation, scenarios)
```

---

## 🐛 故障排除

### 问题1: Numba未自动启用

**症状**:
```python
print(solver.use_numba)  # False
```

**解决**:
```bash
# 检查是否安装
python -c "import numba"

# 如果报错ModuleNotFoundError
pip install numba

# 重新运行程序
```

### 问题2: JIT编译失败

**症状**:
```
NumbaError: cannot compile function ...
```

**解决**:
```bash
# 启用Numba调试
export NUMBA_WARNINGS=1
export NUMBA_DISABLE_JIT=0

python your_script.py

# 检查错误信息,可能是类型不匹配
# 如果无法解决,禁用Numba:
solver = GodunvFVMSolver(..., use_numba=False)
```

### 问题3: 性能未达预期

**症状**: 只有2x加速,预期是10x

**可能原因**:
1. **首次运行** - 包含JIT编译开销
   - 解决: 运行多次或使用预热

2. **网格太小** - <50单元
   - 解决: 增大网格或禁用Numba

3. **步数太少** - <10步
   - 解决: 运行更长时间

**诊断**:
```python
import time

# 首次运行 (含编译)
start = time.time()
for _ in range(100):
    solver.step()
time1 = time.time() - start
print(f"首次100步: {time1:.3f}s")

# 二次运行 (使用缓存)
start = time.time()
for _ in range(100):
    solver.step()
time2 = time.time() - start
print(f"二次100步: {time2:.3f}s")
print(f"缓存加速比: {time1/time2:.1f}x")  # 应该接近1.0x (已经很快)
```

---

## 📚 更多信息

### 详细技术报告
- [Phase 8.4 性能优化报告](PHASE_8_4_PERFORMANCE_OPTIMIZATION_REPORT.md)
  - 详细基准测试结果
  - 性能分析和瓶颈识别
  - 对比商业软件

### 代码实现
- `solvers/riemann_numba.py` - Numba优化Riemann求解器
- `solvers/numba_kernels.py` - 高级Numba计算内核
- `tests/numba_performance_validation.py` - 性能验证脚本

### 官方文档
- Numba官方: https://numba.pydata.org/
- HydroClaude文档: `docs/`

---

## ✅ 检查清单

安装和验证:
- [ ] 运行 `pip install numba`
- [ ] 验证 `python -c "import numba; print(numba.__version__)"`
- [ ] 运行 `python tests/numba_performance_validation.py`
- [ ] 确认看到 "Average Speedup: 8.80x"

使用:
- [ ] 在代码中创建 `GodunvFVMSolver(..., use_numba=True)`
- [ ] 检查 `solver.use_numba == True`
- [ ] 运行模拟,观察性能提升

优化 (可选):
- [ ] 对于批量模拟,添加预热步骤
- [ ] 对于多场景,考虑使用`multiprocessing`并行化
- [ ] 监控性能指标,确认达到预期加速比

---

## 🎉 总结

**3个关键点**:

1. **安装简单**: `pip install numba` (30秒)
2. **自动启用**: 无需代码修改
3. **性能惊人**: 8-14倍加速 ⚡

**立即体验**:
```bash
pip install numba
python tests/numba_performance_validation.py
```

享受HydroClaude的超高性能吧! 🚀

---

**文档版本**: 1.0
**作者**: HydroClaude Development Team
**日期**: 2025-10-31
