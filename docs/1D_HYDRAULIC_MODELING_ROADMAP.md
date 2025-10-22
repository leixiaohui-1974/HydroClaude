# HydroClaude 一维水力学模拟完整开发计划

**制定日期**: 2025-10-22
**规划期**: 2025年11月 - 2026年6月（8个月）
**作者**: Claude AI
**版本**: v1.0
**目标**: 实现对明渠、有压、闸、泵、阀、水轮机及各种水工程的完整一维水力学模拟

---

## 📋 执行摘要

基于对现有代码库的全面分析，HydroClaude已经具备了扎实的基础：
- ✅ 明渠非恒定流求解（MOC, Preissmann, FVM）
- ✅ 有压管道水击求解（RK4, RK2）
- ✅ 闸门模型（含解析导数，Jacobian满秩）
- ✅ 稳态求解器（Newton法，100-500x加速）
- ✅ 延拓求解、混合求解等高级策略

**本计划聚焦于**：
1. **补全水力元件库**（泵、阀、水轮机、调压井等）
2. **完善现有元件**（泵特性曲线、阀门控制特性）
3. **建立水电站系统**（引水、厂房、尾水）
4. **构建工程应用案例**（灌溉系统、水电站、供水管网）

---

## 🎯 现状分析

### 已实现的水力元件（7类）

| 元件类型 | 实现状态 | 功能完整度 | 文件位置 | 备注 |
|---------|---------|-----------|---------|------|
| **明渠（Canal）** | ✅ 完整 | ★★★★★ | `physics/canal.py` | 支持3种数值方法 |
| **管道（Pipe）** | ✅ 完整 | ★★★★☆ | `physics/pipe.py` | 水击方程，RK4/RK2 |
| **水池（Tank）** | ✅ 完整 | ★★★☆☆ | `physics/tank.py` | 简单水量平衡 |
| **闸门（Gate）** | ✅ 完整 | ★★★★★ | `solvers/gate.py` | 3种类型，解析导数 |
| **堰（Weir）** | ✅ 完整 | ★★★★☆ | `solvers/gate.py` | 宽顶堰 |
| **孔口（Orifice）** | ✅ 完整 | ★★★★☆ | `solvers/gate.py` | 淹没/自由流态 |
| **泵（Pump）** | ⚠️ 简化 | ★★☆☆☆ | `physics/pump.py` | 仅线性模型 |
| **阀（Valve）** | ❌ 缺失 | ★☆☆☆☆ | `physics/valve.py` | 只有1行代码 |

### 完全缺失的关键元件（9类）

| 元件类型 | 优先级 | 应用场景 | 技术难度 |
|---------|-------|---------|---------|
| **水轮机（Turbine）** | 🔴 最高 | 水电站 | ★★★★☆ |
| **调压井（Surge Tank）** | 🔴 高 | 水电站、长管道 | ★★★★☆ |
| **阀门（Valve）** | 🔴 高 | 管网控制 | ★★★☆☆ |
| **溢洪道（Spillway）** | 🟡 中 | 水库大坝 | ★★★☆☆ |
| **渐变段（Transition）** | 🟡 中 | 渠道过渡 | ★★☆☆☆ |
| **跌水（Drop）** | 🟢 低 | 灌溉渠道 | ★★☆☆☆ |
| **倒虹吸（Inverted Siphon）** | 🟢 低 | 跨越障碍 | ★★★☆☆ |
| **引水隧洞（Tunnel）** | 🟡 中 | 水电站 | ★★★☆☆ |
| **水电站厂房（Powerhouse）** | 🔴 高 | 水电站 | ★★★★★ |

---

## 🚀 开发路线图

```
阶段1 (3周)          阶段2 (4周)          阶段3 (5周)          阶段4 (6周)
基础元件补全          水电系统              控制与优化            综合应用
├─ 阀门完善          ├─ 水轮机            ├─ 调压井            ├─ 典型工程案例
├─ 泵特性曲线        ├─ 引水隧洞          ├─ 先进控制          ├─ 性能优化
├─ 溢洪道            ├─ 厂房系统          ├─ 优化调度          ├─ 文档完善
└─ 渐变段/跌水       └─ 尾水系统          └─ 事故工况          └─ 发布v1.0
```

---

## 🔧 阶段1：基础水力元件补全（3周）

### 1.1 阀门（Valve）完整实现 ⭐⭐⭐

**优先级**: 🔴 最高

#### 功能需求

阀门是管网控制的核心元件，需要支持：

1. **多种阀门类型**：
   - 闸阀（Gate Valve）
   - 蝶阀（Butterfly Valve）
   - 球阀（Ball Valve）
   - 调节阀（Control Valve）

2. **流量特性**：
   ```
   Q = Cv(τ) * √(ΔP)

   其中：
   - Cv(τ): 阀门流量系数，τ为开度（0-1）
   - ΔP: 阀门前后压差
   ```

3. **开度-流量特性曲线**：
   - **快开特性**（Quick Opening）：Cv(τ) ≈ τ²
   - **线性特性**（Linear）：Cv(τ) ≈ τ
   - **等百分比特性**（Equal Percentage）：Cv(τ) = Cv_max * R^(τ-1)

4. **动态响应**：
   ```python
   dτ/dt = (τ_target - τ_current) / T_response
   ```

#### 技术实现方案

