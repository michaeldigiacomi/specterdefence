import { Tenant, User, LoginRecord, AlertHistory, Alert, DashboardStats } from '@/types';

// ============================================
// User / Auth Mocks
// ============================================

export const mockUser: User = {
  username: 'admin',
  is_authenticated: true,
};

export const mockToken = 'mock-jwt-token-12345';

export const mockLoginResponse = {
  access_token: mockToken,
  token_type: 'bearer',
  expires_in: 3600,
};

export const mockAuthCheckResponse = {
  authenticated: true,
  username: 'admin',
};

// ============================================
// Tenant Mocks
// ============================================

export const mockTenants: Tenant[] = [
  {
    id: 'tenant-1',
    name: 'Contoso Production',
    tenant_id: '12345678-1234-1234-1234-123456789012',
    client_id: 'client-id-1',
    is_active: true,
    created_at: '2024-01-15T10:00:00Z',
    updated_at: '2024-01-15T10:00:00Z',
    ms_tenant_name: 'contoso.onmicrosoft.com',
  },
  {
    id: 'tenant-2',
    name: 'Fabrikam Test',
    tenant_id: '87654321-4321-4321-4321-210987654321',
    client_id: 'client-id-2',
    is_active: true,
    created_at: '2024-02-20T14:30:00Z',
    updated_at: '2024-02-20T14:30:00Z',
    ms_tenant_name: 'fabrikam.onmicrosoft.com',
  },
  {
    id: 'tenant-3',
    name: 'Inactive Tenant',
    tenant_id: 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee',
    client_id: 'client-id-3',
    is_active: false,
    created_at: '2024-03-01T09:00:00Z',
    updated_at: '2024-03-01T09:00:00Z',
  },
];

export const mockTenantListResponse = {
  items: mockTenants,
  total: mockTenants.length,
};

// ============================================
// Alert Mocks
// ============================================

export const mockAlerts: Alert[] = [
  {
    id: 'alert-1',
    severity: 'CRITICAL',
    event_type: 'impossible_travel',
    event_type_name: 'Impossible Travel',
    user_email: 'user1@contoso.com',
    title: 'Impossible travel detected',
    message: 'User logged in from two locations 5,000 miles apart within 1 hour',
    metadata: {
      ip_address: '192.168.1.1',
      current_location: { city: 'New York', country: 'USA' },
      previous_location: { city: 'London', country: 'UK' },
      time_diff_minutes: 60,
    },
    timestamp: new Date().toISOString(),
    tenant_id: 'tenant-1',
    status: 'new',
  },
  {
    id: 'alert-2',
    severity: 'HIGH',
    event_type: 'brute_force',
    event_type_name: 'Brute Force Attack',
    user_email: 'admin@contoso.com',
    title: 'Multiple failed login attempts',
    message: '10 failed login attempts detected in 5 minutes',
    metadata: {
      ip_address: '10.0.0.1',
      attempt_count: 10,
      time_window_minutes: 5,
    },
    timestamp: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
    tenant_id: 'tenant-1',
    status: 'acknowledged',
    acknowledged_by: 'admin',
    acknowledged_at: new Date().toISOString(),
  },
  {
    id: 'alert-3',
    severity: 'MEDIUM',
    event_type: 'new_country',
    event_type_name: 'New Country Login',
    user_email: 'user2@fabrikam.com',
    title: 'Login from new country',
    message: 'User logged in from a country not seen before',
    metadata: {
      ip_address: '203.0.113.1',
      location: { city: 'Tokyo', country: 'Japan' },
      previous_countries: ['USA', 'Canada'],
    },
    timestamp: new Date(Date.now() - 1000 * 60 * 60 * 2).toISOString(),
    tenant_id: 'tenant-2',
    status: 'new',
  },
  {
    id: 'alert-4',
    severity: 'LOW',
    event_type: 'new_ip',
    event_type_name: 'New IP Address',
    user_email: 'user3@contoso.com',
    title: 'Login from new IP address',
    message: 'User logged in from a new IP address',
    metadata: {
      ip_address: '198.51.100.1',
    },
    timestamp: new Date(Date.now() - 1000 * 60 * 60 * 4).toISOString(),
    tenant_id: 'tenant-1',
    status: 'dismissed',
  },
];

export const mockAlertHistory: AlertHistory[] = [
  {
    id: 'history-1',
    webhook_id: 'webhook-1',
    severity: 'CRITICAL',
    event_type: 'impossible_travel',
    user_email: 'user1@contoso.com',
    title: 'Impossible travel detected',
    message: 'User logged in from two distant locations',
    metadata: {},
    sent_at: new Date().toISOString(),
  },
  {
    id: 'history-2',
    webhook_id: 'webhook-1',
    severity: 'HIGH',
    event_type: 'brute_force',
    user_email: 'admin@contoso.com',
    title: 'Brute force attack',
    message: 'Multiple failed login attempts',
    metadata: {},
    sent_at: new Date(Date.now() - 1000 * 60 * 60).toISOString(),
  },
];

