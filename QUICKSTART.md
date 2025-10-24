# HydroClaude 快速入门指南

欢迎使用 HydroClaude！本指南将帮助您在 5 分钟内运行第一个水力模拟。

## 目录

- [环境要求](#环境要求)
- [5分钟快速开始](#5分钟快速开始)
- [基本概念](#基本概念)
- [常见用例](#常见用例)
- [使用CLI工具](#使用cli工具)
- [下一步](#下一步)

## 环境要求

确保您的系统已安装：

- Python 3.8 或更高版本
- NumPy
- Matplotlib
- PyYAML

```bash
# 安装依赖
pip install numpy matplotlib pyyaml scipy
```

## 5分钟快速开始

### 方法 1: 使用统一CLI工具（推荐）

```bash
# 1. 交互式创建配置文件
python hydroclaude_cli.py config create --interactive

# 2. 运行模拟
python hydroclaude_cli.py run config.yaml --plot

# 3. 验证所有示例
python hydroclaude_cli.py validate
```

### 方法 2: 运行现有示例

```bash
# 运行简单渠道流动模拟
python examples/basic_examples/simple_channel_flow.py

# 运行闸门控制示例
python examples/basic_examples/gate_control.py

# 运行泵站控制示例
python examples/basic_examples/pump_control.py
```

### 方法 3: 编写您的第一个模拟脚本

创建文件 `my_first_simulation.py`:

```python
import numpy as np
from core.solver import HydraulicSolver

# 1. 定义计算域
L = 1000.0  # 渠道长度 (m)
nx = 100    # 网格点数
x = np.linspace(0, L, nx)

# 2. 设置初始条件
h_init = np.ones(nx) * 2.0  # 初始水深 2m
u_init = np.zeros(nx)        # 初始速度 0 m/s
z_bed = np.zeros(nx)         # 平底渠道

# 3. 创建求解器
solver = HydraulicSolver(
    x=x,
    h=h_init,
    u=u_init,
    z_bed=z_bed,
    width=10.0,     # 渠道宽度 10m
    manning_n=0.025  # 曼宁系数
)

# 4. 设置边界条件：上游流量 20 m³/s，下游水深 2m
def boundary_conditions(t):
    Q_upstream = 20.0
    h_downstream = 2.0
    return Q_upstream, h_downstream

solver.set_boundary_conditions(boundary_conditions)

# 5. 运行模拟 (600秒，时间步长0.1秒)
t_final = 600.0
dt = 0.1
time, results = solver.solve(t_final, dt, save_interval=10)

# 6. 可视化结果
import matplotlib.pyplot as plt

plt.figure(figsize=(12, 5))

# 绘制水深分布
plt.subplot(1, 2, 1)
plt.plot(x, results['h'][-1])
plt.xlabel('距离 (m)')
plt.ylabel('水深 (m)')
plt.title('最终水深分布')
plt.grid(True)

# 绘制流速分布
plt.subplot(1, 2, 2)
plt.plot(x, results['u'][-1])
plt.xlabel('距离 (m)')
plt.ylabel('流速 (m/s)')
plt.title('最终流速分布')
plt.grid(True)

plt.tight_layout()
plt.savefig('my_first_simulation.png', dpi=150, bbox_inches='tight')
plt.show()

print("✓ 模拟完成！结果已保存到 my_first_simulation.png")
```

运行脚本：

```bash
python my_first_simulation.py
```

## 基本概念

### 1. 核心模块

HydroClaude 由以下核心模块组成：

```
core/
├── solver.py          # 水力求解器（圣维南方程组）
├── structures.py      # 水工结构物（闸门、堰、泵站）
└── controllers.py     # 控制器（PID、MPC等）

utils/
├── visualizer.py      # 高级可视化工具
├── config_generator.py # 配置文件生成器
└── data_validator.py  # 数据验证工具
```

### 2. 工作流程

```
配置/脚本 → 求解器 → 结构物 → 控制器 → 结果输出 → 可视化/分析
```

### 3. 关键参数说明

| 参数 | 符号 | 单位 | 说明 |
|------|------|------|------|
| 水深 | h | m | 垂直水深 |
| 流速 | u | m/s | 断面平均流速 |
| 底高程 | z_bed | m | 渠底高程 |
| 渠道宽度 | width | m | 矩形渠道宽度 |
| 曼宁系数 | manning_n | - | 糙率系数 (0.01-0.05) |
| 流量 | Q | m³/s | Q = u × h × width |
| 弗劳德数 | Fr | - | Fr = u / sqrt(g×h) |

### 4. 常见结构物

```python
from core.structures import SluiceGate, Weir, Pump

# 闸门：通过开度控制流量
gate = SluiceGate(position=500, opening=0.5)  # 50%开度

# 堰：固定溢流结构
weir = Weir(position=500, crest_height=1.0)

# 泵站：提升水位
pump = Pump(position=500, capacity=10.0, efficiency=0.85)
```

## 常见用例

### 用例 1: 渠道稳态流动模拟

适用场景：计算渠道的正常水深和流速分布。

```python
# 使用 examples/basic_examples/simple_channel_flow.py
python examples/basic_examples/simple_channel_flow.py
```

关键技术：
- 恒定边界条件
- 曼宁公式计算摩阻
- 稳态解收敛判断

### 用例 2: 闸门控制水位

适用场景：水库/渠道通过闸门维持目标水位。

```python
# 使用 examples/basic_examples/gate_control.py
python examples/basic_examples/gate_control.py
```

关键技术：
- PID控制器
- 闸门流量系数
- 反馈控制回路

### 用例 3: 泵站自动控制

适用场景：排水泵站根据水位自动启停。

```python
# 使用 examples/basic_examples/pump_control.py
python examples/basic_examples/pump_control.py
```

关键技术：
- 阈值控制（开/停水位）
- 泵站性能曲线
- 能耗计算

### 用例 4: 复杂系统集成

适用场景：多个结构物和控制器协同工作。

```python
# 使用 examples/advanced_examples/multi_structure_control.py
python examples/advanced_examples/multi_structure_control.py
```

关键技术：
- 多点控制
- 结构物相互作用
- 前馈+反馈控制

## 使用CLI工具

### 创建配置文件

```bash
# 交互式向导
python hydroclaude_cli.py config create --interactive

# 从模板创建
python hydroclaude_cli.py config create --template canal_with_gate

# 验证配置文件
python hydroclaude_cli.py config validate config.yaml
```

### 运行模拟

```bash
# 基本运行
python hydroclaude_cli.py run config.yaml

# 运行并绘图
python hydroclaude_cli.py run config.yaml --plot

# 运行并导出数据
python hydroclaude_cli.py run config.yaml --export results.csv

# 详细输出
python hydroclaude_cli.py run config.yaml --verbose
```

### 验证和测试

```bash
# 验证所有示例
python hydroclaude_cli.py validate

# 生成验证报告
python hydroclaude_cli.py validate --report

# 运行单元测试
python hydroclaude_cli.py test --type unit

# 运行集成测试
python hydroclaude_cli.py test --type integration
```

### 性能和健康检查

```bash
# 性能基准测试
python hydroclaude_cli.py benchmark

# 项目健康检查
python hydroclaude_cli.py health

# 生成健康报告
python hydroclaude_cli.py health --report
```

## 下一步

### 学习资源

1. **README.md** - 项目概览和功能介绍
2. **DEVELOPMENT_SUMMARY.md** - 详细开发文档和架构说明
3. **examples/** - 丰富的示例代码
   - `basic_examples/` - 基础示例
   - `advanced_examples/` - 高级示例
   - `real_world_cases/` - 实际工程案例
4. **tests/** - 单元测试和集成测试（最佳学习材料）

### 深入主题

#### 1. 自定义控制器

```python
from core.controllers import BaseController

class MyController(BaseController):
    def compute_control(self, current_state, target_state, dt):
        # 实现您的控制算法
        error = target_state - current_state
        control_output = self.my_algorithm(error)
        return control_output
```

参考：`examples/advanced_examples/custom_controller.py`

#### 2. 高级可视化

```python
from utils.visualizer import HydroVisualizer

viz = HydroVisualizer(style='scientific')
viz.create_dashboard(
    time=time,
    water_level=h_history,
    flow_rate=Q_history,
    control_input=u_control_history
)
```

参考：`examples/visualization_examples/`

#### 3. 数据验证和质量保障

```python
from utils.data_validator import DataValidator

validator = DataValidator()
report = validator.validate_simulation_results(results)
validator.generate_html_report(report, 'validation_report.html')
```

参考：`examples/data_validation_examples/`

#### 4. 性能优化

- 使用向量化操作（NumPy）
- 调整网格分辨率（CFL条件）
- 选择合适的时间步长
- 考虑并行计算（未来功能）

参考：`docs/performance_optimization.md`

### 常见问题

#### Q1: 模拟不稳定/发散？

**解决方案**：
1. 减小时间步长 `dt`
2. 检查CFL条件：`dt < dx / (|u| + sqrt(g*h))`
3. 使用数据验证工具检查初始条件

```python
from utils.data_validator import DataValidator
validator = DataValidator()
validator.check_courant_condition(u, h, dx, dt)
```

#### Q2: 控制器不工作？

**解决方案**：
1. 检查PID参数（Kp, Ki, Kd）
2. 验证测量点位置
3. 查看控制输出是否饱和
4. 使用可视化工具分析控制性能

```python
viz.plot_control_performance(time, actual, target, control)
```

#### Q3: 如何选择网格分辨率？

**经验法则**：
- 简单渠道：`nx = 50-100`
- 有结构物：在结构物附近加密
- 精细模拟：`nx > 200`
- 权衡精度和速度

#### Q4: 如何处理复杂边界条件？

```python
def time_varying_bc(t):
    # 时变边界条件
    Q_upstream = 20.0 + 5.0 * np.sin(2*np.pi*t/3600)  # 周期变化
    h_downstream = 2.0
    return Q_upstream, h_downstream

solver.set_boundary_conditions(time_varying_bc)
```

### 获取帮助

- **GitHub Issues**: 报告bug或请求功能
- **示例代码**: 查看 `examples/` 目录
- **测试代码**: `tests/` 目录包含大量使用示例
- **CLI帮助**: `python hydroclaude_cli.py --help`

## 最佳实践

### 1. 项目组织

```
my_project/
├── configs/          # 配置文件
├── scripts/          # 模拟脚本
├── results/          # 模拟结果
│   ├── data/        # 数据文件
│   └── plots/       # 图表
└── reports/          # 分析报告
```

### 2. 代码风格

```python
# ✓ 好的实践
solver = HydraulicSolver(x=x, h=h_init, u=u_init, z_bed=z_bed)
time, results = solver.solve(t_final=600, dt=0.1)

# ✗ 避免
solver = HydraulicSolver(x, h_init, u_init, z_bed)  # 参数不明确
```

### 3. 模拟流程

1. **前处理**：验证输入数据
2. **模拟**：使用合适的时间步长
3. **后处理**：验证结果物理合理性
4. **可视化**：使用专业工具展示结果
5. **文档化**：记录关键参数和假设

### 4. 版本控制

```bash
# 保存配置
git add configs/

# 不要提交大数据文件
echo "results/*.csv" >> .gitignore
echo "results/*.npy" >> .gitignore
```

## 示例：完整工作流程

```bash
# 1. 创建项目目录
mkdir my_canal_project && cd my_canal_project

# 2. 创建配置
python ../hydroclaude_cli.py config create --interactive

# 3. 验证配置
python ../hydroclaude_cli.py config validate my_config.yaml

# 4. 运行模拟
python ../hydroclaude_cli.py run my_config.yaml --plot --export results.csv

# 5. 验证结果
python -c "
from utils.data_validator import DataValidator
import numpy as np

data = np.loadtxt('results.csv', delimiter=',', skiprows=1)
validator = DataValidator()
# 进行验证...
"

# 6. 生成报告
python ../hydroclaude_cli.py health --report
```

---

**恭喜！您已经掌握了 HydroClaude 的基础使用。** 🎉

现在您可以：
- ✓ 运行基本模拟
- ✓ 使用CLI工具
- ✓ 添加结构物和控制器
- ✓ 可视化和验证结果

继续探索 `examples/` 目录，尝试更高级的功能！
