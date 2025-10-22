# HydroClaude 动画生成指南

## 概述

HydroClaude提供了两种方式生成示例动画：

1. **嵌入式动画生成**（推荐）：在示例脚本中集成动画生成功能，使用`--animate`参数控制
2. **独立动画生成器**：使用`comprehensive_animation_generator.py`批量生成所有示例的动画

## 方法1：嵌入式动画生成（推荐）

### 优势

- 使用真实的仿真数据
- 与代码逻辑紧密集成
- 可选择性生成（节省时间）
- 更灵活的自定义

### 使用步骤

#### 1. 导入动画工具模块

```python
import sys
import os

# 添加examples目录到路径
EXAMPLES_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, EXAMPLES_DIR)
from animation_utils import AnimationGenerator
```

#### 2. 添加命令行参数

```python
import argparse

def parse_args():
    parser = argparse.ArgumentParser(description='Your example description')
    parser.add_argument('--animate', action='store_true',
                       help='生成动画（默认：不生成）')
    parser.add_argument('--animation-fps', type=int, default=10,
                       help='动画帧率 (默认: 10)')
    parser.add_argument('--animation-dpi', type=int, default=100,
                       help='动画DPI (默认: 100)')
    return parser.parse_args()

args = parse_args()
```

#### 3. 在仿真后生成动画

```python
if args.animate:
    print("生成动画...")

    # 创建动画生成器
    anim_gen = AnimationGenerator(
        output_dir='./outputs/animations',
        fps=args.animation_fps,
        dpi=args.animation_dpi
    )

    # 时间序列动画
    gif_path = anim_gen.create_timeseries_animation(
        t=time_array,
        data={
            'Speed': speed_array,
            'Power': power_array,
            'Pressure': pressure_array,
        },
        filename='transient_response.gif',
        title='Turbine Transient Response',
        xlabel='Time (s)',
        ylabels={
            'Speed': 'Speed (p.u.)',
            'Power': 'Power (p.u.)',
            'Pressure': 'Pressure (p.u.)',
        },
        reference_lines={
            'Speed': 1.0,
            'Power': 1.0,
            'Pressure': 1.0,
        },
        layout=(3, 1)
    )

    print(f"动画已保存: {gif_path}")
```

#### 4. 运行示例

```bash
# 不生成动画（快速测试）
python your_example.py

# 生成动画（默认设置）
python your_example.py --animate

# 自定义动画设置
python your_example.py --animate --animation-fps 15 --animation-dpi 150
```

### 完整示例

参考 `examples/example_01_canal_flow/code/01_basic_with_animation.py`，这是一个完整的嵌入式动画生成示例。

## 方法2：独立动画生成器

### 使用场景

- 批量生成所有示例的动画
- 为已有示例快速生成动画预览
- 不需要修改现有代码

### 使用步骤

```bash
cd examples
python comprehensive_animation_generator.py
```

该脚本会自动：
- 识别22个需要动画的示例
- 根据示例类型生成相应动画（水电站、控制系统、管道流动、水资源）
- 将GIF保存到各示例的`outputs/animations/`目录

## AnimationGenerator API 参考

### 初始化

```python
AnimationGenerator(output_dir='./outputs/animations', fps=10, dpi=100)
```

**参数:**
- `output_dir`: 输出目录
- `fps`: 帧率（推荐10-15）
- `dpi`: 分辨率（推荐100-150）

### create_timeseries_animation

创建时间序列动画（多子图）

```python
create_timeseries_animation(
    t,              # 时间数组
    data,           # 数据字典 {变量名: 数据数组}
    filename,       # 输出文件名
    title='',       # 主标题
    xlabel='Time (s)',  # x轴标签
    ylabels=None,   # y轴标签字典
    ylims=None,     # y轴范围字典
    reference_lines=None,  # 参考线字典
    layout=(None, 1),      # 子图布局 (rows, cols)
    figsize=None    # 图形大小
)
```

**示例:**
```python
anim_gen.create_timeseries_animation(
    t=t,
    data={
        'Upstream h': h_upstream,
        'Downstream h': h_downstream,
        'Flow Rate': Q_array,
    },
    filename='canal_timeseries.gif',
    title='Canal Flow Time Series',
    reference_lines={'Flow Rate': 8.0},
    layout=(3, 1)
)
```

### create_spatial_animation

创建空间分布动画（如管道流动、渠道水位）

```python
create_spatial_animation(
    x,              # 空间坐标数组
    t,              # 时间数组
    data,           # 数据字典 {变量名: 二维数组 (len(t), len(x))}
    filename,       # 输出文件名
    title='',       # 主标题
    xlabel='Distance (m)',  # x轴标签
    ylabels=None,   # y轴标签字典
    ylims=None,     # y轴范围字典
    layout=(None, 1),      # 子图布局
    figsize=None    # 图形大小
)
```

**示例:**
```python
# h_history: shape (n_timesteps, n_spatial_points)
anim_gen.create_spatial_animation(
    x=x_coords,
    t=time_array,
    data={
        'Water Depth': h_history,
        'Flow Velocity': u_history,
    },
    filename='canal_spatial.gif',
    title='Canal Flow Spatial Distribution',
    layout=(2, 1)
)
```

### create_network_animation

创建网络系统动画（管网、水电站系统等）

```python
create_network_animation(
    t,              # 时间数组
    nodes_data,     # 节点数据字典 {'Node1': pressure_array, ...}
    edges_data,     # 边数据字典 {'Pipe1': flow_array, ...}
    filename,       # 输出文件名
    title='',       # 主标题
    figsize=(14, 10)  # 图形大小
)
```

