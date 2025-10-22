#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Example 01: Canal Flow - Master Script

Runs all reorganized examples in sequence and generates comprehensive report.

Author: Claude
Date: 2025-10-22
"""

import sys
import os
import time
import subprocess
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def run_script(script_path, description):
    """Run a script and capture its status"""
    print("\n" + "=" * 80)
    print(f"Running: {description}")
    print("=" * 80)
    print(f"Script: {script_path}")
    print("-" * 80)

    start_time = time.time()

    try:
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout
        )

        elapsed = time.time() - start_time

        if result.returncode == 0:
            print(result.stdout)
            print(f"\n✅ SUCCESS - Completed in {elapsed:.1f}s")
            return {
                'name': description,
                'script': os.path.basename(script_path),
                'status': 'SUCCESS',
                'time': elapsed,
                'output': result.stdout
            }
        else:
            print(result.stdout)
            print(result.stderr)
            print(f"\n❌ FAILED - Error after {elapsed:.1f}s")
            return {
                'name': description,
                'script': os.path.basename(script_path),
                'status': 'FAILED',
                'time': elapsed,
                'error': result.stderr
            }

    except subprocess.TimeoutExpired:
        elapsed = time.time() - start_time
        print(f"\n⏱️ TIMEOUT - Exceeded time limit ({elapsed:.1f}s)")
        return {
            'name': description,
            'script': os.path.basename(script_path),
            'status': 'TIMEOUT',
            'time': elapsed
        }

    except Exception as e:
        elapsed = time.time() - start_time
        print(f"\n❌ ERROR - {str(e)}")
        return {
            'name': description,
            'script': os.path.basename(script_path),
            'status': 'ERROR',
            'time': elapsed,
            'error': str(e)
        }


def generate_report(results, output_dir):
    """Generate comprehensive execution report"""
    report_path = os.path.join(output_dir, "EXECUTION_REPORT.md")

    with open(report_path, 'w') as f:
        f.write("# Example 01: Canal Flow - Execution Report\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        # Summary statistics
        total = len(results)
        success = sum(1 for r in results if r['status'] == 'SUCCESS')
        failed = sum(1 for r in results if r['status'] == 'FAILED')
        timeout = sum(1 for r in results if r['status'] == 'TIMEOUT')
        error = sum(1 for r in results if r['status'] == 'ERROR')
        total_time = sum(r['time'] for r in results)

        f.write("## Summary\n\n")
        f.write(f"- **Total scripts:** {total}\n")
        f.write(f"- **Successful:** {success}\n")
        f.write(f"- **Failed:** {failed}\n")
        f.write(f"- **Timeout:** {timeout}\n")
        f.write(f"- **Error:** {error}\n")
        f.write(f"- **Total time:** {total_time:.1f}s ({total_time/60:.1f}min)\n\n")

        # Detailed results
        f.write("## Detailed Results\n\n")

        for idx, result in enumerate(results, 1):
            status_emoji = {
                'SUCCESS': '✅',
                'FAILED': '❌',
                'TIMEOUT': '⏱️',
                'ERROR': '❌'
            }

            f.write(f"### {idx}. {result['name']}\n\n")
            f.write(f"- **Script:** `{result['script']}`\n")
            f.write(f"- **Status:** {status_emoji.get(result['status'], '❓')} {result['status']}\n")
            f.write(f"- **Time:** {result['time']:.1f}s\n")

            if result['status'] != 'SUCCESS' and 'error' in result:
                f.write(f"- **Error:**\n```\n{result['error']}\n```\n")

            f.write("\n")

        # Output files summary
        f.write("## Generated Outputs\n\n")
        f.write("### Figures\n\n")

        figures_dir = os.path.join(os.path.dirname(output_dir), "outputs_new", "figures")
        if os.path.exists(figures_dir):
            figures = sorted([f for f in os.listdir(figures_dir) if f.endswith('.png')])
            for fig in figures:
                f.write(f"- `{fig}`\n")
        else:
            f.write("- No figures generated\n")

        f.write("\n### Animations\n\n")

        animations_dir = os.path.join(os.path.dirname(output_dir), "outputs_new", "animations")
        if os.path.exists(animations_dir):
            animations = sorted([f for f in os.listdir(animations_dir) if f.endswith('.gif')])
            for anim in animations:
                size_mb = os.path.getsize(os.path.join(animations_dir, anim)) / (1024 * 1024)
                f.write(f"- `{anim}` ({size_mb:.2f} MB)\n")
        else:
            f.write("- No animations generated\n")

    print(f"\n📄 Report saved: {report_path}")
    return report_path


def main():
    """Main function"""
    print("=" * 80)
    print("EXAMPLE 01: CANAL FLOW - MASTER EXECUTION SCRIPT")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Get base directory
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # Define scripts to run
    scripts = [
        (os.path.join(base_dir, "code_new", "basic", "01_basic_simulation.py"),
         "01 - Basic Simulation (Three Methods)"),

        (os.path.join(base_dir, "code_new", "basic", "02_step_response.py"),
         "02 - Step Response Analysis"),

        (os.path.join(base_dir, "code_new", "basic", "03_idz_identification.py"),
         "03 - IDZ Parameter Identification"),

        (os.path.join(base_dir, "code_new", "visualization", "04_animation_generator.py"),
         "04 - Animation Generator"),
    ]

    # Check all scripts exist
    print("Checking scripts...")
    all_exist = True
    for script_path, desc in scripts:
        if os.path.exists(script_path):
            print(f"  ✓ {os.path.basename(script_path)}")
        else:
            print(f"  ✗ {os.path.basename(script_path)} - NOT FOUND")
            all_exist = False

    if not all_exist:
        print("\n❌ Some scripts are missing. Aborting.")
        return

    print(f"\n✓ All {len(scripts)} scripts found")

    # Create output directories
    output_dir = os.path.join(base_dir, "outputs_new", "reports")
    os.makedirs(output_dir, exist_ok=True)

    # Run all scripts
    results = []
    start_time = time.time()

    for script_path, description in scripts:
        result = run_script(script_path, description)
        results.append(result)

    total_time = time.time() - start_time

    # Generate report
    print("\n" + "=" * 80)
    print("GENERATING EXECUTION REPORT")
    print("=" * 80)

    report_path = generate_report(results, output_dir)

    # Print final summary
    print("\n" + "=" * 80)
    print("EXECUTION COMPLETE")
    print("=" * 80)

    success_count = sum(1 for r in results if r['status'] == 'SUCCESS')
    total_count = len(results)

    print(f"\nResults: {success_count}/{total_count} scripts completed successfully")
    print(f"Total time: {total_time:.1f}s ({total_time/60:.1f}min)")
    print(f"\n📄 Full report: {report_path}")

    if success_count == total_count:
        print("\n🎉 All scripts completed successfully!")
        return 0
    else:
        print("\n⚠️ Some scripts failed. Check the report for details.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
