import { http, HttpResponse, delay } from 'msw';
import {
  mockLoginResponse,
  mockAuthCheckResponse,
  mockUser,
  mockTenantListResponse,
  mockTenants,
  mockDashboardData,
  mockAlertHistory,
  mockLoginRecords,
} from './data';

const API_BASE = '/api/v1';

// ============================================
// Auth Handlers
// ============================================

export const authHandlers = [
  // Login - Support both /auth/login and /auth/local/login
  http.post(`${API_BASE}/auth/local/login`, async ({ request }) => {
    const body = await request.json() as { username: string; password: string };
    
    if (body.username === 'admin' && body.password === 'admin123') {
      return HttpResponse.json(mockLoginResponse);
    }
    
    return HttpResponse.json(
      { detail: 'Invalid credentials' },
      { status: 401 }
    );
  }),

  // Logout
  http.post(`${API_BASE}/auth/local/logout`, () => {
    return HttpResponse.json({ message: 'Logged out successfully' });
  }),

  // Check Auth
  http.get(`${API_BASE}/auth/local/check`, ({ request }) => {
    const authHeader = request.headers.get('Authorization');
    
    if (authHeader?.includes('mock-jwt-token')) {
      return HttpResponse.json(mockAuthCheckResponse);
    }
    
    return HttpResponse.json(
      { authenticated: false },
      { status: 401 }
    );
  }),

  // Get Current User
  http.get(`${API_BASE}/auth/local/me`, ({ request }) => {
    const authHeader = request.headers.get('Authorization');
    
    if (authHeader?.includes('mock-jwt-token')) {
      return HttpResponse.json(mockUser);
    }
    
    return HttpResponse.json(
      { detail: 'Unauthorized' },
      { status: 401 }
    );
  }),

  // Change Password
  http.post(`${API_BASE}/auth/local/change-password`, async ({ request }) => {
    const body = await request.json() as { current_password: string; new_password: string };
    
    if (body.current_password === 'admin123') {
      return HttpResponse.json({ message: 'Password changed successfully' });
    }
    
    return HttpResponse.json(
      { detail: 'Current password is incorrect' },
      { status: 400 }
    );
  }),
];

// ============================================
// Tenant Handlers
// ============================================

