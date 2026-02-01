#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
冰盖下明渠水力学模块 - Ice-Covered Channel Hydraulics

南水北调中线工程冰期调度关键技术：
1. 冰盖下Saint-Venant方程修正
2. 复合糙率计算（Sabaneev公式、加权平均法、双层流速分布法）
3. 冰盖下水力半径修正
4. 冰情对过流能力的影响

技术来源：
- 南水北调中线冰期输水实践
- MIKE ICE河冰动力学模型
- RIVICE冰情预报系统

作者: HydroClaude Team
日期: 2025-11-02
"""

import numpy as np
from typing import Dict, Optional, Tuple, Literal
from enum import Enum


class CompositeRoughnessMethod(Enum):
    """复合糙率计算方法"""
    SABANEEV = "sabaneev"          # Sabaneev公式（苏联经验公式）
    WEIGHTED_AVERAGE = "weighted"   # 加权平均法（美国COE方法）
    DOUBLE_LAYER = "double_layer"   # 双层流速分布法


class IceCoveredChannelHydraulics:
    """
    冰盖下明渠水力学求解器

    核心功能：
    - 复合糙率计算（考虑冰底和渠床双重阻力）
    - 冰盖下水力半径修正
    - 冰盖下过流能力计算
    - 冰盖对Saint-Venant方程的影响

    适用场景：
    - 南水北调中线京石段冰期输水
    - 北方明渠冬季输水工程
    - 河冰动力学模拟
    """

    def __init__(
        self,
        n_bed: float = 0.015,      # 渠床曼宁糙率（混凝土衬砌）
        n_ice_smooth: float = 0.010,  # 光滑冰底糙率
        n_ice_rough: float = 0.025,   # 粗糙冰底糙率
        kappa: float = 0.4,        # 卡门常数
        g: float = 9.81            # 重力加速度 (m/s²)
    ):
        """
        初始化冰盖下水力学求解器

        Parameters
        ----------
        n_bed : float
            渠床曼宁糙率，混凝土衬砌典型值0.015
        n_ice_smooth : float
            光滑冰盖底面糙率，典型值0.008-0.012
        n_ice_rough : float
            粗糙冰盖/冰塞底面糙率，典型值0.020-0.035
        kappa : float
            卡门常数，约0.4
        g : float
            重力加速度 (m/s²)
        """
        self.n_bed = n_bed
        self.n_ice_smooth = n_ice_smooth
        self.n_ice_rough = n_ice_rough
        self.kappa = kappa
        self.g = g

    def compute_composite_roughness(
        self,
        P_bed: np.ndarray,
        P_ice: np.ndarray,
        n_ice: Optional[np.ndarray] = None,
        method: CompositeRoughnessMethod = CompositeRoughnessMethod.SABANEEV
    ) -> np.ndarray:
        """
        计算冰盖下明渠的复合糙率

        冰盖形成后，渠道从三边界约束变为四边界约束，
        需要综合考虑渠床和冰底的双重阻力。

        Parameters
        ----------
        P_bed : np.ndarray
            渠床湿周 (m)
        P_ice : np.ndarray
            冰盖接触湿周 (m)
        n_ice : np.ndarray, optional
            冰底糙率，若不指定则使用默认光滑冰底糙率
        method : CompositeRoughnessMethod
            复合糙率计算方法

        Returns
        -------
        n_composite : np.ndarray
            复合曼宁糙率
        """
        if n_ice is None:
            n_ice = np.full_like(P_bed, self.n_ice_smooth)

        n_bed = self.n_bed

        if method == CompositeRoughnessMethod.SABANEEV:
            # Sabaneev公式（苏联经验公式）
            # n_c = [(n_bed^1.5 * P_bed + n_ice^1.5 * P_ice) / (P_bed + P_ice)]^(2/3)
            numerator = n_bed**1.5 * P_bed + n_ice**1.5 * P_ice
            denominator = P_bed + P_ice + 1e-10
            n_composite = (numerator / denominator) ** (2/3)

        elif method == CompositeRoughnessMethod.WEIGHTED_AVERAGE:
            # 加权平均法（美国COE方法）
            # n_c = [(n_bed^2 * P_bed + n_ice^2 * P_ice) / (P_bed + P_ice)]^0.5
            numerator = n_bed**2 * P_bed + n_ice**2 * P_ice
            denominator = P_bed + P_ice + 1e-10
            n_composite = np.sqrt(numerator / denominator)

        elif method == CompositeRoughnessMethod.DOUBLE_LAYER:
            # 双层流速分布法（理论推导）
            # 基于对数流速分布假设，更精确但计算复杂
            # 简化近似：取几何平均
            n_composite = np.sqrt(n_bed * n_ice)

        else:
            raise ValueError(f"未知的复合糙率计算方法: {method}")

        return n_composite

    def compute_hydraulic_radius_ice_covered(
        self,
        A: np.ndarray,
        P_bed: np.ndarray,
        P_ice: np.ndarray
    ) -> np.ndarray:
        """
        计算冰盖下明渠的水力半径

        R_ice = A / (P_bed + P_ice)

        相比开敞明渠，冰盖使水力半径减小约50%（宽浅渠道），
        导致过流能力显著下降。

        Parameters
        ----------
        A : np.ndarray
            过水断面积 (m²)
        P_bed : np.ndarray
            渠床湿周 (m)
        P_ice : np.ndarray
            冰盖接触湿周 (m)

        Returns
        -------
        R_h : np.ndarray
            冰盖下水力半径 (m)
        """
        P_total = P_bed + P_ice
        R_h = A / (P_total + 1e-10)
        return R_h

    def compute_friction_slope_ice_covered(
        self,
        Q: np.ndarray,
        A: np.ndarray,
        R_h: np.ndarray,
        n_composite: np.ndarray
    ) -> np.ndarray:
        """
        计算冰盖下的摩阻坡降

        使用Manning公式：
        S_f = (n * Q / A / R^(2/3))²

        Parameters
        ----------
        Q : np.ndarray
            流量 (m³/s)
        A : np.ndarray
            过水断面积 (m²)
        R_h : np.ndarray
            水力半径 (m)
        n_composite : np.ndarray
            复合糙率

        Returns
        -------
        S_f : np.ndarray
            摩阻坡降
        """
        V = Q / (A + 1e-10)
        S_f = (n_composite * V / R_h**(2/3) + 1e-10)**2
        return S_f

    def compute_flow_capacity_reduction(
        self,
        h: np.ndarray,
        B: float,
        h_ice: np.ndarray,
        ice_fraction: np.ndarray
    ) -> Dict[str, np.ndarray]:
        """
        计算冰盖导致的过流能力折减

        冰盖对过流能力的影响：
        1. 有效过水面积减小
        2. 复合糙率增大
        3. 水力半径减小

        Parameters
        ----------
        h : np.ndarray
            水深 (m)
        B : float
            渠道宽度 (m)
        h_ice : np.ndarray
            冰盖厚度 (m)
        ice_fraction : np.ndarray
            冰盖覆盖率 (0-1)

        Returns
        -------
        result : dict
            包含：
            - A_effective: 有效过水面积
            - P_bed: 渠床湿周
            - P_ice: 冰盖湿周
            - R_h: 水力半径
            - n_composite: 复合糙率
            - capacity_ratio: 过流能力比（相对于无冰状态）
        """
        n_cells = len(h)

        # 原始过水面积（无冰）
        A_open = B * h
        P_bed = B + 2 * h  # 渠床湿周（矩形断面）
        R_open = A_open / P_bed

        # 冰盖下过水面积
        h_effective = h - h_ice * (1 - 0.1)  # 考虑冰的浮力，冰下沉约10%
        h_effective = np.maximum(h_effective, 0.1)  # 最小水深
        A_effective = B * h_effective

        # 冰盖湿周（矩形断面，仅顶部）
        P_ice = B * ice_fraction

        # 冰盖下水力半径
        P_total = P_bed + P_ice
        R_ice = A_effective / (P_total + 1e-10)

        # 复合糙率
        n_ice = np.where(
            ice_fraction > 0.5,
            self.n_ice_rough,  # 高覆盖率用粗糙糙率
            self.n_ice_smooth  # 低覆盖率用光滑糙率
        )
        n_composite = self.compute_composite_roughness(
            P_bed, P_ice, n_ice,
            method=CompositeRoughnessMethod.SABANEEV
        )

        # 过流能力比（Manning公式比值）
        # Q = (1/n) * A * R^(2/3) * S^0.5
        # 比值 = (A_ice/A_open) * (R_ice/R_open)^(2/3) * (n_open/n_ice)
        capacity_ratio = np.where(
            ice_fraction > 0.01,
            (A_effective / A_open) * (R_ice / R_open)**(2/3) * (self.n_bed / n_composite),
            1.0
        )
        capacity_ratio = np.clip(capacity_ratio, 0.1, 1.0)

        return {
            'A_effective': A_effective,
            'P_bed': P_bed,
            'P_ice': P_ice,
            'R_h': R_ice,
            'n_composite': n_composite,
            'capacity_ratio': capacity_ratio
        }

    def modify_saint_venant_for_ice(
        self,
        h: np.ndarray,
        u: np.ndarray,
        Q: np.ndarray,
        B: float,
        h_ice: np.ndarray,
        ice_fraction: np.ndarray,
        S0: np.ndarray
    ) -> Dict[str, np.ndarray]:
        """
        修正Saint-Venant方程以考虑冰盖影响

        冰盖下的动量方程需要修正摩阻项：
        ∂Q/∂t + ∂(Q²/A)/∂x + gA∂h/∂x + gA*S_f_composite = 0

        Parameters
        ----------
        h : np.ndarray
            水深 (m)
        u : np.ndarray
            流速 (m/s)
        Q : np.ndarray
            流量 (m³/s)
        B : float
            渠道宽度 (m)
        h_ice : np.ndarray
            冰盖厚度 (m)
        ice_fraction : np.ndarray
            冰盖覆盖率 (0-1)
        S0 : np.ndarray
            底坡

        Returns
        -------
        modified : dict
            修正后的水力学参数
        """
        # 计算冰盖影响
        capacity = self.compute_flow_capacity_reduction(h, B, h_ice, ice_fraction)

        # 修正摩阻坡降
        S_f = self.compute_friction_slope_ice_covered(
            Q, capacity['A_effective'], capacity['R_h'], capacity['n_composite']
        )

        # 冰盖下的有效流速
        u_effective = Q / (capacity['A_effective'] + 1e-10)

        # 计算Froude数（用于冰塞判断）
        Fr = np.abs(u_effective) / np.sqrt(self.g * (h - h_ice) + 1e-6)

        return {
            'u_effective': u_effective,
            'A_effective': capacity['A_effective'],
            'R_h': capacity['R_h'],
            'n_composite': capacity['n_composite'],
            'S_f': S_f,
            'Fr': Fr,
            'capacity_ratio': capacity['capacity_ratio']
        }


class JingShiSegmentHydraulics:
    """
    京石段特定水力学参数

    南水北调中线京石段（217km）冬季输水关键参数：
    - 渠道断面：梯形/矩形混合
    - 典型水深：2.0-4.0m
    - 设计流量：350 m³/s（常规）/ 58-28 m³/s（冰期）
    - 曼宁糙率：0.015（混凝土衬砌）
    """

    # 京石段节制闸信息（14座）
    JINGSHI_GATES = [
        {"name": "岗头", "chainage": 0.0, "width": 30.0},
        {"name": "古运河", "chainage": 15.5, "width": 28.0},
        {"name": "漳河", "chainage": 35.2, "width": 32.0},
        {"name": "滏阳河", "chainage": 52.8, "width": 30.0},
        {"name": "七里河", "chainage": 72.0, "width": 28.0},
        {"name": "午河", "chainage": 88.5, "width": 26.0},
        {"name": "泜河", "chainage": 105.0, "width": 30.0},
        {"name": "沙河", "chainage": 122.3, "width": 32.0},
        {"name": "洺河", "chainage": 138.6, "width": 28.0},
        {"name": "李阳河", "chainage": 155.0, "width": 26.0},
        {"name": "槐河", "chainage": 171.5, "width": 30.0},
        {"name": "蒲阳河", "chainage": 188.0, "width": 28.0},
        {"name": "南拒马河", "chainage": 202.5, "width": 30.0},
        {"name": "北拒马河", "chainage": 217.0, "width": 32.0},
    ]

    # 冰期输水控制参数（南水北调中线实测）
    ICE_PERIOD_PARAMS = {
        'Fr_critical_upstream': 0.065,    # 上游控制断面临界Froude数
        'Fr_critical_downstream': 0.055,  # 下游控制断面临界Froude数
        'V_max_upstream': 0.40,           # 上游控制断面最大流速 (m/s)
        'V_max_downstream': 0.35,         # 下游控制断面最大流速 (m/s)
        'T_trigger': 1.2,                 # 冰期调度触发水温 (°C)
        'Q_normal': 350.0,                # 常规输水流量 (m³/s)
        'Q_ice_high': 58.0,               # 冰期高流量 (m³/s)
        'Q_ice_low': 28.0,                # 冰期低流量 (m³/s)
        'h_ice_max': 0.32,                # 实测最大冰厚 (m)
        'K_wa': 18.0,                     # 水面热交换系数 W/(m²·K)
    }

    def __init__(self, n_cells: int = 217):
        """
        初始化京石段水力学参数

        Parameters
        ----------
        n_cells : int
            网格数量，默认217（每公里1个网格）
        """
        self.n_cells = n_cells
        self.L = 217000.0  # 京石段总长217km
        self.dx = self.L / n_cells

        # 初始化水力学求解器
        self.hydraulics = IceCoveredChannelHydraulics(
            n_bed=0.015,  # 混凝土衬砌
            n_ice_smooth=0.010,
            n_ice_rough=0.025
        )

        # 生成断面参数（沿程变化）
        self._initialize_cross_sections()

    def _initialize_cross_sections(self):
        """初始化沿程断面参数"""
        x = np.linspace(0, self.L, self.n_cells)

        # 河宽沿程变化（从30m渐变）
        self.width = 30.0 + 5.0 * np.sin(2 * np.pi * x / self.L)

        # 底坡（总体较平缓）
        self.S0 = np.full(self.n_cells, 0.0001)  # 万分之一

        # 设计水深
        self.h_design = np.full(self.n_cells, 3.0)  # 3m设计水深

    def get_gate_locations(self) -> np.ndarray:
        """获取节制闸位置（网格索引）"""
        gate_indices = []
        for gate in self.JINGSHI_GATES:
            idx = int(gate['chainage'] * 1000 / self.dx)
            idx = min(idx, self.n_cells - 1)
            gate_indices.append(idx)
        return np.array(gate_indices)

    def check_ice_period_constraints(
        self,
        u: np.ndarray,
        h: np.ndarray,
        T_water: np.ndarray
    ) -> Dict[str, np.ndarray]:
        """
        检查冰期输水约束条件

        约束条件（南水北调中线实践）：
        - 流速约束：V ≤ 0.40 m/s（上游）/ 0.35 m/s（下游）
        - Froude数约束：Fr ≤ 0.065（上游）/ 0.055（下游）
        - 水温触发：T_w ≤ 1.2℃ 启动冰期调度

        Parameters
        ----------
        u : np.ndarray
            流速 (m/s)
        h : np.ndarray
            水深 (m)
        T_water : np.ndarray
            水温 (°C)

        Returns
        -------
        constraints : dict
            约束检查结果
        """
        params = self.ICE_PERIOD_PARAMS
        g = 9.81

        # 计算Froude数
        Fr = np.abs(u) / np.sqrt(g * h + 1e-6)

        # 划分上下游（以蒲阳河为界，约188km处）
        upstream_mask = np.arange(self.n_cells) < int(188000 / self.dx)
        downstream_mask = ~upstream_mask

        # 流速约束检查
        V_limit = np.where(upstream_mask, params['V_max_upstream'], params['V_max_downstream'])
        velocity_violation = np.abs(u) > V_limit

        # Froude数约束检查
        Fr_limit = np.where(upstream_mask, params['Fr_critical_upstream'], params['Fr_critical_downstream'])
        froude_violation = Fr > Fr_limit

        # 水温触发检查
        ice_period_triggered = T_water <= params['T_trigger']

        # 综合安全状态
        safe = ~(velocity_violation | froude_violation)

        return {
            'Fr': Fr,
            'Fr_limit': Fr_limit,
            'velocity_violation': velocity_violation,
            'froude_violation': froude_violation,
            'ice_period_triggered': ice_period_triggered,
            'safe': safe,
            'violation_count': np.sum(velocity_violation) + np.sum(froude_violation)
        }

    def compute_ice_period_flow_reduction(
        self,
        T_water_avg: float,
        T_air_forecast: float
    ) -> float:
        """
        计算冰期输水流量调减

        动态调度模式：
        当水温下降至1.2℃左右时，开始调减对应输水流量

        Parameters
        ----------
        T_water_avg : float
            平均水温 (°C)
        T_air_forecast : float
            气温预报 (°C)

        Returns
        -------
        Q_target : float
            目标流量 (m³/s)
        """
        params = self.ICE_PERIOD_PARAMS

        if T_water_avg > params['T_trigger'] + 1.0:
            # 常规输水
            Q_target = params['Q_normal']
        elif T_water_avg > params['T_trigger']:
            # 过渡期，线性调减
            ratio = (T_water_avg - params['T_trigger']) / 1.0
            Q_target = params['Q_ice_high'] + ratio * (params['Q_normal'] - params['Q_ice_high'])
        else:
            # 冰期输水
            if T_air_forecast < -10:
                # 极端低温，最低流量
                Q_target = params['Q_ice_low']
            else:
                # 正常冰期
                Q_target = params['Q_ice_high']

        return Q_target