```python
# physics/valve.py

import numpy as np
from core.base import HydraulicComponent
from core.states import ComponentState, HydraulicState

class Valve(HydraulicComponent):
    """阀门 - 控制流量和压力"""

    def __init__(self, name: str, valve_type: str = 'linear',
                 Cv_max: float = 100.0, response_time: float = 5.0):
        """
        Args:
            name: 阀门名称
            valve_type: 阀门类型 ('quick', 'linear', 'equal_percentage')
            Cv_max: 最大流量系数
            response_time: 响应时间 (s)
        """
        super().__init__(name, "valve")
        self.valve_type = valve_type
        self.Cv_max = Cv_max
        self.response_time = response_time

        # 等百分比特性参数
        self.R = 50  # 可调范围比

        self.state = ComponentState()
        self.state.opening = 1.0  # 开度 (0-1)
        self.state.flow = 0.0
        self.state.pressure_drop = 0.0

    def get_Cv(self, opening: float) -> float:
        """
        计算流量系数

        Args:
            opening: 阀门开度 (0-1)

        Returns:
            流量系数
        """
        tau = np.clip(opening, 0.0, 1.0)

        if self.valve_type == 'quick':
            # 快开特性：流量随开度快速增加
            Cv = self.Cv_max * tau**2
        elif self.valve_type == 'linear':
            # 线性特性：流量与开度成正比
            Cv = self.Cv_max * tau
        elif self.valve_type == 'equal_percentage':
            # 等百分比特性：相同开度变化，流量变化百分比相同
            if tau < 0.01:
                Cv = 0.0
            else:
                Cv = self.Cv_max * self.R**(tau - 1)
        else:
            raise ValueError(f"Unknown valve type: {self.valve_type}")

        return Cv

    def calculate_flow(self, P_upstream: float, P_downstream: float,
                       opening: float = None) -> float:
        """
        计算通过阀门的流量

        Args:
            P_upstream: 上游压力 (Pa)
            P_downstream: 下游压力 (Pa)
            opening: 阀门开度 (0-1)，如果为None则使用当前开度

        Returns:
            流量 (m³/s)
        """
        if opening is None:
            opening = self.state.opening

        # 压差（确保非负）
        delta_P = max(0.0, P_upstream - P_downstream)

        # 流量系数
        Cv = self.get_Cv(opening)

        # 流量计算（简化公式）
        # Q = Cv * sqrt(ΔP / ρ)
        rho = 1000.0  # 水密度 (kg/m³)
        Q = Cv * np.sqrt(delta_P / rho)

        return Q

    def calculate_flow_derivatives(self, P_upstream: float, P_downstream: float,
                                  opening: float = None) -> tuple:
        """
        计算流量对压力的导数（用于Jacobian）

        Args:
            P_upstream: 上游压力 (Pa)
            P_downstream: 下游压力 (Pa)
            opening: 阀门开度 (0-1)

        Returns:
            (dQ/dP_up, dQ/dP_down): 流量对上下游压力的导数
        """
        if opening is None:
            opening = self.state.opening

        delta_P = max(1e-4, P_upstream - P_downstream)
        Cv = self.get_Cv(opening)
        rho = 1000.0

        # Q = Cv * sqrt(ΔP / ρ)
        # dQ/dP_up = Cv / (2 * sqrt(ΔP * ρ))
        # dQ/dP_down = -dQ/dP_up

        if delta_P > 1e-4:
            dQ_dP_up = Cv / (2.0 * np.sqrt(delta_P * rho))
            dQ_dP_down = -dQ_dP_up
        else:
            # 压差很小时，导数在截断点
            dQ_dP_up = Cv / (2.0 * np.sqrt(1e-4 * rho))
            dQ_dP_down = -dQ_dP_up

        return dQ_dP_up, dQ_dP_down

    def update_high_fidelity(self, dt: float, inputs: dict) -> ComponentState:
        """
        高保真更新（考虑动态响应）

        Args:
            dt: 时间步长 (s)
            inputs: 输入字典
                - 'target_opening': 目标开度 (0-1)
                - 'upstream_pressure': 上游压力 (Pa)
                - 'downstream_pressure': 下游压力 (Pa)

        Returns:
            更新后的状态
        """
        # 目标开度
        target_opening = inputs.get('target_opening', self.state.opening)

        # 动态响应（一阶惯性）
        if self.response_time > 0:
            tau = dt / self.response_time
            self.state.opening += tau * (target_opening - self.state.opening)
        else:
            # 瞬时响应
            self.state.opening = target_opening

        self.state.opening = np.clip(self.state.opening, 0.0, 1.0)

        # 计算流量
        P_up = inputs.get('upstream_pressure', 0.0)
        P_down = inputs.get('downstream_pressure', 0.0)

        self.state.flow = self.calculate_flow(P_up, P_down)
        self.state.pressure_drop = P_up - P_down

        return self.state

    def update_reduced_order(self, dt: float, inputs: dict) -> ComponentState:
        """降阶模型（与高保真相同）"""
        return self.update_high_fidelity(dt, inputs)

    def get_constraints(self) -> dict:
        return {
            'opening': (0.0, 1.0),
            'Cv': (0.0, self.Cv_max)
        }


class GateValve(Valve):
    """闸阀 - 通常使用线性特性"""
    def __init__(self, name: str, **kwargs):
        super().__init__(name, valve_type='linear', **kwargs)


class ButterflyValve(Valve):
    """蝶阀 - 通常使用等百分比特性"""
    def __init__(self, name: str, **kwargs):
        super().__init__(name, valve_type='equal_percentage', **kwargs)


class BallValve(Valve):
    """球阀 - 通常使用快开特性"""
    def __init__(self, name: str, **kwargs):
        super().__init__(name, valve_type='quick', **kwargs)
```

#### 验证测试

```python
# tests/test_valve.py

import pytest
import numpy as np
from physics.valve import Valve, GateValve, ButterflyValve, BallValve

def test_valve_characteristics():
    """测试不同阀门特性曲线"""

    # 线性阀门
    valve_linear = Valve("V1", valve_type='linear', Cv_max=100.0)

    openings = np.linspace(0, 1, 11)
    Cvs = [valve_linear.get_Cv(tau) for tau in openings]

    # 验证线性特性
    assert abs(Cvs[5] - 50.0) < 0.1  # 50%开度 → Cv=50
    assert abs(Cvs[10] - 100.0) < 0.1  # 100%开度 → Cv=100

    # 等百分比阀门
    valve_eqp = Valve("V2", valve_type='equal_percentage', Cv_max=100.0)
    Cvs_eqp = [valve_eqp.get_Cv(tau) for tau in openings]

    # 验证等百分比特性（指数增长）
    assert Cvs_eqp[1] < Cvs_eqp[5] < Cvs_eqp[10]

    print("✓ 阀门特性曲线测试通过")


def test_valve_flow_calculation():
    """测试流量计算"""

    valve = GateValve("GV1", Cv_max=50.0)
    valve.state.opening = 0.5  # 50%开度

    P_up = 500000.0  # 500 kPa
    P_down = 100000.0  # 100 kPa

    Q = valve.calculate_flow(P_up, P_down)

    # 验证流量为正
    assert Q > 0

    # 验证流量随压差增加
    Q2 = valve.calculate_flow(P_up * 2, P_down)
    assert Q2 > Q

    # 验证流量随开度增加
    valve.state.opening = 0.8
    Q3 = valve.calculate_flow(P_up, P_down)
    assert Q3 > Q

    print(f"✓ 流量计算测试通过: Q={Q:.3f} m³/s @ 50%开度, ΔP=400kPa")


def test_valve_derivatives():
    """测试流量导数（用于Jacobian）"""

    valve = ButterflyValve("BV1", Cv_max=80.0)
    valve.state.opening = 0.6

    P_up = 600000.0
    P_down = 200000.0

    # 解析导数
    dQ_dP_up, dQ_dP_down = valve.calculate_flow_derivatives(P_up, P_down)

    # 数值导数验证
    eps = 1e-3
    Q0 = valve.calculate_flow(P_up, P_down)
    Q_up = valve.calculate_flow(P_up + eps, P_down)
    Q_down = valve.calculate_flow(P_up, P_down + eps)

    dQ_dP_up_num = (Q_up - Q0) / eps
    dQ_dP_down_num = (Q_down - Q0) / eps

    # 验证解析导数与数值导数一致（5%误差）
    assert abs(dQ_dP_up - dQ_dP_up_num) / abs(dQ_dP_up_num) < 0.05
    assert abs(dQ_dP_down - dQ_dP_down_num) / abs(dQ_dP_down_num) < 0.05

    print("✓ 导数计算测试通过")


def test_valve_dynamics():
    """测试阀门动态响应"""

    valve = GateValve("GV2", response_time=5.0)
    valve.state.opening = 0.0  # 初始关闭

    dt = 0.1
    target_opening = 1.0  # 目标全开

    # 模拟动态响应
    openings = []
    for i in range(100):
        valve.update_high_fidelity(dt, {
            'target_opening': target_opening,
            'upstream_pressure': 500000.0,
            'downstream_pressure': 100000.0
        })
        openings.append(valve.state.opening)

    # 验证渐进趋向目标值
    assert openings[10] < openings[50] < openings[90]
    assert abs(openings[-1] - target_opening) < 0.05  # 最终接近目标值

    print(f"✓ 动态响应测试通过: 最终开度={openings[-1]:.3f}")


if __name__ == "__main__":
    test_valve_characteristics()
    test_valve_flow_calculation()
    test_valve_derivatives()
    test_valve_dynamics()
    print("\n✓✓✓ 所有阀门测试通过！")
```

