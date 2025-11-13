# 甩负荷暂态分析

## 概述

分析水电站甩负荷（负荷突然减小或消失）时的暂态过程。

## 物理原理

甩负荷时动能转化为势能，导致转速上升和水位波动

## 主要功能

- 负荷突变响应
- 转速上升分析
- 导叶关闭策略
- 调压井水位波动

## 应用场景

- 电站安全分析
- 调速器整定
- 保护配置
- 事故预案

## 脚本文件

- `example_05_load_rejection.py`

## 运行方法

```bash
cd examples/example_05_transient_analysis
PYTHONPATH=../.. python example_05_load_rejection.py
```

## 输出结果

### 图表

- `outputs/figures/load_rejection.png`

### 动画

- `outputs/animations/example_05_transient_analysis_hydropower_transient.gif`

![动画](outputs\animations\example_05_transient_analysis_hydropower_transient.gif)

## 技术要点

本示例展示了以下技术：

1. **负荷突变响应**
2. **转速上升分析**
3. **导叶关闭策略**

## 参考

- 项目文档: [HydroClaude文档](../../docs/)
- 相关示例: 查看 `examples/` 目录下的其他示例

---

*本README由自动化脚本生成*
