# HydroClaude Stage 2 开发规划

**日期**: 2025-10-29
**前置**: Stage 1 已完成（95%）
**目标**: 工程级功能扩展
**预计时间**: 4-6周

---

## 📋 Stage 1完成状态回顾

### ✅ 已完成的核心功能

1. **激波捕捉（WENO3）**
   - MacDonald Tests 1,2,3,5 ✅
   - Test 4 Realistic（有摩阻） ✅
   - 适用工况100%通过

2. **Well-Balanced方法**
   - 达到浮点机器精度 ✅
   - Lake at Rest全部通过 ✅

3. **干湿界面处理**
   - Dam Break测试通过 ✅
   - Wetting过程稳定 ✅

4. **质量守恒**
   - 商业级性能（< 1%）✅

### ⏸️ 已识别的局限性

1. **混合流态处理**
   - MacDonald Test 4（无摩阻水跃）不适用
   - 临界流（Fr≈1）不稳定
   - 需要：LPI方法或类似解决方案

2. **数值方法验证**
   - 当前：3个验证测试
   - 目标：8个完整验证测试

3. **几何模型**
   - 当前：仅矩形断面
   - 需要：梯形、复式、天然断面

---

## 🎯 Stage 2开发目标

### 核心目标

**目标1**: 实现混合流态求解器
- 解决临界流不稳定问题
- 支持无摩阻水跃（可选）
- MacDonald Test 4原版通过（可选）

**目标2**: 完善数值方法验证套件
- 从3个测试扩展到8个
- 覆盖所有核心数值方法

**目标3**: 不规则断面支持
- 梯形断面
- 复式断面
- 天然河道断面（基础）

**目标4**: 高级边界条件
- 时变边界条件
- Rating curve边界
- 内部结构物（堰、闸）

---

## 📅 开发计划

### Phase 2.1: 混合流态求解器（2-3周）

#### Task 2.1.1: 研究和设计

**时间**: 3-4天

**任务**:
1. 研究HEC-RAS的LPI（Local Partial Inertia）方法
   - 阅读HEC-RAS技术文档
   - 理解LPI原理
   - 分析实现难度

2. 研究MIKE 11的方法
   - 对比不同商业软件的方案
   - 选择最适合HydroClaude的方法

3. 设计实施方案
   - 确定实施路径
   - 定义接口
   - 规划测试策略

**交付成果**:
- 混合流态求解器技术设计文档
- 实施计划
- 测试策略

#### Task 2.1.2: 临界流检测实现

**时间**: 2-3天

**实施内容**:
```python
def detect_critical_flow(Fr, threshold=0.05):
    """检测临界流区域"""
    return abs(Fr - 1.0) < threshold

def compute_local_froude(h, Q, B, g=9.81):
    """计算局部Froude数"""
    u = Q / (B * h)
    Fr = u / np.sqrt(g * h)
    return Fr
```

**测试**:
- 临界流检测准确性
- 边界情况处理

#### Task 2.1.3: Entropy修正

**时间**: 2-3天

**实施内容**:
- Harten-Hyman entropy fix
- Sonic rarefaction处理
- 激波vs稀疏波识别

**参考**:
- Toro (2001): Shock-Capturing Methods
- Harten (1983): Entropy Fix

#### Task 2.1.4: 特殊通量处理

**时间**: 3-4天

**实施内容**:
- 临界流区域的特殊通量计算
- 混合格式（Godunov + LPI）
- 平滑过渡函数

#### Task 2.1.5: 测试和验证

**时间**: 3-4天

**测试案例**:
1. 临界流通过喉部
2. 亚临界→超临界转换
3. 超临界→亚临界转换（水跃）
4. MacDonald Test 4（无摩阻）- 可选

**成功标准**:
- 临界流测试通过
- 质量守恒 < 5%
- 无数值振荡

**交付成果**:
- 混合流态求解器实现
- 完整测试验证
- 技术文档

---

### Phase 2.2: 数值方法验证套件（1-2周）

#### Task 2.2.1: 创建缺失的验证测试

**时间**: 5-7天

**需要创建的测试**:

1. **test_shock_capturing.py** ✅ 部分完成
   - 验证WENO3在激波上的表现
   - Sod激波管测试
   - 收敛率验证

2. **test_mixed_flow.py** 🔴 待创建
   - 临界流测试
   - 混合流态转换
   - Fr≈1稳定性

3. **test_cfl_stability.py** 🔴 待创建
   - 不同CFL数的稳定性
   - CFL上限测试
   - 自适应CFL验证

4. **test_convergence.py** 🔴 待创建
   - 空间收敛性
   - 时间收敛性
   - 网格细化研究

