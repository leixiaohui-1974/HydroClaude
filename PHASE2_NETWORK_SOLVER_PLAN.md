# Phase 2: 网络求解器专项攻关

**开始日期**: 2025-10-27  
**核心目标**: 突破网络求解器守恒性问题  
**目标**: 质量误差 < 1%

---

## 🎯 Phase 2 核心任务

### 主要目标

**网络求解器质量误差从 9-22% → <1%**

**关键挑战**: 
- Phase 1测试：串联质量误差-17%，Y-split NaN
- 根本原因：频繁修改边界条件破坏FVM守恒性
- 单渠道Godunov: 0.355%误差（完美）✅

---

## 📚 算法研究

### 方案对比

#### ❌ 方案0: 频繁修改边界条件（Phase 1失败）

**Phase 1方法**:
```python
# 每步更新边界条件
for step in range(max_steps):
    update_boundary_conditions()  # 修改每条边的bc_left/bc_right
    for edge in edges:
        edge.solver.step()
```

**问题**: 
- 破坏FVM守恒性
- 质量误差-17%到-22%

---

#### ✅ 方案A: Ghost Cell方法（推荐）

**核心思想**: 
- 不修改边界条件
- 通过Ghost Cell（虚拟单元）传递信息
- 每条边保持独立的FVM守恒性

**原理**:
```
渠道1: [cell1, cell2, ..., cellN] + [ghost_right]
                                      ↑
                                      | 信息传递
                                      ↓
渠道2: [ghost_left] + [cell1, cell2, ..., cellN]
```

**实现**:
```python
class EdgeWithGhost:
    def __init__(self, n_cells):
        self.h = np.zeros(n_cells + 2)  # 包括2个ghost cells
        self.Q = np.zeros(n_cells + 2)
        # ghost: [0], [n_cells+1]
        # interior: [1] to [n_cells]
    
    def update_ghost_cells(self, left_h, left_Q, right_h, right_Q):
        """从邻居边更新ghost cells"""
        self.h[0] = left_h     # 左ghost
        self.Q[0] = left_Q
        self.h[-1] = right_h   # 右ghost
        self.Q[-1] = right_Q
    
    def compute_flux_at_boundaries(self):
        """使用ghost cells计算边界通量"""
        # 左边界: 使用h[0](ghost)和h[1](interior)
        F_left = compute_flux(self.h[0], self.Q[0], self.h[1], self.Q[1])
        
        # 右边界: 使用h[-2](interior)和h[-1](ghost)
        F_right = compute_flux(self.h[-2], self.Q[-2], self.h[-1], self.Q[-1])
        
        return F_left, F_right
```

**网络节点处理**:
```python
def handle_junction_ghost(node):
    """汇流节点: 多入一出"""
    # 1. 获取所有入流边的下游状态
    h_list = [edge.h[-2] for edge in node.inflow_edges]  # interior cell
    Q_list = [edge.Q[-2] for edge in node.inflow_edges]
    
    # 2. 计算节点状态（平均）
    h_node = np.mean(h_list)
    Q_node = sum(Q_list)
    
    # 3. 设置ghost cells
    for in_edge in node.inflow_edges:
        in_edge.h[-1] = h_node  # 右ghost
        in_edge.Q[-1] = Q_node / len(node.inflow_edges)
    
    for out_edge in node.outflow_edges:
        out_edge.h[0] = h_node  # 左ghost
        out_edge.Q[0] = Q_node
```

**优点**:
- ✅ 不修改边界条件
- ✅ 保持FVM守恒性
- ✅ 理论上质量误差应接近单渠道（0.355%）

**缺点**:
- ⚠️ 需要重写求解器（增加ghost cells）
- ⚠️ 实现复杂度中等

---

#### ✅ 方案B: 全局求解器（备选）

**核心思想**:
- 将整个网络视为一个大的求解器
- 统一编号所有单元
- 一次性求解整个网络

