import axios, { AxiosInstance, AxiosError } from 'axios';
import {
  LoginAnalyticsResponse,
  LoginFilters,
  UserLoginSummary,
  Tenant,
  TenantCreate,
  TenantUpdate,
  TenantListResponse,
  AlertHistoryList,
  AlertFilters,
  AnomalyDetail,
  DashboardStats,
  SystemSettings,
  SystemSettingsUpdate,
  UserPreferences,
  UserPreferencesUpdate,
  DetectionThresholds,
  DetectionThresholdsUpdate,
  ApiKey,
  ApiKeyCreate,
  ApiKeyCreateResponse,
  ApiKeyUpdate,
  WebhookTestRequest,
  WebhookTestResponse,
  ConfigExportRequest,
  ConfigExportResponse,
  ConfigImportRequest,
  ConfigImportResponse,
  ConfigBackup,
  AlertRule,
  AlertRuleCreate,
  AlertRuleUpdate,
  WebhookConfig,
  WebhookCreate,
  WebhookUpdate,
  LoginRequest,
  LoginResponse,
  User,
  UserInternal,
  UserCreate,
  UserUpdate,
  UserListResponse,
} from '@/types';
import type {
  TimeRange,
  DashboardDataResponse,
  DashboardSummary,
  LoginActivityTimeline,
  GeoHeatmapData,
  AnomalyTrendData,
  TopRiskUsersData,
  AlertVolumeData,
  AnomalyBreakdownItem,
} from '@/hooks/useDashboard';

const API_BASE_URL = '/api/v1';

