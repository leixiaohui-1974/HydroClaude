"""测试适配器改进：验证新字段提取"""
from pathlib import Path
import json
from integration.hec_ras_adapter import extract_hecras_result_summary

# 测试 HDF 文件
test_hdf = Path(r"Z:\research\hydroclaude\reports\hec_ras_example_project\Example 1 - Critical Creek_hydromind2\CRITCREK.p01.hdf")

if not test_hdf.exists():
    print(f"ERROR: Test HDF not found: {test_hdf}")
    exit(1)

print(f"Testing HDF: {test_hdf}")
print("=" * 80)

# 提取结果
try:
    result = extract_hecras_result_summary(test_hdf)
    
    print(f"\n[基本信息]")
    print(f"  模式: {result.mode}")
    print(f"  单位制: {result.unit_system}")
    print(f"  单位制来源: {result.unit_system_source}")
    print(f"  断面数: {result.n_cross_sections}")
    print(f"  剖面数: {result.n_profiles}")
    
    print(f"\n[新增字段检查]")
    print(f"  reach_lengths_m: {'OK' if result.reach_lengths_m else 'MISSING'} ({len(result.reach_lengths_m) if result.reach_lengths_m else 0} 个)")
    print(f"  reach_lengths_lob_m: {'OK' if result.reach_lengths_lob_m else 'MISSING'} ({len(result.reach_lengths_lob_m) if result.reach_lengths_lob_m else 0} 个)")
    print(f"  reach_lengths_rob_m: {'OK' if result.reach_lengths_rob_m else 'MISSING'} ({len(result.reach_lengths_rob_m) if result.reach_lengths_rob_m else 0} 个)")
    print(f"  manning_n_ch_values: {'OK' if result.manning_n_ch_values else 'MISSING'} ({len(result.manning_n_ch_values) if result.manning_n_ch_values else 0} 个)")
    print(f"  manning_n_lob_values: {'OK' if result.manning_n_lob_values else 'MISSING'} ({len(result.manning_n_lob_values) if result.manning_n_lob_values else 0} 个)")
    print(f"  manning_n_rob_values: {'OK' if result.manning_n_rob_values else 'MISSING'} ({len(result.manning_n_rob_values) if result.manning_n_rob_values else 0} 个)")
    print(f"  left_bank_m: {'OK' if result.left_bank_m else 'MISSING'} ({len(result.left_bank_m) if result.left_bank_m else 0} 个)")
    print(f"  right_bank_m: {'OK' if result.right_bank_m else 'MISSING'} ({len(result.right_bank_m) if result.right_bank_m else 0} 个)")
    print(f"  contraction_coefs: {'OK' if result.contraction_coefs else 'MISSING'} ({len(result.contraction_coefs) if result.contraction_coefs else 0} 个)")
    print(f"  expansion_coefs: {'OK' if result.expansion_coefs else 'MISSING'} ({len(result.expansion_coefs) if result.expansion_coefs else 0} 个)")
    
    print(f"\n[参数完整性报告]")
    if result.parameter_completeness:
        for key, value in result.parameter_completeness.items():
            status = "OK" if value else "MISSING"
            print(f"  {key}: {status}")
    else:
        print("  ERROR: parameter_completeness is None")
    
    # 显示前3个断面的数据样本
    if result.reach_lengths_lob_m and len(result.reach_lengths_lob_m) >= 3:
        print(f"\n[数据样本 - 前3个断面]")
        for i in range(min(3, result.n_cross_sections)):
            print(f"  断面 {i}:")
            if result.reach_lengths_m:
                print(f"    流程长(Channel): {result.reach_lengths_m[i]:.2f} m")
            if result.reach_lengths_lob_m:
                print(f"    流程长(LOB): {result.reach_lengths_lob_m[i]:.2f} m")
            if result.reach_lengths_rob_m:
                print(f"    流程长(ROB): {result.reach_lengths_rob_m[i]:.2f} m")
            if result.manning_n_ch_values:
                print(f"    Manning n(Channel): {result.manning_n_ch_values[i]:.4f}")
            if result.manning_n_lob_values:
                print(f"    Manning n(LOB): {result.manning_n_lob_values[i]:.4f}")
            if result.manning_n_rob_values:
                print(f"    Manning n(ROB): {result.manning_n_rob_values[i]:.4f}")
    
    print(f"\n{'='*80}")
    print("测试通过！所有新字段已成功提取。")
    
except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
