#!/bin/bash
# 全面测试脚本 - 运行所有可运行的示例

set +e  # 不要在错误时退出

echo "======================================================================"
echo "HydroClaude Examples 全面测试"
echo "======================================================================"

# 设置环境变量
export PYTHONPATH=/home/user/HydroClaude
export MPLBACKEND=Agg

# 计数器
total=0
success=0
failed=0

# 定义要测试的示例（扩展列表）
declare -a examples=(
    "example_01_canal_flow:code/01_basic.py"
    "example_01_canal_flow:code/06_animation.py"
    "example_02_pump_system:code/example_02_pump_system.py"
    "example_03_turbine_demo:example_03_turbine_comparison.py"
    "example_05_transient_analysis:example_05_load_rejection.py"
    "example_08_load_acceptance:example_08_load_acceptance.py"
    "example_17_reservoir_basic:demo_reservoir.py"
    "example_19_water_transfer:demo_water_transfer.py"
    "example_20_urban_water_supply:demo_urban_supply.py"
    "example_21_irrigation_optimization:demo_irrigation.py"
)

# 创建结果摘要
RESULT_FILE="/tmp/examples_test_summary.txt"
echo "示例运行摘要 - $(date)" > $RESULT_FILE
echo "======================================================================" >> $RESULT_FILE

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
        echo "[$total] $example_name - 失败 (目录不存在)" >> $RESULT_FILE
        continue
    fi

    cd "$example_dir"

    # 运行脚本，设置120秒超时
    log_file="/tmp/test_${example_name}_${total}.log"

    start_time=$(date +%s)
    if timeout 120 python "$script_path" > "$log_file" 2>&1; then
        end_time=$(date +%s)
        elapsed=$((end_time - start_time))
        echo "  ✓ 成功 (${elapsed}秒)"
        success=$((success + 1))
        echo "[$total] $example_name - 成功 (${elapsed}s)" >> $RESULT_FILE
    else
        echo "  ✗ 失败 (详见日志: $log_file)"
        failed=$((failed + 1))
        echo "[$total] $example_name - 失败 (日志: $log_file)" >> $RESULT_FILE

        # 显示错误的前10行
        echo "    错误信息:"
        head -10 "$log_file" | sed 's/^/      /'
    fi
done

echo ""
echo "======================================================================"
echo "测试完成"
echo "======================================================================"
echo "总计: $total"
echo "成功: $success"
echo "失败: $failed"
echo "成功率: $(awk "BEGIN {printf \"%.1f\", ($success/$total)*100}")%"
echo "======================================================================"

# 添加摘要到结果文件
echo "" >> $RESULT_FILE
echo "======================================================================" >> $RESULT_FILE
echo "总计: $total | 成功: $success | 失败: $failed" >> $RESULT_FILE
echo "成功率: $(awk "BEGIN {printf \"%.1f\", ($success/$total)*100}")%" >> $RESULT_FILE
echo "======================================================================" >> $RESULT_FILE

echo ""
echo "详细结果已保存到: $RESULT_FILE"
cat "$RESULT_FILE"

# 统计输出文件
echo ""
echo "======================================================================"
echo "输出文件统计"
echo "======================================================================"
find /home/user/HydroClaude/examples -type f -name "*.png" -newer /home/user/HydroClaude/examples/README.md 2>/dev/null | wc -l | xargs echo "新生成PNG:"
find /home/user/HydroClaude/examples -type f -name "*.gif" -newer /home/user/HydroClaude/examples/README.md 2>/dev/null | wc -l | xargs echo "新生成GIF:"

exit 0
