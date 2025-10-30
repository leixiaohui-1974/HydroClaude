# Stage 5 开发计划 - 有压管网系统
# Stage 5 Development Plan - Pressurized Pipe Network System

**版本 Version**: 1.0.0
**日期 Date**: 2025-10-30
**状态 Status**: 🚀 准备启动
**作者 Author**: HydroClaude Team

---

## 📋 执行摘要 Executive Summary

Stage 5 专注于**有压管网系统开发**，将HydroClaude从明渠水力学扩展到有压管道，填补当前最大的功能缺口，实现与商业软件（EPANET, MIKE URBAN）对标的能力。

### 前置条件 Prerequisites
- ✅ Stage 1: 核心数值方法 - 95%完成
- ✅ Stage 2: 基础求解器 - 100%完成
- ✅ Stage 3: 河网拓扑 - 100%完成
- ✅ Stage 4: 高级断面和建筑物 - 100%完成

### 核心目标 Core Objectives
1. **有压管道水力计算** - 稳态管网平差
2. **明满流转换** - 管道自动切换流态
3. **水锤分析** - 瞬变流模拟
4. **管网拓扑分析** - 复杂管网求解

---

## 🎯 总体目标 Overall Goals

### P0 目标（必须完成 Must-Have）

| 目标 | 描述 | 优先级 | 预计工期 |
|------|------|--------|---------|
| 有压管道类 | 单管道水力计算 | 🔴 P0 | 3天 |
| 管网节点类 | 节点连接和存储 | 🔴 P0 | 2天 |
| Hardy Cross法 | 管网平差求解器 | 🔴 P0 | 5天 |
| Newton-Raphson法 | 替代求解器 | 🔴 P0 | 3天 |
| 基础验证案例 | 2-3个经典案例 | 🔴 P0 | 3天 |

**P0小计**: 16天（~3周）

### P1 目标（重要 Important）

| 目标 | 描述 | 优先级 | 预计工期 |
|------|------|--------|---------|
| 明满流转换 | Preissmann Slot法 | 🟡 P1 | 5天 |
| 阀门系统 | PRV, PSV, FCV等7种 | 🟡 P1 | 5天 |
| 水锤基础 | MOC特征线法 | 🟡 P1 | 7天 |
| 高级验证案例 | 实际工程案例 | 🟡 P1 | 3天 |

**P1小计**: 20天（~4周）

### P2 目标（可选 Nice-to-Have）

| 目标 | 描述 | 优先级 | 预计工期 |
|------|------|--------|---------|
| 水泵特性曲线 | 多工况点运行 | 🟢 P2 | 3天 |
| 水箱/水塔 | 储能设施 | 🟢 P2 | 2天 |
| 管网优化 | 管径优化设计 | 🟢 P2 | 5天 |
| 实时调度 | SCADA集成 | 🟢 P2 | 7天 |

**P2小计**: 17天（~3周）

---

## 📊 阶段划分 Phase Breakdown

### Phase 5.1: 单管道水力计算 (第1周 Week 1)

**目标 Goal**: 实现单根有压管道的水力计算基础

#### Task 5.1.1: PressurePipe类 🔴 P0

**实施内容 Implementation**:

