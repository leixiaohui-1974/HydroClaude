# Phase 3 修订计划 - 可运行非v2脚本迁移

**项目**: HydroClaude 可运行非v2脚本工程化迁移
**日期**: 2025-10-23
**状态**: 🚀 进行中
**修订原因**: 发现7个非v2脚本因依赖缺失而无法运行

---

## ⚠️ 重要发现

在开始Phase 3迁移工作时，对所有13个非v2脚本进行了运行测试，**发现7个脚本无法运行**：

### 无法运行的脚本 (7个)

| 脚本名 | 行数 | 错误原因 | 缺失模块 |
|--------|------|----------|----------|
| 01_basic.py | 280 | ModuleNotFoundError | solvers.canal_solver |
| 01_basic_with_animation.py | 373 | ModuleNotFoundError | solvers.canal_solver |
| 04_boundary_conditions.py | 392 | ModuleNotFoundError | solvers.canal_solver |
| 07_sluice_gate_flow.py | 515 | ModuleNotFoundError | solvers.single_canal_solver |
| 08_optimized_steady_solving.py | 309 | ModuleNotFoundError | solvers.single_canal_solver |
| 09_simple_canal_enhanced.py | 342 | ModuleNotFoundError | physics.canal |
| 12_advanced_optimized.py | 261 | ModuleNotFoundError | solvers.single_canal_solver |
| **总计** | **2,472** | | |

**原因**: 这些模块已被移动到 `legacy_backup/` 或完全移除。这些脚本已过时。

**建议**:
1. 暂时跳过这些脚本的迁移
2. 如有需要，单独修复（恢复模块或重写脚本）
3. 或者标记为废弃

---

## ✅ 可运行的脚本 (6个)

### 脚本清单和分类

| 序号 | 脚本名 | 行数 | 类型 | 求解器方式 | 迁移优先级 |
|------|--------|------|------|-----------|-----------|
| 1 | 02_methods_comparison.py | 858 | 性能对比 | 内联CanalSolver | ⭐⭐⭐ 高 |
| 2 | 03_idz_identification.py | 900 | 特殊可视化 | 内联CanalSolver | ⭐⭐ 中 |
| 3 | 05_step_response.py | 539 | 标准绘图 | 内联CanalSolver | ⭐⭐⭐ 高 |
| 4 | 06_animation.py | 503 | 动画 | 内联实现 | ⭐⭐ 中 |
| 5 | 10_canal_deep_analysis.py | 650 | 特殊可视化 | 混合 | ⭐ 低 |
| 6 | 11_advanced_structures.py | 560 | 混合型 | 内联实现 | ⭐⭐ 中 |
| | **总计** | **4,010** | | | |

---

## 🎯 修订后的Phase 3范围

### 目标

迁移 **6个可运行的非v2脚本**，使其使用ScriptHelper进行路径管理现代化。

### 预期成果

- ✅ 6/6 可运行脚本迁移完成
- ✅ 路径管理100%现代化（pathlib）
- ✅ 数值结果100%一致
- ✅ 代码可维护性提升

### 工作量估算

| 指标 | 原计划 (13脚本) | 修订后 (6脚本) | 变化 |
|------|----------------|---------------|------|
| 脚本数量 | 13 | 6 | -54% |
| 总代码行数 | 6,482 | 4,010 | -38% |
| 预估时间 | 8.0小时 | 4.5小时 | -44% |

---

## 📝 迁移策略

### 按类型分类

**1. 性能对比脚本** (1个): 02_methods_comparison.py
- **策略**: ScriptHelper only（保留matplotlib复杂图表）
- **特点**: 内联CanalSolver，复杂可视化
- **预估时间**: 30-35分钟

**2. 标准绘图脚本** (1个): 05_step_response.py
- **策略**: ScriptHelper + 考虑PlotHelper（如适用）
- **特点**: 内联CanalSolver，标准图表
- **预估时间**: 25-30分钟

**3. 动画脚本** (1个): 06_animation.py
- **策略**: ScriptHelper only（保留animation逻辑）
- **特点**: FuncAnimation, GIF输出
- **预估时间**: 25-30分钟

**4. 特殊可视化脚本** (2个): 03_idz_identification.py, 10_canal_deep_analysis.py
- **策略**: ScriptHelper only（保留所有复杂matplotlib特性）
- **特点**: fill_between, subplot2grid, 复杂布局
- **预估时间**: 35-40分钟/个

**5. 混合型脚本** (1个): 11_advanced_structures.py
- **策略**: ScriptHelper + 部分PlotHelper
- **特点**: 多种图表混合
- **预估时间**: 30-35分钟

---

## 🚀 执行计划

### Phase 3.1 - 试点批次 (预计1.5小时)

**目标**: 验证迁移策略在自包含脚本上的适用性

**脚本选择** (3个):
1. ✅ 05_step_response.py (539行, 标准绘图) - 相对简单
2. ✅ 02_methods_comparison.py (858行, 性能对比) - 复杂但结构清晰
3. ✅ 06_animation.py (503行, 动画) - 验证动画迁移

**成功标准**:
- ✅ 3个脚本迁移完成
- ✅ 运行成功，输出正确
- ✅ 路径管理现代化
- ✅ 数值/可视化结果一致

---

### Phase 3.2 - 复杂批次 (预计2.5小时)

**脚本选择** (3个):
1. 03_idz_identification.py (900行, 特殊可视化)
2. 10_canal_deep_analysis.py (650行, 特殊可视化)
3. 11_advanced_structures.py (560行, 混合型)

---

## 📈 预期成果

### 代码统计

```
Phase 3总迁移代码: ~4,010行
├── 原版脚本: 4,010行
├── 预计重构版: 3,950-4,000行
└── 预期改善: -0.5% ~ -1.5% (主要是结构改善)
```

### 时间预算

| 阶段 | 脚本数 | 预估时间 | 缓冲 | 总计 |
|------|--------|---------|------|------|
| Phase 3.1 | 3 | 1.5小时 | +0.5小时 | 2.0小时 |
| Phase 3.2 | 3 | 2.0小时 | +0.5小时 | 2.5小时 |
| 文档更新 | - | 0.5小时 | +0.5小时 | 1.0小时 |
| **总计** | **6** | **4.0小时** | **+1.5小时** | **5.5小时** |

---

## ✅ 成功标准

| 标准 | 目标 |
|------|------|
| 可运行脚本迁移完成度 | 100% (6/6) |
| 路径管理现代化 | 100% (pathlib) |
| 运行成功率 | 100% |
| 输出正确性 | 100% |
| 代码可维护性 | 显著提升 |
| 文档更新 | 100% |

---

## 🎯 立即行动

### 第一步: Phase 3.1 试点批次

**目标脚本**:
1. ✅ 05_step_response.py (539行) - **NOW**
2. 02_methods_comparison.py (858行)
3. 06_animation.py (503行)

**行动**:
开始迁移 `05_step_response.py`

---

## 📝 关于无法运行的7个脚本

### 后续处理建议

**选项A: 修复脚本**
- 恢复缺失的模块（从legacy_backup/）
- 或者重写为使用现有API
- 时间成本: ~2-3小时

**选项B: 标记为废弃**
- 在文档中明确标注
- 移动到 `legacy/` 或 `deprecated/` 目录
- 时间成本: 10分钟

**选项C: 暂时保留**
- 不做处理，保持现状
- 在MIGRATION_SUMMARY中记录
- 时间成本: 5分钟

**推荐**: 选项C，在Phase 3完成后再决定

---

**生成时间**: 2025-10-23
**项目阶段**: Phase 3 - 修订计划
**负责人**: Claude
