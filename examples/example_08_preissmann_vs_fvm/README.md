# Preissmann格式与有限体积法对比

## 概述

对比Preissmann四点隐式格式和有限体积法（FVM）求解明渠流的性能差异。

## 物理原理

Preissmann是隐式格式，无条件稳定；FVM是守恒型方法，处理间断能力强

## 主要功能

- Preissmann四点格式
- 有限体积法（FVM）
- HLL通量计算
- 精度对比
- 稳定性分析
- 计算效率评估

## 应用场景

- 数值方法研究
- 算法选择
- 精度评估
- 明渠仿真

## 脚本文件

- `code/example_08_preissmann_vs_fvm.py`
- `example_08_preissmann_vs_fvm_enhanced.py`

## 运行方法

```bash
cd examples/example_08_preissmann_vs_fvm
PYTHONPATH=../.. python code/example_08_preissmann_vs_fvm.py
```

## 输出结果

- 两种方法的水位对比
- 质量守恒检查
- 计算时间对比
- 精度和效率权衡

## 技术要点

本示例展示了以下技术：

1. **Preissmann四点格式**
2. **有限体积法（FVM）**
3. **HLL通量计算**

## 参考

- 项目文档: [HydroClaude文档](../../docs/)
- 相关示例: 查看 `examples/` 目录下的其他示例

---

*本README由自动化脚本生成*