**工作量估算**: 3天
- 实现阀门类：1.5天
- 测试验证：1天
- 文档编写：0.5天

---

### 1.2 泵特性曲线完善 ⭐⭐⭐

**优先级**: 🔴 高

#### 现状问题

当前泵模型过于简化：
```python
# 当前实现（physics/pump.py）
self.state.flow = self.max_flow * speed / 100.0
self.state.head = self.rated_head * (speed / 100.0) ** 2
```

**问题**：
- 只有线性流量关系
- 扬程仅考虑转速，不考虑流量
- 缺少效率曲线
- 无法模拟泵的全特性工况

#### 改进方案

实现完整的泵特性曲线：

```python
# physics/pump.py (改进版)

import numpy as np
from scipy.interpolate import interp1d

class Pump(HydraulicComponent):
    """泵站 - 完整特性曲线"""

    def __init__(self, name: str, rated_flow: float = 100.0,
                 rated_head: float = 50.0, rated_speed: float = 1500.0,
                 characteristic_curve: str = 'parabolic'):
        """
        Args:
            name: 泵名称
            rated_flow: 额定流量 (m³/s)
            rated_head: 额定扬程 (m)
            rated_speed: 额定转速 (rpm)
            characteristic_curve: 特性曲线类型 ('parabolic', 'polynomial', 'tabular')
        """
        super().__init__(name, "pump")
        self.rated_flow = rated_flow
        self.rated_head = rated_head
        self.rated_speed = rated_speed
        self.curve_type = characteristic_curve

        # 特性曲线参数（抛物线型）
        self.H0 = rated_head * 1.2  # 零流量扬程
        self.a = -(self.H0 - rated_head) / (rated_flow ** 2)  # 二次项系数

        # 效率曲线参数
        self.eta_max = 0.85  # 最高效率
        self.Q_eta_max = rated_flow  # 最高效率点流量

        self.state = ComponentState()
        self.state.flow = 0.0
        self.state.head = 0.0
        self.state.power = 0.0
        self.state.efficiency = 0.0
        self.state.speed = rated_speed  # 当前转速 (rpm)

    def calculate_head(self, Q: float, n: float = None) -> float:
        """
        根据流量和转速计算扬程（泵特性曲线）

        H = H₀ - a*Q² (相似定律修正)

        Args:
            Q: 流量 (m³/s)
            n: 转速 (rpm)，如果为None则使用当前转速

        Returns:
            扬程 (m)
        """
        if n is None:
            n = self.state.speed

        # 转速修正系数
        speed_ratio = n / self.rated_speed

        # 根据相似定律修正流量到额定转速
        Q_rated = Q / speed_ratio if speed_ratio > 0.1 else 0.0

        # 特性曲线计算
        if self.curve_type == 'parabolic':
            # H = H₀ - a*Q²
            H_rated = self.H0 + self.a * (Q_rated ** 2)
            H_rated = max(0.0, H_rated)
        else:
            H_rated = 0.0

        # 扬程随转速的相似定律：H ∝ n²
        H = H_rated * (speed_ratio ** 2)

        return H

    def calculate_efficiency(self, Q: float, n: float = None) -> float:
        """
        计算泵效率

        η = η_max * (1 - ((Q - Q_opt) / Q_opt)²)

        Args:
            Q: 流量 (m³/s)
            n: 转速 (rpm)

        Returns:
            效率 (0-1)
        """
        if n is None:
            n = self.state.speed

        speed_ratio = n / self.rated_speed
        Q_rated = Q / speed_ratio if speed_ratio > 0.1 else 0.0

        # 效率曲线（简化为抛物线，最高效率点在额定流量）
        if Q_rated > 0:
            eta = self.eta_max * (1.0 - ((Q_rated - self.Q_eta_max) / self.Q_eta_max) ** 2)
            eta = np.clip(eta, 0.1, self.eta_max)
        else:
            eta = 0.0

        return eta

    def calculate_power(self, Q: float, H: float, eta: float) -> float:
        """
        计算泵功率

        P = ρ * g * Q * H / η

        Args:
            Q: 流量 (m³/s)
            H: 扬程 (m)
            eta: 效率 (0-1)

        Returns:
            功率 (W)
        """
        rho = 1000.0  # 水密度 (kg/m³)
        g = 9.81      # 重力加速度 (m/s²)

        if eta > 0.01:
            P = rho * g * Q * H / eta
        else:
            P = 0.0

        return P

    def update_high_fidelity(self, dt: float, inputs: dict) -> ComponentState:
        """
        高保真更新

        Args:
            dt: 时间步长 (s)
            inputs: 输入字典
                - 'speed': 转速设定值 (rpm)
                - 'suction_head': 吸入端水头 (m)
                - 'discharge_head': 排出端水头 (m)

        Returns:
            更新后的状态
        """
        # 转速
        target_speed = inputs.get('speed', self.rated_speed)
        self.state.speed = target_speed

        # 吸入和排出端水头
        h_suction = inputs.get('suction_head', 0.0)
        h_discharge = inputs.get('discharge_head', 0.0)

        # 实际扬程（系统需求）
        H_required = h_discharge - h_suction

        # 迭代求解工作点（H_pump(Q) = H_required）
        # 简化方法：使用特性曲线反解
        # H₀ - a*Q² = H_required
        # Q = sqrt((H₀ - H_required) / a)

        speed_ratio = target_speed / self.rated_speed
        H0_actual = self.H0 * (speed_ratio ** 2)

        if H0_actual > H_required and abs(self.a) > 1e-9:
            Q_rated_sq = (self.H0 - H_required / (speed_ratio ** 2)) / abs(self.a)
            if Q_rated_sq > 0:
                Q_rated = np.sqrt(Q_rated_sq)
                Q_actual = Q_rated * speed_ratio
            else:
                Q_actual = 0.0
        else:
            Q_actual = 0.0

        # 更新状态
        self.state.flow = Q_actual
        self.state.head = self.calculate_head(Q_actual, target_speed)
        self.state.efficiency = self.calculate_efficiency(Q_actual, target_speed)
        self.state.power = self.calculate_power(Q_actual, self.state.head,
                                                self.state.efficiency)

        return self.state

    def update_reduced_order(self, dt: float, inputs: dict) -> ComponentState:
        """降阶模型（简化为线性）"""
        speed = inputs.get('speed', self.rated_speed)
        speed_ratio = speed / self.rated_speed

        self.state.flow = self.rated_flow * speed_ratio
        self.state.head = self.rated_head * (speed_ratio ** 2)
        self.state.efficiency = self.eta_max
        self.state.power = self.calculate_power(self.state.flow, self.state.head,
                                                self.state.efficiency)

        return self.state

    def get_constraints(self):
        return {
            'flow': (0.0, self.rated_flow * 1.2),
            'head': (0.0, self.H0),
            'speed': (0.0, self.rated_speed * 1.2),
            'efficiency': (0.0, self.eta_max)
        }
```

