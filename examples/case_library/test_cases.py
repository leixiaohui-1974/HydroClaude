# -*- coding: utf-8 -*-
"""
Test Suite for Engineering Cases - 工程案例测试套件
==================================================

Tests all engineering cases to ensure they run correctly and produce
reasonable results.

Author: Claude
Date: 2025-10-30
"""

import sys
import os
import time
import traceback

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, project_root)


class CaseTestRunner:
    """Test runner for engineering cases / 工程案例测试运行器"""

    def __init__(self):
        self.results = {
            'passed': [],
            'failed': [],
            'skipped': []
        }

    def run_test(self, case_name, test_func):
        """
        Run a single test case

        Args:
            case_name: Name of the test case
            test_func: Test function to run
        """
        print(f"\n{'='*70}")
        print(f"Running: {case_name}")
        print(f"{'='*70}")

        try:
            start_time = time.time()
            test_func()
            elapsed = time.time() - start_time

            print(f"\n✓ {case_name} PASSED ({elapsed:.2f}s)")
            self.results['passed'].append({
                'name': case_name,
                'time': elapsed
            })
            return True

        except ImportError as e:
            print(f"\n⊘ {case_name} SKIPPED (Missing dependency: {e})")
            self.results['skipped'].append({
                'name': case_name,
                'reason': str(e)
            })
            return None

        except Exception as e:
            print(f"\n✗ {case_name} FAILED")
            print(f"Error: {e}")
            print(f"\nTraceback:")
            traceback.print_exc()

            self.results['failed'].append({
                'name': case_name,
                'error': str(e)
            })
            return False

    def print_summary(self):
        """Print test summary / 打印测试总结"""
        print(f"\n{'#'*70}")
        print(f"#{'  TEST SUMMARY  ':^68}#")
        print(f"{'#'*70}\n")

        total = len(self.results['passed']) + len(self.results['failed']) + len(self.results['skipped'])

        print(f"Total Tests: {total}")
        print(f"✓ Passed:  {len(self.results['passed'])}")
        print(f"✗ Failed:  {len(self.results['failed'])}")
        print(f"⊘ Skipped: {len(self.results['skipped'])}")

        if self.results['passed']:
            print(f"\nPassed Tests:")
            for result in self.results['passed']:
                print(f"  ✓ {result['name']} ({result['time']:.2f}s)")

        if self.results['failed']:
            print(f"\nFailed Tests:")
            for result in self.results['failed']:
                print(f"  ✗ {result['name']}")
                print(f"     Error: {result['error']}")

        if self.results['skipped']:
            print(f"\nSkipped Tests:")
            for result in self.results['skipped']:
                print(f"  ⊘ {result['name']}")
                print(f"     Reason: {result['reason']}")

        print(f"\n{'#'*70}\n")

        # Return True if all tests passed
        return len(self.results['failed']) == 0


# Test functions for each case
# 每个案例的测试函数

def test_case_01_hydropower_basic():
    """Test Case 01: Hydropower Plant - Basic Functionality"""
    from case_01_hydropower_plant import HydropowerPlant

    # Create plant
    plant = HydropowerPlant(plant_type='francis', capacity_mw=100.0)

    # Check components exist
    assert plant.reservoir is not None, "Reservoir not created"
    assert plant.headrace is not None, "Headrace not created"
    assert plant.surge_tank is not None, "Surge tank not created"
    assert plant.penstock is not None, "Penstock not created"
    assert plant.turbine is not None, "Turbine not created"
    assert plant.tailrace is not None, "Tailrace not created"

    # Check parameters
    assert plant.turbine.rated_power == 100e6, "Turbine power incorrect"
    assert plant.reservoir.area == 5e6, "Reservoir area incorrect"

    print("✓ All components created successfully")
    print(f"✓ Turbine: {plant.turbine.rated_power/1e6:.0f} MW")
    print(f"✓ Reservoir: {plant.reservoir.area/1e6:.1f} km²")


