# 🌱 Spec-Kit 快速开始指南

**HydroClaude 现已整合 GitHub Spec-Kit 规格驱动开发工具包**

---

## 📖 什么是 Spec-Kit？

Spec-Kit 是 **GitHub/Microsoft** 发布的开源工具包，实现"规格驱动开发（Spec-Driven Development, SDD）"方法论。它通过结构化的工作流，让 AI 代理有章可循，避免"凭感觉写代码"。

### 核心理念

- **Intent First** - 明确"什么/为什么"，再谈"怎么做"
- **Rich Specs** - 用结构化规格约束 AI
- **Multi-step Refinement** - 多阶段收敛，不是一次性大 Prompt
- **Model-Agnostic** - 与多种 AI 代理协同

---

## 🚀 快速开始

### 1️⃣ 可用的 Spec-Kit 命令

在 Cursor 中，你可以使用以下斜杠命令：

```bash
/speckit.constitution   # 建立/更新项目原则
/speckit.specify       # 创建功能规格
/speckit.clarify       # 澄清模糊需求
/speckit.plan          # 制定技术方案
/speckit.tasks         # 生成任务列表
/speckit.analyze       # 一致性检查
/speckit.implement     # 执行实现
/speckit.checklist     # 生成质量清单
```

### 2️⃣ 标准工作流程

```
步骤1: /speckit.specify
       ↓ 描述你要构建什么（关注用户价值）
       
步骤2: /speckit.clarify （可选）
       ↓ 澄清需求中的模糊点
       
步骤3: /speckit.plan
       ↓ 创建技术实现方案
       
步骤4: /speckit.tasks
       ↓ 拆解为可执行任务
       
步骤5: /speckit.analyze （可选）
       ↓ 检查文档一致性
       
步骤6: /speckit.implement
       ↓ 开始编码实现
```

---

## 💡 实际使用示例

### 示例 1：开发新的水力学功能

```bash
# 1. 创建功能规格
/speckit.specify 开发一个多级串联渠道求解器，支持不同渠段的几何参数和糙率系数。
需要处理渠段连接处的边界条件，并验证质量和动量守恒。

# 2. AI 会自动生成 specs/001-multi-stage-canal-solver/ 目录和 spec.md

# 3. 制定技术方案
/speckit.plan

# 4. 生成任务列表
/speckit.tasks

# 5. 开始实现
/speckit.implement
```

### 示例 2：重构现有代码

```bash
# 1. 描述重构目标
/speckit.specify 重构 canal_utils.py，将水力学计算函数模块化，
增加类型提示，改进错误处理，添加单元测试

# 2. 制定重构计划
/speckit.plan

# 3. 生成重构任务
/speckit.tasks

# 4. 执行重构
/speckit.implement
```

### 示例 3：API 设计

```bash
# 1. 定义 API 规格
/speckit.specify 设计 RESTful API 用于远程运行水力学计算任务。
支持异步任务提交、状态查询、结果下载。需要考虑认证、限流和错误处理。

# 2. 澄清 API 细节
/speckit.clarify

# 3. 制定 API 实现方案
/speckit.plan

# 4. 生成 API 开发任务
/speckit.tasks
```

---

## 📁 生成的文件结构

使用 Spec-Kit 后，会在项目中生成以下结构：

```
HydroClaude/
├── .specify/                    # Spec-Kit 配置
│   ├── memory/
│   │   └── constitution.md      # 项目宪法（已创建）
│   ├── scripts/                 # 自动化脚本
│   └── templates/               # 模板文件
│
├── .claude/                     # AI 代理配置
│   └── commands/                # Spec-Kit 命令定义
│       ├── speckit.specify.md
│       ├── speckit.plan.md
│       ├── speckit.tasks.md
│       └── ...
│
└── specs/                       # 功能规格目录
    └── 001-feature-name/        # 自动编号
        ├── spec.md              # 功能规格
        ├── plan.md              # 技术方案
        ├── tasks.md             # 任务列表
        ├── research.md          # 技术研究（可选）
        ├── data-model.md        # 数据模型（可选）
        ├── contracts/           # API 契约（可选）
        └── quickstart.md        # 快速验证（可选）
```

---

## 🎯 何时使用 Spec-Kit

### ✅ 必须使用：

- 复杂新功能开发（涉及多个模块）
- 重大重构或架构变更
- 需要团队协作的功能
- 公开 API 或接口变更