**工作量估算**: 2天

---

### 1.3 溢洪道（Spillway）⭐⭐

**优先级**: 🟡 中

#### 技术实现

```python
# solvers/gate.py (添加到现有文件)

class Spillway(HydraulicStructure):
    """
    溢洪道 - 自由溢流堰

    支持多种堰型：
    - 实用堰（Practical Weir）
    - WES标准堰（WES Standard Spillway）
    - 宽顶堰（Broad-Crested Weir）
    """

    def __init__(self, position: float, width: float, crest_elevation: float,
                 spillway_type: str = 'wes', Cd: float = 2.1, g: float = 9.81):
        """
        Args:
            position: 溢洪道位置 (m)
            width: 溢洪道宽度 (m)
            crest_elevation: 堰顶高程 (m)
            spillway_type: 溢洪道类型 ('wes', 'ogee', 'broad_crested')
            Cd: 流量系数（WES堰约2.1）
            g: 重力加速度 (m/s²)
        """
        super().__init__(position, width, g)
        self.crest_elevation = crest_elevation
        self.spillway_type = spillway_type
        self.Cd = Cd

    def calculate_discharge(self, h_upstream: float, h_downstream: float = None,
                          t: float = None) -> tuple:
        """
        计算溢洪道流量

        标准堰流公式：
        Q = Cd * B * H^(3/2)

        其中 H 为堰顶以上水头

        Args:
            h_upstream: 上游水深 (m)
            h_downstream: 下游水深 (m，用于淹没修正)
            t: 时间 (s)

        Returns:
            (discharge, flow_type): 流量 (m³/s) 和流态
        """
        # 堰顶以上水头
        H = max(0.0, h_upstream - self.crest_elevation)

        if H < 1e-4:
            return 0.0, 'no_flow'

        # 基本流量公式
        if self.spillway_type == 'wes':
            # WES标准溢洪道：Q = Cd * B * H^(3/2)
            Q_free = self.Cd * self.width * (H ** 1.5)
        elif self.spillway_type == 'ogee':
            # 实用堰（Ogee）：与WES类似
            Q_free = self.Cd * self.width * (H ** 1.5)
        elif self.spillway_type == 'broad_crested':
            # 宽顶堰：Q = Cd * B * H^(3/2) * sqrt(2g)
            Q_free = self.Cd * self.width * (H ** 1.5) * np.sqrt(2 * self.g)
        else:
            Q_free = 0.0

        # 淹没修正（如果下游水位影响）
        if h_downstream is not None:
            h_tail = h_downstream
            # 淹没比
            if h_tail > self.crest_elevation:
                submergence_ratio = (h_tail - self.crest_elevation) / H
                if submergence_ratio > 0.67:
                    # 淹没出流，流量折减
                    submergence_factor = (1.0 - submergence_ratio) ** 1.5
                    Q = Q_free * max(0.1, submergence_factor)
                    return Q, 'submerged'

        return Q_free, 'free'

    def calculate_discharge_derivatives(self, h_upstream: float,
                                        h_downstream: float = None,
                                        t: float = None) -> tuple:
        """
        计算流量对水深的导数

        Q = Cd * B * H^(3/2)
        dQ/dH = (3/2) * Cd * B * H^(1/2)

        Args:
            h_upstream: 上游水深 (m)
            h_downstream: 下游水深 (m)
            t: 时间 (s)

        Returns:
            (dQ/dh_up, dQ/dh_down): 导数
        """
        H = max(1e-4, h_upstream - self.crest_elevation)

        if H < 1e-4:
            return 0.0, 0.0

        # dQ/dH
        if self.spillway_type in ['wes', 'ogee']:
            dQ_dH = 1.5 * self.Cd * self.width * np.sqrt(H)
        elif self.spillway_type == 'broad_crested':
            dQ_dH = 1.5 * self.Cd * self.width * np.sqrt(H * 2 * self.g)
        else:
            dQ_dH = 0.0

        # dQ/dh_up = dQ/dH * dH/dh_up = dQ/dH * 1
        dQ_dh_up = dQ_dH

        # 自由溢流不依赖下游水深
        dQ_dh_down = 0.0

        return dQ_dh_up, dQ_dh_down

    def __repr__(self) -> str:
        return (f"Spillway(type={self.spillway_type}, position={self.position}m, "
                f"width={self.width}m, crest={self.crest_elevation}m, Cd={self.Cd})")
```

**工作量估算**: 1天

---

### 1.4 渐变段（Transition）和跌水（Drop）⭐

**优先级**: 🟢 低

#### 渐变段

用于明渠断面尺寸变化：

```python
# solvers/gate.py (添加)

class Transition(HydraulicStructure):
    """
    渐变段 - 断面过渡

    能量方程：
    h₁ + V₁²/(2g) = h₂ + V₂²/(2g) + h_loss

    其中 h_loss = K * (V₁ - V₂)²/(2g)
    K为局部损失系数
    """

    def __init__(self, position: float, width_upstream: float,
                 width_downstream: float, K_loss: float = 0.1, g: float = 9.81):
        super().__init__(position, width_upstream, g)
        self.width_downstream = width_downstream
        self.K_loss = K_loss  # 局部损失系数

    def calculate_discharge(self, h_upstream: float, h_downstream: float,
                          t: float = None) -> tuple:
        """
        通过渐变段的流量（使用能量方程）
        """
        # 简化：假设流量连续
        # Q = A₁*V₁ = A₂*V₂
        # 通过能量方程迭代求解

        A1 = h_upstream * self.width
        A2 = h_downstream * self.width_downstream

        # 简化计算（假设损失较小）
        E1 = h_upstream  # 比能（忽略流速水头）
        E2 = h_downstream + self.K_loss * 0.01  # 估计损失

        # 流量估算
        V1 = np.sqrt(2 * self.g * (E1 - E2))
        Q = A1 * V1

        return Q, 'transition'
```

#### 跌水

用于渠道高程跌落：

