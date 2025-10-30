# Legacy Diagnostic Tests

**⚠️ 警告**: 本目录包含已废弃的诊断测试文件，这些文件引用了已移除或重构的模块，无法正常运行。

**迁移日期**: 2025-10-30
**迁移原因**: 代码重构后模块路径变更，这些测试不再适用于当前代码库

---

## 📋 迁移文件列表

以下17个测试文件已从`tests/diagnostic/`迁移到此目录：

### 1. 引用不存在的solvers模块的文件

这些文件引用了以下已移除的模块：
- `solvers.single_canal_solver`
- `solvers.fixed_point_iteration`
- `solvers.digital_twin`

**文件列表**:
1. `test_adaptive_fine_tuned.py` - 自适应网格微调测试
2. `test_adaptive_grid_optimized.py` - 优化的自适应网格测试
3. `test_adaptive_grid_solver.py` - 自适应网格求解器测试
4. `test_adaptive_smooth_weight.py` - 平滑权重自适应测试
5. `test_anderson_vs_aitken.py` - Anderson vs Aitken加速对比
6. `test_digital_twin.py` - 数字孪生测试
7. `test_final_optimization.py` - 最终优化测试
8. `test_fixes_quick.py` - 快速修复测试
9. `test_fvm_fdm_comparison.py` - FVM vs FDM对比测试
10. `test_fvm_full_final.py` - FVM完整最终测试
11. `test_fvm_steady_comparison.py` - FVM稳态对比测试
12. `test_grid_comprehensive.py` - 综合网格测试
13. `test_grid_refinement.py` - 网格细化测试
14. `test_high_precision_solver.py` - 高精度求解器测试
15. `test_performance_comparison.py` - 性能对比测试
16. `test_phase2_solver.py` - Phase 2求解器测试
17. `test_swmm_omega.py` - SWMM omega参数测试

---

## 🔍 为什么这些测试被废弃？

### 原因1: 模块重构

在2025年10月的代码重构中，`solvers/`目录下的一些模块被：
- **移除**: 因为功能已集成到其他模块
- **重命名**: 采用了新的模块组织结构
- **重构**: 代码被重写以提高质量

### 原因2: 测试目标已过时

这些诊断测试主要用于：
- 早期开发阶段的性能调试
- 实验性功能的验证（如Anderson加速、自适应网格）
- 与已废弃求解器版本的对比

随着项目的成熟，这些测试的价值已经降低。

### 原因3: 重复测试覆盖

这些测试的核心功能现在已被更完善的测试套件覆盖：
- `tests/test_components.py` - 组件测试
- `tests/test_boundary_conditions.py` - 边界条件测试
- `tests/test_cross_section.py` - 断面几何测试
- `physics/numerical_methods/test_preissmann_corrected.py` - Preissmann求解器测试

---

## 🚀 如果需要恢复这些测试

如果将来需要恢复这些测试，需要进行以下工作：

### 1. 更新导入路径

将旧的导入：
```python
from solvers.single_canal_solver import SingleCanalSolver
```

更新为新的模块路径（如果存在对应功能）：
```python
from physics.canal import Canal
# 或其他适当的替代模块
```

### 2. 更新API调用

检查API变化，更新函数调用和参数：
- 参数名称可能已更改（如`tolerance` → `tol`）
- 类接口可能已重构
- 返回值格式可能不同

### 3. 验证测试仍然有意义

考虑：
- 测试的目标功能是否仍然相关？
- 是否有更好的测试方法？
- 是否与现有测试重复？

---

## 📊 当前测试套件状态

**核心测试** (推荐运行):
```bash
# 组件测试
pytest tests/test_components.py

# 边界条件测试
pytest tests/test_boundary_conditions.py

# 断面几何测试
pytest tests/test_cross_section.py

# Preissmann求解器测试
python physics/numerical_methods/test_preissmann_corrected.py
```

**诊断测试** (tests/diagnostic/):
- 移除legacy文件后，剩余约100+个诊断测试
- 这些测试大多可以正常运行
- 用于深入验证特定功能和数值算法

---

## 📚 相关文档

1. `docs/DEVELOPMENT_SESSION_20251030.md` - Preissmann求解器修复报告
2. `docs/DEVELOPMENT_SESSION_20251030_PART2.md` - 代码清理和测试配置修复
3. `docs/DEVELOPMENT_SESSION_20251030_PART3.md` - Legacy测试迁移记录
4. `physics/numerical_methods/legacy_preissmann/README.md` - Legacy Preissmann求解器说明

---

## 🎯 建议

1. **不要删除这些文件** - 它们包含有价值的历史信息和测试思路
2. **不要尝试直接运行** - 这些测试需要大量修复工作才能运行
3. **参考历史价值** - 可以作为实现新测试的参考
4. **关注新测试** - 集中精力在`tests/`目录下的现代测试套件

---

**迁移完成时间**: 2025-10-30
**负责人**: HydroClaude Team
**相关提交**: (将在git commit时记录)

🎉 Generated with [Claude Code](https://claude.com/claude-code)
