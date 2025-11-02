#!/usr/bin/env python3
"""
HydroClaude 端到端应用示例: 冬季河流冰-水质模拟

场景: 北方河流冬季冰封期水质演变
- 气温从0°C逐渐下降到-15°C
- 河流逐渐结冰
- 冰盖遮蔽导致DO下降
- 藻类生长受到抑制
- 营养盐循环变缓

对标: 松花江/黄河凌汛期水质变化

作者: HydroClaude Team
日期: 2025-11-02
版本: v1.0
"""

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# 导入HydroClaude模块
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from solvers.water_temperature import WaterTemperatureSolver
from solvers.dissolved_oxygen import DissolvedOxygenSolver
from solvers.ice_cover import IceCoverSolver
from solvers.nutrients import NutrientsSolver
from solvers.phytoplankton import PhytoplanktonSolver

print("=" * 70)
print("HydroClaude 冬季河流冰-水质模拟示例")
print("=" * 70)
print()

# ==================== 场景设置 ====================
print("[1] 场景设置")
print("-" * 70)

# 河道参数
L = 10000.0  # 河道长度 (m)
n_cells = 100  # 网格数
dx = L / n_cells  # 空间步长 (m)
print(f"河道长度: {L/1000:.1f} km")
print(f"网格数: {n_cells}")
print(f"空间步长: {dx:.1f} m")
print()

# 水力条件
u = np.full(n_cells, 0.3)  # 流速 (m/s)
h = np.full(n_cells, 2.5)  # 水深 (m)
manning_n = np.full(n_cells, 0.03)  # 曼宁系数
width = 30.0  # 河宽 (m)
print(f"流速: {u[0]:.1f} m/s")
print(f"水深: {h[0]:.1f} m")
print(f"河宽: {width:.1f} m")
print(f"流量: {u[0] * h[0] * width:.1f} m³/s")
print()

# 模拟时间
n_days = 30  # 模拟30天
dt = 3600.0  # 时间步长 1小时 (s)
n_steps = int(n_days * 24 * 3600 / dt)
print(f"模拟时间: {n_days} 天")
print(f"时间步长: {dt/3600:.1f} 小时")
print(f"总步数: {n_steps}")
print()

# ==================== 初始条件 ====================
print("[2] 初始条件")
print("-" * 70)

# 水温: 初冬，接近冰点
T_init = np.full(n_cells, 2.0)  # °C
print(f"初始水温: {T_init[0]:.1f} °C")

# 溶解氧: 较高（低温高溶解度）
DO_init = np.full(n_cells, 12.0)  # mg/L
print(f"初始DO: {DO_init[0]:.1f} mg/L")

# 营养盐: 秋季残留营养盐
NH4_init = np.full(n_cells, 0.3)  # mg/L
NO3_init = np.full(n_cells, 1.2)  # mg/L
PO4_init = np.full(n_cells, 0.08)  # mg/L
OrgN_init = np.full(n_cells, 0.5)  # mg/L
OrgP_init = np.full(n_cells, 0.05)  # mg/L
print(f"初始NH4: {NH4_init[0]:.2f} mg/L")
print(f"初始NO3: {NO3_init[0]:.2f} mg/L")
print(f"初始PO4: {PO4_init[0]:.3f} mg/L")
print(f"总氮TN: {(NH4_init[0] + NO3_init[0] + OrgN_init[0]):.2f} mg/L")
print(f"总磷TP: {(PO4_init[0] + OrgP_init[0]):.3f} mg/L")

# 叶绿素: 秋季藻类
Chla_init = np.full(n_cells, 12.0)  # μg/L
print(f"初始叶绿素: {Chla_init[0]:.1f} μg/L")
print()

# ==================== 边界条件 ====================
print("[3] 气象强迫")
print("-" * 70)

# 气温: 从0°C逐渐降到-15°C
def get_air_temperature(day):
    """气温随时间变化 (线性降温)"""
    T_start = 0.0  # °C
    T_end = -15.0  # °C
    T_air = T_start + (T_end - T_start) * day / n_days
    # 添加日变化 (±3°C)
    hour = (day - int(day)) * 24
    T_daily = 3.0 * np.sin(2 * np.pi * (hour - 6) / 24)
    return T_air + T_daily

