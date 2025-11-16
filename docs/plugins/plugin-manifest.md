# 插件清单规范

**版本**: 2.0.0  
**更新**: 2025-11-15

---

## 📖 概述

`plugin.json`是插件的清单文件，定义了插件的元数据、权限、贡献点和依赖关系。

---

## 📄 基本结构

### 最小示例

```json
{
  "id": "my-plugin",
  "name": "我的插件",
  "version": "1.0.0",
  "description": "插件描述",
  "author": "作者名称",
  "main": "dist/index.js",
  "permissions": [],
  "license": "MIT"
}
```

### 完整示例

```json
{
  "id": "advanced-plugin",
  "name": "高级插件",
  "version": "1.2.3",
  "description": "一个功能丰富的高级插件",
  "author": {
    "name": "张三",
    "email": "zhangsan@example.com",
    "url": "https://github.com/zhangsan"
  },
  "main": "dist/index.js",
  "icon": "icon.png",
  "homepage": "https://github.com/zhangsan/advanced-plugin",
  "repository": {
    "type": "git",
    "url": "https://github.com/zhangsan/advanced-plugin.git"
  },
  "bugs": "https://github.com/zhangsan/advanced-plugin/issues",
  "license": "MIT",
  "keywords": ["optimization", "simulation", "analysis"],
  "category": "optimization",
  "engines": {
    "hydroclaude": ">=2.0.0"
  },
  "permissions": [
    "simulation:read",
    "simulation:write",
    "ui:modify"
  ],
  "contributes": {
    "commands": [
      {
        "id": "optimize",
        "title": "运行优化",
        "category": "优化"
      }
    ],
    "settings": [
      {
        "key": "maxIterations",
        "type": "number",
        "default": 100,
        "title": "最大迭代次数"
      }
    ],
    "views": [
      {
        "id": "results-view",
        "title": "优化结果",
        "position": "sidebar"
      }
    ]
  },
  "dependencies": {
    "lodash": "^4.17.21"
  },
  "devDependencies": {
    "typescript": "^5.0.0"
  }
}
```

---

## 🔑 必需字段

### id

插件的唯一标识符。

**类型**: `string`  
**格式**: 小写字母、数字、连字符  
**示例**: `"my-plugin"`, `"data-importer-v2"`

**规则**:
- 必须全局唯一
- 只能包含小写字母、数字、连字符
- 不能以连字符开头或结尾
- 长度: 3-50个字符

```json
{
  "id": "my-awesome-plugin"
}
```

---

### name

插件的显示名称。

**类型**: `string`  
**示例**: `"数据导入插件"`

```json
{
  "name": "数据导入插件"
}
```

---

### version

插件版本号（遵循语义化版本）。

**类型**: `string`  
**格式**: `MAJOR.MINOR.PATCH`  
**示例**: `"1.2.3"`

```json
{
  "version": "1.0.0"
}
```

**版本规则**:
- MAJOR: 不兼容的API修改
- MINOR: 向下兼容的功能性新增
- PATCH: 向下兼容的bug修复

---

### description

插件的简短描述。

**类型**: `string`  
**长度**: 最多200个字符  
**示例**: `"快速导入Excel、CSV、JSON等格式的数据"`

```json
{
  "description": "快速导入Excel、CSV、JSON等格式的数据"
}
```

---

### author

插件作者信息。

**类型**: `string | object`

**字符串格式**:
```json
{
  "author": "张三 <zhangsan@example.com>"
}
```

**对象格式**:
```json
{
  "author": {
    "name": "张三",
    "email": "zhangsan@example.com",
    "url": "https://github.com/zhangsan"
  }
}
```

---

### main

插件入口文件路径。

**类型**: `string`  
**示例**: `"dist/index.js"`

```json
{
  "main": "dist/index.js"
}
```

---

### permissions

插件需要的权限列表。

**类型**: `string[]`  
**示例**: `["simulation:read", "ui:modify"]`

