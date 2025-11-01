#!/usr/bin/env python3
"""
HydroClaude Quick Verification Script
快速验证脚本

Purpose: Quickly verify that HydroClaude is correctly installed and working
用途: 快速验证HydroClaude是否正确安装并工作

Author: HydroClaude Development Team
Date: 2025-10-31
"""

import sys
import numpy as np

print("\n" + "="*70)
print("HydroClaude Quick Verification")
print("HydroClaude 快速验证")
print("="*70)

# Test 1: Import core modules
print("\n[1/5] Testing module imports...")
try:
    from solvers.godunov_fvm_solver import GodunvFVMSolver
    from physics.cross_section import RectangularSection
    from core.base import HydraulicComponent
    print("  ✅ Core modules imported successfully")
except ImportError as e:
    print(f"  ❌ Import failed: {e}")
    sys.exit(1)

# Test 2: Create solver instance
print("\n[2/5] Testing solver initialization...")
try:
    solver = GodunvFVMSolver(
        width=10.0,
        length=100.0,
        n_cells=50,
        manning_n=0.03,
        slope=0.0,  # Flat bottom to avoid warnings
        cfl=0.5,
        order=1
    )
    print(f"  ✅ Solver created: {solver.n} cells, dx={solver.dx:.2f}m")
except Exception as e:
    print(f"  ❌ Solver creation failed: {e}")
    sys.exit(1)

# Test 3: Run simple simulation
print("\n[3/5] Testing basic simulation (dam break)...")
try:
    # Setup simple dam break
    h_init = np.ones(50)
    h_init[:25] = 5.0  # Left side high
    h_init[25:] = 1.0  # Right side low
    Q_init = np.zeros(50)

    solver.initialize(
        h_init, Q_init,
        bc_left={'type': 'h', 'value': 5.0},
        bc_right={'type': 'h', 'value': 1.0}
    )

    # Run 10 steps
    step_count = 0
    for _ in range(10):
        solver.step()
        step_count += 1

    # Check for NaN
    has_nan = np.any(np.isnan(solver.h)) or np.any(np.isnan(solver.Q))
    if has_nan:
        print(f"  ❌ Simulation produced NaN values")
        sys.exit(1)

    print(f"  ✅ Simulation successful: t={solver.t:.3f}s, {step_count} steps")

except Exception as e:
    print(f"  ❌ Simulation failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Test Well-Balanced format
print("\n[4/5] Testing Well-Balanced format...")
try:
    # Create simple topography
    L = 100.0
    n_cells = 50
    x = np.linspace(0.5, L-0.5, n_cells)

    # Gentle slope
    z_b = 0.01 * x

    # Static water
    eta = 10.0
    h = eta - z_b
    Q = np.zeros(n_cells)

    solver_wb = GodunvFVMSolver(
        width=10.0,
        length=L,
        n_cells=n_cells,
        manning_n=0.0,
        z_b=z_b,
        cfl=0.5,
        order=1,
        well_balanced=True
    )

    solver_wb.initialize(
        h, Q,
        bc_left={'type': 'h', 'value': h[0]},
        bc_right={'type': 'h', 'value': h[-1]}
    )

    # Run 10 steps
    for _ in range(10):
        solver_wb.step()

    # Check stability
    has_nan = np.any(np.isnan(solver_wb.h)) or np.any(np.isnan(solver_wb.Q))
    if has_nan:
        print(f"  ❌ Well-Balanced simulation produced NaN")
        sys.exit(1)

    print(f"  ✅ Well-Balanced format working: t={solver_wb.t:.3f}s")

except Exception as e:
    print(f"  ❌ Well-Balanced test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 5: Check optional dependencies
print("\n[5/5] Checking optional dependencies...")

try:
    import numba
    print("  ✅ Numba available (JIT acceleration enabled)")
except ImportError:
    print("  ⚠️  Numba not available (running in pure Python mode)")

try:
    import matplotlib
    print("  ✅ Matplotlib available (visualization enabled)")
except ImportError:
    print("  ⚠️  Matplotlib not available (no visualization)")

try:
    import scipy
    print("  ✅ SciPy available (optimization enabled)")
except ImportError:
    print("  ⚠️  SciPy not available (limited optimization)")

# Success!
print("\n" + "="*70)
print("✅ All core tests passed!")
print("="*70)
print("\nHydroClaude is correctly installed and working.")
print("\nNext steps:")
print("  - Run full test suite: python tests/core_functionality_verification_v2.py")
print("  - Try example cases: python examples/case_library/case_01_hydropower_plant.py")
print("  - Run benchmarks: python tests/performance_benchmark.py")
print("  - Read documentation: docs/")
print("\nFor questions or issues:")
print("  - GitHub: https://github.com/your-repo/HydroClaude")
print("  - Documentation: docs/VERIFICATION_VALIDATION_COMPREHENSIVE_REPORT.md")
print("\n" + "="*70)

sys.exit(0)
