import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import {
  useTenants,
  useCreateTenant,
  useUpdateTenant,
  useDeleteTenant,
  useValidateTenant,
} from './useApi';
import { server } from '@/test/mocks/server';
import { http, HttpResponse } from 'msw';
import React from 'react';

// Create a wrapper with QueryClient
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
        {children}
      </QueryClientProvider>
    );
  };
};

describe('Tenant API Hooks', () => {
  describe('useTenants', () => {
    it('fetches tenants successfully', async () => {
      const { result } = renderHook(() => useTenants(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data?.items).toHaveLength(3);
      expect(result.current.data?.total).toBe(3);
    });

    it('handles error state', async () => {
      server.use(
        http.get('/api/v1/tenants', () => {
          return HttpResponse.json(
            { detail: 'Failed to fetch tenants' },
            { status: 500 }
          );
        })
      );

      const { result } = renderHook(() => useTenants(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });
    });
  });

  describe('useCreateTenant', () => {
    it('creates tenant successfully', async () => {
      const { result } = renderHook(() => useCreateTenant(), {
        wrapper: createWrapper(),
      });

      result.current.mutate({
        name: 'New Tenant',
        tenant_id: '12345678-1234-1234-1234-123456789012',
        client_id: 'client-id',
        client_secret: 'client-secret',
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data?.name).toBe('New Tenant');
    });

    it('handles creation error', async () => {
      server.use(
        http.post('/api/v1/tenants', () => {
          return HttpResponse.json(
            { detail: 'Tenant already exists' },
            { status: 409 }
          );
        })
      );

      const { result } = renderHook(() => useCreateTenant(), {
        wrapper: createWrapper(),
      });

      result.current.mutate({
        name: 'Duplicate Tenant',
        tenant_id: 'existing-id',
        client_id: 'client-id',
        client_secret: 'client-secret',
      });

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });
    });
  });

  describe('useUpdateTenant', () => {
    it('updates tenant successfully', async () => {
      const { result } = renderHook(() => useUpdateTenant('tenant-1'), {
        wrapper: createWrapper(),
      });

      result.current.mutate({
        name: 'Updated Tenant Name',
        is_active: false,
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });
    });

    it('handles not found error', async () => {
      server.use(
        http.patch('/api/v1/tenants/:id', () => {
          return HttpResponse.json(
            { detail: 'Tenant not found' },
            { status: 404 }
          );
        })
      );

      const { result } = renderHook(() => useUpdateTenant('non-existent'), {
        wrapper: createWrapper(),
      });

      result.current.mutate({ name: 'Updated Name' });

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });
    });
  });

  describe('useDeleteTenant', () => {
    it('deletes tenant successfully', async () => {
      const { result } = renderHook(() => useDeleteTenant(), {
        wrapper: createWrapper(),
      });

      result.current.mutate('tenant-1');

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });
    });

    it('handles delete error for non-existent tenant', async () => {
      server.use(
        http.delete('/api/v1/tenants/:id', () => {
          return HttpResponse.json(
            { detail: 'Tenant not found' },
            { status: 404 }
          );
        })
      );

      const { result } = renderHook(() => useDeleteTenant(), {
        wrapper: createWrapper(),
      });

      result.current.mutate('non-existent');

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });
    });
  });

  describe('useValidateTenant', () => {
    it('validates tenant credentials successfully', async () => {
      const { result } = renderHook(() => useValidateTenant(), {
        wrapper: createWrapper(),
      });

      result.current.mutate({
        name: 'Test Tenant',
        tenant_id: '12345678-1234-1234-1234-123456789012',
        client_id: 'client-id',
        client_secret: 'client-secret',
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data?.valid).toBe(true);
    });

    it('returns invalid for incorrect credentials', async () => {
      server.use(
        http.post('/api/v1/tenants/validate', () => {
          return HttpResponse.json({
            valid: false,
            message: 'Invalid Azure AD credentials',
          });
        })
      );

      const { result } = renderHook(() => useValidateTenant(), {
        wrapper: createWrapper(),
      });

      result.current.mutate({
        name: 'Test Tenant',
        tenant_id: 'invalid-id',
        client_id: 'invalid-client',
        client_secret: 'invalid-secret',
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data?.valid).toBe(false);
    });
  });
});
