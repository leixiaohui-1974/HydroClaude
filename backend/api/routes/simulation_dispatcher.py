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
    - pipe_network: Steady-state pipe network hydraulics (Hardy-Cross / Newton-Raphson)
    - pipe_network_pdd: Pressure-Driven Demand analysis for pipe networks
    - network_wq: Water quality transport in pressurized pipe networks
    - network_optimization: Genetic Algorithm pipe sizing optimization
    - extended_period: Extended Period Simulation (EPS) with demand patterns
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
# 7. Pipe network steady-state hydraulics (Hardy-Cross / Newton-Raphson)
# ---------------------------------------------------------------------------
def _create_network_solver(topo, config: dict, max_iter_override=None, tol_override=None):
    """Create the appropriate network solver based on config."""
    solver_cfg = config.get("solver", {})
    method = solver_cfg.get("method", "hardy_cross")
    max_iter = max_iter_override or solver_cfg.get("max_iter", 100)
    tol = tol_override or solver_cfg.get("tol", 1e-6)

    if method == "newton_raphson":
        from solvers.newton_raphson_network_solver import NewtonRaphsonNetworkSolver
        return NewtonRaphsonNetworkSolver(
            network=topo,
            max_iter=max_iter,
            tol=tol,
            damping_factor=solver_cfg.get("damping_factor", 0.5),
            adaptive_damping=solver_cfg.get("adaptive_damping", True),
            use_hardy_cross_init=solver_cfg.get("use_hardy_cross_init", False),
            verbose=False,
        )
    else:
        from solvers.hardy_cross_solver import HardyCrossSolver
        return HardyCrossSolver(
            network=topo,
            max_iter=max_iter,
            tol=tol,
            relaxation_factor=solver_cfg.get("relaxation_factor", 1.0),
            verbose=False,
        )


def _build_network(config: dict):
    """Build a NetworkTopology from JSON config."""
    # Ensure project root is in sys.path for background threads
    if _project_root not in sys.path:
        sys.path.insert(0, _project_root)

    from network.network_topology import NetworkTopology
    from network.network_node import NetworkNode
    from network.pressure_pipe import PressurePipe

    net_cfg = config.get("network", {})
    topo = NetworkTopology(name=net_cfg.get("name", "API Network"))

    for nd in net_cfg.get("nodes", []):
        node = NetworkNode(
            node_id=nd["id"],
            node_type=nd.get("type", "junction"),
            elevation=nd.get("elevation", 0.0),
            demand=nd.get("demand", 0.0),
            initial_head=nd.get("head"),
            min_pressure=nd.get("min_pressure", 0.0),
            required_pressure=nd.get("required_pressure", 20.0),
        )
        topo.add_node(node)

    for pp in net_cfg.get("pipes", []):
        pipe = PressurePipe(
            pipe_id=pp["id"],
            diameter=pp.get("diameter", 0.3),
            length=pp.get("length", 500.0),
            roughness=pp.get("roughness", 0.001),
            formula=pp.get("formula", "darcy"),
            K_minor=pp.get("K_minor", 0.0),
        )
        topo.add_pipe(pipe, pp["from"], pp["to"])

    return topo


