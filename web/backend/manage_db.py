#!/usr/bin/env python3
"""
Database management script
Provides CLI commands for database operations
"""

import sys
import os
import argparse

# Add backend path
backend_path = os.path.dirname(os.path.abspath(__file__))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from shared.database import init_db, drop_db, reset_db, SessionLocal, crud


def cmd_init():
    """Initialize database (create tables)"""
    print("Initializing database...")
    init_db()
    print("[OK] Database initialized successfully")


def cmd_drop():
    """Drop all database tables"""
    response = input("WARNING: This will delete all data! Continue? (yes/no): ")
    if response.lower() == 'yes':
        print("Dropping all tables...")
        drop_db()
        print("[OK] All tables dropped")
    else:
        print("Cancelled")


def cmd_reset():
    """Reset database (drop and recreate)"""
    response = input("WARNING: This will delete all data! Continue? (yes/no): ")
    if response.lower() == 'yes':
        print("Resetting database...")
        reset_db()
        print("[OK] Database reset successfully")
    else:
        print("Cancelled")


def cmd_status():
    """Show database status"""
    from shared.database.models import Simulation, SimulationMetrics
    from sqlalchemy import inspect

    db = SessionLocal()
    try:
        # Check if tables exist
        inspector = inspect(db.bind)
        tables = inspector.get_table_names()

        print(f"\n{'='*60}")
        print("Database Status")
        print(f"{'='*60}")
        print(f"Tables: {len(tables)}")
        for table in tables:
            print(f"  - {table}")

        # Count records
        sim_count = crud.count_simulations(db)
        queued_count = crud.count_simulations(db, status='queued')
        running_count = crud.count_simulations(db, status='running')
        completed_count = crud.count_simulations(db, status='completed')
        failed_count = crud.count_simulations(db, status='failed')

        print(f"\n{'='*60}")
        print("Statistics")
        print(f"{'='*60}")
        print(f"Total Simulations: {sim_count}")
        print(f"  - Queued:    {queued_count}")
        print(f"  - Running:   {running_count}")
        print(f"  - Completed: {completed_count}")
        print(f"  - Failed:    {failed_count}")
        print(f"{'='*60}\n")

    finally:
        db.close()


def cmd_list(status=None, limit=10):
    """List simulations"""
    db = SessionLocal()
    try:
        simulations = crud.get_simulations(db, skip=0, limit=limit, status=status)

        if not simulations:
            print("No simulations found")
            return

        print(f"\n{'='*100}")
        print(f"{'Task ID':<40} {'Name':<30} {'Status':<12} {'Created':<20}")
        print(f"{'='*100}")

        for sim in simulations:
            created_str = sim.created_at.strftime('%Y-%m-%d %H:%M:%S') if sim.created_at else 'N/A'
            print(f"{sim.task_id:<40} {sim.name[:28]:<30} {sim.status:<12} {created_str:<20}")

        print(f"{'='*100}\n")
        print(f"Showing {len(simulations)} simulation(s)")

    finally:
        db.close()


def cmd_show(task_id):
    """Show detailed simulation information"""
    db = SessionLocal()
    try:
        sim = crud.get_simulation_by_task_id(db, task_id)

        if not sim:
            print(f"Simulation {task_id} not found")
            return

        print(f"\n{'='*60}")
        print("Simulation Details")
        print(f"{'='*60}")
        print(f"Task ID:      {sim.task_id}")
        print(f"Name:         {sim.name}")
        print(f"Description:  {sim.description or 'N/A'}")
        print(f"Status:       {sim.status}")
        print(f"Progress:     {sim.progress}%")
        print(f"Created:      {sim.created_at}")
        print(f"Started:      {sim.started_at or 'N/A'}")
        print(f"Completed:    {sim.completed_at or 'N/A'}")
        print(f"Duration:     {sim.duration}s" if sim.duration else "Duration:     N/A")

        if sim.status == 'failed':
            print(f"Error:        {sim.error_message}")

        if sim.status == 'completed':
            metrics = crud.get_simulation_metrics(db, task_id)
            if metrics:
                print(f"\n{'='*60}")
                print("Performance Metrics")
                print(f"{'='*60}")
                print(f"Mass Conservation Error: {metrics.mass_conservation_error:.2e}")
                print(f"Max Depth:               {metrics.max_depth:.4f} m")
                print(f"Min Depth:               {metrics.min_depth:.4f} m")
                print(f"Max Velocity:            {metrics.max_velocity:.4f} m/s")
                print(f"Max Froude Number:       {metrics.max_froude:.4f}")
                print(f"Total Iterations:        {metrics.total_iterations}")
                print(f"Converged:               {'Yes' if metrics.converged else 'No'}")

        print(f"{'='*60}\n")

    finally:
        db.close()


def cmd_delete(task_id):
    """Delete a simulation"""
    db = SessionLocal()
    try:
        sim = crud.get_simulation_by_task_id(db, task_id)
        if not sim:
            print(f"Simulation {task_id} not found")
            return

        response = input(f"Delete simulation '{sim.name}' ({task_id})? (yes/no): ")
        if response.lower() == 'yes':
            crud.delete_simulation(db, task_id)
            print(f"[OK] Simulation {task_id} deleted")
        else:
            print("Cancelled")

    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description='HydroClaude Database Management')
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # init command
    subparsers.add_parser('init', help='Initialize database')

    # drop command
    subparsers.add_parser('drop', help='Drop all tables')

    # reset command
    subparsers.add_parser('reset', help='Reset database (drop and recreate)')

    # status command
    subparsers.add_parser('status', help='Show database status')

    # list command
    parser_list = subparsers.add_parser('list', help='List simulations')
    parser_list.add_argument('--status', help='Filter by status', choices=['queued', 'running', 'completed', 'failed'])
    parser_list.add_argument('--limit', type=int, default=10, help='Number of records to show')

    # show command
    parser_show = subparsers.add_parser('show', help='Show simulation details')
    parser_show.add_argument('task_id', help='Task ID')

    # delete command
    parser_delete = subparsers.add_parser('delete', help='Delete simulation')
    parser_delete.add_argument('task_id', help='Task ID')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Execute command
    if args.command == 'init':
        cmd_init()
    elif args.command == 'drop':
        cmd_drop()
    elif args.command == 'reset':
        cmd_reset()
    elif args.command == 'status':
        cmd_status()
    elif args.command == 'list':
        cmd_list(status=args.status, limit=args.limit)
    elif args.command == 'show':
        cmd_show(args.task_id)
    elif args.command == 'delete':
        cmd_delete(args.task_id)


if __name__ == '__main__':
    main()