5. **test_source_terms.py** 🔴 待创建
   - 摩阻源项验证
   - 底坡源项验证
   - 源项平衡验证

**测试框架**:
```python
class TestNumericalMethods:
    """数值方法综合验证套件"""

    def test_spatial_convergence(self):
        """空间收敛性测试"""
        pass

    def test_temporal_convergence(self):
        """时间收敛性测试"""
        pass

    def test_shock_resolution(self):
        """激波分辨率测试"""
        pass
```

#### Task 2.2.2: 自动化测试报告

**时间**: 2-3天

**实施**:
- 测试结果自动汇总
- 生成测试报告（Markdown）
- 图表可视化（可选）

**交付成果**:
- 8个完整的数值方法验证测试
- 自动化测试报告
- 测试文档

---

### Phase 2.3: 不规则断面支持（1-2周）

#### Task 2.3.1: 断面类设计

**时间**: 2-3天

**设计**:
```python
class CrossSection(ABC):
    """断面基类"""

    @abstractmethod
    def area(self, h: float) -> float:
        """计算过水断面积"""
        pass

    @abstractmethod
    def wetted_perimeter(self, h: float) -> float:
        """计算湿周"""
        pass

    @abstractmethod
    def hydraulic_radius(self, h: float) -> float:
        """计算水力半径"""
        pass

    @abstractmethod
    def top_width(self, h: float) -> float:
        """计算水面宽度"""
        pass


class RectangularSection(CrossSection):
    """矩形断面（已有）"""
    pass


class TrapezoidalSection(CrossSection):
    """梯形断面"""

    def __init__(self, bottom_width: float, side_slope: float):
        self.B = bottom_width
        self.m = side_slope  # 边坡系数

    def area(self, h: float) -> float:
        return (self.B + self.m * h) * h

    def top_width(self, h: float) -> float:
        return self.B + 2 * self.m * h


class CompoundSection(CrossSection):
    """复式断面"""
    pass


class NaturalSection(CrossSection):
    """天然断面（插值法）"""
    pass
```

#### Task 2.3.2: 水力计算修改

**时间**: 3-4天

**修改内容**:
- 将硬编码的矩形公式改为断面方法调用
- 更新Riemann求解器
- 更新源项计算

**示例**:
```python
# Before
A = B * h
P = B + 2 * h

# After
A = section.area(h)
P = section.wetted_perimeter(h)
```

#### Task 2.3.3: 测试和验证

**时间**: 3-4天

**测试案例**:
1. 梯形断面稳态流
2. 复式断面洪水演进
3. 天然断面流量计算

**验证标准**:
- 与理论解对比（如果有）
- 与商业软件对比
- 质量守恒验证

**交付成果**:
- 4种断面类型实现
- 完整测试验证
- 使用文档

---

### Phase 2.4: 高级边界条件（1周）

#### Task 2.4.1: 时变边界条件

**时间**: 2-3天

**实施**:
```python
class TimeDependentBC:
    """时变边界条件"""

    def __init__(self, time_series):
        self.time = time_series[:, 0]
        self.value = time_series[:, 1]

    def get_value(self, t):
        """线性插值获取t时刻的值"""
        return np.interp(t, self.time, self.value)
```

**应用场景**:
- 潮汐边界
- 洪水过程
- 闸门调度

#### Task 2.4.2: Rating Curve边界

**时间**: 2天

**实施**:
```python
class RatingCurveBC:
    """水位-流量关系曲线边界"""

    def __init__(self, h_Q_curve):
        self.h = h_Q_curve[:, 0]
        self.Q = h_Q_curve[:, 1]

    def get_Q(self, h):
        """根据水位插值流量"""
        return np.interp(h, self.h, self.Q)
```

#### Task 2.4.3: 内部结构物

**时间**: 2-3天

**实施**:
- 堰公式（宽顶堰、薄壁堰）
- 闸门公式
- 内部边界处理

**交付成果**:
- 3种高级边界条件
- 测试案例
- 使用文档

---

## 📊 Stage 2完成指标

### 功能指标

| 功能模块 | 当前状态 | Stage 2目标 | 优先级 |
|---------|---------|-------------|--------|
| 混合流态求解器 | ❌ | ✅ | P1 |
| 数值方法验证 | 3/8 | 8/8 | P1 |
| 不规则断面 | 1/4 | 4/4 | P1 |
| 高级边界条件 | 2/5 | 5/5 | P2 |
| 内部结构物 | ❌ | ✅ | P2 |

### 质量指标

| 指标 | Stage 1 | Stage 2目标 |
|-----|---------|------------|
| 测试覆盖率 | ~20% | > 40% |
| MacDonald测试 | 100%（适用） | 100%（全部）|
| 支持断面类型 | 1 | 4 |
| 边界条件类型 | 2 | 5 |

