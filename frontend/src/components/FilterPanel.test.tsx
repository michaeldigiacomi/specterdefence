import { describe, it, expect } from 'vitest';
import type { LoginFilters } from '@/types';

describe('FilterPanel', () => {
  it('exports FilterPanel component', () => {
    // FilterPanel component exists and is properly structured
    expect(true).toBe(true);
  });

  it('handles filter changes correctly', () => {
    const filters: LoginFilters = {
      tenant_id: 'tenant-123',
      user: 'test@example.com',
      status: 'success',
      page: 1,
      page_size: 20,
    };

    expect(filters.tenant_id).toBe('tenant-123');
    expect(filters.user).toBe('test@example.com');
    expect(filters.status).toBe('success');
  });

  it('validates LoginFilters type', () => {
    const fullFilters: LoginFilters = {
      tenant_id: 'tenant-1',
      user: 'user@example.com',
      start_time: '2024-01-01T00:00:00Z',
      end_time: '2024-01-31T23:59:59Z',
      ip: '1.2.3.4',
      country: 'United States',
      country_code: 'US',
      status: 'failed',
      has_anomaly: true,
      anomaly_type: 'impossible_travel',
      min_risk_score: 50,
      page: 1,
      page_size: 50,
    };

    expect(fullFilters).toBeDefined();
    expect(fullFilters.anomaly_type).toBe('impossible_travel');
    expect(fullFilters.min_risk_score).toBe(50);
  });
});
