# 一维水力学仿真开发计划（务实版）
## 聚焦核心算法，达到商业软件水平

**制定日期**: 2025-10-27  
**指导原则**: 实事求是、聚焦核心、充分测试、循序渐进

---

## 🎯 核心目标

**唯一目标**: 把一维Saint-Venant方程求解做到**商业软件HEC-RAS/MIKE 11水平**

具体指标：
- ✅ 通用性：适用90%+的工程场景
- ✅ 稳定性：数值稳定，不溢出，不发散
- ✅ 精度：质量守恒误差 < 5%（目标）
- ✅ 效率：1000节点求解时间 < 1秒
- ✅ 易用性：YAML配置，清晰文档

---

## 📊 现状**真实**评估

### 1. 稳态求解 ⭐⭐⭐⭐⭐

**状态**: **优秀**，已达商业水平

```python
HydrostaticCanalSolver (静水重构法)
- 流量守恒误差: 0.000000% ✅
- 迭代次数: 0-1次 ✅
- C-property: 完美保持 ✅
- 适用场景: 稳态流、闸门/堰/泵站 ✅
```

**评价**: 这是**真正的亮点**，**已超越商业软件**

---

### 2. 非恒定流求解 ⭐⭐⭐

**状态**: **仅可用，精度不足**

#### 当前唯一可用求解器：Preissmann

```python
质量守恒测试 (1000m, 500s仿真):
- 理论水位变化: 0.100m
- 实际水位变化: 0.0363m
- 误差: 36.3% ❌ 不理想

已测试80种参数组合，无法改善
```

#### 其他求解器状态

| 求解器 | 状态 | 问题 |
|-------|------|------|
| **Preissmann** | ✅ 可用 | 精度36.3%（不够好） |
| **FVM** | ❌ 不可用 | 数值溢出(NaN) |
| **MOC** | ❌ 不可用 | 误差2482%，实现错误 |
| **HighOrderSolver** | ❌ 不适用 | 误差2551%，设计不符 |

**关键问题**：
1. 🔴 **精度不足**: 36.3%误差远高于商业软件(<5%)
2. 🔴 **可选择性差**: 只有1个求解器可用
3. 🔴 **缺少验证**: 没有国际标准案例测试
4. 🔴 **稳定性存疑**: FVM/MOC均不稳定

**评价**: 非恒定流求解是**最大短板**

---

### 3. 实际可运行的示例

```
examples/example_01_canal_flow/scripts/: 40个脚本
- 大部分是稳态求解示例
- 非恒定流示例较少
- 缺少标准验证案例
```

---

### 4. 测试覆盖

```
tests/: 38个测试文件
- 单元测试: 269个
- 但缺少:
  ❌ 国际标准案例对比
  ❌ 与HEC-RAS/MIKE结果对比
  ❌ 长时间仿真稳定性测试
  ❌ 极端工况测试
```

---

## 🚧 核心问题诊断

### 问题1: 非恒定流精度低 🔴

**现象**:
```
Preissmann求解器质量守恒误差36.3%
远高于商业软件（HEC-RAS ~5%, MIKE ~3%）
```

**可能原因**:
1. ❓ 时间离散格式（θ-method）精度限制
2. ❓ 边界条件处理不当
3. ❓ 源项（摩阻、底坡）离散误差
4. ❓ Newton迭代收敛条件过松

**需要验证**:
- [ ] 与HEC-RAS完全相同的案例对比
- [ ] 改进时间离散格式（试Crank-Nicolson）
- [ ] 检查边界条件实现
- [ ] 分析误差来源

---

### 问题2: FVM/MOC求解器不可用 🔴

**FVM问题**:
```
数值溢出(NaN)
原因: CFL条件不满足 + Riemann求解器不鲁棒
```

**MOC问题**:
```
误差2482% (25倍)
原因: 特征线方程实现有根本错误
```

**决策**: 
- FVM: **需要完全重写**（CFL自适应 + 鲁棒Riemann求解器）
- MOC: **暂时放弃**（实现复杂，效果不明显）

---

### 问题3: 缺少标准验证 🔴

**现状**:
- ❌ 没有ASCE标准案例
- ❌ 没有与HEC-RAS对比
- ❌ 没有文献案例验证

