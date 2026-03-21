# HydroClaude 涵洞求解器实现计划

生成日期: 2026-03-21
分析基准: FHWA HDS-5 第三版（2012）
当前分支: refactor-and-debug-water-network-simulation

---

## 1. 当前状态评估

### 1.1 代码分布现状

HydroClaude 中存在三套独立的涵洞实现，互不连通：

- `physics/structures/culvert.py`（629 行）：主物理计算引擎，声称实现 FHWA HDS-5，但与稳态求解器脱节
- `network/culvert_structure.py`（593 行）：管网涵洞/倒虹吸，支持多孔、高程，独立存在未接入主路径
- `web/backend/core/structures/culvert.py`（303 行）：Web 后端对标商业软件版本，仅供 Web 使用

### 1.2 主模块（physics/structures/culvert.py）技术评估

#### 入口控制（严重偏差）

当前使用简化孔口公式，而非 HDS-5 标准无量纲曲线方程：

    非淹没: Q = Cd * A * sqrt(2*g*H)
    淹没:   Q = Cd * A * sqrt(2*g*(H - D/2))  <- 公式错误

主要问题：
- HDS-5 入口控制使用 Form 1 和 Form 2 无量纲方程，不是孔口公式
- 仅 4 个离散 Cd 值（0.47~0.57），无法覆盖 HDS-5 至少 9 种进口配置
- 淹没判据 h >= 1.2D 及修正 H-D/2 均不符合 HDS-5 标准
- HDS-5 Form 2 正确公式为：H/D = c*(Q/A*D^0.5)^2 + Y - 0.5*S

#### 出口控制（中等偏差）

主要问题：
- 第 335 行 R_h 固定取满流断面（注释写明"assume full or nearly full"），部分流计算完全失效
- 未实现下游临界水深比较：正确出口边界应为 max(tailwater, critical_depth + z_outlet)
- 无涵洞内水面线推算（Standard Step Method）
- 迭代为简单 +-5% 乘法更新，极端条件下不稳定

#### 流态识别（严重缺失）

当前仅有 'inlet' / 'outlet' 两种标签，完全缺少 HDS-5 定义的 6 种物理流型（Type 1-6）。

#### 与稳态求解器的集成（严重缺陷）

physics/steady_saint_venant.py 的 SteadySaintVenantSystem（第 51 行 structures 参数）只接受
HydraulicStructure 闸门接口，完全没有涵洞内部边界处理路径。

这是 HEC-RAS Example 3/4 误差的根本原因：
- wse_mae = 0.50~0.54 m（门限 0.5 m）
- flow_rel_error = 139.99%（目标 <15%，差距约 10 倍）

### 1.3 network/culvert_structure.py 技术评估

功能相对完整：多孔并联（n_barrels）、进出口高程、弯头损失（n_bends/Ke_bends）、壅水反推（Newton 迭代）。

不足：
- 入口控制固定使用 Cd=0.62 孔口公式（_compute_inlet_control 第 267 行）
- 出口控制取满流面积，不随水深变化（_solve_outlet_control_iterative）
- 流态判断过于简化（classify_flow_regime：坡度 >0.02 即判陡坡）

---

## 2. HEC-RAS Example 3/4 具体参数需求

### 2.1 Example 3 — Single Culvert（TWINPIPE）

项目特征：
- 河段：Spring Creek，稳态回水，M1 型水面线，Froude < 0.02（充分亚临界）
- 10 个断面，代表流量 Q = 16.99 m3/s，下游水深 h = 2.4232 m
- 底坡 0.001554，河道 Manning n = 0.08，宽度约 91.6 m
- 几何文件（g02）含 1 个 inline structure，从文件名 TWINPIPE 判断为双管涵洞（n_barrels=2）

当前误差：
- flow_rel_error = 139.99%：涵洞未作内部边界，流量不受限制
- wse_mae = 0.501 m：壅水效应未传递至上游断面

所需功能：
1. 双管并联流量分配（n_barrels=2，相同涵洞）
2. 涵洞内部边界正确接入稳态水面线
3. 出口控制满流/非满流自适应
4. 混凝土管进口系数（对应 HDS-5 concrete pipe 系列）

### 2.2 Example 4 — Multiple Culverts（MULTCULV）

项目特征：
- 河段：Spring Creek Multiple Culverts，水文条件同 Example 3
- 几何标题"Multiple Culvert Geometry"，多种规格涵洞并列

