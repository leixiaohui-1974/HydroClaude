#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HydroClaude Python SDK

Provides a Python client library for interacting with HydroClaude REST API.

Author: HydroClaude Development Team
Date: 2025-11-15
"""

import time
from typing import Dict, Any, List, Optional, Union
from datetime import datetime

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    requests = None


class HydroClaudeClient:
    """
    Python client for HydroClaude REST API.
    
    Examples:
        >>> client = HydroClaudeClient('http://localhost:5000')
        >>> job_id = client.create_job(config)
        >>> client.run_job(job_id)
        >>> results = client.get_results(job_id)
    """
    
    def __init__(self, base_url: str = 'http://localhost:5000', 
                 timeout: int = 300):
        """
        Initialize HydroClaude client.
        
        Args:
            base_url: Base URL of REST API
            timeout: Request timeout in seconds
        """
        if not REQUESTS_AVAILABLE:
            raise ImportError(
                "requests library is required. "
                "Install with: pip install requests"
            )
        
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()
    
    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Make HTTP request to API.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            **kwargs: Additional request parameters
            
        Returns:
            Response JSON
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        # Set timeout if not specified
        if 'timeout' not in kwargs:
            kwargs['timeout'] = self.timeout
        
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            raise APIError(f"API request failed: {str(e)}")
    
    def health(self) -> Dict[str, Any]:
        """
        Check API health.
        
        Returns:
            Health status dictionary
        """
        return self._request('GET', '/api/health')
    
    def create_job(self, config: Dict[str, Any], 
                   name: Optional[str] = None) -> str:
        """
        Create a new simulation job.
        
        Args:
            config: Simulation configuration dictionary
            name: Job name (optional)
            
        Returns:
            Job ID
            
        Examples:
            >>> config = {
            ...     'simulation': {'type': 'steady'},
            ...     'canal': {'length': 1000, 'width': 10},
            ...     ...
            ... }
            >>> job_id = client.create_job(config, name='my_simulation')
        """
        data = {'config': config}
        if name:
            data['name'] = name
        
        response = self._request('POST', '/api/jobs', json=data)
        return response['job_id']
    
    def get_job(self, job_id: str) -> Dict[str, Any]:
        """
        Get job information.
        
        Args:
            job_id: Job ID
            
        Returns:
            Job information dictionary
        """
        response = self._request('GET', f'/api/jobs/{job_id}')
        return response['job']
    
    def list_jobs(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all jobs.
        
        Args:
            status: Filter by status (pending, running, completed, failed)
            
        Returns:
            List of job information dictionaries
        """
        params = {}
        if status:
            params['status'] = status
        
        response = self._request('GET', '/api/jobs', params=params)
        return response['jobs']
    
    def run_job(self, job_id: str, wait: bool = False, 
                poll_interval: float = 1.0) -> Dict[str, Any]:
        """
        Run a simulation job.
        
        Args:
            job_id: Job ID
            wait: Wait for completion
            poll_interval: Polling interval in seconds (when wait=True)
            
        Returns:
            Execution result
            
        Examples:
            >>> # Async execution
            >>> result = client.run_job(job_id)
            
            >>> # Wait for completion
            >>> result = client.run_job(job_id, wait=True)
        """
        response = self._request('POST', f'/api/jobs/{job_id}/run')
        
        if wait:
            return self.wait_for_completion(job_id, poll_interval)
        
        return response
    
    def wait_for_completion(self, job_id: str, 
                           poll_interval: float = 1.0,
                           max_wait: Optional[float] = None) -> Dict[str, Any]:
        """
        Wait for job completion.
        
        Args:
            job_id: Job ID
            poll_interval: Polling interval in seconds
            max_wait: Maximum wait time in seconds
            
        Returns:
            Final job information
            
        Raises:
            TimeoutError: If max_wait is exceeded
        """
        start_time = time.time()
        
        while True:
            job_info = self.get_job(job_id)
            status = job_info['status']
            
            if status in ['completed', 'failed']:
                return job_info
            
            # Check timeout
            if max_wait and (time.time() - start_time) > max_wait:
                raise TimeoutError(f"Job {job_id} did not complete within {max_wait}s")
            
            time.sleep(poll_interval)
    
    def get_results(self, job_id: str) -> Dict[str, Any]:
        """
        Get simulation results.
        
        Args:
            job_id: Job ID
            
        Returns:
            Simulation results dictionary
        """
        response = self._request('GET', f'/api/jobs/{job_id}/results')
        return response['results']
    
    def delete_job(self, job_id: str) -> bool:
        """
        Delete a job.
        
        Args:
            job_id: Job ID
            
        Returns:
            Success status
        """
        try:
            self._request('DELETE', f'/api/jobs/{job_id}')
            return True
        except APIError:
            return False
    
    def download_file(self, job_id: str, filename: str, 
                     output_path: str) -> bool:
        """
        Download a file from job directory.
        
        Args:
            job_id: Job ID
            filename: File name (relative to job directory)
            output_path: Local output path
            
        Returns:
            Success status
        """
        url = f"{self.base_url}/api/jobs/{job_id}/files/{filename}"
        
        try:
            response = self.session.get(url, timeout=self.timeout, stream=True)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            return True
            
        except Exception:
            return False
    
    def submit_and_wait(self, config: Dict[str, Any], 
                       name: Optional[str] = None,
                       poll_interval: float = 1.0) -> Dict[str, Any]:
        """
        Submit a job and wait for completion (convenience method).
        
        Args:
            config: Simulation configuration
            name: Job name
            poll_interval: Polling interval
            
        Returns:
            Simulation results
            
        Examples:
            >>> results = client.submit_and_wait(config)
        """
        # Create job
        job_id = self.create_job(config, name)
        
        # Run and wait
        self.run_job(job_id, wait=True, poll_interval=poll_interval)
        
        # Get results
        return self.get_results(job_id)
    
    def cleanup_completed_jobs(self, keep_recent: int = 10) -> int:
        """
        Clean up old completed jobs.
        
        Args:
            keep_recent: Number of recent jobs to keep
            
        Returns:
            Number of jobs deleted
        """
        jobs = self.list_jobs(status='completed')
        
        # Keep only recent jobs
        if len(jobs) <= keep_recent:
            return 0
        
        jobs_to_delete = jobs[keep_recent:]
        deleted = 0
        
        for job in jobs_to_delete:
            if self.delete_job(job['job_id']):
                deleted += 1
        
        return deleted


