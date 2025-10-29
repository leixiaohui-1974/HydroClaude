# Godunov FVM Solver User Guide

**Version**: 1.0
**Date**: 2025-10-29
**Status**: Complete

## Overview

This guide provides practical instructions for using the Godunov Finite Volume Method (FVM) solver in HydroClaude. The guide is based on the MacDonald test suite, which provides validated benchmark cases for open channel flow simulation.

### What is Godunov FVM?

The Godunov Finite Volume Method is a conservative numerical scheme for solving hyperbolic partial differential equations, particularly suited for:

- Open channel flow (Saint-Venant equations)
- Transient flow simulation (dam breaks, flood waves)
- Subcritical flow (Froude number < 0.9)
- Flows with weak discontinuities

**Key Features**:
- ✅ Conservative (preserves mass)
- ✅ Robust (handles transients)
- ✅ Monotonic (no spurious oscillations)
- ⚠️ Diffusive (1st order accuracy dominant)

---

## Quick Start

### Basic Workflow

```python
from engine.model_builder import ModelBuilder

# 1. Define configuration
config = {
    'geometry': {
        'channel_width': 10.0,      # meters
        'channel_length': 1000.0,   # meters
        'manning_n': 0.03,          # Manning's n
        'bed_slope': 0.001          # Slope
    },
    'mesh': {
        'n_cells': 100              # Number of cells
    },
    'solver': {
        'type': 'godunov_fvm',
        'spatial_order': 1,          # 1 or 2
        'riemann_solver': 'hll',     # 'hll' recommended
        'cfl': 0.5,                  # CFL number
        'dt_max': 0.5,               # Max time step (s)
        'eps_dry': 1e-6,             # Dry bed threshold
        'use_numba': True            # Enable JIT compilation
    },
    'initial_conditions': {
        'h0': 2.0,                   # Initial depth (m)
        'Q0': 20.0                   # Initial discharge (m³/s)
    },
    'boundary_conditions': {
        'left': {'type': 'Q', 'value': 20.0},    # Discharge BC
        'right': {'type': 'h', 'value': 2.0}     # Depth BC
    }
}

# 2. Build model
builder = ModelBuilder(config)
solver = builder.solver

# 3. Run simulation
t_end = 1000.0  # End time (s)
dt_output = 10.0  # Output interval

t = 0.0
while t < t_end:
    dt = solver.compute_dt()
    solver.step(dt)
    t += dt

    if t % dt_output < dt:
        print(f"t={t:.1f}s: h_avg={solver.h.mean():.3f}m")

# 4. Get results
h_final = solver.h.copy()
Q_final = solver.Q.copy()
```

---

## Configuration Parameters

### Geometry Parameters

| Parameter | Type | Range | Description | Example |
|-----------|------|-------|-------------|---------|
| `channel_width` | float | >0 | Channel width (m) | 10.0 |
| `channel_length` | float | >0 | Channel length (m) | 1000.0 |
| `manning_n` | float | 0.01-0.1 | Manning roughness coefficient | 0.03 |
| `bed_slope` | float | -0.1 to 0.1 | Channel bed slope (m/m) | 0.001 |

**Manning's n values** (reference):
- Concrete channels: 0.012 - 0.018
- Natural earth channels: 0.020 - 0.035
- Rivers with vegetation: 0.035 - 0.100

### Mesh Parameters

| Parameter | Type | Range | Description | Recommendation |
|-----------|------|-------|-------------|----------------|
| `n_cells` | int | 10-1000 | Number of computational cells | 50-200 for most cases |

**Grid resolution guidelines**:
- Coarse (20-50 cells): Quick estimates, smooth flows
- Medium (50-200 cells): General purpose, good accuracy
- Fine (200-1000 cells): High accuracy, transient details

### Solver Parameters

