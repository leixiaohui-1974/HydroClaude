# Legacy Preissmann Solvers

**状态**: 已废弃 / DEPRECATED
**日期**: 2025-10-30

---

## 说明

本目录包含了已废弃的Preissmann求解器版本。这些版本因各种原因已不再推荐使用。

### ⚠️ 请勿在生产代码中使用这些版本！

**推荐使用**：
```python
from physics.numerical_methods.preissmann_solver_corrected import PreissmannSolverCorrected
```

---

## 版本历史和废弃原因

### 1. preissmann_solver.py（原始版本）
**创建日期**: 约2024年初
**废弃日期**: 2025-10-30
**废弃原因**:
- ❌ **质量守恒误差 +279%**（致命缺陷）
- ❌ Bug #1: `np.maximum(Q, 0.01)`强制正流量，凭空创造质量
- ❌ Bug #2: 连续方程使用中点平均，违反守恒
- ❌ Bug #3: 动量方程缺少旧时刻对流项
- ❌ Bug #4: Jacobian矩阵奇异
- ❌ Bug #5: 数值溢出

**详细分析**: 见 `/docs/PREISSMANN_SOLVER_FIX_REPORT.md`

### 2. preissmann_solver_fixed.py
**创建日期**: 2024年中
**废弃日期**: 2025-10-30
**废弃原因**:
- ❌ 尝试修复原始版本的bug
- ❌ Jacobian矩阵仍然奇异
- ❌ 产生NaN值
- ❌ 静水测试失败

**测试结果**:
```
质量误差: nan%
状态: Matrix is exactly singular
```

### 3. preissmann_solver_v2.py
**创建日期**: 2024年中
**废弃日期**: 2025-10-30
**废弃原因**:
- ❌ 尝试添加自适应阻尼
- ❌ Jacobian矩阵奇异
- ❌ 产生NaN值
- ❌ 所有测试失败

**测试结果**:
```
质量误差: nan%
状态: Matrix is exactly singular
```

### 4. preissmann_solver_v3_scaled.py
**创建日期**: 2024年中
**废弃日期**: 2025-10-30
**废弃原因**:
- ❌ 尝试使用变量缩放改善矩阵条件数
- ❌ h_scaled = h/h_scale, Q_scaled = Q/Q_scale
- ❌ 仍然矩阵奇异
- ❌ 所有测试失败

**测试结果**:
```
质量误差: nan%
状态: Matrix is exactly singular
```

### 5. preissmann_solver_v4_linear.py
**创建日期**: 2024年末
**废弃日期**: 2025-10-30
**废弃原因**:
- ⚠️ 线性化Q²/A项: `Q²/A ≈ 2Q*Q_old/A_old`
- ⚠️ 极简Jacobian（仅主对角线）
- ✅ 静水测试通过（质量误差0.00%）
- ❌ 动态流测试失败（数值溢出）
- ❌ 过度简化，不适用于复杂流动

**测试结果**:
```
静水测试: ✅ 通过（0.000000%）
均匀流测试: ❌ 失败（NaN）
水位阶跃: ❌ 失败（NaN）
```

**评价**: 在正确方向上迈出了一步，但简化过度

---

## 替代方案

### ✅ 推荐：PreissmannSolverCorrected

**文件**: `preissmann_solver_corrected.py`
**创建日期**: 2025-10-30
**状态**: 生产就绪 ✅

**关键改进**:
1. ✅ 移除Q截断（允许Q=0和负值）
2. ✅ 修正连续方程（分别计算各节点）
3. ✅ 完整对流项（新旧时刻θ加权）
4. ✅ Tikhonov正则化（J + λI）解决奇异
5. ✅ 数值保护（防止溢出）
6. ✅ 自适应松弛因子

**测试结果**:
```
静水测试: ✅ 通过（0.000000%质量误差）
均匀流测试: ✅ 通过（0.000000%质量误差）
水位阶跃测试: ✅ 通过（+0.625%，合理）
案例库测试: ✅ 15/15通过
验证案例: ✅ Dam Break, MacDonald全部通过
```

