# HydroClaude 非恒定流 HEC-RAS 对标实施清单

## 现状结论

当前仓库已经具备非恒定流开发的部分基础，但还没有形成完整的 `HEC-RAS -> HydroClaude -> 批量验证` 闭环。

更严格地说，非恒定流开发必须被视为以下流水线的第三阶段：

1. 建模与基础数据一致性
2. 稳态计算达标
3. 非恒定流计算达标

已确认的事实：

- 已有稳态 HEC-RAS 参考数据目录：`reports/hecras_reference_data`
- 已有非恒定流参考目录：`reports/hecras_unsteady_reference`
- 已有 HEC-RAS 原始案例/提取资产：`reports/hecras_cases`、`reports/hecras_examples_raw`
- 已有 HEC-RAS 运行时和 HDF 提取适配器：`integration/hec_ras_adapter.py`
- 已有非恒定流求解器：`solvers/unsteady_preissmann_solver.py`、`solvers/godunov_fvm_solver.py`
- 现有 `hydroclaude_cli.py batch` 仍然是稳态对标入口，主要消费 `reports/hecras_reference_data`

这意味着：

- 稳态对标基线已成形
- 非恒定流对标仍处于“资产存在、流程未闭环”的阶段
- 非恒定流不能脱离前置建模和稳态基线单独推进

## 当前可复用资产

### 1. 求解器层

- `solvers/unsteady_preissmann_solver.py`
  - 适合对标 HEC-RAS 1D finite difference 类案例
  - 已有分区 conveyance、HTAB、质量平衡和部分网络边界能力

- `solvers/godunov_fvm_solver.py`
  - 适合对标 HEC-RAS 1D finite volume / dam-break / mixed-flow 类案例
  - 已有 well-balanced、干湿处理、质量误差统计和混合边界稳定化

### 2. 集成层

- `integration/hec_ras_adapter.py`
  - 已能做 runtime 检测
  - 已能读取 project / plan / HDF 摘要
  - 已有 mixed-flow sample 和 flow-regime diagnose 能力

### 3. 参考和验证层

- `validation_cases/analytical/dam_break_ritter.py`
- `validation_cases/analytical/dam_break_godunov.py`
- `tests/diagnostic/test_godunov_dam_break.py`
- `tests/diagnostic/test_transient_flow.py`

这些资产可作为非恒定流第一批基准，但还不是 HEC-RAS 工程对标闭环。

## 当前缺口

### 0. 缺建模-稳态-非恒定的显式关联

当前 metadata 和运行入口已经开始形成，但还没有显式记录：

- 该非恒定案例对应哪一套 HEC-RAS 基础模型
- 该模型对应哪一个稳态基线案例或稳态验证结果
- 当前非恒定案例是否继承了同一套几何、糙率、bank stations、边界解释和结构参数

这部分必须补上，否则非恒定流验证会失去前提约束。

当前补充约束：

- `validation_cases/unsteady/metadata/basis_registry.json` 是 unsteady 三阶段 traceability 的单一真源。
- `modeling_basis_case` 和 `steady_basis_case` 必须引用 registry 中的真实 ID。
- 若 steady basis 只是 `same_physics_family` 或 `planned_gap`，报告必须明示，不能表述为同项目稳态已闭环。

### 1. 缺统一的非恒定流案例元数据

目前缺少一套统一 schema 来描述：

- 案例名称
- 对应的建模基线
- 对应的稳态基线
- HEC-RAS 项目来源
- 单位系统
- 几何输入文件
- 边界条件时序
- 结构物输入
- 目标求解器
- 验证点位
- 对比指标

### 2. 缺统一的重建入口

目前还没有统一脚本完成：

- 从 HEC-RAS 非恒定案例中抽取输入
- 重建 HydroClaude 配置
- 选择 Preissmann 或 Godunov 求解器
- 输出统一误差报告

### 3. 缺非恒定流批量 CLI

`hydroclaude_cli.py batch` 现在主要用于稳态工况，不适用于：

- 时序边界
- 峰值时刻误差
- 洪峰传播
- 波前位置
- 动态结构控制

### 4. 缺案例分流策略

当前最容易犯的错误是混用数值路线。

必须明确：

- `Preissmann` 对标 `HEC-RAS 1D finite difference`
- `Godunov-FVM` 对标 `HEC-RAS 1D finite volume`
- 结构物 / HTAB / mixed-flow 场景需要单独建类，不可简单归入“普通非恒定流”

## 首批实施范围

第一阶段只做 4 类案例，先建立闭环，不追求一次性覆盖全部。

### A. Dam Break

目标：