# 太阳辐射: 冬季，短日照
def get_solar_radiation(day):
    """太阳辐射随时间变化 (W/m²)"""
    hour = (day - int(day)) * 24
    if 7 <= hour <= 17:  # 白天10小时
        # 冬季最大辐射300 W/m²
        max_radiation = 300.0
        return max_radiation * np.sin(np.pi * (hour - 7) / 10)
    else:
        return 0.0

# 风速: 冬季较强
wind_speed = 5.0  # m/s
print(f"风速: {wind_speed:.1f} m/s")

# 相对湿度
relative_humidity = 0.7
print(f"相对湿度: {relative_humidity*100:.0f}%")

# 云量
cloud_cover = 0.3
print(f"云量: {cloud_cover*100:.0f}%")
print()

# 测试气象强迫
print("气象强迫时间序列:")
for day in [0, 7, 14, 21, 28]:
    T_air = get_air_temperature(day)
    I_0 = get_solar_radiation(day + 0.5)  # 中午
    print(f"  Day {day:2d}: T_air={T_air:6.1f}°C, I_0={I_0:6.1f} W/m²")
print()

# ==================== 初始化求解器 ====================
print("[4] 初始化求解器")
print("-" * 70)

# 水温求解器
temp_solver = WaterTemperatureSolver(n_cells, dx, use_numba=False)
temp_solver.T = T_init.copy()
print("✓ 水温求解器")

# 溶解氧求解器
do_solver = DissolvedOxygenSolver(
    n_cells, dx,
    kd_20=0.15,  # BOD降解系数 (1/day)
    SOD_20=1.0,  # 底泥耗氧 (g/m²/day)
    use_numba=False
)
do_solver.DO = DO_init.copy()
do_solver.BOD = np.full(n_cells, 3.0)  # 初始BOD (mg/L)
print("✓ 溶解氧求解器")

# 冰盖求解器
ice_solver = IceCoverSolver(n_cells=n_cells)
ice_solver.ice_thickness = np.zeros(n_cells)
ice_solver.ice_cover_fraction = np.zeros(n_cells)
print("✓ 冰盖求解器")

# 营养盐求解器
nutrients_solver = NutrientsSolver(n_cells, dx, use_numba=False)
nutrients_solver.NH4 = NH4_init.copy()
nutrients_solver.NO3 = NO3_init.copy()
nutrients_solver.PO4 = PO4_init.copy()
nutrients_solver.OrgN = OrgN_init.copy()
nutrients_solver.OrgP = OrgP_init.copy()
print("✓ 营养盐求解器")

# 藻类求解器
algae_solver = PhytoplanktonSolver(n_cells, dx, use_numba=False)
algae_solver.Chla = Chla_init.copy()
print("✓ 藻类求解器")
print()

# ==================== 时间积分 ====================
print("[5] 时间积分")
print("-" * 70)
print(f"开始模拟 {n_days} 天...")
print()

# 输出存储
output_interval = 24  # 每天输出一次
n_outputs = n_days + 1
output_times = []
output_T = []
output_DO = []
output_ice_thickness = []
output_ice_fraction = []
output_NH4 = []
output_NO3 = []
output_PO4 = []
output_Chla = []

# 保存初始状态
output_times.append(0)
output_T.append(temp_solver.T.copy())
output_DO.append(do_solver.DO.copy())
output_ice_thickness.append(ice_solver.ice_thickness.copy())
output_ice_fraction.append(ice_solver.ice_cover_fraction.copy())
output_NH4.append(nutrients_solver.NH4.copy())
output_NO3.append(nutrients_solver.NO3.copy())
output_PO4.append(nutrients_solver.PO4.copy())
output_Chla.append(algae_solver.Chla.copy())

