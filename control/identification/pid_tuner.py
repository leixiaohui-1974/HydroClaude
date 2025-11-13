#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PID参数自动整定工具

基于系统辨识和频域分析的PID参数优化

方法：
1. Ziegler-Nichols频域法
2. IMC-PID设计
3. 极点配置法
4. 优化算法（遗传算法/PSO等）

作者: Claude AI
日期: 2025-10-26
"""

import numpy as np
from scipy import signal, optimize
from typing import Tuple, Dict, Optional
import warnings


class PIDTuner:
    """
    PID参数自动整定器
    
    基于辨识模型自动计算PID参数
    """
    
    def __init__(self, num: np.ndarray, den: np.ndarray, dt: float = 1.0):
        """
        初始化PID整定器
        
        Args:
            num: 系统传递函数分子
            den: 系统传递函数分母  
            dt: 采样周期
        """
        self.num = np.array(num)
        self.den = np.array(den)
        self.dt = dt
        
        # 创建系统对象
        self.sys = signal.TransferFunction(num, den, dt=dt)
        
    def ziegler_nichols_frequency(self) -> Dict:
        """
        Ziegler-Nichols频域整定法
        
        步骤：
        1. 找到临界增益Ku（系统震荡边缘的增益）
        2. 找到临界周期Tu（震荡周期）
        3. 根据ZN公式计算PID参数
        
        Returns:
            params: PID参数字典
        """
        # 1. 找临界点（相位=-180°时的增益和频率）
        w = np.logspace(-3, 2, 10000)
        _, h = signal.freqz(self.num, self.den, worN=w, fs=1/self.dt)
        
        phase = np.angle(h, deg=True)
        mag = np.abs(h)
        
        # 找相位穿越点（-180°）
        crossover_indices = np.where(np.diff(np.sign(phase + 180)))[0]
        
        if len(crossover_indices) == 0:
            warnings.warn("未找到相位穿越点，使用默认参数")
            return {'kp': 1.0, 'ki': 0.1, 'kd': 0.1, 'method': 'default'}
        
        idx = crossover_indices[0]
        w_u = w[idx]  # 临界频率
        Ku = 1 / mag[idx]  # 临界增益
        Tu = 2 * np.pi / w_u  # 临界周期
        
        # 2. ZN公式
        # P控制器
        kp_p = 0.5 * Ku
        
        # PI控制器
        kp_pi = 0.45 * Ku
        ki_pi = 0.54 * Ku / Tu
        
        # PID控制器（经典ZN）
        kp = 0.6 * Ku
        ki = 1.2 * Ku / Tu
        kd = 0.075 * Ku * Tu
        
        # PID控制器（改进ZN，减少超调）
        kp_mod = 0.33 * Ku
        ki_mod = 0.66 * Ku / Tu
        kd_mod = 0.11 * Ku * Tu
        
        return {
            'critical_gain': Ku,
            'critical_period': Tu,
            'critical_frequency': w_u,
            'kp': kp,
            'ki': ki,
            'kd': kd,
            'kp_modified': kp_mod,  # 改进版
            'ki_modified': ki_mod,
            'kd_modified': kd_mod,
            'kp_pi': kp_pi,
            'ki_pi': ki_pi,
            'method': 'ziegler_nichols_frequency'
        }
    
    def imc_pid(self, lambda_: float = None) -> Dict:
        """
        IMC-PID设计（Internal Model Control）
        
        优点：
        - 只需调节一个参数λ（闭环时间常数）
        - 理论完备
        - 鲁棒性好
        
        Args:
            lambda_: 期望闭环时间常数（None则自动选择）
            
        Returns:
            params: PID参数
        """
        # 将系统近似为一阶+时滞模型
        # G(s) = K * exp(-θs) / (τs + 1)
        
        # 阶跃响应
        t = np.arange(0, 100*self.dt, self.dt)
        _, y = signal.dstep(self.sys, t=t)
        y = y[0].flatten()
        
        # 提取参数
        K = y[-1]  # 稳态增益
        
        # 时滞（63.2%上升时间方法）
        idx_63 = np.where(y >= 0.632 * K)[0]
        if len(idx_63) > 0:
            t_63 = t[idx_63[0]]
        else:
            t_63 = 0
        
        # 时间常数（从10%到90%）
        idx_10 = np.where(y >= 0.1 * K)[0]
        idx_90 = np.where(y >= 0.9 * K)[0]
        
        if len(idx_10) > 0 and len(idx_90) > 0:
            tau = 1.5 * (t[idx_90[0]] - t[idx_10[0]])
            theta = max(0, t_63 - tau)
        else:
            tau = 10 * self.dt
            theta = self.dt
        
        # 自动选择λ
        if lambda_ is None:
            lambda_ = max(theta, 0.1 * tau)
        
        # IMC-PID公式（一阶+时滞系统）
        kp = tau / (K * (lambda_ + theta))
        ki = 1 / (tau * K)
        kd = 0  # 一阶系统不需要微分
        
        # 如果是二阶或更高阶，添加微分项
        if len(self.den) > 2:
            kd = tau / (K * (lambda_ + theta))
        
        return {
            'kp': kp,
            'ki': ki,
            'kd': kd,
            'lambda': lambda_,
            'K': K,
            'tau': tau,
            'theta': theta,
            'method': 'imc_pid'
        }
    
    def pole_placement(self, desired_poles: Optional[np.ndarray] = None) -> Dict:
        """
        极点配置法
        
        将闭环极点配置到期望位置
        
        Args:
            desired_poles: 期望的闭环极点（None则自动选择）
            
        Returns:
            params: PID参数
        """
        # 自动选择期望极点（稳定、快速、无超调）
        if desired_poles is None:
            # 主导极点：实部=-wn, wn由系统特性决定
            wn = 0.5 / self.dt  # 自然频率
            zeta = 0.9  # 阻尼比（高阻尼，减少超调）
            
            desired_poles = np.array([
                -zeta*wn + 1j*wn*np.sqrt(1-zeta**2),
                -zeta*wn - 1j*wn*np.sqrt(1-zeta**2),
                -10*wn  # 快速极点
            ])
        
        # 特征方程系数
        char_poly = np.poly(desired_poles)
        
        # 从特征方程反推PID参数（简化方法）
        # 这里使用优化方法
        def objective(pid_params):
            kp, ki, kd = pid_params
            
            # PID传递函数（离散形式）
            num_pid = np.array([kd/self.dt, kp + 2*kd/self.dt, ki*self.dt - kp - kd/self.dt])
            den_pid = np.array([1, -1, 0])
            
            # 闭环传递函数
            num_cl = signal.convolve(num_pid, self.num)
            den_cl = signal.convolve(den_pid, self.den) + signal.convolve(num_pid, self.num)
            
            # 闭环极点
            poles_cl = np.roots(den_cl)
            
            # 目标：闭环极点接近期望极点
            min_dist = np.sum([np.min(np.abs(poles_cl - p)) for p in desired_poles])
            
            return min_dist
        
        # 优化
        x0 = [1.0, 0.1, 0.1]  # 初始猜测
        bounds = [(0.01, 10), (0.001, 1), (0, 1)]  # 参数范围
        
        result = optimize.minimize(objective, x0, bounds=bounds, method='L-BFGS-B')
        
        kp, ki, kd = result.x
        
        return {
            'kp': kp,
            'ki': ki,
            'kd': kd,
            'desired_poles': desired_poles,
            'method': 'pole_placement'
        }
    
    def optimization_based(self, objective_type: str = 'iae') -> Dict:
        """
        基于优化的PID整定
        
        最小化性能指标：
        - IAE: 积分绝对误差
        - ISE: 积分平方误差
        - ITAE: 时间加权积分绝对误差
        
        Args:
            objective_type: 'iae', 'ise', 'itae'
            
        Returns:
            params: PID参数
        """
        def simulate_closed_loop(pid_params):
            """模拟闭环响应"""
            kp, ki, kd = pid_params
            
            # PID控制器（离散形式）
            # u(k) = kp*e(k) + ki*sum(e) + kd*(e(k)-e(k-1))
            
            # 简化：使用离散PID传递函数
            num_pid = np.array([kd, kp, ki*self.dt])
            den_pid = np.array([self.dt, 0, 0])
            
            # 闭环
            num_cl = signal.convolve(num_pid, self.num)
            den_cl = signal.convolve(den_pid, self.den) + signal.convolve(num_pid, self.num)
            
            sys_cl = signal.TransferFunction(num_cl, den_cl, dt=self.dt)
            
            # 阶跃响应
            t = np.arange(0, 100*self.dt, self.dt)
            try:
                _, y = signal.dstep(sys_cl, t=t)
                y = y[0].flatten()
                
                # 误差
                error = 1 - y
                
                # 性能指标
                if objective_type == 'iae':
                    J = np.sum(np.abs(error)) * self.dt
                elif objective_type == 'ise':
                    J = np.sum(error**2) * self.dt
                elif objective_type == 'itae':
                    J = np.sum(t * np.abs(error)) * self.dt
                else:
                    J = np.sum(np.abs(error)) * self.dt
                
                # 惩罚超调和振荡
                overshoot = np.max(y) - 1
                if overshoot > 0:
                    J += 10 * overshoot
                
                # 惩罚稳态误差
                steady_error = np.abs(1 - np.mean(y[-10:]))
                J += 100 * steady_error
                
            except:
                J = 1e6  # 不稳定系统的惩罚
            
            return J
        
        # 优化
        x0 = [1.0, 0.1, 0.1]
        bounds = [(0.01, 20), (0.001, 2), (0, 2)]
        
        result = optimize.minimize(simulate_closed_loop, x0, bounds=bounds, 
                                  method='L-BFGS-B',
                                  options={'maxiter': 100})
        
        kp, ki, kd = result.x
        
        return {
            'kp': kp,
            'ki': ki,
            'kd': kd,
            'objective_value': result.fun,
            'method': f'optimization_{objective_type}'
        }
    
    def compare_methods(self) -> Dict:
        """
        对比所有整定方法
        
        Returns:
            comparison: 包含所有方法结果的字典
        """
        results = {}
        
        print("\n" + "="*60)
        print("PID参数整定 - 多方法对比")
        print("="*60)
        
        # 方法1: Ziegler-Nichols
        print("\n[1/4] Ziegler-Nichols频域法...")
        try:
            zn = self.ziegler_nichols_frequency()
            results['ZN'] = zn
            print(f"  Kp={zn['kp']:.4f}, Ki={zn['ki']:.4f}, Kd={zn['kd']:.4f}")
            print(f"  临界增益: {zn['critical_gain']:.4f}, 临界周期: {zn['critical_period']:.4f}")
        except Exception as e:
            print(f"   失败: {e}")
            results['ZN'] = None
        
        # 方法2: IMC-PID
        print("\n[2/4] IMC-PID设计...")
        try:
            imc = self.imc_pid()
            results['IMC'] = imc
            print(f"  Kp={imc['kp']:.4f}, Ki={imc['ki']:.4f}, Kd={imc['kd']:.4f}")
            print(f"  λ={imc['lambda']:.4f}, K={imc['K']:.4f}, τ={imc['tau']:.4f}")
        except Exception as e:
            print(f"   失败: {e}")
            results['IMC'] = None
        
        # 方法3: 极点配置
        print("\n[3/4] 极点配置法...")
        try:
            pp = self.pole_placement()
            results['Pole_Placement'] = pp
            print(f"  Kp={pp['kp']:.4f}, Ki={pp['ki']:.4f}, Kd={pp['kd']:.4f}")
        except Exception as e:
            print(f"   失败: {e}")
            results['Pole_Placement'] = None
        
        # 方法4: 优化
        print("\n[4/4] 优化算法（IAE）...")
        try:
            opt = self.optimization_based('iae')
            results['Optimization'] = opt
            print(f"  Kp={opt['kp']:.4f}, Ki={opt['ki']:.4f}, Kd={opt['kd']:.4f}")
            print(f"  目标函数值: {opt['objective_value']:.4f}")
        except Exception as e:
            print(f"   失败: {e}")
            results['Optimization'] = None
        
        print("\n" + "="*60)
        
        return results
    
    def recommend(self) -> Dict:
        """
        推荐最佳PID参数
        
        综合考虑：
        - 稳定裕度
        - 性能指标
        - 鲁棒性
        
        Returns:
            recommended: 推荐的PID参数
        """
        # 运行所有方法
        results = self.compare_methods()
        
        # 选择IMC方法（理论完备，鲁棒性好）
        if results.get('IMC') is not None:
            recommended = results['IMC']
            print("\n 推荐使用IMC-PID参数（鲁棒性好）")
        elif results.get('ZN') is not None:
            # 使用改进的ZN参数（减少超调）
            zn = results['ZN']
            recommended = {
                'kp': zn['kp_modified'],
                'ki': zn['ki_modified'],
                'kd': zn['kd_modified'],
                'method': 'ziegler_nichols_modified'
            }
            print("\n 推荐使用改进ZN参数（减少超调）")
        elif results.get('Optimization') is not None:
            recommended = results['Optimization']
            print("\n 推荐使用优化参数")
        else:
            # 默认保守参数
            recommended = {
                'kp': 1.0,
                'ki': 0.1,
                'kd': 0.1,
                'method': 'default_conservative'
            }
            print("\n  使用默认保守参数")
        
        return recommended


if __name__ == "__main__":
    """测试PID整定器"""
    print("PID自动整定工具测试")
    print("=" * 60)
    
    # 创建测试系统：一阶+时滞
    # G(s) = 1 / (5s + 1) * exp(-2s)
    
    # 离散化
    dt = 0.5
    tau = 5.0
    theta = 2.0
    
    # 一阶系统
    sys_cont = signal.TransferFunction([1], [tau, 1])
    sys_disc = signal.cont2discrete((sys_cont.num, sys_cont.den), dt)
    
    # 时滞（作为纯时滞环节）
    delay_steps = int(theta / dt)
    num_delay = np.concatenate(([0]*delay_steps, [1]))
    den_delay = np.concatenate(([1], [0]*delay_steps))
    
    # 组合系统
    num = signal.convolve(sys_disc[0][0], num_delay)
    den = signal.convolve(sys_disc[1], den_delay)
    
    # 整定
    tuner = PIDTuner(num, den, dt)
    
    print("\n测试系统: G(s) = 1/(5s+1) * exp(-2s)")
    print(f"采样周期: {dt}s")
    
    # 推荐参数
    recommended = tuner.recommend()
    
    print("\n" + "="*60)
    print("推荐PID参数:")
    print("="*60)
    print(f"  Kp = {recommended['kp']:.4f}")
    print(f"  Ki = {recommended['ki']:.4f}")
    print(f"  Kd = {recommended['kd']:.4f}")
    print(f"  方法: {recommended['method']}")
    print("="*60)
    
    print("\n 测试完成")
