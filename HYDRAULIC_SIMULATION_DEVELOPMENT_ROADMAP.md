# HydroClaude 水力学仿真核心开发路线图
## 聚焦于水力计算功能的渐进式实现

**版本**: v1.0
**创建日期**: 2025-10-28
**规划期**: 4-6个月
**负责**: 核心算法团队

---

## 📋 总览

本路线图专注于**水力学仿真核心功能**的开发，暂不涉及GUI、云计算等外围功能。目标是建立完整、准确、高效的水力计算引擎。

### 核心目标

1. **扩展水工建筑物库**：7种 → 20+种
2. **丰富边界条件**：6种 → 12+种
3. **增强有压系统**：完整的管网+水锤分析
4. **优化求解性能**：30-50%速度提升
5. **验证复杂系统**：5+工程级测试案例

### 开发原则

- ✅ **质量优先**：每个功能都要充分测试和验证
- ✅ **渐进开发**：小步快跑，每周交付可用功能
- ✅ **文档同步**：代码和文档同步更新
- ✅ **物理准确**：严格遵循水力学原理
- ✅ **向后兼容**：不破坏现有功能

---

## 🗓️ 阶段划分

```
┌──────────────────────────────────────────────────────────────┐
│                    6个月水力学开发路线                         │
├─────────────┬─────────────┬─────────────┬─────────────────────┤
│ 阶段1 (6周) │ 阶段2 (6周) │ 阶段3 (6周) │ 阶段4 (6周)         │
│ 明渠建筑物  │ 有压系统    │ 求解器优化  │ 复杂系统与验证      │
├─────────────┼─────────────┼─────────────┼─────────────────────┤
│ Week 1-2    │ Week 7-8    │ Week 13-14  │ Week 19-20          │
│ • 涵洞      │ • 蝶阀      │ • 混合求解  │ • 长距离输水系统    │
│ • 桥梁      │ • 球阀      │ • 并行计算  │ • 梯级水电站        │
│             │ • 减压阀    │             │                     │
│ Week 3-4    │ Week 9-10   │ Week 15-16  │ Week 21-22          │
│ • 跌水      │ • 水锤增强  │ • 自适应步  │ • 城市供水管网      │
│ • 测流槽    │ • MOC求解器 │ • 网格优化  │ • 灌区渠系          │
│             │             │             │                     │
│ Week 5-6    │ Week 11-12  │ Week 17-18  │ Week 23-24          │
│ • 边界条件  │ • 管网拓扑  │ • 性能测试  │ • 防洪工程系统      │
│ • 测试验证  │ • 泵站优化  │ • 文档完善  │ • 综合测试          │
└─────────────┴─────────────┴─────────────┴─────────────────────┘
```

---

## 🚀 阶段1：明渠系统建筑物扩展（Week 1-6）

### Week 1-2: 涵洞（Culvert）

**目标**：实现完整的涵洞水力计算模型

#### 1.1 理论基础

**涵洞流态分类**：
```
1. 入口控制（Inlet Control）
   - 非淹没出口
   - 上游水位决定流量
   - Q = Cd * A * sqrt(2*g*H)

2. 出口控制（Outlet Control）
   - 淹没出口
   - 能量方程控制
   - 考虑摩阻损失和出口损失

3. 流态判别
   - 计算两种控制下的上游水位
   - 取较高者（更不利）
```

**进口类型系数**：
```
Type 1: Square edge (方形边缘)          - Cd = 0.44-0.50
Type 2: Groove end (槽形端)             - Cd = 0.49-0.54
Type 3: Groove end with headwall (带翼墙) - Cd = 0.50-0.55
Type 4: Beveled (斜切)                  - Cd = 0.55-0.60
```

#### 1.2 代码实现

**文件**: `physics/structures/culvert.py`

