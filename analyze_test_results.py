import os
import json
import glob

RESULTS_DIR = "batch_test_results"

def analyze_results():
    print(f"Analyzing results in {RESULTS_DIR}...")
    
    files = glob.glob(os.path.join(RESULTS_DIR, "results_*.json"))
    
    total = 0
    passed = 0
    failed = 0
    timeouts = 0
    errors = 0
    
    failures = []
    
    for file_path in files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            for result in data.get('results', []):
                total += 1
                status = result.get('status', 'unknown')
                
                if status == 'pass':
                    passed += 1
                elif status == 'fail':
                    failed += 1
                    failures.append(result)
                elif status == 'timeout':
                    timeouts += 1
                    failures.append(result)
                elif status == 'error':
                    errors += 1
                    failures.append(result)
                    
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            
    print("\n" + "="*60)
    print("TEST EXECUTION SUMMARY")
    print("="*60)
    print(f"Total Tests Run: {total}")
    print(f"Passed:          {passed} ({passed/total*100:.1f}%)" if total > 0 else "Passed: 0")
    print(f"Failed:          {failed}")
    print(f"Timeouts:        {timeouts}")
    print(f"Errors:          {errors}")
    print("="*60)
    
    if failures:
        print("\nFAILURE DETAILS:")
        for i, fail in enumerate(failures, 1):
            print(f"\n{i}. {fail.get('script_path')}")
            print(f"   Status: {fail.get('status').upper()}")
            print(f"   Return Code: {fail.get('return_code')}")
            print(f"   Duration: {fail.get('duration_seconds')}s")
            # print(f"   Stderr: {fail.get('stderr')[:200]}...")

if __name__ == "__main__":
    analyze_results()
