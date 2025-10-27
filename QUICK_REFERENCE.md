# HydroClaude AI开发快速参考

> 5分钟速查手册

---

## 🚀 立即开始

```bash
# 查阅示例索引（找参考代码）
cat EXAMPLES_INDEX.md

# 生成新示例（自动生成标准代码）
python tools/create_example.py my_test "测试描述"

# 检查代码（确保使用基础库）
python tools/check_library_usage.py examples/my_test/

# 安装pre-commit（提交前自动检查）
pip install pre-commit && pre-commit install
```

---

## 📚 必须使用的基础库

```python
# ✅ 求解器（唯一推荐）
from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver

# ✅ 验证（必须）
from utils.result_validator import quick_validate_steady_state

# ✅ 水力学计算（必须）
from utils.canal_utils import compute_steady_uniform_flow

# ✅ 绘图（推荐）
from utils.plot_helper import PlotHelper

# ✅ 结构
from solvers.gate import SluiceGate, BroadCrestedWeir, Orifice
```

---

## ❌ 禁止的行为

```python
# ❌ 不要使用废弃的求解器
from solvers.single_canal_solver import SingleCanalSolver  # 已废弃

# ❌ 不要自己写验证函数
def validate_flow(Q, Q_target):  # 使用 ResultValidator
    pass

# ❌ 不要手写matplotlib代码
fig, ax = plt.subplots()  # 使用 PlotHelper
```

---

## 🔍 快速查询

| 需要实现 | 参考文档/示例 |
|---------|-------------|
| 任何功能 | `LIBRARY_REFERENCE.md` |
| 找示例代码 | `EXAMPLES_INDEX.md` |
| 单闸门 | `examples/.../07_sluice_gate_flow_v2.py` |
| 多闸门 | `examples/.../12_advanced_optimized_v2.py` |
| 绘制纵剖面 | `PlotHelper.plot_profile` |
| 验证结果 | `quick_validate_steady_state` |

---

## 📝 标准代码模板

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""描述"""

import sys, os
script_path = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(script_path)))
sys.path.insert(0, project_root)

# ========== 基础库导入（必须）==========
from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver
from utils.canal_utils import compute_steady_uniform_flow
from utils.result_validator import quick_validate_steady_state
from utils.plot_helper import PlotHelper

import numpy as np
import matplotlib.pyplot as plt

def main():
    # 1. 参数设置
    # 2. 创建求解器
    solver = HydrostaticCanalSolver(...)
    
    # 3. 初始化
    h_uniform = compute_steady_uniform_flow(Q, B, S0, n)
    solver.h[:] = h_uniform
    
    # 4. 求解
    result = solver.solve_steady_state(
        Q_target=Q, 
        convergence_tol=0.1  # 推荐
    )
    
    # 5. 验证（必须！）
    validator = quick_validate_steady_state(
        solver, result, Q, "场景名"
    )
    
    # 6. 可视化
    plotter = PlotHelper()
    fig = plotter.plot_profile(x, h)
    
    return validator

if __name__ == '__main__':
    main()
```

---

## 🛠️ 工具命令

```bash
# 生成代码
python tools/create_example.py <名称> "<描述>"

# 检查代码
python tools/check_library_usage.py <文件或目录>

# 测试工具
python tools/test_all_tools.py

# 运行pre-commit
pre-commit run --all-files
```

---

## 📖 完整文档

- **工具使用指南**: `AI_DEVELOPMENT_TOOLS.md` ⭐⭐⭐
- **示例代码索引**: `EXAMPLES_INDEX.md` ⭐⭐⭐
- **开发规范**: `DEVELOPMENT_GUIDE.md`
- **基础库API**: `LIBRARY_REFERENCE.md`
- **AI规则**: `.cursorrules`（AI自动读取）

---

## 💡 关键提示

1. **开发前**先查 `EXAMPLES_INDEX.md`
2. **必须使用**基础库（不要重复实现）
3. **必须验证**结果（使用 ResultValidator）
4. **推荐容差** convergence_tol=0.1（极快收敛）

---

**快速求助**: 
- 需要什么功能？ → 查 `LIBRARY_REFERENCE.md`
- 怎么用？ → 看 `EXAMPLES_INDEX.md`
- 代码规范？ → 看 `.cursorrules`
