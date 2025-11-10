# HydroClaude Web - 水力学仿真管理平台

> 基于HydroClaude引擎的商业化Web水力学管理系统

## 📋 项目结构

```
web/
├── frontend/                    # 前端应用
│   ├── src/
│   │   ├── artifacts/          # Artifacts组件库
│   │   ├── features/           # 功能模块
│   │   ├── shared/             # 共享资源
│   │   └── services/           # API服务
│   ├── public/                 # 静态资源
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.json
│
├── backend/                    # 后端服务
│   ├── api_gateway/           # API网关
│   ├── services/              # 微服务
│   │   ├── modeling_service/  # 建模服务
│   │   ├── simulation_service/# 仿真服务
│   │   ├── data_service/      # 数据服务
│   │   └── user_service/      # 用户服务
│   ├── core/                  # 核心引擎封装
│   ├── shared/                # 共享资源
│   ├── requirements.txt
│   └── pyproject.toml
│
├── docker/                    # Docker配置
│   ├── frontend.Dockerfile
│   ├── backend.Dockerfile
│   └── docker-compose.yml
│
├── k8s/                      # Kubernetes配置
│   ├── deployment.yaml
│   ├── service.yaml
│   └── ingress.yaml
│
├── scripts/                  # 工具脚本
│   ├── setup.sh             # 环境搭建
│   ├── dev.sh               # 开发启动
│   └── deploy.sh            # 部署脚本
│
└── docs/                     # 文档
    ├── architecture.md
    ├── api.md
    └── deployment.md
```

## 🚀 快速开始

### 前置要求

- Node.js >= 18.0
- Python >= 3.10
- Docker >= 20.0
- PostgreSQL >= 15
- Redis >= 7.0

### 开发环境搭建

```bash
# 1. 初始化项目
cd /home/user/HydroClaude/web
./scripts/setup.sh

# 2. 启动开发环境
./scripts/dev.sh

# 3. 访问应用
# 前端: http://localhost:3000
# 后端: http://localhost:8000
# API文档: http://localhost:8000/docs
```

### 手动启动

#### 前端开发

```bash
cd frontend
npm install
npm run dev
```

#### 后端开发

```bash
cd backend
pip install -r requirements.txt
uvicorn api_gateway.main:app --reload --host 0.0.0.0 --port 8000
```

#### 数据库

```bash
# 启动PostgreSQL和Redis
docker-compose up -d db redis

# 运行数据库迁移
cd backend
alembic upgrade head
```

## 📚 文档

- [设计方案](../WEB_SYSTEM_DESIGN_PLAN.md)
- [API规范](../WEB_API_SPECIFICATION.md)
- [开发指南](./docs/development.md)
- [部署指南](./docs/deployment.md)

## 🏗️ 开发进度

- [ ] Phase 1: 基础架构（1-3个月）
  - [ ] 前后端框架搭建
  - [ ] 数据库设计与实现
  - [ ] 核心API开发
  - [ ] 用户认证系统

- [ ] Phase 2: 核心功能（4-6个月）
  - [ ] 建模工作台
  - [ ] 仿真引擎集成
  - [ ] 基础可视化
  - [ ] 项目管理

- [ ] Phase 3: 高级功能（7-9个月）
  - [ ] 3D可视化
  - [ ] 控制系统
  - [ ] 高级分析
  - [ ] 协作功能

- [ ] Phase 4: 商业化（10-12个月）
  - [ ] 性能优化
  - [ ] 安全加固
  - [ ] 许可证系统
  - [ ] 文档培训

## 🛠️ 技术栈

### 前端
- React 18 + TypeScript
- Ant Design
- Three.js (3D可视化)
- Plotly.js (图表)
- Redux Toolkit (状态管理)
- Vite (构建工具)

### 后端
- FastAPI
- SQLAlchemy
- PostgreSQL
- Redis
- Celery (任务队列)
- MinIO (对象存储)

### DevOps
- Docker + Kubernetes
- GitHub Actions (CI/CD)
- Prometheus + Grafana (监控)

## 📝 许可证

商业专有许可证 - 详见 [LICENSE](./LICENSE)

## 📧 联系

- 技术支持: tech@hydroclaude.com
- 商务咨询: business@hydroclaude.com
