# HydroClaude Accuracy Verification

## Grid Convergence Testing

Grid convergence tests verify that numerical error decreases at the expected rate as the mesh is refined.

**Methodology:**
1. Run the same problem on grids with decreasing dx (e.g., dx, dx/2, dx/4, dx/8).
2. Compute L1 and L2 error norms against the analytical solution.
3. Calculate the convergence order: `p = log(E1/E2) / log(dx1/dx2)`.
4. Verify that the observed order matches the theoretical order of the scheme (first-order for Godunov, second-order for MUSCL/WENO).

## Analytical Benchmarks

### Manning Uniform Flow
- Compute normal depth from Manning's equation for a rectangular channel.
- Compare solver steady-state output against the analytical depth.
- Expected error: < 0.01%.

### Stoker Dam-Break (Ritter Solution)
- Instantaneous dam-break in a frictionless rectangular channel.
- Compare water depth and velocity profiles at a given time against the Ritter analytical solution.
- L2 error should converge at second order with grid refinement.

### M1 Backwater Curve
- Subcritical flow with downstream depth greater than normal depth.
- Compare computed water surface profile against ODE-integrated analytical profile.

### Critical Depth
- Verify Froude number = 1.0 at critical sections.
- Validate specific energy minimization.

### Mass and Energy Conservation
- Check that total mass is conserved to machine precision over the simulation.
- Verify energy balance across structures (weirs, gates, orifices).

## Test Coverage

- **Gate/structure tests**: 127 tests covering sluice gates, broad-crested weirs, orifices, pumps, and turbines under various flow conditions.
- **Boundary condition tests**: 82 tests covering upstream/downstream BCs, internal boundaries, and reflective walls.

## Running the Tests

```bash
pytest tests/backend/test_convergence_order.py tests/backend/test_analytical_benchmarks.py -v
```

For the full accuracy test suite including structures and boundary conditions:

```bash
pytest tests/backend/ -v -k "convergence or analytical or gate or boundary"
```