def test_case_01_hydropower_simulation():
    """Test Case 01: Hydropower Plant - Short Simulation"""
    from case_01_hydropower_plant import HydropowerPlant

    # Create plant
    plant = HydropowerPlant(plant_type='francis', capacity_mw=100.0)

    # Run short simulation (10 seconds instead of 600)
    plant.simulate_normal_operation(duration=10.0, dt=0.1)

    # Check results
    assert len(plant.state_history['time']) > 0, "No history recorded"
    assert len(plant.state_history['turbine_power']) > 0, "No power data"

    # Check values are reasonable
    max_power = max(plant.state_history['turbine_power'])
    assert 0 < max_power < 150, f"Power out of range: {max_power} MW"

    print(f"✓ Simulation completed: {len(plant.state_history['time'])} steps")
    print(f"✓ Max power: {max_power:.1f} MW")


def test_case_01_hydropower_load_rejection():
    """Test Case 01: Hydropower Plant - Load Rejection"""
    from case_01_hydropower_plant import HydropowerPlant

    # Create plant
    plant = HydropowerPlant(plant_type='francis', capacity_mw=100.0)

    # Run load rejection (shortened)
    plant.simulate_load_rejection(duration=30.0, dt=0.01)

    # Check surge tank response
    assert len(plant.state_history['surge_tank_level']) > 0, "No surge tank data"

    max_level = max(plant.state_history['surge_tank_level'])
    min_level = min(plant.state_history['surge_tank_level'])

    assert plant.surge_tank.min_level < min_level, "Surge tank below minimum"
    assert max_level < plant.surge_tank.max_level, "Surge tank above maximum"

    print(f"✓ Load rejection simulation completed")
    print(f"✓ Surge tank range: {min_level:.1f} - {max_level:.1f} m")


def test_case_02_water_supply_basic():
    """Test Case 02: Water Supply Network - Basic Functionality"""
    from case_02_water_supply_network import WaterSupplyNetwork

    # Create network
    network = WaterSupplyNetwork(network_size='small')

    # Check components
    assert len(network.nodes) > 0, "No nodes created"
    assert len(network.pipes) > 0, "No pipes created"
    assert len(network.pumps) > 0, "No pumps created"
    assert network.water_tower is not None, "Water tower not created"

    print(f"✓ Network created: {len(network.nodes)} nodes, {len(network.pipes)} pipes")
    print(f"✓ Pumps: {len(network.pumps)}")


def test_case_02_water_supply_demand_pattern():
    """Test Case 02: Water Supply Network - Demand Pattern"""
    from case_02_water_supply_network import WaterSupplyNetwork

    # Create network
    network = WaterSupplyNetwork(network_size='small')

    # Test demand pattern
    demand_at_midnight = network.get_demand_multiplier(0.0)
    demand_at_morning_peak = network.get_demand_multiplier(8.0)
    demand_at_evening_peak = network.get_demand_multiplier(19.0)

    assert demand_at_midnight < demand_at_morning_peak, "Morning peak not higher than midnight"
    assert demand_at_midnight < demand_at_evening_peak, "Evening peak not higher than midnight"

    # Update demands
    network.update_demands(8.0)  # Morning peak
    total_demand = sum(node['current_demand'] for node_id, node in network.nodes.items()
                      if node_id not in ['SOURCE', 'TOWER'])

    assert total_demand > 0, "Total demand is zero"

    print(f"✓ Demand pattern working")
    print(f"✓ Midnight: {demand_at_midnight:.2f}x, Morning: {demand_at_morning_peak:.2f}x")
    print(f"✓ Total demand at 8am: {total_demand*1000:.1f} L/s")


def test_physics_turbine():
    """Test Physics: Turbine Models"""
    from physics.turbine import FrancisTurbine

    # Create Francis turbine
    turbine = FrancisTurbine(
        position=0.0,
        rated_power=50.0,  # MW
        rated_head=80.0,
        rated_flow=65.0,
        rated_speed=500.0
    )

    # Test power calculation
    P, eta, mode = turbine.calculate_power(
        Q=65.0,
        H=80.0,
        n=500.0,
        opening=0.8
    )

    assert P > 0, "Power is zero"
    assert 0 < eta < 1, f"Efficiency out of range: {eta}"

    print(f"✓ Turbine power: {P/1e6:.1f} MW")
    print(f"✓ Efficiency: {eta*100:.1f}%")


