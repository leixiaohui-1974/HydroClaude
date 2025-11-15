import axios, { AxiosInstance, AxiosError } from 'axios'

// 创建axios实例
const api: AxiosInstance = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    // 可以在这里添加token等
    console.log('API Request:', config.method?.toUpperCase(), config.url)
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    console.log('API Response:', response.status, response.config.url)
    return response
  },
  (error: AxiosError) => {
    console.error('API Error:', error.message)
    return Promise.reject(error)
  }
)

// API服务类
export class HydraulicAPI {
  // ========== 泵站和闸门 (Week 1-2) ==========
  
  static async runPumpSimulation(config: any) {
    const response = await api.post('/structures/pump', config)
    return response.data
  }
  
  static async runGateSimulation(config: any) {
    const response = await api.post('/structures/gate', config)
    return response.data
  }
  
  static async runCanalWithPump(config: any) {
    const response = await api.post('/structures/canal-with-pump', config)
    return response.data
  }
  
  static async runCanalWithGate(config: any) {
    const response = await api.post('/structures/canal-with-gate', config)
    return response.data
  }
  
  // ========== 堰和水库 (Week 3-4) ==========
  
  static async runWeirSimulation(config: any) {
    const response = await api.post('/reservoir/weir', config)
    return response.data
  }
  
  static async runCanalWithWeir(config: any) {
    const response = await api.post('/reservoir/canal-with-weir', config)
    return response.data
  }
  
  static async runReservoirSimulation(config: any) {
    const response = await api.post('/reservoir/simulation', config)
    return response.data
  }
  
  static async runReservoirOperation(config: any) {
    const response = await api.post('/reservoir/operation', config)
    return response.data
  }
  
  static async getWeirTypes() {
    const response = await api.get('/reservoir/weir-types')
    return response.data
  }
  
  // ========== 管网和复杂系统 (Week 5-6) ==========
  
  static async runPipeFlow(config: any) {
    const response = await api.post('/network/pipe-flow', config)
    return response.data
  }
  
  static async runNetworkSimulation(config: any) {
    const response = await api.post('/network/simulation', config)
    return response.data
  }
  
  static async runComplexSystem(config: any) {
    const response = await api.post('/network/complex-system', config)
    return response.data
  }
  
  static async runIntegratedOperation(config: any) {
    const response = await api.post('/network/integrated-operation', config)
    return response.data
  }
  
  static async getPipeFormulas() {
    const response = await api.get('/network/formulas')
    return response.data
  }
  
  // ========== 系统信息 ==========
  
  static async getEngineInfo() {
    const response = await api.get('/engine/info')
    return response.data
  }
  
  static async healthCheck() {
    const response = await api.get('/health')
    return response.data
  }
}

export default api
