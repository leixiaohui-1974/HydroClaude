#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
多网格求解器

用于加速线性系统 A·x = b 的求解
支持V-cycle、全加权限制、线性插值延拓

作者: Claude
日期: 2025-10-22
"""

import numpy as np
from scipy.sparse import csr_matrix, diags, lil_matrix
from scipy.sparse.linalg import spsolve
from typing import List, Optional, Tuple


class MultiGridSolver:
    """
    多网格求解器（几何多网格）

    特点：
    - V-cycle迭代
    - 全加权限制算子
    - 线性插值延拓算子
    - Gauss-Seidel平滑器
    - 自动层次生成
    """

    def __init__(self,
                 n_levels: Optional[int] = None,
                 nu1: int = 2,
                 nu2: int = 2,
                 coarsest_size: int = 20,
                 verbose: bool = False):
        """
        Args:
            n_levels: 网格层数（None则自动确定）
            nu1: 前平滑次数
            nu2: 后平滑次数
            coarsest_size: 最粗层最小点数
            verbose: 是否输出调试信息
        """
        self.n_levels = n_levels
        self.nu1 = nu1
        self.nu2 = nu2
        self.coarsest_size = coarsest_size
        self.verbose = verbose

        # 网格层次数据（在setup时填充）
        self.grids = []  # 每层网格大小
        self.R_operators = []  # 限制算子列表
        self.P_operators = []  # 延拓算子列表
        self.A_hierarchy = []  # 各层系数矩阵

    def setup(self, A: csr_matrix, n_fine: int):
        """
        设置多网格层次

        Args:
            A: 细网格系数矩阵（稀疏）
            n_fine: 细网格点数
        """
        # 确定层数
        if self.n_levels is None:
            self.n_levels = self._determine_levels(n_fine)

        if self.verbose:
            print(f"[MultiGrid] 设置 {self.n_levels} 层网格")

        # 生成网格层次
        self.grids = [n_fine]
        n_current = n_fine
        for level in range(1, self.n_levels):
            n_coarse = (n_current + 1) // 2  # 向上取整
            if n_coarse < self.coarsest_size:
                # 调整层数
                self.n_levels = level
                if self.verbose:
                    print(f"[MultiGrid] 调整为 {self.n_levels} 层（最粗层 {n_current} 点）")
                break
            self.grids.append(n_coarse)
            n_current = n_coarse

        # 构建限制和延拓算子
        self.R_operators = []
        self.P_operators = []
        for level in range(self.n_levels - 1):
            n_f = self.grids[level]
            n_c = self.grids[level + 1]
            R = self._build_restriction(n_f, n_c)
            P = self._build_prolongation(n_f, n_c)
            self.R_operators.append(R)
            self.P_operators.append(P)

        # 构建各层系数矩阵（Galerkin粗化：A_c = R·A_f·P）
        self.A_hierarchy = [A]
        for level in range(self.n_levels - 1):
            A_fine = self.A_hierarchy[level]
            R = self.R_operators[level]
            P = self.P_operators[level]
            A_coarse = R @ A_fine @ P
            self.A_hierarchy.append(A_coarse.tocsr())

        if self.verbose:
            print(f"[MultiGrid] 网格层次: {self.grids}")

    def _determine_levels(self, n_fine: int) -> int:
        """自动确定层数"""
        levels = 1
        n = n_fine
        while n > self.coarsest_size:
            n = (n + 1) // 2
            levels += 1
            if levels > 10:  # 最多10层
                break
        return levels

    def _build_restriction(self, n_fine: int, n_coarse: int) -> csr_matrix:
        """
        构建限制算子（全加权限制）

        对于1D问题：
        r_c[i] = 0.25·r_f[2i-1] + 0.5·r_f[2i] + 0.25·r_f[2i+1]

        Args:
            n_fine: 细网格点数
            n_coarse: 粗网格点数

        Returns:
            R: 限制算子矩阵 (n_coarse × n_fine)
        """
        R = lil_matrix((n_coarse, n_fine))

        for i in range(n_coarse):
            j_center = 2 * i

            if j_center >= n_fine:
                # 边界情况
                R[i, -1] = 1.0
            elif j_center == 0:
                # 左边界
                R[i, 0] = 1.0
            elif j_center >= n_fine - 1:
                # 右边界
                R[i, -1] = 1.0
            else:
                # 内部节点：全加权
                R[i, j_center - 1] = 0.25
                R[i, j_center] = 0.5
                R[i, j_center + 1] = 0.25

        return R.tocsr()

    def _build_prolongation(self, n_fine: int, n_coarse: int) -> csr_matrix:
        """
        构建延拓算子（线性插值）

        对于1D问题：
        e_f[2i] = e_c[i]
        e_f[2i+1] = 0.5·(e_c[i] + e_c[i+1])

        Args:
            n_fine: 细网格点数
            n_coarse: 粗网格点数

        Returns:
            P: 延拓算子矩阵 (n_fine × n_coarse)
        """
        P = lil_matrix((n_fine, n_coarse))

        for i in range(n_coarse):
            j_center = 2 * i

            if j_center < n_fine:
                # 粗网格点对应的细网格点
                P[j_center, i] = 1.0

            # 插值点
            j_interp = 2 * i + 1
            if j_interp < n_fine and i < n_coarse - 1:
                P[j_interp, i] = 0.5
                P[j_interp, i + 1] = 0.5
            elif j_interp < n_fine:
                # 右边界
                P[j_interp, i] = 1.0

        return P.tocsr()

    def _smooth(self, A: csr_matrix, b: np.ndarray, x: np.ndarray,
                nu: int) -> np.ndarray:
        """
        Gauss-Seidel平滑（红黑排序）

        Args:
            A: 系数矩阵
            b: 右端项
            x: 当前解
            nu: 平滑次数

        Returns:
            平滑后的解
        """
        n = len(x)
        x = x.copy()

        for _ in range(nu):
            # Red sweep（偶数索引）
            for i in range(0, n, 2):
                row_start = A.indptr[i]
                row_end = A.indptr[i + 1]
                indices = A.indices[row_start:row_end]
                data = A.data[row_start:row_end]

                # 找到对角元素
                diag_idx = np.where(indices == i)[0]
                if len(diag_idx) == 0:
                    continue

                a_ii = data[diag_idx[0]]
                if abs(a_ii) < 1e-14:
                    continue

                # 计算残差
                residual = b[i] - (data @ x[indices])

                # 更新
                x[i] += residual / a_ii

            # Black sweep（奇数索引）
            for i in range(1, n, 2):
                row_start = A.indptr[i]
                row_end = A.indptr[i + 1]
                indices = A.indices[row_start:row_end]
                data = A.data[row_start:row_end]

                diag_idx = np.where(indices == i)[0]
                if len(diag_idx) == 0:
                    continue

                a_ii = data[diag_idx[0]]
                if abs(a_ii) < 1e-14:
                    continue

                residual = b[i] - (data @ x[indices])
                x[i] += residual / a_ii

        return x

    def _v_cycle(self, level: int, b: np.ndarray, x: np.ndarray) -> np.ndarray:
        """
        V-cycle递归

        Args:
            level: 当前层级（0为最细）
            b: 右端项
            x: 当前解

        Returns:
            校正后的解
        """
        A = self.A_hierarchy[level]

        # 最粗层：直接求解
        if level == self.n_levels - 1:
            try:
                x = spsolve(A, b)
            except:
                # 如果直接求解失败，使用多次平滑
                x = self._smooth(A, b, x, nu=50)
            return x

        # 前平滑
        x = self._smooth(A, b, x, self.nu1)

        # 计算残差
        r = b - A @ x

        # 限制到粗网格
        R = self.R_operators[level]
        r_c = R @ r

        # 粗网格求解（递归）
        e_c = np.zeros(self.grids[level + 1])
        e_c = self._v_cycle(level + 1, r_c, e_c)

        # 延拓校正
        P = self.P_operators[level]
        e = P @ e_c

        # 更新解
        x = x + e

        # 后平滑
        x = self._smooth(A, b, x, self.nu2)

        return x

    def solve(self,
              A: csr_matrix,
              b: np.ndarray,
              x_init: Optional[np.ndarray] = None,
              n_cycles: int = 1,
              tol: float = 1e-10,
              max_cycles: int = 50) -> Tuple[np.ndarray, dict]:
        """
        多网格求解 A·x = b

        Args:
            A: 系数矩阵（稀疏）
            b: 右端项
            x_init: 初始解（None则用零向量）
            n_cycles: V-cycle次数（固定）
            tol: 收敛容差（相对残差）
            max_cycles: 最大V-cycle次数（自适应模式）

        Returns:
            x: 解向量
            info: 求解信息字典
        """
        n = len(b)

        # 设置多网格层次
        self.setup(A, n)

        # 初始解
        if x_init is None:
            x = np.zeros(n)
        else:
            x = x_init.copy()

        # 初始残差
        r0_norm = np.linalg.norm(b - A @ x)
        if r0_norm < 1e-14:
            return x, {'converged': True, 'cycles': 0, 'residual': 0.0}

        # V-cycle迭代
        residual_history = [r0_norm]

        for cycle in range(max_cycles):
            x = self._v_cycle(0, b, x)

            # 计算残差
            r = b - A @ x
            r_norm = np.linalg.norm(r)
            residual_history.append(r_norm)

            # 检查收敛
            rel_residual = r_norm / r0_norm

            if self.verbose and cycle % 5 == 0:
                print(f"  [MG] Cycle {cycle+1}: res={r_norm:.3e}, rel={rel_residual:.3e}")

            if rel_residual < tol or cycle + 1 >= n_cycles:
                converged = rel_residual < tol
                if self.verbose:
                    status = "收敛" if converged else "达到最大循环数"
                    print(f"  [MG] {status}: {cycle+1} cycles, rel_res={rel_residual:.3e}")

                return x, {
                    'converged': converged,
                    'cycles': cycle + 1,
                    'residual': r_norm,
                    'relative_residual': rel_residual,
                    'residual_history': residual_history
                }

        # 超出最大循环数
        return x, {
            'converged': False,
            'cycles': max_cycles,
            'residual': r_norm,
            'relative_residual': rel_residual,
            'residual_history': residual_history
        }


def test_multigrid():
    """测试多网格求解器"""
    print("=" * 80)
    print("多网格求解器测试")
    print("=" * 80)

    # 测试问题：1D Poisson方程 -u''(x) = f(x), x∈[0,1], u(0)=u(1)=0
    # 解析解：u(x) = x(1-x)/2

    n = 401  # 网格点数
    dx = 1.0 / (n - 1)

    # 构建系数矩阵（三对角）
    main_diag = 2.0 / dx**2 * np.ones(n)
    off_diag = -1.0 / dx**2 * np.ones(n - 1)

    # 边界条件（Dirichlet）
    main_diag[0] = main_diag[-1] = 1.0
    off_diag[0] = off_diag[-1] = 0.0

    A = diags([off_diag, main_diag, off_diag], [-1, 0, 1], format='csr')

    # 右端项 f(x) = 1
    b = np.ones(n)
    b[0] = b[-1] = 0.0  # 边界条件

    # 解析解
    x_grid = np.linspace(0, 1, n)
    u_exact = x_grid * (1 - x_grid) / 2

    print(f"\n问题规模: {n} × {n}")
    print(f"稀疏度: {A.nnz / n**2 * 100:.2f}%")

    # 测试多网格求解器
    print("\n多网格求解器:")
    mg_solver = MultiGridSolver(nu1=2, nu2=2, verbose=True)

    import time
    start_time = time.time()
    u_mg, info_mg = mg_solver.solve(A, b, n_cycles=10, tol=1e-8)
    mg_time = time.time() - start_time

    error_mg = np.linalg.norm(u_mg - u_exact) / np.linalg.norm(u_exact)

    print(f"\n结果:")
    print(f"  V-cycles: {info_mg['cycles']}")
    print(f"  收敛: {info_mg['converged']}")
    print(f"  最终残差: {info_mg['residual']:.3e}")
    print(f"  相对残差: {info_mg['relative_residual']:.3e}")
    print(f"  相对误差: {error_mg:.3e}")
    print(f"  计算时间: {mg_time:.4f}s")

    # 对比直接求解
    print("\n直接求解（scipy.sparse.linalg.spsolve）:")
    start_time = time.time()
    u_direct = spsolve(A, b)
    direct_time = time.time() - start_time

    error_direct = np.linalg.norm(u_direct - u_exact) / np.linalg.norm(u_exact)

    print(f"  相对误差: {error_direct:.3e}")
    print(f"  计算时间: {direct_time:.4f}s")

    print(f"\n加速比: {direct_time / mg_time:.2f}x")
    print("=" * 80)


if __name__ == "__main__":
    test_multigrid()