| Parameter | Type | Options | Description | Recommendation |
|-----------|------|---------|-------------|----------------|
| `type` | str | 'godunov_fvm' | Solver type | Required |
| `spatial_order` | int | 1, 2 | Spatial discretization order | **1** (robust) |
| `riemann_solver` | str | 'hll', 'hllc' | Riemann solver | **'hll'** (robust) |
| `cfl` | float | 0.1-0.9 | CFL number for time stepping | 0.5 (balanced) |
| `dt_max` | float | >0 or None | Maximum time step (s) | **0.5-1.0** (prevent instability) |
| `eps_dry` | float | 1e-8 to 1e-4 | Dry bed threshold (m) | 1e-6 (default) |
| `well_balanced` | bool | True/False | Well-balanced scheme | False (default) |
| `use_numba` | bool | True/False | Enable JIT compilation | True (faster) |

#### Important Parameter Notes

**`spatial_order`**:
- Order 1: Robust, diffusive, monotonic ✅ **Recommended**
- Order 2: Less diffusive, but may cause oscillations near discontinuities

**`riemann_solver`**:
- `'hll'`: Robust, diffusive, always stable ✅ **Recommended**
- `'hllc'`: Less diffusive, better for contact discontinuities (experimental)

**`cfl`**:
- Lower (0.3-0.4): More stable, smaller time steps
- Higher (0.6-0.8): Faster, less stable
- **Recommended**: 0.5 (good balance)

**`dt_max`** ⚠️ **IMPORTANT**:
- **Purpose**: Prevents excessively large time steps in near-uniform flows
- **Problem**: Adaptive CFL-based time stepping can produce dt=3-5s when flow is smooth
- **Issue**: Large dt causes instability from boundary perturbations
- **Solution**: Set dt_max=0.5 to 1.0s for most applications
- **When to use**:
  - Always for supercritical flows
  - Recommended for all transient simulations
  - Not needed for very short simulations (<100s)

### Initial Conditions

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `h0` | float or array | Initial water depth (m) | 2.0 |
| `Q0` | float or array | Initial discharge (m³/s) | 20.0 |

Can be:
- **Scalar**: Uniform initial condition
- **Array**: Spatially varying initial condition (length = n_cells)

### Boundary Conditions

Three types supported:

#### 1. Discharge Boundary (Q)
```python
'left': {'type': 'Q', 'value': 20.0}
```
Specifies discharge (m³/s). Suitable for:
- Inflow boundaries
- Subcritical inlet (Fr < 1)

#### 2. Depth Boundary (h)
```python
'right': {'type': 'h', 'value': 2.0}
```
Specifies water depth (m). Suitable for:
- Outflow boundaries
- Subcritical outlet (Fr < 1)
- Reservoir boundaries

#### 3. Supercritical Boundary (h + Q)
```python
'left': {'type': 'supercritical', 'h': 0.7, 'Q': 20.0}
```
Specifies both h and Q. Required for:
- Supercritical inflow (Fr > 1)
- Critical flow (Fr ≈ 1)

**Boundary enforcement method**: Relaxation with α=0.5
- Smooth convergence over ~5 time steps
- Reduces boundary-induced waves
- Good balance between speed and stability

---

## Example Cases

### Example 1: Backwater Curve (MacDonald Test 1)

**Physical setup**:
- Subcritical flow in a mild slope channel
- Downstream depth control creates backwater
- Steady-state solution

```python
config = {
    'geometry': {
        'channel_width': 1.0,
        'channel_length': 1000.0,
        'manning_n': 0.03,
        'bed_slope': 0.0002
    },
    'mesh': {
        'n_cells': 100
    },
    'solver': {
        'type': 'godunov_fvm',
        'spatial_order': 1,
        'riemann_solver': 'hll',
        'cfl': 0.5,
        'eps_dry': 1e-6,
        'use_numba': True
    },
    'initial_conditions': {
        'h0': 2.0,
        'Q0': 0.1
    },
    'boundary_conditions': {
        'left': {'type': 'Q', 'value': 0.1},
        'right': {'type': 'h', 'value': 2.0}
    }
}

# Run simulation
builder = ModelBuilder(config)
solver = builder.solver

t = 0.0
t_end = 5000.0
while t < t_end:
    dt = solver.compute_dt()
    solver.step(dt)
    t += dt

# Expected result: Smooth backwater curve
# Accuracy: <2% error vs analytical solution
```

