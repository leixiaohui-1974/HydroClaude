/**
 * Modeling Workspace Type Definitions
 * 建模工作台类型定义
 */

import { Node } from 'reactflow';

// ============= 节点类型枚举 =============

/**
 * 支持的节点类型
 */
export enum NodeType {
  CANAL = 'canal',                   // 明渠
  GATE = 'gate',                     // 闸门
  WEIR = 'weir',                     // 堰
  BOUNDARY_FLOW = 'boundary_flow',   // 流量边界
  BOUNDARY_DEPTH = 'boundary_depth'  // 水深边界
}

// ============= 节点数据接口 =============

/**
 * 明渠节点数据
 */
export interface CanalNodeData {
  name: string;                      // 名称
  width: number;                     // 宽度 (m)
  length: number;                    // 长度 (m)
  slope: number;                     // 坡度 (无量纲)
  manning_n: number;                 // 曼宁系数
  n_cells: number;                   // 网格数

  // 初始条件
  initial_depth?: number;            // 初始水深 (m)
  initial_discharge?: number;        // 初始流量 (m³/s)

  // 验证状态
  validated: boolean;                // 是否已验证
  errors: string[];                  // 错误信息列表
  warnings: string[];                // 警告信息列表
}

/**
 * 闸门节点数据
 */
export interface GateNodeData {
  name: string;                      // 名称
  opening: number;                   // 开度 (0-1)
  discharge_coeff: number;           // 流量系数
  width: number;                     // 闸门宽度 (m)
  crest_height?: number;             // 堰顶高程 (m, 可选)

  validated: boolean;
  errors: string[];
  warnings: string[];
}

/**
 * 堰节点数据
 */
export interface WeirNodeData {
  name: string;                      // 名称
  weir_type: 'broad_crested' | 'sharp_crested';  // 堰型
  discharge_coeff: number;           // 流量系数
  width: number;                     // 堰宽 (m)
  crest_elevation: number;           // 堰顶高程 (m)

  validated: boolean;
  errors: string[];
  warnings: string[];
}

/**
 * 边界条件节点数据
 */
export interface BoundaryNodeData {
  name: string;                      // 名称
  boundary_type: 'flow' | 'depth';   // 边界类型
  value: number;                     // 边界值

  // 时间序列 (可选)
  time_series?: Array<{
    t: number;                       // 时间 (s)
    value: number;                   // 值
  }>;

  // 位置信息
  position: 'upstream' | 'downstream';  // 上游/下游

  validated: boolean;
  errors: string[];
  warnings: string[];
}

/**
 * 节点数据联合类型
 */
export type NodeData =
  | CanalNodeData
  | GateNodeData
  | WeirNodeData
  | BoundaryNodeData;

// ============= React Flow 节点和边 =============

/**
 * 模型节点 (扩展React Flow Node)
 */
export interface ModelNode extends Node {
  type: NodeType;
  data: NodeData;
}

/**
 * 模型边 (React Flow Edge with extensions)
 */
export interface ModelEdge {
  id: string;
  source: string;
  target: string;
  type?: string;
  animated?: boolean;
  style?: React.CSSProperties;
  validated: boolean;                // 验证状态
  flow_direction?: 'forward' | 'reverse';  // 流动方向
}

// ============= 验证相关 =============

/**
 * 验证错误级别
 */
export enum ValidationSeverity {
  ERROR = 'error',
  WARNING = 'warning',
  INFO = 'info'
}

/**
 * 验证错误类型
 */
export enum ValidationErrorType {
  TOPOLOGY = 'topology',             // 拓扑错误
  PARAMETER = 'parameter',           // 参数错误
  PHYSICS = 'physics',               // 物理一致性错误
  BOUNDARY = 'boundary'              // 边界条件错误
}

/**
 * 验证错误
 */
export interface ValidationError {
  id: string;                        // 错误ID
  type: ValidationErrorType;         // 错误类型
  severity: ValidationSeverity;      // 严重程度
  node_id?: string;                  // 相关节点ID
  edge_id?: string;                  // 相关边ID
  message: string;                   // 错误消息
  suggestion?: string;               // 修复建议
}

