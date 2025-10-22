Quick Start
===========

This guide will help you run your first simulation in 10 minutes.

First Example: Canal Flow
--------------------------

Create a file ``my_first_canal.py``:

.. code-block:: python

   import numpy as np
   from physics.steady_saint_venant import SteadySaintVenantSystem
   from solvers.newton_solver import NewtonSolver
   from utils.canal_utils import compute_steady_uniform_flow

   # Define canal parameters
   length = 1000.0      # m
   nx = 21              # grid points
   B = 10.0             # width (m)
   S0 = 0.001           # slope
   n = 0.025            # Manning roughness
   Q_target = 10.0      # flow (m³/s)

   # Create physical system
   system = SteadySaintVenantSystem(
       length=length, nx=nx, B=B, S0=S0, n=n, pseudo_dt=0.1
   )

   # Set boundary conditions
   h_uniform = compute_steady_uniform_flow(Q_target, B, S0, n)
   system.set_boundary_conditions(
       Q_upstream=Q_target,
       h_upstream=h_uniform,
       h_downstream=h_uniform * 1.1
   )

   # Prepare initial values
   h_init = np.ones(nx) * h_uniform
   Q_init = np.ones(nx) * Q_target
   U_init = system.pack_state(h_init, Q_init)
   system.U_prev = U_init.copy()

   # Solve
   solver = NewtonSolver(max_iter=20, tol_residual=1e-6, verbose=True)
   U_solution, info = solver.solve(
       U_init=U_init,
       residual_func=system.compute_residual,
       jacobian_func=system.compute_jacobian
   )

   # Extract results
   h_solution, Q_solution = system.unpack_state(U_solution)
   print(f"Converged: {info['converged']}")
   print(f"Iterations: {info['iterations']}")

Run it:

.. code-block:: bash

   python my_first_canal.py

Expected output::

   Newton solver: iteration 1, residual: 1.23e-02
   Newton solver: iteration 2, residual: 2.45e-04
   Newton solver: iteration 3, residual: 3.67e-08
   ✓ Newton converged
   Converged: True
   Iterations: 3

Using YAML Configuration
-------------------------

Instead of writing Python code, use YAML configuration:

``config/my_system.yaml``:

.. code-block:: yaml

   name: Simple Canal System
   canals:
     - id: main_canal
       length: 1000.0
       nx: 21
       width: 10.0
       slope: 0.001
       roughness: 0.025
       initial_depth: 2.0
       initial_flow: 10.0

   simulation:
     duration: 3600
     timestep: 10
     solver: implicit

Load and use it:

.. code-block:: python

   from core.config import SystemConfig

   config = SystemConfig.from_yaml('config/my_system.yaml')
   errors = config.validate()
   if errors:
       print("Configuration errors:", errors)
   else:
       print("✓ Configuration valid")

Choosing a Solver
-----------------

**Newton Direct** (fast, good initial values)

.. code-block:: python

   from solvers.newton_solver import NewtonSolver
   solver = NewtonSolver(max_iter=20, linear_solver='direct')

**Continuation** (robust, poor initial values)

.. code-block:: python

   from solvers.continuation_solver import ContinuationSolver
   solver = ContinuationSolver(system, [10.0, 1.0, 0.1])

**Hybrid** (automatic, best overall)

.. code-block:: python

   from solvers.hybrid_solver_enhanced import HybridSolverEnhanced
   solver = HybridSolverEnhanced()

Next Steps
----------

* Read the full tutorial: :doc:`tutorial`
* Explore examples in ``examples/``
* Check out YAML configs in ``config/``
* Run benchmarks: ``hydroclaude-benchmark --quick``
