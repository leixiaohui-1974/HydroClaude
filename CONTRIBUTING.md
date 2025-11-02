# HydroClaude 开发者贡献指南

欢迎为 HydroClaude 做出贡献！本指南将帮助您了解如何参与项目开发。

## 目录

- [开发环境设置](#开发环境设置)
- [代码架构](#代码架构)
- [添加新功能](#添加新功能)
- [测试指南](#测试指南)
- [代码风格](#代码风格)
- [提交规范](#提交规范)
- [Pull Request 流程](#pull-request-流程)
- [文档要求](#文档要求)

---

## 开发环境设置

### 1. 克隆仓库

```bash
git clone https://github.com/yourusername/HydroClaude.git
cd HydroClaude
```

### 2. 创建虚拟环境

```bash
# 使用 venv
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 使用 conda
conda create -n hydroclaude python=3.9
conda activate hydroclaude
```

### 3. 安装依赖

```bash
# 基础依赖
pip install numpy scipy matplotlib

# 可选加速依赖
pip install numba  # JIT 编译加速

# 开发依赖
pip install pytest pytest-cov  # 测试
pip install black flake8        # 代码格式化和检查
pip install sphinx              # 文档生成
```

### 4. 运行测试验证

```bash
# 运行所有测试
python -m pytest tests/ -v

# 运行覆盖率测试
python -m pytest tests/ --cov=solvers --cov-report=html
```

---

## 代码架构

### 项目结构

```
HydroClaude/
├── solvers/              # 核心求解器模块
│   ├── water_temperature.py    # 水温求解器
│   ├── dissolved_oxygen.py     # 溶解氧求解器
│   ├── ice_cover.py            # 冰盖求解器
│   ├── nutrients.py            # 营养盐求解器
│   ├── phytoplankton.py        # 藻类求解器
│   └── hydraulics.py           # 水力学求解器
│
├── tests/                # 单元测试
│   ├── test_water_temperature.py
│   ├── test_dissolved_oxygen.py
│   ├── test_ice_cover.py
│   ├── test_nutrients.py
│   ├── test_phytoplankton.py
│   └── test_integration.py     # 集成测试
│
├── examples/             # 应用示例
│   ├── winter_river_simulation.py
│   ├── summer_eutrophication.py
│   └── spring_ice_breakup.py
│
├── tools/                # 辅助工具
│   ├── run_from_config.py       # 配置驱动模拟
│   ├── sensitivity_analysis.py  # 参数敏感性分析
│   └── export_data.py           # 数据导出
│
├── config/               # 配置文件
├── outputs/              # 输出结果
└── docs/                 # 文档
```

### 核心设计原则

1. **模块化**: 每个求解器独立实现，通过明确的接口通信
2. **可扩展性**: 易于添加新的物理过程和生态模块
3. **性能优化**: 支持 Numba JIT 编译加速
4. **数值稳定性**: 使用高阶数值格式和稳定性保证
5. **测试驱动**: 每个模块都有完整的单元测试

### 求解器接口规范

所有求解器应遵循以下接口规范:

```python
class MySolver:
    """
    求解器描述

    Parameters:
    -----------
    n_cells : int
        网格数量
    dx : float
        网格间距 (m)
    use_numba : bool
        是否使用 Numba 加速
    """

    def __init__(self, n_cells, dx, use_numba=False):
        self.n_cells = n_cells
        self.dx = dx
        self.use_numba = use_numba

        # 初始化状态变量
        self.state_variable = np.zeros(n_cells)

    def step(self, dt, *args, **kwargs):
        """
        推进一个时间步

        Parameters:
        -----------
        dt : float
            时间步长 (s)
        *args :
            其他必需参数

        Returns:
        --------
        state : dict
            当前状态字典
        """
        # 计算源汇项
        sources = self._compute_sources(*args, **kwargs)

        # 更新状态
        self.state_variable += sources * dt

        # 返回状态
        return {
            'state_variable': self.state_variable.copy(),
            'sources': sources
        }

    def _compute_sources(self, *args):
        """计算源汇项 (私有方法)"""
        pass
```

---

## 添加新功能

### 添加新的物理过程

假设要添加一个新的 "悬浮物 (Suspended Solids)" 求解器:

#### 1. 创建求解器文件

**文件:** `solvers/suspended_solids.py`

```python
#!/usr/bin/env python3
"""
HydroClaude 悬浮物传输模块

实现悬浮物的对流-扩散-沉降过程
"""

import numpy as np

class SuspendedSolidsSolver:
    """
    悬浮物传输求解器

    支持:
    - 对流传输
    - 扩散混合
    - 重力沉降
    - 再悬浮
    """

    def __init__(self, n_cells, dx, settling_velocity=0.001, resuspension_rate=0.0, use_numba=False):
        """
        初始化悬浮物求解器

        Parameters:
        -----------
        n_cells : int
            网格数量
        dx : float
            网格间距 (m)
        settling_velocity : float
            沉降速度 (m/s)
        resuspension_rate : float
            再悬浮速率 (kg/m2/s)
        use_numba : bool
            是否使用 Numba 加速
        """
        self.n_cells = n_cells
        self.dx = dx
        self.vs = settling_velocity
        self.kr = resuspension_rate
        self.use_numba = use_numba

        # 状态变量
        self.SS = np.zeros(n_cells)  # 悬浮物浓度 (kg/m3)

    def step(self, dt, u, h):
        """
        推进一个时间步

        Parameters:
        -----------
        dt : float
            时间步长 (s)
        u : ndarray
            流速 (m/s)
        h : ndarray
            水深 (m)

        Returns:
        --------
        state : dict
            当前状态
        """
        # 计算沉降
        settling = -self.vs * self.SS / h

        # 计算再悬浮
        resuspension = self.kr / h

        # 对流项 (使用上风格式)
        advection = np.zeros(self.n_cells)
        for i in range(1, self.n_cells - 1):
            if u[i] > 0:
                advection[i] = -u[i] * (self.SS[i] - self.SS[i-1]) / self.dx
            else:
                advection[i] = -u[i] * (self.SS[i+1] - self.SS[i]) / self.dx

        # 更新浓度
        self.SS += (advection + settling + resuspension) * dt
        self.SS = np.maximum(self.SS, 0.0)  # 非负约束

        return {
            'SS': self.SS.copy(),
            'settling_flux': settling,
            'resuspension_flux': resuspension
        }
```

#### 2. 编写单元测试

**文件:** `tests/test_suspended_solids.py`

```python
#!/usr/bin/env python3
"""
悬浮物求解器单元测试
"""

import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from solvers.suspended_solids import SuspendedSolidsSolver

def test_initialization():
    """测试初始化"""
    solver = SuspendedSolidsSolver(n_cells=100, dx=10.0)
    assert solver.n_cells == 100
    assert solver.dx == 10.0
    assert len(solver.SS) == 100
    print("✓ 初始化测试通过")

def test_settling():
    """测试沉降过程"""
    solver = SuspendedSolidsSolver(n_cells=100, dx=10.0, settling_velocity=0.001)

    # 初始均匀分布
    solver.SS = np.full(100, 10.0)  # 10 kg/m3

    # 静水沉降
    u = np.zeros(100)
    h = np.full(100, 2.0)

    # 运行 1 小时
    dt = 3600.0
    state = solver.step(dt, u, h)

    # 沉降后浓度应降低
    assert np.all(state['SS'] < 10.0)
    print(f"✓ 沉降测试通过: 初始 10.0 -> 最终 {state['SS'][0]:.2f} kg/m3")

def test_mass_conservation():
    """测试质量守恒"""
    solver = SuspendedSolidsSolver(n_cells=100, dx=10.0,
                                   settling_velocity=0.0,  # 无沉降
                                   resuspension_rate=0.0)  # 无再悬浮

    solver.SS = np.random.rand(100) * 5.0
    h = np.full(100, 2.0)

    initial_mass = np.sum(solver.SS * h * solver.dx)

    # 运行多步
    u = np.full(100, 0.3)
    dt = 100.0
    for _ in range(100):
        solver.step(dt, u, h)

    final_mass = np.sum(solver.SS * h * solver.dx)

    # 质量守恒误差应小于 5%
    error = abs(final_mass - initial_mass) / initial_mass * 100
    assert error < 5.0
    print(f"✓ 质量守恒测试通过: 误差 {error:.2f}%")

if __name__ == '__main__':
    print("=" * 70)
    print("悬浮物求解器测试")
    print("=" * 70)
    print()

    test_initialization()
    test_settling()
    test_mass_conservation()

    print()
    print("=" * 70)
    print("所有测试通过!")
    print("=" * 70)
```

#### 3. 添加集成示例

**文件:** `examples/sediment_transport.py`

```python
#!/usr/bin/env python3
"""
悬浮物输运示例
"""

import numpy as np
import matplotlib.pyplot as plt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from solvers.suspended_solids import SuspendedSolidsSolver

# ... 示例代码 ...
```

#### 4. 更新文档

在 `docs/` 中添加模块文档，说明:
- 物理模型
- 数学公式
- 参数说明
- 使用示例
- 参考文献

---

## 测试指南

### 测试分类

1. **单元测试**: 测试单个模块的功能
2. **集成测试**: 测试模块间的耦合
3. **验证测试**: 与解析解或商业软件对比
4. **性能测试**: 测试计算效率

### 编写测试的原则

1. **完整性**: 覆盖所有主要功能
2. **独立性**: 测试之间不相互依赖
3. **可重复性**: 使用固定随机种子
4. **清晰性**: 测试意图明确
5. **快速性**: 单个测试应在秒级完成

### 测试示例

```python
def test_physical_constraint():
    """测试物理约束 (如非负性)"""
    solver = MySolver(n_cells=100, dx=10.0)

    # 设置极端初始条件
    solver.state = np.array([-1.0, 0.0, 1.0, 100.0])

    # 运行求解器
    dt = 3600.0
    state = solver.step(dt, ...)

    # 验证物理约束
    assert np.all(state['variable'] >= 0), "物理变量应非负"
    assert np.all(state['variable'] < 1000), "物理变量应在合理范围"
```

### 运行测试

```bash
# 运行所有测试
python -m pytest tests/ -v

# 运行特定测试
python -m pytest tests/test_suspended_solids.py -v

# 运行覆盖率分析
python -m pytest tests/ --cov=solvers --cov-report=html

# 查看覆盖率报告
open htmlcov/index.html
```

---

## 代码风格

### Python 代码规范

遵循 [PEP 8](https://pep8.org/) 风格指南:

```python
# 好的代码风格
def compute_advection(u, c, dx):
    """
    计算对流项

    Parameters:
    -----------
    u : ndarray
        流速 (m/s)
    c : ndarray
        浓度
    dx : float
        网格间距 (m)

    Returns:
    --------
    advection : ndarray
        对流项
    """
    n = len(c)
    adv = np.zeros(n)

    for i in range(1, n - 1):
        if u[i] > 0:
            adv[i] = -u[i] * (c[i] - c[i-1]) / dx
        else:
            adv[i] = -u[i] * (c[i+1] - c[i]) / dx

    return adv
```

### 命名约定

- **类名**: 大驼峰命名 (e.g., `WaterTemperatureSolver`)
- **函数名**: 小写下划线 (e.g., `compute_sources`)
- **常量**: 大写下划线 (e.g., `MAX_ITERATIONS`)
- **私有方法**: 下划线前缀 (e.g., `_internal_method`)

### 文档字符串

使用 NumPy 风格的文档字符串:

```python
def my_function(param1, param2):
    """
    简短描述 (一句话)

    详细描述 (可选，多行)

    Parameters:
    -----------
    param1 : type
        参数1描述
    param2 : type
        参数2描述

    Returns:
    --------
    result : type
        返回值描述

    Examples:
    ---------
    >>> result = my_function(1, 2)
    >>> print(result)
    3

    References:
    -----------
    [1] Author et al. (2023), Title, Journal
    """
    pass
```

### 代码检查

```bash
# 使用 black 格式化
black solvers/ tests/ examples/

# 使用 flake8 检查
flake8 solvers/ tests/ examples/ --max-line-length=100

# 使用 pylint 深度检查
pylint solvers/
```

---

## 提交规范

### Commit 消息格式

使用约定式提交 (Conventional Commits):

```
<type>(<scope>): <subject>

<body>

<footer>
```

**类型 (type):**
- `feat`: 新功能
- `fix`: 错误修复
- `docs`: 文档更新
- `style`: 代码格式 (不影响功能)
- `refactor`: 重构 (不是新功能也不是修复)
- `perf`: 性能优化
- `test`: 测试相关
- `chore`: 构建/工具链

**示例:**

```
feat(solvers): 添加悬浮物传输模块

实现了悬浮物的对流-扩散-沉降过程，包括:
- 对流传输 (上风格式)
- 重力沉降 (沉降速度可配置)
- 底床再悬浮
- 单元测试和集成示例

相关 issue: #42
```

```
fix(ice_cover): 修复负厚度问题

在极端条件下冰盖厚度可能变为负值，
添加了非负性约束确保物理合理性。

Fixes #38
```

---

## Pull Request 流程

### 1. Fork 仓库

在 GitHub 上 Fork HydroClaude 仓库到你的账号。

### 2. 创建功能分支

```bash
git checkout -b feature/suspended-solids
```

### 3. 开发和测试

```bash
# 开发代码
vim solvers/suspended_solids.py

# 运行测试
python -m pytest tests/ -v

# 格式化代码
black solvers/ tests/
```

### 4. 提交代码

```bash
git add solvers/suspended_solids.py tests/test_suspended_solids.py
git commit -m "feat(solvers): 添加悬浮物传输模块"
```

### 5. 推送到 Fork

```bash
git push origin feature/suspended-solids
```

### 6. 创建 Pull Request

在 GitHub 上创建 Pull Request，包含:

- **标题**: 简洁描述改动
- **描述**: 详细说明
  - 改动内容
  - 相关 issue
  - 测试结果
  - 破坏性变更 (如有)
- **检查清单**:
  - [ ] 代码通过所有测试
  - [ ] 添加了单元测试
  - [ ] 更新了文档
  - [ ] 遵循代码风格
  - [ ] 无破坏性变更 (或已说明)

### PR 模板

```markdown
## 改动描述

简要描述这个 PR 的目的和改动内容。

## 相关 Issue

Fixes #42

## 改动类型

- [ ] 新功能
- [ ] 错误修复
- [ ] 文档更新
- [ ] 性能优化
- [ ] 其他 (请说明):

## 测试

描述你做了哪些测试:

- 单元测试: ✓ 通过
- 集成测试: ✓ 通过
- 手动测试: 运行了 `examples/sediment_transport.py`

## 检查清单

- [x] 代码通过所有测试
- [x] 添加了单元测试
- [x] 更新了文档
- [x] 遵循代码风格
- [x] 无破坏性变更

## 截图/输出 (如适用)

```
[运行结果截图或输出]
```

## 额外说明

其他需要说明的内容。
```

---

## 文档要求

### 代码文档

1. **所有公共 API 必须有文档字符串**
2. **复杂算法需要行内注释**
3. **物理公式用 LaTeX 表示**

示例:

```python
def compute_heat_flux(T_air, T_water, wind_speed):
    """
    计算表面热通量

    使用经验公式:
    Q = a * (T_air - T_water) * wind_speed^b

    Parameters:
    -----------
    T_air : float
        气温 (°C)
    T_water : float
        水温 (°C)
    wind_speed : float
        风速 (m/s)

    Returns:
    --------
    heat_flux : float
        热通量 (W/m2)

    Notes:
    ------
    公式来自 Smith et al. (2010):

    .. math::
        Q = 15.0 \cdot (T_{air} - T_{water}) \cdot U_{wind}^{0.5}

    References:
    -----------
    [1] Smith, J. et al. (2010). "Heat transfer in rivers",
        Journal of Hydrology, 123(4), 567-589.
    """
    a = 15.0
    b = 0.5
    return a * (T_air - T_water) * wind_speed ** b
```

### 用户文档

在 `docs/` 目录添加:

1. **README**: 模块概述
2. **理论**: 数学模型和物理方程
3. **API 参考**: 类和函数文档
4. **示例**: 使用教程
5. **验证**: 与已知解的对比

### 文档生成

使用 Sphinx 生成文档:

```bash
cd docs/
sphinx-apidoc -o source/ ../solvers/
make html
```

---

## 社区

### 提问和讨论

- **GitHub Issues**: 报告 bug 或请求功能
- **GitHub Discussions**: 技术讨论和问答
- **邮件列表**: hydroclaude@example.com

### 行为准则

- 尊重他人
- 建设性反馈
- 包容多样性
- 专注技术

---

## 许可证

贡献代码即表示您同意将代码以项目相同的许可证 (MIT License) 发布。

---

## 致谢

感谢所有为 HydroClaude 做出贡献的开发者！

---

**欢迎贡献！Let's make HydroClaude better together! 🚀**
