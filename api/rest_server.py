#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
REST API Server for HydroClaude

Provides RESTful API endpoints for simulation management and execution.

Author: HydroClaude Development Team
Date: 2025-11-15
"""

import os
import sys
import json
import uuid
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

try:
    from flask import Flask, request, jsonify, send_file
    from flask_cors import CORS
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    Flask = None
    CORS = None

from core.config_parser import ConfigParser
from core.simulation_engine import SimulationEngine
from core.output_manager import OutputManager


class SimulationManager:
    """
    Manages simulation jobs and their lifecycle.
    """
    
    def __init__(self, workspace_dir: str = "./api_workspace"):
        """
        Initialize simulation manager.
        
        Args:
            workspace_dir: Directory for storing simulation data
        """
        self.workspace_dir = Path(workspace_dir)
        self.workspace_dir.mkdir(exist_ok=True)
        
        self.jobs = {}  # job_id -> job_info
        self.results = {}  # job_id -> results
    
    def create_job(self, config: Dict[str, Any], name: Optional[str] = None) -> str:
        """
        Create a new simulation job.
        
        Args:
            config: Simulation configuration
            name: Job name (optional)
            
        Returns:
            Job ID
        """
        job_id = str(uuid.uuid4())
        
        # Create job directory
        job_dir = self.workspace_dir / job_id
        job_dir.mkdir(exist_ok=True)
        
        # Save configuration
        config_file = job_dir / "config.json"
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        # Create job info
        job_info = {
            'job_id': job_id,
            'name': name or f"job_{job_id[:8]}",
            'status': 'pending',
            'created_at': datetime.now().isoformat(),
            'started_at': None,
            'completed_at': None,
            'error': None,
            'config_file': str(config_file),
            'job_dir': str(job_dir)
        }
        
        self.jobs[job_id] = job_info
        
        return job_id
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job information"""
        return self.jobs.get(job_id)
    
    def list_jobs(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all jobs, optionally filtered by status.
        
        Args:
            status: Filter by status (pending, running, completed, failed)
            
        Returns:
            List of job info dictionaries
        """
        jobs = list(self.jobs.values())
        
        if status:
            jobs = [j for j in jobs if j['status'] == status]
        
        # Sort by creation time (newest first)
        jobs.sort(key=lambda x: x['created_at'], reverse=True)
        
        return jobs
    
    def run_job(self, job_id: str) -> Dict[str, Any]:
        """
        Execute a simulation job.
        
        Args:
            job_id: Job ID
            
        Returns:
            Execution result
        """
        job_info = self.jobs.get(job_id)
        
        if not job_info:
            raise ValueError(f"Job not found: {job_id}")
        
        if job_info['status'] == 'running':
            raise ValueError(f"Job already running: {job_id}")
        
        # Update status
        job_info['status'] = 'running'
        job_info['started_at'] = datetime.now().isoformat()
        
        try:
            # Parse configuration
            parser = ConfigParser(verbose=False)
            config = parser.parse(job_info['config_file'])
            
            # Update output directory
            config['output']['directory'] = job_info['job_dir']
            
            # Run simulation
            engine = SimulationEngine(config, verbose=False)
            results = engine.run()
            
            # Save outputs
            output_manager = OutputManager(config, results, verbose=False)
            output_manager.save_all()
            
            # Store results
            self.results[job_id] = results
            
            # Update status
            job_info['status'] = 'completed'
            job_info['completed_at'] = datetime.now().isoformat()
            job_info['error'] = None
            
            return {
                'success': True,
                'job_id': job_id,
                'status': 'completed',
                'message': 'Simulation completed successfully'
            }
            
        except Exception as e:
            # Update status
            job_info['status'] = 'failed'
            job_info['completed_at'] = datetime.now().isoformat()
            job_info['error'] = str(e)
            
            return {
                'success': False,
                'job_id': job_id,
                'status': 'failed',
                'error': str(e)
            }
    
    def get_results(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get simulation results"""
        return self.results.get(job_id)
    
    def delete_job(self, job_id: str) -> bool:
        """
        Delete a job and its data.
        
        Args:
            job_id: Job ID
            
        Returns:
            Success status
        """
        if job_id not in self.jobs:
            return False
        
        job_info = self.jobs[job_id]
        
        # Delete job directory
        import shutil
        job_dir = Path(job_info['job_dir'])
        if job_dir.exists():
            shutil.rmtree(job_dir)
        
        # Remove from memory
        del self.jobs[job_id]
        if job_id in self.results:
            del self.results[job_id]
        
        return True


def create_app(workspace_dir: str = "./api_workspace") -> Flask:
    """
    Create Flask application.
    
    Args:
        workspace_dir: Workspace directory
        
    Returns:
        Flask app
    """
    if not FLASK_AVAILABLE:
        raise ImportError(
            "Flask is required for REST API. "
            "Install with: pip install flask flask-cors"
        )
    
    app = Flask(__name__)
    CORS(app)  # Enable CORS for all routes
    
    # Create simulation manager
    manager = SimulationManager(workspace_dir)
    
    # ========== API Endpoints ==========
    
    @app.route('/')
    def index():
        """API root endpoint"""
        return jsonify({
            'name': 'HydroClaude REST API',
            'version': '1.2.0',
            'status': 'running',
            'endpoints': {
                'POST /api/jobs': 'Create a new simulation job',
                'GET /api/jobs': 'List all jobs',
                'GET /api/jobs/<job_id>': 'Get job details',
                'POST /api/jobs/<job_id>/run': 'Run a job',
                'GET /api/jobs/<job_id>/results': 'Get job results',
                'DELETE /api/jobs/<job_id>': 'Delete a job',
                'GET /api/health': 'Health check'
            }
        })
    
    @app.route('/api/health')
    def health():
        """Health check endpoint"""
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'jobs': {
                'total': len(manager.jobs),
                'pending': len([j for j in manager.jobs.values() if j['status'] == 'pending']),
                'running': len([j for j in manager.jobs.values() if j['status'] == 'running']),
                'completed': len([j for j in manager.jobs.values() if j['status'] == 'completed']),
                'failed': len([j for j in manager.jobs.values() if j['status'] == 'failed'])
            }
        })
    
    @app.route('/api/jobs', methods=['POST'])
    def create_job():
        """Create a new simulation job"""
        try:
            data = request.get_json()
            
            if 'config' not in data:
                return jsonify({'error': 'Missing config'}), 400
            
            config = data['config']
            name = data.get('name')
            
            job_id = manager.create_job(config, name)
            job_info = manager.get_job(job_id)
            
            return jsonify({
                'success': True,
                'job_id': job_id,
                'job': job_info
            }), 201
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/jobs', methods=['GET'])
    def list_jobs():
        """List all jobs"""
        try:
            status = request.args.get('status')
            jobs = manager.list_jobs(status)
            
            return jsonify({
                'success': True,
                'total': len(jobs),
                'jobs': jobs
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/jobs/<job_id>', methods=['GET'])
    def get_job(job_id):
        """Get job details"""
        job_info = manager.get_job(job_id)
        
        if not job_info:
            return jsonify({'error': 'Job not found'}), 404
        
        return jsonify({
            'success': True,
            'job': job_info
        })
    
    @app.route('/api/jobs/<job_id>/run', methods=['POST'])
    def run_job(job_id):
        """Run a simulation job"""
        try:
            result = manager.run_job(job_id)
            
            if result['success']:
                return jsonify(result), 200
            else:
                return jsonify(result), 500
                
        except ValueError as e:
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/jobs/<job_id>/results', methods=['GET'])
    def get_results(job_id):
        """Get simulation results"""
        job_info = manager.get_job(job_id)
        
        if not job_info:
            return jsonify({'error': 'Job not found'}), 404
        
        if job_info['status'] != 'completed':
            return jsonify({
                'error': f"Job not completed (status: {job_info['status']})"
            }), 400
        
        results = manager.get_results(job_id)
        
        if not results:
            return jsonify({'error': 'Results not available'}), 404
        
        return jsonify({
            'success': True,
            'job_id': job_id,
            'results': results
        })
    
    @app.route('/api/jobs/<job_id>', methods=['DELETE'])
    def delete_job(job_id):
        """Delete a job"""
        success = manager.delete_job(job_id)
        
        if not success:
            return jsonify({'error': 'Job not found'}), 404
        
        return jsonify({
            'success': True,
            'message': f'Job {job_id} deleted'
        })
    
    @app.route('/api/jobs/<job_id>/files/<path:filename>', methods=['GET'])
    def get_file(job_id, filename):
        """Download a file from job directory"""
        job_info = manager.get_job(job_id)
        
        if not job_info:
            return jsonify({'error': 'Job not found'}), 404
        
        file_path = Path(job_info['job_dir']) / filename
        
        if not file_path.exists():
            return jsonify({'error': 'File not found'}), 404
        
        return send_file(file_path)
    
    return app


def main():
    """Run REST API server"""
    import argparse
    
    parser = argparse.ArgumentParser(description='HydroClaude REST API Server')
    parser.add_argument('--host', default='127.0.0.1',
                       help='Host address (default: 127.0.0.1)')
    parser.add_argument('--port', type=int, default=5000,
                       help='Port number (default: 5000)')
    parser.add_argument('--workspace', default='./api_workspace',
                       help='Workspace directory (default: ./api_workspace)')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug mode')
    
    args = parser.parse_args()
    
    if not FLASK_AVAILABLE:
        print("Error: Flask is required for REST API")
        print("Install with: pip install flask flask-cors")
        sys.exit(1)
    
    print("=" * 80)
    print("  HydroClaude REST API Server")
    print("=" * 80)
    print(f"  Host: {args.host}")
    print(f"  Port: {args.port}")
    print(f"  Workspace: {args.workspace}")
    print(f"  Debug: {args.debug}")
    print("=" * 80)
    print(f"\n  API available at: http://{args.host}:{args.port}")
    print(f"  Health check: http://{args.host}:{args.port}/api/health")
    print("\n  Press Ctrl+C to stop\n")
    
    app = create_app(args.workspace)
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == '__main__':
    main()
