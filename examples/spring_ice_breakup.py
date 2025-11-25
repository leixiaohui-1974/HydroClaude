#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HydroClaude 应用案例: 春季融冰期模拟

场景: 北方河流春季解冻过程
- 气温从负值逐渐上升
- 冰盖逐渐融化
- 水温回升
- 光照逐渐增强
- 藻类开始复苏

应用: 春季水质预测生态恢复评估

作者: HydroClaude Team
日期: 2025-11-02
版本: v1.0
"""

import numpy as np
import warnings
warnings.filterwarnings("ignore")
import matplotlib.pyplot as plt
from pathlib import Path
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from solvers.water_temperature import WaterTemperatureSolver
from solvers.dissolved_oxygen import DissolvedOxygenSolver
from solvers.ice_cover import IceCoverSolver
from solvers.nutrients import NutrientsSolver
from solvers.phytoplankton import PhytoplanktonSolver

print("=" * 70)
print("HydroClaude 春季融冰期模拟")
print("=" * 70)
print()

# ==================== 场景设置 ====================
print("[1] 场景设置: 北方河流春季解冻")
print("-" * 70)

# 河道参数
L = 15000.0  # 15 km
n_cells = 150
dx = L / n_cells
print(f"河道长度: {L/1000:.1f} km")
print(f"网格数: {n_cells}")
print()

# 水力条件
u = np.full(n_cells, 0.4)  # 融雪径流流速增加
h = np.full(n_cells, 3.5)  # 水深增加
manning_n = np.full(n_cells, 0.03)
print(f"流速: {u[0]:.1f} m/s (融雪径流)")
print(f"水深: {h[0]:.1f} m (水位上涨)")
print()

# 模拟时间
n_days = 21  # 3周
dt = 3600.0  # 1小时步长
n_steps = int(n_days * 24 * 3600 / dt)
print(f"模拟时间: {n_days} 天")
print(f"时间步长: {dt/3600:.0f} 小时")
print()

# ==================== 初始条件 ====================
print("[2] 初始条件: 早春冰封期末")
print("-" * 70)

# 水温: 接近冰点
T_init = np.full(n_cells, 0.5)  #  degC
print(f"初始水温: {T_init[0]:.1f}  degC (接近冰点)")

# DO: 冰封期DO较高
DO_init = np.full(n_cells, 13.0)  # mg/L
print(f"初始DO: {DO_init[0]:.1f} mg/L (高溶解度)")

# 冰盖: 有一定厚度
ice_thickness_init = np.full(n_cells, 0.30)  # 30 cm
print(f"初始冰厚: {ice_thickness_init[0]*100:.0f} cm")

# 营养盐: 冬季积累
NH4_init = np.full(n_cells, 0.4)  # mg/L
NO3_init = np.full(n_cells, 1.5)  # mg/L
PO4_init = np.full(n_cells, 0.10)  # mg/L
OrgN_init = np.full(n_cells, 0.8)  # mg/L (冬季积累)
OrgP_init = np.full(n_cells, 0.08)  # mg/L
TN = NH4_init[0] + NO3_init[0] + OrgN_init[0]
TP = PO4_init[0] + OrgP_init[0]
print(f"总氮TN: {TN:.2f} mg/L")
print(f"总磷TP: {TP:.3f} mg/L")

# 叶绿素: 冬季很低
Chla_init = np.full(n_cells, 3.0)  # mug/L
print(f"初始叶绿素: {Chla_init[0]:.1f} mug/L (冬季低水平)")
print()

# ==================== 气象条件 ====================
print("[3] 气象条件: 春季气温回升")
print("-" * 70)

def get_spring_forcing(day):
    """春季气象强迫"""
    hour = (day - int(day)) * 24

    # 气温: 从-5 degC逐渐上升到15 degC
    T_start = -5.0
    T_end = 15.0
    T_mean = T_start + (T_end - T_start) * day / n_days

    # 日变化
    T_amplitude = 5.0  #  degC
    T_air = T_mean + T_amplitude * np.sin(2 * np.pi * (hour - 6) / 24)

    # 太阳辐射: 春季逐渐增强
    if 6 <= hour <= 18:  # 白天12小时
        # 最大辐射从200逐渐增加到500 W/m^2
        max_rad_start = 200.0
        max_rad_end = 500.0
        max_radiation = max_rad_start + (max_rad_end - max_rad_start) * day / n_days
        I_0 = max_radiation * np.sin(np.pi * (hour - 6) / 12)
    else:
        I_0 = 0.0

    return T_air, I_0

# 其他气象参数
wind_speed = 4.0  # m/s (春季多风)
relative_humidity = 0.65
cloud_cover = 0.2

print(f"气温变化: -5 degC -> 15 degC (21天)")
print(f"太阳辐射: 200 -> 500 W/m^2 (逐渐增强)")
print(f"白天时长: 12 小时")
print(f"风速: {wind_speed:.1f} m/s")
print()

# ==================== 初始化求解器 ====================
print("[4] 初始化求解器")
print("-" * 70)

temp_solver = WaterTemperatureSolver(n_cells, dx, use_numba=False)
temp_solver.T = T_init.copy()

do_solver = DissolvedOxygenSolver(
    n_cells, dx,
    kd_20=0.10,  # 春季BOD降解慢
    SOD_20=0.5,  # 底泥耗氧低
    use_numba=False
)
do_solver.DO = DO_init.copy()
do_solver.BOD = np.full(n_cells, 2.0)  # 低BOD

ice_solver = IceCoverSolver(n_cells=n_cells)
ice_solver.ice_thickness = ice_thickness_init.copy()
ice_solver.ice_cover_fraction = np.ones(n_cells)  # 完全覆盖

nutrients_solver = NutrientsSolver(n_cells, dx, use_numba=False)
nutrients_solver.NH4 = NH4_init.copy()
nutrients_solver.NO3 = NO3_init.copy()
nutrients_solver.PO4 = PO4_init.copy()
nutrients_solver.OrgN = OrgN_init.copy()
nutrients_solver.OrgP = OrgP_init.copy()

algae_solver = PhytoplanktonSolver(n_cells, dx, use_numba=False)
algae_solver.Chla = Chla_init.copy()

print(" 所有求解器初始化完成")
print()

# ==================== 时间积分 ====================
print("[5] 时间积分")
print("-" * 70)
print(f"开始模拟 {n_days} 天...")
print()

# 输出存储每天输出
output_interval = 24
output_times = []
output_T = []
output_DO = []
output_ice_thickness = []
output_ice_fraction = []
output_NH4 = []
output_NO3 = []
output_Chla = []
output_Tair = []

# 保存初始状态
output_times.append(0)
output_T.append(temp_solver.T.mean())
output_DO.append(do_solver.DO.mean())
output_ice_thickness.append(ice_solver.ice_thickness.mean())
output_ice_fraction.append(ice_solver.ice_cover_fraction.mean())
output_NH4.append(nutrients_solver.NH4.mean())
output_NO3.append(nutrients_solver.NO3.mean())
output_Chla.append(algae_solver.Chla.mean())
T_air, _ = get_spring_forcing(0)
output_Tair.append(T_air)

# 时间循环
for step in range(n_steps):
    t = step * dt
    day = t / 86400.0

    # 气象强迫
    T_air, I_0_surface = get_spring_forcing(day)
    I_0 = np.full(n_cells, I_0_surface)

    # Step 1: 水温
    T = temp_solver.step(
        dt, u, h, T_air, I_0_surface, wind_speed, relative_humidity,
        ice_cover_fraction=ice_solver.ice_cover_fraction
    )

    # Step 2: 冰盖融化过程
    ice_state = ice_solver.step(dt, T_air, T)

    # Step 3: 营养盐
    nutrients_state = nutrients_solver.step(dt, u, h, T, do_solver.DO)

    # Step 4: 藻类
    algae_state = algae_solver.step(
        dt, u, h, T, I_0,
        nutrients_solver.NH4,
        nutrients_solver.NO3,
        nutrients_solver.PO4,
        ice_cover_fraction=ice_solver.ice_cover_fraction
    )

    # Step 5: DO
    do_state = do_solver.step(
        dt, u, h, T, manning_n,
        ice_cover_fraction=ice_solver.ice_cover_fraction
    )

    # 耦合
    dt_day = dt / 86400.0
    do_solver.DO += algae_state['DO_production'] * dt_day
    do_solver.DO = np.maximum(do_solver.DO, 0.0)

    nutrients_solver.NH4 -= algae_state['NH4_uptake'] * dt_day
    nutrients_solver.NH4 = np.maximum(nutrients_solver.NH4, 0.0)

    nutrients_solver.NO3 -= algae_state['NO3_uptake'] * dt_day
    nutrients_solver.NO3 = np.maximum(nutrients_solver.NO3, 0.0)

    # 输出
    if (step + 1) % output_interval == 0:
        output_times.append(day)
        output_T.append(temp_solver.T.mean())
        output_DO.append(do_solver.DO.mean())
        output_ice_thickness.append(ice_solver.ice_thickness.mean())
        output_ice_fraction.append(ice_solver.ice_cover_fraction.mean())
        output_NH4.append(nutrients_solver.NH4.mean())
        output_NO3.append(nutrients_solver.NO3.mean())
        output_Chla.append(algae_solver.Chla.mean())
        T_air_now, _ = get_spring_forcing(day)
        output_Tair.append(T_air_now)

        print(f"Day {day:4.0f}: Tair={T_air_now:6.1f} degC, T={T.mean():5.2f} degC, "
              f"Ice={ice_solver.ice_thickness.mean()*100:5.1f}cm, "
              f"Chla={algae_solver.Chla.mean():5.1f}mug/L")

print()
print(" 模拟完成!")
print()

# ==================== 结果分析 ====================
print("[6] 结果分析")
print("=" * 70)

output_times = np.array(output_times)
output_T = np.array(output_T)
output_DO = np.array(output_DO)
output_ice_thickness = np.array(output_ice_thickness)
output_ice_fraction = np.array(output_ice_fraction)
output_Chla = np.array(output_Chla)
output_Tair = np.array(output_Tair)

print(f"初始状态:")
print(f"  气温: {output_Tair[0]:.1f}  degC")
print(f"  水温: {output_T[0]:.1f}  degC")
print(f"  冰厚: {output_ice_thickness[0]*100:.0f} cm")
print(f"  叶绿素: {output_Chla[0]:.1f} mug/L")
print()

print(f"最终状态 (Day {n_days}):")
print(f"  气温: {output_Tair[-1]:.1f}  degC")
print(f"  水温: {output_T[-1]:.1f}  degC")
print(f"  冰厚: {output_ice_thickness[-1]*100:.1f} cm")
print(f"  冰盖覆盖率: {output_ice_fraction[-1]*100:.1f}%")
print(f"  叶绿素: {output_Chla[-1]:.1f} mug/L")
print()

# 融冰进程
ice_free_day = None
for i, frac in enumerate(output_ice_fraction):
    if frac < 0.1:
        ice_free_day = output_times[i]
        break

if ice_free_day:
    print(f"解冻完成时间: Day {ice_free_day:.0f}")
else:
    print(f"解冻未完成 (残余冰盖: {output_ice_fraction[-1]*100:.1f}%)")
print()

print("变化量:")
print(f"  水温上升: {output_T[-1] - output_T[0]:+.1f}  degC")
print(f"  冰厚减少: {(output_ice_thickness[0] - output_ice_thickness[-1])*100:.1f} cm")
print(f"  藻类恢复: {output_Chla[-1] / output_Chla[0]:.1f} 倍")
print()

# ==================== 可视化 ====================
print("[7] 生成可视化")
print("-" * 70)

fig, axes = plt.subplots(3, 2, figsize=(14, 12))

# (1,1) 气温和水温
ax = axes[0, 0]
ax.plot(output_times, output_Tair, 'r--', linewidth=2, label='Air Temp')
ax.plot(output_times, output_T, 'b-', linewidth=2, label='Water Temp')
ax.axhline(0, color='gray', linestyle='--', linewidth=1)
ax.set_xlabel('Time (days)')
ax.set_ylabel('Temperature ( degC)')
ax.set_title('(a) Temperature Recovery')
ax.legend()
ax.grid(True, alpha=0.3)

# (1,2) 冰盖融化
ax = axes[0, 1]
ax.plot(output_times, output_ice_thickness * 100, 'c-', linewidth=2.5, label='Ice Thickness')
ax2 = ax.twinx()
ax2.plot(output_times, output_ice_fraction * 100, 'm--', linewidth=2, label='Ice Cover %')
ax.set_xlabel('Time (days)')
ax.set_ylabel('Ice Thickness (cm)', color='c')
ax2.set_ylabel('Ice Cover (%)', color='m')
ax.set_title('(b) Ice Breakup Process')
ax.tick_params(axis='y', labelcolor='c')
ax2.tick_params(axis='y', labelcolor='m')
ax.grid(True, alpha=0.3)

# (2,1) DO演变
ax = axes[1, 0]
ax.plot(output_times, output_DO, 'b-', linewidth=2)
ax.set_xlabel('Time (days)')
ax.set_ylabel('DO (mg/L)')
ax.set_title('(c) DO Evolution')
ax.grid(True, alpha=0.3)

# (2,2) 藻类复苏
ax = axes[1, 1]
ax.plot(output_times, output_Chla, 'g-', linewidth=2.5)
ax.set_xlabel('Time (days)')
ax.set_ylabel('Chlorophyll-a (mug/L)')
ax.set_title('(d) Algal Recovery')
ax.grid(True, alpha=0.3)

# (3,1) 营养盐
ax = axes[2, 0]
ax.plot(output_times, output_NH4, 'r-', linewidth=2, label='NH4')
ax.plot(output_times, output_NO3, 'b-', linewidth=2, label='NO3')
ax.set_xlabel('Time (days)')
ax.set_ylabel('Concentration (mg/L)')
ax.set_title('(e) Nutrients Dynamics')
ax.legend()
ax.grid(True, alpha=0.3)

# (3,2) 综合状态
ax = axes[2, 1]
# 归一化显示
T_norm = (output_T - output_T.min()) / (output_T.max() - output_T.min() + 1e-6)
ice_norm = output_ice_fraction
chla_norm = (output_Chla - output_Chla.min()) / (output_Chla.max() - output_Chla.min() + 1e-6)

ax.plot(output_times, T_norm, 'r-', linewidth=2, label='Temp (normalized)')
ax.plot(output_times, 1 - ice_norm, 'c-', linewidth=2, label='Ice-free fraction')
ax.plot(output_times, chla_norm, 'g-', linewidth=2, label='Algae (normalized)')
ax.set_xlabel('Time (days)')
ax.set_ylabel('Normalized Value')
ax.set_title('(f) Spring Ecosystem Recovery')
ax.legend()
ax.grid(True, alpha=0.3)

plt.tight_layout()
output_file = 'spring_ice_breakup_results.png'
plt.savefig(output_file, dpi=150, bbox_inches='tight')
print(f" 图表已保存: {output_file}")
print()

# ==================== 总结 ====================
print("[8] 模拟总结")
print("=" * 70)
print()
print(" 成功模拟了春季融冰期生态恢复过程")
print()
print("主要发现:")
print(f"  1. 气温回升: {output_Tair[0]:.1f} -> {output_Tair[-1]:.1f}  degC")
print(f"  2. 水温恢复: {output_T[0]:.1f} -> {output_T[-1]:.1f}  degC")
print(f"  3. 冰盖融化: {output_ice_thickness[0]*100:.0f} -> {output_ice_thickness[-1]*100:.1f} cm")
if ice_free_day:
    print(f"  4. 解冻时间: Day {ice_free_day:.0f}")
print(f"  5. 藻类恢复: {output_Chla[0]:.1f} -> {output_Chla[-1]:.1f} mug/L ({output_Chla[-1]/output_Chla[0]:.1f}倍)")
print()
print("生态过程:")
print("   气温回升 -> 冰盖融化")
print("   冰盖融化 -> 光照增强")
print("   水温回升 + 光照增强 -> 藻类复苏")
print("   冰盖消失 -> 大气复氧恢复")
print("   春季是生态系统从冬眠到活跃的关键转换期")
print()
print("=" * 70)
print("HydroClaude v1.0 - 春季生态恢复评估工具 ")
print("=" * 70)
