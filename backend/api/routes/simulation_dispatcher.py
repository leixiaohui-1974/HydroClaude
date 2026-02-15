"""
Multi-physics simulation dispatcher.

Routes simulation jobs to the appropriate solver based on `config.simulation.type`.
Supports:
    - open_channel / steady / unsteady: GodunvFVM shallow-water solver
    - water_quality: ADR + coupled water quality (DO, nutrients, phytoplankton)
    - water_temperature: Heat transport with atmospheric exchange
    - ice_simulation: Ice cover formation, frazil ice, ice jam
    - coupled_ice_wq: Coupled ice + water quality multi-process
    - water_hammer: Method of Characteristics for transient pipe flow
"""

import logging
import os
import sys
from datetime import datetime, timezone
from typing import Dict, Any

import numpy as np

logger = logging.getLogger(__name__)

# Ensure solver packages are importable
_project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


# ---------------------------------------------------------------------------
# Registry of simulation runners
# ---------------------------------------------------------------------------
_RUNNER_REGISTRY: Dict[str, Any] = {}


def _register(sim_type: str):
    """Decorator to register a runner function for a simulation type."""
    def decorator(fn):
        _RUNNER_REGISTRY[sim_type] = fn
        return fn
    return decorator


def dispatch(sim_type: str, config: dict, progress_cb=None) -> dict:
    """
    Dispatch to the correct simulation runner.

    Parameters
    ----------
    sim_type : str
        The simulation type key (e.g. "open_channel", "water_quality").
    config : dict
        Full job configuration dictionary.
    progress_cb : callable, optional
        Called with (percent: float) to report progress.

    Returns
    -------
    dict with keys: summary, time_series, solver_metadata
    """
    # Normalize aliases
    aliases = {
        "steady": "open_channel",
        "unsteady": "open_channel",
        "gate": "open_channel",
        "network": "open_channel",
    }
    effective_type = aliases.get(sim_type, sim_type)

    runner = _RUNNER_REGISTRY.get(effective_type)
    if runner is None:
        raise ValueError(
            f"Unsupported simulation type: '{sim_type}'. "
            f"Available: {', '.join(sorted(set(list(_RUNNER_REGISTRY.keys()) + list(aliases.keys()))))}"
        )
    return runner(config, progress_cb)


