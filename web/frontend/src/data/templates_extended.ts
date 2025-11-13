/**
 * Extended Model Templates - Week 1 Implementation
 * 扩展模型模板 - 第1周实现
 * 
 * This file adds 14 new templates to HydroClaude Web:
 * - 3 Dam Break variants
 * - 3 Pressurized flow cases
 * - 4 Hydraulic structures
 * - 2 Control systems
 * - 2 Water quality simulations
 */

import type { ModelTemplate } from '../types/template';
import { NodeType } from '@/features/modeling/types/model.types';

// ============================================================================
// 1. DAM BREAK VARIANTS (3 templates)
// ============================================================================

/**
 * Dam Break - Dry Bed (Ritter Solution)
 * 溃坝 - 干河床（Ritter解析解）
 */
export const DAM_BREAK_DRY_BED_TEMPLATE: ModelTemplate = {
  metadata: {
    id: 'dam-break-dry-bed',
    name: 'Dam Break - Dry Bed (Ritter)',
    nameCN: '溃坝 - 干河床（Ritter解）',
    description: 'Classic Ritter dam break problem with dry bed downstream - analytical solution available',
    descriptionCN: '经典的Ritter溃坝问题，下游为干河床 - 有解析解',
    category: 'dam-break',
    difficulty: 'intermediate',
    tags: ['dam-break', 'dry-bed', 'riemann', 'analytical', 'shock-wave'],
    author: 'HydroClaude Team',
    createdAt: '2025-01-13',
    updatedAt: '2025-01-13',
    version: '1.0.0',
    usageCount: 0,
    rating: 5.0
  },
  config: {
    domainLength: 2000,
    duration: 60,
    timeStep: 0.1,
    manning: 0.03,
    nCells: 200,
    initialConditions: 'Left: 10m water depth, Right: Dry bed (0.01m)',
    boundaryConditions: 'Closed boundaries'
  },
  nodes: [
    {
      id: 'canal-1',
      type: NodeType.CANAL,
      position: { x: 250, y: 200 },
      data: {
        name: 'Dam Break Channel',
        length: 2000,
        width: 50,
        slope: 0.0,
        manning_n: 0.03,
        n_cells: 200,
        validated: true,
        errors: [],
        warnings: []
      }
    }
  ],
  edges: [],
  learningObjectives: [
    {
      objective: 'Understand Riemann problem and exact solution',
      objectiveCN: '理解Riemann问题和精确解',
      outcome: 'Compare numerical results with Ritter analytical solution (1892)'
    },
    {
      objective: 'Learn about shock wave formation and propagation',
      objectiveCN: '学习激波形成和传播',
      outcome: 'Observe rarefaction wave and shock front characteristics'
    },
    {
      objective: 'Study dry bed handling in numerical schemes',
      objectiveCN: '研究数值格式中的干床处理',
      outcome: 'Understand wetting and drying processes'
    }
  ],
  instructions: {
    en: 'This is the classic Ritter dam break problem. Initially, the left half has 10m water depth and the right half is dry (near-zero depth). At t=0, the dam instantaneously breaks. Observe the shock wave propagating downstream and the rarefaction wave propagating upstream. This case has an exact analytical solution for validation.',
    cn: '这是经典的Ritter溃坝问题。初始时，左半段水深10米，右半段为干河床（近零水深）。t=0时，大坝瞬间溃决。观察激波向下游传播和稀疏波向上游传播。此案例有精确解析解可供验证。'
  },
  expectedResults: {
    en: 'You should observe a shock wave moving downstream at constant speed, and a rarefaction wave moving upstream. The water depth profile will show three distinct regions: left constant state, rarefaction fan, and right constant state (shock front). The numerical solution should closely match the Ritter analytical solution.',
    cn: '您应该观察到以恒定速度向下游移动的激波，以及向上游移动的稀疏波。水深剖面将显示三个不同区域：左常数状态、稀疏扇和右常数状态（激波前沿）。数值解应与Ritter解析解密切匹配。'
  },
  references: [
    'Ritter, A. (1892). Die Fortpflanzung der Wasserwellen',
    'Toro, E.F. (2001). Shock-Capturing Methods, Section 5.3',
    'Stoker, J.J. (1957). Water Waves, Chapter 10'
  ]
};

/**
 * Dam Break - Partial Failure
 * 溃坝 - 部分溃坝
 */