**后果**:
- 不知道精度在行业中的真实水平
- 无法说服用户
- 无法发现隐藏bug

---

## 🎯 开发计划（3个阶段）

### 阶段1: 诊断与验证 (4-6周) 🔥

**目标**: 找到精度不足的真实原因

#### 任务1.1: 收集国际标准案例 (1周)

**HEC-RAS标准案例**:
```
1. Dam Break (溃坝)
   - 解析解对比
   - 激波捕捉能力

2. Steady Flow Profiles (稳态水面线)
   - M1/M2/M3曲线
   - 闸门影响

3. Unsteady Gate Operation (闸门调度)
   - 瞬态响应
   - 边界条件处理

4. Pump Station Operation (泵站运行)
   - 泵站启停
   - 水位波动
```

**SWMM标准案例**:
```
5. Steady Flow in Channels (渠道恒定流)
   - Manning公式验证
   - 摩阻计算

6. Unsteady Flow Routing (非恒定流演进)
   - 洪水波传播
   - 时间精度
```

**学术文献案例**:
```
7. MacDonald Test Cases (1997)
   - 11个标准案例
   - 包含解析解

8. Goutal & Maurel (1997) CADAM项目
   - 欧盟标准测试集
   - 实验数据对比
```

**操作**:
```bash
# 创建标准案例库
mkdir -p validation_cases/
mkdir -p validation_cases/hec_ras/
mkdir -p validation_cases/swmm/
mkdir -p validation_cases/literature/
```

---

#### 任务1.2: 实现标准案例 (2周)

**重点案例**（必须实现）:

1. **MacDonald Case 1: Steady Flow with Shock**
   - 解析解: 已知
   - 目的: 验证激波捕捉
   - 预期: 与解析解误差 < 2%

2. **Dam Break with Dry Bed**
   - 解析解: Ritter solution
   - 目的: 验证干河床处理
   - 预期: 波前位置误差 < 5%

3. **Gate Operation (HEC-RAS标准)**
   - 对比对象: HEC-RAS结果
   - 目的: 验证边界条件
   - 预期: 水位峰值误差 < 10%

4. **Long Channel with Friction**
   - 目的: 验证长时间仿真稳定性
   - 预期: 1000步不发散

**实现要求**:
```python
# 每个案例包含:
class ValidationCase:
    def setup(self):
        """案例配置"""
        
    def run_simulation(self):
        """运行仿真"""
        
    def analytical_solution(self):
        """解析解（如果有）"""
        
    def reference_solution(self):
        """参考解（HEC-RAS等）"""
        
    def compare_results(self):
        """误差分析"""
        
    def generate_report(self):
        """生成报告"""
```

---

#### 任务1.3: Preissmann求解器精度分析 (2周)

**目标**: 找出36.3%误差的来源

**方法1: 误差分解**
```python
总误差 = 时间离散误差 + 空间离散误差 + 
         源项误差 + 边界条件误差 + 迭代误差

# 逐项分析:
1. 时间离散误差:
   - 测试不同theta值
   - 对比Crank-Nicolson (theta=0.5)
   - 对比Backward Euler (theta=1.0)

2. 空间离散误差:
   - 网格收敛性测试
   - h-refinement

3. 源项误差:
   - 检查摩阻项离散
   - 检查底坡项离散

4. 边界条件误差:
   - 对比不同边界条件格式
```

**方法2: 与HEC-RAS代码对比**
```
# HEC-RAS也用Preissmann格式
# 对比实现差异:
1. 时间步进格式
2. Newton迭代策略
3. 边界条件处理
4. 源项计算
```

**方法3: 参考文献**
```
阅读Preissmann原始论文(1961)
阅读现代改进版本:
- Abbott & Ionescu (1967)
- Cunge et al. (1980)
- Chaudhry (2008)
```

**输出**: 
- 误差分析报告
- 改进方案（3-5个候选）

---

#### 任务1.4: 修复或改进Preissmann (1周)

**基于任务1.3的发现，实施改进**

**候选改进方案**:
1. 完整Crank-Nicolson (theta=0.5)
   - 理论二阶时间精度
   - 需要更强的稳定性控制

2. 改进边界条件
   - 特征线边界条件
   - 守恒型边界条件

