# HydroClaude Web Application

**React前端应用 - Phase 5.1**

---

## 📖 概述

HydroClaude的现代化Web GUI，基于React 18 + TypeScript + Vite构建。

---

## 🚀 快速开始

### 安装依赖

```bash
cd webapp
npm install
```

### 开发模式

```bash
npm run dev
```

访问: http://localhost:3000

### 构建生产版本

```bash
npm run build
```

### 预览生产构建

```bash
npm run preview
```

---

## 🏗️ 技术栈

### 核心框架
- **React 18** - UI框架
- **TypeScript** - 类型安全
- **Vite** - 构建工具

### 路由和状态
- **React Router 6** - 路由管理
- **Zustand** - 轻量级状态管理
- **TanStack Query** - 服务器状态管理

### UI组件
- **Ant Design 5** - UI组件库
- **Plotly.js** - 交互式图表
- **Leaflet** - GIS地图

### 工具库
- **Axios** - HTTP客户端
- **Day.js** - 日期处理
- **Monaco Editor** - 代码编辑器

---

## 📁 项目结构

```
webapp/
├── src/
│   ├── components/        # 可复用组件
│   │   └── Layout/        # 布局组件
│   ├── pages/             # 页面组件
│   │   ├── Home/          # 首页
│   │   ├── Projects/      # 项目管理
│   │   ├── Editor/        # 配置编辑器
│   │   ├── Simulation/    # 仿真执行
│   │   ├── Results/       # 结果查看
│   │   ├── Plugins/       # 插件市场
│   │   └── NotFound/      # 404页面
│   ├── services/          # API服务
│   │   ├── api.ts         # API客户端
│   │   └── simulations.ts # 仿真API
│   ├── stores/            # 状态管理 (待实现)
│   ├── utils/             # 工具函数 (待实现)
│   ├── assets/            # 静态资源
│   ├── App.tsx            # 应用入口
│   ├── main.tsx           # 主入口
│   └── index.css          # 全局样式
├── public/                # 公共资源
├── index.html             # HTML模板
├── package.json           # 依赖配置
├── tsconfig.json          # TS配置
├── vite.config.ts         # Vite配置
└── README.md              # 本文档
```

---

## 🎯 已实现功能

### Phase 5.1.1: 项目初始化 ✅
- [x] Vite + React + TypeScript配置
- [x] Ant Design集成
- [x] React Router配置
- [x] API客户端封装
- [x] 基础布局组件

### Phase 5.1.2: 核心页面 ✅
- [x] 首页/仪表板
- [x] 项目管理页
- [x] 配置编辑器（占位）
- [x] 仿真执行页（占位）
- [x] 结果查看器（占位）
- [x] 插件市场（占位）

---

## 🔜 待实现功能

### Phase 5.1.3: 配置编辑器 (2周)
- [ ] 可视化表单编辑器
- [ ] JSON代码编辑器（Monaco）
- [ ] 实时预览
- [ ] 配置验证
- [ ] 模板选择

### Phase 5.1.4: 结果可视化 (2周)
- [ ] Plotly图表组件
- [ ] 数据表格
- [ ] 动画播放器
- [ ] 3D水面可视化
- [ ] 导出功能

---

## 📝 开发指南

### 添加新页面

1. 在 `src/pages/` 创建页面目录
2. 创建 `index.tsx` 组件
3. 在 `App.tsx` 添加路由
4. 在 `MainLayout.tsx` 添加菜单项（如需要）

### 添加API服务

1. 在 `src/services/` 创建服务文件
2. 使用 `api.ts` 封装的方法
3. 定义TypeScript类型
4. 导出服务函数

### 添加全局状态

1. 在 `src/stores/` 创建store文件
2. 使用Zustand创建store
3. 在组件中使用hook

---

## 🔧 配置说明

### 环境变量

创建 `.env` 文件：

```env
VITE_API_BASE_URL=http://localhost:5000/api
```

### API代理

Vite开发服务器已配置代理：

```typescript
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:5000',
      changeOrigin: true,
    },
  },
}
```

---

## 🧪 测试

```bash
# 类型检查
npm run type-check

# Lint检查
npm run lint
```

---

## 📦 构建优化

### 代码分割

已配置按vendor分割：
- `react-vendor`: React核心
- `ui-vendor`: Ant Design
- `charts-vendor`: Plotly
- `maps-vendor`: Leaflet

### 生产构建

```bash
npm run build
```

构建产物在 `dist/` 目录。

---

## 🌐 部署

### 静态服务器

```bash
# 使用任何静态服务器
npx serve dist
```

### Nginx

```nginx
server {
  listen 80;
  server_name your-domain.com;
  root /path/to/dist;
  index index.html;

  location / {
    try_files $uri $uri/ /index.html;
  }

  location /api {
    proxy_pass http://localhost:5000;
  }
}
```

---

## 📚 相关文档

- [React文档](https://react.dev/)
- [TypeScript文档](https://www.typescriptlang.org/)
- [Vite文档](https://vitejs.dev/)
- [Ant Design文档](https://ant.design/)
- [Plotly.js文档](https://plotly.com/javascript/)
- [Leaflet文档](https://leafletjs.com/)

---

## 🎯 Phase 5进度

| 阶段 | 状态 | 进度 |
|------|------|------|
| 5.1.1 项目初始化 | ✅ | 100% |
| 5.1.2 核心页面 | ✅ | 100% |
| 5.1.3 配置编辑器 | 🚧 | 0% |
| 5.1.4 结果可视化 | ⏳ | 0% |
| 5.2 GIS集成 | ⏳ | 0% |
| 5.3 插件系统 | ⏳ | 0% |

---

<p align="center">
  <b>🚀 Phase 5: From CLI to Beautiful GUI 🚀</b>
</p>

---

**HydroClaude Development Team**  
**Version: 2.0.0-alpha**  
**Last Updated: November 15, 2025**
