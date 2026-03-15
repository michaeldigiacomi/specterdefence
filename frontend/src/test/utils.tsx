import React, { ReactElement } from 'react';
import { render, RenderOptions } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { vi } from 'vitest';

// ============================================
// Mock Zustand Store
// ============================================

interface MockAppState {
  theme: 'light' | 'dark';
  sidebarOpen: boolean;
  user: { username: string; is_authenticated: boolean } | null;
  token: string | null;
  isAuthenticated: boolean;
  toggleTheme: () => void;
  toggleSidebar: () => void;
  setUser: (user: any) => void;
  login: (token: string) => void;
  logout: () => void;
}

export const createMockStore = (overrides: Partial<MockAppState> = {}) => ({
  theme: 'light',
  sidebarOpen: true,
  user: null,
  token: null,
  isAuthenticated: false,
  toggleTheme: vi.fn(),
  toggleSidebar: vi.fn(),
  setUser: vi.fn(),
  login: vi.fn(),
  logout: vi.fn(),
  ...overrides,
});

// Mock the store module
export const mockUseAppStore = vi.fn();

// ============================================
// Custom Render with Providers
// ============================================

interface CustomRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  route?: string;
  initialEntries?: string[];
  queryClient?: QueryClient;
  storeState?: Partial<MockAppState>;
}

export function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
        staleTime: 0,
      },
    },
  });
}

function AllProviders({
  children,
  queryClient,
  initialEntries = ['/'],
}: {
  children: React.ReactNode;
  queryClient: QueryClient;
  initialEntries?: string[];
}) {
  return (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={initialEntries}>{children}</MemoryRouter>
    </QueryClientProvider>
  );
}

export function renderWithProviders(ui: ReactElement, options: CustomRenderOptions = {}) {
  const {
    route,
    initialEntries = ['/'],
    queryClient = createTestQueryClient(),
    storeState,
    ...renderOptions
  } = options;

  // Update mock store state if provided
  if (storeState) {
    mockUseAppStore.mockReturnValue(createMockStore(storeState));
  }

  const Wrapper = ({ children }: { children: React.ReactNode }) => (
    <AllProviders queryClient={queryClient} initialEntries={initialEntries}>
      {children}
    </AllProviders>
  );

  return {
    ...render(ui, { wrapper: Wrapper, ...renderOptions }),
    queryClient,
  };
}

// ============================================
// Router-specific Render
// ============================================

export function renderWithRouter(
  ui: ReactElement,
  { route = '/', path = '/', ...options }: CustomRenderOptions & { path?: string } = {}
) {
  const queryClient = createTestQueryClient();

  return renderWithProviders(
    <Routes>
      <Route path={path} element={ui} />
    </Routes>,
    {
      initialEntries: [route],
      queryClient,
      ...options,
    }
  );
}

// ============================================
// Async Utilities
// ============================================

export function waitForMs(ms: number) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// ============================================
// Element Queries Helpers
// ============================================

export function getByRoleWithName(container: HTMLElement, role: string, name: string | RegExp) {
  const elements = container.querySelectorAll(`[role="${role}"]`);
  return Array.from(elements).find(el => {
    const text = el.textContent || '';
    return typeof name === 'string' ? text.includes(name) : name.test(text);
  });
}

// ============================================
// Mock Data Helpers
// ============================================

export function createMockTenant(overrides = {}) {
  return {
    id: `tenant-${Date.now()}`,
    name: 'Test Tenant',
    tenant_id: '12345678-1234-1234-1234-123456789012',
    client_id: 'client-id',
    is_active: true,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    ...overrides,
  };
}

export function createMockAlert(overrides = {}) {
  return {
    id: `alert-${Date.now()}`,
    severity: 'MEDIUM',
    event_type: 'new_country',
    event_type_name: 'New Country Login',
    user_email: 'test@example.com',
    title: 'Test Alert',
    message: 'Test alert message',
    metadata: {},
    timestamp: new Date().toISOString(),
    tenant_id: 'tenant-1',
    status: 'new',
    ...overrides,
  };
}

// ============================================
// Mock ResizeObserver
// ============================================

export function mockResizeObserver() {
  const observe = vi.fn();
  const unobserve = vi.fn();
  const disconnect = vi.fn();

  window.ResizeObserver = vi.fn(() => ({
    observe,
    unobserve,
    disconnect,
  })) as any;

  return { observe, unobserve, disconnect };
}

// ============================================
// Mock MatchMedia
// ============================================

export function mockMatchMedia(matches = false) {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  });
}
