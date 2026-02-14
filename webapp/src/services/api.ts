import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';
import { message } from 'antd';
import i18n from '@/i18n';

// API基础URL
const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api';

// 认证回调接口 - 用于避免与auth store的循环依赖
interface AuthCallbacks {
  getToken: () => string | null;
  onUnauthorized: () => void;
}

let authCallbacks: AuthCallbacks | null = null;

// 注册认证回调（由auth store调用）
export const registerAuthCallbacks = (callbacks: AuthCallbacks) => {
  authCallbacks = callbacks;
};

// 创建axios实例
const apiClient: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    // 从注册的回调获取token，回退到localStorage
    const token = authCallbacks?.getToken() ?? localStorage.getItem('authToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    return response.data;
  },
  (error) => {
    // 错误处理
    const errorMessage = error.response?.data?.message || error.message || 'Request failed';

    if (error.response?.status === 401) {
      message.error(i18n.t('apiErrors.unauthorized'));
      // 通过注册的回调清除认证状态
      if (authCallbacks) {
        authCallbacks.onUnauthorized();
      } else {
        localStorage.removeItem('authToken');
        window.location.href = '/login';
      }
    } else if (error.response?.status === 403) {
      message.error(i18n.t('apiErrors.forbidden'));
    } else if (error.response?.status === 404) {
      message.error(i18n.t('apiErrors.notFound'));
    } else if (error.response?.status >= 500) {
      message.error(i18n.t('apiErrors.serverError'));
    } else {
      message.error(errorMessage);
    }

    return Promise.reject(error);
  }
);

// API接口封装
export const api = {
  // GET请求
  get: <T = any>(url: string, config?: AxiosRequestConfig): Promise<T> => {
    return apiClient.get(url, config);
  },

  // POST请求
  post: <T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> => {
    return apiClient.post(url, data, config);
  },

  // PUT请求
  put: <T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> => {
    return apiClient.put(url, data, config);
  },

  // DELETE请求
  delete: <T = any>(url: string, config?: AxiosRequestConfig): Promise<T> => {
    return apiClient.delete(url, config);
  },

  // PATCH请求
  patch: <T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> => {
    return apiClient.patch(url, data, config);
  },
};

export default api;
