# HydroClaude 快速参考卡

## 1. 核心数字概览

```
总代码规模:     789 个 Python 文件，~350K+ 行代码
项目年龄:       2025-10-30 (持续开发中)
开发语言:       Python 3.8+
许可证:         MIT

核心指标:
  流量守恒误差:  < 0.0001%  ✓ 优秀
  数值稳定性:    无条件稳定 ✓ (隐式格式)
  收敛速度:      0-1 迭代   ✓ (典型)
  代码覆盖率:    > 80%      ✓
  测试通过率:    > 95%      ✓
```

## 2. 模块速查表

| 模块 | 文件 | 职责 | 关键类 |
|------|------|------|--------|
| **core/** | 10 | 基础设施 | HydraulicComponent, Config, Constants |
| **physics/** | 51 | 物理模型 | Canal, Reservoir, Pump, Turbine, Gate, etc. |
| **network/** | 15 | 拓扑网络 | Node, Reach, RiverNetwork, NetworkSolver |
| **solvers/** | 45 | 数值算法 | HydrostaticCanalSolver, GodunvFVMSolver, etc. |
| **control/** | 26 | 控制优化 | MPCController, PIDController, Governor, etc. |
| **utils/** | 29 | 工具库 | ResultValidator, PlotHelper, DataExporter |
| **modeling/** | 9 | 建模框架 | UniversalModeler, GridGenerator |
| **tests/** | 212 | 测试套件 | 653 个测试函数 |
| **examples/** | 242 | 示例应用 | 42 个完整示例脚本 |

## 3. 求解器选择速查

### 按应用场景

```python
# 稳态均匀流（最常用）
from solvers.fvm_steady_solver import FVMSteadySolver
# 或
from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver  # 推荐 ⭐

# 瞬变流（通用）
from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver  # 推荐 ⭐

# 高精度（光滑解）
from solvers.godunov_fvm_weno3 import GodunvFVMWENO3

# Dam Break（激波）
from solvers.godunov_fvm_solver import GodunvFVMSolver
solver = GodunvFVMSolver(order=2)  # 使用二阶

# 水锤（管道）
from solvers.water_hammer_moc_solver import WaterHammerMOCSolver

# 管网流量分配
from solvers.hardy_cross import HardyCrossSolver

# 网络耦合
from solvers.coupled_solver import CoupledNetworkSolver
```

### 按精度等级

```
高精度:  GodunvFVMWENO3 (3阶，需要Well-Balanced)
中精度:  GodunvFVMSolver (1-2阶，通用可靠) ⭐
稳定性:  HydrostaticCanalSolver (良平衡)
速度优先: FVMSteadySolver (稳态，极快)
```

## 4. 组件创建快速模板

### 明渠

```python
from physics.canal import Canal

canal = Canal(
    name="Main Channel",
    volume_min=1000,      # m³
    volume_max=50000,
    area=100,             # m²
    length=5000,          # m
    slope=0.001,          # 0.1%
    manning_n=0.025,      # Manning n
    width=10.0,           # m
    n_sections=51,        # 空间离散
    initial_depth=2.5,    # m
    initial_flow=50.0     # m³/s
)
```

### 泵站

```python
from physics.pump import Pump

pump = Pump(
    name="Main Pump",
    rated_flow=100.0,     # m³/s
    rated_head=50.0,      # m
    rated_speed=1500.0,   # rpm
    shutoff_head_ratio=1.2,
    max_efficiency=0.85
)
```

### 水库

```python
from physics.reservoir import Reservoir

reservoir = Reservoir(
    reservoir_id="Dam01",
    total_capacity=1e9,   # m³
    dead_storage=1e8,
    min_level=100.0,      # m
    normal_level=150.0,
    flood_limit_level=165.0,
    design_level=170.0,
    turbine_capacity=100.0,  # MW
    ecological_flow=50.0  # m³/s
)
```

### 控制器

```python
from control.mpc_controller import MPCController

controller = MPCController(
    prediction_horizon=10,
    control_horizon=3,
    weight_tracking=1.0,
    weight_control=0.1
)

# 使用控制器
state = {...}
Q_ref = 80.0
u_optimal = controller.optimize(state, Q_ref)
```

## 5. 常用工具函数

### 结果验证

```python
from utils.result_validator import ResultValidator

validator = ResultValidator("My Simulation")
result = validator.validate_flow_conservation(
    Q_computed=Q_array,
    Q_target=50.0,
    label="Main Flow"
)
print(result['grade'])  # 优秀/良好/可接受/不合格
```

### 绘图

```python
from utils.plot_helper import PlotHelper

plotter = PlotHelper()
plotter.plot_water_profile(
    x=x_array,
    h=h_array,
    z_bed=z_bed_array,
    title="Water Profile"
)
plotter.show()
```

### 数据导出

```python
from utils.data_exporter import DataExporter

exporter = DataExporter("output_dir")
exporter.export_to_csv("results.csv", data_dict)
exporter.export_to_hdf5("results.h5", data_dict)
exporter.generate_report("report.html", results)
```

### 水力学计算

```python
from utils.hydraulic_tools import HydraulicTools

tools = HydraulicTools()

# 均匀流水深
h_uniform = tools.compute_uniform_flow(
    Q=50.0,
    B=10.0,
    S0=0.001,
    n=0.025
)

# Froude 数
Fr = tools.compute_froude_number(Q, h, B)

# 临界深度
h_c = tools.compute_critical_depth(Q, B)
```

## 6. 网络建模

```python
from network.topology import RiverNetwork, Node, Reach

# 创建网络
network = RiverNetwork()

# 添加节点
network.add_node(Node('N1', 'boundary', elevation=100.0))
network.add_node(Node('N2', 'junction', elevation=95.0))
network.add_node(Node('N3', 'boundary', elevation=90.0))

# 添加河段
solver1 = GodunvFVMSolver(...)
solver2 = GodunvFVMSolver(...)

network.add_reach(Reach('R1', 'N1', 'N2', solver1))
network.add_reach(Reach('R2', 'N2', 'N3', solver2))

# 求解
network.solve(t_end=3600.0)
```

## 7. 配置驱动模式

```yaml
# config.yaml
reservoir:
  id: Dam01
  total_capacity: 1e9
  normal_level: 150.0

canal:
  id: Main_Channel
  length: 5000
  nx: 51
  width: 10.0
  slope: 0.001
  manning_n: 0.025

pump:
  id: Pump01
  rated_flow: 100.0
  rated_head: 50.0
```

```python
from modeling.universal_modeler import UniversalModeler

modeler = UniversalModeler("config.yaml")
results = modeler.run()
```

## 8. 测试运行

```bash
# 运行所有测试
pytest tests/

# 运行特定级别的测试
pytest -m p0              # P0 阻塞测试
pytest -m p1              # P1 关键测试
pytest -m unit            # 单元测试

# 运行特定模块测试
pytest tests/test_solvers/
pytest tests/test_network/

# 生成覆盖率报告
pytest --cov=. --cov-report=html tests/
```

## 9. CLI 命令速查

```bash
# 查看帮助
python hydroclaude_cli.py --help

# 运行模拟
python hydroclaude_cli.py run config.yaml

# 创建配置
python hydroclaude_cli.py config create --template basic_canal

# 验证示例
python hydroclaude_cli.py validate --report

# 运行测试
python hydroclaude_cli.py test --type unit

# 性能基准
python hydroclaude_cli.py benchmark

# 项目健康检查
python hydroclaude_cli.py health --report
```

## 10. 常见问题快速解答

### Q: 如何选择合适的求解器？
A: 查看第 3.4.3 节"求解器选择指南"。通常推荐 HydrostaticCanalSolver。

### Q: 流量守恒误差太大怎么办？
A: 
1. 减小时间步长（减小 CFL 数）
2. 增加空间网格数
3. 使用更高精度的求解器

### Q: 如何添加新的水工结构？
A:
1. 继承 `HydraulicComponent` 基类
2. 实现 `update_high_fidelity()` 和 `update_reduced_order()` 方法
3. 在 `physics/structures/` 中创建文件

### Q: 支持哪些边界条件？
A: Dirichlet (固定水深/流量), Neumann (梯度), Mixed (混合), Rating Curve (流量-水深关系)

### Q: 如何加速模拟？
A:
1. 减少网格数（更粗的离散）
2. 使用显式求解器
3. 增大时间步长（小心稳定性）
4. 使用降阶模型

## 11. 关键文件快速导航

```
库参考手册:        LIBRARY_REFERENCE.md
快速入门:          QUICKSTART_GUIDE.md
开发指南:          DEVELOPMENT_GUIDE.md
示例目录:          examples/EXAMPLES_CATALOG.md
最佳实践:          .cursorrules
完整结构分析:      CODEBASE_STRUCTURE_ANALYSIS.md (本文件)

水力学工具:        /utils/hydraulic_tools.py
结果验证:          /utils/result_validator.py
绘图模板:          /utils/plot_helper.py
数据导出:          /utils/data_exporter.py

示例脚本:          /examples/example_*.py
工程案例:          /examples/case_library/
测试:              /tests/, /unit_tests/
```

## 12. 常用导入集合

```python
# 物理组件
from physics.canal import Canal
from physics.reservoir import Reservoir
from physics.pump import Pump
from physics.turbine import Turbine
from physics.valve import Valve

# 求解器
from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver
from solvers.godunov_fvm_solver import GodunvFVMSolver
from solvers.godunov_fvm_weno3 import GodunvFVMWENO3

# 网络
from network.topology import RiverNetwork, Node, Reach

# 控制
from control.mpc_controller import MPCController
from control.pid_controller import PIDController

# 工具
from utils.result_validator import ResultValidator
from utils.data_exporter import DataExporter
from utils.plot_helper import PlotHelper
from utils.hydraulic_tools import HydraulicTools

# 配置
from modeling.universal_modeler import UniversalModeler
from modeling.grid_generator import GridGenerator
```

## 13. 性能优化建议

```
场景                      建议
================================================
单河段，快速仿真          FVMSteadySolver
单河段，高精度            GodunvFVMWENO3
多河段网络                CoupledNetworkSolver
实时优化控制              简化模型 + MPC
工程验证                  HydrostaticCanalSolver ⭐

网格细化建议:
  粗:   dx ≈ length/10    (快速)
  中:   dx ≈ length/50    (平衡) ⭐
  细:   dx ≈ length/200   (精确但慢)

时间步长建议:
  Explicit:  CFL ≤ 0.5    (安全)
  Implicit:  CFL ≤ 1.0    (可更大，需验证)
```

---

**最后更新**: 2025-10-30  
**快速参考卡版本**: 1.0

