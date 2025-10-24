# 控制系统API参考手册

本文档提供HydroClaude控制系统模块的完整API参考。

**版本**: v1.3
**更新日期**: 2025-10-24
**作者**: HydroClaude Team

---

## 目录

1. [河道断面模块 (physics.cross_section)](#河道断面模块)
2. [IDZ模型 (control.idz_model)](#idz模型)
3. [在线辨识 (control.online_identification)](#在线辨识)
4. [多断面辨识 (control.multi_section_identification)](#多断面辨识)
5. [性能基准测试 (tools.performance_benchmark)](#性能基准测试)
6. [完整示例](#完整示例)

---

## 河道断面模块

### 模块: `physics.cross_section`

提供多种河道断面类型的几何计算功能。

#### 1. `CrossSectionGeometry` - 断面几何数据类

```python
@dataclass
class CrossSectionGeometry:
    """断面几何计算结果"""
    area: float          # 过流面积 (m²)
    wetted_perimeter: float  # 湿周 (m)
    hydraulic_radius: float  # 水力半径 (m)
    top_width: float     # 水面宽度 (m)
```

#### 2. `RectangularSection` - 矩形断面

```python
class RectangularSection:
    def __init__(self, name: str, width: float):
        """
        初始化矩形断面

        参数:
            name: 断面名称
            width: 渠道宽度 (m)
        """

    def compute_geometry(self, depth: float) -> CrossSectionGeometry:
        """
        计算给定水深下的几何参数

        参数:
            depth: 水深 (m)

        返回:
            CrossSectionGeometry: 几何参数
        """
```

**示例**:
```python
from physics.cross_section import RectangularSection

section = RectangularSection("Main Channel", width=10.0)
geom = section.compute_geometry(depth=3.0)

print(f"面积: {geom.area:.2f} m²")
print(f"湿周: {geom.wetted_perimeter:.2f} m")
print(f"水力半径: {geom.hydraulic_radius:.2f} m")
```

#### 3. `TrapezoidalSection` - 梯形断面

```python
class TrapezoidalSection:
    def __init__(self, name: str, bottom_width: float, side_slope: float):
        """
        初始化梯形断面

        参数:
            name: 断面名称
            bottom_width: 底宽 (m)
            side_slope: 边坡系数（水平:垂直）
                       例如：1.5 表示 1.5:1 边坡
        """

    def compute_geometry(self, depth: float) -> CrossSectionGeometry:
        """计算给定水深下的几何参数"""
```

**示例**:
```python
from physics.cross_section import TrapezoidalSection

section = TrapezoidalSection(
    name="Trapezoidal Canal",
    bottom_width=8.0,
    side_slope=1.5  # 1.5:1 边坡
)

geom = section.compute_geometry(depth=2.5)
# 面积 = 8*2.5 + 1.5*2.5² = 29.375 m²
```

#### 4. `NaturalSection` - 自然河道断面

基于实测点数据的不规则断面。

```python
class NaturalSection:
    def __init__(self, name: str, stations: List[float],
                 elevations: List[float]):
        """
        初始化自然河道断面

        参数:
            name: 断面名称
            stations: 测点桩号列表 (m)
            elevations: 测点高程列表 (m)

        注意:
            - stations和elevations长度必须相同
            - stations必须递增
        """

    def compute_geometry(self, water_level: float) -> CrossSectionGeometry:
        """
        计算给定水位下的几何参数

        参数:
            water_level: 水位高程 (m)

        返回:
            CrossSectionGeometry: 几何参数
        """
```

**示例**:
```python
from physics.cross_section import NaturalSection

# 实测断面数据
stations = [0, 5, 10, 15, 20]      # 桩号 (m)
elevations = [10, 5, 3, 5, 10]     # 高程 (m)

natural = NaturalSection("River Section", stations, elevations)
geom = natural.compute_geometry(water_level=8.0)

print(f"过流面积: {geom.area:.2f} m²")
print(f"湿周: {geom.wetted_perimeter:.2f} m")
```

#### 5. `CompoundSection` - 复合断面

由主槽和滩地组成的复合断面。

```python
class CompoundSection:
    def __init__(self, name: str,
                 main_channel: CrossSection,
                 left_floodplain: Optional[CrossSection] = None,
                 right_floodplain: Optional[CrossSection] = None,
                 main_invert: float = 0.0,
                 left_invert: float = 0.0,
                 right_invert: float = 0.0):
        """
        初始化复合断面

        参数:
            name: 断面名称
            main_channel: 主槽断面
            left_floodplain: 左滩地断面（可选）
            right_floodplain: 右滩地断面（可选）
            main_invert: 主槽底高程 (m)
            left_invert: 左滩地底高程 (m)
            right_invert: 右滩地底高程 (m)
        """
```

**示例**:
```python
from physics.cross_section import (
    CompoundSection, TrapezoidalSection, RectangularSection
)

# 主槽：梯形断面
main = TrapezoidalSection("Main", bottom_width=15.0, side_slope=2.0)

# 滩地：矩形断面
left_fp = RectangularSection("Left FP", width=30.0)
right_fp = RectangularSection("Right FP", width=30.0)

# 复合断面
compound = CompoundSection(
    name="River with Floodplain",
    main_channel=main,
    left_floodplain=left_fp,
    right_floodplain=right_fp,
    main_invert=0.0,
    left_invert=3.0,   # 滩地高出主槽3m
    right_invert=3.0
)

# 低水位（仅主槽）
geom_low = compound.compute_geometry(depth=2.0)

# 高水位（主槽+滩地）
geom_high = compound.compute_geometry(depth=5.0)
```

---

## IDZ模型

### 模块: `control.idz_model`

Integrator-Delay-Zero (IDZ) 模型是专为渠道系统设计的低阶控制模型。

#### 传递函数

```
G(s) = K * (1 + τ_z * s) / [s * (1 + τ_d * s)] * exp(-θ * s)
```

其中：
- `K`: 系统增益
- `τ_z`: 零点时间常数 (s)
- `τ_d`: 延迟时间常数 (s)
- `θ`: 纯滞后 (s)

### 1. `IDZParameters` - IDZ参数类

```python
@dataclass
class IDZParameters:
    """IDZ模型参数"""
    K: float       # 系统增益
    tau_z: float   # 零点时间常数 (s)
    tau_d: float   # 延迟时间常数 (s)
    theta: float   # 纯滞后 (s)

    def validate(self):
        """验证参数合理性"""

    @staticmethod
    def from_hydraulics(length: float, width: float,
                       bed_slope: float, manning: float,
                       normal_depth: float) -> 'IDZParameters':
        """
        从水力学参数计算IDZ参数

        参数:
            length: 渠段长度 (m)
            width: 渠道宽度 (m)
            bed_slope: 底坡
            manning: Manning糙率系数
            normal_depth: 正常水深 (m)

        返回:
            IDZParameters: 计算得到的IDZ参数
        """
```

**示例**:
```python
from control.idz_model import IDZParameters

# 方法1: 直接指定参数
params1 = IDZParameters(K=100.0, tau_z=50.0, tau_d=100.0, theta=20.0)

# 方法2: 从水力学参数计算
params2 = IDZParameters.from_hydraulics(
    length=1000.0,      # 1km
    width=10.0,         # 10m
    bed_slope=0.0001,
    manning=0.025,
    normal_depth=2.0
)

print(f"增益 K = {params2.K:.2f}")
print(f"零点时间常数 τ_z = {params2.tau_z:.2f} s")
print(f"延迟时间常数 τ_d = {params2.tau_d:.2f} s")
print(f"纯滞后 θ = {params2.theta:.2f} s")
```

### 2. `IDZModel` - IDZ模型类

```python
class IDZModel:
    def __init__(self, params: IDZParameters, dt: float):
        """
        初始化IDZ模型

        参数:
            params: IDZ参数
            dt: 采样时间 (s)
        """

    def step(self, u: float) -> float:
        """
        仿真一步

        参数:
            u: 控制输入（流量差异，m³/s）

        返回:
            y: 输出（水深变化，m）
        """

    def predict(self, u_sequence: np.ndarray) -> np.ndarray:
        """
        多步预测

        参数:
            u_sequence: 输入序列 [u(k), u(k+1), ..., u(k+N-1)]

        返回:
            y_sequence: 输出序列 [y(k), y(k+1), ..., y(k+N-1)]
        """

    def reset(self):
        """重置模型状态"""
```

**示例**:
```python
from control.idz_model import IDZParameters, IDZModel
import numpy as np

# 创建IDZ模型
params = IDZParameters(K=100.0, tau_z=50.0, tau_d=100.0, theta=20.0)
model = IDZModel(params, dt=10.0)

# 单步仿真
u = 0.1  # 流量差异 0.1 m³/s
y = model.step(u)
print(f"水深变化: {y:.4f} m")

# 多步预测
horizon = 20
u_sequence = np.ones(horizon) * 0.1
y_pred = model.predict(u_sequence)

import matplotlib.pyplot as plt
plt.plot(y_pred)
plt.xlabel('Time Step')
plt.ylabel('Depth Change (m)')
plt.title('IDZ Model Prediction')
plt.show()
```

### 3. `SeriesIDZModel` - 串联IDZ模型

```python
class SeriesIDZModel:
    def __init__(self, pool_params: List[IDZParameters], dt: float):
        """
        初始化串联IDZ模型

        参数:
            pool_params: 各池段的IDZ参数列表
            dt: 采样时间 (s)
        """

    def step(self, u: np.ndarray) -> np.ndarray:
        """
        仿真一步

        参数:
            u: 输入向量 [Q0, Q1, ..., Qn]
               n个池段需要n+1个流量输入

        返回:
            y: 输出向量 [h1, h2, ..., hn]
               各池段的水深
        """
```

**示例**:
```python
from control.idz_model import IDZParameters, SeriesIDZModel
import numpy as np

# 创建3个池段
pool_params = [
    IDZParameters(K=100.0, tau_z=50.0, tau_d=100.0, theta=20.0),
    IDZParameters(K=120.0, tau_z=55.0, tau_d=110.0, theta=22.0),
    IDZParameters(K=110.0, tau_z=52.0, tau_d=105.0, theta=21.0)
]

model = SeriesIDZModel(pool_params, dt=10.0)

# 3个池段需要4个流量输入
u = np.array([10.0, 9.5, 9.0, 8.5])  # Q0, Q1, Q2, Q3

# 仿真
y = model.step(u)
print(f"池段1水深: {y[0]:.4f} m")
print(f"池段2水深: {y[1]:.4f} m")
print(f"池段3水深: {y[2]:.4f} m")
```

---

## 在线辨识

### 模块: `control.online_identification`

提供多种在线参数辨识算法。

### 1. `RecursiveLeastSquares` - 递归最小二乘

```python
class RecursiveLeastSquares:
    def __init__(self, n_params: int, config: RLSConfig = None):
        """
        初始化RLS辨识器

        参数:
            n_params: 参数个数
            config: RLS配置（可选）
        """

    def update(self, phi: np.ndarray, y: float) -> np.ndarray:
        """
        RLS更新

        参数:
            phi: 回归向量 [phi1, phi2, ..., phi_n]
            y: 观测值

        返回:
            theta: 更新后的参数估计
        """
```

**示例**:
```python
from control.online_identification import RecursiveLeastSquares
import numpy as np

# 初始化RLS（估计2个参数）
rls = RecursiveLeastSquares(n_params=2)

# 在线更新
for i in range(100):
    x = np.random.randn()
    phi = np.array([1.0, x])  # [1, x]
    y = 3.0 + 2.0 * x + 0.1 * np.random.randn()  # y = 3 + 2x + noise

    theta = rls.update(phi, y)

print(f"估计参数: {theta}")  # 应该接近 [3.0, 2.0]
```

### 2. `IDZIdentifier` - IDZ参数辨识

```python
class IDZIdentifier:
    def __init__(self, dt: float):
        """
        初始化IDZ辨识器

        参数:
            dt: 采样时间 (s)
        """

    def update(self, u: float, y: float) -> Optional[IDZParameters]:
        """
        更新辨识

        参数:
            u: 控制输入
            y: 系统输出

        返回:
            params: 辨识得到的IDZ参数（可能为None）
        """

    def get_idz_parameters(self) -> Optional[IDZParameters]:
        """获取当前IDZ参数估计"""
```

**示例**:
```python
from control.online_identification import IDZIdentifier

identifier = IDZIdentifier(dt=10.0)

# 在线辨识
for u, y in data_stream:
    params = identifier.update(u, y)

    if params is not None:
        print(f"辨识成功: K={params.K:.2f}")
```

#### ⚠️ 重要提示：数据类型要求（2025-10-24更新）

**IDZIdentifier需要输入变化量而非绝对值！**

IDZ模型表示的是**变化量之间的关系**：
```
Δy(s) = G(s) * Δu(s)
```

其中：
- `Δu`: 控制输入的**变化量**（相对于标称工作点）
- `Δy`: 系统输出的**变化量**（相对于标称工作点）

**错误用法**❌:
```python
identifier = IDZIdentifier(dt=10.0)

# 错误：直接传入绝对值
u_absolute = 20.0  # 绝对流量 (m³/s)
y_absolute = 2.5   # 绝对水深 (m)
params = identifier.update(u_absolute, y_absolute)  # ❌ 错误！
```

**正确用法**✅:
```python
identifier = IDZIdentifier(dt=10.0)

# 定义工作点（标称值）
u_nominal = 20.0  # 标称流量 (m³/s)
y_nominal = 2.0   # 标称水深 (m)

# 正确：传入变化量
u_absolute = 22.0  # 当前流量
y_absolute = 2.1   # 当前水深

u_deviation = u_absolute - u_nominal  # Δu = +2.0 m³/s
y_deviation = y_absolute - y_nominal  # Δy = +0.1 m

params = identifier.update(u_deviation, y_deviation)  # ✅ 正确！
```

**完整示例（集成到闭环系统）**:
```python
from control.online_identification import IDZIdentifier
from control.idz_model import IDZModel

class AdaptiveIDZSystem:
    def __init__(self, canal, dt=10.0):
        self.canal = canal
        self.dt = dt

        # 记录工作点（标称值）
        self.depth_nominal = canal.initial_depth
        self.flow_nominal = 20.0  # 标称流量

        # 初始化辨识器
        self.identifier = IDZIdentifier(dt=dt)

    def update_identification(self, u_absolute, y_absolute):
        """
        在线辨识更新

        参数:
            u_absolute: 绝对流量 (m³/s)
            y_absolute: 绝对水深 (m)
        """
        # 转换为变化量
        u_deviation = u_absolute - self.flow_nominal
        y_deviation = y_absolute - self.depth_nominal

        # 在线辨识（传入变化量）
        params = self.identifier.update(u_deviation, y_deviation)

        if params is not None:
            print(f"辨识更新: K={params.K:.1f}, τ_d={params.tau_d:.1f}s")

        return params
```

**参考**:
- 完整示例: `examples/advanced_examples/idz_saint_venant_integration.py`
- 修复报告: `docs/IDZ_Saint_Venant_Fix_Report.md`

---

### 3. `GateIdentifier` - 闸门特性辨识

```python
class GateIdentifier:
    def __init__(self, gate_width: float):
        """
        初始化闸门辨识器

        参数:
            gate_width: 闸门宽度 (m)
        """

    def update(self, opening: float, head: float, flow: float):
        """
        更新放流系数辨识

        参数:
            opening: 闸门开度 (m)
            head: 上下游水头差 (m)
            flow: 实测流量 (m³/s)
        """

    @property
    def C_d(self) -> float:
        """当前放流系数估计"""
```

**闸门流量公式**:
```
Q = C_d * b * a * sqrt(2 * g * h)
```

其中：
- `C_d`: 放流系数（通常0.6左右）
- `b`: 闸门宽度
- `a`: 闸门开度
- `h`: 上下游水头差

**示例**:
```python
from control.online_identification import GateIdentifier

identifier = GateIdentifier(gate_width=5.0)

# 在线辨识
for opening, head, flow in measurements:
    identifier.update(opening, head, flow)

print(f"辨识的放流系数 C_d = {identifier.C_d:.3f}")
```

### 4. `PumpIdentifier` - 水泵特性辨识

```python
class PumpIdentifier:
    def __init__(self):
        """初始化水泵辨识器"""

    def update(self, flow: float, head: float):
        """
        更新水泵特性曲线辨识

        参数:
            flow: 流量 (m³/s)
            head: 扬程 (m)
        """

    @property
    def H0(self) -> float:
        """零流量扬程"""

    @property
    def K(self) -> float:
        """特性曲线系数"""
```

**水泵特性曲线**:
```
H = H0 - K * Q²
```

**示例**:
```python
from control.online_identification import PumpIdentifier

identifier = PumpIdentifier()

# 在线辨识
for Q, H in measurements:
    identifier.update(Q, H)

print(f"H0 = {identifier.H0:.2f} m")
print(f"K = {identifier.K:.5f}")
```

---

## 多断面辨识

### 模块: `control.multi_section_identification`

处理多断面渠道的IDZ参数辨识。

### 1. `SectionLocation` - 断面位置

```python
@dataclass
class SectionLocation:
    """断面位置信息"""
    section: CrossSection  # 断面对象
    station: float         # 桩号 (m)
```

### 2. `EquivalentSectionMethod` - 等效断面法

```python
class EquivalentSectionMethod:
    def __init__(self, section_locations: List[SectionLocation],
                 normal_depth: float):
        """
        初始化等效断面法

        参数:
            section_locations: 断面位置列表
            normal_depth: 正常水深 (m)
        """

    def compute_equivalent_geometry(self, depth: float) -> Dict[str, float]:
        """
        计算等效几何参数

        参数:
            depth: 水深 (m)

        返回:
            geometry: 等效几何参数字典
        """

    def compute_idz_parameters(self, normal_flow: float,
                              manning_n: float,
                              bed_slope: float) -> IDZParameters:
        """
        计算等效IDZ参数

        参数:
            normal_flow: 正常流量 (m³/s)
            manning_n: Manning糙率
            bed_slope: 底坡

        返回:
            params: 等效IDZ参数
        """
```

**示例**:
```python
from physics.cross_section import TrapezoidalSection
from control.multi_section_identification import (
    SectionLocation, EquivalentSectionMethod
)

# 创建多个断面
sections = [
    TrapezoidalSection("S1", bottom_width=8.0, side_slope=1.5),
    TrapezoidalSection("S2", bottom_width=10.0, side_slope=1.5),
    TrapezoidalSection("S3", bottom_width=12.0, side_slope=1.5)
]

locations = [
    SectionLocation(section=sections[0], station=0.0),
    SectionLocation(section=sections[1], station=1000.0),
    SectionLocation(section=sections[2], station=2000.0)
]

# 等效断面法
method = EquivalentSectionMethod(locations, normal_depth=2.5)

# 计算等效IDZ参数
params = method.compute_idz_parameters(
    normal_flow=25.0,
    manning_n=0.025,
    bed_slope=0.0001
)

print(f"等效IDZ参数: K={params.K:.2f}, τ_d={params.tau_d:.2f}")
```

### 3. `SectionClusteringMethod` - 断面聚类法

```python
class SectionClusteringMethod:
    def __init__(self, section_locations: List[SectionLocation],
                 normal_depth: float, n_clusters: int):
        """
        初始化断面聚类法

        参数:
            section_locations: 断面位置列表
            normal_depth: 正常水深 (m)
            n_clusters: 聚类数量
        """

    def get_representative_sections(self) -> List[Tuple[float, float, SectionLocation]]:
        """
        获取代表断面

        返回:
            representatives: [(start, end, section)]列表
        """
```

**示例**:
```python
from control.multi_section_identification import SectionClusteringMethod

# 10个断面，聚为3类
method = SectionClusteringMethod(
    section_locations=locations,
    normal_depth=2.5,
    n_clusters=3
)

representatives = method.get_representative_sections()

for start, end, section_loc in representatives:
    print(f"段 {start:.0f}m - {end:.0f}m: 使用断面 {section_loc.section.name}")
```

---

## 性能基准测试

### 模块: `tools.performance_benchmark`

完整的控制器性能评估框架。

### 1. `PerformanceMetrics` - 性能指标

```python
@dataclass
class PerformanceMetrics:
    """性能指标"""
    name: str

    # 跟踪误差
    mae: float           # 平均绝对误差
    rmse: float          # 均方根误差
    max_error: float     # 最大误差

    # 动态性能
    settling_time: float # 调节时间（2%带）
    overshoot: float     # 超调量（%）
    rise_time: float     # 上升时间（10%-90%）

    # 能耗和平滑度
    total_energy: float  # 总能耗
    control_variation: float  # 控制输入变化率

    # 计算时间
    computation_time: float  # 平均计算时间（毫秒）
```

### 2. `BenchmarkScenario` - 测试场景

#### 阶跃响应

```python
class StepResponseScenario(BenchmarkScenario):
    def __init__(self, duration: float = 600.0, dt: float = 1.0,
                 initial_value: float = 2.0, final_value: float = 3.0,
                 step_time: float = 60.0):
        """
        阶跃响应场景

        参数:
            duration: 持续时间 (s)
            dt: 采样时间 (s)
            initial_value: 初始值
            final_value: 最终值
            step_time: 阶跃时刻 (s)
        """
```

#### 斜坡跟踪

```python
class RampTrackingScenario(BenchmarkScenario):
    def __init__(self, duration: float = 600.0, dt: float = 1.0,
                 initial_value: float = 2.0, ramp_rate: float = 0.01,
                 ramp_start: float = 60.0):
        """
        斜坡跟踪场景

        参数:
            duration: 持续时间 (s)
            dt: 采样时间 (s)
            initial_value: 初始值
            ramp_rate: 斜坡速率 (单位/s)
            ramp_start: 斜坡开始时刻 (s)
        """
```

#### 正弦跟踪

```python
class SinusoidalTrackingScenario(BenchmarkScenario):
    def __init__(self, duration: float = 600.0, dt: float = 1.0,
                 mean_value: float = 2.5, amplitude: float = 0.5,
                 frequency: float = 0.01):
        """
        正弦跟踪场景

        参数:
            duration: 持续时间 (s)
            dt: 采样时间 (s)
            mean_value: 平均值
            amplitude: 振幅
            frequency: 频率 (Hz)
        """
```

#### 扰动抑制

```python
class DisturbanceRejectionScenario(BenchmarkScenario):
    def __init__(self, duration: float = 600.0, dt: float = 1.0,
                 setpoint: float = 2.5, disturbance_magnitude: float = 0.3,
                 disturbance_time: float = 200.0):
        """
        扰动抑制场景

        参数:
            duration: 持续时间 (s)
            dt: 采样时间 (s)
            setpoint: 设定值
            disturbance_magnitude: 扰动幅度
            disturbance_time: 扰动时刻 (s)
        """
```

### 3. `ControllerInterface` - 控制器接口

```python
class ControllerInterface(ABC):
    """控制器接口"""

    @abstractmethod
    def reset(self):
        """重置控制器状态"""

    @abstractmethod
    def compute_control(self, reference: float, output: float,
                       disturbance: float = 0.0) -> float:
        """
        计算控制输入

        参数:
            reference: 参考值
            output: 当前输出
            disturbance: 扰动（可选）

        返回:
            control: 控制输入
        """

    @abstractmethod
    def get_name(self) -> str:
        """获取控制器名称"""
```

### 4. `BenchmarkRunner` - 基准测试运行器

```python
class BenchmarkRunner:
    def __init__(self, system_model: Callable[[float, float], float],
                 dt: float = 1.0):
        """
        初始化基准测试运行器

        参数:
            system_model: 系统模型函数 f(u, disturbance) -> y
            dt: 采样时间 (s)
        """

    def run_benchmark(self, controller: ControllerInterface,
                     scenario: BenchmarkScenario,
                     verbose: bool = True) -> PerformanceMetrics:
        """
        运行单个基准测试

        参数:
            controller: 控制器
            scenario: 测试场景
            verbose: 是否显示进度

        返回:
            metrics: 性能指标
        """

    def run_comparison(self, controllers: List[ControllerInterface],
                      scenarios: List[BenchmarkScenario],
                      save_results: bool = True,
                      output_dir: str = "benchmark_results") -> Dict[str, List[PerformanceMetrics]]:
        """
        运行多个控制器和场景的对比测试

        参数:
            controllers: 控制器列表
            scenarios: 测试场景列表
            save_results: 是否保存结果
            output_dir: 输出目录

        返回:
            results: 结果字典 {场景名: [性能指标列表]}
        """
```

---

## 完整示例

### 示例1: 从水力学参数到MPC控制

```python
from physics.cross_section import TrapezoidalSection
from control.idz_model import IDZParameters, IDZModel
import numpy as np

# 1. 定义渠道断面
section = TrapezoidalSection("Canal", bottom_width=10.0, side_slope=1.5)

# 2. 计算几何参数
geom = section.compute_geometry(depth=2.5)
print(f"过流面积: {geom.area:.2f} m²")

# 3. 计算IDZ参数
params = IDZParameters.from_hydraulics(
    length=1000.0,
    width=10.0,
    bed_slope=0.0001,
    manning=0.025,
    normal_depth=2.5
)

# 4. 创建IDZ模型
model = IDZModel(params, dt=10.0)

# 5. MPC控制仿真
horizon = 20
Q = 10.0  # 目标流量差异

for step in range(100):
    # 简单MPC: 预测horizon步
    u_sequence = np.ones(horizon) * Q
    y_pred = model.predict(u_sequence)

    # 选择控制输入
    u = Q
    y = model.step(u)

    print(f"步骤 {step}: 控制输入 {u:.2f}, 输出 {y:.4f}")
```

### 示例2: 在线辨识与自适应控制

```python
from control.idz_model import IDZParameters, IDZModel
from control.online_identification import IDZIdentifier

# 初始IDZ参数（可能不准确）
initial_params = IDZParameters(K=100.0, tau_z=50.0, tau_d=100.0, theta=20.0)
model = IDZModel(initial_params, dt=10.0)

# 在线辨识器
identifier = IDZIdentifier(dt=10.0)

# 自适应控制循环
for step in range(200):
    # 计算控制输入
    u = 0.1  # 简单控制策略

    # 系统响应
    y = model.step(u)

    # 在线辨识
    identified_params = identifier.update(u, y)

    if identified_params is not None:
        # 更新模型参数
        model = IDZModel(identified_params, dt=10.0)
        print(f"步骤 {step}: 更新参数 K={identified_params.K:.2f}")
```

### 示例3: 多断面渠道辨识

```python
from physics.cross_section import TrapezoidalSection
from control.multi_section_identification import (
    SectionLocation, EquivalentSectionMethod
)

# 沿程变化的断面
sections = [
    TrapezoidalSection(f"S{i}", bottom_width=8.0 + i*0.5, side_slope=1.5)
    for i in range(10)
]

locations = [
    SectionLocation(section=s, station=i*1000.0)
    for i, s in enumerate(sections)
]

# 等效断面法
equiv_method = EquivalentSectionMethod(locations, normal_depth=2.5)

# 计算等效IDZ参数
equiv_params = equiv_method.compute_idz_parameters(
    normal_flow=25.0,
    manning_n=0.025,
    bed_slope=0.0001
)

print(f"等效参数: K={equiv_params.K:.2f}, τ_d={equiv_params.tau_d:.2f}")
```

### 示例4: 控制器性能对比

```python
from tools.performance_benchmark import (
    BenchmarkRunner, StepResponseScenario,
    RampTrackingScenario, ControllerInterface
)
from control.idz_model import IDZParameters, IDZModel

# 系统模型
params = IDZParameters(K=100.0, tau_z=50.0, tau_d=100.0, theta=20.0)
pool_model = IDZModel(params, dt=1.0)

def system_model(u, disturbance):
    return pool_model.step(u + disturbance)

# 定义控制器（需要实现ControllerInterface）
class SimplePID(ControllerInterface):
    def __init__(self, kp=0.5, ki=0.1, kd=0.0):
        self.kp, self.ki, self.kd = kp, ki, kd
        self.integral = 0.0
        self.last_error = 0.0

    def reset(self):
        self.integral = 0.0
        self.last_error = 0.0

    def compute_control(self, reference, output, disturbance=0.0):
        error = reference - output
        self.integral += error
        derivative = error - self.last_error
        self.last_error = error
        return self.kp * error + self.ki * self.integral + self.kd * derivative

    def get_name(self):
        return "PID"

# 运行基准测试
runner = BenchmarkRunner(system_model, dt=1.0)
controller = SimplePID()
scenario = StepResponseScenario(duration=600.0, dt=1.0)

metrics = runner.run_benchmark(controller, scenario)

print(f"MAE: {metrics.mae:.4f}")
print(f"RMSE: {metrics.rmse:.4f}")
print(f"调节时间: {metrics.settling_time:.2f} s")
```

---

## 单元测试

所有模块都有完整的单元测试覆盖。

### 运行测试

```bash
# 运行所有测试
python -m pytest tests/ -v

# 运行特定模块测试
python -m pytest tests/test_cross_section.py -v
python -m pytest tests/test_idz_model.py -v
python -m pytest tests/test_online_identification.py -v
python -m pytest tests/test_multi_section_identification.py -v

# 运行单个测试
python -m pytest tests/test_idz_model.py::TestIDZModel::test_step_response_increases -v
```

### 测试统计

- `test_cross_section.py`: 14个测试
- `test_idz_model.py`: 23个测试
- `test_online_identification.py`: 25个测试
- `test_multi_section_identification.py`: 16个测试
- **总计**: 78个单元测试，100%通过

---

## 相关文档

- [README.md](README.md) - 项目总览
- [QUICKSTART_GUIDE.md](QUICKSTART_GUIDE.md) - 快速入门
- [LIBRARY_REFERENCE.md](LIBRARY_REFERENCE.md) - 完整库参考
- [DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md) - 开发指南

---

## 技术支持

- **GitHub Issues**: [https://github.com/leixiaohui-1974/HydroClaude/issues](https://github.com/leixiaohui-1974/HydroClaude/issues)
- **项目主页**: [https://github.com/leixiaohui-1974/HydroClaude](https://github.com/leixiaohui-1974/HydroClaude)

---

**Generated with Claude Code**
**Co-Authored-By: Claude <noreply@anthropic.com>**

**最后更新**: 2025-10-24
**版本**: v1.3
