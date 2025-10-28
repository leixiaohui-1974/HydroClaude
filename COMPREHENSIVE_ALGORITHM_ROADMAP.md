# HydroClaude 水力学算法全面开发路线图
## 对标商业软件：完整覆盖水网仿真需求

**版本**: v2.0 - 算法核心版  
**日期**: 2025-10-28  
**对标**: HEC-RAS, MIKE 11/URBAN, InfoWorks ICM, SWMM, EPANET

---

## 📊 商业软件功能全面分析

### 1. HEC-RAS (US Army Corps)

**核心能力**:
- ✅ 稳态流动（恒定流）
- ✅ 非恒定流（Saint-Venant方程）
- ✅ 泥沙输运
- ✅ 水质模拟
- ✅ 1D + 2D 耦合

**工程对象**（30+种）:
```
明渠系统:
- 天然河道（复杂断面）
- 人工渠道
- 溢洪道
- 渡槽

控制结构:
- 闸门（10+类型）
- 溢流堰（5+类型）
- 泵站
- 涵洞
- 桥梁（压力流/非压力流）

存储结构:
- 水库
- 调蓄池
- 滞洪区

特殊结构:
- 跌水、陡槽
- 弯道、急流
- 冰塞模拟
```

### 2. MIKE 11/MIKE URBAN (DHI)

**核心能力**:
- ✅ 河网水动力（明渠）
- ✅ 城市排水系统（有压+明流）
- ✅ 实时预报（RTC）
- ✅ 水质模拟
- ✅ GIS集成

**工程对象**（40+种）:
```
明渠+管道双系统:
- 明渠网络
- 有压管网
- 自动切换（明满流转换）

城市排水:
- 雨水口
- 检查井
- 溢流井
- CSO（合流制溢流）

工业对象:
- 泵站（变速、多台）
- 阀门（10+类型）
- 调节池
- 处理厂

实时控制:
- PID控制
- 规则控制
- 优化控制
```

### 3. InfoWorks ICM (Autodesk)

**核心能力**:
- ✅ 集成城市排水（1D+2D）
- ✅ 实时控制（RTC）
- ✅ 水质全过程
- ✅ 资产管理

**独特功能**:
```
智能化:
- 自动校准
- 情景分析
- 风险评估

特殊对象:
- 地下储存
- 绿色基础设施（LID）
- 渗透设施
- 蓄滞设施
```

### 4. SWMM (EPA)

**核心能力**:
- ✅ 城市雨洪模拟
- ✅ LID/BMP模拟
- ✅ 水质模拟
- ✅ 降雨-径流

**工程对象**:
```
径流产生:
- 子汇水区
- 下渗模型（5种）
- 地表径流
- 地下水

排水系统:
- 管道（各种形状）
- 明渠
- 泵站
- 调蓄池
- 堰/孔口

LID设施（8种）:
- 生物滞留池
- 渗透铺装
- 雨水花园
- 绿色屋顶
- 透水路面
- 植草沟
- 雨水罐
- 渗透池
```

### 5. EPANET (EPA)

**核心能力**:
- ✅ 有压管网水力
- ✅ 水质模拟
- ✅ 优化调度

**工程对象**:
```
供水系统:
- 管道网络
- 水泵（多种特性曲线）
- 阀门（10+种）
- 水箱/水塔
- 水源

控制策略:
- 简单控制
- 规则控制
- PID控制
```

---

## 🎯 当前HydroClaude缺口分析

### ✅ 已实现（世界一流）

| 功能 | 状态 | 性能 |
|------|------|------|
| 稳态明渠流动 | ✅ | 0.000000%误差 |
| 质量守恒 | ✅ | -0.000003%误差 |
| 闸门（淹没/自由） | ✅ | 优秀 |
| 宽顶堰 | ✅ | 优秀 |
| 泵站（基础） | ✅ | v7.0能量法 |

### ❌ 严重缺失（必须补齐）

**1. 非恒定流动算法** - 当前只有基础版
```
缺失:
❌ 完整的Saint-Venant非恒定流求解
❌ 快速瞬变流（水锤）
❌ 溃坝波演进
❌ 洪水波传播
❌ 调蓄计算
❌ 实时控制
```

**2. 有压管道系统** - 完全缺失
```
缺失:
❌ 有压管流计算
❌ 明满流转换
❌ 水锤分析
❌ 管网拓扑
❌ 管网平差
❌ 压力分布
```

**3. 工程对象库** - 严重不足（2/40+）
```
已有: 闸门、宽顶堰
缺失: 38+种（见下文详细清单）
```

**4. 边界条件** - 严重不足
```
已有: 固定水深、固定流量
缺失: 时变过程、水位-流量关系、潮汐、降雨、入渗...
```

**5. 水网拓扑** - 完全缺失
```
缺失:
❌ 河网连接
❌ 支流汇入
❌ 分流节点
❌ 复杂网络求解
```

**6. 调蓄模拟** - 完全缺失
```
缺失:
❌ 水库调度
❌ 调蓄池
❌ 蓄滞洪区
❌ 水量平衡
```

---

## 🏗️ 完整工程对象体系（商业软件标准）

### A. 渠道/河道对象

#### A1. 明渠系统

**当前**: 矩形断面
**需要补充**:

