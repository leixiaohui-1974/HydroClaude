/**
 * Component Templates
 * 组件模板配置
 */

import { ComponentCategory, NodeType } from '../types/model.types';

/**
 * 组件库配置
 */
export const componentCategories: ComponentCategory[] = [
  {
    id: 'canal',
    name: '明渠',
    icon: '🌊',
    components: [
      {
        id: 'canal_rectangular',
        type: NodeType.CANAL,
        name: '矩形明渠',
        description: '矩形断面明渠,用于一般水流模拟',
        icon: '▭',
        defaultData: {
          name: '矩形明渠',
          width: 10.0,
          length: 1000.0,
          slope: 0.001,
          manning_n: 0.025,
          n_cells: 100,
          initial_depth: 5.0,
          initial_discharge: 0.0,
          validated: false,
          errors: [],
          warnings: []
        }
      },
      {
        id: 'canal_trapezoidal',
        type: NodeType.CANAL,
        name: '梯形明渠',
        description: '梯形断面明渠,常用于天然河道和灌溉渠道',
        icon: '⏢',
        defaultData: {
          name: '梯形明渠',
          width: 10.0,
          side_slope: 2.0,  // 边坡系数
          length: 1000.0,
          slope: 0.001,
          manning_n: 0.030,
          n_cells: 100,
          initial_depth: 5.0,
          initial_discharge: 0.0,
          validated: false,
          errors: [],
          warnings: []
        }
      },
      {
        id: 'canal_circular',
        type: NodeType.CANAL,
        name: '圆形渠道',
        description: '圆形断面渠道,常用于排水管道',
        icon: '⬤',
        defaultData: {
          name: '圆形渠道',
          diameter: 2.0,
          length: 500.0,
          slope: 0.002,
          manning_n: 0.013,
          n_cells: 50,
          initial_depth: 1.0,
          initial_discharge: 0.0,
          validated: false,
          errors: [],
          warnings: []
        }
      },
      {
        id: 'canal_compound',
        type: NodeType.CANAL,
        name: '复式断面',
        description: '复式断面渠道,适用于有滩地的河道',
        icon: '⛰',
        defaultData: {
          name: '复式断面',
          main_width: 20.0,
          floodplain_width: 50.0,
          bank_height: 5.0,
          length: 2000.0,
          slope: 0.0005,
          manning_n: 0.035,
          n_cells: 150,
          initial_depth: 3.0,
          initial_discharge: 0.0,
          validated: false,
          errors: [],
          warnings: []
        }
      }
    ]
  },
  {
    id: 'structures',
    name: '水工建筑物',
    icon: '🏗️',
    components: [
      {
        id: 'gate',
        type: NodeType.GATE,
        name: '闸门',
        description: '可调节开度的闸门',
        icon: '⫿',
        defaultData: {
          name: '闸门',
          opening: 0.5,
          discharge_coeff: 0.6,
          width: 10.0,
          validated: false,
          errors: [],
          warnings: []
        }
      },
      {
        id: 'weir',
        type: NodeType.WEIR,
        name: '堰',
        description: '固定堰顶的溢流堰',
        icon: '⏚',
        defaultData: {
          name: '堰',
          weir_type: 'broad_crested',
          discharge_coeff: 0.6,
          width: 10.0,
          crest_elevation: 5.0,
          validated: false,
          errors: [],
          warnings: []
        }
      },
      {
        id: 'pump',
        type: NodeType.GATE,  // 暂时使用GATE类型
        name: '泵站',
        description: '提升水位的泵站设施',
        icon: '⚙️',
        defaultData: {
          name: '泵站',
          flow_rate: 10.0,
          head: 15.0,
          num_pumps: 1,
          validated: false,
          errors: [],
          warnings: []
        }
      },
      {
        id: 'culvert',
        type: NodeType.GATE,
        name: '涵洞',
        description: '地下通道，用于水流穿越路基',
        icon: '🚇',
        defaultData: {
          name: '涵洞',
          diameter: 2.0,
          length: 50.0,
          inlet_coeff: 0.6,
          validated: false,
          errors: [],
          warnings: []
        }
      },
      {
        id: 'bridge',
        type: NodeType.GATE,
        name: '桥梁',
        description: '跨河桥梁，影响水流断面',
        icon: '🌉',
        defaultData: {
          name: '桥梁',
          span_width: 20.0,
          pier_width: 2.0,
          num_piers: 2,
          validated: false,
          errors: [],
          warnings: []
        }
      },
      {
        id: 'drop_structure',
        type: NodeType.WEIR,
        name: '跌水',
        description: '陡坡跌水结构，用于能量消散',
        icon: '🎢',
        defaultData: {
          name: '跌水',
          drop_height: 2.0,
          weir_type: 'broad_crested',
          discharge_coeff: 0.6,
          width: 10.0,
          crest_elevation: 5.0,
          validated: false,
          errors: [],
          warnings: []
        }
      }
    ]
  },
  {
    id: 'pipes',
    name: '管道系统',
    icon: '🚰',
    components: [
      {
        id: 'pipe',
        type: NodeType.CANAL,
        name: '管道',
        description: '压力管道，用于输水',
        icon: '━',
        defaultData: {
          name: '管道',
          diameter: 1.0,
          length: 500.0,
          roughness: 0.015,
          slope: 0.001,
          validated: false,
          errors: [],
          warnings: []
        }
      },
      {
        id: 'junction',
        type: NodeType.BOUNDARY_FLOW,
        name: '节点',
        description: '管网节点，连接多根管道',
        icon: '⊕',
        defaultData: {
          name: '节点',
          elevation: 100.0,
          boundary_type: 'flow',
          value: 0.0,
          position: 'upstream',
          validated: false,
          errors: [],
          warnings: []
        }
      },
      {
        id: 'valve',
        type: NodeType.GATE,
        name: '阀门',
        description: '管道阀门，控制流量',
        icon: '⊗',
        defaultData: {
          name: '阀门',
          opening: 1.0,
          discharge_coeff: 0.9,
          width: 1.0,
          validated: false,
          errors: [],
          warnings: []
        }
      }
    ]
  },
  {
    id: 'boundaries',
    name: '边界条件',
    icon: '🎯',
    components: [
      {
        id: 'boundary_flow',
        type: NodeType.BOUNDARY_FLOW,
        name: '流量边界',
        description: '指定流量的边界条件',
        icon: '➜',
        defaultData: {
          name: '流量边界',
          boundary_type: 'flow',
          value: 100.0,
          position: 'upstream',
          validated: false,
          errors: [],
          warnings: []
        }
      },
      {
        id: 'boundary_depth',
        type: NodeType.BOUNDARY_DEPTH,
        name: '水深边界',
        description: '指定水深的边界条件',
        icon: '⬍',
        defaultData: {
          name: '水深边界',
          boundary_type: 'depth',
          value: 5.0,
          position: 'downstream',
          validated: false,
          errors: [],
          warnings: []
        }
      }
    ]
  }
];

/**
 * 根据类型获取组件模板
 */
export const getComponentTemplate = (type: NodeType) => {
  for (const category of componentCategories) {
    const template = category.components.find(c => c.type === type);
    if (template) return template;
  }
  return null;
};

/**
 * 获取所有组件模板
 */
export const getAllComponentTemplates = () => {
  return componentCategories.flatMap(cat => cat.components);
};
