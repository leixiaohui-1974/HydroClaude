# 配置编辑器组件

**Phase 5.1.3 完成**

---

## 📖 概述

配置编辑器是HydroClaude Web应用的核心功能，提供了三种方式编辑仿真配置：
1. **表单编辑器** - 可视化表单，无需了解JSON
2. **JSON编辑器** - Monaco编辑器，支持语法高亮和验证
3. **配置预览** - 实时查看配置摘要和派生信息

---

## 🏗️ 组件结构

```
ConfigEditor/
├── index.tsx           主编辑器组件
├── ConfigPreview.tsx   配置预览组件
└── README.md           本文档

FormEditor/
└── index.tsx           表单编辑器组件

JsonEditor/
└── index.tsx           JSON编辑器组件
```

---

## 🎯 功能特性

### 1. 表单编辑器 (FormEditor)

**功能**:
- ✅ 可视化表单编辑
- ✅ 实时表单验证
- ✅ 响应式布局（移动端友好）
- ✅ 动态添加/删除水工结构

**支持的配置项**:
- 仿真设置（类型、模式）
- 渠道参数（长度、宽度、坡度、Manning系数）
- 求解器设置（求解方法）
- 边界条件（上游、下游）
- 水工结构（闸门、堰、孔板）

**表单验证规则**:
```typescript
- 渠道长度: >= 1 m
- 渠道宽度: >= 0.1 m
- 渠道坡度: >= 0.0001
- Manning系数: 0.01 - 0.1
- 边界值: >= 0
```

### 2. JSON编辑器 (JsonEditor)

**功能**:
- ✅ Monaco编辑器集成
- ✅ 语法高亮
- ✅ 自动补全
- ✅ JSON Schema验证
- ✅ 实时错误提示
- ✅ 代码格式化（Ctrl/Cmd + S）

**编辑器选项**:
```typescript
{
  minimap: true,          // 小地图
  fontSize: 14,           // 字体大小
  lineNumbers: 'on',      // 行号
  wordWrap: 'on',         // 自动换行
  formatOnPaste: true,    // 粘贴时格式化
  formatOnType: true,     // 输入时格式化
  theme: 'vs-dark',       // 深色主题
}
```

### 3. 配置预览 (ConfigPreview)

**功能**:
- ✅ 配置摘要展示
- ✅ 派生信息计算（网格数、Froude数等）
- ✅ 流态判断（缓流/急流/临界流）
- ✅ 预估运行时间
- ✅ 配置检查和警告

**显示信息**:
- 仿真设置（类型、模式、求解方法）
- 渠道参数（长度、宽度、坡度等）
- 边界条件（上下游边界）
- 水工结构（如有）
- 水力学分析（Froude数、流态）

---

## 💻 使用方法

### 基础使用

```typescript
import ConfigEditor from '@/components/ConfigEditor';

const MyPage = () => {
  const handleSave = (config) => {
    console.log('保存配置:', config);
  };

  const handleRun = (config) => {
    console.log('运行仿真:', config);
  };

  return (
    <ConfigEditor
      initialConfig={myConfig}
      onSave={handleSave}
      onRun={handleRun}
    />
  );
};
```

### Props

#### ConfigEditor

| 属性 | 类型 | 必需 | 说明 |
|------|------|------|------|
| initialConfig | SimulationConfig | 否 | 初始配置（不提供则使用默认配置） |
| onSave | (config) => void | 否 | 保存回调 |
| onRun | (config) => void | 否 | 运行回调 |

#### FormEditor

| 属性 | 类型 | 必需 | 说明 |
|------|------|------|------|
| config | SimulationConfig | 是 | 当前配置 |
| onChange | (config) => void | 是 | 配置变化回调 |

#### JsonEditor

| 属性 | 类型 | 必需 | 说明 |
|------|------|------|------|
| config | SimulationConfig | 是 | 当前配置 |
| onChange | (config) => void | 是 | 配置变化回调 |
| height | string | 否 | 编辑器高度 |

#### ConfigPreview

| 属性 | 类型 | 必需 | 说明 |
|------|------|------|------|
| config | SimulationConfig | 是 | 要预览的配置 |

---

## 🔄 数据流

```
用户输入
    ↓
表单编辑器 / JSON编辑器
    ↓
onChange回调
    ↓
ConfigEditor状态更新
    ↓
ConfigPreview实时更新
    ↓
用户点击"保存" / "运行"
    ↓
配置验证
    ↓
onSave / onRun回调
```

---

## 🎨 UI截图