```json
{
  "permissions": [
    "simulation:read",
    "simulation:write",
    "ui:modify"
  ]
}
```

**可用权限**: 参见[权限列表](#权限列表)

---

### license

软件许可证。

**类型**: `string`  
**示例**: `"MIT"`, `"Apache-2.0"`, `"GPL-3.0"`

```json
{
  "license": "MIT"
}
```

**推荐许可证**:
- MIT (最宽松)
- Apache-2.0
- BSD-3-Clause
- GPL-3.0

---

## 📋 可选字段

### icon

插件图标路径。

**类型**: `string`  
**格式**: PNG, SVG  
**尺寸**: 推荐128x128或256x256  
**示例**: `"icon.png"`

```json
{
  "icon": "assets/icon.png"
}
```

---

### homepage

插件主页URL。

**类型**: `string`  
**示例**: `"https://github.com/user/plugin"`

```json
{
  "homepage": "https://github.com/user/my-plugin"
}
```

---

### repository

代码仓库信息。

**类型**: `object | string`

**对象格式**:
```json
{
  "repository": {
    "type": "git",
    "url": "https://github.com/user/plugin.git"
  }
}
```

**字符串格式**:
```json
{
  "repository": "github:user/plugin"
}
```

---

### bugs

问题跟踪URL。

**类型**: `string | object`

**字符串格式**:
```json
{
  "bugs": "https://github.com/user/plugin/issues"
}
```

**对象格式**:
```json
{
  "bugs": {
    "url": "https://github.com/user/plugin/issues",
    "email": "bugs@example.com"
  }
}
```

---

### keywords

关键词列表（用于搜索）。

**类型**: `string[]`  
**示例**: `["optimization", "data", "import"]`

```json
{
  "keywords": [
    "optimization",
    "parameter",
    "genetic-algorithm",
    "calibration"
  ]
}
```

---

### category

插件分类。

**类型**: `string`  
**可选值**: `"data"`, `"visualization"`, `"optimization"`, `"analysis"`, `"tool"`, `"other"`

```json
{
  "category": "optimization"
}
```

---

### engines

插件兼容的HydroClaude版本。

**类型**: `object`

```json
{
  "engines": {
    "hydroclaude": ">=2.0.0"
  }
}
```

**版本范围语法**:
- `>=2.0.0`: 大于等于2.0.0
- `~1.2.3`: 1.2.x (>=1.2.3, <1.3.0)
- `^1.2.3`: 1.x.x (>=1.2.3, <2.0.0)
- `1.2.3 - 2.0.0`: 范围

---

### dependencies

运行时依赖。

**类型**: `object`

```json
{
  "dependencies": {
    "lodash": "^4.17.21",
    "axios": "^1.0.0"
  }
}
```

---

### devDependencies

开发依赖。

**类型**: `object`

```json
{
  "devDependencies": {
    "typescript": "^5.0.0",
    "@types/node": "^18.0.0",
    "jest": "^29.0.0"
  }
}
```

---

## 🎁 贡献点 (contributes)

### commands

注册的命令。

**类型**: `object[]`

```json
{
  "contributes": {
    "commands": [
      {
        "id": "my-plugin.command",
        "title": "执行命令",
        "category": "我的插件",
        "icon": "play",
        "shortcut": "Ctrl+Shift+P"
      }
    ]
  }
}
```

**字段说明**:
- `id`: 命令ID（必需）
- `title`: 显示标题（必需）
- `category`: 分类（可选）
- `icon`: 图标（可选）
- `shortcut`: 快捷键（可选）

---

### settings

配置项。

**类型**: `object[]`

```json
{
  "contributes": {
    "settings": [
      {
        "key": "maxIterations",
        "type": "number",
        "default": 100,
        "title": "最大迭代次数",
        "description": "优化算法的最大迭代次数",
        "minimum": 10,
        "maximum": 1000
      },
      {
        "key": "algorithm",
        "type": "string",
        "default": "auto",
        "title": "优化算法",
        "enum": ["auto", "genetic", "gradient"],
        "enumLabels": ["自动选择", "遗传算法", "梯度下降"]
      },
      {
        "key": "enableLogging",
        "type": "boolean",
        "default": true,
        "title": "启用日志"
      }
    ]
  }
}
```

**支持的类型**:
- `number`: 数字
- `string`: 字符串
- `boolean`: 布尔值
- `array`: 数组
- `object`: 对象

**数字类型额外字段**:
- `minimum`: 最小值
- `maximum`: 最大值
- `step`: 步长

**字符串类型额外字段**:
- `enum`: 可选值列表
- `enumLabels`: 可选值标签
- `pattern`: 正则表达式
- `minLength`: 最小长度
- `maxLength`: 最大长度

---

### views

自定义视图。

**类型**: `object[]`

```json
{
  "contributes": {
    "views": [
      {
        "id": "my-view",
        "title": "我的视图",
        "position": "sidebar",
        "icon": "chart",
        "initialVisibility": "visible"
      }
    ]
  }
}
```

**字段说明**:
- `position`: `"sidebar"`, `"panel"`, `"modal"`
- `initialVisibility`: `"visible"`, `"hidden"`, `"collapsed"`

---

### menus

菜单项。

**类型**: `object`

```json
{
  "contributes": {
    "menus": {
      "toolbar": [
        {
          "command": "my-plugin.action",
          "group": "1_edit",
          "when": "editorTextFocus"
        }
      ],
      "contextMenu": [
        {
          "command": "my-plugin.action",
          "group": "navigation"
        }
      ]
    }
  }
}
```

---

### charts

图表类型。

**类型**: `object[]`

```json
{
  "contributes": {
    "charts": [
      {
        "type": "heatmap",
        "title": "热力图",
        "icon": "chart-heatmap",
        "description": "显示2D数据的热力分布"
      }
    ]
  }
}
```

---

## 🔒 权限列表

### 仿真权限

```json
"simulation:read"      // 读取仿真配置和结果
"simulation:write"     // 修改仿真配置
"simulation:execute"   // 执行仿真
"simulation:stop"      // 停止仿真
"simulation:delete"    // 删除仿真结果
```

### 数据权限

```json
"data:read"      // 读取数据文件
"data:write"     // 写入数据文件
"data:delete"    // 删除数据文件
"data:import"    // 导入数据
"data:export"    // 导出数据
```

### UI权限

```json
"ui:modify"      // 修改UI（添加按钮、面板等）
"ui:theme"       // 修改主题
```

### 文件系统权限

```json
"filesystem:read"      // 读取文件
"filesystem:write"     // 写入文件
"filesystem:delete"    // 删除文件
```

### 网络权限

```json
"network:request"      // 发送HTTP请求
```

---

## ✅ 验证清单

发布前检查：

- [ ] 所有必需字段都已填写
- [ ] `id`全局唯一且格式正确
- [ ] `version`遵循语义化版本
- [ ] `description`清晰准确
- [ ] `permissions`最小化
- [ ] `main`指向正确的入口文件
- [ ] `license`已指定
- [ ] `keywords`有助于搜索
- [ ] JSON格式正确（无语法错误）

---

## 🔧 验证工具

### 命令行验证

```bash
# 验证清单文件
npx jsonlint plugin.json

# 使用HydroClaude CLI验证
hydroclaude-cli validate plugin.json
```

### 编程验证

```typescript
import { validateManifest } from '@hydroclaude/plugin-validator';

const manifest = require('./plugin.json');
const errors = validateManifest(manifest);

if (errors.length > 0) {
  console.error('清单验证失败:', errors);
} else {
  console.log('清单验证通过');
}
```

---

## 📚 相关文档

- [快速入门](./getting-started.md)
- [API参考](./api-reference.md)
- [最佳实践](./best-practices.md)
- [FAQ](./faq.md)

---

<p align="center">
  <b>规范的清单文件是高质量插件的基础</b>
</p>
