/**
 * 统一组件库 - Unified Component Library
 * 
 * 集成所有23种水工组件的完整定义
 * 对应后端HydraulicEngineV2的所有仿真方法
 * 
 * @author HydroClaude Team
 * @date 2025-11-17
 * @version 2.0.0
 */

import { NodeType } from '../types/model.types';

// ==================== 类型定义 ====================

export interface ComponentConfig {
  id: string;
  type: NodeType | string;
  name: string;
  nameCN: string;
  category: string;
  icon: string;
  description: string;
  apiEndpoint: string;  // 对应的后端API端点
  defaultData: Record<string, any>;
  requiredFields: string[];
  advancedFields?: string[];
}

export interface ComponentCategory {
  id: string;
  name: string;
  nameCN: string;
  icon: string;
  description: string;
  components: ComponentConfig[];
}

// ==================== 完整组件库（23种）====================

export const UNIFIED_COMPONENT_LIBRARY: ComponentCategory[] = [
  // ========== 第一部分：泵站系统（1种）==========
  {
    id: 'pump-system',
    name: 'Pump System',
    nameCN: '泵站系统',
    icon: '⚙️',
    description: 'Pump stations and pumping systems',
    components: [
      {
        id: 'pump-station',
        type: 'PUMP',
        name: 'Pump Station',
        nameCN: '泵站',
        category: 'pump-system',
        icon: '⚙️',
        description: '泵站系统，支持单泵、并联、串联运行',
        apiEndpoint: '/api/structures/pump',
        defaultData: {
          name: '泵站',
          flow_rate: 10.0,
          head: 15.0,
          num_pumps: 1,
          pump_type: 'single',  // single, parallel, series
          position: 500.0,
          upstream: { water_level: 5.0 },
          downstream: { elevation: 20.0 },
          operation: { duration: 3600.0 }
        },
        requiredFields: ['flow_rate', 'head', 'position'],
        advancedFields: ['num_pumps', 'pump_type', 'operation']
      }
    ]
  },

  // ========== 第二部分：闸门系统（5种）==========
  {
    id: 'gate-system',
    name: 'Gate System',
    nameCN: '闸门系统',
    icon: '⫿',
    description: 'Various types of hydraulic gates',
    components: [
      {
        id: 'sluice-gate',
        type: 'GATE',
        name: 'Sluice Gate',
        nameCN: '滑动闸门',
        category: 'gate-system',
        icon: '⫿',
        description: '滑动闸门，最常用的闸门类型',
        apiEndpoint: '/api/structures/gate',
        defaultData: {
          name: '滑动闸门',
          type: 'sluice',
          width: 10.0,
          opening: 2.0,
          discharge_coeff: 0.6,
          position: 500.0,
          upstream: { water_depth: 5.0 },
          downstream: { water_depth: 2.0 }
        },
        requiredFields: ['width', 'opening', 'position'],
        advancedFields: ['discharge_coeff']
      },
      {
        id: 'radial-gate',
        type: 'GATE',
        name: 'Radial Gate',
        nameCN: '径向闸门',
        category: 'gate-system',
        icon: '◗',
        description: '弧形径向闸门，大型水利枢纽常用',
        apiEndpoint: '/api/structures/radial-gate',
        defaultData: {
          name: '径向闸门',
          type: 'radial',
          width: 15.0,
          opening: 3.0,
          radius: 20.0,
          discharge_coeff: 0.65,
          position: 500.0,
          upstream: { water_depth: 8.0 },
          downstream: { water_depth: 3.0 }
        },
        requiredFields: ['width', 'opening', 'radius', 'position'],
        advancedFields: ['discharge_coeff']
      },
      {
        id: 'vertical-lift-gate',
        type: 'GATE',
        name: 'Vertical Lift Gate',
        nameCN: '垂直提升闸门',
        category: 'gate-system',
        icon: '⇅',
        description: '垂直升降闸门，适用于深水调节',
        apiEndpoint: '/api/structures/vertical-lift-gate',
        defaultData: {
          name: '垂直提升闸门',
          type: 'vertical_lift',
          width: 12.0,
          opening: 4.0,
          discharge_coeff: 0.62,
          position: 500.0,
          upstream: { water_depth: 10.0 },
          downstream: { water_depth: 4.0 }
        },
        requiredFields: ['width', 'opening', 'position'],
        advancedFields: ['discharge_coeff']
      },
      {
        id: 'roller-gate',
        type: 'GATE',
        name: 'Roller Gate',
        nameCN: '滚轮闸门',
        category: 'gate-system',
        icon: '⊚',
        description: '滚轮式闸门，启闭力小',
        apiEndpoint: '/api/structures/gate',
        defaultData: {
          name: '滚轮闸门',
          type: 'roller',
          width: 10.0,
          opening: 2.5,
          discharge_coeff: 0.6,
          position: 500.0,
          upstream: { water_depth: 6.0 },
          downstream: { water_depth: 2.5 }
        },
        requiredFields: ['width', 'opening', 'position'],
        advancedFields: ['discharge_coeff']
      },
      {
        id: 'flap-gate',
        type: 'GATE',
        name: 'Flap Gate',
        nameCN: '翻板闸门',
        category: 'gate-system',
        icon: '⊳',
        description: '自动翻板闸门，水位控制',
        apiEndpoint: '/api/structures/gate',
        defaultData: {
          name: '翻板闸门',
          type: 'flap',
          width: 8.0,
          opening: 1.5,
          pivot_height: 1.0,
          discharge_coeff: 0.55,
          position: 500.0,
          upstream: { water_depth: 4.0 },
          downstream: { water_depth: 1.5 }
        },
        requiredFields: ['width', 'opening', 'pivot_height', 'position'],
        advancedFields: ['discharge_coeff']
      }
    ]
  },

  // ========== 第三部分：堰系统（6种）==========
  {
    id: 'weir-system',
    name: 'Weir System',
    nameCN: '堰系统',
    icon: '⏚',
    description: 'Various types of weirs',
    components: [
      {
        id: 'broad-crested-weir',
        type: 'WEIR',
        name: 'Broad Crested Weir',
        nameCN: '宽顶堰',
        category: 'weir-system',
        icon: '⊐',
        description: '宽顶堰，常用于测流和调节',
        apiEndpoint: '/api/structures/broad-crested-weir',
        defaultData: {
          name: '宽顶堰',
          type: 'broad_crested',
          width: 10.0,
          crest_height: 1.0,
          discharge_coeff: 0.6,
          position: 500.0,
          upstream: { water_depth: 5.0 },
          downstream: { water_depth: 2.0 }
        },
        requiredFields: ['width', 'crest_height', 'position'],
        advancedFields: ['discharge_coeff']
      },
      {
        id: 'sharp-crested-weir',
        type: 'WEIR',
        name: 'Sharp Crested Weir',
        nameCN: '尖顶堰',
        category: 'weir-system',
        icon: '△',
        description: '尖顶薄壁堰，精确测流',
        apiEndpoint: '/api/structures/sharp-crested-weir',
        defaultData: {
          name: '尖顶堰',
          type: 'sharp_crested',
          width: 5.0,
          crest_height: 0.5,
          discharge_coeff: 0.62,
          position: 500.0,
          upstream: { water_depth: 3.0 },
          downstream: { water_depth: 1.0 }
        },
        requiredFields: ['width', 'crest_height', 'position'],
        advancedFields: ['discharge_coeff']
      },
      {
        id: 'v-notch-weir',
        type: 'WEIR',
        name: 'V-Notch Weir',
        nameCN: 'V型槽堰',
        category: 'weir-system',
        icon: '∨',
        description: 'V型槽堰，小流量测量',
        apiEndpoint: '/api/structures/v-notch-weir',
        defaultData: {
          name: 'V型槽堰',
          type: 'v_notch',
          notch_angle: 90.0,
          crest_height: 0.5,
          discharge_coeff: 0.58,
          position: 500.0,
          upstream: { water_depth: 2.0 },
          downstream: { water_depth: 0.5 }
        },
        requiredFields: ['notch_angle', 'crest_height', 'position'],
        advancedFields: ['discharge_coeff']
      },
      {
        id: 'rectangular-weir',
        type: 'WEIR',
        name: 'Rectangular Weir',
        nameCN: '矩形堰',
        category: 'weir-system',
        icon: '▭',
        description: '矩形堰，通用测流设施',
        apiEndpoint: '/api/structures/weir',
        defaultData: {
          name: '矩形堰',
          type: 'rectangular',
          width: 8.0,
          crest_height: 1.0,
          discharge_coeff: 0.6,
          position: 500.0,
          upstream: { water_depth: 4.0 },
          downstream: { water_depth: 1.5 }
        },
        requiredFields: ['width', 'crest_height', 'position'],
        advancedFields: ['discharge_coeff']
      },
      {
        id: 'trapezoidal-weir',
        type: 'WEIR',
        name: 'Trapezoidal Weir',
        nameCN: '梯形堰',
        category: 'weir-system',
        icon: '⏢',
        description: '梯形堰，Cipolletti堰',
        apiEndpoint: '/api/structures/weir',
        defaultData: {
          name: '梯形堰',
          type: 'trapezoidal',
          width: 6.0,
          side_slope: 0.25,
          crest_height: 0.8,
          discharge_coeff: 0.63,
          position: 500.0,
          upstream: { water_depth: 3.5 },
          downstream: { water_depth: 1.2 }
        },
        requiredFields: ['width', 'side_slope', 'crest_height', 'position'],
        advancedFields: ['discharge_coeff']
      },
      {
        id: 'ogee-weir',
        type: 'WEIR',
        name: 'Ogee Weir',
        nameCN: '实用堰',
        category: 'weir-system',
        icon: '◠',
        description: '实用堰，大坝溢洪道',
        apiEndpoint: '/api/structures/weir',
        defaultData: {
          name: '实用堰',
          type: 'ogee',
          width: 20.0,
          crest_height: 2.0,
          discharge_coeff: 0.75,
          position: 500.0,
          upstream: { water_depth: 10.0 },
          downstream: { water_depth: 3.0 }
        },
        requiredFields: ['width', 'crest_height', 'position'],
        advancedFields: ['discharge_coeff']
      }
    ]
  },

  // ========== 第四部分：高级水电组件（4种）⭐ ==========
  {
    id: 'hydropower-system',
    name: 'Hydropower System',
    nameCN: '水电系统',
    icon: '⚡',
    description: 'Advanced hydropower components',
    components: [
      {
        id: 'turbine',
        type: 'TURBINE',
        name: 'Turbine',
        nameCN: '水轮机',
        category: 'hydropower-system',
        icon: '⚡',
        description: '水轮机，水电站核心设备',
        apiEndpoint: '/api/structures/turbine',
        defaultData: {
          name: '水轮机',
          type: 'francis',  // francis, kaplan, pelton
          rated_power: 50.0,  // MW
          rated_head: 100.0,  // m
          rated_flow: 60.0,   // m³/s
          position: 500.0,
          operation: {
            head: 100.0,
            flow: 60.0
          }
        },
        requiredFields: ['type', 'rated_power', 'rated_head', 'rated_flow', 'position'],
        advancedFields: ['operation']
      },
      {
        id: 'valve',
        type: 'VALVE',
        name: 'Valve',
        nameCN: '阀门',
        category: 'hydropower-system',
        icon: '⊗',
        description: '阀门，流量控制设备',
        apiEndpoint: '/api/structures/valve',
        defaultData: {
          name: '阀门',
          type: 'butterfly',  // butterfly, ball, gate, globe
          diameter: 1.0,
          opening_percent: 80.0,
          position: 500.0,
          operation: {
            pressure_drop: 100.0  // kPa
          }
        },
        requiredFields: ['type', 'diameter', 'opening_percent', 'position'],
        advancedFields: ['operation']
      },
      {
        id: 'surge-tank',
        type: 'SURGE_TANK',
        name: 'Surge Tank',
        nameCN: '调压井',
        category: 'hydropower-system',
        icon: '⊙',
        description: '调压井，水锤防护设施',
        apiEndpoint: '/api/structures/surge-tank',
        defaultData: {
          name: '调压井',
          type: 'simple',  // simple, throttled, differential
          diameter: 5.0,
          height: 20.0,
          bottom_elevation: 100.0,
          position: 500.0,
          initial_conditions: {
            water_level: 110.0
          }
        },
        requiredFields: ['type', 'diameter', 'height', 'position'],
        advancedFields: ['bottom_elevation', 'initial_conditions']
      },
      {
        id: 'hydropower-station',
        type: 'HYDROPOWER_STATION',
        name: 'Hydropower Station',
        nameCN: '水电站系统',
        category: 'hydropower-system',
        icon: '🏭',
        description: '完整的水电站系统，集成多种设备',
        apiEndpoint: '/api/structures/hydropower-station',
        defaultData: {
          name: '水电站',
          num_units: 2,
          unit_capacity: 50.0,  // MW
          design_head: 100.0,
          design_flow: 120.0,
          position: 500.0,
          components: {
            turbines: 2,
            valves: 2,
            surge_tank: true
          }
        },
        requiredFields: ['num_units', 'unit_capacity', 'design_head', 'position'],
        advancedFields: ['components']
      }
    ]
  },

  // ========== 第五部分：明渠系统（4种）==========
  {
    id: 'canal-system',
    name: 'Canal System',
    nameCN: '明渠系统',
    icon: '🌊',
    description: 'Open channel flow',
    components: [
      {
        id: 'rectangular-canal',
        type: 'CANAL',
        name: 'Rectangular Canal',
        nameCN: '矩形明渠',
        category: 'canal-system',
        icon: '▭',
        description: '矩形断面明渠',
        apiEndpoint: '/api/structures/canal',
        defaultData: {
          name: '矩形明渠',
          width: 10.0,
          length: 1000.0,
          slope: 0.001,
          manning_n: 0.025,
          n_cells: 100,
          initial_depth: 5.0
        },
        requiredFields: ['width', 'length', 'slope'],
        advancedFields: ['manning_n', 'n_cells']
      },
      {
        id: 'trapezoidal-canal',
        type: 'CANAL',
        name: 'Trapezoidal Canal',
        nameCN: '梯形明渠',
        category: 'canal-system',
        icon: '⏢',
        description: '梯形断面明渠',
        apiEndpoint: '/api/structures/canal',
        defaultData: {
          name: '梯形明渠',
          width: 10.0,
          side_slope: 2.0,
          length: 1000.0,
          slope: 0.001,
          manning_n: 0.030,
          n_cells: 100,
          initial_depth: 5.0
        },
        requiredFields: ['width', 'side_slope', 'length', 'slope'],
        advancedFields: ['manning_n', 'n_cells']
      },
      {
        id: 'circular-canal',
        type: 'CANAL',
        name: 'Circular Canal',
        nameCN: '圆形渠道',
        category: 'canal-system',
        icon: '⬤',
        description: '圆形断面渠道',
        apiEndpoint: '/api/structures/canal',
        defaultData: {
          name: '圆形渠道',
          diameter: 2.0,
          length: 500.0,
          slope: 0.002,
          manning_n: 0.013,
          n_cells: 50,
          initial_depth: 1.0
        },
        requiredFields: ['diameter', 'length', 'slope'],
        advancedFields: ['manning_n', 'n_cells']
      },
      {
        id: 'compound-canal',
        type: 'CANAL',
        name: 'Compound Canal',
        nameCN: '复式断面',
        category: 'canal-system',
        icon: '⛰',
        description: '复式断面渠道',
        apiEndpoint: '/api/structures/canal',
        defaultData: {
          name: '复式断面',
          main_width: 20.0,
          floodplain_width: 50.0,
          bank_height: 5.0,
          length: 2000.0,
          slope: 0.0005,
          manning_n: 0.035,
          n_cells: 150,
          initial_depth: 3.0
        },
        requiredFields: ['main_width', 'floodplain_width', 'length', 'slope'],
        advancedFields: ['manning_n', 'n_cells', 'bank_height']
      }
    ]
  },

  // ========== 第六部分：扩展结构（4种）==========
  {
    id: 'extended-structures',
    name: 'Extended Structures',
    nameCN: '扩展结构',
    icon: '🏗️',
    description: 'Additional hydraulic structures',
    components: [
      {
        id: 'culvert',
        type: 'CULVERT',
        name: 'Culvert',
        nameCN: '涵洞',
        category: 'extended-structures',
        icon: '🚇',
        description: '涵洞，地下通道',
        apiEndpoint: '/api/structures/culvert',
        defaultData: {
          name: '涵洞',
          diameter: 2.0,
          length: 50.0,
          position: 500.0,
          upstream: { water_depth: 3.0 },
          downstream: { water_depth: 1.0 }
        },
        requiredFields: ['diameter', 'length', 'position'],
        advancedFields: []
      },
      {
        id: 'bridge',
        type: 'BRIDGE',
        name: 'Bridge',
        nameCN: '桥梁',
        category: 'extended-structures',
        icon: '🌉',
        description: '桥梁，壅水分析',
        apiEndpoint: '/api/structures/bridge',
        defaultData: {
          name: '桥梁',
          span_width: 20.0,
          pier_width: 2.0,
          num_piers: 2,
          position: 500.0,
          flow: { discharge: 100.0 },
          upstream: { water_depth: 5.0 }
        },
        requiredFields: ['span_width', 'pier_width', 'num_piers', 'position'],
        advancedFields: ['flow']
      },
      {
        id: 'reservoir',
        type: 'RESERVOIR',
        name: 'Reservoir',
        nameCN: '水库',
        category: 'extended-structures',
        icon: '⛲',
        description: '水库，蓄水调节',
        apiEndpoint: '/api/structures/reservoir',
        defaultData: {
          name: '水库',
          capacity: 1000000.0,  // m³
          initial_level: 100.0,
          min_level: 90.0,
          max_level: 110.0,
          position: 500.0
        },
        requiredFields: ['capacity', 'initial_level', 'position'],
        advancedFields: ['min_level', 'max_level']
      },
      {
        id: 'pipe',
        type: 'PIPE',
        name: 'Pipe',
        nameCN: '管道',
        category: 'extended-structures',
        icon: '━',
        description: '管道，压力输水',
        apiEndpoint: '/api/structures/pipe',
        defaultData: {
          name: '管道',
          diameter: 1.0,
          length: 500.0,
          roughness: 0.015,
          slope: 0.001,
          position: 0.0
        },
        requiredFields: ['diameter', 'length', 'position'],
        advancedFields: ['roughness', 'slope']
      }
    ]
  }
];