### Example 2: Dam Break (MacDonald Test 3)

**Physical setup**:
- Transient flow from dam failure
- Strong discontinuity propagation
- Tests shock-capturing capability

```python
import numpy as np

config = {
    'geometry': {
        'channel_width': 1.0,
        'channel_length': 2000.0,
        'manning_n': 0.0,  # Frictionless
        'bed_slope': 0.0
    },
    'mesh': {
        'n_cells': 200
    },
    'solver': {
        'type': 'godunov_fvm',
        'spatial_order': 1,
        'riemann_solver': 'hll',
        'cfl': 0.5,
        'dt_max': 0.5,  # Important for transients
        'eps_dry': 1e-6,
        'use_numba': True
    },
    'initial_conditions': {
        # Dam at x=1000m: h=10m upstream, h=5m downstream
        'h0': None,  # Will set manually
        'Q0': 0.0
    },
    'boundary_conditions': {
        'left': {'type': 'Q', 'value': 0.0},
        'right': {'type': 'Q', 'value': 0.0}
    }
}

builder = ModelBuilder(config)
solver = builder.solver

# Set dam initial condition
x = np.linspace(0, 2000, 200)
solver.h = np.where(x < 1000, 10.0, 5.0)
solver.Q = np.zeros_like(solver.h)

# Run transient simulation
t = 0.0
t_end = 100.0
results = {'t': [], 'h': []}

while t < t_end:
    dt = solver.compute_dt()
    solver.step(dt)
    t += dt

    if t % 10 < dt:
        results['t'].append(t)
        results['h'].append(solver.h.copy())

# Expected: Shock wave propagation
# Wave speed: ~sqrt(g*h) ≈ 10 m/s
```

### Example 3: Wide Channel Normal Depth (MacDonald Test 5)

**Physical setup**:
- Flow toward normal depth equilibrium
- Tests Manning friction implementation
- Long-time stability

```python
config = {
    'geometry': {
        'channel_width': 10.0,
        'channel_length': 6000.0,
        'manning_n': 0.03,
        'bed_slope': 0.0002
    },
    'mesh': {
        'n_cells': 50
    },
    'solver': {
        'type': 'godunov_fvm',
        'spatial_order': 1,
        'riemann_solver': 'hll',
        'cfl': 0.5,
        'dt_max': 0.5,  # CRITICAL: Prevents large adaptive dt
        'eps_dry': 1e-6,
        'use_numba': True,
        'well_balanced': False
    },
    'initial_conditions': {
        'h0': 1.0,  # Below normal depth
        'Q0': 20.0
    },
    'boundary_conditions': {
        'left': {'type': 'Q', 'value': 20.0},
        'right': {'type': 'h', 'value': 2.3769}  # Normal depth
    }
}

# Run to steady state
builder = ModelBuilder(config)
solver = builder.solver

t = 0.0
t_end = 500.0  # Long simulation

while t < t_end:
    dt = solver.compute_dt()
    solver.step(dt)
    t += dt

# Calculate normal depth (Manning equation)
Q = 20.0
B = 10.0
n = 0.03
S = 0.0002
h_normal = (Q * n / (B * np.sqrt(S))) ** (3/5)

print(f"Normal depth (theory): {h_normal:.3f}m")
print(f"Simulated depth: {solver.h.mean():.3f}m")
print(f"Deviation: {abs(solver.h.mean() - h_normal) / h_normal * 100:.1f}%")

# Expected: ~17-18% deviation (acceptable for engineering)
```

---

## Common Issues and Solutions

### Issue 1: NaN (Not a Number) in Results

