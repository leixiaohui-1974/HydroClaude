# Milestone 1.3 开发计划 - 可视化建模工作台

> **版本**: v1.0
> **日期**: 2025-11-10
> **里程碑**: 可视化建模工作台 (Week 7-10)
> **状态**: 🚧 **开发中**

---

## 📋 目标概览

### 核心目标
实现**可视化拖拽建模工作台**,让用户通过图形化界面构建水力学模型,替代当前的手动配置方式。

### 功能范围

#### 本期实现 (Milestone 1.3)
1. ✅ **拖拽式组件库**
   - 明渠组件 (矩形渠道、梯形渠道)
   - 水工建筑物 (闸门、堰)
   - 边界条件 (恒定流量、恒定水位)
   - 组件参数配置面板

2. ✅ **可视化画布**
   - React-Flow画布集成
   - 缩放、平移、网格
   - 组件拖拽添加
   - 连线建立

3. ✅ **状态管理**
   - Redux Toolkit状态集中管理
   - 模型配置持久化
   - Undo/Redo功能

4. ✅ **模型验证**
   - 拓扑验证 (连通性检查)
   - 参数合理性检查
   - 实时验证反馈

5. ✅ **导入导出**
   - JSON格式模型保存
   - 模型加载
   - 配置转换 (图形模型 → 仿真配置)

#### 后续实现 (Milestone 1.4+)
- 更多组件类型 (管道、泵站、水库)
- 复杂网络拓扑
- 3D可视化
- 模板库和案例库

---

## 🏗️ 技术架构

### 1. 技术栈选择

| 技术 | 版本 | 用途 | 理由 |
|-----|------|------|------|
| **React-Flow** | 11.10.1 | 可视化画布 | 成熟的流程图库,支持拖拽、缩放、连线 |
| **Redux Toolkit** | 2.0.1 | 状态管理 | 简化Redux使用,集成Immer |
| **React Hook Form** | 7.49.2 | 表单管理 | 高性能,少重渲染 |
| **Zod** | 3.22.4 | 数据验证 | TypeScript友好,运行时类型检查 |
| **@dnd-kit** | 6.1.0 | 拖拽功能 | 现代化拖拽库,可访问性好 |

### 2. 目录结构

```
frontend/src/
├── features/
│   ├── modeling/                      # 建模工作台模块
│   │   ├── components/                # 组件
│   │   │   ├── ModelCanvas.tsx        # 画布主组件
│   │   │   ├── ComponentPalette.tsx   # 组件面板
│   │   │   ├── PropertyPanel.tsx      # 属性面板
│   │   │   ├── ToolBar.tsx            # 工具栏
│   │   │   └── nodes/                 # 自定义节点
│   │   │       ├── CanalNode.tsx      # 明渠节点
│   │   │       ├── GateNode.tsx       # 闸门节点
│   │   │       └── BoundaryNode.tsx   # 边界节点
│   │   ├── hooks/                     # 自定义Hooks
│   │   │   ├── useModelValidation.ts  # 模型验证
│   │   │   ├── useModelExport.ts      # 导出逻辑
│   │   │   └── useUndoRedo.ts         # 撤销重做
│   │   ├── store/                     # Redux状态
│   │   │   ├── modelSlice.ts          # 模型状态切片
│   │   │   └── selectors.ts           # 选择器
│   │   ├── types/                     # 类型定义
│   │   │   └── model.types.ts         # 模型类型
│   │   └── utils/                     # 工具函数
│   │       ├── validator.ts           # 验证器
│   │       └── converter.ts           # 配置转换器
│   └── simulation/                    # 仿真管理 (已有)
└── shared/
    ├── store/                         # 全局Store
    │   └── index.ts                   # Store配置
    └── types/                         # 共享类型
        └── index.ts
```

### 3. 数据模型设计

#### 3.1 模型节点 (Node)

```typescript
// 节点基础类型
interface BaseNode {
  id: string;                    // 唯一标识
  type: NodeType;                // 节点类型
  position: { x: number; y: number };
  data: NodeData;                // 节点数据
}

// 节点类型枚举
enum NodeType {
  CANAL = 'canal',               // 明渠
  GATE = 'gate',                 // 闸门
  WEIR = 'weir',                 // 堰
  BOUNDARY_FLOW = 'boundary_flow',     // 流量边界
  BOUNDARY_DEPTH = 'boundary_depth'    // 水深边界
}

// 明渠节点数据
interface CanalNodeData {
  name: string;
  width: number;                 // 宽度 (m)
  length: number;                // 长度 (m)
  slope: number;                 // 坡度
  manning_n: number;             // 曼宁系数
  n_cells: number;               // 网格数
  validated: boolean;            // 验证状态
  errors: string[];              // 错误信息
}

// 闸门节点数据
interface GateNodeData {
  name: string;
  opening: number;               // 开度 (0-1)
  discharge_coeff: number;       // 流量系数
  width: number;                 // 闸门宽度 (m)
}

// 边界条件节点数据
interface BoundaryNodeData {
  name: string;
  boundary_type: 'flow' | 'depth';
  value: number;                 // 边界值
  time_series?: Array<{t: number; value: number}>; // 时间序列 (可选)
}
```