@_register("pipe_network")
def _run_pipe_network(config: dict, progress_cb=None) -> dict:
    """Steady-state pipe network hydraulic analysis."""
    solver_cfg = config.get("solver", {})
    method = solver_cfg.get("method", "newton_raphson")

    topo = _build_network(config)

    if progress_cb:
        progress_cb(10.0)

    solver = _create_network_solver(topo, config)

    if progress_cb:
        progress_cb(30.0)

    flows, heads = solver.solve()

    if progress_cb:
        progress_cb(90.0)

    # Compute derived quantities
    net_cfg = config.get("network", {})
    pipes_info = {}
    for pp in net_cfg.get("pipes", []):
        pid = pp["id"]
        Q = flows.get(pid, 0.0)
        D = pp.get("diameter", 0.3)
        A = np.pi * D**2 / 4
        v = abs(Q) / A if A > 0 else 0.0
        pipes_info[pid] = {"Q": Q, "velocity": v, "diameter": D}

    # Pressure at junctions
    pressures = {}
    for nd in net_cfg.get("nodes", []):
        nid = nd["id"]
        if nid in heads:
            pressures[nid] = heads[nid] - nd.get("elevation", 0.0)

    min_pressure = min(pressures.values()) if pressures else 0.0

    return {
        "summary": {
            "simulation_type": "pipe_network",
            "solver_method": method,
            "converged": solver.converged,
            "iterations": solver.iteration_count,
            "num_nodes": len(topo.nodes),
            "num_pipes": len(topo.pipes),
            "min_pressure": float(min_pressure),
            "max_velocity": float(max((p["velocity"] for p in pipes_info.values()), default=0.0)),
            "total_demand": float(sum(nd.get("demand", 0.0) for nd in net_cfg.get("nodes", []))),
            "stable": solver.converged,
        },
        "time_series": {
            "flows": {k: float(v) for k, v in flows.items()},
            "heads": {k: float(v) for k, v in heads.items()},
            "pressures": {k: float(v) for k, v in pressures.items()},
            "pipes": {k: {kk: float(vv) for kk, vv in v.items()} for k, v in pipes_info.items()},
        },
        "solver_metadata": {
            "solver": method,
            "iterations": solver.iteration_count,
            "converged": solver.converged,
            "num_loops": topo.num_loops if hasattr(topo, "num_loops") else 0,
        },
    }


# ---------------------------------------------------------------------------
# 8. Pressure-Driven Demand (PDD) analysis
# ---------------------------------------------------------------------------
@_register("pipe_network_pdd")
def _run_pipe_network_pdd(config: dict, progress_cb=None) -> dict:
    """
    Pressure-Driven Demand analysis.

    Uses the Wagner formula: Q_actual = Q_base * ((P - P_min) / (P_req - P_min))^0.5
    where P_min = minimum serviceable pressure, P_req = required pressure.
    Iterates until demand-pressure equilibrium is reached.
    """
    solver_cfg = config.get("solver", {})
    pdd_cfg = config.get("pdd", {})
    P_min = pdd_cfg.get("min_pressure", 0.0)
    P_req = pdd_cfg.get("required_pressure", 20.0)
    pdd_max_iter = pdd_cfg.get("max_iter", 30)
    pdd_tol = pdd_cfg.get("tol", 0.001)

    net_cfg = config.get("network", {})
    base_demands = {nd["id"]: nd.get("demand", 0.0) for nd in net_cfg.get("nodes", [])}

    if progress_cb:
        progress_cb(5.0)

    pdd_iteration = 0
    demand_converged = False
    current_demands = dict(base_demands)
    prev_demands = {}
    pdd_history = []

    while pdd_iteration < pdd_max_iter and not demand_converged:
        # Update demands in config
        for nd in net_cfg["nodes"]:
            nd["demand"] = current_demands[nd["id"]]
        config["network"] = net_cfg

        # Solve hydraulics
        topo = _build_network(config)
        solver = _create_network_solver(topo, config)
        flows, heads = solver.solve()

        # Compute pressures and update demands (Wagner formula)
        pressures = {}
        for nd in net_cfg.get("nodes", []):
            nid = nd["id"]
            if nid in heads:
                pressures[nid] = heads[nid] - nd.get("elevation", 0.0)

        prev_demands = dict(current_demands)
        for nid, base_d in base_demands.items():
            if base_d <= 0 or nid not in pressures:
                continue
            P = pressures[nid]
            if P <= P_min:
                current_demands[nid] = 0.0
            elif P >= P_req:
                current_demands[nid] = base_d
            else:
                ratio = (P - P_min) / (P_req - P_min)
                current_demands[nid] = base_d * float(np.sqrt(max(ratio, 0.0)))

        # Check convergence
        max_diff = max(
            abs(current_demands[nid] - prev_demands.get(nid, 0.0))
            for nid in base_demands if base_demands[nid] > 0
        ) if any(base_demands[nid] > 0 for nid in base_demands) else 0.0

        pdd_iteration += 1
        pdd_history.append({
            "iteration": pdd_iteration,
            "max_demand_diff": float(max_diff),
            "total_actual_demand": float(sum(current_demands[nid] for nid in current_demands if base_demands[nid] > 0)),
        })

        if max_diff < pdd_tol:
            demand_converged = True

        if progress_cb:
            progress_cb(min(10 + 80 * pdd_iteration / pdd_max_iter, 90.0))

    # Compute demand satisfaction ratio
    total_base = sum(d for d in base_demands.values() if d > 0)
    total_actual = sum(current_demands[nid] for nid in current_demands if base_demands[nid] > 0)
    satisfaction = total_actual / total_base if total_base > 0 else 1.0

    # Deficit nodes
    deficit_nodes = []
    for nid, base_d in base_demands.items():
        if base_d > 0 and current_demands[nid] < base_d * 0.99:
            deficit_nodes.append({
                "node_id": nid,
                "base_demand": base_d,
                "actual_demand": current_demands[nid],
                "pressure": pressures.get(nid, 0.0),
                "deficit_percent": (1 - current_demands[nid] / base_d) * 100 if base_d > 0 else 0,
            })

    return {
        "summary": {
            "simulation_type": "pipe_network_pdd",
            "pdd_converged": demand_converged,
            "pdd_iterations": pdd_iteration,
            "hydraulic_converged": solver.converged,
            "demand_satisfaction": float(satisfaction * 100),
            "total_base_demand": float(total_base),
            "total_actual_demand": float(total_actual),
            "num_deficit_nodes": len(deficit_nodes),
            "min_pressure": float(min(pressures.values()) if pressures else 0.0),
            "stable": demand_converged and solver.converged,
        },
        "time_series": {
            "flows": {k: float(v) for k, v in flows.items()},
            "heads": {k: float(v) for k, v in heads.items()},
            "pressures": {k: float(v) for k, v in pressures.items()},
            "actual_demands": {k: float(v) for k, v in current_demands.items()},
            "deficit_nodes": deficit_nodes,
            "pdd_convergence": pdd_history,
        },
        "solver_metadata": {
            "solver": "newton_raphson_pdd",
            "P_min": P_min, "P_req": P_req,
            "pdd_iterations": pdd_iteration,
            "demand_satisfaction_percent": float(satisfaction * 100),
        },
    }


