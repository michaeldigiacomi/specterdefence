import { describe, it, expect } from 'vitest';
import { Tenant, TenantCreate, TenantUpdate, TenantListResponse } from '@/types';

describe('Tenant Types', () => {
  it('validates Tenant structure', () => {
    const tenant: Tenant = {
      id: 'uuid-123',
      name: 'Test Tenant',
      tenant_id: '12345678-1234-1234-1234-123456789012',
      client_id: 'abcdef12...1234',
      is_active: true,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
      ms_tenant_name: 'Microsoft Test',
    };

    expect(tenant.id).toBe('uuid-123');
    expect(tenant.name).toBe('Test Tenant');
    expect(tenant.is_active).toBe(true);
    expect(tenant.client_id).toContain('...');
  });

  it('validates TenantCreate structure', () => {
    const create: TenantCreate = {
      name: 'New Tenant',
      tenant_id: '12345678-1234-1234-1234-123456789012',
      client_id: 'abcdef12-3456-7890-abcd-ef1234567890',
      client_secret: 'super-secret-value',
    };

    expect(create.name).toBe('New Tenant');
    expect(create.tenant_id).toHaveLength(36);
    expect(create.client_secret).toBe('super-secret-value');
  });

  it('validates TenantUpdate structure', () => {
    const update: TenantUpdate = {
      name: 'Updated Name',
      is_active: false,
    };

    expect(update.name).toBe('Updated Name');
    expect(update.is_active).toBe(false);
  });

  it('validates TenantListResponse structure', () => {
    const response: TenantListResponse = {
      items: [
        {
          id: '1',
          name: 'Tenant 1',
          tenant_id: 'guid-1',
          client_id: 'client-1',
          is_active: true,
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z',
        },
      ],
      total: 1,
    };

    expect(response.items).toHaveLength(1);
    expect(response.total).toBe(1);
  });
});
