#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""检查测试进度"""
import json
from pathlib import Path

results_file = Path("test_results/batch_test_results.json")

if results_file.exists():
    with open(results_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if 'results' in data:
        results = data['results']
        total = len(results)
        success = sum(1 for r in results if r['status'] == 'success')
        failed = sum(1 for r in results if r['status'] == 'failed')
        error = sum(1 for r in results if r['status'] == 'error')
        
        print(f"Progress: {total}/541 ({total/541*100:.1f}%)")
        print(f"Success: {success} ({success/total*100:.1f}%)")
        print(f"Failed: {failed} ({failed/total*100:.1f}%)")
        print(f"Error: {error} ({error/total*100:.1f}%)")
    else:
        print("No results found in data")
else:
    print("Results file not found")

