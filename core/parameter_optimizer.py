#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Parameter Optimizer - Automatic Parameter Calibration

Provides tools for optimizing simulation parameters to match observed data.

Author: HydroClaude Development Team
Date: 2025-11-15
"""

import os
import sys
import json
import copy
from typing import Dict, Any, List, Tuple, Callable, Optional

import numpy as np

try:
    from scipy.optimize import minimize, differential_evolution
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False


class ParameterOptimizer:
    """
    Parameter optimization tool for hydraulic simulations.
    
    Features:
    - Multiple optimization algorithms
    - Custom objective functions
    - Constraint handling
    - Parallel evaluation support
    - Progress tracking
    """
    
    def __init__(self, config: Dict[str, Any], verbose: bool = True):
        """
        Initialize parameter optimizer.
        
        Args:
            config: Base configuration dictionary
            verbose: Enable verbose output
        """
        self.config = copy.deepcopy(config)
        self.verbose = verbose
        
        self.parameters = []  # List of parameters to optimize
        self.bounds = []      # Parameter bounds
        self.observed_data = None  # Observed data for comparison
        self.objective_func = None  # Objective function
        
        self.best_params = None
        self.best_score = np.inf
        self.iteration = 0
        self.history = []
    
    def add_parameter(self, path: str, bounds: Tuple[float, float], 
                     initial: Optional[float] = None):
        """
        Add a parameter to optimize.
        
        Args:
            path: Parameter path in config (e.g., 'canal.manning_n')
            bounds: (min, max) bounds for parameter
            initial: Initial value (default: midpoint of bounds)
        """
        if initial is None:
            initial = (bounds[0] + bounds[1]) / 2.0
        
        self.parameters.append({
            'path': path,
            'bounds': bounds,
            'initial': initial
        })
        self.bounds.append(bounds)
        
        if self.verbose:
            print(f"  Added parameter: {path}")
            print(f"    Bounds: [{bounds[0]:.6f}, {bounds[1]:.6f}]")
            print(f"    Initial: {initial:.6f}")
    
    def set_observed_data(self, data: Dict[str, np.ndarray]):
        """
        Set observed data for comparison.
        
        Args:
            data: Dictionary of observed arrays
                  e.g., {'position': [...], 'depth': [...]}
        """
        self.observed_data = data
        
        if self.verbose:
            print(f"  Observed data set:")
            for key, values in data.items():
                print(f"    {key}: {len(values)} points")
    
    def set_objective_function(self, func: Callable):
        """
        Set custom objective function.
        
        Args:
            func: Function(simulated, observed) -> float
                  Returns error value (lower is better)
        """
        self.objective_func = func
    
    def optimize(self, method: str = 'nelder-mead', 
                max_iterations: int = 100,
                tolerance: float = 1e-6) -> Dict[str, Any]:
        """
        Run optimization.
        
        Args:
            method: Optimization method
                   'nelder-mead', 'powell', 'cobyla', 'differential_evolution'
            max_iterations: Maximum iterations
            tolerance: Convergence tolerance
            
        Returns:
            Optimization results dictionary
        """
        if not self.parameters:
            raise ValueError("No parameters added for optimization")
        
        if self.observed_data is None:
            raise ValueError("No observed data set")
        
        if self.verbose:
            print(f"\n{'='*80}")
            print(f"  Starting Optimization")
            print(f"{'='*80}")
            print(f"  Method: {method}")
            print(f"  Parameters: {len(self.parameters)}")
            print(f"  Max iterations: {max_iterations}")
            print(f"  Tolerance: {tolerance}")
        
        # Initial parameter values
        x0 = [p['initial'] for p in self.parameters]
        
        # Reset iteration counter
        self.iteration = 0
        self.history = []
        
        # Choose optimization method
        if method == 'differential_evolution':
            if not SCIPY_AVAILABLE:
                raise ImportError("scipy required for differential_evolution")
            
            result = differential_evolution(
                self._objective_wrapper,
                bounds=self.bounds,
                maxiter=max_iterations,
                tol=tolerance,
                disp=self.verbose
            )
        else:
            if not SCIPY_AVAILABLE:
                # Use simple grid search as fallback
                result = self._grid_search(max_iterations)
            else:
                result = minimize(
                    self._objective_wrapper,
                    x0=x0,
                    method=method,
                    bounds=self.bounds,
                    options={
                        'maxiter': max_iterations,
                        'xatol': tolerance,
                        'fatol': tolerance,
                        'disp': self.verbose
                    }
                )
        
        # Extract results
        if SCIPY_AVAILABLE and hasattr(result, 'x'):
            optimal_params = result.x
            optimal_score = result.fun
            success = result.success
        else:
            optimal_params = result['x']
            optimal_score = result['fun']
            success = result['success']
        
        # Update config with optimal parameters
        optimized_config = self._apply_parameters(optimal_params)
        
        results = {
            'success': success,
            'optimal_parameters': {},
            'optimal_score': optimal_score,
            'iterations': self.iteration,
            'optimized_config': optimized_config,
            'history': self.history
        }
        
        # Store optimal parameter values by name
        for i, param in enumerate(self.parameters):
            results['optimal_parameters'][param['path']] = optimal_params[i]
        
        if self.verbose:
            print(f"\n{'='*80}")
            print(f"  Optimization Complete")
            print(f"{'='*80}")
            print(f"  Success: {success}")
            print(f"  Final score: {optimal_score:.6e}")
            print(f"  Iterations: {self.iteration}")
            print(f"\n  Optimal parameters:")
            for path, value in results['optimal_parameters'].items():
                print(f"    {path}: {value:.6f}")
        
        return results
    
    def _objective_wrapper(self, params: np.ndarray) -> float:
        """
        Wrapper for objective function evaluation.
        
        Args:
            params: Parameter values array
            
        Returns:
            Objective function value
        """
        self.iteration += 1
        
        # Apply parameters to config
        config = self._apply_parameters(params)
        
        # Run simulation
        try:
            from core.simulation_engine import SimulationEngine
            engine = SimulationEngine(config, verbose=False)
            results = engine.run()
            
            # Extract simulated data
            simulated = self._extract_simulated_data(results)
            
            # Calculate error
            if self.objective_func is not None:
                error = self.objective_func(simulated, self.observed_data)
            else:
                error = self._default_objective(simulated, self.observed_data)
            
            # Track history
            self.history.append({
                'iteration': self.iteration,
                'parameters': params.copy(),
                'score': error
            })
            
            # Update best
            if error < self.best_score:
                self.best_score = error
                self.best_params = params.copy()
            
            if self.verbose and self.iteration % 10 == 0:
                print(f"  Iteration {self.iteration}: score = {error:.6e}")
            
            return error
            
        except Exception as e:
            if self.verbose:
                print(f"  Iteration {self.iteration}: simulation failed ({str(e)})")
            return 1e10  # Large penalty for failed simulations
    
    def _apply_parameters(self, params: np.ndarray) -> Dict[str, Any]:
        """Apply parameter values to configuration"""
        config = copy.deepcopy(self.config)
        
        for i, param_def in enumerate(self.parameters):
            path = param_def['path']
            value = params[i]
            
            # Navigate to parameter location
            keys = path.split('.')
            obj = config
            for key in keys[:-1]:
                obj = obj[key]
            
            # Set value
            obj[keys[-1]] = float(value)
        
        return config
    
    def _extract_simulated_data(self, results: Dict[str, Any]) -> Dict[str, np.ndarray]:
        """Extract simulated data from results"""
        simulated = {}
        
        if 'universal_data_model' in results:
            spatial_data = results['universal_data_model']['data'].get('spatial', {})
            for key, value in spatial_data.items():
                simulated[key] = value
        
        return simulated
    
    def _default_objective(self, simulated: Dict[str, np.ndarray], 
                          observed: Dict[str, np.ndarray]) -> float:
        """
        Default objective function: RMSE of depth.
        
        Args:
            simulated: Simulated data dictionary
            observed: Observed data dictionary
            
        Returns:
            Root mean square error
        """
        # Interpolate simulated data to observed positions
        if 'depth' not in simulated or 'depth' not in observed:
            return 1e10
        
        if 'position' not in simulated or 'position' not in observed:
            return 1e10
        
        sim_pos = simulated['position']
        sim_depth = simulated['depth']
        obs_pos = observed['position']
        obs_depth = observed['depth']
        
        # Interpolate simulated to observed positions
        sim_depth_interp = np.interp(obs_pos, sim_pos, sim_depth)
        
        # Calculate RMSE
        rmse = np.sqrt(np.mean((sim_depth_interp - obs_depth)**2))
        
        return rmse
    
    def _grid_search(self, max_iterations: int) -> Dict[str, Any]:
        """Simple grid search fallback when scipy not available"""
        n_params = len(self.parameters)
        n_points = int(max_iterations ** (1.0 / n_params))
        
        if self.verbose:
            print(f"  Using grid search: {n_points} points per parameter")
        
        # Generate grid
        grids = []
        for bounds in self.bounds:
            grids.append(np.linspace(bounds[0], bounds[1], n_points))
        
        # Evaluate grid points
        best_params = None
        best_score = np.inf
        
        def evaluate_point(indices):
            nonlocal best_params, best_score
            params = np.array([grids[i][indices[i]] for i in range(n_params)])
            score = self._objective_wrapper(params)
            if score < best_score:
                best_score = score
                best_params = params
        
        # Simple nested loop for small dimensions
        if n_params == 1:
            for i in range(n_points):
                evaluate_point([i])
        elif n_params == 2:
            for i in range(n_points):
                for j in range(n_points):
                    evaluate_point([i, j])
        elif n_params == 3:
            for i in range(n_points):
                for j in range(n_points):
                    for k in range(n_points):
                        evaluate_point([i, j, k])
        else:
            # For higher dimensions, use random sampling
            for _ in range(max_iterations):
                indices = [np.random.randint(0, n_points) for _ in range(n_params)]
                evaluate_point(indices)
        
        return {
            'x': best_params,
            'fun': best_score,
            'success': True
        }
    
    def save_results(self, results: Dict[str, Any], filepath: str):
        """
        Save optimization results to JSON file.
        
        Args:
            results: Optimization results
            filepath: Output file path
        """
        # Convert numpy arrays to lists for JSON serialization
        results_copy = copy.deepcopy(results)
        
        if 'history' in results_copy:
            for entry in results_copy['history']:
                if 'parameters' in entry:
                    entry['parameters'] = entry['parameters'].tolist()
        
        with open(filepath, 'w') as f:
            json.dump(results_copy, f, indent=2)
        
        if self.verbose:
            print(f"  Results saved to: {filepath}")


def optimize_manning_n(config: Dict[str, Any], 
                      observed_depth: np.ndarray,
                      observed_positions: np.ndarray,
                      verbose: bool = True) -> Dict[str, Any]:
    """
    Convenience function to optimize Manning's n coefficient.
    
    Args:
        config: Base configuration
        observed_depth: Observed water depths
        observed_positions: Observation positions
        verbose: Enable verbose output
        
    Returns:
        Optimization results
    """
    optimizer = ParameterOptimizer(config, verbose=verbose)
    
    # Add Manning's n as parameter (typical range: 0.010 - 0.050)
    optimizer.add_parameter('canal.manning_n', bounds=(0.010, 0.050))
    
    # Set observed data
    optimizer.set_observed_data({
        'position': observed_positions,
        'depth': observed_depth
    })
    
    # Run optimization
    results = optimizer.optimize(method='nelder-mead', max_iterations=50)
    
    return results


if __name__ == '__main__':
    print("Parameter Optimizer Test")
    print(f"SciPy Available: {SCIPY_AVAILABLE}")
    
    # Create test configuration
    test_config = {
        'simulation': {'type': 'steady', 'mode': 'single_canal'},
        'canal': {
            'length': 1000,
            'width': 10,
            'slope': 0.001,
            'manning_n': 0.025
        },
        'solver': {'method': 'hydrostatic'},
        'boundary_conditions': {
            'upstream': {'type': 'flow', 'value': 8.0},
            'downstream': {'type': 'depth', 'method': 'uniform_flow'}
        }
    }
    
    # Create "observed" data (synthetic)
    obs_pos = np.linspace(0, 1000, 20)
    obs_depth = np.ones(20) * 2.0 + np.random.randn(20) * 0.1
    
    print("\n✅ Test configuration created")
    print(f"✅ Test optimization ready (requires dependencies)")
