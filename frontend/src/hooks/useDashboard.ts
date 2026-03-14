import { useQuery } from '@tanstack/react-query';
import { apiService } from '@/services/api';

export type TimeRange = '7d' | '30d' | '90d';

// Query keys
export const dashboardQueryKeys = {
  full: (timeRange: TimeRange, tenantId?: string) =>
    ['dashboard', 'full', timeRange, tenantId] as const,
  summary: (tenantId?: string) => ['dashboard', 'summary', tenantId] as const,
  loginTimeline: (timeRange: TimeRange, tenantId?: string) =>
    ['dashboard', 'login-timeline', timeRange, tenantId] as const,
  geoHeatmap: (timeRange: TimeRange, tenantId?: string) =>
    ['dashboard', 'geo-heatmap', timeRange, tenantId] as const,
  successfulLoginLocations: (timeRange: TimeRange, tenantId?: string) =>
    ['dashboard', 'successful-login-locations', timeRange, tenantId] as const,
  anomalyTrend: (timeRange: TimeRange, tenantId?: string) =>
    ['dashboard', 'anomaly-trend', timeRange, tenantId] as const,
  topRiskUsers: (tenantId?: string) => ['dashboard', 'top-risk-users', tenantId] as const,
  alertVolume: (timeRange: TimeRange, tenantId?: string) =>
    ['dashboard', 'alert-volume', timeRange, tenantId] as const,
  anomalyBreakdown: (timeRange: TimeRange, tenantId?: string) =>
    ['dashboard', 'anomaly-breakdown', timeRange, tenantId] as const,
};

// Dashboard summary interface
export interface DashboardSummary {
  total_logins_24h: number;
  failed_logins_24h: number;
  active_users_24h: number;
  anomalies_today: number;
  alerts_today: number;
  active_tenants: number;
  avg_risk_score: number;
  login_success_rate: number;
  top_threats: string[];
  mfa_compliance_rate: number;
  high_risk_oauth_apps: number;
  disabled_ca_policies: number;
  suspicious_mailbox_rules: number;
  total_protected_users: number;
}

// Login timeline interfaces
export interface LoginActivityPoint {
  timestamp: string;
  successful_logins: number;
  failed_logins: number;
  total_logins: number;
}

export interface LoginActivityTimeline {
  data: LoginActivityPoint[];
  time_range: TimeRange;
  total_successful: number;
  total_failed: number;
  change_percent: number;
}

// Geo heatmap interfaces
export interface GeoLocationPoint {
  country_code: string;
  country_name: string;
  latitude: number;
  longitude: number;
  login_count: number;
  user_count: number;
  risk_score_avg: number;
  success_count: number;
  failed_count: number;
}

export interface GeoHeatmapData {
  locations: GeoLocationPoint[];
  total_countries: number;
  top_country: string | null;
  top_country_count: number;
}

// Anomaly trend interfaces
export interface AnomalyTrendPoint {
  date: string;
  count: number;
  types: Record<string, number>;
}

export interface AnomalyTrendData {
  data: AnomalyTrendPoint[];
  time_range: TimeRange;
  total_anomalies: number;
  top_type: string | null;
  change_percent: number;
}

// Top risk users interfaces
export interface RiskUser {
  user_email: string;
  tenant_id: string;
  risk_score: number;
  anomaly_count: number;
  last_anomaly_time?: string;
  top_anomaly_types: string[];
  country_count: number;
}

export interface TopRiskUsersData {
  users: RiskUser[];
  total_users: number;
  avg_risk_score: number;
}

// Alert volume interfaces
export interface AlertVolumePoint {
  timestamp: string;
  critical: number;
  high: number;
  medium: number;
  low: number;
  total: number;
}

export interface AlertVolumeData {
  data: AlertVolumePoint[];
  time_range: TimeRange;
  total_by_severity: Record<string, number>;
  peak_volume: number;
  peak_time: string | null;
}

// Anomaly breakdown interfaces
export interface AnomalyBreakdownItem {
  type: string;
  count: number;
  percentage: number;
  avg_risk_score: number;
}

// Full dashboard response
export interface DashboardDataResponse {
  summary: DashboardSummary;
  login_timeline: LoginActivityTimeline;
  geo_heatmap: GeoHeatmapData;
  anomaly_trend: AnomalyTrendData;
  top_risk_users: TopRiskUsersData;
  alert_volume: AlertVolumeData;
  anomaly_breakdown: AnomalyBreakdownItem[];
  generated_at: string;
  time_range: TimeRange;
}

// ============== Hooks ==============

export function useDashboardData(timeRange: TimeRange = '30d', tenantId?: string) {
  return useQuery({
    queryKey: dashboardQueryKeys.full(timeRange, tenantId),
    queryFn: () => apiService.getDashboardData(timeRange, tenantId),
    staleTime: 60000, // 1 minute
    refetchInterval: 300000, // 5 minutes
  });
}

export function useDashboardSummary(tenantId?: string) {
  return useQuery({
    queryKey: dashboardQueryKeys.summary(tenantId),
    queryFn: () => apiService.getDashboardSummary(tenantId),
    staleTime: 30000, // 30 seconds
    refetchInterval: 60000, // 1 minute
  });
}

export function useLoginTimeline(timeRange: TimeRange = '30d', tenantId?: string) {
  return useQuery({
    queryKey: dashboardQueryKeys.loginTimeline(timeRange, tenantId),
    queryFn: () => apiService.getLoginTimeline(timeRange, tenantId),
    staleTime: 60000,
  });
}

export function useGeoHeatmap(timeRange: TimeRange = '30d', tenantId?: string) {
  return useQuery({
    queryKey: dashboardQueryKeys.geoHeatmap(timeRange, tenantId),
    queryFn: () => apiService.getGeoHeatmap(timeRange, tenantId),
    staleTime: 120000, // 2 minutes
  });
}

export function useSuccessfulLoginLocations(timeRange: TimeRange = '30d', tenantId?: string) {
  return useQuery({
    queryKey: dashboardQueryKeys.successfulLoginLocations(timeRange, tenantId),
    queryFn: () => apiService.getSuccessfulLoginLocations(timeRange, tenantId),
    staleTime: 120000, // 2 minutes
  });
}

export function useAnomalyTrend(timeRange: TimeRange = '30d', tenantId?: string) {
  return useQuery({
    queryKey: dashboardQueryKeys.anomalyTrend(timeRange, tenantId),
    queryFn: () => apiService.getAnomalyTrend(timeRange, tenantId),
    staleTime: 60000,
  });
}

export function useTopRiskUsers(limit: number = 10, tenantId?: string) {
  return useQuery({
    queryKey: dashboardQueryKeys.topRiskUsers(tenantId),
    queryFn: () => apiService.getTopRiskUsers(limit, tenantId),
    staleTime: 60000,
  });
}

export function useAlertVolume(timeRange: TimeRange = '30d', tenantId?: string) {
  return useQuery({
    queryKey: dashboardQueryKeys.alertVolume(timeRange, tenantId),
    queryFn: () => apiService.getAlertVolume(timeRange, tenantId),
    staleTime: 60000,
  });
}

export function useAnomalyBreakdown(timeRange: TimeRange = '30d', tenantId?: string) {
  return useQuery({
    queryKey: dashboardQueryKeys.anomalyBreakdown(timeRange, tenantId),
    queryFn: () => apiService.getAnomalyBreakdown(timeRange, tenantId),
    staleTime: 120000,
  });
}
