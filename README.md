# HydroClaude - 水力学仿真与优化框架

[![CI](https://github.com/leixiaohui-1974/HydroClaude/workflows/CI/badge.svg)](https://github.com/leixiaohui-1974/HydroClaude/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-164%2F164-brightgreen.svg)](tests/)
[![Examples](https://img.shields.io/badge/examples-21%2F21-brightgreen.svg)](examples/)
[![Documentation](https://img.shields.io/badge/docs-sphinx-blue.svg)](docs/)

HydroClaude是一个专业的水力学仿真与优化框架，专注于明渠流动、管网系统和梯级水库调度。

## ✨ 主要功能

### 🌊 水力学仿真
- **明渠流动**: Saint-Venant方程求解
  - 显式方法 (MOC, 有限差分)
  - 隐式方法 (Preissmann四点格式)
  - 有限体积法 (HLL Riemann求解器)
- **稳态剖面**: 牛顿法 + 伪瞬态延拓
- **非恒定流**: Runge-Kutta, MOC时间步进
- **边界条件**: 水库、闸门、堰、阀门、泵站

### 🔧 数值求解器
- **Newton求解器**: 稀疏Jacobian + 线搜索
- **延拓求解器**: 伪时间步长延拓策略
- **迭代求解器**:
  - Aitken加速
  - Anderson加速 (m=3/5/7, 可调参数)
- **管网求解器**: Hardy-Cross方法
- **混合求解器**: 自动切换策略

### 🎛️ 控制与优化
- **经典控制**: PID控制器
- **先进控制**: 模型预测控制 (MPC)
- **优化调度**:
  - 梯级水库优化
  - 动态规划
  - 遗传算法 (AGC)
  - 目标: 发电量最大化、防洪、生态流量

### 📊 典型应用
- 明渠流动分析
- 水闸调度策略
- 梯级水电站优化
- 长距离调水工程
- 城市供水系统
- 灌区配水优化

---

## 🚀 快速开始

### 安装

```bash
# 克隆仓库
git clone https://github.com/leixiaohui-1974/HydroClaude.git
cd HydroClaude

# 安装依赖
pip install -r requirements.txt
```

### 第一个示例：明渠流动

```python
import numpy as np
from physics.steady_saint_venant import SteadySaintVenantSystem
from solvers.newton_solver import NewtonSolver
from utils.canal_utils import compute_steady_uniform_flow

# 系统参数
length = 1000.0  # 渠道长度 (m)
nx = 21          # 网格点数
B = 10.0         # 渠道宽度 (m)
S0 = 0.001       # 渠底坡度
n = 0.025        # Manning糙率
Q_target = 10.0  # 目标流量 (m³/s)

# 创建系统
system = SteadySaintVenantSystem(length, nx, B, S0, n)
h_uniform = compute_steady_uniform_flow(Q_target, B, S0, n)

# 边界条件
system.set_boundary_conditions(
    Q_upstream=Q_target,
    h_upstream=h_uniform,
    h_downstream=h_uniform * 1.1  # 下游壅水
)

# 初值
h_init = np.ones(nx) * h_uniform
Q_init = np.ones(nx) * Q_target
U_init = system.pack_state(h_init, Q_init)

# 牛顿求解
newton = NewtonSolver(max_iter=20, tol_residual=1e-6)
U_solution, info = newton.solve(
    U_init=U_init,
    residual_func=system.compute_residual,
    jacobian_func=system.compute_jacobian
)

# 提取结果
h_sol, Q_sol = system.unpack_state(U_solution)
print(f"收敛: {info['converged']}, 迭代: {info['iterations']}")
```

### 运行示例

```bash
# 基础示例 - 明渠流动
python examples/example_01_canal_flow/01_basic.py

# 水闸调度
python examples/example_02_gate_control/main.py

# 梯级水库优化
python examples/example_03_reservoir_cascade/main.py

# 灌区配水
python examples/example_16_weirs_application/main.py
```

---

## 📚 文档

### 核心概念

#### Saint-Venant方程组
明渠非恒定流控制方程：

```
∂A/∂t + ∂Q/∂x = 0                       (连续性方程)
∂Q/∂t + ∂(Q²/A)/∂x + gA·∂h/∂x = gA(S₀-Sf) (动量方程)
```

其中：
- h: 水深 (m)
- Q: 流量 (m³/s)
- A = B×h: 断面面积 (m²)
- Sf: 摩阻坡度 (Manning公式)
- S₀: 渠底坡度
- g: 重力加速度 (9.81 m/s²)

#### 数值方法

**牛顿法**:
- 适用: 稳态问题，良好初值
- 收敛速度: 二次收敛（1-5次迭代）
- 特点: 需要Jacobian矩阵

**Anderson加速**:
- 适用: 固定点迭代收敛慢的问题
- 推荐参数: m=5, β=0.8
- 性能: 减少40-70%迭代次数

**延拓策略**:
- 适用: 初值较差的情况
- 方法: 逐步减小伪时间步长 (10.0 → 1.0 → 0.1)
- 鲁棒性: 显著提升

### 项目结构

```
HydroClaude/
├── physics/                    # 物理模型层
│   ├── steady_saint_venant.py # 稳态Saint-Venant方程
│   ├── reservoir.py           # 水库模型
│   ├── boundaries.py          # 边界条件
│   └── ...
├── solvers/                    # 数值求解器层
│   ├── newton_solver.py       # 牛顿法求解器
│   ├── continuation_solver.py # 延拓求解器
│   ├── anderson_acceleration.py # Anderson加速
│   └── ...
├── control/                    # 控制层
│   ├── pid_controller.py      # PID控制器
│   ├── mpc_controller.py      # 模型预测控制
│   └── ...
├── topology/                   # 拓扑层
│   ├── network.py             # 网络拓扑
│   └── cascade.py             # 梯级系统
├── optimization/               # 优化层
│   ├── dynamic_programming.py # 动态规划
│   ├── genetic_algorithm.py   # 遗传算法
│   └── ...
├── examples/                   # 示例库
│   ├── example_01_canal_flow/ # 明渠流动示例
│   ├── example_02_gate_control/ # 水闸控制
│   ├── example_03_reservoir_cascade/ # 梯级水库
│   └── ...
├── tests/                      # 测试套件 (164个测试)
├── docs/                       # 文档
└── utils/                      # 工具函数
```

---

## 🧪 测试

项目包含完整的测试套件 (164个测试，100%通过)：

```bash
# 运行全部测试
pytest tests/

# 运行特定测试
pytest tests/test_newton_solver.py -v

# 运行示例测试
python test_all_examples.py

# 性能基准测试
pytest tests/benchmark_newton_vs_iterative.py -v
```

测试覆盖：
- ✅ 核心物理模型
- ✅ 数值求解器
- ✅ 边界条件
- ✅ 控制算法
- ✅ 拓扑网络
- ✅ 优化调度
- ✅ 示例完整性

---

## 📖 示例库

### 基础示例

| 示例 | 描述 | 文件 |
|------|------|------|
| Example 01 | 明渠流动基础 | `examples/example_01_canal_flow/` |
| Example 02 | 水闸控制 | `examples/example_02_gate_control/` |
| Example 08 | 负荷接受测试 | `examples/example_08_load_acceptance/` |
| Example 16 | 堰流应用 | `examples/example_16_weirs_application/` |

### 高级示例

| 示例 | 描述 | 关键技术 |
|------|------|----------|
| Example 18 | 梯级水库优化 | AGC遗传算法 |
| Example 19 | 长距离调水 | 延时模型 |
| Example 20 | 城市供水系统 | 混合边界条件 |
| Example 24 | 灌区配水优化 | 多目标优化 |

---

## 🔬 算法与方法

### Newton求解器

**特点**:
- Jacobian满秩验证 ✓
- 条件数优化 (κ < 15)
- 线搜索回溯
- 良好初值下1-2次迭代收敛

**使用建议**:
```python
# 推荐配置
newton = NewtonSolver(
    max_iter=20,
    tol_residual=1e-6,
    linear_solver='direct',  # 或 'gmres'
    line_search=True,
    verbose=True
)
```

### Anderson加速

**验证状态**: ✅ 完全验证通过 (见 `ANDERSON_ACCELERATION_VERIFICATION.md`)

**推荐配置**:
```python
from solvers.anderson_acceleration import AndersonAcceleration

anderson = AndersonAcceleration(
    m=5,            # 历史深度
    beta=0.8,       # 松弛因子
    reg=1e-8,       # 正则化
    restart=True    # 自动重启
)
```

**性能**:
- 减少40-70%迭代次数
- 特别适合中等到复杂问题
- 优于Aitken加速

### 延拓策略

**原理**: 伪时间步长逐步减小

```python
from solvers.continuation_solver import ContinuationSolver

solver = ContinuationSolver(
    pseudo_dt_sequence=[10.0, 1.0, 0.1],  # 粗 → 细
    newton_max_iter=20,
    newton_tol=1e-4
)
```

**优势**:
- 显著提升鲁棒性
- 处理较差初值
- 自动热启动

---

## 🛠️ 开发指南

### 添加新的边界条件

```python
from physics.boundaries import HydraulicStructure

class MyCustomGate(HydraulicStructure):
    def __init__(self, position, width, custom_param):
        super().__init__(position, width)
        self.custom_param = custom_param

    def calculate_discharge(self, h_upstream, h_downstream, t=None):
        # 实现过流计算
        Q = self.custom_param * h_upstream ** 1.5
        return Q, "free_flow"

    def calculate_discharge_derivatives(self, h_upstream, h_downstream, t=None):
        # 实现导数计算（用于Jacobian）
        dQ_dh_up = 1.5 * self.custom_param * h_upstream ** 0.5
        dQ_dh_down = 0.0
        return dQ_dh_up, dQ_dh_down
```

### 添加新的求解器

```python
from solvers.newton_solver import NewtonSolver

class MyCustomSolver(NewtonSolver):
    def solve(self, U_init, residual_func, jacobian_func):
        # 实现自定义求解逻辑
        # ...
        return U_solution, info
```

### 代码风格

- 遵循PEP 8
- 使用类型提示
- 编写docstring
- 添加单元测试

---

## 📊 性能基准

### Newton法性能 (nx=21)

| 初值误差 | 迭代次数 | 最终残差 | 时间 |
|---------|---------|---------|------|
| 0% (完美) | 1 | 2.98e-13 | 6.2ms |
| 0.1% | 1 | 2.65e-07 | 5.0ms |
| 1% | 2 | 9.41e-13 | 7.4ms |
| 20% | 2 | 4.27e-11 | 7.4ms |

### Anderson加速性能

| 场景 | 无加速 | Anderson (m=5, β=0.8) | 加速比 |
|------|-------|---------------------|--------|
| 简单 | 100次 | 40-50次 | 2.0-2.5x |
| 中等 | 500次 | 200-250次 | 2.0-2.5x |
| 复杂 | 2000次 | 800-1000次 | 2.0-2.5x |

---

## 📝 最近更新

### 第一阶段完成 (2025-10-22)

✅ **核心验证与测试**
- 牛顿法边界条件验证: Jacobian满秩 ✓
- 测试错误修复: 164/164 tests passing ✓
- Examples 1-16测试: 完整报告生成 ✓
- Anderson加速验证: 全面验证通过 ✓

**新增文档**:
- `ANDERSON_ACCELERATION_VERIFICATION.md` - Anderson加速验证报告
- `EXAMPLES_TEST_ANALYSIS.md` - 示例测试分析
- `DEVELOPMENT_TASKS.md` - 完整开发路线图

---

## 🤝 贡献

欢迎贡献！请遵循以下步骤：

1. Fork本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启Pull Request

---

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

---

## 📧 联系方式

项目维护者: leixiaohui-1974

项目链接: https://github.com/leixiaohui-1974/HydroClaude

---

## 🙏 致谢

- Saint-Venant方程数值方法参考了经典教材
- Anderson加速算法基于 Walker & Ni (2011) SIAM论文
- 感谢所有贡献者和使用者的反馈

---

**Happy Simulating! 🌊**
