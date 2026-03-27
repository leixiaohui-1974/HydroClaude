"""
hydraulic_structures.py
=======================
水工构筑物模拟模块，支持：
  - SluiceGate    : 平板闸门（自由出流 / 淹没出流）
  - RadialGate    : 弧形闸门（Tainter Gate）
  - PumpStation   : 泵站（固定流量 / H-Q 曲线）
  - Culvert       : 涵洞（圆形 / 矩形，进口控制 / 出口控制）
  - StructureGroup: 多构筑物组合管理器

所有构筑物均实现统一的 HydraulicStructure 基类接口，
通过 compute_flow(h_up, h_down) 返回流量 Q (m³/s)，
正值表示从上游流向下游。

参考标准：
  - HEC-RAS Hydraulic Reference Manual v6.5
  - USBR Design of Small Canal Structures (1978)
  - ASCE Manual of Engineering Practice No. 36
"""

from __future__ import annotations

import numpy as np
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List, Callable


# ---------------------------------------------------------------------------
# 基类
# ---------------------------------------------------------------------------

class HydraulicStructure(ABC):
    """水工构筑物基类。"""

    def __init__(self, name: str, node_up: int, node_down: int):
        """
        Args:
            name      : 构筑物名称（用于日志和调试）
            node_up   : 上游节点索引（1D 网格中的节点编号）
            node_down : 下游节点索引
        """
        self.name      = name
        self.node_up   = node_up
        self.node_down = node_down
        self._Q_last   = 0.0  # 上一时间步的流量（用于平滑）

    @abstractmethod
    def compute_flow(self, h_up: float, h_down: float, dt: float = 1.0) -> float:
        """
        计算通过构筑物的流量。

        Args:
            h_up   : 上游水深 (m)
            h_down : 下游水深 (m)
            dt     : 时间步长 (s)，用于泵站的启停逻辑

        Returns:
            Q : 流量 (m³/s)，正值为从上游流向下游
        """
        ...

    def get_source_terms(self, h_up: float, h_down: float,
                         dt: float = 1.0) -> tuple[float, float]:
        """
        返回注入 1D 方程的源汇项 (q_up, q_down)。

        q_up   : 注入上游节点的侧向流量 (m³/s)，负值表示流出
        q_down : 注入下游节点的侧向流量 (m³/s)，正值表示流入

        Returns:
            (q_up, q_down)
        """
        Q = self.compute_flow(h_up, h_down, dt)
        self._Q_last = Q
        return -Q, +Q  # 上游流出，下游流入


# ---------------------------------------------------------------------------
# 1. 平板闸门（Sluice Gate）
# ---------------------------------------------------------------------------

