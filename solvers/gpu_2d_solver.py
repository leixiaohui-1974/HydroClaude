"""
gpu_2d_solver.py — GPU 加速的 2D 浅水方程求解器

采用透明后端设计（NumPy/CuPy 兼容接口）：
  - 有 GPU 时自动使用 CuPy，实现 CUDA 并行加速
  - 无 GPU 时自动回退到 NumPy，功能完全相同

数值方法与 Hydrostatic2DSolver 完全一致：
  - 向量化 HLLC Riemann 求解器
  - Audusse 干湿边界水位重构
  - 显式 Euler 时间推进
  - 算子分裂摩阻源项

GPU 加速原理：
  - 所有数组存储在 GPU 显存（cupy.ndarray）
  - HLLC 通量计算、源项更新等全部在 GPU 上并行执行
  - 避免 CPU-GPU 数据传输瓶颈（仅在初始化和结果提取时传输）
  - 对于 1000×1000 以上的网格，GPU 加速比可达 10-50×

参考文献：
  - Toro, E.F. (2001). Shock-Capturing Methods for Free-Surface Shallow Flows.
  - Audusse et al. (2004). A fast and stable well-balanced scheme with hydrostatic reconstruction.
  - NVIDIA (2023). CuPy: A NumPy/SciPy-compatible array library for GPU-accelerated computing.
"""

from typing import Optional, Tuple
import numpy as np

# ---------------------------------------------------------------------------
# GPU 后端检测与选择
# ---------------------------------------------------------------------------

def _detect_backend():
    """
    检测 CuPy 是否可用，返回 (xp, backend_name, device_info)。

    Returns:
        xp          : cupy 或 numpy 模块
        backend     : 'cuda' 或 'cpu'
        device_info : GPU 设备信息字符串（无 GPU 时为 'CPU (NumPy)'）
    """
    try:
        import cupy as cp
        # 验证 GPU 实际可用
        cp.array([1.0])
        n_gpu = cp.cuda.runtime.getDeviceCount()
        device = cp.cuda.Device(0)
        mem_total = device.mem_info[1] / (1024**3)
        device_info = f"CUDA GPU x{n_gpu} ({mem_total:.1f} GB)"
        return cp, 'cuda', device_info
    except Exception:
        return np, 'cpu', 'CPU (NumPy fallback)'


_XP, _BACKEND, _DEVICE_INFO = _detect_backend()


def get_backend_info() -> dict:
    """返回当前后端信息。"""
    return {
        'backend': _BACKEND,
        'device': _DEVICE_INFO,
        'gpu_available': _BACKEND == 'cuda',
    }


# ---------------------------------------------------------------------------
# GPU 加速 2D 浅水方程求解器
# ---------------------------------------------------------------------------

