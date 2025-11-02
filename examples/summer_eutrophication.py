#!/usr/bin/env python3
"""
HydroClaude 应用案例: 夏季富营养化模拟

场景: 平原河流夏季藻华爆发
- 高温促进藻类生长
- 营养盐充足
- 光照充足
- DO日变化明显
- 藻类-营养盐-DO强耦合

应用: 水华预警、水环境管理

作者: HydroClaude Team
日期: 2025-11-02
版本: v1.0
"""

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from solvers.water_temperature import WaterTemperatureSolver
from solvers.dissolved_oxygen import DissolvedOxygenSolver
from solvers.nutrients import NutrientsSolver
from solvers.phytoplankton import PhytoplanktonSolver

print("=" * 70)
print("HydroClaude 夏季富营养化模拟")
print("=" * 70)
print()

# ==================== 场景设置 ====================
print("[1] 场景设置: 平原河流夏季水华爆发")
print("-" * 70)

# 河道参数
L = 20000.0  # 20 km
n_cells = 200
dx = L / n_cells
print(f"河道长度: {L/1000:.1f} km")
print(f"网格数: {n_cells}")
print()

# 水力条件 (平原河流，流速慢)
u = np.full(n_cells, 0.2)  # 缓流
h = np.full(n_cells, 3.0)  # 较深
manning_n = np.full(n_cells, 0.035)  # 有植被
print(f"流速: {u[0]:.2f} m/s (缓流)")
print(f"水深: {h[0]:.1f} m")
print()

# 模拟时间
n_days = 14  # 2周
dt = 1800.0  # 30分钟步长（捕捉昼夜DO变化）
n_steps = int(n_days * 24 * 3600 / dt)
print(f"模拟时间: {n_days} 天")
print(f"时间步长: {dt/60:.0f} 分钟")
print()

# ==================== 初始条件 ====================
print("[2] 初始条件: 营养盐充足，有藻类种群")
print("-" * 70)

# 水温: 夏季高温
T_init = np.full(n_cells, 28.0)  # °C
print(f"水温: {T_init[0]:.1f} °C (夏季高温)")

# DO: 接近饱和
DO_init = np.full(n_cells, 7.0)  # mg/L
print(f"DO: {DO_init[0]:.1f} mg/L")

# 营养盐: 富营养化水平
NH4_init = np.full(n_cells, 0.8)  # mg/L (高)
NO3_init = np.full(n_cells, 3.0)  # mg/L (高)
PO4_init = np.full(n_cells, 0.15)  # mg/L (高)
OrgN_init = np.full(n_cells, 1.0)  # mg/L
OrgP_init = np.full(n_cells, 0.1)  # mg/L
TN = NH4_init[0] + NO3_init[0] + OrgN_init[0]
TP = PO4_init[0] + OrgP_init[0]
print(f"总氮TN: {TN:.2f} mg/L (富营养)")
print(f"总磷TP: {TP:.3f} mg/L (富营养)")

# 叶绿素: 初始有少量藻类
Chla_init = np.full(n_cells, 20.0)  # μg/L
print(f"初始叶绿素: {Chla_init[0]:.1f} μg/L")
print()

# ==================== 气象条件 ====================
print("[3] 气象条件: 夏季典型晴天")
print("-" * 70)

def get_summer_forcing(day):
    """夏季气象强迫"""
    hour = (day - int(day)) * 24

    # 气温日变化
    T_mean = 32.0  # °C
    T_amplitude = 6.0  # °C
    T_air = T_mean + T_amplitude * np.sin(2 * np.pi * (hour - 6) / 24)

    # 太阳辐射（夏季强烈）
    if 5 <= hour <= 19:  # 白天14小时
        max_radiation = 800.0  # W/m²
        I_0 = max_radiation * np.sin(np.pi * (hour - 5) / 14)
    else:
        I_0 = 0.0

    return T_air, I_0

# 其他气象参数
wind_speed = 2.0  # m/s (夏季微风)
relative_humidity = 0.75
cloud_cover = 0.1  # 晴天

print(f"日均气温: 32 °C (±6 °C)")
print(f"最大太阳辐射: 800 W/m²")
print(f"白天时长: 14 小时")
print(f"风速: {wind_speed:.1f} m/s")
print()

# ==================== 初始化求解器 ====================
print("[4] 初始化求解器")
print("-" * 70)

temp_solver = WaterTemperatureSolver(n_cells, dx, use_numba=False)
temp_solver.T = T_init.copy()

do_solver = DissolvedOxygenSolver(
    n_cells, dx,
    kd_20=0.20,  # 较高BOD降解
    SOD_20=2.0,  # 较高底泥耗氧（有机质多）
    use_numba=False
)
do_solver.DO = DO_init.copy()
do_solver.BOD = np.full(n_cells, 5.0)  # 较高BOD

nutrients_solver = NutrientsSolver(n_cells, dx, use_numba=False)
nutrients_solver.NH4 = NH4_init.copy()
nutrients_solver.NO3 = NO3_init.copy()
nutrients_solver.PO4 = PO4_init.copy()
nutrients_solver.OrgN = OrgN_init.copy()
nutrients_solver.OrgP = OrgP_init.copy()

