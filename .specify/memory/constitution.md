# HydroClaude Constitution

**智能水力学计算平台 - 开发原则与治理规范**

## 核心原则

### I. 基础库优先（Library-First Development）

**强制性原则 - 最高优先级 ⚠️**

所有功能开发必须严格遵循以下顺序：

1. **查阅基础库**：在编写任何代码之前，必须先查阅 `LIBRARY_REFERENCE.md`
2. **使用现有组件**：如果基础库中已存在相应功能，必须使用它，禁止重复实现
3. **参考示例代码**：查看 `examples/` 下的 `_v2` 版本示例学习最佳实践
4. **扩展与文档**：如需新功能，实现后必须更新 `LIBRARY_REFERENCE.md` 和 `DEVELOPMENT_GUIDE.md`

**强制使用的基础库清单：**

```python
# ✅ 求解器（唯一推荐）
from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver

# ✅ 结果验证（必须使用）
from utils.result_validator import quick_validate_steady_state

# ✅ 水力学计算（禁止自己实现）
from utils.canal_utils import (
    compute_steady_uniform_flow,
    compute_critical_depth,
    compute_froude_number
)

# ✅ 可视化（优先使用）
from utils.plot_helper import PlotHelper
from utils.visualization_templates import VisualizationTemplates

# ✅ 水工结构
from solvers.gate import SluiceGate, BroadCrestedWeir, Orifice
```

**禁止的行为：**
- ❌ 使用废弃的求解器（SingleCanalSolver, CanalSolver）
- ❌ 手写流量验证函数
- ❌ 自己实现水力学计算
- ❌ 直接使用 matplotlib 绘图（除非 PlotHelper 无对应模板）

### II. 规格驱动开发（Spec-Driven Development）

**采用 Spec-Kit 标准化工作流：**

```
规格（Specify） → 计划（Plan） → 任务（Tasks） → 实现（Implement）
```

**必须遵循的开发阶段：**

1. **Constitution** - 确立项目原则和约束
2. **Specify** - 定义"什么"和"为什么"（关注用户价值）
3. **Clarify** - 结构化澄清需求，填补空白
4. **Plan** - 创建技术实现方案（关注"怎么做"）
5. **Tasks** - 拆解为可执行任务
6. **Analyze** - 一致性检查
7. **Implement** - 按规范实现

**规格文档要求：**
- 所有新功能必须在 `specs/NNN-feature-name/` 下创建规格文档
- 必须包含：`spec.md`, `plan.md`, `tasks.md`
- 可选但推荐：`research.md`, `data-model.md`, `contracts/`, `quickstart.md`

### III. 测试优先（Test-First - NON-NEGOTIABLE）

**不可协商的强制性原则：**

1. **TDD 必须执行**：测试编写 → 用户批准 → 测试失败 → 然后实现
2. **Red-Green-Refactor**：严格遵循 TDD 循环
3. **验证必须存在**：所有稳态求解后必须使用 `ResultValidator` 验证结果

**测试覆盖要求：**
- 单元测试：核心算法和工具函数
- 集成测试：求解器与结构物的组合
- 端到端测试：完整工作流
- API 测试：所有后端端点

**性能基准（使用 HydrostaticCanalSolver）：**
- ✅ 流量误差：**0.000000%**（所有场景）
- ✅ 迭代次数：**0-1次**（简单）/ **1-10次**（复杂）
- ✅ 收敛成功率：**100%**
- ✅ 闸门误差：**< 1%**

### IV. 水力学算法正确性（Hydraulic Accuracy）

**核心计算要求：**

1. **Saint-Venant 方程**：准确实现一维水流控制方程
2. **数值稳定性**：确保求解器收敛，避免振荡
3. **物理合理性**：验证结果符合水力学原理（Froude 数、临界水深等）
4. **误差控制**：流量误差 < 0.01%，水深误差 < 1mm

**边界条件处理：**
- 上游：流量边界或水深边界
- 下游：水深边界或临界水深
- 结构物：使用标准水力学公式（闸门、堰、孔口）

### V. 代码质量与可维护性（Code Quality）

**代码标准：**

1. **标准模板**：所有新脚本必须遵循标准代码模板
   ```python
   #!/usr/bin/env python
   # -*- coding: utf-8 -*-
   """功能描述"""
   
   import sys, os
   # 路径设置
   # 基础库导入（必须）
   # 主函数实现
   ```

2. **命名规范**：
   - 变量：小写下划线（`water_depth`, `flow_rate`）
   - 类：大驼峰（`HydrostaticCanalSolver`）
   - 函数：小写下划线（`compute_steady_flow`）
   - 常量：大写下划线（`MAX_ITERATIONS`）

3. **文档要求**：
   - 所有公共函数必须有 docstring
   - 复杂算法必须有注释说明
   - 所有模块必须有模块级文档

4. **Linter 合规**：
   - 使用 `black` 格式化 Python 代码
   - 使用 `flake8` 检查代码质量
   - 使用 `mypy` 进行类型检查（推荐）

### VI. 版本控制与分支管理（Version Control）

**Git 工作流：**

1. **分支命名**：
   - 功能分支：`feature/NNN-feature-name`
   - 修复分支：`fix/bug-description`
   - Spec-Kit 分支：自动生成（如 `003-user-management-system`）

2. **提交规范**：
   ```
   type(scope): summary
   
   - Detailed description
   - Why this change is needed
   
   Type: feat, fix, docs, refactor, test, perf, chore
   ```

3. **代码审查**：
   - 所有 PR 必须经过审查
   - 必须通过所有测试
   - 必须更新相关文档

### VII. 可观察性与调试（Observability）

**日志要求：**

