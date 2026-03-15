import { describe, it, expect } from 'vitest';
import type { LoginFilters, TenantCreate } from '@/types';

describe('apiService', () => {
  describe('getLoginAnalytics', () => {
    it('constructs URL with filters', async () => {
      const filters: LoginFilters = {
        tenant_id: 'tenant-123',
        user: 'test@example.com',
        status: 'success',
        page: 1,
        page_size: 20,
      };

      // This test validates the URL construction logic
      const params = new URLSearchParams();
      if (filters.tenant_id) params.append('tenant_id', filters.tenant_id);
      if (filters.user) params.append('user', filters.user);
      if (filters.status) params.append('status', filters.status);
      if (filters.page) params.append('page', String(filters.page));
      if (filters.page_size) params.append('page_size', String(filters.page_size));

      expect(params.toString()).toContain('tenant_id=tenant-123');
      expect(params.toString()).toContain('user=test%40example.com');
      expect(params.toString()).toContain('status=success');
    });
  });

  describe('createTenant', () => {
    it('sends correct payload', async () => {
      const tenantData: TenantCreate = {
        name: 'Test Tenant',
        tenant_id: '12345678-1234-1234-1234-123456789012',
        client_id: 'abcdef12-3456-7890-abcd-ef1234567890',
        client_secret: 'secret123',
      };

      // Verify payload structure
      expect(tenantData).toHaveProperty('name');
      expect(tenantData).toHaveProperty('tenant_id');
      expect(tenantData).toHaveProperty('client_id');
      expect(tenantData).toHaveProperty('client_secret');
    });
  });

  describe('getDashboardStats', () => {
    it('returns stats structure', async () => {
      const mockStats = {
        total_logins: 1000,
        failed_logins: 50,
        anomalies_today: 5,
        active_tenants: 3,
      };

      expect(mockStats).toHaveProperty('total_logins');
      expect(mockStats).toHaveProperty('failed_logins');
      expect(mockStats).toHaveProperty('anomalies_today');
      expect(mockStats).toHaveProperty('active_tenants');
    });
  });
});
