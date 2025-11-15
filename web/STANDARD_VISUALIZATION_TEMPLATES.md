# 🎨 HydroClaude Web 标准化可视化模板规范

**版本**: v2.0  
**更新日期**: 2025-11-15  
**适用范围**: 所有水力学仿真结果的可视化展示

---

## 📋 目录

1. [设计原则](#设计原则)
2. [标准图表类型](#标准图表类型)
3. [标准表格类型](#标准表格类型)
4. [报告生成模板](#报告生成模板)
5. [实施指南](#实施指南)

---

## 🎯 设计原则

### 1. 统一性原则
- 所有图表使用统一的配色方案
- 所有图表使用统一的字体和字号
- 所有图表使用统一的图例位置和样式

### 2. 简洁性原则
- 每个图表聚焦一个核心信息
- 避免信息过载
- 使用清晰的标签和标题

### 3. 可读性原则
- 高对比度的颜色搭配
- 适当的线条粗细
- 清晰的坐标轴标注

### 4. 专业性原则
- 符合水力学工程规范
- 包含必要的技术参数
- 提供工程解释

---

## 📊 标准图表类型

### 图表1: 水面线纵剖面图 (Water Surface Profile)

**用途**: 显示渠道纵向水面线、河床高程和水深分布

**标准配置**:
```javascript
{
  title: "水面线纵剖面图 Water Surface Profile",
  xaxis: {
    title: "距离 Distance (m)",
    showgrid: true,
    gridcolor: "#E5E7EB"
  },
  yaxis: {
    title: "高程 Elevation (m)",
    showgrid: true,
    gridcolor: "#E5E7EB"
  },
  traces: [
    {
      name: "河床高程 Bed Elevation",
      type: "line",
      color: "#8B4513", // 棕色
      width: 2,
      fill: "tozeroy",
      fillcolor: "rgba(139, 69, 19, 0.2)"
    },
    {
      name: "水面线 Water Surface",
      type: "line",
      color: "#1E90FF", // 蓝色
      width: 3,
      fill: "tonexty",
      fillcolor: "rgba(30, 144, 255, 0.3)"
    }
  ],
  annotations: [
    {
      text: "正常水深 Normal Depth",
      type: "horizontal_line",
      color: "#00AA00"
    },
    {
      text: "临界水深 Critical Depth",
      type: "horizontal_line",
      color: "#FF6B6B"
    }
  ]
}
```

**显示内容**:
- ✅ 河床高程线（填充）
- ✅ 水面线（填充）
- ✅ 正常水深参考线
- ✅ 临界水深参考线
- ✅ 关键位置标注（闸门、堰等）

**尺寸**: 1200×600 px (宽×高)

---

### 图表2: 水深分布图 (Depth Distribution)

**用途**: 显示沿程水深变化

**标准配置**:
```javascript
{
  title: "水深分布图 Depth Distribution",
  xaxis: {
    title: "距离 Distance (m)"
  },
  yaxis: {
    title: "水深 Depth (m)"
  },
  traces: [
    {
      name: "水深 Water Depth",
      type: "line",
      color: "#1E90FF",
      width: 3,
      mode: "lines+markers",
      marker: {
        size: 4,
        color: "#1E90FF"
      }
    }
  ]
}
```

**显示内容**:
- ✅ 水深分布曲线
- ✅ 平均水深参考线
- ✅ 最大/最小水深标注

**尺寸**: 1000×500 px

---

### 图表3: 流速分布图 (Velocity Distribution)

**用途**: 显示沿程流速变化

**标准配置**:
```javascript
{
  title: "流速分布图 Velocity Distribution",
  xaxis: {
    title: "距离 Distance (m)"
  },
  yaxis: {
    title: "流速 Velocity (m/s)"
  },
  traces: [
    {
      name: "流速 Velocity",
      type: "line",
      color: "#FF6B6B",
      width: 3,
      mode: "lines"
    }
  ],
  annotations: [
    {
      text: "最大允许流速 Max Allowable Velocity",
      type: "horizontal_line",
      color: "#FFA500",
      dash: "dash"
    }
  ]
}
```

**显示内容**:
- ✅ 流速分布曲线
- ✅ 平均流速参考线
- ✅ 最大允许流速警戒线

**尺寸**: 1000×500 px

---

### 图表4: Froude数分布图 (Froude Number Distribution)

**用途**: 显示流态分布（急流/缓流）

**标准配置**:
```javascript
{
  title: "Froude数分布图 Froude Number Distribution",
  xaxis: {
    title: "距离 Distance (m)"
  },
  yaxis: {
    title: "Froude数 Froude Number"
  },
  traces: [
    {
      name: "Froude数",
      type: "line",
      color: "#00AA00",
      width: 3
    }
  ],
  shapes: [
    {
      type: "rect",
      y0: 0, y1: 1,
      fillcolor: "rgba(0, 170, 0, 0.1)",
      line: { width: 0 },
      label: "缓流区 Subcritical"
    },
    {
      type: "rect",
      y0: 1, y1: 3,
      fillcolor: "rgba(255, 107, 107, 0.1)",
      line: { width: 0 },
      label: "急流区 Supercritical"
    }
  ],
  annotations: [
    {
      text: "临界流 Fr=1",
      y: 1,
      type: "horizontal_line",
      color: "#FF0000",
      width: 2
    }
  ]
}
```

**显示内容**:
- ✅ Froude数曲线
- ✅ 临界流分界线 (Fr=1)
- ✅ 缓流/急流区域标注

**尺寸**: 1000×500 px

---

### 图表5: 流量分布图 (Discharge Distribution)

**用途**: 显示沿程流量变化（检验质量守恒）

**标准配置**:
```javascript
{
  title: "流量分布图 Discharge Distribution",
  xaxis: {
    title: "距离 Distance (m)"
  },
  yaxis: {
    title: "流量 Discharge (m³/s)"
  },
  traces: [
    {
      name: "流量 Discharge",
      type: "line",
      color: "#9B59B6",
      width: 3
    }
  ],
  annotations: [
    {
      text: "设计流量 Design Discharge",
      type: "horizontal_line",
      color: "#00AA00",
      dash: "dash"
    }
  ]
}
```

**显示内容**:
- ✅ 流量分布曲线
- ✅ 设计流量参考线
- ✅ 流量误差标注

**尺寸**: 1000×500 px

---

### 图表6: 时空演化图 (Space-Time Evolution)

**用途**: 显示水深/流量随时间和空间的演化（等值线图）

**标准配置**:
```javascript
{
  title: "水深时空演化图 Depth Space-Time Evolution",
  xaxis: {
    title: "距离 Distance (m)"
  },
  yaxis: {
    title: "时间 Time (s)"
  },
  type: "contour",
  colorscale: "Viridis",
  colorbar: {
    title: "水深 (m)"
  }
}
```

**显示内容**:
- ✅ 等值线图
- ✅ 颜色条标注
- ✅ 关键时刻标注

**尺寸**: 1000×700 px

---

### 图表7: 单点时序图 (Time Series at Location)

**用途**: 显示某个位置随时间的水深/流量变化

**标准配置**:
```javascript
{
  title: "关键位置时序图 Time Series at Key Location",
  xaxis: {
    title: "时间 Time (s)"
  },
  yaxis: {
    title: "水深 Depth (m)"
  },
  traces: [
    {
      name: "水深 Depth",
      type: "line",
      color: "#1E90FF",
      width: 2
    }
  ]
}
```

**显示内容**:
- ✅ 时间序列曲线
- ✅ 平衡态参考线
- ✅ 关键事件标注（如：闸门开启）

**尺寸**: 1000×500 px

---

## 📋 标准表格类型

### 表格1: 仿真配置参数表 (Simulation Configuration)

**用途**: 显示仿真的输入参数

| 参数名称 | 参数值 | 单位 | 说明 |
|----------|--------|------|------|
| 渠道长度 Length | 2000 | m | 渠道总长度 |
| 渠道宽度 Width | 5.0 | m | 矩形渠道宽度 |
| 糙率系数 Manning's n | 0.025 | - | 曼宁糙率系数 |
| 底坡 Bed Slope | 0.0005 | - | 渠底纵坡 |
| 网格数 Cells | 200 | - | 空间离散网格数 |
| CFL数 CFL | 0.3 | - | 时间步长控制参数 |
| 模拟时长 Duration | 60.0 | s | 仿真总时间 |
| 上游边界 Upstream BC | Q = 10.0 m³/s | - | 流量边界条件 |
| 下游边界 Downstream BC | h = 2.0 m | - | 水深边界条件 |

**格式要求**:
- ✅ 中英文对照
- ✅ 包含单位
- ✅ 包含说明
- ✅ 参数对齐

---

### 表格2: 仿真结果统计表 (Simulation Statistics)

**用途**: 显示仿真的关键结果统计

| 统计指标 | 数值 | 单位 | 评价标准 | 状态 |
|----------|------|------|----------|------|
| 平均水深 Avg Depth | 2.000 | m | > 1.5 m | ✅ 合格 |
| 最大水深 Max Depth | 2.050 | m | < 3.0 m | ✅ 合格 |
| 最小水深 Min Depth | 1.950 | m | > 0.5 m | ✅ 合格 |
| 平均流速 Avg Velocity | 1.000 | m/s | < 2.0 m/s | ✅ 合格 |
| 最大流速 Max Velocity | 1.050 | m/s | < 3.0 m/s | ✅ 合格 |
| 平均Froude数 Avg Fr | 0.226 | - | < 1.0 | ✅ 缓流 |
| 流量守恒误差 Mass Error | 0.000001 | % | < 0.01% | ✅ 优秀 |
| 计算耗时 CPU Time | 0.234 | s | < 60 s | ✅ 快速 |

**格式要求**:
- ✅ 包含评价标准
- ✅ 状态标识（✅❌⚠️）
- ✅ 保留合理精度
- ✅ 中英文对照

---

### 表格3: 关键位置分析表 (Key Locations Analysis)

**用途**: 显示关键位置的详细参数

| 位置 | 距离 (m) | 水深 (m) | 流速 (m/s) | Froude数 | 流量 (m³/s) | 备注 |
|------|---------|---------|-----------|---------|------------|------|
| 上游边界 Upstream | 0 | 2.00 | 1.00 | 0.23 | 10.00 | 边界条件 |
| 闸门位置 Gate | 1000 | 1.85 | 1.08 | 0.25 | 10.00 | 水跃位置 |
| 下游边界 Downstream | 2000 | 2.00 | 1.00 | 0.23 | 10.00 | 边界条件 |

**格式要求**:
- ✅ 包含关键水工结构
- ✅ 包含边界位置
- ✅ 备注特殊现象
- ✅ 中英文对照

---

### 表格4: 水工结构参数表 (Hydraulic Structures)

**用途**: 显示模型中的水工结构参数

| 结构类型 | 位置 (m) | 参数1 | 参数2 | 参数3 | 状态 |
|---------|---------|-------|-------|-------|------|
| 闸门 Sluice Gate | 500 | 宽度: 10 m | 开度: 5 m | 流量系数: 0.6 | ✅ 正常 |
| 溢流堰 Weir | 1000 | 宽度: 10 m | 堰顶高程: 0.5 m | - | ✅ 正常 |

**格式要求**:
- ✅ 结构类型标注
- ✅ 位置精确
- ✅ 参数完整
- ✅ 状态标识

---

## 📄 报告生成模板

### 模板1: 标准仿真报告 (Standard Simulation Report)

**结构**:

```markdown
# HydroClaude 仿真分析报告
## Hydraulic Simulation Analysis Report

---

### 1. 项目信息 Project Information

- **项目名称 Project Name**: [自动填入]
- **仿真ID Simulation ID**: [自动填入]
- **生成时间 Generated**: [自动填入]
- **分析人员 Analyst**: [可选]

---

### 2. 仿真配置 Simulation Configuration

[表格1: 仿真配置参数表]

---

### 3. 水工结构 Hydraulic Structures

[表格4: 水工结构参数表]

---

### 4. 仿真结果 Simulation Results

#### 4.1 结果统计 Statistics

[表格2: 仿真结果统计表]

#### 4.2 水面线分析 Water Surface Profile

[图表1: 水面线纵剖面图]

**分析说明 Analysis**:
- 水流类型: [缓流/急流]
- 流态稳定性: [稳定/不稳定]
- 关键现象: [水跃/壅水/...]

#### 4.3 水深分布 Depth Distribution

[图表2: 水深分布图]

#### 4.4 流速分布 Velocity Distribution

[图表3: 流速分布图]

**安全评估 Safety Assessment**:
- 最大流速: [数值] m/s
- 允许流速: [数值] m/s
- 评估结果: [✅合格 / ❌超标]

#### 4.5 流态分析 Flow Regime Analysis

[图表4: Froude数分布图]

#### 4.6 流量分析 Discharge Analysis

[图表5: 流量分布图]

**质量守恒 Mass Conservation**:
- 流量误差: [数值]%
- 评估: [✅优秀 / ⚠️可接受 / ❌失败]

---

### 5. 关键位置分析 Key Locations Analysis

[表格3: 关键位置分析表]

---

### 6. 工程评价 Engineering Assessment

#### 6.1 设计合规性 Design Compliance

- [ ] ✅ 通水能力满足要求
- [ ] ✅ 流速在安全范围内
- [ ] ✅ 水深满足设计要求
- [ ] ✅ 流态稳定

#### 6.2 风险评估 Risk Assessment

- **高风险 High Risk**: [列出]
- **中风险 Medium Risk**: [列出]
- **低风险 Low Risk**: [列出]

#### 6.3 改进建议 Recommendations

1. [建议1]
2. [建议2]
3. [建议3]

---

### 7. 技术指标 Technical Metrics

- **计算精度 Accuracy**: [数值]%
- **计算耗时 CPU Time**: [数值] s
- **收敛性 Convergence**: [✅收敛 / ❌未收敛]

---

### 8. 附录 Appendix

#### 8.1 时空演化 Space-Time Evolution

[图表6: 时空演化图]

#### 8.2 关键位置时序 Time Series

[图表7: 单点时序图]

---

### 报告说明 Report Notes

- 本报告由HydroClaude自动生成
- 图表和数据基于数值模拟结果
- 工程决策需结合实际情况综合考虑

---

**生成时间 Generated**: [时间戳]  
**系统版本 Version**: HydroClaude v1.0.0
```

---

### 模板2: 对比分析报告 (Comparison Report)

**用途**: 多场景对比分析

**结构**:

```markdown
# HydroClaude 多场景对比分析报告
## Multi-Scenario Comparison Report

---

### 1. 对比概况 Comparison Overview

- **对比场景数 Number of Scenarios**: [数量]
- **对比参数 Comparison Parameters**: [列表]
- **生成时间 Generated**: [时间戳]

---

### 2. 场景配置对比 Configuration Comparison

| 参数 Parameter | 场景1 | 场景2 | 场景3 | 差异说明 |
|---------------|-------|-------|-------|----------|
| [参数1] | [值] | [值] | [值] | [说明] |
| [参数2] | [值] | [值] | [值] | [说明] |

---

### 3. 结果对比 Results Comparison

#### 3.1 水面线对比

[多场景水面线叠加图]

#### 3.2 关键指标对比

| 指标 Metric | 场景1 | 场景2 | 场景3 | 最优方案 |
|------------|-------|-------|-------|----------|
| 平均水深 | [值] | [值] | [值] | [场景X] |
| 最大流速 | [值] | [值] | [值] | [场景X] |
| 流量误差 | [值] | [值] | [值] | [场景X] |

---

### 4. 综合评价 Overall Assessment

- **推荐方案 Recommended**: [场景X]
- **理由 Reason**: [说明]

---
```

---

### 模板3: 快速测试报告 (Quick Test Report)

**用途**: 快速验证测试

**结构**:

```markdown
# 快速测试报告 Quick Test Report

---

## ✅ 测试通过 Test Passed

- **测试ID Test ID**: [ID]
- **测试时间 Time**: [时间戳]
- **测试结果 Result**: ✅ PASS / ❌ FAIL

---

## 关键指标 Key Metrics

| 指标 | 实际值 | 期望值 | 状态 |
|------|--------|--------|------|
| 流量误差 | [值] | < 0.01% | ✅ |
| 计算耗时 | [值] | < 10 s | ✅ |

---

## 快速图表 Quick Charts

[水面线图]
[流量分布图]

---
```

---

## 🚀 实施指南

### 1. 前端实现

#### 1.1 创建可视化组件库

路径: `/web/frontend/src/components/visualization/StandardCharts.tsx`

```typescript
// 标准图表生成器
export const StandardCharts = {
  // 水面线纵剖面图
  createWaterSurfaceProfile(data: SimulationData) {
    // 实现标准图表1
  },
  
  // 水深分布图
  createDepthDistribution(data: SimulationData) {
    // 实现标准图表2
  },
  
  // ... 其他标准图表
}
```

#### 1.2 创建报告生成器

路径: `/web/frontend/src/utils/reportGenerator.ts`

```typescript
// 标准报告生成器
export const ReportGenerator = {
  // 生成标准仿真报告
  generateStandardReport(data: SimulationData): string {
    // 实现模板1
  },
  
  // 生成对比报告
  generateComparisonReport(scenarios: SimulationData[]): string {
    // 实现模板2
  },
  
  // 导出PDF
  exportToPDF(report: string): void {
    // PDF导出功能
  }
}
```

### 2. 后端实现

#### 2.1 图表数据预处理

路径: `/web/backend/core/visualization_helper.py`

```python
class VisualizationHelper:
    """可视化数据预处理"""
    
    @staticmethod
    def prepare_water_surface_data(result):
        """准备水面线数据"""
        # 计算河床高程
        # 计算水面高程
        # 计算参考线
        return {
            'x': [...],
            'bed_elevation': [...],
            'water_surface': [...],
            'normal_depth': ...,
            'critical_depth': ...
        }
```

#### 2.2 报告模板引擎

路径: `/web/backend/core/report_generator.py`

```python
class ReportGenerator:
    """报告生成器"""
    
    def generate_standard_report(self, simulation_result):
        """生成标准报告"""
        # 使用Jinja2模板
        # 填充数据
        # 生成Markdown/HTML
        pass
```

### 3. 配色方案

**主色调 Primary Colors**:
- 水体: `#1E90FF` (DodgerBlue)
- 地面: `#8B4513` (SaddleBrown)
- 成功: `#00AA00` (Green)
- 警告: `#FFA500` (Orange)
- 危险: `#FF6B6B` (Red)

**辅助色 Secondary Colors**:
- 流速: `#FF6B6B` (Coral)
- Froude数: `#00AA00` (Green)
- 流量: `#9B59B6` (Purple)

**背景色 Background Colors**:
- 网格: `#E5E7EB` (Gray-200)
- 填充: `rgba(color, 0.3)` (30% 透明度)

### 4. 字体规范

- **标题**: 16pt, Bold
- **坐标轴标签**: 12pt, Regular
- **图例**: 11pt, Regular
- **注释**: 10pt, Italic

---

## 📝 使用示例

### 示例1: 生成标准报告

```typescript
import { StandardCharts } from '@/components/visualization/StandardCharts';
import { ReportGenerator } from '@/utils/reportGenerator';

// 1. 获取仿真结果
const result = await getSimulationResult(taskId);

// 2. 生成标准图表
const charts = {
  profile: StandardCharts.createWaterSurfaceProfile(result),
  depth: StandardCharts.createDepthDistribution(result),
  velocity: StandardCharts.createVelocityDistribution(result),
  froude: StandardCharts.createFroudeDistribution(result),
  discharge: StandardCharts.createDischargeDistribution(result)
};

// 3. 生成报告
const report = ReportGenerator.generateStandardReport({
  result,
  charts
});

// 4. 导出PDF
ReportGenerator.exportToPDF(report);
```

### 示例2: 场景对比

```typescript
import { ComparisonCharts } from '@/components/visualization/ComparisonCharts';

// 1. 获取多个场景
const scenarios = [result1, result2, result3];

// 2. 生成对比图表
const comparisonChart = ComparisonCharts.createProfileComparison(scenarios);

// 3. 生成对比报告
const report = ReportGenerator.generateComparisonReport(scenarios);
```

---

## ✅ 检查清单

在实施标准化模板时，请确保：

- [ ] 所有图表使用统一配色方案
- [ ] 所有图表包含中英文对照标签
- [ ] 所有表格包含单位和说明
- [ ] 所有报告包含生成时间戳
- [ ] 所有图表可导出高分辨率图片
- [ ] 所有报告可导出PDF格式
- [ ] 响应式设计支持移动端查看
- [ ] 图表支持交互式缩放和悬停提示

---

## 🎯 下一步计划

1. **Phase 1**: 实现基础图表组件库 (1-2天)
2. **Phase 2**: 实现标准表格组件 (1天)
3. **Phase 3**: 实现报告生成器 (2-3天)
4. **Phase 4**: 测试和优化 (1-2天)
5. **Phase 5**: 文档和培训 (1天)

---

**维护者 Maintainer**: HydroClaude Team  
**联系方式 Contact**: [待定]  
**更新频率 Update Frequency**: 根据用户反馈持续改进

---

**文档结束 End of Document**
