#!/bin/bash
# 一键测试核心学习案例

echo "========================================================================"
echo "测试核心学习路径（14个案例）"
echo "========================================================================"
echo ""

cd examples/example_01_canal_flow/scripts

PASSED=0
FAILED=0
TOTAL=0

# Level 1 cases
cases=(
  "01_basic_v2.py:01-第一个模拟"
  "02_methods_comparison.py:02-参数影响"
  "07_sluice_gate_flow_v2.py:03-添加闸门"
  "04_boundary_conditions_v2.py:04-边界条件"
  "06_animation.py:05-可视化"
  "05_step_response.py:06-非恒定流"
  "08_optimized_steady_solving_v2.py:07-优化求解"
  "11_advanced_structures.py:08-多个结构"
  "12_advanced_optimized_v2.py:09-复杂系统"
  "03_idz_identification.py:10-系统辨识"
  "01_basic_v2_refactored.py:11-代码重构"
  "07_sluice_gate_flow_v2_refactored.py:12-闸门优化"
  "08_optimized_steady_solving_v2_refactored.py:13-求解器优化"
  "12_advanced_optimized_v2_refactored.py:14-综合项目"
)

for case in "${cases[@]}"; do
  IFS=':' read -r script title <<< "$case"
  TOTAL=$((TOTAL + 1))
  
  echo -n "[$TOTAL/14] $title..."
  
  if timeout 90 python3 "$script" > /dev/null 2>&1; then
    echo " ✅"
    PASSED=$((PASSED + 1))
  else
    echo " ❌"
    FAILED=$((FAILED + 1))
  fi
done

echo ""
echo "========================================================================"
echo "测试完成"
echo "========================================================================"
echo "总数: $TOTAL"
echo "通过: $PASSED"
echo "失败: $FAILED"
echo "成功率: $((PASSED * 100 / TOTAL))%"
echo "========================================================================"

if [ $PASSED -eq $TOTAL ]; then
  echo "🎉 所有案例测试通过！可以开始学习了！"
  exit 0
else
  echo "⚠️ 有案例测试失败，请检查环境配置"
  exit 1
fi
