"""
水工建筑物模块 (Hydraulic Structures)

实现常见的水工建筑物水力计算：
1. 堰 (Weirs) - 宽顶堰、薄壁堰、实用堰
2. 闸门 (Gates) - 平板闸门、弧形闸门
3. 孔口 (Orifices) - 淹没/自由出流

Phase 2.4 - Task 2.4.3

作者: HydroClaude Team
日期: 2025-10-29
"""

import numpy as np
from typing import Optional, Dict
from enum import Enum


class WeirType(Enum):
    """堰类型"""
    BROAD_CRESTED = "broad_crested"      # 宽顶堰
    SHARP_CRESTED = "sharp_crested"      # 薄壁堰
    OGEE = "ogee"                        # 实用堰（溢流堰）


class FlowRegime(Enum):
    """流态"""
    FREE = "free"          # 自由出流
    SUBMERGED = "submerged"  # 淹没出流


class BroadCrestedWeir:
    """
    宽顶堰 (Broad-Crested Weir)

    标准公式：Q = C * B * H^(3/2)
    其中：
    - C = 流量系数 ≈ 1.7 (SI单位)
    - B = 堰宽 (m)
    - H = 堰顶水头 (m)

    适用条件：
    - H/L < 0.5 (L为堰顶长度)
    - 宽顶堰流

    示例：
        weir = BroadCrestedWeir(
            crest_elevation=2.0,  # 堰顶高程 (m)
            width=10.0,           # 堰宽 (m)
            discharge_coeff=1.7   # 流量系数
        )

        # 计算过堰流量
        h_upstream = 3.5  # 上游水位 (m)
        Q = weir.compute_discharge(h_upstream, h_downstream=2.5)
    """

    def __init__(
        self,
        crest_elevation: float,
        width: float,
        discharge_coeff: float = 1.7,
        name: str = "Broad-Crested Weir",
        g: float = 9.81
    ):
        """
        初始化宽顶堰

        Args:
            crest_elevation: 堰顶高程 (m)
            width: 堰宽 (m)
            discharge_coeff: 流量系数 (默认1.7)
            name: 名称
            g: 重力加速度 (m/s²)
        """
        self.z_crest = crest_elevation
        self.B = width
        self.C = discharge_coeff
        self.name = name
        self.g = g

    def compute_discharge(
        self,
        h_upstream: float,
        h_downstream: Optional[float] = None
    ) -> float:
        """
        计算过堰流量

        Args:
            h_upstream: 上游水位 (m)
            h_downstream: 下游水位 (m)，None则假设自由出流

        Returns:
            流量 Q (m³/s)
        """
        # 堰顶水头
        H = h_upstream - self.z_crest

        if H <= 0:
            return 0.0

        # 判断流态
        if h_downstream is None:
            # 自由出流
            Q = self.C * self.B * H**(3/2)
        else:
            # 检查淹没度
            H_d = h_downstream - self.z_crest
            if H_d <= 0:
                # 下游未淹没堰顶，自由出流
                Q = self.C * self.B * H**(3/2)
            else:
                # 淹没出流，使用淹没系数
                submergence_ratio = H_d / H
                if submergence_ratio < 0.67:
                    # 部分淹没，应用淹没系数
                    # Villemonte公式
                    factor = (1 - submergence_ratio**1.5)**0.385
                    Q = self.C * self.B * H**(3/2) * factor
                else:
                    # 深度淹没，使用孔流公式
                    Q = self.compute_orifice_flow(H, H_d)

        return Q

    def compute_orifice_flow(self, H_up: float, H_down: float) -> float:
        """
        深度淹没时的孔流公式

        Q = C_d * A * sqrt(2*g*ΔH)

        Args:
            H_up: 上游水头 (m)
            H_down: 下游水头 (m)

        Returns:
            流量 (m³/s)
        """
        delta_H = H_up - H_down
        if delta_H <= 0:
            return 0.0

        # 淹没孔流系数
        C_d = 0.6
        # 过流面积（近似为堰顶宽度×水头差）
        A = self.B * delta_H
        Q = C_d * A * np.sqrt(2 * self.g * delta_H)

        return Q

    def get_regime(self, h_upstream: float, h_downstream: float) -> FlowRegime:
        """判断流态"""
        H = h_upstream - self.z_crest
        H_d = h_downstream - self.z_crest

        if H <= 0:
            return None

        if H_d <= 0 or H_d / H < 0.67:
            return FlowRegime.FREE
        else:
            return FlowRegime.SUBMERGED

    def __repr__(self):
        return (f"{self.name}: "
                f"z_crest={self.z_crest:.2f}m, "
                f"B={self.B:.2f}m, "
                f"C={self.C:.2f}")


