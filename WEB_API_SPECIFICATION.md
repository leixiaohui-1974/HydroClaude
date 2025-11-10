# HydroClaude Web API 规范文档

> **版本**: v1.0
> **日期**: 2025-11-10
> **API版本**: v1
> **基础URL**: `https://api.hydroclaude.com/v1`

---

## 目录

1. [API设计原则](#1-api设计原则)
2. [认证与授权](#2-认证与授权)
3. [通用规范](#3-通用规范)
4. [错误处理](#4-错误处理)
5. [API端点](#5-api端点)
6. [数据模型](#6-数据模型)
7. [WebSocket API](#7-websocket-api)
8. [速率限制](#8-速率限制)

---

## 1. API设计原则

### 1.1 RESTful设计

- **资源导向**：API以资源为中心，使用名词而非动词
- **HTTP方法语义**：
  - `GET`: 读取资源
  - `POST`: 创建资源
  - `PUT`: 完整更新资源
  - `PATCH`: 部分更新资源
  - `DELETE`: 删除资源
- **无状态**：每个请求包含所有必要信息
- **分层系统**：客户端无需知道是否直接连接到服务器

### 1.2 版本控制

- URL版本控制：`/v1/projects`
- 废弃API在6个月后移除
- 通过响应头`X-API-Version`返回实际API版本

### 1.3 响应格式

- 默认返回JSON格式
- 支持`Accept`头指定格式
- 时间格式：ISO 8601 (UTC)
- 数字精度：浮点数保留6位小数

---

## 2. 认证与授权

### 2.1 认证方式

#### JWT Token认证（推荐）

```http
POST /v1/auth/login
Content-Type: application/json

{
  "username": "user@example.com",
  "password": "password123"
}
```

**响应**：
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 86400
}
```

**使用Token**：
```http
GET /v1/projects
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

#### OAuth2认证

```http
GET /v1/auth/oauth/google
```
重定向到Google OAuth2授权页面。

#### API Key认证（企业版）

```http
GET /v1/projects
X-API-Key: your-api-key-here
```

### 2.2 Token刷新

```http
POST /v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### 2.3 权限控制

- 基于RBAC（基于角色的访问控制）
- 权限检查在每个请求中执行
- 无权限时返回`403 Forbidden`

---

## 3. 通用规范

### 3.1 请求格式

**Headers**：
```
Content-Type: application/json
Accept: application/json
Authorization: Bearer {token}
X-Request-ID: {uuid}  # 可选，用于请求追踪
```

**分页参数**：
```
?page=1          # 页码，从1开始
&size=20         # 每页数量，默认20，最大100
&sort=created_at # 排序字段
&order=desc      # 排序方向: asc | desc
```

**过滤参数**：
```
?status=active           # 单个过滤
&tags=water_supply       # 标签过滤
&created_after=2025-01-01 # 日期过滤
```

### 3.2 响应格式

**成功响应**（列表）：
```json
{
  "items": [...],
  "total": 100,
  "page": 1,
  "size": 20,
  "pages": 5
}
```

**成功响应**（单个资源）：
```json
{
  "id": "uuid",
  "name": "项目名称",
  "created_at": "2025-11-10T08:00:00Z",
  ...
}
```

**创建/更新响应**：
```json
{
  "id": "uuid",
  "message": "Resource created successfully",
  ...
}
```

### 3.3 HTTP状态码

| 状态码 | 含义 | 使用场景 |
|-------|------|---------|
| `200 OK` | 成功 | GET、PUT、PATCH成功 |
| `201 Created` | 已创建 | POST成功创建资源 |
| `204 No Content` | 无内容 | DELETE成功 |
| `400 Bad Request` | 请求错误 | 参数验证失败 |
| `401 Unauthorized` | 未认证 | Token缺失或无效 |
| `403 Forbidden` | 无权限 | 权限不足 |
| `404 Not Found` | 未找到 | 资源不存在 |
| `409 Conflict` | 冲突 | 资源已存在或状态冲突 |
| `422 Unprocessable Entity` | 无法处理 | 业务逻辑错误 |
| `429 Too Many Requests` | 请求过多 | 超过速率限制 |
| `500 Internal Server Error` | 服务器错误 | 系统异常 |
| `503 Service Unavailable` | 服务不可用 | 系统维护 |

---

## 4. 错误处理

### 4.1 错误响应格式

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Validation failed",
    "details": [
      {
        "field": "length",
        "message": "Length must be greater than 0",
        "value": -10
      }
    ],
    "request_id": "req_123abc",
    "timestamp": "2025-11-10T08:00:00Z"
  }
}
```

### 4.2 错误码

| 错误码 | HTTP状态 | 说明 |
|-------|---------|------|
| `VALIDATION_ERROR` | 400 | 参数验证失败 |
| `AUTHENTICATION_FAILED` | 401 | 认证失败 |
| `INVALID_TOKEN` | 401 | Token无效或过期 |
| `PERMISSION_DENIED` | 403 | 权限不足 |
| `RESOURCE_NOT_FOUND` | 404 | 资源不存在 |
| `RESOURCE_ALREADY_EXISTS` | 409 | 资源已存在 |
| `INVALID_STATE` | 422 | 资源状态不允许操作 |
| `SIMULATION_FAILED` | 422 | 仿真执行失败 |
| `RATE_LIMIT_EXCEEDED` | 429 | 超过速率限制 |
| `INTERNAL_ERROR` | 500 | 系统内部错误 |
| `SERVICE_UNAVAILABLE` | 503 | 服务暂时不可用 |

---

## 5. API端点

### 5.1 认证 (`/auth`)

#### 5.1.1 用户登录

```http
POST /v1/auth/login
```

**请求体**：
```json
{
  "username": "user@example.com",
  "password": "password123"
}
```

**响应**：
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "Bearer",
  "expires_in": 86400,
  "user": {
    "id": "user_123",
    "username": "user@example.com",
    "full_name": "张工",
    "role": "engineer"
  }
}
```

#### 5.1.2 用户注册

```http
POST /v1/auth/register
```

**请求体**：
```json
{
  "email": "user@example.com",
  "password": "password123",
  "full_name": "张三",
  "organization": "某公司"
}
```

#### 5.1.3 刷新Token

```http
POST /v1/auth/refresh
```

**请求体**：
```json
{
  "refresh_token": "eyJ..."
}
```

#### 5.1.4 退出登录

```http
POST /v1/auth/logout
```

---

### 5.2 项目管理 (`/projects`)

#### 5.2.1 列出所有项目

```http
GET /v1/projects?page=1&size=20&status=active&sort=created_at&order=desc
```

**查询参数**：
- `page`: 页码（默认1）
- `size`: 每页数量（默认20，最大100）
- `status`: 状态过滤 (`draft|active|archived`)
- `tags`: 标签过滤（逗号分隔）
- `search`: 搜索关键词（名称、描述）
- `sort`: 排序字段 (`name|created_at|updated_at`)
- `order`: 排序方向 (`asc|desc`)

**响应**：
```json
{
  "items": [
    {
      "id": "proj_123",
      "name": "城市供水系统",
      "description": "某市供水管网仿真分析",
      "model_type": "mixed",
      "status": "active",
      "owner": {
        "id": "user_123",
        "name": "张工"
      },
      "tags": ["water_supply", "urban"],
      "created_at": "2025-11-01T08:00:00Z",
      "updated_at": "2025-11-10T08:00:00Z",
      "stats": {
        "models": 5,
        "simulations": 23,
        "last_simulation": "2025-11-09T15:30:00Z"
      }
    }
  ],
  "total": 42,
  "page": 1,
  "size": 20,
  "pages": 3
}
```

#### 5.2.2 创建项目

```http
POST /v1/projects
```

**请求体**：
```json
{
  "name": "新项目",
  "description": "项目描述",
  "model_type": "canal",  // canal | pipe | mixed
  "tags": ["test", "demo"]
}
```

**响应** (201 Created)：
```json
{
  "id": "proj_456",
  "name": "新项目",
  "description": "项目描述",
  "model_type": "canal",
  "status": "draft",
  "owner": {
    "id": "user_123",
    "name": "张工"
  },
  "tags": ["test", "demo"],
  "created_at": "2025-11-10T08:00:00Z",
  "updated_at": "2025-11-10T08:00:00Z"
}
```

#### 5.2.3 获取项目详情

```http
GET /v1/projects/{project_id}
```

**响应**：
```json
{
  "id": "proj_123",
  "name": "城市供水系统",
  "description": "某市供水管网仿真分析",
  "model_type": "mixed",
  "status": "active",
  "owner": {
    "id": "user_123",
    "name": "张工",
    "email": "zhang@example.com"
  },
  "tags": ["water_supply", "urban"],
  "created_at": "2025-11-01T08:00:00Z",
  "updated_at": "2025-11-10T08:00:00Z",
  "models": [
    {
      "id": "model_789",
      "version": 5,
      "is_current": true,
      "created_at": "2025-11-09T10:00:00Z"
    }
  ],
  "collaborators": [
    {
      "user_id": "user_456",
      "name": "李工",
      "role": "editor"
    }
  ],
  "permissions": {
    "can_edit": true,
    "can_delete": true,
    "can_share": true,
    "can_simulate": true
  }
}
```

#### 5.2.4 更新项目

```http
PUT /v1/projects/{project_id}
```

**请求体**：
```json
{
  "name": "更新后的名称",
  "description": "更新后的描述",
  "status": "active",
  "tags": ["water_supply", "updated"]
}
```

#### 5.2.5 删除项目

```http
DELETE /v1/projects/{project_id}
```

**响应** (204 No Content)

#### 5.2.6 项目统计

```http
GET /v1/projects/{project_id}/stats
```

**响应**：
```json
{
  "project_id": "proj_123",
  "models": {
    "total": 5,
    "current_version": 5
  },
  "simulations": {
    "total": 23,
    "completed": 20,
    "failed": 2,
    "running": 1
  },
  "storage": {
    "models_size": "15.2 MB",
    "results_size": "450.8 MB",
    "total_size": "466.0 MB"
  },
  "activity": {
    "last_updated": "2025-11-10T08:00:00Z",
    "last_simulation": "2025-11-09T15:30:00Z",
    "contributors": 3
  }
}
```

---

### 5.3 模型管理 (`/models`)

#### 5.3.1 获取当前模型

```http
GET /v1/projects/{project_id}/models/current
```

**响应**：
```json
{
  "id": "model_789",
  "project_id": "proj_123",
  "version": 5,
  "is_current": true,
  "model_config": {
    "solver": "godunov_fvm",
    "time": {
      "t_start": 0,
      "t_end": 100,
      "dt_max": 0.1
    },
    "spatial": {
      "n_cells": 200,
      "cfl": 0.5
    }
  },
  "topology": {
    "nodes": [
      {
        "id": "node_1",
        "type": "reservoir",
        "position": {"x": 0, "y": 0}
      },
      {
        "id": "node_2",
        "type": "canal",
        "position": {"x": 100, "y": 0}
      }
    ],
    "edges": [
      {
        "from": "node_1",
        "to": "node_2",
        "type": "flow"
      }
    ]
  },
  "components": [
    {
      "id": "reservoir_1",
      "type": "reservoir",
      "name": "上游水库",
      "parameters": {
        "initial_level": 100.0,
        "area": 1000000.0
      }
    },
    {
      "id": "canal_1",
      "type": "canal",
      "name": "主渠道",
      "parameters": {
        "length": 1000.0,
        "width": 10.0,
        "slope": 0.001,
        "manning_n": 0.025,
        "n_sections": 50
      }
    }
  ],
  "created_by": {
    "id": "user_123",
    "name": "张工"
  },
  "created_at": "2025-11-09T10:00:00Z"
}
```

#### 5.3.2 列出模型版本

```http
GET /v1/projects/{project_id}/models?page=1&size=10
```

**响应**：
```json
{
  "items": [
    {
      "id": "model_789",
      "version": 5,
      "is_current": true,
      "summary": "添加调压室组件",
      "created_by": {"id": "user_123", "name": "张工"},
      "created_at": "2025-11-09T10:00:00Z"
    },
    {
      "id": "model_788",
      "version": 4,
      "is_current": false,
      "summary": "修改管道参数",
      "created_by": {"id": "user_123", "name": "张工"},
      "created_at": "2025-11-08T14:30:00Z"
    }
  ],
  "total": 5,
  "page": 1,
  "size": 10
}
```

#### 5.3.3 保存模型（创建新版本）

```http
POST /v1/projects/{project_id}/models
```

**请求体**：
```json
{
  "summary": "修改说明（可选）",
  "model_config": { ... },
  "topology": { ... },
  "components": [ ... ]
}
```

**响应** (201 Created)：
```json
{
  "id": "model_790",
  "version": 6,
  "message": "Model version 6 created successfully"
}
```

#### 5.3.4 验证模型

```http
POST /v1/models/validate
```

**请求体**：
```json
{
  "model_config": { ... },
  "topology": { ... },
  "components": [ ... ]
}
```

**响应**：
```json
{
  "valid": true,
  "errors": [],
  "warnings": [
    {
      "code": "LOW_GRID_RESOLUTION",
      "message": "网格数较少（200），建议增加到500以提高精度",
      "component": "canal_1",
      "severity": "warning"
    }
  ],
  "suggestions": [
    {
      "message": "检测到急流，建议启用激波捕捉算法",
      "parameter": "shock_capturing",
      "recommended_value": true
    }
  ]
}
```

**验证失败响应** (422 Unprocessable Entity)：
```json
{
  "valid": false,
  "errors": [
    {
      "code": "INVALID_TOPOLOGY",
      "message": "检测到断开的组件",
      "component": "canal_3",
      "details": "组件没有入口连接"
    },
    {
      "code": "INVALID_PARAMETER",
      "message": "长度必须大于0",
      "component": "pipe_2",
      "parameter": "length",
      "value": -10
    }
  ],
  "warnings": []
}
```

#### 5.3.5 切换模型版本

```http
POST /v1/projects/{project_id}/models/{model_id}/activate
```

**响应**：
```json
{
  "message": "Model version 4 activated successfully"
}
```

#### 5.3.6 导出模型

```http
GET /v1/projects/{project_id}/models/{model_id}/export?format=json
```

**查询参数**：
- `format`: 导出格式 (`json|yaml|python`)

**响应**：
- Content-Type: `application/json` 或 `text/yaml` 或 `text/x-python`
- Content-Disposition: `attachment; filename="model_v5.json"`

---

### 5.4 仿真管理 (`/simulations`)

#### 5.4.1 提交仿真任务

```http
POST /v1/simulations
```

**请求体**：
```json
{
  "model_id": "model_789",
  "name": "标准工况仿真",
  "solver_type": "godunov_fvm",  // godunov_fvm | preissmann | hydrostatic | moc | rk4
  "solver_config": {
    "cfl": 0.5,
    "order": 2,
    "use_numba": true,
    "shock_capturing": true
  },
  "time_config": {
    "t_start": 0,
    "t_end": 100,
    "dt_max": 0.1,
    "output_interval": 0.5
  },
  "boundary_conditions": {
    "upstream": {
      "type": "constant_flow",
      "value": 100.0
    },
    "downstream": {
      "type": "constant_level",
      "value": 5.0
    }
  },
  "priority": 5,  // 1-10, 默认5
  "tags": ["standard", "baseline"]
}
```

**响应** (201 Created)：
```json
{
  "task_id": "sim_456",
  "status": "queued",
  "queue_position": 3,
  "estimated_start_time": "2025-11-10T08:05:00Z",
  "estimated_duration": 120,
  "message": "Simulation task created successfully"
}
```

#### 5.4.2 查询仿真状态

```http
GET /v1/simulations/{task_id}
```

**响应**：

**排队中**：
```json
{
  "task_id": "sim_456",
  "name": "标准工况仿真",
  "status": "queued",
  "queue_position": 2,
  "submitted_at": "2025-11-10T08:00:00Z",
  "estimated_start_time": "2025-11-10T08:05:00Z"
}
```

**运行中**：
```json
{
  "task_id": "sim_456",
  "name": "标准工况仿真",
  "status": "running",
  "progress": 45.5,
  "current_time": 45.5,
  "total_time": 100.0,
  "started_at": "2025-11-10T08:05:00Z",
  "estimated_completion": "2025-11-10T08:10:00Z",
  "metrics": {
    "mass_conservation_error": 0.000002,
    "max_velocity": 5.23,
    "max_depth": 3.45,
    "iterations": 4550
  },
  "resource_usage": {
    "cpu_percent": 85,
    "memory_mb": 2100
  }
}
```

**已完成**：
```json
{
  "task_id": "sim_456",
  "name": "标准工况仿真",
  "status": "completed",
  "progress": 100.0,
  "submitted_at": "2025-11-10T08:00:00Z",
  "started_at": "2025-11-10T08:05:00Z",
  "completed_at": "2025-11-10T08:10:00Z",
  "duration": 125.5,
  "metrics": {
    "mass_conservation_error": 0.000001,
    "max_velocity": 5.67,
    "max_depth": 3.50,
    "total_iterations": 10000
  },
  "results": {
    "timeseries": "/v1/simulations/sim_456/results/timeseries",
    "snapshots": "/v1/simulations/sim_456/results/snapshots",
    "statistics": "/v1/simulations/sim_456/results/statistics",
    "download": "/v1/simulations/sim_456/results/download"
  }
}
```

**失败**：
```json
{
  "task_id": "sim_456",
  "name": "标准工况仿真",
  "status": "failed",
  "progress": 45.5,
  "started_at": "2025-11-10T08:05:00Z",
  "failed_at": "2025-11-10T08:07:30Z",
  "error": {
    "code": "NUMERICAL_INSTABILITY",
    "message": "Numerical instability detected at t=45.5s",
    "details": "CFL condition violated in cell 123",
    "suggestions": [
      "Reduce time step size (dt_max < 0.05)",
      "Increase grid resolution",
      "Check boundary conditions"
    ]
  }
}
```

#### 5.4.3 列出仿真任务

```http
GET /v1/simulations?model_id=model_789&status=completed&page=1&size=20
```

**查询参数**：
- `model_id`: 模型ID过滤
- `project_id`: 项目ID过滤
- `status`: 状态过滤 (`queued|running|completed|failed|cancelled`)
- `submitted_after`: 提交时间过滤
- `sort`: 排序字段 (`submitted_at|started_at|completed_at|duration`)
- `order`: 排序方向 (`asc|desc`)

**响应**：
```json
{
  "items": [
    {
      "task_id": "sim_456",
      "name": "标准工况仿真",
      "model_id": "model_789",
      "status": "completed",
      "submitted_at": "2025-11-10T08:00:00Z",
      "duration": 125.5,
      "submitted_by": {"id": "user_123", "name": "张工"}
    }
  ],
  "total": 23,
  "page": 1,
  "size": 20
}
```

#### 5.4.4 取消仿真

```http
DELETE /v1/simulations/{task_id}
```

**响应** (204 No Content)

或

```http
POST /v1/simulations/{task_id}/cancel
```

**响应**：
```json
{
  "message": "Simulation cancelled successfully"
}
```

#### 5.4.5 获取仿真结果 - 时序数据

```http
GET /v1/simulations/{task_id}/results/timeseries?location=canal_1&variables=h,Q&t_start=0&t_end=100&step=0.5
```

**查询参数**：
- `location`: 位置ID（可选，不指定则返回所有位置）
- `variables`: 变量列表 (`h,Q,V,P`，逗号分隔）
- `t_start`: 起始时间（可选）
- `t_end`: 结束时间（可选）
- `step`: 时间步长（可选，用于降采样）

**响应**：
```json
{
  "task_id": "sim_456",
  "location": "canal_1",
  "variables": ["h", "Q"],
  "time": [0.0, 0.5, 1.0, 1.5, ...],
  "data": {
    "h": [2.0, 2.1, 2.15, 2.18, ...],
    "Q": [100.0, 102.5, 105.0, 106.8, ...]
  },
  "units": {
    "h": "m",
    "Q": "m³/s"
  },
  "statistics": {
    "h": {"min": 2.0, "max": 3.5, "mean": 2.8, "std": 0.35},
    "Q": {"min": 100.0, "max": 150.0, "mean": 125.0, "std": 12.5}
  }
}
```

#### 5.4.6 获取仿真结果 - 快照

```http
GET /v1/simulations/{task_id}/results/snapshots?t=50.0
```

**响应**：
```json
{
  "task_id": "sim_456",
  "time": 50.0,
  "snapshot": {
    "canal_1": {
      "h": [2.0, 2.1, 2.15, ...],  // 沿渠道的水深分布
      "Q": [100, 102, 105, ...],
      "V": [5.0, 5.1, 5.15, ...]
    },
    "pipe_1": {
      "P": [50, 51, 52, ...],  // 沿管道的压力分布
      "Q": [50, 50, 50, ...]
    }
  },
  "locations": {
    "canal_1": [0, 20, 40, ...],  // x坐标
    "pipe_1": [0, 10, 20, ...]
  }
}
```

#### 5.4.7 获取仿真结果 - 统计

```http
GET /v1/simulations/{task_id}/results/statistics
```

**响应**：
```json
{
  "task_id": "sim_456",
  "global_metrics": {
    "mass_conservation_error": 0.000001,
    "max_velocity": 5.67,
    "max_depth": 3.50,
    "min_depth": 0.01,
    "total_volume": 25000.0,
    "peak_discharge": 150.0
  },
  "component_statistics": {
    "canal_1": {
      "max_depth": 3.50,
      "max_velocity": 5.67,
      "max_froude": 0.95,
      "flow_regime": "subcritical"
    },
    "pipe_1": {
      "max_pressure": 85.0,
      "min_pressure": 45.0,
      "max_flow": 50.0
    }
  },
  "convergence": {
    "iterations": 10000,
    "residual_norm": 1e-8,
    "converged": true
  }
}
```

#### 5.4.8 下载仿真结果

```http
GET /v1/simulations/{task_id}/results/download?format=csv
```

**查询参数**：
- `format`: 格式 (`csv|json|hdf5|vtk`)

**响应**：
- Content-Type: `text/csv` 或 `application/json` 等
- Content-Disposition: `attachment; filename="sim_456_results.csv"`

#### 5.4.9 批量仿真

```http
POST /v1/simulations/batch
```

**请求体**：
```json
{
  "model_id": "model_789",
  "name_template": "参数扫描_{param_name}={param_value}",
  "base_config": {
    "solver_type": "godunov_fvm",
    "solver_config": { ... },
    "time_config": { ... }
  },
  "parameter_sweep": {
    "parameter": "components.canal_1.manning_n",
    "values": [0.020, 0.025, 0.030, 0.035, 0.040]
  }
}
```

**响应**：
```json
{
  "batch_id": "batch_789",
  "tasks": [
    {"task_id": "sim_501", "parameters": {"manning_n": 0.020}},
    {"task_id": "sim_502", "parameters": {"manning_n": 0.025}},
    {"task_id": "sim_503", "parameters": {"manning_n": 0.030}},
    {"task_id": "sim_504", "parameters": {"manning_n": 0.035}},
    {"task_id": "sim_505", "parameters": {"manning_n": 0.040}}
  ],
  "message": "Batch simulation with 5 tasks created successfully"
}
```

---

### 5.5 控制系统 (`/control`)

#### 5.5.1 设计MPC控制器

```http
POST /v1/control/mpc
```

**请求体**：
```json
{
  "model_id": "model_789",
  "name": "水位MPC控制器",
  "prediction_horizon": 10,
  "control_horizon": 3,
  "sampling_time": 1.0,
  "state_variables": ["level"],
  "control_variables": ["gate_opening"],
  "Q_weight": [[1.0]],
  "R_weight": [[0.1]],
  "constraints": {
    "state": {
      "level": {"min": 4.0, "max": 6.0}
    },
    "control": {
      "gate_opening": {"min": 0.0, "max": 1.0},
      "gate_opening_rate": {"min": -0.1, "max": 0.1}
    }
  },
  "setpoint": {
    "level": 5.0
  }
}
```

**响应** (201 Created)：
```json
{
  "controller_id": "ctrl_123",
  "name": "水位MPC控制器",
  "type": "mpc",
  "status": "designed",
  "parameters": {
    "prediction_horizon": 10,
    "control_horizon": 3,
    ...
  },
  "performance_estimate": {
    "settling_time": "~15s",
    "overshoot": "<5%",
    "steady_state_error": "<0.1m"
  }
}
```

#### 5.5.2 PID参数整定

```http
POST /v1/control/pid/tune
```

**请求体**：
```json
{
  "model_id": "model_789",
  "method": "frequency_response",  // frequency_response | ziegler_nichols | cohen_coon
  "control_variable": "gate_opening",
  "measured_variable": "level",
  "setpoint": 5.0,
  "performance_criteria": "balanced"  // aggressive | balanced | conservative
}
```

**响应**：
```json
{
  "controller_id": "ctrl_456",
  "type": "pid",
  "parameters": {
    "Kp": 1.5,
    "Ki": 0.3,
    "Kd": 0.05,
    "sampling_time": 1.0
  },
  "performance": {
    "rise_time": 2.5,
    "settling_time": 8.0,
    "overshoot": 5.2,
    "steady_state_error": 0.05,
    "phase_margin": 45.0,
    "gain_margin": 12.0
  },
  "tuning_method": "frequency_response",
  "recommendations": [
    "性能良好，可直接使用",
    "如需更快响应，可增加Kp到2.0"
  ]
}
```

#### 5.5.3 运行控制仿真

```http
POST /v1/control/{controller_id}/simulate
```

**请求体**：
```json
{
  "simulation_time": 100.0,
  "disturbances": [
    {
      "type": "step",
      "variable": "inflow",
      "time": 20.0,
      "value": 150.0
    }
  ],
  "scenarios": [
    {"name": "标准工况", "setpoint": 5.0},
    {"name": "高水位", "setpoint": 5.5},
    {"name": "低水位", "setpoint": 4.5}
  ]
}
```

**响应**：
```json
{
  "task_id": "sim_789",
  "controller_id": "ctrl_123",
  "status": "queued",
  "message": "Control simulation task created"
}
```

#### 5.5.4 在线识别

```http
POST /v1/control/identification
```

**请求体**：
```json
{
  "model_id": "model_789",
  "method": "rls",  // rls | frequency_analysis
  "input_variable": "gate_opening",
  "output_variable": "level",
  "excitation": {
    "type": "prbs",  // prbs | chirp | step
    "duration": 100.0,
    "amplitude": 0.1
  }
}
```

**响应**：
```json
{
  "identification_id": "iden_123",
  "status": "queued",
  "estimated_duration": 150.0
}
```

#### 5.5.5 获取识别结果

```http
GET /v1/control/identification/{identification_id}
```

**响应**：
```json
{
  "identification_id": "iden_123",
  "status": "completed",
  "transfer_function": {
    "numerator": [0, 1.5],
    "denominator": [1, 0.5, 0.1],
    "delay": 2.0,
    "form": "1.5 / (s^2 + 0.5*s + 0.1) * e^(-2s)"
  },
  "state_space": {
    "A": [[0, 1], [-0.1, -0.5]],
    "B": [[0], [1.5]],
    "C": [[1, 0]],
    "D": [[0]]
  },
  "frequency_response": {
    "frequencies": [0.01, 0.02, ...],
    "magnitude": [15.0, 14.5, ...],
    "phase": [-20, -25, ...]
  },
  "fit_quality": {
    "r_squared": 0.95,
    "rmse": 0.05,
    "aic": -150.5
  }
}
```

---

### 5.6 用户与组织 (`/users`, `/organizations`)

#### 5.6.1 获取当前用户信息

```http
GET /v1/users/me
```

**响应**：
```json
{
  "id": "user_123",
  "username": "user@example.com",
  "email": "user@example.com",
  "full_name": "张工",
  "role": "engineer",
  "organization": {
    "id": "org_456",
    "name": "某公司"
  },
  "license": {
    "type": "professional",
    "expires_at": "2026-11-10T00:00:00Z"
  },
  "created_at": "2025-01-01T00:00:00Z",
  "last_login": "2025-11-10T08:00:00Z"
}
```

#### 5.6.2 更新用户信息

```http
PATCH /v1/users/me
```

**请求体**：
```json
{
  "full_name": "张三丰",
  "avatar_url": "https://..."
}
```

#### 5.6.3 修改密码

```http
POST /v1/users/me/change-password
```

**请求体**：
```json
{
  "current_password": "old_password",
  "new_password": "new_password"
}
```

#### 5.6.4 列出组织成员

```http
GET /v1/organizations/{org_id}/members
```

**响应**：
```json
{
  "items": [
    {
      "user_id": "user_123",
      "full_name": "张工",
      "email": "zhang@example.com",
      "role": "admin",
      "joined_at": "2025-01-01T00:00:00Z"
    }
  ],
  "total": 15
}
```

#### 5.6.5 邀请成员

```http
POST /v1/organizations/{org_id}/members/invite
```

**请求体**：
```json
{
  "email": "newuser@example.com",
  "role": "engineer",
  "message": "欢迎加入团队"
}
```

---

## 6. 数据模型

### 6.1 Project（项目）

```typescript
interface Project {
  id: string;
  name: string;
  description?: string;
  model_type: 'canal' | 'pipe' | 'mixed';
  status: 'draft' | 'active' | 'archived';
  owner: UserSummary;
  organization: OrganizationSummary;
  tags: string[];
  created_at: string;  // ISO 8601
  updated_at: string;
  permissions: ProjectPermissions;
}

interface ProjectPermissions {
  can_edit: boolean;
  can_delete: boolean;
  can_share: boolean;
  can_simulate: boolean;
}
```

### 6.2 Model（模型）

```typescript
interface Model {
  id: string;
  project_id: string;
  version: number;
  is_current: boolean;
  summary?: string;
  model_config: ModelConfig;
  topology: Topology;
  components: Component[];
  created_by: UserSummary;
  created_at: string;
}

interface ModelConfig {
  solver: string;
  time: TimeConfig;
  spatial: SpatialConfig;
  advanced?: AdvancedConfig;
}

interface Component {
  id: string;
  type: string;  // reservoir, canal, pipe, gate, etc.
  name: string;
  parameters: Record<string, any>;
}
```

### 6.3 SimulationTask（仿真任务）

```typescript
interface SimulationTask {
  task_id: string;
  name: string;
  model_id: string;
  project_id: string;
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';
  progress: number;  // 0-100
  solver_type: string;
  solver_config: Record<string, any>;
  time_config: TimeConfig;
  submitted_at: string;
  started_at?: string;
  completed_at?: string;
  duration?: number;  // seconds
  metrics?: SimulationMetrics;
  error?: SimulationError;
}

interface SimulationMetrics {
  mass_conservation_error: number;
  max_velocity: number;
  max_depth: number;
  iterations: number;
}
```

---

## 7. WebSocket API

### 7.1 连接

```javascript
const ws = new WebSocket('wss://api.hydroclaude.com/v1/ws/simulations/{task_id}?token={jwt_token}');
```

### 7.2 服务器推送消息

#### 进度更新

```json
{
  "type": "progress",
  "task_id": "sim_456",
  "progress": 55.5,
  "current_time": 55.5,
  "metrics": {
    "mass_conservation": 0.000001,
    "max_velocity": 5.45
  },
  "timestamp": "2025-11-10T08:07:30Z"
}
```

#### 完成通知

```json
{
  "type": "completed",
  "task_id": "sim_456",
  "duration": 125.5,
  "result_url": "/v1/simulations/sim_456/results",
  "timestamp": "2025-11-10T08:10:00Z"
}
```

#### 错误通知

```json
{
  "type": "error",
  "task_id": "sim_456",
  "error": {
    "code": "NUMERICAL_INSTABILITY",
    "message": "Numerical instability detected at t=45.5s"
  },
  "timestamp": "2025-11-10T08:07:30Z"
}
```

### 7.3 客户端消息

#### 订阅多个任务

```json
{
  "action": "subscribe",
  "task_ids": ["sim_456", "sim_457"]
}
```

#### 取消订阅

```json
{
  "action": "unsubscribe",
  "task_ids": ["sim_456"]
}
```

---

## 8. 速率限制

### 8.1 限制规则

| 端点类型 | 限制 | 窗口 |
|---------|------|------|
| 认证 | 5次 | 15分钟 |
| 读取操作 | 100次 | 1分钟 |
| 写入操作 | 30次 | 1分钟 |
| 仿真提交 | 10次 | 1分钟 |
| WebSocket连接 | 10个 | 并发 |

### 8.2 响应头

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 75
X-RateLimit-Reset: 1699612345
```

### 8.3 超限响应

```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded. Try again in 45 seconds.",
    "retry_after": 45
  }
}
```

---

## 附录

### A. 完整示例：从建模到仿真

```bash
# 1. 登录
curl -X POST https://api.hydroclaude.com/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"user@example.com","password":"password123"}'

# 响应: {"access_token":"eyJ...","token_type":"Bearer"}

# 2. 创建项目
curl -X POST https://api.hydroclaude.com/v1/projects \
  -H "Authorization: Bearer eyJ..." \
  -H "Content-Type: application/json" \
  -d '{"name":"溃坝案例","model_type":"canal"}'

# 响应: {"id":"proj_123",...}

# 3. 保存模型
curl -X POST https://api.hydroclaude.com/v1/projects/proj_123/models \
  -H "Authorization: Bearer eyJ..." \
  -H "Content-Type: application/json" \
  -d @model_definition.json

# 响应: {"id":"model_789","version":1}

# 4. 提交仿真
curl -X POST https://api.hydroclaude.com/v1/simulations \
  -H "Authorization: Bearer eyJ..." \
  -H "Content-Type: application/json" \
  -d '{
    "model_id":"model_789",
    "solver_type":"godunov_fvm",
    "solver_config":{"cfl":0.5,"order":2},
    "time_config":{"t_start":0,"t_end":100,"dt_max":0.1}
  }'

# 响应: {"task_id":"sim_456","status":"queued"}

# 5. 查询状态
curl https://api.hydroclaude.com/v1/simulations/sim_456 \
  -H "Authorization: Bearer eyJ..."

# 响应: {"task_id":"sim_456","status":"running","progress":45.5,...}

# 6. 获取结果
curl https://api.hydroclaude.com/v1/simulations/sim_456/results/timeseries?location=canal_1&variables=h,Q \
  -H "Authorization: Bearer eyJ..."

# 响应: {"time":[...],"data":{"h":[...],"Q":[...]}}
```

### B. SDK示例（Python）

```python
from hydroclaude_sdk import HydroClaude

# 初始化客户端
client = HydroClaude(api_key="your_api_key")

# 创建项目
project = client.projects.create(
    name="溃坝案例",
    model_type="canal"
)

# 构建模型
model = project.models.create({
    "components": [
        {"type": "reservoir", "parameters": {...}},
        {"type": "canal", "parameters": {...}}
    ],
    "topology": {...}
})

# 提交仿真
sim = client.simulations.create(
    model_id=model.id,
    solver_type="godunov_fvm",
    solver_config={"cfl": 0.5, "order": 2},
    time_config={"t_start": 0, "t_end": 100}
)

# 等待完成
sim.wait()

# 获取结果
results = sim.results.timeseries(location="canal_1", variables=["h", "Q"])
print(results.data["h"])
```

---

**文档版本**: v1.0
**最后更新**: 2025-11-10
**联系**: api-support@hydroclaude.com
