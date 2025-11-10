"""
Standard Test Cases for HydroClaude Web
Collection of validated test cases for canal flow simulation
"""

# Test Case 1: Static Uniform Flow
TEST_CASE_1_STATIC_UNIFORM = {
    "name": "TC1 - Static Uniform Flow",
    "description": "静态均匀流：水体保持完全静止，验证质量守恒和数值稳定性",
    "config": {
        "width": 10.0,
        "length": 1000.0,
        "n_cells": 100,
        "manning_n": 0.0,
        "slope": 0.0,
        "t_end": 10.0,
        "dt_max": 0.1,
        "output_interval": 1.0,
        "initial_conditions": {
            "type": "uniform",
            "h": 5.0,
            "Q": 0.0
        },
        "boundary_conditions": {
            "upstream": {"type": "h", "value": 5.0},
            "downstream": {"type": "h", "value": 5.0}
        }
    },
    "expected": {
        "mass_conservation_error": {"max": 1e-10},
        "max_velocity": {"max": 1e-3},
        "converged": True,
        "final_mean_depth": {"value": 5.0, "tolerance": 0.01}
    }
}

# Test Case 2: Shallow Uniform Flow
TEST_CASE_2_SHALLOW_UNIFORM = {
    "name": "TC2 - Shallow Uniform Flow",
    "description": "浅水均匀流：较小水深的静态场景",
    "config": {
        "width": 10.0,
        "length": 500.0,
        "n_cells": 50,
        "manning_n": 0.0,
        "slope": 0.0,
        "t_end": 5.0,
        "dt_max": 0.05,
        "output_interval": 0.5,
        "initial_conditions": {
            "type": "uniform",
            "h": 1.0,
            "Q": 0.0
        },
        "boundary_conditions": {
            "upstream": {"type": "h", "value": 1.0},
            "downstream": {"type": "h", "value": 1.0}
        }
    },
    "expected": {
        "mass_conservation_error": {"max": 1e-10},
        "max_velocity": {"max": 1e-3},
        "converged": True,
        "final_mean_depth": {"value": 1.0, "tolerance": 0.01}
    }
}

# Test Case 3: Deep Uniform Flow
TEST_CASE_3_DEEP_UNIFORM = {
    "name": "TC3 - Deep Uniform Flow",
    "description": "深水均匀流：较大水深的静态场景",
    "config": {
        "width": 10.0,
        "length": 1000.0,
        "n_cells": 100,
        "manning_n": 0.0,
        "slope": 0.0,
        "t_end": 10.0,
        "dt_max": 0.1,
        "output_interval": 1.0,
        "initial_conditions": {
            "type": "uniform",
            "h": 10.0,
            "Q": 0.0
        },
        "boundary_conditions": {
            "upstream": {"type": "h", "value": 10.0},
            "downstream": {"type": "h", "value": 10.0}
        }
    },
    "expected": {
        "mass_conservation_error": {"max": 1e-10},
        "max_velocity": {"max": 1e-3},
        "converged": True,
        "final_mean_depth": {"value": 10.0, "tolerance": 0.01}
    }
}

# Test Case 4: Wide Channel Uniform Flow
TEST_CASE_4_WIDE_CHANNEL = {
    "name": "TC4 - Wide Channel Uniform Flow",
    "description": "宽渠道均匀流：验证不同渠道宽度",
    "config": {
        "width": 50.0,
        "length": 1000.0,
        "n_cells": 100,
        "manning_n": 0.0,
        "slope": 0.0,
        "t_end": 10.0,
        "dt_max": 0.1,
        "output_interval": 1.0,
        "initial_conditions": {
            "type": "uniform",
            "h": 5.0,
            "Q": 0.0
        },
        "boundary_conditions": {
            "upstream": {"type": "h", "value": 5.0},
            "downstream": {"type": "h", "value": 5.0}
        }
    },
    "expected": {
        "mass_conservation_error": {"max": 1e-10},
        "max_velocity": {"max": 1e-3},
        "converged": True,
        "final_mean_depth": {"value": 5.0, "tolerance": 0.01}
    }
}

# Test Case 5: Long Channel Uniform Flow
TEST_CASE_5_LONG_CHANNEL = {
    "name": "TC5 - Long Channel Uniform Flow",
    "description": "长渠道均匀流：验证较长的计算域",
    "config": {
        "width": 10.0,
        "length": 5000.0,
        "n_cells": 200,
        "manning_n": 0.0,
        "slope": 0.0,
        "t_end": 10.0,
        "dt_max": 0.1,
        "output_interval": 1.0,
        "initial_conditions": {
            "type": "uniform",
            "h": 5.0,
            "Q": 0.0
        },
        "boundary_conditions": {
            "upstream": {"type": "h", "value": 5.0},
            "downstream": {"type": "h", "value": 5.0}
        }
    },
    "expected": {
        "mass_conservation_error": {"max": 1e-9},
        "max_velocity": {"max": 1e-3},
        "converged": True,
        "final_mean_depth": {"value": 5.0, "tolerance": 0.01}
    }
}

# All test cases
ALL_TEST_CASES = [
    TEST_CASE_1_STATIC_UNIFORM,
    TEST_CASE_2_SHALLOW_UNIFORM,
    TEST_CASE_3_DEEP_UNIFORM,
    TEST_CASE_4_WIDE_CHANNEL,
    TEST_CASE_5_LONG_CHANNEL,
]

# Test suite metadata
TEST_SUITE_INFO = {
    "name": "HydroClaude Web Standard Test Suite",
    "version": "1.0.0",
    "description": "标准测试案例集，验证明渠均匀流仿真功能",
    "total_cases": len(ALL_TEST_CASES),
    "categories": {
        "uniform_flow": 5
    }
}
