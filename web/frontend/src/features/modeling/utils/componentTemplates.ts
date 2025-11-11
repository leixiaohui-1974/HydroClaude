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
