import { create } from 'zustand'
import axios from 'axios'

// 仿真结果接口
export interface SimulationResult {
  success: boolean
  message: string
  result?: any
  metrics?: Record<string, any>
  time_elapsed?: number
  timestamp?: string
}

// 仿真状态接口
export interface SimulationState {
  // 状态
  isLoading: boolean
  error: string | null
  currentResult: SimulationResult | null
  history: SimulationResult[]
  
  // 配置
  apiBaseUrl: string
  
  // Actions
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  setResult: (result: SimulationResult) => void
  clearResult: () => void
  clearHistory: () => void
  
  // API调用
  runPumpSimulation: (config: any) => Promise<void>
  runGateSimulation: (config: any) => Promise<void>
  runWeirSimulation: (config: any) => Promise<void>
  runReservoirSimulation: (config: any) => Promise<void>
  runPipeFlow: (config: any) => Promise<void>
  runNetworkSimulation: (config: any) => Promise<void>
}

// 创建状态管理
export const useSimulationStore = create<SimulationState>((set, get) => ({
  // 初始状态
  isLoading: false,
  error: null,
  currentResult: null,
  history: [],
  apiBaseUrl: '/api',
  
  // 基础Actions
  setLoading: (loading) => set({ isLoading: loading }),
  
  setError: (error) => set({ error }),
  
  setResult: (result) => set((state) => ({
    currentResult: result,
    history: [...state.history, result],
    error: null,
  })),
  
  clearResult: () => set({ currentResult: null }),
  
  clearHistory: () => set({ history: [] }),
  
  // API调用 - 泵站仿真
  runPumpSimulation: async (config) => {
    set({ isLoading: true, error: null })
    try {
      const response = await axios.post(
        `${get().apiBaseUrl}/structures/pump`,
        config
      )
      set({ 
        currentResult: response.data,
        history: [...get().history, response.data],
        isLoading: false,
      })
    } catch (error: any) {
      set({ 
        error: error.response?.data?.detail || error.message,
        isLoading: false,
      })
    }
  },
  
  // API调用 - 闸门仿真
  runGateSimulation: async (config) => {
    set({ isLoading: true, error: null })
    try {
      const response = await axios.post(
        `${get().apiBaseUrl}/structures/gate`,
        config
      )
      set({ 
        currentResult: response.data,
        history: [...get().history, response.data],
        isLoading: false,
      })
    } catch (error: any) {
      set({ 
        error: error.response?.data?.detail || error.message,
        isLoading: false,
      })
    }
  },
  
  // API调用 - 堰仿真
  runWeirSimulation: async (config) => {
    set({ isLoading: true, error: null })
    try {
      const response = await axios.post(
        `${get().apiBaseUrl}/reservoir/weir`,
        config
      )
      set({ 
        currentResult: response.data,
        history: [...get().history, response.data],
        isLoading: false,
      })
    } catch (error: any) {
      set({ 
        error: error.response?.data?.detail || error.message,
        isLoading: false,
      })
    }
  },
  
  // API调用 - 水库仿真
  runReservoirSimulation: async (config) => {
    set({ isLoading: true, error: null })
    try {
      const response = await axios.post(
        `${get().apiBaseUrl}/reservoir/simulation`,
        config
      )
      set({ 
        currentResult: response.data,
        history: [...get().history, response.data],
        isLoading: false,
      })
    } catch (error: any) {
      set({ 
        error: error.response?.data?.detail || error.message,
        isLoading: false,
      })
    }
  },
  
  // API调用 - 管道流动
  runPipeFlow: async (config) => {
    set({ isLoading: true, error: null })
    try {
      const response = await axios.post(
        `${get().apiBaseUrl}/network/pipe-flow`,
        config
      )
      set({ 
        currentResult: response.data,
        history: [...get().history, response.data],
        isLoading: false,
      })
    } catch (error: any) {
      set({ 
        error: error.response?.data?.detail || error.message,
        isLoading: false,
      })
    }
  },
  
  // API调用 - 管网仿真
  runNetworkSimulation: async (config) => {
    set({ isLoading: true, error: null })
    try {
      const response = await axios.post(
        `${get().apiBaseUrl}/network/simulation`,
        config
      )
      set({ 
        currentResult: response.data,
        history: [...get().history, response.data],
        isLoading: false,
      })
    } catch (error: any) {
      set({ 
        error: error.response?.data?.detail || error.message,
        isLoading: false,
      })
    }
  },
}))
