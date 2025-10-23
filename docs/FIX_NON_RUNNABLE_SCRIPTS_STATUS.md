# 修复不可运行脚本 - 工作状态报告

**日期**: 2025-10-23
**任务**: 修复Phase 3中发现的7个不可运行脚本
**状态**: ⚠️ 进行中 - 遇到依赖问题

---

## 📋 任务概览

### 目标脚本（7个）

| 脚本 | 行数 | 原始错误 | 当前状态 |
|------|------|----------|----------|
| 01_basic.py | 280 | solvers.canal_solver | ⚠️ 需legacy模块 |
| 01_basic_with_animation.py | 373 | solvers.canal_solver | ⚠️ 需legacy模块 |
| 04_boundary_conditions.py | 392 | solvers.canal_solver | ⚠️ 需legacy模块 |
| 07_sluice_gate_flow.py | 515 | solvers.single_canal_solver | ⚠️ 需legacy模块 |
| 08_optimized_steady_solving.py | 309 | solvers.single_canal_solver | ⚠️ 需legacy模块 |
| 09_simple_canal_enhanced.py | 342 | physics.canal | ⚠️ 需networkx |
| 12_advanced_optimized.py | 261 | solvers.single_canal_solver | ⚠️ 需legacy模块 |

---

## ✅ 已完成工作

### 1. 基础路径迁移
- ✅ 所有7个脚本创建重构版本
- ✅ 迁移到ScriptHelper路径管理
- ✅ 修正路径层级（parents[3]指向项目根）
- ✅ 修复导入顺序（sys.path在项目导入之前）

### 2. 输出管理现代化
- ✅ 替换所有`get_output_path`调用
- ✅ 替换所有`save_figure`调用
- ✅ 替换所有`save_table`调用
- ✅ 替换所有`save_animation`调用

### 3. 语法验证
- ✅ 所有脚本Python语法检查通过
- ✅ 导入语句结构正确
- ✅ ScriptHelper初始化正确

---

## ⚠️ 遇到的问题

### 问题1: Legacy模块依赖（6个脚本）

**影响脚本**: 01_basic, 01_basic_with_animation, 04_boundary_conditions,
07_sluice_gate_flow, 08_optimized_steady_solving, 12_advanced_optimized

**问题描述**:
这些脚本依赖已移至`legacy_backup/`的模块：
- `solvers.canal_solver` → `legacy_backup/solvers_canal_solver.py`
- `solvers.single_canal_solver` → `legacy_backup/solvers_single_canal_solver.py`

**当前错误**:
```
ModuleNotFoundError: No module named 'solvers.canal_solver'
ModuleNotFoundError: No module named 'solvers.single_canal_solver'
```

**可能解决方案**:

**方案A**: 恢复legacy模块到solvers/
```bash
cp legacy_backup/solvers_canal_solver.py solvers/canal_solver.py
cp legacy_backup/solvers_single_canal_solver.py solvers/single_canal_solver.py
```
- 优点: 直接修复，脚本可运行
- 缺点: 可能与现有代码冲突，增加维护负担

**方案B**: 重写脚本使用现有API
- 将脚本改写为使用`HydrostaticCanalSolver`
- 优点: 与项目主线一致
- 缺点: 需要重写大量代码，相当于创建新脚本

**方案C**: 创建兼容层
- 在legacy_backup中创建`__init__.py`
- 或创建wrapper模块
- 优点: 不影响现有代码
- 缺点: 增加复杂性

**方案D**: 标记为废弃
- 移动到`deprecated/`目录
- 在README中说明
- 优点: 清晰明确
- 缺点: 减少可用示例

---

### 问题2: 缺少networkx依赖（1个脚本）

**影响脚本**: 09_simple_canal_enhanced

**问题描述**:
脚本导入`utils.visualization`，而该模块需要networkx:
```python
from utils.visualization import SimulationVisualizer, ReportGenerator
# utils/visualization.py需要: import networkx as nx
```

**当前错误**:
```
ModuleNotFoundError: No module named 'networkx'
```

**解决方案**:
```bash
pip install networkx
```
- 简单直接
- 但09脚本可能还有其他依赖问题

---

## 📊 工作进度

### 已完成 ✅
- [x] 路径管理迁移（7/7）
- [x] 输出管理现代化（7/7）
- [x] 导入顺序修复（7/7）
- [x] 语法检查（7/7）

### 进行中 ⚠️
- [ ] 解决legacy模块依赖（0/6）
- [ ] 解决networkx依赖（0/1）
- [ ] 运行测试（0/7）

### 待定 ❓
- [ ] 决定legacy模块处理方案
- [ ] 完整测试所有脚本
- [ ] 创建最终报告

---

## 💡 建议

### 短期建议（推荐）

**对于legacy模块问题**:
采用方案D（标记为废弃）：
1. 在Phase 3报告中说明这6个脚本依赖legacy代码
2. 提供修复指南（如何手动恢复模块）
3. 建议用户使用v2版本脚本

**理由**:
- 这些脚本使用旧版API（已被HydrostaticCanalSolver替代）
- v2脚本提供了相同功能但更现代
- 避免引入legacy代码到main分支

**对于09脚本**:
简单安装networkx并测试：
```bash
pip install networkx
```

### 长期建议（可选）

如果用户强烈需要这些脚本：
1. 创建`legacy/`目录
2. 恢复legacy模块到该目录
3. 修改脚本从legacy导入
4. 在README中明确标注

---

## 📝 技术细节

### 修复的路径设置

**Before** (原始):
```python
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from output_helper import get_output_path
```

**After** (重构):
```python
from pathlib import Path
script_path = Path(__file__).resolve()
project_root = script_path.parents[3]  # 指向/home/user/HydroClaude
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
from utils.script_helper import ScriptHelper
helper = ScriptHelper(__file__)
```

### 修复的导入顺序

**Before** (错误):
```python
from physics.canal import Canal  # 在sys.path设置之前！
...
sys.path.insert(0, ...)
```

**After** (正确):
```python
import sys
from pathlib import Path
# 先设置路径
sys.path.insert(0, str(project_root))
# 再导入项目模块
from physics.canal import Canal
```

---

## 🎯 结论

### 当前状态
7个脚本已完成基础重构，但**无法运行**due to：
- 6个脚本: legacy模块依赖
- 1个脚本: networkx依赖

### 推荐行动
1. ✅ 提交当前重构工作（WIP状态）
2. ✅ 在Phase 3报告中说明情况
3. ⚠️ 建议用户：
   - 使用5个v2脚本 + 6个已迁移非v2脚本（Phase 3.1+3.2）
   - 如需这7个脚本，参考修复指南

### 项目整体状态
**可用脚本总数**:
- ✅ v2脚本重构版: 5个（100%可用）
- ✅ 非v2脚本重构版: 6个（100%可用）
- ⚠️ 非v2脚本修复中: 7个（需进一步工作）
- **总计**: 11个完全可用 + 7个需额外步骤

---

**文档创建**: 2025-10-23
**状态**: WIP - 等待决策
**负责人**: Claude
