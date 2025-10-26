#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
频域分析工具

提供Bode图、Nyquist图、稳定裕度分析等功能

作者: Claude AI
日期: 2025-10-26
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy import signal
from typing import Tuple, Dict, Optional
import warnings


class FrequencyAnalyzer:
    """
    频域分析器
    
    分析系统频率响应特性，包括：
    - Bode图（幅频和相频特性）
    - Nyquist图（稳定性）
    - 增益裕度和相位裕度
    - 谐振峰和带宽
    """
    
    def __init__(self, num: np.ndarray, den: np.ndarray, dt: float = 1.0):
        """
        初始化频域分析器
        
        Args:
            num: 传递函数分子系数
            den: 传递函数分母系数
            dt: 采样周期
        """
        self.num = np.array(num)
        self.den = np.array(den)
        self.dt = dt
        
        # 创建传递函数对象（离散系统）
        self.sys = signal.TransferFunction(num, den, dt=dt)
        
        # 频率点（对数分布）
        self.w = np.logspace(-3, 2, 1000)  # 0.001 到 100 rad/s
        
    def bode(self, plot: bool = True) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        计算Bode图
        
        Args:
            plot: 是否绘图
            
        Returns:
            w: 频率点 (rad/s)
            mag: 幅值 (dB)
            phase: 相位 (度)
        """
        # 计算频率响应
        w, h = signal.freqz(self.num, self.den, worN=self.w, fs=1/self.dt)
        
        # 转换为dB和度
        mag = 20 * np.log10(np.abs(h) + 1e-10)
        phase = np.angle(h, deg=True)
        
        if plot:
            self._plot_bode(w, mag, phase)
        
        return w, mag, phase
    
    def _plot_bode(self, w: np.ndarray, mag: np.ndarray, phase: np.ndarray):
        """绘制Bode图"""
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
        
        # 幅频特性
        ax1.semilogx(w, mag, 'b-', linewidth=2)
        ax1.set_xlabel('Frequency (rad/s)', fontsize=11)
        ax1.set_ylabel('Magnitude (dB)', fontsize=11)
        ax1.set_title('Bode Diagram - Magnitude', fontweight='bold')
        ax1.grid(True, which='both', alpha=0.3)
        ax1.axhline(0, color='k', linestyle='--', linewidth=0.8, alpha=0.5)
        
        # 相频特性
        ax2.semilogx(w, phase, 'r-', linewidth=2)
        ax2.set_xlabel('Frequency (rad/s)', fontsize=11)
        ax2.set_ylabel('Phase (degrees)', fontsize=11)
        ax2.set_title('Bode Diagram - Phase', fontweight='bold')
        ax2.grid(True, which='both', alpha=0.3)
        ax2.axhline(-180, color='k', linestyle='--', linewidth=0.8, alpha=0.5)
        
        plt.tight_layout()
        return fig
    
    def nyquist(self, plot: bool = True) -> Tuple[np.ndarray, np.ndarray]:
        """
        计算Nyquist图
        
        Args:
            plot: 是否绘图
            
        Returns:
            real: 实部
            imag: 虚部
        """
        w, h = signal.freqz(self.num, self.den, worN=self.w, fs=1/self.dt)
        
        real = np.real(h)
        imag = np.imag(h)
        
        if plot:
            self._plot_nyquist(real, imag)
        
        return real, imag
    
    def _plot_nyquist(self, real: np.ndarray, imag: np.ndarray):
        """绘制Nyquist图"""
        fig, ax = plt.subplots(figsize=(8, 8))
        
        # 绘制Nyquist曲线
        ax.plot(real, imag, 'b-', linewidth=2, label='G(jω)')
        ax.plot(real, -imag, 'b--', linewidth=1, alpha=0.5, label='G(-jω)')
        
        # 关键点
        ax.plot(-1, 0, 'rx', markersize=15, label='Critical Point (-1, 0)')
        ax.plot(real[0], imag[0], 'go', markersize=10, label='ω=0')
        ax.plot(real[-1], imag[-1], 'rs', markersize=10, label='ω=∞')
        
        # 单位圆
        theta = np.linspace(0, 2*np.pi, 100)
        ax.plot(np.cos(theta), np.sin(theta), 'k:', linewidth=1, alpha=0.3)
        
        ax.set_xlabel('Real Part', fontsize=11)
        ax.set_ylabel('Imaginary Part', fontsize=11)
        ax.set_title('Nyquist Diagram', fontweight='bold', fontsize=12)
        ax.grid(True, alpha=0.3)
        ax.axis('equal')
        ax.legend()
        
        plt.tight_layout()
        return fig
    
    def stability_margins(self) -> Dict:
        """
        计算稳定裕度
        
        Returns:
            margins: 包含增益裕度和相位裕度的字典
        """
        w, h = signal.freqz(self.num, self.den, worN=self.w, fs=1/self.dt)
        
        mag = np.abs(h)
        phase = np.angle(h, deg=True)
        
        # 1. 增益裕度 (Gain Margin)
        # 在相位=-180°处的增益倒数
        phase_crossover_indices = np.where(np.diff(np.sign(phase + 180)))[0]
        
        if len(phase_crossover_indices) > 0:
            idx = phase_crossover_indices[0]
            w_pc = w[idx]  # 相位穿越频率
            gm = 1 / mag[idx]  # 增益裕度（倍数）
            gm_db = 20 * np.log10(gm) if gm > 0 else -np.inf  # 转dB
        else:
            w_pc = np.nan
            gm = np.inf
            gm_db = np.inf
        
        # 2. 相位裕度 (Phase Margin)
        # 在增益=1(0dB)处的相位与-180°的差
        gain_crossover_indices = np.where(np.diff(np.sign(mag - 1)))[0]
        
        if len(gain_crossover_indices) > 0:
            idx = gain_crossover_indices[-1]  # 取最后一个
            w_gc = w[idx]  # 增益穿越频率
            pm = 180 + phase[idx]  # 相位裕度（度）
        else:
            w_gc = np.nan
            pm = np.inf
        
        # 3. 截止频率（带宽）
        # -3dB带宽
        mag_db = 20 * np.log10(mag + 1e-10)
        bw_indices = np.where(mag_db < -3)[0]
        if len(bw_indices) > 0:
            bandwidth = w[bw_indices[0]]
        else:
            bandwidth = np.nan
        
        # 4. 谐振峰
        peak_mag = np.max(mag)
        peak_db = 20 * np.log10(peak_mag)
        peak_idx = np.argmax(mag)
        peak_freq = w[peak_idx]
        
        return {
            'gain_margin_db': gm_db,
            'gain_margin': gm,
            'phase_crossover_freq': w_pc,
            'phase_margin_deg': pm,
            'gain_crossover_freq': w_gc,
            'bandwidth': bandwidth,
            'peak_magnitude_db': peak_db,
            'peak_frequency': peak_freq
        }
    
    def sensitivity_function(self, controller_num: Optional[np.ndarray] = None,
                            controller_den: Optional[np.ndarray] = None,
                            plot: bool = True) -> Tuple[np.ndarray, np.ndarray]:
        """
        计算灵敏度函数 S = 1/(1+PC)
        
        Args:
            controller_num: 控制器分子
            controller_den: 控制器分母
            plot: 是否绘图
            
        Returns:
            w: 频率
            S: 灵敏度函数幅值 (dB)
        """
        w, h_plant = signal.freqz(self.num, self.den, worN=self.w, fs=1/self.dt)
        
        if controller_num is not None and controller_den is not None:
            _, h_controller = signal.freqz(controller_num, controller_den, worN=self.w, fs=1/self.dt)
            L = h_plant * h_controller  # 开环传递函数
        else:
            L = h_plant
        
        S = 1 / (1 + L)  # 灵敏度函数
        S_mag_db = 20 * np.log10(np.abs(S) + 1e-10)
        
        if plot:
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.semilogx(w, S_mag_db, 'b-', linewidth=2)
            ax.set_xlabel('Frequency (rad/s)', fontsize=11)
            ax.set_ylabel('|S(jω)| (dB)', fontsize=11)
            ax.set_title('Sensitivity Function', fontweight='bold')
            ax.grid(True, which='both', alpha=0.3)
            ax.axhline(0, color='k', linestyle='--', linewidth=0.8, alpha=0.5)
            ax.axhline(6, color='r', linestyle=':', linewidth=1, label='6 dB limit')
            ax.legend()
            plt.tight_layout()
        
        return w, S_mag_db
    
    def complementary_sensitivity(self, controller_num: Optional[np.ndarray] = None,
                                  controller_den: Optional[np.ndarray] = None,
                                  plot: bool = True) -> Tuple[np.ndarray, np.ndarray]:
        """
        计算补灵敏度函数 T = PC/(1+PC)
        
        Args:
            controller_num: 控制器分子
            controller_den: 控制器分母
            plot: 是否绘图
            
        Returns:
            w: 频率
            T: 补灵敏度函数幅值 (dB)
        """
        w, h_plant = signal.freqz(self.num, self.den, worN=self.w, fs=1/self.dt)
        
        if controller_num is not None and controller_den is not None:
            _, h_controller = signal.freqz(controller_num, controller_den, worN=self.w, fs=1/self.dt)
            L = h_plant * h_controller
        else:
            L = h_plant
        
        T = L / (1 + L)  # 补灵敏度函数
        T_mag_db = 20 * np.log10(np.abs(T) + 1e-10)
        
        if plot:
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.semilogx(w, T_mag_db, 'r-', linewidth=2)
            ax.set_xlabel('Frequency (rad/s)', fontsize=11)
            ax.set_ylabel('|T(jω)| (dB)', fontsize=11)
            ax.set_title('Complementary Sensitivity Function', fontweight='bold')
            ax.grid(True, which='both', alpha=0.3)
            ax.axhline(0, color='k', linestyle='--', linewidth=0.8, alpha=0.5)
            plt.tight_layout()
        
        return w, T_mag_db
    
    def print_report(self):
        """打印频域分析报告"""
        margins = self.stability_margins()
        
        print("\n" + "="*60)
        print("频域分析报告")
        print("="*60)
        
        print("\n1. 稳定裕度:")
        print(f"  增益裕度: {margins['gain_margin_db']:.2f} dB ({margins['gain_margin']:.2f} 倍)")
        print(f"  相位裕度: {margins['phase_margin_deg']:.2f} °")
        print(f"  增益穿越频率: {margins['gain_crossover_freq']:.4f} rad/s")
        print(f"  相位穿越频率: {margins['phase_crossover_freq']:.4f} rad/s")
        
        print("\n2. 性能指标:")
        print(f"  带宽 (-3dB): {margins['bandwidth']:.4f} rad/s")
        print(f"  谐振峰: {margins['peak_magnitude_db']:.2f} dB @ {margins['peak_frequency']:.4f} rad/s")
        
        print("\n3. 稳定性评估:")
        if margins['gain_margin_db'] > 6 and margins['phase_margin_deg'] > 45:
            print("  ✅ 系统稳定性良好（GM>6dB, PM>45°）")
        elif margins['gain_margin_db'] > 3 and margins['phase_margin_deg'] > 30:
            print("  ⚠️  系统稳定性一般（GM>3dB, PM>30°）")
        else:
            print("  ❌ 系统稳定性差（GM<3dB 或 PM<30°）")
        
        print("="*60)


def compare_systems(systems: Dict[str, Tuple[np.ndarray, np.ndarray]], 
                   dt: float = 1.0, save_path: Optional[str] = None):
    """
    对比多个系统的频域特性
    
    Args:
        systems: 字典 {名称: (num, den)}
        dt: 采样周期
        save_path: 保存路径
    """
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))
    
    w = np.logspace(-3, 2, 1000)
    colors = ['b', 'r', 'g', 'm', 'c']
    
    for i, (name, (num, den)) in enumerate(systems.items()):
        color = colors[i % len(colors)]
        
        # 频率响应
        w_sys, h = signal.freqz(num, den, worN=w, fs=1/dt)
        
        mag_db = 20 * np.log10(np.abs(h) + 1e-10)
        phase_deg = np.angle(h, deg=True)
        
        # Bode图
        ax1.semilogx(w_sys, mag_db, color=color, linewidth=2, label=name)
        ax2.semilogx(w_sys, phase_deg, color=color, linewidth=2, label=name)
        
        # Nyquist图
        real = np.real(h)
        imag = np.imag(h)
        ax3.plot(real, imag, color=color, linewidth=2, label=name)
    
    # 设置子图
    ax1.set_xlabel('Frequency (rad/s)')
    ax1.set_ylabel('Magnitude (dB)')
    ax1.set_title('Magnitude Comparison')
    ax1.grid(True, which='both', alpha=0.3)
    ax1.legend()
    
    ax2.set_xlabel('Frequency (rad/s)')
    ax2.set_ylabel('Phase (deg)')
    ax2.set_title('Phase Comparison')
    ax2.grid(True, which='both', alpha=0.3)
    ax2.legend()
    
    ax3.plot(-1, 0, 'rx', markersize=15, label='Critical Point')
    ax3.set_xlabel('Real Part')
    ax3.set_ylabel('Imaginary Part')
    ax3.set_title('Nyquist Comparison')
    ax3.grid(True, alpha=0.3)
    ax3.axis('equal')
    ax3.legend()
    
    # 稳定裕度对比
    margins_data = []
    for name, (num, den) in systems.items():
        analyzer = FrequencyAnalyzer(num, den, dt)
        margins = analyzer.stability_margins()
        margins_data.append({
            'name': name,
            'GM': margins['gain_margin_db'],
            'PM': margins['phase_margin_deg']
        })
    
    names = [m['name'] for m in margins_data]
    gms = [m['GM'] for m in margins_data]
    pms = [m['PM'] for m in margins_data]
    
    x = np.arange(len(names))
    width = 0.35
    
    ax4.bar(x - width/2, gms, width, label='Gain Margin (dB)', color='steelblue')
    ax4.bar(x + width/2, pms, width, label='Phase Margin (deg)', color='coral')
    ax4.set_xlabel('System')
    ax4.set_ylabel('Margin')
    ax4.set_title('Stability Margins Comparison')
    ax4.set_xticks(x)
    ax4.set_xticklabels(names, rotation=45)
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    ax4.axhline(6, color='g', linestyle='--', linewidth=1, alpha=0.5, label='GM target')
    ax4.axhline(45, color='r', linestyle='--', linewidth=1, alpha=0.5, label='PM target')
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
    
    return fig


if __name__ == "__main__":
    """测试频域分析器"""
    print("频域分析工具测试")
    print("=" * 60)
    
    # 创建测试系统：二阶系统
    # G(s) = ω_n^2 / (s^2 + 2*ζ*ω_n*s + ω_n^2)
    wn = 1.0  # 自然频率
    zeta = 0.3  # 阻尼比
    
    # 连续系统
    sys_cont = signal.TransferFunction([wn**2], [1, 2*zeta*wn, wn**2])
    
    # 离散化
    dt = 0.1
    sys_disc = signal.cont2discrete((sys_cont.num, sys_cont.den), dt)
    
    # 分析
    analyzer = FrequencyAnalyzer(sys_disc[0][0], sys_disc[1], dt)
    
    print("\n1. Bode图分析...")
    w, mag, phase = analyzer.bode(plot=False)
    print(f"  频率范围: [{w[0]:.4f}, {w[-1]:.4f}] rad/s")
    print(f"  幅值范围: [{mag.min():.2f}, {mag.max():.2f}] dB")
    
    print("\n2. 稳定裕度...")
    margins = analyzer.stability_margins()
    print(f"  增益裕度: {margins['gain_margin_db']:.2f} dB")
    print(f"  相位裕度: {margins['phase_margin_deg']:.2f} °")
    
    print("\n3. 性能指标...")
    print(f"  带宽: {margins['bandwidth']:.4f} rad/s")
    print(f"  谐振峰: {margins['peak_magnitude_db']:.2f} dB")
    
    # 完整报告
    analyzer.print_report()
    
    print("\n✓ 测试完成")
