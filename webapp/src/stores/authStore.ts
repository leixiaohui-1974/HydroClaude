import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { api, registerAuthCallbacks } from '@/services/api';

export interface AuthUser {
  id: number;
  username: string;
  email: string;
  avatar_url?: string;
}

export interface AuthState {
  token: string | null;
  user: AuthUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, email: string, password: string) => Promise<void>;
  logout: () => void;
  refreshToken: () => Promise<void>;
  checkAuth: () => Promise<void>;
  setToken: (token: string | null) => void;
  setUser: (user: AuthUser | null) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      user: null,
      isAuthenticated: false,
      isLoading: false,

      setToken: (token: string | null) => {
        set({ token, isAuthenticated: !!token });
        // Sync to localStorage for backward compatibility
        if (token) {
          localStorage.setItem('authToken', token);
        } else {
          localStorage.removeItem('authToken');
        }
      },

      setUser: (user: AuthUser | null) => {
        set({ user });
      },

      login: async (username: string, password: string) => {
        set({ isLoading: true });
        try {
          const response: any = await api.post('/auth/login', { username, password });
          const { token, user } = response;
          set({
            token,
            user,
            isAuthenticated: true,
            isLoading: false,
          });
          localStorage.setItem('authToken', token);
        } catch (error) {
          set({ isLoading: false });
          throw error;
        }
      },

      register: async (username: string, email: string, password: string) => {
        set({ isLoading: true });
        try {
          await api.post('/auth/register', { username, email, password });
          // Auto-login after registration
          const loginResponse: any = await api.post('/auth/login', { username, password });
          const { token, user } = loginResponse;
          set({
            token,
            user,
            isAuthenticated: true,
            isLoading: false,
          });
          localStorage.setItem('authToken', token);
        } catch (error) {
          set({ isLoading: false });
          throw error;
        }
      },

      logout: () => {
        set({
          token: null,
          user: null,
          isAuthenticated: false,
          isLoading: false,
        });
        localStorage.removeItem('authToken');
        window.location.href = '/login';
      },

      refreshToken: async () => {
        const { token } = get();
        if (!token) return;
        try {
          const response: any = await api.post('/auth/refresh', { token });
          const newToken = response.token;
          set({ token: newToken });
          localStorage.setItem('authToken', newToken);
        } catch {
          // If refresh fails, log out
          get().logout();
        }
      },

      checkAuth: async () => {
        const { token } = get();
        if (!token) {
          set({ isAuthenticated: false, user: null });
          return;
        }
        set({ isLoading: true });
        try {
          const response: any = await api.get('/auth/me');
          set({
            user: response.user || response,
            isAuthenticated: true,
            isLoading: false,
          });
        } catch {
          // Token is invalid or expired
          set({
            token: null,
            user: null,
            isAuthenticated: false,
            isLoading: false,
          });
          localStorage.removeItem('authToken');
        }
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        token: state.token,
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);

// 注册认证回调到API模块，避免循环依赖
registerAuthCallbacks({
  getToken: () => useAuthStore.getState().token,
  onUnauthorized: () => useAuthStore.getState().logout(),
});

export default useAuthStore;
