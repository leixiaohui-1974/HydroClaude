"""
多目标优化算法模块

本模块实现了先进的多目标进化算法，用于水资源系统优化中的多目标决策问题。

主要算法：
- NSGA-II: 经典的多目标遗传算法（2-3个目标）
- NSGA-III: 基于参考点的多目标算法（3+个目标）

应用场景：
- 水库多目标调度（防洪 vs 发电 vs 生态）
- 供水系统优化（成本 vs 可靠性 vs 水质）
- 灌溉优化（用水量 vs 作物产量 vs 公平性）

作者：HydroClaude Team
日期：2025-10-24
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Callable, Optional, Dict, Any
from enum import Enum
import numpy as np
from abc import ABC, abstractmethod


class DominanceRelation(Enum):
    """支配关系"""
    DOMINATES = 1      # a 支配 b
    DOMINATED = 2      # a 被 b 支配
    NON_DOMINATED = 3  # 互不支配


@dataclass
class Individual:
    """个体类"""
    decision_variables: np.ndarray  # 决策变量
    objectives: Optional[np.ndarray] = None  # 目标函数值
    constraints: Optional[np.ndarray] = None  # 约束违反度
    rank: int = 0  # Pareto前沿等级
    crowding_distance: float = 0.0  # 拥挤距离
    reference_point_distance: float = 0.0  # 参考点距离（NSGA-III）

    def __post_init__(self):
        """确保决策变量是numpy数组"""
        if not isinstance(self.decision_variables, np.ndarray):
            self.decision_variables = np.array(self.decision_variables)

    def dominates(self, other: 'Individual') -> bool:
        """
        判断当前个体是否支配另一个个体

        支配定义：所有目标都不劣于对方，至少一个目标严格优于对方
        （假设所有目标都是最小化问题）
        """
        if self.objectives is None or other.objectives is None:
            return False

        # 首先检查约束违反度（可行解优于不可行解）
        self_violation = np.sum(np.maximum(0, self.constraints)) if self.constraints is not None else 0
        other_violation = np.sum(np.maximum(0, other.constraints)) if other.constraints is not None else 0

        if self_violation < other_violation:
            return True
        if self_violation > other_violation:
            return False

        # 两者都可行（或都不可行），比较目标
        at_least_one_better = False
        for i in range(len(self.objectives)):
            if self.objectives[i] > other.objectives[i]:
                return False  # 有目标更差
            if self.objectives[i] < other.objectives[i]:
                at_least_one_better = True

        return at_least_one_better

    def copy(self) -> 'Individual':
        """创建个体副本"""
        return Individual(
            decision_variables=self.decision_variables.copy(),
            objectives=self.objectives.copy() if self.objectives is not None else None,
            constraints=self.constraints.copy() if self.constraints is not None else None,
            rank=self.rank,
            crowding_distance=self.crowding_distance,
            reference_point_distance=self.reference_point_distance
        )


@dataclass
class MOProblem:
    """多目标优化问题定义"""
    n_objectives: int  # 目标数量
    n_variables: int  # 决策变量数量
    bounds: List[Tuple[float, float]]  # 变量边界 [(lower, upper), ...]
    objective_function: Callable[[np.ndarray], np.ndarray]  # 目标函数
    constraint_function: Optional[Callable[[np.ndarray], np.ndarray]] = None  # 约束函数

    def evaluate(self, individual: Individual) -> Individual:
        """评估个体"""
        individual.objectives = self.objective_function(individual.decision_variables)
        if self.constraint_function is not None:
            individual.constraints = self.constraint_function(individual.decision_variables)
        return individual


@dataclass
class MOResult:
    """多目标优化结果"""
    pareto_front: List[Individual]  # Pareto最优解集
    all_individuals: List[Individual]  # 所有个体（最后一代）
    n_generations: int  # 运行代数
    hypervolume: float = 0.0  # 超体积指标
    igd: float = 0.0  # 反向世代距离
    convergence_history: List[float] = field(default_factory=list)  # 收敛历史

    def get_pareto_objectives(self) -> np.ndarray:
        """获取Pareto前沿目标值矩阵"""
        return np.array([ind.objectives for ind in self.pareto_front])

    def get_pareto_variables(self) -> np.ndarray:
        """获取Pareto前沿决策变量矩阵"""
        return np.array([ind.decision_variables for ind in self.pareto_front])


def fast_non_dominated_sort(population: List[Individual]) -> List[List[Individual]]:
    """
    快速非支配排序算法（NSGA-II核心）

    时间复杂度：O(MN²) 其中M是目标数，N是种群大小

    返回：
        List[List[Individual]]: 各个Pareto前沿层级
    """
    n = len(population)

    # 初始化
    domination_count = [0] * n  # 被多少个个体支配
    dominated_solutions = [[] for _ in range(n)]  # 支配了哪些个体（存储索引）
    rank = [0] * n  # 每个个体的rank
    fronts = [[]]  # 存储索引

    # 计算支配关系
    for i in range(n):
        for j in range(i + 1, n):
            if population[i].dominates(population[j]):
                dominated_solutions[i].append(j)
                domination_count[j] += 1
            elif population[j].dominates(population[i]):
                dominated_solutions[j].append(i)
                domination_count[i] += 1

        # 如果没有被任何个体支配，属于第一层前沿
        if domination_count[i] == 0:
            rank[i] = 0
            fronts[0].append(i)

    # 迭代构建后续前沿
    current_front = 0
    while current_front < len(fronts) and fronts[current_front]:
        next_front = []
        for idx in fronts[current_front]:
            for dominated_idx in dominated_solutions[idx]:
                domination_count[dominated_idx] -= 1
                if domination_count[dominated_idx] == 0:
                    rank[dominated_idx] = current_front + 1
                    next_front.append(dominated_idx)
        current_front += 1
        if next_front:
            fronts.append(next_front)

    # 设置每个个体的rank并转换为Individual列表
    result_fronts = []
    for front_indices in fronts:
        front = []
        for idx in front_indices:
            population[idx].rank = rank[idx]
            front.append(population[idx])
        result_fronts.append(front)

    return result_fronts


def calculate_crowding_distance(front: List[Individual]) -> None:
    """
    计算拥挤距离（NSGA-II核心）

    拥挤距离衡量个体周围的空间密度，用于保持解的分布性
    """
    n = len(front)
    if n == 0:
        return

    n_obj = len(front[0].objectives)

    # 初始化拥挤距离
    for ind in front:
        ind.crowding_distance = 0.0

    # 对每个目标维度
    for m in range(n_obj):
        # 按目标m排序
        front.sort(key=lambda x: x.objectives[m])

        # 边界点设置为无穷大
        front[0].crowding_distance = float('inf')
        front[-1].crowding_distance = float('inf')

        # 目标范围
        obj_range = front[-1].objectives[m] - front[0].objectives[m]
        if obj_range == 0:
            continue

        # 计算中间点的拥挤距离
        for i in range(1, n - 1):
            distance = (front[i + 1].objectives[m] - front[i - 1].objectives[m]) / obj_range
            front[i].crowding_distance += distance


def crowding_distance_tournament(ind1: Individual, ind2: Individual) -> Individual:
    """
    拥挤距离锦标赛选择

    规则：
    1. rank更小的优先
    2. rank相同时，crowding_distance更大的优先
    """
    if ind1.rank < ind2.rank:
        return ind1
    elif ind1.rank > ind2.rank:
        return ind2
    else:
        # rank相同，比较拥挤距离
        if ind1.crowding_distance > ind2.crowding_distance:
            return ind1
        else:
            return ind2


def simulated_binary_crossover(parent1: Individual, parent2: Individual,
                               bounds: List[Tuple[float, float]],
                               eta: float = 20.0) -> Tuple[Individual, Individual]:
    """
    模拟二进制交叉（SBX）

    参数：
        parent1, parent2: 父代个体
        bounds: 变量边界
        eta: 分布指数（越大，子代越接近父代）
    """
    n_var = len(parent1.decision_variables)
    child1_vars = np.zeros(n_var)
    child2_vars = np.zeros(n_var)

    for i in range(n_var):
        if np.random.rand() > 0.5:
            # 交叉
            x1 = parent1.decision_variables[i]
            x2 = parent2.decision_variables[i]

            if abs(x1 - x2) > 1e-14:
                if x1 < x2:
                    y1, y2 = x1, x2
                else:
                    y1, y2 = x2, x1

                lb, ub = bounds[i]

                # 计算beta
                beta = 1.0 + 2.0 * (y1 - lb) / (y2 - y1)
                alpha = 2.0 - beta ** (-(eta + 1.0))
                rand = np.random.rand()

                if rand <= 1.0 / alpha:
                    betaq = (rand * alpha) ** (1.0 / (eta + 1.0))
                else:
                    betaq = (1.0 / (2.0 - rand * alpha)) ** (1.0 / (eta + 1.0))

                c1 = 0.5 * ((y1 + y2) - betaq * (y2 - y1))

                beta = 1.0 + 2.0 * (ub - y2) / (y2 - y1)
                alpha = 2.0 - beta ** (-(eta + 1.0))

                if rand <= 1.0 / alpha:
                    betaq = (rand * alpha) ** (1.0 / (eta + 1.0))
                else:
                    betaq = (1.0 / (2.0 - rand * alpha)) ** (1.0 / (eta + 1.0))

                c2 = 0.5 * ((y1 + y2) + betaq * (y2 - y1))

                # 确保在边界内
                c1 = np.clip(c1, lb, ub)
                c2 = np.clip(c2, lb, ub)

                if np.random.rand() > 0.5:
                    child1_vars[i] = c1
                    child2_vars[i] = c2
                else:
                    child1_vars[i] = c2
                    child2_vars[i] = c1
            else:
                child1_vars[i] = x1
                child2_vars[i] = x2
        else:
            # 不交叉
            child1_vars[i] = parent1.decision_variables[i]
            child2_vars[i] = parent2.decision_variables[i]

    child1 = Individual(decision_variables=child1_vars)
    child2 = Individual(decision_variables=child2_vars)

    return child1, child2


def polynomial_mutation(individual: Individual, bounds: List[Tuple[float, float]],
                       eta: float = 20.0, mutation_prob: float = None) -> Individual:
    """
    多项式变异

    参数：
        individual: 待变异个体
        bounds: 变量边界
        eta: 分布指数
        mutation_prob: 变异概率（默认为1/n_var）
    """
    n_var = len(individual.decision_variables)
    if mutation_prob is None:
        mutation_prob = 1.0 / n_var

    mutated_vars = individual.decision_variables.copy()

    for i in range(n_var):
        if np.random.rand() < mutation_prob:
            x = mutated_vars[i]
            lb, ub = bounds[i]

            delta1 = (x - lb) / (ub - lb)
            delta2 = (ub - x) / (ub - lb)

            rand = np.random.rand()
            mut_pow = 1.0 / (eta + 1.0)

            if rand < 0.5:
                xy = 1.0 - delta1
                val = 2.0 * rand + (1.0 - 2.0 * rand) * (xy ** (eta + 1.0))
                deltaq = val ** mut_pow - 1.0
            else:
                xy = 1.0 - delta2
                val = 2.0 * (1.0 - rand) + 2.0 * (rand - 0.5) * (xy ** (eta + 1.0))
                deltaq = 1.0 - val ** mut_pow

            x = x + deltaq * (ub - lb)
            mutated_vars[i] = np.clip(x, lb, ub)

    return Individual(decision_variables=mutated_vars)


def generate_reference_points(n_objectives: int, n_divisions: int) -> np.ndarray:
    """
    生成均匀分布的参考点（NSGA-III核心）

    使用Das and Dennis方法在单位超平面上生成均匀分布的点

    参数：
        n_objectives: 目标数量
        n_divisions: 每个目标轴的分割数

    返回：
        np.ndarray: 参考点矩阵 [n_points, n_objectives]
    """
    def generate_recursive(n_obj, n_div, current_sum=0, current_point=None):
        if current_point is None:
            current_point = []

        if n_obj == 1:
            current_point.append(n_div - current_sum)
            return [current_point]

        points = []
        for i in range(n_div - current_sum + 1):
            new_point = current_point + [i]
            points.extend(generate_recursive(n_obj - 1, n_div, current_sum + i, new_point))

        return points

    # 生成整数点
    int_points = generate_recursive(n_objectives, n_divisions)

    # 归一化到单位超平面
    ref_points = np.array(int_points, dtype=float) / n_divisions

    return ref_points


def associate_to_reference_points(population: List[Individual],
                                  ref_points: np.ndarray) -> Tuple[List[List[int]], np.ndarray]:
    """
    将个体关联到最近的参考点（NSGA-III核心）

    返回：
        associations: 每个参考点关联的个体索引列表
        distances: 每个个体到其关联参考点的距离
    """
    n_points = len(ref_points)
    n_pop = len(population)
    n_obj = len(population[0].objectives)

    # 构建目标矩阵
    objectives = np.array([ind.objectives for ind in population])

    # 归一化目标（使用理想点和最差点）
    ideal_point = np.min(objectives, axis=0)
    worst_point = np.max(objectives, axis=0)

    range_obj = worst_point - ideal_point
    range_obj[range_obj < 1e-10] = 1.0  # 避免除零

    normalized_obj = (objectives - ideal_point) / range_obj

    # 计算每个个体到每个参考点的垂直距离
    associations = [[] for _ in range(n_points)]
    distances = np.zeros(n_pop)

    for i in range(n_pop):
        min_dist = float('inf')
        min_idx = 0

        for j in range(n_points):
            # 计算垂直距离
            ref_dir = ref_points[j]
            norm = np.linalg.norm(ref_dir)
            if norm < 1e-10:
                continue
            ref_dir = ref_dir / norm

            # 投影
            projection = np.dot(normalized_obj[i], ref_dir)
            projected_point = projection * ref_dir

            # 垂直距离
            dist = np.linalg.norm(normalized_obj[i] - projected_point)

            if dist < min_dist:
                min_dist = dist
                min_idx = j

        associations[min_idx].append(i)
        distances[i] = min_dist
        population[i].reference_point_distance = min_dist

    return associations, distances


@dataclass
class NSGA2Config:
    """NSGA-II配置"""
    population_size: int = 100  # 种群大小
    n_generations: int = 100  # 最大代数
    crossover_prob: float = 0.9  # 交叉概率
    mutation_prob: float = None  # 变异概率（None表示1/n_var）
    crossover_eta: float = 20.0  # 交叉分布指数
    mutation_eta: float = 20.0  # 变异分布指数
    seed: Optional[int] = None  # 随机种子


class NSGA2:
    """
    NSGA-II算法实现

    Non-dominated Sorting Genetic Algorithm II

    特点：
    - 快速非支配排序
    - 拥挤距离保持解的分布性
    - 精英策略

    适用于2-3个目标的优化问题

    参考文献：
    Deb, K., et al. (2002). A fast and elitist multiobjective genetic algorithm: NSGA-II.
    IEEE transactions on evolutionary computation, 6(2), 182-197.
    """

    def __init__(self, problem: MOProblem, config: NSGA2Config):
        self.problem = problem
        self.config = config

        if config.seed is not None:
            np.random.seed(config.seed)

    def initialize_population(self) -> List[Individual]:
        """初始化种群"""
        population = []
        for _ in range(self.config.population_size):
            # 随机生成决策变量
            variables = np.array([
                np.random.uniform(lb, ub)
                for lb, ub in self.problem.bounds
            ])
            ind = Individual(decision_variables=variables)
            population.append(ind)

        # 评估
        for ind in population:
            self.problem.evaluate(ind)

        return population

    def evolve(self, population: List[Individual]) -> List[Individual]:
        """进化一代"""
        offspring = []

        # 生成子代
        while len(offspring) < self.config.population_size:
            # 锦标赛选择
            parent1 = crowding_distance_tournament(
                population[np.random.randint(len(population))],
                population[np.random.randint(len(population))]
            )
            parent2 = crowding_distance_tournament(
                population[np.random.randint(len(population))],
                population[np.random.randint(len(population))]
            )

            # 交叉
            if np.random.rand() < self.config.crossover_prob:
                child1, child2 = simulated_binary_crossover(
                    parent1, parent2,
                    self.problem.bounds,
                    self.config.crossover_eta
                )
            else:
                child1 = parent1.copy()
                child2 = parent2.copy()

            # 变异
            child1 = polynomial_mutation(
                child1, self.problem.bounds,
                self.config.mutation_eta,
                self.config.mutation_prob
            )
            child2 = polynomial_mutation(
                child2, self.problem.bounds,
                self.config.mutation_eta,
                self.config.mutation_prob
            )

            # 评估
            self.problem.evaluate(child1)
            self.problem.evaluate(child2)

            offspring.append(child1)
            if len(offspring) < self.config.population_size:
                offspring.append(child2)

        return offspring

    def environmental_selection(self, population: List[Individual],
                               offspring: List[Individual]) -> List[Individual]:
        """环境选择（精英策略）"""
        # 合并父代和子代
        combined = population + offspring

        # 非支配排序
        fronts = fast_non_dominated_sort(combined)

        # 选择下一代
        next_population = []
        for front in fronts:
            if len(next_population) + len(front) <= self.config.population_size:
                # 整个前沿都加入
                next_population.extend(front)
            else:
                # 需要从当前前沿中选择一部分
                calculate_crowding_distance(front)
                front.sort(key=lambda x: x.crowding_distance, reverse=True)
                needed = self.config.population_size - len(next_population)
                next_population.extend(front[:needed])
                break

        return next_population

    def optimize(self) -> MOResult:
        """执行优化"""
        # 初始化
        population = self.initialize_population()

        convergence_history = []

        # 主循环
        for gen in range(self.config.n_generations):
            # 非支配排序和拥挤距离计算
            fronts = fast_non_dominated_sort(population)
            for front in fronts:
                calculate_crowding_distance(front)

            # 记录收敛历史（第一层前沿的平均目标值）
            if fronts[0]:
                avg_objectives = np.mean([ind.objectives for ind in fronts[0]], axis=0)
                convergence_history.append(np.mean(avg_objectives))

            # 进化
            offspring = self.evolve(population)

            # 环境选择
            population = self.environmental_selection(population, offspring)

        # 最终排序
        fronts = fast_non_dominated_sort(population)
        for front in fronts:
            calculate_crowding_distance(front)

        # 构建结果
        result = MOResult(
            pareto_front=fronts[0] if fronts else [],
            all_individuals=population,
            n_generations=self.config.n_generations,
            convergence_history=convergence_history
        )

        return result


@dataclass
class NSGA3Config:
    """NSGA-III配置"""
    population_size: int = 92  # 种群大小（建议与参考点数量一致）
    n_generations: int = 100  # 最大代数
    n_divisions: int = 12  # 参考点分割数
    crossover_prob: float = 0.9  # 交叉概率
    mutation_prob: float = None  # 变异概率
    crossover_eta: float = 30.0  # 交叉分布指数
    mutation_eta: float = 20.0  # 变异分布指数
    seed: Optional[int] = None  # 随机种子


class NSGA3:
    """
    NSGA-III算法实现

    Non-dominated Sorting Genetic Algorithm III

    特点：
    - 基于参考点的选择机制
    - 适用于多目标（3+）优化问题
    - 保持解的多样性

    参考文献：
    Deb, K., & Jain, H. (2014). An evolutionary many-objective optimization algorithm
    using reference-point-based nondominated sorting approach, part I: solving problems
    with box constraints. IEEE transactions on evolutionary computation, 18(4), 577-601.
    """

    def __init__(self, problem: MOProblem, config: NSGA3Config):
        self.problem = problem
        self.config = config

        if config.seed is not None:
            np.random.seed(config.seed)

        # 生成参考点
        self.ref_points = generate_reference_points(
            problem.n_objectives,
            config.n_divisions
        )

    def initialize_population(self) -> List[Individual]:
        """初始化种群"""
        population = []
        for _ in range(self.config.population_size):
            variables = np.array([
                np.random.uniform(lb, ub)
                for lb, ub in self.problem.bounds
            ])
            ind = Individual(decision_variables=variables)
            population.append(ind)

        for ind in population:
            self.problem.evaluate(ind)

        return population

    def evolve(self, population: List[Individual]) -> List[Individual]:
        """进化一代（与NSGA-II相同）"""
        offspring = []

        while len(offspring) < self.config.population_size:
            # 二元锦标赛选择
            parent1 = self._tournament_selection(population)
            parent2 = self._tournament_selection(population)

            # 交叉
            if np.random.rand() < self.config.crossover_prob:
                child1, child2 = simulated_binary_crossover(
                    parent1, parent2,
                    self.problem.bounds,
                    self.config.crossover_eta
                )
            else:
                child1 = parent1.copy()
                child2 = parent2.copy()

            # 变异
            child1 = polynomial_mutation(
                child1, self.problem.bounds,
                self.config.mutation_eta,
                self.config.mutation_prob
            )
            child2 = polynomial_mutation(
                child2, self.problem.bounds,
                self.config.mutation_eta,
                self.config.mutation_prob
            )

            # 评估
            self.problem.evaluate(child1)
            self.problem.evaluate(child2)

            offspring.append(child1)
            if len(offspring) < self.config.population_size:
                offspring.append(child2)

        return offspring

    def _tournament_selection(self, population: List[Individual]) -> Individual:
        """锦标赛选择"""
        ind1 = population[np.random.randint(len(population))]
        ind2 = population[np.random.randint(len(population))]

        if ind1.rank < ind2.rank:
            return ind1
        elif ind1.rank > ind2.rank:
            return ind2
        else:
            # rank相同，随机选择
            return ind1 if np.random.rand() < 0.5 else ind2

    def environmental_selection(self, population: List[Individual],
                               offspring: List[Individual]) -> List[Individual]:
        """环境选择（基于参考点）"""
        # 合并父代和子代
        combined = population + offspring

        # 非支配排序
        fronts = fast_non_dominated_sort(combined)

        # 选择下一代
        next_population = []
        last_front_idx = 0

        for i, front in enumerate(fronts):
            if len(next_population) + len(front) <= self.config.population_size:
                next_population.extend(front)
                last_front_idx = i
            else:
                # 需要从当前前沿中选择一部分
                last_front_idx = i
                break

        # 如果还需要从最后一个前沿选择个体
        if len(next_population) < self.config.population_size:
            last_front = fronts[last_front_idx]
            k = self.config.population_size - len(next_population)

            # 关联到参考点（只对最后一个前沿）
            associations, distances = associate_to_reference_points(
                last_front,
                self.ref_points
            )

            # 小生境选择
            selected = self._niching_selection(
                last_front,
                associations,
                k
            )
            next_population.extend(selected)

        return next_population

    def _niching_selection(self, candidates: List[Individual],
                          associations: List[List[int]],
                          k: int) -> List[Individual]:
        """小生境选择"""
        if len(candidates) == 0 or k == 0:
            return []

        # 计算每个参考点已关联的个体数
        niche_count = [len(assoc) for assoc in associations]

        selected = []
        selected_indices = set()

        for _ in range(k):
            # 选择关联个体最少的参考点
            if not niche_count or all(c == 0 for c in niche_count):
                # 所有参考点都没有候选者了，随机选择剩余候选者
                remaining = [i for i in range(len(candidates)) if i not in selected_indices]
                if remaining:
                    idx = remaining[np.random.randint(len(remaining))]
                    selected.append(candidates[idx])
                    selected_indices.add(idx)
                break

            min_count = min(niche_count)
            min_niches = [i for i, count in enumerate(niche_count) if count == min_count]

            # 随机选择一个
            niche_idx = min_niches[np.random.randint(len(min_niches))]

            if associations[niche_idx]:
                # 选择距离最小的个体
                best_idx = min(
                    associations[niche_idx],
                    key=lambda i: candidates[i].reference_point_distance
                )
                selected.append(candidates[best_idx])
                selected_indices.add(best_idx)
                associations[niche_idx].remove(best_idx)
                niche_count[niche_idx] += 1
            else:
                # 该参考点没有关联个体，继续尝试其他参考点
                niche_count[niche_idx] = float('inf')  # 标记为不可用

        return selected

    def optimize(self) -> MOResult:
        """执行优化"""
        # 初始化
        population = self.initialize_population()

        convergence_history = []

        # 主循环
        for gen in range(self.config.n_generations):
            # 非支配排序
            fronts = fast_non_dominated_sort(population)

            # 记录收敛历史
            if fronts[0]:
                avg_objectives = np.mean([ind.objectives for ind in fronts[0]], axis=0)
                convergence_history.append(np.mean(avg_objectives))

            # 进化
            offspring = self.evolve(population)

            # 环境选择
            population = self.environmental_selection(population, offspring)

        # 最终排序
        fronts = fast_non_dominated_sort(population)

        # 构建结果
        result = MOResult(
            pareto_front=fronts[0] if fronts else [],
            all_individuals=population,
            n_generations=self.config.n_generations,
            convergence_history=convergence_history
        )

        return result


def calculate_hypervolume(pareto_front: List[Individual],
                         reference_point: np.ndarray) -> float:
    """
    计算超体积指标（Hypervolume Indicator）

    超体积是Pareto前沿质量的重要指标，值越大越好

    注意：此实现为简化版本，仅支持2-3个目标
    """
    if not pareto_front:
        return 0.0

    objectives = np.array([ind.objectives for ind in pareto_front])
    n_obj = objectives.shape[1]

    if n_obj == 2:
        # 2D情况：计算面积
        # 按第一个目标排序（升序）
        sorted_indices = np.argsort(objectives[:, 0])
        sorted_obj = objectives[sorted_indices]

        hv = 0.0
        prev_x = 0.0  # 前一个点的x坐标

        for i in range(len(sorted_obj)):
            # 当前矩形的宽度
            width = sorted_obj[i, 0] - prev_x
            # 当前矩形的高度（到参考点的距离）
            height = reference_point[1] - sorted_obj[i, 1]

            if height > 0 and width > 0:
                hv += width * height

            # 更新前一个x坐标
            prev_x = sorted_obj[i, 0]

        # 最后一个矩形（到参考点）
        if len(sorted_obj) > 0:
            width = reference_point[0] - sorted_obj[-1, 0]
            height = reference_point[1] - sorted_obj[-1, 1]
            if height > 0 and width > 0:
                hv += width * height

        return hv
    elif n_obj == 3:
        # 3D情况：使用蒙特卡洛方法估计
        n_samples = 10000

        # 计算边界
        min_obj = np.min(objectives, axis=0)

        # 随机采样
        samples = np.random.uniform(
            low=min_obj,
            high=reference_point,
            size=(n_samples, n_obj)
        )

        # 计算有多少样本被Pareto前沿支配
        dominated_count = 0
        for sample in samples:
            for obj in objectives:
                if np.all(obj <= sample):
                    dominated_count += 1
                    break

        # 估计超体积
        volume = np.prod(reference_point - min_obj)
        hv = volume * dominated_count / n_samples

        return hv
    else:
        # 更高维度：返回0（需要更复杂的算法）
        return 0.0


def calculate_igd(pareto_front: List[Individual],
                 true_pareto_front: np.ndarray) -> float:
    """
    计算反向世代距离（Inverted Generational Distance）

    IGD衡量算法得到的Pareto前沿与真实Pareto前沿的距离
    值越小越好

    参数：
        pareto_front: 算法得到的Pareto前沿
        true_pareto_front: 真实Pareto前沿（或参考前沿）
    """
    if not pareto_front or len(true_pareto_front) == 0:
        return float('inf')

    objectives = np.array([ind.objectives for ind in pareto_front])

    # 计算每个真实前沿点到算法前沿的最小距离
    distances = []
    for true_point in true_pareto_front:
        min_dist = np.min(np.linalg.norm(objectives - true_point, axis=1))
        distances.append(min_dist)

    igd = np.mean(distances)
    return igd


# 导出的类和函数
__all__ = [
    # 数据类
    'Individual',
    'MOProblem',
    'MOResult',
    'NSGA2Config',
    'NSGA3Config',
    # 算法类
    'NSGA2',
    'NSGA3',
    # 核心函数
    'fast_non_dominated_sort',
    'calculate_crowding_distance',
    'generate_reference_points',
    'associate_to_reference_points',
    # 遗传算子
    'simulated_binary_crossover',
    'polynomial_mutation',
    'crowding_distance_tournament',
    # 性能指标
    'calculate_hypervolume',
    'calculate_igd',
]