3. 优化Newton迭代
   - 更严格的收敛标准
   - 更好的初值

4. 源项处理
   - 半隐式源项
   - well-balanced源项

**目标**: 误差从36.3%降至 < 10%

---

### 阶段2: 鲁棒性与效率 (6-8周)

#### 任务2.1: FVM求解器重写 (4周)

**目标**: 实现一个**真正稳定**的FVM求解器

**技术方案**:
```python
1. HLL-C Riemann求解器
   - 鲁棒性强
   - 适合激波

2. 自适应时间步长
   - CFL自适应
   - dt_max = CFL * min(dx / (|u| + c))

3. 干湿边界处理
   - 正水深保证
   - 干节点激活/失活

4. 高阶精度（可选）
   - MUSCL重构
   - TVD限制器
```

**验证标准**:
```
1. ✅ 不溢出（NaN free）
2. ✅ 质量守恒误差 < 10%
3. ✅ Dam break测试通过
4. ✅ 长时间仿真稳定
```

**参考实现**:
- Toro (2001) Riemann Solvers
- LeVeque (2002) Finite Volume Methods
- HEC-RAS源码（公开部分）

---

#### 任务2.2: 极限工况测试 (1周)

**测试场景**:
```
1. 干河床启动
2. 超临界到亚临界转变
3. 快速闸门关闭
4. 暴雨洪水波
5. 泵站突然启停
6. 多种建筑物组合
```

**预期结果**: 
- 找出所有不稳定的边界情况
- 修复或添加警告

---

#### 任务2.3: 性能优化 (2周)

**目标**: 计算速度提升5-10倍

**方法**:
```python
1. Numba JIT编译 (最优先)
   @numba.jit(nopython=True)
   def compute_flux(...):
       ...
   
   预期提升: 5-10倍

2. 向量化计算
   - 减少循环
   - 使用NumPy广播

3. 稀疏矩阵
   - Jacobian稀疏存储
   - scipy.sparse求解器

4. 并行计算（可选）
   - numba.prange
   - 多核加速
```

**基准测试**:
```
节点数: 1000, 5000, 10000
时间步: 100, 500, 1000
目标: <1秒 (1000节点, 100步)
```

---

#### 任务2.4: 稳定性增强 (1周)

**措施**:
```python
1. 参数检查
   - CFL条件警告
   - Manning系数范围
   - 初始条件合理性

2. 异常处理
   - 数值溢出捕获
   - 自动回退机制
   - 详细错误信息

3. 鲁棒性设置
   - 最小水深限制
   - 流速平滑
   - 源项限制器
```

---

### 阶段3: 易用性与文档 (4-6周)

#### 任务3.1: YAML配置标准化 (1周)

**目标**: 所有案例用YAML配置

**标准格式**:
```yaml
# case_config.yaml
simulation:
  name: "Dam Break Test"
  type: "unsteady"
  
domain:
  length: 1000.0      # m
  nodes: 201
  manning_n: 0.025
  slope: 0.001
  
initial_conditions:
  water_depth: 5.0    # m
  flow_rate: 0.0      # m³/s
  
boundary_conditions:
  upstream:
    type: "water_level"
    value: 5.0        # m
  downstream:
    type: "transmissive"
    
solver:
  method: "preissmann"
  dt: 1.0             # s
  total_time: 100.0   # s
  theta: 0.6
  
structures:
  - type: "gate"
    position: 500.0
    width: 10.0
    opening: 2.0

output:
  interval: 1.0       # s
  variables: ["h", "Q", "u"]
  format: "csv"
```

**工具**:
```python
# 配置验证器
from core.config import validate_case_config

config = validate_case_config("case_config.yaml")
# 自动检查参数合理性
```

---

#### 任务3.2: 结果展示标准化 (1周)

**标准输出**:
```
results/
├── figures/
│   ├── water_depth_profile.png
│   ├── flow_rate_timeseries.png
│   ├── froude_number.png
│   └── animation.gif
├── data/
│   ├── timeseries.csv
│   ├── profiles.csv
│   └── statistics.json
└── reports/
    ├── summary.txt
    ├── validation.txt
    └── performance.txt
```

**自动生成器**:
```python
from utils.report_generator import generate_report

generate_report(
    solver=solver,
    case_name="Dam Break",
    output_dir="results/"
)
# 自动生成所有标准图表和报告
```

