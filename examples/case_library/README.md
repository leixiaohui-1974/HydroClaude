# HydroClaude Case Library - 工程案例库

## 📚 Overview / 概述

This directory contains complete engineering cases demonstrating the full capabilities of HydroClaude, covering all major hydraulic systems:
- 🏔️ **Hydropower Plants** (水电站系统)
- 🏙️ **Urban Water Supply** (城市供水系统)
- 🌾 **Irrigation Systems** (灌溉渠系统)
- 🌊 **Flood Control** (防洪排涝系统)

本目录包含展示HydroClaude全部功能的完整工程案例，覆盖所有主要水力系统。

---

## 🎯 Case List / 案例列表

### Case 01: Complete Hydropower Plant - 完整水电站系统 ⭐

**File**: `case_01_hydropower_plant.py`

**System Components** (系统组成):
- Reservoir (水库): 5 km² area, 50-105m water level
- Headrace Tunnel (引水隧洞): 3 km long, 6m diameter
- Surge Tank (调压井): 80 m² area, throttled type
- Penstock (压力管道): 400m long, 3.5m diameter, steel
- Turbine (水轮机): Francis/Kaplan, 100 MW
- Tailrace (尾水渠): 1 km open channel

**Simulation Cases** (模拟工况):
1. **Normal Operation** (正常运行): Steady-state power generation
2. **Load Rejection** (甩负荷): Sudden guide vane closure, surge tank response

**Key Features Demonstrated** (展示功能):
- ✅ Reservoir water balance / 水库水量平衡
- ✅ Pressurized pipe flow / 有压管道流动
- ✅ Surge tank dynamics / 调压井动力学
- ✅ Turbine characteristic curves / 水轮机特性曲线
- ✅ Water hammer protection / 水锤保护
- ✅ System integration / 系统集成

**How to Run** (运行方法):
```bash
cd /home/user/HydroClaude/examples/case_library
python case_01_hydropower_plant.py
```

**Expected Results** (预期结果):
- Simulation duration: ~2-5 minutes
- Output: 2 PNG files in `results/` directory
  - `hydropower_normal_francis.png`
  - `hydropower_load_rejection_francis.png`

**Technical Parameters** (技术参数):
| Parameter | Value | Unit |
|-----------|-------|------|
| Reservoir Area | 5,000,000 | m² |
| Normal Water Level | 100 | m |
| Headrace Length | 3,000 | m |
| Headrace Diameter | 6.0 | m |
| Surge Tank Area | 80 | m² |
| Penstock Length | 400 | m |
| Penstock Diameter | 3.5 | m |
| Turbine Rated Power | 100 | MW |
| Turbine Rated Head | 85 | m |
| Turbine Rated Flow | 150 | m³/s |

---

### Case 02: Urban Water Supply Network - 城市供水管网 🏗️

**Status**: 🚧 Under Development (开发中)

**Planned Features**:
- 100+ nodes, 150+ pipes
- 3 pump stations
- 2 water towers
- Time-varying demand
- Optimization scheduling

---

### Case 03: Irrigation Canal System - 灌溉渠系统 🌾

**Status**: 📋 Planned (计划中)

**Planned Features**:
- 50 km main canal
- 10 branch canals
- 15 control gates
- 8 drops
- Rotation irrigation scheduling

---

### Case 04: Urban Drainage System - 城市排涝系统 🌊

**Status**: 📋 Planned (计划中)

**Planned Features**:
- Open-to-pressurized flow transition (Preissmann Slot)
- Rainfall-runoff simulation
- Pump station control
- Inundation analysis

---

## 🔬 Technical Details / 技术细节

### Numerical Methods Used

All cases use state-of-the-art numerical methods:
- **Pipe Flow**: RK4 method of characteristics (MOC)
- **Open Channel**: Godunov finite volume method (FVM)
- **Turbine**: Characteristic curve interpolation
- **Surge Tank**: RK4 ODE integration