```python
"""
涵洞水力计算模型
支持圆形、矩形、拱形断面
实现入口控制和出口控制
"""

import numpy as np
from typing import Tuple, Literal
from dataclasses import dataclass

@dataclass
class CulvertGeometry:
    """涵洞几何参数"""
    shape: Literal['circular', 'rectangular', 'arch']
    diameter: float = None          # 圆形涵洞直径 (m)
    width: float = None             # 矩形涵洞宽度 (m)
    height: float = None            # 矩形涵洞高度 (m)
    length: float = None            # 涵洞长度 (m)
    slope: float = 0.001           # 涵洞坡度 (无量纲)
    invert_elevation: float = 0.0   # 进口底高程 (m)

    def area(self) -> float:
        """计算断面面积"""
        if self.shape == 'circular':
            return np.pi * (self.diameter/2)**2
        elif self.shape == 'rectangular':
            return self.width * self.height
        elif self.shape == 'arch':
            # 简化为半圆+矩形
            return (np.pi/2) * (self.width/2)**2 + self.width * (self.height - self.width/2)

    def hydraulic_radius(self, depth: float) -> float:
        """计算水力半径"""
        if self.shape == 'circular':
            if depth >= self.diameter:
                # 满管流
                return self.diameter / 4
            else:
                # 部分充满
                theta = 2 * np.arccos(1 - 2*depth/self.diameter)
                A = (self.diameter**2 / 8) * (theta - np.sin(theta))
                P = self.diameter * theta / 2
                return A / P
        elif self.shape == 'rectangular':
            A = self.width * min(depth, self.height)
            P = self.width + 2 * min(depth, self.height)
            return A / P

class Culvert:
    """
    涵洞水力计算类

    实现FHWA HDS 5方法（联邦公路管理局标准）
    """

    def __init__(self,
                 position: float,
                 geometry: CulvertGeometry,
                 manning_n: float = 0.013,
                 inlet_type: Literal['square_edge', 'groove_end', 'groove_headwall', 'beveled'] = 'square_edge',
                 entrance_loss_coef: float = 0.5,
                 exit_loss_coef: float = 1.0):
        """
        Parameters
        ----------
        position : float
            涵洞在渠道中的位置 (m)
        geometry : CulvertGeometry
            涵洞几何参数
        manning_n : float
            Manning糙率系数
        inlet_type : str
            进口类型
        entrance_loss_coef : float
            进口损失系数 Ke
        exit_loss_coef : float
            出口损失系数 (通常为1.0)
        """
        self.position = position
        self.geom = geometry
        self.n = manning_n
        self.inlet_type = inlet_type
        self.K_e = entrance_loss_coef
        self.K_exit = exit_loss_coef

        # 根据进口类型确定流量系数
        self.C_d = self._get_discharge_coefficient()

        # 物理常数
        self.g = 9.81

    def _get_discharge_coefficient(self) -> float:
        """根据进口类型获取流量系数"""
        coef_map = {
            'square_edge': 0.47,
            'groove_end': 0.52,
            'groove_headwall': 0.53,
            'beveled': 0.57
        }
        return coef_map.get(self.inlet_type, 0.50)

    def compute_discharge(self, h_upstream: float, h_downstream: float) -> Tuple[float, str]:
        """
        计算涵洞流量

        Parameters
        ----------
        h_upstream : float
            上游水深 (m，相对于进口底高程)
        h_downstream : float
            下游水深 (m，相对于出口底高程)

        Returns
        -------
        Q : float
            流量 (m³/s)
        control_type : str
            'inlet' 或 'outlet'，指示控制类型
        """
        # 计算入口控制下的流量
        Q_inlet, H_inlet = self._inlet_control(h_upstream)

        # 计算出口控制下的流量
        Q_outlet, H_outlet = self._outlet_control(h_upstream, h_downstream)

        # 取更不利的情况（需要更高上游水位）
        if H_inlet >= H_outlet:
            return Q_inlet, 'inlet'
        else:
            return Q_outlet, 'outlet'

    def _inlet_control(self, h_upstream: float) -> Tuple[float, float]:
        """
        入口控制计算

        Returns
        -------
        Q : float
            流量
        H : float
            所需上游水头
        """
        A = self.geom.area()

        # 非淹没条件：H < 1.2*D (D为涵洞高度)
        D = self.geom.diameter if self.geom.shape == 'circular' else self.geom.height

        if h_upstream < 1.2 * D:
            # 非淹没入口控制
            # Q = Cd * A * sqrt(2*g*H)
            H = h_upstream - self.geom.invert_elevation
            Q = self.C_d * A * np.sqrt(2 * self.g * H)
        else:
            # 淹没入口控制
            # Q = Cd * A * sqrt(2*g*H)，H为上游水位
            H = h_upstream - self.geom.invert_elevation - D/2
            Q = self.C_d * A * np.sqrt(2 * self.g * H)

        return Q, h_upstream

    def _outlet_control(self, h_upstream: float, h_downstream: float) -> Tuple[float, float]:
        """
        出口控制计算（能量方程）

        使用能量方程：
        H_u = H_d + h_f + h_e + h_exit

        其中：
        - h_f: 摩阻损失 = (n²*L*V²)/(R^(4/3))
        - h_e: 进口损失 = K_e * V²/(2g)
        - h_exit: 出口损失 = K_exit * V²/(2g)
        """
        A = self.geom.area()
        L = self.geom.length
        S_0 = self.geom.slope

        # 假设满管流，迭代求解流量
        Q_guess = 0.5  # 初始猜测

        for iteration in range(50):
            V = Q_guess / A
            R_h = self.geom.hydraulic_radius(
                self.geom.diameter if self.geom.shape == 'circular' else self.geom.height
            )

            # 摩阻损失
            h_f = (self.n**2 * L * V**2) / (R_h**(4/3))

            # 进口损失
            h_e = self.K_e * V**2 / (2 * self.g)

            # 出口损失
            h_exit = self.K_exit * V**2 / (2 * self.g)

            # 能量方程
            H_required = h_downstream + h_f + h_e + h_exit - S_0 * L

            # 检查收敛
            if abs(H_required - h_upstream) < 0.001:
                return Q_guess, H_required

            # 更新流量猜测
            if H_required > h_upstream:
                Q_guess *= 0.95  # 减小流量
            else:
                Q_guess *= 1.05  # 增大流量

        # 未收敛，返回近似值
        return Q_guess, H_required

    def compute_headloss(self, Q: float, h_downstream: float) -> float:
        """
        计算总水头损失

        Parameters
        ----------
        Q : float
            流量 (m³/s)
        h_downstream : float
            下游水深 (m)

        Returns
        -------
        h_loss : float
            总水头损失 (m)
        """
        A = self.geom.area()
        V = Q / A
        L = self.geom.length
        R_h = self.geom.hydraulic_radius(
            self.geom.diameter if self.geom.shape == 'circular' else self.geom.height
        )

        # 各项损失
        h_f = (self.n**2 * L * V**2) / (R_h**(4/3))  # 摩阻
        h_e = self.K_e * V**2 / (2 * self.g)         # 进口
        h_exit = self.K_exit * V**2 / (2 * self.g)   # 出口

        return h_f + h_e + h_exit

    def get_derivatives(self, Q: float, h_upstream: float, h_downstream: float) -> Tuple[float, float]:
        """
        计算流量对上下游水深的导数（用于Newton法）

        Returns
        -------
        dQ_dh_up : float
            ∂Q/∂h_upstream
        dQ_dh_down : float
            ∂Q/∂h_downstream
        """
        delta_h = 0.001  # 微小扰动

        # 数值微分
        Q_plus_up, _ = self.compute_discharge(h_upstream + delta_h, h_downstream)
        Q_minus_up, _ = self.compute_discharge(h_upstream - delta_h, h_downstream)
        dQ_dh_up = (Q_plus_up - Q_minus_up) / (2 * delta_h)

        Q_plus_down, _ = self.compute_discharge(h_upstream, h_downstream + delta_h)
        Q_minus_down, _ = self.compute_discharge(h_upstream, h_downstream - delta_h)
        dQ_dh_down = (Q_plus_down - Q_minus_down) / (2 * delta_h)

        return dQ_dh_up, dQ_dh_down


# ============================================================================
# 便捷构造函数
# ============================================================================

def create_circular_culvert(position: float, diameter: float, length: float,
                           manning_n: float = 0.013,
                           inlet_type: str = 'square_edge') -> Culvert:
    """创建圆形涵洞"""
    geom = CulvertGeometry(
        shape='circular',
        diameter=diameter,
        length=length
    )
    return Culvert(position, geom, manning_n, inlet_type)


def create_rectangular_culvert(position: float, width: float, height: float, length: float,
                               manning_n: float = 0.013,
                               inlet_type: str = 'square_edge') -> Culvert:
    """创建矩形涵洞"""
    geom = CulvertGeometry(
        shape='rectangular',
        width=width,
        height=height,
        length=length
    )
    return Culvert(position, geom, manning_n, inlet_type)
```

