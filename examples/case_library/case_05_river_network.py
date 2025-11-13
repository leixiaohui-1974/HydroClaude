# -*- coding: utf-8 -*-
"""
HydroClaude Engineering Case 05: River Network System
HydroClaude 工程案例 05: 河网系统

This case demonstrates:
此案例演示:
- Natural river network with multiple tributaries / 多支流天然河网
- Flood routing and propagation / 洪水演进与传播
- River confluence modeling / 河流汇流模拟
- Compound channel cross-sections / 复式河道断面
- Flood diversion gates / 分洪闸调度
- Stage-discharge relationships / 水位-流量关系

Author: HydroClaude Development Team
Date: 2025-10-30
"""

import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import math

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
    from scipy.interpolate import interp1d
    from scipy.integrate import solve_ivp
except ImportError as e:
    print(f"Warning: {e}")
    print("Please install required packages: pip install numpy matplotlib scipy")


@dataclass
class CompoundChannel:
    """
    Compound channel cross-section (main channel + floodplains)
    复式河道断面（主槽 + 滩地）

    Typical cross-section:
    典型断面:
        Left floodplain | Main channel | Right floodplain
        左滩地          |    主槽      |   右滩地
    """
    # Main channel / 主槽
    main_width: float  # Bottom width (m) / 底宽
    main_depth: float  # Bank-full depth (m) / 槽深
    main_side_slope: float  # Side slope (H:V) / 边坡
    main_manning_n: float  # Manning's n / 曼宁系数

    # Floodplains / 滩地
    left_floodplain_width: float  # Width (m) / 宽度
    right_floodplain_width: float  # Width (m) / 宽度
    floodplain_manning_n: float  # Manning's n / 曼宁系数

    def get_area(self, depth: float) -> float:
        """
        Calculate flow area at given depth
        计算给定水深的过流面积

        Args:
            depth: Water depth (m) / 水深

        Returns:
            Flow area (m^2) / 过流面积
        """
        if depth <= 0:
            return 0.0

        if depth <= self.main_depth:
            # Flow only in main channel / 仅主槽过流
            b = self.main_width + 2 * self.main_side_slope * depth
            area = (self.main_width + b) / 2 * depth
            return area
        else:
            # Flow in main channel + floodplains / 主槽+滩地过流
            # Main channel area / 主槽面积
            b_main = self.main_width + 2 * self.main_side_slope * self.main_depth
            area_main = (self.main_width + b_main) / 2 * self.main_depth

            # Floodplain area / 滩地面积
            h_flood = depth - self.main_depth
            area_flood = (self.left_floodplain_width + self.right_floodplain_width) * h_flood

            return area_main + area_flood

    def get_wetted_perimeter(self, depth: float) -> float:
        """
        Calculate wetted perimeter at given depth
        计算给定水深的湿周

        Args:
            depth: Water depth (m) / 水深

        Returns:
            Wetted perimeter (m) / 湿周
        """
        if depth <= 0:
            return 0.0

        if depth <= self.main_depth:
            # Only main channel / 仅主槽
            side_length = depth * math.sqrt(1 + self.main_side_slope ** 2)
            perimeter = self.main_width + 2 * side_length
            return perimeter
        else:
            # Main channel + floodplains / 主槽+滩地
            # Main channel perimeter (without top width) / 主槽湿周（不含顶宽）
            side_length = self.main_depth * math.sqrt(1 + self.main_side_slope ** 2)
            p_main = self.main_width + 2 * side_length

            # Floodplain perimeter / 滩地湿周
            h_flood = depth - self.main_depth
            p_flood = self.left_floodplain_width + self.right_floodplain_width

            return p_main + p_flood

    def get_top_width(self, depth: float) -> float:
        """
        Calculate top width at given depth
        计算给定水深的水面宽

        Args:
            depth: Water depth (m) / 水深

        Returns:
            Top width (m) / 水面宽
        """
        if depth <= 0:
            return 0.0

        if depth <= self.main_depth:
            # Only main channel / 仅主槽
            width = self.main_width + 2 * self.main_side_slope * depth
            return width
        else:
            # Main channel + floodplains / 主槽+滩地
            width_main = self.main_width + 2 * self.main_side_slope * self.main_depth
            width_total = width_main + self.left_floodplain_width + self.right_floodplain_width
            return width_total

    def get_hydraulic_radius(self, depth: float) -> float:
        """Calculate hydraulic radius / 计算水力半径"""
        A = self.get_area(depth)
        P = self.get_wetted_perimeter(depth)
        return A / P if P > 0 else 0.0

    def get_conveyance(self, depth: float, slope: float) -> float:
        """
        Calculate conveyance using Manning's equation
        使用曼宁公式计算输水能力

        K = (1/n) * A * R^(2/3)
        Q = K * sqrt(S0)

        Args:
            depth: Water depth (m) / 水深
            slope: Channel slope / 河道坡度

        Returns:
            Conveyance / 输水能力
        """
        if depth <= 0:
            return 0.0

        if depth <= self.main_depth:
            # Only main channel / 仅主槽
            A = self.get_area(depth)
            R = self.get_hydraulic_radius(depth)
            K = (1.0 / self.main_manning_n) * A * (R ** (2.0/3.0))
            return K
        else:
            # Main channel + floodplains (divided channel method) / 主槽+滩地（分区法）
            # Main channel / 主槽
            b_main = self.main_width + 2 * self.main_side_slope * self.main_depth
            A_main = (self.main_width + b_main) / 2 * self.main_depth
            side_length = self.main_depth * math.sqrt(1 + self.main_side_slope ** 2)
            P_main = self.main_width + 2 * side_length
            R_main = A_main / P_main if P_main > 0 else 0.0
            K_main = (1.0 / self.main_manning_n) * A_main * (R_main ** (2.0/3.0))

            # Floodplains / 滩地
            h_flood = depth - self.main_depth
            A_flood = (self.left_floodplain_width + self.right_floodplain_width) * h_flood
            P_flood = self.left_floodplain_width + self.right_floodplain_width
            R_flood = A_flood / P_flood if P_flood > 0 else 0.0
            K_flood = (1.0 / self.floodplain_manning_n) * A_flood * (R_flood ** (2.0/3.0))

            return K_main + K_flood