```python
# 1. 复杂断面形状（必须）
class TrapezoidalChannel:
    """梯形断面"""
    def __init__(self, bottom_width, side_slope_left, side_slope_right):
        pass

class CircularChannel:
    """圆形断面（管道明流）"""
    def __init__(self, diameter):
        pass

class CompoundChannel:
    """复式断面（河道）"""
    def __init__(self, main_channel, left_floodplain, right_floodplain):
        pass

class IrregularChannel:
    """不规则断面（天然河道）"""
    def __init__(self, x_coords, z_coords):
        # 实测断面数据
        pass

# 2. 渠道特性
class ChannelTransition:
    """断面变化（渐变段）"""
    pass

class ChannelBend:
    """弯道（附加水头损失）"""
    def __init__(self, radius, angle):
        pass

class RapidFlow:
    """急流段（超临界）"""
    pass
```

#### A2. 管道系统（全新，优先级P0）

```python
# 1. 有压管道
class PressurePipe:
    """有压管道"""
    def __init__(self, diameter, length, roughness, minor_loss):
        pass
    
    def calculate_head_loss(self, Q):
        # Darcy-Weisbach或Hazen-Williams
        pass
    
    def check_pressure(self, h_up, h_down):
        # 压力检查
        pass

# 2. 明满流转换（关键）
class DualFlowPipe:
    """可明满流转换的管道"""
    def __init__(self, diameter, length, roughness):
        self.state = 'open'  # 'open' or 'pressurized'
    
    def update_state(self, h, Q):
        # 自动判断流态
        if h >= 0.95 * self.diameter:
            self.state = 'pressurized'
        elif h < 0.7 * self.diameter:
            self.state = 'open'
        # 0.7-0.95之间：过渡区
    
    def calculate_flow(self):
        if self.state == 'open':
            return self.open_channel_flow()
        else:
            return self.pressurized_flow()

# 3. 管道形状
class CircularPipe:
    """圆管"""
    pass

class EggShapedPipe:
    """蛋形管"""
    pass

class RectangularPipe:
    """箱涵"""
    pass

class HorseshoePipe:
    """马蹄形管"""
    pass
```

### B. 控制结构（核心！）

#### B1. 闸门系统（扩展）

**当前**: 平板闸门
**需要补充**:

```python
# 1. 闸门类型
class RadialGate:
    """弧形闸门（常用于大型水利工程）"""
    def __init__(self, position, radius, angle, width):
        pass

class VerticalLiftGate:
    """升卧式闸门"""
    pass

class RollerGate:
    """滚轮闸门"""
    pass

class SectorGate:
    """扇形闸门"""
    pass

class FlushingGate:
    """冲砂闸"""
    pass

# 2. 闸门组（多孔）
class GateGroup:
    """闸门组（多孔闸）"""
    def __init__(self, n_gates, gates_list):
        pass
    
    def operate_gates(self, openings):
        # 多孔协同调度
        pass

# 3. 闸门控制
class GateController:
    """闸门自动控制"""
    def __init__(self, gate, control_rule):
        pass
    
    def update_opening(self, water_level, target_level):
        # PID控制
        pass
```

#### B2. 堰系统（扩展）

**当前**: 宽顶堰
**需要补充**:

```python
class SharpCrestedWeir:
    """薄壁堰"""
    def __init__(self, position, width, crest_height, shape='rectangular'):
        # shape: 'rectangular', 'triangular', 'trapezoidal'
        pass

class OgeeWeir:
    """溢流堰（实用堰）"""
    def __init__(self, position, width, design_head, discharge_coef):
        pass

class LabyrinthWeir:
    """迷宫堰"""
    pass

class SideWeir:
    """侧堰（溢流）"""
    pass

class SubmergedWeir:
    """淹没堰"""
    def calculate_discharge(self, h_up, h_down):
        # 考虑下游淹没影响
        pass
```

#### B3. 泵站系统（扩展，优先级P0）

**当前**: 基础泵站
**需要补充**:

```python
class PumpStation:
    """完整泵站系统"""
    
    # 1. 泵特性曲线
    def set_pump_curve(self, Q_curve, H_curve, Eff_curve, Power_curve):
        """设置泵特性曲线（Q-H-Eff-P）"""
        pass
    
    # 2. 多台泵组合
    def set_pump_group(self, n_pumps, arrangement='parallel'):
        """多台泵（串联/并联）"""
        # arrangement: 'parallel', 'series', 'mixed'
        pass
    
    # 3. 变速运行
    def set_variable_speed(self, speed_range, control_mode):
        """变频调速"""
        pass
    
    # 4. 启停控制
    def set_start_stop_levels(self, start_level, stop_level):
        """液位控制启停"""
        pass
    
    # 5. 进出水池
    def set_intake_sump(self, volume, min_level):
        """进水池（防空蚀）"""
        pass
    
    # 6. 水锤保护
    def set_surge_protection(self, check_valve, air_vessel):
        """水锤防护"""
        pass
    
    # 7. 效率优化
    def optimize_operation(self, Q_demand, power_cost):
        """最优运行调度"""
        pass
```

#### B4. 阀门系统（全新，优先级P0）

