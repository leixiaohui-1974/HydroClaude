/**
 * Built-in Model Templates
 * 内置模型模板
 *
 * v1.5.0 Feature: Model Templates
 */

import type { ModelTemplate } from '../types/template';
import { NodeType } from '@/features/modeling/types/model.types';

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
      type: NodeType.CANAL,
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
      type: NodeType.BOUNDARY_DEPTH,
      position: { x: 100, y: 200 },
      data: {
        name: 'Upstream (High Water)',
        boundary_type: 'depth',
        value: 10.0,
        position: 'upstream',
        validated: true,
        errors: [],
        warnings: []
      }
    },
    {
      id: 'boundary-downstream',
      type: NodeType.BOUNDARY_DEPTH,
      position: { x: 400, y: 200 },
      data: {
        name: 'Downstream (Low Water)',
        boundary_type: 'depth',
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
      type: 'default',
      validated: true
    },
    {
      id: 'edge-2',
      source: 'canal-1',
      target: 'boundary-downstream',
      type: 'default',
      validated: true
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
      type: NodeType.CANAL,
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
      type: NodeType.BOUNDARY_FLOW,
      position: { x: 100, y: 200 },
      data: {
        name: 'Constant Inflow',
        boundary_type: 'flow',
        value: 50.0,
        position: 'upstream',
        validated: true,
        errors: [],
        warnings: []
      }
    },
    {
      id: 'weir-outlet',
      type: NodeType.WEIR,
      position: { x: 400, y: 200 },
      data: {
        name: 'Spillway',
        weir_type: 'broad_crested',
        crest_elevation: 3.0,
        discharge_coeff: 1.7,
        width: 80,
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
      type: 'default',
      validated: true
    },
    {
      id: 'edge-2',
      source: 'canal-reservoir',
      target: 'weir-outlet',
      type: 'default',
      validated: true
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
 * Channel Flow Template
 * 渠道流动模型模板
 */
export const CHANNEL_FLOW_TEMPLATE: ModelTemplate = {
  metadata: {
    id: 'channel-flow-basic',
    name: 'Channel Flow - Basic',
    nameCN: '渠道流动 - 基础',
    description: 'Study steady uniform flow in an open channel with varying bed slope',
    descriptionCN: '研究开放渠道中具有变化床坡的稳态均匀流动',
    category: 'channel',
    difficulty: 'beginner',
    tags: ['channel', 'uniform-flow', 'beginner', 'open-channel'],
    author: 'HydroClaude Team',
    createdAt: '2025-01-12',
    updatedAt: '2025-01-12',
    version: '1.0.0',
    usageCount: 0,
    rating: 4.7
  },
  config: {
    domainLength: 800,
    duration: 150,
    timeStep: 0.15,
    manning: 0.02,
    nCells: 80,
    initialConditions: 'Uniform 3m water depth',
    boundaryConditions: 'Constant discharge upstream, normal depth downstream'
  },
  nodes: [
    {
      id: 'canal-main',
      type: NodeType.CANAL,
      position: { x: 250, y: 200 },
      data: {
        name: 'Main Channel',
        length: 800,
        width: 30,
        slope: 0.002,
        manning_n: 0.02,
        n_cells: 80,
        validated: true,
        errors: [],
        warnings: []
      }
    },
    {
      id: 'boundary-upstream',
      type: NodeType.BOUNDARY_FLOW,
      position: { x: 100, y: 200 },
      data: {
        name: 'Upstream Discharge',
        boundary_type: 'flow',
        value: 30.0,
        position: 'upstream',
        validated: true,
        errors: [],
        warnings: []
      }
    },
    {
      id: 'boundary-downstream',
      type: NodeType.BOUNDARY_DEPTH,
      position: { x: 400, y: 200 },
      data: {
        name: 'Downstream Normal Depth',
        boundary_type: 'depth',
        value: 2.5,
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
      target: 'canal-main',
      type: 'default',
      validated: true
    },
    {
      id: 'edge-2',
      source: 'canal-main',
      target: 'boundary-downstream',
      type: 'default',
      validated: true
    }
  ],
  learningObjectives: [
    {
      objective: 'Understand steady uniform flow principles',
      objectiveCN: '理解稳态均匀流原理',
      outcome: 'Observe how flow reaches equilibrium in a channel'
    },
    {
      objective: 'Learn Manning equation application',
      objectiveCN: '学习曼宁公式的应用',
      outcome: 'Analyze relationship between slope, roughness, and flow depth'
    },
    {
      objective: 'Study normal depth concept',
      objectiveCN: '研究正常水深概念',
      outcome: 'Identify normal depth under given conditions'
    }
  ],
  instructions: {
    en: 'This template demonstrates steady uniform flow in an open channel. A constant discharge enters upstream, and the flow adjusts to reach normal depth conditions. Observe how the water surface profile stabilizes along the channel.',
    cn: '此模板演示开放渠道中的稳态均匀流动。恒定流量从上游进入，流动调整以达到正常水深条件。观察水面剖面如何沿渠道稳定。'
  },
  expectedResults: {
    en: 'The flow will establish a near-uniform water depth profile after initial transients. The depth should approximate the normal depth calculated from Manning equation. Velocity will be relatively constant along the channel.',
    cn: '在初始瞬态后，流动将建立近乎均匀的水深剖面。水深应接近从曼宁公式计算的正常水深。流速沿渠道将相对恒定。'
  },
  references: [
    'Chow, V.T. (1959). Open-Channel Hydraulics',
    'French, R.H. (1985). Open-Channel Hydraulics'
  ]
};

/**
 * River Flood Template
 * 河流洪水模型模板
 */
export const RIVER_FLOOD_TEMPLATE: ModelTemplate = {
  metadata: {
    id: 'river-flood-intermediate',
    name: 'River Flood - Wave Propagation',
    nameCN: '河流洪水 - 波动传播',
    description: 'Simulate flood wave propagation in a river with time-varying inflow',
    descriptionCN: '模拟河流中具有时变入流的洪水波传播',
    category: 'flood',
    difficulty: 'intermediate',
    tags: ['flood', 'river', 'unsteady-flow', 'intermediate', 'wave-propagation'],
    author: 'HydroClaude Team',
    createdAt: '2025-01-12',
    updatedAt: '2025-01-12',
    version: '1.0.0',
    usageCount: 0,
    rating: 4.9
  },
  config: {
    domainLength: 2000,
    duration: 300,
    timeStep: 0.2,
    manning: 0.035,
    nCells: 150,
    initialConditions: 'Low flow: 2m water depth',
    boundaryConditions: 'Time-varying discharge upstream (flood hydrograph), normal depth downstream'
  },
  nodes: [
    {
      id: 'canal-river',
      type: NodeType.CANAL,
      position: { x: 250, y: 200 },
      data: {
        name: 'River Reach',
        length: 2000,
        width: 80,
        slope: 0.0008,
        manning_n: 0.035,
        n_cells: 150,
        validated: true,
        errors: [],
        warnings: []
      }
    },
    {
      id: 'boundary-flood',
      type: NodeType.BOUNDARY_FLOW,
      position: { x: 100, y: 200 },
      data: {
        name: 'Flood Hydrograph',
        boundary_type: 'flow',
        value: 100.0,
        position: 'upstream',
        validated: true,
        errors: [],
        warnings: []
      }
    },
    {
      id: 'boundary-downstream',
      type: NodeType.BOUNDARY_DEPTH,
      position: { x: 400, y: 200 },
      data: {
        name: 'Downstream Control',
        boundary_type: 'depth',
        value: 2.0,
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
      source: 'boundary-flood',
      target: 'canal-river',
      type: 'default',
      validated: true
    },
    {
      id: 'edge-2',
      source: 'canal-river',
      target: 'boundary-downstream',
      type: 'default',
      validated: true
    }
  ],
  learningObjectives: [
    {
      objective: 'Understand flood wave propagation mechanisms',
      objectiveCN: '理解洪水波传播机制',
      outcome: 'Observe wave attenuation and timing'
    },
    {
      objective: 'Analyze peak discharge and water level changes',
      objectiveCN: '分析峰值流量和水位变化',
      outcome: 'Study how peak flows are reduced and delayed downstream'
    },
    {
      objective: 'Learn flood routing concepts',
      objectiveCN: '学习洪水演进概念',
      outcome: 'Understand storage effects in river channels'
    }
  ],
  instructions: {
    en: 'This template simulates a flood event in a river. The upstream boundary represents a flood hydrograph with rising and falling stages. Observe how the flood wave propagates downstream, experiencing attenuation and lag. Pay attention to peak flow reduction and timing delays.',
    cn: '此模板模拟河流中的洪水事件。上游边界表示具有上升和下降阶段的洪水过程线。观察洪水波如何向下游传播，经历衰减和滞后。注意峰值流量减少和时间延迟。'
  },
  expectedResults: {
    en: 'The flood wave will propagate downstream with reduced peak magnitude and delayed peak timing. You should observe the characteristic flood wave attenuation due to channel storage. The water surface profile will show a gradual rise and fall during the event.',
    cn: '洪水波将向下游传播，峰值幅度减小，峰值时间延迟。您应该观察到由于渠道蓄水导致的特征洪水波衰减。水面剖面将在事件期间显示出渐进的上升和下降。'
  },
  references: [
    'Cunge, J.A. (1969). On the Subject of a Flood Propagation Method',
    'Fread, D.L. (1993). Flow Routing in Handbook of Hydrology'
  ]
};

/**
 * Urban Drainage Template
 * 城市排水模型模板
 */
export const URBAN_DRAINAGE_TEMPLATE: ModelTemplate = {
  metadata: {
    id: 'urban-drainage-intermediate',
    name: 'Urban Drainage - Stormwater',
    nameCN: '城市排水 - 雨水系统',
    description: 'Model urban stormwater drainage system with rainfall-runoff',
    descriptionCN: '模拟具有降雨-径流的城市雨水排水系统',
    category: 'urban',
    difficulty: 'intermediate',
    tags: ['urban', 'drainage', 'stormwater', 'intermediate', 'rainfall'],
    author: 'HydroClaude Team',
    createdAt: '2025-01-12',
    updatedAt: '2025-01-12',
    version: '1.0.0',
    usageCount: 0,
    rating: 4.6
  },
  config: {
    domainLength: 600,
    duration: 180,
    timeStep: 0.1,
    manning: 0.015,
    nCells: 60,
    initialConditions: 'Dry channel (0.1m base flow)',
    boundaryConditions: 'Runoff hydrograph upstream, free outfall downstream'
  },
  nodes: [
    {
      id: 'canal-storm-drain',
      type: NodeType.CANAL,
      position: { x: 250, y: 200 },
      data: {
        name: 'Storm Drain Channel',
        length: 600,
        width: 15,
        slope: 0.005,
        manning_n: 0.015,
        n_cells: 60,
        validated: true,
        errors: [],
        warnings: []
      }
    },
    {
      id: 'boundary-runoff',
      type: NodeType.BOUNDARY_FLOW,
      position: { x: 100, y: 200 },
      data: {
        name: 'Runoff Inflow',
        boundary_type: 'flow',
        value: 20.0,
        position: 'upstream',
        validated: true,
        errors: [],
        warnings: []
      }
    },
    {
      id: 'boundary-outfall',
      type: NodeType.BOUNDARY_DEPTH,
      position: { x: 400, y: 200 },
      data: {
        name: 'Outfall',
        boundary_type: 'depth',
        value: 0.5,
        position: 'downstream',
        validated: true,
        errors: [],
        warnings: []
      }
    },
    {
      id: 'weir-overflow',
      type: NodeType.WEIR,
      position: { x: 325, y: 150 },
      data: {
        name: 'Emergency Overflow',
        weir_type: 'sharp_crested',
        crest_elevation: 2.5,
        discharge_coeff: 1.8,
        width: 12,
        validated: true,
        errors: [],
        warnings: []
      }
    }
  ],
  edges: [
    {
      id: 'edge-1',
      source: 'boundary-runoff',
      target: 'canal-storm-drain',
      type: 'default',
      validated: true
    },
    {
      id: 'edge-2',
      source: 'canal-storm-drain',
      target: 'boundary-outfall',
      type: 'default',
      validated: true
    }
  ],
  learningObjectives: [
    {
      objective: 'Understand urban drainage system response to rainfall',
      objectiveCN: '理解城市排水系统对降雨的响应',
      outcome: 'Analyze runoff conveyance in storm drains'
    },
    {
      objective: 'Study capacity and overflow conditions',
      objectiveCN: '研究容量和溢流条件',
      outcome: 'Identify when system capacity is exceeded'
    },
    {
      objective: 'Learn about hydraulic design of drainage systems',
      objectiveCN: '学习排水系统的水力设计',
      outcome: 'Evaluate drainage system performance'
    }
  ],
  instructions: {
    en: 'This template represents an urban stormwater drainage channel receiving runoff from a rainfall event. The system includes an emergency overflow weir. Run the simulation to observe how the drainage system conveys stormwater and whether overflow occurs during peak flows.',
    cn: '此模板代表一个接收降雨事件径流的城市雨水排水渠道。系统包括紧急溢流堰。运行模拟以观察排水系统如何输送雨水，以及在峰值流量期间是否发生溢流。'
  },
  expectedResults: {
    en: 'The drainage channel will respond to the runoff hydrograph with rapidly rising water levels. If inflow exceeds channel capacity, you may observe overflow at the emergency weir. The simulation demonstrates the importance of adequate drainage system sizing.',
    cn: '排水渠道将响应径流过程线，水位迅速上升。如果入流超过渠道容量，您可能会观察到紧急堰处的溢流。该模拟展示了适当排水系统规模的重要性。'
  },
  references: [
    'ASCE (1992). Design and Construction of Urban Stormwater Management Systems',
    'Butler, D. & Davies, J.W. (2011). Urban Drainage'
  ]
};

/**
 * Complex River System Template
 * 复杂河流系统模型模板
 */
export const COMPLEX_RIVER_TEMPLATE: ModelTemplate = {
  metadata: {
    id: 'river-system-advanced',
    name: 'River System - Two Reaches',
    nameCN: '河流系统 - 双河段',
    description: 'Advanced river system with upstream and downstream reaches connected in series',
    descriptionCN: '具有串联连接的上下游河段的高级河流系统',
    category: 'river',
    difficulty: 'advanced',
    tags: ['river', 'advanced', 'multi-reach', 'complex'],
    author: 'HydroClaude Team',
    createdAt: '2025-01-12',
    updatedAt: '2025-01-12',
    version: '1.0.0',
    usageCount: 0,
    rating: 4.5
  },
  config: {
    domainLength: 3000,
    duration: 400,
    timeStep: 0.25,
    manning: 0.04,
    nCells: 200,
    initialConditions: 'Variable depth: 2-4m depending on reach',
    boundaryConditions: 'Constant inflow upstream, time-varying tributary inflow, downstream water level control'
  },
  nodes: [
    {
      id: 'canal-upstream-reach',
      type: NodeType.CANAL,
      position: { x: 200, y: 200 },
      data: {
        name: 'Upstream Reach',
        length: 1500,
        width: 80,
        slope: 0.001,
        manning_n: 0.038,
        n_cells: 100,
        validated: true,
        errors: [],
        warnings: []
      }
    },
    {
      id: 'canal-downstream-reach',
      type: NodeType.CANAL,
      position: { x: 400, y: 200 },
      data: {
        name: 'Downstream Reach',
        length: 1500,
        width: 100,
        slope: 0.0006,
        manning_n: 0.04,
        n_cells: 100,
        validated: true,
        errors: [],
        warnings: []
      }
    },
    {
      id: 'boundary-main-upstream',
      type: NodeType.BOUNDARY_FLOW,
      position: { x: 50, y: 200 },
      data: {
        name: 'Main River Inflow',
        boundary_type: 'flow',
        value: 150.0,
        position: 'upstream',
        validated: true,
        errors: [],
        warnings: []
      }
    },
    {
      id: 'boundary-tributary',
      type: NodeType.BOUNDARY_FLOW,
      position: { x: 300, y: 100 },
      data: {
        name: 'Tributary Inflow',
        boundary_type: 'flow',
        value: 75.0,
        position: 'upstream',
        validated: true,
        errors: [],
        warnings: []
      }
    },
    {
      id: 'boundary-downstream',
      type: NodeType.BOUNDARY_DEPTH,
      position: { x: 550, y: 200 },
      data: {
        name: 'Downstream Control',
        boundary_type: 'depth',
        value: 3.0,
        position: 'downstream',
        validated: true,
        errors: [],
        warnings: []
      }
    }
  ],
  edges: [
    {
      id: 'edge-main-upstream',
      source: 'boundary-main-upstream',
      target: 'canal-upstream-reach',
      type: 'default',
      validated: true
    },
    {
      id: 'edge-reach-connection',
      source: 'canal-upstream-reach',
      target: 'canal-downstream-reach',
      type: 'default',
      validated: true
    },
    {
      id: 'edge-tributary',
      source: 'boundary-tributary',
      target: 'canal-downstream-reach',
      type: 'default',
      validated: true
    },
    {
      id: 'edge-downstream',
      source: 'canal-downstream-reach',
      target: 'boundary-downstream',
      type: 'default',
      validated: true
    }
  ],
  learningObjectives: [
    {
      objective: 'Understand flow dynamics in multi-reach river systems',
      objectiveCN: '理解多河段河流系统中的流动动力学',
      outcome: 'Analyze flow transitions between different channel geometries'
    },
    {
      objective: 'Study tributary contributions to downstream flow',
      objectiveCN: '研究支流对下游流量的贡献',
      outcome: 'Quantify effects of lateral inflows on main channel'
    },
    {
      objective: 'Learn advanced river modeling with varying characteristics',
      objectiveCN: '学习具有不同特征的高级河流建模',
      outcome: 'Handle systems with varying slope, width, and roughness'
    }
  ],
  instructions: {
    en: 'This advanced template represents a river system with two reaches of different characteristics connected in series. The upstream reach is narrower and steeper, while the downstream reach is wider with gentler slope. A tributary provides additional inflow at the junction. Run the simulation to observe how flow characteristics change between reaches and how the tributary inflow affects downstream conditions.',
    cn: '此高级模板代表一个由两个具有不同特征的河段串联连接的河流系统。上游河段较窄且坡度较陡，而下游河段较宽且坡度较缓。支流在汇合处提供额外的入流。运行模拟以观察流动特征如何在河段之间变化，以及支流入流如何影响下游条件。'
  },
  expectedResults: {
    en: 'You will observe flow transitions as water moves from the steeper, narrower upstream reach to the wider, flatter downstream reach. The tributary inflow will increase discharge and modify water levels downstream of the junction. This demonstrates how rivers with varying geometry and multiple sources behave, which is common in natural river systems.',
    cn: '当水流从更陡、更窄的上游河段移动到更宽、更平坦的下游河段时，您将观察到流动转换。支流入流将增加流量并改变汇合点下游的水位。这展示了具有不同几何形状和多个源的河流如何表现，这在自然河流系统中很常见。'
  },
  references: [
    'Chaudhry, M.H. (2008). Open-Channel Flow (2nd Edition)',
    'Singh, V.P. (1996). Kinematic Wave Modeling in Water Resources: Surface-Water Hydrology',
    'USGS (2018). StreamStats: Streamflow Statistics and Spatial Analysis Tools'
  ]
};

export const TEMPLATES: ModelTemplate[] = [
  DAM_BREAK_TEMPLATE,
  RESERVOIR_TEMPLATE,
  CHANNEL_FLOW_TEMPLATE,
  RIVER_FLOOD_TEMPLATE,
  URBAN_DRAINAGE_TEMPLATE,
  COMPLEX_RIVER_TEMPLATE
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