```python
# network/pressure_pipe.py

import numpy as np
from typing import Optional, Dict, Literal

class PressurePipe:
    """
    有压管道类 - Pressurized Pipe

    支持：
    - Darcy-Weisbach 公式
    - Hazen-Williams 公式
    - Colebrook-White 公式（摩阻系数）
    - 局部损失系数
    """

    def __init__(
        self,
        pipe_id: str,
        diameter: float,  # 管径 (m)
        length: float,  # 长度 (m)
        roughness: float,  # 粗糙度 (m) for Darcy-Weisbach
        formula: Literal["darcy", "hazen"] = "darcy",
        K_minor: float = 0.0  # 局部损失系数
    ):
        """
        初始化有压管道

        Args:
            pipe_id: 管道标识
            diameter: 内径 (m)
            length: 管道长度 (m)
            roughness: 绝对粗糙度 (m)，典型值：
                - 新铸铁管: 0.00026 m
                - 旧铸铁管: 0.0015 m
                - 混凝土管: 0.0003-0.003 m
                - PVC管: 0.000015 m
            formula: 水头损失公式 'darcy' 或 'hazen'
            K_minor: 局部损失系数之和
        """
        self.pipe_id = pipe_id
        self.D = diameter
        self.L = length
        self.epsilon = roughness
        self.formula = formula
        self.K_minor = K_minor

        # 计算属性
        self.A = np.pi * (self.D / 2.0)**2  # 断面积

    def reynolds_number(self, Q: float, nu: float = 1.0e-6) -> float:
        """
        计算雷诺数 Reynolds number

        Re = V*D/ν = (4*Q)/(π*D*ν)

        Args:
            Q: 流量 (m³/s)
            nu: 运动粘度 (m²/s)，默认1e-6（20°C水）

        Returns:
            雷诺数（无量纲）
        """
        if Q == 0:
            return 0.0
        V = Q / self.A
        Re = V * self.D / nu
        return Re

    def friction_factor_colebrook(self, Q: float, nu: float = 1.0e-6) -> float:
        """
        Colebrook-White公式计算摩阻系数

        1/√f = -2*log₁₀(ε/(3.7*D) + 2.51/(Re*√f))

        采用迭代求解（Swamee-Jain显式近似作为初值）

        Args:
            Q: 流量 (m³/s)
            nu: 运动粘度 (m²/s)

        Returns:
            Darcy-Weisbach摩阻系数 f
        """
        Re = self.reynolds_number(Q, nu)

        if Re < 2000:
            # 层流: f = 64/Re
            return 64.0 / Re if Re > 0 else 0.0

        # 湍流: Colebrook-White迭代
        # 初值: Swamee-Jain公式
        rel_roughness = self.epsilon / self.D
        f = 0.25 / (np.log10(rel_roughness/3.7 + 5.74/Re**0.9))**2

        # 迭代求解Colebrook方程
        for _ in range(10):
            f_new = 1.0 / (-2.0 * np.log10(rel_roughness/3.7 + 2.51/(Re*np.sqrt(f))))**2
            if abs(f_new - f) < 1e-6:
                break
            f = f_new

        return f

    def head_loss_darcy(self, Q: float, nu: float = 1.0e-6) -> float:
        """
        Darcy-Weisbach公式计算水头损失

        h_f = f * (L/D) * (V²/2g) + K * (V²/2g)

        Args:
            Q: 流量 (m³/s)
            nu: 运动粘度 (m²/s)

        Returns:
            水头损失 (m)
        """
        if Q == 0:
            return 0.0

        g = 9.81  # m/s²
        V = Q / self.A
        f = self.friction_factor_colebrook(Q, nu)

        # 沿程损失
        h_friction = f * (self.L / self.D) * (V**2 / (2*g))

        # 局部损失
        h_minor = self.K_minor * (V**2 / (2*g))

        return h_friction + h_minor

    def head_loss_hazen(self, Q: float, C: float = 130.0) -> float:
        """
        Hazen-Williams公式计算水头损失

        h_f = 10.67 * L * Q^1.852 / (C^1.852 * D^4.87)

        Args:
            Q: 流量 (m³/s)
            C: Hazen-Williams系数，典型值：
                - 新铸铁管: 130
                - 旧铸铁管: 100
                - 混凝土管: 120-140
                - PVC管: 150

        Returns:
            水头损失 (m)
        """
        if Q == 0:
            return 0.0

        h_f = 10.67 * self.L * (Q**1.852) / (C**1.852 * self.D**4.87)

        # 局部损失（用简化公式）
        V = Q / self.A
        g = 9.81
        h_minor = self.K_minor * (V**2 / (2*g))

        return h_f + h_minor

    def head_loss(self, Q: float, **kwargs) -> float:
        """
        计算水头损失（根据公式类型自动选择）

        Args:
            Q: 流量 (m³/s)
            **kwargs: 其他参数（nu for Darcy, C for Hazen）

        Returns:
            水头损失 (m)
        """
        if self.formula == "darcy":
            nu = kwargs.get('nu', 1.0e-6)
            return self.head_loss_darcy(Q, nu)
        else:  # hazen
            C = kwargs.get('C', 130.0)
            return self.head_loss_hazen(Q, C)

    def flow_from_head_loss(
        self,
        h_loss: float,
        tol: float = 1e-6,
        max_iter: int = 50
    ) -> float:
        """
        根据水头损失反算流量（牛顿法）

        求解: h_loss = f(Q)

        Args:
            h_loss: 给定水头损失 (m)
            tol: 收敛容差
            max_iter: 最大迭代次数

        Returns:
            流量 (m³/s)
        """
        # 初值估计（假设线性关系）
        Q = np.sqrt(2 * 9.81 * h_loss * self.A * self.D / self.L)

        for i in range(max_iter):
            h_calc = self.head_loss(Q)
            residual = h_calc - h_loss

            if abs(residual) < tol:
                return Q

            # 数值导数
            dQ = Q * 1e-6
            h_plus = self.head_loss(Q + dQ)
            dh_dQ = (h_plus - h_calc) / dQ

            if abs(dh_dQ) < 1e-12:
                break

            # 牛顿更新
            Q_new = Q - residual / dh_dQ

            # 确保正值
            if Q_new < 0:
                Q_new = Q * 0.5

            Q = Q_new

        return Q

    def properties(self, Q: float) -> Dict[str, float]:
        """
        计算管道所有水力属性

        Args:
            Q: 流量 (m³/s)

        Returns:
            属性字典
        """
        V = Q / self.A if Q != 0 else 0.0
        Re = self.reynolds_number(Q)
        f = self.friction_factor_colebrook(Q)
        h_loss = self.head_loss(Q)

        return {
            'Q': Q,
            'V': V,
            'Re': Re,
            'f': f,
            'h_loss': h_loss,
            'regime': 'laminar' if Re < 2000 else 'turbulent'
        }

    def __repr__(self) -> str:
        return (f"PressurePipe(id='{self.pipe_id}', D={self.D:.3f}m, "
                f"L={self.L:.1f}m, ε={self.epsilon:.6f}m)")


# 便捷构造函数
def create_pressure_pipe(
    pipe_id: str,
    diameter: float,
    length: float,
    material: str = "cast_iron",
    formula: str = "darcy"
) -> PressurePipe:
    """
    便捷创建管道（根据材料自动设置粗糙度）

    Args:
        pipe_id: 管道ID
        diameter: 管径 (m)
        length: 长度 (m)
        material: 材料类型，支持：
            - 'cast_iron_new': 新铸铁管 (ε=0.00026m)
            - 'cast_iron_old': 旧铸铁管 (ε=0.0015m)
            - 'concrete': 混凝土管 (ε=0.001m)
            - 'pvc': PVC管 (ε=0.000015m)
            - 'steel': 钢管 (ε=0.000046m)
        formula: 'darcy' 或 'hazen'

    Returns:
        PressurePipe实例
    """
    roughness_db = {
        'cast_iron_new': 0.00026,
        'cast_iron_old': 0.0015,
        'concrete': 0.001,
        'pvc': 0.000015,
        'steel': 0.000046
    }

    epsilon = roughness_db.get(material, 0.001)

    return PressurePipe(
        pipe_id=pipe_id,
        diameter=diameter,
        length=length,
        roughness=epsilon,
        formula=formula
    )


# Hazen-Williams系数数据库
HAZEN_WILLIAMS_C = {
    'cast_iron_new': 130,
    'cast_iron_old': 100,
    'concrete_good': 140,
    'concrete_average': 120,
    'pvc': 150,
    'steel_new': 140,
    'steel_old': 110
}
```