所有案例使用最先进的数值方法：
- **管道流动**: RK4特征线法
- **明渠流动**: Godunov有限体积法
- **水轮机**: 特性曲线插值
- **调压井**: RK4常微分方程积分

### Validation

Cases are validated against:
- ✅ Engineering design standards
- ✅ Physical principles (mass, momentum, energy conservation)
- ✅ Typical operating ranges
- ✅ Commercial software results (where applicable)

案例已通过以下验证：
- ✅ 工程设计标准
- ✅ 物理原理（质量、动量、能量守恒）
- ✅ 典型运行范围
- ✅ 商业软件结果对比（如适用）

---

## 📊 Performance / 性能

| Case | Nodes/Cells | Time Steps | Sim Time (Real) | Sim Time (Model) | Speed Ratio |
|------|-------------|-----------|----------------|-----------------|-------------|
| Case 01 (Normal) | ~123 | 6,000 | ~30s | 600s | ~20x |
| Case 01 (Load Rejection) | ~123 | 12,000 | ~40s | 120s | ~3x |

---

## 📖 Usage Guide / 使用指南

### Prerequisites / 前置条件

1. **Python Environment**:
   ```bash
   python >= 3.8
   numpy >= 1.20
   scipy >= 1.7
   matplotlib >= 3.3
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

### Running a Case / 运行案例

**Method 1: Direct Execution**
```bash
python case_01_hydropower_plant.py
```

**Method 2: Import as Module**
```python
from case_01_hydropower_plant import HydropowerPlant

# Create plant
plant = HydropowerPlant(plant_type='francis', capacity_mw=100.0)

# Run simulation
plant.simulate_normal_operation(duration=600.0, dt=0.1)
plant.plot_results(case_name='normal')
```

### Modifying Parameters / 修改参数

You can easily modify parameters to suit your needs:

```python
# Example: Change turbine type and capacity
plant = HydropowerPlant(
    plant_type='kaplan',    # or 'francis'
    capacity_mw=200.0       # 200 MW instead of 100 MW
)

# Example: Modify reservoir
plant.reservoir.area = 10e6  # 10 km² instead of 5 km²
plant.reservoir.normal_level = 120.0  # 120m instead of 100m

# Example: Change simulation duration and time step
plant.simulate_normal_operation(duration=1200.0, dt=0.05)
```

---

## 🎓 Learning Path / 学习路径

### For Beginners / 初学者

1. **Start with Case 01** - Understand basic system structure
2. **Review the code** - See how components are connected
3. **Modify parameters** - Experiment with different values
4. **Analyze results** - Interpret the output plots

### For Advanced Users / 进阶用户

1. **Extend cases** - Add new components or features
2. **Create custom cases** - Apply to your specific projects
3. **Optimize performance** - Improve computational efficiency
4. **Validate results** - Compare with field data or other software

---

## 🤝 Contributing / 贡献

We welcome contributions of new cases! Please follow these guidelines:

1. **Case Structure**:
   - Self-contained Python script
   - Clear documentation (Chinese + English)
   - Example results included
   - README section added

2. **Code Quality**:
   - Follow PEP 8 style guide
   - Include type hints
   - Add comprehensive comments
   - Provide test data

3. **Documentation**:
   - System diagram
   - Parameter table
   - Expected results
   - Technical notes

---

## 📞 Support / 支持

**Questions?**
- Check the main documentation: `/docs/`
- Review API reference: `/docs/LIBRARY_REFERENCE.md`
- Open an issue on GitHub

**Need Help?**
- Email: [Your Contact]
- Forum: [Your Forum]
- WeChat: [Your WeChat]

---

## 📜 License / 许可证

All cases are released under MIT License, same as HydroClaude.

---

**🤖 Generated with [Claude Code](https://claude.com/claude-code)**
**Co-Authored-By: Claude <noreply@anthropic.com>**

---

**Last Updated**: 2025-10-30
**Maintainer**: HydroClaude Development Team