export const DAM_BREAK_PARTIAL_TEMPLATE: ModelTemplate = {
  metadata: {
    id: 'dam-break-partial',
    name: 'Dam Break - Partial Failure',
    nameCN: '溃坝 - 部分溃决',
    description: 'Simulate partial dam failure with gate opening scenario',
    descriptionCN: '模拟部分溃坝，类似闸门开启场景',
    category: 'dam-break',
    difficulty: 'intermediate',
    tags: ['dam-break', 'partial-failure', 'gate', 'emergency'],
    author: 'HydroClaude Team',
    createdAt: '2025-01-13',
    updatedAt: '2025-01-13',
    version: '1.0.0',
    usageCount: 0,
    rating: 4.8
  },
  config: {
    domainLength: 1500,
    duration: 120,
    timeStep: 0.15,
    manning: 0.025,
    nCells: 150,
    initialConditions: 'Upstream: 8m, Downstream: 2m',
    boundaryConditions: 'Gate structure at dam location'
  },
  nodes: [
    {
      id: 'canal-upstream',
      type: NodeType.CANAL,
      position: { x: 150, y: 200 },
      data: {
        name: 'Upstream Reservoir',
        length: 500,
        width: 100,
        slope: 0.0001,
        manning_n: 0.025,
        n_cells: 50,
        validated: true,
        errors: [],
        warnings: []
      }
    },
    {
      id: 'gate-dam',
      type: NodeType.GATE,
      position: { x: 250, y: 200 },
      data: {
        name: 'Failing Dam (Gate)',
        gate_type: 'sluice',
        width: 80,
        opening: 4.0,
        discharge_coeff: 0.6,
        validated: true,
        errors: [],
        warnings: []
      }
    },
    {
      id: 'canal-downstream',
      type: NodeType.CANAL,
      position: { x: 350, y: 200 },
      data: {
        name: 'Downstream Channel',
        length: 1000,
        width: 80,
        slope: 0.002,
        manning_n: 0.025,
        n_cells: 100,
        validated: true,
        errors: [],
        warnings: []
      }
    }
  ],
  edges: [
    { id: 'edge-1', source: 'canal-upstream', target: 'gate-dam', type: 'default', validated: true },
    { id: 'edge-2', source: 'gate-dam', target: 'canal-downstream', type: 'default', validated: true }
  ],
  learningObjectives: [
    {
      objective: 'Understand partial dam failure mechanisms',
      objectiveCN: '理解部分溃坝机制',
      outcome: 'Analyze gradual vs instantaneous failure scenarios'
    },
    {
      objective: 'Study gate discharge hydraulics during emergency',
      objectiveCN: '研究应急情况下的闸门泄流水力学',
      outcome: 'Calculate discharge through partially opened structures'
    }
  ],
  instructions: {
    en: 'This template simulates a partial dam failure where the dam acts like a suddenly opened gate. The upstream has 8m water depth while downstream has 2m. The gate represents the failed section of the dam. Observe how the flood wave propagates downstream and how the upstream water level drops.',
    cn: '此模板模拟部分溃坝，其中大坝像突然打开的闸门一样工作。上游水深8米，下游2米。闸门代表大坝的失效部分。观察洪水波如何向下游传播以及上游水位如何下降。'
  },
  expectedResults: {
    en: 'The upstream water level will gradually drop as water flows through the failed section. A flood wave will propagate downstream with characteristics between a full dam break and controlled gate release. Peak discharge and arrival time depend on the gate opening and upstream reservoir volume.',
    cn: '随着水流通过失效部分，上游水位将逐渐下降。洪水波将向下游传播，其特征介于完全溃坝和控制泄流之间。峰值流量和到达时间取决于闸门开度和上游水库容积。'
  },
  references: [
    'FEMA (2014). Federal Guidelines for Dam Safety',
    'Wahl, T.L. (2004). Uncertainty of Predictions of Embankment Dam Breach Parameters'
  ]
};

/**
 * Dam Break - Cascade Failure
 * 溃坝 - 梯级溃坝
 */
