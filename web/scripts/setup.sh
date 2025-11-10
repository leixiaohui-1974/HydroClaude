#!/bin/bash
# HydroClaude Web - 项目初始化脚本

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}HydroClaude Web 项目初始化${NC}"
echo -e "${GREEN}================================${NC}"
echo ""

# 检查前置条件
echo -e "${YELLOW}[1/8] 检查前置条件...${NC}"

# 检查Node.js
if ! command -v node &> /dev/null; then
    echo -e "${RED}错误: 未安装Node.js，请先安装Node.js >= 18.0${NC}"
    exit 1
fi
NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    echo -e "${RED}错误: Node.js版本过低，需要 >= 18.0，当前版本: $(node -v)${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Node.js 版本: $(node -v)${NC}"

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}错误: 未安装Python3，请先安装Python >= 3.10${NC}"
    exit 1
fi
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo -e "${GREEN}✓ Python 版本: $PYTHON_VERSION${NC}"

# 检查Docker
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}警告: 未安装Docker，某些功能可能无法使用${NC}"
else
    echo -e "${GREEN}✓ Docker 版本: $(docker --version | cut -d' ' -f3 | sed 's/,//')${NC}"
fi

echo ""

# 创建目录结构
echo -e "${YELLOW}[2/8] 创建项目目录结构...${NC}"

mkdir -p web/frontend/src/{artifacts,features,shared,services}
mkdir -p web/frontend/public
mkdir -p web/backend/{api_gateway,services,core,shared}
mkdir -p web/backend/services/{modeling_service,simulation_service,data_service,user_service}
mkdir -p web/docker
mkdir -p web/k8s
mkdir -p web/scripts
mkdir -p web/docs
mkdir -p web/tests/{frontend,backend}

echo -e "${GREEN}✓ 目录结构创建完成${NC}"
echo ""

# 初始化前端
echo -e "${YELLOW}[3/8] 初始化前端项目...${NC}"

cd web/frontend

if [ ! -f "package.json" ]; then
    cat > package.json <<EOF
{
  "name": "hydroclaude-web-frontend",
  "version": "1.0.0",
  "description": "HydroClaude Web Frontend",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "lint": "eslint . --ext ts,tsx --report-unused-disable-directives --max-warnings 0",
    "test": "vitest"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.0",
    "antd": "^5.11.0",
    "@reduxjs/toolkit": "^1.9.7",
    "react-redux": "^8.1.3",
    "three": "^0.159.0",
    "@react-three/fiber": "^8.15.11",
    "@react-three/drei": "^9.88.17",
    "plotly.js": "^2.27.1",
    "react-plotly.js": "^2.6.0",
    "reactflow": "^11.10.1",
    "react-hook-form": "^7.48.2",
    "zod": "^3.22.4",
    "axios": "^1.6.2"
  },
  "devDependencies": {
    "@types/react": "^18.2.37",
    "@types/react-dom": "^18.2.15",
    "@typescript-eslint/eslint-plugin": "^6.10.0",
    "@typescript-eslint/parser": "^6.10.0",
    "@vitejs/plugin-react": "^4.2.0",
    "typescript": "^5.2.2",
    "vite": "^5.0.0",
    "vitest": "^1.0.0",
    "eslint": "^8.53.0",
    "eslint-plugin-react-hooks": "^4.6.0",
    "eslint-plugin-react-refresh": "^0.4.4"
  }
}
EOF
    echo -e "${GREEN}✓ package.json 创建完成${NC}"
else
    echo -e "${YELLOW}  package.json 已存在，跳过${NC}"
fi

# 创建 vite.config.ts
if [ ! -f "vite.config.ts" ]; then
    cat > vite.config.ts <<EOF
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      }
    }
  }
})
EOF
    echo -e "${GREEN}✓ vite.config.ts 创建完成${NC}"
fi

# 创建 tsconfig.json
if [ ! -f "tsconfig.json" ]; then
    cat > tsconfig.json <<EOF
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"]
    }
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
EOF
    echo -e "${GREEN}✓ tsconfig.json 创建完成${NC}"
fi

echo -e "${GREEN}✓ 前端项目初始化完成${NC}"
echo ""

cd ../..

# 初始化后端
echo -e "${YELLOW}[4/8] 初始化后端项目...${NC}"

cd web/backend

if [ ! -f "requirements.txt" ]; then
    cat > requirements.txt <<EOF
# Web框架
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6

# 数据库
sqlalchemy==2.0.23
alembic==1.12.1
psycopg2-binary==2.9.9
asyncpg==0.29.0

# 验证
pydantic==2.5.0
pydantic-settings==2.1.0
email-validator==2.1.0

# 认证
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6

# 缓存和任务队列
redis==5.0.1
celery==5.3.4

# 对象存储
minio==7.2.0

# 监控
prometheus-client==0.19.0

# 工具
python-dotenv==1.0.0
httpx==0.25.2

# HydroClaude核心依赖
numpy>=1.24.0
scipy>=1.11.0
matplotlib>=3.7.0
numba>=0.58.0

# 测试
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
httpx==0.25.2
EOF
    echo -e "${GREEN}✓ requirements.txt 创建完成${NC}"
fi

# 创建 pyproject.toml
if [ ! -f "pyproject.toml" ]; then
    cat > pyproject.toml <<EOF
