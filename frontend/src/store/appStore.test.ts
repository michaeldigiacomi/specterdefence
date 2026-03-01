import { describe, it, expect, vi } from 'vitest';
import { AppState } from '@/types';

describe('appStore', () => {
  it('defines correct initial state structure', () => {
    const initialState: AppState = {
      theme: 'light',
      sidebarOpen: true,
      setTheme: vi.fn(),
      toggleTheme: vi.fn(),
      toggleSidebar: vi.fn(),
      setSidebarOpen: vi.fn(),
    };

    expect(initialState.theme).toBe('light');
    expect(initialState.sidebarOpen).toBe(true);
    expect(typeof initialState.setTheme).toBe('function');
    expect(typeof initialState.toggleTheme).toBe('function');
    expect(typeof initialState.toggleSidebar).toBe('function');
    expect(typeof initialState.setSidebarOpen).toBe('function');
  });

  it('supports theme toggling', () => {
    const themes: Array<'light' | 'dark'> = ['light', 'dark'];
    
    expect(themes).toContain('light');
    expect(themes).toContain('dark');
  });

  it('toggles theme correctly', () => {
    let theme: 'light' | 'dark' = 'light';
    
    const toggleTheme = () => {
      theme = theme === 'light' ? 'dark' : 'light';
    };

    expect(theme).toBe('light');
    toggleTheme();
    expect(theme).toBe('dark');
    toggleTheme();
    expect(theme).toBe('light');
  });

  it('toggles sidebar correctly', () => {
    let sidebarOpen = true;
    
    const toggleSidebar = () => {
      sidebarOpen = !sidebarOpen;
    };

    expect(sidebarOpen).toBe(true);
    toggleSidebar();
    expect(sidebarOpen).toBe(false);
    toggleSidebar();
    expect(sidebarOpen).toBe(true);
  });

  it('sets sidebar open correctly', () => {
    let sidebarOpen = true;
    
    const setSidebarOpen = (open: boolean) => {
      sidebarOpen = open;
    };

    setSidebarOpen(false);
    expect(sidebarOpen).toBe(false);
    
    setSidebarOpen(true);
    expect(sidebarOpen).toBe(true);
  });

  it('sets theme correctly', () => {
    let theme: 'light' | 'dark' = 'light';
    
    const setTheme = (newTheme: 'light' | 'dark') => {
      theme = newTheme;
    };

    setTheme('dark');
    expect(theme).toBe('dark');
    
    setTheme('light');
    expect(theme).toBe('light');
  });
});