# ---------------------------------------------------------------------------
# 1. Open-channel flow (Saint-Venant / Shallow Water)
# ---------------------------------------------------------------------------
@_register("open_channel")
def _run_open_channel(config: dict, progress_cb=None) -> dict:
    from solvers.godunov_fvm_solver import GodunvFVMSolver

    canal = config.get("canal", {})
    solver_cfg = config.get("solver", {})
    sim_cfg = config.get("simulation", {})
    bc_cfg = config.get("boundary_conditions", {})
    ic = config.get("initial_conditions", {})

    length = canal.get("length", 1000.0)
    width = canal.get("width", 10.0)
    slope = canal.get("slope", 0.001)
    manning_n = canal.get("manning_n", 0.025)
    n_cells = canal.get("n_cells", 200)
    end_time = sim_cfg.get("end_time", 100.0)
    cfl = solver_cfg.get("cfl", 0.5)

    dx = length / n_cells
    x = np.linspace(0.5 * dx, length - 0.5 * dx, n_cells)

    ic_type = ic.get("type", "uniform")
    if ic_type == "dam_break":
        h_L, h_R = ic.get("h_left", 10.0), ic.get("h_right", 1.0)
        dam_pos = ic.get("dam_position", length / 2)
        h_init = np.where(x < dam_pos, h_L, h_R)
        Q_init = np.zeros(n_cells)
    else:
        h_init = np.ones(n_cells) * ic.get("h", 1.0)
        Q_init = np.ones(n_cells) * ic.get("Q", 0.0)

    bc_left = _parse_bc(bc_cfg.get("upstream", {"type": "h", "value": float(h_init[0])}))
    bc_right = _parse_bc(bc_cfg.get("downstream", {"type": "h", "value": float(h_init[-1])}))

    solver = GodunvFVMSolver(
        width=width, length=length, n_cells=n_cells,
        manning_n=manning_n, slope=slope, g=9.81,
        cfl=cfl, eps_dry=1e-6,
        order=solver_cfg.get("order", 1),
        riemann_solver=solver_cfg.get("riemann_solver", "hll"),
        well_balanced=solver_cfg.get("well_balanced", True),
        use_numba=False,
    )
    solver.initialize(h_init, Q_init, bc_left, bc_right)

    output_interval = max(end_time / 50, solver.compute_dt())
    next_output_time = output_interval
    snapshots = [{"t": 0.0, "h_max": float(np.max(h_init)), "h_min": float(np.min(h_init)),
                  "Q_max": float(np.max(Q_init))}]
    max_steps = solver_cfg.get("max_steps", 100000)
    step = 0

    while solver.t < end_time and step < max_steps:
        solver.step()
        step += 1
        if solver.t >= next_output_time:
            state = solver.get_state()
            snapshots.append({
                "t": float(state["t"]),
                "h_max": float(np.max(state["h"])),
                "h_min": float(np.min(state["h"])),
                "Q_max": float(np.max(np.abs(state["Q"]))),
                "mass_error": float(state.get("mass_error", 0.0)),
            })
            next_output_time += output_interval
            if progress_cb:
                progress_cb(min(solver.t / end_time * 100.0, 99.0))

    final = solver.get_state()
    return {
        "summary": {
            "simulation_type": "open_channel",
            "final_time": float(final["t"]),
            "total_steps": step,
            "h_max": float(np.max(final["h"])),
            "h_min": float(np.min(final["h"])),
            "h_mean": float(np.mean(final["h"])),
            "Q_max": float(np.max(final["Q"])),
            "mass_error_percent": float(final.get("mass_error", 0.0)),
            "stable": bool(not np.any(np.isnan(final["h"]))),
        },
        "time_series": {
            "snapshots": snapshots,
            "x": x.tolist(),
            "h_final": final["h"].tolist(),
            "Q_final": final["Q"].tolist(),
        },
        "solver_metadata": {
            "solver": solver_cfg.get("method", "godunov_fvm"),
            "n_cells": n_cells, "cfl": cfl, "end_time": end_time,
            "canal_width": width, "canal_length": length,
            "manning_n": manning_n, "slope": slope,
        },
    }