**测试文件 Test File**: `tests/test_network/test_pressure_pipe.py`

**验证目标 Validation Goals**:
- ✅ 摩阻系数计算精度 < 1%
- ✅ 水头损失与解析解误差 < 2%
- ✅ 雷诺数转捩判断正确
- ✅ 流量反算收敛稳定

**工期 Duration**: 3天

---

#### Task 5.1.2: 单管道验证案例 🔴 P0

**实施内容**:

创建经典验证案例验证PressurePipe类：

1. **Hardy Cross原始算例** (1936)
   - 简单管道水头损失计算
   - 对比解析解

2. **Moody图验证**
   - 不同Re和ε/D下的f值
   - 对比Moody图曲线

3. **实际工程管道**
   - 某城市供水主管道
   - 对比实测数据

**验证文件**: `validation_cases/pressure_network/single_pipe_validation.py`

**工期**: 2天

---

### Phase 5.2: 管网节点和拓扑 (第2周 Week 2)

**目标**: 实现管网节点和拓扑连接

#### Task 5.2.1: NetworkNode类 🔴 P0

**实施内容**:

```python
# network/network_node.py

class NetworkNode:
    """
    管网节点类

    类型:
    - Junction: 汇流节点
    - Reservoir: 水库（恒定水头）
    - Tank: 水箱（变水头）
    - Valve: 阀门节点
    - Pump: 水泵节点
    """

    def __init__(
        self,
        node_id: str,
        node_type: Literal["junction", "reservoir", "tank", "valve", "pump"],
        elevation: float,
        demand: float = 0.0,
        initial_head: Optional[float] = None
    ):
        """
        初始化节点

        Args:
            node_id: 节点标识
            node_type: 节点类型
            elevation: 地面高程 (m)
            demand: 用水量 (m³/s)，正值为取水，负值为入流
            initial_head: 初始水头 (m)，用于非稳态
        """
        pass

    def continuity_equation(self, Q_in: List[float], Q_out: List[float]) -> float:
        """
        节点连续性方程

        ΣQ_in - ΣQ_out - demand = 0
        """
        pass
```

