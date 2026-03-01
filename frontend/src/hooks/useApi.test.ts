import { describe, it, expect } from 'vitest';
import { queryKeys } from './useApi';

describe('useApi hooks', () => {
  describe('queryKeys', () => {
    it('generates correct query keys for logins', () => {
      const filters = { tenant_id: '123', page: 1 };
      const keys = queryKeys.logins(filters);
      
      expect(keys).toEqual(['logins', filters]);
    });

    it('generates correct query keys for tenants', () => {
      const keys = queryKeys.tenants();
      
      expect(keys).toEqual(['tenants']);
    });

    it('generates correct query keys for dashboard stats', () => {
      const keys = queryKeys.dashboardStats();
      
      expect(keys).toEqual(['dashboardStats']);
    });

    it('generates correct query keys for user summary', () => {
      const keys = queryKeys.userSummary('test@example.com', 'tenant-123');
      
      expect(keys).toEqual(['userSummary', 'test@example.com', 'tenant-123']);
    });

    it('generates correct query keys for tenant', () => {
      const keys = queryKeys.tenant('tenant-123');
      
      expect(keys).toEqual(['tenant', 'tenant-123']);
    });
  });
});
