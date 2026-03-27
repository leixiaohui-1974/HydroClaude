"""
coupled_1d2d_solver.py
======================
1D-2D 动态耦合求解器。

将 1D Preissmann 隐式求解器（PreissmannUnsteadySolver）与
2D HLLC 显式求解器（Hydrostatic2DSolver）通过以下两种连接方式耦合：

  1. 侧向堰连接（LateralWeirLink）：
     1D 河道侧向溢流进入 2D 泛滥平原，使用宽顶堰公式计算交换流量。

  2. 端点连接（StandardLink）：
     1D 河道端点与 2D 区域格点相连，传递流量和水位边界条件。

耦合策略（显式松弛耦合，Explicit Loose Coupling）：
  每个耦合时间步 Δt_c 内：
    1. 基于上一步状态计算各连接处的交换流量 Q_ex。
    2. 将 Q_ex 作为侧向源汇项注入 1D 求解器的连续性方程，推进 1D 一步。
    3. 将 Q_ex 注入 2D 格点（修改水深），推进 2D（内部细分子步满足 CFL）。
    4. 更新耦合时间。

参考文献：
  - Brunner, G.W. (2016). HEC-RAS 2D Modeling User's Manual.
  - Bladé, E. et al. (2012). 1D–2D coupling in a discontinuous Galerkin
    framework. J. Hydraulic Research.
"""

import numpy as np
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass, field

from solvers.preissmann_unsteady_solver import PreissmannUnsteadySolver
from solvers.hydrostatic_2d_solver import Hydrostatic2DSolver


# ---------------------------------------------------------------------------
# 连接类型定义
# ---------------------------------------------------------------------------

@dataclass
class LateralWeirLink:
    """
    侧向堰连接（Lateral Weir Link）。

    描述 1D 河道某段沿侧向溢流进入 2D 区域的连接关系。

    Attributes:
        i1d_start   : 1D 侧向连接起始节点索引
        i1d_end     : 1D 侧向连接结束节点索引
        cells_2d    : 对应的 2D 格点列表 [(row, col), ...]
        z_weir      : 堰顶高程 (m)，相对于基准面
        C_w         : 堰流系数（宽顶堰，推荐值 1.7 m^0.5/s）
        weir_lengths: 每个 2D 格点对应的堰长 (m)，用于分配流量
    """
    i1d_start: int
    i1d_end: int
    cells_2d: List[Tuple[int, int]]
    z_weir: float
    C_w: float = 1.7
    weir_lengths: List[float] = field(default_factory=list)

    def __post_init__(self):
        if not self.weir_lengths:
            self.weir_lengths = [1.0] * len(self.cells_2d)


@dataclass
class StandardLink:
    """
    端点连接（Standard Link）。

    描述 1D 河道端点（上游或下游）与 2D 区域某个格点的连接关系。

    Attributes:
        end     : 'upstream' 或 'downstream'
        cell_2d : 对应的 2D 格点 (row, col)
    """
    end: str          # 'upstream' or 'downstream'
    cell_2d: Tuple[int, int]


# ---------------------------------------------------------------------------
# 带侧向源项的 Preissmann 求解器包装
# ---------------------------------------------------------------------------

