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

- Python >= 3.10
- FastAPI, uvicorn, pydantic, httpx (已安装)

### 启动后端API服务器

```bash
# 方法1: 使用启动脚本（推荐）
cd /home/user/HydroClaude/web/backend
./start_server.sh --reload

# 方法2: 直接运行
cd /home/user/HydroClaude/web/backend/api_gateway
python main.py

# 方法3: 使用uvicorn
cd /home/user/HydroClaude/web/backend/api_gateway
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 访问API文档

服务器启动后，打开浏览器访问：
- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc
- **健康检查**: http://localhost:8000/health

### 运行测试

```bash
cd /home/user/HydroClaude/web/backend/api_gateway
python test_api.py
```

### API使用示例

#### 创建仿真任务

```bash
curl -X POST "http://localhost:8000/api/v1/simulations" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Uniform Flow Test",
    "config": {
      "width": 10.0,
      "length": 1000.0,
      "n_cells": 100,
      "t_end": 10.0,
      "initial_conditions": {
        "type": "uniform",
        "h": 5.0,
        "Q": 0.0
      }
    }
  }'
```

#### 查询结果

```bash
# 获取task_id后查询结果
curl "http://localhost:8000/api/v1/simulations/{task_id}/results"
```

## 📚 文档

- [设计方案](../WEB_SYSTEM_DESIGN_PLAN.md)
- [API规范](../WEB_API_SPECIFICATION.md)
- [开发指南](./docs/development.md)
- [部署指南](./docs/deployment.md)

## 🏗️ 开发进度

### ✅ Milestone 1.1: 技术验证（Week 1-2）- **已完成**

- ✅ 核心引擎封装（`web/backend/core/hydraulic_engine.py`）
- ✅ FastAPI基础框架（`web/backend/api_gateway/main.py`）
- ✅ 仿真API端点（5个端点全部实现）
- ✅ Pydantic数据模型（8个模型定义）
- ✅ 集成测试（7/7 测试通过）
- ✅ 端到端验证（质量守恒误差 0.00e+00）

**详细报告**: [MILESTONE_1.1_COMPLETED.md](backend/MILESTONE_1.1_COMPLETED.md)

### 🔄 Milestone 1.2: MVP - 明渠基础（Week 3-6）- **进行中**

- [ ] 前端React项目搭建
- [ ] 仿真配置界面
- [ ] 结果可视化（2D图表）
- [ ] 数据持久化（SQLite/PostgreSQL）
- [ ] 任务队列（Celery）
- [ ] 3个标准测试案例通过

### 📋 后续里程碑

- [ ] Milestone 1.3-1.7: 明渠高级功能、管道、混合系统、3D可视化
- [ ] Phase 2: 全面测试与验证（65个测试案例）
- [ ] Phase 3: 控制系统
- [ ] Phase 4: 辨识系统

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
