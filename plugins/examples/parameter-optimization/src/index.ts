/**
 * 参数优化插件
 * 
 * 功能：
 * - 使用遗传算法优化渠道参数
 * - 自动寻找最优糙率、坡度等参数
 * - 可视化优化过程
 * - 保存优化历史
 * 
 * @author HydroClaude Team
 * @version 1.0.0
 */

import type { Plugin, PluginAPI } from '../../../webapp/src/types/plugin';

/**
 * 优化参数
 */
interface OptimizationParams {
  algorithm: 'genetic' | 'gradient' | 'hybrid';
  populationSize: number;
  generations: number;
  mutationRate: number;
  targetVariable: string;
  targetValue: number;
  parameters: {
    name: string;
    min: number;
    max: number;
    current: number;
  }[];
}

/**
 * 个体（染色体）
 */
interface Individual {
  genes: number[];      // 参数值
  fitness: number;      // 适应度
  generation: number;   // 代数
}

/**
 * 优化历史
 */
interface OptimizationHistory {
  generation: number;
  bestFitness: number;
  avgFitness: number;
  bestIndividual: Individual;
  timestamp: number;
}

/**
 * 参数优化插件类
 */
class ParameterOptimizationPlugin implements Plugin {
  private api!: PluginAPI;
  private isOptimizing = false;
  private history: OptimizationHistory[] = [];
  private currentGeneration = 0;

  manifest = {
    id: 'parameter-optimization',
    name: '参数优化插件',
    version: '1.0.0',
    description: '使用遗传算法优化渠道参数',
    author: 'HydroClaude Team',
    main: 'dist/index.js',
    permissions: [
      'simulation:read' as const,
      'simulation:write' as const,
      'simulation:execute' as const,
      'ui:modify' as const,
      'storage:read' as const,
      'storage:write' as const,
    ],
    license: 'MIT',
  };

  /**
   * 插件激活
   */
  async onActivate(api: PluginAPI): Promise<void> {
    this.api = api;

    // 注册命令
    api.commands.register('parameter-optimization.optimize', () => this.startOptimization());
    api.commands.register('parameter-optimization.stop', () => this.stopOptimization());
    api.commands.register('parameter-optimization.viewHistory', () => this.viewHistory());

    // 添加工具栏按钮
    api.ui.addButton({
      id: 'optimize-button',
      label: '参数优化',
      icon: 'target',
      position: 'toolbar',
      onClick: () => this.startOptimization(),
    });

    // 监听仿真完成事件
    api.events.on('simulation:complete', (result) => {
      this.handleSimulationComplete(result);
    });

    // 加载历史记录
    await this.loadHistory();

    api.utils.log('参数优化插件已激活');
  }

  /**
   * 插件停用
   */
  async onDeactivate(): Promise<void> {
    this.stopOptimization();
    await this.saveHistory();
    this.api.utils.log('参数优化插件已停用');
  }

  /**
   * 开始优化
   */
  private async startOptimization(): Promise<void> {
    if (this.isOptimizing) {
      this.api.ui.showNotification({
        type: 'warning',
        message: '优化正在进行中，请先停止当前优化',
      });
      return;
    }

    // 获取优化参数
    const params = await this.getOptimizationParams();
    if (!params) return;

    this.isOptimizing = true;
    this.currentGeneration = 0;
    this.history = [];

    this.api.ui.showNotification({
      type: 'info',
      message: '开始参数优化...',
    });

    try {
      // 运行遗传算法
      await this.runGeneticAlgorithm(params);

      this.api.ui.showNotification({
        type: 'success',
        message: '参数优化完成！',
      });
    } catch (error) {
      this.api.utils.error('优化失败:', error);
      this.api.ui.showNotification({
        type: 'error',
        message: '优化失败: ' + (error as Error).message,
      });
    } finally {
      this.isOptimizing = false;
    }
  }

