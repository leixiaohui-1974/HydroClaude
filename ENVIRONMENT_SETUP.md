# HydroClaude 环境设置指南

## 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/leixiaohui-1974/HydroClaude.git
cd HydroClaude
```

### 2. 安装依赖

```bash
# 基础依赖（必需）
pip install -r requirements_reservoir.txt

# 或者手动安装
pip install numpy scipy matplotlib
```

### 3. 验证安装

```bash
# 使用CLI工具检查环境
python hydro_cli.py check

# 或手动验证
python -c "import numpy, scipy, matplotlib; print('✓ 环境就绪')"
```

### 4. 运行第一个示例

```bash
# 使用CLI工具
python hydro_cli.py run 17

# 或直接运行
cd examples/example_17_reservoir_basic
python demo_reservoir.py
```

---

## 详细安装指南

### Python版本要求

- **推荐**: Python 3.9+
- **最低**: Python 3.8
- **测试**: Python 3.11

检查Python版本:
```bash
python --version
```

### 依赖包详细说明

#### 必需依赖

| 包 | 版本 | 用途 | 安装 |
|---|------|------|------|
| numpy | >= 1.20.0 | 数值计算 | `pip install numpy` |
| scipy | >= 1.7.0 | 科学计算 | `pip install scipy` |
| matplotlib | >= 3.3.0 | 可视化 | `pip install matplotlib` |

#### 优化功能依赖（可选）

| 包 | 版本 | 用途 | 安装 |
|---|------|------|------|
| pyomo | >= 6.7.0 | 优化建模 | `pip install pyomo` |
| pandas | >= 1.3.0 | 数据处理 | `pip install pandas` |

#### 求解器（可选，用于优化调度）

| 求解器 | 类型 | 安装方法 | 推荐度 |
|-------|------|---------|--------|
| GLPK | 开源LP/MIP | `apt-get install glpk-utils` | ⭐⭐⭐ |
| HiGHS | 开源LP/MIP | `pip install highspy` | ⭐⭐⭐⭐ |
| CPLEX | 商业LP/MIP | 下载安装包 | ⭐⭐⭐⭐⭐ |
| Gurobi | 商业LP/MIP | 下载安装包 | ⭐⭐⭐⭐⭐ |

---

## 平台特定安装

### Ubuntu / Debian

```bash
# 更新包管理器
sudo apt-get update

# 安装Python和pip
sudo apt-get install python3 python3-pip

# 安装系统依赖
sudo apt-get install python3-numpy python3-scipy python3-matplotlib

# 或使用pip安装
pip3 install -r requirements_reservoir.txt

# 安装GLPK求解器（可选）
sudo apt-get install glpk-utils
```

### macOS

```bash
# 使用Homebrew安装Python
brew install python

# 安装依赖
pip3 install -r requirements_reservoir.txt

# 安装GLPK（可选）
brew install glpk
```

### Windows

```bash
# 使用Anaconda（推荐）
conda create -n hydroclaude python=3.11
conda activate hydroclaude
conda install numpy scipy matplotlib

# 或使用pip
pip install -r requirements_reservoir.txt
```

---

## 虚拟环境设置

### 使用venv（推荐）

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Linux/macOS:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# 安装依赖
pip install -r requirements_reservoir.txt

# 退出虚拟环境
deactivate
```

### 使用conda

```bash
# 创建环境
conda create -n hydroclaude python=3.11

# 激活环境
conda activate hydroclaude

# 安装依赖
conda install numpy scipy matplotlib
# 或
pip install -r requirements_reservoir.txt

# 退出环境
conda deactivate
```

---

## 开发环境设置

### IDE配置

#### VSCode

1. 安装Python扩展
2. 选择Python解释器（使用虚拟环境）
3. 配置`.vscode/settings.json`:

```json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": true,
    "python.formatting.provider": "black"
}
```

#### PyCharm