```python
class Drop(HydraulicStructure):
    """
    跌水 - 高程变化

    类似小型瀑布，能量损失显著
    """

    def __init__(self, position: float, width: float, drop_height: float,
                 Cd: float = 0.6, g: float = 9.81):
        super().__init__(position, width, g)
        self.drop_height = drop_height
        self.Cd = Cd

    def calculate_discharge(self, h_upstream: float, h_downstream: float = None,
                          t: float = None) -> tuple:
        """
        跌水流量

        Q = Cd * B * h * sqrt(2g * (h + Δz))
        """
        delta_z = self.drop_height

        Q = self.Cd * self.width * h_upstream * np.sqrt(2 * self.g * (h_upstream + delta_z))

        return Q, 'drop'
```

**工作量估算**: 1天

---

## 🔧 阶段2：水电系统元件（4周）

### 2.1 水轮机（Turbine）⭐⭐⭐

**优先级**: 🔴 最高

#### 功能需求

水轮机是水电站的核心设备，需要模拟：

1. **多种水轮机类型**：
   - 冲击式：Pelton（佩尔顿）轮
   - 反击式：Francis（混流式）、Kaplan（轴流式）

2. **特性曲线**：
   - 单位流量曲线：Q₁₁ = f(n₁₁, a)
   - 单位扭矩曲线：M₁₁ = f(n₁₁, a)
   - 效率曲线：η = f(n₁₁, a)

3. **调节机构**：
   - 导叶开度 a（0-1）
   - 转速 n（rpm）

4. **工作点计算**：
   - 综合特性曲线法
   - 相似定律

#### 技术实现

```python
# physics/turbine.py (新文件)

import numpy as np
from scipy.interpolate import interp2d, RectBivariateSpline
from core.base import HydraulicComponent
from core.states import ComponentState

class Turbine(HydraulicComponent):
    """
    水轮机 - 水能转换装置

    模型基于相似定律和特性曲线：
    - 单位转速：n₁₁ = n * D / √H
    - 单位流量：Q₁₁ = Q / (D² * √H)
    - 单位功率：P₁₁ = P / (D² * H^(3/2))

    其中：
    - n: 转速 (rpm)
    - D: 转轮直径 (m)
    - H: 水头 (m)
    - Q: 流量 (m³/s)
    - P: 功率 (W)
    """

    def __init__(self, name: str, turbine_type: str = 'francis',
                 rated_head: float = 100.0, rated_flow: float = 50.0,
                 rated_speed: float = 500.0, runner_diameter: float = 2.0,
                 rated_power: float = 40e6):
        """
        Args:
            name: 水轮机名称
            turbine_type: 水轮机类型 ('pelton', 'francis', 'kaplan')
            rated_head: 额定水头 (m)
            rated_flow: 额定流量 (m³/s)
            rated_speed: 额定转速 (rpm)
            runner_diameter: 转轮直径 (m)
            rated_power: 额定功率 (W)
        """
        super().__init__(name, "turbine")
        self.turbine_type = turbine_type
        self.rated_head = rated_head
        self.rated_flow = rated_flow
        self.rated_speed = rated_speed
        self.D = runner_diameter
        self.rated_power = rated_power

        # 额定工况单位参数
        self.n11_rated = rated_speed * runner_diameter / np.sqrt(rated_head)
        self.Q11_rated = rated_flow / (runner_diameter**2 * np.sqrt(rated_head))

        # 特性曲线（简化为解析函数）
        self._init_characteristic_curves()

        self.state = ComponentState()
        self.state.flow = 0.0
        self.state.head = 0.0
        self.state.power = 0.0
        self.state.efficiency = 0.0
        self.state.speed = rated_speed  # 当前转速 (rpm)
        self.state.guide_vane_opening = 0.5  # 导叶开度 (0-1)
        self.state.torque = 0.0  # 扭矩 (N·m)

    def _init_characteristic_curves(self):
        """初始化特性曲线（简化版）"""

        if self.turbine_type == 'francis':
            # Francis水轮机特性（简化）
            # 单位流量随单位转速和开度变化
            # Q₁₁ = f(n₁₁, a)

            # 单位转速范围
            self.n11_range = np.linspace(20, 120, 20)
            # 开度范围
            self.a_range = np.linspace(0.1, 1.0, 10)

            # 构造特性曲线网格（简化为抛物面）
            n11_grid, a_grid = np.meshgrid(self.n11_range, self.a_range)

            # Q₁₁特性（简化公式）
            self.Q11_grid = a_grid * (150 - 0.5 * (n11_grid - 70)**2)
            self.Q11_grid = np.maximum(self.Q11_grid, 1.0)

            # 效率特性（简化）
            # 最高效率点在n₁₁≈70, a≈0.8
            self.eta_grid = 0.9 * np.exp(-((n11_grid - 70)**2 / 1000 +
                                           (a_grid - 0.8)**2 / 0.2))
            self.eta_grid = np.clip(self.eta_grid, 0.5, 0.93)

            # 创建插值函数
            self.Q11_interp = RectBivariateSpline(self.a_range, self.n11_range,
                                                  self.Q11_grid)
            self.eta_interp = RectBivariateSpline(self.a_range, self.n11_range,
                                                  self.eta_grid)

        elif self.turbine_type == 'pelton':
            # Pelton水轮机特性
            pass  # 类似处理

        elif self.turbine_type == 'kaplan':
            # Kaplan水轮机特性
            pass  # 类似处理

    def calculate_unit_parameters(self, H: float, Q: float, n: float) -> dict:
        """
        计算单位参数

        Args:
            H: 水头 (m)
            Q: 流量 (m³/s)
            n: 转速 (rpm)

        Returns:
            单位参数字典
        """
        sqrt_H = np.sqrt(max(1.0, H))

        n11 = n * self.D / sqrt_H
        Q11 = Q / (self.D**2 * sqrt_H)

        return {'n11': n11, 'Q11': Q11}

    def get_discharge_from_curve(self, H: float, n: float, a: float) -> float:
        """
        根据特性曲线获取流量

        Args:
            H: 水头 (m)
            n: 转速 (rpm)
            a: 导叶开度 (0-1)

        Returns:
            流量 (m³/s)
        """
        sqrt_H = np.sqrt(max(1.0, H))
        n11 = n * self.D / sqrt_H

        # 从特性曲线插值获取Q₁₁
        Q11 = float(self.Q11_interp(a, n11)[0, 0])

        # 反算实际流量
        Q = Q11 * (self.D**2) * sqrt_H

        return Q

    def get_efficiency(self, H: float, n: float, a: float) -> float:
        """
        获取效率

        Args:
            H: 水头 (m)
            n: 转速 (rpm)
            a: 导叶开度 (0-1)

        Returns:
            效率 (0-1)
        """
        sqrt_H = np.sqrt(max(1.0, H))
        n11 = n * self.D / sqrt_H

        # 从特性曲线插值获取效率
        eta = float(self.eta_interp(a, n11)[0, 0])

        return eta

    def calculate_power(self, Q: float, H: float, eta: float) -> float:
        """
        计算输出功率

        P = ρ * g * Q * H * η

        Args:
            Q: 流量 (m³/s)
            H: 水头 (m)
            eta: 效率 (0-1)

        Returns:
            功率 (W)
        """
        rho = 1000.0  # kg/m³
        g = 9.81      # m/s²

        P = rho * g * Q * H * eta

        return P

    def calculate_torque(self, P: float, n: float) -> float:
        """
        计算扭矩

        M = P / ω = P / (2π * n / 60)

        Args:
            P: 功率 (W)
            n: 转速 (rpm)

        Returns:
            扭矩 (N·m)
        """
        if n > 0.1:
            omega = 2 * np.pi * n / 60.0  # rad/s
            M = P / omega
        else:
            M = 0.0

        return M

    def update_high_fidelity(self, dt: float, inputs: dict) -> ComponentState:
        """
        高保真更新（使用特性曲线）

        Args:
            dt: 时间步长 (s)
            inputs: 输入字典
                - 'guide_vane_opening': 导叶开度 (0-1)
                - 'speed': 转速 (rpm)
                - 'upstream_head': 上游水头 (m)
                - 'downstream_head': 下游水头 (m)

        Returns:
            更新后的状态
        """
        # 获取输入
        a = inputs.get('guide_vane_opening', self.state.guide_vane_opening)
        n = inputs.get('speed', self.state.speed)
        h_up = inputs.get('upstream_head', self.rated_head)
        h_down = inputs.get('downstream_head', 0.0)

        # 净水头
        H = h_up - h_down
        H = max(1.0, H)  # 防止负水头

        # 从特性曲线获取流量
        Q = self.get_discharge_from_curve(H, n, a)

        # 从特性曲线获取效率
        eta = self.get_efficiency(H, n, a)

        # 计算功率
        P = self.calculate_power(Q, H, eta)

        # 计算扭矩
        M = self.calculate_torque(P, n)

        # 更新状态
        self.state.guide_vane_opening = a
        self.state.speed = n
        self.state.flow = Q
        self.state.head = H
        self.state.efficiency = eta
        self.state.power = P
        self.state.torque = M

        return self.state

    def update_reduced_order(self, dt: float, inputs: dict) -> ComponentState:
        """降阶模型（简化线性关系）"""
        a = inputs.get('guide_vane_opening', 0.5)
        h_up = inputs.get('upstream_head', self.rated_head)
        h_down = inputs.get('downstream_head', 0.0)

        H = h_up - h_down

        # 简化：流量与开度和水头成正比
        Q = a * self.rated_flow * np.sqrt(H / self.rated_head)

        # 简化：效率恒定
        eta = 0.9

        # 功率
        P = self.calculate_power(Q, H, eta)

        self.state.flow = Q
        self.state.head = H
        self.state.power = P
        self.state.efficiency = eta

        return self.state

    def get_constraints(self) -> dict:
        return {
            'guide_vane_opening': (0.0, 1.0),
            'flow': (0.0, self.rated_flow * 1.2),
            'head': (self.rated_head * 0.5, self.rated_head * 1.3),
            'power': (0.0, self.rated_power * 1.1),
            'efficiency': (0.5, 0.95)
        }
```

