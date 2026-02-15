import api from './api';

// 类型定义
export interface SimulationConfig {
  simulation: {
    type: string;
    mode: string;
    end_time?: number;
    dt?: number;
  };
  canal: {
    length: number;
    width: number;
    slope: number;
    manning_n: number;
    n_cells?: number;
    depth?: number;
    velocity?: number;
  };
  solver: {
    method: string;
  };
  boundary_conditions: {
    upstream: any;
    downstream: any;
  };
  structures?: any[];
  // Water quality parameters
  water_quality?: {
    initial_concentration?: number;
    source_position?: number;
    source_rate?: number;
    decay_rate?: number;
  };
  // Water temperature parameters
  temperature?: {
    initial_temperature?: number;
    air_temperature?: number;
    solar_radiation?: number;
    wind_speed?: number;
    relative_humidity?: number;
  };
  // Ice simulation parameters
  ice?: {
    water_temperature?: number;
    air_temperature?: number;
    initial_ice_thickness?: number;
    rho_ice?: number;
    T_freeze?: number;
  };
  // Coupled ice + water quality
  coupled?: {
    enable_temperature?: boolean;
    enable_do?: boolean;
    enable_ice?: boolean;
    enable_nutrients?: boolean;
    initial_temperature?: number;
    initial_do?: number;
  };
  // Water hammer (pipe) parameters
  pipe?: {
    length?: number;
    diameter?: number;
    friction_factor?: number;
    initial_flow?: number;
    upstream_head?: number;
    n_cells?: number;
  };
  valve?: {
    closure_time?: number;
  };
}

export interface SimulationJob {
  id: number;
  name: string;
  config: SimulationConfig;
  status: 'pending' | 'running' | 'completed' | 'failed';
  created_at: string;
  started_at?: string;
  completed_at?: string;
  progress?: number;
  error?: string;
}

export interface SimulationResults {
  id: number;
  job_id: number;
  summary?: Record<string, any>;
  time_series?: Record<string, any>;
  solver_metadata?: Record<string, any>;
  created_at?: string;
}

// 仿真API服务
export const simulationService = {
  // 创建仿真作业
  createJob: async (config: SimulationConfig, name?: string): Promise<SimulationJob> => {
    return api.post('/jobs', { config, name });
  },

  // 获取所有作业
  listJobs: async (): Promise<SimulationJob[]> => {
    return api.get('/jobs');
  },

  // 获取单个作业详情
  getJob: async (jobId: number | string): Promise<SimulationJob> => {
    return api.get(`/jobs/${jobId}`);
  },

  // 运行作业
  runJob: async (jobId: number | string): Promise<void> => {
    return api.post(`/jobs/${jobId}/run`);
  },

  // 获取作业结果
  getResults: async (jobId: number | string): Promise<SimulationResults> => {
    return api.get(`/jobs/${jobId}/results`);
  },

  // 删除作业
  deleteJob: async (jobId: number | string): Promise<void> => {
    return api.delete(`/jobs/${jobId}`);
  },

  // 轮询作业状态 (max 300 attempts ≈ 10 min at 2s interval)
  pollJobStatus: async (jobId: number | string, interval = 2000, maxAttempts = 300): Promise<SimulationJob> => {
    return new Promise((resolve, reject) => {
      let attempts = 0;
      const poll = async () => {
        attempts++;
        try {
          const job = await simulationService.getJob(jobId);

          if (job.status === 'completed' || job.status === 'failed') {
            resolve(job);
          } else if (attempts >= maxAttempts) {
            reject(new Error(`Polling timed out after ${maxAttempts} attempts for job ${jobId}`));
          } else {
            setTimeout(poll, interval);
          }
        } catch (error) {
          reject(error);
        }
      };

      poll();
    });
  },
};

export default simulationService;