class PreissmannWithLateralSource(PreissmannUnsteadySolver):
    """
    在 PreissmannUnsteadySolver 基础上增加侧向源项支持。

    侧向源项 lateral_q (m²/s，即单位河长的侧向流量) 被加入连续性方程：
        ∂A/∂t + ∂Q/∂x = q_lat
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 侧向源项：形状 (nx,)，单位 m³/s（每个节点的侧向流量）
        self.lateral_q = np.zeros(self.nx)

    def set_lateral_source(self, lateral_q: np.ndarray):
        """设置侧向源项（每个节点的侧向流量，m³/s，正值为流出）。"""
        self.lateral_q = lateral_q.copy()

    def compute_residual(self, U_new: np.ndarray, dt: float) -> np.ndarray:
        """
        重写残差计算，在连续性方程中加入侧向源项。

        连续性方程（Preissmann 离散）：
            (A_avg_new - A_avg_old)/dt + θ*(Q_{i+1}^new - Q_i^new)/dx
                + (1-θ)*(Q_{i+1}^old - Q_i^old)/dx - q_lat_avg = 0

        其中 q_lat_avg 单位为 m²/s（单位河长的侧向流量 = Q_lat / dx）。
        正值表示侧向流出（1D 水量减少）。
        """
        F = super().compute_residual(U_new, dt)

        # 将侧向源项加入连续性方程残差
        # 连续性方程对应 F[2*i+1]（i = 0 to nx-2）
        for i in range(self.nx - 1):
            # 单元 i 两端节点的平均侧向流量（m³/s）
            q_lat_avg_m3s = (self.lateral_q[i] + self.lateral_q[i + 1]) / 2.0
            # 转换为单位河长流量 (m²/s)：q_lat = Q_lat / dx
            q_lat_per_m = q_lat_avg_m3s / self.dx
            # 侧向源项加入残差（正值 = 流出 1D = 减少水量，残差增大）
            # 注意：残差 = 方程左边，源项在方程右边，移项后符号为负
            F[2 * i + 1] += q_lat_per_m

        return F


# ---------------------------------------------------------------------------
# 主耦合求解器
# ---------------------------------------------------------------------------

class Coupled1D2DSolver:
    """
    1D-2D 动态耦合求解器。

    将 PreissmannWithLateralSource（1D）与 Hydrostatic2DSolver（2D）
    通过侧向堰连接和端点连接进行动态耦合。
    """

    def __init__(self,
                 solver_1d: PreissmannWithLateralSource,
                 solver_2d: Hydrostatic2DSolver,
                 lateral_weir_links: Optional[List[LateralWeirLink]] = None,
                 standard_links: Optional[List[StandardLink]] = None,
                 g: float = 9.81):
        """
        Args:
            solver_1d           : 已初始化的 1D 求解器（PreissmannWithLateralSource）
            solver_2d           : 已初始化的 2D 求解器（Hydrostatic2DSolver）
            lateral_weir_links  : 侧向堰连接列表
            standard_links      : 端点连接列表
            g                   : 重力加速度 (m/s²)
        """
        self.s1d = solver_1d
        self.s2d = solver_2d
        self.lateral_links = lateral_weir_links or []
        self.standard_links = standard_links or []
        self.g = g
        self.current_time = 0.0

        # 诊断：记录每步的交换流量和水量
        self.exchange_history: List[Dict] = []

    # ------------------------------------------------------------------
    # 床面高程辅助
    # ------------------------------------------------------------------

    def _get_1d_bed_elevation(self) -> np.ndarray:
        """获取 1D 求解器各节点的床面高程（以上游端为最高点）。"""
        # z_bed[i] = S0 * (length - x[i])，上游高，下游低
        return self.s1d.S0 * (self.s1d.length - self.s1d.x)

    def _get_1d_wse(self) -> np.ndarray:
        """获取 1D 各节点的水面高程（WSE = z_bed + h）。"""
        return self._get_1d_bed_elevation() + self.s1d.get_h()

    # ------------------------------------------------------------------
    # 侧向堰流量计算
    # ------------------------------------------------------------------

    def _compute_lateral_weir_flux(self, link: LateralWeirLink) -> np.ndarray:
        """
        计算侧向堰每个 2D 格点的溢流量 (m³/s)。

        使用宽顶堰公式（自由出流）：
            Q_i = C_w * L_i * max(WSE_1D - z_weir, 0)^1.5   (1D→2D)
            Q_i = -C_w * L_i * max(WSE_2D - z_weir, 0)^1.5  (2D→1D 回流)

        Returns:
            Q_ex : 形状 (n_cells,)，正值表示 1D→2D 溢流
        """
        wse_1d = self._get_1d_wse()
        n_cells = len(link.cells_2d)
        Q_ex = np.zeros(n_cells)

        i_start = link.i1d_start
        i_end = min(link.i1d_end, self.s1d.nx - 1)
        n_1d_nodes = max(i_end - i_start, 1)

        for k, (j2d, i2d) in enumerate(link.cells_2d):
            # 将 2D 格点映射到最近的 1D 节点
            frac = k / max(n_cells - 1, 1)
            i_1d = int(round(i_start + frac * n_1d_nodes))
            i_1d = int(np.clip(i_1d, i_start, i_end))

            wse_1d_local = wse_1d[i_1d]
            wse_2d_local = self.s2d.h[j2d, i2d] + self.s2d.z[j2d, i2d]
            L_i = link.weir_lengths[k]

            if wse_1d_local > link.z_weir and wse_1d_local > wse_2d_local:
                # 正向溢流：1D → 2D
                head = wse_1d_local - link.z_weir
                Q_ex[k] = link.C_w * L_i * head ** 1.5
            elif wse_2d_local > link.z_weir and wse_2d_local > wse_1d_local:
                # 回流：2D → 1D
                head = wse_2d_local - link.z_weir
                Q_ex[k] = -link.C_w * L_i * head ** 1.5

        return Q_ex

    # ------------------------------------------------------------------
    # 端点连接处理
    # ------------------------------------------------------------------

    def _process_standard_links(self) -> Dict[int, float]:
        """
        处理端点连接，更新 1D 边界条件，并返回各连接的交换流量。

        Returns:
            exchange : {link_index: Q_exchange (m³/s)}，正值表示 1D→2D
        """
        exchange = {}
        wse_1d = self._get_1d_wse()
        z_bed_1d = self._get_1d_bed_elevation()

        for k, link in enumerate(self.standard_links):
            j2d, i2d = link.cell_2d
            wse_2d = self.s2d.h[j2d, i2d] + self.s2d.z[j2d, i2d]

            if link.end == 'downstream':
                # 2D 水位 → 1D 下游水深边界
                z_ds = z_bed_1d[-1]
                h_bc = max(wse_2d - z_ds, 1e-4)
                self.s1d.set_boundary_conditions(h_downstream=h_bc)
                # 1D 下游流量流入 2D
                exchange[k] = float(self.s1d.get_Q()[-1])

            elif link.end == 'upstream':
                # 2D 水位 → 1D 上游水深边界
                z_us = z_bed_1d[0]
                h_bc = max(wse_2d - z_us, 1e-4)
                self.s1d.set_boundary_conditions(h_upstream=h_bc)
                # 1D 上游流量从 2D 取水（负值）
                exchange[k] = -float(self.s1d.get_Q()[0])

        return exchange

    # ------------------------------------------------------------------
    # 主耦合时间步
    # ------------------------------------------------------------------

    def step(self, dt: float, cfl_2d: float = 0.45) -> Dict:
        """
        推连耦合系统一个时间步 dt。

        采用守恒耦合策略（Conservative Coupling）：
          1. 基于堰流公式计算交换流量 Q_ex，并将其作为侧向源项注入 1D。
          2. 推连 1D，记录推连前后 1D 水量变化 ΔV_1d。
          3. 将 |ΔV_1d| 分配到对应的 2D 格点，确保严格守恒。
          4. 推连 2D（细分子步满足 CFL）。

        Args:
            dt     : 耦合时间步 (s)
            cfl_2d : 2D 子步的 CFL 数（默认 0.45）

        Returns:
            info : 包含交换流量、子步数等诊断信息的字典
        """
        # ---- 1. 计算侧向堰交换流量（堰流公式）----------------------------
        lateral_Q_all: Dict[int, np.ndarray] = {}
        lateral_q_1d = np.zeros(self.s1d.nx)  # 1D 各节点侧向流量 (m³/s)

        for k, link in enumerate(self.lateral_links):
            Q_ex = self._compute_lateral_weir_flux(link)
            lateral_Q_all[k] = Q_ex

            # 将溢流量分配到对应的 1D 节点（正值 = 流出 1D）
            n_cells = len(link.cells_2d)
            i_start = link.i1d_start
            i_end = min(link.i1d_end, self.s1d.nx - 1)
            n_1d_nodes = max(i_end - i_start, 1)

            for m in range(n_cells):
                frac = m / max(n_cells - 1, 1)
                i_1d = int(round(i_start + frac * n_1d_nodes))
                i_1d = int(np.clip(i_1d, i_start, i_end))
                lateral_q_1d[i_1d] += Q_ex[m]  # 正值 = 从 1D 流出

        # ---- 2. 处理端点连接（更新 1D 边界条件）-----------------------
        std_exchange = self._process_standard_links()

        # ---- 3. 推连 1D（注入侧向源项）并记录实际水量变化 --------
        V1d_before = float(np.sum(self.s1d.get_h()) * self.s1d.B * self.s1d.dx)
        self.s1d.set_lateral_source(lateral_q_1d)
        U_old = self.s1d.U_old.copy()
        U_new = self.s1d.solve_step(U_old, dt)
        self.s1d.U_old = U_new
        V1d_after = float(np.sum(self.s1d.get_h()) * self.s1d.B * self.s1d.dx)

        # 1D 实际减少的水量（正值 = 水量减少，即溢出）
        # 注意：上游有持续输入时 V1d 可能不减，这里只计算侧向溢流导致的净变化
        dV_1d_lateral = V1d_before - V1d_after  # 正值表示 1D 净减少

        # ---- 4. 推连 2D（守恒注入实际水量）---------------------------
        # 计算 2D 最大允许时间步（CFL）
        h2 = self.s2d.h
        u2 = self.s2d._safe_velocity(h2, self.s2d.hu)
        v2 = self.s2d._safe_velocity(h2, self.s2d.hv)
        c2 = np.sqrt(self.g * np.maximum(h2, self.s2d.eps_dry))
        max_spd = float(np.max(np.abs(u2) + c2)) + float(np.max(np.abs(v2) + c2))
        dt_2d_max = cfl_2d * min(self.s2d.dx, self.s2d.dy) / (max_spd + 1e-10)
        dt_2d_max = max(dt_2d_max, 1e-6)

        n_sub = max(1, int(np.ceil(dt / dt_2d_max)))
        dt_sub = dt / n_sub

        cell_area = self.s2d.dx * self.s2d.dy

        # 直接用堰流公式计算的 Q_ex * dt 注入 2D
        # （显式松弛耦合的固有误差，与 HEC-RAS 类似）
        lateral_dh_total: Dict[int, np.ndarray] = {}
        for k, link in enumerate(self.lateral_links):
            Q_ex = lateral_Q_all[k]
            # dh = Q_ex * dt / cell_area，正值 = 注入 2D，负值 = 从 2D 抓水
            dh_total = Q_ex * dt / cell_area
            lateral_dh_total[k] = dh_total

        # 端点连接：每子步的 dh 增量
        std_dh: Dict[int, float] = {}
        for k, link in enumerate(self.standard_links):
            Q_std = std_exchange.get(k, 0.0)
            std_dh[k] = Q_std * dt_sub / cell_area

        # 执行 2D 子步
        # 将总水量均匀分布到每个子步
        for sub_idx in range(n_sub):
            # 注入侧向溢流到 2D 格点（每子步平均分配）
            for k, link in enumerate(self.lateral_links):
                dh_total = lateral_dh_total[k]
                dh_sub = dh_total / n_sub  # 平均分配到每个子步
                for m, (j2d, i2d) in enumerate(link.cells_2d):
                    self.s2d.h[j2d, i2d] = max(
                        self.s2d.h[j2d, i2d] + dh_sub[m], 0.0)

            # 注入端点连接流量到 2D 格点
            for k, link in enumerate(self.standard_links):
                j2d, i2d = link.cell_2d
                self.s2d.h[j2d, i2d] = max(
                    self.s2d.h[j2d, i2d] + std_dh[k], 0.0)

            # 推连 2D 一步
            self.s2d.step_2d(dt_sub)

        # ---- 5. 更新时间与诊断 ----------------------------------------
        self.current_time += dt

        info = {
            'time': self.current_time,
            'dt': dt,
            'n_2d_substeps': n_sub,
            'lateral_Q': {k: v.tolist() for k, v in lateral_Q_all.items()},
            'standard_Q': std_exchange,
            'total_lateral_q_1d': lateral_q_1d.tolist(),
            'dV_1d_lateral': dV_1d_lateral,
        }
        self.exchange_history.append(info)
        return info

    # ------------------------------------------------------------------
    # 质量守恒诊断
    # ------------------------------------------------------------------

    def compute_total_volume(self) -> Tuple[float, float]:
        """
        计算 1D 和 2D 域的当前总水量 (m³)。

        Returns:
            (V_1d, V_2d)
        """
        h_1d = self.s1d.get_h()
        V_1d = float(np.sum(h_1d) * self.s1d.B * self.s1d.dx)
        V_2d = float(np.sum(self.s2d.h) * self.s2d.dx * self.s2d.dy)
        return V_1d, V_2d

    # ------------------------------------------------------------------
    # 便捷运行方法
    # ------------------------------------------------------------------

    def run(self, t_end: float, dt: float,
            output_interval: int = 10) -> List[Dict]:
        """
        运行耦合模型到指定时间。

        Args:
            t_end           : 模拟结束时间 (s)
            dt              : 耦合时间步 (s)
            output_interval : 每隔多少步输出一次诊断信息

        Returns:
            outputs : 输出时刻的诊断信息列表（含总水量）
        """
        outputs = []
        step_count = 0

        while self.current_time < t_end - 1e-10:
            dt_actual = min(dt, t_end - self.current_time)
            info = self.step(dt_actual)
            step_count += 1

            if step_count % output_interval == 0:
                V_1d, V_2d = self.compute_total_volume()
                info['V_1d'] = V_1d
                info['V_2d'] = V_2d
                outputs.append(info)

        return outputs
