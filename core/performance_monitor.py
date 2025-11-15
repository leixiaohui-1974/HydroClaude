#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Performance Monitor - Track and Analyze Simulation Performance

Provides tools for monitoring and profiling simulation performance.

Author: HydroClaude Development Team
Date: 2025-11-15
"""

import time
import sys
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from contextlib import contextmanager


class PerformanceMonitor:
    """
    Performance monitoring and profiling tool.
    
    Features:
    - Timer contexts for code sections
    - Memory usage tracking
    - Performance statistics
    - Profile reports
    """
    
    def __init__(self, name: str = "simulation"):
        """
        Initialize performance monitor.
        
        Args:
            name: Monitor name
        """
        self.name = name
        self.timers = {}
        self.counters = {}
        self.start_time = None
        self.end_time = None
        self.memory_snapshots = []
    
    def start(self):
        """Start overall monitoring"""
        self.start_time = time.time()
        self._take_memory_snapshot("start")
    
    def stop(self):
        """Stop overall monitoring"""
        self.end_time = time.time()
        self._take_memory_snapshot("end")
    
    @contextmanager
    def timer(self, section: str):
        """
        Context manager for timing code sections.
        
        Args:
            section: Section name
            
        Usage:
            with monitor.timer('initialization'):
                # code to time
                pass
        """
        start = time.time()
        
        try:
            yield
        finally:
            elapsed = time.time() - start
            
            if section not in self.timers:
                self.timers[section] = []
            
            self.timers[section].append(elapsed)
    
    def count(self, event: str, value: int = 1):
        """
        Increment a counter.
        
        Args:
            event: Event name
            value: Increment value
        """
        if event not in self.counters:
            self.counters[event] = 0
        
        self.counters[event] += value
    
    def _take_memory_snapshot(self, label: str):
        """Take a memory usage snapshot"""
        try:
            import psutil
            process = psutil.Process(os.getpid())
            memory_mb = process.memory_info().rss / 1024 / 1024
            
            self.memory_snapshots.append({
                'label': label,
                'time': time.time(),
                'memory_mb': memory_mb
            })
        except ImportError:
            # psutil not available, skip memory monitoring
            pass
    
    def get_total_time(self) -> float:
        """Get total monitoring time"""
        if self.start_time is None:
            return 0.0
        
        end = self.end_time if self.end_time else time.time()
        return end - self.start_time
    
    def get_section_stats(self, section: str) -> Dict[str, float]:
        """
        Get statistics for a timed section.
        
        Args:
            section: Section name
            
        Returns:
            Statistics dictionary
        """
        if section not in self.timers:
            return {}
        
        times = self.timers[section]
        
        import numpy as np
        return {
            'count': len(times),
            'total': sum(times),
            'mean': np.mean(times),
            'std': np.std(times),
            'min': min(times),
            'max': max(times)
        }
    
    def generate_report(self) -> str:
        """
        Generate performance report.
        
        Returns:
            Report string
        """
        lines = []
        lines.append("=" * 80)
        lines.append(f"  Performance Report: {self.name}")
        lines.append("=" * 80)
        
        # Overall time
        total_time = self.get_total_time()
        lines.append(f"\nTotal Time: {total_time:.3f} s")
        
        # Timer sections
        if self.timers:
            lines.append("\nTimed Sections:")
            lines.append("-" * 80)
            lines.append(f"{'Section':<30} {'Count':>8} {'Total':>12} {'Mean':>12} {'Std':>12}")
            lines.append("-" * 80)
            
            for section in sorted(self.timers.keys()):
                stats = self.get_section_stats(section)
                lines.append(
                    f"{section:<30} "
                    f"{stats['count']:>8d} "
                    f"{stats['total']:>12.3f} "
                    f"{stats['mean']:>12.6f} "
                    f"{stats['std']:>12.6f}"
                )
            
            lines.append("-" * 80)
            
            # Calculate percentage of total time
            accounted_time = sum(sum(times) for times in self.timers.values())
            if total_time > 0:
                percentage = (accounted_time / total_time) * 100
                lines.append(f"Accounted time: {accounted_time:.3f} s ({percentage:.1f}%)")
        
        # Counters
        if self.counters:
            lines.append("\nCounters:")
            lines.append("-" * 80)
            for event in sorted(self.counters.keys()):
                lines.append(f"{event:<30} {self.counters[event]:>10d}")
            lines.append("-" * 80)
        
        # Memory snapshots
        if self.memory_snapshots:
            lines.append("\nMemory Usage:")
            lines.append("-" * 80)
            for snapshot in self.memory_snapshots:
                lines.append(f"{snapshot['label']:<20} {snapshot['memory_mb']:>10.2f} MB")
            
            if len(self.memory_snapshots) >= 2:
                delta = self.memory_snapshots[-1]['memory_mb'] - self.memory_snapshots[0]['memory_mb']
                lines.append(f"{'Delta':<20} {delta:>+10.2f} MB")
            lines.append("-" * 80)
        
        lines.append("")
        
        return "\n".join(lines)
    
    def save_report(self, filepath: str):
        """
        Save performance report to file.
        
        Args:
            filepath: Output file path
        """
        report = self.generate_report()
        
        with open(filepath, 'w') as f:
            f.write(report)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert monitor data to dictionary.
        
        Returns:
            Dictionary of performance data
        """
        return {
            'name': self.name,
            'total_time': self.get_total_time(),
            'sections': {
                section: self.get_section_stats(section)
                for section in self.timers.keys()
            },
            'counters': self.counters.copy(),
            'memory_snapshots': self.memory_snapshots.copy()
        }


