# HydroClaude AI开发工具使用指南

**版本**: 1.0
**更新日期**: 2025-10-27
**目的**: 帮助AI和开发者正确使用HydroClaude基础库，避免重复造轮子

---

## 📋 目录

1. [工具概述](#工具概述)
2. [工具1: AI规则文件](#工具1-ai规则文件)
3. [工具2: 示例代码索引](#工具2-示例代码索引)
4. [工具3: 自动检查工具](#工具3-自动检查工具)
5. [工具4: 代码模板生成器](#工具4-代码模板生成器)
6. [工具5: Pre-commit Hooks](#工具5-pre-commit-hooks)
7. [完整工作流](#完整工作流)
8. [常见问题](#常见问题)

---

## 工具概述

| 工具 | 文件路径 | 用途 | 使用时机 |
|-----|---------|------|---------|
| **AI规则文件** | `.cursorrules` | 让AI自动遵守开发规范 | 自动（AI工具读取） |
| **示例索引** | `EXAMPLES_INDEX.md` | 快速找到参考代码 | 开发前查阅 |
| **自动检查** | `tools/check_library_usage.py` | 检查代码是否符合规范 | 开发中/提交前 |
| **模板生成器** | `tools/create_example.py` | 生成标准代码框架 | 开始新项目时 |
| **Pre-commit** | `.pre-commit-config.yaml` | 提交前自动检查 | git commit时 |

---

## 工具1: AI规则文件

### 📍 文件位置
```
.cursorrules
```

### 🎯 功能
- AI工具（Cursor、GitHub Copilot等）会自动读取此文件
- 确保AI生成的代码遵守HydroClaude开发规范
- 强制使用基础库，避免重复实现

### ✅ 优点
- ✅ 零配置，AI自动遵守
- ✅ 覆盖所有开发规则
- ✅ 易于维护和更新

### 📖 内容概要
- 基础库优先原则
- 强制使用的基础库清单
- 禁止的行为列表
- 标准代码模板

### 🔧 维护方法
```bash
# 编辑规则文件
vim .cursorrules

# AI工具会自动重新加载
```

---

## 工具2: 示例代码索引

### 📍 文件位置
```
EXAMPLES_INDEX.md
```

### 🎯 功能
- 提供"需求→示例"的快速映射
- 帮助快速找到参考代码
- 列出禁止参考的旧示例

### ✅ 使用场景

**场景1: 需要实现单闸门功能**
```markdown
查阅 EXAMPLES_INDEX.md → 找到参考示例
→ examples/example_01_canal_flow/scripts/07_sluice_gate_flow_v2.py
```

**场景2: 需要绘制纵剖面图**
```markdown
查阅 EXAMPLES_INDEX.md → 找到使用的基础库
→ PlotHelper.plot_profile
→ 参考示例: 01_basic_v2.py
```

### 📖 主要内容
- 按功能分类的示例列表
- 关键代码片段
- 学习路径推荐
- 常见问题速查

### 🔍 快速搜索
```bash
# 搜索闸门相关示例
grep -i "sluicegate" EXAMPLES_INDEX.md

# 搜索绘图相关示例
grep -i "plot" EXAMPLES_INDEX.md
```

---

## 工具3: 自动检查工具

### 📍 文件位置
```
tools/check_library_usage.py
```

### 🎯 功能
自动检查Python代码是否：
- ✅ 使用了推荐的基础库
- ❌ 使用了废弃的类/模块
- ⚠️ 有重复造轮子的迹象
- 💡 可以优化的地方

### 📖 使用方法

#### 基本用法
```bash
# 检查单个文件
python tools/check_library_usage.py examples/my_example.py

# 检查整个目录
python tools/check_library_usage.py examples/

# 检查多个路径
python tools/check_library_usage.py examples/ tests/
```

#### 高级用法
```bash
# 严格模式（警告也视为错误）
python tools/check_library_usage.py examples/ --strict

# 在CI中使用（失败时返回非零退出码）
python tools/check_library_usage.py examples/ || exit 1
```

### 📊 输出示例

**通过的情况**:
```
================================================================================
HydroClaude 基础库使用检查报告
================================================================================

📊 总计: 5 个文件
✅ 通过: 5 (100.0%)
❌ 未通过: 0

================================================================================
✅ 检查通过！代码符合基础库使用规范
================================================================================
```

**有问题的情况**:
```
================================================================================
HydroClaude 基础库使用检查报告
================================================================================

📊 总计: 3 个文件
✅ 通过: 1 (33.3%)
❌ 未通过: 2

⚠️  发现 2 个严重问题
💡 发现 3 个警告

================================================================================
严重问题详情（必须修复）
================================================================================

📁 examples/bad_example.py
   ❌ 使用了废弃的类: SingleCanalSolver (已废弃) → 应使用: HydrostaticCanalSolver
   ❌ 未使用推荐的求解器: HydrostaticCanalSolver

================================================================================
警告和建议（推荐修复）
================================================================================

📁 examples/my_example.py
   ⚠️  求解后未使用 ResultValidator 验证结果
   💡 使用 quick_validate_steady_state 自动验证结果
   ⚠️  使用原生matplotlib绘图，建议使用专业绘图工具
   💡 使用 PlotHelper 或 VisualizationTemplates 简化绘图代码
```

### 🔍 检查规则

工具会检查：

1. **废弃类检测**
   - SingleCanalSolver → HydrostaticCanalSolver
   - CanalSolver → HydrostaticCanalSolver
   - MOCSolver → 已删除

2. **重复实现检测**
   - `def validate_flow(` → 使用 ResultValidator
   - `def compute_uniform_` → 使用 canal_utils
   - `def plot_profile(` → 使用 PlotHelper

3. **基础库使用检测**
   - 求解后未使用 ResultValidator
   - 使用原生matplotlib而非PlotHelper
   - 收敛容差过于严格

---

## 工具4: 代码模板生成器

### 📍 文件位置
```
tools/create_example.py
```

### 🎯 功能
- 自动生成符合规范的代码框架
- 包含所有必要的基础库导入
- 提供清晰的TODO标记
- 自动创建目录结构

### 📖 使用方法

#### 基本用法
```bash
# 创建基本示例
python tools/create_example.py my_canal_test "单闸门流动分析"

# 创建控制示例
python tools/create_example.py my_mpc_test "MPC控制案例" --template control

# 指定作者
python tools/create_example.py my_test "测试案例" --author "Alice"
```

#### 模板类型

**1. basic 模板**（默认）
- 适用于：稳态流动分析
- 包含：HydrostaticCanalSolver、ResultValidator、PlotHelper
- 示例：单闸门、多结构、基础流动

**2. control 模板**
- 适用于：非恒定流控制
- 包含：Canal (Preissmann)、PIDController、时间序列图
- 示例：水位控制、MPC、自适应控制

### 📂 生成的文件结构

```
examples/my_canal_test/
├── my_canal_test.py      # 主脚本（包含完整框架）
├── README.md             # 说明文档
└── results/              # 输出目录
```

### 📝 生成的代码特点

```python
# ✅ 自动包含所有必要导入
from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver
from utils.result_validator import quick_validate_steady_state
from utils.plot_helper import PlotHelper

# ✅ 标准代码结构
def main():
    # 1. 参数设置
    # 2. 创建结构物
    # 3. 创建求解器
    # 4. 初始化
    # 5. 稳态求解
    # 6. 验证结果（必须）
    # 7. 可视化
    # 8. 保存数据
    # 9. 总结

# ✅ 清晰的TODO标记
# TODO: 修改参数
# TODO: 添加结构物
# TODO: 启用可选功能
```

### 🎯 下一步操作

生成代码后：
```bash
# 1. 编辑生成的脚本
vim examples/my_canal_test/my_canal_test.py

# 2. 搜索TODO注释
grep -n "TODO" examples/my_canal_test/my_canal_test.py

# 3. 修改参数和配置

# 4. 运行脚本
python examples/my_canal_test/my_canal_test.py

# 5. 查看结果
ls examples/my_canal_test/results/
```

---

## 工具5: Pre-commit Hooks

### 📍 文件位置
```
.pre-commit-config.yaml
```

### 🎯 功能
- 在git提交前自动运行检查
- 阻止不符合规范的代码提交
- 集成代码质量检查工具

### 📖 安装方法

```bash
# 1. 安装pre-commit
pip install pre-commit

# 2. 安装hooks到git仓库
pre-commit install

# 3. 验证安装
pre-commit --version
```

### ✅ 配置的检查项

1. **HydroClaude基础库检查**（最重要）
   - 自动运行 `check_library_usage.py`
   - 检查是否使用基础库

2. **代码质量检查**
   - 大文件检查（>1MB警告）
   - 合并冲突标记检查
   - YAML/JSON语法检查
   - Python语法检查
   - 去除末尾空白
   - 确保文件以换行符结尾

### 🔧 使用方法

#### 自动运行（推荐）
```bash
# 正常提交，hooks会自动运行
git add my_example.py
git commit -m "Add: 新示例"

# 如果检查失败，commit会被阻止
# 修复问题后重新提交
```

#### 手动运行
```bash
# 检查所有文件
pre-commit run --all-files

# 检查特定文件
pre-commit run --files examples/my_example.py

# 只运行特定hook
pre-commit run check-library-usage --all-files
```

#### 跳过检查（不推荐）
```bash
# 紧急情况下跳过pre-commit
git commit --no-verify -m "Emergency fix"
```

### 📊 输出示例

**通过的情况**:
```
检查基础库使用规范.........................................通过
检查是否有大文件.............................................通过
检查是否有合并冲突标记.......................................通过
检查YAML文件语法.............................................通过
检查Python语法...............................................通过
```

**失败的情况**:
```
检查基础库使用规范.........................................失败
- hook id: check-library-usage
- exit code: 1

❌ 使用了废弃的类: SingleCanalSolver
   应使用: HydrostaticCanalSolver
```

---

## 完整工作流

### 🔄 标准开发流程

```
第1步: 查阅文档
├─ 打开 EXAMPLES_INDEX.md
├─ 搜索类似功能
└─ 找到参考示例

第2步: 生成代码框架
├─ 运行: python tools/create_example.py my_example "描述"
├─ 自动生成标准代码
└─ 包含所有基础库导入

第3步: 开发代码
├─ 编辑生成的脚本
├─ 搜索 TODO 注释
├─ 修改参数和配置
└─ AI自动遵守 .cursorrules

第4步: 检查代码（可选）
├─ 运行: python tools/check_library_usage.py my_example.py
├─ 查看检查报告
└─ 修复问题

第5步: 提交代码
├─ git add my_example.py
├─ git commit -m "Add: 新示例"
├─ pre-commit自动运行检查
└─ 通过后完成提交
```

### 🎯 最佳实践

1. **开发前**
   - ✅ 查阅 EXAMPLES_INDEX.md
   - ✅ 使用 create_example.py 生成框架
   - ✅ 参考已有示例

2. **开发中**
   - ✅ 遵循生成的代码结构
   - ✅ 使用基础库而非重复实现
   - ✅ AI会自动遵守 .cursorrules

3. **开发后**
   - ✅ 运行 check_library_usage.py 检查
   - ✅ 修复所有严重问题
   - ✅ 考虑修复警告

4. **提交前**
   - ✅ pre-commit自动检查
   - ✅ 确保所有检查通过
   - ✅ 提交前再次确认

---

## 常见问题

### Q1: AI还是没有使用基础库怎么办？

**A**: 检查以下几点：
1. `.cursorrules` 文件是否存在且内容正确
2. AI工具是否支持读取 `.cursorrules`（Cursor、GitHub Copilot支持）
3. 尝试在提示词中明确提及"必须使用 HydrostaticCanalSolver"
4. 使用 `create_example.py` 生成初始框架

### Q2: 检查工具报警告，必须修复吗？

**A**: 不强制，但强烈建议：
- ❌ 严重问题（红色）：必须修复
- ⚠️ 警告（黄色）：建议修复
- 💡 建议（蓝色）：可选优化

使用 `--strict` 模式可以将警告视为错误。

### Q3: 如何添加新的检查规则？

**A**: 编辑 `tools/check_library_usage.py`：
```python
# 添加到 FORBIDDEN_PATTERNS 列表
FORBIDDEN_PATTERNS = [
    {
        'pattern': r'def\s+my_function\s*\(',
        'description': '自定义函数描述',
        'suggestion': '使用 基础库.功能'
    },
    # ... 更多规则
]
```

### Q4: 生成的模板不满足需求怎么办？

**A**: 两种方式：
1. 修改生成后的代码（推荐）
2. 在 `tools/create_example.py` 中添加新模板类型

### Q5: Pre-commit太慢了怎么办？

**A**: 优化方法：
```bash
# 只对修改的文件运行检查
git commit  # 默认行为

# 跳过某些检查
SKIP=check-yaml,check-json git commit

# 紧急情况跳过所有检查（不推荐）
git commit --no-verify
```

### Q6: 如何禁用某个工具？

**A**: 
- AI规则：删除或重命名 `.cursorrules`
- 自动检查：不运行该脚本即可
- Pre-commit：`pre-commit uninstall`

### Q7: 工具支持哪些AI？

**A**: 
- ✅ Cursor（完全支持 .cursorrules）
- ✅ GitHub Copilot（支持 .github/copilot-instructions.md）
- ✅ Codeium（支持自定义规则）
- ⚠️ 其他AI：可能需要手动在提示词中说明规则

---

## 📚 相关文档

- **开发规范**: `DEVELOPMENT_GUIDE.md`
- **基础库API**: `LIBRARY_REFERENCE.md`
- **示例索引**: `EXAMPLES_INDEX.md`
- **AI规则**: `.cursorrules`

---

## 🎯 总结

使用这5个工具，可以：

1. **预防问题**（.cursorrules）- AI自动遵守规范
2. **快速参考**（EXAMPLES_INDEX.md）- 找到正确示例
3. **检测问题**（check_library_usage.py）- 发现不合规代码
4. **标准起点**（create_example.py）- 正确的代码框架
5. **强制执行**（pre-commit）- 提交前自动检查

**预期效果**：
- ✅ 减少 80% 的不合规代码
- ✅ 大幅降低提示词复杂度
- ✅ 确保代码质量一致性

---

**Generated by HydroClaude Development Team**
**Last Updated: 2025-10-27**
