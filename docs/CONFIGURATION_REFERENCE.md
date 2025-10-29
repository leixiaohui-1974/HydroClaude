# Configuration Reference

**Version**: 1.0
**Date**: 2025-10-29
**For**: HydroClaude Godunov FVM Solver

## Overview

This document provides complete reference for all configuration parameters used in HydroClaude simulations. Configuration can be provided as Python dictionaries or YAML files.

## Configuration Structure

```python
config = {
    'geometry': { ... },           # Channel geometry
    'mesh': { ... },               # Grid discretization
    'solver': { ... },             # Solver settings
    'initial_conditions': { ... }, # Initial state
    'boundary_conditions': { ... } # Boundary setup
}
```

---

## Geometry Section

Defines the physical channel properties.

### Parameters

#### `channel_width` (float, required)

**Description**: Width of the rectangular channel

**Units**: meters (m)

**Range**: > 0

**Default**: None (must be specified)

**Example**:
```python
'channel_width': 10.0  # 10-meter wide channel
```

**Notes**:
- Only rectangular cross-sections currently supported
- Constant width along channel length
- Wide channel approximation: typically B/h > 5

---

#### `channel_length` (float, required)

**Description**: Total length of the channel

**Units**: meters (m)

**Range**: > 0

**Default**: None (must be specified)

**Example**:
```python
'channel_length': 1000.0  # 1-kilometer channel
```

**Notes**:
- Domain extends from x=0 to x=channel_length
- Cell size dx = channel_length / n_cells

---

#### `manning_n` (float, required)

**Description**: Manning's roughness coefficient

**Units**: dimensionless (s/m^(1/3))

**Range**: 0.01 - 0.15 (typical)

**Default**: None (must be specified)

**Example**:
```python
'manning_n': 0.03  # Natural earth channel
```

**Common Values**:
| Surface Type | Range | Typical |
|--------------|-------|---------|
| Concrete (smooth) | 0.012 - 0.014 | 0.013 |
| Concrete (rough) | 0.014 - 0.018 | 0.016 |
| Asphalt | 0.013 - 0.016 | 0.014 |
| Cast iron | 0.013 - 0.017 | 0.015 |
| Corrugated metal | 0.021 - 0.030 | 0.024 |
| Earth, clean | 0.016 - 0.023 | 0.020 |
| Earth, gravelly | 0.020 - 0.030 | 0.025 |
| Earth, weedy | 0.023 - 0.035 | 0.030 |
| Natural channels | 0.025 - 0.075 | 0.035 |
| Floodplains, light brush | 0.035 - 0.070 | 0.050 |
| Floodplains, heavy brush | 0.075 - 0.150 | 0.100 |

**Notes**:
- Higher values → more friction → lower velocity
- Manning friction provides numerical stability
- Use n=0.0 for frictionless (theoretical) cases

---

#### `bed_slope` (float, required)

**Description**: Bed slope of the channel (positive = downward in flow direction)

**Units**: dimensionless (m/m or %)

**Range**: -0.1 to +0.1 (typical)

**Default**: None (must be specified)

**Example**:
```python
'bed_slope': 0.001   # 0.1% or 1:1000 slope
'bed_slope': 0.0002  # Mild slope
'bed_slope': 0.0     # Horizontal channel
```

**Classification**:
| Type | Slope Range | Description |
|------|-------------|-------------|
| Mild | 0.0001 - 0.001 | Subcritical flow typical |
| Moderate | 0.001 - 0.01 | Normal channel |
| Steep | 0.01 - 0.1 | Supercritical flow possible |
| Very steep | > 0.1 | Chutes, spillways |

**Notes**:
- Positive slope: flow in +x direction
- Zero slope: horizontal channel (only friction/BC affect flow)
- Negative slope: adverse slope (rare, special cases)

---

## Mesh Section

Defines the computational grid.

### Parameters

#### `n_cells` (int, required)

**Description**: Number of computational cells (control volumes)

**Units**: dimensionless

**Range**: 10 - 1000 (practical)

**Default**: None (must be specified)

**Example**:
```python
'n_cells': 100  # 100 cells for 1000m → dx=10m
```

**Guidelines**:

