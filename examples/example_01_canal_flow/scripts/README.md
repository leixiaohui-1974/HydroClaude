# Scripts Directory - 脚本目录说明

所有示例脚本已整合到统一的 `scripts/` 目录，每个脚本独立完整，平等对待。

## 脚本列表 (14个)

### 基础示例 (01-06)

| 编号 | 脚本名称 | 功能说明 |
|------|---------|---------|
| 01 | `01_basic.py` | 基础明渠流动仿真 - 三种数值方法对比 |
| 01a | `01_basic_with_animation.py` | 基础示例 + 动画演示 |
| 02 | `02_methods_comparison.py` | 数值方法深度对比分析 |
| 03 | `03_idz_identification.py` | IDZ降阶模型参数辨识 |
| 04 | `04_boundary_conditions.py` | 边界条件影响分析 |
| 05 | `05_step_response.py` | 阶跃响应分析 |
| 06 | `06_animation.py` | 完整动画演示 |

### 高级示例 (07-12)

| 编号 | 脚本名称 | 功能说明 |
|------|---------|---------|
| 07 | `07_sluice_gate_flow.py` | 闸门流动动力学分析 - 单求解器版本 |
| 08 | `08_optimized_steady_solving.py` | 稳态求解优化方法对比 |
| 09 | `09_simple_canal_enhanced.py` | 简单明渠仿真 - 增强可视化版本 |
| 10 | `10_canal_deep_analysis.py` | 深度分析 - 边界条件+IDZ辨识 |
| 11 | `11_advanced_structures.py` | 多水工建筑物组合 |
| 12 | `12_advanced_optimized.py` | 高级结构优化 |

### 工具模块

| 文件名 | 功能说明 |
|--------|---------|
| `output_helper.py` | 统一输出管理模块 - 处理所有图表、表格、动画输出 |

## 输出结构

所有脚本输出统一保存到 `../results/` 目录：

```
results/
├── figures/       # PNG图表
├── animations/    # GIF动画
├── tables/        # CSV数据表
└── reports/       # Markdown报告
```

## 运行方式

### 单独运行脚本

```bash
# 设置PYTHONPATH
export PYTHONPATH=/path/to/HydroClaude

# 运行任意脚本
python scripts/01_basic.py
python scripts/07_sluice_gate_flow.py
python scripts/10_canal_deep_analysis.py
```

### 批量运行

```bash
# 运行所有基础示例 (01-06)
for i in {01..06}; do
    python scripts/${i}_*.py
done

# 运行所有高级示例 (07-12)
for i in {07..12}; do
    python scripts/${i}_*.py
done
```

## 脚本分类

### 按功能分类：

**数值方法类：**
- 01_basic.py - 基础对比
- 02_methods_comparison.py - 深度对比
- 08_optimized_steady_solving.py - 优化方法

**系统辨识类：**
- 03_idz_identification.py - IDZ辨识
- 05_step_response.py - 阶跃响应  
- 10_canal_deep_analysis.py - 深度分析

**水工结构类：**
- 07_sluice_gate_flow.py - 单闸门
- 11_advanced_structures.py - 多结构
- 12_advanced_optimized.py - 结构优化

**可视化类：**
- 01_basic_with_animation.py - 基础动画
- 06_animation.py - 完整动画
- 09_simple_canal_enhanced.py - 增强可视化

**边界条件类：**
- 04_boundary_conditions.py - 边界条件分析
- 10_canal_deep_analysis.py - 深度边界分析

## 生成的输出文件

### 基础示例输出 (01-06)

- **Figures:** 22 PNG (~3.6 MB)
- **Animations:** 5 GIF (~4.5 MB)  
- **Tables:** 6 CSV (~64 KB)

### 高级示例输出 (07-12)

- **Figures:** 8 PNG (~1.0 MB)
- **Animations:** 5 GIF (~9.3 MB)
- **Tables:** 10 CSV (~1.5 MB)
- **Reports:** 1 MD (~2 KB)

**总计:** 30 PNG + 10 GIF + 16 CSV + 1 MD ≈ 14 MB

## 历史说明

- **原 code/ 目录：** 包含脚本 01-06（主要开发脚本）
- **原 archive/ 目录：** 包含高级实验脚本（已整合为 07-12）
- **统一后：** 所有脚本平等对待，按功能编号

## 注意事项

1. 所有脚本都需要设置 `PYTHONPATH` 指向项目根目录
2. 所有脚本都使用 `output_helper.py` 统一管理输出
3. 所有输出文件都保存到统一的 `results/` 目录
4. 图表均使用英文标签，避免中文字体问题

---

*最后更新: 2025-10-23*
*整合人: Claude*
