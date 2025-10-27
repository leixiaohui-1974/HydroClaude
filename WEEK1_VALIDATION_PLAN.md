# Week 1 验证计划执行记录

**开始日期**: 2025-10-27  
**目标**: 实现第一个标准验证案例，建立验证框架

---

## ✅ 已完成的工作

### 1. 创建验证案例目录结构

```
validation_cases/
├── README.md                    # 案例库说明
├── analytical/                  # 解析解案例
│   └── dam_break_ritter.py      # Dam Break标准案例
├── literature/                  # 文献案例
├── hec_ras/                     # HEC-RAS对比
└── results/                     # 结果输出目录
```

### 2. 实现Dam Break标准案例

**案例**: Dam Break with Dry Bed (Ritter Solution)

**物理场景**:
- 1000m渠道，初始左半段水深10m，右半段干河床
- t=0时溃坝（瞬间移除中间隔板）
- 仿真时间50秒

**参考解**: Ritter (1892) 解析解

**验收标准**:
- 波前位置误差 < 5%
- 水深分布RMSE < 0.5m

**测试内容**:
1. HydrostaticCanalSolver (静水重构法)
2. Canal-Preissmann (四点隐式)
3. 与Ritter解析解对比

---

## 📝 验证案例代码框架

已创建完整的验证脚本：`dam_break_ritter.py`

### 核心功能

```python
class DamBreakRitter:
    """Dam Break标准案例"""
    
    def analytical_solution(self, t):
        """Ritter解析解"""
        # 实现稀疏波解析解
        # 返回: h, u分布
    
    def run_hydrostatic_solver(self):
        """运行HydrostaticCanalSolver"""
        # 使用静水重构法
        # 时间步进50秒
    
    def run_canal_preissmann(self):
        """运行Canal-Preissmann"""
        # 使用四点隐式格式
        # 时间步进50秒
    
    def compare_and_plot(self):
        """误差分析和可视化"""
        # 计算波前位置误差
        # 计算水深RMSE
        # 生成4个对比图表
    
    def generate_report(self):
        """生成验证报告"""
        # 自动判断PASS/FAIL
        # 生成txt报告
```

### 关键测试指标

```python
# 1. 波前位置误差
x_front_exact = x_dam + 2 * sqrt(g * h0) * T
err_front = |x_front_numerical - x_front_exact| / x_front_exact * 100%

验收: < 5%

# 2. 水深RMSE
rmse_h = sqrt(mean((h_numerical - h_exact)^2))

验收: < 0.5m

# 3. 时空演化
contourf(x, t, h(x, t))
验证波的传播特征
```

---

## 🔍 预期测试结果

### 场景1: HydrostaticCanalSolver

**预期表现**:
```
✅ 优点:
- C-property保持良好
- 激波捕捉能力强
- 干河床处理稳定

⚠️ 可能问题:
- 非恒定流模式下精度待验证
- 可能需要调整时间步长
```

### 场景2: Canal-Preissmann

**预期表现**:
```
⚠️ 基于之前的测试:
- 质量守恒误差36.3%
- 可能在dam break场景更差
- 激波捕捉能力弱

目标:
- 量化dam break场景的误差
- 识别改进方向
```

---

## 📊 输出文件

### 自动生成的文件

```
validation_cases/results/
├── dam_break_ritter_20251027_HHMMSS.png
│   ├── [图1] 水深对比 (解析解 vs 数值解)
│   ├── [图2] 误差分布
│   ├── [图3] 时空演化等值线
│   └── [图4] 误差汇总柱状图
│
└── dam_break_report_20251027_HHMMSS.txt
    ├── 问题描述
    ├── 验收标准
    ├── 测试结果 (PASS/FAIL)
    └── 结论
```

---

## 🚧 环境问题与解决

### 当前问题

```
❌ Python环境中缺少numpy等依赖
```

### 解决方案

**方案A: 安装依赖** (推荐)
```bash
pip install numpy scipy matplotlib
```

**方案B: 使用现有测试框架**
```bash
# 项目中已有tests/目录
# 可以扩展现有的测试框架
cd /workspace/tests
python -m pytest test_*.py
```

**方案C: 使用Docker环境**
```bash
# 创建带有完整依赖的Docker镜像
FROM python:3.9
RUN pip install numpy scipy matplotlib pyyaml
```

---

## 📋 下一步行动

### 立即行动（安装依赖后）

```bash
# 1. 运行dam break验证
cd /workspace
python validation_cases/analytical/dam_break_ritter.py

# 预期输出:
# - 终端显示两个求解器的误差
# - 生成4个对比图
# - 生成验证报告

# 2. 查看结果
ls validation_cases/results/
cat validation_cases/results/dam_break_report*.txt
```

### Week 1 剩余任务

#### Day 2-3: 收集更多标准案例

**优先级P0**:
```
1. MacDonald Case 1: Steady Flow with Shock
   - 解析解已知
   - 简单验证
   
2. Steady Uniform Flow
   - Manning公式验证
   - 基础测试
   
3. Critical Flow
   - Froude=1条件
   - 临界水深验证
```

