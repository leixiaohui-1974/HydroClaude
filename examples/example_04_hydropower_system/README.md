# 水电站系统仿真

## 概述

完整的水电站系统仿真，包括引水系统、压力管道、调压井、水轮机和发电机。

## 物理原理

水电站是水力-机械-电气的多物理场耦合系统

## 主要功能

- 压力管道水击
- 调压井水位波动
- 水轮机-发电机耦合
- 负荷响应特性

## 应用场景

- 水电站设计
- 过渡过程分析
- 控制策略优化
- 稳定性分析

## 脚本文件

- `example_04_hydropower_plant.py`

## 运行方法

```bash
cd examples/example_04_hydropower_system
PYTHONPATH=../.. python example_04_hydropower_plant.py
```

## 输出结果

### 图表

- 待生成

### 动画

- `outputs/animations/example_04_hydropower_system_hydropower_transient.gif`

![动画](outputs\animations\example_04_hydropower_system_hydropower_transient.gif)

## 技术要点

本示例展示了以下技术：

1. **压力管道水击**
2. **调压井水位波动**
3. **水轮机-发电机耦合**

## 参考

- 项目文档: [HydroClaude文档](../../docs/)
- 相关示例: 查看 `examples/` 目录下的其他示例

---

*本README由自动化脚本生成*