class SharpCrestedWeir:
    """
    薄壁堰 (Sharp-Crested Weir)

    标准公式：Q = C * B * H^(3/2)
    其中 C ≈ 1.84 (矩形薄壁堰)

    适用于测流、小型溢流

    示例：
        weir = SharpCrestedWeir(
            crest_elevation=1.0,
            width=5.0
        )
    """

    def __init__(
        self,
        crest_elevation: float,
        width: float,
        discharge_coeff: float = 1.84,
        name: str = "Sharp-Crested Weir",
        g: float = 9.81
    ):
        """
        初始化薄壁堰

        Args:
            crest_elevation: 堰顶高程 (m)
            width: 堰宽 (m)
            discharge_coeff: 流量系数 (默认1.84)
            name: 名称
            g: 重力加速度
        """
        self.z_crest = crest_elevation
        self.B = width
        self.C = discharge_coeff
        self.name = name
        self.g = g

    def compute_discharge(self, h_upstream: float) -> float:
        """
        计算过堰流量（自由出流）

        Args:
            h_upstream: 上游水位 (m)

        Returns:
            流量 Q (m³/s)
        """
        H = h_upstream - self.z_crest

        if H <= 0:
            return 0.0

        Q = self.C * self.B * H**(3/2)
        return Q

    def __repr__(self):
        return (f"{self.name}: "
                f"z_crest={self.z_crest:.2f}m, "
                f"B={self.B:.2f}m")


class SluiceGate:
    """
    平板闸门 (Sluice Gate)

    自由出流公式：Q = C_d * a * B * sqrt(2*g*H)
    淹没出流公式：Q = C_d * a * B * sqrt(2*g*ΔH)

    其中：
    - C_d = 收缩系数 ≈ 0.6
    - a = 闸门开度 (m)
    - B = 闸门宽度 (m)
    - H = 上游水头 (m)
    - ΔH = 上下游水头差 (m)

    示例：
        gate = SluiceGate(
            sill_elevation=0.0,  # 闸底高程 (m)
            width=8.0,           # 闸门宽度 (m)
            opening=0.5          # 开度 (m)
        )

        # 设置开度（可时变）
        gate.set_opening(1.0)  # 开到1m

        # 计算过闸流量
        Q = gate.compute_discharge(h_upstream=3.0, h_downstream=2.0)
    """

    def __init__(
        self,
        sill_elevation: float,
        width: float,
        opening: float = 0.0,
        contraction_coeff: float = 0.6,
        name: str = "Sluice Gate",
        g: float = 9.81
    ):
        """
        初始化平板闸门

        Args:
            sill_elevation: 闸底高程 (m)
            width: 闸门宽度 (m)
            opening: 初始开度 (m)
            contraction_coeff: 收缩系数 (默认0.6)
            name: 名称
            g: 重力加速度
        """
        self.z_sill = sill_elevation
        self.B = width
        self.opening = opening
        self.C_d = contraction_coeff
        self.name = name
        self.g = g

    def set_opening(self, opening: float):
        """设置闸门开度"""
        self.opening = max(0.0, opening)

    def compute_discharge(
        self,
        h_upstream: float,
        h_downstream: float
    ) -> float:
        """
        计算过闸流量

        Args:
            h_upstream: 上游水位 (m)
            h_downstream: 下游水位 (m)

        Returns:
            流量 Q (m³/s)
        """
        if self.opening <= 0:
            return 0.0

        # 上游水深
        y_up = h_upstream - self.z_sill
        if y_up <= 0:
            return 0.0

        # 下游水深
        y_down = h_downstream - self.z_sill

        # 有效过流面积
        A = self.C_d * self.opening * self.B

        # 判断流态
        if y_down < 0 or y_down < 0.67 * self.opening:
            # 自由出流
            Q = A * np.sqrt(2 * self.g * y_up)
        else:
            # 淹没出流
            delta_y = y_up - y_down
            if delta_y <= 0:
                return 0.0
            Q = A * np.sqrt(2 * self.g * delta_y)

        return Q

    def get_regime(self, h_upstream: float, h_downstream: float) -> FlowRegime:
        """判断流态"""
        y_up = h_upstream - self.z_sill
        y_down = h_downstream - self.z_sill

        if y_up <= 0 or self.opening <= 0:
            return None

        if y_down < 0.67 * self.opening:
            return FlowRegime.FREE
        else:
            return FlowRegime.SUBMERGED

    def __repr__(self):
        return (f"{self.name}: "
                f"z_sill={self.z_sill:.2f}m, "
                f"B={self.B:.2f}m, "
                f"a={self.opening:.2f}m")


