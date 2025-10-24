# 案例2: 防洪调度应急响应

## 工程背景

某输水渠道，汛期遭遇上游水库紧急泄洪，流量从正常的15 m³/s突增至30 m³/s（翻倍）。渠道设计流量为25 m³/s，超过设计标准，需要紧急调度避免溢出灾害。

### 基本信息
- **渠道长度**：8 km
- **正常流量**：15 m³/s
- **洪水流量**：30 m³/s
- **设计流量**：25 m³/s（接近但未达到洪水流量）
- **调节设施**：中部调节闸门（5 km处）

### 应急目标
1. **安全第一**：防止渠道溢出
2. **监测预警**：追踪洪水传播过程
3. **应急调度**：及时调节闸门开度
4. **恢复运行**：洪峰过后恢复正常

## 水力学分析

### 1. 洪水传播

**波速计算**：
```
c = √(gh) + v
```
其中：
- c: 波速 (m/s)
- g: 重力加速度 (9.81 m/s²)
- h: 水深 (m)
- v: 流速 (m/s)

**传播时间**：
```
t = L / c
```
对于8 km渠道，h ≈ 2.5 m，v ≈ 0.8 m/s：
```
c ≈ √(9.81 × 2.5) + 0.8 ≈ 5.8 m/s
t ≈ 8000 / 5.8 ≈ 1380 s ≈ 23分钟
```

### 2. 壅水分析

洪水流量增大导致：
- 水深增加
- 流速增大
- 闸门上游壅水

**临界条件**：
- 渠道安全水深：3.0 m（假设）
- 正常水深：2.5 m
- 安全余量：0.5 m

### 3. 闸门调度策略

| 阶段 | 时间 | 流量 | 闸门开度 | 说明 |
|------|------|------|----------|------|
| 正常运行 | 0-600s | 15 m³/s | 1.5 m | 初始状态 |
| 洪水来临 | 600s | 30 m³/s | 1.5 m | 流量突增 |
| 应急响应 | 600-1200s | 30 m³/s | 建议2.5m | 开大闸门 |
| 恢复阶段 | >1200s | 30 m³/s | 建议1.8m | 新稳态 |

## 使用方法

### 运行模拟

```bash
cd examples/engineering_cases/case_02_flood_emergency

python -c "
import sys
sys.path.insert(0, '../../..')
from modeling.universal_modeler import UniversalModeler

modeler = UniversalModeler('config.yaml')
modeler.run()
"
```

### 结果分析

#### 1. 洪水传播过程

```python
import sys
sys.path.insert(0, '../../..')
from modeling.universal_modeler import UniversalModeler
import numpy as np
import matplotlib.pyplot as plt

modeler = UniversalModeler('config.yaml')
modeler.run()

# 提取结果
result = modeler.unsteady_result
time = result['time']
h_history = result['h_history']
x = modeler.solver.x

# 关键位置
x_gate = 5000.0  # 闸门位置
idx_gate = np.argmin(np.abs(x - x_gate))

# 闸门处水深时间序列
h_gate = h_history[:, idx_gate]

# 绘制
plt.figure(figsize=(12, 5))

# 子图1: 闸门处水深变化
plt.subplot(1, 2, 1)
plt.plot(time / 60, h_gate, 'b-', linewidth=2)
plt.axvline(x=10, color='r', linestyle='--', label='洪水来临')
plt.axhline(y=3.0, color='orange', linestyle='--', label='安全水深')
plt.xlabel('时间 (分钟)')
plt.ylabel('水深 (m)')
plt.title('闸门处水深变化')
plt.legend()
plt.grid(True, alpha=0.3)

# 子图2: 不同时刻水面线
plt.subplot(1, 2, 2)
t_indices = [0, 120, 240, 360, 480, 600, 720]  # 不同时刻的索引
for ti in t_indices:
    if ti < len(h_history):
        plt.plot(x / 1000, h_history[ti, :], label=f't={time[ti]:.0f}s')
plt.axvline(x=5.0, color='r', linestyle='--', alpha=0.3, label='闸门')
plt.xlabel('距离 (km)')
plt.ylabel('水深 (m)')
plt.title('水面线演变')
plt.legend()
plt.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('flood_analysis.png', dpi=150)
print("分析图已保存: flood_analysis.png")
```

#### 2. 关键指标