**工期**: 2天

---

#### Task 5.2.2: NetworkTopology类 🔴 P0

**实施内容**:

```python
# network/network_topology.py

class NetworkTopology:
    """
    管网拓扑结构分析

    功能:
    - 节点-管道连接关系
    - 回路识别
    - 树状结构分析
    - 路径搜索
    """

    def __init__(self):
        self.nodes: Dict[str, NetworkNode] = {}
        self.pipes: Dict[str, PressurePipe] = {}
        self.connectivity: Dict[str, List[str]] = {}  # 邻接表

    def add_node(self, node: NetworkNode):
        """添加节点"""
        pass

    def add_pipe(self, pipe: PressurePipe, from_node: str, to_node: str):
        """添加管道并建立连接"""
        pass

    def find_loops(self) -> List[List[str]]:
        """
        识别所有独立回路

        使用深度优先搜索(DFS)找出所有基本回路

        Returns:
            回路列表，每个回路是节点ID列表
        """
        pass

    def incidence_matrix(self) -> np.ndarray:
        """
        构造关联矩阵

        A[i,j] = +1 if pipe j flows into node i
                 -1 if pipe j flows out of node i
                  0 otherwise

        Returns:
            关联矩阵 (n_nodes × n_pipes)
        """
        pass
```

**工期**: 3天

---

### Phase 5.3: Hardy Cross法管网平差 (第3周 Week 3)

**目标**: 实现经典Hardy Cross迭代法

#### Task 5.3.1: HardyCrossSolver类 🔴 P0

**实施内容**:

