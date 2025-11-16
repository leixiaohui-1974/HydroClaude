#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Real-Time Monitoring System

Provides real-time monitoring and alerting for simulation execution.

Author: HydroClaude Development Team
Date: 2025-11-15
"""

import time
import queue
import threading
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from collections import deque


class SimulationMonitor:
    """
    Real-time simulation monitoring system.
    
    Features:
    - Real-time progress tracking
    - Performance monitoring
    - Alert system
    - Event logging
    - Metrics collection
    """
    
    def __init__(self, max_history: int = 1000):
        """
        Initialize simulation monitor.
        
        Args:
            max_history: Maximum event history size
        """
        self.max_history = max_history
        
        self.events = deque(maxlen=max_history)
        self.metrics = {}
        self.alerts = []
        self.callbacks = []
        
        self.is_monitoring = False
        self.monitor_thread = None
        
        self._lock = threading.Lock()
    
    def start(self):
        """Start monitoring"""
        if not self.is_monitoring:
            self.is_monitoring = True
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
    
    def stop(self):
        """Stop monitoring"""
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)
    
    def log_event(self, event_type: str, data: Dict[str, Any]):
        """
        Log an event.
        
        Args:
            event_type: Event type (e.g., 'start', 'progress', 'complete', 'error')
            data: Event data
        """
        event = {
            'type': event_type,
            'timestamp': datetime.now().isoformat(),
            'data': data
        }
        
        with self._lock:
            self.events.append(event)
        
        # Trigger callbacks
        self._trigger_callbacks(event)
        
        # Check alerts
        self._check_alerts(event)
    
    def update_metric(self, name: str, value: float):
        """
        Update a metric value.
        
        Args:
            name: Metric name
            value: Metric value
        """
        with self._lock:
            if name not in self.metrics:
                self.metrics[name] = {
                    'current': value,
                    'history': deque(maxlen=100),
                    'min': value,
                    'max': value,
                    'avg': value
                }
            
            metric = self.metrics[name]
            metric['current'] = value
            metric['history'].append(value)
            metric['min'] = min(metric['min'], value)
            metric['max'] = max(metric['max'], value)
            metric['avg'] = sum(metric['history']) / len(metric['history'])
    
    def add_alert(self, name: str, condition: Callable[[Dict[str, Any]], bool],
                 message: str, level: str = 'warning'):
        """
        Add an alert condition.
        
        Args:
            name: Alert name
            condition: Condition function (returns True when alert should fire)
            message: Alert message
            level: Alert level ('info', 'warning', 'error')
        """
        self.alerts.append({
            'name': name,
            'condition': condition,
            'message': message,
            'level': level,
            'triggered': False
        })
    
    def add_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """
        Add event callback.
        
        Args:
            callback: Callback function (receives event dict)
        """
        self.callbacks.append(callback)
    
    def get_events(self, event_type: Optional[str] = None,
                  limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent events.
        
        Args:
            event_type: Filter by event type
            limit: Maximum events to return
            
        Returns:
            List of events
        """
        with self._lock:
            events = list(self.events)
        
        if event_type:
            events = [e for e in events if e['type'] == event_type]
        
        return events[-limit:]
    
    def get_metrics(self) -> Dict[str, Dict[str, float]]:
        """Get current metrics"""
        with self._lock:
            return {
                name: {
                    'current': m['current'],
                    'min': m['min'],
                    'max': m['max'],
                    'avg': m['avg']
                }
                for name, m in self.metrics.items()
            }
    
    def get_triggered_alerts(self) -> List[Dict[str, Any]]:
        """Get triggered alerts"""
        return [a for a in self.alerts if a['triggered']]
    
    def clear_alerts(self):
        """Clear all triggered alerts"""
        for alert in self.alerts:
            alert['triggered'] = False
    
    def _monitor_loop(self):
        """Background monitoring loop"""
        while self.is_monitoring:
            # Periodic monitoring tasks
            time.sleep(0.1)
    
    def _trigger_callbacks(self, event: Dict[str, Any]):
        """Trigger event callbacks"""
        for callback in self.callbacks:
            try:
                callback(event)
            except Exception:
                pass  # Don't let callback errors break monitoring
    
    def _check_alerts(self, event: Dict[str, Any]):
        """Check alert conditions"""
        for alert in self.alerts:
            if not alert['triggered']:
                try:
                    if alert['condition'](event):
                        alert['triggered'] = True
                        self.log_event('alert', {
                            'name': alert['name'],
                            'message': alert['message'],
                            'level': alert['level']
                        })
                except Exception:
                    pass
    
    def create_progress_tracker(self, total_steps: int) -> 'ProgressTracker':
        """
        Create a progress tracker.
        
        Args:
            total_steps: Total number of steps
            
        Returns:
            Progress tracker instance
        """
        return ProgressTracker(self, total_steps)


