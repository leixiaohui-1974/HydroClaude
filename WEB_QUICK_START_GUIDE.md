# HydroClaude Web 快速启动指南

> **目标**: 帮助你在30分钟内启动第一个Web仿真

---

## 📚 文档导航

你现在拥有完整的开发方案文档：

### 核心设计文档

1. **[WEB_SYSTEM_DESIGN_PLAN.md](./WEB_SYSTEM_DESIGN_PLAN.md)** ⭐
   - 完整的系统架构设计
   - 技术栈选择与论证
   - 功能模块详细设计
   - 商业化策略
   - **建议首先阅读**

2. **[WEB_DEVELOPMENT_ROADMAP_REVISED.md](./WEB_DEVELOPMENT_ROADMAP_REVISED.md)** ⭐
   - **修订版开发路线图**
   - **优先开发水力学模拟（6个月）**
   - 详细的里程碑计划
   - 分阶段验收标准
   - **这是实际执行计划**

3. **[WEB_API_SPECIFICATION.md](./WEB_API_SPECIFICATION.md)**
   - 完整的RESTful API设计
   - 数据模型定义
   - WebSocket协议
   - API使用示例

4. **[WEB_TESTING_SPECIFICATION.md](./WEB_TESTING_SPECIFICATION.md)** ⭐
   - **65个标准测试案例**
   - 算法验证流程
   - 性能测试基准
   - 自动化测试方案

---

## 🎯 开发策略概览

```
┌─────────────────────────────────────────────────────┐
│                  开发优先级                          │
├─────────────────────────────────────────────────────┤
│ Phase 1: 水力学模拟 (Month 1-6)                     │
│  ├─ Week 1-2:   技术验证                            │
│  ├─ Week 3-6:   MVP (明渠基础)                      │
│  ├─ Week 7-10:  明渠高级功能                        │
│  ├─ Week 11-14: 有压管道                            │
│  ├─ Week 15-18: 混合系统                            │
│  └─ Week 19-24: 3D可视化+优化                       │
├─────────────────────────────────────────────────────┤
│ Phase 2: 全面测试验证 (Month 7-8)                   │
│  ├─ 65个标准案例100%通过                            │
│  ├─ 与核心引擎结果误差 <1e-6                        │
│  └─ 用户满意度 >4.0/5.0                             │
├─────────────────────────────────────────────────────┤
│ Phase 3-4: 控制与辨识 (Month 9-12)                  │
│  └─ 只有Phase 1-2完成后才启动                       │
└─────────────────────────────────────────────────────┘
```

---

## 🚀 立即开始

### Step 1: 环境准备 (10分钟)

```bash
# 1. 检查前置条件
node --version  # 需要 >= 18.0
python3 --version  # 需要 >= 3.10
docker --version  # 可选，但推荐

# 2. 运行初始化脚本
cd /home/user/HydroClaude
chmod +x web/scripts/setup.sh
./web/scripts/setup.sh

# 这个脚本会：
# - 创建项目目录结构
# - 生成配置文件
# - 初始化前后端项目
# - 创建Docker配置
```

### Step 2: 安装依赖 (10分钟)

```bash
# 前端依赖
cd web/frontend
npm install

# 后端依赖
cd ../backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Step 3: 启动开发环境 (5分钟)

#### 选项A: 使用Docker（推荐）

```bash
cd web/docker
docker-compose up -d

# 访问:
# - 前端: http://localhost:3000
# - 后端: http://localhost:8000
# - API文档: http://localhost:8000/docs
```

#### 选项B: 手动启动

```bash
# 终端1: 启动数据库
docker-compose -f web/docker/docker-compose.yml up -d db redis

# 终端2: 启动后端
cd web/backend
source venv/bin/activate
uvicorn api_gateway.main:app --reload --host 0.0.0.0 --port 8000

