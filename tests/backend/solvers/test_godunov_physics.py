import numpy as np
import pytest

from solvers.godunov_fvm_solver import GodunvFVMSolver


def test_supercritical_inlet_boundary_imposes_state():
    n_cells = 60
    h_bc = 0.2
    q_bc = 4.0
    solver = GodunvFVMSolver(
        width=2.0,
        length=300.0,
        n_cells=n_cells,
        manning_n=0.025,
        slope=0.0,
        g=9.81,
        cfl=0.4,
        order=1,
        use_numba=False,
    )
    solver.initialize(
        h_init=np.ones(n_cells) * 0.6,
        Q_init=np.ones(n_cells) * 1.0,
        bc_left={"type": "supercritical", "h": h_bc, "Q": q_bc},
        bc_right={"type": "wall"},
    )
    h_next, q_next = solver._apply_bc(solver.h.copy(), solver.Q.copy())
    froude = solver.compute_froude_number(h=h_next[:1], Q=q_next[:1])[0]

    assert h_next[0] == pytest.approx(h_bc)
    assert q_next[0] == pytest.approx(q_bc)
    assert froude > 1.0


def test_dry_bed_time_step_and_update_stay_bounded():
    n_cells = 40
    solver = GodunvFVMSolver(
        width=5.0,
        length=200.0,
        n_cells=n_cells,
        manning_n=0.025,
        slope=0.0,
        g=9.81,
        cfl=0.5,
        order=1,
        use_numba=False,
    )
    solver.initialize(
        h_init=np.zeros(n_cells),
        Q_init=np.zeros(n_cells),
        bc_left={"type": "wall"},
        bc_right={"type": "wall"},
    )

    dt = solver.compute_dt()
    solver.step(dt)

    assert dt == pytest.approx(1.0)
    assert np.all(np.isfinite(solver.h))
    assert np.all(np.isfinite(solver.Q))
    assert np.all(solver.h >= 0.0)
    assert np.allclose(solver.Q, 0.0)


def test_critical_boundary_relaxes_boundary_froude_toward_unity():
    n_cells = 60
    q_target = 6.0
    solver = GodunvFVMSolver(
        width=3.0,
        length=300.0,
        n_cells=n_cells,
        manning_n=0.0,
        slope=0.0,
        g=9.81,
        cfl=0.35,
        order=1,
        use_numba=False,
    )
    solver.initialize(
        h_init=np.ones(n_cells) * 0.4,
        Q_init=np.ones(n_cells) * q_target,
        bc_left={"type": "critical"},
        bc_right={"type": "Q", "value": q_target},
    )

    h_next, q_next = solver._apply_bc(solver.h.copy(), solver.Q.copy())
    h_critical, _ = solver.characteristic_bc.apply_critical_depth_bc(Q=q_target, B=solver.B)
    expected_h = solver.h[0] + 0.48 * (h_critical - solver.h[0])

    assert h_critical > solver.h[0]
    assert h_next[0] == pytest.approx(expected_h)
    assert q_next[0] == pytest.approx(q_target)


def test_critical_boundary_ghost_cell_uses_prescribed_discharge():
    n_cells = 20
    q_target = 12.0
    solver = GodunvFVMSolver(
        width=10.0,
        length=100.0,
        n_cells=n_cells,
        manning_n=0.0,
        slope=0.0,
        g=9.81,
        cfl=0.4,
        order=1,
        use_numba=False,
    )
    solver.initialize(
        h_init=np.ones(n_cells) * 2.0,
        Q_init=np.ones(n_cells) * 5.0,
        bc_left={"type": "critical"},
        bc_right={"type": "Q", "value": q_target},
    )

    h_ext, q_ext = solver._extend_with_ghosts(solver.h, solver.Q)
    h_critical, _ = solver.characteristic_bc.apply_critical_depth_bc(Q=q_target, B=solver.B)

    assert h_ext[0] == pytest.approx(h_critical)
    assert q_ext[0] == pytest.approx(solver.Q[0])
    assert h_ext[-1] == pytest.approx(solver.h[-1])
    assert q_ext[-1] == pytest.approx(q_target)


def test_strang_splitting_preserves_uniform_supercritical_flow():
    n_cells = 50
    h0 = 0.3
    q0 = 3.5
    solver = GodunvFVMSolver(
        width=2.0,
        length=250.0,
        n_cells=n_cells,
        manning_n=0.0,
        slope=0.0,
        g=9.81,
        cfl=0.3,
        order=1,
        use_numba=False,
        source_term_treatment="strang_splitting",
    )
    solver.initialize(
        h_init=np.ones(n_cells) * h0,
        Q_init=np.ones(n_cells) * q0,
        bc_left={"type": "supercritical", "h": h0, "Q": q0},
        bc_right={"type": "supercritical"},
    )

    h_initial = solver.h.copy()
    q_initial = solver.Q.copy()

    for _ in range(5):
        solver.step(0.02)

    assert np.max(np.abs(solver.h - h_initial)) < 5e-4
    assert np.max(np.abs(solver.Q - q_initial)) < 5e-4
    assert abs(solver.get_mass_conservation_error()) < 1e-3