- 建立 Godunov-FVM 与解析解、HEC-RAS FV 的双基准对比

需要输出：

- 水深时空图
- 波前位置误差
- 峰值误差
- 质量守恒误差

建议主入口：

- `validation_cases/unsteady/dam_break/`

### B. Inflow Flood Routing

目标：

- 建立入流洪水波传播与下游 stage/normal depth 边界的对比基线

优先求解器：

- `Preissmann`
- 必要时增加 `Godunov-FVM` 对照

需要输出：

- 关键断面时序
- 峰值时间偏差
- 峰值水位偏差
- 总量守恒误差

### C. Gate Operation

目标：

- 对标 HEC-RAS 中随时间变化的闸门控制案例

关键点：

- 开度时序输入
- gate flow regime 切换
- 上下游壅水响应
- 结构方程与边界耦合

### D. Mixed Flow / Near Critical

目标：

- 对标 HEC-RAS mixed-flow 或跨临界案例

优先求解器：

- `Godunov-FVM`

关键点：

- 流态识别
- 跨临界稳定性
- 波面和流量突变
- 必要时保留失败案例并记录根因

## 推荐目录结构

建议新增：

```text
validation_cases/
  unsteady/
    metadata/
    dam_break/
    flood_routing/
    gate_operation/
    mixed_flow/
reports/
  hecras_unsteady_reference/
  hecras_unsteady_validation/
scripts/
  build_unsteady_case_metadata.py
  extract_hecras_unsteady_inputs.py
  run_unsteady_hecras_benchmark.py
```

## 建议的数据结构

每个案例建议至少包含一个 `case_metadata.json`，字段如下：

```json
{
  "case_id": "unsteady_dam_break_01",
  "modeling_basis_case": "hec_project_dam_breaching_baldeagledambrk_p06",
  "steady_basis_case": "steady_gap_dam_breaching_same_project",
  "category": "dam_break",
  "hec_ras_mode": "1d_finite_volume",
  "hydroclaude_solver": "godunov_fvm",
  "unit_system": "si",
  "geometry_source": "path/to/project.g01",
  "boundary_source": "path/to/project.u01",
  "plan_source": "path/to/project.p01",
  "validation_targets": ["stage_timeseries", "peak_timing", "mass_balance"],
  "output_stations": ["XS_01", "XS_05", "XS_10"]
}
```

其中：

- `modeling_basis_case` 指向 HEC-RAS 同项目输入来源
- `steady_basis_case` 指向稳态前置 basis，可标记为 `same_project`、`same_physics_family` 或 `planned_gap`

## 第一阶段具体任务

### Task 1

建立 `validation_cases/unsteady/` 目录与统一 metadata 结构。

完成标准：

- 至少 4 个案例目录骨架
- 每个案例有 metadata 模板
- metadata 中能表达其上游的建模基线和稳态基线

### Task 2

新增 `run_unsteady_hecras_benchmark.py`，统一完成：

- 读 metadata
- 检查建模/稳态前置字段
- 选求解器
- 读取 HydroClaude 配置
- 输出统一误差 JSON/Markdown

完成标准：

- 单案例命令可运行
- 输出结构一致

### Task 3

将 `reports/hecras_unsteady_reference` 中已有资产清点并映射到案例 metadata。

完成标准：

- 出具 inventory 文档
- 每个资产归入明确案例类型

### Task 4

实现非恒定流批量入口。

建议形式：

- 新增 CLI 子命令，例如 `hydroclaude unsteady-batch`
- 或在现有 `hydroclaude_cli.py` 中扩展 `unsteady-batch`

完成标准：

- 至少支持首批 4 类案例批量运行
- 输出 pass / fail / near 状态

## 验收标准

### 工程标准

- 案例可复现
- 输入来源明确
- 单位换算明确
- 求解器选择有理由
- 失败案例不被隐藏

### 数值标准

至少检查：

- stage MAE / RMSE
- discharge MAE / RMSE
- peak stage error
- peak timing error
- mass balance error
- wave-front or celerity error

## 当前建议的开发顺序

1. 先补目录和 metadata，不先改求解器。
2. 把每个非恒定案例挂接到对应的建模和稳态基线。
3. 再做单案例统一入口。
4. 然后把现有 `reports/hecras_unsteady_reference` 资产接进来。
5. 再进入首批 4 类案例的误差收敛和方程修正。

## 不该做的事

- 不要先宣称“非恒定流已全面对标”。
- 不要先把 README 能力描述继续拔高。
- 不要在未区分 HEC-RAS FD / FV 的情况下比较数值误差。
- 不要跳过失败案例。