# 终端3: 启动前端
cd web/frontend
npm run dev
```

### Step 4: 验证安装 (5分钟)

```bash
# 1. 检查后端API
curl http://localhost:8000/health

# 预期响应: {"status": "ok"}

# 2. 检查前端
# 浏览器访问: http://localhost:3000
# 应该看到登录页面

# 3. 运行基础测试
cd web/backend
pytest tests/test_basic.py -v
```

---

## 📋 第一个里程碑：技术验证 (Week 1-2)

### 目标
验证Web系统能正确调用HydroClaude引擎并获得一致结果

### 任务清单

#### 后端任务（Week 1）

**1. 创建引擎封装接口**

```python
# web/backend/core/hydraulic_engine.py

from solvers.godunov_fvm_solver import GodunvFVMSolver
import numpy as np

class HydraulicEngine:
    """HydroClaude核心引擎封装"""

    def run_canal_simulation(self, config: dict) -> dict:
        """
        运行明渠仿真

        Args:
            config: {
                'width': 10.0,
                'length': 1000.0,
                'n_cells': 200,
                'manning_n': 0.025,
                'slope': 0.001,
                't_end': 100.0,
                'dt_max': 0.1,
                'initial_conditions': {...},
                'boundary_conditions': {...}
            }

        Returns:
            {
                'time': [0, 0.1, 0.2, ...],
                'x': [0, 5, 10, ...],
                'h': [[...], [...], ...],  # h[time_idx, x_idx]
                'Q': [[...], [...], ...],
                'metrics': {
                    'mass_conservation_error': 1.23e-7,
                    'max_velocity': 5.67,
                    ...
                }
            }
        """
        # 创建求解器
        solver = GodunvFVMSolver(
            width=config['width'],
            length=config['length'],
            n_cells=config['n_cells'],
            manning_n=config.get('manning_n', 0.0),
            slope=config.get('slope', 0.0),
            cfl=config.get('cfl', 0.5),
            order=config.get('order', 2),
            use_numba=config.get('use_numba', True)
        )

        # 设置初始条件和边界条件
        # ... (根据config设置)

        # 运行仿真
        h, Q = solver.solve(
            t_final=config['t_end'],
            dt_max=config['dt_max']
        )

        # 计算关键指标
        metrics = self._calculate_metrics(h, Q, solver)

        return {
            'time': solver.time_history,
            'x': solver.x_centers,
            'h': h.tolist(),
            'Q': Q.tolist(),
            'V': (Q / (h * config['width'])).tolist(),
            'metrics': metrics
        }

    def _calculate_metrics(self, h, Q, solver):
        """计算质量守恒等关键指标"""
        # 实现计算逻辑
        pass


# 使用示例
if __name__ == '__main__':
    engine = HydraulicEngine()

    # 溃坝案例
    config = {
        'width': 10.0,
        'length': 1000.0,
        'n_cells': 200,
        'manning_n': 0.0,
        'slope': 0.0,
        't_end': 50.0,
        'dt_max': 0.1,
        'initial_conditions': {
            'type': 'dam_break',
            'dam_position': 500.0,
            'h_left': 10.0,
            'h_right': 1.0
        }
    }

    result = engine.run_canal_simulation(config)
    print(f"仿真完成，质量守恒误差: {result['metrics']['mass_conservation_error']}")
```

**2. 创建FastAPI端点**

```python
# web/backend/api_gateway/routes/simulations.py

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from core.hydraulic_engine import HydraulicEngine

router = APIRouter(prefix="/simulations", tags=["simulations"])
engine = HydraulicEngine()

class SimulationConfig(BaseModel):
    width: float
    length: float
    n_cells: int
    t_end: float
    # ... 其他参数

class SimulationResponse(BaseModel):
    task_id: str
    status: str

