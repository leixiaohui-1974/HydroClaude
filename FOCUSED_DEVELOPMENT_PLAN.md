# HydroClaude 聚焦算法的完整开发计划

**版本**: v3.0 - 算法聚焦版  
**日期**: 2025-10-28  
**核心认识**: **项目已有丰富对象库，关键是完善核心算法**

---

## 🎯 核心发现

### 项目现状重新评估

**✅ 好消息（远超预期）**:
- ✅ 已有**25+种工程对象**（不是2种！）
- ✅ 已有**5种断面类型**（完整）
- ✅ 已有**10+种控制结构**（闸门、堰、阀门、泵站）
- ✅ 已有**水库、水电站系统**（完整）
- ✅ 已有**河网、管网拓扑**（基础框架）
- ✅ 已有**倒虹吸、管道、水轮机**

**⚠️ 关键问题（算法缺陷）**:
- ❌ Preissmann求解器有bug（**质量非守恒+279%**）
- ❌ 非恒定流能力不足（Dam Break误差32.91%）
- ❌ 明满流转换缺失（无法模拟城市排水）
- ❌ 有压管网未集成到主求解器
- ❌ 已有对象缺少充分测试和文档

### 核心认识

**不是缺对象，是缺算法和集成！**

**真正需要的**:
1. ✅ 修复核心算法bug
2. ✅ 完善非恒定流求解
3. ✅ 实施明满流转换
4. ✅ 集成已有对象到统一框架
5. ✅ 充分测试和文档化

---

## 🏗️ 六大核心算法体系

### 1. 明渠非恒定流算法（当前最大缺口！）

#### 1.1 完整Saint-Venant方程组求解器

**现状**:
- ⚠️ Preissmann四点隐式格式有bug
- ⚠️ 显式格式（Euler/RK）精度不足

**需要实施**:

```python
class FullSaintVenantSolver:
    """完整Saint-Venant方程组求解器"""
    
    def __init__(self, method='preissmann_fixed'):
        """
        支持方法:
        1. preissmann_fixed: 修复的Preissmann格式（P0优先级）
        2. maccormack: MacCormack显式格式（P1）
        3. lax_wendroff: Lax-Wendroff二阶格式（P1）
        4. beam_warming: Beam-Warming隐式格式（P2）
        """
        pass
    
    def solve_conservative_form(self, U, dt, dx):
        """
        守恒型方程:
        ∂U/∂t + ∂F/∂x = S
        
        其中:
        U = [A, Q]ᵀ
        F = [Q, Q²/A + gI₁]ᵀ
        S = [0, gI₂ - gAS_f]ᵀ
        
        I₁ = ∫h dB (压力积分)
        I₂ = ∫h dz_b (底坡积分)
        """
        pass
    
    def solve_non_conservative_form(self, h, Q, dt, dx):
        """
        非守恒型方程:
        ∂h/∂t + u∂h/∂x + h∂u/∂x = 0
        ∂u/∂t + u∂u/∂x + g∂h/∂x = g(S₀ - S_f)
        """
        pass
```

**关键: 修复Preissmann的3个bug**:

```python
def fixed_preissmann_scheme(self):
    """
    修复的Preissmann四点隐式格式
    
    原bug:
    1. ❌ 连续方程离散不一致（混用中点和节点）
    2. ❌ Jacobian矩阵不完整
    3. ❌ 最小流量/水深添加质量
    
    修复:
    1. ✅ 统一使用中点离散
    2. ✅ 完整Jacobian（所有偏导数）
    3. ✅ 物理限制（不添加质量）
    """
    # 连续方程（中点，时间加权）
    # (A_{i+1}^{n+1} - A_{i+1}^n)/dt + theta*(Q_{i+1}^{n+1} - Q_i^{n+1})/dx
    #                                + (1-theta)*(Q_{i+1}^n - Q_i^n)/dx = 0
    
    # 动量方程（中点，时间加权）
    # 类似处理，确保所有项一致
    pass
```

#### 1.2 洪水演进算法

