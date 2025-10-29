# Diagnostic Tests Directory

This directory contains diagnostic tests created during development to investigate specific issues, verify implementations, and explore numerical behavior. Unlike standard tests that verify correct functionality, diagnostic tests are designed to understand *why* things work or don't work.

## Test Organization

### 1. MacDonald Test Diagnostics

#### Test 2 (Drawdown) Diagnostics
- **`test_macdonald_test2_detailed_mass.py`** - Detailed mass conservation analysis
- **`test_macdonald_test2_exact_config.py`** - Exact configuration from MacDonald paper
- **`test_macdonald_test2_mass.py`** - Basic mass conservation check

**History**: Created to diagnose mass conservation issues during relaxation method implementation (2025-10-29).

#### Test 4 (Hydraulic Jump) Diagnostics
- **`test_macdonald4_diagnosis.py`** (287 lines) - Comprehensive hydraulic jump diagnosis
  - Test 1: Linear initial condition (Test 4 original config)
  - Test 2: Pre-formed jump initial condition
  - **Finding**: Supercritical BC works correctly (Fr=1.09 maintained), but mass conservation fails (55-120% error)
  - **Root cause**: Shock wave requires specialized numerical methods (ENO/WENO)
  - **Decision**: Keep Test 4 SKIPPED, documented in `docs/TEST4_HYDRAULIC_JUMP_DIAGNOSIS.md`

**Key Results**:
```
✅ Upstream supercritical maintained: Fr[0] = 1.0903
❌ Mass conservation failure: 55-120% error
❌ Supercritical region shrinks: 100 → 1 cell
⚠️  Physical incompatibility: h_downstream=2.8m vs h2_theory=0.78m (260% difference)
```

#### Test 5 (Wide Channel) Diagnostics
Created during Test 5 fix session (2025-10-29) to diagnose NaN failures.

- **`test_macdonald5_diagnosis.py`** (150 lines) - Step-by-step diagnosis
  - Step 1: No Manning friction → NaN at step 88
  - Step 2: With Manning → Stable
  - Step 3: Second order → Stable
  - **Finding**: Manning friction provides numerical stability

- **`test_macdonald5_stability.py`** (160 lines) - Stability testing
  - Progressive tests: 100s, 200s, 500s, 1000s
  - Fixed dt vs adaptive dt comparison
  - **Finding**: Fixed dt=0.5s stable, adaptive CFL=0.5 fails at step 32

- **`test_macdonald5_dt_trace.py`** (200 lines) - Time step evolution tracking
  - Detailed dt evolution trace
  - **Critical discovery**: Initial dt=3.31s causes instability
  - Failure timeline:
    ```
    Step 1-23 (76s):   dt=3.31s, stable
    Step 25 (82s):     h_min=0.06m, instability begins
    Step 26 (84s):     h_min=0.0m (dry bed), u→∞
    Step 27-32:        dt→0, h→461m, NaN
    ```

- **`test_macdonald5_dt_limit.py`** (150 lines) - dt_max verification
  - Tested dt_max: 1.0, 0.5, 0.3, 0.2
  - **Optimal**: dt_max=0.5s
  - Result: 1000 stable steps, 6.05% mass error

- **`test_macdonald5_full.py`** (180 lines) - Full configuration test
  - Complete Test 5 configuration with dt_max=0.5
  - Verification of final fix

- **`test_macdonald5_accuracy.py`** (320 lines) - Accuracy improvement exploration
  - Test 1: Longer simulation (500s → 2000s): +0.8% improvement
  - Test 2: Finer grid (50 → 400 cells): NaN failures
  - Test 3: 2nd order scheme: No improvement (worse by 1.7%)
  - Test 4: Optimal config comparison
  - **Conclusion**: Current config near optimal, 17-18% is practical limit

**Solution**: Implemented `dt_max` parameter to limit maximum time step.

### 2. Boundary Condition Diagnostics

#### Supercritical BC Tests
- **`test_supercritical_bc.py`** (118 lines) - Supercritical BC verification
  - Verifies Fr>1 maintenance
  - Tests h and Q enforcement
  - **Result**: ✅ PASSED (0.00% error)

- **`test_config_supercritical.py`** - Config-driven supercritical test
  - **Result**: ✅ PASSED (0.00% error)

- **`test_simple_supercritical.py`** - Simplified supercritical test

**Conclusion**: Supercritical BC implementation is correct.

#### General BC Tests
- **`test_boundary_enforcement.py`** - Tests Q, h, and supercritical enforcement
- **`test_boundary_cell_evolution.py`** - Ghost cell evolution tracking
- **`test_boundary_evolution.py`** - Boundary state evolution
- **`test_boundary_natural_evolution.py`** - Natural evolution without forcing
- **`test_critical_bc_fix.py`** - Critical flow boundary condition
- **`test_ghost_cell_consistency.py`** - Ghost cell consistency checks
- **`test_ghost_cells_diagnosis.py`** - Detailed ghost cell diagnosis
- **`test_h_boundary_fix_simple.py`** - Simple h boundary fix
- **`test_q_boundary.py`** - Q boundary tests (simple and with Manning)
- **`test_simple_bc_check.py`** - Basic BC verification

### 3. Mass Conservation Diagnostics

Created during relaxation method debugging to track down mass leakage sources.