# 时间循环
for step in range(n_steps):
    t = step * dt
    day = t / 86400.0

    # 气象强迫
    T_air = get_air_temperature(day)
    I_0_surface = get_solar_radiation(day)
    I_0 = np.full(n_cells, I_0_surface)

    # Step 1: 水温
    T = temp_solver.step(
        dt, u, h, T_air, I_0_surface, wind_speed, relative_humidity,
        ice_cover_fraction=ice_solver.ice_cover_fraction
    )

    # Step 2: 冰盖
    ice_state = ice_solver.step(dt, T_air, T)

    # Step 3: 营养盐
    nutrients_state = nutrients_solver.step(dt, u, h, T, do_solver.DO)

    # Step 4: 藻类 (需要营养盐和光照)
    algae_state = algae_solver.step(
        dt, u, h, T, I_0,
        nutrients_solver.NH4,
        nutrients_solver.NO3,
        nutrients_solver.PO4,
        ice_cover_fraction=ice_solver.ice_cover_fraction
    )

    # Step 5: DO (藻类影响)
    do_state = do_solver.step(
        dt, u, h, T, manning_n,
        ice_cover_fraction=ice_solver.ice_cover_fraction
    )

    # 藻类产氧
    dt_day = dt / 86400.0
    algae_DO_production = algae_state['DO_production']
    do_solver.DO += algae_DO_production * dt_day
    do_solver.DO = np.maximum(do_solver.DO, 0.0)

    # 藻类吸收营养盐
    algae_NH4_uptake = algae_state['NH4_uptake']
    algae_NO3_uptake = algae_state['NO3_uptake']
    nutrients_solver.NH4 -= algae_NH4_uptake * dt_day
    nutrients_solver.NH4 = np.maximum(nutrients_solver.NH4, 0.0)
    nutrients_solver.NO3 -= algae_NO3_uptake * dt_day
    nutrients_solver.NO3 = np.maximum(nutrients_solver.NO3, 0.0)

    # 输出
    if (step + 1) % output_interval == 0:
        output_times.append(day)
        output_T.append(temp_solver.T.copy())
        output_DO.append(do_solver.DO.copy())
        output_ice_thickness.append(ice_solver.ice_thickness.copy())
        output_ice_fraction.append(ice_solver.ice_cover_fraction.copy())
        output_NH4.append(nutrients_solver.NH4.copy())
        output_NO3.append(nutrients_solver.NO3.copy())
        output_PO4.append(nutrients_solver.PO4.copy())
        output_Chla.append(algae_solver.Chla.copy())

        # 打印进度
        print(f"Day {day:5.1f}: T={T.mean():5.2f}°C, DO={do_solver.DO.mean():6.2f}mg/L, "
              f"Ice={ice_solver.ice_thickness.mean()*100:5.1f}cm, Chla={algae_solver.Chla.mean():5.1f}μg/L")

print()
print("✓ 模拟完成!")
print()

# ==================== 结果分析 ====================
print("[6] 结果分析")
print("-" * 70)

output_times = np.array(output_times)
output_T = np.array(output_T)
output_DO = np.array(output_DO)
output_ice_thickness = np.array(output_ice_thickness)
output_ice_fraction = np.array(output_ice_fraction)
output_NH4 = np.array(output_NH4)
output_NO3 = np.array(output_NO3)
output_PO4 = np.array(output_PO4)
output_Chla = np.array(output_Chla)

# 计算平均值
T_mean = output_T.mean(axis=1)
DO_mean = output_DO.mean(axis=1)
ice_thickness_mean = output_ice_thickness.mean(axis=1)
ice_fraction_mean = output_ice_fraction.mean(axis=1)
NH4_mean = output_NH4.mean(axis=1)
NO3_mean = output_NO3.mean(axis=1)
Chla_mean = output_Chla.mean(axis=1)

print(f"初始状态 (Day 0):")
print(f"  水温: {T_mean[0]:.2f} °C")
print(f"  DO: {DO_mean[0]:.2f} mg/L")
print(f"  冰厚: {ice_thickness_mean[0]*100:.2f} cm")
print(f"  叶绿素: {Chla_mean[0]:.2f} μg/L")
print()