/**
 * 验证结果
 */
export interface ValidationResult {
  valid: boolean;                    // 是否有效
  errors: ValidationError[];         // 错误列表
  timestamp: string;                 // 验证时间
}

// ============= 完整模型 =============

/**
 * 水力学模型
 */
export interface HydraulicModel {
  id: string;                        // 模型ID
  name: string;                      // 模型名称
  description: string;               // 描述

  // 图形结构
  nodes: ModelNode[];                // 节点列表
  edges: ModelEdge[];                // 边列表

  // 元数据
  created_at: string;                // 创建时间
  updated_at: string;                // 更新时间
  version: number;                   // 版本号

  // 验证状态
  validated: boolean;                // 是否已验证
  validation_result?: ValidationResult;  // 验证结果

  // 可选配置
  metadata?: Record<string, any>;    // 额外元数据
}

// ============= 组件面板 =============

/**
 * 组件类别
 */
export interface ComponentCategory {
  id: string;                        // 类别ID
  name: string;                      // 类别名称
  icon: string;                      // 图标
  components: ComponentTemplate[];   // 组件列表
}

/**
 * 组件模板
 */
export interface ComponentTemplate {
  id: string;                        // 模板ID
  type: NodeType;                    // 节点类型
  name: string;                      // 显示名称
  description: string;               // 描述
  icon: string;                      // 图标
  defaultData: Partial<NodeData>;    // 默认数据
}

// ============= 配置转换 =============

/**
 * 仿真配置 (用于转换为API请求)
 */
export interface SimulationConfig {
  model_id: string;                  // 模型ID
  model_name: string;                // 模型名称

  // 渠道配置 (从节点提取)
  width: number;
  length: number;
  n_cells: number;
  manning_n: number;
  slope: number;

  // 时间配置
  t_end: number;
  dt_max?: number;
  output_interval?: number;

  // 初始条件
  initial_conditions: {
    type: 'uniform' | 'dam_break';
    h_initial?: number;
    Q_initial?: number;
    // dam_break specific
    h_left?: number;
    h_right?: number;
    dam_position?: number;
  };

  // 边界条件
  boundary_conditions?: {
    upstream?: {
      type: 'flow' | 'depth';
      value: number;
    };
    downstream?: {
      type: 'flow' | 'depth';
      value: number;
    };
  };

  // 求解器配置
  solver_config?: {
    cfl?: number;
    order?: number;
    use_numba?: boolean;
  };
}

// ============= Redux State =============

/**
 * 建模工作台状态
 */
export interface ModelingState {
  // 当前模型
  currentModel: HydraulicModel | null;

  // 选中状态
  selectedNodeIds: string[];
  selectedEdgeIds: string[];

  // 历史记录 (用于Undo/Redo)
  history: {
    past: HydraulicModel[];
    present: HydraulicModel | null;
    future: HydraulicModel[];
  };

  // UI状态
  ui: {
    showComponentPalette: boolean;
    showPropertyPanel: boolean;
    showValidationPanel: boolean;
    zoom: number;
    gridEnabled: boolean;
    snapToGrid: boolean;
  };

  // 验证状态
  validation: {
    isValidating: boolean;
    lastValidation?: ValidationResult;
  };

  // 导入导出状态
  io: {
    isImporting: boolean;
    isExporting: boolean;
    error?: string;
  };
}

// ============= Action Payloads =============

/**
 * 添加节点Payload
 */
export interface AddNodePayload {
  type: NodeType;
  position: { x: number; y: number };
  data?: Partial<NodeData>;
}

/**
 * 更新节点Payload
 */
export interface UpdateNodePayload {
  id: string;
  data: Partial<NodeData>;
}

/**
 * 添加边Payload
 */
export interface AddEdgePayload {
  source: string;
  target: string;
}

/**
 * 导入模型Payload
 */
export interface ImportModelPayload {
  model: HydraulicModel;
  replace?: boolean;  // 是否替换当前模型
}
