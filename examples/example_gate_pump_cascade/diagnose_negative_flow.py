#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
诊断负流量问题根源
"""

import os
import numpy as np
import matplotlib.pyplot as plt

def diagnose_negative_flow(scenario_dir):
    """诊断负流量出现的位置和时间"""
    
    scenario_name = os.path.basename(scenario_dir)
    data_file = os.path.join(scenario_dir, "scenario_data.npz")
    
    if not os.path.exists(data_file):
        return
    
    data = np.load(data_file)
    
    x = data['x']
    time = data['time']
    h_history = data['h_history']
    q_history = data['q_history']
    
    print(f"\n{'='*100}")
    print(f"工况: {scenario_name}".center(100))
    print('='*100)
    
    # 找到负流量
    neg_mask = q_history < 0
    if not neg_mask.any():
        print("✅ 无负流量")
        return
    
    # 统计
    neg_count = neg_mask.sum()
    total_count = q_history.size
    neg_percent = 100 * neg_count / total_count
    
    print(f"\n负流量统计:")
    print(f"  - 负值点数: {neg_count} / {total_count} ({neg_percent:.2f}%)")
    print(f"  - 最小流量: {q_history.min():.2f} m³/s")
    
    # 找到首次出现负流量的时间和位置
    time_idx, space_idx = np.where(neg_mask)
    if len(time_idx) > 0:
        first_idx = 0
        first_t_idx = time_idx[first_idx]
        first_x_idx = space_idx[first_idx]
        
        print(f"\n首次负流量:")
        print(f"  - 时间: t = {time[first_t_idx]:.1f} s (第{first_t_idx}步)")
        print(f"  - 位置: x = {x[first_x_idx]:.1f} m (第{first_x_idx}点)")
        print(f"  - 流量: Q = {q_history[first_t_idx, first_x_idx]:.2f} m³/s")
        
        # 检查前后时间步
        if first_t_idx > 0:
            print(f"\n前一时间步 (t={time[first_t_idx-1]:.1f}s):")
            print(f"  - 该位置流量: {q_history[first_t_idx-1, first_x_idx]:.2f} m³/s")
            print(f"  - 最小流量: {q_history[first_t_idx-1, :].min():.2f} m³/s")
        
        # 检查周围位置
        print(f"\n同时间步周围位置流量:")
        for di in [-2, -1, 0, 1, 2]:
            idx = first_x_idx + di
            if 0 <= idx < len(x):
                print(f"  - x={x[idx]:.1f}m: Q={q_history[first_t_idx, idx]:.2f} m³/s")
    
    # 分析空间分布
    print(f"\n空间分布:")
    neg_by_x = neg_mask.sum(axis=0)
    if neg_by_x.max() > 0:
        most_neg_idx = neg_by_x.argmax()
        print(f"  - 最常出现负值位置: x = {x[most_neg_idx]:.1f} m (出现{neg_by_x[most_neg_idx]}次)")
        
        # 检查是否集中在边界附近
        if most_neg_idx < 10:
            print(f"  ⚠️ 负值集中在上游边界附近")
        elif most_neg_idx > len(x) - 10:
            print(f"  ⚠️ 负值集中在下游边界附近")
    
    # 分析时间演化
    print(f"\n时间演化:")
    neg_by_t = neg_mask.sum(axis=1)
    if neg_by_t.max() > 0:
        most_neg_t_idx = neg_by_t.argmax()
        print(f"  - 负值最多时刻: t = {time[most_neg_t_idx]:.1f} s (有{neg_by_t[most_neg_t_idx]}个点)")
        
        # 检查是否在初期
        if most_neg_t_idx < 10:
            print(f"  ⚠️ 负值主要出现在初期 - 可能是初值问题")
    
    # 检查初值
    print(f"\n初值检查 (t=0):")
    print(f"  - 流量范围: [{q_history[0, :].min():.2f}, {q_history[0, :].max():.2f}] m³/s")
    print(f"  - 水深范围: [{h_history[0, :].min():.2f}, {h_history[0, :].max():.2f}] m")
    if q_history[0, :].min() < 0:
        print(f"  ❌ 初值就有负流量！稳态求解有问题")


def main():
    """主函数"""
    print("\n" + "="*100)
    print("负流量问题深度诊断".center(100))
    print("="*100)
    
    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results_advanced")
    
    # 选择几个典型工况进行详细分析
    scenarios_to_check = [
        "scenario_01_upstream_flow_large",
        "scenario_02_upstream_flow_medium",
        "scenario_03_downstream_level_step"
    ]
    
    for scenario in scenarios_to_check:
        scenario_dir = os.path.join(base_dir, scenario)
        if os.path.exists(scenario_dir):
            diagnose_negative_flow(scenario_dir)
    
    print("\n" + "="*100)
    print("诊断完成".center(100))
    print("="*100 + "\n")


if __name__ == "__main__":
    main()
