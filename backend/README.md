# HydroClaude 社区平台API

**版本**: 2.0.0  
**框架**: FastAPI  
**数据库**: SQLite/PostgreSQL

---

## 📖 概述

HydroClaude社区平台的后端API服务，提供用户认证、插件市场和社区功能。

---

## 🚀 快速开始

### 1. 安装依赖

```bash
cd backend

# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt
```

---

### 2. 配置环境

```bash
# 复制配置文件
cp .env.example .env

# 编辑配置（可选）
vim .env
```

**关键配置**:
```bash
# 数据库（默认使用SQLite）
DATABASE_URL=sqlite:///./hydroclaude.db

# JWT密钥（生产环境必须修改）
SECRET_KEY=your-secret-key-change-this-in-production

# 服务器
PORT=8000
DEBUG=True
```

---

### 3. 运行服务器

```bash
# 开发模式（自动重载）
python run.py

# 或使用uvicorn
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

**访问**:
- API文档: http://localhost:8000/docs
- 替代文档: http://localhost:8000/redoc
- 健康检查: http://localhost:8000/health

---

## 📚 API端点

### 认证 (Authentication)

```
POST   /api/auth/register     # 用户注册
POST   /api/auth/login        # 用户登录
```

---

### 用户 (Users)

```
GET    /api/users/me          # 当前用户信息
PUT    /api/users/me          # 更新个人资料
GET    /api/users/{id}        # 用户公开信息
```

---

### 插件 (Plugins)

```
GET    /api/plugins           # 插件列表（支持分页、筛选、搜索）
POST   /api/plugins           # 发布插件
GET    /api/plugins/{id}      # 插件详情
PUT    /api/plugins/{id}      # 更新插件
DELETE /api/plugins/{id}      # 删除插件
```

---

### 评分和评论 (Ratings & Comments)

```
POST   /api/plugins/{id}/rating    # 评分
POST   /api/plugins/{id}/comments  # 添加评论
GET    /api/plugins/{id}/comments  # 评论列表
```

---

## 🗄️ 数据库

### 使用SQLite（默认，开发）

```bash
# 自动创建数据库文件
python run.py
# 数据库文件：./hydroclaude.db
```

---

### 使用PostgreSQL（生产）

1. **安装PostgreSQL**

2. **创建数据库**
```sql
CREATE DATABASE hydroclaude;
CREATE USER hydroclaude WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE hydroclaude TO hydroclaude;
```

3. **配置.env**
```bash
DATABASE_URL=postgresql://hydroclaude:your_password@localhost:5432/hydroclaude
```

---

### 数据库结构

#### users表
```sql
- id: 主键
- username: 用户名（唯一）
- email: 邮箱（唯一）
- password_hash: 密码哈希
- avatar_url: 头像URL
- bio: 个人简介
- is_active: 是否激活
- is_verified: 是否验证
- is_admin: 是否管理员
- created_at: 创建时间
- updated_at: 更新时间
```

#### plugins表
```sql
- id: 主键
- user_id: 作者ID
- plugin_id: 插件ID（唯一）
- name: 插件名称
- description: 描述
- version: 版本
- category: 分类
- downloads: 下载次数
- rating_avg: 平均评分
- rating_count: 评分数量
- file_url: 文件URL
- homepage: 主页
- repository: 仓库
- license: 许可证
- keywords: 关键词
- screenshots: 截图
- status: 状态（pending/approved/rejected）
- created_at: 创建时间
- updated_at: 更新时间
```

#### ratings表
```sql
- id: 主键
- plugin_id: 插件ID
- user_id: 用户ID
- rating: 评分（1-5）
- review: 评论内容
- created_at: 创建时间
- updated_at: 更新时间
```

#### comments表
```sql
- id: 主键
- plugin_id: 插件ID
- user_id: 用户ID
- parent_id: 父评论ID（回复）
- content: 内容
- created_at: 创建时间
- updated_at: 更新时间
```

---

## 🔒 认证

### 注册

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "securepassword123"
  }'
```

---

### 登录

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser&password=securepassword123"
```

**响应**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 900
}
```

---

### 使用Token

