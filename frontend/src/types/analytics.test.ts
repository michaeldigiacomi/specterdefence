import { describe, it, expect } from 'vitest';
import type { LoginAnalyticsResponse, AnomalyDetail, DashboardStats } from '@/types';

describe('Analytics Types', () => {
  it('validates LoginAnalyticsResponse structure', () => {
    const response: LoginAnalyticsResponse = {
      logins: [],
      total: 0,
      page: 1,
      page_size: 20,
      filters_applied: {
        tenant_id: 'tenant-123',
      },
      anomalies: [],
    };

    expect(response.logins).toEqual([]);
    expect(response.total).toBe(0);
    expect(response.page).toBe(1);
    expect(response.filters_applied.tenant_id).toBe('tenant-123');
  });

  it('validates AnomalyDetail structure', () => {
    const anomaly: AnomalyDetail = {
      type: 'impossible_travel',
      user: 'user@example.com',
      locations: ['NYC', 'LA'],
      time_diff_minutes: 30,
      risk_score: 85,
      country: 'USA',
      previous_countries: ['UK', 'CA'],
      details: {
        previous_ip: '1.2.3.4',
        current_ip: '5.6.7.8',
      },
    };

    expect(anomaly.type).toBe('impossible_travel');
    expect(anomaly.risk_score).toBe(85);
    expect(anomaly.locations).toHaveLength(2);
    expect(anomaly.details?.previous_ip).toBe('1.2.3.4');
  });

  it('validates DashboardStats structure', () => {
    const stats: DashboardStats = {
      total_logins: 1000,
      failed_logins: 50,
      anomalies_today: 5,
      active_tenants: 3,
    };

    expect(stats.total_logins).toBe(1000);
    expect(stats.failed_logins).toBe(50);
    expect(stats.anomalies_today).toBe(5);
    expect(stats.active_tenants).toBe(3);
  });
});