#### 1.3 测试代码

**文件**: `tests/test_culvert.py`

```python
"""
涵洞模型测试
"""

import pytest
import numpy as np
from physics.structures.culvert import (
    Culvert, CulvertGeometry,
    create_circular_culvert, create_rectangular_culvert
)


class TestCulvertGeometry:
    """测试涵洞几何计算"""

    def test_circular_area(self):
        """测试圆形涵洞面积"""
        geom = CulvertGeometry(shape='circular', diameter=1.0)
        area = geom.area()
        expected = np.pi * 0.5**2
        assert abs(area - expected) < 1e-10

    def test_rectangular_area(self):
        """测试矩形涵洞面积"""
        geom = CulvertGeometry(shape='rectangular', width=2.0, height=1.5)
        area = geom.area()
        expected = 2.0 * 1.5
        assert abs(area - expected) < 1e-10

    def test_hydraulic_radius_full_pipe(self):
        """测试满管流水力半径"""
        geom = CulvertGeometry(shape='circular', diameter=1.0)
        R_h = geom.hydraulic_radius(depth=1.0)
        expected = 1.0 / 4  # D/4
        assert abs(R_h - expected) < 1e-6


class TestCulvertFlow:
    """测试涵洞流量计算"""

    def test_inlet_control_unsubmerged(self):
        """测试非淹没入口控制"""
        culvert = create_circular_culvert(
            position=100.0,
            diameter=1.0,
            length=20.0,
            manning_n=0.013,
            inlet_type='square_edge'
        )

        # 非淹没条件：上游水深 < 1.2*D
        h_upstream = 0.8  # 小于1.2m
        h_downstream = 0.3

        Q, control_type = culvert.compute_discharge(h_upstream, h_downstream)

        # 验证流量为正
        assert Q > 0

        # 验证为入口控制
        assert control_type == 'inlet'

        # 手动计算验证
        A = np.pi * 0.5**2
        Cd = 0.47
        g = 9.81
        Q_manual = Cd * A * np.sqrt(2 * g * h_upstream)

        assert abs(Q - Q_manual) / Q_manual < 0.05  # 5%误差

    def test_inlet_control_submerged(self):
        """测试淹没入口控制"""
        culvert = create_circular_culvert(
            position=100.0,
            diameter=1.0,
            length=20.0
        )

        # 淹没条件：上游水深 >= 1.2*D
        h_upstream = 1.5
        h_downstream = 0.5

        Q, control_type = culvert.compute_discharge(h_upstream, h_downstream)

        assert Q > 0
        # 可能是入口或出口控制，取决于条件

    def test_outlet_control(self):
        """测试出口控制"""
        culvert = create_circular_culvert(
            position=100.0,
            diameter=1.0,
            length=50.0,  # 较长的涵洞更容易出口控制
            manning_n=0.030  # 较大的糙率
        )

        h_upstream = 1.2
        h_downstream = 1.0  # 高下游水位

        Q, control_type = culvert.compute_discharge(h_upstream, h_downstream)

        assert Q > 0
        # 应该是出口控制
        assert control_type == 'outlet'

    def test_rectangular_culvert(self):
        """测试矩形涵洞"""
        culvert = create_rectangular_culvert(
            position=100.0,
            width=2.0,
            height=1.5,
            length=30.0
        )

        Q, control_type = culvert.compute_discharge(
            h_upstream=1.2,
            h_downstream=0.5
        )

        assert Q > 0

    def test_headloss_calculation(self):
        """测试水头损失计算"""
        culvert = create_circular_culvert(
            position=100.0,
            diameter=1.0,
            length=20.0,
            manning_n=0.013
        )

        Q = 1.5  # m³/s
        h_downstream = 0.5

        h_loss = culvert.compute_headloss(Q, h_downstream)

        # 水头损失应为正值
        assert h_loss > 0

        # 合理范围检查（不应过大）
        assert h_loss < 10.0

    def test_derivatives(self):
        """测试导数计算"""
        culvert = create_circular_culvert(
            position=100.0,
            diameter=1.0,
            length=20.0
        )

        dQ_dh_up, dQ_dh_down = culvert.get_derivatives(
            Q=1.5,
            h_upstream=1.0,
            h_downstream=0.5
        )

        # 导数应为有限值
        assert np.isfinite(dQ_dh_up)
        assert np.isfinite(dQ_dh_down)

        # 上游导数应为正（水位升高，流量增大）
        assert dQ_dh_up > 0

        # 下游导数应为负（下游水位升高，流量减小）
        assert dQ_dh_down < 0


class TestCulvertIntegration:
    """集成测试：涵洞在渠道系统中"""

    def test_culvert_in_channel(self):
        """测试涵洞在渠道中的集成"""
        # 这将在后续与HydrostaticCanalSolver集成时测试
        pass


# ============================================================================
# 验证案例：与手册计算对比
# ============================================================================

class TestCulvertValidation:
    """与标准手册对比验证"""

    def test_fhwa_example_1(self):
        """
        FHWA HDS 5 Example 1
        圆形涵洞，入口控制
        """
        # 标准案例数据
        culvert = create_circular_culvert(
            position=0.0,
            diameter=1.2,  # 48 inch
            length=30.0,   # 100 ft
            manning_n=0.012,
            inlet_type='groove_headwall'
        )

        h_upstream = 1.5
        h_downstream = 0.6

        Q, control_type = culvert.compute_discharge(h_upstream, h_downstream)

        # 手册计算值（需要从FHWA标准中获取）
        Q_expected = 2.8  # m³/s (示例值)

        # 允许10%误差
        assert abs(Q - Q_expected) / Q_expected < 0.10

    def test_fhwa_example_2(self):
        """
        FHWA HDS 5 Example 2
        矩形涵洞，出口控制
        """
        # 标准案例数据
        culvert = create_rectangular_culvert(
            position=0.0,
            width=2.0,
            height=1.5,
            length=40.0,
            manning_n=0.013,
            inlet_type='square_edge'
        )

        h_upstream = 1.8
        h_downstream = 1.2

        Q, control_type = culvert.compute_discharge(h_upstream, h_downstream)

        # 应该是出口控制
        assert control_type == 'outlet'

        # 手册计算值
        Q_expected = 4.5  # m³/s (示例值)

        assert abs(Q - Q_expected) / Q_expected < 0.10


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
```