class SluiceGate(HydraulicStructure):
    """
    平板闸门（Sluice Gate）。

    流量公式（参考 HEC-RAS Hydraulic Reference Manual）：

    自由出流（Free Flow）：
        Q = Cd * b * a * sqrt(2g * h_up)

    淹没出流（Submerged Flow）：
        Q = Cs * b * a * sqrt(2g * (h_up - h_down))

    淹没判断条件（Villemonte 准则）：
        h_down / h_up > 0.67 → 淹没出流

    其中：
        Cd : 自由出流流量系数（典型值 0.61）
        Cs : 淹没出流流量系数（典型值 0.61 * 修正系数）
        b  : 闸孔宽度 (m)
        a  : 闸门开度 (m)
        g  : 重力加速度 (m/s²)
    """

    # 淹没出流判断阈值（Villemonte, 1947）
    SUBMERGENCE_RATIO = 0.67

    def __init__(self, name: str, node_up: int, node_down: int,
                 width: float, opening: float,
                 Cd: float = 0.61, z_sill: float = 0.0):
        """
        Args:
            width   : 闸孔宽度 (m)
            opening : 闸门开度 (m)，0 = 全关，可动态修改
            Cd      : 流量系数（默认 0.61）
            z_sill  : 闸底高程 (m)，相对于基准面
        """
        super().__init__(name, node_up, node_down)
        self.width   = float(width)
        self.opening = float(opening)
        self.Cd      = float(Cd)
        self.z_sill  = float(z_sill)
        self.g       = 9.81

    def set_opening(self, opening: float):
        """动态设置闸门开度（用于调度控制）。"""
        self.opening = max(0.0, float(opening))

    def compute_flow(self, h_up: float, h_down: float, dt: float = 1.0) -> float:
        """计算闸门过流量。"""
        g = self.g
        a = self.opening
        b = self.width

        # 有效水头（相对于闸底）
        H_up   = max(h_up   - self.z_sill, 0.0)
        H_down = max(h_down - self.z_sill, 0.0)

        # 闸门全关或无水头
        if a <= 0.0 or H_up <= 0.0:
            return 0.0

        # 有效开度（不超过上游水深）
        a_eff = min(a, H_up)

        # 淹没判断
        if H_up > 1e-6 and H_down / H_up > self.SUBMERGENCE_RATIO:
            # 淹没出流（Submerged Flow）
            dH = max(H_up - H_down, 0.0)
            Q  = self.Cd * b * a_eff * np.sqrt(2.0 * g * dH)
        else:
            # 自由出流（Free Flow）
            Q = self.Cd * b * a_eff * np.sqrt(2.0 * g * H_up)

        return Q


# ---------------------------------------------------------------------------
# 2. 弧形闸门（Radial / Tainter Gate）
# ---------------------------------------------------------------------------

class RadialGate(HydraulicStructure):
    """
    弧形闸门（Radial Gate / Tainter Gate）。

    流量公式（参考 USBR Design of Small Canal Structures）：

    自由出流：
        Q = Cd * b * a * sqrt(2g * H_up)

    其中 Cd 随 a/H_up 变化（Toch, 1955 曲线近似）：
        Cd = 0.61 * (1 - 0.75 * a/H_up + 0.36 * (a/H_up)^2)

    淹没出流修正（与平板闸门相同）：
        Q_submerged = Q_free * sqrt(1 - (H_down/H_up)^1.5)
    """

    def __init__(self, name: str, node_up: int, node_down: int,
                 width: float, opening: float, z_sill: float = 0.0):
        super().__init__(name, node_up, node_down)
        self.width   = float(width)
        self.opening = float(opening)
        self.z_sill  = float(z_sill)
        self.g       = 9.81

    def set_opening(self, opening: float):
        self.opening = max(0.0, float(opening))

    def _toch_cd(self, a_over_H: float) -> float:
        """Toch (1955) 弧形闸门流量系数近似公式。"""
        r = min(a_over_H, 1.0)
        return 0.61 * (1.0 - 0.75 * r + 0.36 * r**2)

    def compute_flow(self, h_up: float, h_down: float, dt: float = 1.0) -> float:
        g = self.g
        a = self.opening
        b = self.width

        H_up   = max(h_up   - self.z_sill, 0.0)
        H_down = max(h_down - self.z_sill, 0.0)

        if a <= 0.0 or H_up <= 1e-6:
            return 0.0

        a_eff     = min(a, H_up)
        a_over_H  = a_eff / H_up
        Cd        = self._toch_cd(a_over_H)

        # 自由出流
        Q_free = Cd * b * a_eff * np.sqrt(2.0 * g * H_up)

        # 淹没修正（Villemonte, 1947）
        if H_up > 1e-6 and H_down / H_up > 0.67:
            ratio = H_down / H_up
            Q = Q_free * np.sqrt(max(1.0 - ratio**1.5, 0.0))
        else:
            Q = Q_free

        return Q


# ---------------------------------------------------------------------------
# 3. 泵站（Pump Station）
# ---------------------------------------------------------------------------