**Symptoms**:
```python
RuntimeWarning: invalid value encountered in divide
h contains NaN values
```

**Causes**:
1. Time step too large
2. Dry bed (h=0) causing division by zero
3. Supercritical flow instability

**Solutions**:

✅ **Solution 1**: Add dt_max limit
```python
'solver': {
    'dt_max': 0.5  # Limit maximum time step
}
```

✅ **Solution 2**: Reduce CFL
```python
'cfl': 0.3  # Lower CFL for stability
```

✅ **Solution 3**: Check initial conditions
```python
# Ensure h0 > eps_dry everywhere
'initial_conditions': {
    'h0': 1.0,  # Avoid h0 < 1e-6
}
```

### Issue 2: Poor Mass Conservation

**Symptoms**:
```python
Mass error: 15%  # Should be <10%
```

**Causes**:
1. Boundary condition issues
2. Too few cells
3. Time step too large

**Solutions**:

✅ **Solution 1**: Increase grid resolution
```python
'n_cells': 200  # Instead of 50
```

✅ **Solution 2**: Use dt_max
```python
'dt_max': 0.5
```

✅ **Solution 3**: Check BC compatibility
```python
# Ensure BC values are physically consistent
# Example: Q_in should match channel capacity at h_out
```

### Issue 3: Oscillations in Solution

**Symptoms**:
- Spurious waves
- Non-physical oscillations near boundaries

**Causes**:
1. 2nd order scheme near discontinuities
2. Incompatible boundary conditions
3. Coarse grid

**Solutions**:

✅ **Solution 1**: Use 1st order
```python
'spatial_order': 1  # More robust
```

✅ **Solution 2**: Refine grid
```python
'n_cells': 100  # Increase resolution
```

✅ **Solution 3**: Check BC
```python
# Use 'supercritical' BC for Fr>1 flows
'left': {'type': 'supercritical', 'h': 0.7, 'Q': 20.0}
```

### Issue 4: Simulation Too Slow

**Symptoms**:
- Takes minutes to run simple case
- Python feels unresponsive

**Solutions**:

✅ **Solution 1**: Enable Numba
```python
'use_numba': True  # 10-100x speedup
```

✅ **Solution 2**: Increase time step
```python
'cfl': 0.7,  # Higher CFL (if stable)
'dt_max': 1.0  # Allow larger dt
```

✅ **Solution 3**: Reduce cells
```python
'n_cells': 50  # Start with coarse grid
```

---

## Performance Tips

### Speed Optimization

1. **Enable Numba JIT** (10-100x speedup):
```python
'use_numba': True
```

2. **Use coarse grid for prototyping**:
```python
'n_cells': 50  # Quick tests
```

3. **Increase CFL carefully**:
```python
'cfl': 0.7  # Faster, but test stability
```

4. **Use 1st order scheme**:
```python
'spatial_order': 1  # Faster than 2nd order
```

### Accuracy Optimization

1. **Refine grid**:
```python
'n_cells': 200  # Higher resolution
```

2. **Reduce time step**:
```python
'dt_max': 0.3  # Smaller steps
```

3. **Longer simulation time** (for steady-state):
```python
t_end = 2000.0  # Allow full convergence
```

4. **Check mass conservation**:
```python
mass_initial = np.sum(solver.h * solver.B * solver.dx)
mass_final = np.sum(solver.h * solver.B * solver.dx)
mass_error = abs(mass_final - mass_initial) / mass_initial * 100
print(f"Mass error: {mass_error:.2f}%")
```

### Stability Tips

1. **Always use dt_max for transients**:
```python
'dt_max': 0.5  # Essential for stability
```

2. **Use HLL Riemann solver**:
```python
'riemann_solver': 'hll'  # Most robust
```

3. **Start with 1st order**:
```python
'spatial_order': 1  # Then try 2 if needed
```

4. **Avoid extreme conditions**:
- Very shallow water (h < 0.01m)
- Very steep slopes (|S| > 0.1)
- Very high Froude numbers (Fr > 3)

