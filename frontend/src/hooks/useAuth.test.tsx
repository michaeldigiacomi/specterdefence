import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { useLogin, useLogout, useChangePassword, useAuthCheck, useCurrentUser } from './useAuth';
import { server } from '@/test/mocks/server';
import { http, HttpResponse } from 'msw';
import React from 'react';

// Create a wrapper with QueryClient and Router
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
    },
  });

  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>{children}</BrowserRouter>
      </QueryClientProvider>
    );
  };
};

describe('useLogin', () => {
  it('successfully logs in with valid credentials', async () => {
    const { result } = renderHook(() => useLogin(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ username: 'admin', password: 'admin123' });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });
  });

  it('fails with invalid credentials', async () => {
    server.use(
      http.post('/api/v1/auth/local/login', () => {
        return HttpResponse.json({ detail: 'Invalid credentials' }, { status: 401 });
      })
    );

    const { result } = renderHook(() => useLogin(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ username: 'wrong', password: 'wrong' });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });
  });
});

describe('useLogout', () => {
  it('successfully logs out', async () => {
    const { result } = renderHook(() => useLogout(), {
      wrapper: createWrapper(),
    });

    result.current.mutate();

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });
  });
});

describe('useChangePassword', () => {
  it('successfully changes password with valid current password', async () => {
    const { result } = renderHook(() => useChangePassword(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({
      currentPassword: 'admin123',
      newPassword: 'newpassword456',
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });
  });

  it('fails when current password is incorrect', async () => {
    server.use(
      http.post('/api/v1/auth/local/change-password', () => {
        return HttpResponse.json({ detail: 'Current password is incorrect' }, { status: 400 });
      })
    );

    const { result } = renderHook(() => useChangePassword(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({
      currentPassword: 'wrongpassword',
      newPassword: 'newpassword456',
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });
  });
});

describe('useAuthCheck', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns authenticated status when token is valid', async () => {
    const { result } = renderHook(() => useAuthCheck(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });
  });

  it('returns error when token is invalid', async () => {
    server.use(
      http.get('/api/v1/auth/local/check', () => {
        return HttpResponse.json({ authenticated: false }, { status: 401 });
      })
    );

    const { result } = renderHook(() => useAuthCheck(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isError || result.current.data === null).toBeTruthy();
    });
  });
});

describe('useCurrentUser', () => {
  it('fetches current user successfully', async () => {
    const { result } = renderHook(() => useCurrentUser(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.username).toBe('admin');
  });
});
