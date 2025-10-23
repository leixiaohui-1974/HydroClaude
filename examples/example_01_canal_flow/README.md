# Example 01: Open Channel Unsteady Flow (明渠非恒定流)

## Overview

This example demonstrates the numerical simulation of unsteady flow in open channels using the Saint-Venant equations. It showcases three different numerical methods and comprehensive analysis techniques.

**Physical Principles:** Open channel flow governed by continuity and momentum equations (Saint-Venant equations)

**Application Scenarios:**
- Irrigation canals
- Drainage systems
- Flood control in rivers
- Water level forecasting

---

## Directory Structure

```
example_01_canal_flow/
├── code/               # Core example scripts
│   ├── 01_basic.py
│   ├── 02_methods_comparison.py
│   ├── 03_idz_identification.py
│   ├── 04_boundary_conditions.py
│   ├── 05_step_response.py
│   └── 06_animation.py
├── archive/            # Archived examples
│   ├── example_01_canal_deep_analysis_v2.py
│   ├── example_01_sluice_gate_flow.py
│   ├── example_02_advanced_structures.py
│   └── ... (3 more files)
├── tests/              # Test and diagnostic scripts
│   ├── test_convergence_visual.py
│   ├── test_performance_comparison.py
│   └── ... (7 more files)
├── docs/               # Documentation
│   └── ... (various MD files)
├── results/            # **ALL OUTPUTS (UNIFIED)**
│   ├── figures/        # PNG figures (8 files)
│   ├── animations/     # GIF animations (4 files)
│   ├── reports/        # Documentation and execution logs
│   └── tables/         # Data tables
├── run_all_unified.sh  # Master execution script
└── README.md           # This file
```

---

## Core Scripts

### 01 - Basic Simulation (`01_basic.py`)

**Purpose:** Basic canal flow simulation using the refactored library framework

**Features:**
- Demonstrates the simplest usage of `CanalSolver`
- Uses Preissmann implicit scheme
- Includes stability evaluation and visualization
- Clean code (~100 lines vs ~500 lines before refactoring)

**Usage:**
```bash
python code/01_basic.py
```

**Outputs:**
- `example_01_refactored_comparison.png` - Methods comparison
- `example_01_refactored_explicit.png` - Explicit method results
- `example_01_refactored_preissmann.png` - Preissmann method results
- `example_01_refactored_hll.png` - HLL method results

---

### 02 - Methods Comparison (`02_methods_comparison.py`)

**Purpose:** Systematic comparison of three numerical methods

**Methods Tested:**
- **EXPLICIT**: Mixed upwind-central finite difference
- **PREISSMANN**: 4-point implicit scheme
- **HLL**: Harten-Lax-van Leer Riemann solver

**Features:**
- Standard physical parameters and boundary conditions
- Side-by-side accuracy and stability comparison
- Performance metrics (computation time, convergence)

**Usage:**
```bash
python code/02_methods_comparison.py
```

**Outputs:**
- Spatial distribution comparison
- Temporal evolution comparison
- Performance comparison charts
- Overlay comparison plots

---

### 03 - IDZ Parameter Identification (`03_idz_identification.py`)

**Purpose:** Identify IDZ transfer function parameters from step response data

**IDZ Model:**
```
G(s) = K × exp(-τs) / (Ts + 1)

Where:
  K: Steady-state gain
  τ: Time delay (seconds)
  T: Time constant (seconds)
```

**Features:**
- 4-direction transfer function identification:
  1. Upstream discharge → Downstream depth
  2. Downstream depth → Upstream depth
  3. Upstream discharge → Downstream discharge
  4. Downstream depth → Upstream discharge
- Step response curve fitting
- Parameter estimation and validation plots

**Usage:**
```bash
python code/03_idz_identification.py
```

**Outputs:**
- IDZ identification plots for each direction
- Parameter estimation tables
- Fit quality metrics (R² values)

---

### 04 - Boundary Conditions (`04_boundary_conditions.py`)

**Purpose:** Study of different downstream boundary conditions

**Boundary Conditions Tested:**
- High water level (backwater effect from gates/reservoirs)
- Normal uniform flow (ideal free outflow)
- Low water level (pumping stations)

**Key Innovation:**
- Convergence-monitored steady-state initialization
- Ensures true steady state before unsteady simulation
- Flow step response analysis (Q: 8.0 → 10.0 m³/s)

**Usage:**
```bash
python code/04_boundary_conditions.py
```

**Outputs:**
- Time evolution plots
- Spatial profile plots
- Mass conservation error analysis (< 0.1%)

---

### 05 - Step Response (`05_step_response.py`)

**Purpose:** Step response analysis and comparison

