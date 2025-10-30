"""
物理常数和默认参数集中管理

消除代码中的硬编码，提供统一的参数配置中心。

作者: HydroClaude Team
日期: 2025-10-22
"""


class PhysicsConstants:
    """
    物理常数

    集中管理所有物理常数，确保整个项目使用一致的值
    """
    # 基本物理常数
    GRAVITY = 9.81                    # 重力加速度 (m/s²)
    WATER_DENSITY = 1000.0            # 水的密度 (kg/m³)
    KINEMATIC_VISCOSITY = 1.0e-6      # 运动粘度 (m²/s)
    ATMOSPHERIC_PRESSURE = 101325.0   # 标准大气压 (Pa)

    # 单位转换
    KW_TO_MW = 0.001                  # kW 转 MW
    M3_TO_L = 1000.0                  # m³ 转 L
    HOUR_TO_SECOND = 3600.0           # 小时转秒
    DAY_TO_SECOND = 86400.0           # 天转秒


class CanalDefaults:
    """
    明渠(Canal)组件的默认参数

    这些值适用于一般的明渠系统，可以根据具体工程调整
    """
    # 水力参数
    MANNING_N = 0.025                 # 曼宁粗糙系数 (混凝土衬砌渠道)
    WIDTH = 10.0                      # 默认渠道宽度 (m)
    SLOPE = 0.0001                    # 默认渠底坡度 (无量纲)

    # 初始状态
    INITIAL_DEPTH = 5.0               # 初始水深 (m)
    INITIAL_FLOW = 5.0                # 初始流量 (m³/s)

    # 约束范围
    H_MIN = 0.1                       # 最小水深 (m) - 避免数值奇异
    H_MAX = 20.0                      # 最大水深 (m)
    Q_MIN = 0.0                       # 最小流量 (m³/s)
    Q_MAX = 100.0                     # 最大流量 (m³/s)

    # 数值求解参数
    DEFAULT_SECTIONS = 11             # 默认空间离散节点数
    DEFAULT_METHOD = 'preissmann'     # 默认求解方法 (使用修复后的preissmann)

    # 曼宁系数参考值
    MANNING_N_RANGES = {
        'concrete': (0.012, 0.018),   # 混凝土
        'earth': (0.020, 0.030),      # 土渠
        'gravel': (0.025, 0.035),     # 砾石
        'vegetated': (0.030, 0.050),  # 有植被
    }


class ReservoirDefaults:
    """
    水库(Reservoir)组件的默认参数
    """
    # 溢洪道参数
    SPILLWAY_COEFFICIENT = 2.0        # 溢洪道流量系数 (无量纲)
    SPILLWAY_LENGTH = 50.0            # 溢洪道长度 (m)

    # 水轮机参数
    TURBINE_EFFICIENCY = 0.85         # 水轮机综合效率 (0-1)
    TURBINE_MIN_FLOW_RATIO = 0.3      # 最小流量比例 (相对额定流量)
    TURBINE_MAX_FLOW_RATIO = 1.2      # 最大流量比例 (相对额定流量)

    # 生态流量
    ECOLOGICAL_FLOW_RATIO = 0.1       # 生态流量占平均流量的比例

    # 库容曲线默认参数 (如果没有提供曲线数据)
    STORAGE_CURVE_TYPE = 'linear'     # 默认库容曲线类型 (linear/power/polynomial)


class PumpDefaults:
    """
    水泵(Pump)组件的默认参数
    """
    RATED_SPEED = 1500.0              # 额定转速 (rpm)
    SHUTOFF_HEAD_RATIO = 1.2          # 关闭扬程比例
    MAX_EFFICIENCY = 0.85             # 最大效率
    EFFICIENCY_CURVE_EXPONENT = 2.0   # 效率曲线指数


class ValveDefaults:
    """
    阀门(Valve)组件的默认参数
    """
    DEFAULT_CV = 100.0                # 默认流量系数 Cv
    OPENING_RATE_LIMIT = 0.1          # 开度变化率限制 (每秒)


class TurbineDefaults:
    """
    水轮机(Turbine)组件的默认参数
    """
    # Francis水轮机
    FRANCIS_EFFICIENCY = 0.93         # 峰值效率
    FRANCIS_NS_RANGE = (60, 400)      # 比转速范围
    FRANCIS_HEAD_RANGE = (40, 300)    # 适用水头范围 (m)

    # Kaplan水轮机
    KAPLAN_EFFICIENCY = 0.94          # 峰值效率
    KAPLAN_NS_RANGE = (300, 1000)     # 比转速范围
    KAPLAN_HEAD_RANGE = (10, 70)      # 适用水头范围 (m)

    # Pelton水轮机
    PELTON_EFFICIENCY = 0.90          # 峰值效率
    PELTON_NS_RANGE = (10, 70)        # 比转速范围
    PELTON_HEAD_RANGE = (300, 1500)   # 适用水头范围 (m)


