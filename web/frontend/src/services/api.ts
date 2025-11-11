/**
 * API Service Layer
 * Handles all communication with HydroClaude Web API
 */

import axios, { AxiosInstance } from 'axios';

// API Base URL
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Create axios instance
const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
apiClient.interceptors.request.use(
  (config) => {
    // Add auth token if available
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized
      localStorage.removeItem('auth_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// ========== Type Definitions ==========

export interface InitialConditionConfig {
  type: 'uniform' | 'dam_break' | 'custom';
  h?: number;
  Q?: number;
  dam_position?: number;
  h_left?: number;
  h_right?: number;
  Q_left?: number;
  Q_right?: number;
}

export interface BoundaryConfig {
  type: 'h' | 'Q' | 'wall';
  value?: number;
}

export interface BoundaryConditionConfig {
  upstream: BoundaryConfig;
  downstream: BoundaryConfig;
}

export interface SimulationConfig {
  width: number;
  length: number;
  n_cells: number;
  manning_n: number;
  slope: number;
  cfl?: number;
  order?: number;
  use_numba?: boolean;
  t_end: number;
  dt_max?: number;
  output_interval?: number;
  initial_conditions: InitialConditionConfig;
  boundary_conditions?: BoundaryConditionConfig;
}

export interface SimulationRequest {
  name: string;
  description?: string;
  config: SimulationConfig;
  project_id?: string;
}

export interface SimulationResponse {
  task_id: string;
  status: 'queued' | 'running' | 'completed' | 'failed';
  name: string;
  created_at: string;
  message: string;
}

export interface SimulationStatusResponse {
  task_id: string;
  status: 'queued' | 'running' | 'completed' | 'failed';
  progress?: number;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  duration?: number;
  error?: string;
}

export interface SimulationMetrics {
  mass_conservation_error: number;
  max_depth: number;
  min_depth: number;
  max_velocity: number;
  max_discharge: number;
  max_froude: number;
  mean_depth_final: number;
  mean_discharge_final: number;
  total_iterations: number;
  converged: boolean;
}

export interface SimulationResultResponse {
  task_id: string;
  status: string;
  duration: number;
  timestamp: string;
  x: number[];
  time: number[];
  h: number[][];
  Q: number[][];
  V: number[][];
  metrics: SimulationMetrics;
  error?: string;
}

export interface EngineInfo {
  engine_version: string;
  engine_path: string;
  solvers: {
    canal: string[];
    pipe: string[];
    network: string[];
  };
  features: {
    numba_acceleration: boolean;
    '3d_visualization': boolean;
    control_system: boolean;
    identification: boolean;
  };
}

// ========== API Functions ==========

/**
 * Health Check
 */
export const checkHealth = async () => {
  const response = await apiClient.get('/health');
  return response.data;
};

/**
 * Get Engine Info
 */
export const getEngineInfo = async (): Promise<EngineInfo> => {
  const response = await apiClient.get<EngineInfo>('/api/v1/engine/info');
  return response.data;
};

/**
 * Create Simulation
 */
export const createSimulation = async (
  request: SimulationRequest
): Promise<SimulationResponse> => {
  const response = await apiClient.post<SimulationResponse>(
    '/api/v1/simulations',
    request
  );
  return response.data;
};

/**
 * Get Simulation Status
 */
export const getSimulationStatus = async (
  taskId: string
): Promise<SimulationStatusResponse> => {
  const response = await apiClient.get<SimulationStatusResponse>(
    `/api/v1/simulations/${taskId}/status`
  );
  return response.data;
};

/**
 * Get Simulation Results
 */
export const getSimulationResults = async (
  taskId: string
): Promise<SimulationResultResponse> => {
  const response = await apiClient.get<SimulationResultResponse>(
    `/api/v1/simulations/${taskId}/results`
  );
  return response.data;
};

/**
 * List Simulations
 */
export const listSimulations = async (params?: {
  skip?: number;
  limit?: number;
  status?: string;
}): Promise<SimulationStatusResponse[]> => {
  const response = await apiClient.get<SimulationStatusResponse[]>(
    '/api/v1/simulations',
    { params }
  );
  return response.data;
};

/**
 * Delete Simulation
 */
export const deleteSimulation = async (taskId: string): Promise<void> => {
  await apiClient.delete(`/api/v1/simulations/${taskId}`);
};

// Export api client for custom requests
export default apiClient;