class RiverReach:
    """
    River reach segment
    河段
    """

    def __init__(self,
                 name: str,
                 length: float,
                 slope: float,
                 cross_section: CompoundChannel,
                 n_cells: int = 50):
        """
        Initialize river reach
        初始化河段

        Args:
            name: Reach name / 河段名称
            length: Reach length (m) / 河段长度
            slope: Average slope / 平均坡度
            cross_section: Cross-section geometry / 断面几何
            n_cells: Number of computational cells / 计算单元数
        """
        self.name = name
        self.L = length
        self.S0 = slope
        self.xs = cross_section
        self.n_cells = n_cells
        self.dx = length / n_cells

        # Initialize state variables / 初始化状态变量
        self.depths = np.zeros(n_cells)
        self.flows = np.zeros(n_cells)
        self.velocities = np.zeros(n_cells)

        # Upstream and downstream boundary conditions / 上下游边界条件
        self.upstream_bc = None  # 'flow' or 'stage'
        self.downstream_bc = None

    def set_initial_condition(self, depth: float = 1.0, flow: float = 100.0):
        """
        Set initial conditions
        设置初始条件

        Args:
            depth: Initial depth (m) / 初始水深
            flow: Initial flow (m^3/s) / 初始流量
        """
        self.depths[:] = depth
        self.flows[:] = flow

        # Calculate initial velocities / 计算初始流速
        for i in range(self.n_cells):
            A = self.xs.get_area(self.depths[i])
            self.velocities[i] = self.flows[i] / A if A > 0 else 0.0

    def calculate_normal_depth(self, flow: float) -> float:
        """
        Calculate normal depth using Manning's equation
        使用曼宁公式计算正常水深

        Args:
            flow: Flow rate (m^3/s) / 流量

        Returns:
            Normal depth (m) / 正常水深
        """
        if flow <= 0:
            return 0.0

        # Iterative solution / 迭代求解
        depth = 2.0  # Initial guess

        for _ in range(100):
            K = self.xs.get_conveyance(depth, self.S0)
            Q_calc = K * math.sqrt(self.S0)

            error = flow - Q_calc
            if abs(error) < 0.01:
                break

            # Adjust depth / 调整水深
            if error > 0:
                depth *= 1.05
            else:
                depth *= 0.95

        return depth