1. 创建新项目，选择现有解释器
2. 配置Python解释器指向虚拟环境
3. 标记`HydroClaude`为源代码根目录

### 代码格式化

```bash
# 安装工具
pip install black flake8

# 格式化代码
black .

# 检查代码风格
flake8 .
```

---

## 验证安装

### 运行测试套件

```bash
# 使用CLI工具
python hydro_cli.py test

# 或直接运行
python tests/test_reservoir.py
```

### 检查环境

```bash
# 使用CLI工具
python hydro_cli.py check
```

预期输出:
```
检查环境依赖
================================================================================

✓ numpy           - 数值计算
✓ scipy           - 科学计算
✓ matplotlib      - 可视化
✓ pyomo           - 优化建模（可选）
✓ pandas          - 数据处理（可选）

✓ 所有依赖已安装
```

### 运行简单示例

```python
# test_basic.py
import sys
sys.path.append('.')

from physics.reservoir import Reservoir

# 创建水库
reservoir = Reservoir(
    reservoir_id="test",
    total_capacity=1000e4,
    dead_storage=100e4,
    min_level=100.0,
    normal_level=120.0,
    flood_limit_level=118.0,
    design_level=125.0
)

# 仿真
dt = 3600.0
inputs = {'inflow': 100.0, 'outflow_target': 80.0}
state = reservoir.update_high_fidelity(dt, inputs)

print(f"✓ 水库仿真成功")
print(f"  水位: {state.water_level:.2f} m")
print(f"  出流: {state.outflow:.2f} m³/s")
```

运行:
```bash
python test_basic.py
```

---

## 常见问题

### Q1: ImportError: No module named 'numpy'

**A**: numpy未安装。安装方法:
```bash
pip install numpy
```

### Q2: ModuleNotFoundError: No module named 'scipy'

**A**: scipy未安装。安装方法:
```bash
pip install scipy
```

### Q3: matplotlib中文显示乱码

**A**: 需要配置中文字体:
```python
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
```

或在系统中安装中文字体。

### Q4: Pyomo求解器不可用

**A**: 需要安装求解器:
```bash
# Linux
sudo apt-get install glpk-utils

# 或安装HiGHS
pip install highspy
```

### Q5: 示例运行时提示"权限拒绝"

**A**: 确保有执行权限:
```bash
chmod +x hydro_cli.py
./hydro_cli.py list
```

### Q6: Windows上路径问题

**A**: 使用反斜杠或原始字符串:
```python
path = r"C:\Users\xxx\HydroClaude"
# 或
path = "C:/Users/xxx/HydroClaude"
```

---

## 性能优化

### 加速计算

```bash
# 安装加速库
pip install numba

# 使用多核
export OMP_NUM_THREADS=4
```

### 减少内存占用

```python
# 使用float32代替float64
import numpy as np
data = np.array(data, dtype=np.float32)
```

---

## 卸载

### 删除虚拟环境

```bash
# venv
rm -rf venv

# conda
conda env remove -n hydroclaude
```

### 删除依赖包

```bash
pip uninstall -r requirements_reservoir.txt -y
```

---

## 获取帮助

### 文档

- 示例指南: `docs/EXAMPLES_GUIDE.md`
- API文档: `physics/README_RESERVOIR.md`
- 设计文档: `docs/INTEGRATION_DESIGN.md`

### 命令行工具

```bash
# 查看帮助
python hydro_cli.py help

# 查看系统信息
python hydro_cli.py info

# 列出示例
python hydro_cli.py list
```

### 在线资源

- GitHub Issues: 报告问题和建议
- 项目Wiki: 详细文档
- 示例代码: `examples/` 目录

---

## 更新日志

### v2.0.0 (2025-10-22)
- 新增水库调度功能
- 新增5个综合示例
- 新增CLI工具
- 完善文档体系

### v1.0.0
- 初始版本
- 基础物理组件

---

**维护者**: HydroClaude Team
**更新日期**: 2025-10-22