| Resolution | n_cells | Use Case | Accuracy | Speed |
|------------|---------|----------|----------|-------|
| Coarse | 20-50 | Quick tests, smooth flows | Low | Fast |
| Medium | 50-200 | General purpose | Good | Medium |
| Fine | 200-500 | High accuracy, transients | High | Slow |
| Very Fine | 500-1000 | Research, validation | Very High | Very Slow |

**Grid Convergence**:
```python
# Test grid independence
for n_cells in [50, 100, 200, 400]:
    config['mesh']['n_cells'] = n_cells
    # Run simulation and compare results
```

**Notes**:
- Cell size: dx = channel_length / n_cells
- More cells → better accuracy, slower simulation
- Diminishing returns beyond ~200 cells for most cases
- CFL condition limits time step based on dx

---

## Solver Section

Configures the numerical solver.

### Parameters

#### `type` (str, required)

**Description**: Solver type identifier

**Options**: `'godunov_fvm'`

**Default**: None (must be specified)

**Example**:
```python
'type': 'godunov_fvm'
```

**Notes**:
- Currently only Godunov FVM implemented
- Future: May add other solver types

---

#### `spatial_order` (int, required)

**Description**: Spatial discretization order

**Options**: `1`, `2`

**Default**: `1` (recommended)

**Example**:
```python
'spatial_order': 1  # First-order (robust)
'spatial_order': 2  # Second-order (less diffusive)
```

**Comparison**:

| Order | Accuracy | Diffusion | Oscillations | Stability | Use Case |
|-------|----------|-----------|--------------|-----------|----------|
| 1 | Lower | High | None | Excellent | **Recommended for production** |
| 2 | Higher | Low | Possible | Good | Research, smooth flows |

**Implementation**:
- Order 1: Godunov method (piecewise constant)
- Order 2: MUSCL reconstruction with slope limiter

**When to use Order 2**:
- Smooth flows with no shocks
- Need to resolve fine features
- After validating stability with Order 1

**When to use Order 1**:
- Transient flows with discontinuities
- First time running a case
- Stability issues with Order 2
- Production simulations

---

#### `riemann_solver` (str, required)

**Description**: Riemann solver for flux calculation

**Options**: `'hll'`, `'hllc'`

**Default**: `'hll'` (recommended)

**Example**:
```python
'riemann_solver': 'hll'   # HLL (recommended)
'riemann_solver': 'hllc'  # HLLC (experimental)
```

**Comparison**:

| Solver | Robustness | Accuracy | Diffusion | Status |
|--------|------------|----------|-----------|---------|
| HLL | Excellent | Good | Moderate | **Recommended** ✅ |
| HLLC | Good | Better | Low | Experimental ⚠️ |

**HLL (Harten-Lax-van Leer)**:
- Very robust, never fails
- Slightly diffusive
- Smears contact discontinuities
- **Use for**: All production work

**HLLC (HLL-Contact)**:
- Better resolves contact waves
- Less diffusive
- More complex
- **Use for**: Research, after HLL validation

---

#### `cfl` (float, required)

**Description**: CFL (Courant-Friedrichs-Lewy) number for time step calculation

**Units**: dimensionless

**Range**: 0.1 - 0.9

**Default**: `0.5` (recommended)

**Example**:
```python
'cfl': 0.5   # Balanced (recommended)
'cfl': 0.3   # Conservative (more stable)
'cfl': 0.7   # Aggressive (faster but less stable)
```

**Formula**:
```
dt = CFL × dx / (|u| + c)

where:
  dx = cell size
  u = flow velocity
  c = wave celerity = sqrt(g×h)
```

**Guidelines**:

| CFL | Stability | Speed | Use Case |
|-----|-----------|-------|----------|
| 0.2-0.3 | Excellent | Slow | Debugging, difficult cases |
| 0.4-0.6 | Good | Medium | **General purpose** |
| 0.7-0.8 | Moderate | Fast | Smooth flows only |
| >0.9 | Poor | Fastest | Not recommended |

**Notes**:
- Lower CFL = smaller time steps = more stable
- Higher CFL = larger time steps = faster simulation
- Stability limit: CFL ≤ 1 (theoretical)
- Practical limit: CFL ≤ 0.8 for safety

