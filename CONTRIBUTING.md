# 贡献指南

感谢你考虑为 HydroClaude 做出贡献！

本文档提供了如何为项目贡献的详细指南。

---

## 📋 目录

- [行为准则](#行为准则)
- [如何贡献](#如何贡献)
- [开发流程](#开发流程)
- [代码规范](#代码规范)
- [测试要求](#测试要求)
- [提交规范](#提交规范)
- [Pull Request流程](#pull-request流程)
- [常见问题](#常见问题)

---

## 行为准则

### 我们的承诺

为了促进一个开放和友好的环境，我们作为贡献者和维护者承诺：无论年龄、体型、残疾、种族、性别认同和表达、经验水平、教育程度、社会经济地位、国籍、个人外貌、种族、宗教或性认同和性取向如何，参与我们项目和社区的每个人都不会受到骚扰。

### 我们的标准

有助于创造积极环境的行为包括：

- ✅ 使用友好和包容的语言
- ✅ 尊重不同的观点和经验
- ✅ 优雅地接受建设性批评
- ✅ 关注对社区最有利的事情
- ✅ 对其他社区成员表示同情

不可接受的行为包括：

- ❌ 使用性化语言或图像，以及不受欢迎的性关注或骚扰
- ❌ 恶意评论、侮辱性/贬损性评论和人身或政治攻击
- ❌ 公开或私下骚扰
- ❌ 未经明确许可发布他人的私人信息（如地址、电子邮件）
- ❌ 在专业环境中可能被合理认为不适当的其他行为

---

## 如何贡献

### 报告Bug

在报告Bug之前，请确保：

1. **检查文档**：问题可能在文档中已有解决方案
2. **搜索Issues**：问题可能已经被报告

如果确定是新Bug，请[创建Issue](https://github.com/your-org/hydroclaude/issues/new)并包含：

- ✅ 清晰的标题和描述
- ✅ 重现步骤（越详细越好）
- ✅ 预期行为和实际行为
- ✅ 系统信息（OS, Python版本等）
- ✅ 错误日志和截图（如适用）

**Bug报告模板**：

```markdown
**描述**
简要描述Bug

**重现步骤**
1. 执行 '...'
2. 点击 '...'
3. 看到错误

**预期行为**
应该发生什么

**实际行为**
实际发生了什么

**系统信息**
- OS: [例如 Ubuntu 20.04]
- Python: [例如 3.12.0]
- HydroClaude版本: [例如 2.0.0]

**额外信息**
任何其他相关信息
```

### 请求功能

我们欢迎功能请求！请[创建Issue](https://github.com/your-org/hydroclaude/issues/new)并包含：

- ✅ 功能的清晰描述
- ✅ 使用场景（为什么需要这个功能）
- ✅ 可能的实现方案（如有想法）
- ✅ 相关的参考资料

**功能请求模板**：

```markdown
**功能描述**
清晰简洁地描述你想要的功能

**使用场景**
描述这个功能的使用场景

**可能的解决方案**
描述你考虑的解决方案

**替代方案**
描述你考虑过的替代方案

**额外信息**
任何其他相关信息
```

### 改进文档

文档改进同样重要！你可以：

- 修正错别字和语法错误
- 改进不清晰的说明
- 添加更多示例
- 翻译文档到其他语言

---

## 开发流程

### 1. Fork 和 Clone

```bash
# Fork 项目到你的 GitHub 账号
# 然后 Clone

git clone https://github.com/YOUR_USERNAME/hydroclaude.git
cd hydroclaude

# 添加上游仓库
git remote add upstream https://github.com/ORIGINAL_OWNER/hydroclaude.git
```

### 2. 创建分支

```bash
# 从 main 分支创建新分支
git checkout main
git pull upstream main
git checkout -b feature/my-feature

# 分支命名规范：
# feature/功能名称    - 新功能
# fix/问题描述        - Bug修复
# docs/文档主题       - 文档更新
# refactor/重构内容   - 代码重构
# test/测试内容       - 测试相关
```

### 3. 设置开发环境

```bash
# 创建虚拟环境（推荐）
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 安装开发依赖
pip install pytest pytest-html pytest-cov black pylint
```

### 4. 进行开发

**核心原则：基础库优先（LIBRARY FIRST）⚠️**

在编写代码之前：

```
✅ 第1步：查阅 LIBRARY_REFERENCE.md
✅ 第2步：搜索是否有对应的基础库
✅ 第3步：查看 examples/ 下的示例
✅ 第4步：如果有基础库，必须使用它！
❌ 禁止：重复实现基础库已有的功能
```

**推荐求解器**：

```python
# ✅ 推荐（性能最好，精度最高）
from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver

# ❌ 不推荐（已废弃）
# from solvers.single_canal_solver import SingleCanalSolver
# from solvers.canal_solver import CanalSolver
```

**必须使用的工具**：

```python
# 结果验证（必须）
from utils.result_validator import quick_validate_steady_state

# 水力学计算（必须）
from utils.canal_utils import (
    compute_steady_uniform_flow,
    compute_critical_depth,
    compute_froude_number
)

# 绘图（推荐）
from utils.plot_helper import PlotHelper
```

### 5. 编写测试

**所有新功能都必须有测试！**

```python
import pytest
from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver

class TestMyFeature:
    """测试我的新功能"""
    
    @pytest.fixture
    def solver(self):
        """创建求解器实例"""
        return HydrostaticCanalSolver(
            L=1000.0,
            B=5.0,
            S0=0.001,
            n=0.025,
            nx=101
        )
    
    def test_my_feature(self, solver):
        """测试特定功能"""
        # 准备
        Q_target = 10.0
        
        # 执行
        result = solver.solve_steady_state(Q_target=Q_target)
        
        # 断言
        assert result['converged'] == True
        flow_error = abs(result['Q_final'] - Q_target) / Q_target * 100
        assert flow_error < 0.01
```

运行测试：

```bash
# 运行所有测试
./run_tests.sh

# 运行特定测试
pytest tests/backend/test_my_feature.py -v

# 生成覆盖率报告
pytest tests/backend/ --cov=solvers --cov=utils --cov-report=html
```

### 6. 代码格式化

```bash
# 使用 black 格式化代码
black solvers/ utils/ tests/

# 使用 pylint 检查代码
pylint solvers/ utils/
```

### 7. 提交代码

**提交信息规范**：

```bash
# 格式
<type>(<scope>): <subject>

# 类型（type）
feat:     新功能
fix:      Bug修复
docs:     文档更新
style:    代码格式（不影响代码运行）
refactor: 重构
test:     测试相关
chore:    构建过程或辅助工具的变动

# 示例
git commit -m "feat(solver): 添加新的水工结构类型"
git commit -m "fix(utils): 修复临界水深计算错误"
git commit -m "docs: 更新快速开始指南"
```

---

## 代码规范

### Python 代码规范

#### 导入顺序

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
模块功能描述

Author: [作者名]
Date: [日期]
"""

# 1. 标准库
import sys
import os
from typing import Optional, Tuple

# 2. 第三方库
import numpy as np
import matplotlib.pyplot as plt

# 3. 路径设置
script_path = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(script_path))
sys.path.insert(0, project_root)

# 4. HydroClaude基础库（必须）
from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver
from utils.canal_utils import compute_steady_uniform_flow
from utils.result_validator import quick_validate_steady_state
```

#### 命名规范

```python
# 类名：大驼峰
class HydrostaticCanalSolver:
    pass

# 函数名：小写+下划线
def compute_steady_uniform_flow():
    pass

# 常量：大写+下划线
MAX_ITERATIONS = 1000
CONVERGENCE_TOL = 0.1

# 变量：小写+下划线
flow_rate = 10.0
water_depth = 2.5
```

#### 类型注解（推荐）

```python
def compute_flow(
    width: float,
    depth: float,
    slope: float,
    roughness: float
) -> Tuple[float, Dict[str, float]]:
    """
    计算流量
    
    Args:
        width: 渠道宽度 (m)
        depth: 水深 (m)
        slope: 底坡
        roughness: 糙率系数
        
    Returns:
        (flow_rate, diagnostics): 流量和诊断信息
    """
    pass
```

### TypeScript/React 代码规范

#### 组件结构

```typescript
import React, { useState, useEffect } from 'react';
import { Button, Modal } from 'antd';

// 接口定义
interface MyComponentProps {
  title: string;
  visible: boolean;
  onClose: () => void;
}

// 组件定义
export const MyComponent: React.FC<MyComponentProps> = ({
  title,
  visible,
  onClose
}) => {
  // 状态
  const [loading, setLoading] = useState(false);

  // 副作用
  useEffect(() => {
    // ...
  }, []);

  // 事件处理
  const handleSubmit = () => {
    // ...
  };

  // 渲染
  return (
    <Modal title={title} open={visible} onCancel={onClose}>
      {/* 内容 */}
    </Modal>
  );
};
```

---

## 测试要求

### 测试覆盖要求

- ✅ 所有新功能必须有单元测试
- ✅ 关键功能必须有集成测试
- ✅ Bug修复必须有回归测试
- ✅ 测试覆盖率应 > 80%

### 测试命名规范

```python
class TestFeatureName:
    """测试功能名称"""
    
    def test_basic_case(self):
        """测试基本情况"""
        pass
    
    def test_edge_case(self):
        """测试边界情况"""
        pass
    
    def test_error_handling(self):
        """测试错误处理"""
        pass
```

### 性能要求

新功能应满足：

- ✅ 流量误差 < 0.01%
- ✅ 迭代次数 < 100次（复杂场景）
- ✅ 收敛成功率 > 95%

---

## 提交规范

### Commit Message 格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

#### Type（必须）

- `feat`: 新功能
- `fix`: Bug修复
- `docs`: 文档变更
- `style`: 代码格式（不影响代码运行）
- `refactor`: 重构
- `test`: 测试相关
- `chore`: 构建/工具变更

#### Scope（可选）

- `solver`: 求解器相关
- `utils`: 工具函数相关
- `structure`: 水工结构相关
- `frontend`: 前端相关
- `docs`: 文档相关

#### Subject（必须）

- 简短描述（<50字符）
- 使用祈使句
- 不要以句号结尾

#### Body（可选）

- 详细描述
- 解释"为什么"而非"是什么"

#### Footer（可选）

- 关闭Issue：`Closes #123`
- 破坏性变更：`BREAKING CHANGE: ...`

### 示例

```
feat(solver): 添加新的水轮机结构

- 实现水轮机特性曲线计算
- 添加相关的单元测试
- 更新文档和示例

Closes #456
```

---

## Pull Request流程

### 1. 确保代码质量

在提交PR之前：

```bash
# 运行所有测试
./run_tests.sh

# 代码格式化
black solvers/ utils/ tests/

# 代码检查
pylint solvers/ utils/
```

### 2. 更新文档

- [ ] 更新 README.md（如适用）
- [ ] 更新 LIBRARY_REFERENCE.md（如有新API）
- [ ] 更新 CHANGELOG.md
- [ ] 添加/更新示例（如适用）

### 3. 创建 Pull Request

**PR标题格式**：

```
<type>: <简短描述>

# 示例
feat: 添加2D水流模拟功能
fix: 修复临界水深计算错误
docs: 更新贡献指南
```

**PR描述模板**：

```markdown
## 变更描述
简要描述这个 PR 做了什么

## 变更类型
- [ ] 新功能
- [ ] Bug修复
- [ ] 文档更新
- [ ] 性能优化
- [ ] 代码重构
- [ ] 测试相关

## 测试
- [ ] 所有现有测试通过
- [ ] 添加了新测试
- [ ] 手动测试完成

## 检查清单
- [ ] 代码遵循项目规范
- [ ] 更新了相关文档
- [ ] 没有引入新的警告
- [ ] 提交信息遵循规范
- [ ] 性能要求满足

## 相关 Issue
Closes #issue_number

## 截图（如适用）
...
```

### 4. 响应Review

- ✅ 及时响应reviewer的评论
- ✅ 根据反馈修改代码
- ✅ 解释设计决策（如有必要）
- ✅ 保持友好和专业

### 5. 合并后

- ✅ 删除功能分支
- ✅ 更新本地仓库
- ✅ 庆祝贡献！🎉

---

## 常见问题

### Q: 我应该使用哪个求解器？

**A**: 优先使用 `HydrostaticCanalSolver`（稳态明渠流动）

查看[用户使用手册](./📖_用户使用手册.md) - 常见问题章节。

### Q: 如何验证计算结果？

**A**: 必须使用 `ResultValidator`

```python
from utils.result_validator import quick_validate_steady_state

validator = quick_validate_steady_state(
    solver=solver,
    result_dict=result,
    Q_target=Q_target,
    name="我的场景"
)
```

### Q: 测试失败怎么办？

**A**: 按以下步骤排查：

1. 检查依赖是否完整
2. 确保使用正确的求解器
3. 验证初始条件
4. 查看测试输出日志

详见[开发者贡献指南](./🎓_开发者贡献指南.md) - 常见问题章节。

### Q: 如何添加新的水工结构？

**A**: 继承 `Structure` 基类

```python
from solvers.gate import Structure

class MyStructure(Structure):
    def __init__(self, position: float, ...):
        super().__init__(position)
        # ...
    
    def compute_flow(self, h_upstream: float, h_downstream: float) -> float:
        """计算通过结构的流量"""
        pass
    
    def compute_head_loss(self, Q: float, h_upstream: float) -> float:
        """计算水头损失"""
        pass
```

---

## 获取帮助

如果在贡献过程中遇到问题，可以：

1. **查看文档**：
   - [用户使用手册](./📖_用户使用手册.md)
   - [开发者贡献指南](./🎓_开发者贡献指南.md)
   - [基础库API文档](./LIBRARY_REFERENCE.md)

2. **搜索 Issues**：问题可能已经被讨论过

3. **创建 Issue**：描述你遇到的问题

4. **联系我们**：
   - 邮件：dev@hydroclaude.org
   - GitHub Discussions

---

## 致谢

感谢你为 HydroClaude 做出贡献！

每一个贡献，无论大小，都会让这个项目变得更好。

---

**HydroClaude Development Team**  
**Last Updated: 2025-11-20**
