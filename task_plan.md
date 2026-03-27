# Unsteady HEC-RAS Benchmark Breakthrough Plan

## Goal
在不违反第一性原理和 HEC-RAS 输入约束的前提下，继续提升 HydroClaude 的非恒定流对标能力；先用现有 metadata/runner 跑出现状，再选一个“阻塞性最强且可直接落地”的物理/数值缺口完成修复并验证。

## Current baseline
- 稳态 45 工况已完成，是非恒定流开发前置基线。
- 非恒定流已有 8 个 metadata 案例和统一 runner。
- 已识别 `Example 17` 属于 storage-area / lateral-to-storage 物理缺口，当前应视为 blocked，而不是普通求解失败。
- 当前主路线需要区分：
  - Preissmann ↔ HEC-RAS 1D finite difference
  - Godunov/FVM ↔ HEC-RAS 1D finite volume / mixed-flow / dam-break

## Phases

### Phase 1: Rebuild current unsteady benchmark status [in_progress]
- 运行 metadata 驱动的 unsteady benchmark
- 形成 PASS / NEAR / FAIL / BLOCKED 分布
- 识别优先修复对象

### Phase 2: Root-cause diagnosis for top-priority failure [completed]
- 读取 runner、solver、案例 metadata 和参考输入
- 判断问题属于：边界解释 / 初值 / 几何属性 / 结构物 / 动量项 / 网络耦合 / mixed-flow 路由
- 明确一个可实现的首修复点

### Phase 3: Align structure model with HEC-RAS crossing physics [in_progress]
- 把 bridge/culvert 从单 cell HTAB 代理升级为 crossing 对象
- 接入 near/far section、contraction/expansion 信息
- 保持 SI 单位、守恒、边界一致性
- 不注入任何 HEC-RAS results 字段作为求解输入

### Phase 4: Validate and document next blockers [pending]
- 复跑目标案例和必要回归
- 更新 findings/progress
- 明确剩余 blocked/gap，不夸大闭环状态

## Acceptance for this session
- 产出当前 unsteady 基线分布
- 至少完成 1 个首要修复并验证结果
- 对未完成案例给出基于物理类别的下一步路径