// ==================== 辅助函数 ====================

/**
 * 获取所有组件配置（扁平化）
 */
export const getAllComponents = (): ComponentConfig[] => {
  return UNIFIED_COMPONENT_LIBRARY.flatMap(cat => cat.components);
};

/**
 * 根据ID获取组件配置
 */
export const getComponentById = (id: string): ComponentConfig | undefined => {
  return getAllComponents().find(comp => comp.id === id);
};

/**
 * 根据类别获取组件列表
 */
export const getComponentsByCategory = (categoryId: string): ComponentConfig[] => {
  const category = UNIFIED_COMPONENT_LIBRARY.find(cat => cat.id === categoryId);
  return category ? category.components : [];
};

/**
 * 获取组件统计信息
 */
export const getComponentStats = () => {
  const allComponents = getAllComponents();
  return {
    totalComponents: allComponents.length,
    totalCategories: UNIFIED_COMPONENT_LIBRARY.length,
    byCategory: UNIFIED_COMPONENT_LIBRARY.map(cat => ({
      id: cat.id,
      name: cat.nameCN,
      count: cat.components.length
    })),
    apiEndpoints: [...new Set(allComponents.map(c => c.apiEndpoint))]
  };
};

/**
 * 验证组件配置的必填字段
 */
export const validateComponentConfig = (
  componentId: string,
  config: Record<string, any>
): { isValid: boolean; missingFields: string[] } => {
  const component = getComponentById(componentId);
  if (!component) {
    return { isValid: false, missingFields: ['Invalid component ID'] };
  }

  const missingFields = component.requiredFields.filter(
    field => config[field] === undefined || config[field] === null
  );

  return {
    isValid: missingFields.length === 0,
    missingFields
  };
};

/**
 * 获取API端点列表（用于端到端测试）
 */
export const getAllApiEndpoints = (): string[] => {
  return [...new Set(getAllComponents().map(c => c.apiEndpoint))];
};

// ==================== 导出统计信息 ====================

export const COMPONENT_LIBRARY_INFO = {
  version: '2.0.0',
  lastUpdated: '2025-11-17',
  totalComponents: 23,
  categories: 6,
  description: '完整的水工组件库，对应后端HydraulicEngineV2的所有仿真方法'
};