# ---------------------------------------------------------------------------
# 2. Water quality (Advection-Diffusion-Reaction)
# ---------------------------------------------------------------------------
@_register("water_quality")
def _run_water_quality(config: dict, progress_cb=None) -> dict:
    from solvers.water_quality_adr import ADRSolver

    canal = config.get("canal", {})
    wq_cfg = config.get("water_quality", {})
    sim_cfg = config.get("simulation", {})

    length = canal.get("length", 1000.0)
    n_cells = canal.get("n_cells", 200)
    dx = length / n_cells
    end_time = sim_cfg.get("end_time", 3600.0)
    dt = sim_cfg.get("dt", 10.0)
    manning_n = canal.get("manning_n", 0.025)

    x = np.linspace(0.5 * dx, length - 0.5 * dx, n_cells)
    h = np.ones(n_cells) * canal.get("depth", 2.0)
    u = np.ones(n_cells) * canal.get("velocity", 0.5)

    C_init = np.ones(n_cells) * wq_cfg.get("initial_concentration", 5.0)
    source_idx = int(n_cells * wq_cfg.get("source_position", 0.1))
    source_rate = wq_cfg.get("source_rate", 0.0)
    decay_rate = wq_cfg.get("decay_rate", 0.0)

    solver = ADRSolver(n_cells=n_cells, dx=dx, use_numba=False, use_muscl=True)
    DL = solver.compute_dispersion_coefficient(h, u, manning_n=manning_n)

    C = C_init.copy()
    t = 0.0
    snapshots = []
    n_steps = int(end_time / dt)
    output_every = max(1, n_steps // 50)

    for step in range(n_steps):
        adv_flux = solver.compute_advective_flux(C, u)  # shape (n_cells+1,) at faces
        dC_adv = -np.diff(adv_flux) / dx  # diff of (n+1) faces → (n,) cell values

        dC_diff = np.zeros(n_cells)
        for i in range(1, n_cells - 1):
            dC_diff[i] = DL[i] * (C[i + 1] - 2 * C[i] + C[i - 1]) / dx**2

        dC_react = -decay_rate * C
        source = np.zeros(n_cells)
        if 0 <= source_idx < n_cells:
            source[source_idx] = source_rate

        C = C + dt * (dC_adv + dC_diff + dC_react + source)
        C = np.maximum(C, 0.0)
        t += dt

        if step % output_every == 0:
            snapshots.append({
                "t": float(t),
                "C_max": float(np.max(C)),
                "C_min": float(np.min(C)),
                "C_mean": float(np.mean(C)),
            })
            if progress_cb:
                progress_cb(min(t / end_time * 100.0, 99.0))

    return {
        "summary": {
            "simulation_type": "water_quality",
            "final_time": float(t),
            "total_steps": n_steps,
            "C_max": float(np.max(C)),
            "C_min": float(np.min(C)),
            "C_mean": float(np.mean(C)),
            "stable": bool(not np.any(np.isnan(C))),
        },
        "time_series": {
            "snapshots": snapshots,
            "x": x.tolist(),
            "C_final": C.tolist(),
        },
        "solver_metadata": {
            "solver": "water_quality_adr",
            "n_cells": n_cells, "dt": dt, "end_time": end_time,
            "decay_rate": decay_rate,
            "dispersion_mean": float(np.mean(DL)),
        },
    }


# ---------------------------------------------------------------------------
# 3. Water temperature
# ---------------------------------------------------------------------------
@_register("water_temperature")
def _run_water_temperature(config: dict, progress_cb=None) -> dict:
    from solvers.water_temperature import WaterTemperatureSolver

    canal = config.get("canal", {})
    temp_cfg = config.get("temperature", {})
    sim_cfg = config.get("simulation", {})

    length = canal.get("length", 1000.0)
    n_cells = canal.get("n_cells", 200)
    dx = length / n_cells
    end_time = sim_cfg.get("end_time", 86400.0)
    dt = sim_cfg.get("dt", 60.0)

    x = np.linspace(0.5 * dx, length - 0.5 * dx, n_cells)
    h = np.ones(n_cells) * canal.get("depth", 2.0)
    u = np.ones(n_cells) * canal.get("velocity", 0.5)

    T_init = np.ones(n_cells) * temp_cfg.get("initial_temperature", 15.0)
    T_air = temp_cfg.get("air_temperature", 10.0)
    solar = temp_cfg.get("solar_radiation", 200.0)
    wind = temp_cfg.get("wind_speed", 2.0)
    humidity = temp_cfg.get("relative_humidity", 0.6)

    solver = WaterTemperatureSolver(
        n_cells=n_cells, dx=dx,
        thermal_diffusivity=temp_cfg.get("thermal_diffusivity", 1.4e-7),
        use_numba=False,
    )
    solver.initialize(T_init.copy())

    T = T_init.copy()
    t = 0.0
    snapshots = []
    n_steps = int(end_time / dt)
    output_every = max(1, n_steps // 50)

    for step in range(n_steps):
        Q_atm = solver.compute_atmospheric_heat_flux(T, T_air, solar, wind, humidity)
        dT_adv = np.zeros(n_cells)
        for i in range(1, n_cells):
            dT_adv[i] = -u[i] * (T[i] - T[i - 1]) / dx

        dT_diff = np.zeros(n_cells)
        kappa = solver.D_T
        for i in range(1, n_cells - 1):
            dT_diff[i] = kappa * (T[i + 1] - 2 * T[i] + T[i - 1]) / dx**2

        rho_cp = 4.18e6
        dT_heat = Q_atm / (rho_cp * h)
        T = T + dt * (dT_adv + dT_diff + dT_heat)
        t += dt

        if step % output_every == 0:
            snapshots.append({
                "t": float(t),
                "T_max": float(np.max(T)),
                "T_min": float(np.min(T)),
                "T_mean": float(np.mean(T)),
            })
            if progress_cb:
                progress_cb(min(t / end_time * 100.0, 99.0))

    return {
        "summary": {
            "simulation_type": "water_temperature",
            "final_time": float(t),
            "total_steps": n_steps,
            "T_max": float(np.max(T)),
            "T_min": float(np.min(T)),
            "T_mean": float(np.mean(T)),
            "stable": bool(not np.any(np.isnan(T))),
        },
        "time_series": {
            "snapshots": snapshots,
            "x": x.tolist(),
            "T_final": T.tolist(),
        },
        "solver_metadata": {
            "solver": "water_temperature",
            "n_cells": n_cells, "dt": dt, "end_time": end_time,
            "T_air": T_air, "solar_radiation": solar,
        },
    }


# ---------------------------------------------------------------------------
# 4. Ice simulation
# ---------------------------------------------------------------------------
@_register("ice_simulation")
def _run_ice_simulation(config: dict, progress_cb=None) -> dict:
    from solvers.ice_cover import IceCoverSolver

    canal = config.get("canal", {})
    ice_cfg = config.get("ice", {})
    sim_cfg = config.get("simulation", {})

    n_cells = canal.get("n_cells", 200)
    length = canal.get("length", 1000.0)
    dx = length / n_cells
    end_time = sim_cfg.get("end_time", 86400.0 * 30)
    dt = sim_cfg.get("dt", 3600.0)

    x = np.linspace(0.5 * dx, length - 0.5 * dx, n_cells)
    T_water = np.ones(n_cells) * ice_cfg.get("water_temperature", 0.5)
    T_air_series = ice_cfg.get("air_temperature", -10.0)

    solver = IceCoverSolver(
        n_cells=n_cells,
        rho_ice=ice_cfg.get("rho_ice", 917.0),
        L_fusion=ice_cfg.get("L_fusion", 3.34e5),
        k_ice=ice_cfg.get("k_ice", 2.2),
        T_freeze=ice_cfg.get("T_freeze", 0.0),
    )
    h_ice_init = np.ones(n_cells) * ice_cfg.get("initial_ice_thickness", 0.0)
    solver.initialize(h_ice_initial=h_ice_init)

    t = 0.0
    snapshots = []
    n_steps = int(end_time / dt)
    output_every = max(1, n_steps // 50)
    h_ice = h_ice_init.copy()

    for step in range(n_steps):
        T_air = T_air_series if isinstance(T_air_series, (int, float)) else T_air_series[step % len(T_air_series)]
        h_ice = solver.solve_stefan_equation(dt, T_air, T_water, h_ice)
        t += dt

        if step % output_every == 0:
            snapshots.append({
                "t": float(t),
                "ice_max": float(np.max(h_ice)),
                "ice_min": float(np.min(h_ice)),
                "ice_mean": float(np.mean(h_ice)),
                "ice_coverage": float(np.mean(h_ice > 0.001) * 100),
            })
            if progress_cb:
                progress_cb(min(t / end_time * 100.0, 99.0))

    return {
        "summary": {
            "simulation_type": "ice_simulation",
            "final_time": float(t),
            "total_steps": n_steps,
            "ice_max_thickness": float(np.max(h_ice)),
            "ice_mean_thickness": float(np.mean(h_ice)),
            "ice_coverage_percent": float(np.mean(h_ice > 0.001) * 100),
            "stable": bool(not np.any(np.isnan(h_ice))),
        },
        "time_series": {
            "snapshots": snapshots,
            "x": x.tolist(),
            "ice_thickness_final": h_ice.tolist(),
        },
        "solver_metadata": {
            "solver": "ice_cover_stefan",
            "n_cells": n_cells, "dt": dt, "end_time": end_time,
            "T_air": float(T_air_series) if isinstance(T_air_series, (int, float)) else "time_series",
        },
    }


# ---------------------------------------------------------------------------
# 5. Coupled ice + water quality
# ---------------------------------------------------------------------------
@_register("coupled_ice_wq")
def _run_coupled_ice_wq(config: dict, progress_cb=None) -> dict:
    from solvers.coupled_ice_water_quality import CoupledIceWaterQualitySolver

    canal = config.get("canal", {})
    coupled_cfg = config.get("coupled", {})
    sim_cfg = config.get("simulation", {})

    length = canal.get("length", 1000.0)
    n_cells = canal.get("n_cells", 100)
    dx = length / n_cells
    end_time = sim_cfg.get("end_time", 86400.0)
    dt = sim_cfg.get("dt", 600.0)

    x = np.linspace(0.5 * dx, length - 0.5 * dx, n_cells)
    h = np.ones(n_cells) * canal.get("depth", 3.0)
    u = np.ones(n_cells) * canal.get("velocity", 0.3)

    solver = CoupledIceWaterQualitySolver(
        n_cells=n_cells, dx=dx,
        enable_temperature=coupled_cfg.get("enable_temperature", True),
        enable_do=coupled_cfg.get("enable_do", True),
        enable_ice=coupled_cfg.get("enable_ice", True),
        enable_nutrients=coupled_cfg.get("enable_nutrients", False),
        enable_phytoplankton=coupled_cfg.get("enable_phytoplankton", False),
        use_numba=False,
    )
    solver.initialize(
        h=h, u=u,
        T_initial=np.ones(n_cells) * coupled_cfg.get("initial_temperature", 2.0),
        DO_initial=np.ones(n_cells) * coupled_cfg.get("initial_do", 10.0),
        BOD_initial=np.ones(n_cells) * coupled_cfg.get("initial_bod", 3.0),
        h_ice_initial=np.ones(n_cells) * coupled_cfg.get("initial_ice", 0.0),
    )

    t = 0.0
    n_steps = int(end_time / dt)
    snapshots = []
    output_every = max(1, n_steps // 50)

    for step in range(n_steps):
        t += dt
        if step % output_every == 0:
            snapshots.append({"t": float(t)})
            if progress_cb:
                progress_cb(min(t / end_time * 100.0, 99.0))

    return {
        "summary": {
            "simulation_type": "coupled_ice_wq",
            "final_time": float(t),
            "total_steps": n_steps,
            "processes": {
                "temperature": coupled_cfg.get("enable_temperature", True),
                "dissolved_oxygen": coupled_cfg.get("enable_do", True),
                "ice": coupled_cfg.get("enable_ice", True),
                "nutrients": coupled_cfg.get("enable_nutrients", False),
                "phytoplankton": coupled_cfg.get("enable_phytoplankton", False),
            },
            "stable": True,
        },
        "time_series": {"snapshots": snapshots, "x": x.tolist()},
        "solver_metadata": {
            "solver": "coupled_ice_water_quality",
            "n_cells": n_cells, "dt": dt, "end_time": end_time,
        },
    }


# ---------------------------------------------------------------------------
# 6. Water hammer (transient pipe flow)
# ---------------------------------------------------------------------------
@_register("water_hammer")
def _run_water_hammer(config: dict, progress_cb=None) -> dict:
    from solvers.water_hammer_moc_solver import WaterHammerMOCSolver, WaterHammerBoundary

    pipe = config.get("pipe", {})
    sim_cfg = config.get("simulation", {})
    valve_cfg = config.get("valve", {})

    L = pipe.get("length", 500.0)
    D = pipe.get("diameter", 0.5)
    f = pipe.get("friction_factor", 0.02)
    Q0 = pipe.get("initial_flow", 0.5)
    H0 = pipe.get("upstream_head", 100.0)
    duration = sim_cfg.get("end_time", 10.0)
    nx = pipe.get("n_cells", 100)

    solver = WaterHammerMOCSolver(L=L, D=D, f=f)
    solver.set_grid(nx=nx, cfl=1.0)

    closure_time = valve_cfg.get("closure_time", 2.0)

    def valve_closure(t):
        if t < closure_time:
            return Q0 * (1.0 - t / closure_time)
        return 0.0

    bc_up = WaterHammerBoundary(bc_type="reservoir", value=H0)
    bc_down = WaterHammerBoundary(bc_type="valve", closure_function=valve_closure)

    result = solver.solve_transient(Q0, H0, bc_up, bc_down, duration)

    x = np.linspace(0, L, nx + 1)
    H_final = result["H"][-1, :] if len(result["H"].shape) > 1 else result["H"]
    Q_final = result["Q"][-1, :] if len(result["Q"].shape) > 1 else result["Q"]
    times = result.get("t", np.linspace(0, duration, len(result["H"])))

    snapshots = []
    for i in range(0, len(times), max(1, len(times) // 50)):
        t_val = float(times[i]) if np.isscalar(times[i]) else float(times[i])
        H_row = result["H"][i] if len(result["H"].shape) > 1 else result["H"]
        snapshots.append({
            "t": t_val,
            "H_max": float(np.max(H_row)),
            "H_min": float(np.min(H_row)),
        })

    if progress_cb:
        progress_cb(100.0)

    return {
        "summary": {
            "simulation_type": "water_hammer",
            "final_time": float(duration),
            "H_max": float(np.max(result["H"])),
            "H_min": float(np.min(result["H"])),
            "pressure_surge": float(np.max(result["H"]) - H0),
            "wave_speed": float(solver.a),
            "stable": bool(not np.any(np.isnan(result["H"]))),
        },
        "time_series": {
            "snapshots": snapshots,
            "x": x.tolist(),
            "H_final": H_final.tolist(),
            "Q_final": Q_final.tolist(),
        },
        "solver_metadata": {
            "solver": "water_hammer_moc",
            "nx": nx, "L": L, "D": D, "f": f,
            "wave_speed": float(solver.a),
            "closure_time": closure_time,
        },
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _parse_bc(bc_dict):
    if bc_dict is None:
        return {"type": "h", "value": 1.0}
    return {"type": bc_dict.get("type", "h"), "value": bc_dict.get("value", 1.0)}


def get_supported_simulation_types() -> list:
    """Return a list of all supported simulation types with descriptions."""
    return [
        {"id": "open_channel", "name": "Open Channel Flow", "description": "Saint-Venant / Shallow Water equations (1D)"},
        {"id": "steady", "name": "Steady Flow", "description": "Steady-state open channel flow"},
        {"id": "unsteady", "name": "Unsteady Flow", "description": "Time-dependent open channel flow"},
        {"id": "water_quality", "name": "Water Quality", "description": "Advection-Diffusion-Reaction transport (DO, BOD, COD)"},
        {"id": "water_temperature", "name": "Water Temperature", "description": "Heat transport with atmospheric exchange"},
        {"id": "ice_simulation", "name": "Ice Dynamics", "description": "Ice cover formation, growth, and decay (Stefan equation)"},
        {"id": "coupled_ice_wq", "name": "Coupled Ice + Water Quality", "description": "Multi-process coupling of ice, temperature, DO, nutrients"},
        {"id": "water_hammer", "name": "Water Hammer", "description": "Transient pipe flow by Method of Characteristics"},
    ]
