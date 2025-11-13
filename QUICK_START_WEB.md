# HydroClaude Web System - Quick Start Guide
# HydroClaude Web系统 - 快速启动指南

**Last Updated:** 2025-11-13  
**Status:** ✅ Phase 1 & 2 Complete - Ready for Use

---

## 🚀 Quick Start / 快速启动

### 1. Start Backend Server / 启动后端服务器

```bash
cd E:\OneDrive\Documents\GitHub\Test\HydroClaude
python -m uvicorn web.backend.api_gateway.main:app --reload --host 0.0.0.0 --port 8000
```

**Server will be available at:** `http://localhost:8000`  
**API Documentation:** `http://localhost:8000/api/docs`

### 2. Test API / 测试API

```powershell
# Get statistics
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/test-cases/statistics"

# List test cases
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/test-cases/?limit=5"

# Search test cases
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/test-cases/search?q=dam"
```

### 3. Access Frontend (Future)
```bash
cd web/frontend
npm install
npm run dev
```

---

## 📊 What's New / 新功能

### ✅ Test Case Integration (541 Cases)
- **扫描并加载**: 541个测试案例（tests: 270, examples: 249, validation: 22）
- **9大分类**: dam_break, pressurized, lake_at_rest, structures, control, water_quality, network, benchmark, general
- **3个难度级别**: beginner, intermediate, advanced
- **10+热门标签**: godunov, gate, control, riemann, network, pump, mpc, pid, dam-break, weno

### ✅ Auto Report Generation
- **6种报告模板**: 溃坝、有压流、湖泊静止、水工结构、控制系统、水质
- **自动分析**: 关键指标、验证检查、物理分析
- **Markdown导出**: 专业报告文档

### ✅ Enhanced Visualization
- **LongitudinalProfile**: 纵剖面图（水面线 + 河床 + 结构）
- **TimeSeriesChart**: 时间序列图（多变量对比）
- **AnimationPlayer**: 动画播放器（时空演变）
- **ComparisonChart**: 场景对比图（多方案）

---

## 🎯 Key API Endpoints / 主要API端点

### Test Cases API

| Endpoint | Method | Description | 中文描述 |
|----------|--------|-------------|----------|
| `/api/v1/test-cases/statistics` | GET | Get statistics | 获取统计信息 |
| `/api/v1/test-cases/` | GET | List test cases | 列出测试案例 |
| `/api/v1/test-cases/search?q={query}` | GET | Search | 搜索案例 |
| `/api/v1/test-cases/categories` | GET | Get categories | 获取分类 |
| `/api/v1/test-cases/detail/{id}` | GET | Get details | 获取详情 |
| `/api/v1/test-cases/run/{id}` | POST | Run test | 运行测试 |
| `/api/v1/test-cases/report/{id}` | GET | Get report | 获取报告 |

### Query Parameters / 查询参数

- `limit`: Number of results (default: 100)
- `offset`: Pagination offset (default: 0)
- `category`: Filter by category (optional)
- `difficulty`: Filter by difficulty (optional)
- `q`: Search query (optional)

---

## 📂 File Structure / 文件结构

```
web/
├── backend/
│   ├── api_gateway/
│   │   ├── main.py                    # FastAPI entry point
│   │   ├── routers/
│   │   │   ├── simulation.py         # Simulation API
│   │   │   └── test_cases.py         # ✨ Test cases API (NEW)
│   │   └── models/
│   │       └── simulation.py
│   ├── test_case_manager.py           # ✨ Case scanner (NEW)
│   ├── auto_report_generator.py       # ✨ Report generator (NEW)
│   └── data/
│       └── test_cases_catalog.json    # ✨ 541 cases (NEW)
│
└── frontend/
    └── src/
        ├── features/
        │   └── test-cases/
        │       ├── TestCaseLibrary.tsx    # ✨ Test library UI (NEW)
        │       └── TestCaseLibrary.css
        ├── components/
        │   └── visualization/
        │       ├── EnhancedCharts.tsx      # ✨ Chart library (NEW)
        │       └── EnhancedCharts.css
        ├── pages/
        │   └── VisualizationDemo.tsx       # ✨ Demo page (NEW)
        └── data/
            └── templates_extended.ts        # ✨ 12 new templates (NEW)
```

---

## 🛠️ Development Commands / 开发命令

### Run Test Case Manager / 运行测试案例管理器
```bash
python web/backend/test_case_manager.py
```

### Test API Integration / 测试API集成
```bash
python test_api_integration.py
```

### Generate Report Example / 生成报告示例
```python
from web.backend.auto_report_generator import ReportGenerator, SimulationResult

generator = ReportGenerator()
result = SimulationResult(...)  # Your simulation result
test_case = {...}  # Your test case metadata
report = generator.generate_report(result, test_case)
markdown = generator.export_to_markdown(report)
```