```python
# solvers/hardy_cross_solver.py

class HardyCrossSolver:
    """
    Hardy Cross管网平差求解器

    原理:
    1. 假设各管段初始流量
    2. 对每个回路应用能量守恒: Σh_loss = 0
    3. 迭代修正流量直到收敛

    修正公式:
    ΔQ = -Σh / (n * Σ(h/Q))

    其中 h = r * Q^n (r为阻力系数，n=2 for Darcy)
    """

    def __init__(self, network: NetworkTopology, max_iter: int = 100, tol: float = 1e-6):
        self.network = network
        self.max_iter = max_iter
        self.tol = tol

    def solve(self) -> Dict[str, float]:
        """
        求解稳态管网流量分布

        Returns:
            {pipe_id: Q} 流量分布字典
        """
        # 1. 初始流量分配（满足连续性）
        Q = self._initialize_flows()

        # 2. 识别回路
        loops = self.network.find_loops()

        # 3. Hardy Cross迭代
        for iteration in range(self.max_iter):
            max_correction = 0.0

            for loop in loops:
                # 计算回路水头损失代数和
                delta_h = 0.0
                delta_h_derivative = 0.0

                for pipe_id in loop:
                    pipe = self.network.pipes[pipe_id]
                    q = Q[pipe_id]
                    h = pipe.head_loss(abs(q))

                    # 考虑流向
                    if q < 0:
                        h = -h

                    delta_h += h
                    delta_h_derivative += 2 * h / q if q != 0 else 0

                # 流量修正
                dQ = -delta_h / delta_h_derivative if delta_h_derivative != 0 else 0

                # 应用修正到回路所有管道
                for pipe_id in loop:
                    Q[pipe_id] += dQ

                max_correction = max(max_correction, abs(dQ))

            # 检查收敛
            if max_correction < self.tol:
                print(f"Hardy Cross收敛，迭代{iteration+1}次")
                return Q

        raise RuntimeError(f"Hardy Cross未收敛，最大修正量{max_correction}")

    def _initialize_flows(self) -> Dict[str, float]:
        """初始流量分配（连续性方程）"""
        # 简单策略：平均分配
        pass
```

**工期**: 5天

---

#### Task 5.3.2: Hardy Cross验证案例 🔴 P0

经典算例：

1. **Two-Loop Network** (Hardy Cross 1936原文)
   - 2个回路，7根管道
   - 手算对比

2. **Three-Loop Network**
   - 3个回路，复杂连接
   - 对比EPANET结果

**验证文件**: `validation_cases/pressure_network/hardy_cross_validation.py`

**工期**: 2天

---

### Phase 5.4: Newton-Raphson全局法 (第4周 Week 4)

**目标**: 实现更快速的Newton-Raphson法

#### Task 5.4.1: NewtonRaphsonSolver类 🔴 P0

**实施内容**:

```python
# solvers/newton_raphson_network_solver.py

class NewtonRaphsonNetworkSolver:
    """
    Newton-Raphson管网求解器

    优势:
    - 收敛速度快于Hardy Cross
    - 处理复杂边界条件能力强
    - 可扩展到水质模拟

    方程组:
    F(Q, H) = 0
    其中包括:
    - 能量方程: H_i - H_j = h_loss(Q_ij)
    - 连续性方程: ΣQ_in - ΣQ_out - demand_i = 0

    Jacobian矩阵:
    J = [∂F/∂Q, ∂F/∂H]

    迭代:
    X_{k+1} = X_k - J^{-1} * F(X_k)
    """

    def __init__(self, network: NetworkTopology, max_iter: int = 50, tol: float = 1e-6):
        self.network = network
        self.max_iter = max_iter
        self.tol = tol

    def build_equations(self, Q: np.ndarray, H: np.ndarray) -> np.ndarray:
        """
        构造方程组 F(Q,H) = 0

        Returns:
            残差向量
        """
        pass

    def build_jacobian(self, Q: np.ndarray, H: np.ndarray) -> np.ndarray:
        """
        构造Jacobian矩阵

        Returns:
            Jacobian矩阵
        """
        pass

    def solve(self) -> Tuple[Dict[str, float], Dict[str, float]]:
        """
        求解管网流量和水头

        Returns:
            (流量字典, 水头字典)
        """
        pass
```

**工期**: 3天

---

### Phase 5.5: 明满流转换 (第5-6周 Weeks 5-6) 🟡 P1

**目标**: 实现管道明流/压力流自动切换

#### Task 5.5.1: Preissmann Slot法 🟡 P1

**实施内容**:

```python
# network/dual_flow_pipe.py

class DualFlowPipe:
    """
    可明满流转换的管道

    方法: Preissmann Slot（虚拟狭缝法）

    原理:
    在管顶添加虚拟狭缝，使满管流也能用明渠方程求解

    狭缝宽度:
    b_slot = (π*D²/4) / (g * Δt * c)

    优点:
    - 方程统一，无需切换
    - 连续性好
    - 稳定性高
    """

    def __init__(self, diameter: float, length: float, roughness: float):
        self.D = diameter
        self.L = length
        self.n = roughness

        # Preissmann Slot参数
        self.slot_width = self._calculate_slot_width()

    def flow_area(self, h: float) -> float:
        """
        计算过水面积（考虑虚拟狭缝）

        Args:
            h: 水深 (m)

        Returns:
            面积 (m²)
        """
        if h <= self.D:
            # 明流：圆管部分充满
            return self._circular_area(h)
        else:
            # 满流：圆管全满 + 狭缝
            A_pipe = np.pi * (self.D / 2)**2
            A_slot = self.slot_width * (h - self.D)
            return A_pipe + A_slot

    def _circular_area(self, h: float) -> float:
        """圆管部分充满面积"""
        # A = (D²/4) * (θ - sin(θ))
        # 其中 θ = 2*arccos(1 - 2h/D)
        pass
```

**工期**: 5天

---

### Phase 5.6: 水锤分析基础 (第7周 Week 7) 🟡 P1

**目标**: 实现瞬变流（水锤）模拟

#### Task 5.6.1: MOC水锤求解器 🟡 P1

**实施内容**:

```python
# solvers/water_hammer_moc_solver.py

class WaterHammerMOCSolver:
    """
    特征线法(MOC)水锤求解器

    控制方程:
    连续性: ∂H/∂t + (a²/gA) * ∂Q/∂x = 0
    动量:   ∂Q/∂t + gA * ∂H/∂x + (f*Q*|Q|)/(2DA) = 0

    其中 a = 波速 = √(K/ρ / (1 + K*D/(E*e)))

    特征线:
    C⁺: dx/dt = +a
    C⁻: dx/dt = -a

    相容方程:
    C⁺: H_P + B*Q_P = H_A + B*Q_A - R*Q_A*|Q_A|
    C⁻: H_P - B*Q_P = H_B - B*Q_B + R*Q_B*|Q_B|

    其中:
    B = a / (g*A)
    R = f*Δx / (2*D*A*g)
    """

    def __init__(
        self,
        pipe: PressurePipe,
        wave_speed: float,
        dx: float,
        dt: float
    ):
        self.pipe = pipe
        self.a = wave_speed
        self.dx = dx
        self.dt = dt

        # 检查CFL条件
        self.cfl = self.a * self.dt / self.dx
        if self.cfl > 1.0:
            raise ValueError(f"违反CFL条件: CFL={self.cfl:.2f} > 1.0")

    def solve_transient(
        self,
        initial_Q: float,
        initial_H_up: float,
        boundary_condition: Callable,
        duration: float
    ) -> Dict[str, np.ndarray]:
        """
        求解瞬变流过程

        Args:
            initial_Q: 初始流量 (m³/s)
            initial_H_up: 上游初始水头 (m)
            boundary_condition: 边界条件函数 f(t) -> (Q or H)
            duration: 模拟时长 (s)

        Returns:
            {
                't': 时间数组,
                'x': 空间坐标数组,
                'Q': 流量场 (t, x),
                'H': 水头场 (t, x),
                'p': 压力场 (t, x)
            }
        """
        pass

    def wave_speed(self, K: float = 2.1e9, E: float = 2e11, e: float = 0.01) -> float:
        """
        计算水锤波速

        a = √(K/ρ / (1 + K*D/(E*e)))

        Args:
            K: 水的体积弹性模量 (Pa)，默认2.1×10⁹
            E: 管材弹性模量 (Pa)，默认2×10¹¹（铸铁）
            e: 管壁厚度 (m)，默认0.01

        Returns:
            波速 (m/s)
        """
        rho = 1000.0  # kg/m³
        a = np.sqrt((K / rho) / (1 + K * self.pipe.D / (E * e)))
        return a
```