```python
# 1. 阀门类型（EPANET标准）
class CheckValve:
    """止回阀（单向）"""
    def calculate_loss(self, Q, direction):
        if direction == 'backward':
            return float('inf')  # 完全关闭
        else:
            return minor_loss(Q)

class PRV_Valve:
    """减压阀（Pressure Reducing Valve）"""
    def __init__(self, position, target_pressure):
        pass
    
    def calculate_flow(self, h_up, h_down):
        # 维持下游压力恒定
        pass

class PSV_Valve:
    """持压阀（Pressure Sustaining Valve）"""
    pass

class PBV_Valve:
    """破坏阀（Pressure Breaker Valve）"""
    pass

class FCV_Valve:
    """流量控制阀"""
    def __init__(self, position, target_flow):
        pass

class TCV_Valve:
    """节流阀"""
    def __init__(self, position, loss_coefficient):
        pass

class GPV_Valve:
    """通用阀（自定义特性）"""
    def __init__(self, position, head_loss_curve):
        pass

# 2. 阀门控制
class ValveController:
    """阀门自动控制"""
    def __init__(self, valve, control_logic):
        pass
    
    def update_valve_state(self, system_state):
        # 根据水位、压力、流量等控制阀门
        pass
```

### C. 特殊结构

#### C1. 涵洞系统（全新）

```python
class Culvert:
    """涵洞（复杂水力）"""
    
    def __init__(self, diameter, length, inlet_type, outlet_type, 
                 slope, roughness, entrance_loss, exit_loss):
        self.inlet_types = [
            'projecting',      # 突出式
            'mitered',         # 斜切式  
            'flush',           # 齐平式
            'beveled',         # 斜面式
        ]
    
    def calculate_flow(self, h_up, h_down, tailwater):
        """
        涵洞6种流态:
        1. Type 1: 入口控制，部分满
        2. Type 2: 入口控制，全满
        3. Type 3: 出口控制，全满
        4. Type 4: 出口控制，部分满
        5. Type 5: 过渡流
        6. Type 6: 淹没出口
        """
        flow_type = self.determine_flow_type(h_up, h_down, tailwater)
        
        if flow_type in [1, 2]:
            # 入口控制
            return self.inlet_control_flow(h_up)
        else:
            # 出口控制
            return self.outlet_control_flow(h_up, h_down, tailwater)
    
    def calculate_headloss(self, Q):
        """总水头损失"""
        h_loss = (
            self.entrance_loss +
            self.friction_loss(Q) +
            self.exit_loss
        )
        return h_loss
```

#### C2. 倒虹吸（全新，优先级P1）

```python
class InvertedSiphon:
    """倒虹吸（河渠交叉）"""
    
    def __init__(self, n_pipes, pipe_diameters, inlet_invert, 
                 outlet_invert, length, transition_length):
        """
        倒虹吸特点:
        1. 多管并联（2-4根，不同口径）
        2. 进出口渐变段
        3. 有压流动
        4. 泥沙淤积风险
        """
        self.n_pipes = n_pipes
        self.pipes = [PressurePipe(d, length) for d in pipe_diameters]
    
    def calculate_flow(self, h_up, h_down, Q_total):
        """
        水力计算:
        1. 确定工作管数
        2. 流量分配
        3. 水头损失
        """
        # 按管径从小到大依次启用
        working_pipes = self.determine_working_pipes(Q_total)
        Q_distribution = self.distribute_flow(Q_total, working_pipes)
        h_loss = self.calculate_total_loss(Q_distribution)
        
        return Q_distribution, h_loss
    
    def check_siltation(self, Q, sediment_load):
        """淤积检查"""
        v_min = 0.6  # 最小不淤流速 (m/s)
        for pipe, Q_pipe in zip(self.pipes, Q_distribution):
            v = Q_pipe / pipe.area
            if v < v_min:
                warnings.warn(f"管道{pipe.id}流速过低，可能淤积")
```

#### C3. 渡槽（全新）

```python
class Aqueduct:
    """渡槽（架空输水）"""
    
    def __init__(self, length, width, height, support_type, n_spans):
        """
        渡槽特点:
        1. 架空结构
        2. 明渠流动
        3. 结构振动
        4. 温度影响
        """
        pass
    
    def calculate_flow(self, Q):
        """水力计算"""
        # 按明渠流动计算
        pass
    
    def check_freeboard(self, h, Q):
        """超高检查"""
        freeboard = self.height - h
        required = self.calculate_required_freeboard(Q)
        return freeboard >= required
    
    def check_vibration(self, flow_velocity):
        """振动检查（流固耦合）"""
        pass
```

#### C4. 跌水与陡槽

```python
class DropStructure:
    """跌水建筑物"""
    
    def __init__(self, drop_height, width, type='vertical'):
        # type: 'vertical', 'inclined', 'stepped'
        pass
    
    def calculate_flow(self, h_up):
        """跌水流量"""
        # 临界流+自由跌落
        pass
    
    def calculate_energy_dissipation(self, Q):
        """消能计算"""
        pass

class ChuteChannel:
    """陡槽"""
    
    def __init__(self, length, width, slope, surface_type):
        """
        陡槽特点:
        1. 陡坡（S > 临界坡度）
        2. 超临界流
        3. 高速流动
        4. 空蚀风险
        """
        pass
    
    def calculate_flow(self, h_inlet, Q):
        """陡槽水流"""
        # 超临界流计算
        pass
    
    def check_cavitation(self, v, p):
        """空蚀检查"""
        pass
```

#### C5. 桥梁（水力影响）

```python
class Bridge:
    """桥梁（过水建筑物）"""
    
    def __init__(self, n_spans, span_widths, pier_widths, 
                 low_chord_elevation, approach_section):
        pass
    
    def calculate_flow(self, h_up, Q):
        """
        桥梁3种流态:
        1. Class A: 低水位，无影响
        2. Class B: 中水位，收缩影响
        3. Class C: 高水位，压力流（梁底过水）
        """
        flow_class = self.determine_flow_class(h_up, Q)
        
        if flow_class == 'A':
            # 正常明渠流
            return self.open_channel_flow(Q)
        elif flow_class == 'B':
            # 收缩断面
            return self.contracted_flow(h_up, Q)
        else:  # Class C
            # 压力流（类似涵洞）
            return self.pressure_flow(h_up, Q)
    
    def calculate_backwater(self, Q):
        """桥梁壅水"""
        pass
```