@router.post("/", response_model=SimulationResponse)
async def submit_simulation(
    config: SimulationConfig,
    background_tasks: BackgroundTasks
):
    """提交仿真任务"""
    task_id = generate_task_id()

    # 后台执行仿真
    background_tasks.add_task(
        run_simulation_task,
        task_id,
        config.dict()
    )

    return {
        "task_id": task_id,
        "status": "queued"
    }

@router.get("/{task_id}")
async def get_simulation_status(task_id: str):
    """查询仿真状态"""
    # 从数据库或缓存查询状态
    pass

@router.get("/{task_id}/results")
async def get_simulation_results(task_id: str):
    """获取仿真结果"""
    # 从存储加载结果
    pass
```

**3. 编写集成测试**

```python
# web/backend/tests/test_integration.py

import pytest
from httpx import AsyncClient
from api_gateway.main import app

@pytest.mark.asyncio
async def test_dam_break_simulation():
    """测试溃坝案例端到端流程"""

    async with AsyncClient(app=app, base_url="http://test") as client:
        # 1. 提交仿真
        response = await client.post("/simulations", json={
            "width": 10.0,
            "length": 1000.0,
            "n_cells": 200,
            "manning_n": 0.0,
            "slope": 0.0,
            "t_end": 50.0,
            "dt_max": 0.1
        })
        assert response.status_code == 201
        task_id = response.json()['task_id']

        # 2. 等待完成
        await wait_for_completion(client, task_id, timeout=60)

        # 3. 获取结果
        response = await client.get(f"/simulations/{task_id}/results")
        assert response.status_code == 200
        result = response.json()

        # 4. 验证结果
        assert result['metrics']['mass_conservation_error'] < 1e-6
        assert len(result['time']) > 0
        assert len(result['h']) > 0

        # 5. 与直接调用引擎对比
        from core.hydraulic_engine import HydraulicEngine
        engine = HydraulicEngine()
        result_direct = engine.run_canal_simulation({...})

        # 对比结果
        assert_results_equal(result, result_direct, tolerance=1e-6)
```

#### 前端任务（Week 1）

**1. 创建API服务层**

```typescript
// web/frontend/src/services/api.ts

import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

// 仿真API
export const simulationAPI = {
  // 提交仿真
  submit: async (config: SimulationConfig) => {
    const response = await api.post('/simulations', config);
    return response.data;
  },

  // 查询状态
  getStatus: async (taskId: string) => {
    const response = await api.get(`/simulations/${taskId}`);
    return response.data;
  },

  // 获取结果
  getResults: async (taskId: string) => {
    const response = await api.get(`/simulations/${taskId}/results`);
    return response.data;
  },
};

export default api;
```

**2. 创建简单UI**

```typescript
// web/frontend/src/pages/DamBreakDemo.tsx

import React, { useState } from 'react';
import { Button, Card, message } from 'antd';
import { simulationAPI } from '@/services/api';
import Plot from 'react-plotly.js';

const DamBreakDemo: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);

  const runSimulation = async () => {
    setLoading(true);
    try {
      // 1. 提交仿真
      const { task_id } = await simulationAPI.submit({
        width: 10.0,
        length: 1000.0,
        n_cells: 200,
        t_end: 50.0,
        dt_max: 0.1,
      });

      message.info('仿真任务已提交');

      // 2. 轮询状态
      const pollStatus = setInterval(async () => {
        const status = await simulationAPI.getStatus(task_id);

        if (status.status === 'completed') {
          clearInterval(pollStatus);

          // 3. 获取结果
          const data = await simulationAPI.getResults(task_id);
          setResult(data);

          message.success('仿真完成！');
          setLoading(false);
        } else if (status.status === 'failed') {
          clearInterval(pollStatus);
          message.error('仿真失败');
          setLoading(false);
        }
      }, 2000);

    } catch (error) {
      message.error('请求失败');
      setLoading(false);
    }
  };

  return (
    <Card title="溃坝案例演示">
      <Button type="primary" onClick={runSimulation} loading={loading}>
        运行仿真
      </Button>

      {result && (
        <div style={{ marginTop: 20 }}>
          <h3>水深分布</h3>
          <Plot
            data={[{
              x: result.x,
              y: result.h[result.h.length - 1],  // 最后时刻
              type: 'scatter',
              mode: 'lines',
              name: '水深',
            }]}
            layout={{ title: '水深-距离曲线', xaxis: { title: '距离 (m)' }, yaxis: { title: '水深 (m)' } }}
          />

          <h3>质量守恒误差: {result.metrics.mass_conservation_error.toExponential(2)}</h3>
        </div>
      )}
    </Card>
  );
};