---

#### `dt_max` (float or None, optional)

**Description**: Maximum time step limit (seconds)

**Units**: seconds (s)

**Range**: > 0 or None

**Default**: `None` (no limit)

**Example**:
```python
'dt_max': 0.5   # Limit to 0.5s (recommended for transients)
'dt_max': 1.0   # Limit to 1.0s
'dt_max': None  # No limit (use with caution)
```

**Why Needed**:
- Adaptive CFL-based dt can become very large (3-5s) in near-uniform flows
- Large dt causes instability from boundary perturbations
- Dry beds can occur → numerical explosion

**Critical for**:
- ✅ Supercritical flows (always set dt_max)
- ✅ Transient simulations
- ✅ Long simulations (>500s)
- ⚠️ Short simulations (<100s) may not need

**Recommended Values**:

| Scenario | dt_max | Rationale |
|----------|--------|-----------|
| Supercritical flow | 0.3 - 0.5 | Very sensitive |
| Transient flow | 0.5 - 1.0 | Capture dynamics |
| Steady flow | 1.0 - 2.0 | Allow convergence |
| Short test (<100s) | None | Not critical |

**Example from MacDonald Test 5**:
```python
# Without dt_max: NaN at t=100s (dt grew to 3.31s)
# With dt_max=0.5: Stable for 1000s
'dt_max': 0.5  # Essential fix
```

---

#### `eps_dry` (float, optional)

**Description**: Dry bed threshold - minimum water depth

**Units**: meters (m)

**Range**: 1e-8 to 1e-4

**Default**: `1e-6`

**Example**:
```python
'eps_dry': 1e-6  # Default (recommended)
'eps_dry': 1e-4  # More robust for very shallow flows
```

**Purpose**:
- Prevent division by zero when h → 0
- Define "dry" vs "wet" cells
- Numerical stability near dry beds

**Effects**:
- Smaller eps_dry: More accurate for shallow water, less stable
- Larger eps_dry: More stable, less accurate

**Notes**:
- Cells with h < eps_dry treated as dry
- Typically don't need to change default
- Increase if getting NaN near dry beds

---

#### `well_balanced` (bool, optional)

**Description**: Enable well-balanced scheme for still water

**Options**: `True`, `False`

**Default**: `False`

**Example**:
```python
'well_balanced': False  # Default
'well_balanced': True   # For lake-at-rest problems
```

**When to use**:
- `False` (default): General flows, transients
- `True`: Still water, lake-at-rest, very small perturbations

**Notes**:
- Well-balanced: Exactly preserves h+z=constant
- Not needed for most applications
- Slight performance penalty when enabled

---

#### `use_numba` (bool, optional)

**Description**: Enable Numba JIT compilation for performance

**Options**: `True`, `False`

**Default**: `True` (recommended)

**Example**:
```python
'use_numba': True   # Fast (recommended)
'use_numba': False  # Slow (debugging only)
```

**Performance Impact**:

| State | Speed | First Run | Debugging |
|-------|-------|-----------|-----------|
| True | 10-100× faster | Slow (compile) | Harder |
| False | Baseline | Fast | Easy |

**When to disable**:
- Debugging numerical issues
- Profiling code
- First-time testing

**Notes**:
- First run with Numba=True is slow (compiles functions)
- Subsequent runs are very fast
- Production simulations: always use True

---

## Initial Conditions Section

Defines the initial state of the flow.

### Parameters

#### `h0` (float or array, required)

**Description**: Initial water depth

**Units**: meters (m)

**Type**: float (uniform) or numpy array (spatially varying)

**Range**: > eps_dry

**Default**: None (must be specified)

**Example**:
```python
# Uniform depth
'h0': 2.0

# Spatially varying
'h0': np.linspace(1.0, 2.0, n_cells)  # Linear variation

# Dam break
x = np.linspace(0, L, n_cells)
'h0': np.where(x < L/2, 10.0, 5.0)  # Step function
```

**Notes**:
- Must be array of length n_cells if not scalar
- Avoid h0 < eps_dry (causes instability)
- Consider steady-state depth for steady flows

---

#### `Q0` (float or array, required)

**Description**: Initial discharge