  /**
   * 停止优化
   */
  private stopOptimization(): void {
    if (!this.isOptimizing) {
      this.api.ui.showNotification({
        type: 'info',
        message: '当前没有正在进行的优化',
      });
      return;
    }

    this.isOptimizing = false;
    this.api.ui.showNotification({
      type: 'info',
      message: '优化已停止',
    });
  }

  /**
   * 获取优化参数
   */
  private async getOptimizationParams(): Promise<OptimizationParams | null> {
    // 从设置中读取
    const algorithm = (await this.api.storage.get('algorithm')) || 'genetic';
    const populationSize = (await this.api.storage.get('populationSize')) || 50;
    const generations = (await this.api.storage.get('generations')) || 100;
    const mutationRate = (await this.api.storage.get('mutationRate')) || 0.1;

    // 获取当前配置
    const config = await this.api.simulation.getConfig();

    // 构建优化参数
    return {
      algorithm,
      populationSize,
      generations,
      mutationRate,
      targetVariable: 'flow_rate',
      targetValue: config.flow_rate || 10.0,
      parameters: [
        {
          name: 'roughness',
          min: 0.01,
          max: 0.05,
          current: config.roughness || 0.025,
        },
        {
          name: 'slope',
          min: 0.0001,
          max: 0.01,
          current: config.slope || 0.001,
        },
      ],
    };
  }

  /**
   * 运行遗传算法
   */
  private async runGeneticAlgorithm(params: OptimizationParams): Promise<void> {
    // 初始化种群
    let population = this.initializePopulation(params);

    // 迭代
    for (let gen = 0; gen < params.generations && this.isOptimizing; gen++) {
      this.currentGeneration = gen;

      // 评估适应度
      population = await this.evaluateFitness(population, params);

      // 选择
      const selected = this.selection(population, params.populationSize / 2);

      // 交叉
      const offspring = this.crossover(selected, params.populationSize);

      // 变异
      this.mutate(offspring, params);

      // 新一代
      population = offspring;

      // 记录历史
      const best = population.reduce((a, b) => (a.fitness > b.fitness ? a : b));
      const avgFitness = population.reduce((sum, ind) => sum + ind.fitness, 0) / population.length;

      this.history.push({
        generation: gen,
        bestFitness: best.fitness,
        avgFitness,
        bestIndividual: best,
        timestamp: Date.now(),
      });

      // 更新进度
      this.api.events.emit('optimization:progress', {
        generation: gen,
        maxGenerations: params.generations,
        bestFitness: best.fitness,
      });

      // 每10代显示一次进度
      if (gen % 10 === 0) {
        this.api.utils.log(
          `第${gen}代: 最佳适应度=${best.fitness.toFixed(4)}, 平均适应度=${avgFitness.toFixed(4)}`
        );
      }
    }

    // 保存历史
    await this.saveHistory();

    // 应用最优参数
    const best = population.reduce((a, b) => (a.fitness > b.fitness ? a : b));
    await this.applyBestParameters(best, params);
  }

  /**
   * 初始化种群
   */
  private initializePopulation(params: OptimizationParams): Individual[] {
    const population: Individual[] = [];

    for (let i = 0; i < params.populationSize; i++) {
      const genes = params.parameters.map((p) => Math.random() * (p.max - p.min) + p.min);

      population.push({
        genes,
        fitness: 0,
        generation: 0,
      });
    }

    return population;
  }

  /**
   * 评估适应度
   */
  private async evaluateFitness(
    population: Individual[],
    params: OptimizationParams
  ): Promise<Individual[]> {
    for (const individual of population) {
      // 构建配置
      const config = await this.api.simulation.getConfig();

      // 应用参数
      params.parameters.forEach((p, i) => {
        (config as any)[p.name] = individual.genes[i];
      });

      try {
        // 运行仿真
        const result = await this.api.simulation.run(config);

        // 计算适应度（误差的负数，越小越好）
        const error = Math.abs(result[params.targetVariable] - params.targetValue);
        individual.fitness = 1.0 / (1.0 + error);
      } catch (error) {
        // 仿真失败，适应度为0
        individual.fitness = 0;
        this.api.utils.warn('仿真失败:', error);
      }
    }

    return population;
  }