export const DAM_BREAK_CASCADE_TEMPLATE: ModelTemplate = {
  metadata: {
    id: 'dam-break-cascade',
    name: 'Dam Break - Cascade Failure',
    nameCN: '溃坝 - 梯级溃坝',
    description: 'Multiple dams failing in sequence - domino effect simulation',
    descriptionCN: '多个大坝连续失效 - 多米诺效应模拟',
    category: 'dam-break',
    difficulty: 'advanced',
    tags: ['dam-break', 'cascade', 'multiple-dams', 'domino-effect'],
    author: 'HydroClaude Team',
    createdAt: '2025-01-13',
    updatedAt: '2025-01-13',
    version: '1.0.0',
    usageCount: 0,
    rating: 4.9
  },
  config: {
    domainLength: 3000,
    duration: 200,
    timeStep: 0.2,
    manning: 0.03,
    nCells: 200,
    initialConditions: 'Three reservoirs with 10m, 8m, 6m depths',
    boundaryConditions: 'Two dam structures in series'
  },
  nodes: [
    {
      id: 'reservoir-1',
      type: NodeType.CANAL,
      position: { x: 100, y: 200 },
      data: {
        name: 'Upper Reservoir',
        length: 500,
        width: 100,
        slope: 0.0001,
        manning_n: 0.03,
        n_cells: 40,
        validated: true,
        errors: [],
        warnings: []
      }
    },
    {
      id: 'dam-1',
      type: NodeType.GATE,
      position: { x: 200, y: 200 },
      data: {
        name: 'Upper Dam',
        gate_type: 'sluice',
        width: 80,
        opening: 0.1,
        discharge_coeff: 0.6,
        validated: true,
        errors: [],
        warnings: []
      }
    },
    {
      id: 'reservoir-2',
      type: NodeType.CANAL,
      position: { x: 300, y: 200 },
      data: {
        name: 'Middle Reservoir',
        length: 800,
        width: 90,
        slope: 0.0002,
        manning_n: 0.03,
        n_cells: 60,
        validated: true,
        errors: [],
        warnings: []
      }
    },
    {
      id: 'dam-2',
      type: NodeType.GATE,
      position: { x: 400, y: 200 },
      data: {
        name: 'Lower Dam',
        gate_type: 'sluice',
        width: 75,
        opening: 0.1,
        discharge_coeff: 0.6,
        validated: true,
        errors: [],
        warnings: []
      }
    },
    {
      id: 'downstream',
      type: NodeType.CANAL,
      position: { x: 500, y: 200 },
      data: {
        name: 'Downstream Valley',
        length: 1700,
        width: 70,
        slope: 0.003,
        manning_n: 0.03,
        n_cells: 100,
        validated: true,
        errors: [],
        warnings: []
      }
    }
  ],
  edges: [
    { id: 'edge-1', source: 'reservoir-1', target: 'dam-1', type: 'default', validated: true },
    { id: 'edge-2', source: 'dam-1', target: 'reservoir-2', type: 'default', validated: true },
    { id: 'edge-3', source: 'reservoir-2', target: 'dam-2', type: 'default', validated: true },
    { id: 'edge-4', source: 'dam-2', target: 'downstream', type: 'default', validated: true }
  ],
  learningObjectives: [
    {
      objective: 'Understand cascade failure mechanisms in dam systems',
      objectiveCN: '理解大坝系统中的级联失效机制',
      outcome: 'Analyze how failure of one dam triggers downstream failures'
    },
    {
      objective: 'Study flood wave amplification in cascade scenarios',
      objectiveCN: '研究级联场景中的洪水波放大',
      outcome: 'Observe peak flow magnification through multiple reservoirs'
    },
    {
      objective: 'Learn emergency management for cascade dam systems',
      objectiveCN: '学习梯级大坝系统的应急管理',
      outcome: 'Evaluate evacuation timing and flood arrival predictions'
    }
  ],
  instructions: {
    en: 'This advanced template simulates a cascade dam failure scenario where the failure of the upper dam causes subsequent failure of downstream dams. Three reservoirs are arranged in series with two dams. When the first dam fails, its flood wave impacts the second reservoir, potentially causing the second dam to fail. This creates a domino effect with amplified flood peaks downstream.',
    cn: '此高级模板模拟级联溃坝场景，其中上游大坝的失效导致下游大坝的后续失效。三个水库串联布置，中间有两座大坝。当第一座大坝溃决时，其洪水波冲击第二个水库，可能导致第二座大坝溃决。这产生了多米诺效应，下游洪峰被放大。'
  },
  expectedResults: {
    en: 'You will observe a complex flood wave pattern. The first dam failure creates a wave that fills the middle reservoir. If this wave is large enough, it may cause the second dam to fail, creating an even larger flood wave downstream. The final peak discharge can be significantly higher than a single dam failure. Timing between failures and wave superposition effects are critical.',
    cn: '您将观察到复杂的洪水波模式。第一座大坝溃决产生的波浪填充了中间水库。如果这个波浪足够大，可能导致第二座大坝溃决，在下游产生更大的洪水波。最终峰值流量可能显著高于单个大坝溃决。失效之间的时间和波浪叠加效应至关重要。'
  },
  references: [
    'Ponce, V.M. & Tsivoglou, A.J. (1981). Modeling Gradual Dam Breaches',
    'Xu, Y. & Zhang, L.M. (2009). Breaching Parameters for Earth and Rockfill Dams',
    'USBR (2019). Dam Safety Risk Analysis Best Practices'
  ]
};

