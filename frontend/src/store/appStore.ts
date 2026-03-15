import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { AppState, Theme, User } from '@/types';

export const useAppStore = create<AppState>()(
  persist(
    (set, _get) => ({
      theme: 'light',
      sidebarOpen: true,
      user: null,
      token: null,
      isAuthenticated: false,
      setTheme: (theme: Theme) => set({ theme }),
      toggleTheme: () => set(state => ({ theme: state.theme === 'light' ? 'dark' : 'light' })),
      toggleSidebar: () => set(state => ({ sidebarOpen: !state.sidebarOpen })),
      setSidebarOpen: (open: boolean) => set({ sidebarOpen: open }),
      setUser: (user: User | null) => set({ user }),
      setToken: (token: string | null) => set({ token }),
      login: (token: string) => set({ token, isAuthenticated: true }),
      logout: () => set({ user: null, token: null, isAuthenticated: false }),
    }),
    {
      name: 'specterdefence-storage',
      partialize: state => ({
        theme: state.theme,
        token: state.token,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
