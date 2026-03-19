"""Controller adapter -- implements ControllerProtocol from hydromind-contracts.

Wraps HydroClaude PID and MPC controllers behind the uniform
``ControllerProtocol`` interface.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class HydroClaudeController:
    """ControllerProtocol implementation backed by HydroClaude controllers.

    Satisfies ``hydromind_contracts.ControllerProtocol`` (duck-typed /
    runtime-checkable Protocol).

    Supported controller types (set via ``controller_type`` in
    ``compute_action`` *state* dict or via ``set_target``):
        - ``"pid"`` -- PIDController (default)
        - ``"mpc"`` -- MPCController (requires cvxpy + IDZ model params)
    """

    def __init__(self) -> None:
        self._targets: dict = {}
        self._controller_type: str = "pid"
        self._pid: Any = None
        self._mpc: Any = None
        self._pid_config: dict = {}
        self._mpc_config: dict = {}

    # ------------------------------------------------------------------
    # ControllerProtocol.compute_action
    # ------------------------------------------------------------------
    def compute_action(self, state: dict, target: dict, constraints: dict) -> dict:
        """Compute a control action given current state and targets.

        Args:
            state: Current system state. Expected keys:
                - h (float): current water level
                - controller_type (str, optional): "pid" or "mpc"
                - dt (float, optional): time step for PID integration
            target: Desired setpoints. Expected keys:
                - h (float): target water level
            constraints: Operational constraints (currently used for
                PID output limits):
                - output_min (float)
                - output_max (float)

        Returns:
            Dictionary with:
                - u (float): control output
                - error (float): setpoint - measurement
                - controller_type (str)
        """
        ctype = state.get("controller_type", self._controller_type)
        setpoint = target.get("h", self._targets.get("h", 1.0))
        measurement = state.get("h", 0.0)

        try:
            if ctype == "mpc":
                return self._compute_mpc(measurement, setpoint, state, constraints)
            else:
                return self._compute_pid(measurement, setpoint, state, constraints)
        except Exception as exc:
            logger.exception("Controller computation failed")
            return {
                "u": 0.0,
                "error": setpoint - measurement,
                "controller_type": ctype,
                "error_message": str(exc),
            }

    # ------------------------------------------------------------------
    # ControllerProtocol.set_target
    # ------------------------------------------------------------------
    def set_target(self, targets: dict) -> None:
        """Update control targets and optionally the controller type."""
        self._targets.update(targets)
        if "controller_type" in targets:
            self._controller_type = targets["controller_type"]
        if "pid_config" in targets:
            self._pid_config = targets["pid_config"]
            self._pid = None  # Force rebuild
        if "mpc_config" in targets:
            self._mpc_config = targets["mpc_config"]
            self._mpc = None  # Force rebuild

    # ==================================================================
    # Private helpers
    # ==================================================================

    def _get_pid(self, constraints: dict) -> Any:
        """Lazily build a PID controller."""
        if self._pid is not None:
            return self._pid
        from control.pid_controller import PIDController, PIDConfig

        cfg_kwargs: dict = dict(self._pid_config)
        # Apply constraints as output limits
        if "output_min" in constraints:
            cfg_kwargs.setdefault("output_min", constraints["output_min"])
        if "output_max" in constraints:
            cfg_kwargs.setdefault("output_max", constraints["output_max"])
        cfg_kwargs.setdefault("kp", 1.0)
        cfg_kwargs.setdefault("ki", 0.1)
        cfg_kwargs.setdefault("kd", 0.05)

        config = PIDConfig(**{
            k: v for k, v in cfg_kwargs.items()
            if k in PIDConfig.__dataclass_fields__
        })
        self._pid = PIDController(config)
        return self._pid

    def _compute_pid(
        self, measurement: float, setpoint: float, state: dict, constraints: dict
    ) -> dict:
        pid = self._get_pid(constraints)
        pid.setpoint = setpoint
        dt = state.get("dt", pid.config.dt)
        u = pid.compute(measurement, dt=dt)
        return {
            "u": float(u),
            "error": float(setpoint - measurement),
            "controller_type": "pid",
        }

    def _compute_mpc(
        self, measurement: float, setpoint: float, state: dict, constraints: dict
    ) -> dict:
        if self._mpc is None:
            try:
                from control.mpc_controller import MPCController, MPCConfig
                from control.idz_model import IDZParameters
            except ImportError as exc:
                return {
                    "u": 0.0,
                    "error": setpoint - measurement,
                    "controller_type": "mpc",
                    "error_message": f"MPC dependencies unavailable: {exc}",
                }

            # Build IDZ params from config or defaults
            idz_cfg = self._mpc_config.get("idz", {})
            idz_params = IDZParameters(
                K=idz_cfg.get("K", 0.001),
                tau_z=idz_cfg.get("tau_z", 30.0),
                tau_d=idz_cfg.get("tau_d", 60.0),
                theta=idz_cfg.get("theta", 120.0),
            )

            mpc_cfg_kwargs = {
                k: v for k, v in self._mpc_config.items()
                if k in MPCConfig.__dataclass_fields__ and k != "idz"
            }
            mpc_config = MPCConfig(**mpc_cfg_kwargs)

            self._mpc = MPCController(idz_params, mpc_config)

        u, info = self._mpc.compute_control(measurement, setpoint)
        result = {
            "u": float(u),
            "error": float(setpoint - measurement),
            "controller_type": "mpc",
        }
        if isinstance(info, dict):
            result["diagnostics"] = {
                k: float(v) if hasattr(v, "__float__") else v
                for k, v in info.items()
            }
        return result