```python
class FloodRoutingSolver:
    """洪水演进求解器"""
    
    def muskingum_cunge(self, inflow, dx, dt, S0, n, B):
        """
        Muskingum-Cunge法（可变参数）
        
        优点:
        - 物理参数（不需要率定）
        - 基于Saint-Venant简化
        - 计算快速
        
        参数自动计算:
        K = dx / c  (波速)
        X = 0.5 * (1 - Q/(B*S0*c*dx))
        """
        pass
    
    def level_pool_routing(self, reservoir, inflow, dt):
        """
        水平水库法
        
        (I1 + I2)/2 - (O1 + O2)/2 = (S2 - S1)/dt
        """
        pass
```

#### 1.3 快速瞬变流（水锤）

```python
class WaterHammerSolver:
    """水锤特征线法求解器"""
    
    def solve_MOC(self, pipes, dt, wave_speed):
        """
        Method of Characteristics
        
        C+特征线: dx/dt = u + a
        C-特征线: dx/dt = u - a
        
        相容方程:
        C+: dH + (a/gA)dQ + (f/2gDA)Q|Q|dx = 0
        C-: dH - (a/gA)dQ - (f/2gDA)Q|Q|dx = 0
        """
        pass
    
    def boundary_conditions(self):
        """
        边界条件:
        - 定水头水库
        - 阀门（快速关闭）
        - 泵（突然停机）
        - 调压井
        - 空气罐
        """
        pass
```

**实施时间**: 6-8周

---

### 2. 有压管网算法（完整实现）

#### 2.1 稳态管网平差

```python
class PipeNetworkSolver:
    """完整管网平差求解器"""
    
    def __init__(self, method='newton_raphson'):
        """
        方法:
        1. hardy_cross: Hardy-Cross法（已有基础）
        2. newton_raphson: 牛顿法（推荐，快速收敛）
        3. linear_theory: 线性理论法
        4. global_gradient: 全局梯度法（大型网络）
        """
        pass
    
    def newton_raphson_method(self, nodes, pipes):
        """
        Newton-Raphson法求解管网
        
        节点方程: Σ Q = 0 (连续性)
        管段方程: h_i - h_j = h_loss(Q_ij) (能量)
        
        组装Jacobian:
        J[i,j] = ∂F_i/∂x_j
        
        Newton迭代:
        J * Δx = -F
        x^{k+1} = x^k + Δx
        """
        pass
    
    def solve_with_pumps_valves(self, pumps, valves):
        """
        考虑泵站和阀门的管网
        
        泵: h_pump = h(Q) (泵特性曲线)
        阀门: h_valve = K*Q² (阻力特性)
        """
        pass
```

#### 2.2 非恒定管网（扩展周期法）

```python
class UnsteadyPipeNetwork:
    """非恒定管网求解器"""
    
    def solve_extended_period(self, time_horizon, dt, demand_pattern):
        """
        扩展周期模拟（EPS）
        
        应用:
        - 24小时供水模拟
        - 泵站优化调度
        - 水箱充放水
        
        方法:
        - 准稳态假设（每个dt内稳态）
        - 水箱水位动态更新
        - 泵站/阀门状态切换
        """
        results = []
        
        for t in np.arange(0, time_horizon, dt):
            # 1. 更新需水量
            demands = self.get_demands(t, demand_pattern)
            
            # 2. 稳态求解
            steady_result = self.solve_steady_network(demands)
            
            # 3. 更新水箱水位
            for tank in self.tanks:
                tank.update_volume(dt, steady_result)
            
            # 4. 检查泵站/阀门控制逻辑
            for pump in self.pumps:
                pump.check_control_logic(tank.level)
            
            results.append(steady_result)
        
        return results
```

**实施时间**: 4-5周

---

### 3. 明满流转换算法（关键技术！）