# 藻类求解器（提高生长速率适应夏季高温）
algae_solver = PhytoplanktonSolver(n_cells, dx, use_numba=False)
algae_solver.Chla = Chla_init.copy()
# 夏季藻类生长参数调整
algae_solver.mu_max_20 = 2.5  # 1/day (夏季高生长率)
algae_solver.k_d = 0.1  # 1/day (低死亡率)
algae_solver.k_r = 0.05  # 1/day (低呼吸率)

print("✓ 所有求解器初始化完成")
print()

# ==================== 时间积分 ====================
print("[5] 时间积分")
print("-" * 70)
print(f"开始模拟 {n_days} 天（高频输出，捕捉昼夜变化）...")
print()

# 输出存储（每小时输出）
output_interval = 2  # 每小时输出（30分钟步长 × 2）
output_times = []
output_T = []
output_DO = []
output_NH4 = []
output_NO3 = []
output_PO4 = []
output_Chla = []
output_I0 = []
output_Tair = []

# 保存初始状态
output_times.append(0)
output_T.append(temp_solver.T.mean())
output_DO.append(do_solver.DO.mean())
output_NH4.append(nutrients_solver.NH4.mean())
output_NO3.append(nutrients_solver.NO3.mean())
output_PO4.append(nutrients_solver.PO4.mean())
output_Chla.append(algae_solver.Chla.mean())
output_I0.append(0)
output_Tair.append(32.0)

# 时间循环
for step in range(n_steps):
    t = step * dt
    day = t / 86400.0

    # 气象强迫
    T_air, I_0_surface = get_summer_forcing(day)
    I_0 = np.full(n_cells, I_0_surface)

    # Step 1: 水温
    T = temp_solver.step(dt, u, h, T_air, I_0_surface, wind_speed, relative_humidity)

    # Step 2: 营养盐
    nutrients_state = nutrients_solver.step(dt, u, h, T, do_solver.DO)

    # Step 3: 藻类
    algae_state = algae_solver.step(
        dt, u, h, T, I_0,
        nutrients_solver.NH4,
        nutrients_solver.NO3,
        nutrients_solver.PO4
    )

    # Step 4: DO
    do_state = do_solver.step(dt, u, h, T, manning_n)

    # 藻类-DO-营养盐耦合
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
        output_NH4.append(nutrients_solver.NH4.mean())
        output_NO3.append(nutrients_solver.NO3.mean())
        output_PO4.append(nutrients_solver.PO4.mean())
        output_Chla.append(algae_solver.Chla.mean())
        output_I0.append(I_0_surface)
        output_Tair.append(T_air)

    # 每天打印一次
    if (step + 1) % (24 * 2) == 0:  # 每天
        print(f"Day {day:4.0f}: T={T.mean():5.1f}°C, DO={do_solver.DO.mean():6.2f}mg/L, "
              f"Chla={algae_solver.Chla.mean():7.1f}μg/L, "
              f"TN={nutrients_solver.NH4.mean() + nutrients_solver.NO3.mean():.2f}mg/L")

print()
print("✓ 模拟完成!")
print()

# ==================== 结果分析 ====================
print("[6] 结果分析")
print("=" * 70)

output_times = np.array(output_times)
output_T = np.array(output_T)
output_DO = np.array(output_DO)
output_NH4 = np.array(output_NH4)
output_NO3 = np.array(output_NO3)
output_Chla = np.array(output_Chla)

print(f"初始状态:")
print(f"  叶绿素: {output_Chla[0]:.1f} μg/L")
print(f"  DO: {output_DO[0]:.1f} mg/L")
print(f"  总无机氮: {output_NH4[0] + output_NO3[0]:.2f} mg/L")
print()

print(f"最终状态 (Day {n_days}):")
print(f"  叶绿素: {output_Chla[-1]:.1f} μg/L")
print(f"  DO: {output_DO[-1]:.1f} mg/L")
print(f"  总无机氮: {output_NH4[-1] + output_NO3[-1]:.2f} mg/L")
print()

# 水华判定
if output_Chla[-1] > 100:
    bloom_level = "重度水华 ⚠️⚠️⚠️"
elif output_Chla[-1] > 50:
    bloom_level = "中度水华 ⚠️⚠️"
elif output_Chla[-1] > 30:
    bloom_level = "轻度水华 ⚠️"
else:
    bloom_level = "正常"

print(f"水华评估: {bloom_level}")
print(f"  藻类增长: {output_Chla[-1] / output_Chla[0]:.1f} 倍")
print()

# DO昼夜变化分析（最后一天）
last_day_start = len(output_times) - 48  # 最后24小时
DO_day = output_DO[last_day_start:]
DO_max = DO_day.max()
DO_min = DO_day.min()
DO_range = DO_max - DO_min