class ProgressTracker:
    """
    Progress tracking helper.
    
    Examples:
        >>> tracker = monitor.create_progress_tracker(100)
        >>> for i in range(100):
        ...     tracker.update(i + 1, message=f"Processing {i+1}")
        >>> tracker.complete()
    """
    
    def __init__(self, monitor: SimulationMonitor, total_steps: int):
        """
        Initialize progress tracker.
        
        Args:
            monitor: Monitor instance
            total_steps: Total steps
        """
        self.monitor = monitor
        self.total_steps = total_steps
        self.current_step = 0
        self.start_time = time.time()
    
    def update(self, step: Optional[int] = None, message: str = ""):
        """
        Update progress.
        
        Args:
            step: Current step (increments by 1 if None)
            message: Progress message
        """
        if step is not None:
            self.current_step = step
        else:
            self.current_step += 1
        
        percent = (self.current_step / self.total_steps) * 100
        elapsed = time.time() - self.start_time
        
        if self.current_step > 0:
            eta = (elapsed / self.current_step) * (self.total_steps - self.current_step)
        else:
            eta = 0
        
        self.monitor.log_event('progress', {
            'step': self.current_step,
            'total': self.total_steps,
            'percent': percent,
            'message': message,
            'elapsed': elapsed,
            'eta': eta
        })
        
        self.monitor.update_metric('progress_percent', percent)
    
    def complete(self, message: str = "Completed"):
        """Mark as complete"""
        self.current_step = self.total_steps
        elapsed = time.time() - self.start_time
        
        self.monitor.log_event('complete', {
            'total': self.total_steps,
            'elapsed': elapsed,
            'message': message
        })


class DashboardMonitor:
    """
    Dashboard-style monitoring with formatted output.
    """
    
    def __init__(self, monitor: SimulationMonitor):
        """
        Initialize dashboard monitor.
        
        Args:
            monitor: Monitor instance
        """
        self.monitor = monitor
        self.last_update = time.time()
        self.update_interval = 1.0  # seconds
    
    def print_status(self, force: bool = False):
        """
        Print current status.
        
        Args:
            force: Force print even if update interval not reached
        """
        now = time.time()
        if not force and (now - self.last_update) < self.update_interval:
            return
        
        self.last_update = now
        
        # Clear screen (simple version)
        print("\n" * 2)
        
        # Header
        print("=" * 80)
        print("  HydroClaude Simulation Monitor")
        print("=" * 80)
        
        # Metrics
        metrics = self.monitor.get_metrics()
        if metrics:
            print("\n  Metrics:")
            for name, data in metrics.items():
                print(f"    {name:<30} {data['current']:>10.2f} "
                     f"(min: {data['min']:.2f}, max: {data['max']:.2f}, avg: {data['avg']:.2f})")
        
        # Recent events
        recent = self.monitor.get_events(limit=5)
        if recent:
            print("\n  Recent Events:")
            for event in recent:
                timestamp = event['timestamp'].split('T')[1][:8]  # HH:MM:SS
                print(f"    [{timestamp}] {event['type']}: {event['data']}")
        
        # Alerts
        alerts = self.monitor.get_triggered_alerts()
        if alerts:
            print("\n  Active Alerts:")
            for alert in alerts:
                print(f"    [{alert['level'].upper()}] {alert['message']}")
        
        print("=" * 80)


# Global monitor instance
_global_monitor = None


def get_monitor() -> SimulationMonitor:
    """Get global monitor instance"""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = SimulationMonitor()
        _global_monitor.start()
    return _global_monitor


if __name__ == '__main__':
    # Test monitoring system
    print("Real-Time Monitoring Test\n")
    
    monitor = SimulationMonitor()
    monitor.start()
    
    # Add alerts
    monitor.add_alert(
        'high_progress',
        lambda e: e['type'] == 'progress' and e['data'].get('percent', 0) > 50,
        'Progress > 50%',
        level='info'
    )
    
    # Add callback
    def print_event(event):
        if event['type'] == 'progress':
            data = event['data']
            print(f"  Progress: {data['percent']:.1f}% - {data['message']}")
    
    monitor.add_callback(print_event)
    
    # Simulate progress
    tracker = monitor.create_progress_tracker(10)
    for i in range(10):
        tracker.update(message=f"Step {i+1}")
        time.sleep(0.1)
    
    tracker.complete()
    
    # Get results
    print("\n✅ Final metrics:")
    for name, data in monitor.get_metrics().items():
        print(f"  {name}: {data['current']:.2f}")
    
    print("\n✅ Triggered alerts:")
    for alert in monitor.get_triggered_alerts():
        print(f"  {alert['name']}: {alert['message']}")
    
    monitor.stop()
    print("\n✅ Monitoring test complete")