```python
class OpenPressurizedFlowSolver:
    """明满流统一求解器"""
    
    def __init__(self, method='preissmann_slot'):
        """
        方法:
        1. preissmann_slot: Preissmann虚拟狭缝法（推荐）⭐
        2. TPA: 双组分法
        3. interface_tracking: 界面追踪法
        """
        self.method = method
    
    def preissmann_slot_method(self, pipe):
        """
        Preissmann Slot法（虚拟狭缝）
        
        原理:
        在圆管顶部加虚拟狭缝，使满管流也能用明渠方程
        
        关键:
        1. 狭缝宽度计算
           T_s = g*A² / (c² * B)
           
           其中:
           A: 满管时过水面积
           B: 管顶宽度
           c: 压力波速（有压流）
        
        2. 统一方程
           明流区: 标准Saint-Venant
           满流区: 带虚拟狭缝的Saint-Venant
           
        3. 自动转换
           h < 0.95*D: 明流
           h > 0.95*D: 自动加狭缝
        
        优点:
        - 无需判断切换
        - 统一求解框架
        - 数值稳定
        
        缺点:
        - 虚拟参数选择
        - 压力波速需要估计
        """
        
        # 1. 计算狭缝宽度
        A_full = np.pi * (pipe.D / 2)**2
        c_wave = self.estimate_wave_speed(pipe)  # ~1000-1400 m/s
        T_s = self.g * A_full**2 / (c_wave**2 * pipe.D)
        
        # 2. 修正断面参数
        if h > 0.95 * pipe.D:
            # 加狭缝
            A = A_full + T_s * (h - pipe.D)
            B = T_s  # 水面宽度=狭缝宽度
        else:
            # 正常明流
            A = pipe.compute_area(h)
            B = pipe.compute_width(h)
        
        # 3. 用Saint-Venant求解（统一）
        return self.solve_saint_venant(A, B, ...)
    
    def compute_wave_speed(self, pipe, fluid_properties):
        """
        压力波速:
        a = √(K/ρ) / √(1 + (K/E)*(D/e)*C)
        
        K: 液体体积模量（水: 2.1 GPa）
        E: 管材弹性模量
        D: 管径
        e: 壁厚
        C: 约束系数
        """
        K = 2.1e9  # 水的体积模量 (Pa)
        E = pipe.elastic_modulus  # 管材模量
        D = pipe.diameter
        e = pipe.wall_thickness
        rho = fluid_properties.density
        
        # 简化Joukowsky公式
        a = np.sqrt(K / rho) / np.sqrt(1 + (K/E) * (D/e))
        
        return a
```

**实施时间**: 3-4周

---

### 4. 复杂网络拓扑求解

```python
class HybridNetworkSolver:
    """混合网络求解器（明渠+管道）"""
    
    def __init__(self, canals, pipes, nodes, structures):
        """
        网络组成:
        - canals: 明渠列表
        - pipes: 管道列表  
        - nodes: 节点列表（汇合、分流、水库等）
        - structures: 控制结构（闸门、泵站、阀门等）
        """
        self.topology = self.build_topology(canals, pipes, nodes)
    
    def build_topology(self):
        """
        建立拓扑:
        1. 节点-支路关联矩阵
        2. 环路识别（管网部分）
        3. 树形路径（河网部分）
        4. 分层排序（上下游关系）
        """
        pass
    
    def solve_coupled_system(self, dt):
        """
        耦合求解明渠+管道系统
        
        策略:
        1. 分区求解
           - 明渠区: Saint-Venant
           - 管道区: Hardy-Cross或Newton
        
        2. 迭代耦合
           - 交界节点: 水位/流量传递
           - 迭代至收敛
        
        3. 时间推进
           - 明渠: 显式或隐式
           - 管道: 准稳态或瞬变流
        """
        
        for t in time_steps:
            converged = False
            iteration = 0
            
            while not converged:
                # 1. 求解明渠部分
                for canal in self.canals:
                    canal.step(dt)
                
                # 2. 求解管道部分
                pipe_results = self.solve_pipe_network()
                
                # 3. 更新耦合节点
                for node in self.coupling_nodes:
                    # 传递水位/流量
                    node.update_boundary()
                
                # 4. 检查收敛
                residual = self.compute_coupling_residual()
                converged = residual < tolerance
                iteration += 1
        
        return results
```

