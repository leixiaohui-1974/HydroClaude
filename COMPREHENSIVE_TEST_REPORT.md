# HydroClaude 综合测试报告

**测试日期**: 2025-11-25 16:59:24

**测试时长**: 33.52 秒

##  总体统计

- **总测试数**: 4
- **通过**: 3 
- **失败**: 1 
- **通过率**: 75.0%

##  后台算法测试

###  GodunvFVMSolver

- **状态**: passed
- **信息**: 质量守恒误差: 0.336433%

###  HydrostaticCanalSolver

- **状态**: passed
- **信息**: 收敛: True, 流量误差: 0.000000%

###  canal_utils

- **状态**: failed
- **信息**: 错误: compute_froude_number() missing 1 required positional argument: 'B'

###  ResultValidator

- **状态**: passed
- **信息**: 等级: 优秀 (Excellent), 误差: 0.000000%

##  Web API测试

###  Backend Service

- **状态**: failed
- **信息**: 无法启动后端服务

## ️ Web UI测试

###  Frontend Service

- **状态**: skipped
- **信息**: 前端服务未运行

---

**报告生成时间**: 2025-11-25 16:59:57