**优先级P1**:
```
4. MacDonald Case 2-4
5. Goutal & Maurel案例
6. HEC-RAS标准案例
```

#### Day 4-5: 实现MacDonald Case 1

```python
# validation_cases/literature/macdonald_case1.py

class MacdonaldCase1:
    """
    MacDonald (1997) Test Case 1
    Steady Flow with Standing Shock
    """
    
    def analytical_solution(self):
        # 从文献中提取解析解
        
    def run_simulation(self):
        # 运行HydroClaude求解器
        
    def compare(self):
        # 与解析解对比
        # 目标: 误差 < 2%
```

#### Day 6-7: Preissmann误差初步分析

**目标**: 找出36.3%误差的来源

**方法**:
```python
# 误差分解测试
1. 时间离散误差测试
   - 不同theta值 (0.5, 0.6, 0.7)
   - 不同dt值
   
2. 空间离散误差测试
   - 网格收敛性 (h-refinement)
   - Richardson外推
   
3. 边界条件误差测试
   - 不同边界条件格式
   
4. 源项误差测试
   - 摩阻项离散格式
   - 底坡项离散格式
```

---

## 📈 Week 1 预期成果

### 技术成果

```
✅ 建立标准验证框架
✅ 完成1-2个标准案例
✅ 量化当前求解器精度
✅ 识别主要误差来源
```

### 文档成果

```
✅ validation_cases/README.md
✅ 2个验证案例代码
✅ 2-4份验证报告
✅ 误差分析初步报告
```

### 关键发现

预期发现:
```
1. Dam Break场景下:
   - HydrostaticSolver精度: ?% (待测)
   - Preissmann精度: ?% (预计>36.3%)
   
2. 误差主要来源:
   - 时间离散? (θ-method一阶)
   - 边界条件? (处理不当)
   - 源项处理? (数值格式)
   - 初值敏感性?
   
3. 改进方向:
   - 候选方案1: Crank-Nicolson (θ=0.5)
   - 候选方案2: 改进边界条件
   - 候选方案3: Well-balanced源项
```

---

## 🎯 Week 1 验收标准

### 必须完成 (P0)

- [x] ✅ 创建验证案例目录结构
- [x] ✅ 实现Dam Break标准案例代码
- [ ] 🔧 运行Dam Break测试（待安装numpy）
- [ ] 📊 生成第一份验证报告
- [ ] 📝 初步误差分析

### 应该完成 (P1)

- [ ] 实现MacDonald Case 1
- [ ] 收集3-5个标准案例描述
- [ ] 阅读Preissmann原始论文

### 可以完成 (P2)

- [ ] HEC-RAS案例收集
- [ ] 误差分解实验设计
- [ ] 自动化测试脚本

---

## 💡 关键洞察

### 1. 测试驱动开发

```
之前: 先写代码，后测试（不充分）
现在: 先定标准案例，再验证求解器

优势:
- 明确的验收标准
- 客观的精度评估
- 可重复的验证
```

### 2. 与商业软件对标

```
不再自说自话，而是:
- 用国际标准案例
- 与解析解对比
- 与HEC-RAS对比

结果:
- 可信度高
- 问题暴露清晰
- 改进方向明确
```

### 3. 务实的态度

```
承认:
- 非恒定流精度不足(36.3%)
- 需要大量验证工作
- 距离商业软件有差距

行动:
- 从简单案例开始
- 逐步建立信心
- 不夸大，用数据说话
```

---

## 📞 问题与解决

### Q1: 为什么从Dam Break开始？

**A**: 
- 有解析解（Ritter）
- 物理清晰（稀疏波）
- 测试多项能力（激波、干床、瞬态）
- 是国际标准案例

### Q2: 如果测试失败怎么办？

**A**:
- 预期会失败（36.3%误差）
- 关键是量化失败程度
- 识别具体问题
- 制定改进方案

### Q3: 需要多少个验证案例？

**A**:
```
最少: 5-8个
- 覆盖不同物理场景
- 包含解析解和参考解
- 涵盖常见工程问题

目标: 15-20个
- 达到HEC-RAS验证手册水平
```

---

## 🔚 Week 1 总结

### 已建立的框架

```
✅ 验证案例目录结构
✅ 标准测试代码模板
✅ 自动化报告生成
✅ 误差分析方法
```

### 待执行的测试

```
⏳ 等待Python环境配置
⏳ 运行dam_break_ritter.py
⏳ 分析第一份验证报告
⏳ 根据结果调整计划
```

### 经验教训

```
💡 验证比实现更重要
💡 标准案例是唯一可信的证据
💡 诚实面对问题才能进步
```

---

**更新人**: HydroClaude开发团队  
**状态**: Week 1 进行中  
**下次更新**: 完成第一个验证案例后

🌊 **让测试结果说话！** 🚀