误差情况：wse_mae = 0.542 m，比 Example 3 的 0.501 m 更大，
说明多涵洞并联的误差叠加效应明显。

所需功能：
1. 不同规格涵洞并联（按水头非均匀流量分配）
2. 不同涵底高程处理
3. 各涵洞独立控制类型判断
4. 总流量守恒约束下的联立求解

注意事项：两个 report.json 中 num_culverts=0 是 HEC-RAS HDF 提取的已知问题，
不代表案例无涵洞，需从 .g01 几何文件或 HDF 结构数据中读取真实涵洞几何参数。

---

## 3. 缺失功能清单（按优先级）

### P0 — 核心重建（阻塞性缺陷，当前结果不可信）

P0-1: HDS-5 标准入口控制方程（Form 1/Form 2 + 系数表）
  文件: physics/structures/culvert.py + 新建 physics/structures/hds5_coefficients.py
  影响: 入口控制流量计算完全错误

P0-2: 出口控制水力半径随深变化（部分流 R_h(y)）
  文件: CulvertGeometry 类新增 area_at_depth() 和 top_width_at_depth()
  影响: 非满流出口控制计算失效

P0-3: 下游临界水深边界条件
  文件: Culvert 类新增 critical_depth() 方法
  影响: 出口边界水深被低估

P0-4: 涵洞作为稳态求解器的内部边界条件
  文件: 新建 solvers/steady_culvert_solver.py + 集成层修改
  影响: Example 3/4 flow_error=140% 根因

### P1 — 重要功能（显著影响精度）

P1-1: 6 种流型（Type 1-6）识别与诊断（枚举类型 CulvertFlowType）
P1-2: 多孔并联求解器（相同涵洞 n_barrels / 不同涵洞 Newton 联立求解）
P1-3: 水面线推算（Standard Step）在涵洞内部
P1-4: HDS-5 入口系数完整表格（至少 9 组 K/M/c/Y）
P1-5: Brent 法替换乘法迭代（scipy.optimize.brentq）

### P2 — 优化/扩展（精度提升）

P2-1: 弯头损失（K_b 按 HDS-5 Table 2-2 查表）
P2-2: 拱形断面精确几何（当前为简化矩形近似）
P2-3: 正常水深求解器（normal_depth，用于 Type 1/2 判断）
P2-4: 三套实现统一重构（消除重复代码）
P2-5: 涵洞 Rating Curve 预计算缓存（多流量剖面提速）
P2-6: 进出口速度水头修正（精度约 1-3%）

---

## 4. 每项功能的实现方案

### 4.1 P0-1：HDS-5 标准入口控制方程

当前错误位置：culvert.py 第 240-290 行 _inlet_control 方法

错误形式：Q = Cd * A * sqrt(2*g*H)  （孔口公式，非 HDS-5 标准）

HDS-5 Form 1（非淹没入口，HW/D 约 < 1.0）：
  HW_i = D * (Q / (K * A * D^0.5))^(1/M)

HDS-5 Form 2（淹没入口，HW/D 约 > 1.5）：
  HW_i = D * (c * (Q / (A * D^0.5))^2 + Y - 0.5*S)

控制水头 = max(Form 1, Form 2)

新建文件 physics/structures/hds5_coefficients.py，
核心数据（来源：HDS-5 Third Edition, Appendix A Table A-1，需对照原文核实）：

  concrete_pipe_projecting:          K=0.0098, M=2.0, c=0.0398, Y=0.67
  concrete_pipe_headwall_square:     K=0.0078, M=2.0, c=0.0292, Y=0.74
  concrete_pipe_mitered:             K=0.0045, M=2.0, c=0.0317, Y=0.69
  concrete_pipe_groove_end_headwall: K=0.0018, M=2.5, c=0.0242, Y=0.83
  box_culvert_headwall_flared:       K=0.0083, M=1.5, c=0.0379, Y=0.69
  box_culvert_headwall_90deg:        K=0.0145, M=1.5, c=0.0317, Y=0.81
  cmp_projecting:                    K=0.0317, M=0.5, c=0.0249, Y=0.94

旧字符串别名（向后兼容）：
  square_edge     -> concrete_pipe_headwall_square
  groove_end      -> concrete_pipe_groove_end_headwall
  groove_headwall -> concrete_pipe_groove_end_headwall
  beveled         -> box_culvert_headwall_flared