class APIError(Exception):
    """API error exception"""
    pass


class Job:
    """
    Job wrapper for convenient access to job operations.
    
    Examples:
        >>> job = Job(client, job_id)
        >>> job.run(wait=True)
        >>> results = job.results
    """
    
    def __init__(self, client: HydroClaudeClient, job_id: str):
        """
        Initialize job wrapper.
        
        Args:
            client: HydroClaude client
            job_id: Job ID
        """
        self.client = client
        self.job_id = job_id
        self._info = None
        self._results = None
    
    @property
    def info(self) -> Dict[str, Any]:
        """Get job information (cached)"""
        if self._info is None:
            self._info = self.client.get_job(self.job_id)
        return self._info
    
    @property
    def status(self) -> str:
        """Get job status"""
        self._info = self.client.get_job(self.job_id)
        return self._info['status']
    
    @property
    def results(self) -> Optional[Dict[str, Any]]:
        """Get results (if completed)"""
        if self.status == 'completed':
            if self._results is None:
                self._results = self.client.get_results(self.job_id)
            return self._results
        return None
    
    def run(self, wait: bool = False) -> Dict[str, Any]:
        """Run the job"""
        return self.client.run_job(self.job_id, wait=wait)
    
    def wait(self, poll_interval: float = 1.0) -> Dict[str, Any]:
        """Wait for completion"""
        return self.client.wait_for_completion(self.job_id, poll_interval)
    
    def delete(self) -> bool:
        """Delete the job"""
        return self.client.delete_job(self.job_id)
    
    def download(self, filename: str, output_path: str) -> bool:
        """Download a file"""
        return self.client.download_file(self.job_id, filename, output_path)
    
    def __repr__(self) -> str:
        return f"Job(id={self.job_id}, status={self.status})"


def create_client(base_url: str = 'http://localhost:5000') -> HydroClaudeClient:
    """
    Create a HydroClaude client.
    
    Args:
        base_url: API base URL
        
    Returns:
        Client instance
    """
    return HydroClaudeClient(base_url)


if __name__ == '__main__':
    # Example usage
    print("HydroClaude Python SDK")
    print("\nExample usage:")
    print("""
    from sdk.hydroclaude_sdk import HydroClaudeClient
    
    # Create client
    client = HydroClaudeClient('http://localhost:5000')
    
    # Check health
    health = client.health()
    print(f"API Status: {health['status']}")
    
    # Create and run job
    config = {
        'simulation': {'type': 'steady', 'mode': 'single_canal'},
        'canal': {'length': 1000, 'width': 10, 'slope': 0.001, 'manning_n': 0.025},
        'solver': {'method': 'hydrostatic'},
        'boundary_conditions': {
            'upstream': {'type': 'flow', 'value': 8.0},
            'downstream': {'type': 'depth', 'method': 'uniform_flow'}
        }
    }
    
    # Submit and wait for results
    results = client.submit_and_wait(config, name='test_simulation')
    print(f"Simulation completed!")
    
    # Or use Job wrapper
    job_id = client.create_job(config)
    job = Job(client, job_id)
    job.run(wait=True)
    print(f"Results: {job.results}")
    """)