#### 测试验证

```python
# tests/test_turbine.py

def test_turbine_characteristic_curve():
    """测试水轮机特性曲线"""

    turbine = Turbine(
        name="Francis1",
        turbine_type='francis',
        rated_head=100.0,
        rated_flow=50.0,
        rated_speed=500.0,
        runner_diameter=2.0
    )

    # 测试额定工况
    H = 100.0
    n = 500.0
    a = 0.8

    Q = turbine.get_discharge_from_curve(H, n, a)
    eta = turbine.get_efficiency(H, n, a)
    P = turbine.calculate_power(Q, H, eta)

    print(f"额定工况:")
    print(f"  流量: {Q:.2f} m³/s")
    print(f"  效率: {eta*100:.1f}%")
    print(f"  功率: {P/1e6:.2f} MW")

    # 验证功率在合理范围
    assert P > 30e6 and P < 50e6  # 30-50 MW
    assert eta > 0.85  # 效率>85%

    print("✓ 水轮机特性曲线测试通过")


def test_turbine_unit_parameters():
    """测试单位参数计算"""

    turbine = Turbine(name="T1")

    unit_params = turbine.calculate_unit_parameters(
        H=100.0, Q=50.0, n=500.0
    )

    assert 'n11' in unit_params
    assert 'Q11' in unit_params

    print(f"单位参数: n₁₁={unit_params['n11']:.1f}, Q₁₁={unit_params['Q11']:.2f}")
    print("✓ 单位参数计算测试通过")


if __name__ == "__main__":
    test_turbine_characteristic_curve()
    test_turbine_unit_parameters()
    print("\n✓✓✓ 所有水轮机测试通过！")
```

**工作量估算**: 5天
- 特性曲线实现：2天
- 相似定律和工作点计算：2天
- 测试验证：1天

---

### 2.2 调压井（Surge Tank）⭐⭐⭐

**优先级**: 🔴 高

#### 功能需求

调压井用于：
1. 缓冲水击压力
2. 稳定水位波动
3. 保护管道和水轮机

#### 技术实现