重构后计算方法在 Culvert 类中定义，签名：

  def _inlet_control_hds5(self, Q: float) -> float:
      # 1. 查表根据 self.inlet_type 获取 K/M/c/Y
      # 2. Q_norm = Q / (A * D^0.5)
      # 3. HW_D_unsub = (Q_norm / K)^(1/M)
      # 4. HW_D_sub   = c * Q_norm^2 + Y - 0.5 * S
      # 5. return max(HW_D_unsub, HW_D_sub) * D

### 4.2 P0-2：出口控制水力半径随深变化

当前错误：culvert.py 第 335 行  R_h = self.geom.hydraulic_radius(D)（固定满流）

需在 CulvertGeometry 类新增两个方法：

  area_at_depth(y: float) -> float
    圆形：theta = 2*arccos(1 - 2*min(y,D)/D)
          A = (D^2/8)*(theta - sin(theta))
    矩形：A = width * min(y, height)

  top_width_at_depth(y: float) -> float
    圆形：T = 2 * sqrt(max(0, y*(D-y)))
    矩形：T = width（直到满流）

出口控制迭代修改（动态 R_h）：

  depth_avg = clip(h_downstream, 0.05*D, D)
  R_h    = self.geom.hydraulic_radius(depth_avg)
  A_flow = self.geom.area_at_depth(depth_avg)
  V      = Q_guess / A_flow
  h_f    = (n^2 * L * V^2) / R_h^(4/3)

### 4.3 P0-3：下游临界水深边界条件

HDS-5 规定出口有效控制水深（高程形式）：
  h_d = max(TW_elevation, y_c + z_outlet) - z_outlet

新增方法 Culvert.critical_depth(Q: float) -> float：
  二分法在 [1e-5*D, 0.999*D] 内求解 Q^2*T / (g*A^3) = 1

出口控制主方法修改：
  y_c = self.critical_depth(Q_guess)
  h_downstream_effective = max(h_downstream, y_c)

### 4.4 P0-4：涵洞作为稳态求解器的内部边界

根本问题：SteadySaintVenantSystem（steady_saint_venant.py 第 21、51 行）只接受
HydraulicStructure 闸门接口，涵洞无法注入。

推荐方案：在求解器外层（adapter/runner）实现分段推算，不改动 Newton 矩阵。

新建文件 solvers/steady_culvert_solver.py，定义标准接口：

  class CulvertInternalBoundary:
      def __init__(self, culvert: Culvert, n_barrels: int = 1): ...

      def compute_headwater(self, Q_total: float, tailwater_elevation: float) -> tuple[float, str]:
          # 返回 (上游水头高程, 控制类型)
          ...

      def compute_discharge(self, headwater_elevation: float, tailwater_elevation: float) -> float:
          # 给定上下游水位，返回总过涵流量
          ...

稳态水面线推算流程修改（integration 层，伪代码）：

  # 从下游向上游推算，遇到涵洞时：
  if 当前断面位置有 CulvertInternalBoundary:
      TW = 当前累积水面高程
      HW = culvert_boundary.compute_headwater(Q, TW)
      以 HW 为上游河段新的起始水面高程，继续推算

### 4.5 P1-1：6 种流型识别

新增枚举 CulvertFlowType（在 culvert.py 顶部）：

  TYPE_1: 入口控制，陡坡，出口自由
  TYPE_2: 入口控制，缓坡，出口淹没
  TYPE_3: 入口控制，入口淹没，出口自由
  TYPE_4: 出口控制，满流，进出口均淹没
  TYPE_5: 出口控制，满流，出口自由
  TYPE_6: 出口控制，部分流，下游淹没

判断逻辑依赖：HW_elevation, TW_elevation, is_inlet_control, critical_depth(Q), normal_depth(Q)
（normal_depth 需另行实现：Manning 均匀流，二分法求解）

### 4.6 P1-2：多孔并联求解器

相同涵洞（Example 3 双管）：Q_total = Q_single * n_barrels，在调用层处理即可。

不同涵洞并联（Example 4）—— 新增函数 solve_parallel_culverts()：
  约束：所有涵洞共用同一 HW 和 TW，总流量守恒
  算法：外层 Newton 迭代，内层对每个涵洞独立调用 compute_discharge，
        用数值 Jacobian（小扰动）更新 HW_guess

### 4.7 P1-5：Brent 法替换乘法迭代

当前问题：culvert.py 第 358-368 行简单 +-5% 乘法更新，收敛慢。