class FloodDiversionGate:
    """
    Flood diversion gate for river flood control
    分洪闸，用于河道防洪调度
    """

    def __init__(self,
                 name: str,
                 crest_elevation: float,
                 gate_width: float,
                 max_opening: float,
                 trigger_stage: float):
        """
        Initialize flood diversion gate
        初始化分洪闸

        Args:
            name: Gate name / 闸门名称
            crest_elevation: Crest elevation (m) / 堰顶高程
            gate_width: Gate width (m) / 闸门宽度
            max_opening: Maximum gate opening (m) / 最大开度
            trigger_stage: Water stage to trigger opening (m) / 启用水位
        """
        self.name = name
        self.z_crest = crest_elevation
        self.width = gate_width
        self.max_opening = max_opening
        self.trigger_stage = trigger_stage

        self.opening = 0.0  # Current opening (m) / 当前开度
        self.flow = 0.0  # Current flow (m^3/s) / 当前流量

    def update(self, water_stage: float, dt: float = 60.0) -> float:
        """
        Update gate operation based on water stage
        根据水位更新闸门运行

        Args:
            water_stage: Current water stage (m) / 当前水位
            dt: Time step (s) / 时间步长

        Returns:
            Diversion flow (m^3/s) / 分洪流量
        """
        # Gate opening logic / 闸门开启逻辑
        if water_stage >= self.trigger_stage:
            # Open gate gradually / 逐渐开启
            target_opening = self.max_opening * min(1.0, (water_stage - self.trigger_stage) / 2.0)
            opening_rate = 0.1  # m/min
            max_change = opening_rate * (dt / 60.0)
            if target_opening > self.opening:
                self.opening = min(self.opening + max_change, target_opening, self.max_opening)
            else:
                self.opening = max(self.opening - max_change, target_opening, 0.0)
        else:
            # Close gate gradually / 逐渐关闭
            closing_rate = 0.05  # m/min
            self.opening = max(0.0, self.opening - closing_rate * (dt / 60.0))

        # Calculate flow through gate / 计算过闸流量
        if self.opening > 0 and water_stage > self.z_crest:
            # Broad-crested weir formula / 堰流公式
            h = water_stage - self.z_crest
            if h > 0:
                # Free flow / 自由出流
                C = 1.7  # Discharge coefficient
                self.flow = C * self.width * self.opening * math.sqrt(2 * 9.81 * h)
            else:
                self.flow = 0.0
        else:
            self.flow = 0.0

        return self.flow


