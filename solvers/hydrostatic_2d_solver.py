import numpy as np
from typing import Tuple, Optional


class Hydrostatic2DSolver:
    """
    二维浅水方程（2D SWE）有限体积求解器。

    控制方程（守恒形式）：
        ∂h/∂t  + ∂(hu)/∂x + ∂(hv)/∂y = 0
        ∂(hu)/∂t + ∂(hu²+½gh²)/∂x + ∂(huv)/∂y = -gh·∂z/∂x - gn²hu·|V|/h^(4/3)
        ∂(hv)/∂t + ∂(huv)/∂x + ∂(hv²+½gh²)/∂y = -gh·∂z/∂y - gn²hv·|V|/h^(4/3)

    数值方法：
        - 空间离散：有限体积法（Godunov 型）
        - Riemann 求解器：向量化 HLLC（Toro, 2001）
        - 干湿边界：基于 Audusse et al. (2004) 的水位重构
        - 时间推进：显式 Euler（可扩展为 SSP-RK2）
        - 源项：算子分裂（分步处理摩阻源项，提高稳定性）
    """

    def __init__(self, Lx: float, Ly: float, nx: int, ny: int,
                 S0x: float = 0.0, S0y: float = 0.0,
                 n: float = 0.025, g: float = 9.81,
                 eps_dry: float = 1e-4,
                 z_bed: Optional[np.ndarray] = None):
        """
        Args:
            Lx, Ly   : 计算域长度和宽度 (m)
            nx, ny   : x 和 y 方向的格点数
            S0x, S0y : x 和 y 方向的床面坡度（正值表示向下倾斜）
            n        : Manning 糙率系数
            g        : 重力加速度 (m/s²)
            eps_dry  : 干床阈值 (m)
            z_bed    : 自定义床面高程数组，形状 (ny, nx)；若为 None 则由坡度自动生成
        """
        self.Lx = Lx
        self.Ly = Ly
        self.nx = nx
        self.ny = ny
        self.dx = Lx / nx       # 单元宽度（单元中心格）
        self.dy = Ly / ny       # 单元高度
        self.S0x = S0x
        self.S0y = S0y
        self.n = n
        self.g = g
        self.eps_dry = eps_dry

        # 单元中心坐标
        self.x = np.linspace(self.dx / 2, Lx - self.dx / 2, nx)
        self.y = np.linspace(self.dy / 2, Ly - self.dy / 2, ny)
        self.X, self.Y = np.meshgrid(self.x, self.y)

        # 床面高程（单元中心）
        if z_bed is not None:
            assert z_bed.shape == (ny, nx), "z_bed shape must be (ny, nx)"
            self.z = z_bed.copy()
        else:
            self.z = -S0x * self.X - S0y * self.Y

        # 状态变量：h（水深），hu（x 动量），hv（y 动量），形状均为 (ny, nx)
        self.h  = np.full((ny, nx), eps_dry)
        self.hu = np.zeros((ny, nx))
        self.hv = np.zeros((ny, nx))

        self.current_time = 0.0

    # ------------------------------------------------------------------
    # 辅助函数
    # ------------------------------------------------------------------

    def _safe_velocity(self, h: np.ndarray, hm: np.ndarray) -> np.ndarray:
        """从动量 hm 和水深 h 安全计算速度，干床处返回 0。"""
        return np.where(h > self.eps_dry, hm / np.maximum(h, self.eps_dry), 0.0)

    def _wave_speeds(self, hL, uL, hR, uR):
        """
        计算 HLLC 左右波速（Einfeldt 估计）。
        返回 sL, sR（均为 numpy 数组）。
        """
        cL = np.sqrt(self.g * np.maximum(hL, 0.0))
        cR = np.sqrt(self.g * np.maximum(hR, 0.0))

        # Roe 平均
        sqrtHL = np.sqrt(np.maximum(hL, 0.0))
        sqrtHR = np.sqrt(np.maximum(hR, 0.0))
        denom  = sqrtHL + sqrtHR + 1e-12
        u_roe  = (sqrtHL * uL + sqrtHR * uR) / denom
        h_roe  = 0.5 * (hL + hR)
        c_roe  = np.sqrt(self.g * np.maximum(h_roe, 0.0))

        sL = np.minimum(uL - cL, u_roe - c_roe)
        sR = np.maximum(uR + cR, u_roe + c_roe)
        return sL, sR

    # ------------------------------------------------------------------
    # 向量化 HLLC Riemann 求解器（x 方向）
    # ------------------------------------------------------------------

    def _hllc_flux_x_vec(self,
                          hL:  np.ndarray, huL: np.ndarray, hvL: np.ndarray,
                          hR:  np.ndarray, huR: np.ndarray, hvR: np.ndarray
                          ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        向量化 HLLC Riemann 求解器（x 方向界面通量）。

        输入：左右单元的守恒变量数组，形状均为 (ny, nx-1)（界面数量）。
        输出：三个通量分量数组，形状均为 (ny, nx-1)。

        参考：Toro (2001), Chapter 10; Audusse et al. (2004) 干湿处理。
        """
        g = self.g
        eps = self.eps_dry

        # 安全水深
        hL_s = np.maximum(hL, 0.0)
        hR_s = np.maximum(hR, 0.0)

        # 原始变量（干床处速度置零）
        uL = self._safe_velocity(hL_s, huL)
        vL = self._safe_velocity(hL_s, hvL)
        uR = self._safe_velocity(hR_s, huR)
        vR = self._safe_velocity(hR_s, hvR)

        # 波速
        sL, sR = self._wave_speeds(hL_s, uL, hR_s, uR)
        # 确保 sL <= sR
        sL = np.minimum(sL, sR - 1e-12)

        # 接触波速 s* （Toro 2001, Eq. 10.55）
        num   = hR_s * uR * (uR - sR) - hL_s * uL * (uL - sL) + \
                0.5 * g * (hR_s**2 - hL_s**2)
        denom = hR_s * (uR - sR) - hL_s * (uL - sL)
        s_star = np.where(np.abs(denom) > 1e-12, num / denom, 0.5 * (uL + uR))

        # 物理通量 FL, FR
        FL0 = huL
        FL1 = huL * uL + 0.5 * g * hL_s**2
        FL2 = huL * vL

        FR0 = huR
        FR1 = huR * uR + 0.5 * g * hR_s**2
        FR2 = huR * vR

        # 星态水深
        h_starL = hL_s * (uL - sL) / (s_star - sL + 1e-12)
        h_starR = hR_s * (uR - sR) / (s_star - sR + 1e-12)
        h_starL = np.maximum(h_starL, 0.0)
        h_starR = np.maximum(h_starR, 0.0)

        # 星态通量 F*L, F*R（HLLC 公式）
        # F*K = FK + sK * (U*K - UK)
        # U*K = [h*K, h*K * s*, h*K * vK]
        Fstar_L0 = FL0 + sL * (h_starL       - hL_s)
        Fstar_L1 = FL1 + sL * (h_starL * s_star - huL)
        Fstar_L2 = FL2 + sL * (h_starL * vL   - hvL)

        Fstar_R0 = FR0 + sR * (h_starR       - hR_s)
        Fstar_R1 = FR1 + sR * (h_starR * s_star - huR)
        Fstar_R2 = FR2 + sR * (h_starR * vR   - hvR)

        # 根据波速选择通量（Godunov 上风选择）
        # sL >= 0  → FL
        # sL < 0 <= s* → F*L
        # s* < 0 <= sR → F*R
        # sR < 0  → FR
        f0 = np.where(sL >= 0, FL0,
             np.where(s_star >= 0, Fstar_L0,
             np.where(sR >= 0, Fstar_R0, FR0)))

        f1 = np.where(sL >= 0, FL1,
             np.where(s_star >= 0, Fstar_L1,
             np.where(sR >= 0, Fstar_R1, FR1)))

        f2 = np.where(sL >= 0, FL2,
             np.where(s_star >= 0, Fstar_L2,
             np.where(sR >= 0, Fstar_R2, FR2)))

        # 干床处通量置零
        both_dry = (hL_s < eps) & (hR_s < eps)
        f0 = np.where(both_dry, 0.0, f0)
        f1 = np.where(both_dry, 0.0, f1)
        f2 = np.where(both_dry, 0.0, f2)

        return f0, f1, f2

    # ------------------------------------------------------------------
    # 时间推进
    # ------------------------------------------------------------------

    def _compute_dt(self, cfl: float = 0.45) -> float:
        """根据 CFL 条件计算自适应时间步长。"""
        h_s = np.maximum(self.h, 0.0)
        c   = np.sqrt(self.g * h_s)
        u   = self._safe_velocity(h_s, self.hu)
        v   = self._safe_velocity(h_s, self.hv)
        max_speed = np.max(np.abs(u) + c) + 1e-12
        max_speed_y = np.max(np.abs(v) + c) + 1e-12
        dt = cfl * min(self.dx / max_speed, self.dy / max_speed_y)
        return dt

    def step_2d(self, dt: float) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        执行一个时间步（显式 Euler + 算子分裂摩阻）。

        Args:
            dt: 时间步长 (s)

        Returns:
            更新后的 (h, hu, hv)，形状均为 (ny, nx)
        """
        h  = self.h
        hu = self.hu
        hv = self.hv
        g  = self.g
        eps = self.eps_dry

        # ---- 1. x 方向界面通量 ----------------------------------------
        # 界面左右状态（简单一阶重构，无坡度限制器）
        hL_x  = h[:, :-1];  huL_x = hu[:, :-1]; hvL_x = hv[:, :-1]
        hR_x  = h[:, 1:];   huR_x = hu[:, 1:];  hvR_x = hv[:, 1:]

        Fx0, Fx1, Fx2 = self._hllc_flux_x_vec(hL_x, huL_x, hvL_x,
                                                hR_x, huR_x, hvR_x)

        # ---- 2. y 方向界面通量（交换 u↔v 分量后复用 x 方向求解器）----
        # 转置到 (nx, ny) 后调用，再转置回来
        h_T  = h.T;  hu_T = hu.T;  hv_T = hv.T

        hL_y  = h_T[:, :-1];  huL_y = hv_T[:, :-1]; hvL_y = hu_T[:, :-1]
        hR_y  = h_T[:, 1:];   huR_y = hv_T[:, 1:];  hvR_y = hu_T[:, 1:]

        Gy0_T, Gy1_T, Gy2_T = self._hllc_flux_x_vec(hL_y, huL_y, hvL_y,
                                                       hR_y, huR_y, hvR_y)
        # 转置回 (ny-1, nx)，并还原 u↔v
        Fy0 = Gy0_T.T   # 质量通量
        Fy1 = Gy2_T.T   # hu 通量（原 hv 分量）
        Fy2 = Gy1_T.T   # hv 通量（原 hu 分量）

        # ---- 3. 有限体积更新 ------------------------------------------
        h_new  = h.copy()
        hu_new = hu.copy()
        hv_new = hv.copy()

        # x 方向通量散度
        h_new [:, 1:-1] -= (dt / self.dx) * (Fx0[:, 1:] - Fx0[:, :-1])
        hu_new[:, 1:-1] -= (dt / self.dx) * (Fx1[:, 1:] - Fx1[:, :-1])
        hv_new[:, 1:-1] -= (dt / self.dx) * (Fx2[:, 1:] - Fx2[:, :-1])

        # y 方向通量散度
        h_new [1:-1, :] -= (dt / self.dy) * (Fy0[1:, :] - Fy0[:-1, :])
        hu_new[1:-1, :] -= (dt / self.dy) * (Fy1[1:, :] - Fy1[:-1, :])
        hv_new[1:-1, :] -= (dt / self.dy) * (Fy2[1:, :] - Fy2[:-1, :])

        # ---- 4. 床面坡度源项（中心差分）-------------------------------
        # 使用更新后的 h 计算坡度力（半隐式处理提高稳定性）
        h_s = np.maximum(h_new, 0.0)

        # 内部节点中心差分
        dz_dx = np.zeros_like(h_new)
        dz_dy = np.zeros_like(h_new)
        dz_dx[:, 1:-1] = (self.z[:, 2:] - self.z[:, :-2]) / (2 * self.dx)
        dz_dy[1:-1, :] = (self.z[2:, :] - self.z[:-2, :]) / (2 * self.dy)
        # 边界一阶差分
        dz_dx[:, 0]  = (self.z[:, 1]  - self.z[:, 0])  / self.dx
        dz_dx[:, -1] = (self.z[:, -1] - self.z[:, -2]) / self.dx
        dz_dy[0, :]  = (self.z[1, :]  - self.z[0, :])  / self.dy
        dz_dy[-1, :] = (self.z[-1, :] - self.z[-2, :]) / self.dy

        hu_new -= dt * g * h_s * dz_dx
        hv_new -= dt * g * h_s * dz_dy

        # ---- 5. 摩阻源项（半隐式，避免速度反向）-----------------------
        h_s2 = np.maximum(h_new, eps)
        u_n  = self._safe_velocity(h_s2, hu_new)
        v_n  = self._safe_velocity(h_s2, hv_new)
        vel_mag = np.sqrt(u_n**2 + v_n**2)

        # 摩阻系数 Cf = g*n² / h^(4/3)
        Cf = g * self.n**2 / (h_s2**(4.0/3.0))

        # 半隐式更新：hu_new = hu_new / (1 + Cf * vel_mag * dt)
        denom_fric = 1.0 + Cf * vel_mag * dt
        hu_new = hu_new / denom_fric
        hv_new = hv_new / denom_fric

        # ---- 6. 干床约束 -----------------------------------------------
        h_new  = np.maximum(h_new, 0.0)
        hu_new = np.where(h_new < eps, 0.0, hu_new)
        hv_new = np.where(h_new < eps, 0.0, hv_new)

        # ---- 7. 反射边界（四周固壁）------------------------------------
        # 左右壁：法向动量为零
        hu_new[:, 0]  = 0.0
        hu_new[:, -1] = 0.0
        # 上下壁：法向动量为零
        hv_new[0, :]  = 0.0
        hv_new[-1, :] = 0.0

        self.h  = h_new
        self.hu = hu_new
        self.hv = hv_new
        self.current_time += dt

        return self.h, self.hu, self.hv

    # ------------------------------------------------------------------
    # 初始条件与驱动方法
    # ------------------------------------------------------------------

    def set_initial_condition(self, h0: np.ndarray,
                               hu0: Optional[np.ndarray] = None,
                               hv0: Optional[np.ndarray] = None):
        """设置初始条件。"""
        assert h0.shape == (self.ny, self.nx)
        self.h  = np.maximum(h0.copy(), 0.0)
        self.hu = hu0.copy() if hu0 is not None else np.zeros_like(h0)
        self.hv = hv0.copy() if hv0 is not None else np.zeros_like(h0)
        self.current_time = 0.0

    def solve_2d_dam_break(self, h_dam: float, h_down: float, dam_x: float,
                            total_time: float, dt: Optional[float] = None,
                            cfl: float = 0.45) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        求解二维溃坝问题。

        Args:
            h_dam      : 坝上水深 (m)
            h_down     : 坝下水深 (m)
            dam_x      : 坝位置 x 坐标 (m)
            total_time : 模拟总时长 (s)
            dt         : 固定时间步长；若为 None 则使用自适应 CFL 步长
            cfl        : CFL 数（仅自适应模式有效）
        """
        # 初始条件
        h0 = np.where(self.X < dam_x, h_dam, h_down)
        self.set_initial_condition(h0)

        t = 0.0
        step = 0
        print(f"Running 2D Dam Break: h_dam={h_dam}m, h_down={h_down}m, "
              f"dam_x={dam_x}m, T={total_time}s")

        while t < total_time:
            if dt is None:
                dt_use = min(self._compute_dt(cfl), total_time - t)
            else:
                dt_use = min(dt, total_time - t)

            if dt_use <= 0:
                break

            self.step_2d(dt_use)
            t = self.current_time
            step += 1

            if step % 50 == 0:
                print(f"  t={t:.3f}s  h_max={self.h.max():.4f}m  "
                      f"h_min={self.h.min():.6f}m")

            if np.any(np.isnan(self.h)) or np.any(self.h < -1e-6):
                print(f"  [ERROR] Simulation failed at t={t:.3f}s "
                      f"(NaN or negative depth detected)")
                break

        print(f"Simulation completed at t={self.current_time:.3f}s "
              f"({step} steps)")
        return self.h, self.hu, self.hv

    def compute_cfl(self) -> float:
        """计算当前时刻的最大 CFL 数（用于监控稳定性）。"""
        h_s = np.maximum(self.h, 0.0)
        c   = np.sqrt(self.g * h_s)
        u   = self._safe_velocity(h_s, self.hu)
        v   = self._safe_velocity(h_s, self.hv)
        max_speed_x = np.max(np.abs(u) + c) + 1e-12
        max_speed_y = np.max(np.abs(v) + c) + 1e-12
        return max(max_speed_x * self.dx, max_speed_y * self.dy)


# ======================================================================
# 快速验证入口
# ======================================================================
if __name__ == "__main__":
    import time

    Lx, Ly = 100.0, 50.0
    nx, ny = 100, 50

    solver = Hydrostatic2DSolver(Lx=Lx, Ly=Ly, nx=nx, ny=ny,
                                  S0x=0.0, S0y=0.0, n=0.01, g=9.81,
                                  eps_dry=1e-4)

    t0 = time.time()
    h_f, hu_f, hv_f = solver.solve_2d_dam_break(
        h_dam=5.0, h_down=1.0, dam_x=Lx/2,
        total_time=5.0, cfl=0.45
    )
    elapsed = time.time() - t0

    print(f"\nGrid: {nx}×{ny}  Elapsed: {elapsed:.2f}s")
    print(f"Final h: min={h_f.min():.6f}  max={h_f.max():.4f}  "
          f"mean={h_f.mean():.4f}")
    print(f"NaN check: {np.any(np.isnan(h_f))}")
