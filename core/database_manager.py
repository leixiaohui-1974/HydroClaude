#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Database Manager - Simulation Data Persistence

Provides database integration for storing simulation configurations, results, and metadata.

Author: HydroClaude Development Team
Date: 2025-11-15
"""

import os
import json
import sqlite3
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from pathlib import Path


class DatabaseManager:
    """
    Manages simulation data in SQLite database.
    
    Features:
    - Store simulation configurations
    - Store simulation results
    - Query and filter simulations
    - Track simulation history
    - Export/import data
    """
    
    def __init__(self, db_path: str = "hydroclaude.db"):
        """
        Initialize database manager.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.conn = None
        self._initialize_database()
    
    def _initialize_database(self):
        """Create database tables if they don't exist"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        
        cursor = self.conn.cursor()
        
        # Simulations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS simulations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                simulation_type TEXT,
                mode TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                config_json TEXT,
                error TEXT
            )
        ''')
        
        # Results table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                simulation_id INTEGER,
                result_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (simulation_id) REFERENCES simulations(id)
            )
        ''')
        
        # Validation metrics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS validation_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                simulation_id INTEGER,
                mass_error_percent REAL,
                convergence_iterations INTEGER,
                max_depth REAL,
                min_depth REAL,
                max_velocity REAL,
                min_velocity REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (simulation_id) REFERENCES simulations(id)
            )
        ''')
        
        # Tags table (for categorizing simulations)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                simulation_id INTEGER,
                tag TEXT,
                FOREIGN KEY (simulation_id) REFERENCES simulations(id)
            )
        ''')
        
        # Create indices for faster queries
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_status ON simulations(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_type ON simulations(simulation_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_created ON simulations(created_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tags ON tags(tag)')
        
        self.conn.commit()
    
    def create_simulation(self, name: str, config: Dict[str, Any], 
                         tags: Optional[List[str]] = None) -> int:
        """
        Create a new simulation record.
        
        Args:
            name: Simulation name
            config: Configuration dictionary
            tags: List of tags
            
        Returns:
            Simulation ID
        """
        cursor = self.conn.cursor()
        
        # Extract metadata from config
        sim_type = config.get('simulation', {}).get('type', 'unknown')
        mode = config.get('simulation', {}).get('mode', 'unknown')
        
        cursor.execute('''
            INSERT INTO simulations (name, simulation_type, mode, config_json)
            VALUES (?, ?, ?, ?)
        ''', (name, sim_type, mode, json.dumps(config)))
        
        sim_id = cursor.lastrowid
        
        # Add tags
        if tags:
            for tag in tags:
                cursor.execute('''
                    INSERT INTO tags (simulation_id, tag)
                    VALUES (?, ?)
                ''', (sim_id, tag))
        
        self.conn.commit()
        return sim_id
    
    def update_simulation_status(self, sim_id: int, status: str,
                                 started_at: Optional[str] = None,
                                 completed_at: Optional[str] = None,
                                 error: Optional[str] = None):
        """
        Update simulation status.
        
        Args:
            sim_id: Simulation ID
            status: New status (pending, running, completed, failed)
            started_at: Start timestamp
            completed_at: Completion timestamp
            error: Error message (if failed)
        """
        cursor = self.conn.cursor()
        
        updates = ['status = ?']
        values = [status]
        
        if started_at:
            updates.append('started_at = ?')
            values.append(started_at)
        
        if completed_at:
            updates.append('completed_at = ?')
            values.append(completed_at)
        
        if error:
            updates.append('error = ?')
            values.append(error)
        
        values.append(sim_id)
        
        cursor.execute(f'''
            UPDATE simulations
            SET {', '.join(updates)}
            WHERE id = ?
        ''', values)
        
        self.conn.commit()
    
    def save_results(self, sim_id: int, results: Dict[str, Any]):
        """
        Save simulation results.
        
        Args:
            sim_id: Simulation ID
            results: Results dictionary
        """
        cursor = self.conn.cursor()
        
        # Save full results
        cursor.execute('''
            INSERT INTO results (simulation_id, result_json)
            VALUES (?, ?)
        ''', (sim_id, json.dumps(results)))
        
        # Extract and save validation metrics
        if 'validation' in results:
            val = results['validation']
            
            # Get spatial extrema
            max_depth = min_depth = max_velocity = min_velocity = None
            if 'universal_data_model' in results:
                spatial = results['universal_data_model']['data'].get('spatial', {})
                if 'depth' in spatial:
                    import numpy as np
                    max_depth = float(np.max(spatial['depth']))
                    min_depth = float(np.min(spatial['depth']))
                if 'velocity' in spatial:
                    max_velocity = float(np.max(spatial['velocity']))
                    min_velocity = float(np.min(spatial['velocity']))
            
            cursor.execute('''
                INSERT INTO validation_metrics (
                    simulation_id, mass_error_percent, convergence_iterations,
                    max_depth, min_depth, max_velocity, min_velocity
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                sim_id,
                val.get('mass_error_percent'),
                val.get('convergence_iterations'),
                max_depth, min_depth, max_velocity, min_velocity
            ))
        
        self.conn.commit()
    
    def get_simulation(self, sim_id: int) -> Optional[Dict[str, Any]]:
        """
        Get simulation record.
        
        Args:
            sim_id: Simulation ID
            
        Returns:
            Simulation dictionary or None
        """
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM simulations WHERE id = ?', (sim_id,))
        row = cursor.fetchone()
        
        if not row:
            return None
        
        sim = dict(row)
        sim['config'] = json.loads(sim['config_json']) if sim['config_json'] else None
        
        # Get tags
        cursor.execute('SELECT tag FROM tags WHERE simulation_id = ?', (sim_id,))
        sim['tags'] = [r['tag'] for r in cursor.fetchall()]
        
        return sim
    
    def get_results(self, sim_id: int) -> Optional[Dict[str, Any]]:
        """
        Get simulation results.
        
        Args:
            sim_id: Simulation ID
            
        Returns:
            Results dictionary or None
        """
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT result_json FROM results
            WHERE simulation_id = ?
            ORDER BY created_at DESC
            LIMIT 1
        ''', (sim_id,))
        
        row = cursor.fetchone()
        if not row:
            return None
        
        return json.loads(row['result_json'])
    
    def list_simulations(self, status: Optional[str] = None,
                        simulation_type: Optional[str] = None,
                        tag: Optional[str] = None,
                        limit: int = 100,
                        offset: int = 0) -> List[Dict[str, Any]]:
        """
        List simulations with filters.
        
        Args:
            status: Filter by status
            simulation_type: Filter by type
            tag: Filter by tag
            limit: Maximum results
            offset: Offset for pagination
            
        Returns:
            List of simulation dictionaries
        """
        cursor = self.conn.cursor()
        
        query = 'SELECT * FROM simulations'
        conditions = []
        values = []
        
        if status:
            conditions.append('status = ?')
            values.append(status)
        
        if simulation_type:
            conditions.append('simulation_type = ?')
            values.append(simulation_type)
        
        if tag:
            query = '''
                SELECT s.* FROM simulations s
                JOIN tags t ON s.id = t.simulation_id
            '''
            conditions.append('t.tag = ?')
            values.append(tag)
        
        if conditions:
            query += ' WHERE ' + ' AND '.join(conditions)
        
        query += ' ORDER BY created_at DESC LIMIT ? OFFSET ?'
        values.extend([limit, offset])
        
        cursor.execute(query, values)
        
        simulations = []
        for row in cursor.fetchall():
            sim = dict(row)
            sim['config'] = None  # Don't load full config in list
            simulations.append(sim)
        
        return simulations
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get database statistics.
        
        Returns:
            Statistics dictionary
        """
        cursor = self.conn.cursor()
        
        stats = {}
        
        # Total simulations
        cursor.execute('SELECT COUNT(*) as count FROM simulations')
        stats['total_simulations'] = cursor.fetchone()['count']
        
        # By status
        cursor.execute('''
            SELECT status, COUNT(*) as count
            FROM simulations
            GROUP BY status
        ''')
        stats['by_status'] = {r['status']: r['count'] for r in cursor.fetchall()}
        
        # By type
        cursor.execute('''
            SELECT simulation_type, COUNT(*) as count
            FROM simulations
            GROUP BY simulation_type
        ''')
        stats['by_type'] = {r['simulation_type']: r['count'] for r in cursor.fetchall()}
        
        # Recent activity
        cursor.execute('''
            SELECT DATE(created_at) as date, COUNT(*) as count
            FROM simulations
            WHERE created_at >= DATE('now', '-7 days')
            GROUP BY DATE(created_at)
            ORDER BY date
        ''')
        stats['recent_activity'] = [dict(r) for r in cursor.fetchall()]
        
        return stats
    
    def search_simulations(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Search simulations by name.
        
        Args:
            query: Search query
            limit: Maximum results
            
        Returns:
            List of matching simulations
        """
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM simulations
            WHERE name LIKE ?
            ORDER BY created_at DESC
            LIMIT ?
        ''', (f'%{query}%', limit))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def delete_simulation(self, sim_id: int) -> bool:
        """
        Delete a simulation and its results.
        
        Args:
            sim_id: Simulation ID
            
        Returns:
            Success status
        """
        cursor = self.conn.cursor()
        
        try:
            cursor.execute('DELETE FROM results WHERE simulation_id = ?', (sim_id,))
            cursor.execute('DELETE FROM validation_metrics WHERE simulation_id = ?', (sim_id,))
            cursor.execute('DELETE FROM tags WHERE simulation_id = ?', (sim_id,))
            cursor.execute('DELETE FROM simulations WHERE id = ?', (sim_id,))
            self.conn.commit()
            return True
        except Exception:
            self.conn.rollback()
            return False
    
    def export_database(self, output_path: str):
        """
        Export database to JSON file.
        
        Args:
            output_path: Output file path
        """
        simulations = self.list_simulations(limit=10000)
        
        # Get full data for each simulation
        export_data = []
        for sim in simulations:
            full_sim = self.get_simulation(sim['id'])
            results = self.get_results(sim['id'])
            
            export_data.append({
                'simulation': full_sim,
                'results': results
            })
        
        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2)
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


if __name__ == '__main__':
    # Test database manager
    print("Database Manager Test\n")
    
    with DatabaseManager('test_hydroclaude.db') as db:
        # Create test simulation
        config = {
            'simulation': {'type': 'steady', 'mode': 'single_canal'},
            'canal': {'length': 1000, 'width': 10}
        }
        
        sim_id = db.create_simulation('test_sim', config, tags=['test', 'example'])
        print(f"✅ Created simulation: {sim_id}")
        
        # Update status
        db.update_simulation_status(sim_id, 'running', 
                                   started_at=datetime.now().isoformat())
        print(f"✅ Updated status to running")
        
        # Complete simulation
        db.update_simulation_status(sim_id, 'completed',
                                   completed_at=datetime.now().isoformat())
        print(f"✅ Completed simulation")
        
        # Get statistics
        stats = db.get_statistics()
        print(f"✅ Statistics: {stats}")
        
        # Clean up
        os.remove('test_hydroclaude.db')
        print("✅ Test completed")
