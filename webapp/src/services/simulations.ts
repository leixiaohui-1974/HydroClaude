import api from './api';

// 类型定义
export interface SimulationConfig {
  simulation: {
    type: string;
    mode: string;
  };
  canal: {
    length: number;
    width: number;
    slope: number;
    manning_n: number;
  };
  solver: {
    method: string;
  };
  boundary_conditions: {
    upstream: any;
    downstream: any;
  };
  structures?: any[];
}

export interface SimulationJob {
  id: string;
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
  job_id: string;
  status: string;
  results: any;
  metadata: any;
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
  getJob: async (jobId: string): Promise<SimulationJob> => {
    return api.get(`/jobs/${jobId}`);
  },

  // 运行作业
  runJob: async (jobId: string): Promise<void> => {
    return api.post(`/jobs/${jobId}/run`);
  },

  // 获取作业结果
  getResults: async (jobId: string): Promise<SimulationResults> => {
    return api.get(`/jobs/${jobId}/results`);
  },

  // 删除作业
  deleteJob: async (jobId: string): Promise<void> => {
    return api.delete(`/jobs/${jobId}`);
  },

  // 轮询作业状态
  pollJobStatus: async (jobId: string, interval = 2000): Promise<SimulationJob> => {
    return new Promise((resolve, reject) => {
      const poll = async () => {
        try {
          const job = await simulationService.getJob(jobId);
          
          if (job.status === 'completed' || job.status === 'failed') {
            resolve(job);
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