class Orifice:
    """
    孔口 (Orifice)

    标准孔流公式：Q = C_d * A * sqrt(2*g*H)

    用于：
    - 涵洞
    - 泄水孔
    - 箱涵

    示例：
        orifice = Orifice(
            center_elevation=1.0,  # 孔口中心高程 (m)
            diameter=1.5,          # 直径 (m)
            discharge_coeff=0.62   # 流量系数
        )
    """

    def __init__(
        self,
        center_elevation: float,
        diameter: float,
        discharge_coeff: float = 0.62,
        name: str = "Orifice",
        g: float = 9.81
    ):
        """
        初始化圆形孔口

        Args:
            center_elevation: 孔口中心高程 (m)
            diameter: 直径 (m)
            discharge_coeff: 流量系数 (默认0.62)
            name: 名称
            g: 重力加速度
        """
        self.z_center = center_elevation
        self.D = diameter
        self.C_d = discharge_coeff
        self.name = name
        self.g = g

        # 孔口面积
        self.A = np.pi * (diameter / 2)**2

    def compute_discharge(
        self,
        h_upstream: float,
        h_downstream: Optional[float] = None
    ) -> float:
        """
        计算过流量

        Args:
            h_upstream: 上游水位 (m)
            h_downstream: 下游水位 (m)，None则假设自由出流

        Returns:
            流量 Q (m³/s)
        """
        # 上游水头（到孔口中心）
        H_up = h_upstream - self.z_center

        if H_up <= -self.D/2:
            # 上游水位低于孔口底部
            return 0.0

        if h_downstream is None:
            # 自由出流
            H = max(H_up, 0)
            Q = self.C_d * self.A * np.sqrt(2 * self.g * H)
        else:
            # 考虑下游水位
            H_down = h_downstream - self.z_center

            if H_down < -self.D/2:
                # 下游未淹没孔口，自由出流
                H = max(H_up, 0)
                Q = self.C_d * self.A * np.sqrt(2 * self.g * H)
            else:
                # 淹没出流
                delta_H = H_up - H_down
                if delta_H <= 0:
                    return 0.0
                Q = self.C_d * self.A * np.sqrt(2 * self.g * delta_H)

        return Q

    def __repr__(self):
        return (f"{self.name}: "
                f"z_center={self.z_center:.2f}m, "
                f"D={self.D:.2f}m, "
                f"A={self.A:.3f}m²")


def create_weir_bc(
    weir: BroadCrestedWeir,
    h_downstream: Optional[float] = None
) -> callable:
    """
    创建堰的边界条件函数

    根据上游水位自动计算过堰流量

    Args:
        weir: 堰对象
        h_downstream: 下游水位 (m)，None则自由出流

    Returns:
        边界条件函数 Q(h_upstream)

    示例：
        weir = BroadCrestedWeir(crest_elevation=2.0, width=10.0)
        bc_func = create_weir_bc(weir, h_downstream=2.5)

        # 用于求解器 (作为Rating Curve类型的BC)
        solver.set_boundary_conditions(
            ...,
            bc_right={'type': 'weir', 'weir': weir, 'h_downstream': 2.5}
        )
    """
    def weir_discharge(h_upstream):
        return weir.compute_discharge(h_upstream, h_downstream)

    weir_discharge.__name__ = f"Weir_BC_{weir.name}"
    return weir_discharge


