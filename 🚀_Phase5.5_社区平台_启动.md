# 🚀 Phase 5.5: 社区平台 - 项目启动

**日期**: 2025-11-15  
**版本**: HydroClaude v2.0.0  
**状态**: 🚧 进行中

---

## 📖 项目概述

Phase 5.5将构建完整的社区平台，包括用户系统、插件市场后端和社区功能，形成完整的插件生态系统。

---

## 🎯 目标

### 核心目标

1. **用户认证系统** - 注册、登录、权限管理
2. **插件市场后端** - 插件上传、审核、分发
3. **社区功能** - 论坛、评论、评分

### 价值

- ✅ 完整的插件生态
- ✅ 用户协作平台
- ✅ 知识分享社区
- ✅ 持续改进反馈

---

## 📋 开发计划

### Phase 5.5.1: 用户系统

**工作内容**:
- 用户认证API（注册、登录、JWT）
- 数据库设计（用户、会话）
- 权限管理
- 个人资料管理

**预计时间**: 1-2天

---

### Phase 5.5.2: 插件市场后端

**工作内容**:
- 插件发布API
- 插件下载统计
- 版本管理
- 审核系统

**预计时间**: 1-2天

---

### Phase 5.5.3: 社区功能

**工作内容**:
- 评论系统
- 评分系统
- 用户论坛（可选）
- 活动动态

**预计时间**: 1天

---

## 🛠️ 技术栈

### 后端

```
FastAPI: 现代Python Web框架
├── SQLAlchemy: ORM
├── Alembic: 数据库迁移
├── JWT: 身份认证
├── Pydantic: 数据验证
└── Uvicorn: ASGI服务器
```

### 数据库

```
PostgreSQL: 主数据库
├── 用户表
├── 插件表
├── 评论表
├── 评分表
└── 会话表
```

### 存储

```
本地文件系统或对象存储
├── 插件包文件
├── 用户头像
└── 插件截图
```

---

## 📂 项目结构

```
backend/
├── api/                      # API服务
│   ├── main.py               # FastAPI应用
│   ├── models/               # 数据库模型
│   │   ├── user.py
│   │   ├── plugin.py
│   │   ├── comment.py
│   │   └── rating.py
│   ├── schemas/              # Pydantic模型
│   │   ├── user.py
│   │   ├── plugin.py
│   │   └── auth.py
│   ├── routes/               # API路由
│   │   ├── auth.py
│   │   ├── users.py
│   │   ├── plugins.py
│   │   └── community.py
│   ├── services/             # 业务逻辑
│   │   ├── auth_service.py
│   │   ├── plugin_service.py
│   │   └── community_service.py
│   ├── database.py           # 数据库连接
│   ├── config.py             # 配置
│   └── utils/                # 工具函数
├── alembic/                  # 数据库迁移
├── tests/                    # 测试
├── requirements.txt          # Python依赖
└── README.md                 # 文档
```

---

## 🔑 核心功能

### 1. 用户认证

```python
# 注册
POST /api/auth/register
{
  "username": "user123",
  "email": "user@example.com",
  "password": "secure_password"
}

# 登录
POST /api/auth/login
{
  "username": "user123",
  "password": "secure_password"
}
→ { "access_token": "jwt_token", "token_type": "bearer" }

# 个人资料
GET /api/users/me
Authorization: Bearer <token>
```

---

### 2. 插件市场

```python
# 发布插件
POST /api/plugins
Authorization: Bearer <token>
Content-Type: multipart/form-data
{
  "manifest": {...},
  "file": <plugin.zip>,
  "screenshots": [<image1>, <image2>]
}

# 获取插件列表
GET /api/plugins?category=optimization&sort=downloads

# 下载插件
GET /api/plugins/{id}/download

# 更新插件
PUT /api/plugins/{id}
```

---

### 3. 评分和评论

```python
# 评分
POST /api/plugins/{id}/rating
{
  "rating": 5,
  "review": "Excellent plugin!"
}

# 评论
POST /api/plugins/{id}/comments
{
  "content": "Great work! How do I..."
}

# 获取评论
GET /api/plugins/{id}/comments?page=1&limit=10
```

---

## 📊 数据库设计

