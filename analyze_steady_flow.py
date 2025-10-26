#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""详细分析恒定流水位分布"""

import numpy as np

# 加载稳态数据
data = np.load('examples/example_gate_pump_cascade/results/steady_state_data.npz')
x = data['x']
h = data['h']
q = data['q']
gate1_pos = data['gate1_pos']
pump_pos = data['pump_pos']
gate2_pos = data['gate2_pos']

# 计算底床高程
S0 = 0.0001
z = -S0 * x
# 泵后底床抬高5m
pump_idx = np.argmin(np.abs(x - pump_pos))
z[pump_idx:] += 5.0

# 计算水位（水面高程）
eta = z + h

# 找到关键位置的索引
gate1_idx = np.argmin(np.abs(x - gate1_pos))
gate2_idx = np.argmin(np.abs(x - gate2_pos))

print('=' * 90)
print('详细的恒定流水位分析')
print('=' * 90)
print()

# 1. 上游段（0 - 闸门1）
print('1. 上游段（渠首 → 闸门1，25km）')
print('-' * 90)
print(f'  渠首 (x=0km):')
print(f'    底床高程 z = {z[0]:.3f} m')
print(f'    水深 h = {h[0]:.3f} m')
print(f'    水位 η = {eta[0]:.3f} m')
print(f'    流量 Q = {q[0]:.3f} m³/s')
print()
print(f'  闸门1前 (x={x[gate1_idx-1]/1000:.2f}km):')
print(f'    底床高程 z = {z[gate1_idx-1]:.3f} m')
print(f'    水深 h = {h[gate1_idx-1]:.3f} m')
print(f'    水位 η = {eta[gate1_idx-1]:.3f} m')
print(f'    流量 Q = {q[gate1_idx-1]:.3f} m³/s')
print()
print(f'  水位变化: Δη = {eta[gate1_idx-1] - eta[0]:.3f} m')
print(f'  分析: 上游段水位{"上升" if eta[gate1_idx-1] > eta[0] else "下降"}（闸门1造成回水）')
print()

# 2. 闸门1前后
print('2. 闸门1 (x=25km)')
print('-' * 90)
print(f'  闸门1前:')
print(f'    水位 η = {eta[gate1_idx-1]:.3f} m, 水深 h = {h[gate1_idx-1]:.3f} m')
print(f'  闸门1后:')
print(f'    水位 η = {eta[gate1_idx+1]:.3f} m, 水深 h = {h[gate1_idx+1]:.3f} m')
print(f'  水位差: Δη = {eta[gate1_idx+1] - eta[gate1_idx-1]:.3f} m')
print(f'  分析: 闸门造成{"壅水" if eta[gate1_idx-1] > eta[gate1_idx+1] else "跌水"}')
print()

# 3. 中间段（闸门1 - 泵站）
print('3. 中间段（闸门1 → 泵站，25-50km）')
print('-' * 90)
print(f'  闸门1后 (x={x[gate1_idx+1]/1000:.2f}km):')
print(f'    水位 η = {eta[gate1_idx+1]:.3f} m')
print(f'  泵站前 (x={x[pump_idx-1]/1000:.2f}km):')
print(f'    底床高程 z = {z[pump_idx-1]:.3f} m')
print(f'    水深 h = {h[pump_idx-1]:.3f} m')
print(f'    水位 η = {eta[pump_idx-1]:.3f} m')
print(f'  水位变化: Δη = {eta[pump_idx-1] - eta[gate1_idx+1]:.3f} m')
print()

