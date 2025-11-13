# RLS参数辨识

## 概述

使用递推最小二乘法（RLS）进行系统参数在线辨识。

## 物理原理

通过最小化预测误差平方和辨识模型参数

## 主要功能

- RLS算法
- 在线参数辨识
- 自适应滤波
- 收敛性分析

## 应用场景

- 系统辨识
- 自适应控制
- 参数估计
- 模型更新

## 脚本文件

- `example_15_rls_identification.py`

## 运行方法

```bash
cd examples/example_15_rls_identification
PYTHONPATH=../.. python code/example_15_rls_identification.py
```

## 输出结果

### 图表

- 待生成

### 动画

- `outputs/animations/example_15_convergence_animation.gif`

![动画](outputs\animations\example_15_convergence_animation.gif)
- `outputs/animations/example_15_rls_identification_control.gif`

## 技术要点

本示例展示了以下技术：

1. **RLS算法**
2. **在线参数辨识**
3. **自适应滤波**

## 参考

- 项目文档: [HydroClaude文档](../../docs/)
- 相关示例: 查看 `examples/` 目录下的其他示例

---

*本README由自动化脚本生成*
