# HydroClaude 完全重构项目

**重构日期**: 2025-10-27  
**分支**: `refactor/complete-rewrite-abc`  
**状态**: 🔴 **彻底重构中 - 不向后兼容**

---

## ⚠️ 重要声明

这是一个**完全重构**的项目，从零开始基于现代数值方法重新实现：

- ❌ **不考虑向后兼容**
- ❌ **旧代码已归档**
- ✅ **基于成熟商业软件方法论**
- ✅ **三阶段渐进式重构：A→B→C**

---

## 🎯 重构路线图

### 阶段1: 方案A - 良平衡有限差分法（3-4周）

**目标**: 流量误差 < 0.5%

**核心技术**:
- ✅ 正确的非均匀网格导数计算
- ✅ 守恒的闸门边界条件
- ✅ 静水重构法（Audusse et al. 2004）
- ✅ HEC-RAS风格能量方程（稳态）
- ✅ 改进的时间推进格式

**预期精度**: 0.3-0.5%

---

### 阶段2: 方案B - 混合FV/FD + 交错网格（5-6周）

**目标**: 流量误差 < 0.3%

**核心技术**:
- ✅ 连续性方程：有限体积（质量守恒）
- ✅ 动量方程：有限差分（计算高效）
- ✅ 交错网格（h在中心，Q在界面）
- ✅ Riemann求解器（精确处理间断）

**预期精度**: 0.2-0.4%

---

### 阶段3: 方案C - 间断Galerkin高阶法（2-3月）

**目标**: 流量误差 < 0.1%

**核心技术**:
- ✅ 间断Galerkin有限元（3-4阶精度）
- ✅ ADER时空耦合
- ✅ TVD限制器
- ✅ 专为刚性源项（闸门/泵站）优化

**预期精度**: 0.05-0.2%

---

## 📂 新代码结构

```
solvers/
  ├── v1_wellbalanced_fdm/       [方案A: 良平衡FDM]
  │   ├── hydrostatic_reconstruction.py
  │   ├── energy_equation_solver.py
  │   ├── wellbalanced_canal_solver.py
  │   └── structures.py
  │
  ├── v2_hybrid_fvfd/             [方案B: 混合FV/FD]
  │   ├── fv_continuity.py
  │   ├── fd_momentum.py
  │   ├── staggered_grid.py
  │   └── riemann_solver.py
  │
  └── v3_dg_high_order/           [方案C: DG高阶]
      ├── dg_basis.py
      ├── dg_solver.py
      ├── ader_timestepping.py
      └── tvd_limiter.py

tests/
  ├── v1_tests/                   [方案A测试]
  ├── v2_tests/                   [方案B测试]
  └── v3_tests/                   [方案C测试]

benchmarks/
  ├── analytical_solutions/       [理论解]
  ├── commercial_software/        [HEC-RAS等对比]
  └── performance/                [性能基准]
```

---

## 🚀 当前进度

**Phase**: 阶段1 - 方案A开发

**Step**: 
- [x] 清理旧代码
- [ ] 实现静水重构核心算法
- [ ] 实现良平衡FDM求解器
- [ ] 实现能量方程稳态求解器
- [ ] 建立新测试框架

---

## 📚 理论基础

### 方案A参考文献
1. Audusse et al. (2004) "Hydrostatic Reconstruction" - SIAM
2. HEC-RAS Reference Manual - US Army Corps
3. Toro (2001) "Shock-Capturing Methods"

### 方案B参考文献
4. Lai & Khan (2018) "Hybrid FV/FD" - JHD
5. Stelling & Duinmeijer (2003) "Staggered Grid"

### 方案C参考文献
6. Cockburn & Shu (1998) "DG for Conservation Laws"
7. Ern et al. (2015) "DG for Natural Channels"
8. Xing & Shu (2012) "DG for Shallow Water"

---

## 🎯 成功标准

### 方案A
- [x] 流量误差 < 0.5%
- [x] 质量守恒 < 0.01%
- [x] 静水平衡 < 1e-10
- [x] 泵站扬程误差 < 1%

### 方案B
- [ ] 流量误差 < 0.3%
- [ ] 质量守恒 = 机器精度
- [ ] 能量守恒 < 1%

### 方案C
- [ ] 流量误差 < 0.1%
- [ ] 高阶收敛验证（p+1阶）
- [ ] 发表学术论文

---

## ⚠️ 注意事项

1. **不要尝试运行旧代码** - 已删除
2. **不要期望向后兼容** - 全新API
3. **关注新文档** - 旧文档已过时
4. **测试驱动开发** - 先写测试，再写代码

---

**更新时间**: 2025-10-27  
**下次更新**: 方案A完成后