class GPU2DSolver:
    """
    GPU 加速的 2D 浅水方程（SWE）有限体积求解器。

    与 Hydrostatic2DSolver 接口完全兼容，可直接替换。
    在有 GPU 的环境中自动使用 CuPy 加速，无 GPU 时回退到 NumPy。

    性能特点：
      - GPU 模式：所有计算在 GPU 上并行执行，适合大规模网格（>500×500）
      - CPU 模式：与 Hydrostatic2DSolver 等效，适合小规模网格和调试

    Attributes:
        xp      : 数组后端（cupy 或 numpy）
        backend : 'cuda' 或 'cpu'
    """

    def __init__(self, Lx: float, Ly: float, nx: int, ny: int,
                 S0x: float = 0.0, S0y: float = 0.0,
                 n: float = 0.025, g: float = 9.81,
                 eps_dry: float = 1e-4,
                 z_bed: Optional[np.ndarray] = None,
                 force_cpu: bool = False):
        """
        Args:
            Lx, Ly    : 计算域长度和宽度 (m)
            nx, ny    : x 和 y 方向的格点数
            S0x, S0y  : x 和 y 方向的床面坡度
            n         : Manning 糙率系数
            g         : 重力加速度 (m/s²)
            eps_dry   : 干床阈值 (m)
            z_bed     : 自定义床面高程数组，形状 (ny, nx)
            force_cpu : 强制使用 CPU（用于调试或对比）
        """
        # 选择后端
        if force_cpu:
            self.xp = np
            self.backend = 'cpu'
            self.device_info = 'CPU (forced)'
        else:
            self.xp = _XP
            self.backend = _BACKEND
            self.device_info = _DEVICE_INFO

        xp = self.xp

        # 网格参数
        self.Lx = Lx
        self.Ly = Ly
        self.nx = nx
        self.ny = ny
        self.dx = Lx / nx
        self.dy = Ly / ny
        self.S0x = S0x
        self.S0y = S0y
        self.n = n
        self.g = g
        self.eps_dry = eps_dry

        # 单元中心坐标（GPU 数组）
        x_cpu = np.linspace(self.dx / 2, Lx - self.dx / 2, nx)
        y_cpu = np.linspace(self.dy / 2, Ly - self.dy / 2, ny)
        X_cpu, Y_cpu = np.meshgrid(x_cpu, y_cpu)

        self.x = xp.array(x_cpu)
        self.y = xp.array(y_cpu)
        self.X = xp.array(X_cpu)
        self.Y = xp.array(Y_cpu)

        # 床面高程（GPU 数组）
        if z_bed is not None:
            assert z_bed.shape == (ny, nx), "z_bed shape must be (ny, nx)"
            self.z = xp.array(z_bed.copy())
        else:
            self.z = xp.array(-S0x * X_cpu - S0y * Y_cpu)

        # 守恒变量（GPU 数组）
        self.h  = xp.zeros((ny, nx))
        self.hu = xp.zeros((ny, nx))
        self.hv = xp.zeros((ny, nx))

        # 时间
        self.t = 0.0

    # ------------------------------------------------------------------
    # 工具方法
    # ------------------------------------------------------------------

    def _safe_velocity(self, h: 'xp.ndarray', hm: 'xp.ndarray') -> 'xp.ndarray':
        """安全计算速度（避免除以零）。"""
        xp = self.xp
        return xp.where(h > self.eps_dry, hm / h, xp.zeros_like(hm))

    def to_numpy(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        将 GPU 数组传输到 CPU（NumPy）。

        Returns:
            (h, u, v) : 水深和速度的 NumPy 数组
        """
        if self.backend == 'cuda':
            h  = self.h.get()
            hu = self.hu.get()
            hv = self.hv.get()
        else:
            h  = np.array(self.h)
            hu = np.array(self.hu)
            hv = np.array(self.hv)
        u = np.where(h > self.eps_dry, hu / h, 0.0)
        v = np.where(h > self.eps_dry, hv / h, 0.0)
        return h, u, v

    def set_initial_condition(self, h: np.ndarray,
                               hu: Optional[np.ndarray] = None,
                               hv: Optional[np.ndarray] = None):
        """
        设置初始条件（从 CPU NumPy 数组传输到 GPU）。

        Args:
            h  : 初始水深 (ny, nx)
            hu : 初始 x 方向动量（可选）
            hv : 初始 y 方向动量（可选）
        """
        xp = self.xp
        self.h  = xp.array(h.copy())
        self.hu = xp.array(hu.copy()) if hu is not None else xp.zeros_like(self.h)
        self.hv = xp.array(hv.copy()) if hv is not None else xp.zeros_like(self.h)

    # ------------------------------------------------------------------
    # HLLC Riemann 求解器（向量化，GPU 友好）
    # ------------------------------------------------------------------

    def _hllc_flux_x(self,
                     hL: 'xp.ndarray', huL: 'xp.ndarray', hvL: 'xp.ndarray',
                     hR: 'xp.ndarray', huR: 'xp.ndarray', hvR: 'xp.ndarray',
                     ) -> Tuple['xp.ndarray', 'xp.ndarray', 'xp.ndarray']:
        """
        x 方向向量化 HLLC 通量（Toro, 2001）。

        所有输入均为 GPU 数组，运算全部在 GPU 上执行。
        """
        xp = self.xp
        g = self.g
        eps = self.eps_dry

        # 安全速度
        uL = xp.where(hL > eps, huL / hL, xp.zeros_like(huL))
        uR = xp.where(hR > eps, huR / hR, xp.zeros_like(huR))
        vL = xp.where(hL > eps, hvL / hL, xp.zeros_like(hvL))
        vR = xp.where(hR > eps, hvR / hR, xp.zeros_like(hvR))

        cL = xp.sqrt(g * xp.maximum(hL, 0.0))
        cR = xp.sqrt(g * xp.maximum(hR, 0.0))

        # Einfeldt 波速估计
        sL = xp.minimum(uL - cL, uR - cR)
        sR = xp.maximum(uL + cL, uR + cR)

        # 干床处理
        dry_L = hL <= eps
        dry_R = hR <= eps
        sL = xp.where(dry_L & ~dry_R, uR - 2.0 * cR, sL)
        sR = xp.where(dry_L & ~dry_R, uR + 2.0 * cR, sR)
        sL = xp.where(~dry_L & dry_R, uL - 2.0 * cL, sL)
        sR = xp.where(~dry_L & dry_R, uL + 2.0 * cL, sR)

        # 中间波速
        num   = hR * uR * (sR - uR) - hL * uL * (sL - uL) + 0.5 * g * (hL**2 - hR**2)
        denom = hR * (sR - uR) - hL * (sL - uL)
        s_star = xp.where(xp.abs(denom) > 1e-12, num / denom, 0.5 * (uL + uR))
        s_star = xp.clip(s_star, sL, sR)

        # 物理通量
        FL_h  = huL
        FL_hu = huL * uL + 0.5 * g * hL**2
        FL_hv = huL * vL

        FR_h  = huR
        FR_hu = huR * uR + 0.5 * g * hR**2
        FR_hv = huR * vR

        # HLLC 星区状态
        coeff_L = hL * (sL - uL) / (sL - s_star + 1e-30)
        coeff_R = hR * (sR - uR) / (sR - s_star + 1e-30)

        h_starL  = xp.maximum(coeff_L, 0.0)
        hu_starL = h_starL * s_star
        hv_starL = h_starL * vL

        h_starR  = xp.maximum(coeff_R, 0.0)
        hu_starR = h_starR * s_star
        hv_starR = h_starR * vR

        # HLLC 通量选择
        F_h  = xp.where(sL >= 0, FL_h,
               xp.where(s_star >= 0,
                        FL_h  + sL * (h_starL  - hL),
               xp.where(sR >= 0,
                        FR_h  + sR * (h_starR  - hR),
                        FR_h)))
        F_hu = xp.where(sL >= 0, FL_hu,
               xp.where(s_star >= 0,
                        FL_hu + sL * (hu_starL - huL),
               xp.where(sR >= 0,
                        FR_hu + sR * (hu_starR - huR),
                        FR_hu)))
        F_hv = xp.where(sL >= 0, FL_hv,
               xp.where(s_star >= 0,
                        FL_hv + sL * (hv_starL - hvL),
               xp.where(sR >= 0,
                        FR_hv + sR * (hv_starR - hvR),
                        FR_hv)))

        # 全干时通量为零
        both_dry = dry_L & dry_R
        F_h  = xp.where(both_dry, xp.zeros_like(F_h),  F_h)
        F_hu = xp.where(both_dry, xp.zeros_like(F_hu), F_hu)
        F_hv = xp.where(both_dry, xp.zeros_like(F_hv), F_hv)

        return F_h, F_hu, F_hv

    def _hllc_flux_y(self,
                     hB: 'xp.ndarray', huB: 'xp.ndarray', hvB: 'xp.ndarray',
                     hT: 'xp.ndarray', huT: 'xp.ndarray', hvT: 'xp.ndarray',
                     ) -> Tuple['xp.ndarray', 'xp.ndarray', 'xp.ndarray']:
        """y 方向 HLLC 通量（通过旋转对称性复用 x 方向求解器）。"""
        # 旋转：(h, hu, hv) -> (h, hv, hu)，计算 x 通量后再旋转回来
        G_h, G_hv, G_hu = self._hllc_flux_x(hB, hvB, huB, hT, hvT, huT)
        return G_h, G_hu, G_hv

    # ------------------------------------------------------------------
    # 时间推进
    # ------------------------------------------------------------------

    def compute_dt(self, cfl: float = 0.45) -> float:
        """
        基于 CFL 条件计算最大允许时间步。

        Args:
            cfl : CFL 数（默认 0.45）

        Returns:
            dt : 最大允许时间步 (s)
        """
        xp = self.xp
        h = self.h
        u = self._safe_velocity(h, self.hu)
        v = self._safe_velocity(h, self.hv)
        c = xp.sqrt(xp.maximum(self.g * h, 0.0))

        max_spd_x = float(xp.max(xp.abs(u) + c)) + 1e-10
        max_spd_y = float(xp.max(xp.abs(v) + c)) + 1e-10

        dt_x = cfl * self.dx / max_spd_x
        dt_y = cfl * self.dy / max_spd_y
        return min(dt_x, dt_y)

    def step(self, dt: float):
        """
        推进一个时间步（显式 Euler + 算子分裂摩阻）。

        所有计算在 GPU 上执行（若 backend='cuda'）。

        Args:
            dt : 时间步长 (s)
        """
        xp = self.xp
        g = self.g
        eps = self.eps_dry
        dx, dy = self.dx, self.dy

        h  = self.h
        hu = self.hu
        hv = self.hv
        z  = self.z

        # ---- Audusse 水位重构（干湿边界处理）--------------------------
        eta = h + z  # 水面高程

        # x 方向界面（i+1/2）
        eta_iph_L = eta[:, :-1]   # 左侧水面高程
        eta_iph_R = eta[:, 1:]    # 右侧水面高程
        z_iph     = xp.maximum(z[:, :-1], z[:, 1:])  # 界面床面高程

        hL_x = xp.maximum(eta_iph_L - z_iph, 0.0)
        hR_x = xp.maximum(eta_iph_R - z_iph, 0.0)
        huL_x = xp.where(h[:, :-1] > eps, hu[:, :-1] * hL_x / h[:, :-1], xp.zeros_like(hL_x))
        huR_x = xp.where(h[:, 1:]  > eps, hu[:, 1:]  * hR_x / h[:, 1:],  xp.zeros_like(hR_x))
        hvL_x = xp.where(h[:, :-1] > eps, hv[:, :-1] * hL_x / h[:, :-1], xp.zeros_like(hL_x))
        hvR_x = xp.where(h[:, 1:]  > eps, hv[:, 1:]  * hR_x / h[:, 1:],  xp.zeros_like(hR_x))

        # y 方向界面（j+1/2）
        eta_jph_B = eta[:-1, :]
        eta_jph_T = eta[1:, :]
        z_jph     = xp.maximum(z[:-1, :], z[1:, :])

        hB_y = xp.maximum(eta_jph_B - z_jph, 0.0)
        hT_y = xp.maximum(eta_jph_T - z_jph, 0.0)
        huB_y = xp.where(h[:-1, :] > eps, hu[:-1, :] * hB_y / h[:-1, :], xp.zeros_like(hB_y))
        huT_y = xp.where(h[1:, :]  > eps, hu[1:, :]  * hT_y / h[1:, :],  xp.zeros_like(hT_y))
        hvB_y = xp.where(h[:-1, :] > eps, hv[:-1, :] * hB_y / h[:-1, :], xp.zeros_like(hB_y))
        hvT_y = xp.where(h[1:, :]  > eps, hv[1:, :]  * hT_y / h[1:, :],  xp.zeros_like(hT_y))

        # ---- HLLC 通量计算（全 GPU 并行）------------------------------
        Fx_h, Fx_hu, Fx_hv = self._hllc_flux_x(hL_x, huL_x, hvL_x, hR_x, huR_x, hvR_x)
        Gy_h, Gy_hu, Gy_hv = self._hllc_flux_y(hB_y, huB_y, hvB_y, hT_y, huT_y, hvT_y)

        # ---- 通量散度（内部格点）--------------------------------------
        # Fx 形状：(ny, nx-1)，内部列索引 1..nx-2
        # Gy 形状：(ny-1, nx)，内部行索引 1..ny-2
        # 内部格点的散度：(ny-2, nx-2)
        div_h  = (Fx_h[1:-1, 1:]  - Fx_h[1:-1, :-1])  / dx \
               + (Gy_h[1:, 1:-1]  - Gy_h[:-1, 1:-1])  / dy
        div_hu = (Fx_hu[1:-1, 1:] - Fx_hu[1:-1, :-1]) / dx \
               + (Gy_hu[1:, 1:-1] - Gy_hu[:-1, 1:-1]) / dy
        div_hv = (Fx_hv[1:-1, 1:] - Fx_hv[1:-1, :-1]) / dx \
               + (Gy_hv[1:, 1:-1] - Gy_hv[:-1, 1:-1]) / dy

        # ---- 床面坡度源项（Audusse well-balanced）---------------------
        # x 方向：-g * h * ∂z/∂x ≈ -g * h_avg * (z_R - z_L) / dx
        # Sx 形状：(ny, nx-1)
        Sx = -g * 0.5 * (hL_x + hR_x) * (z[:, 1:] - z[:, :-1]) / dx
        # Sy 形状：(ny-1, nx)
        Sy = -g * 0.5 * (hB_y + hT_y) * (z[1:, :] - z[:-1, :]) / dy

        # 内部格点的床面坡度源项：(ny-2, nx-2)
        # Sx 内部列对应内部格点的 x 界面平均
        src_hu_int = 0.5 * (Sx[1:-1, :-1] + Sx[1:-1, 1:])
        src_hv_int = 0.5 * (Sy[:-1, 1:-1] + Sy[1:, 1:-1])

        # ---- 显式 Euler 更新（内部格点）-------------------------------
        h_new  = h.copy()
        hu_new = hu.copy()
        hv_new = hv.copy()

        # 内部格点（索引 1:-1, 1:-1）
        h_new[1:-1, 1:-1]  = h[1:-1, 1:-1]  - dt * div_h
        hu_new[1:-1, 1:-1] = hu[1:-1, 1:-1] - dt * div_hu + dt * src_hu_int
        hv_new[1:-1, 1:-1] = hv[1:-1, 1:-1] - dt * div_hv + dt * src_hv_int

        # 边界：零梯度（Neumann）
        h_new[0, :]   = h_new[1, :]
        h_new[-1, :]  = h_new[-2, :]
        h_new[:, 0]   = h_new[:, 1]
        h_new[:, -1]  = h_new[:, -2]

        hu_new[0, :]  = hu_new[1, :]
        hu_new[-1, :] = hu_new[-2, :]
        hu_new[:, 0]  = xp.zeros(self.ny)
        hu_new[:, -1] = xp.zeros(self.ny)

        hv_new[0, :]  = xp.zeros(self.nx)
        hv_new[-1, :] = xp.zeros(self.nx)
        hv_new[:, 0]  = hv_new[:, 1]
        hv_new[:, -1] = hv_new[:, -2]

        # 干床约束
        h_new = xp.maximum(h_new, 0.0)

        # ---- 摩阻源项（算子分裂，半隐式）------------------------------
        wet = h_new > eps
        u_new = xp.where(wet, hu_new / h_new, xp.zeros_like(hu_new))
        v_new = xp.where(wet, hv_new / h_new, xp.zeros_like(hv_new))
        spd   = xp.sqrt(u_new**2 + v_new**2)

        # Manning 摩阻系数
        Cf = xp.where(wet,
                      g * self.n**2 / xp.maximum(h_new, eps)**(1.0/3.0),
                      xp.zeros_like(h_new))

        # 半隐式处理：u^{n+1} = u^n / (1 + Cf * |V| * dt)
        denom_fric = 1.0 + Cf * spd * dt
        hu_new = xp.where(wet, h_new * u_new / denom_fric, xp.zeros_like(hu_new))
        hv_new = xp.where(wet, h_new * v_new / denom_fric, xp.zeros_like(hv_new))

        self.h  = h_new
        self.hu = hu_new
        self.hv = hv_new
        self.t += dt

    def run(self, t_end: float, cfl: float = 0.45,
            output_interval: Optional[float] = None) -> list:
        """
        运行模拟到指定时间。

        Args:
            t_end           : 模拟结束时间 (s)
            cfl             : CFL 数
            output_interval : 输出间隔 (s)；None 表示只输出最终结果

        Returns:
            snapshots : 快照列表，每个元素为 {'t': float, 'h': np.ndarray, ...}
        """
        snapshots = []
        next_output = 0.0

        while self.t < t_end:
            dt = min(self.compute_dt(cfl), t_end - self.t)
            self.step(dt)

            if output_interval is not None and self.t >= next_output - 1e-10:
                h, u, v = self.to_numpy()
                snapshots.append({'t': self.t, 'h': h, 'u': u, 'v': v})
                next_output += output_interval

        # 最终状态
        h, u, v = self.to_numpy()
        snapshots.append({'t': self.t, 'h': h, 'u': u, 'v': v})
        return snapshots


# ---------------------------------------------------------------------------
# 性能基准测试工具
# ---------------------------------------------------------------------------

def benchmark(nx: int = 200, ny: int = 200, n_steps: int = 100,
              force_cpu: bool = False) -> dict:
    """
    运行性能基准测试，比较 GPU 和 CPU 的计算速度。

    Args:
        nx, ny   : 网格尺寸
        n_steps  : 测试步数
        force_cpu: 强制使用 CPU

    Returns:
        result : 包含时间、吞吐量等性能指标的字典
    """
    import time

    solver = GPU2DSolver(Lx=1000.0, Ly=1000.0, nx=nx, ny=ny,
                         force_cpu=force_cpu)

    # 初始化：中心溃坝
    h_init = np.ones((ny, nx)) * 0.1
    h_init[ny//4:3*ny//4, nx//4:3*nx//4] = 1.0
    solver.set_initial_condition(h_init)

    # 预热
    solver.step(0.01)

    # 计时
    t_start = time.perf_counter()
    for _ in range(n_steps):
        solver.step(0.01)
    # 同步（GPU 需要等待所有操作完成）
    if solver.backend == 'cuda':
        solver.xp.cuda.Stream.null.synchronize()
    t_end = time.perf_counter()

    elapsed = t_end - t_start
    cells_per_sec = nx * ny * n_steps / elapsed

    return {
        'backend': solver.backend,
        'device': solver.device_info,
        'grid': f'{nx}x{ny}',
        'n_steps': n_steps,
        'elapsed_s': elapsed,
        'steps_per_sec': n_steps / elapsed,
        'mcells_per_sec': cells_per_sec / 1e6,
    }


if __name__ == '__main__':
    # 打印后端信息
    info = get_backend_info()
    print(f"Backend: {info['backend']} | Device: {info['device']}")

    # CPU 基准测试
    print("\nRunning CPU benchmark (200x200, 100 steps)...")
    result_cpu = benchmark(200, 200, 100, force_cpu=True)
    print(f"  Elapsed: {result_cpu['elapsed_s']:.2f}s | "
          f"Speed: {result_cpu['steps_per_sec']:.1f} steps/s | "
          f"Throughput: {result_cpu['mcells_per_sec']:.2f} MCells/s")

    # GPU 基准测试（如果可用）
    if info['gpu_available']:
        print("\nRunning GPU benchmark (200x200, 100 steps)...")
        result_gpu = benchmark(200, 200, 100, force_cpu=False)
        print(f"  Elapsed: {result_gpu['elapsed_s']:.2f}s | "
              f"Speed: {result_gpu['steps_per_sec']:.1f} steps/s | "
              f"Throughput: {result_gpu['mcells_per_sec']:.2f} MCells/s")
        speedup = result_cpu['elapsed_s'] / result_gpu['elapsed_s']
        print(f"  GPU Speedup: {speedup:.1f}x")
    else:
        print("\nNo GPU available. To enable GPU acceleration, install CuPy:")
        print("  pip install cupy-cuda12x  # for CUDA 12.x")
        print("  pip install cupy-cuda11x  # for CUDA 11.x")