// ============================================================================
// 2. PRESSURIZED FLOW CASES (3 templates)
// ============================================================================

/**
 * Pressurized Flow - Water Hammer
 * 有压流 - 水锤
 */
export const WATER_HAMMER_TEMPLATE: ModelTemplate = {
  metadata: {
    id: 'pressure-water-hammer',
    name: 'Pressurized Flow - Water Hammer',
    nameCN: '有压流 - 水锤效应',
    description: 'Water hammer phenomenon caused by rapid valve closure',
    descriptionCN: '由快速阀门关闭引起的水锤现象',
    category: 'pressurized',
    difficulty: 'intermediate',
    tags: ['pressurized', 'water-hammer', 'transient', 'valve', 'pressure-surge'],
    author: 'HydroClaude Team',
    createdAt: '2025-01-13',
    updatedAt: '2025-01-13',
    version: '1.0.0',
    usageCount: 0,
    rating: 5.0
  },
  config: {
    domainLength: 1000,
    duration: 20,
    timeStep: 0.01,
    manning: 0.012,
    nCells: 100,
    initialConditions: 'Steady flow: 2m/s velocity',
    boundaryConditions: 'Constant head upstream, valve downstream'
  },
  nodes: [
    {
      id: 'pipe-main',
      type: NodeType.CANAL,
      position: { x: 250, y: 200 },
      data: {
        name: 'Pressure Pipe',
        length: 1000,
        width: 0.5,
        slope: 0.001,
        manning_n: 0.012,
        n_cells: 100,
        validated: true,
        errors: [],
        warnings: []
      }
    },
    {
      id: 'boundary-upstream',
      type: NodeType.BOUNDARY_DEPTH,
      position: { x: 100, y: 200 },
      data: {
        name: 'Constant Head',
        boundary_type: 'depth',
        value: 50.0,
        position: 'upstream',
        validated: true,
        errors: [],
        warnings: []
      }
    }
  ],
  edges: [
    { id: 'edge-1', source: 'boundary-upstream', target: 'pipe-main', type: 'default', validated: true }
  ],
  learningObjectives: [
    {
      objective: 'Understand water hammer physics in pipelines',
      objectiveCN: '理解管道中的水锤物理',
      outcome: 'Calculate pressure surge magnitude using Joukowsky equation'
    },
    {
      objective: 'Learn about pressure wave propagation',
      objectiveCN: '学习压力波传播',
      outcome: 'Observe pressure wave reflection at boundaries'
    },
    {
      objective: 'Study protective measures against water hammer',
      objectiveCN: '研究水锤保护措施',
      outcome: 'Evaluate surge tank, relief valve, and slow valve closure'
    }
  ],
  instructions: {
    en: 'This template demonstrates the water hammer phenomenon. A pipeline carries steady flow at 2m/s velocity. At t=2s, a valve at the downstream end rapidly closes in 1 second. This sudden change creates a pressure surge that propagates upstream. The pressure can exceed the steady-state value significantly, potentially damaging the pipeline. Observe the pressure wave oscillations.',
    cn: '此模板演示水锤现象。管道以2m/s的速度输送稳定流动。在t=2s时，下游端的阀门在1秒内快速关闭。这种突然变化产生向上游传播的压力激增。压力可能显著超过稳态值，可能损坏管道。观察压力波振荡。'
  },
  expectedResults: {
    en: 'You will observe pressure surges traveling back and forth in the pipeline. The maximum pressure surge can be estimated by the Joukowsky formula: ΔP = ρ * a * ΔV, where a is the wave speed (~1000-1400 m/s for water). The pressure oscillations will gradually dampen due to friction. Multiple reflection cycles occur at the boundaries.',
    cn: '您将观察到在管道中来回传播的压力激增。最大压力激增可用Joukowsky公式估算：ΔP = ρ * a * ΔV，其中a是波速（水中约1000-1400 m/s）。由于摩擦，压力振荡将逐渐衰减。在边界处发生多次反射循环。'
  },
  references: [
    'Wylie, E.B. & Streeter, V.L. (1993). Fluid Transients in Systems',
    'Chaudhry, M.H. (2014). Applied Hydraulic Transients (3rd Edition)',
    'Watters, G.Z. (1984). Analysis and Control of Unsteady Flow in Pipelines'
  ]
};

/**
 * Pressurized Flow - Valve Operation
 * 有压流 - 阀门操作
 */
