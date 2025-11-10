# HydroClaude Web Frontend

React前端应用，用于水力学仿真管理。

## 技术栈

- **React 18** - UI框架
- **TypeScript** - 类型安全
- **Vite** - 构建工具
- **Ant Design** - UI组件库
- **Plotly.js** - 数据可视化
- **Axios** - HTTP客户端

## 快速开始

### 1. 安装依赖

```bash
cd /home/user/HydroClaude/web/frontend
npm install
```

### 2. 启动开发服务器

```bash
npm run dev
```

前端将在 http://localhost:5173 启动

### 3. 确保后端运行

前端需要连接到后端API服务器（默认 http://localhost:8000）

```bash
# 在另一个终端
cd /home/user/HydroClaude/web/backend
./start_server.sh --reload
```

## 项目结构

```
src/
├── main.tsx              # 应用入口
├── App.tsx               # 主应用组件
├── features/             # 功能模块
│   └── simulation/       # 仿真功能
│       ├── SimulationWorkspace.tsx      # 工作区
│       ├── SimulationConfigForm.tsx     # 配置表单
│       └── SimulationResults.tsx        # 结果展示
└── services/             # 服务层
    └── api.ts            # API客户端
```

## 功能特性

### 仿真配置
- 几何参数配置（宽度、长度、网格数）
- 物理参数配置（曼宁糙率、底坡）
- 初始条件设置（均匀流、溃坝）
- 边界条件设置
- 时间参数配置

### 结果可视化
- 实时水深分布图
- 流速分布图
- 流量分布图
- 时间滑块控制
- 性能指标展示

### 用户体验
- 响应式布局
- 表单验证
- 加载状态提示
- 错误处理
- 进度显示

## 开发命令

```bash
# 开发模式（热重载）
npm run dev

# 构建生产版本
npm run build

# 预览生产构建
npm run preview

# 代码检查
npm run lint
```

## 环境变量

创建 `.env` 文件配置环境变量：

```env
VITE_API_URL=http://localhost:8000
```

## API集成

前端通过 `src/services/api.ts` 与后端通信：

- 健康检查
- 引擎信息
- 创建仿真
- 查询状态
- 获取结果
- 列出任务
- 删除任务

所有API调用都经过类型检查和错误处理。

## 浏览器支持

- Chrome (推荐)
- Firefox
- Safari
- Edge

需要支持 ES2020 特性。
