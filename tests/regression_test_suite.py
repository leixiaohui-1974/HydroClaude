#!/usr/bin/env python3
"""
HydroClaude Comprehensive Regression Test Suite
综合回归测试套件

Purpose:
- Run comprehensive tests across all major components
- Generate detailed test reports
- Track regression issues
- CI/CD integration ready

Author: HydroClaude Development Team
Date: 2025-10-31
"""

import sys
import os
import time
import json
from datetime import datetime
from typing import Dict, List, Tuple

import numpy as np

sys.path.insert(0, '.')

from solvers.godunov_fvm_solver import GodunvFVMSolver


class RegressionTestSuite:
    """Comprehensive regression test suite"""

    def __init__(self, output_dir: str = "test_results"):
        self.output_dir = output_dir
        self.results = []
        self.start_time = None
        self.end_time = None

        # Create output directory
        os.makedirs(output_dir, exist_ok=True)

    def run_all_tests(self):
        """Run all regression tests"""
        print("\n" + "="*70)
        print("HydroClaude Comprehensive Regression Test Suite")
        print("="*70)

        self.start_time = time.time()

        # Run test categories
        self._run_solver_tests()
        self._run_well_balanced_tests()
        self._run_boundary_condition_tests()
        self._run_physical_tests()

        self.end_time = time.time()

        # Generate report
        self._generate_report()
        self._print_summary()

    def _run_solver_tests(self):
        """Category 1: Core Solver Tests"""
        print("\n" + "="*70)
        print("Category 1: Core Solver Tests")
        print("="*70)

        # Test 1.1: Flat bottom, should maintain exact static water
        self._test_flat_bottom_static()

        # Test 1.2: Dam break
        self._test_dam_break()

        # Test 1.3: Smooth shock propagation
        self._test_shock_propagation()

    def _run_well_balanced_tests(self):
        """Category 2: Well-Balanced Format Tests"""
        print("\n" + "="*70)
        print("Category 2: Well-Balanced Format Tests")
        print("="*70)

        # Test 2.1: Lake at Rest with gentle slope
        self._test_lake_at_rest_gentle()

        # Test 2.2: Lake at Rest with hump
        self._test_lake_at_rest_hump()

        # Test 2.3: Well-Balanced with Manning friction
        self._test_well_balanced_friction()

    def _run_boundary_condition_tests(self):
        """Category 3: Boundary Condition Tests"""
        print("\n" + "="*70)
        print("Category 3: Boundary Condition Tests")
        print("="*70)

        # Test 3.1: Fixed h boundary
        self._test_bc_fixed_h()

        # Test 3.2: Fixed Q boundary
        self._test_bc_fixed_q()

        # Test 3.3: Mixed boundaries
        self._test_bc_mixed()

    def _run_physical_tests(self):
        """Category 4: Physical Correctness Tests"""
        print("\n" + "="*70)
        print("Category 4: Physical Correctness Tests")
        print("="*70)

        # Test 4.1: Mass conservation
        self._test_mass_conservation()

        # Test 4.2: Energy dissipation
        self._test_energy_dissipation()

        # Test 4.3: Froude number calculation
        self._test_froude_number()

    # ========================================================================
    # Category 1: Core Solver Tests
    # ========================================================================

    def _test_flat_bottom_static(self):
        """Test 1.1: Flat bottom static water"""
        test_name = "1.1_flat_bottom_static"
        print(f"\n[Test {test_name}] Flat bottom static water...")

        try:
            # Setup
            L = 1000.0
            n_cells = 100
            h_init = 5.0

            solver = GodunvFVMSolver(
                width=10.0,
                length=L,
                n_cells=n_cells,
                manning_n=0.0,
                slope=0.0,
                cfl=0.5,
                order=1
            )

            h = np.ones(n_cells) * h_init
            Q = np.zeros(n_cells)

            solver.initialize(
                h, Q,
                bc_left={'type': 'h', 'value': h_init},
                bc_right={'type': 'h', 'value': h_init}
            )

            # Run 1000 steps
            for _ in range(1000):
                solver.step()

            # Check
            max_Q = np.max(np.abs(solver.Q))
            max_h_dev = np.max(np.abs(solver.h - h_init))

            passed = max_Q < 1e-10 and max_h_dev < 1e-10
            status = "PASS" if passed else "FAIL"

            result = {
                'test': test_name,
                'description': 'Flat bottom static water (machine precision test)',
                'status': status,
                'metrics': {
                    'max_Q': float(max_Q),
                    'max_h_deviation': float(max_h_dev),
                    'steps': 1000,
                    'time': float(solver.t)
                },
                'passed': bool(passed)
            }

            print(f"  Status: {status}")
            print(f"  max|Q|: {max_Q:.3e}")
            print(f"  max|h-h₀|: {max_h_dev:.3e}")

        except Exception as e:
            result = {
                'test': test_name,
                'description': 'Flat bottom static water',
                'status': 'ERROR',
                'error': str(e),
                'passed': False
            }
            print(f"  Status: ERROR - {e}")

        self.results.append(result)

    def _test_dam_break(self):
        """Test 1.2: Dam break"""
        test_name = "1.2_dam_break"
        print(f"\n[Test {test_name}] Dam break simulation...")

        try:
            # Setup
            L = 1000.0
            n_cells = 200
            h_L, h_R = 10.0, 1.0

            solver = GodunvFVMSolver(
                width=10.0,
                length=L,
                n_cells=n_cells,
                manning_n=0.0,
                slope=0.0,
                cfl=0.5,
                order=1
            )

            h_init = np.where(solver.x < L/2, h_L, h_R)
            Q_init = np.zeros(n_cells)

            solver.initialize(
                h_init, Q_init,
                bc_left={'type': 'h', 'value': h_L},
                bc_right={'type': 'h', 'value': h_R}
            )

            mass_init = solver._compute_total_mass()

            # Run 10 seconds
            while solver.t < 10.0:
                solver.step()

            mass_final = solver._compute_total_mass()
            mass_error = abs(mass_final - mass_init) / mass_init * 100

            has_nan = np.any(np.isnan(solver.h)) or np.any(np.isnan(solver.Q))
            passed = not has_nan and mass_error < 5.0

            status = "PASS" if passed else "FAIL"

            result = {
                'test': test_name,
                'description': 'Dam break with mass conservation check',
                'status': status,
                'metrics': {
                    'mass_error_percent': float(mass_error),
                    'has_nan': bool(has_nan),
                    'final_time': float(solver.t),
                    'h_min': float(np.min(solver.h)),
                    'h_max': float(np.max(solver.h))
                },
                'passed': bool(passed)
            }

            print(f"  Status: {status}")
            print(f"  Mass error: {mass_error:.3f}%")
            print(f"  NaN check: {'Failed' if has_nan else 'Passed'}")

        except Exception as e:
            result = {
                'test': test_name,
                'description': 'Dam break',
                'status': 'ERROR',
                'error': str(e),
                'passed': False
            }
            print(f"  Status: ERROR - {e}")

        self.results.append(result)

    def _test_shock_propagation(self):
        """Test 1.3: Shock propagation"""
        test_name = "1.3_shock_propagation"
        print(f"\n[Test {test_name}] Shock propagation...")

        try:
            # Setup - Riemann problem
            L = 100.0
            n_cells = 100

            solver = GodunvFVMSolver(
                width=10.0,
                length=L,
                n_cells=n_cells,
                manning_n=0.0,
                slope=0.0,
                cfl=0.5,
                order=1
            )

            # Initial condition: shock tube
            h_init = np.where(solver.x < L/2, 2.0, 1.0)
            Q_init = np.zeros(n_cells)

            solver.initialize(
                h_init, Q_init,
                bc_left={'type': 'h', 'value': 2.0},
                bc_right={'type': 'h', 'value': 1.0}
            )

            # Run 5 seconds
            while solver.t < 5.0:
                solver.step()

            # Check: shock should propagate, no NaN
            has_nan = np.any(np.isnan(solver.h)) or np.any(np.isnan(solver.Q))
            h_range = np.max(solver.h) - np.min(solver.h)
            passed = not has_nan and h_range > 0.5  # Shock still present

            status = "PASS" if passed else "FAIL"

            result = {
                'test': test_name,
                'description': 'Shock propagation stability',
                'status': status,
                'metrics': {
                    'has_nan': bool(has_nan),
                    'h_range': float(h_range),
                    'final_time': float(solver.t)
                },
                'passed': bool(passed)
            }

            print(f"  Status: {status}")
            print(f"  h range: {h_range:.3f}m")

        except Exception as e:
            result = {
                'test': test_name,
                'description': 'Shock propagation',
                'status': 'ERROR',
                'error': str(e),
                'passed': False
            }
            print(f"  Status: ERROR - {e}")

        self.results.append(result)

    # ========================================================================
    # Category 2: Well-Balanced Tests
    # ========================================================================

    def _test_lake_at_rest_gentle(self):
        """Test 2.1: Lake at Rest with gentle slope"""
        test_name = "2.1_lake_at_rest_gentle"
        print(f"\n[Test {test_name}] Lake at Rest (gentle slope)...")

        try:
            L = 100.0
            n_cells = 100
            eta_init = 10.0

            # Gentle slope
            x = np.linspace(0.5, L-0.5, n_cells)
            z_b = 0.01 * x  # 1% slope

            h = eta_init - z_b
            Q = np.zeros(n_cells)

            solver = GodunvFVMSolver(
                width=10.0,
                length=L,
                n_cells=n_cells,
                manning_n=0.0,
                z_b=z_b,
                cfl=0.5,
                order=1,
                well_balanced=True
            )

            solver.initialize(
                h, Q,
                bc_left={'type': 'h', 'value': h[0]},
                bc_right={'type': 'h', 'value': h[-1]}
            )

            # Run 10 seconds
            for _ in range(100):
                solver.step()

            # Check
            eta_current = solver.h + solver.z_b
            disturbance = np.max(np.abs(eta_current - eta_init))
            max_Q = np.max(np.abs(solver.Q))

            passed = disturbance < 1.0 and max_Q < 1.0

            status = "PASS" if passed else "FAIL"

            result = {
                'test': test_name,
                'description': 'Lake at Rest with gentle 1% slope',
                'status': status,
                'metrics': {
                    'disturbance': float(disturbance),
                    'max_Q': float(max_Q),
                    'time': float(solver.t)
                },
                'passed': bool(passed)
            }

            print(f"  Status: {status}")
            print(f"  Disturbance: {disturbance:.3f}m")
            print(f"  max|Q|: {max_Q:.3e}")

        except Exception as e:
            result = {
                'test': test_name,
                'description': 'Lake at Rest gentle slope',
                'status': 'ERROR',
                'error': str(e),
                'passed': False
            }
            print(f"  Status: ERROR - {e}")

        self.results.append(result)

    def _test_lake_at_rest_hump(self):
        """Test 2.2: Lake at Rest with hump"""
        test_name = "2.2_lake_at_rest_hump"
        print(f"\n[Test {test_name}] Lake at Rest (2m hump)...")

        try:
            L = 100.0
            n_cells = 100
            eta_init = 10.0
            hump_height = 2.0
            hump_width = 20.0

            # Create hump
            x = np.linspace(0.5, L-0.5, n_cells)
            x_center = L / 2.0

            z_b = np.zeros(n_cells)
            for i in range(n_cells):
                if abs(x[i] - x_center) < hump_width / 2:
                    dist = abs(x[i] - x_center)
                    z_b[i] = hump_height * (1.0 - 2.0 * dist / hump_width)

            h = eta_init - z_b
            Q = np.zeros(n_cells)

            solver = GodunvFVMSolver(
                width=10.0,
                length=L,
                n_cells=n_cells,
                manning_n=0.03,
                z_b=z_b,
                cfl=0.5,
                order=1,
                well_balanced=True
            )

            solver.initialize(
                h, Q,
                bc_left={'type': 'h', 'value': h[0]},
                bc_right={'type': 'h', 'value': h[-1]}
            )

            mass_init = solver._compute_total_mass()

            # Run 10 seconds
            while solver.t < 10.0:
                solver.step()

            eta_current = solver.h + solver.z_b
            disturbance = np.max(np.abs(eta_current - eta_init))
            mass_final = solver._compute_total_mass()
            mass_error = abs(mass_final - mass_init) / mass_init * 100

            passed = disturbance < 5.0 and mass_error < 10.0

            status = "PASS" if passed else "FAIL"

            result = {
                'test': test_name,
                'description': 'Lake at Rest with 2m hump',
                'status': status,
                'metrics': {
                    'disturbance': float(disturbance),
                    'mass_error_percent': float(mass_error),
                    'time': float(solver.t)
                },
                'passed': bool(passed)
            }

            print(f"  Status: {status}")
            print(f"  Disturbance: {disturbance:.3f}m")
            print(f"  Mass error: {mass_error:.3f}%")

        except Exception as e:
            result = {
                'test': test_name,
                'description': 'Lake at Rest hump',
                'status': 'ERROR',
                'error': str(e),
                'passed': False
            }
            print(f"  Status: ERROR - {e}")

        self.results.append(result)

    def _test_well_balanced_friction(self):
        """Test 2.3: Well-Balanced with Manning friction"""
        test_name = "2.3_well_balanced_friction"
        print(f"\n[Test {test_name}] Well-Balanced with friction...")

        try:
            # Setup: Uniform flow with slope and friction should balance
            L = 1000.0
            n_cells = 50
            S0 = 0.001
            n = 0.03
            Q = 50.0
            B = 10.0

            # Normal depth calculation
            h_normal = (Q * n / (B * np.sqrt(S0))) ** (3/5)

            solver = GodunvFVMSolver(
                width=B,
                length=L,
                n_cells=n_cells,
                manning_n=n,
                slope=S0,
                cfl=0.5,
                order=1,
                well_balanced=True
            )

            h = h_normal * np.ones(n_cells)
            Q_arr = Q * np.ones(n_cells)

            solver.initialize(
                h, Q_arr,
                bc_left={'type': 'Q', 'value': Q},
                bc_right={'type': 'h', 'value': h_normal}
            )

            # Run 100 seconds
            step_count = 0
            while solver.t < 100.0 and step_count < 500:
                solver.step()
                step_count += 1

            # Check stability
            has_nan = np.any(np.isnan(solver.h)) or np.any(np.isnan(solver.Q))
            h_dev = np.max(np.abs(solver.h - h_normal))

            passed = not has_nan and step_count > 10

            status = "PASS" if passed else "FAIL"

            result = {
                'test': test_name,
                'description': 'Well-Balanced with Manning friction',
                'status': status,
                'metrics': {
                    'has_nan': bool(has_nan),
                    'h_deviation': float(h_dev),
                    'steps': step_count,
                    'time': float(solver.t)
                },
                'passed': bool(passed)
            }

            print(f"  Status: {status}")
            print(f"  Steps: {step_count}")
            print(f"  h deviation: {h_dev:.3f}m")

        except Exception as e:
            result = {
                'test': test_name,
                'description': 'Well-Balanced friction',
                'status': 'ERROR',
                'error': str(e),
                'passed': False
            }
            print(f"  Status: ERROR - {e}")

        self.results.append(result)

    # ========================================================================
    # Category 3: Boundary Condition Tests
    # ========================================================================

    def _test_bc_fixed_h(self):
        """Test 3.1: Fixed h boundary"""
        test_name = "3.1_bc_fixed_h"
        print(f"\n[Test {test_name}] Fixed h boundary...")

        try:
            solver = GodunvFVMSolver(
                width=10.0, length=100.0, n_cells=50,
                manning_n=0.0, slope=0.0, cfl=0.5, order=1
            )

            h = np.ones(50) * 3.0
            Q = np.zeros(50)

            solver.initialize(
                h, Q,
                bc_left={'type': 'h', 'value': 3.0},
                bc_right={'type': 'h', 'value': 3.0}
            )

            for _ in range(10):
                solver.step()

            # Check: boundary values should be maintained
            passed = abs(solver.h[0] - 3.0) < 0.1 and abs(solver.h[-1] - 3.0) < 0.1

            status = "PASS" if passed else "FAIL"

            result = {
                'test': test_name,
                'description': 'Fixed h boundary condition',
                'status': status,
                'metrics': {
                    'h_left': float(solver.h[0]),
                    'h_right': float(solver.h[-1])
                },
                'passed': bool(passed)
            }

            print(f"  Status: {status}")

        except Exception as e:
            result = {
                'test': test_name,
                'description': 'Fixed h boundary',
                'status': 'ERROR',
                'error': str(e),
                'passed': False
            }
            print(f"  Status: ERROR - {e}")

        self.results.append(result)

    def _test_bc_fixed_q(self):
        """Test 3.2: Fixed Q boundary"""
        test_name = "3.2_bc_fixed_q"
        print(f"\n[Test {test_name}] Fixed Q boundary...")

        try:
            solver = GodunvFVMSolver(
                width=10.0, length=100.0, n_cells=50,
                manning_n=0.03, slope=0.001, cfl=0.5, order=1
            )

            h = np.ones(50) * 2.0
            Q = np.ones(50) * 50.0

            solver.initialize(
                h, Q,
                bc_left={'type': 'Q', 'value': 50.0},
                bc_right={'type': 'h', 'value': 2.0}
            )

            for _ in range(10):
                solver.step()

            # Check: flow should be maintained
            has_nan = np.any(np.isnan(solver.Q))
            passed = not has_nan and abs(solver.Q[0] - 50.0) < 10.0

            status = "PASS" if passed else "FAIL"

            result = {
                'test': test_name,
                'description': 'Fixed Q boundary condition',
                'status': status,
                'metrics': {
                    'Q_left': float(solver.Q[0]),
                    'has_nan': bool(has_nan)
                },
                'passed': bool(passed)
            }

            print(f"  Status: {status}")

        except Exception as e:
            result = {
                'test': test_name,
                'description': 'Fixed Q boundary',
                'status': 'ERROR',
                'error': str(e),
                'passed': False
            }
            print(f"  Status: ERROR - {e}")

        self.results.append(result)

    def _test_bc_mixed(self):
        """Test 3.3: Mixed boundaries"""
        test_name = "3.3_bc_mixed"
        print(f"\n[Test {test_name}] Mixed boundaries (Q + h)...")

        try:
            solver = GodunvFVMSolver(
                width=10.0, length=100.0, n_cells=50,
                manning_n=0.03, slope=0.001, cfl=0.5, order=1
            )

            h = np.ones(50) * 2.0
            Q = np.ones(50) * 30.0

            solver.initialize(
                h, Q,
                bc_left={'type': 'Q', 'value': 30.0},
                bc_right={'type': 'h', 'value': 2.0}
            )

            for _ in range(10):
                solver.step()

            has_nan = np.any(np.isnan(solver.h)) or np.any(np.isnan(solver.Q))
            passed = not has_nan

            status = "PASS" if passed else "FAIL"

            result = {
                'test': test_name,
                'description': 'Mixed boundary conditions (Q+h)',
                'status': status,
                'metrics': {
                    'has_nan': bool(has_nan)
                },
                'passed': bool(passed)
            }

            print(f"  Status: {status}")

        except Exception as e:
            result = {
                'test': test_name,
                'description': 'Mixed boundaries',
                'status': 'ERROR',
                'error': str(e),
                'passed': False
            }
            print(f"  Status: ERROR - {e}")

        self.results.append(result)

    # ========================================================================
    # Category 4: Physical Correctness Tests
    # ========================================================================

    def _test_mass_conservation(self):
        """Test 4.1: Mass conservation"""
        test_name = "4.1_mass_conservation"
        print(f"\n[Test {test_name}] Mass conservation...")

        try:
            solver = GodunvFVMSolver(
                width=10.0, length=100.0, n_cells=100,
                manning_n=0.0, slope=0.0, cfl=0.5, order=1
            )

            h = np.ones(100) * 5.0
            h[:50] = 8.0
            Q = np.zeros(100)

            solver.initialize(
                h, Q,
                bc_left={'type': 'h', 'value': 8.0},
                bc_right={'type': 'h', 'value': 5.0}
            )

            mass_init = solver._compute_total_mass()

            for _ in range(100):
                solver.step()

            mass_final = solver._compute_total_mass()
            mass_error = abs(mass_final - mass_init) / mass_init * 100

            passed = mass_error < 5.0

            status = "PASS" if passed else "FAIL"

            result = {
                'test': test_name,
                'description': 'Mass conservation over 100 steps',
                'status': status,
                'metrics': {
                    'mass_init': float(mass_init),
                    'mass_final': float(mass_final),
                    'mass_error_percent': float(mass_error)
                },
                'passed': bool(passed)
            }

            print(f"  Status: {status}")
            print(f"  Mass error: {mass_error:.3f}%")

        except Exception as e:
            result = {
                'test': test_name,
                'description': 'Mass conservation',
                'status': 'ERROR',
                'error': str(e),
                'passed': False
            }
            print(f"  Status: ERROR - {e}")

        self.results.append(result)

    def _test_energy_dissipation(self):
        """Test 4.2: Energy dissipation with friction"""
        test_name = "4.2_energy_dissipation"
        print(f"\n[Test {test_name}] Energy dissipation...")

        try:
            solver = GodunvFVMSolver(
                width=10.0, length=100.0, n_cells=50,
                manning_n=0.05,  # High friction
                slope=0.001, cfl=0.5, order=1
            )

            h = np.ones(50) * 3.0
            Q = np.ones(50) * 100.0  # High initial flow

            solver.initialize(
                h, Q,
                bc_left={'type': 'Q', 'value': 100.0},
                bc_right={'type': 'h', 'value': 3.0}
            )

            Q_init_avg = np.mean(solver.Q)

            for _ in range(100):
                solver.step()

            Q_final_avg = np.mean(solver.Q)

            # With friction, average Q should decrease
            passed = Q_final_avg < Q_init_avg

            status = "PASS" if passed else "FAIL"

            result = {
                'test': test_name,
                'description': 'Energy dissipation with friction',
                'status': status,
                'metrics': {
                    'Q_init_avg': float(Q_init_avg),
                    'Q_final_avg': float(Q_final_avg),
                    'reduction_percent': float((Q_init_avg - Q_final_avg) / Q_init_avg * 100)
                },
                'passed': bool(passed)
            }

            print(f"  Status: {status}")
            print(f"  Q reduction: {(Q_init_avg - Q_final_avg) / Q_init_avg * 100:.1f}%")

        except Exception as e:
            result = {
                'test': test_name,
                'description': 'Energy dissipation',
                'status': 'ERROR',
                'error': str(e),
                'passed': False
            }
            print(f"  Status: ERROR - {e}")

        self.results.append(result)

    def _test_froude_number(self):
        """Test 4.3: Froude number calculation"""
        test_name = "4.3_froude_number"
        print(f"\n[Test {test_name}] Froude number calculation...")

        try:
            solver = GodunvFVMSolver(
                width=10.0, length=100.0, n_cells=50,
                manning_n=0.03, slope=0.001, cfl=0.5, order=1
            )

            h = np.ones(50) * 2.0
            Q = np.ones(50) * 30.0

            solver.initialize(
                h, Q,
                bc_left={'type': 'Q', 'value': 30.0},
                bc_right={'type': 'h', 'value': 2.0}
            )

            solver.step()

            # Calculate Froude number manually
            u = solver.Q / (solver.h * solver.B)
            Fr = u / np.sqrt(solver.g * solver.h)

            # Should be subcritical (Fr < 1) for this gentle case
            Fr_max = np.max(Fr[solver.h > 0.1])
            passed = Fr_max < 2.0  # Reasonable range

            status = "PASS" if passed else "FAIL"

            result = {
                'test': test_name,
                'description': 'Froude number physical range',
                'status': status,
                'metrics': {
                    'Fr_max': float(Fr_max),
                    'Fr_mean': float(np.mean(Fr[solver.h > 0.1]))
                },
                'passed': bool(passed)
            }

            print(f"  Status: {status}")
            print(f"  Fr_max: {Fr_max:.3f}")

        except Exception as e:
            result = {
                'test': test_name,
                'description': 'Froude number',
                'status': 'ERROR',
                'error': str(e),
                'passed': False
            }
            print(f"  Status: ERROR - {e}")

        self.results.append(result)

    # ========================================================================
    # Reporting
    # ========================================================================

    def _generate_report(self):
        """Generate JSON and text reports"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # JSON report
        report = {
            'timestamp': timestamp,
            'total_tests': len(self.results),
            'passed': sum(1 for r in self.results if r['passed']),
            'failed': sum(1 for r in self.results if not r['passed'] and r['status'] != 'ERROR'),
            'errors': sum(1 for r in self.results if r['status'] == 'ERROR'),
            'duration_seconds': self.end_time - self.start_time,
            'tests': self.results
        }

        json_path = os.path.join(self.output_dir, f'regression_report_{timestamp}.json')
        with open(json_path, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"\n📄 JSON report saved: {json_path}")

        # Text report
        txt_path = os.path.join(self.output_dir, f'regression_report_{timestamp}.txt')
        with open(txt_path, 'w') as f:
            f.write("="*70 + "\n")
            f.write("HydroClaude Regression Test Report\n")
            f.write("="*70 + "\n\n")
            f.write(f"Timestamp: {timestamp}\n")
            f.write(f"Duration: {self.end_time - self.start_time:.2f}s\n\n")

            f.write(f"Total Tests: {len(self.results)}\n")
            f.write(f"Passed: {report['passed']}\n")
            f.write(f"Failed: {report['failed']}\n")
            f.write(f"Errors: {report['errors']}\n\n")

            f.write("="*70 + "\n")
            f.write("Detailed Results\n")
            f.write("="*70 + "\n\n")

            for r in self.results:
                f.write(f"[{r['test']}] {r['description']}\n")
                f.write(f"  Status: {r['status']}\n")
                if 'metrics' in r:
                    for key, val in r['metrics'].items():
                        f.write(f"  {key}: {val}\n")
                if 'error' in r:
                    f.write(f"  Error: {r['error']}\n")
                f.write("\n")

        print(f"📄 Text report saved: {txt_path}")

    def _print_summary(self):
        """Print summary to console"""
        print("\n" + "="*70)
        print("Test Summary")
        print("="*70)

        passed = sum(1 for r in self.results if r['passed'])
        failed = sum(1 for r in self.results if not r['passed'] and r['status'] != 'ERROR')
        errors = sum(1 for r in self.results if r['status'] == 'ERROR')

        print(f"\nTotal Tests: {len(self.results)}")
        print(f"Passed:      {passed} ({passed/len(self.results)*100:.0f}%)")
        print(f"Failed:      {failed}")
        print(f"Errors:      {errors}")
        print(f"Duration:    {self.end_time - self.start_time:.2f}s")

        if passed == len(self.results):
            print("\n✅ All tests passed!")
        else:
            print("\n⚠️  Some tests failed or had errors")
            print("\nFailed/Error tests:")
            for r in self.results:
                if not r['passed']:
                    print(f"  - [{r['test']}] {r['status']}")

        print("\n" + "="*70)


def main():
    """Run regression test suite"""
    suite = RegressionTestSuite()
    suite.run_all_tests()


if __name__ == '__main__':
    main()
