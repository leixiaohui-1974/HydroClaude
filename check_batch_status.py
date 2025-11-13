#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
检查批次状态和修复情况

Author: HydroClaude
Date: 2025-11-13
"""

import json
import os

def main():
    """检查状态"""
    
    state_file = 'test_results/batch_state.json'
    
    if not os.path.exists(state_file):
        print("No state file found")
        return
    
    with open(state_file, 'r', encoding='utf-8') as f:
        state = json.load(f)
    
    print("="*70)
    print("BATCH STATUS REPORT")
    print("="*70)
    print()
    
    # 总体统计
    print(f"Total batches completed: {state['current_batch']}/37")
    print(f"Total files tested: {state['stats']['total_passed'] + state['stats']['total_failed']}/361")
    print(f"Total passed: {state['stats']['total_passed']}")
    print(f"Total failed: {state['stats']['total_failed']}")
    print(f"Total fixed: {state['stats']['total_fixed']}")
    print(f"Current pass rate: {state['stats']['total_passed']/(state['stats']['total_passed']+state['stats']['total_failed'])*100:.1f}%")
    print()
    
    # 第一批详情
    print("="*70)
    print("BATCH 1 DETAILS:")
    print("="*70)
    
    batch1_files = state['all_files'][0:10]
    
    for i, file in enumerate(batch1_files, 1):
        basename = os.path.basename(file)
        result = state['results'].get(file, {})
        status = result.get('status', 'N/A')
        fixed = result.get('fixed', False)
        
        symbol = '[OK]' if status == 'PASS' else f'[{status}]'
        fix_status = ' (FIXED)' if fixed else ''
        
        print(f"{i:2d}. {basename:50s} {symbol}{fix_status}")
    
    batch1_passed = sum(1 for f in batch1_files if state['results'].get(f, {}).get('status') == 'PASS')
    batch1_failed = 10 - batch1_passed
    
    print()
    print(f"Batch 1 Summary: {batch1_passed} passed, {batch1_failed} failed")
    print()
    
    # 问题分析
    print("="*70)
    print("ISSUE ANALYSIS:")
    print("="*70)
    
    if state['stats']['total_fixed'] == 0:
        print("[!] WARNING: No files were successfully fixed!")
        print()
        print("Possible reasons:")
        print("  1. Fix function is not working properly")
        print("  2. Files don't match the fix patterns")
        print("  3. Files are not writable")
        print()
        print("Recommendation: Improve the fix_file() function")
    
    print()
    print("="*70)


if __name__ == '__main__':
    main()