# 4. 泵站前后（关键！）
print('4. 泵站 (x=50km) ⭐ 关键分析')
print('-' * 90)
print(f'  泵站前（上游）:')
print(f'    底床高程 z = {z[pump_idx-1]:.3f} m')
print(f'    水深 h = {h[pump_idx-1]:.3f} m')
print(f'    水位 η = {eta[pump_idx-1]:.3f} m')
print(f'    流量 Q = {q[pump_idx-1]:.3f} m³/s')
print()
print(f'  泵站后（下游）:')
print(f'    底床高程 z = {z[pump_idx+1]:.3f} m')
print(f'    水深 h = {h[pump_idx+1]:.3f} m')
print(f'    水位 η = {eta[pump_idx+1]:.3f} m')
print(f'    流量 Q = {q[pump_idx+1]:.3f} m³/s')
print()
print(f'  泵站效果:')
print(f'    底床高差: Δz = {z[pump_idx+1] - z[pump_idx-1]:.3f} m (设计值: 5.0m)')
print(f'    水深差: Δh = {h[pump_idx+1] - h[pump_idx-1]:.3f} m (应接近0)')
print(f'    水位差: Δη = {eta[pump_idx+1] - eta[pump_idx-1]:.3f} m (应为5.0m)')
print(f'    流量变化: ΔQ = {q[pump_idx+1] - q[pump_idx-1]:.3f} m³/s (应为0)')
print()
if eta[pump_idx+1] > eta[pump_idx-1]:
    print(f'  ✅ 验证: 泵后水位 ({eta[pump_idx+1]:.3f}m) > 泵前水位 ({eta[pump_idx-1]:.3f}m)')
else:
    print(f'  ❌ 问题: 泵后水位 ({eta[pump_idx+1]:.3f}m) <= 泵前水位 ({eta[pump_idx-1]:.3f}m)')
print()

# 5. 泵站后到闸门2
print('5. 段落（泵站 → 闸门2，50-75km）')
print('-' * 90)
print(f'  泵站后 (x={x[pump_idx+1]/1000:.2f}km):')
print(f'    水位 η = {eta[pump_idx+1]:.3f} m')
print(f'  闸门2前 (x={x[gate2_idx-1]/1000:.2f}km):')
print(f'    底床高程 z = {z[gate2_idx-1]:.3f} m')
print(f'    水深 h = {h[gate2_idx-1]:.3f} m')
print(f'    水位 η = {eta[gate2_idx-1]:.3f} m')
print(f'  水位变化: Δη = {eta[gate2_idx-1] - eta[pump_idx+1]:.3f} m')
print()

# 6. 闸门2前后
print('6. 闸门2 (x=75km)')
print('-' * 90)
print(f'  闸门2前:')
print(f'    水位 η = {eta[gate2_idx-1]:.3f} m, 水深 h = {h[gate2_idx-1]:.3f} m')
print(f'  闸门2后:')
print(f'    水位 η = {eta[gate2_idx+1]:.3f} m, 水深 h = {h[gate2_idx+1]:.3f} m')
print(f'  水位差: Δη = {eta[gate2_idx+1] - eta[gate2_idx-1]:.3f} m')
print()

# 7. 下游段（闸门2 - 渠尾）
print('7. 下游段（闸门2 → 渠尾，75-100km）')
print('-' * 90)
print(f'  闸门2后 (x={x[gate2_idx+1]/1000:.2f}km):')
print(f'    水位 η = {eta[gate2_idx+1]:.3f} m')
print(f'  渠尾 (x=100km):')
print(f'    底床高程 z = {z[-1]:.3f} m')
print(f'    水深 h = {h[-1]:.3f} m')
print(f'    水位 η = {eta[-1]:.3f} m')
print(f'    流量 Q = {q[-1]:.3f} m³/s')
print(f'  水位变化: Δη = {eta[-1] - eta[gate2_idx+1]:.3f} m')
print()

# 8. 泵后与渠尾的关系
print('8. 泵后水位 vs 渠尾水位 ⭐ 关键关系')
print('-' * 90)
print(f'  泵后水位 (x=50.2km): η = {eta[pump_idx+1]:.3f} m')
print(f'  渠尾水位 (x=100km):   η = {eta[-1]:.3f} m')
print(f'  差值: Δη = {eta[-1] - eta[pump_idx+1]:.3f} m')
print()
if eta[-1] < eta[pump_idx+1]:
    print(f'  分析: 渠尾水位 < 泵后水位')
    print(f'       原因: 泵后到渠尾有50km距离，底坡使底床下降约{S0*50000:.1f}m')
    print(f'            闸门2造成一定的水位损失')
    print(f'       结论: ✅ 这是正常的，符合明渠水力学规律')
elif eta[-1] > eta[pump_idx+1]:
    print(f'  分析: 渠尾水位 > 泵后水位')
    print(f'       原因: 下游边界条件或闸门2造成回水')
    print(f'       结论: ⚠️ 需要检查下游边界条件设置')
else:
    print(f'  分析: 渠尾水位 = 泵后水位（特殊情况）')