**Units**: cubic meters per second (m³/s)

**Type**: float (uniform) or numpy array (spatially varying)

**Range**: any (positive = forward flow)

**Default**: None (must be specified)

**Example**:
```python
# Uniform discharge
'Q0': 20.0

# Zero initial flow (dam break)
'Q0': 0.0

# Spatially varying
'Q0': np.linspace(10.0, 30.0, n_cells)
```

**Notes**:
- Positive Q = flow in +x direction
- Negative Q = reverse flow (rare)
- Q=0 for still water initial conditions

---

## Boundary Conditions Section

Defines inflow and outflow conditions.

### Structure

```python
'boundary_conditions': {
    'left': { ... },   # Inlet (x=0)
    'right': { ... }   # Outlet (x=L)
}
```

### BC Types

Three types supported:

---

#### Type 1: Discharge Boundary (`'Q'`)

**Use for**: Inflow boundaries, subcritical inlet

**Parameters**:
- `type`: `'Q'`
- `value`: discharge (m³/s)

**Example**:
```python
'left': {
    'type': 'Q',
    'value': 20.0  # 20 m³/s inflow
}
```

**Theory**:
- Specifies discharge Q
- Depth h computed from flow dynamics
- Suitable when Q is known (pump, reservoir, etc.)

**Subcritical Requirements** (Fr < 1):
- At inlet: Can specify Q (1 variable)
- At outlet: Need to specify h

---

#### Type 2: Depth Boundary (`'h'`)

**Use for**: Outflow boundaries, downstream control

**Parameters**:
- `type`: `'h'`
- `value`: water depth (m)

**Example**:
```python
'right': {
    'type': 'h',
    'value': 2.0  # 2m depth at outlet
}
```

**Theory**:
- Specifies depth h
- Discharge Q computed from flow dynamics
- Suitable for reservoir, lake, rating curve

**Common Uses**:
- Downstream reservoir
- Normal depth at outlet
- Rating curve h(Q)

---

#### Type 3: Supercritical Boundary (`'supercritical'`)

**Use for**: Supercritical inflow (Fr > 1)

**Parameters**:
- `type`: `'supercritical'`
- `h`: water depth (m)
- `Q`: discharge (m³/s)

**Example**:
```python
'left': {
    'type': 'supercritical',
    'h': 0.7,   # Shallow, fast flow
    'Q': 20.0
}
```

**Theory**:
- Supercritical flow: Fr = u/sqrt(g*h) > 1
- Information propagates downstream only
- Can specify both h AND Q (2 incoming characteristics)

**When Required**:
- Critical flow (Fr ≈ 1)
- Supercritical inlet (Fr > 1)
- Gates with high-speed discharge

**Validation**:
```python
# Check if supercritical
Fr = Q / (h * B) / np.sqrt(9.81 * h)
if Fr > 1:
    print("Supercritical: use 'supercritical' BC")
```

---

### Boundary Enforcement Method

**Relaxation with α=0.5**:

```python
h_bc_new = h_bc_old + α × (h_target - h_bc_old)
Q_bc_new = Q_bc_old + α × (Q_target - Q_bc_old)
```

**Characteristics**:
- α = 0.5: Half-step relaxation
- Smooth convergence over ~5 time steps
- Reduces boundary-induced waves
- Good balance: speed vs stability

**Effect on Results**:
- ~6% accuracy impact (inherent to method)
- More stable than direct enforcement
- Less reflections at boundaries

---

## Complete Example Configurations

### Example 1: Backwater Curve (Subcritical)

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
        'dt_max': None,  # Not critical for steady flow
        'eps_dry': 1e-6,
        'well_balanced': False,
        'use_numba': True
    },
    'initial_conditions': {
        'h0': 2.0,
        'Q0': 0.1
    },
    'boundary_conditions': {
        'left': {'type': 'Q', 'value': 0.1},   # Discharge inlet
        'right': {'type': 'h', 'value': 2.0}   # Depth outlet
    }
}
```

### Example 2: Dam Break (Transient)

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
        'dt_max': 0.5,  # IMPORTANT for transients
        'eps_dry': 1e-6,
        'well_balanced': False,
        'use_numba': True
    },
    'initial_conditions': {
        'h0': None,  # Set manually
        'Q0': 0.0
    },
    'boundary_conditions': {
        'left': {'type': 'Q', 'value': 0.0},
        'right': {'type': 'Q', 'value': 0.0}
    }
}

# Set dam initial condition after building model
builder = ModelBuilder(config)
solver = builder.solver
x = np.linspace(0, 2000, 200)
solver.h = np.where(x < 1000, 10.0, 5.0)
solver.Q = np.zeros_like(solver.h)
```

