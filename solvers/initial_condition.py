"""从稳态求解器计算非恒定流初始条件。

复用 SteadyProfileSolver 的全部已验证逻辑（分区 K、结构物、能量方程），
从 HEC-RAS 原始输入数据（几何 + Manning n + 边界条件）生成初始水面线。

对于溃坝等特殊案例，提供基于正常水深的简单初始化。
"""

import numpy as np
from solvers.steady_profile_solver import SteadyProfileSolver
from physics.property_table import subdivided_conveyance


def compute_steady_initial_conditions(
    sections: list,
    bed_elevations: np.ndarray,
    manning_n: np.ndarray,
    reach_lengths: np.ndarray,
    Q_initial: float,
    downstream_wse: float,
    manning_n_lob: np.ndarray | None = None,
    manning_n_rob: np.ndarray | None = None,
    left_bank: np.ndarray | None = None,
    right_bank: np.ndarray | None = None,
    reach_lengths_lob: np.ndarray | None = None,
    reach_lengths_rob: np.ndarray | None = None,
    contraction_coefs: np.ndarray | None = None,
    expansion_coefs: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """用稳态求解器计算初始水面线和流量分布。

    Args:
        sections: NaturalSection 对象列表 [n_xs]
        bed_elevations: 河床高程 [n_xs] (m)
        manning_n: 主槽 Manning n [n_xs]
        reach_lengths: 断面间距 [n_xs-1] (m)
        Q_initial: 初始流量 (m³/s)，取上游边界 t=0 的值
        downstream_wse: 下游水位 (m)，取下游边界 t=0 的值
        manning_n_lob: 左滩 Manning n [n_xs]
        manning_n_rob: 右滩 Manning n [n_xs]
        left_bank: 左岸站号 [n_xs] (m)
        right_bank: 右岸站号 [n_xs] (m)
        reach_lengths_lob: 左滩间距 [n_xs-1] (m)
        reach_lengths_rob: 右滩间距 [n_xs-1] (m)
        contraction_coefs: 收缩系数 [n_xs]
        expansion_coefs: 膨胀系数 [n_xs]

    Returns:
        (Z_init, Q_init): 初始水位 [n_xs] 和流量 [n_xs] (m, m³/s)
    """
    n_xs = len(sections)
    bed = list(bed_elevations)

    # 构建 bank_stations 元组列表
    bank_stations = None
    if left_bank is not None and right_bank is not None:
        bank_stations = list(zip(left_bank.tolist(), right_bank.tolist()))

    # 构建稳态求解器（复用全部已验证逻辑）
    solver = SteadyProfileSolver(
        length=max(float(np.sum(reach_lengths)), 1.0),
        cross_sections=sections,
        bed_elevations=bed,
        manning_ns=list(manning_n),
        reach_lengths=list(reach_lengths),
        reach_lengths_lob=list(reach_lengths_lob) if reach_lengths_lob is not None else None,
        reach_lengths_rob=list(reach_lengths_rob) if reach_lengths_rob is not None else None,
        manning_n_lob=list(manning_n_lob) if manning_n_lob is not None else None,
        manning_n_rob=list(manning_n_rob) if manning_n_rob is not None else None,
        bank_stations=bank_stations,
        contraction_coefs=list(contraction_coefs) if contraction_coefs is not None else None,
        expansion_coefs=list(expansion_coefs) if expansion_coefs is not None else None,
    )

    # 下游水深
    h_downstream = max(downstream_wse - bed[-1], 0.1)

    # 求解稳态水面线
    result = solver.solve_standard_step(
        Q=Q_initial,
        h_downstream=h_downstream,
        nx=n_xs,
    )

    # 提取 WSE
    h_arr = np.array(result["h"])
    if len(h_arr) != n_xs:
        # solve_standard_step 可能返回不同长度，用插值对齐
        x_result = np.array(result["x"])
        x_target = np.zeros(n_xs)
        x_target[0] = 0.0
        for i in range(n_xs - 1):
            x_target[i + 1] = x_target[i] + reach_lengths[i]
        h_arr = np.interp(x_target, x_result, h_arr)

    Z_init = np.array(bed) + h_arr

    # 确保水位不低于河床
    for i in range(n_xs):
        if Z_init[i] < bed[i] + 0.05:
            Z_init[i] = bed[i] + 0.05

    Q_init = np.full(n_xs, Q_initial)

    return Z_init, Q_init


def compute_normal_depth_ic(
    sections: list,
    bed_elevations: np.ndarray,
    manning_n: np.ndarray,
    reach_lengths: np.ndarray,
    Q_initial: float,
    bed_slope: float | None = None,
    manning_n_lob: np.ndarray | None = None,
    manning_n_rob: np.ndarray | None = None,
    left_bank: np.ndarray | None = None,
    right_bank: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """基于正常水深的简单初始条件（适用于溃坝等无稳态的案例）。

    逐断面用 Manning 公式反算正常水深：K(Z) * sqrt(S) = Q。
    """
    from scipy.optimize import brentq

    n_xs = len(sections)
    bed = np.array(bed_elevations)

    # 估算底坡
    if bed_slope is None:
        total_len = float(np.sum(reach_lengths))
        if total_len > 0:
            bed_slope = max((bed[0] - bed[-1]) / total_len, 1e-5)
        else:
            bed_slope = 0.001

    sqrt_s = bed_slope ** 0.5
    Z_init = np.zeros(n_xs)

    for i in range(n_xs):
        sec = sections[i]
        invert = bed[i]
        target_K = abs(Q_initial) / max(sqrt_s, 1e-10)

        has_sub = (left_bank is not None and right_bank is not None
                   and hasattr(sec, 'distances') and hasattr(sec, 'elevations'))

        def _K_at_z(z):
            if has_sub:
                K, _ = subdivided_conveyance(
                    np.asarray(sec.distances), np.asarray(sec.elevations),
                    z, float(left_bank[i]), float(right_bank[i]),
                    float(manning_n_lob[i]) if manning_n_lob is not None else float(manning_n[i]),
                    float(manning_n[i]),
                    float(manning_n_rob[i]) if manning_n_rob is not None else float(manning_n[i]))
                return K
            return sec.compute_conveyance(z, float(manning_n[i]))

        z_hi = invert + 0.1
        for _ in range(50):
            if _K_at_z(z_hi) > target_K:
                break
            z_hi += z_hi - invert
        else:
            Z_init[i] = z_hi
            continue

        try:
            Z_init[i] = brentq(lambda z: _K_at_z(z) - target_K, invert + 1e-6, z_hi, xtol=1e-4)
        except ValueError:
            Z_init[i] = invert + 1.0

    # 保底
    for i in range(n_xs):
        if Z_init[i] < bed[i] + 0.05:
            Z_init[i] = bed[i] + 0.05

    Q_init = np.full(n_xs, Q_initial)
    return Z_init, Q_init