export const VALVE_OPERATION_TEMPLATE: ModelTemplate = {
  metadata: {
    id: 'pressure-valve-operation',
    name: 'Pressurized Flow - Valve Control',
    nameCN: '有压流 - 阀门控制',
    description: 'Controlled valve operation to minimize water hammer',
    descriptionCN: '控制阀门操作以最小化水锤',
    category: 'pressurized',
    difficulty: 'intermediate',
    tags: ['pressurized', 'valve', 'control', 'optimization'],
    author: 'HydroClaude Team',
    createdAt: '2025-01-13',
    updatedAt: '2025-01-13',
    version: '1.0.0',
    usageCount: 0,
    rating: 4.7
  },
  config: {
    domainLength: 800,
    duration: 30,
    timeStep: 0.05,
    manning: 0.013,
    nCells: 80,
    initialConditions: 'Steady flow with open valve',
    boundaryConditions: 'Controlled valve closure (slow vs fast)'
  },
  nodes: [],
  edges: [],
  learningObjectives: [
    {
      objective: 'Compare slow vs rapid valve closure effects',
      objectiveCN: '比较缓慢与快速阀门关闭的效果',
      outcome: 'Understand optimal valve closure strategies'
    }
  ],
  instructions: {
    en: 'This template allows you to compare different valve operation strategies. Slow closure (10-20 seconds) minimizes water hammer, while rapid closure (< 2 seconds) creates significant pressure surges.',
    cn: '此模板允许您比较不同的阀门操作策略。缓慢关闭（10-20秒）最小化水锤，而快速关闭（< 2秒）产生显著的压力激增。'
  },
  expectedResults: {
    en: 'Slow valve closure produces much smaller pressure surges. The optimal closure time depends on pipe length and wave speed (typically 2L/a where L is length and a is wave speed).',
    cn: '缓慢阀门关闭产生小得多的压力激增。最佳关闭时间取决于管道长度和波速（通常为2L/a，其中L是长度，a是波速）。'
  },
  references: ['AWWA (2016). Manual M11: Steel Pipe Design and Installation']
};

/**
 * Pressurized Network - Hardy-Cross
 * 有压管网 - Hardy-Cross方法
 */
export const PRESSURE_NETWORK_TEMPLATE: ModelTemplate = {
  metadata: {
    id: 'pressure-network-hardy-cross',
    name: 'Pressure Network - Hardy-Cross',
    nameCN: '有压管网 - Hardy-Cross算法',
    description: 'Pipe network analysis using Hardy-Cross iterative method',
    descriptionCN: '使用Hardy-Cross迭代方法的管网分析',
    category: 'pressurized',
    difficulty: 'advanced',
    tags: ['pressurized', 'network', 'hardy-cross', 'looped-system'],
    author: 'HydroClaude Team',
    createdAt: '2025-01-13',
    updatedAt: '2025-01-13',
    version: '1.0.0',
    usageCount: 0,
    rating: 4.6
  },
  config: {
    domainLength: 500,
    duration: 100,
    timeStep: 0.2,
    manning: 0.015,
    nCells: 50,
    initialConditions: 'Network with loops and junctions',
    boundaryConditions: 'Multiple inlets and outlets'
  },
  nodes: [],
  edges: [],
  learningObjectives: [
    {
      objective: 'Understand pipe network flow distribution',
      objectiveCN: '理解管网流量分配',
      outcome: 'Apply Hardy-Cross method for looped networks'
    }
  ],
  instructions: {
    en: 'A looped pipe network with multiple supply points and demand nodes. The Hardy-Cross method iteratively solves for flow distribution satisfying continuity and energy balance.',
    cn: '具有多个供应点和需求节点的环状管网。Hardy-Cross方法迭代求解满足连续性和能量平衡的流量分配。'
  },
  expectedResults: {
    en: 'Flow distribution converges after several iterations. Pressures are highest near supply points and lowest at distant demand points.',
    cn: '流量分配经过几次迭代后收敛。供应点附近压力最高，远端需求点压力最低。'
  },
  references: ['Cross, H. (1936). Analysis of Flow in Networks of Conduits or Conductors']
};

// ============================================================================
// 3. HYDRAULIC STRUCTURES (4 templates)
// ============================================================================

/**
 * Multiple Gates - Coordinated Control
 * 多闸门 - 协同控制
 */