class RiverNetworkSystem:
    """
    River network system with multiple tributaries
    多支流河网系统
    """

    def __init__(self):
        """Initialize river network system / 初始化河网系统"""
        self.reaches: Dict[str, RiverReach] = {}
        self.junctions: Dict[str, Dict] = {}
        self.gates: List[FloodDiversionGate] = []
        self.time = 0.0

        # Setup network / 设置河网
        self._setup_river_network()
        self._setup_flood_gates()

    def _setup_river_network(self):
        """
        Setup river network topology
        设置河网拓扑

        Network structure / 河网结构:

        Tributary 1 (支流1) ─┐
                              ├─> Main River Upper (干流上游) ─> Main River Middle (干流中游)
        Tributary 2 (支流2) ─┘                                        ↓
                                                               Main River Lower (干流下游)
        """
        print("Setting up river network...")

        # Tributary 1 / 支流1
        xs_trib1 = CompoundChannel(
            main_width=30.0,
            main_depth=3.0,
            main_side_slope=2.0,
            main_manning_n=0.030,
            left_floodplain_width=50.0,
            right_floodplain_width=50.0,
            floodplain_manning_n=0.045
        )
        self.reaches['tributary_1'] = RiverReach(
            name='Tributary 1',
            length=15000.0,  # 15 km
            slope=0.0008,
            cross_section=xs_trib1,
            n_cells = 100
        )

        # Tributary 2 / 支流2
        xs_trib2 = CompoundChannel(
            main_width=25.0,
            main_depth=2.5,
            main_side_slope=2.0,
            main_manning_n=0.030,
            left_floodplain_width=40.0,
            right_floodplain_width=40.0,
            floodplain_manning_n=0.045
        )
        self.reaches['tributary_2'] = RiverReach(
            name='Tributary 2',
            length=12000.0,  # 12 km
            slope=0.001,
            cross_section=xs_trib2,
            n_cells = 100
        )

        # Main River Upper / 干流上游
        xs_main_upper = CompoundChannel(
            main_width=50.0,
            main_depth=4.0,
            main_side_slope=2.5,
            main_manning_n=0.028,
            left_floodplain_width=100.0,
            right_floodplain_width=100.0,
            floodplain_manning_n=0.040
        )
        self.reaches['main_upper'] = RiverReach(
            name='Main River Upper',
            length=20000.0,  # 20 km
            slope=0.0005,
            cross_section=xs_main_upper,
            n_cells = 100
        )

        # Main River Middle / 干流中游
        xs_main_middle = CompoundChannel(
            main_width=60.0,
            main_depth=5.0,
            main_side_slope=3.0,
            main_manning_n=0.028,
            left_floodplain_width=150.0,
            right_floodplain_width=150.0,
            floodplain_manning_n=0.040
        )
        self.reaches['main_middle'] = RiverReach(
            name='Main River Middle',
            length=25000.0,  # 25 km
            slope=0.0003,
            cross_section=xs_main_middle,
            n_cells = 100
        )

        # Main River Lower / 干流下游
        xs_main_lower = CompoundChannel(
            main_width=80.0,
            main_depth=6.0,
            main_side_slope=3.0,
            main_manning_n=0.030,
            left_floodplain_width=200.0,
            right_floodplain_width=200.0,
            floodplain_manning_n=0.045
        )
        self.reaches['main_lower'] = RiverReach(
            name='Main River Lower',
            length=30000.0,  # 30 km
            slope=0.0002,
            cross_section=xs_main_lower,
            n_cells = 100
        )

        print(f" Created {len(self.reaches)} river reaches")

        # Set initial conditions / 设置初始条件
        for reach in self.reaches.values():
            reach.set_initial_condition(depth=2.0, flow=50.0)

    def _setup_flood_gates(self):
        """
        Setup flood diversion gates
        设置分洪闸
        """
        # Gate 1: On main river middle reach / 闸1：干流中游
        gate1 = FloodDiversionGate(
            name='Diversion Gate 1',
            crest_elevation=100.0,
            gate_width=20.0,
            max_opening=3.0,
            trigger_stage=104.0  # Trigger at 4m above crest
        )
        self.gates.append(gate1)

        # Gate 2: On main river lower reach / 闸2：干流下游
        gate2 = FloodDiversionGate(
            name='Diversion Gate 2',
            crest_elevation=95.0,
            gate_width=25.0,
            max_opening=3.5,
            trigger_stage=99.5  # Trigger at 4.5m above crest
        )
        self.gates.append(gate2)

        print(f" Created {len(self.gates)} flood diversion gates")

    def create_flood_hydrograph(self, peak_flow: float, time_to_peak: float, duration: float) -> Tuple:
        """
        Create flood hydrograph (triangular shape)
        创建洪水过程线（三角形）

        Args:
            peak_flow: Peak flow (m^3/s) / 洪峰流量
            time_to_peak: Time to peak (hours) / 涨洪历时
            duration: Total duration (hours) / 总历时

        Returns:
            (times, flows) arrays / 时间和流量数组
        """
        times_hr = np.linspace(0, duration, int(duration * 6))  # 10-min intervals
        flows = np.zeros_like(times_hr)

        base_flow = peak_flow * 0.1  # Base flow / 基流

        for i, t in enumerate(times_hr):
            if t <= time_to_peak:
                # Rising limb / 涨水段
                flows[i] = base_flow + (peak_flow - base_flow) * (t / time_to_peak)
            else:
                # Recession limb / 退水段
                recession_time = duration - time_to_peak
                flows[i] = peak_flow - (peak_flow - base_flow) * ((t - time_to_peak) / recession_time)

        return times_hr, flows

    def simulate_flood_event(self,
                            tributary_1_peak: float = 500.0,
                            tributary_2_peak: float = 400.0,
                            duration: float = 48.0,
                            dt: float = 600.0):
        """
        Simulate flood event propagation through river network
        模拟洪水在河网中的演进

        Args:
            tributary_1_peak: Peak flow from tributary 1 (m^3/s) / 支流1洪峰
            tributary_2_peak: Peak flow from tributary 2 (m^3/s) / 支流2洪峰
            duration: Simulation duration (hours) / 模拟时长
            dt: Time step (s) / 时间步长
        """
        print(f"\n{'='*70}")
        print(f"Simulating flood event in river network")
        print(f"模拟河网洪水演进")
        print(f"{'='*70}\n")

        print(f"Tributary 1 peak flow / 支流1洪峰: {tributary_1_peak:.0f} m^3/s")
        print(f"Tributary 2 peak flow / 支流2洪峰: {tributary_2_peak:.0f} m^3/s")
        print(f"Duration / 历时: {duration:.1f} hours")
        print(f"Time step / 时间步长: {dt:.0f} s\n")

        # Create flood hydrographs / 创建洪水过程线
        times_hr_1, flows_1 = self.create_flood_hydrograph(tributary_1_peak, 12.0, duration)
        times_hr_2, flows_2 = self.create_flood_hydrograph(tributary_2_peak, 10.0, duration)

        # Simulation time loop / 时间循环
        n_steps = int(duration * 3600 / dt)
        times = np.zeros(n_steps)

        # Result storage / 结果存储
        results = {
            'times': times,
            'trib1_outflow': np.zeros(n_steps),
            'trib2_outflow': np.zeros(n_steps),
            'main_upper_outflow': np.zeros(n_steps),
            'main_middle_outflow': np.zeros(n_steps),
            'main_lower_outflow': np.zeros(n_steps),
            'gate1_flow': np.zeros(n_steps),
            'gate2_flow': np.zeros(n_steps),
            'max_stages': np.zeros((n_steps, 5)),  # Max stage for each reach
        }

        # Interpolate hydrographs / 插值过程线
        from scipy.interpolate import interp1d
        f_trib1 = interp1d(times_hr_1 * 3600, flows_1, kind='linear', fill_value='extrapolate')
        f_trib2 = interp1d(times_hr_2 * 3600, flows_2, kind='linear', fill_value='extrapolate')

        # Time-stepping loop / 时间步进
        for step in range(n_steps):
            t = step * dt
            times[step] = t / 3600.0  # Store in hours

            # Get inflows from tributaries / 获取支流入流
            inflow_trib1 = float(f_trib1(t))
            inflow_trib2 = float(f_trib2(t))

            # Simplified routing using Muskingum method
            # 使用Muskingum法简化演进
            K = 3600.0  # Storage coefficient (s) / 蓄量系数
            x = 0.2  # Weighting factor / 权重因子

            # Tributary 1 routing / 支流1演进
            reach_trib1 = self.reaches['tributary_1']
            C0 = (-K * x + dt / 2) / (K - K * x + dt / 2)
            C1 = (K * x + dt / 2) / (K - K * x + dt / 2)
            C2 = (K - K * x - dt / 2) / (K - K * x + dt / 2)

            outflow_trib1 = C0 * inflow_trib1 + C1 * inflow_trib1 + C2 * reach_trib1.flows[-1]
            reach_trib1.flows[-1] = outflow_trib1
            results['trib1_outflow'][step] = outflow_trib1

            # Tributary 2 routing / 支流2演进
            reach_trib2 = self.reaches['tributary_2']
            outflow_trib2 = C0 * inflow_trib2 + C1 * inflow_trib2 + C2 * reach_trib2.flows[-1]
            reach_trib2.flows[-1] = outflow_trib2
            results['trib2_outflow'][step] = outflow_trib2

            # Main river upper (receives both tributaries) / 干流上游（汇合两支流）
            reach_main_upper = self.reaches['main_upper']
            inflow_main_upper = outflow_trib1 + outflow_trib2
            outflow_main_upper = C0 * inflow_main_upper + C1 * inflow_main_upper + C2 * reach_main_upper.flows[-1]
            reach_main_upper.flows[-1] = outflow_main_upper
            results['main_upper_outflow'][step] = outflow_main_upper

            # Main river middle / 干流中游
            reach_main_middle = self.reaches['main_middle']
            inflow_main_middle = outflow_main_upper
            outflow_main_middle = C0 * inflow_main_middle + C1 * inflow_main_middle + C2 * reach_main_middle.flows[-1]
            reach_main_middle.flows[-1] = outflow_main_middle

            # Update gate 1 / 更新闸1
            depth_middle = reach_main_middle.calculate_normal_depth(outflow_main_middle)
            stage_middle = 100.0 + depth_middle  # Assume base elevation 100m
            gate1_flow = self.gates[0].update(stage_middle, dt)
            results['gate1_flow'][step] = gate1_flow

            # Flow continues to lower reach minus diverted flow / 流向下游减去分洪
            outflow_main_middle_net = max(0, outflow_main_middle - gate1_flow)
            results['main_middle_outflow'][step] = outflow_main_middle_net

            # Main river lower / 干流下游
            reach_main_lower = self.reaches['main_lower']
            inflow_main_lower = outflow_main_middle_net
            outflow_main_lower = C0 * inflow_main_lower + C1 * inflow_main_lower + C2 * reach_main_lower.flows[-1]
            reach_main_lower.flows[-1] = outflow_main_lower

            # Update gate 2 / 更新闸2
            depth_lower = reach_main_lower.calculate_normal_depth(outflow_main_lower)
            stage_lower = 95.0 + depth_lower  # Assume base elevation 95m
            gate2_flow = self.gates[1].update(stage_lower, dt)
            results['gate2_flow'][step] = gate2_flow

            # Final outflow / 最终出流
            outflow_final = max(0, outflow_main_lower - gate2_flow)
            results['main_lower_outflow'][step] = outflow_final

            # Store maximum stages / 存储最大水位
            results['max_stages'][step, 0] = depth_trib1 = reach_trib1.calculate_normal_depth(outflow_trib1)
            results['max_stages'][step, 1] = depth_trib2 = reach_trib2.calculate_normal_depth(outflow_trib2)
            results['max_stages'][step, 2] = depth_main_upper = reach_main_upper.calculate_normal_depth(outflow_main_upper)
            results['max_stages'][step, 3] = depth_middle
            results['max_stages'][step, 4] = depth_lower

            # Progress indicator / 进度指示
            if step % 48 == 0:
                progress = (step + 1) / n_steps * 100
                print(f"Progress: {progress:5.1f}% | Time: {t/3600:6.1f} hr | "
                      f"Main lower flow: {outflow_final:7.1f} m^3/s | "
                      f"Gates diverted: {gate1_flow + gate2_flow:6.1f} m^3/s")

        print(f"\n Simulation completed\n")

        self.results = results
        return results

    def analyze_results(self):
        """
        Analyze simulation results
        分析模拟结果
        """
        if not hasattr(self, 'results'):
            print("No results to analyze. Run simulation first.")
            return

        results = self.results

        print(f"\n{'='*70}")
        print(f"RIVER NETWORK SIMULATION RESULTS")
        print(f"河网模拟结果分析")
        print(f"{'='*70}\n")

        # Peak flows / 洪峰流量
        peak_main_upper = np.max(results['main_upper_outflow'])
        peak_main_middle = np.max(results['main_middle_outflow'])
        peak_main_lower = np.max(results['main_lower_outflow'])

        print(f"Peak Flows / 洪峰流量:")
        print(f"  Main River Upper / 干流上游:  {peak_main_upper:7.1f} m^3/s")
        print(f"  Main River Middle / 干流中游: {peak_main_middle:7.1f} m^3/s")
        print(f"  Main River Lower / 干流下游:  {peak_main_lower:7.1f} m^3/s")

        # Peak stages / 最高水位
        print(f"\nPeak Stages / 最高水位:")
        reach_names = ['Trib 1', 'Trib 2', 'Main Upper', 'Main Middle', 'Main Lower']
        for i, name in enumerate(reach_names):
            peak_stage = np.max(results['max_stages'][:, i])
            print(f"  {name:15}: {peak_stage:5.2f} m")

        # Flood diversion / 分洪效果
        total_gate1 = np.sum(results['gate1_flow']) * (results['times'][1] - results['times'][0]) * 3600
        total_gate2 = np.sum(results['gate2_flow']) * (results['times'][1] - results['times'][0]) * 3600
        total_diverted = total_gate1 + total_gate2

        print(f"\nFlood Diversion / 分洪效果:")
        print(f"  Gate 1 total volume / 闸1总分洪量: {total_gate1/1e6:8.2f} million m^3")
        print(f"  Gate 2 total volume / 闸2总分洪量: {total_gate2/1e6:8.2f} million m^3")
        print(f"  Total diverted / 总分洪量:        {total_diverted/1e6:8.2f} million m^3")

        # Peak reduction / 削峰效果
        peak_without_diversion = peak_main_upper
        reduction = (peak_without_diversion - peak_main_lower) / peak_without_diversion * 100

        print(f"\nPeak Reduction / 削峰效果:")
        print(f"  Peak at confluence / 汇流洪峰:    {peak_without_diversion:7.1f} m^3/s")
        print(f"  Peak at outlet / 出口洪峰:        {peak_main_lower:7.1f} m^3/s")
        print(f"  Reduction / 削减率:               {reduction:6.2f} %")

        print(f"\n{'='*70}\n")

    def plot_results(self, save_path: Optional[str] = None):
        """
        Plot simulation results
        绘制模拟结果

        Args:
            save_path: Path to save figure / 保存图形路径
        """
        if not hasattr(self, 'results'):
            print("No results to plot. Run simulation first.")
            return

        results = self.results

        fig, axes = plt.subplots(3, 2, figsize=(14, 10))
        fig.suptitle('River Network Flood Simulation Results\n河网洪水模拟结果',
                     fontsize=14, fontweight='bold')

        # 1. Tributary flows / 支流流量
        ax = axes[0, 0]
        ax.plot(results['times'], results['trib1_outflow'], 'b-', linewidth=2, label='Tributary 1 / 支流1')
        ax.plot(results['times'], results['trib2_outflow'], 'r-', linewidth=2, label='Tributary 2 / 支流2')
        ax.set_xlabel('Time / 时间 (hr)')
        ax.set_ylabel('Flow / 流量 (m^3/s)')
        ax.set_title('Tributary Flows / 支流流量')
        ax.legend()
        ax.grid(True, alpha=0.3)

        # 2. Main river flows / 干流流量
        ax = axes[0, 1]
        ax.plot(results['times'], results['main_upper_outflow'], 'g-', linewidth=2, label='Upper / 上游')
        ax.plot(results['times'], results['main_middle_outflow'], 'orange', linewidth=2, label='Middle / 中游')
        ax.plot(results['times'], results['main_lower_outflow'], 'purple', linewidth=2, label='Lower / 下游')
        ax.set_xlabel('Time / 时间 (hr)')
        ax.set_ylabel('Flow / 流量 (m^3/s)')
        ax.set_title('Main River Flows / 干流流量')
        ax.legend()
        ax.grid(True, alpha=0.3)

        # 3. Flood diversion flows / 分洪流量
        ax = axes[1, 0]
        ax.plot(results['times'], results['gate1_flow'], 'darkblue', linewidth=2, label='Gate 1 / 闸1')
        ax.plot(results['times'], results['gate2_flow'], 'darkred', linewidth=2, label='Gate 2 / 闸2')
        total_diverted = results['gate1_flow'] + results['gate2_flow']
        ax.plot(results['times'], total_diverted, 'k--', linewidth=1.5, label='Total / 总计')
        ax.set_xlabel('Time / 时间 (hr)')
        ax.set_ylabel('Diversion Flow / 分洪流量 (m^3/s)')
        ax.set_title('Flood Diversion / 分洪流量')
        ax.legend()
        ax.grid(True, alpha=0.3)

        # 4. Water stages / 水位
        ax = axes[1, 1]
        reach_names = ['Trib1', 'Trib2', 'Upper', 'Middle', 'Lower']
        colors = ['b', 'r', 'g', 'orange', 'purple']
        for i in range(5):
            ax.plot(results['times'], results['max_stages'][:, i],
                   color=colors[i], linewidth=1.5, label=reach_names[i])
        ax.set_xlabel('Time / 时间 (hr)')
        ax.set_ylabel('Water Depth / 水深 (m)')
        ax.set_title('Water Stages / 水位')
        ax.legend(ncol=2)
        ax.grid(True, alpha=0.3)

        # 5. Flow comparison at key locations / 关键断面流量对比
        ax = axes[2, 0]
        ax.plot(results['times'], results['main_upper_outflow'],
               'g-', linewidth=2, label='Confluence / 汇流点', alpha=0.7)
        ax.plot(results['times'], results['main_lower_outflow'],
               'purple', linewidth=2, label='Outlet / 出口', alpha=0.7)
        ax.fill_between(results['times'],
                       results['main_upper_outflow'],
                       results['main_lower_outflow'],
                       alpha=0.2, color='red', label='Diverted / 分洪量')
        ax.set_xlabel('Time / 时间 (hr)')
        ax.set_ylabel('Flow / 流量 (m^3/s)')
        ax.set_title('Peak Reduction Effect / 削峰效果')
        ax.legend()
        ax.grid(True, alpha=0.3)

        # 6. Cumulative volumes / 累积水量
        ax = axes[2, 1]
        dt_hr = results['times'][1] - results['times'][0]
        cum_inflow = np.cumsum(results['main_upper_outflow']) * dt_hr * 3600 / 1e6  # Million m^3
        cum_outflow = np.cumsum(results['main_lower_outflow']) * dt_hr * 3600 / 1e6
        cum_diverted = np.cumsum(total_diverted) * dt_hr * 3600 / 1e6

        ax.plot(results['times'], cum_inflow, 'g-', linewidth=2, label='Inflow / 入流')
        ax.plot(results['times'], cum_outflow, 'purple', linewidth=2, label='Outflow / 出流')
        ax.plot(results['times'], cum_diverted, 'r--', linewidth=2, label='Diverted / 分洪')
        ax.set_xlabel('Time / 时间 (hr)')
        ax.set_ylabel('Volume / 水量 (million m^3)')
        ax.set_title('Cumulative Volumes / 累积水量')
        ax.legend()
        ax.grid(True, alpha=0.3)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f" Figure saved to: {save_path}")
        else:
            plt.savefig('case_05_river_network_results.png', dpi=300, bbox_inches='tight')
            print(f" Figure saved to: case_05_river_network_results.png")

        plt.close()


def main():
    """
    Main function to run Case 05 demonstration
    主函数运行案例05演示
    """
    print("\n" + "="*70)
    print("HydroClaude Case 05: River Network System")
    print("HydroClaude 案例05: 河网系统")
    print("="*70 + "\n")

    # Create river network system / 创建河网系统
    print("Initializing river network system...")
    river_network = RiverNetworkSystem()

    # Run flood simulation / 运行洪水模拟
    print("\nRunning flood simulation...")
    results = river_network.simulate_flood_event(
        tributary_1_peak=600.0,  # m^3/s
        tributary_2_peak=500.0,  # m^3/s
        duration=48.0,  # hours
        dt=600.0  # 10-minute time step
    )

    # Analyze results / 分析结果
    river_network.analyze_results()

    # Plot results / 绘制结果
    print("Generating plots...")
    river_network.plot_results()

    print("\n" + "="*70)
    print(" Case 05 simulation completed successfully!")
    print(" 案例05模拟成功完成!")
    print("\n Output file: case_05_river_network_results.png")
    print("="*70 + "\n")


if __name__ == '__main__':
    main()
