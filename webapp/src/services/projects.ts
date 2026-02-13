import api from './api';

// 类型定义
export interface Project {
  id: number;
  name: string;
  description?: string;
  config?: Record<string, any>;
  status: string;
  created_at?: string;
  updated_at?: string;
}

export interface ProjectList {
  total: number;
  items: Project[];
}

export interface CreateProjectData {
  name: string;
  description?: string;
  config?: Record<string, any>;
}

export interface UpdateProjectData {
  name?: string;
  description?: string;
  config?: Record<string, any>;
  status?: string;
}

// 项目API服务
export const projectService = {
  // 获取项目列表
  list: async (skip = 0, limit = 100, status?: string): Promise<ProjectList> => {
    const params: Record<string, any> = { skip, limit };
    if (status) params.status = status;
    return api.get('/projects', { params });
  },

  // 获取单个项目
  get: async (id: number): Promise<Project> => {
    return api.get(`/projects/${id}`);
  },

  // 创建项目
  create: async (data: CreateProjectData): Promise<Project> => {
    return api.post('/projects', data);
  },

  // 更新项目
  update: async (id: number, data: UpdateProjectData): Promise<Project> => {
    return api.put(`/projects/${id}`, data);
  },

  // 删除项目
  delete: async (id: number): Promise<void> => {
    return api.delete(`/projects/${id}`);
  },
};

export default projectService;
