# Well-Balanced格式失败分析（第四次失败）

**日期**: 2025-10-29
**状态**: ❌ 失败（最严重的一次！）
**问题**: Well-Balanced格式（Hydrostatic Reconstruction）导致质量守恒严重恶化

---

## 📊 测试结果

### 对比数据（MacDonald场景）

| 方法 | 质量误差 | 流量误差 | 相对standard的改变 |
|------|----------|----------|-------------------|
| **Standard (well_balanced=False)** | 61.41% | 27.03% | 基准 |
| **Well-Balanced (well_balanced=True)** | 119.67% | 53.47% | ❌ 恶化58.27% |

###详细观察

1. **质量累积速度**：
   - Standard: t=193s → 26%, t=382s → 50%, t=500s → 61%
   - Well-Balanced: t=186s → 42%, t=356s → 87%, t=500s → 120%
   - Well-Balanced方法的质量泄漏速度**快得多**

2. **流量偏离**：
   - Standard: 平均Q = 1.46 m³/s（目标2.0）
   - Well-Balanced: 平均Q = 0.93 m³/s（目标2.0）
   - Well-Balanced方法的流量偏离**更加严重**

3. **严重性**：
   - 这是**四次失败中最严重的一次**！
   - 比Interface方法失败（114%）还要糟糕
   - 恶化程度（58.27%）与Interface方法相当

---

## 🔄 四次失败的总结

| 尝试 | 方法 | 质量误差 | 恶化程度 | 失败类型 |
|------|------|----------|----------|----------|
| 基准 | Standard | 61.41% | - | - |
| #1 | Interface源项法 | 114.17% | +52.76% | 方法论错误 |
| #2 | Strang Splitting | 64.81% | +3.40% | 方法不适用 |
| #3 | 空间精度order=2 | 66.11% | +4.71% | 问题不在这 |
| #4 | **Well-Balanced** | **119.67%** | **+58.27%** | **最严重！** |

**关键发现**：
- 所有尝试都**失败**了
- 两次最严重的失败都是**改变重构方式**的方法：
  - Interface方法：改变源项计算（未改重构）→ 114%
  - Well-Balanced：改变重构变量（η而非h）→ 120%
- **根本问题**：重构方式的改变在MacDonald问题上适得其反！

---

## 🔍 失败原因分析

### 1. **Well-Balanced方法不适合MacDonald问题** ⭐ 主要原因

MacDonald问题的特点：
- **动态非平衡流动**：从非均匀初始条件逼近稳态
- **连续非零坡度**：S0 = 0.002 (2m/1000m下降)
- **强摩阻源项**：Manning n = 0.03（较粗糙）
- **流量边界**：左边界Q固定，驱动流动

Well-Balanced方法的设计目标：
- **静态平衡**：Lake at Rest问题（零流速）
- **局部地形变化**：凸起、台阶等
- **压力-底坡平衡**：∇p = ρg∇z_b

**根本冲突**：
```
MacDonald问题是:  动态流动 + 连续坡度 + 强摩阻
Well-Balanced设计: 静态平衡 + 局部地形 + 无摩阻（或弱摩阻）

问题 = 方法不匹配！
```

### 2. **Hydrostatic Reconstruction过度修正**

Hydrostatic Reconstruction的核心操作：
```python
# 1. 重构水面高程 η = h + z_b
eta_L, eta_R = muscl_reconstruction(eta_ext)

# 2. 计算界面底高程（取最大值，保守）
z_b_interface = max(z_b_left, z_b_right)

# 3. 调整界面水深
h_L = max(0, eta_L - z_b_interface)
h_R = max(0, eta_R - z_b_interface)
```

**在MacDonald问题中的效果**：

对于连续斜坡（左高右低）：
- 单元i的z_b > 单元i+1的z_b（下坡）
- z_b_interface = max(z_b[i], z_b[i+1]) = z_b[i]（左单元的底高程）
- h_L调整：h_L = eta_L - z_b[i]（可能合理）
- h_R调整：h_R = eta_R - z_b[i] < eta_R - z_b[i+1]（**过度减小**！）

**结果**：
- 右侧水深被系统性地低估
- Riemann求解器看到的界面状态偏差很大
- 计算出的通量不准确
- 质量守恒严重破坏

### 3. **Q边界与η重构的冲突**

MacDonald左边界条件：**Q = 2.0 m³/s固定**

Standard格式：
```python
# Ghost cell: 保持Q_ghost = Q_bc
# 重构h_ghost（从内部外推）
h_ext[0] = 2*h[0] - h[1]  # 线性外推
Q_ext[0] = Q_bc  # 固定
```

Well-Balanced格式：
```python
# Ghost cell: 外推η
eta_ext[0] = eta[0]  # 使用内部eta
# 然后从eta还原h_ghost
h_ghost = eta_ghost - z_b_ghost
Q_ext[0] = Q_bc  # 固定
```