#### 3.2 模型连接 (Edge)

```typescript
interface ModelEdge {
  id: string;
  source: string;                // 源节点ID
  target: string;                // 目标节点ID
  type: 'default' | 'smoothstep';
  validated: boolean;            // 验证状态
}
```

#### 3.3 完整模型

```typescript
interface HydraulicModel {
  id: string;
  name: string;
  description: string;
  nodes: BaseNode[];
  edges: ModelEdge[];
  created_at: string;
  updated_at: string;
  version: number;
  validated: boolean;
  validation_errors: ValidationError[];
}

interface ValidationError {
  type: 'topology' | 'parameter' | 'physics';
  severity: 'error' | 'warning';
  node_id?: string;
  edge_id?: string;
  message: string;
}
```

---

## 🎨 UI/UX 设计

### 1. 整体布局

```
┌────────────────────────────────────────────────────────────────┐
│  [HydroClaude Web]  项目: 城市供水系统   [保存] [导出] [运行]  │
├──────────┬───────────────────────────────────────┬─────────────┤
│          │                                       │             │
│ 组件库    │         画布区域 (React-Flow)         │  属性面板   │
│          │                                       │             │
│ ┌──────┐ │  ┌─────┐       ┌─────┐               │ ┌─────────┐ │
│ │明渠   │ │  │边界 │───────│明渠 │───┐          │ │节点属性 │ │
│ │      │ │  └─────┘       └─────┘   │          │ │         │ │
│ │拖拽→ │ │                           │          │ │名称:    │ │
│ └──────┘ │                           ↓          │ │明渠1    │ │
│          │                      ┌─────┐         │ │         │ │
│ ┌──────┐ │                      │闸门 │         │ │长度:    │ │
│ │闸门   │ │                      └─────┘         │ │1000 m   │ │
│ │      │ │                           │          │ │         │ │
│ └──────┘ │                           ↓          │ │宽度:    │ │
│          │                      ┌─────┐         │ │10 m     │ │
│ ┌──────┐ │                      │边界 │         │ │         │ │
│ │边界   │ │                      └─────┘         │ └─────────┘ │
│ │      │ │                                       │             │
│ └──────┘ │  [缩放 100%] [网格] [对齐] [撤销]    │ [验证模型]  │
└──────────┴───────────────────────────────────────┴─────────────┘
```

### 2. 交互流程

```
用户操作流程:
1. 从组件库拖拽组件到画布
   ↓
2. 点击节点显示属性面板
   ↓
3. 编辑参数 (实时验证)
   ↓
4. 连接节点建立拓扑
   ↓
5. 验证模型 (拓扑+参数)
   ↓
6. 导出/运行仿真
```

### 3. 组件样式

- **明渠节点**: 蓝色矩形,显示名称和主要参数
- **闸门节点**: 橙色菱形,显示开度
- **边界节点**: 绿色圆形,显示边界类型和值
- **连线**: 灰色实线,验证失败时红色虚线
- **选中状态**: 蓝色高亮边框

---

## 🔧 实施计划

### Phase 1: 基础框架搭建 (Day 1-2)

**目标**: 搭建建模工作台基础架构

**任务**:
1. 安装依赖包
   ```bash
   npm install reactflow @reduxjs/toolkit react-redux
   npm install react-hook-form zod @hookform/resolvers
   npm install @dnd-kit/core @dnd-kit/sortable
   ```

2. 创建目录结构
   - features/modeling/ 完整目录
   - Redux store配置

3. 定义TypeScript类型
   - model.types.ts 完整类型定义

4. 基础组件框架
   - ModelCanvas.tsx (空白画布)
   - ComponentPalette.tsx (组件列表)
   - PropertyPanel.tsx (空属性面板)

**验收标准**:
- ✅ 依赖安装成功
- ✅ 目录结构完整
- ✅ TypeScript无编译错误
- ✅ 基础页面可访问

### Phase 2: React-Flow画布集成 (Day 3-4)

**目标**: 实现可拖拽的流程图画布

**任务**:
1. React-Flow基础配置
   - 画布初始化
   - 缩放、平移、网格功能
   - 工具栏 (放大、缩小、居中)

2. 自定义节点组件
   - CanalNode.tsx (明渠节点)
   - GateNode.tsx (闸门节点)
   - BoundaryNode.tsx (边界节点)