**实施时间**: 4-5周

---

### 5. 水库群联合调度算法

```python
class CascadeReservoirScheduler:
    """梯级水库联合调度"""
    
    def __init__(self, reservoirs, river_network, optimization_config):
        """
        梯级水库系统:
        - 多个串联水库
        - 河道连接
        - 区间入流
        - 多目标优化
        """
        pass
    
    def optimize_multi_objective(self, objectives, constraints, horizon):
        """
        多目标优化调度
        
        目标:
        1. 最大发电量
        2. 最小弃水
        3. 满足防洪安全
        4. 保证生态流量
        5. 兼顾供水需求
        
        约束:
        1. 水位约束
        2. 出力约束
        3. 下泄流量约束
        4. 水量平衡
        
        算法:
        - 动态规划（DP）
        - 逐步优化算法（POA）
        - 粒子群算法（PSO）
        - 遗传算法（GA）
        """
        pass
    
    def flood_control_dispatch(self, forecast_inflow, current_storage):
        """
        防洪调度
        
        策略:
        1. 预泄腾库（提前降低水位）
        2. 拦洪削峰（减小下游洪峰）
        3. 错峰调度（延迟洪峰时间）
        """
        pass
```

**实施时间**: 4-6周

---

### 6. 实时控制算法（RTC）

```python
class RealTimeController:
    """实时控制器"""
    
    def __init__(self, control_objects, sensors, control_rules):
        """
        控制对象:
        - 闸门（开度控制）
        - 泵站（启停、变速）
        - 阀门（开关、调节）
        
        传感器:
        - 水位计
        - 流量计
        - 压力表
        
        控制策略:
        - 规则控制（If-Then）
        - PID控制
        - MPC预测控制
        """
        pass
    
    def rule_based_control(self, current_state):
        """
        规则控制
        
        示例:
        IF water_level > target + threshold:
            THEN open_gate(amount)
        
        IF water_level < target - threshold:
            THEN close_gate(amount)
        """
        actions = []
        
        for rule in self.rules:
            if rule.check_condition(current_state):
                action = rule.get_action()
                actions.append(action)
        
        return actions
    
    def pid_control(self, setpoint, current_value, dt):
        """
        PID控制
        
        u(t) = K_p*e + K_i*∫e dt + K_d*de/dt
        
        应用:
        - 水位控制
        - 流量控制
        - 压力控制
        """
        error = setpoint - current_value
        
        # 比例项
        P = self.K_p * error
        
        # 积分项
        self.integral += error * dt
        I = self.K_i * self.integral
        
        # 微分项
        derivative = (error - self.last_error) / dt
        D = self.K_d * derivative
        
        # 控制输出
        output = P + I + D
        
        self.last_error = error
        
        return output
    
    def mpc_control(self, current_state, prediction_horizon, forecast):
        """
        模型预测控制（MPC）
        
        步骤:
        1. 状态估计
        2. 未来预测（N步）
        3. 优化求解（最优控制序列）
        4. 执行第一步
        5. 滚动优化
        
        应用:
        - 泵站优化调度
        - 闸门协同控制
        - 防洪预报调度
        """
        pass
```

**实施时间**: 6-8周

---

## 📅 详细开发时间表

### Phase 0: 算法修复与增强（3个月，P0优先级）

#### 第1-2周: 修复Preissmann求解器 ⭐

```
任务:
✅ Day 1-3: 诊断当前bug（已完成Day 2）
⏭️ Day 4-7: 重新实现Preissmann格式
  - 统一中点离散
  - 完整Jacobian矩阵
  - 物理限制（不添加质量）
⏭️ Day 8-10: 测试验证
  - Dam Break
  - 洪水演进
  - 质量守恒
⏭️ Day 11-14: 文档和示例

预期成果:
- Dam Break误差: 32.91% → 15-20%
- 质量守恒: +279% → < 0.01%
- 收敛性: 稳定
```

#### 第3-4周: MacCormack显式格式