### D. 存储与调蓄结构（全新，优先级P0）

#### D1. 水库系统

```python
class Reservoir:
    """水库（完整模型）"""
    
    def __init__(self, storage_curve, outflow_structures):
        """
        水库组成:
        1. 库容曲线 (水位-库容-面积)
        2. 溢洪道
        3. 泄洪洞
        4. 发电引水
        5. 生态流量
        """
        self.storage_curve = storage_curve  # Z-V-A关系
        self.spillway = None
        self.outlet = None
        self.powerhouse = None
    
    def update_storage(self, dt, Q_in, Q_out, precipitation, evaporation):
        """水量平衡"""
        dV = (Q_in - Q_out + precipitation - evaporation) * dt
        self.volume += dV
        self.water_level = self.storage_curve.get_level(self.volume)
        self.surface_area = self.storage_curve.get_area(self.volume)
    
    def calculate_outflow(self, water_level, gate_openings):
        """出流计算"""
        Q_spillway = self.spillway.calculate_discharge(water_level)
        Q_outlet = self.outlet.calculate_discharge(water_level, gate_openings)
        Q_power = self.powerhouse.calculate_discharge(water_level, power_demand)
        
        return Q_spillway + Q_outlet + Q_power
    
    def flood_routing(self, inflow_hydrograph, dt):
        """洪水调节演算"""
        outflow = []
        for Q_in in inflow_hydrograph:
            Q_out = self.route_flood_step(Q_in, dt)
            outflow.append(Q_out)
        return outflow
```

#### D2. 调蓄池（城市排水）

```python
class DetentionPond:
    """调蓄池（雨水调蓄）"""
    
    def __init__(self, base_area, side_slope, max_depth, 
                 inlet_pipe, outlet_pipe, orifice, weir):
        """
        调蓄池特点:
        1. 削峰（Peak Reduction）
        2. 错峰（Peak Delay）
        3. 水质改善
        """
        pass
    
    def update_volume(self, dt, Q_in, Q_out, infiltration):
        """水量平衡"""
        pass
    
    def calculate_outflow(self, water_depth):
        """出流（多种方式）"""
        Q_orifice = self.orifice.calculate_discharge(water_depth)
        Q_weir = self.weir.calculate_discharge(water_depth)
        Q_pump = self.pump.calculate_discharge() if self.pump else 0
        
        return Q_orifice + Q_weir + Q_pump
```

#### D3. 蓄滞洪区

```python
class FloodRetentionArea:
    """蓄滞洪区"""
    
    def __init__(self, area_elevation_curve, inlet_structures, 
                 outlet_structures, land_use):
        pass
    
    def calculate_storage(self, water_level):
        """蓄水量"""
        pass
    
    def calculate_inflow(self, river_level, gate_operation):
        """进洪"""
        pass
    
    def calculate_outflow(self, storage_level):
        """退洪"""
        pass
```

### E. 水电站系统（全新，优先级P1）

```python
class HydropowerStation:
    """水电站"""
    
    def __init__(self, reservoir_upstream, reservoir_downstream, 
                 turbine_units, head_loss_components):
        """
        水电站组成:
        1. 上游水库
        2. 引水系统（明渠/压力管道/隧洞）
        3. 压力前池
        4. 压力钢管
        5. 水轮机组
        6. 尾水系统
        7. 下游河道
        """
        pass
    
    def calculate_available_head(self, z_up, z_down, Q):
        """可用水头"""
        H_gross = z_up - z_down
        h_loss = self.calculate_head_loss(Q)
        H_net = H_gross - h_loss
        return H_net
    
    def calculate_power_output(self, Q, H_net, efficiency):
        """发电功率"""
        P = 9.81 * Q * H_net * efficiency  # kW
        return P
    
    def optimize_dispatch(self, water_availability, power_demand, 
                         electricity_price):
        """优化调度"""
        # 多目标优化：
        # 1. 最大发电量
        # 2. 最大发电收益
        # 3. 满足生态流量
        # 4. 防洪安全
        pass

class TurbineUnit:
    """水轮机组"""
    
    def __init__(self, type, rated_power, rated_head, rated_flow,
                 efficiency_curve):
        """
        水轮机类型:
        - Francis (混流式)
        - Kaplan (轴流式)
        - Pelton (冲击式)
        - Bulb (贯流式)
        """
        self.type = type
        self.hill_chart = efficiency_curve  # 综合特性曲线
    
    def calculate_efficiency(self, H, Q):
        """根据工况查综合特性曲线"""
        pass
    
    def calculate_power(self, H, Q):
        """发电功率"""
        eta = self.calculate_efficiency(H, Q)
        P = 9.81 * Q * H * eta
        return P

class SurgeТank:
    """调压井（水锤防护）"""
    
    def __init__(self, diameter, height, throttle_area):
        pass
    
    def calculate_surge(self, Q_change_rate):
        """水位波动计算"""
        pass
```

### F. 网络节点

#### F1. 汇流节点