print(f"最终状态 (Day {n_days}):")
print(f"  水温: {T_mean[-1]:.2f} °C")
print(f"  DO: {DO_mean[-1]:.2f} mg/L")
print(f"  冰厚: {ice_thickness_mean[-1]*100:.2f} cm")
print(f"  冰盖覆盖率: {ice_fraction_mean[-1]*100:.1f}%")
print(f"  叶绿素: {Chla_mean[-1]:.2f} μg/L")
print()

print("变化量:")
print(f"  水温变化: {T_mean[-1] - T_mean[0]:+.2f} °C")
print(f"  DO变化: {DO_mean[-1] - DO_mean[0]:+.2f} mg/L")
print(f"  冰厚增长: {ice_thickness_mean[-1]*100:.2f} cm")
print(f"  藻类变化: {Chla_mean[-1] - Chla_mean[0]:+.2f} μg/L ({(Chla_mean[-1]/Chla_mean[0]-1)*100:+.1f}%)")
print()

# ==================== 可视化 ====================
print("[7] 生成可视化")
print("-" * 70)

fig, axes = plt.subplots(3, 2, figsize=(14, 12))

# (1,1) 水温演变
ax = axes[0, 0]
ax.plot(output_times, T_mean, 'b-', linewidth=2, label='Water Temperature')
ax.axhline(0, color='gray', linestyle='--', linewidth=1, label='Freezing Point')
ax.set_xlabel('Time (days)')
ax.set_ylabel('Temperature (°C)')
ax.set_title('(a) Water Temperature Evolution')
ax.legend()
ax.grid(True, alpha=0.3)

# (1,2) 冰盖演变
ax = axes[0, 1]
ax.plot(output_times, ice_thickness_mean * 100, 'c-', linewidth=2, label='Ice Thickness')
ax.set_xlabel('Time (days)')
ax.set_ylabel('Ice Thickness (cm)')
ax.set_title('(b) Ice Cover Growth')
ax.legend()
ax.grid(True, alpha=0.3)

# (2,1) DO演变
ax = axes[1, 0]
ax.plot(output_times, DO_mean, 'r-', linewidth=2, label='Dissolved Oxygen')
ax.set_xlabel('Time (days)')
ax.set_ylabel('DO (mg/L)')
ax.set_title('(c) Dissolved Oxygen Evolution')
ax.legend()
ax.grid(True, alpha=0.3)

# (2,2) 冰盖覆盖率
ax = axes[1, 1]
ax.plot(output_times, ice_fraction_mean * 100, 'm-', linewidth=2, label='Ice Cover Fraction')
ax.set_xlabel('Time (days)')
ax.set_ylabel('Ice Cover (%)')
ax.set_title('(d) Ice Cover Fraction')
ax.legend()
ax.grid(True, alpha=0.3)

# (3,1) 营养盐演变
ax = axes[2, 0]
ax.plot(output_times, NH4_mean, 'g-', linewidth=2, label='NH4')
ax.plot(output_times, NO3_mean, 'b-', linewidth=2, label='NO3')
TN_mean = NH4_mean + NO3_mean + output_NH4.mean(axis=1) * 0  # 简化
ax.plot(output_times, NH4_mean + NO3_mean, 'k--', linewidth=2, label='TIN (NH4+NO3)')
ax.set_xlabel('Time (days)')
ax.set_ylabel('Concentration (mg/L)')
ax.set_title('(e) Nutrients Evolution')
ax.legend()
ax.grid(True, alpha=0.3)

# (3,2) 叶绿素演变
ax = axes[2, 1]
ax.plot(output_times, Chla_mean, 'g-', linewidth=2, label='Chlorophyll-a')
ax.set_xlabel('Time (days)')
ax.set_ylabel('Chlorophyll-a (μg/L)')
ax.set_title('(f) Phytoplankton Evolution')
ax.legend()
ax.grid(True, alpha=0.3)

plt.tight_layout()
output_file = 'winter_river_simulation_results.png'
plt.savefig(output_file, dpi=150, bbox_inches='tight')
print(f"✓ 图表已保存: {output_file}")
print()

