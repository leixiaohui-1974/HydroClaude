# 串联管网系统

## 概述

多段串联管道的水力计算，包括节点连续性和压力传递。

## 物理原理

串联系统中流量处处相等，总水头损失为各段之和

## 主要功能

- 串联管段
- 节点连续方程
- 压力传递
- 流量守恒

## 应用场景

- 输水管线
- 长距离管道
- 多级泵站
- 压力分析

## 脚本文件

- `example_10_series_network.py`

## 运行方法

```bash
cd examples/example_10_series_network
PYTHONPATH=../.. python code/example_10_series_network.py
```

## 输出结果

### 图表

- `outputs/figures/series_network.png`

### 动画

- `outputs/animations/example_10_series_network_network.gif`

![动画](outputs\animations\example_10_series_network_network.gif)
- `outputs/animations/series_network_embedded.gif`

## 技术要点

本示例展示了以下技术：

1. **串联管段**
2. **节点连续方程**
3. **压力传递**

## 参考

- 项目文档: [HydroClaude文档](../../docs/)
- 相关示例: 查看 `examples/` 目录下的其他示例

---

*本README由自动化脚本生成*