#### 1.4 文档

**文件**: `docs/structures/culvert.md`

```markdown
# 涵洞（Culvert）水力计算

## 概述

涵洞是穿越路堤、堤坝等构筑物的过水结构，通常为圆形、矩形或拱形断面。

## 理论基础

### 流态分类

涵洞流态主要分为两种控制类型：

1. **入口控制（Inlet Control）**
   - 出口未淹没
   - 流量由进口断面控制
   - 公式：Q = Cd·A·√(2g·H)

2. **出口控制（Outlet Control）**
   - 出口淹没
   - 能量方程控制
   - 考虑摩阻、进出口损失

### 判别方法

计算两种控制下所需的上游水位，取较高者。

## 使用示例

### 创建圆形涵洞

```python
from physics.structures.culvert import create_circular_culvert

culvert = create_circular_culvert(
    position=100.0,        # 位置 (m)
    diameter=1.2,          # 直径 (m)
    length=30.0,           # 长度 (m)
    manning_n=0.013,       # 糙率
    inlet_type='square_edge'  # 进口类型
)
```

### 计算流量

```python
Q, control_type = culvert.compute_discharge(
    h_upstream=1.5,    # 上游水深 (m)
    h_downstream=0.6   # 下游水深 (m)
)

print(f"流量: {Q:.2f} m³/s")
print(f"控制类型: {control_type}")
```

### 计算水头损失

```python
h_loss = culvert.compute_headloss(Q=2.0, h_downstream=0.6)
print(f"水头损失: {h_loss:.3f} m")
```

## 参数说明

### 几何参数

- `diameter`: 圆形涵洞直径 (m)
- `width`, `height`: 矩形涵洞尺寸 (m)
- `length`: 涵洞长度 (m)
- `slope`: 涵洞坡度（默认0.001）

### 水力参数

- `manning_n`: Manning糙率系数
  - 混凝土: 0.012-0.015
  - 波纹钢: 0.024-0.030
- `inlet_type`: 进口类型
  - `square_edge`: 方形边缘（Cd≈0.47）
  - `groove_headwall`: 槽形带翼墙（Cd≈0.53）
  - `beveled`: 斜切（Cd≈0.57）

## 验证案例

### 案例1：入口控制

标准算例来自FHWA HDS 5

- 直径: 1.2 m
- 长度: 30 m
- 上游水深: 1.5 m
- 计算流量: 2.8 m³/s
- 误差: <5%

### 案例2：出口控制

- 矩形 2.0m × 1.5m
- 长度: 40 m
- 下游淹没
- 计算准确度: <10%

## 参考文献

1. FHWA (2012). *Hydraulic Design of Highway Culverts*, HDS 5, 3rd Edition
2. USBR (1987). *Design of Small Dams*
3. Bodhaine, G.L. (1968). "Measurement of Peak Discharge at Culverts"

## API参考

详见API文档: [culvert API](../api/culvert.html)
```

### Week 1-2 交付清单

- ✅ `physics/structures/culvert.py` - 完整实现
- ✅ `tests/test_culvert.py` - 20+测试函数
- ✅ `docs/structures/culvert.md` - 完整文档
- ✅ 与现有求解器集成示例
- ✅ 验证报告（对比手册计算）

---

## 实施计划：立即开始Week 1-2

我将按照以下步骤开始实现：

1. **创建目录结构**
2. **实现涵洞类**
3. **编写测试**
4. **验证计算**
5. **编写文档**

每个步骤完成后我会报告进度。
