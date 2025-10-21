# Example 01: Canal Flow - Code Directory

## Overview

This directory contains the core example codes for canal flow simulation using Saint-Venant equations. All examples use the refactored base library modules for consistency and maintainability.

## Core Examples

### 01_basic.py
**Purpose**: Basic canal flow simulation using refactored libraries
**Features**:
- Demonstrates the simplest usage of `CanalSolver`
- Uses Preissmann implicit scheme
- Shows stability evaluation and visualization
- ~100 lines of clean code (vs ~500 lines before refactoring)

**Usage**:
```bash
python 01_basic.py
```

**Outputs**: Figures and evaluation results in `../figures/`

---

### 02_methods_comparison.py
**Purpose**: Comparison of three numerical methods
**Features**:
- EXPLICIT (mixed upwind-central difference)
- PREISSMANN (4-point implicit scheme)
- HLL (Riemann solver)
- Side-by-side comparison of accuracy and stability

**Usage**:
```bash
python 02_methods_comparison.py
```

**Outputs**:
- `example_01_methods_comparison.png` - Spatial distribution comparison
- Stability metrics for each method

---

### 03_idz_identification.py
**Purpose**: IDZ transfer function parameter identification
**Features**:
- 4-direction transfer function identification
- Step response curve fitting
- K, τ, T parameter estimation
- Validation plots

**Model**: G(s) = K × exp(-τs) / (Ts + 1)

**Usage**:
```bash
python 03_idz_identification.py
```

**Outputs**:
- `example_01_idz_*.png` - IDZ identification results for all 4 directions
- Parameter estimation tables

---

### 04_boundary_conditions.py
**Purpose**: Study of different downstream boundary conditions
**Features**:
- High water level (backwater effect from gates/reservoirs)
- Normal uniform flow (ideal free outflow)
- Low water level (pumping stations)
- Convergence-monitored steady-state initialization
- Flow step response analysis (Q: 8.0 → 10.0 m³/s)

**Key Innovation**: Ensures true steady-state before unsteady simulation

**Usage**:
```bash
python 04_boundary_conditions.py
```

**Outputs**:
- `example_01_boundary_converged_timeseries.png` - Time evolution
- `example_01_boundary_converged_spatial.png` - Spatial profiles
- Mass conservation errors < 0.1%

---

### 05_step_response.py
**Purpose**: Step response analysis and comparison
**Features**:
- Upstream flow step change
- Downstream water level response
- Transient behavior analysis
- Method comparison

**Usage**:
```bash
python 05_step_response.py
```

**Outputs**: Step response figures and analysis

---

### 06_animation.py
**Purpose**: Generate GIF animations for visualization
**Features**:
- Spatiotemporal evolution animation
- Multiple methods side-by-side
- Improved version with oscillation suppression
- High spatial resolution (nx=201)

**Usage**:
```bash
python 06_animation.py
```

**Outputs**: `*.gif` animation files in `../figures/`

---

## Archived Files

The `_deprecated/` directory contains:
- Legacy code versions (various `*_fixed.py`, `*_stable.py` files)
- Development iterations and test files
- Diagnostic tools and temporary scripts

These files are preserved for reference but should not be used for new work.

---

## Quick Start

Run all examples in sequence:
```bash
python 01_basic.py
python 02_methods_comparison.py
python 03_idz_identification.py
python 04_boundary_conditions.py
python 05_step_response.py
python 06_animation.py
```

## Dependencies

All examples require the HydroClaude base library modules:
- `solvers/canal_solver.py` - Unified canal solver
- `utils/canal_utils.py` - Utility functions
- `visualization/canal_visualizer.py` - Visualization tools
- `analysis/idz_identifier.py` - IDZ parameter identification
- `analysis/stability_evaluator.py` - Stability assessment

## Performance Notes

- `01_basic.py`: ~10 seconds
- `02_methods_comparison.py`: ~30 seconds
- `03_idz_identification.py`: ~60 seconds
- `04_boundary_conditions.py`: ~5 minutes (due to convergence monitoring)
- `05_step_response.py`: ~20 seconds
- `06_animation.py`: ~2 minutes

---

**Last Updated**: 2025-10-21
**Refactoring**: Complete modularization with 80% code reduction
