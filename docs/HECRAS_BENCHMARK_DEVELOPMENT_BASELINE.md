# HydroClaude HEC-RAS 对标开发基线

## 目标

HydroClaude 后续开发以“对标 HEC-RAS 的主要案例族和数值原理”为主线推进，重点覆盖：

- 稳态水面线
- 1D 非恒定流
- 结构物控制与过流
- 混合流与跨临界
- 干湿交替与溃坝波
- 河网、junction、storage area 关联场景

目标不是挑选少量容易案例，而是建立可复用、可扩展、可审计的对标体系。

## 第一性原则

- 所有改动必须能对应到控制方程、离散格式、边界条件、结构方程或单位换算。
- 不允许通过经验修正、结果回填、选择性汇报或案例规避来“凑数”。
- 任何“与 HEC-RAS 一致”的说法，都必须对应明确的案例、输入、求解设置和误差报告。

## 对标方法

### 1. 先判问题类型，再选求解器

每个案例在实现前必须先标注：

- 物理类别：稳态 / 非恒定 / 混合流 / 结构控制 / 溃坝 / 河网
- HEC-RAS 对应能力：1D finite difference / 1D finite volume / HTAB / mixed flow / storage-junction
- HydroClaude 对应求解器：steady profile / hydrostatic / Preissmann / Godunov-FVM / network solver

### 1.1 固定开发流水线

所有 HEC-RAS 对标开发必须按以下顺序推进：

1. 建模
2. 稳态计算
3. 非恒定流计算

含义如下：

- 建模阶段必须完全复用 HEC-RAS 的基础输入数据，不能建立“看起来类似”的替代模型。
- 稳态阶段用于验证几何解释、断面输水能力、边界条件和结构静态行为是否正确。
- 非恒定流阶段不是重新开始，而是在同一套已达标模型上继续做时间推进和动态边界对标。
- 因此，非恒定流误差的排查顺序必须是：先排除建模误差，再排除稳态误差，最后才进入时间推进、源项和流态处理误差。

### 2. 输入和结果分离

- 允许使用 HEC-RAS 输入：几何、断面、糙率、bank stations、reach lengths、边界、结构参数、HTAB 原始输入。
- 不允许使用 HEC-RAS 结果作为 HydroClaude 输入：WSE、flow split、computed K、Sf、结果时序。
- HEC-RAS 结果只用于验证阶段的误差统计和现象对比。

### 3. 非恒定流验收指标

非恒定流案例至少要输出以下指标：

- stage MAE / RMSE
- discharge MAE / RMSE
- peak stage error
- peak timing error
- mass balance error
- wave celerity or front-position error
- regime transition notes

## 案例分层

### A 类：解析/教材标准案例

- Ritter dam break
- MacDonald cases
- Gradually varied flow
- Hydraulic jump canonical cases

作用：

- 验证方程离散、守恒和收敛阶

### B 类：HEC-RAS 官方或可审计工程案例

- Steady profile examples
- Unsteady routing examples
- Gate operation
- Mixed flow regime channel
- Bridge / culvert / inline structure

作用：

- 验证真实工程设置下与 HEC-RAS 的一致性

### C 类：HydroMind 体系耦合案例

- 控制调度
- HIL / E2EControl 联动
- 多项目接口验证

作用：

- 验证 HydroClaude 在主项目体系中的可集成性

## 当前推进顺序

1. 稳态 45 工况基线固化，不回归。
2. 非恒定流首批 4 类算例闭环：
   - dam break
   - inflow flood routing
   - gate operation
   - mixed-flow / near-critical
3. 建立 HEC-RAS case ingestion -> HydroClaude reconstruction -> batch verification 的统一流程。
4. 扩展到结构物、河网和 storage/junction 场景。

当前实施细化见：

- `docs/HECRAS_UNSTEADY_IMPLEMENTATION_PLAN.md`

当前前提说明：

- 稳态 45 工况已经是非恒定流开发的前置基线。
- 后续任何非恒定流案例都必须挂接到对应的同源建模和稳态基线上。

## Team 模式约定

当用户以 `team` 开头下达任务时，默认采用 `tri-model-collab` 工作方式：

- 主模型：`Codex Main / gpt-5.4`
- 研究和设计可以使用 team 分工
- 最终结论必须回到仓库内的代码、测试、报告和可复现命令

## 每次开发必须回答的问题

- 这个问题对应哪一个控制方程或结构方程？
- 这个案例的边界条件是否和 HEC-RAS 输入完全一致？
- 当前误差主要来自几何、摩阻、边界、源项、时间推进还是流态处理？
- 修改是否会回归已通过的稳态 45 工况或现有非恒定流基准？

## 交付物要求

每个新增 HEC-RAS 对标案例至少提供：

- case metadata
- HEC-RAS 输入来源说明
- HydroClaude 重建脚本或配置
- 运行命令
- 对比图和误差表
- 已知问题和下一步计划