class ApiService {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: 30000,
    });

    // Add request interceptor to include auth token
    this.client.interceptors.request.use(
      config => {
        const token = localStorage.getItem('specterdefence-storage');
        if (token) {
          try {
            const parsed = JSON.parse(token);
            if (parsed.state?.token) {
              config.headers.Authorization = `Bearer ${parsed.state.token}`;
            }
          } catch {
            // Ignore parse errors
          }
        }
        return config;
      },
      error => Promise.reject(error)
    );

    // Add response interceptor for error handling
    this.client.interceptors.response.use(
      response => response,
      (error: AxiosError) => {
        if (error.response) {
          // Handle 401 Unauthorized - redirect to login
          if (error.response.status === 401) {
            localStorage.removeItem('specterdefence-storage');
            window.location.href = '/login';
          }
          console.error('API Error:', error.response.data);
        } else if (error.request) {
          console.error('Network Error:', error.message);
        }
        return Promise.reject(error);
      }
    );
  }

  // ============== Analytics ==============

  async getLoginAnalytics(filters: LoginFilters): Promise<LoginAnalyticsResponse> {
    const params = new URLSearchParams();

    if (filters.tenant_id) params.append('tenant_id', filters.tenant_id);
    if (filters.user) params.append('user', filters.user);
    if (filters.start_time) params.append('start_time', filters.start_time);
    if (filters.end_time) params.append('end_time', filters.end_time);
    if (filters.ip) params.append('ip', filters.ip);
    if (filters.country) params.append('country', filters.country);
    if (filters.country_code) params.append('country_code', filters.country_code);
    if (filters.status) params.append('status', filters.status);
    if (filters.has_anomaly !== undefined)
      params.append('has_anomaly', String(filters.has_anomaly));
    if (filters.anomaly_type) params.append('anomaly_type', filters.anomaly_type);
    if (filters.min_risk_score) params.append('min_risk_score', String(filters.min_risk_score));
    if (filters.page) params.append('page', String(filters.page));
    if (filters.page_size) params.append('page_size', String(filters.page_size));

    const response = await this.client.get(`/analytics/logins?${params.toString()}`);
    return response.data;
  }

  async getUserLoginSummary(userEmail: string, tenantId: string): Promise<UserLoginSummary> {
    const response = await this.client.get(
      `/analytics/logins/${encodeURIComponent(userEmail)}/summary?tenant_id=${tenantId}`
    );
    return response.data;
  }

  async getRecentAnomalies(filters: AlertFilters): Promise<AnomalyDetail[]> {
    const params = new URLSearchParams();

    if (filters.tenant_id) params.append('tenant_id', filters.tenant_id);
    if (filters.hours) params.append('hours', String(filters.hours));
    if (filters.min_risk_score) params.append('min_risk_score', String(filters.min_risk_score));
    if (filters.limit) params.append('limit', String(filters.limit));

    const response = await this.client.get(`/analytics/anomalies/recent?${params.toString()}`);
    return response.data;
  }

  // ============== Tenants ==============

  async getTenants(): Promise<TenantListResponse> {
    const response = await this.client.get('/tenants/');
    const data = response.data;
    // Backend returns a plain array; wrap it into the shape the frontend expects
    if (Array.isArray(data)) {
      return { items: data, total: data.length };
    }
    return data;
  }

  async getTenant(id: string): Promise<Tenant> {
    const response = await this.client.get(`/tenants/${id}`);
    return response.data;
  }

  async createTenant(data: TenantCreate): Promise<Tenant> {
    const response = await this.client.post('/tenants/', data);
    return response.data;
  }

  async updateTenant(id: string, data: TenantUpdate): Promise<Tenant> {
    const response = await this.client.patch(`/tenants/${id}`, data);
    return response.data;
  }

  async deleteTenant(id: string): Promise<void> {
    await this.client.delete(`/tenants/${id}`);
  }

  async validateTenant(data: TenantCreate): Promise<{ valid: boolean; message?: string }> {
    const response = await this.client.post('/tenants/validate', data);
    return response.data;
  }

  // ============== Users ==============

  async getUsers(): Promise<UserListResponse> {
    const response = await this.client.get('/users/');
    const data = response.data;
    if (Array.isArray(data)) {
      return { items: data, total: data.length };
    }
    return data;
  }

  async createUser(data: UserCreate): Promise<UserInternal> {
    const response = await this.client.post('/users/', data);
    return response.data;
  }

  async updateUser(id: number, data: UserUpdate): Promise<UserInternal> {
    const response = await this.client.patch(`/users/${id}`, data);
    return response.data;
  }

  async getUserTenants(id: number): Promise<Tenant[]> {
    const response = await this.client.get(`/users/${id}/tenants`);
    return response.data;
  }

  async assignUserTenant(userId: number, tenantId: string): Promise<void> {
    await this.client.post(`/users/${userId}/tenants/${tenantId}`);
  }

  async unassignUserTenant(userId: number, tenantId: string): Promise<void> {
    await this.client.delete(`/users/${userId}/tenants/${tenantId}`);
  }

  // ============== Alerts ==============

  async getAlertHistory(filters: AlertFilters): Promise<AlertHistoryList> {
    const params = new URLSearchParams();

    if (filters.tenant_id) params.append('tenant_id', filters.tenant_id);
    if (filters.hours) params.append('hours', String(filters.hours));
    if (filters.limit) params.append('limit', String(filters.limit));
    if (filters.event_type) params.append('event_type', filters.event_type);
    if (filters.severity) params.append('severity', filters.severity);

    const response = await this.client.get(`/alerts/history?${params.toString()}`);
    return response.data;
  }

  // ============== Dashboard Stats (via summary endpoint) ==============

  async getDashboardStats(): Promise<DashboardStats> {
    const summary = await this.getDashboardSummary();
    return {
      total_logins: summary.total_logins_24h,
      failed_logins: summary.failed_logins_24h,
      anomalies_today: summary.anomalies_today,
      active_tenants: summary.active_tenants,
    };
  }

  // ============== Dashboard API ==============

  async getDashboardData(timeRange: TimeRange, tenantId?: string): Promise<DashboardDataResponse> {
    const params = new URLSearchParams();
    params.append('time_range', timeRange);
    if (tenantId) params.append('tenant_id', tenantId);

    const response = await this.client.get(`/dashboard/full?${params.toString()}`);
    return response.data;
  }

  async getDashboardSummary(tenantId?: string): Promise<DashboardSummary> {
    const params = new URLSearchParams();
    if (tenantId) params.append('tenant_id', tenantId);

    const response = await this.client.get(`/dashboard/summary?${params.toString()}`);
    return response.data;
  }

  async getLoginTimeline(timeRange: TimeRange, tenantId?: string): Promise<LoginActivityTimeline> {
    const params = new URLSearchParams();
    params.append('time_range', timeRange);
    if (tenantId) params.append('tenant_id', tenantId);

    const response = await this.client.get(`/dashboard/login-timeline?${params.toString()}`);
    return response.data;
  }

  async getGeoHeatmap(timeRange: TimeRange, tenantId?: string): Promise<GeoHeatmapData> {
    const params = new URLSearchParams();
    params.append('time_range', timeRange);
    if (tenantId) params.append('tenant_id', tenantId);

    const response = await this.client.get(`/dashboard/geo-heatmap?${params.toString()}`);
    return response.data;
  }

  async getSuccessfulLoginLocations(
    timeRange: TimeRange,
    tenantId?: string
  ): Promise<GeoHeatmapData> {
    const params = new URLSearchParams();
    params.append('time_range', timeRange);
    if (tenantId) params.append('tenant_id', tenantId);

    const response = await this.client.get(
      `/dashboard/successful-login-locations?${params.toString()}`
    );
    return response.data;
  }

  async getAnomalyTrend(timeRange: TimeRange, tenantId?: string): Promise<AnomalyTrendData> {
    const params = new URLSearchParams();
    params.append('time_range', timeRange);
    if (tenantId) params.append('tenant_id', tenantId);

    const response = await this.client.get(`/dashboard/anomaly-trend?${params.toString()}`);
    return response.data;
  }

  async getTopRiskUsers(limit: number = 10, tenantId?: string): Promise<TopRiskUsersData> {
    const params = new URLSearchParams();
    params.append('limit', String(limit));
    if (tenantId) params.append('tenant_id', tenantId);

    const response = await this.client.get(`/dashboard/top-risk-users?${params.toString()}`);
    return response.data;
  }

  async getAlertVolume(timeRange: TimeRange, tenantId?: string): Promise<AlertVolumeData> {
    const params = new URLSearchParams();
    params.append('time_range', timeRange);
    if (tenantId) params.append('tenant_id', tenantId);

    const response = await this.client.get(`/dashboard/alert-volume?${params.toString()}`);
    return response.data;
  }

  async getAnomalyBreakdown(
    timeRange: TimeRange,
    tenantId?: string
  ): Promise<AnomalyBreakdownItem[]> {
    const params = new URLSearchParams();
    params.append('time_range', timeRange);
    if (tenantId) params.append('tenant_id', tenantId);

    const response = await this.client.get(`/dashboard/anomaly-breakdown?${params.toString()}`);
    return response.data;
  }

  async exportDashboard(
    format: 'csv' | 'json' | 'pdf',
    timeRange: TimeRange,
    tenantId?: string
  ): Promise<Blob> {
    const params = new URLSearchParams();
    params.append('format', format);
    params.append('time_range', timeRange);
    if (tenantId) params.append('tenant_id', tenantId);

    const response = await this.client.get(
      `/dashboard/export/download/${format}?${params.toString()}`,
      {
        responseType: 'blob',
      }
    );
    return response.data;
  }

  // Export logins to CSV
  async exportLoginsToCSV(filters: LoginFilters): Promise<Blob> {
    const params = new URLSearchParams();

    // Add all filters
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        params.append(key, String(value));
      }
    });

    const response = await this.client.get(`/analytics/logins/export?${params.toString()}`, {
      responseType: 'blob',
    });
    return response.data;
  }

  // ============== Settings API ==============

  // System Settings
  async getSystemSettings(): Promise<SystemSettings> {
    const response = await this.client.get('/settings/system');
    return response.data;
  }

  async updateSystemSettings(data: SystemSettingsUpdate): Promise<SystemSettings> {
    const response = await this.client.patch('/settings/system', data);
    return response.data;
  }

  // User Preferences
  async getUserPreferences(userEmail: string): Promise<UserPreferences> {
    const response = await this.client.get(
      `/settings/preferences/${encodeURIComponent(userEmail)}`
    );
    return response.data;
  }

  async updateUserPreferences(
    userEmail: string,
    data: UserPreferencesUpdate
  ): Promise<UserPreferences> {
    const response = await this.client.patch(
      `/settings/preferences/${encodeURIComponent(userEmail)}`,
      data
    );
    return response.data;
  }

  // Detection Thresholds
  async getDetectionThresholds(tenantId?: string): Promise<DetectionThresholds> {
    const params = new URLSearchParams();
    if (tenantId) params.append('tenant_id', tenantId);
    const response = await this.client.get(`/settings/detection?${params.toString()}`);
    return response.data;
  }

  async updateDetectionThresholds(
    data: DetectionThresholdsUpdate,
    tenantId?: string
  ): Promise<DetectionThresholds> {
    const params = new URLSearchParams();
    if (tenantId) params.append('tenant_id', tenantId);
    const response = await this.client.patch(`/settings/detection?${params.toString()}`, data);
    return response.data;
  }

  // API Keys
  async getApiKeys(tenantId?: string, includeInactive?: boolean): Promise<ApiKey[]> {
    const params = new URLSearchParams();
    if (tenantId) params.append('tenant_id', tenantId);
    if (includeInactive) params.append('include_inactive', 'true');
    const response = await this.client.get(`/settings/api-keys?${params.toString()}`);
    return response.data;
  }

  async createApiKey(data: ApiKeyCreate): Promise<ApiKeyCreateResponse> {
    const response = await this.client.post('/settings/api-keys', data);
    return response.data;
  }

  async getApiKey(keyId: string): Promise<ApiKey> {
    const response = await this.client.get(`/settings/api-keys/${keyId}`);
    return response.data;
  }

  async updateApiKey(keyId: string, data: ApiKeyUpdate): Promise<ApiKey> {
    const response = await this.client.patch(`/settings/api-keys/${keyId}`, data);
    return response.data;
  }

  async revokeApiKey(keyId: string): Promise<void> {
    await this.client.delete(`/settings/api-keys/${keyId}`);
  }

  // Webhook Test
  async testWebhook(data: WebhookTestRequest): Promise<WebhookTestResponse> {
    const response = await this.client.post('/settings/webhooks/test', data);
    return response.data;
  }

  // Configuration Import/Export
  async exportConfiguration(data: ConfigExportRequest): Promise<ConfigExportResponse> {
    const response = await this.client.post('/settings/config/export', data);
    return response.data;
  }

  async importConfiguration(data: ConfigImportRequest): Promise<ConfigImportResponse> {
    const response = await this.client.post('/settings/config/import', data);
    return response.data;
  }

  async getConfigurationBackups(): Promise<ConfigBackup[]> {
    const response = await this.client.get('/settings/config/backups');
    return response.data;
  }

  async deleteConfigurationBackup(backupId: string): Promise<void> {
    await this.client.delete(`/settings/config/backups/${backupId}`);
  }

  async downloadConfigurationBackup(backupId: string): Promise<Blob> {
    const response = await this.client.get(`/settings/config/export/${backupId}/download`, {
      responseType: 'blob',
    });
    return response.data;
  }

  // Alert Rules
  async getAlertRules(): Promise<AlertRule[]> {
    const response = await this.client.get('/alerts/rules');
    return response.data;
  }

  async createAlertRule(data: AlertRuleCreate): Promise<AlertRule> {
    const response = await this.client.post('/alerts/rules', data);
    return response.data;
  }

  async updateAlertRule(ruleId: string, data: AlertRuleUpdate): Promise<AlertRule> {
    const response = await this.client.patch(`/alerts/rules/${ruleId}`, data);
    return response.data;
  }

  async deleteAlertRule(ruleId: string): Promise<void> {
    await this.client.delete(`/alerts/rules/${ruleId}`);
  }

  // Webhooks
  async getWebhooks(): Promise<WebhookConfig[]> {
    const response = await this.client.get('/alerts/webhooks');
    return response.data;
  }

  async createWebhook(data: WebhookCreate): Promise<WebhookConfig> {
    const response = await this.client.post('/alerts/webhooks', data);
    return response.data;
  }

  async updateWebhook(webhookId: string, data: WebhookUpdate): Promise<WebhookConfig> {
    const response = await this.client.patch(`/alerts/webhooks/${webhookId}`, data);
    return response.data;
  }

  async deleteWebhook(webhookId: string): Promise<void> {
    await this.client.delete(`/alerts/webhooks/${webhookId}`);
  }

  // Tenant Settings
  async getTenantSettings(tenantId: string): Promise<Record<string, unknown>> {
    const response = await this.client.get(`/settings/tenants/${tenantId}`);
    return response.data;
  }

  // ============== Authentication ==============

  async login(data: LoginRequest): Promise<LoginResponse> {
    const response = await this.client.post('/auth/local/login', data);
    return response.data;
  }

  async logout(): Promise<{ message: string }> {
    const response = await this.client.post('/auth/local/logout');
    return response.data;
  }

  async getCurrentUser(): Promise<User> {
    const response = await this.client.get('/auth/local/me');
    return response.data;
  }

  async checkAuth(): Promise<{ authenticated: boolean; username: string }> {
    const response = await this.client.get('/auth/local/check');
    return response.data;
  }

  async changePassword(
    current_password: string,
    new_password: string
  ): Promise<{ message: string }> {
    const response = await this.client.post('/auth/local/change-password', {
      current_password,
      new_password,
    });
    return response.data;
  }

  // ============== Conditional Access Policies ==============

  async getCAPolicies(params?: {
    tenant_id?: string;
    state?: string;
    is_baseline_policy?: boolean;
    limit?: number;
    offset?: number;
  }): Promise<import('@/types/securityTypes').CAPolicyListResponse> {
    const searchParams = new URLSearchParams();
    if (params?.tenant_id) searchParams.append('tenant_id', params.tenant_id);
    if (params?.state) searchParams.append('state', params.state);
    if (params?.is_baseline_policy !== undefined)
      searchParams.append('is_baseline_policy', String(params.is_baseline_policy));
    if (params?.limit) searchParams.append('limit', String(params.limit));
    if (params?.offset) searchParams.append('offset', String(params.offset));
    const response = await this.client.get(`/ca-policies/?${searchParams.toString()}`);
    return response.data;
  }

  async getCAPolicySummary(
    tenantId: string
  ): Promise<import('@/types/securityTypes').CAPolicySummary> {
    const response = await this.client.get(`/ca-policies/tenants/${tenantId}/summary`);
    return response.data;
  }

  async getCAPolicyChanges(params?: {
    tenant_id?: string;
    change_type?: string;
    limit?: number;
    offset?: number;
  }): Promise<import('@/types/securityTypes').CAPolicyChangeListResponse> {
    const searchParams = new URLSearchParams();
    if (params?.tenant_id) searchParams.append('tenant_id', params.tenant_id);
    if (params?.change_type) searchParams.append('change_type', params.change_type);
    if (params?.limit) searchParams.append('limit', String(params.limit));
    if (params?.offset) searchParams.append('offset', String(params.offset));
    const response = await this.client.get(`/ca-policies/changes?${searchParams.toString()}`);
    return response.data;
  }

  async getCAPolicyAlerts(params?: {
    tenant_id?: string;
    acknowledged?: boolean;
    severity?: string;
    limit?: number;
    offset?: number;
  }): Promise<import('@/types/securityTypes').CAPolicyAlertListResponse> {
    const searchParams = new URLSearchParams();
    if (params?.tenant_id) searchParams.append('tenant_id', params.tenant_id);
    if (params?.acknowledged !== undefined)
      searchParams.append('acknowledged', String(params.acknowledged));
    if (params?.severity) searchParams.append('severity', params.severity);
    if (params?.limit) searchParams.append('limit', String(params.limit));
    if (params?.offset) searchParams.append('offset', String(params.offset));
    const response = await this.client.get(`/ca-policies/alerts?${searchParams.toString()}`);
    return response.data;
  }

  // ============== Mailbox Rules ==============

  async getMailboxRules(params?: {
    tenant_id?: string;
    user_email?: string;
    status?: string;
    severity?: string;
    rule_type?: string;
    limit?: number;
    offset?: number;
  }): Promise<import('@/types/securityTypes').MailboxRuleListResponse> {
    const searchParams = new URLSearchParams();
    if (params?.tenant_id) searchParams.append('tenant_id', params.tenant_id);
    if (params?.user_email) searchParams.append('user_email', params.user_email);
    if (params?.status) searchParams.append('status', params.status);
    if (params?.severity) searchParams.append('severity', params.severity);
    if (params?.rule_type) searchParams.append('rule_type', params.rule_type);
    if (params?.limit) searchParams.append('limit', String(params.limit));
    if (params?.offset) searchParams.append('offset', String(params.offset));
    const response = await this.client.get(`/mailbox-rules/?${searchParams.toString()}`);
    return response.data;
  }

  async getMailboxRuleSummary(
    tenantId: string
  ): Promise<import('@/types/securityTypes').MailboxRuleSummary> {
    const response = await this.client.get(`/mailbox-rules/tenants/${tenantId}/summary`);
    return response.data;
  }

  async getMailboxRuleAlerts(params?: {
    tenant_id?: string;
    acknowledged?: boolean;
    severity?: string;
    limit?: number;
    offset?: number;
  }): Promise<import('@/types/securityTypes').MailboxRuleAlertListResponse> {
    const searchParams = new URLSearchParams();
    if (params?.tenant_id) searchParams.append('tenant_id', params.tenant_id);
    if (params?.acknowledged !== undefined)
      searchParams.append('acknowledged', String(params.acknowledged));
    if (params?.severity) searchParams.append('severity', params.severity);
    if (params?.limit) searchParams.append('limit', String(params.limit));
    if (params?.offset) searchParams.append('offset', String(params.offset));
    const response = await this.client.get(`/mailbox-rules/alerts?${searchParams.toString()}`);
    return response.data;
  }

  // ============== MFA Report ==============

  async getMFASummary(
    tenantId: string
  ): Promise<import('@/types/securityTypes').MFAEnrollmentSummary> {
    const response = await this.client.get(`/mfa-report/?tenant_id=${tenantId}`);
    return response.data;
  }

  async getMFAUsers(params: {
    tenant_id: string;
    is_mfa_registered?: boolean;
    is_admin?: boolean;
    mfa_strength?: string;
    needs_attention?: boolean;
    limit?: number;
    offset?: number;
  }): Promise<import('@/types/securityTypes').MFAUserListResponse> {
    const searchParams = new URLSearchParams();
    searchParams.append('tenant_id', params.tenant_id);
    if (params.is_mfa_registered !== undefined)
      searchParams.append('is_mfa_registered', String(params.is_mfa_registered));
    if (params.is_admin !== undefined) searchParams.append('is_admin', String(params.is_admin));
    if (params.mfa_strength) searchParams.append('mfa_strength', params.mfa_strength);
    if (params.needs_attention !== undefined)
      searchParams.append('needs_attention', String(params.needs_attention));
    if (params.limit) searchParams.append('limit', String(params.limit));
    if (params.offset) searchParams.append('offset', String(params.offset));
    const response = await this.client.get(`/mfa-report/users?${searchParams.toString()}`);
    return response.data;
  }

  async getMFATrends(
    tenantId: string,
    days: number = 30
  ): Promise<import('@/types/securityTypes').MFAEnrollmentTrendsResponse> {
    const response = await this.client.get(`/mfa-report/trends?tenant_id=${tenantId}&days=${days}`);
    return response.data;
  }

  async getMFAMethodDistribution(
    tenantId: string
  ): Promise<import('@/types/securityTypes').MFAMethodsDistributionResponse> {
    const response = await this.client.get(`/mfa-report/method-distribution?tenant_id=${tenantId}`);
    return response.data;
  }

  async getMFAStrengthDistribution(
    tenantId: string
  ): Promise<import('@/types/securityTypes').MFAStrengthDistributionResponse> {
    const response = await this.client.get(
      `/mfa-report/strength-distribution?tenant_id=${tenantId}`
    );
    return response.data;
  }

  async getAdminsWithoutMFA(
    tenantId: string
  ): Promise<import('@/types/securityTypes').AdminsWithoutMFAResponse> {
    const response = await this.client.get(`/mfa-report/admins-without-mfa?tenant_id=${tenantId}`);
    return response.data;
  }

  // ============== OAuth Applications ==============

  async getOAuthApps(params?: {
    tenant_id?: string;
    status?: string;
    risk_level?: string;
    publisher_type?: string;
    is_internal?: boolean;
    exclude_microsoft?: boolean;
    limit?: number;
    offset?: number;
  }): Promise<import('@/types/securityTypes').OAuthAppListResponse> {
    const searchParams = new URLSearchParams();
    if (params?.tenant_id) searchParams.append('tenant_id', params.tenant_id);
    if (params?.status) searchParams.append('status', params.status);
    if (params?.risk_level) searchParams.append('risk_level', params.risk_level);
    if (params?.publisher_type) searchParams.append('publisher_type', params.publisher_type);
    if (params?.is_internal !== undefined)
      searchParams.append('is_internal', String(params.is_internal));
    if (params?.exclude_microsoft !== undefined)
      searchParams.append('exclude_microsoft', String(params.exclude_microsoft));
    if (params?.limit) searchParams.append('limit', String(params.limit));
    if (params?.offset) searchParams.append('offset', String(params.offset));
    const response = await this.client.get(`/oauth-apps/?${searchParams.toString()}`);
    return response.data;
  }

  async getOAuthAppSummary(
    tenantId: string
  ): Promise<import('@/types/securityTypes').OAuthAppsSummary> {
    const response = await this.client.get(`/oauth-apps/tenants/${tenantId}/summary`);
    return response.data;
  }

  async getOAuthAppAlerts(params?: {
    tenant_id?: string;
    acknowledged?: boolean;
    severity?: string;
    limit?: number;
    offset?: number;
  }): Promise<import('@/types/securityTypes').OAuthAppAlertListResponse> {
    const searchParams = new URLSearchParams();
    if (params?.tenant_id) searchParams.append('tenant_id', params.tenant_id);
    if (params?.acknowledged !== undefined)
      searchParams.append('acknowledged', String(params.acknowledged));
    if (params?.severity) searchParams.append('severity', params.severity);
    if (params?.limit) searchParams.append('limit', String(params.limit));
    if (params?.offset) searchParams.append('offset', String(params.offset));
    const response = await this.client.get(`/oauth-apps/alerts?${searchParams.toString()}`);
    return response.data;
  }

  // ============== SharePoint ==============

  async getSharePointMetrics(tenantId?: string): Promise<any> {
    const params = new URLSearchParams();
    if (tenantId) params.append('tenant_id', tenantId);
    const response = await this.client.get(`/sharepoint/metrics?${params.toString()}`);
    return response.data;
  }

  async getSharePointLinks(
    tenantId?: string,
    limit: number = 50,
    offset: number = 0
  ): Promise<any[]> {
    const params = new URLSearchParams();
    if (tenantId) params.append('tenant_id', tenantId);
    params.append('limit', String(limit));
    params.append('offset', String(offset));
    const response = await this.client.get(`/sharepoint/sharing-links?${params.toString()}`);
    return response.data;
  }

  async getDlpStats(days: number = 30, tenantId?: string): Promise<any> {
    const params = new URLSearchParams();
    params.append('days', String(days));
    if (tenantId && tenantId !== 'all') params.append('tenant_id', tenantId);
    const response = await this.client.get(`/dlp/stats?${params.toString()}`);
    return response.data;
  }

  async getDlpEvents(limit: number = 50, tenantId?: string): Promise<any> {
    const params = new URLSearchParams();
    params.append('limit', String(limit));
    if (tenantId) params.append('tenant_id', tenantId);
    const response = await this.client.get(`/dlp?${params.toString()}`);
    return response.data;
  }
  async getMailboxSecurityStats(days: number = 30, tenantId?: string): Promise<any> {
    const params = new URLSearchParams();
    params.append('days', String(days));
    if (tenantId && tenantId !== 'all') params.append('tenant_id', tenantId);
    const response = await this.client.get(`/mailbox-security/stats?${params.toString()}`);
    return response.data;
  }

  async getMailboxAccessEvents(limit: number = 50, tenantId?: string): Promise<any> {
    const params = new URLSearchParams();
    params.append('limit', String(limit));
    if (tenantId && tenantId !== 'all') params.append('tenant_id', tenantId);
    const response = await this.client.get(`/mailbox-security/access?${params.toString()}`);
    return response.data;
  }
}

export const apiService = new ApiService();
export default apiService;