class PumpStation(HydraulicStructure):
    """
    泵站（Pump Station）。

    支持两种运行模式：
    1. 固定流量泵（Constant Flow Pump）：以恒定流量 Q_design 运行。
    2. H-Q 曲线泵（Variable Speed Pump）：根据扬程-流量曲线插值计算流量。

    启停控制：
    - 当上游水深 h_up > h_start 时启动
    - 当上游水深 h_up < h_stop 时停止
    - 支持多台泵并联（n_pumps）
    """

    def __init__(self, name: str, node_up: int, node_down: int,
                 Q_design: float,
                 h_start: float = 0.5,
                 h_stop:  float = 0.1,
                 n_pumps: int   = 1,
                 hq_curve: Optional[List[tuple]] = None):
        """
        Args:
            Q_design  : 单台泵设计流量 (m³/s)
            h_start   : 启泵水深 (m)
            h_stop    : 停泵水深 (m)
            n_pumps   : 并联泵台数
            hq_curve  : H-Q 曲线，格式 [(H1, Q1), (H2, Q2), ...]
                        H 为扬程 (m)，Q 为流量 (m³/s)
        """
        super().__init__(name, node_up, node_down)
        self.Q_design = float(Q_design)
        self.h_start  = float(h_start)
        self.h_stop   = float(h_stop)
        self.n_pumps  = int(n_pumps)
        self._running = False  # 泵的当前运行状态

        # H-Q 曲线
        if hq_curve is not None:
            H_arr = np.array([p[0] for p in hq_curve])
            Q_arr = np.array([p[1] for p in hq_curve])
            # 排序
            idx = np.argsort(H_arr)
            self._hq_H = H_arr[idx]
            self._hq_Q = Q_arr[idx]
        else:
            self._hq_H = None
            self._hq_Q = None

    @property
    def is_running(self) -> bool:
        return self._running

    def compute_flow(self, h_up: float, h_down: float, dt: float = 1.0) -> float:
        """计算泵站流量（含启停逻辑）。"""
        # 启停逻辑（滞回控制）
        if not self._running and h_up >= self.h_start:
            self._running = True
        elif self._running and h_up <= self.h_stop:
            self._running = False

        if not self._running:
            return 0.0

        # 计算扬程
        H_pump = max(h_down - h_up, 0.0)  # 净扬程（下游水位 - 上游水位）

        if self._hq_H is not None:
            # H-Q 曲线插值
            Q_single = float(np.interp(H_pump, self._hq_H, self._hq_Q,
                                        left=self._hq_Q[0], right=0.0))
        else:
            # 固定流量（不受扬程影响）
            Q_single = self.Q_design

        return max(Q_single, 0.0) * self.n_pumps


# ---------------------------------------------------------------------------
# 4. 涵洞（Culvert）
# ---------------------------------------------------------------------------