**工期**: 7天

---

## 📋 交付物清单 Deliverables

### 代码模块 Code Modules

| 模块 | 文件路径 | 功能 | 优先级 |
|------|---------|------|--------|
| PressurePipe | `network/pressure_pipe.py` | 有压管道类 | P0 |
| NetworkNode | `network/network_node.py` | 管网节点类 | P0 |
| NetworkTopology | `network/network_topology.py` | 拓扑分析 | P0 |
| HardyCrossSolver | `solvers/hardy_cross_solver.py` | HC求解器 | P0 |
| NewtonRaphsonSolver | `solvers/newton_raphson_network_solver.py` | NR求解器 | P0 |
| DualFlowPipe | `network/dual_flow_pipe.py` | 明满流管道 | P1 |
| WaterHammerSolver | `solvers/water_hammer_moc_solver.py` | 水锤求解器 | P1 |

### 测试文件 Test Files

| 测试 | 文件路径 | 覆盖率目标 |
|------|---------|-----------|
| PressurePipe测试 | `tests/test_network/test_pressure_pipe.py` | >95% |
| NetworkNode测试 | `tests/test_network/test_network_node.py` | >90% |
| HardyCross测试 | `tests/test_solvers/test_hardy_cross.py` | >90% |
| NewtonRaphson测试 | `tests/test_solvers/test_newton_raphson_network.py` | >90% |

### 验证案例 Validation Cases

| 案例 | 文件路径 | 对标 |
|------|---------|------|
| 单管水头损失 | `validation_cases/pressure_network/single_pipe.py` | 解析解 |
| Hardy Cross两回路 | `validation_cases/pressure_network/hardy_cross_2loop.py` | 原文算例 |
| EPANET对比 | `validation_cases/pressure_network/epanet_benchmark.py` | EPANET |
| 水锤算例 | `validation_cases/pressure_network/water_hammer.py` | 经典算例 |

### 文档 Documentation

| 文档 | 文件路径 | 内容 |
|------|---------|------|
| API文档 | `docs/api/pressure_network.md` | 类和方法说明 |
| 理论手册 | `docs/theory/pipe_hydraulics.md` | 公式推导 |
| 用户指南 | `docs/user_guide/pipe_network_tutorial.md` | 使用教程 |

---

## 🎯 验收标准 Acceptance Criteria

### P0 功能验收

| 功能 | 验收标准 | 测试方法 |
|------|---------|---------|
| 单管计算 | 摩阻系数误差<1%，水头损失误差<2% | 对比Moody图和解析解 |
| Hardy Cross | 收敛稳定，2回路算例与手算一致 | 经典算例对比 |
| Newton-Raphson | 收敛速度>Hardy Cross，结果一致 | 性能对比 |
| 单元测试 | 所有P0模块测试通过率>95% | pytest |

### P1 功能验收

| 功能 | 验收标准 | 测试方法 |
|------|---------|---------|
| 明满流切换 | 切换平滑无跳跃，水量守恒 | 数值实验 |
| 水锤分析 | 波速计算准确，压力峰值合理 | 经典算例对比 |

---

## 📊 工期和资源估算

### 总工期估算

| 阶段 | P0任务 | P1任务 | P2任务 | 小计 |
|------|--------|--------|--------|------|
| Phase 5.1 | 5天 | - | - | 5天 |
| Phase 5.2 | 5天 | - | - | 5天 |
| Phase 5.3 | 7天 | - | - | 7天 |
| Phase 5.4 | 3天 | - | - | 3天 |
| Phase 5.5 | - | 5天 | - | 5天 |
| Phase 5.6 | - | 7天 | - | 7天 |
| 测试和文档 | 3天 | 2天 | - | 5天 |
| **总计** | **23天** | **14天** | **0天** | **37天** |

**按优先级分组**:
- **P0核心**: 23天（~4.5周）
- **P1重要**: 14天（~2.5周）
- **P2可选**: 待定