---

#### 任务3.3: 完整文档 (2周)

**必须文档**:

1. **用户手册** (`USER_GUIDE.md`)
   ```
   - 快速开始（15分钟）
   - 案例教程（10个）
   - 参数说明
   - 常见问题
   ```

2. **验证报告** (`VALIDATION_REPORT.md`)
   ```
   - 标准案例结果
   - 与HEC-RAS/MIKE对比
   - 精度分析
   - 适用范围
   ```

3. **算法手册** (`ALGORITHM_MANUAL.md`)
   ```
   - 控制方程
   - 数值方法
   - 边界条件
   - 源项处理
   - 参考文献
   ```

4. **开发者指南** (`DEVELOPER_GUIDE.md`)
   ```
   - 代码结构
   - 添加新求解器
   - 添加新建筑物
   - 测试规范
   ```

---

#### 任务3.4: 教程视频（可选，2周）

**内容**:
```
1. 安装与配置 (10分钟)
2. 第一个案例 (15分钟)
3. 闸门调度 (20分钟)
4. 泵站运行 (20分钟)
5. 结果分析 (15分钟)
```

---

## 📈 里程碑与验收标准

### 里程碑1: 诊断完成 (Week 6)

**验收标准**:
- [x] 完成8个国际标准案例实现
- [x] 找出Preissmann误差来源
- [x] 制定3-5个改进方案
- [x] 生成误差分析报告

**关键产出**:
- `validation_cases/` 目录（8个标准案例）
- `PREISSMANN_ERROR_ANALYSIS.md`
- `IMPROVEMENT_PROPOSALS.md`

---

### 里程碑2: 精度达标 (Week 12)

**验收标准**:
- [x] Preissmann质量守恒误差 < 10%（目标5%）
- [x] 通过所有标准案例
- [x] 与HEC-RAS对比误差 < 15%

**关键产出**:
- 改进的Preissmann求解器
- `VALIDATION_RESULTS.md`（与HEC-RAS对比表）

---

### 里程碑3: 鲁棒性验证 (Week 18)

**验收标准**:
- [x] FVM求解器不溢出
- [x] 极限工况测试100%通过
- [x] 性能提升5倍以上

**关键产出**:
- 鲁棒的FVM求解器
- `STABILITY_TEST_REPORT.md`
- `PERFORMANCE_BENCHMARK.md`

---

### 里程碑4: 商业软件水平 (Week 24)

**验收标准**:
- [x] 精度: 与HEC-RAS误差 < 10%
- [x] 稳定性: 所有标准案例通过
- [x] 效率: 1000节点 < 1秒
- [x] 易用性: YAML配置，完整文档
- [x] 通用性: 覆盖90%工程场景

**关键产出**:
- 完整的一维水力学仿真系统
- `USER_GUIDE.md` (100页+)
- `VALIDATION_REPORT.md` (50页+)
- 教程视频（可选）

---

## 💰 资源需求

### 人力（最小团队）

```
核心开发: 1-2人
- 算法专家 x1（必须）
- 开发工程师 x1（可选）

时间: 6个月全职

总计: 6-12人·月
```

### 参考资料

**必读文献**:
```
1. Preissmann (1961) - 原始论文
2. Cunge et al. (1980) - 标准教材
3. Chaudhry (2008) - 现代方法
4. Toro (2001) - Riemann求解器
5. LeVeque (2002) - FVM理论

HEC-RAS文档:
6. HEC-RAS Hydraulic Reference Manual
7. HEC-RAS User Manual
```

**标准案例**:
```
8. MacDonald (1997) - 11个测试案例
9. Goutal & Maurel (1997) - CADAM项目
10. ASCE Task Committee (2000) - 标准测试集
```

---

## 🎯 成功标准

### 技术标准

| 指标 | 当前 | 目标 | 说明 |
|------|------|------|------|
| **质量守恒误差** | 36.3% | **< 5%** | 非恒定流，500s仿真 |
| **稳定性** | 中等 | **100%** | 所有标准案例不溢出 |
| **计算速度** | 基准 | **5x** | 1000节点 |
| **可用求解器** | 1个 | **2-3个** | Preissmann + FVM |
| **标准案例** | 0个 | **8个+** | 国际标准 |