```
任务:
⏭️ Day 1-5: 实施MacCormack格式
  - 预测步
  - 校正步
  - 边界条件
⏭️ Day 6-10: 测试与优化
  - 稳定性测试
  - 精度对比
⏭️ Day 11-14: 文档

预期成果:
- 提供显式求解选项
- 易于实施和理解
- 中等精度
```

#### 第5-6周: 明满流转换（Preissmann Slot）

```
任务:
⏭️ Day 1-7: 实施Preissmann Slot
  - 狭缝参数计算
  - 统一求解框架
  - 自动切换逻辑
⏭️ Day 8-12: 测试城市排水案例
  - 管道满流
  - 检查井溢流
  - 明满流转换
⏭️ Day 13-14: 文档

预期成果:
- 支持城市排水系统
- 无需手动判断流态
```

#### 第7-8周: 有压管网集成

```
任务:
⏭️ Day 1-7: Newton-Raphson管网平差
  - Jacobian组装
  - 泵站/阀门集成
⏭️ Day 8-12: 扩展周期模拟
  - 时间推进
  - 水箱更新
⏭️ Day 13-14: 测试

预期成果:
- 完整供水系统模拟
- 泵站优化调度
```

#### 第9-10周: Roe求解器（可选）

```
任务:
⏭️ Week 1: 实施Roe求解器
⏭️ Week 2: 熵修正与测试

预期成果:
- Dam Break改进5-10%
```

#### 第11-12周: 综合测试与文档

```
任务:
⏭️ Week 1: 国际标准案例测试
  - HEC-RAS案例库
  - SWMM案例库
  - EPANET案例库
⏭️ Week 2: 文档完善
  - API更新
  - 使用指南
  - 算法说明
```

**Phase 0 交付**: v1.5
- ✅ 修复的Preissmann
- ✅ 明满流转换
- ✅ 完整管网求解
- ✅ 非恒定流能力提升

---

### Phase 1: 工程对象测试与完善（2-3个月）

#### 任务清单

| 周 | 任务 | 说明 |
|----|------|------|
| 1-2 | **已有对象测试** | 系统测试25+个已有对象 |
| 3 | **涵洞实施** | 6种流态完整模型 |
| 4 | **桥梁实施** | 3种流态 |
| 5 | **时变边界** | 流量/水位过程线 |
| 6 | **城市调蓄池** | 雨水调蓄 |
| 7-8 | **案例库建设** | 50+工程案例 |
| 9-10 | **文档完善** | 每个对象详细说明 |

**Phase 1 交付**: v2.0
- ✅ 所有对象充分测试
- ✅ 补齐缺失对象
- ✅ 完整案例库

---

### Phase 2: 系统验证与优化（2-3个月）

#### 任务清单

| 周 | 任务 | 说明 |
|----|------|------|
| 1-2 | **复杂河网验证** | 多支流、多结构 |
| 3-4 | **城市排水验证** | SWMM对标 |
| 5-6 | **供水管网验证** | EPANET对标 |
| 7-8 | **性能优化** | Numba JIT, 并行 |
| 9-10 | **完整文档** | 用户手册、API |

**Phase 2 交付**: v2.5
- ✅ 国际标准案例100%通过
- ✅ 性能提升2-5倍
- ✅ 完整文档体系

---

## 🎯 功能对比矩阵（修正版）

### 当前状态（v1.0）重新评估

| 功能领域 | 已有对象 | 缺失对象 | 完成度 |
|---------|---------|---------|--------|
| **断面类型** | 5种 | 0 | 100% ✅ |
| **闸门/堰** | 5种 | 3种 | 60% ⚠️ |
| **阀门** | 5种 | 2种 | 70% ⚠️ |
| **泵站** | ✅ | 需完善 | 70% ⚠️ |
| **特殊结构** | 2种 | 2种 | 50% ⚠️ |
| **水库系统** | ✅ | 0 | 100% ✅ |
| **水电系统** | ✅ | 0 | 100% ✅ |
| **网络拓扑** | ✅ | 需完善 | 60% ⚠️ |

### 算法能力（关键！）

