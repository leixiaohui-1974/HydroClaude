# 故障测试

## 概述

测试水电站系统在各种故障工况下的响应和保护动作。

## 物理原理

故障工况下系统的非正常运行特性

## 主要功能

- 短路故障
- 失磁保护
- 阀门卡死
- 保护动作逻辑

## 应用场景

- 保护配置
- 故障诊断
- 安全评估
- 应急预案

## 脚本文件

- `example_07_fault_test.py`

## 运行方法

```bash
cd examples/example_07_fault_test
PYTHONPATH=../.. python code/example_07_fault_test.py
```

## 输出结果

### 图表

- 待生成

### 动画

- `outputs/animations/example_07_fault_test_control.gif`

![动画](outputs\animations\example_07_fault_test_control.gif)

## 技术要点

本示例展示了以下技术：

1. **短路故障**
2. **失磁保护**
3. **阀门卡死**

## 参考

- 项目文档: [HydroClaude文档](../../docs/)
- 相关示例: 查看 `examples/` 目录下的其他示例

---

*本README由自动化脚本生成*