- **`test_direct_mass_conservation.py`** - Direct mass calculation
- **`test_flux_conservation.py`** - Flux conservation diagnosis
- **`test_interface_flux_detail.py`** - Interface flux detailed analysis
- **`test_mass_balance_verification.py`** - Complete mass balance verification
- **`test_short_mass_conservation.py`** - Short-time mass conservation
- **`test_single_step_mass.py`** - Single time step mass tracking

### 4. Numerical Method Tests

#### Time Integration
- **`test_rk2_flux.py`** - RK2 time integration flux analysis
- **`test_strang_splitting.py`** - Strang splitting comparison

#### Spatial Discretization
- **`test_spatial_order.py`** - Spatial order comparison (1st vs 2nd)
- **`test_grid_convergence.py`** - Grid convergence study
- **`test_well_balanced_comparison.py`** - Well-balanced scheme comparison
- **`test_well_balanced_solution.py`** - Well-balanced solution verification

#### Manning Friction
- **`test_manning_friction.py`** - Manning friction tests
  - Short time test
  - First order test
  - No Numba test

### 5. Feature Implementation Tests

- **`test_dt_max_feature.py`** (100 lines) - dt_max parameter verification
  - Three scenarios: no limit, with limit, limit not active
  - **Result**: ✅ All tests passed
  - Verifies correct implementation of dt_max limiter

### 6. Convergence and Stability Tests

- **`test_long_time_convergence.py`** - Long-time convergence behavior
- **`test_static_water.py`** - Static water (no flow) stability

## Running Diagnostic Tests

### Run all diagnostic tests
```bash
python -m pytest tests/diagnostic/ -v
```

### Run specific test category
```bash
# MacDonald Test 5 diagnostics
python -m pytest tests/diagnostic/test_macdonald5*.py -v

# MacDonald Test 4 diagnostics
python -m pytest tests/diagnostic/test_macdonald4*.py -v

# Boundary condition tests
python -m pytest tests/diagnostic/test_*boundary*.py tests/diagnostic/test_*bc*.py -v

# Mass conservation tests
python -m pytest tests/diagnostic/test_*mass*.py -v
```

### Run individual diagnostic script
```bash
# Many diagnostics can be run as standalone scripts
python tests/diagnostic/test_macdonald5_diagnosis.py
python tests/diagnostic/test_macdonald4_diagnosis.py
```

## Test Status Summary

- **Total diagnostic tests**: 53
- **Status**: ✅ 53/53 passing (100%)
- **Coverage**: Boundary conditions, mass conservation, time stepping, spatial discretization

## Key Findings

### 1. Test 5 (Wide Channel) - FIXED ✅
- **Problem**: NaN failures at ~100s
- **Root cause**: Adaptive time step dt=3.31s too large (6.6× stable value)
- **Solution**: Implemented dt_max=0.5s parameter
- **Result**: Test passes with 17.6% deviation, 6.1% mass error

### 2. Test 4 (Hydraulic Jump) - SKIPPED ⏭️
- **Problem**: Mass conservation failure (55-120% error)
- **Root cause**: Shock wave requires specialized methods (ENO/WENO)
- **Status**: Supercritical BC verified correct, but shock treatment inadequate
- **Decision**: Document limitation, keep SKIPPED

### 3. Boundary Conditions - VERIFIED ✅
- All BC types (Q, h, supercritical) verified working correctly
- Relaxation method (α=0.5) successfully implemented
- Mass conservation within acceptable limits for stable flows

### 4. Numerical Methods - VALIDATED ✅
- Godunov FVM + HLL Riemann solver: Robust for smooth/weak discontinuities
- MUSCL reconstruction: Working correctly
- Manning friction: Provides numerical stability
- dt_max limiter: Essential for stability with adaptive time stepping

## Historical Context

These diagnostic tests were created during several development sessions:

1. **2025-10-29 (Relaxation Method)**: Test 2 mass conservation diagnostics
2. **2025-10-29 (Test 5 Fix)**: Comprehensive Test 5 stability analysis, dt_max implementation
3. **2025-10-29 (Continued Development)**: Test 4 hydraulic jump diagnosis, Test 5 accuracy exploration

## Documentation References

For detailed analysis and historical context, see:

- `docs/SESSION_2025_10_29_RELAXATION_METHOD.md` - Relaxation method implementation
- `docs/SESSION_2025_10_29_MACDONALD_TEST5_FIX.md` - Test 5 diagnosis and fix (829 lines)
- `docs/TEST4_HYDRAULIC_JUMP_DIAGNOSIS.md` - Test 4 diagnosis report (400 lines)
- `docs/SESSION_2025_10_29_CONTINUED_DEVELOPMENT.md` - Final session summary (600 lines)

## Maintenance Notes

### Keeping Tests vs. Cleanup

**Keep these tests**:
- All MacDonald diagnostics (historical record + valuable for future debugging)
- dt_max feature test (verifies important feature)
- Supercritical BC tests (validates critical functionality)
- Mass conservation tests (ongoing verification need)

**Consider archiving** (if disk space becomes concern):
- Redundant BC tests that verify the same thing
- One-off exploration tests that served their purpose

**Current recommendation**: Keep all tests. They provide:
1. Historical development record
2. Regression testing
3. Future debugging reference
4. Educational value for understanding numerical behavior

---

**Last updated**: 2025-10-29
**Total diagnostic tests**: 53
**Status**: All passing ✅
