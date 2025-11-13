"""
验证有限体积法的符号约定

Saint-Venant方程：
∂U/∂t + ∂F/∂x = S

其中：
U = [h, hu]
F = [hu, hu²/h + gh²/2]
S = [0, -gh∂z/∂x - friction]

有限体积法离散化：
dU_i/dt = -(F_{i+1/2} - F_{i-1/2})/dx + S_i

还是：
dU_i/dt = (F_{i-1/2} - F_{i+1/2})/dx + S_i

让我查看标准教材...
"""

import numpy as np

print("="*70)
print("有限体积法符号约定验证")
print("="*70)

print("\n标准形式（守恒律）:")
print("  ∂U/∂t + ∂F/∂x = S")

print("\n有限体积法离散化（守恒形式）:")
print("  对单元i积分：")
print("  ∫_{x_{i-1/2}}^{x_{i+1/2}} [∂U/∂t + ∂F/∂x] dx = ∫_{x_{i-1/2}}^{x_{i+1/2}} S dx")
print()
print("  得到：")
print("  d/dt ∫ U dx + [F_{i+1/2} - F_{i-1/2}] = ∫ S dx")
print()
print("  即：")
print("  dU_i/dt = -(F_{i+1/2} - F_{i-1/2})/Δx + S_i")
print()
print("  其中负号来自于通量的散度形式")

print("\n良平衡条件（稳态）:")
print("  dU_i/dt = 0")
print("  所以：-(F_{i+1/2} - F_{i-1/2})/Δx + S_i = 0")
print("  即：S_i = (F_{i+1/2} - F_{i-1/2})/Δx")

print("\n" + "="*70)
print("结论：标准有限体积法中通量梯度确实有负号")
print("="*70)

# 测试：简单算例
print("\n【测试算例】")
print("平坦底床，湖面静止：h=10m everywhere, u=0, z=0")

g = 9.81
h = 10.0
F = 0.5 * g * h**2  # 压力通量

print(f"\n通量：F = gh²/2 = {F:.3f} m³/s²（所有界面相同）")
print("通量梯度：∂F/∂x = (F[i+1/2] - F[i-1/2])/dx = 0")
print("源项：S = -gh∂z/∂x = 0（平坦底床）")
print("残差：R = -∂F/∂x + S = 0 ")

print("\n【测试算例2】")
print("台阶地形，湖面静止：η=10m everywhere, u=0")
print("单元1: z=0, h=10")
print("单元2: z=1.5, h=8.5")

z1 = 0.0
h1 = 10.0
z2 = 1.5
h2 = 8.5
dx = 1.0

# 界面1（左侧）：假设也是h=10
F1 = 0.5 * g * 10.0**2
# 界面2（右侧）：重构后h*=8.5
F2 = 0.5 * g * 8.5**2

dF_dx = (F2 - F1) / dx

print(f"\n界面1通量：F_1 = {F1:.3f} m³/s²（h*=10）")
print(f"界面2通量：F_2 = {F2:.3f} m³/s²（h*=8.5）")
print(f"通量梯度：∂F/∂x = (F_2 - F_1)/dx = {dF_dx:.3f} m²/s²")

# 源项（Audusse公式，使用重构水深）
h_star_L = 10.0  # 左界面从右侧看
h_star_R = 8.5   # 右界面从左侧看

S = 0.5 * g * (h_star_L**2 - h_star_R**2) / dx

print(f"\n源项（Audusse）：S = g/2*(h*_L² - h*_R²)/dx")
print(f"                = {g}/2*({h_star_L}² - {h_star_R}²)/{dx}")
print(f"                = {S:.3f} m²/s²")

R = -dF_dx + S

print(f"\n良平衡条件验证：")
print(f"  R = -∂F/∂x + S")
print(f"    = -{dF_dx:.3f} + {S:.3f}")
print(f"    = {R:.3e}")
print(f"  结果：{' 平衡' if abs(R) < 1e-10 else ' 不平衡'}")

print("\n" + "="*70)
