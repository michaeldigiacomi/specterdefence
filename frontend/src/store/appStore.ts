import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { AppState, Theme } from '@/types';

export const useAppStore = create<AppState>()(
  persist(
    (set, _get) => ({
      theme: 'light',
      sidebarOpen: true,
      setTheme: (theme: Theme) => set({ theme }),
      toggleTheme: () => set((state) => ({ theme: state.theme === 'light' ? 'dark' : 'light' })),
      toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
      setSidebarOpen: (open: boolean) => set({ sidebarOpen: open }),
    }),
    {
      name: 'specterdefence-storage',
      partialize: (state) => ({ theme: state.theme }),
    }
  )
);