**Features:**
- Upstream flow step change simulation
- Downstream water level response tracking
- Transient behavior analysis
- Multi-method comparison

**Usage:**
```bash
python code/05_step_response.py
```

**Outputs:**
- Step response comparison figures
- Transient analysis plots

---

### 06 - Animation Generation (`06_animation.py`)

**Purpose:** Generate GIF animations for visualization

**Features:**
- Spatiotemporal evolution animation
- Multiple methods side-by-side
- Improved version with oscillation suppression
- High spatial resolution (nx=201)

**Usage:**
```bash
python code/06_animation.py
```

**Outputs:**
- `canal_flow_comparison_improved.gif` - Improved animation
- `canal_flow_final_state_improved.png` - Final state plot

---

## Archive Scripts

The `archive/` directory contains valuable examples:

1. **example_01_canal_deep_analysis_v2.py** - Deep analysis with IDZ identification
2. **example_01_sluice_gate_flow.py** - Sluice gate flow dynamics
3. **example_02_advanced_structures.py** - Multiple gates and mixed structures

These scripts demonstrate advanced features and alternative implementations.

---

## Test Scripts

The `tests/` directory contains diagnostic and performance test scripts:

- `test_convergence_visual.py` - Convergence visualization
- `test_performance_comparison.py` - Performance benchmarking
- `test_anderson_vs_aitken.py` - Acceleration method comparison
- And more...

---

## Quick Start

### Run All Examples

Execute all core examples in sequence:

```bash
bash run_all_unified.sh
```

This script will:
1. Run all 6 core examples
2. Run selected archive scripts
3. Consolidate all outputs to `results/`
4. Generate execution summary

### Run Individual Examples

```bash
cd examples/example_01_canal_flow
python code/01_basic.py
python code/02_methods_comparison.py
python code/03_idz_identification.py
python code/05_step_response.py
python code/06_animation.py
```

---

## Generated Outputs

All outputs are consolidated in the `results/` directory:

### Figures (results/figures/)

- `example_01_refactored_comparison.png`
- `example_01_refactored_explicit.png`
- `example_01_refactored_preissmann.png`
- `example_01_refactored_hll.png`
- `canal_flow_final_state_improved.png`
- And more...

### Animations (results/animations/)

- `canal_flow_comparison.gif` (859 KB)
- `canal_flow_comparison_improved.gif` (1.2 MB)
- `example_01_comprehensive_animation.gif` (1.2 MB)

### Reports (results/reports/)

- Execution logs
- Summary reports
- Technical documentation

---

## Dependencies

All examples require the HydroClaude base library modules:

- `solvers/canal_solver.py` - Unified canal solver
- `utils/canal_utils.py` - Utility functions
- `visualization/canal_visualizer.py` - Visualization tools
- `analysis/idz_identifier.py` - IDZ parameter identification
- `analysis/stability_evaluator.py` - Stability assessment

### Install Dependencies

```bash
pip install -r ../../requirements.txt
```

---

## Performance Notes

Approximate execution times:

- `01_basic.py`: ~6 seconds
- `02_methods_comparison.py`: ~9 seconds
- `03_idz_identification.py`: ~18 seconds
- `04_boundary_conditions.py`: ~5 minutes (convergence monitoring)
- `05_step_response.py`: ~10 seconds
- `06_animation.py`: ~67 seconds

**Total time (run_all_unified.sh):** ~2 minutes

---

## Technical Highlights

### Numerical Methods

1. **EXPLICIT (Explicit Finite Difference)**
   - Upwind-central hybrid scheme
   - Fast computation
   - Requires small time steps for stability

2. **PREISSMANN (Implicit 4-Point Scheme)**
   - Unconditionally stable
   - Allows larger time steps
   - Requires matrix inversion

3. **HLL (Harten-Lax-van Leer)**
   - Finite volume method
   - Riemann solver
   - Robust for shock capturing

### Key Features

- **Convergence Monitoring**: Ensures true steady state before transient simulation
- **Stability Evaluation**: Comprehensive metrics (CV, mass conservation, oscillation index)
- **IDZ Identification**: Transfer function parameter estimation from step response
- **Visualization**: High-quality plots and animations (all labels in English)

---

## References

- Project documentation: `../../docs/`
- Related examples: Other examples in `examples/` directory

---

## Version History

- **2025-10-22**: Reorganized structure, unified outputs to `results/` directory
- **2025-10-21**: Refactored with base library framework (80% code reduction)
- **Earlier**: Initial development and various iterations

---

## Notes

- All visualizations use **English labels** to avoid font display issues
- Scripts are standalone and can be run independently
- Use `run_all_unified.sh` for comprehensive testing
- Archive and test scripts provide additional functionality

---

*Last Updated: 2025-10-22*
*Generated by reorganization script*
