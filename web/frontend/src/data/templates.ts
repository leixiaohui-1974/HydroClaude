/**
 * Built-in Model Templates
 * 内置模型模板
 *
 * v1.5.0 Feature: Model Templates
 */

import type { ModelTemplate } from '../types/template';

/**
 * Dam Break Template
 * 溃坝模型模板
 */
export const DAM_BREAK_TEMPLATE: ModelTemplate = {
  metadata: {
    id: 'dam-break-basic',
    name: 'Dam Break - Basic',
    nameCN: '溃坝 - 基础',
    description: 'A basic dam break scenario for understanding sudden release of water',
    descriptionCN: '基础溃坝场景，用于理解水体突然释放的过程',
    category: 'dam-break',
    difficulty: 'beginner',
    tags: ['dam-break', 'beginner', 'fundamental', 'hydraulics'],
    author: 'HydroClaude Team',
    createdAt: '2025-01-10',
    updatedAt: '2025-01-10',
    version: '1.0.0',
    usageCount: 0,
    rating: 5.0
  },
  config: {
    domainLength: 1000,
    duration: 100,
    timeStep: 0.1,
    manning: 0.03,
    nCells: 100,
    initialConditions: 'Upstream: 10m water depth, Downstream: 1m water depth',
    boundaryConditions: 'Closed boundaries at both ends'
  },
  nodes: [
    {
      id: 'canal-1',
      type: 'canal',
      position: { x: 250, y: 200 },
      data: {
        name: 'Main Channel',
        length: 1000,
        width: 50,
        slope: 0.001,
        manning_n: 0.03,
        n_cells: 100,
        validated: true,
        errors: [],
        warnings: []
      }
    },
    {
      id: 'boundary-upstream',
      type: 'boundary',
      position: { x: 100, y: 200 },
      data: {
        name: 'Upstream (High Water)',
        boundary_type: 'water_level',
        value: 10.0,
        position: 'upstream',
        validated: true,
        errors: [],
        warnings: []
      }
    },
    {
      id: 'boundary-downstream',
      type: 'boundary',
      position: { x: 400, y: 200 },
      data: {
        name: 'Downstream (Low Water)',
        boundary_type: 'water_level',
        value: 1.0,
        position: 'downstream',
        validated: true,
        errors: [],
        warnings: []
      }
    }
  ],
  edges: [
    {
      id: 'edge-1',
      source: 'boundary-upstream',
      target: 'canal-1',
      type: 'default'
    },
    {
      id: 'edge-2',
      source: 'canal-1',
      target: 'boundary-downstream',
      type: 'default'
    }
  ],
  learningObjectives: [
    {
      objective: 'Understand wave propagation in sudden release scenarios',
      objectiveCN: '理解突然释放情况下的波动传播',
      outcome: 'Observe shock wave formation and propagation speed'
    },
    {
      objective: 'Analyze water depth and velocity changes over time',
      objectiveCN: '分析水深和流速随时间的变化',
      outcome: 'Visualize the transition from high to low water levels'
    },
    {
      objective: 'Learn about Froude number and flow regimes',
      objectiveCN: '了解弗劳德数和流态',
      outcome: 'Identify subcritical and supercritical flow regions'
    }
  ],
  instructions: {
    en: 'This template simulates a classic dam break scenario. The upstream section has 10m water depth while downstream has only 1m. When simulation starts, observe how the water propagates downstream, creating a shock wave. Pay attention to the water depth profile evolution and velocity changes.',
    cn: '此模板模拟经典的溃坝场景。上游段水深10米，下游仅1米。当模拟开始时，观察水流如何向下游传播，形成激波。注意水深剖面演化和流速变化。'
  },
  expectedResults: {
    en: 'You should observe a shock wave moving downstream, with rapid water depth increase behind the wave front. The velocity will show a sharp gradient at the wave front. The simulation demonstrates the fundamental characteristics of dam break flow.',
    cn: '您应该观察到激波向下游移动，波前后方水深迅速增加。流速在波前处显示出急剧梯度。该模拟展示了溃坝流的基本特征。'
  },
  references: [
    'Toro, E.F. (2001). Shock-Capturing Methods for Free-Surface Shallow Flows',
    'Stoker, J.J. (1957). Water Waves: The Mathematical Theory with Applications'
  ]
};

/**
 * Reservoir Template
 * 水库模型模板
 */