print()

# 9. 整体分析
print('9. 整体水力分析')
print('-' * 90)
print(f'  全渠道水位范围: [{eta.min():.3f}, {eta.max():.3f}] m')
print(f'  全渠道水深范围: [{h.min():.3f}, {h.max():.3f}] m')
print(f'  平均流量: {np.mean(q):.3f} m³/s (目标: 30.0 m³/s)')
print(f'  流量标准差: {np.std(q):.6f} m³/s')
print()

# 检查水位是否单调或合理变化
print('  水位变化趋势:')
trend1 = eta[gate1_idx-1] - eta[0]
trend2 = eta[gate1_idx+1] - eta[gate1_idx-1]
trend3 = eta[pump_idx-1] - eta[gate1_idx+1]
trend4 = eta[pump_idx+1] - eta[pump_idx-1]
trend5 = eta[gate2_idx-1] - eta[pump_idx+1]
trend6 = eta[gate2_idx+1] - eta[gate2_idx-1]
trend7 = eta[-1] - eta[gate2_idx+1]

print(f'    渠首 → 闸门1前: {trend1:+.3f} m ({"上升-回水" if trend1 > 0 else "下降"})')
print(f'    闸门1前 → 闸门1后: {trend2:+.3f} m ({"壅水" if trend2 < 0 else "跌水或持平"})')
print(f'    闸门1后 → 泵站前: {trend3:+.3f} m')
print(f'    泵站前 → 泵站后: {trend4:+.3f} m ⭐ (泵站扬程效果)')
print(f'    泵站后 → 闸门2前: {trend5:+.3f} m')
print(f'    闸门2前 → 闸门2后: {trend6:+.3f} m')
print(f'    闸门2后 → 渠尾: {trend7:+.3f} m')
print()

# 10. 合理性判断
print('10. 合理性判断')
print('=' * 90)

checks = []

# 检查1: 泵后水位 > 泵前水位
check1 = eta[pump_idx+1] > eta[pump_idx-1]
delta_pump = eta[pump_idx+1] - eta[pump_idx-1]
checks.append(('泵后水位 > 泵前水位', check1, f'差值={delta_pump:.3f}m，目标=5.0m'))

# 检查2: 水位差接近泵站扬程
check2 = abs(delta_pump - 5.0) < 0.1
checks.append(('泵站水位差接近扬程(5m)', check2, f'误差={abs(delta_pump-5.0):.3f}m'))

# 检查3: 流量守恒
Q_mean = np.mean(q)
Q_error = abs(Q_mean - 30.0) / 30.0 * 100
check3 = Q_error < 1.0
checks.append(('流量守恒（误差<1%）', check3, f'误差={Q_error:.3f}%'))

# 检查4: 泵前后水深接近
dh_pump = abs(h[pump_idx+1] - h[pump_idx-1])
check4 = dh_pump < 0.5
checks.append(('泵前后水深接近（<0.5m）', check4, f'差值={dh_pump:.3f}m'))

# 检查5: 渠尾水位的合理性
L_pump_to_end = x[-1] - x[pump_idx+1]
z_drop = S0 * L_pump_to_end  # 底床下降
expected_eta_drop_min = z_drop * 0.5  # 至少应该下降底床下降的一半
check5 = (eta[pump_idx+1] - eta[-1]) >= expected_eta_drop_min
checks.append(('渠尾水位合理（考虑底坡）', check5, f'水位下降={eta[pump_idx+1]-eta[-1]:.3f}m'))

print()
for i, (desc, passed, detail) in enumerate(checks, 1):
    status = '✅ 通过' if passed else '❌ 不通过'
    print(f'  {status}  检查{i}: {desc}')
    print(f'          {detail}')
    print()

all_passed = all(check[1] for check in checks)
print('=' * 90)
if all_passed:
    print('✅ 总体结论: 恒定流结果完全合理！')
    print()
    print('核心验证:')
    print('  ✓ 泵站正确地将水位抬高了5m')
    print('  ✓ 泵前后水深基本不变（山区泵站特征）')
    print('  ✓ 流量完全守恒')
    print('  ✓ 渠尾水位合理（考虑了底坡和闸门影响）')
else:
    print('⚠️  总体结论: 存在一些需要关注的问题')
print('=' * 90)