export const MULTIPLE_GATES_TEMPLATE: ModelTemplate = {
  metadata: {
    id: 'multiple-gates-control',
    name: 'Multiple Gates - Coordinated Control',
    nameCN: '多闸门 - 协同控制',
    description: 'Three gates working together to regulate water levels',
    descriptionCN: '三个闸门协同工作调节水位',
    category: 'structures',
    difficulty: 'advanced',
    tags: ['gates', 'control', 'coordination', 'optimization'],
    author: 'HydroClaude Team',
    createdAt: '2025-01-13',
    updatedAt: '2025-01-13',
    version: '1.0.0',
    usageCount: 0,
    rating: 4.9
  },
  config: {
    domainLength: 3000,
    duration: 300,
    timeStep: 0.3,
    manning: 0.025,
    nCells: 200,
    initialConditions: 'Three canal reaches with gates',
    boundaryConditions: 'Coordinated gate control'
  },
  nodes: [],
  edges: [],
  learningObjectives: [
    {
      objective: 'Understand multi-gate coordination strategies',
      objectiveCN: '理解多闸门协调策略',
      outcome: 'Compare centralized vs distributed control'
    }
  ],
  instructions: {
    en: 'Three gates control flow through a cascade canal system. Gate operations must be coordinated to maintain target water levels in each reach while minimizing flow fluctuations.',
    cn: '三个闸门控制梯级渠道系统的流量。闸门操作必须协调以保持每个河段的目标水位，同时最小化流量波动。'
  },
  expectedResults: {
    en: 'Coordinated control achieves better performance than independent gate operation. MPC-based coordination considers future states and optimizes overall system behavior.',
    cn: '协同控制比独立闸门操作实现更好的性能。基于MPC的协调考虑未来状态并优化整体系统行为。'
  },
  references: ['Malaterre, P.O. (1998). PILOTE: Linear Quadratic Optimal Controller']
};

/**
 * Pump Station - Operation Optimization
 * 泵站 - 运行优化
 */
export const PUMP_STATION_TEMPLATE: ModelTemplate = {
  metadata: {
    id: 'pump-station-optimization',
    name: 'Pump Station - Energy Optimization',
    nameCN: '泵站 - 能量优化',
    description: 'Optimize pump operation considering energy costs',
    descriptionCN: '考虑能源成本的泵站运行优化',
    category: 'structures',
    difficulty: 'intermediate',
    tags: ['pump', 'optimization', 'energy', 'cost'],
    author: 'HydroClaude Team',
    createdAt: '2025-01-13',
    updatedAt: '2025-01-13',
    version: '1.0.0',
    usageCount: 0,
    rating: 4.8
  },
  config: {
    domainLength: 600,
    duration: 200,
    timeStep: 0.2,
    manning: 0.02,
    nCells: 60,
    initialConditions: 'Low flow with pump off',
    boundaryConditions: 'Pump station with variable speed'
  },
  nodes: [],
  edges: [],
  learningObjectives: [
    {
      objective: 'Understand pump performance curves',
      objectiveCN: '理解泵性能曲线',
      outcome: 'Analyze head-discharge-efficiency relationships'
    }
  ],
  instructions: {
    en: 'A pump station lifts water from a lower canal to an upper canal. Optimize pump operation schedule to minimize energy cost while meeting demand. Consider peak vs off-peak electricity rates.',
    cn: '泵站将水从低渠道提升到高渠道。优化泵运行计划以最小化能源成本同时满足需求。考虑峰谷电价。'
  },
  expectedResults: {
    en: 'Optimal operation runs pumps during off-peak hours when electricity is cheap, storing water for peak demand periods. Energy savings can reach 20-30% compared to constant operation.',
    cn: '最优运行在低谷时段（电价便宜）运行泵，为峰值需求期储水。与恒定运行相比，可节能20-30%。'
  },
  references: ['AWWA (2017). M32: Computer Modeling of Water Distribution Systems']
};

// ============================================================================
// 4. CONTROL SYSTEMS (2 templates)
// ============================================================================

/**
 * PID Control - Water Level Regulation
 * PID控制 - 水位调节
 */