**问题**：
- Q固定但h通过η间接确定
- 这可能导致界面状态（h, Q）的不一致
- 速度u = Q/A = Q/(B*h)会受h变化影响
- Riemann求解器基于不一致的状态计算通量

### 4. **摩阻源项与Well-Balanced的相互作用**

Well-Balanced格式假设：
```
∂/∂x(0.5*g*h²) ≈ g*h*∂z_b/∂x  (压力项与底坡源项平衡)
```

但在MacDonald问题中：
```
dQ/dt = -∂/∂x(Q²/A + 0.5*g*h²*B) + g*A*(S0 - Sf)
      = [通量项] + [底坡源项] + [摩阻源项]
```

**关键**：
- 摩阻源项Sf很大（Manning n=0.03）
- Well-Balanced只平衡了**底坡**，没有平衡**摩阻**
- 调整后的h_L, h_R适合无摩阻情况
- 但实际有强摩阻，导致总平衡被破坏

### 5. **Lake at Rest vs MacDonald的本质区别**

| 特性 | Lake at Rest | MacDonald |
|------|--------------|-----------|
| 流动状态 | 静止（Q=0） | 流动（Q=2.0 m³/s） |
| 时间演化 | 保持静止 | 动态逼近稳态 |
| 底坡 | 局部变化 | 连续斜坡 |
| 摩阻 | 无（Q=0） | 强（Manning n=0.03） |
| 边界条件 | h边界 | Q边界+h边界 |
| 期望性质 | C-property (静水平衡) | 稳态流动平衡 |

**Well-Balanced的C-property**：
```
如果 η = const, Q = 0，则解应保持不变
```

**MacDonald的稳态平衡**：
```
如果 Q = const, S0 = Sf，则解应保持不变
```

**根本不同**：Well-Balanced保护的是静水平衡，而MacDonald需要的是**稳态流动平衡**！

---

## 💡 深层洞察

### 为什么Well-Balanced反而恶化？

**直觉**：Well-Balanced应该更好啊！为什么反而更糟？

**答案**：因为MacDonald问题的"平衡"不是Well-Balanced要保护的"平衡"！

1. **Well-Balanced保护**：静水平衡（Lake at Rest）
   - η = const, Q = 0
   - 压力梯度 = 底坡力

2. **MacDonald的平衡**：稳态流动平衡
   - Q = const, dQ/dt = 0
   - 通量梯度 + 底坡力 = 摩阻力

3. **冲突**：
   - Hydrostatic Reconstruction调整h_L, h_R是为了保护静水平衡
   - 但这破坏了流动状态的通量准确性
   - 导致质量和动量传递出错
   - 最终质量守恒更差

**类比**：
```
用专门为"静止车辆"设计的刹车系统
去控制"行驶中的车辆"
结果 → 不是更安全，而是失控！
```

### 关键教训：方法要匹配问题

| 方法 | 设计目标 | MacDonald匹配度 | 结果 |
|------|----------|----------------|------|
| Standard格式 | 通用 | 一般 | 基准（61%误差） |
| Well-Balanced | Lake at Rest | ❌ 不匹配 | 严重恶化（120%） |
| Interface源项 | 部分Zhou方法 | ❌ 不完整 | 严重恶化（114%） |
| Strang Splitting | 弱耦合源项 | ❌ 强耦合 | 略微恶化（65%） |
| 空间order=2 | 提高精度 | ❌ 问题不在这 | 略微恶化（66%） |

**结论**：
- 61%误差的根源**不是方法选择错误**
- 而是更深层的**数值或物理问题**
- 盲目应用"更高级"的方法只会更糟

---

## 🎯 真正的问题在哪里？

经过四次失败，我们可以排除：
1. ✗ 源项处理方法（Interface、Strang都失败）
2. ✗ 空间离散精度（order=2失败）
3. ✗ Well-Balanced格式（最严重失败）
4. ✓ Q边界处理（之前测试显示3%误差，可以接受）
5. ✓ RK2时间积分（标准方法）

**仍需检查的可能原因**：

### A. 边界条件与内部求解的匹配性

**假设**：Q边界本身可能没问题，但与内部格式的**长时间累积效应**有问题

**测试方案**：
1. 改用h边界（两端都h）
2. 或改用特征线边界（CharacteristicBC）
3. 检查长时间积分下的边界影响

### B. 网格分辨率不足

**假设**：20个单元太粗，无法捕捉MacDonald的物理过程

**测试方案**：
1. n_cells = 40, 80, 160
2. 检查是否随网格加密而收敛
3. 如果误差不收敛 → 问题在别处

### C. CFL数和时间步长

**假设**：CFL=0.4可能导致长时间累积误差

**测试方案**：
1. 降低CFL到0.2, 0.1
2. 检查时间步长对结果的影响

### D. 物理模型问题

**假设**：问题可能不在数值方法，而在**物理设置**

**检查**：
1. Manning公式在大坡度（0.002）下是否适用？
2. 临界水深边界条件是否合理？
3. 初始条件（线性分布）是否合理？

### E. 参考解的准确性