1. **结构化日志**：使用 Python `logging` 模块
2. **日志级别**：
   - DEBUG：详细计算过程
   - INFO：关键步骤和结果
   - WARNING：收敛问题或性能警告
   - ERROR：计算失败或异常

3. **性能监控**：
   - 记录求解器迭代次数
   - 记录计算时间
   - 记录内存使用（大规模计算）

### VIII. 安全与数据隐私（Security）

**安全原则：**

1. **输入验证**：所有用户输入必须验证
2. **文件操作**：使用安全的路径处理
3. **API 安全**：使用适当的认证和授权
4. **敏感数据**：不要在日志中记录敏感信息

### IX. 简洁性原则（Simplicity - YAGNI）

**设计哲学：**

1. **从简单开始**：不要过度设计
2. **YAGNI**：You Aren't Gonna Need It - 只实现当前需要的功能
3. **重构优于预设**：先让它工作，再让它优雅
4. **可读性优先**：代码是写给人看的

## 技术栈约束

### 后端技术栈

- **语言**：Python 3.8+
- **Web 框架**：FastAPI
- **数值计算**：NumPy, SciPy
- **可视化**：Matplotlib, Plotly
- **数据库**：SQLite（开发）/ PostgreSQL（生产）
- **API 规范**：OpenAPI 3.x

### 前端技术栈

- **框架**：React 18+
- **UI 库**：Material-UI / Ant Design
- **状态管理**：React Context / Redux（按需）
- **地图**：Mapbox GL / Leaflet
- **图表**：Plotly.js / ECharts

### 开发工具

- **包管理**：pip, npm
- **测试**：pytest, jest
- **CI/CD**：GitHub Actions
- **文档**：Markdown, Sphinx

## 开发工作流规范

### 标准工作流程

**新功能开发：**

```bash
# 1. 使用 Spec-Kit 创建规格
/speckit.specify [功能描述]

# 2. 澄清需求
/speckit.clarify

# 3. 创建技术方案
/speckit.plan

# 4. 生成任务列表
/speckit.tasks

# 5. 一致性检查
/speckit.analyze

# 6. 实现功能
/speckit.implement

# 7. 验证结果
pytest tests/
```

**Bug 修复：**

```bash
# 1. 重现问题并编写失败的测试
# 2. 修复代码直到测试通过
# 3. 验证没有引入新问题
```

### 质量检查清单

**提交代码前必须确认：**

- [ ] 使用了正确的基础库（HydrostaticCanalSolver 等）
- [ ] 使用了 ResultValidator 验证结果
- [ ] 使用了 PlotHelper 或 VisualizationTemplates 绘图
- [ ] 没有重复实现基础库已有功能
- [ ] 代码遵循标准模板结构
- [ ] 流量误差 < 0.01%
- [ ] 迭代次数合理（< 100次）
- [ ] 所有测试通过
- [ ] 更新了相关文档
- [ ] 代码通过 linter 检查

## 关键文档索引

**开发前必读：**
- `LIBRARY_REFERENCE.md` - 完整的基础库 API 文档（必读！）
- `DEVELOPMENT_GUIDE.md` - 开发规范和最佳实践
- `EXAMPLES_INDEX.md` - 快速找到参考示例
- `SCRIPT_UPGRADE_SUMMARY.md` - 最佳实践案例
- `.specify/memory/constitution.md` - 本文档（项目宪法）

**快速查询：**
- 需要什么功能？→ 查 `LIBRARY_REFERENCE.md`
- 怎么用？→ 看 `examples/` 下的 `_v2` 示例
- 性能基准？→ 看 `SCRIPT_UPGRADE_SUMMARY.md`
- 开发流程？→ 看 `specs/` 下的规格文档

## 治理规则

### 宪法优先级

1. **本宪法优先于所有其他开发实践**
2. **代码审查必须验证宪法合规性**
3. **违反宪法的代码必须修改，不得合并**

### 宪法修订

**修订流程：**
1. 提出修订提案（包含理由、影响分析）
2. 团队讨论与批准
3. 更新文档并通知所有成员
4. 制定迁移计划（如有需要）

**修订记录：**
- 使用语义化版本号（MAJOR.MINOR.PATCH）
- 重大变更增加 MAJOR 版本
- 新增原则增加 MINOR 版本
- 文字修正增加 PATCH 版本

### 例外处理

**申请例外的条件：**
- 技术限制导致无法遵循某原则
- 紧急修复需要快速响应
- 实验性功能需要探索

**例外流程：**
1. 在 PR 中明确说明例外原因
2. 获得项目维护者批准
3. 记录例外并设置技术债务跟踪

## 版本信息

**版本**: 1.0.0  
**制定日期**: 2025-11-20  
**最后修订**: 2025-11-20  
**生效日期**: 2025-11-20  

**制定者**: HydroClaude Development Team  
**适用范围**: HydroClaude 项目的所有代码仓库和子项目

---

## 附录：三个关键问题

**每次编写代码前必问：**

1. **LIBRARY_REFERENCE.md 里有这个功能吗？**
   - 有 → 使用它！
   - 没有 → 继续问题 2

2. **examples/ 下有类似的示例吗？**
   - 有 → 参考它！
   - 没有 → 继续问题 3

3. **我是在重复造轮子吗？**
   - 是 → 停止！回到问题 1
   - 否 → 可以实现新功能（但要更新文档）

---

**记住这三点：**

1. **先查文档，后写代码**（LIBRARY_REFERENCE.md）
2. **必须使用基础库**（禁止重复造轮子）
3. **必须验证结果**（ResultValidator）

---

*"好的规范是自由的基础，而非束缚。"*  
*— HydroClaude Philosophy*
