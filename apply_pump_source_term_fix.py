#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
应用泵站源项法修复（最严格的标准方法）

源项法原理：
===========
在动量方程中添加泵站源项：

∂(hu)/∂t + ∂(hu²/h + gh²/2)/∂x = -gh∂z/∂x - ghu²n²/h^(4/3) + S_pump

其中泵站源项：
S_pump(x) = g * H_pump * δ(x - x_pump) / Δx

物理意义：泵站向水体输入能量（做功）
"""

import re

print("=" * 80)
print("应用泵站源项法修复（标准PDE方法）")
print("=" * 80)

# 读取文件
with open('solvers/hydrostatic_canal_solver.py', 'r', encoding='utf-8') as f:
    content = f.read()

print("\n步骤1: 读取文件...")
print(f"  文件大小: {len(content)} 字符")

# ============================================================================
# 修改1: 修改compute_fluxes_and_sources方法，添加泵站源项
# ============================================================================

# 查找compute_fluxes_and_sources方法中的源项计算部分
old_source_computation = r'''        # 摩阻源项（Manning公式）
        S_momentum = np.zeros(self.nx)
        for i in range(self.nx):
            if h\[i\] > self.eps_dry:
                u = hu\[i\] / h\[i\]
                R = h\[i\]  # 假设宽浅渠道，水力半径≈水深
                # Manning摩阻: S_f = n²u²/R^(4/3)
                S_f = self.n \*\* 2 \* u \*\* 2 / \(R \*\* \(4.0/3.0\)\)
                S_momentum\[i\] = -self.g \* h\[i\] \* \(dz_dx\[i\] \+ S_f\)
            else:
                S_momentum\[i\] = 0.0

        # 不再使用源项法

        return F_mass, F_momentum, S_mass, S_momentum'''

new_source_computation = '''        # 摩阻源项（Manning公式）
        S_momentum = np.zeros(self.nx)
        for i in range(self.nx):
            if h[i] > self.eps_dry:
                u = hu[i] / h[i]
                R = h[i]  # 假设宽浅渠道，水力半径≈水深
                # Manning摩阻: S_f = n²u²/R^(4/3)
                S_f = self.n ** 2 * u ** 2 / (R ** (4.0/3.0))
                S_momentum[i] = -self.g * h[i] * (dz_dx[i] + S_f)
            else:
                S_momentum[i] = 0.0

        # ========================================================================
        # 泵站源项法（标准PDE方法）
        # ========================================================================
        # 在泵站位置添加动量源项，代表泵站向水体输入能量
        # 
        # 理论：泵站通过做功增加水体的总能量
        # 动量方程源项：S_pump = g * H_pump / Δx
        # 
        # 参考文献：
        # - Sanders et al. (2010): ParBreZo shallow-water code
        # - Guinot (2008): Wave Propagation in Fluids
        # ========================================================================
        
        if self.structure_indices and self.structure_objects:
            from solvers.gate import PumpStation
            
            for idx, structure in zip(self.structure_indices, self.structure_objects):
                # 只处理运行中的泵站
                if isinstance(structure, PumpStation) and structure.is_running:
                    # 边界检查
                    if 0 < idx < self.nx - 1:
                        # 计算源项强度
                        # S_pump = g * H_pump / Δx
                        # 物理意义：单位体积水体获得的动量增量
                        dx_local = self.dx if self.is_uniform_grid else self.dx_local[idx]
                        S_pump = self.g * structure.rated_head / dx_local
                        
                        # 添加到动量源项
                        # 在泵站节点及其邻居节点上分布源项（平滑处理）
                        # 这样可以避免过于尖锐的数值跳跃
                        weight_center = 0.5
                        weight_neighbor = 0.25
                        
                        S_momentum[idx] += S_pump * weight_center
                        if idx > 0:
                            S_momentum[idx - 1] += S_pump * weight_neighbor
                        if idx < self.nx - 1:
                            S_momentum[idx + 1] += S_pump * weight_neighbor

        return F_mass, F_momentum, S_mass, S_momentum'''

print("\n步骤2: 修改源项计算方法...")
content = re.sub(old_source_computation, new_source_computation, content, flags=re.DOTALL)
print("  ✓ 已添加泵站源项到compute_fluxes_and_sources")

# ============================================================================
# 修改2: 简化_apply_pump_internal_bc方法（源项法下仅用于确保数值稳定性）
# ============================================================================

new_pump_method = '''    def _apply_pump_internal_bc(self):
        """
        泵站源项法的辅助处理（v4.0 - 源项法版本）
        
        在使用源项法时，泵站的主要作用通过动量方程的源项实现。
        此方法仅用于：
        1. 确保泵站节点的流量连续性
        2. 提供数值稳定性
        
        理论基础：
        =========
        源项法在动量方程中添加：
            S_pump = g * H_pump / Δx
        
        这会自然产生水位抬升，无需人工设置跳跃条件。
        
        参考文献：
        =========
        - Sanders et al. (2010): ParBreZo code
        - Guinot (2008): Wave Propagation in Fluids
        - Toro (2009): Source term treatment
        """
        if not self.structure_indices or not self.structure_objects:
            return

        for idx, structure in zip(self.structure_indices, self.structure_objects):
            from solvers.gate import PumpStation

            if not isinstance(structure, PumpStation) or not structure.is_running:
                continue

            # 边界检查
            if idx <= 0 or idx >= self.nx - 1:
                continue

            # 源项法下，仅确保流量连续性（质量守恒）
            # 水位抬升由源项自然产生
            Q_upstream = self.hu[idx - 1] * self.B
            
            # 在泵站及下游节点保持流量连续
            self.hu[idx] = Q_upstream / self.B
            self.hu[idx + 1] = Q_upstream / self.B
            
            # 确保水深为正
            self.h[idx] = max(self.eps_dry, self.h[idx])
            self.h[idx + 1] = max(self.eps_dry, self.h[idx + 1])
    
    def _apply_pump_region_constraints(self):
        """
        【已废弃 v3.0】应用泵站区域约束（旧方法）
        
        v4.0使用源项法，此方法已废弃。
        保留仅为向后兼容。
        """
        # 调用源项法的辅助方法
        self._apply_pump_internal_bc()
'''

print("\n步骤3: 更新泵站边界条件方法...")
pattern = r'    def _apply_pump_internal_bc\(self\):.*?(?=\n    def _apply_pump_region_constraints)'
content = re.sub(pattern, new_pump_method.rstrip() + '\n', content, flags=re.DOTALL)
print("  ✓ 已更新为源项法版本")

# ============================================================================
# 修改3: 更新_get_pump_region_mask方法
# ============================================================================

new_mask_method = '''    def _get_pump_region_mask(self) -> np.ndarray:
        """
        获取泵站区域掩码（源项法版本）
        
        在源项法中，泵站仅影响3个节点的流量设置。
        水位抬升由源项自动产生，不需要人工设置。
        
        Returns:
            mask: 布尔数组，True表示该点在泵站影响区内
        """
        mask = np.zeros(self.nx, dtype=bool)

        if not self.structure_indices or not self.structure_objects:
            return mask

        for idx, structure in zip(self.structure_indices, self.structure_objects):
            from solvers.gate import PumpStation

            if not isinstance(structure, PumpStation) or not structure.is_running:
                continue

            # 边界检查
            if idx <= 0 or idx >= self.nx - 1:
                continue

            # 标记泵站直接影响的3个节点（用于流量连续性设置）
            mask[idx - 1] = True
            mask[idx] = True
            mask[idx + 1] = True

        return mask
'''

print("\n步骤4: 更新掩码方法...")
pattern = r'    def _get_pump_region_mask\(self\) -> np\.ndarray:.*?(?=\n    def )'
content = re.sub(pattern, new_mask_method.rstrip() + '\n', content, flags=re.DOTALL)
print("  ✓ 已更新掩码方法")

# 保存
with open('solvers/hydrostatic_canal_solver.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("\n" + "=" * 80)
print("✓ 源项法修复已成功应用！")
print("=" * 80)
print("\n变更摘要:")
print("  1. ✓ 在compute_fluxes_and_sources中添加泵站源项")
print("     S_pump = g * H_pump / Δx")
print("  2. ✓ 简化_apply_pump_internal_bc（仅保证流量连续）")
print("  3. ✓ 更新_get_pump_region_mask")
print("  4. ✓ 废弃旧的区域约束法")
print("\n物理原理:")
print("  - 泵站通过动量方程源项向水体输入能量")
print("  - 水位抬升由PDE求解器自然产生")
print("  - 无需人工设置跳跃条件或平台区")
print("\n参考文献:")
print("  - Sanders et al. (2010): ParBreZo code")
print("  - Guinot (2008): Wave Propagation in Fluids")
print("  - Toro (2009): Source term treatment")
print("=" * 80)