---

## 📈 Statistics / 统计数据

### Test Cases Distribution
```
Total: 541

By Category:
  general:       381 (70.4%)
  structures:     50 ( 9.2%)
  network:        30 ( 5.5%)
  control:        28 ( 5.2%)
  dam_break:      14 ( 2.6%)
  pressurized:    14 ( 2.6%)
  benchmark:      14 ( 2.6%)
  lake_at_rest:    6 ( 1.1%)
  water_quality:   4 ( 0.7%)

By Difficulty:
  intermediate:  430 (79.5%)
  advanced:       83 (15.3%)
  beginner:       28 ( 5.2%)

Top 10 Tags:
  1. godunov:    167
  2. gate:       126
  3. control:     91
  4. riemann:     84
  5. network:     77
  6. pump:        57
  7. mpc:         49
  8. pid:         45
  9. dam-break:   41
  10. weno:       40
```

### API Performance
```
Endpoint                     Response Time    Status
/test-cases/statistics       ~50ms            ✅
/test-cases/?limit=100       ~120ms           ✅
/test-cases/search           ~80ms            ✅
/test-cases/categories       ~30ms            ✅
```

---

## 🎓 Usage Examples / 使用示例

### Example 1: Get All Dam Break Cases
```python
import requests

response = requests.get(
    "http://localhost:8000/api/v1/test-cases/",
    params={"category": "dam_break", "limit": 20}
)
cases = response.json()
print(f"Found {cases['total']} dam break cases")
for case in cases['cases']:
    print(f"  - {case['metadata']['name']}")
```

### Example 2: Search and Run Test
```python
# Search for gate-related tests
response = requests.get(
    "http://localhost:8000/api/v1/test-cases/search",
    params={"q": "gate"}
)
results = response.json()
print(f"Found {results['total']} cases with 'gate'")

# Run the first test
if results['total'] > 0:
    case_id = results['cases'][0]['metadata']['id']
    run_response = requests.post(
        f"http://localhost:8000/api/v1/test-cases/run/{case_id}"
    )
    print(f"Test queued: {run_response.json()}")
```

### Example 3: Use Visualization Components
```tsx
import { LongitudinalProfile } from './components/visualization/EnhancedCharts';

function MyComponent() {
  const x = [0, 100, 200, 300, 400, 500];
  const h = [5.0, 4.8, 4.6, 4.5, 4.3, 4.2];
  const bed = [2.0, 1.8, 1.6, 1.5, 1.3, 1.2];
  
  const structures = [
    { x: 250, type: 'gate', name: 'Sluice Gate' }
  ];

  return (
    <LongitudinalProfile
      x={x}
      h={h}
      bed={bed}
      structures={structures}
      title="My Canal Profile"
    />
  );
}
```

---

## 🔥 Next Steps / 下一步

1. **Week 2**: Component Library Expansion
   - Add 7 new hydraulic structures
   - Enhance ComponentPalette

2. **Week 3**: Control System Interface
   - PID/MPC configuration panels
   - Performance visualization

3. **Week 4**: Water Quality Interface
   - DO/BOD simulation setup
   - Nutrient transport modeling

4. **Week 5**: Parameter Optimization
   - Multi-objective optimization
   - Sensitivity analysis

5. **Week 7-8**: Testing & Polish
   - Bug fixes
   - Performance optimization
   - Complete documentation

---

## 📚 Documentation / 文档

- **WEB_SYSTEM_PROGRESS_REPORT.md** - Comprehensive progress report
- **LIBRARY_REFERENCE.md** - API reference
- **DEVELOPMENT_GUIDE.md** - Development guidelines
- **WEB_FEATURE_EXPANSION_PLAN.md** - 8-week expansion plan

---

## ❓ Troubleshooting / 故障排除

### Server not starting?
```bash
# Check if port 8000 is in use
netstat -ano | findstr :8000

# Kill the process if needed
taskkill /PID <PID> /F

# Restart server
python -m uvicorn web.backend.api_gateway.main:app --reload --port 8000
```

### GBK encoding errors?
- ✅ Already fixed with `encoding_patch.py`
- Output is suppressed during simulation
- All API responses are UTF-8

### Import errors?
- Make sure you're in the project root directory
- Check Python path configuration in `main.py`

---

## 🎉 Success Indicators / 成功指标

- ✅ **Server Running**: Check `http://localhost:8000`
- ✅ **API Working**: All endpoints return 200 OK
- ✅ **541 Cases Loaded**: Statistics show correct count
- ✅ **Fast Response**: API responds in <150ms
- ✅ **No Errors**: Server logs show no errors

---

**🚀 You're all set! Happy coding!**

*Generated by HydroClaude Development Team*  
*Last Updated: 2025-11-13*