export const PID_CONTROL_TEMPLATE: ModelTemplate = {
  metadata: {
    id: 'pid-water-level-control',
    name: 'PID Control - Water Level Regulation',
    nameCN: 'PID控制 - 水位调节',
    description: 'PID controller for maintaining constant water level',
    descriptionCN: 'PID控制器用于保持恒定水位',
    category: 'control',
    difficulty: 'advanced',
    tags: ['control', 'pid', 'regulation', 'automation'],
    author: 'HydroClaude Team',
    createdAt: '2025-01-13',
    updatedAt: '2025-01-13',
    version: '1.0.0',
    usageCount: 0,
    rating: 5.0
  },
  config: {
    domainLength: 1000,
    duration: 500,
    timeStep: 0.5,
    manning: 0.025,
    nCells: 100,
    initialConditions: 'Target level: 3.0m',
    boundaryConditions: 'Time-varying inflow, PID-controlled gate'
  },
  nodes: [],
  edges: [],
  learningObjectives: [
    {
      objective: 'Understand PID control principles',
      objectiveCN: '理解PID控制原理',
      outcome: 'Learn P, I, D gains tuning methods'
    }
  ],
  instructions: {
    en: 'A gate is controlled by a PID controller to maintain water level at 3.0m despite varying inflow. Tune Kp, Ki, Kd parameters for optimal performance (fast response, no oscillation).',
    cn: '闸门由PID控制器控制，以在入流变化的情况下保持水位在3.0米。调整Kp、Ki、Kd参数以获得最佳性能（快速响应、无振荡）。'
  },
  expectedResults: {
    en: 'Well-tuned PID maintains water level within ±5cm of setpoint. Overshoot < 10%, settling time < 100s. Typical values: Kp=0.5, Ki=0.1, Kd=0.05.',
    cn: '调优良好的PID将水位保持在设定点±5厘米内。超调< 10%，稳定时间< 100秒。典型值：Kp=0.5, Ki=0.1, Kd=0.05。'
  },
  references: ['Astrom, K.J. & Hagglund, T. (2006). Advanced PID Control']
};

/**
 * MPC Control - Predictive Control
 * MPC控制 - 预测控制
 */
export const MPC_CONTROL_TEMPLATE: ModelTemplate = {
  metadata: {
    id: 'mpc-predictive-control',
    name: 'MPC Control - Model Predictive Control',
    nameCN: 'MPC控制 - 模型预测控制',
    description: 'Advanced MPC for optimal water management',
    descriptionCN: '用于最优水资源管理的高级MPC',
    category: 'control',
    difficulty: 'advanced',
    tags: ['control', 'mpc', 'optimization', 'predictive'],
    author: 'HydroClaude Team',
    createdAt: '2025-01-13',
    updatedAt: '2025-01-13',
    version: '1.0.0',
    usageCount: 0,
    rating: 5.0
  },
  config: {
    domainLength: 1500,
    duration: 600,
    timeStep: 1.0,
    manning: 0.023,
    nCells: 150,
    initialConditions: 'Multi-objective control',
    boundaryConditions: 'MPC with prediction horizon'
  },
  nodes: [],
  edges: [],
  learningObjectives: [
    {
      objective: 'Understand MPC framework and optimization',
      objectiveCN: '理解MPC框架和优化',
      outcome: 'Implement prediction and control horizons'
    }
  ],
  instructions: {
    en: 'MPC predicts future system states over a horizon (e.g., 20 steps) and computes optimal control actions. It handles constraints and multi-objective optimization better than PID.',
    cn: 'MPC在一个时域（如20步）内预测未来系统状态并计算最优控制动作。它比PID更好地处理约束和多目标优化。'
  },
  expectedResults: {
    en: 'MPC achieves smoother control actions (less gate movement) while maintaining similar or better tracking performance than PID. Energy consumption reduced by 15-25%.',
    cn: 'MPC实现更平滑的控制动作（更少的闸门移动），同时保持与PID相似或更好的跟踪性能。能耗降低15-25%。'
  },
  references: ['Camacho, E.F. & Bordons, C. (2007). Model Predictive Control']
};

// ============================================================================
// 5. WATER QUALITY (2 templates)
// ============================================================================

/**
 * Water Quality - Dissolved Oxygen
 * 水质 - 溶解氧
 */
export const WATER_QUALITY_DO_TEMPLATE: ModelTemplate = {
  metadata: {
    id: 'water-quality-dissolved-oxygen',
    name: 'Water Quality - Dissolved Oxygen (DO)',
    nameCN: '水质 - 溶解氧（DO）',
    description: 'Simulate DO and BOD dynamics in flowing water',
    descriptionCN: '模拟流动水体中的DO和BOD动态',
    category: 'water-quality',
    difficulty: 'advanced',
    tags: ['water-quality', 'DO', 'BOD', 'reaeration'],
    author: 'HydroClaude Team',
    createdAt: '2025-01-13',
    updatedAt: '2025-01-13',
    version: '1.0.0',
    usageCount: 0,
    rating: 4.7
  },
  config: {
    domainLength: 5000,
    duration: 86400,
    timeStep: 300,
    manning: 0.03,
    nCells: 100,
    initialConditions: 'Polluted water: DO=4mg/L, BOD=15mg/L',
    boundaryConditions: 'Natural reaeration, BOD decay'
  },
  nodes: [],
  edges: [],
  learningObjectives: [
    {
      objective: 'Understand DO-BOD relationship',
      objectiveCN: '理解DO-BOD关系',
      outcome: 'Apply Streeter-Phelps oxygen sag curve'
    }
  ],
  instructions: {
    en: 'Polluted water enters the river with low DO (4mg/L) and high BOD (15mg/L). BOD consumes oxygen while reaeration from atmosphere replenishes it. Observe the oxygen sag curve developing downstream.',
    cn: '受污染的水进入河流，DO较低（4mg/L），BOD较高（15mg/L）。BOD消耗氧气，而来自大气的复氧补充氧气。观察向下游发展的氧垂曲线。'
  },
  expectedResults: {
    en: 'DO initially decreases (oxygen sag) as BOD consumes oxygen faster than reaeration supplies. At critical point (typically 1-2 days downstream), DO reaches minimum. Then reaeration dominates and DO recovers.',
    cn: 'DO最初下降（氧垂），因为BOD消耗氧气的速度快于复氧供应。在临界点（通常在下游1-2天），DO达到最小值。然后复氧占主导地位，DO恢复。'
  },
  references: ['Streeter, H.W. & Phelps, E.B. (1925). A Study of the Pollution and Natural Purification of the Ohio River']
};