### 🟡 可选使用：

- 简单 Bug 修复（但仍建议创建 spec）
- 单文件小改动
- 文档更新

### ⚡ 快速开发场景：

对于紧急修复或极简单改动，可以跳过 Spec-Kit，但必须：
1. 在 commit message 中说明跳过原因
2. 事后补充规格文档（如适用）
3. 仍需遵循基础库优先原则

---

## 📚 与 HydroClaude 开发规范的整合

Spec-Kit 与 HydroClaude 的基础库优先原则完美结合：

```
规格驱动层（Spec-Kit）：
  定义 What & Why
  ↓
基础库实现层（HydroClaude）：
  使用现有库实现 How
  ↓
验证层（ResultValidator）：
  确保结果正确性
```

### 完整示例工作流：

```bash
# 1. 使用 Spec-Kit 定义规格
/speckit.specify 开发闸门优化算法

# 2. 制定技术方案时，AI 会查阅 LIBRARY_REFERENCE.md
/speckit.plan

# 3. 生成的任务会引用现有基础库
/speckit.tasks
# 输出：
# - Task 1: 使用 HydrostaticCanalSolver 作为基础求解器
# - Task 2: 使用 SluiceGate 类定义闸门
# - Task 3: 使用 ResultValidator 验证优化结果

# 4. 实现时严格遵循基础库优先原则
/speckit.implement
```

---

## 🔧 常见问题

### Q1: Spec-Kit 命令在哪里？

**A:** 命令定义在 `.claude/commands/` 目录下。在 Cursor 中输入 `/speckit.` 会自动提示所有可用命令。

### Q2: 如何查看项目宪法？

**A:** 打开 `.specify/memory/constitution.md` 查看 HydroClaude 的完整开发原则。

### Q3: 规格文档保存在哪里？

**A:** 所有规格保存在 `specs/NNN-feature-name/` 目录下，其中 NNN 是自动编号。

### Q4: Spec-Kit 会覆盖现有的开发规范吗？

**A:** 不会。Spec-Kit 是增强工具，与现有的 `.cursorrules` 和 `LIBRARY_REFERENCE.md` 协同工作。

### Q5: 我可以不使用 Spec-Kit 吗？

**A:** 可以。对于简单改动可以跳过，但复杂功能强烈建议使用，以确保质量和可维护性。

---

## 📖 进阶资源

### HydroClaude 文档：

- `.specify/memory/constitution.md` - 项目宪法（核心原则）
- `.cursorrules` - AI 开发规则（已整合 Spec-Kit）
- `LIBRARY_REFERENCE.md` - 基础库 API 文档
- `DEVELOPMENT_GUIDE.md` - 开发规范

### Spec-Kit 官方资源：

- GitHub 仓库：https://github.com/github/spec-kit
- 官方文档：https://github.github.io/spec-kit/
- 方法论说明：https://github.com/github/spec-kit/blob/main/spec-driven.md

---

## 🎓 最佳实践

### ✅ 推荐做法：

1. **功能规格要具体**：描述用户场景和验收标准
2. **技术方案要详细**：包含架构、数据模型、API 设计
3. **任务拆解要合理**：每个任务可独立完成和测试
4. **持续验证一致性**：使用 `/speckit.analyze` 检查

### ❌ 避免的坑：

1. 规格过于模糊（导致方案偏离目标）
2. 跳过澄清步骤（需求理解不一致）
3. 任务粒度过大（难以跟踪进度）
4. 不更新规格文档（代码与文档脱节）

---

## 🎉 开始使用

现在你已经准备好使用 Spec-Kit 了！

**第一步：** 在 Cursor 中输入：

```
/speckit.specify 我想开发一个...
```

Spec-Kit 会引导你完成整个开发过程，从规格到实现，确保高质量的代码产出。

---

## 💬 获取帮助

如果遇到问题：

1. 查看 `.claude/commands/speckit.*.md` 了解命令详情
2. 参考 `.specify/memory/constitution.md` 了解项目原则
3. 查看 `specs/` 下的已有规格作为示例
4. 阅读 `.cursorrules` 了解完整开发规范

---

**记住：好的规范是自由的基础，而非束缚。**

*— HydroClaude Philosophy*

---

**HydroClaude Development Team**  
**Powered by GitHub Spec-Kit**  
**Created: 2025-11-20**
