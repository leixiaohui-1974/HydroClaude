import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface Project {
  id: number;
  name: string;
  description?: string;
  type: string;
  status: string;
  created: string;
  lastRun?: string;
  config?: any;
}

interface Notification {
  id: string;
  type: string;
  message: string;
  read: boolean;
}

interface AppState {
  // Projects
  projects: Project[];
  currentProject: Project | null;
  setProjects: (projects: Project[]) => void;
  setCurrentProject: (project: Project | null) => void;
  addProject: (project: Project) => void;
  updateProject: (id: number, data: Partial<Project>) => void;
  removeProject: (id: number) => void;

  // Simulation
  currentJobId: number | null;
  setCurrentJobId: (id: number | null) => void;

  // UI State
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;
  theme: 'light' | 'dark';
  setTheme: (theme: 'light' | 'dark') => void;

  // Notifications
  notifications: Notification[];
  addNotification: (type: string, message: string) => void;
  markNotificationRead: (id: string) => void;
  clearNotifications: () => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      // Projects
      projects: [],
      currentProject: null,
      setProjects: (projects) => set({ projects }),
      setCurrentProject: (project) => set({ currentProject: project }),
      addProject: (project) =>
        set((state) => ({ projects: [...state.projects, project] })),
      updateProject: (id, data) =>
        set((state) => ({
          projects: state.projects.map((p) =>
            p.id === id ? { ...p, ...data } : p
          ),
          currentProject:
            state.currentProject?.id === id
              ? { ...state.currentProject, ...data }
              : state.currentProject,
        })),
      removeProject: (id) =>
        set((state) => ({
          projects: state.projects.filter((p) => p.id !== id),
          currentProject:
            state.currentProject?.id === id ? null : state.currentProject,
        })),

      // Simulation
      currentJobId: null,
      setCurrentJobId: (id) => set({ currentJobId: id }),

      // UI State
      sidebarCollapsed: false,
      toggleSidebar: () =>
        set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
      theme: 'light',
      setTheme: (theme) => set({ theme }),

      // Notifications
      notifications: [],
      addNotification: (type, message) =>
        set((state) => ({
          notifications: [
            ...state.notifications,
            {
              id: `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`,
              type,
              message,
              read: false,
            },
          ],
        })),
      markNotificationRead: (id) =>
        set((state) => ({
          notifications: state.notifications.map((n) =>
            n.id === id ? { ...n, read: true } : n
          ),
        })),
      clearNotifications: () => set({ notifications: [] }),
    }),
    {
      name: 'hydroclaude-app',
      partialize: (state) => ({
        sidebarCollapsed: state.sidebarCollapsed,
        theme: state.theme,
        currentProject: state.currentProject,
      }),
    }
  )
);
