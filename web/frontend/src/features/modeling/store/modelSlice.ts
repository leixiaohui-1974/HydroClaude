/**
 * Model Slice - Redux Toolkit
 * 建模工作台状态管理
 */

import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { nanoid } from '@reduxjs/toolkit';
import {
  ModelingState,
  HydraulicModel,
  ModelNode,
  ModelEdge,
  NodeType,
  AddNodePayload,
  UpdateNodePayload,
  AddEdgePayload,
  ImportModelPayload,
  ValidationResult,
  CanalNodeData,
  GateNodeData,
  BoundaryNodeData,
  NodeData
} from '../types/model.types';

// ============= 初始状态 =============

const initialState: ModelingState = {
  currentModel: null,
  selectedNodeIds: [],
  selectedEdgeIds: [],
  history: {
    past: [],
    present: null,
    future: []
  },
  ui: {
    showComponentPalette: true,
    showPropertyPanel: true,
    showValidationPanel: false,
    zoom: 1.0,
    gridEnabled: true,
    snapToGrid: true
  },
  validation: {
    isValidating: false,
    lastValidation: undefined
  },
  io: {
    isImporting: false,
    isExporting: false,
    error: undefined
  }
};

// ============= 辅助函数 =============

/**
 * 创建空模型
 */
const createEmptyModel = (): HydraulicModel => ({
  id: nanoid(),
  name: '未命名模型',
  description: '',
  nodes: [],
  edges: [],
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  version: 1,
  validated: false
});

/**
 * 创建默认节点数据
 */
const createDefaultNodeData = (type: NodeType): NodeData => {
  const baseData = {
    validated: false,
    errors: [],
    warnings: []
  };

  switch (type) {
    case NodeType.CANAL:
      return {
        name: `明渠_${nanoid(6)}`,
        width: 10.0,
        length: 1000.0,
        slope: 0.001,
        manning_n: 0.025,
        n_cells: 100,
        initial_depth: 5.0,
        initial_discharge: 0.0,
        ...baseData
      } as CanalNodeData;

    case NodeType.GATE:
      return {
        name: `闸门_${nanoid(6)}`,
        opening: 0.5,
        discharge_coeff: 0.6,
        width: 10.0,
        ...baseData
      } as GateNodeData;

    case NodeType.BOUNDARY_FLOW:
      return {
        name: `流量边界_${nanoid(6)}`,
        boundary_type: 'flow',
        value: 100.0,
        position: 'upstream',
        ...baseData
      } as BoundaryNodeData;

    case NodeType.BOUNDARY_DEPTH:
      return {
        name: `水深边界_${nanoid(6)}`,
        boundary_type: 'depth',
        value: 5.0,
        position: 'downstream',
        ...baseData
      } as BoundaryNodeData;

    default:
      throw new Error(`Unknown node type: ${type}`);
  }
};

// ============= Slice =============