3. 拖拽功能
   - 从组件面板拖拽到画布
   - 添加节点到模型

4. 连线功能
   - 节点间连线
   - 连线样式定制

**验收标准**:
- ✅ 可拖拽组件到画布
- ✅ 可在节点间建立连接
- ✅ 缩放、平移流畅 (60fps)
- ✅ 节点显示正确样式

### Phase 3: Redux状态管理 (Day 5-6)

**目标**: 实现完整的状态管理和Undo/Redo

**任务**:
1. Redux Slice定义
   - modelSlice.ts (模型状态)
   - Actions: addNode, removeNode, updateNode, addEdge, etc.

2. 选择器 (Selectors)
   - 获取所有节点
   - 获取选中节点
   - 获取验证状态

3. Undo/Redo功能
   - 历史记录管理
   - 快捷键绑定 (Ctrl+Z, Ctrl+Y)

4. 持久化
   - LocalStorage自动保存
   - 项目加载/保存

**验收标准**:
- ✅ 所有操作可撤销/重做
- ✅ 状态变化实时反映到UI
- ✅ 刷新页面后状态保留
- ✅ Redux DevTools可正常使用

### Phase 4: 属性面板与验证 (Day 7-8)

**目标**: 实现参数配置和实时验证

**任务**:
1. 属性面板动态表单
   - 根据节点类型显示不同表单
   - React Hook Form集成
   - 表单联动和计算

2. Zod验证规则
   - 参数范围验证
   - 必填字段检查
   - 物理合理性验证

3. 实时验证反馈
   - 输入时即时验证
   - 错误信息显示
   - 节点状态标记

4. 模型级验证
   - 拓扑连通性检查
   - 边界条件完整性
   - 物理一致性检查

**验收标准**:
- ✅ 参数修改实时生效
- ✅ 无效输入立即提示
- ✅ 验证错误清晰可见
- ✅ 模型验证准确率 >95%

### Phase 5: 导入导出与集成 (Day 9-10)

**目标**: 实现模型保存和与仿真系统集成

**任务**:
1. JSON导出
   - 图形模型序列化
   - 下载为JSON文件

2. JSON导入
   - 文件选择和解析
   - 模型重建

3. 配置转换器
   - 图形模型 → SimulationRequest
   - 自动生成网格、边界条件配置

4. 与仿真系统集成
   - 从建模工作台启动仿真
   - 结果反馈到模型

5. 测试与文档
   - 单元测试
   - 集成测试
   - 用户文档

**验收标准**:
- ✅ 模型可保存为JSON
- ✅ JSON可正确加载
- ✅ 转换器生成有效配置
- ✅ 可成功运行仿真
- ✅ 测试覆盖率 >80%

---

## 📊 验收标准

### 功能性验收

| 功能 | 验收标准 |
|-----|---------|
| **组件拖拽** | 3种组件可拖拽,位置准确 |
| **节点编辑** | 参数修改实时生效,验证正确 |
| **连线** | 可建立连接,拓扑正确 |
| **撤销重做** | 所有操作可撤销,历史正确 |
| **验证** | 错误率<5%,无误报 |
| **导出** | JSON格式正确,可重新加载 |
| **集成** | 可启动仿真,结果正确 |

### 性能验收

| 指标 | 目标值 |
|-----|--------|
| **画布渲染** | 50个节点 >30fps |
| **操作响应** | 点击响应 <100ms |
| **验证速度** | 复杂模型 <1s |
| **保存加载** | 大模型 <2s |

### 用户体验验收

- ✅ 新用户5分钟内学会基本操作
- ✅ 标准案例建模 <3分钟
- ✅ 无明显Bug或卡顿
- ✅ 错误提示清晰易懂

---

## 🎯 成功指标

### 定量指标
- 组件库: 5种组件
- 验证规则: 15条
- 代码行数: ~2000行 (前端)
- 测试覆盖率: >80%

### 定性指标
- 用户体验流畅
- 界面美观专业
- 错误提示友好
- 代码质量高

---

## 🚀 后续规划 (Milestone 1.4)

1. **更多组件**
   - 管道组件
   - 泵站、水库
   - 复合断面明渠

2. **高级功能**
   - 组件模板库
   - 批量操作
   - 快捷键系统

3. **可视化增强**
   - 3D预览
   - 动画演示
   - 剖面图

4. **协作功能**
   - 多人编辑
   - 评论系统
   - 版本对比

---

## 📝 开发日志

### 2025-11-10
- ✅ 创建Milestone 1.3开发计划
- 🚧 开始Phase 1: 基础框架搭建

---

**文档版本**: v1.0
**最后更新**: 2025-11-10
**下次评审**: 完成Phase 1后
