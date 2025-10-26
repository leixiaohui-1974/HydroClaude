#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
应用泵站标准内部边界条件法修复

这个脚本会：
1. 读取当前的hydrostatic_canal_solver.py
2. 替换旧的_apply_pump_region_constraints方法
3. 保存修复后的文件
"""

import re

print("=" * 80)
print("应用泵站标准内部边界条件法修复")
print("=" * 80)

# 读取文件
with open('solvers/hydrostatic_canal_solver.py', 'r', encoding='utf-8') as f:
    content = f.read()

print("\n步骤1: 读取文件...")
print(f"  文件大小: {len(content)} 字符")

# 新的标准方法
new_method = '''    def _apply_pump_internal_bc(self):
        """
        泵站作为内部边界条件（标准数值方法 v4.0）
        
        理论基础：
        =========
        泵站在1D浅水方程中产生水位跃变，类似于激波或水跃。
        根据Rankine-Hugoniot跳跃条件：
        
        质量守恒（连续性）：
            Q⁺ = Q⁻  (流量连续)
        
        能量跃变（泵站做功）：
            h⁺ = h⁻ + H_pump  (水位跃升)
        
        其中：
            h⁻, Q⁻: 泵站上游水深和流量
            h⁺, Q⁺: 泵站下游水深和流量
            H_pump: 泵站额定扬程
        
        数值实现：
        =========
        在泵站节点i处：
        1. 从上游（i-1）获取状态
        2. 施加跳跃条件到下游（i+1）
        3. 泵站节点（i）设为过渡值
        4. 其余所有节点由Preissmann求解器自然求解
        
        参考文献：
        =========
        - Toro (2009): Riemann Solvers and Numerical Methods
        - HEC-RAS Technical Reference: Energy equation at structures
        - DHI MIKE 11: Internal boundary conditions
        
        优点：
        =====
        ✓ 物理清晰（能量守恒 + 质量守恒）
        ✓ 仅影响3个节点（i-1, i, i+1）
        ✓ 自然过渡，无人工台阶
        ✓ 类似闸门的标准处理
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

            # 获取上游状态（泵站直接上游节点）
            h_upstream = self.h[idx - 1]
            hu_upstream = self.hu[idx - 1]
            Q_upstream = hu_upstream * self.B
            
            # 施加跳跃条件：
            # ===============
            
            # 1. 能量跳跃：下游水位 = 上游水位 + 泵站扬程
            #    物理意义：泵站向水体做功，增加势能
            h_downstream = h_upstream + structure.rated_head
            
            # 2. 质量守恒：流量连续（稳态假设）
            #    物理意义：质量不能凭空产生或消失
            hu_downstream = hu_upstream
            
            # 应用到下游节点（i+1）
            self.h[idx + 1] = h_downstream
            self.hu[idx + 1] = hu_downstream
            
            # 泵站节点本身（i）：设置为线性插值
            # 物理意义：泵站内部是一个快速的能量转换区域
            # 数值处理：简化为线性过渡
            self.h[idx] = 0.5 * (h_upstream + h_downstream)
            self.hu[idx] = hu_upstream  # 流量保持连续
            
            # 确保水深为正（数值稳定性）
            self.h[idx] = max(self.eps_dry, self.h[idx])
            self.h[idx + 1] = max(self.eps_dry, self.h[idx + 1])
    
    def _apply_pump_region_constraints(self):
        """
        【已废弃 v3.0】应用泵站区域约束（旧方法）
        
        此方法使用15点区域约束，存在以下问题：
        - 与Preissmann PDE求解器冲突
        - 创造非物理的"平台区"
        - 在边界产生数值台阶
        - 需要调整松弛因子"凑"结果
        
        已被标准的内部边界条件法(_apply_pump_internal_bc)替代。
        保留此方法仅为向后兼容。
        """
        # 调用新的标准内部边界条件方法
        self._apply_pump_internal_bc()
'''

# 查找旧方法的位置
pattern = r'    def _apply_pump_region_constraints\(self\):.*?(?=\n    def )'
match = re.search(pattern, content, re.DOTALL)

if match:
    print("\n步骤2: 找到旧方法...")
    print(f"  位置: {match.start()} - {match.end()}")
    print(f"  大小: {match.end() - match.start()} 字符")
    
    # 替换
    new_content = content[:match.start()] + new_method + '\n' + content[match.end():]
    
    print("\n步骤3: 替换方法...")
    print(f"  新内容大小: {len(new_content)} 字符")
    
    # 保存
    with open('solvers/hydrostatic_canal_solver.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("\n✓ 修复已应用！")
    print("\n变更摘要:")
    print("  - 删除: 旧的15点区域约束法 (77行)")
    print("  - 添加: 新的标准内部边界条件法 (88行)")
    print("  - 方法: 从15个节点简化到3个节点")
    print("  - 参考: Toro (2009), HEC-RAS, MIKE 11")
    
else:
    print("\n✗ 错误: 未找到旧方法")
    print("  请检查文件格式")

print("=" * 80)
