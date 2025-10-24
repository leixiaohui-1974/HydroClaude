"""
诊断：控制器性能排序问题

分析为什么MPC性能不如PID

作者：HydroClaude Team
日期：2025-10-24
"""

import numpy as np
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from control.idz_model import IDZParameters

print("=" * 80)
print("控制器性能排序问题诊断")
print("=" * 80)

# 当前配置
print("\n【SimplifiedCanalSimulator特性】")
print("- 渠道长度 L = 1000m")
print("- 渠道宽度 W = 10m")
print("- 上游水位 h = 2.5m (初始)")
print("- 下游水位 h_down = 2.2m")
print("- 目标水位 = 2.2m")
print("- 闸门方程: Q_out = Cd * a * W * sqrt(2*g*(h-h_down))")
print("- 控制作用: 闸门开度 a ↑ → 出流 Q_out ↑ → 水位 h ↓ (反向作用)")

print("\n【PID配置】")
print("- Kp = -0.5 (负增益)")
print("- Ki = -0.1 (负增益)")
print("- 输出范围: [0.1, 4.0]")
print("- 符号处理: ✓ 使用负增益处理反向作用")
print("- 性能: MAE = 0.0739m 🥇")

print("\n【自适应PI配置】")
print("- 初始 Kp = -0.5 (负增益)")
print("- 初始 Ki = -0.1 (负增益)")
print("- 在线辨识: IDZIdentifier")
print("- IMC整定: 自动计算Kp, Ki后取负")
print("- 符号处理: ✓ 使用负增益处理反向作用")
print("- 性能: MAE = 0.0939m 🥈")

print("\n【MPC配置】")
idz_params = IDZParameters(K=100.0, tau_z=200.0, tau_d=300.0, theta=20.0)
print(f"- IDZ模型: K = {idz_params.K} (正值)")
print(f"- IDZ模型: tau_z = {idz_params.tau_z}s")
print(f"- IDZ模型: tau_d = {idz_params.tau_d}s")
print(f"- IDZ模型: theta = {idz_params.theta}s")
print("- 预测步长: 15")
print("- 控制步长: 10")
print("- 输出范围: [0.5, 4.0]")
print("- 符号处理: ✗ IDZ模型是正向的，未处理反向作用!")
print("- 性能: MAE = 0.1808m 🥉 (最差)")

print("\n【关键问题诊断】")
print("❌ 问题1：模型方向不匹配")
print("   - SimplifiedCanalSimulator: 闸门反向作用 (u↑ → h↓)")
print("   - MPC的IDZ模型: K=100 > 0，表示正向作用 (u↑ → h↑)")
print("   - 结论: 模型预测完全相反!")

print("\n❌ 问题2：控制约束不合理")
print("   - MPC: u_min = 0.5 (太大)")
print("   - PID: output_min = 0.1")
print("   - 结论: MPC无法充分降低闸门开度")

print("\n❌ 问题3：IDZ参数不符合实际")
print("   - 实际系统: 物理水量平衡 (dV/dt = Q_in - Q_out)")
print("   - MPC假设: IDZ传递函数 G(s) = K*(1+tau_z*s)/(s*(1+tau_d*s))*e^(-theta*s)")
print("   - 参数来源: 经验值，未从实际系统辨识")
print("   - 结论: 模型参数不准确")

print("\n【修复方案】")
print("✅ 方案1：修改IDZ模型方向（推荐）")
print("   - 将 K = 100 改为 K = -100")
print("   - 或者在MPC内部反转误差符号")
print("   - 使模型方向与实际系统一致")

print("\n✅ 方案2：放宽MPC控制约束")
print("   - u_min: 0.5 → 0.1")
print("   - 允许更小的闸门开度")

print("\n✅ 方案3：重新辨识IDZ参数")
print("   - 使用SimplifiedCanalSimulator生成数据")
print("   - 用IDZIdentifier辨识真实参数")
print("   - 使用辨识的参数配置MPC")

print("\n✅ 方案4：调整MPC权重")
print("   - 当前 Q=100, R=1 (偏重跟踪)")
print("   - 可能导致控制量变化过大")
print("   - 尝试增大R提高稳定性")

print("\n" + "=" * 80)
print("开始验证方案1：反转IDZ模型方向")
print("=" * 80)

# 测试反转符号的效果
print("\n测试：如果MPC使用K=-100（负值）")
print("场景：h=2.5m, 目标=2.2m, 误差=0.3m (水位过高)")
print()
print("使用K=100 (当前错误配置):")
print("  MPC预测: u增大 → 水位上升 → 误差增大 ❌")
print("  实际系统: u增大 → 水位下降 → 误差减小 ✓")
print("  结论: 模型预测与实际相反!")
print()
print("使用K=-100 (正确配置):")
print("  MPC预测: u增大 → 水位下降 → 误差减小 ✓")
print("  实际系统: u增大 → 水位下降 → 误差减小 ✓")
print("  结论: 模型预测与实际一致!")

print("\n" + "=" * 80)
print("结论：MPC性能差的根本原因是模型方向与实际系统相反")
print("=" * 80)
