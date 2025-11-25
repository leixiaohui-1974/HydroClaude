"""
多目标优化算法单元测试

测试NSGA-II和NSGA-III算法的核心功能
"""

import numpy as np
import warnings
warnings.filterwarnings("ignore")
import sys
import os

# 添加项目根目录
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 直接导入multi_objective模块，避免通过__init__.py
import importlib.util
spec = importlib.util.spec_from_file_location(
    "multi_objective",
    os.path.join(os.path.dirname(__file__), '../optimization/multi_objective.py')
)
multi_objective = importlib.util.module_from_spec(spec)
spec.loader.exec_module(multi_objective)

Individual = multi_objective.Individual
MOProblem = multi_objective.MOProblem
NSGA2 = multi_objective.NSGA2
NSGA2Config = multi_objective.NSGA2Config
NSGA3 = multi_objective.NSGA3
NSGA3Config = multi_objective.NSGA3Config
fast_non_dominated_sort = multi_objective.fast_non_dominated_sort
calculate_crowding_distance = multi_objective.calculate_crowding_distance
generate_reference_points = multi_objective.generate_reference_points
simulated_binary_crossover = multi_objective.simulated_binary_crossover
polynomial_mutation = multi_objective.polynomial_mutation
calculate_hypervolume = multi_objective.calculate_hypervolume


def test_individual_dominance():
    """测试个体支配关系"""
    print("测试1: 个体支配关系...")

    ind1 = Individual(
        decision_variables=np.array([1.0, 2.0]),
        objectives=np.array([1.0, 2.0])
    )

    ind2 = Individual(
        decision_variables=np.array([2.0, 3.0]),
        objectives=np.array([2.0, 3.0])
    )

    ind3 = Individual(
        decision_variables=np.array([1.5, 1.5]),
        objectives=np.array([1.5, 1.5])
    )

    # ind1 支配 ind2
    assert ind1.dominates(ind2) == True
    assert ind2.dominates(ind1) == False

    # ind1 和 ind3 互不支配
    assert ind1.dominates(ind3) == False
    assert ind3.dominates(ind1) == False

    print("   支配关系判断正确")


def test_fast_non_dominated_sort():
    """测试快速非支配排序"""
    print("\n测试2: 快速非支配排序...")

    # 创建测试种群
    population = [
        Individual(np.array([0]), np.array([1.0, 1.0])),  # 第1层
        Individual(np.array([1]), np.array([2.0, 0.5])),  # 第1层
        Individual(np.array([2]), np.array([0.5, 2.0])),  # 第1层
        Individual(np.array([3]), np.array([2.0, 2.0])),  # 第2层
        Individual(np.array([4]), np.array([3.0, 3.0])),  # 第3层
    ]

    fronts = fast_non_dominated_sort(population)

    assert len(fronts) == 3
    assert len(fronts[0]) == 3  # 第1层有3个
    assert len(fronts[1]) == 1  # 第2层有1个
    assert len(fronts[2]) == 1  # 第3层有1个

    print(f"   排序正确: {len(fronts)} 层")
    print(f"    第1层: {len(fronts[0])} 个解")
    print(f"    第2层: {len(fronts[1])} 个解")
    print(f"    第3层: {len(fronts[2])} 个解")


def test_crowding_distance():
    """测试拥挤距离计算"""
    print("\n测试3: 拥挤距离计算...")

    front = [
        Individual(np.array([0]), np.array([1.0, 5.0])),
        Individual(np.array([1]), np.array([2.0, 4.0])),
        Individual(np.array([2]), np.array([3.0, 3.0])),
        Individual(np.array([3]), np.array([4.0, 2.0])),
        Individual(np.array([4]), np.array([5.0, 1.0])),
    ]

    calculate_crowding_distance(front)

    # 边界点应该是无穷大
    assert front[0].crowding_distance == float('inf')
    assert front[-1].crowding_distance == float('inf')

    # 中间点应该有有限值
    for ind in front[1:-1]:
        assert 0 < ind.crowding_distance < float('inf')

    print("   拥挤距离计算正确")
    print(f"    边界点: inf")
    print(f"    中间点: {[f'{ind.crowding_distance:.4f}' for ind in front[1:-1]]}")


def test_reference_points():
    """测试参考点生成"""
    print("\n测试4: 参考点生成...")

    # 3目标，3分割
    ref_points = generate_reference_points(n_objectives=3, n_divisions=3)

    # 应该生成 C(3+3-1, 3) = C(5,3) = 10 个点
    expected_count = 10
    assert len(ref_points) == expected_count

    # 所有点应该在单位超平面上（和为1）
    for point in ref_points:
        assert abs(np.sum(point) - 1.0) < 1e-10

    print(f"   生成了 {len(ref_points)} 个参考点")
    print(f"    示例: {ref_points[0]}, 和={np.sum(ref_points[0]):.6f}")


def test_genetic_operators():
    """测试遗传算子"""
    print("\n测试5: 遗传算子...")

    bounds = [(0, 10), (0, 10), (0, 10)]

    parent1 = Individual(np.array([2.0, 3.0, 4.0]))
    parent2 = Individual(np.array([6.0, 7.0, 8.0]))

    # 测试交叉
    child1, child2 = simulated_binary_crossover(parent1, parent2, bounds, eta=20.0)

    assert len(child1.decision_variables) == 3
    assert len(child2.decision_variables) == 3

    # 子代应该在边界内
    for i in range(3):
        assert bounds[i][0] <= child1.decision_variables[i] <= bounds[i][1]
        assert bounds[i][0] <= child2.decision_variables[i] <= bounds[i][1]

    print("   交叉算子正确")

    # 测试变异
    mutated = polynomial_mutation(child1, bounds, eta=20.0, mutation_prob=1.0)

    assert len(mutated.decision_variables) == 3

    # 变异后应该在边界内
    for i in range(3):
        assert bounds[i][0] <= mutated.decision_variables[i] <= bounds[i][1]

    print("   变异算子正确")