### 用户表 (users)

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    avatar_url VARCHAR(255),
    bio TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE
);
```

---

### 插件表 (plugins)

```sql
CREATE TABLE plugins (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    plugin_id VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    version VARCHAR(20) NOT NULL,
    category VARCHAR(50),
    downloads INTEGER DEFAULT 0,
    rating_avg DECIMAL(3,2) DEFAULT 0,
    rating_count INTEGER DEFAULT 0,
    file_url VARCHAR(255) NOT NULL,
    homepage VARCHAR(255),
    repository VARCHAR(255),
    license VARCHAR(50),
    keywords TEXT[],
    screenshots TEXT[],
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

---

### 评分表 (ratings)

```sql
CREATE TABLE ratings (
    id SERIAL PRIMARY KEY,
    plugin_id INTEGER REFERENCES plugins(id),
    user_id INTEGER REFERENCES users(id),
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    review TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(plugin_id, user_id)
);
```

---

### 评论表 (comments)

```sql
CREATE TABLE comments (
    id SERIAL PRIMARY KEY,
    plugin_id INTEGER REFERENCES plugins(id),
    user_id INTEGER REFERENCES users(id),
    parent_id INTEGER REFERENCES comments(id),
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

---

## 🔒 安全考虑

### 身份认证

```python
# JWT Token
- Access Token: 15分钟过期
- Refresh Token: 7天过期
- 密码哈希: bcrypt

# 权限控制
- 普通用户: 发布、评论、评分
- 审核员: 审核插件
- 管理员: 全部权限
```

---

### 数据验证

```python
# Pydantic模型验证
- 邮箱格式验证
- 密码强度验证
- 文件大小限制
- 内容安全检查
```

---

### API限流

```python
# 速率限制
- 登录: 5次/分钟
- 注册: 3次/小时
- API调用: 100次/分钟
- 文件上传: 10次/小时
```

---

## 📈 API端点设计

### 认证相关

```
POST   /api/auth/register          # 注册
POST   /api/auth/login             # 登录
POST   /api/auth/refresh           # 刷新Token
POST   /api/auth/logout            # 登出
POST   /api/auth/forgot-password   # 忘记密码
POST   /api/auth/reset-password    # 重置密码
GET    /api/auth/verify-email      # 验证邮箱
```

---

### 用户相关

```
GET    /api/users/me               # 当前用户信息
PUT    /api/users/me               # 更新个人资料
GET    /api/users/{id}             # 用户公开信息
GET    /api/users/{id}/plugins     # 用户的插件
```

---

### 插件相关

```
GET    /api/plugins                # 插件列表
POST   /api/plugins                # 发布插件
GET    /api/plugins/{id}           # 插件详情
PUT    /api/plugins/{id}           # 更新插件
DELETE /api/plugins/{id}           # 删除插件
GET    /api/plugins/{id}/download  # 下载插件
GET    /api/plugins/{id}/versions  # 版本历史
```

---

### 社区相关

```
POST   /api/plugins/{id}/rating    # 评分
GET    /api/plugins/{id}/ratings   # 评分列表
POST   /api/plugins/{id}/comments  # 发表评论
GET    /api/plugins/{id}/comments  # 评论列表
PUT    /api/comments/{id}          # 编辑评论
DELETE /api/comments/{id}          # 删除评论
```

---

## 🎯 开发步骤

### 步骤1: 搭建基础框架

```bash
# 创建项目
mkdir backend
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows

# 安装依赖
pip install fastapi uvicorn sqlalchemy alembic psycopg2-binary \
            python-jose python-multipart passlib bcrypt pydantic-settings
```

---

### 步骤2: 数据库设计

- 设计表结构
- 创建SQLAlchemy模型
- 配置Alembic迁移

---

### 步骤3: 实现API

- 用户认证API
- 插件管理API
- 社区功能API

---

### 步骤4: 前端集成

- 更新React应用
- 添加登录/注册页面
- 集成插件市场

---

### 步骤5: 测试和部署

- 单元测试
- 集成测试
- Docker容器化
- 部署文档

---

## 📚 预期成果

### 交付物

- [ ] 完整的后端API服务
- [ ] 数据库设计和迁移脚本
- [ ] 用户认证系统
- [ ] 插件市场后端
- [ ] 评分和评论系统
- [ ] API文档
- [ ] 部署指南

### 性能指标

```
API响应时间:   < 200ms
并发用户:       1000+
插件存储:       支持大文件
数据库:         PostgreSQL优化
缓存:           Redis（可选）
```

---

## 🎉 开始开发

Phase 5.5现在启动！

**第一步**: 搭建FastAPI后端框架

---

<p align="center">
  <b>🚀 Phase 5.5: 社区平台开发启动！</b>
</p>