[build-system]
requires = ["setuptools>=65.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "hydroclaude-web-backend"
version = "1.0.0"
description = "HydroClaude Web Backend Services"
requires-python = ">=3.10"

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
EOF
    echo -e "${GREEN}✓ pyproject.toml 创建完成${NC}"
fi

echo -e "${GREEN}✓ 后端项目初始化完成${NC}"
echo ""

cd ../..

# 创建Docker配置
echo -e "${YELLOW}[5/8] 创建Docker配置...${NC}"

cd web/docker

# docker-compose.yml
cat > docker-compose.yml <<EOF
version: '3.8'

services:
  # 前端
  frontend:
    build:
      context: ../frontend
      dockerfile: ../docker/frontend.Dockerfile
    ports:
      - "3000:3000"
    volumes:
      - ../frontend:/app
      - /app/node_modules
    environment:
      - VITE_API_URL=http://localhost:8000
    depends_on:
      - backend

  # 后端
  backend:
    build:
      context: ../backend
      dockerfile: ../docker/backend.Dockerfile
    ports:
      - "8000:8000"
    volumes:
      - ../backend:/app
      - ../../:/HydroClaude  # 挂载核心引擎
    environment:
      - DATABASE_URL=postgresql://hydroclaude:password@db:5432/hydroclaude
      - REDIS_URL=redis://redis:6379/0
      - MINIO_ENDPOINT=minio:9000
      - MINIO_ACCESS_KEY=minioadmin
      - MINIO_SECRET_KEY=minioadmin
    depends_on:
      - db
      - redis
      - minio

  # 数据库
  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=hydroclaude
      - POSTGRES_USER=hydroclaude
      - POSTGRES_PASSWORD=password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  # Redis
  redis:
    image: redis:7
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  # MinIO
  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      - MINIO_ROOT_USER=minioadmin
      - MINIO_ROOT_PASSWORD=minioadmin
    volumes:
      - minio_data:/data

  # Celery Worker
  celery:
    build:
      context: ../backend
      dockerfile: ../docker/backend.Dockerfile
    command: celery -A app.tasks worker -l info -Q simulations,default
    volumes:
      - ../backend:/app
      - ../../:/HydroClaude
    environment:
      - DATABASE_URL=postgresql://hydroclaude:password@db:5432/hydroclaude
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - redis
      - db

volumes:
  postgres_data:
  redis_data:
  minio_data:
EOF

echo -e "${GREEN}✓ docker-compose.yml 创建完成${NC}"

cd ../..

# 创建环境变量文件
echo -e "${YELLOW}[6/8] 创建环境变量文件...${NC}"

cat > web/.env.example <<EOF
# 数据库
DATABASE_URL=postgresql://hydroclaude:password@localhost:5432/hydroclaude

# Redis
REDIS_URL=redis://localhost:6379/0

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_SECURE=false

# JWT
SECRET_KEY=your-secret-key-change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# 应用
DEBUG=true
CORS_ORIGINS=http://localhost:3000

# HydroClaude核心路径
HYDROCLAUDE_PATH=/home/user/HydroClaude
EOF

cp web/.env.example web/.env

echo -e "${GREEN}✓ 环境变量文件创建完成${NC}"
echo ""

# 创建开发脚本
echo -e "${YELLOW}[7/8] 创建开发脚本...${NC}"

cat > web/scripts/dev.sh <<'DEVSCRIPT'
#!/bin/bash
# 开发环境启动脚本

set -e

echo "启动HydroClaude Web开发环境..."
echo ""

# 启动Docker服务
echo "1. 启动数据库和Redis..."
cd web/docker
docker-compose up -d db redis minio
cd ../..

# 等待服务启动
echo "   等待服务就绪..."
sleep 5

# 启动后端
echo "2. 启动后端服务..."
cd web/backend
source venv/bin/activate 2>/dev/null || true
uvicorn api_gateway.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ../..

# 启动前端
echo "3. 启动前端服务..."
cd web/frontend
npm run dev &
FRONTEND_PID=$!
cd ../..

echo ""
echo "================================"
echo "开发环境启动完成！"
echo "================================"
echo ""
echo "前端地址: http://localhost:3000"
echo "后端地址: http://localhost:8000"
echo "API文档: http://localhost:8000/docs"
echo "MinIO控制台: http://localhost:9001"
echo ""
echo "按 Ctrl+C 停止所有服务"
echo ""

# 等待中断信号
trap "echo '正在停止服务...'; kill $BACKEND_PID $FRONTEND_PID; docker-compose -f web/docker/docker-compose.yml stop; exit" INT
wait
DEVSCRIPT

chmod +x web/scripts/dev.sh

echo -e "${GREEN}✓ 开发脚本创建完成${NC}"
echo ""

# 安装依赖
echo -e "${YELLOW}[8/8] 安装依赖（可选，可能需要较长时间）...${NC}"
read -p "是否现在安装依赖？(y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    # 安装前端依赖
    echo "安装前端依赖..."
    cd web/frontend
    npm install
    cd ../..

    # 创建Python虚拟环境并安装依赖
    echo "安装后端依赖..."
    cd web/backend
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    cd ../..

    echo -e "${GREEN}✓ 依赖安装完成${NC}"
else
    echo -e "${YELLOW}  跳过依赖安装，请稍后手动安装${NC}"
fi

echo ""
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}项目初始化完成！${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo "下一步："
echo "1. 查看项目结构: tree web/"
echo "2. 启动开发环境: ./web/scripts/dev.sh"
echo "3. 查看文档: cat WEB_SYSTEM_DESIGN_PLAN.md"
echo ""
echo "祝开发顺利！"