class SimulationProfiler:
    """
    High-level profiler for complete simulations.
    
    Automatically instruments simulation runs.
    """
    
    def __init__(self):
        """Initialize simulation profiler"""
        self.monitor = PerformanceMonitor("simulation")
        self.enabled = True
    
    def enable(self):
        """Enable profiling"""
        self.enabled = True
    
    def disable(self):
        """Disable profiling"""
        self.enabled = False
    
    @contextmanager
    def profile_simulation(self, config: Dict[str, Any]):
        """
        Context manager for profiling a complete simulation.
        
        Args:
            config: Simulation configuration
            
        Usage:
            with profiler.profile_simulation(config):
                # run simulation
                pass
        """
        if not self.enabled:
            yield
            return
        
        self.monitor = PerformanceMonitor(
            f"simulation_{config['simulation']['type']}"
        )
        self.monitor.start()
        
        try:
            yield self.monitor
        finally:
            self.monitor.stop()
    
    def get_report(self) -> str:
        """Get performance report"""
        return self.monitor.generate_report()
    
    def save_report(self, output_dir: str):
        """
        Save performance report.
        
        Args:
            output_dir: Output directory
        """
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filepath = os.path.join(output_dir, f'performance_{timestamp}.txt')
        
        self.monitor.save_report(filepath)
        
        return filepath


# Global profiler instance
_profiler = SimulationProfiler()


def get_profiler() -> SimulationProfiler:
    """Get global profiler instance"""
    return _profiler


if __name__ == '__main__':
    # Test performance monitor
    print("Performance Monitor Test\n")
    
    monitor = PerformanceMonitor("test")
    monitor.start()
    
    # Test timer
    with monitor.timer('test_section_1'):
        time.sleep(0.1)
    
    with monitor.timer('test_section_2'):
        time.sleep(0.05)
    
    # Test multiple calls to same section
    for i in range(5):
        with monitor.timer('loop'):
            time.sleep(0.01)
    
    # Test counters
    monitor.count('iterations', 100)
    monitor.count('converged', 1)
    
    monitor.stop()
    
    # Generate report
    print(monitor.generate_report())
    
    print("✅ Performance monitor test complete")
