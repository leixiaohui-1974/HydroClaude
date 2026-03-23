# HydroClaude 项目规范

## 核心原则

### 1. 第一性原理
- 所有水力学计算必须基于物理方程（能量方程、动量方程、Manning 公式等）
- 不允许用经验修正系数"凑"精度
- 遇到精度问题时，先诊断根因（逐断面对比 A/P/R/K/Sf），再针对性修复
- 修改代码前先查 HEC-RAS Technical Reference Manual 的具体章节

### 2. 数据来源严格限制
- **只能使用 HEC-RAS 的输入数据和参数**（几何、边界条件、结构物参数、Manning n、损失系数等）
- **这些数据从 HEC-RAS 的 .g01/.f01/.p01 文件或对应 HDF 的 Geometry 组中提取**
- **禁止使用 HEC-RAS 的计算结果**（WSE、flow 分配、K、Sf 等 Results 组中的数据）作为 HydroClaude 的输入
- 参考结果（WSE）只用于**验证对比**（计算 MAE），不能注入求解过程
- 分流/汊口流量必须通过求解器自己计算，不能从 HEC-RAS 结果的 flow 字段反推
- lateral_inflows 只用于 HEC-RAS 输入文件中定义的已知区间来水（如支流汇入）

### 3. 国际标准单位 (SI)
- 内部所有计算使用 SI 单位（m, m³/s, m/s）
- HEC-RAS 参考数据存储英制值时，通过 utils/unit_conversion.py 转换
- HDS-5 涵洞系数是按英制标定的，代入前必须转换 Q/A/D 为英制

### 4. 精度对标标准
- 目标：MAE < 0.15m（与 HEC-RAS 对标）
- 参考数据：reports/hecras_reference_data/ (19 案例 45 工况)
- 验证命令：`python hydroclaude_cli.py batch`
- 任何修改不能导致已通过案例回归

## 技术栈
- Python 3.10+
- scipy (brentq, fsolve)
- numpy
- h5py (HEC-RAS HDF 读取)

### 5. 输水能力 K 必须用分区计算
- **稳态和非恒定流求解器必须使用 LOB/Channel/ROB 三区分区计算 K**
- K_total = K_LOB + K_Ch + K_ROB，每区使用独立 Manning n 和独立湿周
- 稳态求解器已实现：`SteadyProfileSolver._compute_subdivided_conveyance()` + `_zone_conveyance()`
- 非恒定流求解器的 `PropertyTable` 必须复用同样的分区逻辑
- 单一 Manning n 计算整个断面 K 会在洪水漫滩时产生 20-40% 偏差

## 关键文件
- `solvers/steady_profile_solver.py` — 稳态求解器（含分区 K 计算）
- `solvers/unsteady_preissmann_solver.py` — 非恒定流 Preissmann 求解器
- `solvers/unsteady_network_solver.py` — 河网非恒定流求解器
- `physics/structures/culvert.py` — 涵洞 HDS-5
- `physics/cross_section.py` — 断面几何
- `physics/property_table.py` — 断面属性预计算表
- `integration/hec_ras_adapter.py` — HEC-RAS 适配器
- `hydroclaude_cli.py` — CLI 工具
- `utils/unit_conversion.py` — 单位转换