```bash
curl -X GET http://localhost:8000/api/users/me \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

---

## 📊 使用示例

### 1. 用户注册和登录

```python
import requests

# 注册
response = requests.post(
    "http://localhost:8000/api/auth/register",
    json={
        "username": "newuser",
        "email": "newuser@example.com",
        "password": "password123"
    }
)
print(response.json())

# 登录
response = requests.post(
    "http://localhost:8000/api/auth/login",
    data={
        "username": "newuser",
        "password": "password123"
    }
)
token = response.json()["access_token"]
print(f"Token: {token}")
```

---

### 2. 获取插件列表

```python
# 获取所有插件
response = requests.get("http://localhost:8000/api/plugins")
plugins = response.json()
print(f"总共 {plugins['total']} 个插件")

# 筛选和搜索
response = requests.get(
    "http://localhost:8000/api/plugins",
    params={
        "category": "optimization",
        "search": "parameter",
        "sort": "downloads",
        "page": 1,
        "page_size": 10
    }
)
```

---

### 3. 发布插件

```python
headers = {"Authorization": f"Bearer {token}"}

response = requests.post(
    "http://localhost:8000/api/plugins",
    json={
        "plugin_id": "my-awesome-plugin",
        "name": "My Awesome Plugin",
        "description": "A great plugin for HydroClaude",
        "version": "1.0.0",
        "category": "optimization",
        "homepage": "https://github.com/user/plugin",
        "repository": "https://github.com/user/plugin",
        "license": "MIT",
        "keywords": ["optimization", "algorithm"]
    },
    headers=headers
)
```

---

### 4. 评分和评论

```python
plugin_id = 1

# 评分
response = requests.post(
    f"http://localhost:8000/api/plugins/{plugin_id}/rating",
    json={
        "rating": 5,
        "review": "Excellent plugin!"
    },
    headers=headers
)

# 评论
response = requests.post(
    f"http://localhost:8000/api/plugins/{plugin_id}/comments",
    json={
        "content": "How do I use this feature?"
    },
    headers=headers
)
```

---

## 🧪 测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_auth.py

# 查看覆盖率
pytest --cov=api tests/
```

---

## 📦 部署

### Docker部署（推荐）

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
# 构建镜像
docker build -t hydroclaude-api .

# 运行容器
docker run -d -p 8000:8000 \
  -e DATABASE_URL="postgresql://..." \
  -e SECRET_KEY="your-secret-key" \
  --name hydroclaude-api \
  hydroclaude-api
```

---

### 传统部署

```bash
# 安装依赖
pip install -r requirements.txt

# 使用gunicorn运行（生产）
gunicorn api.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

---

## 🔧 配置选项

### 环境变量

| 变量 | 描述 | 默认值 |
|------|------|--------|
| `DATABASE_URL` | 数据库连接字符串 | `sqlite:///./hydroclaude.db` |
| `SECRET_KEY` | JWT密钥 | 必须修改 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token过期时间（分钟） | `15` |
| `DEBUG` | 调试模式 | `True` |
| `HOST` | 服务器地址 | `0.0.0.0` |
| `PORT` | 服务器端口 | `8000` |
| `CORS_ORIGINS` | 允许的跨域源 | `[]` |

---

## 🐛 故障排除

### 问题1: 数据库连接失败

**症状**: `sqlalchemy.exc.OperationalError`

**解决**:
- 检查`DATABASE_URL`配置
- 确保数据库服务运行
- 验证连接权限

---

### 问题2: Token验证失败

**症状**: `401 Unauthorized`

**解决**:
- 检查Token是否过期
- 确认Header格式: `Authorization: Bearer TOKEN`
- 验证`SECRET_KEY`配置

---

### 问题3: CORS错误

**症状**: 浏览器报跨域错误

**解决**:
- 添加前端地址到`CORS_ORIGINS`
- 检查中间件配置

---

## 📚 相关文档

- [FastAPI官方文档](https://fastapi.tiangolo.com/)
- [SQLAlchemy文档](https://docs.sqlalchemy.org/)
- [Pydantic文档](https://docs.pydantic.dev/)

---

## 📝 许可证

MIT License

---

<p align="center">
  <b>HydroClaude API - 让水力学仿真更社交化</b>
</p>