### 表单编辑器
```
┌─────────────────────────────────────────────┐
│ 工具栏: [保存配置] [运行仿真] [验证配置]    │
├─────────────────────────────────────────────┤
│ [表单编辑器] [JSON编辑器] [预览]            │
├─────────────────────────────────────────────┤
│ 仿真设置                                    │
│ ├─ 仿真类型: [稳态流 ▼]                    │
│ └─ 仿真模式: [单一渠道 ▼]                  │
│                                              │
│ 渠道参数                                    │
│ ├─ 长度: [1000] m                          │
│ ├─ 宽度: [10] m                            │
│ ├─ 坡度: [0.001]                           │
│ └─ Manning系数: [0.025]                    │
│                                              │
│ ...                                         │
└─────────────────────────────────────────────┘
```

### JSON编辑器
```
┌─────────────────────────────────────────────┐
│ [表单编辑器] [JSON编辑器] [预览]            │
├─────────────────────────────────────────────┤
│  1  {                                       │
│  2    "simulation": {                       │
│  3      "type": "steady",                   │
│  4      "mode": "single_canal"              │
│  5    },                                    │
│  6    "canal": {                            │
│  7      "length": 1000,                     │
│  8      "width": 10,                        │
│  9      ...                                 │
│     }                                       │
│  }                                          │
└─────────────────────────────────────────────┘
```

---

## 🧪 配置验证

### 客户端验证

```typescript
// 长度检查
if (config.canal.length <= 0) {
  return '渠道长度必须大于0';
}

// 范围检查
if (config.canal.manning_n < 0.01 || config.canal.manning_n > 0.1) {
  return 'Manning系数范围: 0.01-0.1';
}

// 必填检查
if (!config.canal.width) {
  return '请输入渠道宽度';
}
```

### JSON Schema验证

```json
{
  "type": "object",
  "properties": {
    "canal": {
      "type": "object",
      "properties": {
        "length": { "type": "number", "minimum": 1 },
        "width": { "type": "number", "minimum": 0.1 },
        "slope": { "type": "number", "minimum": 0.0001 },
        "manning_n": { 
          "type": "number", 
          "minimum": 0.01, 
          "maximum": 0.1 
        }
      },
      "required": ["length", "width", "slope", "manning_n"]
    }
  }
}
```

---

## 🎯 默认配置

```json
{
  "simulation": {
    "type": "steady",
    "mode": "single_canal"
  },
  "canal": {
    "length": 1000,
    "width": 10,
    "slope": 0.001,
    "manning_n": 0.025
  },
  "solver": {
    "method": "hydrostatic"
  },
  "boundary_conditions": {
    "upstream": {
      "type": "flow",
      "value": 8.0
    },
    "downstream": {
      "type": "depth",
      "method": "uniform_flow"
    }
  }
}
```

---

## 🔧 扩展指南

### 添加新的配置项

1. **更新类型定义** (`services/simulations.ts`)
```typescript
export interface SimulationConfig {
  // 添加新字段
  new_field?: string;
}
```

2. **添加表单字段** (`FormEditor/index.tsx`)
```tsx
<Form.Item label="新字段" name="new_field">
  <Input />
</Form.Item>
```

3. **更新JSON Schema** (`JsonEditor/index.tsx`)
```typescript
schema: {
  properties: {
    new_field: { type: 'string' }
  }
}
```

4. **添加预览显示** (`ConfigPreview.tsx`)
```tsx
<Descriptions.Item label="新字段">
  {config.new_field}
</Descriptions.Item>
```

---

## 💡 最佳实践

### 1. 表单验证
- 使用Ant Design的Form.Item rules
- 提供清晰的错误提示
- 实时验证用户输入

### 2. JSON编辑
- 启用JSON Schema验证
- 提供代码补全
- 格式化快捷键

### 3. 用户体验
- 三种编辑方式无缝切换
- 配置自动同步
- 提供默认值和提示

### 4. 性能优化
- 使用React.memo优化组件
- 防抖处理onChange事件
- 延迟加载Monaco编辑器

---

## 🐛 常见问题

### Q1: Monaco编辑器不显示？
A: 确保安装了 `@monaco-editor/react`：
```bash
npm install @monaco-editor/react
```

### Q2: 表单和JSON编辑器不同步？
A: 检查onChange回调是否正确触发，确保没有循环更新。

### Q3: 配置验证不生效？
A: 检查JSON Schema配置是否正确，Monaco编辑器需要正确的schema设置。

---

## 📚 相关文档

- [Ant Design Form](https://ant.design/components/form)
- [Monaco Editor](https://microsoft.github.io/monaco-editor/)
- [JSON Schema](https://json-schema.org/)

---

<p align="center">
  <b>配置编辑器 - Phase 5.1.3 Complete</b>
</p>