class Culvert(HydraulicStructure):
    """
    涵洞（Culvert）。

    支持截面形状：
    - 圆形（circular）
    - 矩形（rectangular）

    流态判断（参考 HEC-RAS Hydraulic Reference Manual）：
    - 进口控制（Inlet Control）：涵洞进口为控制断面，流量由进口水头决定
    - 出口控制（Outlet Control）：涵洞出口为控制断面，流量由全管水头损失决定

    实际流量取两种控制的最小值（较小者为控制流态）。

    进口控制（无压流）：
        Q = Cd_in * A * sqrt(2g * HW)
        其中 HW = h_up - z_in（进口水头）

    出口控制（满管压力流）：
        Q = A * sqrt(2g * dH / (Ke + Kf + 1.0))
        其中 dH = h_up - h_down，Ke = 进口损失系数，Kf = 摩擦损失系数
        Kf = (2g * n^2 * L) / R^(4/3)（Manning 公式）
    """

    SHAPE_CIRCULAR    = 'circular'
    SHAPE_RECTANGULAR = 'rectangular'

    def __init__(self, name: str, node_up: int, node_down: int,
                 shape: str,
                 diameter_or_height: float,
                 width: float = 1.0,
                 length: float = 10.0,
                 z_in:  float = 0.0,
                 z_out: float = 0.0,
                 n_manning: float = 0.013,
                 Ke: float = 0.5,
                 Cd_in: float = 0.6,
                 n_barrels: int = 1):
        """
        Args:
            shape               : 截面形状 ('circular' 或 'rectangular')
            diameter_or_height  : 圆形直径 D (m) 或矩形高度 H (m)
            width               : 矩形宽度 B (m)（圆形时忽略）
            length              : 涵洞长度 L (m)
            z_in                : 进口底高程 (m)
            z_out               : 出口底高程 (m)
            n_manning           : Manning 糙率系数
            Ke                  : 进口损失系数（方形进口 0.5，圆角进口 0.1）
            Cd_in               : 进口控制流量系数（典型值 0.6）
            n_barrels           : 并联涵洞数量
        """
        super().__init__(name, node_up, node_down)
        self.shape    = shape
        self.D        = float(diameter_or_height)
        self.B        = float(width)
        self.L        = float(length)
        self.z_in     = float(z_in)
        self.z_out    = float(z_out)
        self.n        = float(n_manning)
        self.Ke       = float(Ke)
        self.Cd_in    = float(Cd_in)
        self.n_barrels = int(n_barrels)
        self.g        = 9.81

        # 预计算截面属性（满管）
        self._A_full, self._R_full = self._compute_full_section()

    def _compute_full_section(self) -> tuple[float, float]:
        """计算满管截面面积和水力半径。"""
        if self.shape == self.SHAPE_CIRCULAR:
            D = self.D
            A = np.pi * D**2 / 4.0
            P = np.pi * D
        else:  # rectangular
            A = self.D * self.B
            P = 2.0 * (self.D + self.B)
        R = A / P if P > 0 else 0.0
        return A, R

    def _inlet_control_flow(self, h_up: float) -> float:
        """进口控制流量（无压流，进口水头控制）。"""
        HW = max(h_up - self.z_in, 0.0)  # 进口水头
        if HW <= 0.0:
            return 0.0
        # 使用进口水头计算流量（无压流公式）
        Q = self.Cd_in * self._A_full * np.sqrt(2.0 * self.g * HW)
        return Q

    def _outlet_control_flow(self, h_up: float, h_down: float) -> float:
        """出口控制流量（满管压力流）。"""
        # 总水头差
        dH = max(h_up - h_down, 0.0)
        if dH <= 0.0:
            return 0.0

        # 摩擦损失系数（Manning 公式）
        R = self._R_full
        if R <= 0.0:
            return 0.0
        Kf = (2.0 * self.g * self.n**2 * self.L) / (R**(4.0/3.0))

        # 出口损失系数（取 1.0，动能损失）
        Ko = 1.0

        # 总损失系数
        K_total = self.Ke + Kf + Ko

        Q = self._A_full * np.sqrt(2.0 * self.g * dH / K_total)
        return Q

    def compute_flow(self, h_up: float, h_down: float, dt: float = 1.0) -> float:
        """计算涵洞过流量（取进口控制和出口控制的最小值）。"""
        Q_in  = self._inlet_control_flow(h_up)
        Q_out = self._outlet_control_flow(h_up, h_down)

        # 实际流量取较小值（较小者为控制流态）
        Q = min(Q_in, Q_out)
        return Q * self.n_barrels


# ---------------------------------------------------------------------------
# 5. 溢洪道（Spillway / Broad-crested Weir）
# ---------------------------------------------------------------------------

