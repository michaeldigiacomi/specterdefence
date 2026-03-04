import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor, render } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders, createMockStore } from '@/test/utils';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClientProvider } from '@tanstack/react-query';
import { createTestQueryClient } from '@/test/utils';
import ProtectedRoute from './ProtectedRoute';
import { mockUser } from '@/test/mocks/data';

// Mock the hooks
vi.mock('@/hooks/useAuth', () => ({
  useAuthCheck: vi.fn(),
}));

vi.mock('@/store/appStore', () => ({
  useAppStore: vi.fn(),
}));

import { useAppStore } from '@/store/appStore';
import { useAuthCheck } from '@/hooks/useAuth';

const MockDashboard = () => <div data-testid="dashboard">Dashboard</div>;
const MockLogin = () => <div data-testid="login">Login</div>;

describe('ProtectedRoute', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders children when authenticated', () => {
    (useAppStore as vi.Mock).mockReturnValue({
      isAuthenticated: true,
      token: 'valid-token',
    });
    (useAuthCheck as vi.Mock).mockReturnValue({
      isLoading: false,
      isError: false,
    });

    renderWithProviders(
      <ProtectedRoute>
        <MockDashboard />
      </ProtectedRoute>,
      {
        storeState: { isAuthenticated: true, token: 'valid-token' },
      }
    );

    expect(screen.getByTestId('dashboard')).toBeInTheDocument();
  });

  it('shows loading state while checking auth', () => {
    (useAppStore as vi.Mock).mockReturnValue({
      isAuthenticated: true,
      token: 'valid-token',
    });
    (useAuthCheck as vi.Mock).mockReturnValue({
      isLoading: true,
      isError: false,
    });

    renderWithProviders(
      <ProtectedRoute>
        <MockDashboard />
      </ProtectedRoute>
    );

    expect(screen.getByText(/verifying session/i)).toBeInTheDocument();
  });

  it('redirects to login when not authenticated', () => {
    (useAppStore as vi.Mock).mockReturnValue({
      isAuthenticated: false,
      token: null,
    });
    (useAuthCheck as vi.Mock).mockReturnValue({
      isLoading: false,
      isError: false,
    });

    const queryClient = createTestQueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={["/protected"]}>
          <Routes>
            <Route path="/login" element={<MockLogin />} />
            <Route
              path="/protected"
              element={
                <ProtectedRoute>
                  <MockDashboard />
                </ProtectedRoute>
              }
            />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    );

    expect(screen.getByTestId('login')).toBeInTheDocument();
  });
});