```python
# physics/surge_tank.py (新文件)

import numpy as np
from core.base import HydraulicComponent
from core.states import ComponentState

class SurgeTank(HydraulicComponent):
    """
    调压井 - 缓冲水击和水位波动

    水位振荡微分方程：
    dz/dt = -Q_tunnel / A_tank
    dQ/dt = -g * A_tunnel / L_tunnel * (z + h_loss)

    其中：
    - z: 调压井水位相对平衡位置 (m)
    - Q_tunnel: 隧洞流量 (m³/s)
    - A_tank: 调压井断面积 (m²)
    - A_tunnel: 隧洞断面积 (m²)
    - L_tunnel: 隧洞长度 (m)
    - h_loss: 沿程损失 (m)
    """

    def __init__(self, name: str, cross_section_area: float = 100.0,
                 bottom_elevation: float = 50.0, max_level: float = 100.0,
                 tunnel_length: float = 1000.0, tunnel_area: float = 10.0,
                 friction_factor: float = 0.02):
        """
        Args:
            name: 调压井名称
            cross_section_area: 调压井断面积 (m²)
            bottom_elevation: 井底高程 (m)
            max_level: 最高水位 (m)
            tunnel_length: 上游隧洞长度 (m)
            tunnel_area: 隧洞断面积 (m²)
            friction_factor: 摩阻系数
        """
        super().__init__(name, "surge_tank")
        self.A_tank = cross_section_area
        self.z_bottom = bottom_elevation
        self.z_max = max_level
        self.L_tunnel = tunnel_length
        self.A_tunnel = tunnel_area
        self.f = friction_factor

        self.state = ComponentState()
        self.state.level = (bottom_elevation + max_level) / 2  # 初始水位
        self.state.flow = 0.0  # 隧洞流量
        self.state.volume = self.A_tank * self.state.level

        # 动力学状态
        self.Q_tunnel = 0.0  # 隧洞流量 (m³/s)
        self.z = 0.0  # 水位相对平衡位置 (m)
        self.equilibrium_level = self.state.level  # 平衡水位

    def calculate_friction_loss(self, Q: float) -> float:
        """
        计算隧洞沿程损失

        h_loss = f * (L/D) * V²/(2g) = f * L * Q² / (2gA²D)

        Args:
            Q: 流量 (m³/s)

        Returns:
            水头损失 (m)
        """
        if abs(Q) < 1e-6:
            return 0.0

        # 隧洞直径（假设圆形）
        D = np.sqrt(4 * self.A_tunnel / np.pi)

        # 流速
        V = Q / self.A_tunnel

        # 损失
        g = 9.81
        h_loss = self.f * (self.L_tunnel / D) * (V**2) / (2 * g)

        # 考虑流向（损失始终阻碍流动）
        h_loss = np.sign(Q) * h_loss

        return h_loss

    def surge_oscillation_ode(self, state, reservoir_level: float) -> np.ndarray:
        """
        调压井振荡微分方程

        状态向量: [z, Q]
        - z: 水位相对平衡位置 (m)
        - Q: 隧洞流量 (m³/s)

        微分方程:
        dz/dt = -Q / A_tank
        dQ/dt = -g * A_tunnel / L_tunnel * (z + h_loss)

        Args:
            state: 状态向量 [z, Q]
            reservoir_level: 上游水库水位 (m)

        Returns:
            dstate/dt
        """
        z, Q = state

        # 当前调压井绝对水位
        level = self.equilibrium_level + z

        # 上下游水头差
        delta_h = reservoir_level - level

        # 沿程损失
        h_loss = self.calculate_friction_loss(Q)

        # 净水头（驱动流动）
        h_net = delta_h - h_loss

        # 微分方程
        g = 9.81
        dz_dt = -Q / self.A_tank
        dQ_dt = -(g * self.A_tunnel / self.L_tunnel) * h_net

        return np.array([dz_dt, dQ_dt])

    def update_high_fidelity(self, dt: float, inputs: dict) -> ComponentState:
        """
        高保真更新（求解微分方程）

        Args:
            dt: 时间步长 (s)
            inputs: 输入字典
                - 'reservoir_level': 上游水库水位 (m)
                - 'turbine_flow': 水轮机取水流量 (m³/s)

        Returns:
            更新后的状态
        """
        reservoir_level = inputs.get('reservoir_level', self.equilibrium_level)
        Q_turbine = inputs.get('turbine_flow', 0.0)

        # 状态向量
        state = np.array([self.z, self.Q_tunnel])

        # RK4积分
        k1 = self.surge_oscillation_ode(state, reservoir_level)
        k2 = self.surge_oscillation_ode(state + 0.5*dt*k1, reservoir_level)
        k3 = self.surge_oscillation_ode(state + 0.5*dt*k2, reservoir_level)
        k4 = self.surge_oscillation_ode(state + dt*k3, reservoir_level)

        state_new = state + (dt/6.0) * (k1 + 2*k2 + 2*k3 + k4)

        self.z, self.Q_tunnel = state_new

        # 更新绝对水位
        self.state.level = self.equilibrium_level + self.z

        # 限制水位范围
        self.state.level = np.clip(self.state.level, self.z_bottom, self.z_max)

        # 水量平衡：dV/dt = Q_tunnel - Q_turbine
        dV = (self.Q_tunnel - Q_turbine) * dt
        self.state.volume += dV

        # 更新流量状态
        self.state.flow = self.Q_tunnel

        return self.state

    def update_reduced_order(self, dt: float, inputs: dict) -> ComponentState:
        """降阶模型（简单水量平衡）"""
        Q_in = inputs.get('inflow', 0.0)
        Q_out = inputs.get('outflow', 0.0)

        dV = (Q_in - Q_out) * dt
        self.state.volume += dV
        self.state.volume = np.clip(self.state.volume,
                                    self.z_bottom * self.A_tank,
                                    self.z_max * self.A_tank)

        self.state.level = self.state.volume / self.A_tank
        self.state.flow = (Q_in + Q_out) / 2

        return self.state

    def get_constraints(self) -> dict:
        return {
            'level': (self.z_bottom, self.z_max),
            'volume': (self.z_bottom * self.A_tank, self.z_max * self.A_tank)
        }
```

**工作量估算**: 3天

---

### 2.3 引水隧洞（Tunnel）⭐⭐

**优先级**: 🟡 中

引水隧洞可以复用现有的`Pipe`类，只需要：

1. **设置合适的参数**：
   - 较大直径（5-10m）
   - 较长长度（数km）
   - 较小糙率（混凝土衬砌）

2. **边界条件**：
   - 上游：水库水位
   - 下游：调压井或压力管道

```python
# 示例：创建引水隧洞
from physics.pipe import Pipe

tunnel = Pipe(
    name="DivertingTunnel1",
    length=5000.0,        # 5 km
    diameter=8.0,         # 8 m
    wave_speed=1200.0,    # 混凝土管道
    n_sections=51,
    method='rk4'
)

# 设置糙率
tunnel.parameters['roughness'] = 0.014  # 混凝土
```

**工作量估算**: 0.5天（文档和示例）

---

### 2.4 水电站厂房系统（Powerhouse）⭐⭐⭐

**优先级**: 🔴 高

#### 功能需求

厂房系统集成：
1. 水轮机
2. 发电机
3. 尾水系统
4. 控制逻辑

#### 技术实现

```python
# physics/powerhouse.py (新文件)

from physics.turbine import Turbine

class Powerhouse(HydraulicComponent):
    """
    水电站厂房 - 集成系统

    包含：
    - 水轮机
    - 发电机
    - 尾水管
    - 调速器
    """

    def __init__(self, name: str, turbine: Turbine,
                 generator_efficiency: float = 0.98,
                 tailwater_elevation: float = 0.0):
        super().__init__(name, "powerhouse")
        self.turbine = turbine
        self.eta_generator = generator_efficiency
        self.z_tailwater = tailwater_elevation

        self.state = ComponentState()
        self.state.electrical_power = 0.0  # 电功率 (W)
        self.state.guide_vane_opening = 0.5

    def update_high_fidelity(self, dt: float, inputs: dict) -> ComponentState:
        """更新厂房状态"""

        # 更新水轮机
        turbine_inputs = {
            'guide_vane_opening': inputs.get('guide_vane_opening', 0.5),
            'speed': inputs.get('speed', self.turbine.rated_speed),
            'upstream_head': inputs.get('upstream_head', self.turbine.rated_head),
            'downstream_head': self.z_tailwater
        }

        self.turbine.update_high_fidelity(dt, turbine_inputs)

        # 计算电功率
        P_mechanical = self.turbine.state.power
        P_electrical = P_mechanical * self.eta_generator

        # 更新状态
        self.state.flow = self.turbine.state.flow
        self.state.electrical_power = P_electrical
        self.state.efficiency = self.turbine.state.efficiency * self.eta_generator

        return self.state
```

**工作量估算**: 2天

---

## 🔧 阶段3：控制与优化（5周）

### 3.1 完善控制算法

1. **调速器（Governor）**
2. **励磁系统（Excitation）**
3. **协调控制（Coordinated Control）**