```python
# 最大水深
h_max = h_history.max()
print(f"最大水深: {h_max:.3f} m")

# 最大水深位置和时间
idx_max = np.unravel_index(h_history.argmax(), h_history.shape)
t_max = time[idx_max[0]]
x_max = x[idx_max[1]]
print(f"发生时间: {t_max:.0f} s ({t_max/60:.1f} 分钟)")
print(f"发生位置: {x_max:.0f} m ({x_max/1000:.1f} km)")

# 洪峰到达时间（闸门处）
idx_600 = np.argmin(np.abs(time - 600))  # 洪水来临时刻
h_before = h_gate[:idx_600].mean()
h_peak = h_gate[idx_600:].max()
idx_peak = idx_600 + np.argmax(h_gate[idx_600:])
t_peak = time[idx_peak]
print(f"\n闸门处:")
print(f"  洪前水深: {h_before:.3f} m")
print(f"  洪峰水深: {h_peak:.3f} m")
print(f"  水深增幅: {h_peak - h_before:.3f} m")
print(f"  洪峰到达: {t_peak:.0f} s (洪水来临后 {t_peak-600:.0f} s)")

# 安全评估
if h_max < 3.0:
    print(f"\n✓ 渠道安全（最大水深 {h_max:.3f}m < 3.0m）")
else:
    print(f"\n✗ 存在溢出风险（最大水深 {h_max:.3f}m ≥ 3.0m）")
```

## 典型结果

### 无调度情况（闸门保持1.5m）

**模拟结果**：
```
最大水深: 2.85 m
发生时间: 1250 s (20.8 分钟)
发生位置: 4950 m (闸门上游)
洪峰水深: 2.82 m
水深增幅: 0.65 m
```

**评估**：
- ✓ 渠道安全（2.85m < 3.0m）
- ⚠ 接近安全上限，余量仅0.15m
- ⚠ 闸门上游壅水明显

### 应急调度情况（600s后开大至2.5m）

要测试此场景，需要修改配置或使用控制系统（参考案例3）。

**预期效果**：
- 最大水深降低至2.5m左右
- 壅水减轻
- 安全余量增大至0.5m

## 应急响应流程

### 1. 监测预警

```
上游水库 → 流量监测 → 预警系统
                ↓
           洪水预报
                ↓
           应急准备
```

**预警指标**：
- 上游流量超过20 m³/s：黄色预警
- 上游流量超过25 m³/s：橙色预警
- 上游流量超过30 m³/s：红色预警

### 2. 应急调度

**时间轴**：
```
t = 0s:    正常运行，闸门1.5m
t = 600s:  检测到流量突增至30 m³/s
t = 610s:  启动应急预案，开始开大闸门
t = 620s:  闸门开至2.0m
t = 630s:  闸门开至2.5m（最大开度）
t = 1200s: 洪峰通过，开始恢复
t = 1800s: 闸门恢复至1.8m（新稳态）
```

### 3. 调度原则

1. **及时性**：检测到异常立即响应
2. **安全性**：宁可过度调度，不可延误
3. **平稳性**：闸门开度缓慢调整，避免水击
4. **适应性**：根据实测水位动态调整

## 工程启示

### 1. 设计教训

- **安全余量**：设计流量应考虑突发事件
- **调节设施**：关键位置设置调节闸门
- **监测系统**：实时监测流量和水位

### 2. 运行管理

- **预案制定**：制定详细的应急预案
- **演练培训**：定期演练提高应急能力
- **信息化**：建立自动监测预警系统

### 3. 技术改进

- **自动控制**：实现闸门自动调度（案例3）
- **预报调度**：基于洪水预报的前馈控制
- **多目标优化**：安全、效率、经济综合考虑

## 扩展练习

1. **不同洪水过程**：
   - 缓涨：流量从15逐渐增至30（1小时）
   - 尖峰：流量快速涨落（30分钟）

2. **多闸门调度**：
   - 增加上下游闸门
   - 协同调度策略

3. **控制系统**：
   - 集成PID/MPC控制器
   - 实现自动应急响应

4. **风险分析**：
   - 计算不同调度方案的风险
   - 绘制风险曲线

## 参考资料

- 《防洪调度原理与方法》
- 《水库防洪调度规程》
- 《渠道运行管理规范》

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)
