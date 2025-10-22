# HydroClaude 快速入门指南

欢迎使用 HydroClaude！本指南将帮助您在 **10 分钟内** 快速上手水力学仿真与优化。

---

## 📋 目录

1. [安装](#1-安装)
2. [第一个示例](#2-第一个示例---明渠流动)
3. [使用 YAML 配置](#3-使用-yaml-配置)
4. [求解器选择](#4-求解器选择)
5. [性能基准测试](#5-性能基准测试)
6. [常见问题](#6-常见问题)
7. [下一步](#7-下一步)

---

## 1. 安装

### 方式 A: 开发模式安装（推荐）

```bash
# 克隆仓库
git clone https://github.com/leixiaohui-1974/HydroClaude.git
cd HydroClaude

# 安装（开发模式 + 开发工具 + 彩色日志）
pip install -e .[dev,logging]
```

### 方式 B: 正式安装

```bash
pip install .
```

### 验证安装

```bash
# 检查版本
python -c "import numpy; print('NumPy:', numpy.__version__)"
python -c "import scipy; print('SciPy:', scipy.__version__)"

# 运行测试（可选）
pytest tests/
```

**预期结果**: 164/164 测试通过 ✅

---

## 2. 第一个示例 - 明渠流动

创建文件 `my_first_canal.py`:

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""我的第一个明渠流动模拟"""

import numpy as np
import matplotlib.pyplot as plt

from physics.steady_saint_venant import SteadySaintVenantSystem
from solvers.newton_solver import NewtonSolver
from utils.canal_utils import compute_steady_uniform_flow

# ========== 1. 定义渠道参数 ==========
length = 1000.0      # 渠道长度 (m)
nx = 21              # 网格点数
B = 10.0             # 渠道宽度 (m)
S0 = 0.001           # 渠底坡度
n = 0.025            # Manning 糙率系数
Q_target = 10.0      # 目标流量 (m³/s)

# ========== 2. 创建物理系统 ==========
system = SteadySaintVenantSystem(
    length=length,
    nx=nx,
    B=B,
    S0=S0,
    n=n,
    pseudo_dt=0.1
)

# ========== 3. 设置边界条件 ==========
h_uniform = compute_steady_uniform_flow(Q_target, B, S0, n)

system.set_boundary_conditions(
    Q_upstream=Q_target,           # 上游流量
    h_upstream=h_uniform,          # 上游水深
    h_downstream=h_uniform * 1.1   # 下游壅水
)

# ========== 4. 准备初值 ==========
h_init = np.ones(nx) * h_uniform
Q_init = np.ones(nx) * Q_target
U_init = system.pack_state(h_init, Q_init)
system.U_prev = U_init.copy()

# ========== 5. 求解 ==========
solver = NewtonSolver(
    max_iter=20,
    tol_residual=1e-6,
    linear_solver='direct',
    line_search=True,
    verbose=True
)

U_solution, info = solver.solve(
    U_init=U_init,
    residual_func=system.compute_residual,
    jacobian_func=system.compute_jacobian
)

# ========== 6. 提取结果 ==========
h_solution, Q_solution = system.unpack_state(U_solution)

# ========== 7. 可视化 ==========
x = np.linspace(0, length, nx)

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))

# 水深分布
ax1.plot(x, h_solution, 'b-o', label='水深')
ax1.axhline(h_uniform, color='r', linestyle='--', label='均匀流水深')
ax1.set_xlabel('距离 (m)')
ax1.set_ylabel('水深 (m)')
ax1.set_title('水深沿程分布')
ax1.legend()
ax1.grid(True)

# 流量分布
ax2.plot(x, Q_solution, 'g-o', label='流量')
ax2.axhline(Q_target, color='r', linestyle='--', label='目标流量')
ax2.set_xlabel('距离 (m)')
ax2.set_ylabel('流量 (m³/s)')
ax2.set_title('流量沿程分布')
ax2.legend()
ax2.grid(True)

plt.tight_layout()
plt.savefig('my_first_canal.png', dpi=150)
print("\n✅ 结果已保存到: my_first_canal.png")

# ========== 8. 打印结果 ==========
print("\n" + "="*60)
print("求解结果")
print("="*60)
print(f"收敛: {info['converged']}")
print(f"迭代次数: {info['iterations']}")
print(f"最终残差: {info['residual_norm']:.2e}")
print(f"水深范围: {h_solution.min():.3f} ~ {h_solution.max():.3f} m")
print(f"流量范围: {Q_solution.min():.3f} ~ {Q_solution.max():.3f} m³/s")
print("="*60)
```

### 运行

```bash
python my_first_canal.py
```

**预期输出**:
```
Newton求解器: 迭代 1, 残差: 1.23e-02
Newton求解器: 迭代 2, 残差: 2.45e-04
Newton求解器: 迭代 3, 残差: 3.67e-08
✓ Newton收敛

============================================================
求解结果
============================================================
收敛: True
迭代次数: 3
最终残差: 3.67e-08
水深范围: 1.925 ~ 2.112 m
流量范围: 9.998 ~ 10.002 m³/s
============================================================

✅ 结果已保存到: my_first_canal.png
```

---

## 3. 使用 YAML 配置

HydroClaude 支持 YAML 配置文件，无需编写 Python 代码即可定义复杂系统。

### 3.1 查看示例配置

```bash
# 查看简单渠道配置
cat config/simple_canal.yaml

# 查看三级梯级水电站配置
cat config/example_system.yaml

# 查看灌区配水系统配置
cat config/irrigation_system.yaml

# 查看防洪调度系统配置
cat config/flood_control.yaml

# 查看城市供水系统配置
cat config/urban_water_supply.yaml
```

### 3.2 加载并使用配置

```python
from core.config import SystemConfig

# 加载配置
config = SystemConfig.from_yaml('config/simple_canal.yaml')

# 验证配置
errors = config.validate()
if errors:
    print("配置错误:", errors)
else:
    print("✓ 配置验证通过")

# 访问配置
print(f"渠道数量: {len(config.canals)}")
print(f"闸门数量: {len(config.gates)}")
print(f"仿真时长: {config.simulation.duration} 秒")
```

### 3.3 创建自定义配置

复制并修改现有配置：

```bash
# 复制简单渠道配置
cp config/simple_canal.yaml config/my_canal.yaml

# 编辑配置
vim config/my_canal.yaml  # 或使用您喜欢的编辑器
```

修改参数：
```yaml
canals:
  - id: my_canal
    length: 2000.0      # 修改长度
    nx: 41              # 修改网格点数
    width: 15.0         # 修改宽度
    slope: 0.0008       # 修改坡度
    roughness: 0.020    # 修改糙率
```

---

## 4. 求解器选择

HydroClaude 提供多种求解器，适用于不同场景。

### 4.1 Newton 法（快速、适合好初值）

```python
from solvers.newton_solver import NewtonSolver

solver = NewtonSolver(
    max_iter=20,
    tol_residual=1e-6,
    linear_solver='direct',  # 'direct' 或 'gmres'
    line_search=True,
    verbose=True
)

U_solution, info = solver.solve(U_init, residual_func, jacobian_func)
```

**适用场景**:
- 初值较好（如均匀流）
- 中小规模问题（nx < 500）
- 需要快速收敛

### 4.2 延拓法（鲁棒、适合差初值）

```python
from solvers.continuation_solver import ContinuationSolver

solver = ContinuationSolver(
    system=system,
    pseudo_dt_sequence=[10.0, 1.0, 0.1],
    verbose=True
)

U_solution, info = solver.solve(U_init)
```

**适用场景**:
- 初值较差
- 强非线性问题
- 需要高鲁棒性

### 4.3 混合求解器（智能、自动选择）

```python
from solvers.hybrid_solver_enhanced import HybridSolverEnhanced, SolverStrategy

solver = HybridSolverEnhanced(
    max_strategies=3,
    quick_newton_trials=5,
    enable_strategy_memory=True,
    verbose=True
)

U_solution, info = solver.solve(
    U_init,
    residual_func,
    jacobian_func,
    preferred_strategy=SolverStrategy.AUTO  # 自动选择最优策略
)

print(f"使用策略: {info['strategy_used']}")
print(f"尝试次数: {info['attempts']}")
```

**适用场景**:
- 不确定哪种求解器最好
- 需要自动降级备份
- 追求最高成功率

### 4.4 求解器对比

| 求解器 | 速度 | 鲁棒性 | 适用规模 | 推荐场景 |
|--------|------|--------|----------|----------|
| Newton-Direct | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | 小-中 | 初值好、快速原型 |
| Newton-GMRES | ⭐⭐⭐⭐ | ⭐⭐⭐ | 中-大 | 大规模稀疏系统 |
| Continuation | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 小-中 | 初值差、强非线性 |
| Hybrid | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 小-大 | 生产环境、可靠性优先 |

---

## 5. 性能基准测试

HydroClaude 内置了性能测试套件。

### 5.1 快速测试（~1分钟）

```bash
hydroclaude-benchmark --quick
```

或：

```bash
python benchmark_suite.py --mode quick
```

### 5.2 标准测试（~5分钟）

```bash
python benchmark_suite.py --mode standard
```

### 5.3 全面测试（~15分钟）

```bash
python benchmark_suite.py --mode comprehensive
```

### 5.4 查看测试报告

测试完成后会生成报告：

```bash
# 查看 Markdown 报告
cat benchmark_results/benchmark_report_YYYYMMDD_HHMMSS.md

# 查看 JSON 报告
cat benchmark_results/benchmark_report_YYYYMMDD_HHMMSS.json
```

**示例报告输出**:

```
============================================================
HydroClaude 性能基准测试
============================================================

模式: standard
日期: 2025-10-22 15:30:45

------------------------------------------------------------
1. 求解器性能测试
------------------------------------------------------------
✓ Newton-Direct   : 3 迭代, 0.0123 秒, 残差 2.34e-08
✓ Newton-GMRES    : 5 迭代, 0.0187 秒, 残差 3.45e-08
✓ Continuation    : 2 阶段, 0.0456 秒, 总迭代 12

------------------------------------------------------------
2. 可扩展性测试
------------------------------------------------------------
✓ nx=6    : 0.0012 秒
✓ nx=21   : 0.0123 秒
✓ nx=51   : 0.0345 秒
✓ nx=101  : 0.0678 秒
✓ nx=201  : 0.1234 秒

总计: 6/6 测试通过 (100.0%)
```

---

## 6. 常见问题

### Q1: 安装时提示缺少依赖包

**A**: 确保 pip 版本 ≥ 21.0：

```bash
pip install --upgrade pip
pip install -e .[dev,logging]
```

### Q2: Newton 求解器不收敛

**A**: 尝试以下方法：

1. **改善初值**:
   ```python
   # 使用均匀流作为初值
   h_uniform = compute_steady_uniform_flow(Q, B, S0, n)
   h_init = np.ones(nx) * h_uniform
   ```

2. **使用延拓法**:
   ```python
   from solvers.continuation_solver import ContinuationSolver
   solver = ContinuationSolver(system, [10.0, 1.0, 0.1])
   ```

3. **使用混合求解器**:
   ```python
   from solvers.hybrid_solver_enhanced import HybridSolverEnhanced
   solver = HybridSolverEnhanced()
   ```

### Q3: 测试失败

**A**: 检查测试环境：

```bash
# 查看详细测试输出
pytest tests/ -v

# 查看失败原因
pytest tests/ -v --tb=short

# 只运行特定测试
pytest tests/test_newton_solver.py -v
```

### Q4: YAML 配置加载失败

**A**: 验证 YAML 语法：

```python
from core.config import SystemConfig

config = SystemConfig.from_yaml('config/my_canal.yaml')
errors = config.validate()

if errors:
    print("配置错误:")
    for error in errors:
        print(f"  - {error}")
```

### Q5: 如何查看日志

**A**: 日志保存在 `logs/` 目录：

```bash
# 查看 Newton 求解器日志
cat logs/newtonsolver.log

# 查看水库模拟日志
cat logs/reservoir.log

# 实时监控日志
tail -f logs/hybridsolver.log
```

---

## 7. 下一步

### 📚 学习更多

1. **查看完整示例**:
   ```bash
   ls examples/
   python examples/example_01_steady_canal/example_01_steady_flow.py
   ```

2. **阅读 API 文档**:
   - 查看 `README.md` 的 API 参考部分
   - 查看源代码中的 docstrings

3. **研究高级功能**:
   - Anderson 加速: `ANDERSON_ACCELERATION_VERIFICATION.md`
   - 项目总结: `PROJECT_SUMMARY.md`
   - 开发任务: `DEVELOPMENT_TASKS.md`

### 🎯 实践项目

1. **明渠流动**:
   - 不同坡度对水深的影响
   - 闸门调节对流量的影响
   - 糙率对流速的影响

2. **水库调度**:
   - 发电优化
   - 防洪调度
   - 生态流量保障

3. **管网系统**:
   - 串联管网
   - 树状管网
   - 环状管网

### 🤝 贡献代码

欢迎贡献！查看贡献指南：

```bash
cat CONTRIBUTING.md  # （如果有的话）
```

或直接提交 Pull Request：
1. Fork 仓库
2. 创建功能分支: `git checkout -b feature/my-feature`
3. 提交代码: `git commit -am 'Add my feature'`
4. 推送分支: `git push origin feature/my-feature`
5. 创建 Pull Request

### 📧 获取帮助

- **问题反馈**: [GitHub Issues](https://github.com/leixiaohui-1974/HydroClaude/issues)
- **功能请求**: [GitHub Issues](https://github.com/leixiaohui-1974/HydroClaude/issues)
- **讨论交流**: [GitHub Discussions](https://github.com/leixiaohui-1974/HydroClaude/discussions)

---

## 🎉 恭喜！

您已经完成了 HydroClaude 的快速入门！

现在您可以：
- ✅ 创建和求解明渠流动问题
- ✅ 使用 YAML 配置复杂系统
- ✅ 选择合适的求解器
- ✅ 运行性能基准测试
- ✅ 排查常见问题

**Happy Coding! 🚀**

---

*最后更新: 2025-10-22*
*版本: 0.2.0*
*作者: leixiaohui-1974*
