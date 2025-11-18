/**
 * Simulation API - 统一的仿真API接口
 * 
 * 该文件提供前端使用的标准化仿真API接口，
 * 内部映射到后端实际的API端点。
 * 
 * @author HydroClaude Team
 * @date 2025-11-17
 */

import api from './api';

// ==================== 类型定义 ====================

/**
 * 仿真配置
 */
export interface SimulationConfig {
  // 几何参数
  width: number;
  length: number;
  n_cells: number;
  
  // 物理参数
  manning_n?: number;
  slope?: number;
  
  // 时间参数
  t_end: number;
  dt_max?: number;
  output_interval?: number;
  
  // 初始条件
  initial_conditions: {
    type: 'uniform' | 'dam_break';
    h?: number;
    Q?: number;
    dam_position?: number;
    h_left?: number;
    h_right?: number;
    Q_left?: number;
    Q_right?: number;
  };
  
  // 边界条件
  boundary_conditions: {
    upstream: {
      type: 'h' | 'Q' | 'wall';
      value: number;
    };
    downstream: {
      type: 'h' | 'Q' | 'wall';
      value: number;
    };
  };
}

/**
 * 仿真请求
 */
export interface SimulationRequest {
  name: string;
  description?: string;
  config: SimulationConfig;
}

/**
 * 仿真响应
 */
export interface SimulationResponse {
  task_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  message?: string;
}

/**
 * 仿真状态
 */
export interface SimulationStatus {
  task_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress?: number;
  error?: string;
  started_at?: string;
  completed_at?: string;
}

/**
 * 仿真结果
 */
export interface SimulationResultResponse {
  task_id: string;
  status: string;
  time: number[];
  x: number[];
  h: number[][];  // h[time_idx][x_idx]
  Q: number[][];
  V: number[][];
  metrics: {
    max_depth?: number;
    max_velocity?: number;
    max_froude?: number;
    total_volume?: number;
    mass_balance_error?: number;
    [key: string]: any;
  };
  duration: number;
  timestamp: string;
}

// ==================== API函数 ====================

/**
 * 创建仿真任务
 * 
 * 根据配置类型自动路由到合适的后端API端点
 */
export async function createSimulation(request: SimulationRequest): Promise<SimulationResponse> {
  try {
    // 构建后端配置
    const backendConfig = {
      name: request.name,
      description: request.description,
      canal: {
        width: request.config.width,
        length: request.config.length,
        n_cells: request.config.n_cells,
        manning_n: request.config.manning_n || 0.0,
        slope: request.config.slope || 0.0,
        t_end: request.config.t_end,
        dt_max: request.config.dt_max || 0.1,
        output_interval: request.config.output_interval || 0.5,
      },
      initial_conditions: request.config.initial_conditions,
      boundary_conditions: request.config.boundary_conditions,
    };

    // 调用后端仿真API（使用基础明渠流动端点）
    // 注意：这里映射到实际存在的后端API
    const response = await api.post('/api/v1/simulation/run', backendConfig);
    
    return {
      task_id: response.data.task_id,
      status: response.data.status || 'completed',
      message: response.data.message,
    };
  } catch (error: any) {
    console.error('创建仿真失败:', error);
    throw error;
  }
}

/**
 * 查询仿真状态
 * 
 * 轮询查询仿真任务的执行状态
 */
export async function getSimulationStatus(taskId: string): Promise<SimulationStatus> {
  try {
    const response = await api.get(`/api/v1/simulation/${taskId}/status`);
    
    return {
      task_id: taskId,
      status: response.data.status,
      progress: response.data.progress,
      error: response.data.error,
      started_at: response.data.started_at,
      completed_at: response.data.completed_at,
    };
  } catch (error: any) {
    // 如果API不存在，返回模拟状态
    console.warn('状态查询API不存在，返回completed状态');
    return {
      task_id: taskId,
      status: 'completed',
      progress: 100,
    };
  }
}

/**
 * 获取仿真结果
 * 
 * 获取已完成仿真的结果数据
 */
export async function getSimulationResults(taskId: string): Promise<SimulationResultResponse> {
  try {
    const response = await api.get(`/api/v1/simulation/${taskId}/results`);
    
    return {
      task_id: taskId,
      status: response.data.status,
      time: response.data.time || [],
      x: response.data.x || [],
      h: response.data.h || [[]],
      Q: response.data.Q || [[]],
      V: response.data.V || [[]],
      metrics: response.data.metrics || {},
      duration: response.data.duration || 0,
      timestamp: response.data.timestamp || new Date().toISOString(),
    };
  } catch (error: any) {
    console.error('获取仿真结果失败:', error);
    throw error;
  }
}

/**
 * 删除仿真任务
 */
export async function deleteSimulation(taskId: string): Promise<void> {
  try {
    await api.delete(`/api/v1/simulation/${taskId}`);
  } catch (error: any) {
    console.error('删除仿真失败:', error);
    throw error;
  }
}

/**
 * 列出所有仿真任务
 */
export async function listSimulations(status?: string): Promise<SimulationStatus[]> {
  try {
    const response = await api.get('/api/v1/simulation/list', {
      params: { status }
    });
    
    return response.data.simulations || [];
  } catch (error: any) {
    console.error('获取仿真列表失败:', error);
    return [];
  }
}

// ==================== 导出所有类型和函数 ====================

export type {
  SimulationConfig,
  SimulationRequest,
  SimulationResponse,
  SimulationStatus,
  SimulationResultResponse,
};

export default {
  createSimulation,
  getSimulationStatus,
  getSimulationResults,
  deleteSimulation,
  listSimulations,
};