### 3.2 优化调度

1. **经济调度（Economic Dispatch）**
2. **机组组合（Unit Commitment）**
3. **优化算法（PSO, GA, 等）**

### 3.3 事故工况模拟

1. **甩负荷（Load Rejection）**
2. **飞逸转速（Runaway Speed）**
3. **水锤保护（Water Hammer Protection）**

---

## 🔧 阶段4：综合应用与完善（6周）

### 4.1 典型工程案例

#### 案例1：高坝大库水电站

```
水库 → 引水隧洞 → 调压井 → 压力管道 → 水轮机 → 尾水隧洞 → 河道
```

#### 案例2：灌溉渠系

```
渠首 → 总干渠 → 分水闸 → 支渠 → 跌水 → 农田
```

#### 案例3：城市供水系统

```
水厂 → 泵站 → 主管网 → 调节阀 → 配水管网 → 用户
```

### 4.2 性能优化

1. **并行计算**
2. **GPU加速**
3. **自适应网格**

### 4.3 完善文档

1. **用户手册**
2. **理论手册**
3. **API文档**
4. **案例教程**

---

## 📊 开发时间线

| 阶段 | 周数 | 关键里程碑 | 可交付成果 |
|-----|-----|-----------|-----------|
| **阶段1** | 3周 | 基础元件补全 | 阀门、泵、溢洪道、渐变段 |
| **阶段2** | 4周 | 水电系统 | 水轮机、调压井、厂房系统 |
| **阶段3** | 5周 | 控制优化 | 调速器、优化调度、事故工况 |
| **阶段4** | 6周 | 综合应用 | 典型案例、文档、发布v1.0 |

**总计**: 18周（约4.5个月）

---

## 🎯 优先级矩阵

| 元件/功能 | 技术难度 | 应用价值 | 开发周期 | 综合优先级 |
|---------|---------|---------|---------|-----------|
| **阀门** | ★★★☆☆ | ★★★★★ | 3天 | 🔴 最高 |
| **水轮机** | ★★★★☆ | ★★★★★ | 5天 | 🔴 最高 |
| **调压井** | ★★★★☆ | ★★★★☆ | 3天 | 🔴 高 |
| **泵特性** | ★★★☆☆ | ★★★★☆ | 2天 | 🔴 高 |
| **厂房系统** | ★★★★★ | ★★★★☆ | 2天 | 🔴 高 |
| **溢洪道** | ★★★☆☆ | ★★★☆☆ | 1天 | 🟡 中 |
| **隧洞** | ★★☆☆☆ | ★★★☆☆ | 0.5天 | 🟡 中 |
| **渐变段** | ★★☆☆☆ | ★★☆☆☆ | 1天 | 🟢 低 |
| **跌水** | ★★☆☆☆ | ★★☆☆☆ | 1天 | 🟢 低 |

---

## 💰 投资回报分析

### 高价值元件（ROI > 4）

1. **阀门** - ROI: 5.0
   - 工作量小（3天）
   - 应用广泛（管网、控制）
   - 技术成熟

2. **水轮机** - ROI: 4.5
   - 水电核心设备
   - 技术含量高
   - 开拓新应用领域

3. **泵特性** - ROI: 4.2
   - 完善现有功能
   - 提升仿真精度
   - 工作量适中

### 中等价值元件（ROI: 2-4）

- 调压井 - ROI: 3.5
- 厂房系统 - ROI: 3.2
- 溢洪道 - ROI: 2.8

### 低价值元件（ROI < 2）

- 渐变段 - ROI: 1.5
- 跌水 - ROI: 1.2

---

## ⚠️ 风险与缓解

### 技术风险

| 风险 | 概率 | 影响 | 缓解措施 |
|-----|-----|-----|---------|
| 水轮机特性曲线数据不足 | 中 | 高 | 使用简化解析函数；文献调研 |
| 调压井振荡求解不稳定 | 低 | 中 | 采用刚性ODE求解器 |
| 阀门特性多样性 | 低 | 低 | 提供3种典型特性 |

### 进度风险

| 风险 | 缓解措施 |
|-----|---------|
| 水轮机开发超时 | 预留20%缓冲时间 |
| 测试不充分 | 并行开发测试代码 |

---

## 📈 成功指标（KPI）

### 功能完整性

- ✅ 10种以上水力元件
- ✅ 覆盖明渠、有压、控制
- ✅ 支持恒定流和非恒定流

### 性能指标

- ✅ 水电站仿真：单次运行 < 60s
- ✅ 管网仿真：100节点 < 10s
- ✅ 精度：流量守恒 < 0.5%

### 文档质量

- ✅ 每个元件有详细文档
- ✅ 至少5个完整工程案例
- ✅ API文档覆盖率 100%

---

## 🚀 快速启动

### 本周立即开始

1. **创建开发分支**
   ```bash
   git checkout -b feature/complete-hydraulic-components
   ```

2. **实现阀门类**（第1优先级）
   - 创建 `physics/valve.py`
   - 实现 `Valve`, `GateValve`, `ButterflyValve`, `BallValve`
   - 编写测试 `tests/test_valve.py`

3. **改进泵模型**（第2优先级）
   - 修改 `physics/pump.py`
   - 添加特性曲线
   - 验证测试

### 第一周目标

- ✅ 阀门完整实现
- ✅ 泵特性曲线完善
- ✅ 通过所有测试

---

## 📚 参考资料

### 水力学

1. Chow, V. T. (1959). *Open-Channel Hydraulics*
2. Wylie, E. B., & Streeter, V. L. (1993). *Fluid Transients in Systems*

### 水轮机

3. 刘大凯 (2013). 《水轮机》（第4版）
4. IEC 60193: *Hydraulic turbines, storage pumps and pump-turbines - Model acceptance tests*

### 水电站

5. Raabe, J. (1985). *Hydro Power - The Design, Use, and Function of Hydromechanical, Hydraulic, and Electrical Equipment*
6. Gulliver, J. S., & Arndt, R. E. (1991). *Hydropower Engineering Handbook*

### 管网分析

7. Cross, H. (1936). *Analysis of Flow in Networks of Conduits or Conductors*
8. Todini, E., & Pilati, S. (1988). *A gradient algorithm for the analysis of pipe networks*

---

## 🏆 总结

本开发计划旨在将HydroClaude打造成**功能完整、性能优异**的一维水力学仿真平台，涵盖：

✅ **明渠水力学**：非恒定流、闸控、灌溉渠系
✅ **有压管道**：水击、管网、供水系统
✅ **水电工程**：水轮机、调压井、厂房系统
✅ **控制优化**：调速器、优化调度、智能控制

**核心优势**：
1. 完整的元件库（10+种）
2. 高精度数值方法（Newton法，100-500x加速）
3. 工程应用导向（真实案例）
4. 开源开放（社区驱动）

**第一步**：立即实现阀门和泵特性曲线！

---

*本计划由Claude AI制定 | 2025-10-22*
*规划期：2025年11月 - 2026年6月（18周）*
*版本：v1.0*