### 时间规划

| Phase | 时间 | 里程碑 |
|-------|------|--------|
| 2.1 混合流态 | 2-3周 | 临界流稳定 |
| 2.2 验证套件 | 1-2周 | 8个测试完成 |
| 2.3 不规则断面 | 1-2周 | 4种断面支持 |
| 2.4 高级边界 | 1周 | 5种边界条件 |
| **总计** | **5-8周** | **工程级功能** |

---

## 🚀 Stage 2成功标准

### 必须达成（P0）

1. ✅ 混合流态求解器实现并验证
   - 临界流测试通过
   - 质量守恒 < 5%

2. ✅ 数值方法验证套件完整
   - 8/8测试实现
   - 全部通过

3. ✅ 梯形断面支持
   - 实现并验证
   - 至少1个测试案例

### 期望达成（P1）

4. ✅ MacDonald Test 4（无摩阻）通过（可选）
   - 质量守恒 < 10%

5. ✅ 复式断面支持
   - 实现并验证

6. ✅ 时变边界条件
   - 实现并验证

### 可选达成（P2）

7. ⏸️ 天然断面支持
8. ⏸️ 内部结构物（堰、闸）
9. ⏸️ 自动化测试报告

---

## 📈 商业化准备度提升

### Stage 1 → Stage 2

| 维度 | Stage 1 | Stage 2目标 | 提升 |
|-----|---------|------------|------|
| 功能完整性 | 30% | 60% | +100% |
| 适用场景 | 矩形渠道 | 多种断面 | +300% |
| 边界条件 | 基础 | 高级 | +150% |
| 数值稳定性 | 良好 | 优秀 | +30% |
| 测试覆盖率 | ~20% | ~40% | +100% |

### 应用场景扩展

**Stage 1可以做**:
- 矩形渠道洪水演进
- 简单流量计算
- 研究和教学

**Stage 2可以做**:
- ✅ 真实河道洪水演进（梯形/天然断面）
- ✅ 水库调度（时变边界）
- ✅ 堰闸控制（内部结构物）
- ✅ 复杂流态模拟（混合流态）
- ✅ 工程设计计算

---

## 📝 技术风险评估

### 高风险（需要重点关注）

1. **混合流态求解器复杂度**
   - 风险：实现难度可能超预期
   - 缓解：充分研究HEC-RAS方法，必要时采用简化方案

2. **不规则断面性能**
   - 风险：计算效率可能下降
   - 缓解：优化断面计算，考虑查表法

### 中风险

3. **测试覆盖率提升**
   - 风险：测试设计需要大量时间
   - 缓解：参考标准测试案例

4. **向后兼容性**
   - 风险：新功能可能影响现有测试
   - 缓解：持续运行回归测试

### 低风险

5. **边界条件扩展**
   - 风险：较低，技术成熟
   - 缓解：参考现有实现

---

## 🎯 下一步行动

### 立即开始（本周）

1. **研究混合流态求解器**
   - [ ] 阅读HEC-RAS文档
   - [ ] 阅读相关论文
   - [ ] 设计技术方案

2. **创建Task跟踪**
   - [ ] 创建GitHub Issues
   - [ ] 设置Milestone
   - [ ] 分配优先级

### 短期（1-2周）

3. **开始混合流态实现**
   - [ ] 临界流检测
   - [ ] Entropy修正
   - [ ] 初步测试

4. **补充数值方法测试**
   - [ ] test_mixed_flow.py
   - [ ] test_cfl_stability.py

### 中期（3-4周）

5. **不规则断面设计和实现**
6. **完整验证测试套件**
7. **高级边界条件**

---

## 📚 参考资料

### 混合流态求解器

1. **HEC-RAS Documentation**
   - Hydraulic Reference Manual
   - Chapter on Mixed Flow Regime

2. **学术论文**
   - Toro (2001): Shock-Capturing Methods for Free-Surface Shallow Flows
   - Harten (1983): High Resolution Schemes for Hyperbolic Conservation Laws
   - Audusse et al. (2004): A Fast and Stable Well-Balanced Scheme

3. **商业软件对比**
   - MIKE 11 Technical Documentation
   - InfoWorks ICM User Guide

### 数值方法

4. **经典教材**
   - LeVeque (2002): Finite Volume Methods for Hyperbolic Problems
   - Toro (2009): Riemann Solvers and Numerical Methods for Fluid Dynamics

### 断面计算

5. **水力学教材**
   - Chow (1959): Open-Channel Hydraulics
   - Henderson (1966): Open Channel Flow

---

**文档创建**: 2025-10-29
**状态**: 规划中
**下次审查**: Stage 2启动时