**示例:**
```python
anim_gen.create_network_animation(
    t=t,
    nodes_data={
        'Node A': pressure_A,
        'Node B': pressure_B,
        'Node C': pressure_C,
    },
    edges_data={
        'Pipe 1': flow_1,
        'Pipe 2': flow_2,
    },
    filename='network.gif',
    title='Pipe Network Dynamics'
)
```

## 动画类型分类

### 1. 水电站/水轮机暂态（Hydropower Transient）

**适用示例:**
- example_04_hydropower_system
- example_05_transient_analysis
- example_06_complete_hydropower_system

**典型变量:**
- 转速 (Speed)
- 功率 (Power)
- 导叶开度 (Guide Vane Opening)
- 蜗壳压力 (Spiral Case Pressure)

### 2. 控制系统响应（Control System）

**适用示例:**
- example_06_sil_basic
- example_07_fault_test
- example_07_multi_unit_agc
- example_13_adaptive_timescale
- example_14_adaptive_mpc
- example_15_rls_identification
- example_23_control_comparison
- example_24_multi_objective_optimization

**典型变量:**
- 系统输出 (Output)
- 设定值 (Setpoint)
- 跟踪误差 (Error)
- 控制信号 (Control Signal)

### 3. 管道/流动（Pipe Flow）

**适用示例:**
- example_02_spillway_cascade
- example_03_complex_network
- example_04_moc_boundary
- example_05_mode_comparison
- example_08_preissmann_vs_fvm
- example_09_pipe_rk4
- example_22_water_hammer

**典型变量:**
- 压力 (Pressure)
- 流量/流速 (Flow Rate / Velocity)
- 水锤波动 (Water Hammer Wave)

### 4. 水资源管理（Water Resource）

**适用示例:**
- example_16_weirs_application
- example_19_water_transfer
- example_20_urban_water_supply
- example_21_irrigation_optimization

**典型变量:**
- 水位 (Water Level)
- 入流/出流 (Inflow / Outflow)
- 蓄水量 (Storage)
- 供需平衡 (Supply / Demand)

## 最佳实践

### 1. 帧率选择

- **慢速过程（> 100s）**: 10 FPS
- **中速过程（10-100s）**: 10-12 FPS
- **快速过程（< 10s）**: 15 FPS
- **水锤等波动**: 15-20 FPS

### 2. 分辨率选择

- **预览/网页**: 80-100 DPI
- **报告/文档**: 100-150 DPI
- **论文/出版**: 150-200 DPI

### 3. 数据采样

为了生成流畅的动画，建议：
- 时间步数：100-200 帧
- 如果数据点太多（> 500），考虑降采样
- 如果数据点太少（< 50），考虑插值

```python
# 降采样示例
if len(time_array) > 200:
    step = len(time_array) // 200
    time_sampled = time_array[::step]
    data_sampled = data_array[::step]
```

### 4. 文件命名

推荐命名规范：
- `{example_name}_{variable}_timeseries.gif`
- `{example_name}_{variable}_spatial.gif`
- `{example_name}_network.gif`

示例：
- `example_01_canal_flow_spatial.gif`
- `example_03_turbine_transient.gif`
- `example_12_network_pressure.gif`

## 性能优化

### 减少生成时间

1. **降低帧数**: 使用100帧而不是200帧
2. **降低分辨率**: 使用80 DPI而不是150 DPI
3. **减少子图数量**: 只显示关键变量
4. **使用blit=True**: 已在代码中启用，加速渲染

### 减少文件大小

1. **降低FPS**: 10 FPS通常足够流畅
2. **降低DPI**: 100 DPI适合大多数用途
3. **优化颜色**: 使用简单的颜色方案
4. **限制帧数**: 100帧通常足以展示过程

## 故障排除

### 问题1: 中文字体警告

**症状:**
```
findfont: Generic family 'sans-serif' not found
```

**解决方案:**
- 代码已包含字体降级处理
- 或使用英文标签（推荐）

### 问题2: 动画生成太慢

**原因:**
- 数据点太多
- DPI设置太高
- 子图数量太多

**解决方案:**
- 降采样数据
- 降低DPI到80-100
- 减少子图数量

### 问题3: 动画文件太大

**原因:**
- FPS太高
- DPI太高
- 帧数太多

**解决方案:**
- 使用FPS=10
- 使用DPI=100
- 限制为100帧左右

### 问题4: 动画太快/太慢

**解决方案:**
```bash
# 调整帧率
python your_example.py --animate --animation-fps 8   # 更慢
python your_example.py --animate --animation-fps 15  # 更快
```

## 统计信息

截至2025-10-22，HydroClaude examples目录包含：

- **总示例数**: 31
- **已生成动画的示例**: 31（100%覆盖）
- **总动画数**: 33+ GIF文件
- **动画类型分布**:
  - 水电站暂态: 3个示例
  - 控制系统: 8个示例
  - 管道流动: 7个示例
  - 水资源: 4个示例
  - 其他: 9个示例（已有动画）

## 下一步计划

1. 为更多示例添加嵌入式动画生成
2. 支持3D可视化动画
3. 添加交互式动画（HTML5）
4. 生成视频格式（MP4）

## 参考资料

- `examples/animation_utils.py` - 动画工具模块源代码
- `examples/example_01_canal_flow/code/01_basic_with_animation.py` - 完整示例
- `examples/comprehensive_animation_generator.py` - 批量生成器
- Matplotlib Animation文档: https://matplotlib.org/stable/api/animation_api.html

## 支持

如有问题或建议，请提交issue到项目GitHub仓库。