替换为 scipy.optimize.brentq（无需导数，保证收敛）：
  residual(Q) = _compute_H_required(Q, h_downstream) - h_upstream
  Q_sol = brentq(residual, 1e-12, Q_max, xtol=1e-7)


---

## 5. 预计工作量

### 工作量估算表

| 编号 | 功能 | 难度 | 预计工时 | 依赖项 |
|-----|------|------|---------|--------|
| P0-1 | HDS-5 入口控制方程 + 系数表 | 中 | 6h | 无 |
| P0-2 | 出口控制 R_h 随深变化 + 几何辅助方法 | 中 | 4h | 无 |
| P0-3 | 临界水深求解器 + 下游边界修正 | 中 | 4h | P0-2 |
| P0-4 | 涵洞内部边界接入稳态求解器 | 高 | 12h | P0-1~3 |
| P1-1 | 6 种流型识别 + 枚举类型 | 低 | 3h | P0-1~3 |
| P1-2 | 多孔并联求解器 | 中 | 5h | P0-1~3 |
| P1-3 | 涵洞内水面线推算（Standard Step） | 中 | 4h | P0-2/P0-3 |
| P1-4 | HDS-5 系数表完整化（全 9 组） | 低 | 3h | P0-1 |
| P1-5 | Brent 法替换乘法迭代 | 低 | 2h | P0-2 |
| P2-1 | 弯头损失 | 低 | 2h | P0-1~3 |
| P2-2 | 拱形断面精确几何 | 低 | 2h | 无 |
| P2-3 | 三套实现统一重构 | 中 | 6h | P0-1~3 |
| 合计 P0 | | | 26h | |
| 合计 P1 | | | 17h | |
| 合计 P2 | | | 10h | |
| 总计 | | | 约 53h | |

### 实施顺序建议

第一阶段 P0（约 2 工作日）：解决根本性物理错误
  Day 1: P0-1 + P0-2 + P0-3（物理方程重建，可独立测试）
  Day 2: P0-4（集成接口，解决 Example 3/4 主要误差）

第二阶段 P1（约 1.5 工作日）：功能完善
  Day 3: P1-1 + P1-2 + P1-5（流型识别、并联、迭代改进）
  Day 4 上午: P1-3 + P1-4 + 集成验证

第三阶段 P2（按需）：精度优化
  P2-1 + P2-2：较小改动，可随时插入
  P2-3：代码整合，建议独立排期（较大重构）

### 主要风险

风险 1（高）：P0-4 求解器集成
  SteadySaintVenantSystem 的 Newton 矩阵结构对涵洞的上下游水位跳跃结构不友好。
  涵洞产生的是分段边界（水位在涵洞位置不连续），不适合直接嵌入 Jacobian 矩阵。
  建议优先在 adapter/runner 外层用分段方法实现，确认精度后再评估是否嵌入矩阵。
  避免修改主求解器而引入回归风险。

风险 2（中）：HDS-5 系数录入
  系数表必须对照 HDS-5 Appendix A 原文核实，录入错误会导致系统性偏差。
  应建立独立验证测试（对照 HDS-5 图表中已知算例的 HW/D vs Q/AD^0.5 曲线）。

风险 3（中）：Example 3/4 涵洞几何参数未知
  当前 report.json 的 num_culverts=0 是 HDF 提取的已知问题，不代表无涵洞。
  需解析原始 HEC-RAS .g01 几何文件或 HDF 结构节点才能获取真实涵洞参数（直径、长度、进口类型）。
  当前修复可改善系统误差方向，但无法精确复现 HEC-RAS 绝对数值。

风险 4（低）：多涵洞 Newton 迭代收敛
  当各涵洞截面积差异悬殊时，外层 Newton 收敛可能变慢。
  需要专项调试初值估算策略和步长限制。

---

## 参考文献

1. FHWA (2012). Hydraulic Design of Highway Culverts, HDS 5, Third Edition. FHWA-HIF-12-026.
2. FHWA (2001). Hydraulic Design of Highway Culverts, FHWA-NHI-01-020.
3. HEC-RAS Hydraulic Reference Manual (2016), Chapter 6: Culvert Hydraulic Computations.
4. Chow, V.T. (1959). Open-Channel Hydraulics. McGraw-Hill.

---

文档生成时间: 2026-03-21
分析工具: HydroClaude Code Analysis Agent
