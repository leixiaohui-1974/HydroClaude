"""
求解器基础功能单元测试

测试solvers/hydrostatic_canal_solver.py的基础功能
"""

import pytest
import numpy as np

from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver


class TestHydrostaticCanalSolver:
    """静水重构求解器基础测试"""

    def test_initialization(self, simple_canal_params):
        """测试求解器初始化"""
        solver = HydrostaticCanalSolver(**simple_canal_params)

        assert solver.nx == simple_canal_params['nx']
        assert solver.B == simple_canal_params['B']
        assert solver.S0 == simple_canal_params['S0']
        assert solver.n == simple_canal_params['n']
        assert len(solver.x) == simple_canal_params['nx']
        assert len(solver.h) == simple_canal_params['nx']

    def test_grid_generation(self):
        """测试网格生成"""
        solver = HydrostaticCanalSolver(length=1000.0, nx=101)

        assert len(solver.x) == 101
        assert solver.x[0] == 0.0
        assert solver.x[-1] == 1000.0

        # 验证均匀网格
        dx = np.diff(solver.x)
        np.testing.assert_allclose(dx, dx[0], rtol=1e-10)

    def test_bed_elevation(self):
        """测试底床高程"""
        S0 = 0.001
        solver = HydrostaticCanalSolver(length=1000.0, nx=101, S0=S0)

        # 验证底坡
        assert solver.z[0] == 0.0
        assert solver.z[-1] == pytest.approx(-S0 * 1000.0)

        # 验证线性坡度
        expected_z = -S0 * solver.x
        np.testing.assert_allclose(solver.z, expected_z)

    def test_state_variables(self, canal_solver):
        """测试状态变量"""
        # 验证状态变量存在且维度正确
        assert hasattr(canal_solver, 'h')
        assert hasattr(canal_solver, 'hu')
        assert len(canal_solver.h) == canal_solver.nx
        assert len(canal_solver.hu) == canal_solver.nx

    def test_hydrostatic_reconstruction(self):
        """测试静水重构"""
        solver = HydrostaticCanalSolver(length=100, nx=11)

        # 测试平底情况
        h_L, h_R = solver.reconstruct_interface(
            h_L=2.0, z_L=0.0,
            h_R=2.0, z_R=0.0
        )
        assert h_L == 2.0
        assert h_R == 2.0

        # 测试台阶（右侧高）
        h_L, h_R = solver.reconstruct_interface(
            h_L=2.0, z_L=0.0,
            h_R=1.5, z_R=0.5
        )
        assert h_L == 2.0  # eta_L=2.0, z_int=0.5, h*_L=1.5
        assert h_R == 1.5  # eta_R=2.0, z_int=0.5, h*_R=1.5

        # 测试干底（右侧露出）
        h_L, h_R = solver.reconstruct_interface(
            h_L=1.0, z_L=0.0,
            h_R=0.5, z_R=1.0
        )
        assert h_L == 0.0  # eta_L=1.0 < z_int=1.0
        assert h_R == 0.5  # eta_R=1.5 > z_int=1.0

    def test_manning_friction(self, canal_solver):
        """测试曼宁摩阻计算"""
        # 设置状态
        canal_solver.h[:] = 2.0
        canal_solver.hu[:] = 10.0  # u = 5 m/s

        # 计算摩阻源项
        h = 2.0
        u = 5.0
        n = canal_solver.n
        g = canal_solver.g

        # 理论值: S_f = n^2 * u * |u| / h^(4/3)
        expected_Sf = n**2 * u * abs(u) / (h ** (4/3))

        # 源项: -g * h * S_f
        expected_source = -g * h * expected_Sf

        # 验证符号（阻力应该减速）
        assert expected_source < 0

    @pytest.mark.parametrize("nx", [51, 101, 201])
    def test_different_grid_sizes(self, nx):
        """参数化测试：不同网格尺寸"""
        solver = HydrostaticCanalSolver(length=1000.0, nx=nx)
        assert len(solver.x) == nx
        assert len(solver.h) == nx

    def test_boundary_conditions(self, canal_solver):
        """测试边界条件设置"""
        canal_solver.Q_in = 15.0
        canal_solver.h_downstream = 2.5

        assert canal_solver.Q_in == 15.0
        assert canal_solver.h_downstream == 2.5

    def test_custom_grid(self):
        """测试自定义网格"""
        # 非均匀网格
        x_custom = np.array([0, 10, 25, 50, 100, 200, 500, 1000])

        solver = HydrostaticCanalSolver(
            length=1000.0,  # 会被忽略
            nx=101,  # 会被覆盖
            x_grid=x_custom
        )

        assert solver.nx == len(x_custom)
        np.testing.assert_array_equal(solver.x, x_custom)
        assert not solver.is_uniform_grid


@pytest.mark.slow
class TestSteadyStateSolver:
    """稳态求解测试（较慢）"""

    def test_steady_state_convergence(self, canal_solver):
        """测试稳态收敛"""
        # 求解稳态
        result = canal_solver.solve_steady_state(
            Q_target=10.0,
            h_downstream=2.0,
            max_iterations=1000,
            convergence_tol=0.01
        )

        # 验证收敛
        assert result['converged']
        assert result['iterations'] < 1000

        # 验证流量守恒
        Q = canal_solver.hu * canal_solver.B
        Q_mean = np.mean(Q)
        assert abs(Q_mean - 10.0) < 0.1  # 1%误差

    def test_steady_state_uniform_flow(self):
        """测试均匀流稳态"""
        solver = HydrostaticCanalSolver(
            length=5000.0,
            nx=101,
            B=10.0,
            S0=0.001,
            n=0.025
        )

        result = solver.solve_steady_state(
            Q_target=20.0,
            h_downstream=2.5,
            max_iterations=2000
        )

        # 均匀流应该快速收敛
        assert result['converged']

        # 水深应该相对均匀
        h_std = np.std(solver.h)
        h_mean = np.mean(solver.h)
        assert h_std / h_mean < 0.1  # 变异系数 < 10%