export const tenantHandlers = [
  // List Tenants
  http.get(`${API_BASE}/tenants`, () => {
    return HttpResponse.json(mockTenantListResponse);
  }),

  // Get Single Tenant
  http.get(`${API_BASE}/tenants/:id`, ({ params }) => {
    const tenant = mockTenants.find(t => t.id === params.id);
    
    if (tenant) {
      return HttpResponse.json(tenant);
    }
    
    return HttpResponse.json(
      { detail: 'Tenant not found' },
      { status: 404 }
    );
  }),

  // Create Tenant
  http.post(`${API_BASE}/tenants`, async ({ request }) => {
    const body = await request.json();
    const newTenant = {
      id: `tenant-${Date.now()}`,
      ...body,
      is_active: true,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    
    return HttpResponse.json(newTenant, { status: 201 });
  }),

  // Update Tenant
  http.patch(`${API_BASE}/tenants/:id`, async ({ params, request }) => {
    const body = await request.json();
    const tenant = mockTenants.find(t => t.id === params.id);

    if (tenant) {
      return HttpResponse.json({ ...tenant, ...body });
    }

    return HttpResponse.json(
      { detail: 'Tenant not found' },
      { status: 404 }
    );
  }),

  // Delete Tenant
  http.delete(`${API_BASE}/tenants/:id`, ({ params }) => {
    const tenant = mockTenants.find(t => t.id === params.id);
    
    if (tenant) {
      return HttpResponse.json({ message: 'Tenant deleted' });
    }
    
    return HttpResponse.json(
      { detail: 'Tenant not found' },
      { status: 404 }
    );
  }),

  // Validate Tenant
  http.post(`${API_BASE}/tenants/validate`, async ({ request }) => {
    const body = await request.json() as { tenant_id: string; client_id: string; client_secret: string };
    
    // Simulate validation
    if (body.tenant_id && body.client_id && body.client_secret) {
      return HttpResponse.json({
        valid: true,
        tenant_name: 'Validated Tenant',
      });
    }
    
    return HttpResponse.json({
      valid: false,
      message: 'Invalid credentials provided',
    });
  }),
];

// ============================================
// Dashboard Handlers
// ============================================

export const dashboardHandlers = [
  // Get Dashboard Data
  http.get(`${API_BASE}/dashboard`, ({ request }) => {
    const url = new URL(request.url);
    const timeRange = url.searchParams.get('time_range') || '30d';
    
    return HttpResponse.json({
      ...mockDashboardData,
      time_range: timeRange,
    });
  }),

  // Export Dashboard
  http.get(`${API_BASE}/dashboard/export/download/:format`, async ({ params }) => {
    const format = params.format as string;
    
    // Return a mock blob
    const blob = new Blob(['mock export data'], { 
      type: format === 'csv' ? 'text/csv' : format === 'json' ? 'application/json' : 'application/pdf' 
    });
    
    const arrayBuffer = await blob.arrayBuffer();
    
    return HttpResponse.arrayBuffer(arrayBuffer, {
      headers: {
        'Content-Type': format === 'csv' ? 'text/csv' : format === 'json' ? 'application/json' : 'application/pdf',
        'Content-Disposition': `attachment; filename="dashboard-export.${format}"`,
      },
    });
  }),
];

// ============================================
// Alert Handlers
// ============================================

export const alertHandlers = [
  // Get Alert History
  http.get(`${API_BASE}/alerts/history`, ({ request }) => {
    const url = new URL(request.url);
    const limit = parseInt(url.searchParams.get('limit') || '50');
    
    return HttpResponse.json({
      items: mockAlertHistory.slice(0, limit),
      total: mockAlertHistory.length,
      limit,
      offset: 0,
    });
  }),

  // Acknowledge Alert
  http.post(`${API_BASE}/alerts/:id/acknowledge`, ({ params }) => {
    return HttpResponse.json({
      id: params.id,
      status: 'acknowledged',
      acknowledged_at: new Date().toISOString(),
    });
  }),

  // Dismiss Alert
  http.post(`${API_BASE}/alerts/:id/dismiss`, ({ params }) => {
    return HttpResponse.json({
      id: params.id,
      status: 'dismissed',
    });
  }),
];

// ============================================
// Login Analytics Handlers
// ============================================

export const loginHandlers = [
  // Get Login Analytics
  http.get(`${API_BASE}/logins`, ({ request }) => {
    const url = new URL(request.url);
    const page = parseInt(url.searchParams.get('page') || '1');
    const pageSize = parseInt(url.searchParams.get('page_size') || '20');
    
    return HttpResponse.json({
      logins: mockLoginRecords,
      total: mockLoginRecords.length,
      page,
      page_size: pageSize,
      filters_applied: {},
      anomalies: [],
    });
  }),
];

// ============================================
// Settings Handlers
// ============================================

export const settingsHandlers = [
  // System Settings
  http.get(`${API_BASE}/settings/system`, () => {
    return HttpResponse.json({
      audit_log_retention_days: 90,
      login_history_retention_days: 365,
      alert_history_retention_days: 90,
      auto_cleanup_enabled: true,
      cleanup_schedule: '0 2 * * *',
      api_rate_limit: 1000,
      max_export_rows: 10000,
      log_level: 'INFO',
    });
  }),

  // User Preferences
  http.get(`${API_BASE}/settings/preferences`, () => {
    return HttpResponse.json({
      user_email: 'admin@contoso.com',
      timezone: 'America/New_York',
      date_format: 'ISO',
      theme: 'system',
      email_notifications: true,
      discord_notifications: true,
      notification_min_severity: 'MEDIUM',
      default_dashboard_view: 'overview',
      refresh_interval_seconds: 60,
    });
  }),

  // Detection Thresholds
  http.get(`${API_BASE}/settings/detection-thresholds`, () => {
    return HttpResponse.json({
      impossible_travel_enabled: true,
      impossible_travel_min_speed_kmh: 800,
      impossible_travel_time_window_minutes: 60,
      new_country_enabled: true,
      new_country_learning_period_days: 30,
      brute_force_enabled: true,
      brute_force_threshold: 5,
      brute_force_window_minutes: 10,
      new_ip_enabled: true,
      new_ip_learning_period_days: 7,
      multiple_failures_enabled: true,
      multiple_failures_threshold: 3,
      multiple_failures_window_minutes: 5,
      risk_score_base_multiplier: 1.0,
    });
  }),
];

// Combine all handlers
export const handlers = [
  ...authHandlers,
  ...tenantHandlers,
  ...dashboardHandlers,
  ...alertHandlers,
  ...loginHandlers,
  ...settingsHandlers,
  // Catch-all passthrough for unmatched requests
  http.all('*', ({ request }) => {
    console.warn(`[MSW] Unhandled request: ${request.method} ${request.url}`);
    return;
  }),
];
