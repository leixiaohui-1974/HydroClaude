#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Batch Simulator - Run Multiple Simulations Efficiently

Provides tools for running multiple simulations in parallel or sequence.

Author: HydroClaude Development Team
Date: 2025-11-15
"""

import os
import sys
import json
import time
import copy
from typing import List, Dict, Any, Optional
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)


class BatchSimulator:
    """
    Batch simulation manager.
    
    Features:
    - Sequential or parallel execution
    - Progress tracking
    - Error handling
    - Result aggregation
    - Performance statistics
    """
    
    def __init__(self, verbose: bool = True):
        """
        Initialize batch simulator.
        
        Args:
            verbose: Enable verbose output
        """
        self.verbose = verbose
        self.cases = []
        self.results = []
        self.stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'start_time': None,
            'end_time': None,
            'total_time': 0
        }
    
    def add_case(self, name: str, config: Dict[str, Any]):
        """
        Add a simulation case.
        
        Args:
            name: Case name
            config: Configuration dictionary
        """
        self.cases.append({
            'name': name,
            'config': config,
            'index': len(self.cases)
        })
        
        if self.verbose:
            print(f"  Added case: {name}")
    
    def add_cases_from_directory(self, directory: str):
        """
        Add all JSON configuration files from a directory.
        
        Args:
            directory: Directory path
        """
        if not os.path.exists(directory):
            raise FileNotFoundError(f"Directory not found: {directory}")
        
        count = 0
        for filename in sorted(os.listdir(directory)):
            if filename.endswith('.json'):
                filepath = os.path.join(directory, filename)
                with open(filepath, 'r') as f:
                    config = json.load(f)
                
                name = os.path.splitext(filename)[0]
                self.add_case(name, config)
                count += 1
        
        if self.verbose:
            print(f"  Loaded {count} cases from: {directory}")
    
    def add_parameter_sweep(self, base_config: Dict[str, Any],
                           parameter_path: str,
                           values: List[float],
                           name_prefix: str = "sweep"):
        """
        Add a parameter sweep (varying one parameter).
        
        Args:
            base_config: Base configuration
            parameter_path: Parameter path (e.g., 'canal.manning_n')
            values: List of parameter values
            name_prefix: Prefix for case names
        """
        for i, value in enumerate(values):
            config = copy.deepcopy(base_config)
            
            # Navigate to parameter location
            keys = parameter_path.split('.')
            obj = config
            for key in keys[:-1]:
                obj = obj[key]
            
            # Set value
            obj[keys[-1]] = value
            
            # Create case name
            name = f"{name_prefix}_{parameter_path.replace('.', '_')}_{value:.4f}"
            
            self.add_case(name, config)
        
        if self.verbose:
            print(f"  Added parameter sweep: {len(values)} cases")
    
    def run_sequential(self) -> List[Dict[str, Any]]:
        """
        Run all cases sequentially.
        
        Returns:
            List of results
        """
        if not self.cases:
            raise ValueError("No cases added")
        
        self.stats['total'] = len(self.cases)
        self.stats['start_time'] = datetime.now()
        
        if self.verbose:
            print(f"\n{'='*80}")
            print(f"  Starting Batch Simulation (Sequential)")
            print(f"{'='*80}")
            print(f"  Total cases: {self.stats['total']}")
        
        self.results = []
        for i, case in enumerate(self.cases, 1):
            if self.verbose:
                print(f"\n  [{i}/{self.stats['total']}] Running: {case['name']}")
            
            result = self._run_single_case(case)
            self.results.append(result)
            
            if result['success']:
                self.stats['success'] += 1
            else:
                self.stats['failed'] += 1
        
        self.stats['end_time'] = datetime.now()
        self.stats['total_time'] = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
        
        self._print_summary()
        
        return self.results
    
    def run_parallel(self, max_workers: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Run all cases in parallel.
        
        Args:
            max_workers: Maximum parallel workers (default: CPU count)
            
        Returns:
            List of results
        """
        if not self.cases:
            raise ValueError("No cases added")
        
        self.stats['total'] = len(self.cases)
        self.stats['start_time'] = datetime.now()
        
        if max_workers is None:
            max_workers = os.cpu_count() or 1
        
        if self.verbose:
            print(f"\n{'='*80}")
            print(f"  Starting Batch Simulation (Parallel)")
            print(f"{'='*80}")
            print(f"  Total cases: {self.stats['total']}")
            print(f"  Max workers: {max_workers}")
        
        self.results = [None] * len(self.cases)
        
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            # Submit all cases
            futures = {}
            for case in self.cases:
                future = executor.submit(self._run_single_case, case)
                futures[future] = case['index']
            
            # Collect results as they complete
            completed = 0
            for future in as_completed(futures):
                index = futures[future]
                result = future.result()
                self.results[index] = result
                
                completed += 1
                if result['success']:
                    self.stats['success'] += 1
                else:
                    self.stats['failed'] += 1
                
                if self.verbose:
                    status = "✅" if result['success'] else "❌"
                    print(f"  [{completed}/{self.stats['total']}] {status} {result['name']}")
        
        self.stats['end_time'] = datetime.now()
        self.stats['total_time'] = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
        
        self._print_summary()
        
        return self.results
    
    def _run_single_case(self, case: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run a single simulation case.
        
        Args:
            case: Case dictionary
            
        Returns:
            Result dictionary
        """
        start_time = time.time()
        
        result = {
            'name': case['name'],
            'index': case['index'],
            'success': False,
            'error': None,
            'time': 0,
            'results': None
        }
        
        try:
            from core.config_parser import ConfigParser
            from core.simulation_engine import SimulationEngine
            from core.output_manager import OutputManager
            
            # Parse configuration
            # Note: We already have a dict, so we need to write it temporarily
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(case['config'], f)
                temp_config_file = f.name
            
            try:
                parser = ConfigParser(verbose=False)
                config = parser.parse(temp_config_file)
                
                # Run simulation
                engine = SimulationEngine(config, verbose=False)
                sim_results = engine.run()
                
                # Save outputs (optional, can be disabled for speed)
                # output_manager = OutputManager(config, sim_results, verbose=False)
                # output_manager.save_all()
                
                result['success'] = True
                result['results'] = sim_results
                
            finally:
                os.unlink(temp_config_file)
            
        except Exception as e:
            result['error'] = str(e)
        
        result['time'] = time.time() - start_time
        
        return result
    
    def _print_summary(self):
        """Print batch simulation summary"""
        if not self.verbose:
            return
        
        print(f"\n{'='*80}")
        print(f"  Batch Simulation Complete")
        print(f"{'='*80}")
        print(f"  Total cases:    {self.stats['total']}")
        print(f"  Successful:     {self.stats['success']} ({self.stats['success']/self.stats['total']*100:.1f}%)")
        print(f"  Failed:         {self.stats['failed']} ({self.stats['failed']/self.stats['total']*100:.1f}%)")
        print(f"  Total time:     {self.stats['total_time']:.2f} s")
        print(f"  Average time:   {self.stats['total_time']/self.stats['total']:.2f} s/case")
        print(f"  Start:          {self.stats['start_time'].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  End:            {self.stats['end_time'].strftime('%Y-%m-%d %H:%M:%S')}")
    
    def save_results(self, filepath: str):
        """
        Save batch results to JSON file.
        
        Args:
            filepath: Output file path
        """
        output = {
            'stats': {
                'total': self.stats['total'],
                'success': self.stats['success'],
                'failed': self.stats['failed'],
                'total_time': self.stats['total_time'],
                'start_time': self.stats['start_time'].isoformat() if self.stats['start_time'] else None,
                'end_time': self.stats['end_time'].isoformat() if self.stats['end_time'] else None
            },
            'results': []
        }
        
        for result in self.results:
            # Create simplified result (without full simulation data)
            simplified = {
                'name': result['name'],
                'index': result['index'],
                'success': result['success'],
                'error': result['error'],
                'time': result['time']
            }
            
            # Add key metrics if available
            if result['success'] and result['results']:
                sim_results = result['results']
                if 'validation' in sim_results:
                    simplified['validation'] = sim_results['validation']
            
            output['results'].append(simplified)
        
        with open(filepath, 'w') as f:
            json.dump(output, f, indent=2)
        
        if self.verbose:
            print(f"  Batch results saved to: {filepath}")
    
    def get_successful_results(self) -> List[Dict[str, Any]]:
        """Get only successful results"""
        return [r for r in self.results if r['success']]
    
    def get_failed_results(self) -> List[Dict[str, Any]]:
        """Get only failed results"""
        return [r for r in self.results if not r['success']]
    
    def generate_comparison_report(self, output_dir: str):
        """
        Generate a comparison report for all successful cases.
        
        Args:
            output_dir: Output directory
        """
        successful = self.get_successful_results()
        
        if not successful:
            print("  No successful results to compare")
            return
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Extract key metrics from each case
        comparison_data = []
        for result in successful:
            sim_results = result['results']
            
            metrics = {
                'name': result['name'],
                'time': result['time']
            }
            
            # Extract validation metrics
            if 'validation' in sim_results:
                val = sim_results['validation']
                for key in ['mass_error_percent', 'convergence_iterations']:
                    if key in val:
                        metrics[key] = val[key]
            
            # Extract spatial extrema
            if 'universal_data_model' in sim_results:
                spatial = sim_results['universal_data_model']['data'].get('spatial', {})
                for var in ['depth', 'velocity', 'froude']:
                    if var in spatial:
                        metrics[f'{var}_min'] = float(spatial[var].min())
                        metrics[f'{var}_max'] = float(spatial[var].max())
                        metrics[f'{var}_mean'] = float(spatial[var].mean())
            
            comparison_data.append(metrics)
        
        # Save comparison table
        comparison_file = os.path.join(output_dir, 'comparison.json')
        with open(comparison_file, 'w') as f:
            json.dump(comparison_data, f, indent=2)
        
        if self.verbose:
            print(f"  Comparison report saved to: {comparison_file}")


def main():
    """Command-line interface for batch simulator"""
    import argparse
    
    parser = argparse.ArgumentParser(description='HydroClaude Batch Simulator')
    parser.add_argument('directory', help='Directory containing configuration files')
    parser.add_argument('-o', '--output', default='batch_results',
                       help='Output directory (default: batch_results)')
    parser.add_argument('--parallel', action='store_true',
                       help='Run simulations in parallel')
    parser.add_argument('--workers', type=int, default=None,
                       help='Number of parallel workers')
    parser.add_argument('--quiet', action='store_true',
                       help='Suppress output')
    
    args = parser.parse_args()
    
    # Create batch simulator
    batch = BatchSimulator(verbose=not args.quiet)
    
    # Load cases
    batch.add_cases_from_directory(args.directory)
    
    # Run simulations
    if args.parallel:
        batch.run_parallel(max_workers=args.workers)
    else:
        batch.run_sequential()
    
    # Save results
    os.makedirs(args.output, exist_ok=True)
    batch.save_results(os.path.join(args.output, 'batch_results.json'))
    batch.generate_comparison_report(args.output)
    
    print(f"\n✅ Batch simulation complete!")
    print(f"   Results saved to: {args.output}")


if __name__ == '__main__':
    if len(sys.argv) > 1:
        main()
    else:
        print("Batch Simulator")
        print("Usage: python batch_simulator.py <config_directory> [options]")
        print("\nFor help: python batch_simulator.py -h")