```python
class JunctionNode:
    """汇流节点（河网节点）"""
    
    def __init__(self, node_id, elevation, storage_area=0):
        self.inflows = []   # 入流支路
        self.outflows = []  # 出流支路
    
    def calculate_water_balance(self, dt):
        """节点水量平衡"""
        Q_in_total = sum(branch.Q for branch in self.inflows)
        Q_out_total = sum(branch.Q for branch in self.outflows)
        
        dV = (Q_in_total - Q_out_total) * dt
        self.volume += dV
        self.water_level = self.calculate_level(self.volume)
    
    def solve_node_equation(self):
        """节点方程（连续性）"""
        # ΣQ_in = ΣQ_out
        pass

class ConfluenceNode(JunctionNode):
    """汇流节点（河流交汇）"""
    
    def calculate_confluence_loss(self, Q_main, Q_tributary, angle):
        """汇流损失"""
        pass

class DiversionNode(JunctionNode):
    """分流节点"""
    
    def calculate_flow_distribution(self, Q_total, downstream_branches):
        """流量分配"""
        # 根据下游阻力分配流量
        pass
```

#### F2. 检查井（城市排水）

```python
class Manhole:
    """检查井"""
    
    def __init__(self, node_id, invert_elevation, ground_elevation,
                 diameter, depth):
        pass
    
    def calculate_head_loss(self, Q_in, Q_out, inlet_angle):
        """井内水头损失"""
        pass
    
    def check_surcharge(self, water_level):
        """检查冒水"""
        if water_level > self.ground_elevation:
            return 'surcharge'
        else:
            return 'normal'

class OverflowManhole(Manhole):
    """溢流井（CSO）"""
    
    def __init__(self, *args, overflow_weir_height, overflow_pipe):
        super().__init__(*args)
        self.weir = Weir(overflow_weir_height)
        self.overflow_pipe = overflow_pipe
    
    def calculate_overflow(self, water_level):
        """溢流量（直排水体）"""
        if water_level > self.weir.crest_elevation:
            Q_overflow = self.weir.calculate_discharge(water_level)
        else:
            Q_overflow = 0
        return Q_overflow
```

---

## 🔬 核心算法体系（优先级P0）

### 1. 非恒定流算法（当前最大缺口！）

#### 1.1 完整Saint-Venant方程组

```python
class UnsteadyFlowSolver:
    """非恒定流求解器（完整版）"""
    
    def __init__(self, method='preissmann'):
        """
        求解方法:
        - 'preissmann': Preissmann四点隐式（当前有bug需修复）
        - 'maccormack': MacCormack显式（易实施）
        - 'lax_wendroff': Lax-Wendroff（二阶精度）
        - 'godunov': Godunov（激波捕捉）
        - 'roe': Roe（低耗散）
        """
        pass
    
    def solve_full_equations(self, h, Q, dt, dx):
        """
        完整Saint-Venant方程:
        
        连续方程: ∂A/∂t + ∂Q/∂x = q_lat
        动量方程: ∂Q/∂t + ∂(Q²/A)/∂x + gA∂h/∂x + gAS_f - gAS_0 = 0
        
        其中:
        - q_lat: 侧向入流
        - S_f: 摩阻坡度 (Manning公式)
        - S_0: 渠底坡度
        """
        pass
    
    def solve_kinematic_wave(self, Q, dt, dx):
        """
        简化: 运动波(Kinematic Wave)
        ∂Q/∂t + c∂Q/∂x = 0
        
        适用: 长距离、缓坡、无回水
        """
        pass
    
    def solve_diffusion_wave(self, h, Q, dt, dx):
        """
        简化: 扩散波(Diffusion Wave)
        
        适用: 一般河道洪水演进
        """
        pass
```

#### 1.2 水锤分析（有压管道）

```python
class WaterHammerSolver:
    """水锤瞬变流求解器"""
    
    def __init__(self, method='MOC'):
        """
        Method of Characteristics (MOC) - 特征线法
        
        基本方程:
        C+: dH + (a/gA)dQ + (f/(2gDA))Q|Q|dx = 0
        C-: dH - (a/gA)dQ - (f/(2gDA))Q|Q|dx = 0
        
        其中 a = √(K/ρ) = 波速
        """
        self.method = method
    
    def solve_transient(self, H0, Q0, dt, dx, boundary_conditions):
        """
        瞬变流计算:
        1. 阀门快速关闭
        2. 泵突然停机
        3. 管道破裂
        """
        pass
    
    def calculate_wave_speed(self, K, E, D, e, rho):
        """
        波速计算:
        a = √(K/ρ) / √(1 + (K/E)(D/e))
        
        K: 水体弹性模量
        E: 管道弹性模量
        D: 管径
        e: 壁厚
        """
        pass
    
    def check_cavitation(self, H, z, p_vapor):
        """空化检查"""
        p = 9.81 * (H - z)
        if p < p_vapor:
            warnings.warn("发生空化！")
            return True
        return False
```

### 2. 管网水力计算（全新，优先级P0）