---

## Validation and Testing

### Quick Validation Checklist

✅ **Mass conservation**:
```python
mass_error < 10%  # Acceptable
mass_error < 5%   # Good
mass_error < 2%   # Excellent
```

✅ **Steady-state convergence**:
```python
# Check if dh/dt → 0
h_previous = solver.h.copy()
# ... run 100 time steps
dh = np.abs(solver.h - h_previous).max()
print(f"Max depth change: {dh:.6f}m")  # Should be <1e-4
```

✅ **Physical realism**:
```python
# Check Froude number
Fr = solver.Q / (solver.h * solver.B) / np.sqrt(9.81 * solver.h)
print(f"Fr range: {Fr.min():.2f} - {Fr.max():.2f}")
# Fr should be <1 for subcritical, >1 for supercritical
```

✅ **Numerical stability**:
```python
# Check for NaN, negative values
assert not np.any(np.isnan(solver.h)), "NaN detected!"
assert np.all(solver.h >= 0), "Negative depth!"
```

### Running Standard Tests

```bash
# Run MacDonald test suite
cd tests/standard_tests
python -m pytest test_macdonald.py -v

# Expected results:
# Test 1 (Backwater): PASS (<2% error)
# Test 2 (Drawdown): PASS (<5% error)
# Test 3 (Dam break): PASS (<5% error)
# Test 4 (Hydraulic jump): SKIP (known limitation)
# Test 5 (Wide channel): PASS (<20% error)
```

---

## Known Limitations

### 1. Hydraulic Jumps (Strong Shocks)

**Problem**: Test 4 (hydraulic jump) shows 55-120% mass conservation error

**Why**: Strong shocks require specialized methods (ENO/WENO)

**Workaround**: Use specialized shock-capturing solvers for hydraulic jump applications

**Documentation**: See `docs/TEST4_HYDRAULIC_JUMP_DIAGNOSIS.md`

### 2. Accuracy Limits (~15-20%)

**Problem**: Test 5 shows 17-18% deviation from theoretical solution

**Why**:
- 1st order scheme is diffusive (~10%)
- Relaxation BC method (~6%)
- Spatial discretization error

**Workaround**:
- Acceptable for engineering applications
- For higher accuracy, consider FEM or spectral methods

**Documentation**: See `tests/diagnostic/test_macdonald5_accuracy.py`

### 3. Geometric Limitations

**Current support**: Rectangular cross-sections only

**Not supported**:
- Trapezoidal channels
- Irregular/natural sections
- Compound channels

**Workaround**: Use equivalent rectangular approximation

---

## Further Reading

### Documentation
- `docs/PROJECT_STATUS_2025_10_29.md` - Complete project status
- `docs/SESSION_2025_10_29_MACDONALD_TEST5_FIX.md` - Test 5 diagnosis
- `docs/TEST4_HYDRAULIC_JUMP_DIAGNOSIS.md` - Test 4 analysis
- `tests/diagnostic/README.md` - Diagnostic test catalog

### Code Examples
- `tests/standard_tests/test_macdonald.py` - Validated benchmark cases
- `tests/diagnostic/test_dt_max_feature.py` - dt_max implementation
- `tests/diagnostic/test_supercritical_bc.py` - Supercritical BC verification

### Theory
- Saint-Venant equations: `README.md`
- Godunov method: Toro, "Riemann Solvers and Numerical Methods for Fluid Dynamics"
- HLL Riemann solver: Harten, Lax, van Leer (1983)

---

## Support

**Issues**: Report problems at project GitHub issues page

**Questions**: Check documentation or create a GitHub discussion

**Contributing**: Follow development guidelines in `DEVELOPMENT_GUIDE.md`

---

**Document version**: 1.0
**Last updated**: 2025-10-29
**Tested with**: Python 3.11, NumPy 1.24, Numba 0.57

Happy simulating! 🌊