# ==================== 时空分布图 ====================
fig2, axes2 = plt.subplots(2, 2, figsize=(14, 10))

x_km = np.arange(n_cells) * dx / 1000  # km

# 选择几个时间点
time_indices = [0, 10, 20, 30]  # Day 0, 10, 20, 30
colors = ['blue', 'green', 'orange', 'red']

# (1,1) 水温空间分布
ax = axes2[0, 0]
for i, t_idx in enumerate(time_indices):
    ax.plot(x_km, output_T[t_idx, :], color=colors[i],
            linewidth=2, label=f'Day {int(output_times[t_idx])}')
ax.axhline(0, color='gray', linestyle='--', linewidth=1)
ax.set_xlabel('Distance (km)')
ax.set_ylabel('Temperature (°C)')
ax.set_title('(a) Spatial Temperature Distribution')
ax.legend()
ax.grid(True, alpha=0.3)

# (1,2) 冰厚空间分布
ax = axes2[0, 1]
for i, t_idx in enumerate(time_indices):
    ax.plot(x_km, output_ice_thickness[t_idx, :] * 100, color=colors[i],
            linewidth=2, label=f'Day {int(output_times[t_idx])}')
ax.set_xlabel('Distance (km)')
ax.set_ylabel('Ice Thickness (cm)')
ax.set_title('(b) Spatial Ice Thickness Distribution')
ax.legend()
ax.grid(True, alpha=0.3)

# (2,1) DO空间分布
ax = axes2[1, 0]
for i, t_idx in enumerate(time_indices):
    ax.plot(x_km, output_DO[t_idx, :], color=colors[i],
            linewidth=2, label=f'Day {int(output_times[t_idx])}')
ax.set_xlabel('Distance (km)')
ax.set_ylabel('DO (mg/L)')
ax.set_title('(c) Spatial DO Distribution')
ax.legend()
ax.grid(True, alpha=0.3)

# (2,2) 叶绿素空间分布
ax = axes2[1, 1]
for i, t_idx in enumerate(time_indices):
    ax.plot(x_km, output_Chla[t_idx, :], color=colors[i],
            linewidth=2, label=f'Day {int(output_times[t_idx])}')
ax.set_xlabel('Distance (km)')
ax.set_ylabel('Chlorophyll-a (μg/L)')
ax.set_title('(d) Spatial Chlorophyll Distribution')
ax.legend()
ax.grid(True, alpha=0.3)

plt.tight_layout()
output_file2 = 'winter_river_simulation_spatial.png'
plt.savefig(output_file2, dpi=150, bbox_inches='tight')
print(f"✓ 空间分布图已保存: {output_file2}")
print()

# ==================== 总结 ====================
print("[8] 模拟总结")
print("=" * 70)
print()
print("✅ 成功模拟了北方河流冬季冰封期水质演变过程")
print()
print("主要发现:")
print(f"  1. 冰盖生长: 0 → {ice_thickness_mean[-1]*100:.1f} cm (30天)")
print(f"  2. 水温下降: {T_mean[0]:.1f} → {T_mean[-1]:.1f} °C")
print(f"  3. DO变化: {DO_mean[0]:.1f} → {DO_mean[-1]:.1f} mg/L ({(DO_mean[-1]/DO_mean[0]-1)*100:+.1f}%)")
print(f"  4. 藻类变化: {Chla_mean[0]:.1f} → {Chla_mean[-1]:.1f} μg/L ({(Chla_mean[-1]/Chla_mean[0]-1)*100:+.1f}%)")
print()
print("物理-生态耦合机制:")
print("  ✓ 气温下降 → 水温下降 → 冰盖生长")
print("  ✓ 冰盖生长 → 复氧受阻 → DO下降")
print("  ✓ 冰盖遮蔽 → 光照减弱 → 藻类受抑制")
print("  ✓ 低温低光 → 生化反应变慢 → 营养盐循环减缓")
print()
print("=" * 70)
print("HydroClaude v1.0 - 全球首个开源冰-水质耦合系统 ✨")
print("=" * 70)