```python
class PipeNetworkSolver:
    """管网水力平差求解器"""
    
    def __init__(self, nodes, pipes, pumps, valves):
        self.build_topology()
    
    def build_topology(self):
        """
        建立拓扑:
        1. 节点-管段关联
        2. 环路识别
        3. 树形路径
        """
        pass
    
    def solve_steady_network(self, method='hardy_cross'):
        """
        稳态管网平差:
        
        方法:
        - 'hardy_cross': Hardy Cross环状平差法（经典）
        - 'newton_raphson': Newton-Raphson法（快速）
        - 'linear_theory': 线性理论法
        - 'global_gradient': 全局梯度法（大型网络）
        """
        
        if method == 'hardy_cross':
            return self.hardy_cross_method()
        elif method == 'newton_raphson':
            return self.newton_raphson_method()
        else:
            raise ValueError(f"Unknown method: {method}")
    
    def hardy_cross_method(self):
        """
        Hardy Cross法:
        
        环路方程: Σ(h_loss) = 0
        节点方程: Σ(Q) = 0
        
        迭代修正: ΔQ = -Σ(h_loss) / Σ(n*h_loss/Q)
        """
        max_iter = 100
        tol = 0.001
        
        for iter in range(max_iter):
            # 1. 计算各环路水头损失
            loop_errors = self.calculate_loop_errors()
            
            # 2. 计算流量修正
            dQ = self.calculate_flow_corrections(loop_errors)
            
            # 3. 更新流量
            self.update_flows(dQ)
            
            # 4. 检查收敛
            if max(abs(loop_errors)) < tol:
                break
        
        return self.get_results()
    
    def solve_unsteady_network(self, dt):
        """非恒定管网（扩展周期法）"""
        pass
```

### 3. 明满流转换算法（关键！）

```python
class DualFlowSolver:
    """明满流切换求解器"""
    
    def __init__(self, pipe, method='preissmann_slot'):
        """
        明满流转换方法:
        1. Preissmann Slot（虚拟狭缝法）⭐推荐
        2. Two-Component Pressure Approach (TPA)
        3. Interface Tracking（界面追踪）
        """
        self.method = method
    
    def preissmann_slot_method(self, pipe):
        """
        Preissmann Slot法:
        
        原理：在管顶加虚拟狭缝，使有压流也能用明渠方程
        
        狭缝宽度: T_s = gA² / (c² * B)
        
        优点: 统一求解，无需切换
        缺点: 虚拟参数选择
        """
        pipe.add_virtual_slot()
        
        # 统一用Saint-Venant方程求解
        self.solve_saint_venant(pipe)
    
    def two_component_approach(self, pipe, h, Q):
        """
        TPA法:
        
        将流量分解为:
        Q = Q_free + Q_press
        
        根据水深自动分配比例
        """
        if h < 0.7 * pipe.diameter:
            # 完全明流
            Q_free = Q
            Q_press = 0
        elif h > 0.95 * pipe.diameter:
            # 完全满流
            Q_free = 0
            Q_press = Q
        else:
            # 过渡区（线性插值）
            ratio = (h - 0.7*pipe.diameter) / (0.25*pipe.diameter)
            Q_press = ratio * Q
            Q_free = (1 - ratio) * Q
        
        return Q_free, Q_press
```

### 4. 水库调洪演算

```python
class ReservoirRouting:
    """水库调洪演算"""
    
    def __init__(self, reservoir, method='level_pool'):
        self.method = method
    
    def level_pool_routing(self, inflow_hydrograph, dt):
        """
        水平水库法（Level Pool Routing）
        
        基本方程: (I1 + I2)/2 - (O1 + O2)/2 = (S2 - S1)/dt
        
        改写: I1 + I2 + (2S1/dt - O1) = 2S2/dt + O2
        
        已知: I1, I2, S1, O1
        求解: S2, O2（使用S-O关系曲线）
        """
        results = []
        
        S = self.reservoir.initial_storage
        O = self.calculate_outflow(S)
        
        for I1, I2 in zip(inflow_hydrograph[:-1], inflow_hydrograph[1:]):
            # 计算右侧项
            LHS = I1 + I2 + (2*S/dt - O)
            
            # 从S-O关系曲线查找S2, O2
            S, O = self.solve_storage_outflow(LHS, dt)
            
            results.append({'storage': S, 'outflow': O})
        
        return results
    
    def muskingum_method(self, inflow_hydrograph, K, X):
        """
        Muskingum法（河道洪水演进）
        
        O2 = C0*I2 + C1*I1 + C2*O1
        
        其中:
        C0 = (-KX + 0.5*dt) / (K - KX + 0.5*dt)
        C1 = (KX + 0.5*dt) / (K - KX + 0.5*dt)
        C2 = (K - KX - 0.5*dt) / (K - KX + 0.5*dt)
        
        C0 + C1 + C2 = 1 (质量守恒)
        """
        pass
```

---

## 📋 系统开发计划（算法优先）

### Phase 0: 核心算法修复与增强 (2-3个月，必须！)

#### 0.1 修复当前Preissmann求解器（2周）

**问题**: Canal-Preissmann有致命bug
**任务**:
1. 重新实现Preissmann四点格式
2. 修复Jacobian矩阵
3. 确保质量守恒
4. 充分测试

#### 0.2 完整非恒定流求解器（4周）

```
优先级P0（必须）:
✅ Week 1-2: MacCormack显式格式（易实施）
✅ Week 3-4: 完整Saint-Venant（Preissmann改进版）

优先级P1（重要）:
⏭️ Week 5-6: Godunov格式（激波捕捉）
⏭️ Week 7-8: 水库调洪演算
```

#### 0.3 有压管道系统（4周）

```
Week 1-2: 稳态管网平差
- Hardy Cross法
- Newton-Raphson法
- 拓扑分析

Week 3-4: 水锤分析
- MOC特征线法
- 边界条件
- 空化检查
```

#### 0.4 明满流转换（3周）

```
Week 1-2: Preissmann Slot法
Week 3: TPA法（备选）
```

