import { create } from 'zustand'

// UI状态接口
export interface UIState {
  // 侧边栏
  sidebarCollapsed: boolean
  
  // 主题
  theme: 'light' | 'dark'
  
  // 通知
  notifications: Array<{
    id: string
    type: 'success' | 'error' | 'warning' | 'info'
    message: string
    timestamp: Date
  }>
  
  // Actions
  toggleSidebar: () => void
  setSidebarCollapsed: (collapsed: boolean) => void
  setTheme: (theme: 'light' | 'dark') => void
  addNotification: (notification: Omit<UIState['notifications'][0], 'id' | 'timestamp'>) => void
  removeNotification: (id: string) => void
  clearNotifications: () => void
}

// 创建UI状态管理
export const useUIStore = create<UIState>((set) => ({
  // 初始状态
  sidebarCollapsed: false,
  theme: 'light',
  notifications: [],
  
  // Actions
  toggleSidebar: () => set((state) => ({ 
    sidebarCollapsed: !state.sidebarCollapsed 
  })),
  
  setSidebarCollapsed: (collapsed) => set({ 
    sidebarCollapsed: collapsed 
  }),
  
  setTheme: (theme) => set({ theme }),
  
  addNotification: (notification) => set((state) => ({
    notifications: [
      ...state.notifications,
      {
        ...notification,
        id: Math.random().toString(36).substr(2, 9),
        timestamp: new Date(),
      },
    ],
  })),
  
  removeNotification: (id) => set((state) => ({
    notifications: state.notifications.filter(n => n.id !== id),
  })),
  
  clearNotifications: () => set({ notifications: [] }),
}))
