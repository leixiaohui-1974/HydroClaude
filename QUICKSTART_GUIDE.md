# HydroClaude 快速入门指南

**版本**: 1.0
**预计完成时间**: 30分钟
**更新日期**: 2025-10-24

---

## 📋 目录

1. [环境准备](#环境准备)
2. [第一个示例（5分钟）](#第一个示例5分钟)
3. [结构物示例（10分钟）](#结构物示例10分钟)
4. [控制系统示例（15分钟）](#控制系统示例15分钟)
5. [自定义配置](#自定义配置)
6. [下一步学习](#下一步学习)

---

## 环境准备

### 1. 安装依赖

```bash
# 克隆项目
git clone <repository_url>
cd HydroClaude

# 安装依赖
pip install -r requirements.txt
```

### 2. 验证安装

```bash
# 运行快速测试
python -c "import numpy as np; import matplotlib.pyplot as plt; print('✓ 安装成功!')"
```

---

## 第一个示例（5分钟）

### 运行最简单的案例

```bash
# 进入简单渠道示例
cd examples/example_simple_canal

# 运行示例
python run.py
```

**预期输出**：
```
==========================================================================================
HydroClaude 通用建模系统 v1.0
==========================================================================================

[1/7] 加载配置文件...
      ✓ 配置已加载

[2/7] 生成网格...
      ✓ 网格生成完成

...

✓ 建模完成！
```

**生成文件**：
```
results/
├── data.npz              # 数值数据
└── profile.png           # 纵剖面图
```

### 查看结果

打开 `results/profile.png` 查看水面线剖面图。

<details>
<summary>📝 这个示例做了什么？</summary>

- 模拟一条10km的简单渠道
- 计算稳态流动
- 生成水深、流速分布
- 验证流量守恒

**核心方程**: 圣维南方程（Saint-Venant equations）

</details>

---

## 结构物示例（10分钟）

### 了解所有支持的结构类型

```bash
# 结构类型展示案例
cd examples/example_structure_showcase
python run.py
```

**支持的结构**：
1. ✅ SluiceGate（闸门）
2. ✅ Transition（过渡段）
3. ✅ BroadCrestedWeir（宽顶堰）
4. ✅ Drop（跌水）
5. ✅ Spillway（溢洪道）
6. ✅ Orifice（孔口）
7. ✅ PumpStation（泵站）

**预期输出**：
```
结构物详细信息
================================================================================

1. SluiceGate @ 2.0 km
   - 开度: 2.0 m
   - 流量系数: 0.6

2. Transition @ 4.0 km
   - 上游宽度: 20.0 m
   - 下游宽度: 15.0 m

... (共7个结构物)
```

### 尝试修改配置

编辑 `config.yaml`，例如修改闸门开度：

```yaml
structures:
  - type: sluice_gate
    position: 2000.0
    initial_opening: 3.0    # 改为3.0m（原来是2.0m）
```

重新运行，观察结果变化。

---

## 控制系统示例（15分钟）

### PID控制器

```bash
# 运行PID水位控制示例
python -m modeling.universal_modeler \
    examples/example_control/config_pid_water_level.yaml
```

**配置说明**：
```yaml
control:
  type: pid              # 控制器类型
  setpoint: 2.5          # 目标水位 (m)
  control_interval: 5    # 控制周期 (步)

  controller:
    kp: 0.5              # 比例增益
    ki: 0.05             # 积分增益
    kd: 0.1              # 微分增益
```

**性能指标**：
```
MAE (平均绝对误差): 0.79 m
控制范围: 0.2 - 0.994 m
```

### MPC控制器

```bash
# 运行MPC水位控制示例（调优版）
python -m modeling.universal_modeler \
    examples/example_control/config_mpc_tuned.yaml
```

**MPC特点**：
- ✨ 预测未来状态
- ✨ 优化控制序列
- ✨ 约束处理
- ✨ 在线辨识

**性能对比**：
| 控制器 | MAE | 控制平滑度 | 优势 |
|--------|-----|-----------|------|
| PID | 0.79m | 中等 | 简单、快速 |
| MPC | 0.95m | 高 | 预测、优化 |

### 查看控制效果

生成的文件：
```
results_*/
├── *_data.npz                    # 数值数据
├── *_control_performance.png     # 控制性能图
└── *_final_profile.png           # 最终剖面图
```

打开 `*_control_performance.png` 查看：
- 子图1: 跟踪误差
- 子图2: 测量值 vs 设定值
- 子图3: 控制量变化

---

## 自定义配置

### 创建您的第一个配置文件

```yaml
# my_first_config.yaml

# 1. 渠道参数
canal:
  length: 5000.0         # 5km渠道
  width: 10.0            # 10m宽
  slope: 0.001           # 坡度
  manning_n: 0.025       # 糙率

# 2. 网格
grid:
  nx: 101                # 网格点数

# 3. 结构物（可选）
structures:
  - type: sluice_gate
    position: 2500.0     # 中点
    width: 10.0
    initial_opening: 1.5
    Cd: 0.6

# 4. 边界条件
boundary_conditions:
  upstream:
    type: flow
    value: 10.0          # 上游流量 (m³/s)

  downstream:
    type: depth
    value: 2.0           # 下游水深 (m)

# 5. 模拟类型
simulation:
  type: steady           # 稳态模拟

# 6. 输出
output:
  directory: my_results
  prefix: my_simulation
  formats:
    - npz
    - png
```

### 运行自定义配置

```bash
python -m modeling.universal_modeler my_first_config.yaml
```

### 参数调整指南

**流量和水深**：
- 小流量：< 5 m³/s
- 中流量：5-20 m³/s
- 大流量：> 20 m³/s

**网格密度**：
- 粗网格：nx ~ 50-100（快速）
- 中网格：nx ~ 100-200（平衡）
- 细网格：nx > 200（精确）

**Manning糙率**：
- 混凝土：0.012-0.018
- 土渠：0.020-0.030
- 草地：0.030-0.050

---

## 下一步学习

### 推荐学习路径

```
✓ 完成快速入门
   ↓
→ 浏览 examples/EXAMPLES_CATALOG.md    ← 所有案例目录
   ↓
→ 学习 LIBRARY_REFERENCE.md           ← 基础类库
   ↓
→ 深入 engineering_cases/              ← 工程实践
   ↓
→ 研究 example_control/                ← 控制系统
   ↓
→ 自定义开发                            ← 创新应用
```

### 推荐案例顺序

**初学者（第1-3天）**：
1. `example_simple_canal` ✓
2. `example_universal_modeling`
3. `example_structure_showcase` ✓

**进阶（第4-7天）**：
4. `engineering_cases/case_01`
5. `engineering_cases/case_02`
6. `example_control` ✓
7. `engineering_cases/case_03`

**高级（第8-14天）**：
8. `example_gate_pump_cascade`
9. `example_time_varying_bc`
10. 自选感兴趣的传统示例

### 重要文档

| 文档 | 用途 | 优先级 |
|------|------|--------|
| `EXAMPLES_CATALOG.md` | 案例目录 | ⭐⭐⭐ |
| `LIBRARY_REFERENCE.md` | API参考 | ⭐⭐⭐ |
| `DEVELOPMENT_GUIDE.md` | 开发规范 | ⭐⭐ |
| `USAGE_GUIDE.md` | 使用指南 | ⭐⭐ |

### 获取帮助

**文档资源**：
- 📖 每个示例都有独立的README
- 📖 主要文档在项目根目录

**常见问题**：
- 查看各示例的README中的"常见问题"部分
- 检查 `DEVELOPMENT_TASKS.md` 中的故障排查

**社区支持**：
- GitHub Issues: 报告问题
- 文档PR: 改进文档

---

## 🎓 学习检查清单

完成以下检查点，确保您已掌握基础：

### 基础操作 ✓
- [ ] 成功运行 `example_simple_canal`
- [ ] 查看并理解输出图表
- [ ] 修改配置文件参数
- [ ] 观察参数变化的影响

### 结构物 ✓
- [ ] 运行 `example_structure_showcase`
- [ ] 识别7种结构类型
- [ ] 修改结构物参数
- [ ] 理解不同结构的作用

### 控制系统 ✓
- [ ] 运行PID控制示例
- [ ] 运行MPC控制示例
- [ ] 理解控制性能指标
- [ ] 对比PID和MPC

### 自定义开发
- [ ] 创建自己的配置文件
- [ ] 成功运行自定义配置
- [ ] 调整参数达到预期效果
- [ ] 理解结果物理意义

---

## 💡 快速提示

### Tip 1: 使用命令行接口

```bash
# 方便的命令行运行方式
python -m modeling.universal_modeler <config.yaml>

# 而不是
cd examples/some_example && python run.py
```

### Tip 2: 快速参数扫描

创建多个配置文件，批量运行：

```bash
for config in config_*.yaml; do
    python -m modeling.universal_modeler $config
done
```

### Tip 3: 结果对比

使用Python脚本加载多个结果：

```python
import numpy as np

# 加载结果
data1 = np.load('results_1/data.npz')
data2 = np.load('results_2/data.npz')

# 对比
print("Case 1 MAE:", data1['mae'])
print("Case 2 MAE:", data2['mae'])
```

### Tip 4: 可视化增强

所有结果都包含 `.npz` 数据文件，可以用自己的脚本绘制：

```python
import numpy as np
import matplotlib.pyplot as plt

data = np.load('results/data.npz')
h = data['h']  # 水深
x = data['x']  # 位置

plt.plot(x/1000, h)  # km为单位
plt.xlabel('Distance (km)')
plt.ylabel('Water Depth (m)')
plt.show()
```

---

## 🚀 开始您的旅程！

恭喜您完成快速入门！现在您已经：

- ✅ 运行了第一个示例
- ✅ 了解了所有结构类型
- ✅ 体验了控制系统
- ✅ 知道如何自定义配置

**下一步**：
1. 浏览 `examples/EXAMPLES_CATALOG.md` 找到感兴趣的案例
2. 阅读 `LIBRARY_REFERENCE.md` 深入了解API
3. 尝试工程案例 `engineering_cases/`
4. 开始您自己的水力学项目！

---

## 📞 需要帮助？

- 📚 查看文档：所有示例都有详细README
- 🐛 报告问题：GitHub Issues
- 💬 讨论交流：GitHub Discussions

---

**祝您学习愉快！** 🎉

---

Generated with [Claude Code](https://claude.com/claude-code)

*快速入门指南 v1.0 - 2025-10-24*