const modelSlice = createSlice({
  name: 'model',
  initialState,
  reducers: {
    // === 模型管理 ===

    /**
     * 创建新模型
     */
    createNewModel: (state, action: PayloadAction<{ name?: string; description?: string }>) => {
      const newModel = createEmptyModel();
      if (action.payload.name) {
        newModel.name = action.payload.name;
      }
      if (action.payload.description) {
        newModel.description = action.payload.description;
      }

      // 保存到历史记录
      if (state.currentModel) {
        state.history.past.push(state.currentModel);
      }

      state.currentModel = newModel;
      state.history.present = newModel;
      state.history.future = [];
      state.selectedNodeIds = [];
      state.selectedEdgeIds = [];
    },

    /**
     * 更新模型信息
     */
    updateModelInfo: (state, action: PayloadAction<{ name?: string; description?: string }>) => {
      if (!state.currentModel) return;

      if (action.payload.name !== undefined) {
        state.currentModel.name = action.payload.name;
      }
      if (action.payload.description !== undefined) {
        state.currentModel.description = action.payload.description;
      }
      state.currentModel.updated_at = new Date().toISOString();
    },

    // === 节点操作 ===

    /**
     * 添加节点
     */
    addNode: (state, action: PayloadAction<AddNodePayload>) => {
      if (!state.currentModel) {
        state.currentModel = createEmptyModel();
      }

      const { type, position, data } = action.payload;

      const newNode: ModelNode = {
        id: nanoid(),
        type,
        position,
        data: {
          ...createDefaultNodeData(type),
          ...data
        }
      };

      state.currentModel.nodes.push(newNode);
      state.currentModel.updated_at = new Date().toISOString();
      state.currentModel.validated = false;

      // 自动选中新添加的节点
      state.selectedNodeIds = [newNode.id];
    },

    /**
     * 更新节点数据
     */
    updateNode: (state, action: PayloadAction<UpdateNodePayload>) => {
      if (!state.currentModel) return;

      const { id, data } = action.payload;
      const node = state.currentModel.nodes.find(n => n.id === id);

      if (node) {
        node.data = {
          ...node.data,
          ...data
        };
        state.currentModel.updated_at = new Date().toISOString();
        state.currentModel.validated = false;
      }
    },

    /**
     * 更新节点位置
     */
    updateNodePosition: (state, action: PayloadAction<{ id: string; position: { x: number; y: number } }>) => {
      if (!state.currentModel) return;

      const { id, position } = action.payload;
      const node = state.currentModel.nodes.find(n => n.id === id);

      if (node) {
        node.position = position;
        state.currentModel.updated_at = new Date().toISOString();
      }
    },

    /**
     * 删除节点
     */
    deleteNode: (state, action: PayloadAction<string>) => {
      if (!state.currentModel) return;

      const nodeId = action.payload;

      // 删除节点
      state.currentModel.nodes = state.currentModel.nodes.filter(n => n.id !== nodeId);

      // 删除相关的边
      state.currentModel.edges = state.currentModel.edges.filter(
        e => e.source !== nodeId && e.target !== nodeId
      );

      // 清除选中状态
      state.selectedNodeIds = state.selectedNodeIds.filter(id => id !== nodeId);

      state.currentModel.updated_at = new Date().toISOString();
      state.currentModel.validated = false;
    },

    /**
     * 删除多个节点
     */
    deleteNodes: (state, action: PayloadAction<string[]>) => {
      if (!state.currentModel) return;

      const nodeIds = action.payload;

      // 删除节点
      state.currentModel.nodes = state.currentModel.nodes.filter(
        n => !nodeIds.includes(n.id)
      );

      // 删除相关的边
      state.currentModel.edges = state.currentModel.edges.filter(
        e => !nodeIds.includes(e.source) && !nodeIds.includes(e.target)
      );

      // 清除选中状态
      state.selectedNodeIds = state.selectedNodeIds.filter(id => !nodeIds.includes(id));

      state.currentModel.updated_at = new Date().toISOString();
      state.currentModel.validated = false;
    },

    // === 边操作 ===

    /**
     * 添加边
     */
    addEdge: (state, action: PayloadAction<AddEdgePayload>) => {
      if (!state.currentModel) return;

      const { source, target } = action.payload;

      // 检查是否已存在
      const exists = state.currentModel.edges.some(
        e => e.source === source && e.target === target
      );

      if (!exists) {
        const newEdge: ModelEdge = {
          id: `e_${source}_${target}`,
          source,
          target,
          type: 'smoothstep',
          validated: false
        };

        state.currentModel.edges.push(newEdge);
        state.currentModel.updated_at = new Date().toISOString();
        state.currentModel.validated = false;
      }
    },

    /**
     * 删除边
     */
    deleteEdge: (state, action: PayloadAction<string>) => {
      if (!state.currentModel) return;

      const edgeId = action.payload;
      state.currentModel.edges = state.currentModel.edges.filter(e => e.id !== edgeId);
      state.selectedEdgeIds = state.selectedEdgeIds.filter(id => id !== edgeId);

      state.currentModel.updated_at = new Date().toISOString();
      state.currentModel.validated = false;
    },

    // === 选中状态 ===

    /**
     * 设置选中的节点
     */
    setSelectedNodes: (state, action: PayloadAction<string[]>) => {
      state.selectedNodeIds = action.payload;
    },

    /**
     * 设置选中的边
     */
    setSelectedEdges: (state, action: PayloadAction<string[]>) => {
      state.selectedEdgeIds = action.payload;
    },

    /**
     * 清除所有选中
     */
    clearSelection: (state) => {
      state.selectedNodeIds = [];
      state.selectedEdgeIds = [];
    },

    // === 验证 ===

    /**
     * 开始验证
     */
    startValidation: (state) => {
      state.validation.isValidating = true;
    },

    /**
     * 完成验证
     */
    completeValidation: (state, action: PayloadAction<ValidationResult>) => {
      state.validation.isValidating = false;
      state.validation.lastValidation = action.payload;

      if (state.currentModel) {
        state.currentModel.validated = action.payload.valid;
        state.currentModel.validation_result = action.payload;
      }
    },

    // === UI状态 ===

    /**
     * 切换组件面板显示
     */
    toggleComponentPalette: (state) => {
      state.ui.showComponentPalette = !state.ui.showComponentPalette;
    },

    /**
     * 切换属性面板显示
     */
    togglePropertyPanel: (state) => {
      state.ui.showPropertyPanel = !state.ui.showPropertyPanel;
    },

    /**
     * 切换验证面板显示
     */
    toggleValidationPanel: (state) => {
      state.ui.showValidationPanel = !state.ui.showValidationPanel;
    },

    /**
     * 设置缩放
     */
    setZoom: (state, action: PayloadAction<number>) => {
      state.ui.zoom = action.payload;
    },

    /**
     * 切换网格显示
     */
    toggleGrid: (state) => {
      state.ui.gridEnabled = !state.ui.gridEnabled;
    },

    /**
     * 切换网格吸附
     */
    toggleSnapToGrid: (state) => {
      state.ui.snapToGrid = !state.ui.snapToGrid;
    },

    // === 导入导出 ===

    /**
     * 导入模型
     */
    importModel: (state, action: PayloadAction<ImportModelPayload>) => {
      const { model, replace = true } = action.payload;

      if (replace) {
        // 替换当前模型
        if (state.currentModel) {
          state.history.past.push(state.currentModel);
        }
        state.currentModel = model;
        state.history.present = model;
        state.history.future = [];
      } else {
        // 合并到当前模型
        if (state.currentModel) {
          state.currentModel.nodes.push(...model.nodes);
          state.currentModel.edges.push(...model.edges);
          state.currentModel.updated_at = new Date().toISOString();
        } else {
          state.currentModel = model;
        }
      }

      state.selectedNodeIds = [];
      state.selectedEdgeIds = [];
    },

    /**
     * 设置导入导出错误
     */
    setIOError: (state, action: PayloadAction<string | undefined>) => {
      state.io.error = action.payload;
    },

    // === 历史记录 (Undo/Redo) ===

    /**
     * 撤销
     */
    undo: (state) => {
      if (state.history.past.length === 0) return;

      const previous = state.history.past[state.history.past.length - 1];
      const newPast = state.history.past.slice(0, state.history.past.length - 1);

      if (state.currentModel) {
        state.history.future = [state.currentModel, ...state.history.future];
      }

      state.history.past = newPast;
      state.history.present = previous;
      state.currentModel = previous;
    },

    /**
     * 重做
     */
    redo: (state) => {
      if (state.history.future.length === 0) return;

      const next = state.history.future[0];
      const newFuture = state.history.future.slice(1);

      if (state.currentModel) {
        state.history.past = [...state.history.past, state.currentModel];
      }

      state.history.future = newFuture;
      state.history.present = next;
      state.currentModel = next;
    },

    /**
     * 保存快照 (用于创建历史记录点)
     */
    saveSnapshot: (state) => {
      if (!state.currentModel) return;

      // 深拷贝当前模型
      const snapshot = JSON.parse(JSON.stringify(state.currentModel)) as HydraulicModel;

      state.history.past.push(snapshot);
      state.history.future = [];

      // 限制历史记录长度
      if (state.history.past.length > 50) {
        state.history.past = state.history.past.slice(-50);
      }
    }
  }
});

// ============= 导出 =============

export const {
  createNewModel,
  updateModelInfo,
  addNode,
  updateNode,
  updateNodePosition,
  deleteNode,
  deleteNodes,
  addEdge,
  deleteEdge,
  setSelectedNodes,
  setSelectedEdges,
  clearSelection,
  startValidation,
  completeValidation,
  toggleComponentPalette,
  togglePropertyPanel,
  toggleValidationPanel,
  setZoom,
  toggleGrid,
  toggleSnapToGrid,
  importModel,
  setIOError,
  undo,
  redo,
  saveSnapshot
} = modelSlice.actions;

export default modelSlice.reducer;
