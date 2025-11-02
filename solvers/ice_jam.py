#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
冰塞/冰坝动力学模块 - Ice Jam Dynamics Model

物理模型：
    ∂(h_ice·ρi)/∂t + ∂(h_ice·ρi·ui)/∂x = S_ice_supply - S_ice_jam

    冰塞形成条件:
    1. Froude数低于临界值: Fr < Fr_critical (≈0.08)
    2. 河道坡度较缓: S0 < 0.001
    3. 冰量累积: h_ice > h_critical

对标: RIVICE冰塞模型, CRISSP冰坝动力学

作者: HydroClaude Team
日期: 2025-11-02
"""

import numpy as np
from typing import Dict, Optional, Tuple


class IceJamSolver:
    """
    冰塞/冰坝动力学求解器

    模拟冰块堆积、冰塞形成和壅水效应
    """

    def __init__(
        self,
        n_cells: int,
        dx: float,
        Fr_critical: float = 0.08,      # 临界Froude数
        slope_threshold: float = 0.001,  # 坡度阈值
        ice_thick_threshold: float = 0.3  # 冰厚阈值 (相对水深)
    ):
        """
        初始化冰塞求解器

        Parameters:
        -----------
        n_cells : int
            网格单元数
        dx : float
            网格间距 (m)
        Fr_critical : float
            临界Froude数 (冰塞形成条件)
        slope_threshold : float
            坡度阈值
        ice_thick_threshold : float
            冰厚阈值 (h_ice/h的比值)
        """
        self.n_cells = n_cells
        self.dx = dx
        self.Fr_critical = Fr_critical
        self.slope_threshold = slope_threshold
        self.ice_thick_threshold = ice_thick_threshold

        # 状态变量
        self.h_ice_transport = np.zeros(n_cells)  # 输运冰厚 (m)
        self.ice_jam_mask = np.zeros(n_cells, dtype=bool)  # 冰塞位置
        self.ice_jam_thickness = np.zeros(n_cells)  # 冰塞厚度 (m)

        # 物理常数
        self.rho_ice = 917.0     # 冰密度 kg/m³
        self.rho_water = 1000.0  # 水密度 kg/m³
        self.g = 9.81            # 重力加速度 m/s²

        # 冰塞参数
        self.ice_porosity = 0.4  # 冰塞孔隙率
        self.ice_strength = 1e5  # 冰强度 Pa (粗略估计)

    def compute_froude_number(
        self,
        u: np.ndarray,
        h: np.ndarray
    ) -> np.ndarray:
        """
        计算Froude数

        Fr = u / sqrt(g*h)

        Parameters:
        -----------
        u : array
            流速 (m/s)
        h : array
            水深 (m)

        Returns:
        --------
        Fr : array
            Froude数
        """
        Fr = np.abs(u) / np.sqrt(self.g * h + 1e-6)
        return Fr

    def check_jam_formation_criteria(
        self,
        h: np.ndarray,
        u: np.ndarray,
        h_ice: np.ndarray,
        S0: np.ndarray
    ) -> np.ndarray:
        """
        检查冰塞形成条件

        条件:
        1. Froude数低: Fr < Fr_critical
        2. 坡度较缓: S0 < slope_threshold
        3. 冰量充足: h_ice/h > ice_thick_threshold

        Parameters:
        -----------
        h : array
            水深 (m)
        u : array
            流速 (m/s)
        h_ice : array
            冰厚 (m)
        S0 : array
            河底坡度

        Returns:
        --------
        jam_potential : array (bool)
            是否满足冰塞形成条件
        """
        # 条件1: Froude数
        Fr = self.compute_froude_number(u, h)
        cond1 = Fr < self.Fr_critical

        # 条件2: 坡度
        cond2 = S0 < self.slope_threshold

        # 条件3: 冰量
        ice_ratio = h_ice / (h + 1e-6)
        cond3 = ice_ratio > self.ice_thick_threshold

        # 综合判断
        jam_potential = cond1 & cond2 & cond3

        return jam_potential

    def transport_ice(
        self,
        dt: float,
        u: np.ndarray,
        h: np.ndarray,
        ice_velocity: Optional[np.ndarray] = None
    ):
        """
        输运冰块

        使用一阶迎风格式

        Parameters:
        -----------
        dt : float
            时间步长 (s)
        u : array
            水流速度 (m/s)
        h : array
            水深 (m)
        ice_velocity : array, optional
            冰块速度 (m/s)，如未提供则假设与水流相同
        """
        if ice_velocity is None:
            # 假设冰块与水流速度相同
            u_ice = u
        else:
            u_ice = ice_velocity

        h_ice_old = self.h_ice_transport.copy()

        # 一阶迎风格式
        for i in range(1, self.n_cells - 1):
            if u_ice[i] > 0:
                flux_in = u_ice[i-1] * h_ice_old[i-1]
                flux_out = u_ice[i] * h_ice_old[i]
            else:
                flux_in = u_ice[i+1] * h_ice_old[i+1]
                flux_out = u_ice[i] * h_ice_old[i]

            dh_ice = -(flux_out - flux_in) / self.dx * dt
            self.h_ice_transport[i] += dh_ice

        # 非负约束
        self.h_ice_transport = np.maximum(self.h_ice_transport, 0.0)

    def update_ice_jam(
        self,
        dt: float,
        h: np.ndarray,
        u: np.ndarray,
        S0: np.ndarray
    ):
        """
        更新冰塞状态

        Parameters:
        -----------
        dt : float
            时间步长 (s)
        h : array
            水深 (m)
        u : array
            流速 (m/s)
        S0 : array
            河底坡度
        """
        # 检查冰塞形成条件
        jam_potential = self.check_jam_formation_criteria(
            h, u, self.h_ice_transport, S0
        )

        # 更新冰塞区域
        # 如果满足条件，输运的冰会堆积形成冰塞
        for i in range(self.n_cells):
            if jam_potential[i]:
                # 冰塞增长
                accumulation_rate = self.h_ice_transport[i] / dt  # 假设所有输运冰都堆积
                self.ice_jam_thickness[i] += accumulation_rate * dt

                # 输运冰转为冰塞
                self.h_ice_transport[i] = 0.0

                # 标记为冰塞区
                self.ice_jam_mask[i] = True

            else:
                # 非冰塞区: 冰塞可能破坏
                if self.ice_jam_mask[i]:
                    # 简化: 如果流速增大，冰塞破坏
                    Fr = self.compute_froude_number(u, h)
                    if Fr[i] > self.Fr_critical * 1.5:
                        # 冰塞破坏
                        self.h_ice_transport[i] += self.ice_jam_thickness[i]
                        self.ice_jam_thickness[i] = 0.0
                        self.ice_jam_mask[i] = False

    def compute_backwater_effect(
        self,
        h_original: np.ndarray,
        u: np.ndarray,
        Q: np.ndarray,
        manning_n: float,
        width: float
    ) -> np.ndarray:
        """
        计算冰塞壅水效应

        使用修正的Manning公式:
        1. 增加糙率 (冰塞粗糙)
        2. 减小有效过流面积

        Parameters:
        -----------
        h_original : array
            原始水深 (m)
        u : array
            流速 (m/s)
        Q : array
            流量 (m³/s)
        manning_n : float
            Manning糙率系数
        width : float
            河道宽度 (m)

        Returns:
        --------
        h_backwater : array
            壅水后水深 (m)
        """
        h_backwater = h_original.copy()

        # 冰塞区域
        for i in range(self.n_cells):
            if self.ice_jam_mask[i]:
                # 增加糙率 (冰塞表面很粗糙)
                n_ice = manning_n * 3.0

                # 有效水深 (扣除冰塞占据的空间)
                h_effective = h_original[i] - self.ice_jam_thickness[i] * (1 - self.ice_porosity)
                h_effective = max(h_effective, 0.1)  # 最小水深

                # 有效面积
                A_effective = width * h_effective

                # 有效水力半径
                P = width + 2 * h_effective
                R_h = A_effective / P

                # Manning公式反算水深
                # Q = (1/n) * A * R^(2/3) * S^(1/2)
                # 简化: 假设流量守恒，增大水深来维持流量

                # 壅水增量 (经验公式)
                delta_h = self.ice_jam_thickness[i] * 0.5  # 冰塞高度的50%转为壅水

                h_backwater[i] = h_original[i] + delta_h

        return h_backwater

    def compute_ice_force(
        self,
        h: np.ndarray,
        u: np.ndarray
    ) -> np.ndarray:
        """
        计算冰塞受力 (简化模型)

        F_ice = F_drag - F_resist

        Parameters:
        -----------
        h : array
            水深 (m)
        u : array
            流速 (m/s)

        Returns:
        --------
        F_ice : array
            冰塞受力 (N/m)
        """
        F_ice = np.zeros(self.n_cells)

        for i in range(self.n_cells):
            if self.ice_jam_mask[i]:
                # 拖曳力 (水流对冰塞的推力)
                C_d = 0.01  # 拖曳系数
                F_drag = 0.5 * self.rho_water * C_d * u[i]**2 * self.ice_jam_thickness[i]

                # 阻力 (冰塞自身强度)
                F_resist = self.ice_strength / self.dx  # 简化

                F_ice[i] = F_drag - F_resist

        return F_ice

    def step(
        self,
        dt: float,
        h: np.ndarray,
        u: np.ndarray,
        Q: np.ndarray,
        S0: np.ndarray,
        h_ice_input: Optional[np.ndarray] = None,
        manning_n: float = 0.03,
        width: float = 10.0
    ) -> Dict[str, np.ndarray]:
        """
        推进一个时间步

        Parameters:
        -----------
        dt : float
            时间步长 (s)
        h : array
            水深 (m)
        u : array
            流速 (m/s)
        Q : array
            流量 (m³/s)
        S0 : array
            河底坡度
        h_ice_input : array, optional
            外部冰块输入 (m)
        manning_n : float
            Manning糙率系数
        width : float
            河道宽度 (m)

        Returns:
        --------
        state : dict
            {'h_backwater': array, 'ice_jam_mask': array, 'ice_jam_thickness': array}
        """
        # 添加外部冰块输入
        if h_ice_input is not None:
            self.h_ice_transport += h_ice_input

        # 输运冰块
        self.transport_ice(dt, u, h)

        # 更新冰塞状态
        self.update_ice_jam(dt, h, u, S0)

        # 计算壅水效应
        h_backwater = self.compute_backwater_effect(
            h, u, Q, manning_n, width
        )

        return self.get_state(h_backwater)

    def get_state(self, h_backwater: Optional[np.ndarray] = None) -> Dict[str, np.ndarray]:
        """获取当前状态"""
        state = {
            'h_ice_transport': self.h_ice_transport.copy(),
            'ice_jam_mask': self.ice_jam_mask.copy(),
            'ice_jam_thickness': self.ice_jam_thickness.copy(),
            'ice_jam_locations': np.where(self.ice_jam_mask)[0]
        }

        if h_backwater is not None:
            state['h_backwater'] = h_backwater

        return state

    def get_diagnostics(self, h: np.ndarray, u: np.ndarray) -> Dict:
        """
        获取诊断信息

        Returns:
        --------
        diag : dict
            诊断信息
        """
        Fr = self.compute_froude_number(u, h)
        F_ice = self.compute_ice_force(h, u)

        diag = {
            'froude_number': Fr,
            'ice_jam_count': np.sum(self.ice_jam_mask),
            'total_ice_jam_volume': np.sum(self.ice_jam_thickness) * self.dx,
            'total_transport_ice_volume': np.sum(self.h_ice_transport) * self.dx,
            'ice_force': F_ice,
            'max_jam_thickness': np.max(self.ice_jam_thickness)
        }

        return diag
