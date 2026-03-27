# HEC-RAS 非恒定流参考资产清单

## 范围

本清单对应当前目录：

- `reports/hecras_unsteady_reference`
- `validation_cases/unsteady`

## 当前结论

截至当前，`reports/hecras_unsteady_reference` 下的 8 个参考 JSON 已全部映射到 metadata 体系，并且每个案例都已绑定：

- 一个真实的 `modeling_basis_case`
- 一个可解析的 `steady_basis_case`
- 一个统一的 registry：`validation_cases/unsteady/metadata/basis_registry.json`

另有 1 个规划态占位案例：

- `gate_operation`

该占位案例目前没有绑定真实 `HEC-RAS` reference JSON，仅用于保留开发接口和后续接入位置。

需要特别区分：

- `same_project_unsteady_source`：当前 unsteady 的 HEC-RAS 同项目输入来源已定位
- `same_physics_family`：当前 steady basis 只定位到同物理家族的稳态参考，并非同项目闭环
- `planned_gap`：稳态前置尚未补齐，不能宣称三阶段闭环

当前仓库中**不存在任何已完成 `same_project` steady prerequisite 的非恒定流案例**。

对于 `Bridge Hydraulics` 与 `Culvert Hydraulics` 还必须额外说明：

- 当前 source project 已定位到真实同项目 unsteady source（分别为 `beaver.prj / p03` 与 `Beav_Culvert.prj / p01`）
- 但这两个源项目当前都显示 `steady_flows: []`
- 因此它们的 same-project steady prerequisite **不是“文件已存在但尚未回填”**，而是**当前项目资产集中根本不存在可回填 steady 结果**
- 若未来要升级为 same-project 三阶段闭环，必须先在对应 HEC-RAS 项目中额外创建并运行 dedicated steady plan，再提取并注册 steady artifacts

## 映射表

| Reference JSON | Metadata Case ID | Modeling Basis ID | Steady Basis ID | Steady Status | Runner Mode | 状态 |
|---|---|---|---|---|---|---|
| `BridgeHydraulics_unsteady_ref.json` | `unsteady_bridge_hydraulics_01` | `hec_project_bridge_hydraulics_beaver_p03` | `steady_family_bridge_beaver_bridge_scour` | `same_physics_family` | `single_reach_json_preissmann` | active |
| `CulvertHydraulics_unsteady_ref.json` | `unsteady_culvert_hydraulics_01` | `hec_project_culvert_hydraulics_beav_culvert_p01` | `steady_family_culvert_examples` | `same_physics_family` | `single_reach_json_preissmann` | active |
| `DamBreaching_unsteady_ref.json` | `unsteady_dam_breaching_01` | `hec_project_dam_breaching_baldeagledambrk_p06` | `steady_gap_dam_breaching_same_project` | `planned_gap` | `single_reach_json_preissmann` | active |
| `Example17_Unsteady_unsteady_ref.json` | `unsteady_flood_routing_01` | `hec_project_example17_diamond_p01` | `steady_gap_example17_same_project` | `planned_gap` | `network_json_preissmann` | active, currently `BLOCKED` by storage-area connection and lateral-to-storage physics gaps |
| `Example20_LateralWeir_unsteady_ref.json` | `unsteady_lateral_weir_01` | `hec_project_example20_hagerlatweir_p07` | `steady_family_lateral_weir_split_flow` | `same_physics_family` | `single_reach_json_preissmann` | active |
| `JunctionHydraulics_unsteady_ref.json` | `unsteady_junction_hydraulics_01` | `hec_project_junctionhydraulics_p02` | `steady_family_stream_junction` | `same_physics_family` | `network_json_preissmann` | active |
| `MixedFlowRegime_unsteady_ref.json` | `unsteady_mixed_flow_01` | `hec_project_mixed_flow_regime_mixedflow_p02` | `steady_family_mixed_flow_channel` | `same_physics_family` | `single_reach_json_preissmann` | active |
| `MultipleReaches_unsteady_ref.json` | `unsteady_multiple_reaches_01` | `hec_project_multiple_reaches_3reachunsteady_p01` | `steady_family_network_structures` | `same_physics_family` | `network_json_preissmann` | active |

## 额外占位案例

| Metadata Case ID | Category | Modeling Basis ID | Steady Basis ID | Runner Mode | 状态 | 说明 |
|---|---|---|---|---|---|---|
| `unsteady_gate_operation_01` | `gate_operation` | `hec_project_gate_operation_placeholder` | `steady_gap_gate_operation` | `inventory_only` | planned | 尚未接入真实 gate-control reference JSON |

## 当前 runner 覆盖

已接入统一入口的 runner：

- `single_reach_json_preissmann`
- `network_json_preissmann`
- `inventory_only`

尚未接入统一入口但后续应补的 runner：

- `single_reach_json_godunov`
- `dam_break_dual_solver`
- `structure_gate_control`
- `fv_mixed_flow`

## 下一步

1. 继续补齐 `planned_gap` 的同项目 steady basis，优先处理 `Dam Breaching` 和 `Example 17`。
2. 对 `Dam Breaching` 保持“steady precursor 缺失 + 当前 Preissmann 仅是临时 benchmark path”的口径；在 reservoir/downstream steady base state 被提取并注册之前，不得把当前结果当作闭环证据。
3. 对 `Example 17` 保持“steady precursor 缺失 + storage-area / lateral-to-storage 一阶动态组件缺失”的口径；在这两个前置条件同时满足前，不得把它当作普通 network patch 目标。
4. 对 `Bridge Hydraulics` 与 `Culvert Hydraulics` 保持当前 `same_physics_family` 口径；在外部 HEC-RAS 侧创建 dedicated steady plan 之前，不得把它们表述为“same-project steady 仅待回填”。
5. 运行 `--all` 形成当前批量现状，并在报告里保留 steady status。
6. 把 `PASS / NEAR / FAIL / PLANNED` 与 `same_project / same_physics_family / planned_gap` 交叉汇总。
7. 对 `NEAR/FAIL` 案例按物理类别拆成专题修复路线。

当前已识别的 `BLOCKED` 类：

- `Example 17 Unsteady Flood Routing`
  - 原因：`storage_area_connection`、`lateral_structure_to_storage`
  - 含义：当前 HydroClaude network runner 尚未把 storage area、storage-area connection、lateral-to-storage exchange 建成一阶动态方程组件，因此不能把该案例误报为普通 network 求解失败