  /**
   * 选择
   */
  private selection(population: Individual[], count: number): Individual[] {
    // 轮盘赌选择
    const totalFitness = population.reduce((sum, ind) => sum + ind.fitness, 0);
    const selected: Individual[] = [];

    for (let i = 0; i < count; i++) {
      let rand = Math.random() * totalFitness;
      let sum = 0;

      for (const individual of population) {
        sum += individual.fitness;
        if (sum >= rand) {
          selected.push({ ...individual });
          break;
        }
      }
    }

    return selected;
  }

  /**
   * 交叉
   */
  private crossover(parents: Individual[], targetSize: number): Individual[] {
    const offspring: Individual[] = [];

    while (offspring.length < targetSize) {
      // 随机选择两个父代
      const parent1 = parents[Math.floor(Math.random() * parents.length)];
      const parent2 = parents[Math.floor(Math.random() * parents.length)];

      // 单点交叉
      const crossPoint = Math.floor(Math.random() * parent1.genes.length);
      const childGenes = [
        ...parent1.genes.slice(0, crossPoint),
        ...parent2.genes.slice(crossPoint),
      ];

      offspring.push({
        genes: childGenes,
        fitness: 0,
        generation: this.currentGeneration + 1,
      });
    }

    return offspring;
  }

  /**
   * 变异
   */
  private mutate(population: Individual[], params: OptimizationParams): void {
    for (const individual of population) {
      for (let i = 0; i < individual.genes.length; i++) {
        if (Math.random() < params.mutationRate) {
          const param = params.parameters[i];
          individual.genes[i] = Math.random() * (param.max - param.min) + param.min;
        }
      }
    }
  }

  /**
   * 应用最优参数
   */
  private async applyBestParameters(best: Individual, params: OptimizationParams): Promise<void> {
    const config = await this.api.simulation.getConfig();

    params.parameters.forEach((p, i) => {
      (config as any)[p.name] = best.genes[i];
    });

    await this.api.simulation.updateConfig(config);

    this.api.ui.showNotification({
      type: 'success',
      message: `最优参数已应用: ${params.parameters
        .map((p, i) => `${p.name}=${best.genes[i].toFixed(4)}`)
        .join(', ')}`,
    });
  }

  /**
   * 查看历史
   */
  private async viewHistory(): Promise<void> {
    if (this.history.length === 0) {
      this.api.ui.showNotification({
        type: 'info',
        message: '暂无优化历史',
      });
      return;
    }

    // 显示历史数据
    this.api.utils.log('优化历史:');
    this.history.forEach((h) => {
      this.api.utils.log(
        `第${h.generation}代: 最佳适应度=${h.bestFitness.toFixed(4)}, 平均适应度=${h.avgFitness.toFixed(4)}`
      );
    });

    // TODO: 在UI中显示图表
  }

  /**
   * 处理仿真完成
   */
  private handleSimulationComplete(result: any): void {
    if (!this.isOptimizing) return;

    this.api.utils.log('仿真完成，继续优化...');
  }

  /**
   * 加载历史
   */
  private async loadHistory(): Promise<void> {
    const saved = await this.api.storage.get('optimization-history');
    if (saved) {
      this.history = saved;
      this.api.utils.log(`已加载${this.history.length}条优化历史`);
    }
  }

  /**
   * 保存历史
   */
  private async saveHistory(): Promise<void> {
    await this.api.storage.set('optimization-history', this.history);
    this.api.utils.log('优化历史已保存');
  }
}

// 导出插件实例
export default new ParameterOptimizationPlugin();