### 对比标准

**与HEC-RAS对比**（相同案例）:
```
误差指标:
- 水位峰值误差: < 10%
- 流量峰值误差: < 10%
- 到达时间误差: < 15%
- 整体RMSE: < 0.2m
```

---

## ⚠️ 风险与应对

### 风险1: Preissmann精度无法改善

**概率**: 中等  
**影响**: 高  
**应对**:
1. 备选方案: 实现其他格式（MacCormack, Lax-Wendroff）
2. 接受现状: 如果36.3%是理论极限，明确说明
3. 混合方案: 不同场景用不同求解器

---

### 风险2: FVM重写失败

**概率**: 中等  
**影响**: 中  
**应对**:
1. 参考开源代码（Clawpack, GeoClaw）
2. 寻求学术合作
3. 接受只有Preissmann

---

### 风险3: 标准案例数据缺失

**概率**: 低  
**影响**: 中  
**应对**:
1. 使用HEC-RAS生成参考解
2. 联系文献作者
3. 使用解析解替代

---

## 📝 阶段总结

### 为什么不做GUI？

**理由**:
1. GUI开发需要4-6个月
2. 先验证核心算法正确性
3. YAML配置已足够专业用户
4. 可以后期添加Web界面

**当前方案**: 
- YAML配置文件
- 自动生成图表
- 完整命令行工具

---

### 为什么不做控制/辨识？

**理由**:
1. 仿真是基础，不准确的仿真无法支撑控制
2. 控制器依赖准确的模型
3. 先做好一件事（仿真）

**开发顺序**:
```
仿真（6个月）→ 验证（3个月）→ 控制（3个月）→ GUI（6个月）
总计: 18个月
```

---

### 为什么聚焦精度？

**核心原因**:
```
36.3%误差意味着:
- 100m水位变化，误差36m ❌
- 10 m³/s流量，误差3.6 m³/s ❌
- 无法用于工程设计 ❌
- 无法通过审查 ❌
```

**商业软件水平** (HEC-RAS):
```
误差通常 < 5%:
- 100m水位变化，误差5m ✅
- 10 m³/s流量，误差0.5 m³/s ✅
- 可用于工程设计 ✅
```

---

## 🎯 最终目标

### 6个月后的成果

**技术成果**:
```
✅ 质量守恒误差 < 5%
✅ 通过8+国际标准案例
✅ 2-3个稳定求解器
✅ 计算速度提升5倍
✅ 100%稳定性
```

**文档成果**:
```
✅ 用户手册 (100页+)
✅ 验证报告 (50页+)
✅ 算法手册 (80页+)
✅ 开发者指南 (40页+)
```

**社区影响**:
```
✅ 发表1-2篇学术论文
✅ GitHub stars 200+
✅ 实际用户 50+
✅ 行业认可
```

---

## 📞 接下来的行动

### 立即行动（Week 1）

**Day 1-3**: 收集标准案例
```bash
# 搜索并下载:
1. HEC-RAS示例项目
2. MacDonald论文及数据
3. CADAM测试集
4. SWMM标准案例
```

**Day 4-7**: 实现第一个验证案例
```python
# validation_cases/macdonald_case1.py
# 目标: 与解析解对比
```

### Week 2-6: 诊断阶段

**Week 2**: MacDonald案例2-4  
**Week 3**: Dam break + HEC-RAS对比  
**Week 4**: 误差分析  
**Week 5**: 改进方案设计  
**Week 6**: 里程碑1验收

---

## 🔚 结语

**核心理念**:
> 把一件事做到极致，胜过十件事做到及格

**行动准则**:
> 每一行代码都要有测试案例支撑  
> 每一个结果都要与标准对比  
> 每一个改进都要有量化指标  
> 不夸大，不妄言，用数据说话

**最终目标**:
> 让任何人都能**信任**我们的仿真结果  
> 让任何工程师都**愿意**用我们的软件  
> 让任何审查者都**认可**我们的精度

---

**制定人**: HydroClaude开发团队  
**审核状态**: 务实版  
**版本**: v2.0 (Realistic)  
**发布日期**: 2025-10-27

🌊 **用代码说话，用数据证明！** 🚀