def test_physics_pump():
    """Test Physics: Pump Models"""
    from physics.pump import Pump

    # Create pump
    pump = Pump(
        name='TEST_PUMP',
        rated_flow=100.0,
        rated_head=50.0,
        rated_speed=1500.0
    )

    # Test head calculation
    H = pump.calculate_head(Q=80.0, n=1500.0)

    assert H > 0, "Head is zero"
    assert H > 40.0, "Head too low"

    # Test efficiency
    eta = pump.calculate_efficiency(Q=100.0, n=1500.0)
    assert 0 < eta < 1, f"Efficiency out of range: {eta}"

    print(f"✓ Pump head at 80 m³/s: {H:.1f} m")
    print(f"✓ Efficiency at rated point: {eta*100:.1f}%")


def test_physics_valve():
    """Test Physics: Valve Models"""
    from physics.valve import Valve

    # Create valve
    valve = Valve(
        name='TEST_VALVE',
        valve_type='linear',
        Cv_max=100.0
    )

    # Test flow coefficient
    Cv_50 = valve.get_Cv(opening=0.5)
    Cv_100 = valve.get_Cv(opening=1.0)

    assert Cv_50 == 50.0, "Linear valve Cv incorrect"
    assert Cv_100 == 100.0, "Full open Cv incorrect"

    # Test flow calculation
    Q = valve.calculate_flow(P_upstream=500000.0, P_downstream=100000.0, opening=0.5)

    assert Q > 0, "Flow is zero"

    print(f"✓ Valve Cv at 50%: {Cv_50}")
    print(f"✓ Flow at 400kPa drop: {Q:.3f} m³/s")


def test_physics_surge_tank():
    """Test Physics: Surge Tank Models"""
    from physics.surge_tank import SimpleSurgeTank

    # Create surge tank
    tank = SimpleSurgeTank(
        position=0.0,
        area=100.0,
        min_level=50.0,
        max_level=110.0,
        initial_level=80.0
    )

    # Initial state
    assert tank.water_level == 80.0, "Initial level incorrect"

    # Update water level
    Q_in = 10.0
    Q_out = 8.0
    dt = 1.0
    tank.update_water_level(dt, Q_in, Q_out)

    # Check level increased
    assert tank.water_level > 80.0, "Level should increase"

    expected_level = 80.0 + (Q_in - Q_out) * dt / tank.area
    assert abs(tank.water_level - expected_level) < 0.01, "Level calculation incorrect"

    print(f"✓ Initial level: 80.0 m")
    print(f"✓ After 1s: {tank.water_level:.2f} m")


def main():
    """Main test execution"""

    print(f"\n{'#'*70}")
    print(f"#{'  HydroClaude - Engineering Cases Test Suite  ':^68}#")
    print(f"#{'  工程案例测试套件  ':^68}#")
    print(f"{'#'*70}\n")

    runner = CaseTestRunner()

    # Test Case 01 - Hydropower Plant
    runner.run_test("Case 01 - Hydropower Basic", test_case_01_hydropower_basic)
    runner.run_test("Case 01 - Hydropower Simulation", test_case_01_hydropower_simulation)
    runner.run_test("Case 01 - Hydropower Load Rejection", test_case_01_hydropower_load_rejection)

    # Test Case 02 - Water Supply Network
    runner.run_test("Case 02 - Water Supply Basic", test_case_02_water_supply_basic)
    runner.run_test("Case 02 - Demand Pattern", test_case_02_water_supply_demand_pattern)

    # Test Physics Components
    runner.run_test("Physics - Turbine", test_physics_turbine)
    runner.run_test("Physics - Pump", test_physics_pump)
    runner.run_test("Physics - Valve", test_physics_valve)
    runner.run_test("Physics - Surge Tank", test_physics_surge_tank)

    # Print summary
    all_passed = runner.print_summary()

    if all_passed:
        print("🎉 All tests passed!")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
