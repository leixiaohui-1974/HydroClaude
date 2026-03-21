# HEC-RAS 涵洞 HDF 数据结构分析报告

生成时间: 2026-03-21  
作者: CHS Agent Teams 编码专家（claude-sonnet-4-6）  
数据来源: HEC-RAS 6.6, h5py 3.16.0 直接读取

---

## 1. 分析范围

分析了以下 6 个 HEC-RAS 涵洞案例的 HDF 文件：

| 案例名称 | HDF 文件 | 涵洞类型 | 管道数 |
|----------|----------|----------|--------|
| Example 3 - Single Culvert (TWINPIPE) | TWINPIPE.p01.hdf | Circular 圆管 | 2 |
| Example 4 - Multiple Culverts (MULTCULV) | MULTCULV.p01.hdf | Box + Circular | 4 |
| Culvert Hydraulics (Beav_Culvert) | Beav_Culvert.p01.hdf | Box 箱涵 | 6 |
| ConSpan Culvert | ConSpan.p01.hdf | ConSpan Arch 拱形 | 1 |
| Culverts with Flap Gates | CulvertFlap.p01.hdf | Circular + 拍门 | 1 |
| Lateral Structure with Culverts | LatWeirCulverts.p01.hdf | Circular 侧向 | 1 |

所有 HDF 文件根属性 Units System = US Customary（英制）。  
换算系数：ft → m 乘以 0.3048；cfs → m3/s 乘以 0.028316846592。

---

## 2. HDF 文件类型

HEC-RAS 生成两类 HDF：

- 几何 HDF（）：存储涵洞几何参数（形状、尺寸、损失系数等）
- 计划 HDF（）：含几何副本 + 计算结果（权威来源）

---

## 3. 核心几何路径

### 3.1 结构主表

路径:   
形状:  结构化数组  

涵洞关键字段：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| Type | S16 | Culvert（内联）或 Lateral（侧向） |
| River / Reach / RS | S16/S8 | 河流/河段/里程桩号 |
| Upstream Distance | f4 | 进口距上游断面距离（ft） |
| Culvert Groups | i4 | 涵洞组数量 |
| Culverts Flap Gates | i4 | 拍门数量（>0 有拍门） |
| Weir Coef | f4 | 溢流堰系数 |

### 3.2 涵洞组参数表（核心）

路径:   
形状:  结构化数组  
一个结构可含多个涵洞组，每个组代表一种形状/尺寸的管涵。

| 字段名 | 类型 | 说明 | 典型值 |
|--------|------|------|--------|
| Structure ID | i4 | 所属结构索引 | 0 |
| Name | S12 | 组名 | Circular, Box |
| Shape | i4 | 断面形状编码 | 1=圆管, 2=箱涵, 9=拱形 |
| Shape Name | S32 | 形状文本 | Circular, Box, Conspan Arch |
| Chart | i4 | FHWA 进水口图表编号 | 1, 8, 10, 61 |
| Chart Desc | S64 | 进水口图表描述 | 1 - Concrete Pipe Culvert |
| Scale | i4 | 进水口形式子类 | 1, 2, 3 |
| Scale Desc | S64 | 形式描述 | Square edge entrance with headwall |
| Rise | f4 | 涵洞高度/圆管直径（ft） | 6.0 ft 圆管; 3.0 ft 箱涵高 |
| Span | f4 | 涵洞宽度/圆管直径（ft） | 6.0 ft 圆管; 5.0 ft 箱涵宽 |
| Length | f4 | 涵洞长度（ft） | 50.0 ft = 15.24 m |
| US Distance | f4 | 进口距辅助断面距离（ft） | 5.0 ft |
| Mann Top | f4 | 顶部 Manning n（满流） | 0.013 |
| Mann Bottom | f4 | 底部 Manning n（低水） | 0.013; 0.030（ConSpan 底） |
| Depth for Bottom Mann | f4 | 切换阈值深度（ft） | 0.0; 0.5（ConSpan） |
| Depth Blocked | f4 | 堵塞深度（ft） | 0.0 |
| Entrance Loss | f4 | 进口损失系数 Ke | 0.5（方头）, 0.2（倒角）, 0.4（喇叭） |
| Exit Loss | f4 | 出口损失系数 Kx | 1.0（所有案例均为 1.0） |
| US Invert | f4 | 进口底坎高程（ft） | 25.1 ft |
| DS Invert | f4 | 出口底坎高程（ft） | 25.0 ft |
| Barrels | i4 | 并联管道数（孔数） | 2, 6 |

