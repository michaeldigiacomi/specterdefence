import { describe, it, expect } from 'vitest';
import { LoginRecord } from './index';

describe('Types', () => {
  it('LoginRecord type structure', () => {
    const mockLogin: LoginRecord = {
      id: '123',
      user_email: 'test@example.com',
      ip_address: '1.2.3.4',
      country: 'United States',
      country_code: 'US',
      city: 'New York',
      region: 'NY',
      latitude: 40.7128,
      longitude: -74.006,
      login_time: '2024-01-01T12:00:00Z',
      is_success: true,
      failure_reason: undefined,
      anomaly_flags: [],
      risk_score: 0,
    };

    expect(mockLogin.id).toBe('123');
    expect(mockLogin.user_email).toBe('test@example.com');
    expect(mockLogin.is_success).toBe(true);
    expect(mockLogin.anomaly_flags).toEqual([]);
  });

  it('LoginRecord with anomalies', () => {
    const mockLogin: LoginRecord = {
      id: '456',
      user_email: 'user@example.com',
      ip_address: '5.6.7.8',
      country: 'United Kingdom',
      country_code: 'GB',
      login_time: '2024-01-01T13:00:00Z',
      is_success: false,
      failure_reason: 'Invalid password',
      anomaly_flags: ['new_country', 'multiple_failures'],
      risk_score: 75,
    };

    expect(mockLogin.anomaly_flags).toContain('new_country');
    expect(mockLogin.risk_score).toBe(75);
    expect(mockLogin.failure_reason).toBe('Invalid password');
  });
});