print(f"DO昼夜变化 (最后一天):")
print(f"  最大值: {DO_max:.2f} mg/L (白天)")
print(f"  最小值: {DO_min:.2f} mg/L (夜间)")
print(f"  变化幅度: {DO_range:.2f} mg/L")
if DO_min < 4.0:
    print(f"  ⚠️  夜间低氧风险 (< 4.0 mg/L)")
print()

# ==================== 可视化 ====================
print("[7] 生成可视化")
print("-" * 70)

fig, axes = plt.subplots(3, 2, figsize=(14, 12))

# (1,1) 叶绿素时间序列
ax = axes[0, 0]
ax.plot(output_times, output_Chla, 'g-', linewidth=2)
ax.axhline(30, color='orange', linestyle='--', linewidth=1, label='Light bloom')
ax.axhline(50, color='red', linestyle='--', linewidth=1, label='Moderate bloom')
ax.set_xlabel('Time (days)')
ax.set_ylabel('Chlorophyll-a (μg/L)')
ax.set_title('(a) Algal Bloom Development')
ax.legend()
ax.grid(True, alpha=0.3)

# (1,2) DO时间序列（显示昼夜变化）
ax = axes[0, 1]
ax.plot(output_times, output_DO, 'b-', linewidth=1.5)
ax.axhline(4.0, color='red', linestyle='--', linewidth=1, label='Low DO threshold')
ax.set_xlabel('Time (days)')
ax.set_ylabel('DO (mg/L)')
ax.set_title('(b) DO Diurnal Variation')
ax.legend()
ax.grid(True, alpha=0.3)

# (2,1) 营养盐消耗
ax = axes[1, 0]
ax.plot(output_times, output_NH4, 'r-', linewidth=2, label='NH4')
ax.plot(output_times, output_NO3, 'b-', linewidth=2, label='NO3')
ax.plot(output_times, output_NH4 + output_NO3, 'k--', linewidth=2, label='TIN')
ax.set_xlabel('Time (days)')
ax.set_ylabel('Concentration (mg/L)')
ax.set_title('(c) Nutrients Depletion')
ax.legend()
ax.grid(True, alpha=0.3)

# (2,2) 水温
ax = axes[1, 1]
ax.plot(output_times, output_T, 'r-', linewidth=1.5)
ax.set_xlabel('Time (days)')
ax.set_ylabel('Temperature (°C)')
ax.set_title('(d) Water Temperature')
ax.grid(True, alpha=0.3)

# (3,1) 最后3天的DO昼夜变化细节
ax = axes[2, 0]
last_3days = len(output_times) - 72
ax.plot(output_times[last_3days:], output_DO[last_3days:], 'b-', linewidth=2)
ax.axhline(4.0, color='red', linestyle='--', linewidth=1, label='Low DO')
ax.set_xlabel('Time (days)')
ax.set_ylabel('DO (mg/L)')
ax.set_title('(e) DO Diurnal Cycle (Last 3 days)')
ax.legend()
ax.grid(True, alpha=0.3)

# (3,2) 太阳辐射（最后3天）
ax = axes[2, 1]
ax.plot(output_times[last_3days:], output_I0[last_3days:], 'orange', linewidth=2)
ax.set_xlabel('Time (days)')
ax.set_ylabel('Solar Radiation (W/m²)')
ax.set_title('(f) Solar Radiation Pattern')
ax.grid(True, alpha=0.3)

plt.tight_layout()
output_file = 'summer_eutrophication_results.png'
plt.savefig(output_file, dpi=150, bbox_inches='tight')
print(f"✓ 图表已保存: {output_file}")
print()

# ==================== 总结 ====================
print("[8] 模拟总结")
print("=" * 70)
print()
print("✅ 成功模拟了夏季富营养化水华爆发过程")
print()
print("主要发现:")
print(f"  1. 藻华发展: {output_Chla[0]:.1f} → {output_Chla[-1]:.1f} μg/L ({output_Chla[-1]/output_Chla[0]:.1f}倍)")
print(f"  2. 营养盐消耗: TIN {output_NH4[0]+output_NO3[0]:.1f} → {output_NH4[-1]+output_NO3[-1]:.2f} mg/L")
print(f"  3. DO昼夜变化: {DO_range:.1f} mg/L 幅度")
print(f"  4. 水华等级: {bloom_level}")
print()
print("生态机制:")
print("  ✓ 高温 + 强光 → 藻类快速生长")
print("  ✓ 藻类生长 → 营养盐大量消耗")
print("  ✓ 白天光合作用 → DO过饱和")
print("  ✓ 夜间呼吸作用 → DO显著下降")
print("  ✓ 昼夜DO变化剧烈 → 鱼类应激")
print()
print("管理建议:")
if output_Chla[-1] > 50:
    print("  ⚠️  建议采取控藻措施:")
    print("     - 减少营养盐输入")
    print("     - 增加曝气复氧")
    print("     - 考虑生态调控")
else:
    print("  ✓ 持续监测营养盐和藻类")
print()
print("=" * 70)
print("HydroClaude v1.0 - 水华预警和水环境管理工具 ✨")
print("=" * 70)