**实现**:
```python
class GlobalNetworkSolver:
    def __init__(self, network_topology):
        # 统一编号
        self.n_cells_total = sum([edge.n_cells for edge in edges])
        self.h_global = np.zeros(self.n_cells_total)
        self.Q_global = np.zeros(self.n_cells_total)
        
        # 构建全局通量函数
        self.build_flux_function()
    
    def build_flux_function(self):
        """构建考虑网络拓扑的全局通量"""
        # 对于每个cell，根据邻居关系计算通量
        # 节点处的cell需要特殊处理
        pass
    
    def step(self):
        """一次性更新所有单元"""
        # TVD-RK2 for全局状态向量
        pass
```

**优点**:
- ✅ 理论上完美守恒
- ✅ 统一求解

**缺点**:
- ❌ 实现复杂度高
- ❌ 需要重写大量代码
- ❌ 失去模块化优势

---

#### 🤔 方案C: 减少边界更新频率

**核心思想**:
- 每N步才更新一次边界条件
- 减少破坏守恒性的频率

**实现**:
```python
UPDATE_INTERVAL = 10  # 每10步更新一次

for step in range(max_steps):
    if step % UPDATE_INTERVAL == 0:
        update_boundary_conditions()
    
    for edge in edges:
        edge.solver.step()
```

**优点**:
- ✅ 实现简单（修改少量代码）
- ✅ 保留Phase 1架构

**缺点**:
- ⚠️ 不确定效果
- ⚠️ 可能仍有较大误差

---

## 🎯 Phase 2 实施方案

### 推荐路线: **先C后A**

**第一步**: 尝试方案C（减少更新频率）
- 预计时间: 1小时
- 快速验证是否有效
- 如果成功，问题解决✅
- 如果失败，进入第二步

**第二步**: 实现方案A（Ghost Cell）
- 预计时间: 4-6小时
- 创建`EdgeWithGhost`类
- 实现ghost cell更新逻辑
- 测试Y-split和T-junction

**备选**: 方案B（全局求解器）
- 仅当A和C都失败时考虑
- 预计时间: 1-2天

---

## 📋 详细实施步骤

### Step 1: 测试方案C（减少更新频率）

**代码修改**:
```python
# 在GodunvFVMNetworkV2中添加
self.update_interval = 10  # 可配置

def step(self):
    # 仅在特定步数更新边界
    if self.step_count % self.update_interval == 0:
        self._update_boundary_conditions_conservative()
    
    # 推进所有边
    for edge in self.edges.values():
        edge.step(self.dt)
    
    self.step_count += 1
```

**测试**:
- 串联测试（目标<5%）
- Y-split测试（目标<5%）
- T-junction测试（目标<5%）

**判断标准**:
- 如果质量误差<5%: 成功✅，继续优化
- 如果质量误差>5%: 失败❌，进入Step 2

---

### Step 2: 实现Ghost Cell方法

**新建文件**: `solvers/godunov_fvm_network_ghost.py`

**核心类**:

```python
class EdgeWithGhostCells:
    """带Ghost Cells的边"""
    
    def __init__(self, width, length, n_cells, manning_n, slope):
        # 增加2个ghost cells
        self.n_cells = n_cells
        self.n_total = n_cells + 2
        
        # 状态向量（包括ghost）
        self.h = np.zeros(self.n_total)
        self.Q = np.zeros(self.n_total)
        
        # Interior cells: [1] to [n_cells]
        # Ghost cells: [0] (left), [n_cells+1] (right)
        
        self.width = width
        self.length = length
        self.dx = length / n_cells
        self.n = manning_n
        self.S0 = slope
    
    def set_ghost_cells(self, left_h, left_Q, right_h, right_Q):
        """设置ghost cells"""
        self.h[0] = left_h
        self.Q[0] = left_Q
        self.h[-1] = right_h
        self.Q[-1] = right_Q
    
    def get_interior_state(self):
        """获取内部状态（不包括ghost）"""
        return self.h[1:-1], self.Q[1:-1]
    
    def get_left_boundary_state(self):
        """获取左边界内部单元状态"""
        return self.h[1], self.Q[1]
    
    def get_right_boundary_state(self):
        """获取右边界内部单元状态"""
        return self.h[-2], self.Q[-2]
    
    def compute_fluxes(self):
        """计算通量（使用ghost cells）"""
        fluxes = []
        for i in range(self.n_total - 1):
            # 使用HLL Riemann求解器
            F = hll_flux(self.h[i], self.Q[i], self.h[i+1], self.Q[i+1], self.width)
            fluxes.append(F)
        return np.array(fluxes)
    
    def update_interior(self, dt):
        """仅更新内部单元（不包括ghost）"""
        # TVD-RK2 for interior cells [1] to [n_cells]
        fluxes = self.compute_fluxes()
        
        for i in range(1, self.n_cells + 1):
            # 通量差
            dF = fluxes[i] - fluxes[i-1]
            
            # 源项
            S = self.compute_source(i)
            
            # 更新
            self.h[i] += dt / self.dx * (-dF[0] + S[0])
            self.Q[i] += dt / self.dx * (-dF[1] + S[1])
```