if __name__ == "__main__":
    """测试水工建筑物模块"""

    print("="*80)
    print("水工建筑物模块测试")
    print("="*80)

    # 测试1: 宽顶堰
    print("\n[测试1] 宽顶堰 (Broad-Crested Weir)")
    print("-"*70)

    weir_broad = BroadCrestedWeir(
        crest_elevation=2.0,
        width=10.0,
        discharge_coeff=1.7
    )
    print(weir_broad)

    print("\n过堰流量计算:")
    test_cases = [
        (2.0, None, "堰顶水位，无流"),
        (2.5, None, "自由出流"),
        (3.0, None, "自由出流"),
        (3.0, 2.3, "部分淹没"),
        (3.0, 2.8, "深度淹没")
    ]

    for h_up, h_down, desc in test_cases:
        Q = weir_broad.compute_discharge(h_up, h_down)
        if h_down:
            regime = weir_broad.get_regime(h_up, h_down)
            print(f"  h_up={h_up:.1f}m, h_down={h_down:.1f}m: Q={Q:.2f} m³/s ({desc}, {regime.value if regime else 'N/A'})")
        else:
            print(f"  h_up={h_up:.1f}m: Q={Q:.2f} m³/s ({desc})")

    # 测试2: 薄壁堰
    print("\n[测试2] 薄壁堰 (Sharp-Crested Weir)")
    print("-"*70)

    weir_sharp = SharpCrestedWeir(
        crest_elevation=1.0,
        width=5.0
    )
    print(weir_sharp)

    print("\n过堰流量:")
    for h in [1.0, 1.2, 1.5, 2.0]:
        Q = weir_sharp.compute_discharge(h)
        H = h - weir_sharp.z_crest
        print(f"  h={h:.1f}m (H={H:.1f}m): Q={Q:.2f} m³/s")

    # 测试3: 平板闸门
    print("\n[测试3] 平板闸门 (Sluice Gate)")
    print("-"*70)

    gate = SluiceGate(
        sill_elevation=0.0,
        width=8.0,
        opening=0.5
    )
    print(gate)

    print("\n过闸流量 (开度=0.5m):")
    test_cases = [
        (2.0, 0.3, "自由出流"),
        (3.0, 1.0, "部分淹没"),
        (3.0, 2.5, "深度淹没")
    ]

    for h_up, h_down, desc in test_cases:
        Q = gate.compute_discharge(h_up, h_down)
        regime = gate.get_regime(h_up, h_down)
        print(f"  h_up={h_up:.1f}m, h_down={h_down:.1f}m: Q={Q:.2f} m³/s ({desc}, {regime.value if regime else 'N/A'})")

    # 测试不同开度
    print("\n不同开度下的流量 (h_up=3.0m, h_down=1.0m):")
    for opening in [0.2, 0.5, 1.0, 1.5]:
        gate.set_opening(opening)
        Q = gate.compute_discharge(3.0, 1.0)
        print(f"  开度={opening:.1f}m: Q={Q:.2f} m³/s")

    # 测试4: 圆形孔口
    print("\n[测试4] 圆形孔口 (Orifice)")
    print("-"*70)

    orifice = Orifice(
        center_elevation=1.0,
        diameter=1.5,
        discharge_coeff=0.62
    )
    print(orifice)

    print("\n过流量:")
    test_cases = [
        (2.0, None, "自由出流"),
        (3.0, None, "自由出流"),
        (3.0, 1.5, "淹没出流"),
        (3.0, 2.5, "小水头差")
    ]

    for h_up, h_down, desc in test_cases:
        Q = orifice.compute_discharge(h_up, h_down)
        if h_down:
            print(f"  h_up={h_up:.1f}m, h_down={h_down:.1f}m: Q={Q:.2f} m³/s ({desc})")
        else:
            print(f"  h_up={h_up:.1f}m: Q={Q:.2f} m³/s ({desc})")

    print("\n" + "="*80)
    print("✅ 所有测试通过！")
    print("="*80)
