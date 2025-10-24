#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
有压管道流动求解器

实现有压管道系统的水力瞬变分析（水锤效应）。

控制方程（特征线法）：
1. 连续性方程：∂H/∂t + (a²/g)∂V/∂x = 0
2. 动量方程：∂V/∂t + g∂H/∂x + fV|V|/(2D) = 0

其中：
- H: 压力水头 (m)
- V: 流速 (m/s)
- a: 水锤波速 (m/s)
- f: 达西摩阻系数
- D: 管径 (m)
- g: 重力加速度 (m/s²)

使用特征线法（Method of Characteristics）求解。

参考文献：
- Wylie, E.B. and Streeter, V.L. "Fluid Transients in Systems"
- Chaudhry, M.H. "Applied Hydraulic Transients"

作者: Claude
日期: 2025-10-24
"""

import numpy as np
from typing import Tuple, Optional, Dict, List, Callable
from dataclasses import dataclass
import warnings


@dataclass
class PipelineConfig:
    """管道配置参数"""
    length: float              # 管道长度 (m)
    diameter: float            # 管道内径 (m)
    thickness: float = 0.01    # 管壁厚度 (m)
    roughness: float = 0.0001  # 绝对粗糙度 (m)

    # 材料参数
    youngs_modulus: float = 2.0e11  # 弹性模量 (Pa), 钢管
    poisson_ratio: float = 0.3       # 泊松比
    density: float = 7850            # 管材密度 (kg/m³)

    # 流体参数
    fluid_density: float = 1000      # 流体密度 (kg/m³)
    fluid_bulk_modulus: float = 2.2e9  # 体积弹性模量 (Pa)
    kinematic_viscosity: float = 1e-6  # 运动粘度 (m²/s)

    # 其他
    elevation_start: float = 0.0   # 起点高程 (m)
    elevation_end: float = 0.0     # 终点高程 (m)


class PressurizedFlowSolver:
    """
    有压管道流动求解器

    采用特征线法（Method of Characteristics, MOC）求解
    水锤方程。

    基本原理：
    将偏微分方程转换为沿特征线的常微分方程，
    特征线方程为：C+ 和 C- 线。
    """

    def __init__(self, config: PipelineConfig, nx: int = 50):
        """
        初始化求解器

        Args:
            config: 管道配置
            nx: 空间网格点数
        """
        self.config = config
        self.nx = nx

        # 空间离散
        self.x = np.linspace(0, config.length, nx)
        self.dx = config.length / (nx - 1)

        # 计算水锤波速
        self.wave_speed = self._calculate_wave_speed()

        # 计算达西摩阻系数
        self.friction_factor = self._calculate_friction_factor()

        # 状态变量
        self.H = None  # 压力水头 (m)
        self.V = None  # 流速 (m/s)
        self.Q = None  # 流量 (m³/s)

        # 时间步长（Courant条件）
        self.dt = None

        # 历史记录
        self.time_history = []
        self.H_history = []
        self.V_history = []
        self.Q_history = []

        # 边界条件
        self.bc_upstream = None
        self.bc_downstream = None

        # 结构物
        self.structures = {}

        print(f"有压管道求解器初始化:")
        print(f"  管道长度: {config.length} m")
        print(f"  管径: {config.diameter} m")
        print(f"  网格点数: {nx}")
        print(f"  水锤波速: {self.wave_speed:.2f} m/s")
        print(f"  摩阻系数: {self.friction_factor:.6f}")

    def _calculate_wave_speed(self) -> float:
        """
        计算水锤波速

        考虑管壁弹性的修正公式：
        a = sqrt(K/ρ) / sqrt(1 + (K/E)(D/e))

        其中：
        - K: 流体体积弹性模量
        - ρ: 流体密度
        - E: 管材弹性模量
        - D: 管径
        - e: 管壁厚度
        """
        K = self.config.fluid_bulk_modulus
        rho = self.config.fluid_density
        E = self.config.youngs_modulus
        D = self.config.diameter
        e = self.config.thickness

        # 不考虑管壁弹性的波速
        a0 = np.sqrt(K / rho)

        # 考虑管壁弹性的修正
        psi = 1.0 + (K / E) * (D / e)
        a = a0 / np.sqrt(psi)

        return a

    def _calculate_friction_factor(self, V_ref: float = 1.0) -> float:
        """
        计算达西摩阻系数

        使用Swamee-Jain公式（隐式Colebrook-White的显式近似）：
        f = 0.25 / [log10(ε/(3.7D) + 5.74/Re^0.9)]²

        Args:
            V_ref: 参考流速 (m/s)，用于估算雷诺数
        """
        D = self.config.diameter
        eps = self.config.roughness
        nu = self.config.kinematic_viscosity

        # 雷诺数
        Re = V_ref * D / nu

        if Re < 2300:
            # 层流
            f = 64 / Re
        else:
            # 湍流 - Swamee-Jain公式
            term1 = eps / (3.7 * D)
            term2 = 5.74 / (Re ** 0.9)
            f = 0.25 / (np.log10(term1 + term2)) ** 2

        return f

    def initialize_steady_state(self, Q0: float, H0: float):
        """
        初始化为稳态流动

        Args:
            Q0: 初始流量 (m³/s)
            H0: 上游压力水头 (m)
        """
        A = np.pi * (self.config.diameter / 2) ** 2
        V0 = Q0 / A

        # 初始流速（均匀）
        self.V = np.ones(self.nx) * V0

        # 沿程水头损失（稳态）
        L = self.config.length
        f = self.friction_factor
        D = self.config.diameter

        # 高程变化
        z = np.linspace(
            self.config.elevation_start,
            self.config.elevation_end,
            self.nx
        )

        # 计算各点压力水头
        self.H = np.zeros(self.nx)
        self.H[0] = H0

        for i in range(1, self.nx):
            # 摩阻损失
            dx = self.x[i] - self.x[i-1]
            hf = f * (V0 ** 2) / (2 * 9.81 * D) * dx

            # 高程损失
            dz = z[i] - z[i-1]

            # 总水头平衡
            self.H[i] = self.H[i-1] - hf - dz

        # 流量
        self.Q = self.V * A

        # 计算Courant稳定时间步长
        self.dt = self.dx / self.wave_speed * 0.9  # 0.9是安全系数

        print(f"\n稳态初始化:")
        print(f"  初始流量: {Q0:.4f} m³/s")
        print(f"  初始流速: {V0:.4f} m/s")
        print(f"  上游水头: {H0:.2f} m")
        print(f"  下游水头: {self.H[-1]:.2f} m")
        print(f"  总水头损失: {H0 - self.H[-1]:.2f} m")
        print(f"  时间步长: {self.dt:.6f} s (Courant)")

    def set_boundary_conditions(self,
                               bc_upstream: Callable[[float], Tuple[str, float]],
                               bc_downstream: Callable[[float], Tuple[str, float]]):
        """
        设置边界条件

        Args:
            bc_upstream: 上游边界条件函数
                返回 ('H', value) 或 ('Q', value)
            bc_downstream: 下游边界条件函数
                返回 ('H', value) 或 ('Q', value)

        示例：
            # 上游恒定水头
            bc_up = lambda t: ('H', 100.0)

            # 下游恒定流量
            bc_down = lambda t: ('Q', 0.1)

            # 时变边界
            bc_up = lambda t: ('H', 100.0 + 10*np.sin(2*np.pi*t/10))
        """
        self.bc_upstream = bc_upstream
        self.bc_downstream = bc_downstream

    def add_structure(self, structure, position: float):
        """
        在管道上添加结构物

        Args:
            structure: 结构物对象
            position: 位置 (m from start)
        """
        # 找到最近的网格点
        idx = np.argmin(np.abs(self.x - position))
        self.structures[idx] = structure
        print(f"添加结构物 {structure.__class__.__name__} 在位置 x={self.x[idx]:.2f}m (节点{idx})")

    def step(self, t: float) -> bool:
        """
        时间步进（特征线法）

        Args:
            t: 当前时间 (s)

        Returns:
            是否成功
        """
        g = 9.81
        a = self.wave_speed
        f = self.friction_factor
        D = self.config.diameter
        dt = self.dt
        dx = self.dx

        # 新时刻的值
        H_new = np.zeros(self.nx)
        V_new = np.zeros(self.nx)

        # 内部节点 - 使用特征线法
        for i in range(1, self.nx - 1):
            # 特征线C+：来自左侧
            Hp = self.H[i-1]
            Vp = self.V[i-1]

            # 特征线C-：来自右侧
            Hm = self.H[i+1]
            Vm = self.V[i+1]

            # C+ 线方程：Hp + (a/g)Vp - f(dt/(2D))|Vp|Vp
            Cp = Hp + (a / g) * Vp - f * (dx / (2 * D)) * abs(Vp) * Vp

            # C- 线方程：Hm - (a/g)Vm + f(dt/(2D))|Vm|Vm
            Cm = Hm - (a / g) * Vm - f * (dx / (2 * D)) * abs(Vm) * Vm

            # 求解新时刻的H和V
            H_new[i] = (Cp + Cm) / 2.0
            V_new[i] = (Cp - Cm) * g / (2.0 * a)

        # 边界条件
        # 上游边界
        bc_type_up, bc_value_up = self.bc_upstream(t)
        if bc_type_up == 'H':
            # 已知水头
            H_new[0] = bc_value_up
            # 使用C-线计算流速
            Hm = self.H[1]
            Vm = self.V[1]
            Cm = Hm - (a / g) * Vm - f * (dx / (2 * D)) * abs(Vm) * Vm
            V_new[0] = (H_new[0] - Cm) * g / a
        elif bc_type_up == 'Q':
            # 已知流量
            A = np.pi * (D / 2) ** 2
            V_new[0] = bc_value_up / A
            # 使用C-线计算水头
            Hm = self.H[1]
            Vm = self.V[1]
            Cm = Hm - (a / g) * Vm - f * (dx / (2 * D)) * abs(Vm) * Vm
            H_new[0] = Cm + (a / g) * V_new[0]

        # 下游边界
        bc_type_down, bc_value_down = self.bc_downstream(t)
        if bc_type_down == 'H':
            H_new[-1] = bc_value_down
            # 使用C+线计算流速
            Hp = self.H[-2]
            Vp = self.V[-2]
            Cp = Hp + (a / g) * Vp - f * (dx / (2 * D)) * abs(Vp) * Vp
            V_new[-1] = (Cp - H_new[-1]) * g / a
        elif bc_type_down == 'Q':
            A = np.pi * (D / 2) ** 2
            V_new[-1] = bc_value_down / A
            # 使用C+线计算水头
            Hp = self.H[-2]
            Vp = self.V[-2]
            Cp = Hp + (a / g) * Vp - f * (dx / (2 * D)) * abs(Vp) * Vp
            H_new[-1] = Cp - (a / g) * V_new[-1]

        # 更新状态
        self.H = H_new
        self.V = V_new
        A = np.pi * (D / 2) ** 2
        self.Q = self.V * A

        return True

    def solve(self, t_final: float, save_interval: int = 1) -> Tuple[np.ndarray, Dict]:
        """
        运行瞬变模拟

        Args:
            t_final: 模拟总时间 (s)
            save_interval: 保存间隔（步数）

        Returns:
            (time, results): 时间数组和结果字典
        """
        if self.H is None or self.V is None:
            raise RuntimeError("请先调用 initialize_steady_state() 初始化")

        if self.bc_upstream is None or self.bc_downstream is None:
            raise RuntimeError("请先调用 set_boundary_conditions() 设置边界条件")

        # 清空历史
        self.time_history = []
        self.H_history = []
        self.V_history = []
        self.Q_history = []

        # 保存初始状态
        self.time_history.append(0.0)
        self.H_history.append(self.H.copy())
        self.V_history.append(self.V.copy())
        self.Q_history.append(self.Q.copy())

        # 时间步进
        n_steps = int(t_final / self.dt)
        t = 0.0

        print(f"\n开始瞬变模拟:")
        print(f"  总时间: {t_final} s")
        print(f"  时间步数: {n_steps}")
        print(f"  时间步长: {self.dt:.6f} s")

        for step in range(1, n_steps + 1):
            t += self.dt

            # 时间步进
            success = self.step(t)

            if not success:
                warnings.warn(f"模拟在 t={t:.4f}s 时失败")
                break

            # 保存结果
            if step % save_interval == 0:
                self.time_history.append(t)
                self.H_history.append(self.H.copy())
                self.V_history.append(self.V.copy())
                self.Q_history.append(self.Q.copy())

            # 进度输出
            if step % max(1, n_steps // 20) == 0:
                progress = step / n_steps * 100
                print(f"  进度: {progress:.1f}% (t={t:.4f}s, "
                      f"H_max={np.max(self.H):.2f}m, "
                      f"H_min={np.min(self.H):.2f}m)")

        # 转换为numpy数组
        time = np.array(self.time_history)
        results = {
            'H': np.array(self.H_history),
            'V': np.array(self.V_history),
            'Q': np.array(self.Q_history),
            'x': self.x,
            'wave_speed': self.wave_speed,
            'friction_factor': self.friction_factor
        }

        print(f"\n模拟完成!")
        print(f"  最大压力水头: {np.max(results['H']):.2f} m")
        print(f"  最小压力水头: {np.min(results['H']):.2f} m")
        print(f"  压力波动: {np.max(results['H']) - np.min(results['H']):.2f} m")

        return time, results

    def get_pressure_at(self, position: float) -> float:
        """
        获取指定位置的当前压力水头

        Args:
            position: 位置 (m from start)

        Returns:
            压力水头 (m)
        """
        idx = np.argmin(np.abs(self.x - position))
        return self.H[idx]

    def get_flow_rate_at(self, position: float) -> float:
        """
        获取指定位置的当前流量

        Args:
            position: 位置 (m from start)

        Returns:
            流量 (m³/s)
        """
        idx = np.argmin(np.abs(self.x - position))
        return self.Q[idx]


if __name__ == "__main__":
    # 测试代码
    print("=" * 80)
    print("有压管道流动求解器测试")
    print("=" * 80)

    # 创建管道配置
    config = PipelineConfig(
        length=1000.0,        # 1km管道
        diameter=0.5,         # 0.5m直径
        thickness=0.01,       # 10mm壁厚
        roughness=0.0001,     # 0.1mm粗糙度（钢管）
        elevation_start=0.0,
        elevation_end=-5.0    # 5m高差（下坡）
    )

    # 创建求解器
    solver = PressurizedFlowSolver(config, nx=50)

    # 初始化稳态
    Q0 = 0.1  # 100 L/s
    H0 = 50.0  # 50m水头
    solver.initialize_steady_state(Q0, H0)

    # 设置边界条件 - 模拟阀门快速关闭
    def bc_upstream(t):
        # 上游恒定水头
        return ('H', H0)

    def bc_downstream(t):
        # 下游阀门在t=1s时从Q0快速关闭到0
        t_close = 1.0
        t_duration = 0.5  # 0.5秒关闭时间

        if t < t_close:
            Q = Q0
        elif t < t_close + t_duration:
            # 线性关闭
            Q = Q0 * (1 - (t - t_close) / t_duration)
        else:
            Q = 0.0

        return ('Q', Q)

    solver.set_boundary_conditions(bc_upstream, bc_downstream)

    # 运行模拟
    time, results = solver.solve(t_final=10.0, save_interval=5)

    # 绘图
    try:
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(2, 2, figsize=(14, 10))

        # 1. 压力水头时空分布
        ax = axes[0, 0]
        X, T = np.meshgrid(results['x'], time)
        contour = ax.contourf(X, T, results['H'], levels=20, cmap='RdYlBu_r')
        ax.set_xlabel('位置 (m)')
        ax.set_ylabel('时间 (s)')
        ax.set_title('压力水头分布 (m)')
        plt.colorbar(contour, ax=ax)

        # 2. 特定位置压力变化
        ax = axes[0, 1]
        positions = [0, config.length/2, config.length]
        for pos in positions:
            idx = np.argmin(np.abs(results['x'] - pos))
            ax.plot(time, results['H'][:, idx], label=f'x={pos:.0f}m')
        ax.set_xlabel('时间 (s)')
        ax.set_ylabel('压力水头 (m)')
        ax.set_title('不同位置的压力变化')
        ax.legend()
        ax.grid(True, alpha=0.3)

        # 3. 流量变化
        ax = axes[1, 0]
        for pos in positions:
            idx = np.argmin(np.abs(results['x'] - pos))
            ax.plot(time, results['Q'][:, idx] * 1000, label=f'x={pos:.0f}m')
        ax.set_xlabel('时间 (s)')
        ax.set_ylabel('流量 (L/s)')
        ax.set_title('不同位置的流量变化')
        ax.legend()
        ax.grid(True, alpha=0.3)

        # 4. 最终压力分布
        ax = axes[1, 1]
        ax.plot(results['x'], results['H'][0, :], 'b-', label='初始', linewidth=2)
        ax.plot(results['x'], results['H'][-1, :], 'r-', label='最终', linewidth=2)
        ax.plot(results['x'], np.max(results['H'], axis=0), 'g--', label='最大', alpha=0.7)
        ax.plot(results['x'], np.min(results['H'], axis=0), 'm--', label='最小', alpha=0.7)
        ax.set_xlabel('位置 (m)')
        ax.set_ylabel('压力水头 (m)')
        ax.set_title('沿程压力分布')
        ax.legend()
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig('pressurized_flow_test.png', dpi=150, bbox_inches='tight')
        print(f"\n✓ 测试结果已保存到: pressurized_flow_test.png")

    except ImportError:
        print("\n(Matplotlib未安装，跳过绘图)")

    print("\n" + "=" * 80)
    print("测试完成！")