### 3.3 管道横站坐标

路径:   
形状:  结构化数组  

| 字段名 | 类型 | 说明 |
|--------|------|------|
| Structure ID | i4 | 所属结构 |
| Culvert Group ID | i4 | 所属涵洞组 |
| Name | S32 | 管道名，如 Barrel #1 |
| US Station | f4 | 进口横站坐标（ft） |
| DS Station | f4 | 出口横站坐标（ft） |
| Default Centerline | u1 | 默认中心线标志 |

---

## 4. 形状编码（Shape Code）实测汇总

| Shape 编码 | Shape Name | 说明 |
|-----------|------------|------|
| 1 | Circular | 圆形管涵，Rise = Span = 直径 |
| 2 | Box | 矩形箱涵，Rise = 高，Span = 宽 |
| 3 | Pipe Arch | 管拱（本批未出现） |
| 4 | Ellipse | 椭圆形（本批未出现） |
| 8 | High Profile Arch | 高拱（本批未出现） |
| 9 | Conspan Arch | ConSpan 拱形，Rise=高，Span=宽 |

---

## 5. FHWA 图表与进水口形式实测对照

| Chart | 描述 | 形状 |
|-------|------|------|
| 1 | Concrete Pipe Culvert | Circular |
| 8 | Flared wingwalls | Box |
| 10 | 90 deg headwall; Chamfered or beveled inlet | Box |
| 61 | ConSpan Span/Rise approx 4:1 | Conspan Arch |

| Scale | 描述 | Ke |
|-------|------|----|
| 1 | Square edge entrance with headwall | 0.5 |
| 1 | Wingwall flared 30 to 75 deg | 0.4 |
| 2 | Inlet edges beveled 0.5 in at 45 degrees | 0.2 |
| 3 | 90 deg wing wall angle | 0.5 |

Ke 值直接存于 Entrance Loss 字段，Chart/Scale 仅供记录进口类型。

---

## 6. 稳态结果路径

### 6.1 断面水面线、能量线、流量

Results/Steady/Output/Output Blocks/Base Output/Steady Profiles/
  Cross Sections/Water Surface   shape=(N_profiles, N_xs)  dtype=float32  单位: ft
  Cross Sections/Energy Grade    shape=(N_profiles, N_xs)  dtype=float32  单位: ft
  Cross Sections/Flow            shape=(N_profiles, N_xs)  dtype=float32  单位: cfs
  Profile Names                  shape=(N_profiles,)       dtype=S16

### 6.2 节点信息（含涵洞标识）

Results/Steady/Output/Geometry Info/Node Info
  shape=(N_nodes,)  dtype=S132
  格式: River Reach RS Type
  涵洞节点后缀 CV，如: Spring Creek Culvrt Reach 20.237 CV
  普通断面后缀 XS

### 6.3 实测数据（TWINPIPE Example 3，英制）

Profile: 5 yr / 10 yr / 25 yr  (Q = 250 / 400 / 600 cfs)
涵洞节点 RS=20.237（Node 5）前后出现明显跌水（体现壅水效应）：
  5 yr  水面（ft）: ... 30.511(US XS) | 涵洞 CV | 29.931(DS XS) ...
  10 yr 水面（ft）: ... 32.500(US XS) | 涵洞 CV | 31.301(DS XS) ...
  25 yr 水面（ft）: ... 34.318(US XS) | 涵洞 CV | 32.132(DS XS) ...

---

## 7. 非稳态结果路径

### 7.1 涵洞专用时间序列

路径模板（非稳态）:

Results/Unsteady/Output/Output Blocks/Base Output/Unsteady Time Series/
  Culverts/{River} {Reach} {RS}/Culvert Variables
  shape=(N_timesteps, 3)  dtype=float32
  Dataset 属性 Variable_Unit: [Flow, cfs, Stage HW, ft, Stage TW, ft]
    col 0: Flow      cfs   涵洞流量
    col 1: Stage HW  ft    进水口水面高程
    col 2: Stage TW  ft    出水口水面高程

实测样例（Culvert Hydraulics，英制，前 3 行）：

[500.0, 210.458, 209.623]   t=10FEB1999 00:00:00
[696.2, 210.798, 209.912]   t=10FEB1999 01:00:00
[971.4, 211.224, 210.289]   t=10FEB1999 02:00:00

### 7.2 断面时间序列

