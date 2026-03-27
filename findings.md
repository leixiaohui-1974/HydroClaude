# Bridge HTAB Findings

## HEC-RAS HTAB 机制 (from user investigation)
1. Geometric Preprocessor 预处理桥梁为 TW-Q-HW 曲线族
2. UNET 运行时查表插值，不实时求解结构方程
3. Post-Processor 用 steady 方程重算详细结果（可能与 UNET 略有差异）

## Beaver Creek Bridge 输入参数 (SI)
- Bridge RS: 5.4, US/DS: 5.41/5.39
- US distance: 9.144m, bridge width: 12.192m
- Low chord (deck_elev): 65.745m (215.7 ft)
- Deck weir coef: 2.6 (imperial), max submergence: 0.95
- 9 piers, width 0.381m each (1.25 ft), stations 143.256-192.024m
- Pier elevations: 61.783-65.745m (202.7-215.7 ft)
- Submerged Inlet Cd: 0.34
- Submerged Inlet-Outlet Cd: 0.7

## 现有代码基础
- `StructureHTAB`: 只消费 HTAB 数据，有 compute_hw() 和 compute_hw_and_derivatives()
- `_solve_bridge_energy()`: 4断面 energy method，已实现，但绑定 SteadyProfileSolver 实例
- `_solve_bridge_momentum()`: momentum method，本案例不用
- `_split_deck_overtopping_flow()`: deck weir 分流，可复用
- `_bridge_face_area()`: 桥孔有效面积计算，可复用

## 关键设计决策
- Phase 1 需要把 bridge energy solver 解耦成纯函数，传入断面几何而非索引
- HTAB 生成器的 TW/Q 范围需要从 HTAB 参数推断（或手动指定）