| 算法类别 | 状态 | 评级 | 急迫性 |
|---------|------|------|--------|
| **稳态明渠** | ✅ 完美 | ⭐⭐⭐⭐⭐ | - |
| **非恒定流** | ⚠️ 有bug | ⭐⭐☆☆☆ | 🔥🔥🔥 |
| **有压管网** | ⚠️ 未集成 | ⭐⭐⭐☆☆ | 🔥🔥 |
| **明满流转换** | ❌ 缺失 | ⭐☆☆☆☆ | 🔥🔥🔥 |
| **水锤分析** | ⚠️ 基础版 | ⭐⭐☆☆☆ | 🔥 |
| **网络求解** | ⚠️ 基础版 | ⭐⭐⭐☆☆ | 🔥🔥 |

**结论**: **算法是最大短板，不是对象！**

---

## 🔥 近期工作重点（Phase 0，3个月）

### 优先级P0（必须完成）

| 任务 | 时间 | 预期成果 |
|------|------|---------|
| **1. 修复Preissmann** | 2周 | 质量守恒、精度提升 |
| **2. 明满流转换** | 3周 | 城市排水能力 |
| **3. 管网集成** | 3周 | 供水系统能力 |

### 优先级P1（重要）

| 任务 | 时间 | 预期成果 |
|------|------|---------|
| **4. MacCormack格式** | 2周 | 备选非恒定流求解器 |
| **5. 水库调洪** | 2周 | 洪水调节 |
| **6. 已有对象测试** | 2周 | 验证25+个对象 |

**总计**: 14周（3.5个月）

---

## 📊 资源需求（修正）

### 人力需求

| Phase | 时间 | 核心算法 | 测试 | 文档 | 总人月 |
|-------|------|---------|------|------|--------|
| Phase 0 | 3月 | 2人×3 | 1人×2 | 0.5人×2 | 9人月 |
| Phase 1 | 2.5月 | 1人×2.5 | 1人×2 | 0.5人×2 | 6.5人月 |
| Phase 2 | 2.5月 | 1人×2.5 | 1人×2 | 0.5人×2 | 6.5人月 |
| **总计** | **8个月** | - | - | - | **22人月** |

**大幅减少**: 从75人月 → 22人月

**原因**: 项目已有丰富基础！

---

## 🎯 成功标准（v2.5，8个月后）

### 算法能力

| 算法 | 目标 |
|------|------|
| 稳态明渠 | 0.000000%（保持） |
| 非恒定流 | < 10%（Dam Break） |
| 有压管网 | < 0.1%（稳态） |
| 明满流 | 稳定切换 |
| 质量守恒 | < 0.01%（所有情况） |

### 功能覆盖

| 类别 | 目标 |
|------|------|
| 工程对象 | 30+种（完整测试） |
| 算法类型 | 8种 |
| 边界条件 | 10+种 |
| 系统类型 | 明渠+管道+混合 |

### 标准案例

| 来源 | 通过率目标 |
|------|----------|
| HEC-RAS案例 | 90%+ |
| SWMM案例 | 90%+ |
| EPANET案例 | 95%+ |
| 自有案例 | 100% |

---

## 📝 总结

### 关键认识修正

**之前认为**: 缺少大量工程对象（需要2-3年开发）

**实际情况**: 
- ✅ 已有25+种工程对象
- ✅ 已有完整断面库
- ✅ 已有水库、水电、泵站
- ⚠️ **真正缺的是算法和集成**

### 聚焦重点

**核心任务**（3个月）:
1. 修复Preissmann（质量守恒）
2. 实施明满流转换（统一框架）
3. 集成管网求解（已有Hardy-Cross）

**次要任务**（2-3个月）:
4. 测试已有对象
5. 补齐少量缺失对象
6. 完善文档

### 时间大幅缩短

**从**: 2-3年（75人月）  
**到**: 8个月（22人月）  

**原因**: 项目基础远好于预期！

---

**计划版本**: v3.0 - 聚焦算法  
**发布日期**: 2025-10-28  
**核心策略**: 算法优先，测试集成，快速迭代

