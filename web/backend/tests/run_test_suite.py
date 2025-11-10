#!/usr/bin/env python3
"""
Test Suite Runner
Runs all standard test cases and generates a comprehensive report
"""

import sys
import os
import requests
import time
import json
from datetime import datetime
from typing import Dict, List, Any

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.test_cases import ALL_TEST_CASES, TEST_SUITE_INFO

API_URL = os.environ.get('API_URL', 'http://localhost:8000')


class TestResult:
    """Test case result"""
    def __init__(self, test_case: Dict[str, Any]):
        self.test_case = test_case
        self.task_id = None
        self.status = 'pending'
        self.passed = False
        self.duration = 0.0
        self.metrics = {}
        self.errors = []
        self.warnings = []

    def to_dict(self):
        return {
            'name': self.test_case['name'],
            'description': self.test_case['description'],
            'task_id': self.task_id,
            'status': self.status,
            'passed': self.passed,
            'duration': self.duration,
            'metrics': self.metrics,
            'errors': self.errors,
            'warnings': self.warnings
        }


class TestSuiteRunner:
    """Test suite runner"""

    def __init__(self):
        self.results: List[TestResult] = []
        self.start_time = None
        self.end_time = None

    def check_backend(self) -> bool:
        """Check if backend is running"""
        try:
            response = requests.get(f"{API_URL}/health", timeout=2)
            return response.status_code == 200
        except:
            return False

    def run_test_case(self, test_case: Dict[str, Any]) -> TestResult:
        """Run a single test case"""
        result = TestResult(test_case)

        print(f"\n{'='*70}")
        print(f"Running: {test_case['name']}")
        print(f"Description: {test_case['description']}")
        print(f"{'='*70}")

        try:
            # Create simulation
            request_data = {
                "name": test_case['name'],
                "description": test_case['description'],
                "config": test_case['config']
            }

            print("Submitting simulation...")
            response = requests.post(
                f"{API_URL}/api/v1/simulations",
                json=request_data,
                timeout=10
            )

            if response.status_code != 201:
                result.status = 'failed'
                result.errors.append(f"Failed to create simulation: {response.status_code}")
                print(f"❌ Failed to create simulation: {response.status_code}")
                return result

            task_data = response.json()
            result.task_id = task_data['task_id']
            print(f"✓ Simulation created: {result.task_id}")

            # Wait for completion
            print("Waiting for completion", end="", flush=True)
            max_wait = 60
            waited = 0
            while waited < max_wait:
                time.sleep(1)
                waited += 1
                print(".", end="", flush=True)

                status_response = requests.get(
                    f"{API_URL}/api/v1/simulations/{result.task_id}/status",
                    timeout=5
                )

                if status_response.status_code != 200:
                    result.status = 'failed'
                    result.errors.append("Failed to query status")
                    print(f"\n❌ Failed to query status")
                    return result

                status_data = status_response.json()

                if status_data['status'] == 'completed':
                    result.duration = status_data.get('duration', 0.0)
                    print(f"\n✓ Completed in {result.duration:.3f}s")
                    break
                elif status_data['status'] == 'failed':
                    result.status = 'failed'
                    result.errors.append(f"Simulation failed: {status_data.get('error')}")
                    print(f"\n❌ Simulation failed: {status_data.get('error')}")
                    return result

            if waited >= max_wait:
                result.status = 'timeout'
                result.errors.append("Simulation timeout")
                print(f"\n❌ Timeout after {max_wait}s")
                return result

            # Get results
            print("Retrieving results...")
            results_response = requests.get(
                f"{API_URL}/api/v1/simulations/{result.task_id}/results",
                timeout=10
            )

            if results_response.status_code != 200:
                result.status = 'failed'
                result.errors.append("Failed to retrieve results")
                print(f"❌ Failed to retrieve results")
                return result

            results_data = results_response.json()
            result.metrics = results_data['metrics']
            result.status = 'completed'

            print("✓ Results retrieved")

            # Validate against expected values
            print("\nValidating results...")
            expected = test_case.get('expected', {})
            result.passed = self.validate_results(result.metrics, expected, result)

            if result.passed:
                print("✅ TEST PASSED")
            else:
                print("❌ TEST FAILED")
                for error in result.errors:
                    print(f"  Error: {error}")
                for warning in result.warnings:
                    print(f"  Warning: {warning}")

        except Exception as e:
            result.status = 'error'
            result.errors.append(str(e))
            print(f"\n❌ Error: {e}")

        return result

    def validate_results(self, metrics: Dict, expected: Dict, result: TestResult) -> bool:
        """Validate simulation results against expected values"""
        passed = True

        # Check mass conservation error
        if 'mass_conservation_error' in expected:
            actual = metrics['mass_conservation_error']
            max_allowed = expected['mass_conservation_error']['max']
            if actual > max_allowed:
                result.errors.append(
                    f"Mass conservation error {actual:.2e} exceeds maximum {max_allowed:.2e}"
                )
                passed = False
            else:
                print(f"  ✓ Mass conservation: {actual:.2e} (< {max_allowed:.2e})")

        # Check max velocity
        if 'max_velocity' in expected:
            actual = metrics['max_velocity']
            max_allowed = expected['max_velocity']['max']
            if actual > max_allowed:
                result.errors.append(
                    f"Max velocity {actual:.4f} exceeds maximum {max_allowed:.4f}"
                )
                passed = False
            else:
                print(f"  ✓ Max velocity: {actual:.4f} m/s (< {max_allowed:.4f} m/s)")

        # Check convergence
        if 'converged' in expected:
            actual = metrics['converged']
            expected_val = expected['converged']
            if actual != expected_val:
                result.errors.append(
                    f"Convergence: expected {expected_val}, got {actual}"
                )
                passed = False
            else:
                print(f"  ✓ Converged: {actual}")

        # Check final mean depth
        if 'final_mean_depth' in expected:
            actual = metrics['mean_depth_final']
            expected_val = expected['final_mean_depth']['value']
            tolerance = expected['final_mean_depth']['tolerance']
            diff = abs(actual - expected_val)
            if diff > tolerance:
                result.errors.append(
                    f"Final mean depth {actual:.4f} differs from expected {expected_val:.4f} by {diff:.4f} (tolerance: {tolerance:.4f})"
                )
                passed = False
            else:
                print(f"  ✓ Final mean depth: {actual:.4f} m (expected: {expected_val:.4f} m)")

        return passed

    def run_all(self) -> bool:
        """Run all test cases"""
        self.start_time = datetime.now()

        print("\n" + "="*70)
        print(f"Test Suite: {TEST_SUITE_INFO['name']}")
        print(f"Version: {TEST_SUITE_INFO['version']}")
        print(f"Description: {TEST_SUITE_INFO['description']}")
        print(f"Total Cases: {TEST_SUITE_INFO['total_cases']}")
        print(f"Start Time: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)

        # Check backend
        if not self.check_backend():
            print("\n❌ Backend is not running!")
            print("Please start it with: cd web/backend && ./start_server.sh")
            return False

        print("✓ Backend is running\n")

        # Run each test case
        for i, test_case in enumerate(ALL_TEST_CASES, 1):
            print(f"\n[{i}/{len(ALL_TEST_CASES)}]", end=" ")
            result = self.run_test_case(test_case)
            self.results.append(result)

        self.end_time = datetime.now()

        # Print summary
        self.print_summary()

        # Generate report
        self.generate_report()

        # Return overall status
        passed_count = sum(1 for r in self.results if r.passed)
        return passed_count == len(self.results)

    def print_summary(self):
        """Print test summary"""
        passed = sum(1 for r in self.results if r.passed)
        failed = len(self.results) - passed
        total_duration = (self.end_time - self.start_time).total_seconds()

        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)
        print(f"Total Cases:  {len(self.results)}")
        print(f"Passed:       {passed} ✅")
        print(f"Failed:       {failed} ❌")
        print(f"Success Rate: {passed/len(self.results)*100:.1f}%")
        print(f"Total Time:   {total_duration:.2f}s")
        print("="*70)

        # List failed tests
        if failed > 0:
            print("\nFailed Tests:")
            for result in self.results:
                if not result.passed:
                    print(f"  ❌ {result.test_case['name']}")
                    for error in result.errors:
                        print(f"     - {error}")
        else:
            print("\n✅ ALL TESTS PASSED!")

        print()

    def generate_report(self):
        """Generate JSON report"""
        report = {
            'suite_info': TEST_SUITE_INFO,
            'run_info': {
                'start_time': self.start_time.isoformat(),
                'end_time': self.end_time.isoformat(),
                'duration': (self.end_time - self.start_time).total_seconds()
            },
            'results': [r.to_dict() for r in self.results],
            'summary': {
                'total': len(self.results),
                'passed': sum(1 for r in self.results if r.passed),
                'failed': sum(1 for r in self.results if not r.passed),
                'success_rate': sum(1 for r in self.results if r.passed) / len(self.results) * 100
            }
        }

        # Save to file
        report_file = os.path.join(
            os.path.dirname(__file__),
            f"test_report_{self.start_time.strftime('%Y%m%d_%H%M%S')}.json"
        )

        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"Report saved to: {report_file}")


def main():
    """Main entry point"""
    runner = TestSuiteRunner()
    success = runner.run_all()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
