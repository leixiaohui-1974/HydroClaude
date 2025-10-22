#!/bin/bash
# 批量运行核心示例脚本

set -e

echo "======================================================================"
echo "批量运行HydroClaude核心示例"
echo "======================================================================"

# 设置Python路径
export PYTHONPATH=/home/user/HydroClaude
export MPLBACKEND=Agg

# 计数器
total=0
success=0
failed=0

# 定义要运行的核心示例
declare -a examples=(
    "example_01_canal_flow:code/01_basic.py"
    "example_01_canal_flow:code/06_animation.py"
    "example_03_turbine_demo:example_03_turbine_comparison.py"
    "example_05_transient_analysis:example_05_load_rejection.py"
    "example_08_load_acceptance:example_08_load_acceptance.py"
    "example_17_reservoir_basic:demo_reservoir.py"
)

# 运行每个示例
for item in "${examples[@]}"; do
    IFS=':' read -r example_name script_path <<< "$item"

    total=$((total + 1))

    echo ""
    echo "======================================================================"
    echo "[$total/${#examples[@]}] 运行: $example_name / $script_path"
    echo "======================================================================"

    example_dir="/home/user/HydroClaude/examples/$example_name"

    if [ ! -d "$example_dir" ]; then
        echo "  ✗ 目录不存在: $example_dir"
        failed=$((failed + 1))
        continue
    fi

    cd "$example_dir"

    # 运行脚本
    if timeout 300 python "$script_path" > /tmp/run_${example_name}_${total}.log 2>&1; then
        echo "  ✓ 成功"
        success=$((success + 1))
    else
        echo "  ✗ 失败 (详见日志: /tmp/run_${example_name}_${total}.log)"
        failed=$((failed + 1))
    fi
done

echo ""
echo "======================================================================"
echo "运行完成"
echo "======================================================================"
echo "总计: $total"
echo "成功: $success"
echo "失败: $failed"
echo "======================================================================"
