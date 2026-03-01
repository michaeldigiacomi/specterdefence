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
  DashboardStats
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
  AnomalyBreakdownItem
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

    // Add response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        if (error.response) {
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
    if (filters.has_anomaly !== undefined) params.append('has_anomaly', String(filters.has_anomaly));
    if (filters.anomaly_type) params.append('anomaly_type', filters.anomaly_type);
    if (filters.min_risk_score) params.append('min_risk_score', String(filters.min_risk_score));
    if (filters.page) params.append('page', String(filters.page));
    if (filters.page_size) params.append('page_size', String(filters.page_size));

    const response = await this.client.get(`/analytics/logins?${params.toString()}`);
    return response.data;
  }

  async getUserLoginSummary(userEmail: string, tenantId: string): Promise<UserLoginSummary> {
    const response = await this.client.get(`/analytics/logins/${encodeURIComponent(userEmail)}/summary?tenant_id=${tenantId}`);
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
    const response = await this.client.get('/tenants');
    return response.data;
  }

  async getTenant(id: string): Promise<Tenant> {
    const response = await this.client.get(`/tenants/${id}`);
    return response.data;
  }

  async createTenant(data: TenantCreate): Promise<Tenant> {
    const response = await this.client.post('/tenants', data);
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

  // ============== Dashboard Stats (Legacy) ==============

  async getDashboardStats(): Promise<DashboardStats> {
    // Aggregate data from multiple endpoints
    const [loginsResponse, tenantsResponse, alertsResponse] = await Promise.all([
      this.getLoginAnalytics({ page_size: 1, start_time: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString() }),
      this.getTenants(),
      this.getAlertHistory({ hours: 24, limit: 1000 }),
    ]);

    const activeTenants = tenantsResponse.items.filter(t => t.is_active).length;
    const anomaliesToday = alertsResponse.items.filter(a => {
      const sentAt = new Date(a.sent_at);
      const today = new Date();
      return sentAt.toDateString() === today.toDateString();
    }).length;

    // Get failed logins from the last 24h
    const failedLoginsResponse = await this.getLoginAnalytics({ 
      status: 'failed', 
      page_size: 1,
      start_time: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString()
    });

    return {
      total_logins: loginsResponse.total,
      failed_logins: failedLoginsResponse.total,
      anomalies_today: anomaliesToday,
      active_tenants: activeTenants,
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

  async getAnomalyBreakdown(timeRange: TimeRange, tenantId?: string): Promise<AnomalyBreakdownItem[]> {
    const params = new URLSearchParams();
    params.append('time_range', timeRange);
    if (tenantId) params.append('tenant_id', tenantId);

    const response = await this.client.get(`/dashboard/anomaly-breakdown?${params.toString()}`);
    return response.data;
  }

  async exportDashboard(format: 'csv' | 'json' | 'pdf', timeRange: TimeRange, tenantId?: string): Promise<Blob> {
    const params = new URLSearchParams();
    params.append('format', format);
    params.append('time_range', timeRange);
    if (tenantId) params.append('tenant_id', tenantId);

    const response = await this.client.get(`/dashboard/export/download/${format}?${params.toString()}`, {
      responseType: 'blob',
    });
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
}

export const apiService = new ApiService();
export default apiService;