**网络求解器**:
```python
class GhostCellNetworkSolver:
    """Ghost Cell方法的网络求解器"""
    
    def __init__(self):
        self.nodes = {}
        self.edges = {}
    
    def step(self):
        # 1. 更新所有ghost cells（基于节点）
        self.update_all_ghost_cells()
        
        # 2. 推进所有边（仅更新interior）
        for edge in self.edges.values():
            edge.update_interior(self.dt)
    
    def update_all_ghost_cells(self):
        """更新所有ghost cells"""
        for node in self.nodes.values():
            if node.type == NodeType.JUNCTION:
                self.update_junction_ghost(node)
            elif node.type == NodeType.BIFURCATION:
                self.update_bifurcation_ghost(node)
            # ...
    
    def update_junction_ghost(self, node):
        """汇流节点ghost更新"""
        # 获取所有入流边的右边界内部状态
        h_list = [edge.get_right_boundary_state()[0] for edge in node.inflow_edges]
        Q_list = [edge.get_right_boundary_state()[1] for edge in node.inflow_edges]
        
        # 节点状态
        h_node = np.mean(h_list)
        Q_total = sum(Q_list)
        
        # 设置ghost cells
        # 入流边的右ghost
        for edge in node.inflow_edges:
            edge.set_ghost_cells(
                left_h=None, left_Q=None,  # 保持不变
                right_h=h_node, right_Q=Q_total / len(node.inflow_edges)
            )
        
        # 出流边的左ghost
        for edge in node.outflow_edges:
            edge.set_ghost_cells(
                left_h=h_node, left_Q=Q_total,
                right_h=None, right_Q=None  # 保持不变
            )
```

---

## 🧪 测试计划

### 测试1: 串联（最简单）

**拓扑**: A → B → C

**目标**: 质量误差 < 1%

### 测试2: Y-split（分流）

**拓扑**: A → B → (C, D)

**目标**: 质量误差 < 2%

### 测试3: T-junction（汇流）

**拓扑**: (A, B) → C → D

**目标**: 质量误差 < 2%

### 测试4: 复杂网络

**拓扑**: 多分流多汇流

**目标**: 质量误差 < 3%

---

## ✅ 成功标准

### Phase 2 完成标准

1. **串联**: 质量误差 < 1% ✅
2. **Y-split**: 质量误差 < 2% ✅
3. **T-junction**: 质量误差 < 2% ✅
4. **复杂网络**: 质量误差 < 3% ✅
5. **无NaN崩溃** ✅
6. **稳定运行500步以上** ✅

---

## 📅 时间规划

### 预计时间线

- **Step 1** (方案C测试): 1小时
- **Step 2** (Ghost Cell实现): 4-6小时
  - 设计: 1小时
  - 实现: 2-3小时
  - 调试: 1-2小时
- **Step 3** (测试验证): 2小时
- **Step 4** (文档总结): 1小时

**总计**: 8-10小时

---

## 🎯 开始执行

**立即开始**: 方案C测试

---

**Generated by**: HydroClaude Development Team  
**Date**: 2025-10-27  
**Status**: 🚀 **Phase 2 启动！**
