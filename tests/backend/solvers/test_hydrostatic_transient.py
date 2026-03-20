import numpy as np
import pytest

from solvers.gate import SluiceGate
from solvers.gate import PumpStation
from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver
from utils.canal_utils import compute_steady_uniform_flow


def test_solve_transient_adaptive_respects_dt_bounds_and_records_history():
    q_target = 8.0
    solver = HydrostaticCanalSolver(
        length=300.0,
        nx=31,
        B=6.0,
        S0=0.001,
        n=0.025,
    )
    h_normal = compute_steady_uniform_flow(q_target, solver.B, solver.S0_scalar, solver.n)
    solver.h[:] = h_normal
    solver.set_Q(q_target)

    result = solver.solve_transient_adaptive(
        t_end=0.55,
        dt_initial=0.25,
        dt_min=0.02,
        dt_max=0.08,
        CFL_number=0.5,
        Q_upstream_func=lambda t: q_target + 0.6 * np.sin(6.0 * t),
        h_downstream_func=lambda t: h_normal + 0.02 * np.cos(4.0 * t),
        save_interval_time=0.1,
        verbose=False,
    )

    dt_history = result["dt_history"][1:]

    assert len(result["t_history"]) == len(result["h_history"]) == len(result["Q_history"])
    assert len(dt_history) >= 2
    assert np.all(np.diff(result["t_history"]) > 0.0)
    assert np.all(dt_history >= 0.02 - 1e-12)
    assert np.all(dt_history <= 0.08 + 1e-12)
    assert np.std(result["dt_history"]) > 0.0
    assert np.all(np.isfinite(result["h_history"]))
    assert np.all(result["h_history"] >= solver.eps_dry)


def test_solve_transient_fixed_step_records_expected_history_points():
    q_target = 6.0
    solver = HydrostaticCanalSolver(
        length=240.0,
        nx=25,
        B=5.0,
        S0=0.001,
        n=0.025,
    )
    h_normal = compute_steady_uniform_flow(q_target, solver.B, solver.S0_scalar, solver.n)
    solver.h[:] = h_normal
    solver.set_Q(q_target)

    result = solver.solve_transient(
        t_end=0.5,
        dt=0.1,
        Q_upstream=q_target,
        h_downstream=h_normal,
        save_interval=2,
        verbose=False,
    )

    assert list(result["t_history"]) == pytest.approx([0.0, 0.2, 0.4])
    assert len(result["t_history"]) == len(result["h_history"]) == len(result["Q_history"]) == 3
    assert np.all(np.diff(result["t_history"]) > 0.0)
    assert solver.current_time == pytest.approx(0.5)
    assert np.all(np.isfinite(result["h_final"]))
    assert np.all(result["h_final"] >= solver.eps_dry)


def test_solve_transient_fixed_step_step_inflow_raises_mean_discharge():
    q_base = 5.0
    q_step = 8.0
    solver = HydrostaticCanalSolver(
        length=300.0,
        nx=31,
        B=6.0,
        S0=0.001,
        n=0.025,
    )
    h_normal = compute_steady_uniform_flow(q_base, solver.B, solver.S0_scalar, solver.n)
    solver.h[:] = h_normal
    solver.set_Q(q_base)

    result = solver.solve_transient(
        t_end=0.6,
        dt=0.1,
        Q_upstream_func=lambda t: q_base if t < 0.3 else q_step,
        h_downstream_func=lambda t: h_normal,
        save_interval=1,
        verbose=False,
    )

    q_means = np.mean(result["Q_history"], axis=1)

    assert q_means[-1] > q_means[0]
    assert np.max(result["Q_final"]) > q_base
    assert np.all(np.isfinite(result["Q_history"]))
    assert np.all(np.isfinite(result["h_history"]))
    assert np.all(result["h_history"] >= solver.eps_dry)


def test_step_keeps_dry_cells_nonnegative_and_zero_momentum():
    solver = HydrostaticCanalSolver(
        length=100.0,
        nx=11,
        B=4.0,
        S0=0.001,
        n=0.025,
    )
    solver.h[:] = np.array([0.8, 0.8, 0.7, 0.5, 0.2, solver.eps_dry, solver.eps_dry, solver.eps_dry, 0.15, 0.3, 0.5])
    solver.hu[:] = np.array([0.4, 0.4, 0.3, 0.2, 0.05, 0.1, -0.1, 0.05, 0.02, 0.1, 0.2])

    dt = 0.05
    solver.step(dt)

    dry_mask = solver.h <= solver.eps_dry

    assert np.all(np.isfinite(solver.h))
    assert np.all(np.isfinite(solver.hu))
    assert np.all(solver.h >= solver.eps_dry)
    assert np.allclose(solver.hu[dry_mask], 0.0)
    assert solver.current_time == pytest.approx(dt)


def test_pump_station_mask_and_head_jump_match_energy_gain():
    pump = PumpStation(
        position=100.0,
        width=5.0,
        rated_flow=12.0,
        rated_head=1.5,
        min_suction_head=0.5,
    )
    solver = HydrostaticCanalSolver(
        length=200.0,
        nx=21,
        B=5.0,
        S0=0.001,
        n=0.025,
        internal_structures=[(pump.position, pump)],
    )
    solver.h[:] = 2.0
    solver.set_Q(12.0)

    mask = solver._get_pump_region_mask()
    idx = solver.structure_indices[0]
    z_up = solver.z[idx - 1]
    z_down = solver.z[idx + 1]
    h_up = solver.h[idx - 1]

    solver._apply_pump_internal_bc(conserve_local_flow=True)

    expected_h_down = max(h_up + (z_up - z_down) + pump.rated_head, solver.eps_dry)

    assert mask.sum() == 3
    assert mask[idx - 1] and mask[idx] and mask[idx + 1]
    assert solver.h[idx + 1] == pytest.approx(expected_h_down)
    assert solver.h[idx] == pytest.approx((h_up + expected_h_down) / 2.0)
    assert solver.hu[idx + 1] == pytest.approx(solver.hu[idx - 1])


def test_internal_gate_bc_reduces_discharge_residual():
    gate = SluiceGate(position=100.0, width=5.0, opening=0.4, Cd=0.6)
    solver = HydrostaticCanalSolver(
        length=200.0,
        nx=21,
        B=5.0,
        S0=0.001,
        n=0.025,
        internal_structures=[(gate.position, gate)],
    )
    idx = solver.structure_indices[0]
    solver.h[:] = 1.0
    solver.h[idx - 1] = 1.1
    solver.h[idx + 1] = 0.8

    q_before, _ = gate.calculate_discharge(solver.h[idx - 1], solver.h[idx + 1], 0.0)
    q_target = q_before + 0.8

    solver._apply_internal_bc(t=0.0, Q_target=q_target, max_iter=5, tol=0.001, relax=0.6)

    q_after, _ = gate.calculate_discharge(solver.h[idx - 1], solver.h[idx + 1], 0.0)

    assert abs(q_target - q_after) < abs(q_target - q_before)
    assert solver.h[idx - 1] > 1.1
    assert np.all(np.isfinite(solver.h))
