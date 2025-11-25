import os
import json
import glob
import subprocess
import sys
import time

RESULTS_DIR = "batch_test_results"
BATCH_SCRIPT = "batch_test_all_cases.py"

def get_failed_indices():
    files = glob.glob(os.path.join(RESULTS_DIR, "results_*.json"))
    failed_indices = []
    
    for file_path in files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            start_index = data['metadata']['batch_start_index']
            
            for i, result in enumerate(data.get('results', [])):
                status = result.get('status', 'unknown')
                if status in ['fail', 'timeout', 'error']:
                    failed_indices.append(start_index + i)
                    
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            
    return sorted(list(set(failed_indices)))

def retry_tests():
    indices = get_failed_indices()
    print(f"Found {len(indices)} failed tests to retry.")
    
    if not indices:
        print("No failed tests found.")
        return

    print("Starting retry process...")
    
    for i in indices:
        print(f"\nRetrying test at index {i}...")
        
        command = [
            sys.executable,
            BATCH_SCRIPT,
            "--start", str(i),
            "--end", str(i + 1)
        ]
        
        try:
            process = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace')
            print(process.stdout)
            if process.stderr:
                print(f"STDERR: {process.stderr}")
        except Exception as e:
            print(f"Error running retry for index {i}: {e}")
            
    print("\nRetry process completed.")

if __name__ == "__main__":
    retry_tests()