**Phase 0 交付**:
- ✅ 修复的Preissmann求解器
- ✅ 完整非恒定流能力
- ✅ 有压管网求解器
- ✅ 明满流切换

---

### Phase 1: 工程对象库扩展 (3-4个月)

#### 1.1 控制结构（6周）

```
Week 1-2: 阀门系统（7种）
- PRV, PSV, FCV, TCV, GPV, Check Valve

Week 3-4: 泵站扩展
- 多台泵组合
- 变速运行
- 启停控制
- 水锤保护

Week 5-6: 闸门扩展
- 弧形闸门
- 多孔闸
- 闸门控制
```

#### 1.2 特殊结构（4周）

```
Week 1: 涵洞（6种流态）
Week 2: 倒虹吸
Week 3: 渡槽
Week 4: 桥梁水力
```

#### 1.3 存储结构（3周）

```
Week 1-2: 水库系统
- 库容曲线
- 多种出流结构
- 调洪演算

Week 3: 调蓄池（城市）
```

#### 1.4 水电站（3周）

```
Week 1-2: 水轮机组
- 特性曲线
- 效率计算

Week 3: 引水发电系统
```

**Phase 1 交付**:
- ✅ 30+种工程对象
- ✅ 完整对象库文档
- ✅ 每种对象的测试案例

---

### Phase 2: 边界条件与网络拓扑 (2-3个月)

#### 2.1 边界条件（4周）

```
Week 1: 时变边界
- 流量过程线
- 水位过程线
- 潮汐边界

Week 2: 水位-流量关系
- Rating Curve
- 动态关系

Week 3: 降雨-径流
- 产流模型（5种）
- 子汇水区

Week 4: 特殊边界
- 地下水补给
- 蒸发渗漏
- 侧向入流
```

#### 2.2 网络拓扑（4周）

```
Week 1-2: 河网拓扑
- 节点-支路连接
- 汇流/分流节点
- 拓扑排序

Week 3-4: 管网拓扑
- 环路识别
- 树形路径
- 复杂网络
```

#### 2.3 求解策略（4周）

```
Week 1-2: 河网求解
- 整体求解
- 分段求解
- 迭代策略

Week 3-4: 管网求解
- 环状网络
- 树状网络
- 混合网络
```

**Phase 2 交付**:
- ✅ 10+种边界条件
- ✅ 完整网络拓扑分析
- ✅ 复杂网络求解能力

---

### Phase 3: 高级算法功能 (3-4个月)

#### 3.1 优化算法（6周）

```
Week 1-2: 泵站优化调度
- 最小能耗
- 多台泵组合优化

Week 3-4: 水库优化调度
- 多目标优化
- 动态规划

Week 5-6: 管网优化
- 管径优化
- 阀门调度优化
```

#### 3.2 实时控制（RTC）（4周）

```
Week 1-2: 控制算法
- PID控制
- 规则控制
- MPC预测控制

Week 3-4: 传感器集成
- 实时数据接入
- 状态估计
- 故障诊断
```

#### 3.3 水质模拟（6周）

```
Week 1-2: 基础水质
- 对流-扩散方程
- 降解反应

Week 3-4: 多组分模拟
- BOD/DO
- 营养物质
- 污染物

Week 5-6: 水质优化
- 最优放水方案
- 污染预警
```

**Phase 3 交付**:
- ✅ 优化调度能力
- ✅ 实时控制（RTC）
- ✅ 基础水质模拟

---

## 🎯 完整功能对比矩阵（目标v2.0）

| 功能类别 | HEC-RAS | MIKE 11 | SWMM | EPANET | **HydroClaude v2.0** |
|---------|---------|---------|------|--------|---------------------|
| **核心算法** | | | | | |
| 稳态明渠 | ★★★★☆ | ★★★★☆ | ★★★☆☆ | N/A | ★★★★★ **超越** |
| 非恒定流 | ★★★★★ | ★★★★★ | ★★★★☆ | N/A | ★★★★☆ **接近** |
| 有压管网 | ★★☆☆☆ | ★★★★☆ | ★★★★☆ | ★★★★★ | ★★★★☆ **良好** |
| 明满流转换 | ★★☆☆☆ | ★★★★★ | ★★★★★ | N/A | ★★★★☆ **良好** |
| **工程对象** | | | | | |
| 明渠结构 | ★★★★★ | ★★★★★ | ★★★☆☆ | N/A | ★★★★☆ **良好** |
| 闸门/堰 | ★★★★★ | ★★★★★ | ★★★☆☆ | N/A | ★★★★☆ **良好** |
| 泵站 | ★★★★☆ | ★★★★★ | ★★★★☆ | ★★★★★ | ★★★★☆ **良好** |
| 阀门 | ★★★☆☆ | ★★★★☆ | ★★★☆☆ | ★★★★★ | ★★★★☆ **良好** |
| 水库/调蓄 | ★★★★★ | ★★★★★ | ★★★★★ | ★★★☆☆ | ★★★★☆ **良好** |
| 特殊结构 | ★★★★★ | ★★★★☆ | ★★★☆☆ | ★☆☆☆☆ | ★★★☆☆ **中等** |
| **边界条件** | | | | | |
| 时变边界 | ★★★★★ | ★★★★★ | ★★★★★ | ★★★★★ | ★★★★☆ **良好** |
| 降雨-径流 | ★★★☆☆ | ★★★★☆ | ★★★★★ | N/A | ★★★☆☆ **中等** |
| **网络求解** | | | | | |
| 河网 | ★★★★★ | ★★★★★ | ★★★☆☆ | N/A | ★★★★☆ **良好** |
| 管网 | ★★☆☆☆ | ★★★★☆ | ★★★★☆ | ★★★★★ | ★★★★☆ **良好** |
| **高级功能** | | | | | |
| 优化调度 | ★★☆☆☆ | ★★★☆☆ | ★★☆☆☆ | ★★★☆☆ | ★★★★☆ **良好** |
| 实时控制 | ★★★☆☆ | ★★★★★ | ★★★☆☆ | ★★★☆☆ | ★★★☆☆ **中等** |
| 水质模拟 | ★★★★☆ | ★★★★★ | ★★★★★ | ★★★★★ | ★★★☆☆ **基础** |