def test_well_balanced_lake_at_rest_preserves_free_surface():
    n_cells = 80
    length = 800.0
    dx = length / n_cells
    x = (np.arange(n_cells) + 0.5) * dx
    z_b = 0.3 * np.sin(2.0 * np.pi * x / length)
    eta0 = 2.0
    h0 = eta0 - z_b

    solver = GodunvFVMSolver(
        width=5.0,
        length=length,
        n_cells=n_cells,
        manning_n=0.0,
        slope=None,
        z_b=z_b,
        g=9.81,
        cfl=0.4,
        order=1,
        well_balanced=True,
        use_numba=True,
    )
    solver.initialize(
        h_init=h0,
        Q_init=np.zeros(n_cells),
        bc_left={"type": "wall"},
        bc_right={"type": "wall"},
    )

    eta_initial = solver.h + solver.z_b
    solver.step(0.1)
    eta_final = solver.h + solver.z_b

    assert np.max(np.abs(solver.Q)) < 1e-8
    assert np.max(np.abs(eta_final - eta_initial)) < 1e-8


def test_well_balanced_wet_dry_lake_at_rest_stays_nonnegative():
    n_cells = 100
    length = 1000.0
    dx = length / n_cells
    x = (np.arange(n_cells) + 0.5) * dx
    z_b = 1.2 * np.exp(-((x - length / 2.0) / 120.0) ** 2)
    eta0 = 0.6
    h0 = np.maximum(eta0 - z_b, 0.0)

    solver = GodunvFVMSolver(
        width=4.0,
        length=length,
        n_cells=n_cells,
        manning_n=0.0,
        slope=None,
        z_b=z_b,
        g=9.81,
        cfl=0.35,
        order=1,
        well_balanced=True,
        use_numba=True,
        riemann_solver="hll",
    )
    solver.initialize(
        h_init=h0,
        Q_init=np.zeros(n_cells),
        bc_left={"type": "wall"},
        bc_right={"type": "wall"},
    )

    wet_mask0 = h0 > 1e-4
    for _ in range(3):
        solver.step(0.05)

    eta_final = solver.h + solver.z_b
    nearly_dry = solver.h < 1e-4

    assert np.all(np.isfinite(solver.h))
    assert np.all(np.isfinite(solver.Q))
    assert np.all(solver.h >= 0.0)
    assert np.max(np.abs(solver.Q[nearly_dry])) < 1e-4
    assert np.max(np.abs(eta_final[wet_mask0] - eta0)) < 2e-3


def test_q_boundary_flux_caps_unphysical_boundary_velocity():
    solver = GodunvFVMSolver(
        width=1.0,
        length=20.0,
        n_cells=4,
        manning_n=0.0,
        slope=0.0,
        g=9.81,
        order=1,
        use_numba=False,
    )
    h = np.array([0.15, 0.15, 0.15, 0.15])
    q = np.zeros(4)
    q_bc = 50.0
    solver.initialize(
        h_init=h,
        Q_init=q,
        bc_left={"type": "Q", "value": q_bc},
        bc_right={"type": "wall"},
    )

    f_h = np.zeros(5)
    f_q = np.zeros(5)
    solver._enforce_boundary_fluxes(f_h, f_q, h, q)

    c_bc = np.sqrt(solver.g * h[0])
    u_max = 10.0 * max(c_bc, 1.0)
    expected_fq = q_bc * u_max + 0.5 * solver.g * h[0] ** 2 * solver.B
    uncapped_fq = q_bc * (q_bc / (solver.B * h[0])) + 0.5 * solver.g * h[0] ** 2 * solver.B

    assert f_h[0] == pytest.approx(q_bc)
    assert f_q[0] == pytest.approx(expected_fq)
    assert f_q[0] < uncapped_fq


def test_right_stage_boundary_flux_uses_boundary_depth_not_interior_depth():
    solver = GodunvFVMSolver(
        width=2.0,
        length=40.0,
        n_cells=4,
        manning_n=0.0,
        slope=0.0,
        g=9.81,
        order=1,
        use_numba=False,
    )
    h = np.array([1.2, 1.2, 1.2, 1.2])
    q = np.array([0.0, 0.0, 0.0, 4.0])
    h_bc = 0.8
    solver.initialize(
        h_init=h,
        Q_init=q,
        bc_left={"type": "wall"},
        bc_right={"type": "h", "value": h_bc},
    )

    f_h = np.zeros(5)
    f_q = np.zeros(5)
    solver._enforce_boundary_fluxes(f_h, f_q, h, q)

    expected_velocity = q[-1] / (solver.B * h_bc)
    expected_fq = q[-1] * expected_velocity + 0.5 * solver.g * h_bc ** 2 * solver.B
    interior_fq = q[-1] * (q[-1] / (solver.B * h[-1])) + 0.5 * solver.g * h[-1] ** 2 * solver.B

    assert f_h[-1] == pytest.approx(q[-1])
    assert f_q[-1] == pytest.approx(expected_fq)
    assert f_q[-1] != pytest.approx(interior_fq)