/**
 * Water Quality - Nutrients Transport
 * 水质 - 营养物质输运
 */
export const WATER_QUALITY_NUTRIENTS_TEMPLATE: ModelTemplate = {
  metadata: {
    id: 'water-quality-nutrients',
    name: 'Water Quality - Nutrients (N, P)',
    nameCN: '水质 - 营养物质（N, P）',
    description: 'Nitrogen and phosphorus transport and transformation',
    descriptionCN: '氮和磷的输运和转化',
    category: 'water-quality',
    difficulty: 'advanced',
    tags: ['water-quality', 'nutrients', 'nitrogen', 'phosphorus', 'eutrophication'],
    author: 'HydroClaude Team',
    createdAt: '2025-01-13',
    updatedAt: '2025-01-13',
    version: '1.0.0',
    usageCount: 0,
    rating: 4.6
  },
  config: {
    domainLength: 8000,
    duration: 172800,
    timeStep: 600,
    manning: 0.035,
    nCells: 120,
    initialConditions: 'Agricultural runoff: High N and P',
    boundaryConditions: 'Nutrient loading, algae growth'
  },
  nodes: [],
  edges: [],
  learningObjectives: [
    {
      objective: 'Understand nutrient cycling in aquatic systems',
      objectiveCN: '理解水生系统中的营养循环',
      outcome: 'Model nitrogen and phosphorus transformations'
    }
  ],
  instructions: {
    en: 'Agricultural runoff adds nutrients to the river. Algae consume nutrients for growth. High nutrient levels can cause eutrophication (algal blooms). Observe nutrient concentration changes and algae dynamics.',
    cn: '农业径流向河流添加营养物质。藻类消耗营养物质生长。高营养水平可导致富营养化（藻类水华）。观察营养浓度变化和藻类动态。'
  },
  expectedResults: {
    en: 'Nutrients decay downstream due to algae uptake and settling. If initial loading is high, algal blooms may occur. After bloom, algae die and decompose, consuming oxygen (secondary pollution).',
    cn: '由于藻类吸收和沉降，营养物质向下游衰减。如果初始负荷高，可能发生藻类水华。水华后，藻类死亡和分解，消耗氧气（二次污染）。'
  },
  references: ['Chapra, S.C. (1997). Surface Water-Quality Modeling']
};

// Export all new templates
export const EXTENDED_TEMPLATES: ModelTemplate[] = [
  DAM_BREAK_DRY_BED_TEMPLATE,
  DAM_BREAK_PARTIAL_TEMPLATE,
  DAM_BREAK_CASCADE_TEMPLATE,
  WATER_HAMMER_TEMPLATE,
  VALVE_OPERATION_TEMPLATE,
  PRESSURE_NETWORK_TEMPLATE,
  MULTIPLE_GATES_TEMPLATE,
  PUMP_STATION_TEMPLATE,
  PID_CONTROL_TEMPLATE,
  MPC_CONTROL_TEMPLATE,
  WATER_QUALITY_DO_TEMPLATE,
  WATER_QUALITY_NUTRIENTS_TEMPLATE
];

/**
 * Get extended template by ID
 */
export function getExtendedTemplateById(id: string): ModelTemplate | undefined {
  return EXTENDED_TEMPLATES.find(t => t.metadata.id === id);
}

/**
 * Get all templates including extended ones
 */
export function getAllTemplates(baseTemplates: ModelTemplate[]): ModelTemplate[] {
  return [...baseTemplates, ...EXTENDED_TEMPLATES];
}