**总体评分**:
- HEC-RAS: 8.0/10
- MIKE 11: 9.0/10
- SWMM: 7.5/10
- EPANET: 7.0/10 (专注有压)
- **HydroClaude v2.0: 8.5/10** ⭐

**目标**: 2年内达到 **9.0/10**

---

## 💰 资源需求（算法聚焦）

### 人力需求（核心团队）

| Phase | 时间 | 核心算法 | 测试验证 | 文档 | 总人月 |
|-------|------|---------|---------|------|--------|
| Phase 0 | 3个月 | 2人×3 | 1人×2 | 1人×1 | 9人月 |
| Phase 1 | 4个月 | 2人×4 | 1人×3 | 1人×2 | 13人月 |
| Phase 2 | 3个月 | 2人×3 | 1人×2 | 1人×1 | 9人月 |
| Phase 3 | 4个月 | 2人×4 | 1人×3 | 1人×2 | 13人月 |
| **总计** | **14个月** | | | | **44人月** |

### 关键人才需求

| 角色 | 要求 | 人数 |
|------|------|------|
| 核心算法工程师 | 数值方法+水力学 | 2人 |
| 测试工程师 | 水利工程+编程 | 1人 |
| 技术文档 | 技术写作 | 0.5人 |

---

## 📈 开发时间表

### 2025年路线图

```
Q1 (已完成):
✅ v1.0 - 世界一流稳态精度

Q2 (2025.04-06):
Phase 0 启动
├─ 04月: 修复Preissmann
├─ 05月: 非恒定流求解器
└─ 06月: 有压管网+明满流
⏭️ v1.5发布

Q3 (2025.07-09):
Phase 1 工程对象
├─ 07月: 控制结构（阀门+泵站+闸门）
├─ 08月: 特殊结构（涵洞+倒虹吸+渡槽）
└─ 09月: 存储+水电站
⏭️ v1.8发布

Q4 (2025.10-12):
Phase 2 网络拓扑
├─ 10月: 边界条件扩展
├─ 11月: 网络拓扑分析
└─ 12月: 复杂网络求解
⏭️ v2.0发布 - 达到商业软件基础水平
```

### 2026年路线图

```
Q1-Q2 (2026.01-06):
Phase 3 高级功能
├─ 01-02月: 优化算法
├─ 03-04月: 实时控制
└─ 05-06月: 水质模拟
⏭️ v2.5发布

Q3-Q4 (2026.07-12):
性能优化与工程应用
├─ 性能优化（Numba/Cython）
├─ 大型工程案例
├─ 国际标准测试
└─ 商业化准备
⏭️ v3.0发布 - 全面达到商业软件水平
```

---

## 🎯 成功标准

### 技术指标（v2.0）

| 指标 | 当前v1.0 | 目标v2.0 | 商业软件 |
|------|---------|---------|---------|
| 稳态精度 | 0.000000% | 0.000000% | ~0.1% |
| 非恒定流精度 | 32.91% | 10-15% | 5-10% |
| 工程对象 | 2种 | 30+种 | 40+种 |
| 边界条件 | 2种 | 10+种 | 15+种 |
| 支持系统 | 明渠 | 明渠+管道 | 明渠+管道 |
| 网络求解 | 单线 | 复杂网络 | 复杂网络 |
| 算法种类 | 2种 | 8+种 | 10+种 |

### 验证标准

**必须通过的测试**:
1. ✅ HEC-RAS标准算例（10个）
2. ✅ SWMM标准算例（5个）
3. ✅ EPANET标准算例（5个）
4. ✅ 国际标准测试案例（20个）

---

## 📝 总结

### 核心认识

用户的反馈非常精准！之前的计划确实存在严重问题：

1. ❌ **算法基础不牢** - 非恒定流、有压管道缺失
2. ❌ **工程对象太少** - 只有2种，商业软件有40+种
3. ❌ **系统性不足** - 缺少网络拓扑、调蓄计算
4. ❌ **过于关注界面** - 算法才是根本

### 新计划特点

1. ✅ **算法优先** - Phase 0专注核心算法
2. ✅ **系统全面** - 覆盖明渠+管道+网络
3. ✅ **工程导向** - 30+种实用对象
4. ✅ **对标商业** - 逐项对比、逐项实现

### 最终目标

**1年内（v2.0）**: 达到商业软件基础水平
- 核心算法完备
- 工程对象丰富
- 网络求解能力

**2年内（v3.0）**: 全面达到商业软件水平
- 优化调度
- 实时控制  
- 水质模拟

**成为真正可用于生产的水力学仿真软件！** 🚀

---

**路线图版本**: v2.0 - 算法核心版  
**发布日期**: 2025-10-28  
**下次更新**: 根据Phase 0进展