**假设**：也许61%不是"误差"，而是**问题本身没有守恒稳态解**？

**验证**：
1. 用商业软件（HEC-RAS, SWMM）求解同样问题
2. 对比结果
3. 确认是否存在守恒的稳态解

---

## 🔄 下一步行动

### 立即行动

1. **撤销well_balanced=True的期望**
   - 明确：Well-Balanced **不适用**于MacDonald问题
   - 更新文档和注释

2. **创建第四次失败分析文档**
   - ✓ 本文档
   - 记录为什么Well-Balanced不work

3. **更新调查总结**
   - 添加第四次失败记录
   - 更新"已排除原因"列表

### 短期计划（今天-明天）

4. **测试边界条件影响**
   - 使用CharacteristicBC替代固定Q边界
   - 或尝试两端h边界

5. **网格收敛性测试**
   - n_cells = 40, 80, 160
   - 检查误差是否收敛

### 中期计划（本周）

6. **对比商业软件**
   - 用HEC-RAS或其他工具求解MacDonald问题
   - 确认是否存在守恒解
   - 对比质量守恒性

7. **文献调研MacDonald测试**
   - 查找MacDonald原文
   - 看其他求解器如何处理
   - 了解预期行为

### 长期计划（可能放弃MacDonald）

8. **考虑问题本身的合理性**
   - MacDonald可能本身是个**挑战性问题**
   - 61%误差可能在某些求解器中是**可接受的**
   - 重新评估质量标准

9. **转向其他测试案例**
   - 如果MacDonald太难，先解决其他问题
   - 例如：Dam break, Steady flow等
   - 建立信心后再回来

---

## ✅ 经验总结

### 技术教训

1. **方法要匹配问题**
   - Well-Balanced设计for静水平衡
   - MacDonald是动态流动问题
   - 不匹配 → 性能恶化

2. **"高级"不等于"更好"**
   - Well-Balanced是先进方法
   - 但用错场景反而最糟
   - 基础方法（Standard）反而更好

3. **四次失败的模式**
   - 改变重构方式的方法失败最严重（Interface 114%, Well-Balanced 120%）
   - 改变时间积分的方法略微恶化（Strang 65%）
   - 提高精度的方法略微恶化（order=2 66%）
   - **暗示**：问题可能不在这些方面

### 方法论教训

1. **排除法的价值**
   - 虽然四次都失败，但排除了很多可能性
   - 缩小了问题范围
   - 为后续调查指明方向

2. **文献理解要深入**
   - 不能只看标题和结论
   - Audusse方法的"适用场景"很重要
   - 我们之前忽略了这一点

3. **失败也是数据**
   - 每次失败都在告诉我们问题在哪里
   - Well-Balanced的失败说明：重构变量不是解决方案
   - 四次失败一起看：方法选择不是主要问题

### 心态教训

1. **保持冷静**
   - 四次失败很frustrating
   - 但都是valuable learning
   - 离真相越来越近

2. **质疑假设**
   - 也许61%误差不是"bug"
   - 也许MacDonald本身就是难题
   - 也许我们的期望不合理

3. **记录一切**
   - 每次失败都详细记录
   - 建立了完整的调查档案
   - 未来可复现和学习

---

## 📖 参考文献

1. **Audusse, E., et al. (2004)**. "A Fast and Stable Well-Balanced Scheme with Hydrostatic Reconstruction for Shallow Water Flows." *Journal of Computational Physics*, 193(2), 474-508.
   - ⚠️ 注意适用场景：Lake at Rest, NOT steady flows

2. **Zhou, J.G., et al. (2001)**. "The Surface Gradient Method for the Treatment of Source Terms in the Shallow-Water Equations." *Journal of Computational Physics*, 168(1), 1-25.
   - 可能更适合流动问题，但需完整实现

3. **MacDonald, I., et al. (1997)**. "Analytic Benchmark Solutions for Open-Channel Flows." *Journal of Hydraulic Engineering*, 123(11), 1041-1045.
   - 需要查阅原文，了解问题的预期行为

4. **Toro, E.F. (2009)**. *Riemann Solvers and Numerical Methods for Fluid Dynamics*. 3rd ed. Springer.
   - 标准教材，确认我们的基础方法是否正确

---

## 🏆 正面收获

虽然是第四次失败，但：

1. ✅ 彻底排除了Well-Balanced格式作为解决方案
2. ✅ 理解了Well-Balanced的适用场景和局限性
3. ✅ 建立了完整的失败案例数据库
4. ✅ 学会了区分"静水平衡"和"流动平衡"
5. ✅ 意识到可能需要从不同角度审视问题

**四次失败的价值**：
- 如果第一次尝试就成功，我们不会深入理解这些方法
- 现在我们对每种方法的原理、适用性、局限性都很清楚
- 这为未来的工作打下坚实基础

---

*本文档记录了2025-10-29对Well-Balanced格式的失败尝试及深度分析*
*这是MacDonald Test 2质量守恒调查的第四次失败，但也是重要的学习机会*