export const RESERVOIR_TEMPLATE: ModelTemplate = {
  metadata: {
    id: 'reservoir-basic',
    name: 'Reservoir - Basic',
    nameCN: '水库 - 基础',
    description: 'A basic reservoir model for water level and discharge analysis',
    descriptionCN: '基础水库模型，用于水位和流量分析',
    category: 'reservoir',
    difficulty: 'beginner',
    tags: ['reservoir', 'water-management', 'beginner'],
    author: 'HydroClaude Team',
    createdAt: '2025-01-10',
    updatedAt: '2025-01-10',
    version: '1.0.0',
    usageCount: 0,
    rating: 4.8
  },
  config: {
    domainLength: 500,
    duration: 200,
    timeStep: 0.2,
    manning: 0.025,
    nCells: 50,
    initialConditions: 'Uniform 5m water depth',
    boundaryConditions: 'Constant inflow upstream, weir discharge downstream'
  },
  nodes: [
    {
      id: 'canal-reservoir',
      type: 'canal',
      position: { x: 250, y: 200 },
      data: {
        name: 'Reservoir Channel',
        length: 500,
        width: 100,
        slope: 0.0005,
        manning_n: 0.025,
        n_cells: 50,
        validated: true,
        errors: [],
        warnings: []
      }
    },
    {
      id: 'boundary-inflow',
      type: 'boundary',
      position: { x: 100, y: 200 },
      data: {
        name: 'Constant Inflow',
        boundary_type: 'discharge',
        value: 50.0,
        position: 'upstream',
        validated: true,
        errors: [],
        warnings: []
      }
    },
    {
      id: 'weir-outlet',
      type: 'weir',
      position: { x: 400, y: 200 },
      data: {
        name: 'Spillway',
        weir_type: 'broad_crested',
        crest_elevation: 3.0,
        discharge_coeff: 1.7,
        crest_width: 80,
        validated: true,
        errors: [],
        warnings: []
      }
    }
  ],
  edges: [
    {
      id: 'edge-1',
      source: 'boundary-inflow',
      target: 'canal-reservoir',
      type: 'default'
    },
    {
      id: 'edge-2',
      source: 'canal-reservoir',
      target: 'weir-outlet',
      type: 'default'
    }
  ],
  learningObjectives: [
    {
      objective: 'Understand reservoir water balance',
      objectiveCN: '理解水库水量平衡',
      outcome: 'Analyze inflow vs outflow relationship'
    },
    {
      objective: 'Learn weir hydraulics',
      objectiveCN: '学习堰流水力学',
      outcome: 'Observe weir discharge characteristics'
    },
    {
      objective: 'Study water level fluctuations',
      objectiveCN: '研究水位波动',
      outcome: 'Understand storage-discharge dynamics'
    }
  ],
  instructions: {
    en: 'This template represents a simple reservoir with constant inflow and a weir outlet. The weir controls the outflow based on water level. Run the simulation to see how water level stabilizes when inflow equals outflow over the weir.',
    cn: '此模板代表一个具有恒定入流和堰出口的简单水库。堰根据水位控制出流。运行模拟以查看当入流等于堰上出流时水位如何稳定。'
  },
  expectedResults: {
    en: 'The water level will gradually rise until the weir discharge matches the inflow rate. You will observe a quasi-steady state where water level fluctuates slightly around an equilibrium value.',
    cn: '水位将逐渐上升，直到堰流量与入流流量匹配。您将观察到准稳态，其中水位在平衡值附近略有波动。'
  },
  references: [
    'Chanson, H. (2004). The Hydraulics of Open Channel Flow',
    'USACE (2016). HEC-RAS Hydraulic Reference Manual'
  ]
};

/**
 * All available templates
 * 所有可用模板
 */
export const TEMPLATES: ModelTemplate[] = [
  DAM_BREAK_TEMPLATE,
  RESERVOIR_TEMPLATE
];

/**
 * Get template by ID
 * 通过ID获取模板
 */
export function getTemplateById(id: string): ModelTemplate | undefined {
  return TEMPLATES.find(t => t.metadata.id === id);
}

/**
 * Get templates by category
 * 按分类获取模板
 */
export function getTemplatesByCategory(category: string): ModelTemplate[] {
  return TEMPLATES.filter(t => t.metadata.category === category);
}

/**
 * Get templates by difficulty
 * 按难度获取模板
 */
export function getTemplatesByDifficulty(difficulty: string): ModelTemplate[] {
  return TEMPLATES.filter(t => t.metadata.difficulty === difficulty);
}

/**
 * Search templates by text
 * 文本搜索模板
 */
export function searchTemplates(query: string): ModelTemplate[] {
  const lowercaseQuery = query.toLowerCase();
  return TEMPLATES.filter(t =>
    t.metadata.name.toLowerCase().includes(lowercaseQuery) ||
    t.metadata.nameCN.includes(query) ||
    t.metadata.description.toLowerCase().includes(lowercaseQuery) ||
    t.metadata.descriptionCN.includes(query) ||
    t.metadata.tags.some(tag => tag.toLowerCase().includes(lowercaseQuery))
  );
}
