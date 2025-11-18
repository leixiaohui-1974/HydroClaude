/**
 * 统一组件API服务层
 * Unified Component API Service
 * 
 * 为所有23种组件提供统一的API调用接口
 * 
 * @author HydroClaude Team
 * @date 2025-11-17
 * @version 2.0.0
 */

import axios, { AxiosInstance } from 'axios';
import {
  ComponentConfig,
  getAllApiEndpoints,
  getComponentById
} from '../features/modeling/utils/unifiedComponentLibrary';

// ==================== 配置 ====================

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// ==================== 类型定义 ====================

export interface SimulationRequest {
  [key: string]: any;
}

export interface SimulationResponse {
  task_id: string;
  status: 'completed' | 'failed' | 'running';
  time: number[];
  x: number[];
  h: number[][];
  Q: number[][];
  V: number[][];
  metrics: Record<string, any>;
  duration: number;
  timestamp: string;
  error?: string;
}

export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

// ==================== Axios实例 ====================

class UnifiedComponentApiService {
  private axiosInstance: AxiosInstance;

  constructor() {
    this.axiosInstance = axios.create({
      baseURL: API_BASE_URL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json'
      }
    });

    // 请求拦截器
    this.axiosInstance.interceptors.request.use(
      config => {
        console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`);
        return config;
      },
      error => {
        console.error('[API] Request error:', error);
        return Promise.reject(error);
      }
    );

    // 响应拦截器
    this.axiosInstance.interceptors.response.use(
      response => {
        console.log(`[API] Response:`, response.status);
        return response;
      },
      error => {
        console.error('[API] Response error:', error);
        if (error.response) {
          console.error('[API] Status:', error.response.status);
          console.error('[API] Data:', error.response.data);
        }
        return Promise.reject(error);
      }
    );
  }

  /**
   * 通用组件仿真调用
   */
  async runSimulation(
    componentId: string,
    config: Record<string, any>
  ): Promise<ApiResponse<SimulationResponse>> {
    try {
      const component = getComponentById(componentId);
      if (!component) {
        throw new Error(`未找到组件: ${componentId}`);
      }

      console.log(`[API] 运行仿真: ${component.nameCN}`);
      console.log(`[API] 端点: ${component.apiEndpoint}`);
      console.log(`[API] 配置:`, config);

      const response = await this.axiosInstance.post<SimulationResponse>(
        component.apiEndpoint,
        config
      );

      return {
        success: true,
        data: response.data,
        message: '仿真成功'
      };
    } catch (error: any) {
      console.error('[API] 仿真失败:', error);
      return {
        success: false,
        error: error.message || '仿真失败',
        message: error.response?.data?.detail || error.message
      };
    }
  }

  /**
   * 泵站仿真
   */
  async runPumpSimulation(config: any): Promise<ApiResponse<SimulationResponse>> {
    return this.runSimulation('pump-station', config);
  }

  /**
   * 闸门仿真
   */
  async runGateSimulation(config: any, gateType: 'sluice' | 'radial' | 'vertical_lift' = 'sluice'): Promise<ApiResponse<SimulationResponse>> {
    const componentMap = {
      'sluice': 'sluice-gate',
      'radial': 'radial-gate',
      'vertical_lift': 'vertical-lift-gate'
    };
    return this.runSimulation(componentMap[gateType], config);
  }

  /**
   * 水轮机仿真
   */
  async runTurbineSimulation(config: any): Promise<ApiResponse<SimulationResponse>> {
    return this.runSimulation('turbine', config);
  }

  /**
   * 阀门仿真
   */
  async runValveSimulation(config: any): Promise<ApiResponse<SimulationResponse>> {
    return this.runSimulation('valve', config);
  }

  /**
   * 调压井仿真
   */
  async runSurgeTankSimulation(config: any): Promise<ApiResponse<SimulationResponse>> {
    return this.runSimulation('surge-tank', config);
  }

  /**
   * 堰仿真
   */
  async runWeirSimulation(config: any, weirType: string = 'broad_crested'): Promise<ApiResponse<SimulationResponse>> {
    const componentMap: Record<string, string> = {
      'broad_crested': 'broad-crested-weir',
      'sharp_crested': 'sharp-crested-weir',
      'v_notch': 'v-notch-weir'
    };
    return this.runSimulation(componentMap[weirType] || 'broad-crested-weir', config);
  }

  /**
   * 涵洞仿真
   */
  async runCulvertSimulation(config: any): Promise<ApiResponse<SimulationResponse>> {
    return this.runSimulation('culvert', config);
  }

  /**
   * 桥梁仿真
   */
  async runBridgeSimulation(config: any): Promise<ApiResponse<SimulationResponse>> {
    return this.runSimulation('bridge', config);
  }

  /**
   * 明渠仿真
   */
  async runCanalSimulation(config: any): Promise<ApiResponse<SimulationResponse>> {
    return this.runSimulation('rectangular-canal', config);
  }

  /**
   * 批量仿真
   */
  async runBatchSimulations(
    simulations: Array<{ componentId: string; config: Record<string, any> }>
  ): Promise<ApiResponse<SimulationResponse[]>> {
    try {
      const results = await Promise.all(
        simulations.map(sim => this.runSimulation(sim.componentId, sim.config))
      );

      const successResults = results
        .filter(r => r.success && r.data)
        .map(r => r.data!);

      return {
        success: true,
        data: successResults,
        message: `批量仿真完成: ${successResults.length}/${results.length} 成功`
      };
    } catch (error: any) {
      return {
        success: false,
        error: error.message,
        message: '批量仿真失败'
      };
    }
  }

  /**
   * 健康检查
   */
  async healthCheck(): Promise<ApiResponse<any>> {
    try {
      const response = await this.axiosInstance.get('/api/structures/health');
      return {
        success: true,
        data: response.data,
        message: 'API服务正常'
      };
    } catch (error: any) {
      return {
        success: false,
        error: error.message,
        message: 'API服务异常'
      };
    }
  }

  /**
   * 获取支持的组件类型
   */
  async getStructureTypes(): Promise<ApiResponse<any>> {
    try {
      const response = await this.axiosInstance.get('/api/structures/types');
      return {
        success: true,
        data: response.data,
        message: '获取成功'
      };
    } catch (error: any) {
      return {
        success: false,
        error: error.message,
        message: '获取失败'
      };
    }
  }

  /**
   * 获取所有API端点列表
   */
  getAllEndpoints(): string[] {
    return getAllApiEndpoints();
  }
}

// ==================== 导出单例 ====================

export const unifiedComponentApi = new UnifiedComponentApiService();

// ==================== 便捷函数 ====================

/**
 * 运行组件仿真
 */
export const runComponentSimulation = (
  componentId: string,
  config: Record<string, any>
): Promise<ApiResponse<SimulationResponse>> => {
  return unifiedComponentApi.runSimulation(componentId, config);
};

/**
 * 检查API服务状态
 */
export const checkApiHealth = (): Promise<ApiResponse<any>> => {
  return unifiedComponentApi.healthCheck();
};

/**
 * 获取支持的组件类型
 */
export const getApiStructureTypes = (): Promise<ApiResponse<any>> => {
  return unifiedComponentApi.getStructureTypes();
};

// ==================== 默认导出 ====================

export default unifiedComponentApi;
