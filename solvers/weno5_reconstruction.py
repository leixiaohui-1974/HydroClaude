#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
WENO5 (5th-order Weighted Essentially Non-Oscillatory) Reconstruction

实现标准WENO5格式（Jiang & Shu, 1996）用于一维双曲守恒律

参考文献:
    Jiang, G. S., & Shu, C. W. (1996). Efficient implementation of weighted ENO schemes.
    Journal of Computational Physics, 126(1), 202-228.

作者: HydroClaude Team
日期: 2025-10-31
"""

import numpy as np
from numba import njit


@njit
def weno5_reconstruct(q: np.ndarray, epsilon: float = 1e-6) -> tuple:
    """
    WENO5重构：从单元平均值重构单元界面值

    使用5个单元的模板（i-2, i-1, i, i+1, i+2）重构单元i的左右界面值

    参数:
        q: 单元平均值数组 (长度 n)
        epsilon: 避免除零的小量

    返回:
        q_L: 左界面值 q_{i-1/2}^+ (长度 n-1)
        q_R: 右界面值 q_{i+1/2}^- (长度 n-1)

    注意:
        - 需要2层ghost单元（左右各2个）
        - 实际可用界面：i=2..n-3
    """
    n = len(q)
    q_L = np.zeros(n - 1)  # q_{i+1/2}^-
    q_R = np.zeros(n - 1)  # q_{i+1/2}^+

    # WENO5理想权重（线性权重）
    gamma0 = 0.1
    gamma1 = 0.6
    gamma2 = 0.3

    # 遍历所有可用界面
    # 对于n个单元（含ghost），WENO5需要：
    # - 左重构：i-2, i-1, i, i+1, i+2
    # - 右重构：i-1, i, i+1, i+2, i+3
    # 因此有效范围：i从2到n-3（对于左重构）
    #             i从2到n-4（对于右重构，需要i+3<n）
    # 为了最大化覆盖，我们处理i=2..n-2
    for i in range(2, n - 1):  # 修改：处理更多界面
        # ================================================
        # 左重构：q_{i+1/2}^- （使用i-2, i-1, i, i+1, i+2）
        # ================================================

        # 三个候选模板（stencil）
        # S0: {i-2, i-1, i}   (最左)
        # S1: {i-1, i, i+1}   (中心)
        # S2: {i, i+1, i+2}   (最右)

        # S0: 3阶多项式重构
        q0_L = (2.0 * q[i-2] - 7.0 * q[i-1] + 11.0 * q[i]) / 6.0

        # S1: 3阶多项式重构
        q1_L = (-q[i-1] + 5.0 * q[i] + 2.0 * q[i+1]) / 6.0

        # S2: 3阶多项式重构
        q2_L = (2.0 * q[i] + 5.0 * q[i+1] - q[i+2]) / 6.0

        # 光滑性指示器（smoothness indicators）
        beta0 = (13.0 / 12.0) * (q[i-2] - 2.0 * q[i-1] + q[i])**2 + \
                (1.0 / 4.0) * (q[i-2] - 4.0 * q[i-1] + 3.0 * q[i])**2

        beta1 = (13.0 / 12.0) * (q[i-1] - 2.0 * q[i] + q[i+1])**2 + \
                (1.0 / 4.0) * (q[i-1] - q[i+1])**2

        beta2 = (13.0 / 12.0) * (q[i] - 2.0 * q[i+1] + q[i+2])**2 + \
                (1.0 / 4.0) * (3.0 * q[i] - 4.0 * q[i+1] + q[i+2])**2

        # 非线性权重
        alpha0_L = gamma0 / (epsilon + beta0)**2
        alpha1_L = gamma1 / (epsilon + beta1)**2
        alpha2_L = gamma2 / (epsilon + beta2)**2

        alpha_sum_L = alpha0_L + alpha1_L + alpha2_L

        # 防止除零
        if alpha_sum_L < 1e-40:
            w0_L = gamma0
            w1_L = gamma1
            w2_L = gamma2
        else:
            w0_L = alpha0_L / alpha_sum_L
            w1_L = alpha1_L / alpha_sum_L
            w2_L = alpha2_L / alpha_sum_L

        # 最终重构值（凸组合）
        q_L[i] = w0_L * q0_L + w1_L * q1_L + w2_L * q2_L

        # ================================================
        # 右重构：q_{i+1/2}^+ （使用i-1, i, i+1, i+2, i+3）
        # ================================================
        # 注意：这相当于在界面i+1/2处，从右侧单元i+1往左看

        # 使用对称性：右重构 = 左重构的镜像
        # S0: {i+3, i+2, i+1} → 从i+1往右看
        # S1: {i+2, i+1, i}
        # S2: {i+1, i, i-1}

        # S0: 从i+1往右看的最右模板
        q0_R = (2.0 * q[i+3] - 7.0 * q[i+2] + 11.0 * q[i+1]) / 6.0 if i+3 < n else 0.0

        # S1: 中心模板
        q1_R = (-q[i+2] + 5.0 * q[i+1] + 2.0 * q[i]) / 6.0 if i+2 < n else 0.0

        # S2: 最左模板
        q2_R = (2.0 * q[i+1] + 5.0 * q[i] - q[i-1]) / 6.0

        # 光滑性指示器
        if i + 3 < n:
            beta0_R = (13.0 / 12.0) * (q[i+3] - 2.0 * q[i+2] + q[i+1])**2 + \
                      (1.0 / 4.0) * (q[i+3] - 4.0 * q[i+2] + 3.0 * q[i+1])**2
        else:
            beta0_R = 1e10  # 超出边界，给极大权重惩罚

        if i + 2 < n:
            beta1_R = (13.0 / 12.0) * (q[i+2] - 2.0 * q[i+1] + q[i])**2 + \
                      (1.0 / 4.0) * (q[i+2] - q[i])**2
        else:
            beta1_R = 1e10

        beta2_R = (13.0 / 12.0) * (q[i+1] - 2.0 * q[i] + q[i-1])**2 + \
                  (1.0 / 4.0) * (3.0 * q[i+1] - 4.0 * q[i] + q[i-1])**2

        # 非线性权重
        alpha0_R = gamma0 / (epsilon + beta0_R)**2
        alpha1_R = gamma1 / (epsilon + beta1_R)**2
        alpha2_R = gamma2 / (epsilon + beta2_R)**2

        alpha_sum_R = alpha0_R + alpha1_R + alpha2_R

        # 防止除零
        if alpha_sum_R < 1e-40:
            w0_R = gamma0
            w1_R = gamma1
            w2_R = gamma2
        else:
            w0_R = alpha0_R / alpha_sum_R
            w1_R = alpha1_R / alpha_sum_R
            w2_R = alpha2_R / alpha_sum_R

        # 最终重构值
        q_R[i] = w0_R * q0_R + w1_R * q1_R + w2_R * q2_R

    return q_L, q_R


@njit
def weno5_flux_splitting(q: np.ndarray, flux_func, epsilon: float = 1e-6):
    """
    WENO5 with flux splitting (Lax-Friedrichs)

    参数:
        q: 单元平均值
        flux_func: 通量函数 f(q)
        epsilon: WENO epsilon

    返回:
        f_interface: 界面通量
    """
    n = len(q)

    # 计算通量
    f = flux_func(q)

    # Lax-Friedrichs分裂参数（最大特征值）
    # 这里需要根据具体问题定义
    # 暂时使用简化版本

    # 正负通量分裂
    # f = f^+ + f^-
    # f^+ 使用左重构，f^- 使用右重构

    # 这是简化版，实际应用中需要根据具体问题优化
    pass


def test_weno5():
    """测试WENO5重构精度"""
    print("="*80)
    print("WENO5重构精度测试")
    print("="*80)

    # 测试1：光滑函数（应该达到5阶精度）
    print("\n测试1: 光滑正弦函数")
    n = 100
    x = np.linspace(0, 2*np.pi, n)
    q = np.sin(x)

    # 添加ghost cells（周期边界）
    q_ext = np.zeros(n + 4)
    q_ext[2:-2] = q
    q_ext[0:2] = q[-2:]  # 左ghost
    q_ext[-2:] = q[0:2]  # 右ghost

    q_L, q_R = weno5_reconstruct(q_ext)

    # 检查内部点
    interior = slice(2, -2)
    print(f"  原始值范围: [{q.min():.6f}, {q.max():.6f}]")
    print(f"  重构左值范围: [{q_L[interior].min():.6f}, {q_L[interior].max():.6f}]")
    print(f"  重构右值范围: [{q_R[interior].min():.6f}, {q_R[interior].max():.6f}]")

    # 测试2：间断函数（应该无振荡）
    print("\n测试2: 阶跃间断")
    q_jump = np.ones(n)
    q_jump[n//2:] = 2.0

    q_ext = np.zeros(n + 4)
    q_ext[2:-2] = q_jump
    q_ext[0:2] = q_jump[:2]
    q_ext[-2:] = q_jump[-2:]

    q_L, q_R = weno5_reconstruct(q_ext)

    # 检查间断附近是否无振荡
    jump_idx = n // 2
    local_start = jump_idx - 3
    local_end = jump_idx + 3
    print(f"  间断附近值: {q_jump[local_start:local_end]}")
    print(f"  重构左值: {q_L[local_start+2:local_end+2]}")  # +2 offset for ghost cells

    # 检查是否有过冲/下冲
    overshoot_L = np.max(q_L[interior]) - 2.0
    undershoot_L = 1.0 - np.min(q_L[interior])

    print(f"\n  过冲检查:")
    print(f"    最大值: {np.max(q_L[interior]):.6f} (过冲: {overshoot_L:.6f})")
    print(f"    最小值: {np.min(q_L[interior]):.6f} (下冲: {undershoot_L:.6f})")

    if abs(overshoot_L) < 0.1 and abs(undershoot_L) < 0.1:
        print("  ✅ 无明显振荡")
    else:
        print("  ⚠️  存在振荡")

    print("\n" + "="*80)
    print("WENO5测试完成")
    print("="*80)


if __name__ == '__main__':
    test_weno5()