**建议开发路径**:
- **最小可行产品 (MVP)**: 完成P0任务，4.5周
- **完整版本**: 完成P0+P1任务，7周
- **增强版本**: 完成全部任务，10周

---

## 🚀 开发里程碑

| 里程碑 | 时间点 | 交付内容 | 成功标准 |
|--------|--------|---------|---------|
| **M1: 单管计算** | Week 1 | PressurePipe类 + 测试 | 95%测试通过 |
| **M2: 网络拓扑** | Week 2 | NetworkNode + Topology | 拓扑分析正确 |
| **M3: Hardy Cross** | Week 3 | HC求解器 + 验证 | 2回路算例通过 |
| **M4: Newton-Raphson** | Week 4 | NR求解器 + 对比 | 比HC快2倍+ |
| **M5: P0完成** | Week 4.5 | 所有P0功能 | 全部验收标准 |
| **M6: 明满流** | Week 6 | DualFlowPipe | 切换平滑 |
| **M7: 水锤** | Week 7 | MOC求解器 | 经典算例对比 |
| **M8: Stage 5完成** | Week 7+ | 全部功能 | 100%交付 |

---

## 🎓 技术难点和风险

### 高风险项目

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|---------|
| **Hardy Cross收敛问题** | 高 | 中 | 添加松弛因子，改进初值 |
| **明满流切换不稳定** | 高 | 中 | 使用Preissmann Slot平滑过渡 |
| **水锤数值震荡** | 中 | 高 | 严格遵守CFL条件，添加阻尼 |
| **大型管网性能** | 中 | 中 | 使用稀疏矩阵，优化算法 |

### 技术难点攻克策略

1. **Hardy Cross收敛性**:
   - 参考Jeppson (1976) 改进算法
   - 添加欠松弛因子α ∈ [0.5, 1.0]
   - 使用更好的初始流量分配

2. **明满流切换**:
   - 先实现Preissmann Slot（稳定）
   - 备选方案：TPA法（两阶段算法）
   - 参考SWMM 5源代码

3. **水锤模拟**:
   - 严格的CFL检查: a*Δt/Δx ≤ 1
   - 添加人工粘性抑制数值震荡
   - 参考Wylie & Streeter经典教材

---

## 📚 参考资料

### 经典教材
1. **Pipe Flow Analysis** - P.Jeppson (1976)
2. **Fluid Transients in Systems** - Wylie & Streeter (1993)
3. **Water Distribution Systems Handbook** - Mays (2000)

### 商业软件
1. **EPANET** - EPA开源软件，参考实现
2. **MIKE URBAN** - DHI商业软件
3. **InfoWorks ICM** - Autodesk

### 论文
1. Hardy Cross (1936) - "Analysis of Flow in Networks of Conduits or Conductors"
2. Colebrook (1939) - "Turbulent Flow in Pipes"
3. Preissmann & Cunge (1961) - "Slot Model for Surcharge Flow"

---

## ✅ 下一步行动

### 立即开始 (本周)

1. **创建目录结构**:
   ```bash
   mkdir -p network/pressure
   mkdir -p solvers/pipe_network
   mkdir -p tests/test_network/pressure
   mkdir -p validation_cases/pressure_network
   ```

2. **开始Task 5.1.1**: 实现PressurePipe类
   - 创建 `network/pressure_pipe.py`
   - 实现Darcy-Weisbach公式
   - 实现Colebrook迭代

3. **编写单元测试**:
   - 创建 `tests/test_network/test_pressure_pipe.py`
   - 测试摩阻系数计算
   - 测试水头损失计算

### 第一周目标

- ✅ 完成PressurePipe类
- ✅ 单元测试通过率>95%
- ✅ 完成单管验证案例

---

**计划制定人**: HydroClaude Team
**计划批准**: 待定
**计划开始日期**: 2025-10-30
**预计完成日期**: 2025-12-20 (P0+P1)

**状态**: ✅ 计划完成，等待启动批准

---

**修订历史**:
- v1.0.0 (2025-10-30): 初始版本，完整规划Stage 5