### Example 3: Supercritical Flow

```python
config = {
    'geometry': {
        'channel_width': 10.0,
        'channel_length': 2000.0,
        'manning_n': 0.03,
        'bed_slope': 0.01  # Steep slope
    },
    'mesh': {
        'n_cells': 200
    },
    'solver': {
        'type': 'godunov_fvm',
        'spatial_order': 1,
        'riemann_solver': 'hll',
        'cfl': 0.5,
        'dt_max': 0.3,  # CRITICAL for supercritical
        'eps_dry': 1e-6,
        'well_balanced': False,
        'use_numba': True
    },
    'initial_conditions': {
        'h0': 0.7,  # Shallow (supercritical)
        'Q0': 20.0
    },
    'boundary_conditions': {
        'left': {
            'type': 'supercritical',  # MUST use supercritical BC
            'h': 0.7,
            'Q': 20.0
        },
        'right': {
            'type': 'h',
            'value': 2.8  # Downstream depth
        }
    }
}
```

---

## YAML Configuration Format

Alternatively, use YAML files:

```yaml
# config.yaml
geometry:
  channel_width: 10.0
  channel_length: 1000.0
  manning_n: 0.03
  bed_slope: 0.001

mesh:
  n_cells: 100

solver:
  type: godunov_fvm
  spatial_order: 1
  riemann_solver: hll
  cfl: 0.5
  dt_max: 0.5
  eps_dry: 1.0e-6
  well_balanced: false
  use_numba: true

initial_conditions:
  h0: 1.5
  Q0: 20.0

boundary_conditions:
  left:
    type: Q
    value: 20.0
  right:
    type: h
    value: 2.0
```

**Load in Python**:
```python
import yaml

with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

builder = ModelBuilder(config)
```

---

## Configuration Validation

HydroClaude performs automatic validation:

```python
# Checks performed:
✓ All required parameters present
✓ Values within acceptable ranges
✓ Type checking (int, float, str)
✓ Physical consistency (h>0, L>0, etc.)
✓ BC compatibility with flow regime
```

**Common Validation Errors**:

1. **Missing required parameter**:
```
KeyError: 'channel_width' not found in geometry section
```

2. **Value out of range**:
```
ValueError: CFL must be between 0.1 and 0.9, got 1.5
```

3. **Type mismatch**:
```
TypeError: n_cells must be int, got float
```

4. **Physical inconsistency**:
```
ValueError: Supercritical BC required for Fr>1 flow
```

---

## Quick Reference

### Most Important Parameters

| Parameter | Typical Value | Critical? |
|-----------|---------------|-----------|
| `channel_width` | 1-100m | ✅ |
| `channel_length` | 100-10000m | ✅ |
| `manning_n` | 0.01-0.05 | ✅ |
| `bed_slope` | 0.0001-0.01 | ✅ |
| `n_cells` | 50-200 | ✅ |
| `spatial_order` | 1 | ⚠️ |
| `riemann_solver` | 'hll' | ⚠️ |
| `cfl` | 0.5 | ⚠️ |
| `dt_max` | 0.5-1.0 | ✅ Critical! |
| `use_numba` | True | 💡 Performance |

---

## Further Reading

- [Godunov FVM User Guide](GODUNOV_FVM_USER_GUIDE.md) - Complete usage guide
- [Project Status](PROJECT_STATUS_2025_10_29.md) - Current project state
- [Getting Started Notebook](../notebooks/01_getting_started.ipynb) - Interactive tutorial
- [MacDonald Tests](../tests/standard_tests/test_macdonald.py) - Validation examples

---

**Document version**: 1.0
**Last updated**: 2025-10-29
**For questions**: Open GitHub issue or discussion