// ============================================
// Dashboard Mocks
// ============================================

export const mockDashboardStats: DashboardStats = {
  total_logins: 15234,
  failed_logins: 156,
  anomalies_today: 12,
  active_tenants: 3,
};

export const mockDashboardData = {
  summary: {
    total_logins_24h: 15234,
    failed_logins_24h: 156,
    anomalies_today: 12,
    avg_risk_score: 45.5,
  },
  login_timeline: {
    data: [
      { date: '2024-01-01', total: 500, failed: 10 },
      { date: '2024-01-02', total: 520, failed: 8 },
      { date: '2024-01-03', total: 480, failed: 15 },
    ],
    change_percent: 5.2,
  },
  geo_heatmap: {
    locations: [
      {
        country_code: 'US',
        country_name: 'USA',
        latitude: 37.0902,
        longitude: -95.7129,
        login_count: 5000,
        user_count: 1200,
        risk_score_avg: 35.5,
      },
      {
        country_code: 'GB',
        country_name: 'UK',
        latitude: 55.3781,
        longitude: -3.436,
        login_count: 1200,
        user_count: 300,
        risk_score_avg: 42.0,
      },
      {
        country_code: 'DE',
        country_name: 'Germany',
        latitude: 51.1657,
        longitude: 10.4515,
        login_count: 800,
        user_count: 200,
        risk_score_avg: 38.5,
      },
    ],
    total_countries: 25,
    top_country: 'USA',
  },
  anomaly_trend: {
    data: [
      {
        date: '2024-01-01',
        count: 5,
        types: { impossible_travel: 3, new_country: 1, brute_force: 1 },
      },
      { date: '2024-01-02', count: 3, types: { new_country: 2, brute_force: 1 } },
      { date: '2024-01-03', count: 4, types: { impossible_travel: 2, new_ip: 2 } },
    ],
    total_anomalies: 12,
    top_type: 'impossible_travel',
    change_percent: -10.5,
  },
  alert_volume: {
    data: [
      { date: '2024-01-01', count: 20, severity: 'HIGH' },
      { date: '2024-01-02', count: 15, severity: 'MEDIUM' },
    ],
    total_by_severity: { CRITICAL: 2, HIGH: 15, MEDIUM: 30, LOW: 50 },
    peak_volume: 25,
  },
  top_risk_users: {
    users: [
      {
        user_email: 'user1@contoso.com',
        tenant_id: 'tenant-1',
        risk_score: 85,
        anomaly_count: 12,
        top_anomaly_types: ['impossible_travel', 'new_country'],
        country_count: 5,
        last_anomaly_time: new Date().toISOString(),
      },
      {
        user_email: 'admin@contoso.com',
        tenant_id: 'tenant-1',
        risk_score: 72,
        anomaly_count: 8,
        top_anomaly_types: ['brute_force'],
        country_count: 3,
        last_anomaly_time: new Date(Date.now() - 1000 * 60 * 60).toISOString(),
      },
      {
        user_email: 'user2@fabrikam.com',
        tenant_id: 'tenant-2',
        risk_score: 65,
        anomaly_count: 5,
        top_anomaly_types: ['new_ip', 'impossible_travel'],
        country_count: 2,
        last_anomaly_time: new Date(Date.now() - 1000 * 60 * 60 * 2).toISOString(),
      },
    ],
    total_users: 150,
    avg_risk_score: 35.5,
  },
  anomaly_breakdown: [
    { type: 'impossible_travel', count: 5, percentage: 41.7, avg_risk_score: 68.5 },
    { type: 'brute_force', count: 3, percentage: 25, avg_risk_score: 72.0 },
    { type: 'new_country', count: 2, percentage: 16.7, avg_risk_score: 45.5 },
    { type: 'new_ip', count: 2, percentage: 16.7, avg_risk_score: 35.0 },
  ],
  generated_at: new Date().toISOString(),
};

// ============================================
// Login Records Mocks
// ============================================

export const mockLoginRecords: LoginRecord[] = [
  {
    id: 'login-1',
    user_email: 'user1@contoso.com',
    ip_address: '192.168.1.1',
    country: 'USA',
    country_code: 'US',
    city: 'New York',
    region: 'NY',
    latitude: 40.7128,
    longitude: -74.006,
    login_time: new Date().toISOString(),
    is_success: true,
    anomaly_flags: [],
    risk_score: 10,
  },
  {
    id: 'login-2',
    user_email: 'user2@fabrikam.com',
    ip_address: '203.0.113.1',
    country: 'Japan',
    country_code: 'JP',
    city: 'Tokyo',
    region: 'Tokyo',
    latitude: 35.6762,
    longitude: 139.6503,
    login_time: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
    is_success: false,
    failure_reason: 'Invalid credentials',
    anomaly_flags: ['new_country'],
    risk_score: 65,
  },
];