Results/Unsteady/Output/Output Blocks/Base Output/Unsteady Time Series/
  Cross Sections/Water Surface  dtype=float32  单位: ft
  Cross Sections/Flow           dtype=float32  单位: cfs
  Time Date Stamp               例: 10FEB1999 00:00:00

---

## 8. 拍门（Flap Gate）说明

Geometry/Structures/Attributes 中 Culverts Flap Gates > 0 表示含拍门（单向阀）。  
HDF 中仅存储拍门计数，无独立几何参数子组。  
具体拍门参数需从 .gNN 文本几何文件补充解析。

---

## 9. 现有适配器支持情况

文件: /z/research/hydroclaude/integration/hec_ras_adapter.py

| 功能 | 状态 | 位置 |
|------|------|------|
| 桥梁参数提取 | 已实现 | _extract_bridge_params() L1165 |
| 结构存在性检测 | 已实现 | _detect_structures() L1343 |
| has_structures 标志 | 已实现 | 检测 Geometry/Structures/Culvert Groups |
| 涵洞几何参数提取 | 未实现 | 无对应函数 |
| 涵洞时间序列读取 | 未实现 | 无对应逻辑 |
| HECRASResultSummary.culverts | 未定义 | 仅有 bridges 字段 |

---

## 10. HDF 字段 → HydroClaude Culvert 求解器参数映射

文件: /z/research/hydroclaude/physics/structures/culvert.py

| HDF 字段（英制） | 换算 | HydroClaude 参数 | 说明 |
|-----------------|------|-----------------|------|
| Rise x 0.3048 | ft→m | CulvertGeometry.height 或 diameter | 圆管时 Rise=Span=diameter |
| Span x 0.3048 | ft→m | CulvertGeometry.width | 箱涵宽度 |
| Length x 0.3048 | ft→m | CulvertGeometry.length | 涵洞长度 |
| (US Invert - DS Invert) / Length | 推算 | CulvertGeometry.slope | 不直接存储 |
| US Invert x 0.3048 | ft→m | CulvertGeometry.invert_elevation | 进口底坎高程 |
| Mann Top | 直接 | Culvert.manning_n | 满流 n，通常 0.013 |
| Entrance Loss | 直接 | Culvert.entrance_loss_coef (Ke) | 直接使用 |
| Exit Loss | 直接 | Culvert.exit_loss_coef | 通常 1.0 |
| Barrels | 整数 | 并联孔数 | 单管流量 = 总流量 / N |
| Shape 编码 | 映射 | CulvertGeometry.shape | 见下方映射 |

Shape 编码映射：

SHAPE_CODE_MAP = {
    1: circular,     # Circular
    2: rectangular,  # Box
    9: arch          # Conspan Arch
}

---

## 11. 后续实现 TODO

1. 在 hec_ras_adapter.py 新增 _extract_culvert_params(hdf, lf) 函数
   - 读取: Geometry/Structures/Culvert Groups/Attributes + Barrels/Attributes
   - 输出: list[dict]，每条对应一个涵洞组，字段全部换算为 SI

2. 在 HECRASResultSummary 添加字段: culverts: list[dict] | None = None

3. 新增 SHAPE_CODE_MAP 常量

4. 处理多管并联（Barrels > 1）：总流量等分或并联建模

5. 读取非稳态涵洞时间序列
   路径: Results/Unsteady/Output/.../Culverts/{name}/Culvert Variables

6. 拍门参数补充：从 .gNN 文本文件提取开闭高程

---

## 12. 数据完整性评估

| 参数 | HDF 可读 | 路径 |
|------|---------|------|
| 断面形状 Shape | 是 | Culvert Groups/Attributes.Shape |
| 高 x 宽（Rise x Span） | 是 | Culvert Groups/Attributes |
| 涵洞长度 | 是 | Culvert Groups/Attributes.Length |
| 进出口底坎高程 | 是 | US Invert / DS Invert |
| Manning n | 是 | Mann Top / Mann Bottom |
| 进口损失系数 Ke | 是 | Entrance Loss |
| 出口损失系数 | 是 | Exit Loss |
| 并联孔数 | 是 | Barrels |
| 管道横站坐标 | 是 | Barrels/Attributes.US Station |
| FHWA 图表编号 | 是 | Chart / Scale |
| 涵洞坡度 | 否（需推算） | = (US Invert - DS Invert) / Length |
| 拍门具体参数 | 否（仅计数） | 需从 .gNN 文本文件补充 |
| 翼墙几何 | 否 | 仅 Scale 编号，无几何数据 |