export default DamBreakDemo;
```

#### 验收测试（Week 2）

**运行完整测试**：

```bash
# 1. 后端单元测试
cd web/backend
pytest tests/unit/ -v

# 2. 算法验证测试
pytest tests/validation/test_dam_break.py -v

# 3. 前端组件测试
cd web/frontend
npm run test

# 4. E2E测试
npx playwright test
```

**验收标准**：
- ✅ 溃坝案例通过Web API运行成功
- ✅ 结果与直接调用引擎一致（误差<1e-6）
- ✅ 前端能正确显示结果图表
- ✅ 响应时间 <5s

---

## 📊 进度追踪

### Week 1-2 任务看板

```
TODO (待办)
├─ [ ] 后端引擎封装
├─ [ ] FastAPI端点开发
├─ [ ] 数据库设计
├─ [ ] 前端API服务层
└─ [ ] 基础UI组件

IN PROGRESS (进行中)
├─ [ ] ...

DONE (已完成)
├─ [✅] 需求分析
├─ [✅] 技术选型
├─ [✅] 文档编写
└─ [✅] 项目初始化
```

---

## 🆘 常见问题

### Q1: 找不到HydroClaude模块

**问题**：`ModuleNotFoundError: No module named 'solvers'`

**解决**：
```bash
# 确保HydroClaude路径在PYTHONPATH中
export PYTHONPATH=/home/user/HydroClaude:$PYTHONPATH

# 或在代码中添加
import sys
sys.path.insert(0, '/home/user/HydroClaude')
```

### Q2: 数据库连接失败

**问题**：`could not connect to server`

**解决**：
```bash
# 检查PostgreSQL是否运行
docker-compose ps

# 如果没运行，启动它
docker-compose up -d db

# 检查连接
psql postgresql://hydroclaude:password@localhost:5432/hydroclaude
```

### Q3: 前端跨域问题

**问题**：`CORS policy: No 'Access-Control-Allow-Origin' header`

**解决**：
```python
# backend/api_gateway/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 📚 学习资源

### 必读文档
1. [FastAPI官方教程](https://fastapi.tiangolo.com/tutorial/)
2. [React官方文档](https://react.dev/learn)
3. [Three.js入门](https://threejs.org/manual/#en/fundamentals)

### 推荐阅读
- HydroClaude核心文档：`LIBRARY_REFERENCE.md`
- 数值方法：`COMPREHENSIVE_TECHNICAL_ANALYSIS_2025.md`

---

## ✅ 下一步

完成技术验证后：

1. **Week 3-6**: 开发MVP（明渠基础仿真）
   - 参考：`WEB_DEVELOPMENT_ROADMAP_REVISED.md` Milestone 1.2

2. **持续迭代**: 按照路线图逐步推进

3. **定期评审**: 每2周进行进度和质量评审

---

## 🎯 成功标准提醒

**Phase 1-2 必须达到**：
- ✅ 65个标准测试案例100%通过
- ✅ 计算结果与核心引擎误差 <1e-6
- ✅ 用户满意度 >4.0/5.0
- ✅ 零严重Bug

**只有完全达标，才启动Phase 3-4（控制与辨识）！**

---

**祝开发顺利！如有问题，请参考详细设计文档或寻求技术支持。**