class NumericalDefaults:
    """
    数值求解器的默认参数
    """
    # 时间积分
    DEFAULT_DT = 1.0                  # 默认时间步长 (s)
    MAX_DT = 3600.0                   # 最大时间步长 (s)
    MIN_DT = 0.001                    # 最小时间步长 (s)

    # 迭代求解
    MAX_ITERATIONS = 100              # 最大迭代次数
    CONVERGENCE_TOL = 1e-6            # 收敛容差
    RELAXATION_FACTOR = 0.8           # 松弛因子

    # Preissmann格式
    PREISSMANN_THETA = 0.6            # Preissmann权重系数 (0.5-1.0)

    # FVM格式
    FVM_FLUX_SCHEME = 'hll'           # 通量格式 (hll/roe/lax_friedrichs)
    FVM_LIMITER = 'minmod'            # 限制器 (minmod/superbee/van_leer)

    # MOC格式
    MOC_CFL = 0.9                     # Courant数


class ControlDefaults:
    """
    控制系统的默认参数
    """
    # PID控制器
    PID_KP = 1.0                      # 比例增益
    PID_KI = 0.1                      # 积分增益
    PID_KD = 0.01                     # 微分增益
    PID_OUTPUT_LIMIT = (-1.0, 1.0)    # 输出限制

    # MPC控制器
    MPC_PREDICTION_HORIZON = 10       # 预测时域
    MPC_CONTROL_HORIZON = 3           # 控制时域
    MPC_WEIGHT_OUTPUT = 1.0           # 输出权重
    MPC_WEIGHT_INPUT = 0.01           # 输入权重
    MPC_WEIGHT_DELTA_INPUT = 0.001    # 输入变化率权重


class OptimizationDefaults:
    """
    优化调度的默认参数
    """
    # 通用优化参数
    OPTIMIZATION_TOLERANCE = 1e-4     # 优化容差
    MAX_OPTIMIZATION_TIME = 300.0     # 最大优化时间 (s)

    # 遗传算法
    GA_POPULATION_SIZE = 100          # 种群大小
    GA_MAX_GENERATIONS = 200          # 最大代数
    GA_CROSSOVER_RATE = 0.8           # 交叉率
    GA_MUTATION_RATE = 0.1            # 变异率


def get_constant(category: str, key: str, default=None):
    """
    获取常数值的便捷函数

    Args:
        category: 常数类别 ('physics', 'canal', 'reservoir'等)
        key: 常数键名
        default: 默认值，如果找不到则返回

    Returns:
        常数值

    Examples:
        >>> get_constant('physics', 'GRAVITY')
        9.81
        >>> get_constant('canal', 'MANNING_N')
        0.025
    """
    category_map = {
        'physics': PhysicsConstants,
        'canal': CanalDefaults,
        'reservoir': ReservoirDefaults,
        'pump': PumpDefaults,
        'valve': ValveDefaults,
        'turbine': TurbineDefaults,
        'numerical': NumericalDefaults,
        'control': ControlDefaults,
        'optimization': OptimizationDefaults,
    }

    cls = category_map.get(category.lower())
    if cls is None:
        return default

    return getattr(cls, key.upper(), default)


def list_constants(category: str = None):
    """
    列出所有可用的常数

    Args:
        category: 如果指定，只列出该类别的常数

    Returns:
        常数字典
    """
    categories = {
        'physics': PhysicsConstants,
        'canal': CanalDefaults,
        'reservoir': ReservoirDefaults,
        'pump': PumpDefaults,
        'valve': ValveDefaults,
        'turbine': TurbineDefaults,
        'numerical': NumericalDefaults,
        'control': ControlDefaults,
        'optimization': OptimizationDefaults,
    }

    if category:
        cls = categories.get(category.lower())
        if cls:
            return {k: v for k, v in cls.__dict__.items()
                   if not k.startswith('_')}
        return {}

    result = {}
    for cat, cls in categories.items():
        result[cat] = {k: v for k, v in cls.__dict__.items()
                      if not k.startswith('_')}
    return result


if __name__ == '__main__':
    """测试和演示"""
    print("=" * 80)
    print("HydroClaude 物理常数和默认参数")
    print("=" * 80)
    print()

    print("【物理常数】")
    print(f"  重力加速度: {PhysicsConstants.GRAVITY} m/s²")
    print(f"  水密度: {PhysicsConstants.WATER_DENSITY} kg/m³")
    print()

    print("【明渠默认参数】")
    print(f"  曼宁系数: {CanalDefaults.MANNING_N}")
    print(f"  默认宽度: {CanalDefaults.WIDTH} m")
    print(f"  水深范围: [{CanalDefaults.H_MIN}, {CanalDefaults.H_MAX}] m")
    print()

    print("【水库默认参数】")
    print(f"  溢洪道流量系数: {ReservoirDefaults.SPILLWAY_COEFFICIENT}")
    print(f"  溢洪道长度: {ReservoirDefaults.SPILLWAY_LENGTH} m")
    print(f"  水轮机效率: {ReservoirDefaults.TURBINE_EFFICIENCY}")
    print()

    print("【使用 get_constant 函数】")
    print(f"  get_constant('physics', 'GRAVITY') = {get_constant('physics', 'GRAVITY')}")
    print(f"  get_constant('canal', 'MANNING_N') = {get_constant('canal', 'MANNING_N')}")
    print()
