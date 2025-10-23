#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
有限体积法(FVM)求解器

实现严格守恒的浅水方程求解器：
- Godunov一阶格式
- MUSCL二阶格式
- 多种Riemann求解器
- TVD slope限制器

作者: Claude
日期: 2025-10-23
"""

import numpy as np
import sys
import os

# 导入Riemann求解器和slope限制器
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from riemann_solvers import hll_flux_shallow_water, hllc_flux_shallow_water, rusanov_flux
from slope_limiters import compute_limited_slope


class FVMSolver:
    """
    有限体积法求解器（浅水方程）

    支持：
    - Godunov一阶（分段常数重构）
    - MUSCL二阶（分段线性重构 + TVD限制器）
    - 多种Riemann求解器（HLL/HLLC/Rusanov）
    - 显式Euler或SSP-RK2时间积分
    """

    def __init__(self, x_grid, B, S0, n, g=9.81,
                 reconstruction='muscl', limiter='minmod',
                 riemann='hll', time_integrator='ssp_rk2',
                 gates=None):
        """
        初始化FVM求解器

        Args:
            x_grid: 网格点坐标数组 [m]
            B: 渠道宽度 [m]
            S0: 渠底坡度 [m/m]
            n: Manning糙率 [s/m^(1/3)]
            g: 重力加速度 [m/s²]
            reconstruction: 'godunov' (一阶) 或 'muscl' (二阶)
            limiter: 'minmod', 'vanleer', 'superbee', 'mc'
            riemann: 'hll', 'hllc', 'rusanov'
            time_integrator: 'euler', 'ssp_rk2'
            gates: 闸门列表，每个闸门为(position, opening, Cd)元组
        """
        self.x = np.array(x_grid)
        self.nx = len(self.x)
        self.B = B
        self.S0 = S0
        self.n = n
        self.g = g

        # 计算单元中心和界面
        self.x_cell = 0.5 * (self.x[:-1] + self.x[1:])  # 单元中心
        self.dx = np.diff(self.x)  # 单元尺寸

        self.ncells = len(self.x_cell)

        # 方法选项
        self.reconstruction = reconstruction.lower()
        self.limiter = limiter.lower()
        self.riemann = riemann.lower()
        self.time_integrator = time_integrator.lower()

        # 状态变量 U = [A, Q]
        # 存储在单元中心
        self.U = np.zeros((self.ncells, 2))

        # 验证选项
        valid_recon = ['godunov', 'muscl']
        valid_riemann = ['hll', 'hllc', 'rusanov']
        valid_integrator = ['euler', 'ssp_rk2']

        if self.reconstruction not in valid_recon:
            raise ValueError(f"Invalid reconstruction: {reconstruction}")
        if self.riemann not in valid_riemann:
            raise ValueError(f"Invalid Riemann solver: {riemann}")
        if self.time_integrator not in valid_integrator:
            raise ValueError(f"Invalid time integrator: {time_integrator}")

        # 闸门处理
        self.gates = gates if gates is not None else []
        self.gate_interfaces = []  # 闸门对应的界面索引

        # 为每个闸门找到最近的界面
        for gate_pos, gate_opening, gate_Cd in self.gates:
            # 界面位置是self.x[i]，对应self.U[i-1]和self.U[i]之间
            # 找到最近的界面
            interface_idx = np.argmin(np.abs(self.x - gate_pos))
            self.gate_interfaces.append({
                'index': interface_idx,
                'position': gate_pos,
                'actual_x': self.x[interface_idx],
                'opening': gate_opening,
                'Cd': gate_Cd
            })

        if len(self.gates) > 0:
            print(f"FVM求解器: 检测到{len(self.gates)}个闸门")
            for i, gate_info in enumerate(self.gate_interfaces):
                print(f"  闸门{i+1}: x={gate_info['position']}m -> 界面{gate_info['index']} (x={gate_info['actual_x']:.1f}m), "
                      f"开度={gate_info['opening']}m, Cd={gate_info['Cd']}")

    def initialize(self, h0, Q0):
        """
        初始化状态

        Args:
            h0: 初始水深 [m] (标量或数组)
            Q0: 初始流量 [m³/s] (标量或数组)
        """
        # 转换为数组
        if np.isscalar(h0):
            h0 = np.ones(self.ncells) * h0
        if np.isscalar(Q0):
            Q0 = np.ones(self.ncells) * Q0

        # 初始化 U = [A, Q]
        A0 = self.B * h0
        self.U[:, 0] = A0
        self.U[:, 1] = Q0

    def get_primitive_variables(self):
        """
        获取原始变量 [h, u]

        Returns:
            h: 水深 [m]
            u: 流速 [m/s]
        """
        A = self.U[:, 0]
        Q = self.U[:, 1]

        h = A / self.B
        u = np.where(A > 1e-10, Q / A, 0.0)

        return h, u

    def reconstruct_interface_values(self):
        """
        空间重构，计算单元界面的左右值

        Returns:
            U_L: 界面左值 [ncells+1, 2]
            U_R: 界面右值 [ncells+1, 2]
        """
        U_L = np.zeros((self.ncells + 1, 2))
        U_R = np.zeros((self.ncells + 1, 2))

        if self.reconstruction == 'godunov':
            # Godunov一阶：分段常数
            for i in range(self.ncells + 1):
                if i == 0:
                    # 左边界
                    U_L[i] = self.U[0]
                    U_R[i] = self.U[0]
                elif i == self.ncells:
                    # 右边界
                    U_L[i] = self.U[-1]
                    U_R[i] = self.U[-1]
                else:
                    # 内部界面
                    U_L[i] = self.U[i-1]
                    U_R[i] = self.U[i]

        elif self.reconstruction == 'muscl':
            # MUSCL二阶：分段线性 + 限制器
            sigma = np.zeros((self.ncells, 2))

            # 计算限制后的斜率
            for k in range(2):  # A和Q分量
                for i in range(self.ncells):
                    if i == 0:
                        # 左边界：一阶
                        sigma[i, k] = 0.0
                    elif i == self.ncells - 1:
                        # 右边界：一阶
                        sigma[i, k] = 0.0
                    else:
                        # 内部：TVD限制
                        sigma[i, k] = compute_limited_slope(
                            self.U[i-1, k], self.U[i, k], self.U[i+1, k],
                            self.dx[i-1], self.dx[i], self.dx[i+1] if i+1 < len(self.dx) else self.dx[i],
                            limiter=self.limiter
                        )

            # 计算界面值
            for i in range(self.ncells + 1):
                if i == 0:
                    # 左边界
                    U_L[i] = self.U[0] - 0.5 * self.dx[0] * sigma[0]
                    U_R[i] = self.U[0] - 0.5 * self.dx[0] * sigma[0]
                elif i == self.ncells:
                    # 右边界
                    U_L[i] = self.U[-1] + 0.5 * self.dx[-1] * sigma[-1]
                    U_R[i] = self.U[-1] + 0.5 * self.dx[-1] * sigma[-1]
                else:
                    # 内部界面
                    U_L[i] = self.U[i-1] + 0.5 * self.dx[i-1] * sigma[i-1]
                    U_R[i] = self.U[i] - 0.5 * self.dx[i] * sigma[i]

        return U_L, U_R

    def compute_interface_flux(self, U_L, U_R):
        """
        使用Riemann求解器计算界面通量

        在闸门位置使用闸门方程代替Riemann求解器

        Args:
            U_L, U_R: 界面左右值

        Returns:
            F: 界面通量 [ncells+1, 2]
        """
        F = np.zeros((self.ncells + 1, 2))

        # 创建闸门界面索引集合以便快速查找
        gate_indices = set()
        gate_map = {}
        for gate_info in self.gate_interfaces:
            idx = gate_info['index']
            gate_indices.add(idx)
            gate_map[idx] = gate_info

        for i in range(self.ncells + 1):
            if i in gate_indices:
                # 闸门位置：使用闸门方程
                gate_info = gate_map[i]
                F[i] = self.compute_gate_flux(U_L[i], U_R[i], gate_info)
            else:
                # 普通界面：使用Riemann求解器
                if self.riemann == 'hll':
                    F[i] = hll_flux_shallow_water(U_L[i], U_R[i], self.B, self.g)
                elif self.riemann == 'hllc':
                    F[i] = hllc_flux_shallow_water(U_L[i], U_R[i], self.B, self.g)
                elif self.riemann == 'rusanov':
                    F[i] = rusanov_flux(U_L[i], U_R[i], self.B, self.g)

        return F

    def compute_gate_flux(self, U_L, U_R, gate_info):
        """
        计算闸门通量

        使用闸门方程：Q = Cd * a * B * sqrt(2*g*Δh)

        Args:
            U_L: 上游状态 [A_L, Q_L]
            U_R: 下游状态 [A_R, Q_R]
            gate_info: 闸门信息字典

        Returns:
            F: 闸门通量 [F_mass, F_momentum]
        """
        A_L, Q_L = U_L
        A_R, Q_R = U_R

        # 计算水深
        h_L = A_L / self.B if A_L > 1e-10 else 1e-10
        h_R = A_R / self.B if A_R > 1e-10 else 1e-10

        # 闸门参数
        a = gate_info['opening']  # 闸门开度
        Cd = gate_info['Cd']  # 流量系数

        # 判断流态
        if h_L > a:
            # 淹没出流
            delta_h = h_L - h_R
            if delta_h > 0:
                # 正向流动
                Q_gate = Cd * a * self.B * np.sqrt(2 * self.g * delta_h)
            else:
                # 反向流动或无流动
                Q_gate = 0.0
        else:
            # 自由出流
            Q_gate = Cd * a * self.B * np.sqrt(2 * self.g * h_L)

        # 计算通量
        # 质量通量
        F_mass = Q_gate

        # 动量通量：Q * u + 0.5 * g * A * h
        # 使用闸门处的平均状态
        A_gate = 0.5 * (A_L + A_R)
        h_gate = 0.5 * (h_L + h_R)
        u_gate = Q_gate / A_gate if A_gate > 1e-10 else 0.0

        F_momentum = Q_gate * u_gate + 0.5 * self.g * A_gate * h_gate

        return np.array([F_mass, F_momentum])

    def compute_source_term(self):
        """
        计算源项 S = [0, gA(S0 - Sf)]

        Returns:
            S: 源项 [ncells, 2]
        """
        S = np.zeros((self.ncells, 2))

        A = self.U[:, 0]
        Q = self.U[:, 1]

        h = A / self.B

        # Manning摩阻坡度
        # Sf = n²Q²/(A²R^(4/3))
        # 矩形断面: R = A/P = Bh/(B+2h) ≈ h (宽渠道)
        R = np.where(h > 1e-10, self.B * h / (self.B + 2 * h), 1e-10)
        Sf = np.where(
            A > 1e-10,
            self.n**2 * Q**2 / (A**2 * R**(4.0/3.0)),
            0.0
        )

        # 源项：S = [0, gA(S0 - Sf)]
        S[:, 0] = 0.0
        S[:, 1] = self.g * A * (self.S0 - Sf)

        return S

    def compute_rhs(self, U):
        """
        计算右端项 dU/dt = -1/dx[F(i+1/2) - F(i-1/2)] + S

        Args:
            U: 当前状态 [ncells, 2]

        Returns:
            dU_dt: 右端项 [ncells, 2]
        """
        # 临时保存当前状态
        U_save = self.U.copy()
        self.U = U.copy()

        # 1. 空间重构
        U_L, U_R = self.reconstruct_interface_values()

        # 2. 计算界面通量
        F = self.compute_interface_flux(U_L, U_R)

        # 3. 计算源项
        S = self.compute_source_term()

        # 4. 组装RHS
        dU_dt = np.zeros_like(U)

        for i in range(self.ncells):
            # 通量差分
            flux_diff = (F[i+1] - F[i]) / self.dx[i]

            # dU/dt = -flux_diff + S
            dU_dt[i] = -flux_diff + S[i]

        # 恢复状态
        self.U = U_save

        return dU_dt

    def compute_cfl_timestep(self, cfl=0.5):
        """
        计算满足CFL条件的时间步长

        dt <= CFL * min(dx / (|u| + c))

        Args:
            cfl: CFL数 (0.5 for Euler, 0.9 for RK2)

        Returns:
            dt: 时间步长 [s]
        """
        h, u = self.get_primitive_variables()

        # 波速 c = sqrt(g*h)
        c = np.sqrt(self.g * np.maximum(h, 1e-10))

        # 最大特征速度
        lambda_max = np.abs(u) + c

        # CFL条件
        dt_cfl = cfl * np.min(self.dx / np.maximum(lambda_max, 1e-10))

        return dt_cfl

    def step_euler(self, dt):
        """
        显式Euler时间积分一步

        U^(n+1) = U^n + dt * RHS(U^n)

        Args:
            dt: 时间步长 [s]
        """
        dU_dt = self.compute_rhs(self.U)
        self.U += dt * dU_dt

    def step_ssp_rk2(self, dt):
        """
        SSP-RK2 (Strong Stability Preserving Runge-Kutta 2阶) 时间积分

        U* = U^n + dt * RHS(U^n)
        U^(n+1) = 0.5*U^n + 0.5*(U* + dt*RHS(U*))

        Args:
            dt: 时间步长 [s]
        """
        U_n = self.U.copy()

        # 第一步
        dU_dt_1 = self.compute_rhs(U_n)
        U_star = U_n + dt * dU_dt_1

        # 第二步
        self.U = U_star.copy()
        dU_dt_2 = self.compute_rhs(U_star)
        U_new = 0.5 * U_n + 0.5 * (U_star + dt * dU_dt_2)

        self.U = U_new

    def step(self, dt):
        """
        时间推进一步（根据选定的积分器）

        Args:
            dt: 时间步长 [s]
        """
        if self.time_integrator == 'euler':
            self.step_euler(dt)
        elif self.time_integrator == 'ssp_rk2':
            self.step_ssp_rk2(dt)

    def solve(self, t_end, dt=None, cfl=0.5, output_interval=None, verbose=True):
        """
        求解到指定时间

        Args:
            t_end: 终止时间 [s]
            dt: 时间步长 [s]（如果None则自适应）
            cfl: CFL数
            output_interval: 输出间隔 [s]（None则只输出最终状态）
            verbose: 是否输出进度

        Returns:
            history: {'t': [...], 'U': [...]} 时间历史
        """
        t = 0.0
        step_count = 0

        history = {'t': [0.0], 'U': [self.U.copy()]}

        if verbose:
            print(f"FVM求解开始 (reconstruction={self.reconstruction}, riemann={self.riemann})")
            print(f"  总时间: {t_end}s, CFL={cfl}")

        while t < t_end:
            # 计算时间步长
            if dt is None:
                dt_cfl = self.compute_cfl_timestep(cfl)
            else:
                dt_cfl = dt

            # 不超过终止时间
            if t + dt_cfl > t_end:
                dt_cfl = t_end - t

            # 推进一步
            self.step(dt_cfl)
            t += dt_cfl
            step_count += 1

            # 检查NaN
            if np.any(np.isnan(self.U)) or np.any(np.isinf(self.U)):
                raise RuntimeError(f"数值发散 (NaN/Inf detected at t={t:.2f}s)")

            # 输出
            if output_interval is not None and step_count % max(1, int(output_interval / dt_cfl)) == 0:
                history['t'].append(t)
                history['U'].append(self.U.copy())

                if verbose and step_count % 100 == 0:
                    h, u = self.get_primitive_variables()
                    print(f"  t={t:.2f}s, dt={dt_cfl:.4f}s, h范围=[{h.min():.3f}, {h.max():.3f}]m")

        # 最终状态
        history['t'].append(t_end)
        history['U'].append(self.U.copy())

        if verbose:
            print(f"  完成！总步数={step_count}")

        return history


# 测试
if __name__ == "__main__":
    print("=" * 70)
    print("FVM求解器测试")
    print("=" * 70)
    print()

    # Dam break问题
    print("测试: Dam break (溃坝)")
    print()

    # 网格
    L = 100.0  # 长度
    nx = 101
    x = np.linspace(0, L, nx)

    # 参数
    B = 10.0
    S0 = 0.0
    n = 0.0  # 无摩阻
    g = 9.81

    # 创建求解器
    solver = FVMSolver(
        x_grid=x,
        B=B, S0=S0, n=n, g=g,
        reconstruction='muscl',
        limiter='minmod',
        riemann='hll',
        time_integrator='ssp_rk2'
    )

    # 初始条件：左高右低
    h0 = np.where(solver.x_cell < 50.0, 2.0, 1.0)
    Q0 = np.zeros(solver.ncells)

    solver.initialize(h0, Q0)

    # 求解
    t_end = 5.0
    history = solver.solve(t_end, cfl=0.9, verbose=True)

    print()
    print("✓ Dam break测试完成")
    print(f"  最终时间: {history['t'][-1]:.2f}s")
    print(f"  时间步数: {len(history['t'])}")

    h_final, u_final = solver.get_primitive_variables()
    print(f"  最终水深范围: [{h_final.min():.3f}, {h_final.max():.3f}]m")
    print(f"  最终流速范围: [{u_final.min():.3f}, {u_final.max():.3f}]m/s")