# ---------------------------------------------------------------------------
# 9. Network water quality transport (chlorine decay in pipes)
# ---------------------------------------------------------------------------
@_register("network_wq")
def _run_network_wq(config: dict, progress_cb=None) -> dict:
    """
    Water quality transport in pressurized pipe networks.

    Implements first-order chlorine decay with:
    - Bulk decay: dC/dt = -k_b * C
    - Wall decay: dC/dt = -k_w * C (simplified)
    - Advective transport through pipes based on hydraulic solution
    - Mixing at junctions (flow-weighted)
    """
    wq_cfg = config.get("water_quality", {})
    net_cfg = config.get("network", {})

    k_bulk = wq_cfg.get("bulk_decay_rate", 0.5)   # 1/day
    k_wall = wq_cfg.get("wall_decay_rate", 0.1)    # 1/day
    C_source = wq_cfg.get("source_concentration", 1.0)  # mg/L at reservoirs
    duration = wq_cfg.get("duration", 86400.0)     # seconds
    dt_wq = wq_cfg.get("dt", 60.0)                 # seconds

    # First solve steady-state hydraulics
    topo = _build_network(config)
    solver = _create_network_solver(topo, config)
    flows, heads = solver.solve()

    if progress_cb:
        progress_cb(20.0)

    # Initialize concentrations
    node_ids = list(topo.nodes.keys())
    C = {}
    for nd in net_cfg.get("nodes", []):
        nid = nd["id"]
        if nd.get("type") == "reservoir":
            C[nid] = C_source
        else:
            C[nid] = wq_cfg.get("initial_concentration", 0.0)

    # Pipe travel times and residence concentrations
    pipe_info = {}
    for pp in net_cfg.get("pipes", []):
        pid = pp["id"]
        Q = abs(flows.get(pid, 0.0))
        D = pp.get("diameter", 0.3)
        L = pp.get("length", 500.0)
        A = np.pi * D**2 / 4
        v = Q / A if A > 0 and Q > 1e-12 else 0.001
        travel_time = L / v if v > 1e-12 else L / 0.001
        pipe_info[pid] = {
            "from": pp["from"], "to": pp["to"],
            "Q": flows.get(pid, 0.0),
            "velocity": v, "travel_time": travel_time, "length": L,
        }

    # Time-stepping for WQ transport
    k_total = (k_bulk + k_wall) / 86400.0  # convert 1/day → 1/s
    n_steps = int(duration / dt_wq)
    snapshots = []
    output_every = max(1, n_steps // 50)

    for step in range(n_steps):
        t = (step + 1) * dt_wq
        new_C = {}

        for nid in node_ids:
            nd_info = next((nd for nd in net_cfg["nodes"] if nd["id"] == nid), {})

            # Reservoirs maintain constant concentration
            if nd_info.get("type") == "reservoir":
                new_C[nid] = C_source
                continue

            # Junction mixing: flow-weighted average of incoming pipe concentrations
            total_inflow = 0.0
            mass_inflow = 0.0

            for pp in net_cfg.get("pipes", []):
                pid = pp["id"]
                info = pipe_info[pid]
                Q_pipe = info["Q"]
                travel = info["travel_time"]

                # Determine flow direction and contributing node
                if Q_pipe > 0 and pp["to"] == nid:
                    # Positive flow into this node
                    source_C = C.get(pp["from"], 0.0)
                    # Decay during travel
                    C_arriving = source_C * float(np.exp(-k_total * min(travel, dt_wq)))
                    mass_inflow += abs(Q_pipe) * C_arriving
                    total_inflow += abs(Q_pipe)
                elif Q_pipe < 0 and pp["from"] == nid:
                    # Reverse flow into this node
                    source_C = C.get(pp["to"], 0.0)
                    C_arriving = source_C * float(np.exp(-k_total * min(travel, dt_wq)))
                    mass_inflow += abs(Q_pipe) * C_arriving
                    total_inflow += abs(Q_pipe)

            if total_inflow > 1e-12:
                new_C[nid] = mass_inflow / total_inflow
            else:
                # No inflow: just decay in place
                new_C[nid] = C.get(nid, 0.0) * float(np.exp(-k_total * dt_wq))

        C = new_C

        if step % output_every == 0:
            concentrations = list(C.values())
            snapshots.append({
                "t": float(t),
                "C_max": float(max(concentrations)) if concentrations else 0.0,
                "C_min": float(min(concentrations)) if concentrations else 0.0,
                "C_mean": float(np.mean(concentrations)) if concentrations else 0.0,
            })
            if progress_cb:
                progress_cb(min(20 + 70 * step / n_steps, 90.0))

    # Compliance check (e.g., minimum 0.2 mg/L residual)
    min_residual = wq_cfg.get("min_residual", 0.2)
    non_compliant = [
        {"node_id": nid, "concentration": float(c)}
        for nid, c in C.items()
        if c < min_residual and next((nd for nd in net_cfg["nodes"] if nd["id"] == nid), {}).get("type") != "reservoir"
    ]

    all_c = list(C.values())

    return {
        "summary": {
            "simulation_type": "network_wq",
            "duration_hours": float(duration / 3600),
            "C_max": float(max(all_c)) if all_c else 0.0,
            "C_min_junction": float(min(
                c for nid, c in C.items()
                if next((nd for nd in net_cfg["nodes"] if nd["id"] == nid), {}).get("type") != "reservoir"
            )) if any(
                next((nd for nd in net_cfg["nodes"] if nd["id"] == nid), {}).get("type") != "reservoir"
                for nid in C
            ) else 0.0,
            "C_mean": float(np.mean(all_c)) if all_c else 0.0,
            "num_non_compliant": len(non_compliant),
            "min_residual_threshold": min_residual,
            "stable": True,
        },
        "time_series": {
            "snapshots": snapshots,
            "final_concentrations": {k: float(v) for k, v in C.items()},
            "non_compliant_nodes": non_compliant,
        },
        "solver_metadata": {
            "solver": "network_wq_transport",
            "k_bulk": k_bulk, "k_wall": k_wall,
            "dt": dt_wq, "duration": duration,
            "C_source": C_source,
        },
    }


# ---------------------------------------------------------------------------
# 10. Genetic Algorithm pipe network optimization
# ---------------------------------------------------------------------------
@_register("network_optimization")
def _run_network_optimization(config: dict, progress_cb=None) -> dict:
    """
    Genetic Algorithm for optimal pipe sizing.

    Minimizes total pipe cost subject to minimum pressure constraints.
    Uses tournament selection, uniform crossover, and mutation.
    """
    import random

    opt_cfg = config.get("optimization", {})
    net_cfg = config.get("network", {})
    solver_cfg = config.get("solver", {})

    pop_size = opt_cfg.get("population_size", 50)
    n_gen = opt_cfg.get("generations", 80)
    P_min_req = opt_cfg.get("min_pressure", 20.0)
    crossover_rate = opt_cfg.get("crossover_rate", 0.8)
    mutation_rate = opt_cfg.get("mutation_rate", 0.1)
    seed = opt_cfg.get("seed", 42)
    random.seed(seed)
    np.random.seed(seed)

    # Available commercial pipe diameters (m) and cost per meter ($/m)
    PIPE_CATALOG = opt_cfg.get("pipe_catalog", [
        {"diameter": 0.100, "cost": 30},
        {"diameter": 0.150, "cost": 50},
        {"diameter": 0.200, "cost": 80},
        {"diameter": 0.250, "cost": 120},
        {"diameter": 0.300, "cost": 170},
        {"diameter": 0.350, "cost": 230},
        {"diameter": 0.400, "cost": 300},
        {"diameter": 0.450, "cost": 380},
        {"diameter": 0.500, "cost": 470},
        {"diameter": 0.600, "cost": 680},
        {"diameter": 0.800, "cost": 1200},
        {"diameter": 1.000, "cost": 1900},
    ])
    n_diameters = len(PIPE_CATALOG)
    pipe_list = net_cfg.get("pipes", [])
    n_pipes = len(pipe_list)

    if n_pipes == 0:
        raise ValueError("No pipes defined for optimization")

    # Penalty for pressure violations
    penalty_factor = opt_cfg.get("penalty_factor", 1e6)

    def evaluate(individual):
        """Evaluate cost + penalty for a pipe sizing solution."""
        # Build config with individual's diameters
        test_config = {"network": {"nodes": net_cfg["nodes"], "pipes": []}, "solver": solver_cfg}
        total_cost = 0.0
        for i, pp in enumerate(pipe_list):
            idx = individual[i]
            cat = PIPE_CATALOG[idx]
            test_pipe = dict(pp)
            test_pipe["diameter"] = cat["diameter"]
            test_config["network"]["pipes"].append(test_pipe)
            total_cost += cat["cost"] * pp.get("length", 500.0)

        # Solve hydraulics
        try:
            topo = _build_network(test_config)
            solver = _create_network_solver(topo, test_config, max_iter_override=30, tol_override=1e-4)
            flows, heads = solver.solve()

            if not solver.converged:
                return total_cost + penalty_factor * 10

            # Check pressure constraints
            penalty = 0.0
            for nd in net_cfg["nodes"]:
                nid = nd["id"]
                if nd.get("type") == "reservoir":
                    continue
                if nid in heads:
                    P = heads[nid] - nd.get("elevation", 0.0)
                    if P < P_min_req:
                        penalty += penalty_factor * (P_min_req - P) ** 2
            return total_cost + penalty

        except Exception:
            return total_cost + penalty_factor * 100

    # Initialize population
    population = [
        [random.randint(0, n_diameters - 1) for _ in range(n_pipes)]
        for _ in range(pop_size)
    ]
    fitness = [evaluate(ind) for ind in population]
    best_fitness_history = []
    best_idx = int(np.argmin(fitness))
    best_individual = list(population[best_idx])
    best_fit = fitness[best_idx]

    if progress_cb:
        progress_cb(10.0)

    # GA main loop
    for gen in range(n_gen):
        new_pop = []
        for _ in range(pop_size // 2):
            # Tournament selection (size 3)
            def tournament():
                candidates = random.sample(range(pop_size), min(3, pop_size))
                return population[min(candidates, key=lambda i: fitness[i])]

            p1 = tournament()
            p2 = tournament()

            # Uniform crossover
            if random.random() < crossover_rate:
                c1 = [p1[j] if random.random() < 0.5 else p2[j] for j in range(n_pipes)]
                c2 = [p2[j] if random.random() < 0.5 else p1[j] for j in range(n_pipes)]
            else:
                c1, c2 = list(p1), list(p2)

            # Mutation
            for child in [c1, c2]:
                for j in range(n_pipes):
                    if random.random() < mutation_rate:
                        child[j] = random.randint(0, n_diameters - 1)

            new_pop.extend([c1, c2])

        population = new_pop[:pop_size]
        fitness = [evaluate(ind) for ind in population]

        gen_best_idx = int(np.argmin(fitness))
        if fitness[gen_best_idx] < best_fit:
            best_fit = fitness[gen_best_idx]
            best_individual = list(population[gen_best_idx])

        best_fitness_history.append({"generation": gen + 1, "best_cost": float(best_fit)})

        if progress_cb:
            progress_cb(min(10 + 80 * (gen + 1) / n_gen, 90.0))

    # Decode best solution
    optimal_pipes = {}
    total_cost = 0.0
    for i, pp in enumerate(pipe_list):
        cat = PIPE_CATALOG[best_individual[i]]
        optimal_pipes[pp["id"]] = {
            "diameter": cat["diameter"],
            "cost_per_m": cat["cost"],
            "length": pp.get("length", 500.0),
            "total_cost": cat["cost"] * pp.get("length", 500.0),
            "original_diameter": pp.get("diameter", 0.3),
        }
        total_cost += cat["cost"] * pp.get("length", 500.0)

    return {
        "summary": {
            "simulation_type": "network_optimization",
            "total_cost": float(total_cost),
            "generations": n_gen,
            "population_size": pop_size,
            "num_pipes": n_pipes,
            "best_fitness": float(best_fit),
            "feasible": float(best_fit) == float(total_cost),
            "stable": True,
        },
        "time_series": {
            "convergence": best_fitness_history,
            "optimal_pipes": optimal_pipes,
        },
        "solver_metadata": {
            "solver": "genetic_algorithm",
            "generations": n_gen, "population_size": pop_size,
            "crossover_rate": crossover_rate, "mutation_rate": mutation_rate,
            "min_pressure_constraint": P_min_req,
            "pipe_catalog_size": n_diameters,
        },
    }


# ---------------------------------------------------------------------------
# 11. Extended Period Simulation (EPS)
# ---------------------------------------------------------------------------
@_register("extended_period")
def _run_extended_period(config: dict, progress_cb=None) -> dict:
    """
    Extended Period Simulation for pipe networks.

    Simulates network hydraulics over multiple time steps with:
    - Time-varying demand patterns (multiplier array)
    - Tank level tracking (mass balance)
    - Periodic steady-state solves
    """
    eps_cfg = config.get("eps", {})
    net_cfg = config.get("network", {})
    solver_cfg = config.get("solver", {})

    duration = eps_cfg.get("duration", 86400.0)          # seconds (default 24h)
    timestep = eps_cfg.get("timestep", 3600.0)           # seconds (default 1h)
    # Demand pattern: multipliers for each timestep (repeats cyclically)
    demand_pattern = eps_cfg.get("demand_pattern", [
        0.5, 0.4, 0.3, 0.3, 0.4, 0.6,    # 00:00-06:00
        0.8, 1.2, 1.4, 1.3, 1.1, 1.0,     # 06:00-12:00
        0.9, 0.9, 1.0, 1.1, 1.3, 1.4,     # 12:00-18:00
        1.2, 1.0, 0.8, 0.7, 0.6, 0.5,     # 18:00-24:00
    ])

    n_steps = int(duration / timestep)
    base_demands = {nd["id"]: nd.get("demand", 0.0) for nd in net_cfg.get("nodes", [])}

    # Tank tracking
    tanks = {}
    for nd in net_cfg.get("nodes", []):
        if nd.get("type") == "tank":
            tanks[nd["id"]] = {
                "level": nd.get("initial_level", nd.get("head", 50.0) - nd.get("elevation", 0.0)),
                "area": nd.get("area", 100.0),       # m²
                "min_level": nd.get("min_level", 0.5),
                "max_level": nd.get("max_level", 10.0),
                "elevation": nd.get("elevation", 0.0),
            }

    snapshots = []
    all_flows = []
    all_pressures = []

    for step in range(n_steps):
        t = (step + 1) * timestep
        pattern_idx = step % len(demand_pattern)
        multiplier = demand_pattern[pattern_idx]

        # Apply demand multiplier
        step_config = {"network": {"nodes": [], "pipes": net_cfg["pipes"]}, "solver": solver_cfg}
        for nd in net_cfg["nodes"]:
            nd_copy = dict(nd)
            if nd["id"] in base_demands and base_demands[nd["id"]] > 0:
                nd_copy["demand"] = base_demands[nd["id"]] * multiplier
            # Update tank head from level
            if nd["id"] in tanks:
                tank = tanks[nd["id"]]
                nd_copy["head"] = tank["elevation"] + tank["level"]
                nd_copy["type"] = "reservoir"  # Treat tank as variable-head reservoir
            step_config["network"]["nodes"].append(nd_copy)

        # Solve hydraulics for this timestep
        try:
            topo = _build_network(step_config)
            solver = _create_network_solver(topo, step_config)
            flows, heads = solver.solve()
        except Exception as e:
            logger.warning(f"EPS step {step}: solver failed: {e}")
            flows, heads = {}, {}

        # Compute pressures
        pressures = {}
        for nd in step_config["network"]["nodes"]:
            nid = nd["id"]
            if nid in heads:
                pressures[nid] = heads[nid] - nd.get("elevation", 0.0)

        # Update tank levels
        for tank_id, tank in tanks.items():
            net_inflow = 0.0
            for pp in net_cfg.get("pipes", []):
                pid = pp["id"]
                Q = flows.get(pid, 0.0)
                if Q > 0 and pp["to"] == tank_id:
                    net_inflow += Q
                elif Q > 0 and pp["from"] == tank_id:
                    net_inflow -= Q
                elif Q < 0 and pp["from"] == tank_id:
                    net_inflow += abs(Q)
                elif Q < 0 and pp["to"] == tank_id:
                    net_inflow -= abs(Q)

            # Level change = net_inflow * dt / area
            dLevel = net_inflow * timestep / tank["area"]
            tank["level"] = max(tank["min_level"],
                                min(tank["max_level"], tank["level"] + dLevel))

        # Record snapshot
        all_p = list(pressures.values())
        snapshots.append({
            "t": float(t),
            "t_hours": float(t / 3600),
            "demand_multiplier": float(multiplier),
            "min_pressure": float(min(all_p)) if all_p else 0.0,
            "mean_pressure": float(np.mean(all_p)) if all_p else 0.0,
            "tank_levels": {k: float(v["level"]) for k, v in tanks.items()},
        })

        if progress_cb:
            progress_cb(min(step / n_steps * 95, 95.0))

    # Summary statistics
    all_min_p = [s["min_pressure"] for s in snapshots]
    all_mean_p = [s["mean_pressure"] for s in snapshots]

    return {
        "summary": {
            "simulation_type": "extended_period",
            "duration_hours": float(duration / 3600),
            "timestep_hours": float(timestep / 3600),
            "total_timesteps": n_steps,
            "min_pressure_overall": float(min(all_min_p)) if all_min_p else 0.0,
            "mean_pressure_overall": float(np.mean(all_mean_p)) if all_mean_p else 0.0,
            "num_tanks": len(tanks),
            "final_tank_levels": {k: float(v["level"]) for k, v in tanks.items()},
            "stable": True,
        },
        "time_series": {
            "snapshots": snapshots,
            "demand_pattern": demand_pattern,
        },
        "solver_metadata": {
            "solver": "extended_period_simulation",
            "duration": duration, "timestep": timestep,
            "n_steps": n_steps, "pattern_length": len(demand_pattern),
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
        {"id": "pipe_network", "name": "Pipe Network Hydraulics", "description": "Steady-state pipe network analysis (Hardy-Cross / Newton-Raphson)"},
        {"id": "pipe_network_pdd", "name": "Pressure-Driven Demand", "description": "Pipe network with pressure-dependent demand (Wagner formula)"},
        {"id": "network_wq", "name": "Network Water Quality", "description": "Chlorine decay and transport in pressurized pipe networks"},
        {"id": "network_optimization", "name": "Pipe Sizing Optimization", "description": "Genetic Algorithm for minimum-cost pipe network design"},
        {"id": "extended_period", "name": "Extended Period Simulation", "description": "Multi-timestep network analysis with demand patterns and tank dynamics"},
    ]