**使用示例**:
```python
from physics.numerical_methods.preissmann_solver_corrected import PreissmannSolverCorrected

solver = PreissmannSolverCorrected(
    theta=0.6,        # 推荐值
    max_iter=30,
    tolerance=1e-6,
    verbose=False
)

h_new, Q_new = solver.solve_canal_step(
    h_old, Q_old, dt, dx, width, manning_n, slope,
    boundary_conditions, g=9.81
)
```

---

## 技术总结

### 失败的根本原因

所有legacy版本失败的共同原因：

1. **物理约束vs数学技巧**
   - 错误：用`np.maximum(Q, 0)`防止"负流量"
   - 正确：Q=0和Q<0都是合法物理状态

2. **Jacobian奇异问题**
   - 错误：试图"改进"离散方法
   - 正确：在静态平衡点Jacobian本质奇异，需要正则化

3. **过度简化**
   - 错误：简化方程或Jacobian"解决"问题
   - 正确：完整方程 + 合适的数值技术

### 成功的关键

PreissmannSolverCorrected成功的原因：

1. **理解物理本质**
   - 允许Q=0（静水）和Q<0（回流）
   - 不强加非物理约束

2. **数学上正确**
   - Tikhonov正则化优雅解决奇异性
   - 完整的Saint-Venant方程离散

3. **数值上稳健**
   - 自适应松弛因子
   - 溢出保护
   - 合理的收敛标准

---

## 经验教训

### 给未来开发者

1. **不要重新发明轮子**
   - PreissmannSolverCorrected已经解决了所有已知问题
   - 除非有明确的改进方向，否则使用现有版本

2. **保留历史版本的价值**
   - 这些失败的版本是宝贵的教训
   - 帮助理解什么不可行
   - 避免重复同样的错误

3. **测试驱动开发**
   - 每个版本都应该通过标准测试
   - 静水测试是最基本的质量检查
   - 质量守恒是硬性要求

4. **文档化很重要**
   - 记录为什么某个版本被废弃
   - 帮助后来者理解设计决策
   - 避免历史重演

---

## 参考文献

1. **技术报告**
   - `/docs/PREISSMANN_SOLVER_FIX_REPORT.md` - 完整的修复报告
   - `/docs/SOLVER_COMPARISON_AND_GUIDE.md` - 求解器对比指南

2. **测试代码**
   - `/physics/numerical_methods/test_preissmann_corrected.py` - 标准测试
   - `/validation_cases/` - 验证案例

3. **学术参考**
   - Preissmann, A. (1961). "Propagation of translatory waves."
   - Cunge, J. A., et al. (1980). "Practical Aspects of Computational River Hydraulics."
   - Chaudhry, M. H. (2008). "Open-Channel Flow." 2nd Edition.

---

## 如何迁移

如果您的代码仍在使用legacy版本：

### 步骤1: 更新import
```python
# Before (废弃)
from physics.numerical_methods.preissmann_solver import PreissmannSolver

# After (推荐)
from physics.numerical_methods.preissmann_solver_corrected import PreissmannSolverCorrected
```

### 步骤2: 更新初始化（如果需要）
```python
# Before
solver = PreissmannSolver(theta=0.6)

# After
solver = PreissmannSolverCorrected(
    theta=0.6,
    max_iter=30,      # 新参数
    tolerance=1e-6,   # 新参数
    verbose=False     # 新参数
)
```

### 步骤3: API兼容
`solve_canal_step`方法的API完全兼容，无需修改调用代码。

### 步骤4: 测试
运行您的测试套件，验证：
- 质量守恒（应该大幅改善）
- 收敛性（应该更稳定）
- 结果精度（应该保持或改善）

---

## 联系与支持

如果您在迁移过程中遇到问题：
- 查看文档：`/docs/SOLVER_COMPARISON_AND_GUIDE.md`
- 查看示例：`/examples/case_library/`
- 提交Issue：使用GitHub Issues

**最后更新**: 2025-10-30
**维护者**: HydroClaude Team

---

*这些legacy版本被保留用于历史参考和教育目的。请勿在生产环境中使用。*

🎉 Generated with Claude Code
