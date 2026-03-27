# 非恒定流对标案例

本目录用于组织 `HEC-RAS -> HydroClaude -> 统一验证报告` 的非恒定流案例。

## 结构

```text
validation_cases/unsteady/
  metadata/
  dam_break/
  flood_routing/
  gate_operation/
  mixed_flow/
```

## 规则

- 每个案例必须有 `case_metadata.json`
- 每个案例的 `modeling_basis_case` 和 `steady_basis_case` 必须能在 `validation_cases/unsteady/metadata/basis_registry.json` 中解析
- `HEC-RAS` 结果只能用于验证，不得作为 HydroClaude 输入
- metadata 中必须写明：
  - 物理类别
  - HEC-RAS 模式
  - HydroClaude 求解器
  - 输入来源
  - 验证指标
  - 当前状态
- 若 steady basis 只是 `same_physics_family` 或仍是 `planned_gap`，报告中必须明确写出，不能冒充同项目三阶段闭环

## 运行

单案例：

```bash
python scripts/run_unsteady_hecras_benchmark.py validation_cases/unsteady/dam_break/case_metadata.json
```

批量：

```bash
python scripts/run_unsteady_hecras_benchmark.py --all
```
