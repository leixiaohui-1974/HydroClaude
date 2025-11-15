#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HydroClaude Basic Test Suite

Tests the core functionality of the unified architecture.

Usage:
    python3 test_basic.py
    python3 test_basic.py --verbose
"""

import sys
import os
import json
import tempfile
import shutil

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def print_header(msg):
    """Print test header"""
    print("\n" + "=" * 80)
    print(f"  {msg}")
    print("=" * 80)

def print_success(msg):
    """Print success message"""
    print(f"  ✅ {msg}")

def print_error(msg):
    """Print error message"""
    print(f"  ❌ {msg}")

def print_info(msg):
    """Print info message"""
    print(f"     {msg}")

class TestResults:
    """Track test results"""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
    
    def add_pass(self, test_name):
        self.passed += 1
        print_success(f"{test_name}")
    
    def add_fail(self, test_name, error):
        self.failed += 1
        self.errors.append((test_name, error))
        print_error(f"{test_name}: {error}")
    
    def summary(self):
        total = self.passed + self.failed
        print_header("Test Summary")
        print(f"  Total: {total}")
        print(f"  Passed: {self.passed} ({self.passed/total*100:.1f}%)")
        print(f"  Failed: {self.failed} ({self.failed/total*100:.1f}%)")
        
        if self.errors:
            print("\n  Failed Tests:")
            for test_name, error in self.errors:
                print(f"    - {test_name}: {error}")
        
        return self.failed == 0

# Test 1: Import core modules
def test_imports(results):
    """Test importing core modules"""
    print_header("Test 1: Core Module Imports")
    
    try:
        from core.config_parser import ConfigParser
        results.add_pass("ConfigParser import")
    except Exception as e:
        results.add_fail("ConfigParser import", str(e))
    
    try:
        from core.simulation_engine import SimulationEngine
        results.add_pass("SimulationEngine import")
    except Exception as e:
        results.add_fail("SimulationEngine import", str(e))
    
    try:
        from core.output_manager import OutputManager
        results.add_pass("OutputManager import")
    except Exception as e:
        results.add_fail("OutputManager import", str(e))

# Test 2: Configuration parser
def test_config_parser(results):
    """Test configuration parser"""
    print_header("Test 2: Configuration Parser")
    
    try:
        from core.config_parser import ConfigParser
        
        # Create a minimal config
        config = {
            "simulation": {"type": "steady", "mode": "single_canal"},
            "canal": {
                "length": 1000,
                "width": 10,
                "slope": 0.001,
                "manning_n": 0.025
            },
            "solver": {"method": "hydrostatic"},
            "boundary_conditions": {
                "upstream": {"type": "flow", "value": 8.0},
                "downstream": {"type": "depth", "method": "uniform_flow"}
            }
        }
        
        # Write to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config, f)
            temp_file = f.name
        
        try:
            # Parse config
            parser = ConfigParser(verbose=False)
            parsed_config = parser.parse(temp_file)
            
            # Check basic fields
            assert parsed_config['simulation']['type'] == 'steady'
            assert parsed_config['canal']['length'] == 1000
            
            results.add_pass("Configuration parsing")
            
            # Check defaults filled
            assert 'output' in parsed_config
            assert 'metadata' in parsed_config
            results.add_pass("Default values filled")
            
        finally:
            os.unlink(temp_file)
            
    except Exception as e:
        results.add_fail("Configuration parser", str(e))

# Test 3: Template files exist
def test_templates(results):
    """Test template files"""
    print_header("Test 3: Template Files")
    
    template_dir = os.path.join(os.path.dirname(__file__), 'templates')
    
    files_to_check = [
        'hydro_viewer.js',
        'index_template.html',
        'styles.css'
    ]
    
    for filename in files_to_check:
        filepath = os.path.join(template_dir, filename)
        if os.path.exists(filepath):
            results.add_pass(f"Template exists: {filename}")
        else:
            results.add_fail(f"Template missing: {filename}", "File not found")

# Test 4: Example configs exist
def test_example_configs(results):
    """Test example configurations"""
    print_header("Test 4: Example Configurations")
    
    config_dir = os.path.join(os.path.dirname(__file__), 'examples_config')
    
    configs_to_check = [
        '01_steady_canal.json',
        '02_gate_flow.json',
        '03_unsteady_flow.json'
    ]
    
    for filename in configs_to_check:
        filepath = os.path.join(config_dir, filename)
        if os.path.exists(filepath):
            # Try to load it
            try:
                with open(filepath, 'r') as f:
                    config = json.load(f)
                results.add_pass(f"Example config valid: {filename}")
            except Exception as e:
                results.add_fail(f"Example config invalid: {filename}", str(e))
        else:
            results.add_fail(f"Example config missing: {filename}", "File not found")

# Test 5: Solver imports
def test_solver_imports(results):
    """Test solver imports"""
    print_header("Test 5: Solver Imports")
    
    try:
        from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver
        results.add_pass("HydrostaticCanalSolver import")
    except Exception as e:
        results.add_fail("HydrostaticCanalSolver import", str(e))
    
    try:
        from solvers.godunov_fvm_solver import GodunvFVMSolver
        results.add_pass("GodunvFVMSolver import")
    except Exception as e:
        results.add_fail("GodunvFVMSolver import", str(e))
    
    try:
        from solvers.gate import SluiceGate, BroadCrestedWeir
        results.add_pass("Hydraulic structures import")
    except Exception as e:
        results.add_fail("Hydraulic structures import", str(e))

# Test 6: Utility imports
def test_utility_imports(results):
    """Test utility imports"""
    print_header("Test 6: Utility Imports")
    
    try:
        from utils.canal_utils import compute_steady_uniform_flow
        results.add_pass("canal_utils import")
    except Exception as e:
        results.add_fail("canal_utils import", str(e))
    
    try:
        from utils.result_validator import ResultValidator
        results.add_pass("result_validator import")
    except Exception as e:
        results.add_fail("result_validator import", str(e))
    
    try:
        from utils.plot_helper import PlotHelper
        results.add_pass("plot_helper import")
    except Exception as e:
        results.add_fail("plot_helper import", str(e))

# Test 7: Dependencies
def test_dependencies(results):
    """Test required dependencies"""
    print_header("Test 7: Required Dependencies")
    
    required_packages = [
        'numpy',
        'pandas',
        'matplotlib',
        'jsonschema'
    ]
    
    for package in required_packages:
        try:
            __import__(package)
            results.add_pass(f"Dependency installed: {package}")
        except ImportError:
            results.add_fail(f"Dependency missing: {package}", "Not installed")
    
    # Optional packages
    optional_packages = ['h5py', 'scipy']
    
    for package in optional_packages:
        try:
            __import__(package)
            print_info(f"Optional dependency installed: {package}")
        except ImportError:
            print_info(f"Optional dependency not installed: {package} (OK)")

# Test 8: Main engine script
def test_main_engine(results):
    """Test main engine script"""
    print_header("Test 8: Main Engine Script")
    
    engine_file = os.path.join(os.path.dirname(__file__), 'hydro_engine.py')
    
    if os.path.exists(engine_file):
        results.add_pass("hydro_engine.py exists")
        
        # Check if it's executable
        if os.access(engine_file, os.R_OK):
            results.add_pass("hydro_engine.py is readable")
        else:
            results.add_fail("hydro_engine.py permissions", "Not readable")
            
    else:
        results.add_fail("hydro_engine.py", "File not found")

# Main test function
def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("  HydroClaude Basic Test Suite")
    print("  Version: 1.0.0")
    print("=" * 80)
    
    results = TestResults()
    
    # Run all tests
    test_imports(results)
    test_config_parser(results)
    test_templates(results)
    test_example_configs(results)
    test_solver_imports(results)
    test_utility_imports(results)
    test_dependencies(results)
    test_main_engine(results)
    
    # Summary
    success = results.summary()
    
    print("\n" + "=" * 80)
    if success:
        print("  ✅ All tests passed!")
    else:
        print("  ❌ Some tests failed")
    print("=" * 80 + "\n")
    
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())