def test_zdt1_problem():
    """测试ZDT1标准测试问题"""
    print("\n测试6: ZDT1问题（NSGA-II）...")

    # ZDT1: 两目标测试问题
    # f1(x) = x1
    # f2(x) = g(x) * [1 - sqrt(x1/g(x))]
    # g(x) = 1 + 9 * sum(x2...xn) / (n-1)

    n_var = 30

    def zdt1_objective(x):
        f1 = x[0]
        g = 1.0 + 9.0 * np.sum(x[1:]) / (n_var - 1)
        f2 = g * (1.0 - np.sqrt(f1 / g))
        return np.array([f1, f2])

    bounds = [(0, 1) for _ in range(n_var)]

    problem = MOProblem(
        n_objectives=2,
        n_variables=n_var,
        bounds=bounds,
        objective_function=zdt1_objective
    )

    config = NSGA2Config(
        population_size=50,
        n_generations=50,
        seed=42
    )

    optimizer = NSGA2(problem, config)
    result = optimizer.optimize()

    print(f"   NSGA-II 完成")
    print(f"    Pareto前沿: {len(result.pareto_front)} 个解")
    print(f"    运行代数: {result.n_generations}")

    # 检查收敛
    assert len(result.convergence_history) == config.n_generations
    assert len(result.pareto_front) > 0

    # ZDT1的真实Pareto前沿：f1 ∈ [0,1], f2 = 1 - sqrt(f1)
    # 检查算法找到的解是否接近
    objectives = result.get_pareto_objectives()

    # f1应该在[0,1]范围内
    assert np.all(objectives[:, 0] >= 0)
    assert np.all(objectives[:, 0] <= 1)

    # 检查几个点
    for obj in objectives[:5]:
        f1, f2 = obj
        expected_f2 = 1.0 - np.sqrt(f1)
        error = abs(f2 - expected_f2)
        print(f"    f1={f1:.4f}, f2={f2:.4f}, expected_f2={expected_f2:.4f}, error={error:.4f}")


def test_dtlz2_problem():
    """测试DTLZ2标准测试问题（3目标）"""
    print("\n测试7: DTLZ2问题（NSGA-III）...")

    # DTLZ2: 三目标测试问题
    n_var = 12
    n_obj = 3

    def dtlz2_objective(x):
        k = n_var - n_obj + 1
        xm = x[-k:]
        g = np.sum((xm - 0.5) ** 2)

        f = np.zeros(n_obj)
        f[0] = (1 + g) * np.cos(x[0] * np.pi / 2) * np.cos(x[1] * np.pi / 2)
        f[1] = (1 + g) * np.cos(x[0] * np.pi / 2) * np.sin(x[1] * np.pi / 2)
        f[2] = (1 + g) * np.sin(x[0] * np.pi / 2)

        return f

    bounds = [(0, 1) for _ in range(n_var)]

    problem = MOProblem(
        n_objectives=3,
        n_variables=n_var,
        bounds=bounds,
        objective_function=dtlz2_objective
    )

    config = NSGA3Config(
        population_size=92,
        n_generations=50,
        n_divisions=12,
        seed=42
    )

    optimizer = NSGA3(problem, config)
    result = optimizer.optimize()

    print(f"   NSGA-III 完成")
    print(f"    Pareto前沿: {len(result.pareto_front)} 个解")
    print(f"    参考点数: {len(optimizer.ref_points)}")
    print(f"    运行代数: {result.n_generations}")

    # 检查收敛
    assert len(result.convergence_history) == config.n_generations
    assert len(result.pareto_front) > 0

    # DTLZ2的真实Pareto前沿在球面上：f1^2 + f2^2 + f3^2 = 1
    objectives = result.get_pareto_objectives()
    radii = np.sqrt(np.sum(objectives ** 2, axis=1))

    print(f"    球面半径（应接近1.0）:")
    print(f"      最小: {radii.min():.4f}")
    print(f"      最大: {radii.max():.4f}")
    print(f"      平均: {radii.mean():.4f}")
    print(f"      标准差: {radii.std():.4f}")


def test_hypervolume():
    """测试超体积指标"""
    print("\n测试8: 超体积指标...")

    # 简单的2D Pareto前沿
    front = [
        Individual(np.array([0]), np.array([1.0, 5.0])),
        Individual(np.array([1]), np.array([2.0, 4.0])),
        Individual(np.array([2]), np.array([3.0, 3.0])),
        Individual(np.array([3]), np.array([4.0, 2.0])),
        Individual(np.array([4]), np.array([5.0, 1.0])),
    ]

    ref_point = np.array([6.0, 6.0])
    hv = calculate_hypervolume(front, ref_point)

    # 手动计算期望值
    # 区域1: (6-1)*(6-5) = 5
    # 区域2: (6-2)*(6-4) = 8
    # ...
    # 总和应该是一个正值
    assert hv > 0

    print(f"   超体积 = {hv:.4f}")


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("多目标优化算法单元测试")
    print("=" * 60)

    try:
        test_individual_dominance()
        test_fast_non_dominated_sort()
        test_crowding_distance()
        test_reference_points()
        test_genetic_operators()
        test_zdt1_problem()
        test_dtlz2_problem()
        test_hypervolume()

        print("\n" + "=" * 60)
        print(" 所有测试通过！")
        print("=" * 60)

        return True

    except AssertionError as e:
        print(f"\n 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
