# 明渠非恒定流仿真

## 概述

演示明渠水流的非恒定流动过程，使用Saint-Venant方程描述水位、流速、流量的时空分布。

## 物理原理

明渠流动遵循连续性方程和动量方程（Saint-Venant方程组）

## 主要功能

- Saint-Venant方程求解
- 三种数值方法：显式、Preissmann、HLL
- 边界条件处理（上游流量、下游水深）
- 收敛性和稳定性分析
- 动态可视化（GIF动画）

## 应用场景

- 灌溉渠道
- 排水系统
- 河流防洪
- 水位预报

## 脚本文件

- `batch_modify_scripts.py`
- `run_all.py`
- `validate_all_v2_scripts.py`

## 运行方法

```bash
cd examples/example_01_canal_flow
PYTHONPATH=../.. python batch_modify_scripts.py
```

## 输出结果

- 水位-距离分布图
- 流速-距离分布图
- 时间演化GIF动画
- 收敛性分析报告

## 技术要点

本示例展示了以下技术：

1. **Saint-Venant方程求解**
2. **三种数值方法：显式、Preissmann、HLL**
3. **边界条件处理（上游流量、下游水深）**

## 参考

- 项目文档: [HydroClaude文档](../../docs/)
- 相关示例: 查看 `examples/` 目录下的其他示例

---

*本README由自动化脚本生成*