class Spillway(HydraulicStructure):
    """
    溢洪道 / 宽顶堰（Broad-crested Weir）。

    流量公式：
    自由出流：
        Q = Cd * L * H^1.5 * sqrt(2g/3)^(2/3)
        简化为：Q = Cw * L * H^1.5
        其中 Cw = Cd * sqrt(2g) * (2/3)^1.5 ≈ 1.705 * Cd

    淹没修正（Villemonte, 1947）：
        Q_sub = Q_free * [1 - (h_down/h_up)^1.5]^0.385

    其中：
        Cd : 流量系数（宽顶堰典型值 0.848）
        L  : 堰长 (m)
        H  : 堰上水头 = h_up - z_crest (m)
    """

    def __init__(self, name: str, node_up: int, node_down: int,
                 length: float, z_crest: float,
                 Cd: float = 0.848):
        """
        Args:
            length  : 堰长 (m)
            z_crest : 堰顶高程 (m)
            Cd      : 流量系数（默认 0.848，对应 Cw ≈ 1.705）
        """
        super().__init__(name, node_up, node_down)
        self.length  = float(length)
        self.z_crest = float(z_crest)
        self.Cd      = float(Cd)
        self.g       = 9.81
        # Cw = Cd * sqrt(2g) * (2/3)^1.5
        self.Cw = Cd * np.sqrt(2.0 * self.g) * (2.0/3.0)**1.5

    def compute_flow(self, h_up: float, h_down: float, dt: float = 1.0) -> float:
        """计算溢洪道过流量。"""
        H_up   = max(h_up   - self.z_crest, 0.0)
        H_down = max(h_down - self.z_crest, 0.0)

        if H_up <= 0.0:
            return 0.0

        # 自由出流
        Q_free = self.Cw * self.length * H_up**1.5

        # 淹没修正（Villemonte, 1947）
        if H_up > 1e-6 and H_down / H_up > 0.0:
            ratio = H_down / H_up
            Q = Q_free * (1.0 - ratio**1.5)**0.385
        else:
            Q = Q_free

        return max(Q, 0.0)


# ---------------------------------------------------------------------------
# 6. 构筑物组合管理器
# ---------------------------------------------------------------------------

class StructureGroup:
    """
    水工构筑物组合管理器。

    管理多个构筑物，提供统一的接口将所有构筑物的影响
    聚合为 1D 方程的节点源汇项数组。
    """

    def __init__(self, n_nodes: int):
        """
        Args:
            n_nodes : 1D 网格的节点总数
        """
        self.n_nodes    = n_nodes
        self.structures: List[HydraulicStructure] = []

    def add(self, structure: HydraulicStructure):
        """添加一个水工构筑物。"""
        if structure.node_up >= self.n_nodes or structure.node_down >= self.n_nodes:
            raise ValueError(
                f"构筑物 '{structure.name}' 的节点索引超出范围 "
                f"(n_nodes={self.n_nodes})"
            )
        self.structures.append(structure)
        return self  # 支持链式调用

    def compute_source_terms(self, h: np.ndarray, dt: float = 1.0) -> np.ndarray:
        """
        计算所有构筑物对各节点的源汇项。

        Args:
            h  : 各节点水深数组，形状 (n_nodes,)
            dt : 时间步长 (s)

        Returns:
            q_src : 节点源汇项数组，形状 (n_nodes,)，单位 m³/s
                    正值表示流入，负值表示流出
        """
        q_src = np.zeros(self.n_nodes)
        for s in self.structures:
            h_up   = float(h[s.node_up])
            h_down = float(h[s.node_down])
            q_up, q_down = s.get_source_terms(h_up, h_down, dt)
            q_src[s.node_up]   += q_up
            q_src[s.node_down] += q_down
        return q_src

    def get_all_flows(self, h: np.ndarray, dt: float = 1.0) -> dict:
        """
        返回所有构筑物的当前流量字典。

        Returns:
            {structure_name: Q (m³/s)}
        """
        flows = {}
        for s in self.structures:
            h_up   = float(h[s.node_up])
            h_down = float(h[s.node_down])
            Q = s.compute_flow(h_up, h_down, dt)
            flows[s.name] = Q
        return flows

    def __len__(self):
        return len(self.structures)

    def __repr__(self):
        names = [s.name for s in self.structures]
        return f"StructureGroup(n_nodes={self.n_nodes}, structures={names})"
