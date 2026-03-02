/** Login record response from API */
export interface LoginRecord {
  id: string;
  user_email: string;
  ip_address: string;
  country?: string;
  country_code?: string;
  city?: string;
  region?: string;
  latitude?: number;
  longitude?: number;
  login_time: string;
  is_success: boolean;
  failure_reason?: string;
  anomaly_flags: string[];
  risk_score: number;
}

/** Anomaly detail response */
export interface AnomalyDetail {
  type: string;
  user: string;
  locations?: string[];
  time_diff_minutes?: number;
  risk_score: number;
  country?: string;
  previous_countries?: string[];
  details?: Record<string, unknown>;
}

/** Login analytics response */
export interface LoginAnalyticsResponse {
  logins: LoginRecord[];
  total: number;
  page: number;
  page_size: number;
  filters_applied: Record<string, unknown>;
  anomalies: AnomalyDetail[];
}

/** User login summary */
export interface UserLoginSummary {
  user_email: string;
  tenant_id: string;
  total_logins: number;
  known_countries: string[];
  known_ips_count: number;
  last_login_time?: string;
  last_login_country?: string;
  failed_attempts_24h: number;
  recent_anomalies: Record<string, unknown>[];
}

/** Login filters */
export interface LoginFilters {
  tenant_id?: string;
  user?: string;
  start_time?: string;
  end_time?: string;
  ip?: string;
  country?: string;
  country_code?: string;
  status?: 'success' | 'failed';
  has_anomaly?: boolean;
  anomaly_type?: string;
  min_risk_score?: number;
  page?: number;
  page_size?: number;
}

/** Tenant model */
export interface Tenant {
  id: string;
  name: string;
  tenant_id: string;
  client_id: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  ms_tenant_name?: string;
}

/** Tenant creation request */
export interface TenantCreate {
  name: string;
  tenant_id: string;
  client_id: string;
  client_secret: string;
}

/** Tenant update request */
export interface TenantUpdate {
  name?: string;
  is_active?: boolean;
}

/** Tenant list response */
export interface TenantListResponse {
  items: Tenant[];
  total: number;
}

/** Severity level */
export type SeverityLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

/** Event type */
export type EventType = 
  | 'impossible_travel' 
  | 'new_country' 
  | 'brute_force' 
  | 'admin_action' 
  | 'new_ip' 
  | 'multiple_failures' 
  | 'suspicious_location';

/** Alert history item */
export interface AlertHistory {
  id: string;
  rule_id?: string;
  webhook_id: string;
  severity: SeverityLevel;
  event_type: string;
  user_email?: string;
  title: string;
  message: string;
  metadata: Record<string, unknown>;
  sent_at: string;
}

/** Alert history list response */
export interface AlertHistoryList {
  total: number;
  items: AlertHistory[];
  limit: number;
  offset: number;
}

/** Alert filters */
export interface AlertFilters {
  tenant_id?: string;
  hours?: number;
  min_risk_score?: number;
  limit?: number;
  event_type?: EventType;
  severity?: SeverityLevel;
}

/** Dashboard stats */
export interface DashboardStats {
  total_logins: number;
  failed_logins: number;
  anomalies_today: number;
  active_tenants: number;
}

/** Geographic location for map */
export interface MapLocation {
  id: string;
  lat: number;
  lng: number;
  user_email: string;
  country?: string;
  city?: string;
  ip_address: string;
  login_time: string;
  is_success: boolean;
  risk_score: number;
  anomaly_flags: string[];
}

/** Theme type */
export type Theme = 'light' | 'dark';

/** User authentication */
export interface User {
  username: string;
  is_authenticated: boolean;
}

/** Login request */
export interface LoginRequest {
  username: string;
  password: string;
}

/** Login response */
export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

/** App state */
export interface AppState {
  theme: Theme;
  sidebarOpen: boolean;
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
  setUser: (user: User | null) => void;
  setToken: (token: string | null) => void;
  login: (token: string) => void;
  logout: () => void;
}

// ============================================
// Settings Types
// ============================================

/** System settings */
export interface SystemSettings {
  audit_log_retention_days: number;
  login_history_retention_days: number;
  alert_history_retention_days: number;
  auto_cleanup_enabled: boolean;
  cleanup_schedule: string;
  api_rate_limit: number;
  max_export_rows: number;
  log_level: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL';
  created_at?: string;
  updated_at?: string;
}

/** System settings update */
export interface SystemSettingsUpdate {
  audit_log_retention_days?: number;
  login_history_retention_days?: number;
  alert_history_retention_days?: number;
  auto_cleanup_enabled?: boolean;
  cleanup_schedule?: string;
  api_rate_limit?: number;
  max_export_rows?: number;
  log_level?: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL';
}

/** User preferences */
export interface UserPreferences {
  user_email: string;
  timezone: string;
  date_format: 'ISO' | 'US' | 'EU';
  theme: 'light' | 'dark' | 'system';
  email_notifications: boolean;
  discord_notifications: boolean;
  notification_min_severity: SeverityLevel;
  default_dashboard_view: string;
  refresh_interval_seconds: number;
  created_at?: string;
  updated_at?: string;
}

/** User preferences update */
export interface UserPreferencesUpdate {
  timezone?: string;
  date_format?: 'ISO' | 'US' | 'EU';
  theme?: 'light' | 'dark' | 'system';
  email_notifications?: boolean;
  discord_notifications?: boolean;
  notification_min_severity?: SeverityLevel;
  default_dashboard_view?: string;
  refresh_interval_seconds?: number;
}

/** Detection thresholds */
export interface DetectionThresholds {
  tenant_id?: string;
  impossible_travel_enabled: boolean;
  impossible_travel_min_speed_kmh: number;
  impossible_travel_time_window_minutes: number;
  new_country_enabled: boolean;
  new_country_learning_period_days: number;
  brute_force_enabled: boolean;
  brute_force_threshold: number;
  brute_force_window_minutes: number;
  new_ip_enabled: boolean;
  new_ip_learning_period_days: number;
  multiple_failures_enabled: boolean;
  multiple_failures_threshold: number;
  multiple_failures_window_minutes: number;
  risk_score_base_multiplier: number;
  created_at?: string;
  updated_at?: string;
}

/** Detection thresholds update */
export interface DetectionThresholdsUpdate {
  impossible_travel_enabled?: boolean;
  impossible_travel_min_speed_kmh?: number;
  impossible_travel_time_window_minutes?: number;
  new_country_enabled?: boolean;
  new_country_learning_period_days?: number;
  brute_force_enabled?: boolean;
  brute_force_threshold?: number;
  brute_force_window_minutes?: number;
  new_ip_enabled?: boolean;
  new_ip_learning_period_days?: number;
  multiple_failures_enabled?: boolean;
  multiple_failures_threshold?: number;
  multiple_failures_window_minutes?: number;
  risk_score_base_multiplier?: number;
}

/** API key */
export interface ApiKey {
  id: string;
  name: string;
  key_prefix: string;
  scopes: string[];
  tenant_id?: string;
  is_active: boolean;
  expires_at?: string;
  last_used_at?: string;
  created_by?: string;
  created_at: string;
}

/** API key creation request */
export interface ApiKeyCreate {
  name: string;
  scopes: string[];
  tenant_id?: string;
  expires_days?: number;
}

/** API key creation response */
export interface ApiKeyCreateResponse {
  id: string;
  key: string;
  name: string;
  prefix: string;
  message: string;
}

/** API key update */
export interface ApiKeyUpdate {
  name?: string;
  scopes?: string[];
  is_active?: boolean;
}

/** Webhook test request */
export interface WebhookTestRequest {
  webhook_url: string;
  webhook_type: 'discord' | 'slack';
  message: string;
}

/** Webhook test response */
export interface WebhookTestResponse {
  success: boolean;
  message: string;
  latency_ms?: number;
}

/** Configuration export request */
export interface ConfigExportRequest {
  categories: string[];
  name: string;
  description?: string;
}

/** Configuration export response */
export interface ConfigExportResponse {
  id: string;
  name: string;
  description?: string;
  categories: string[];
  created_at: string;
  download_url: string;
}

/** Configuration import request */
export interface ConfigImportRequest {
  config: Record<string, unknown>;
  overwrite?: boolean;
}

/** Configuration import response */
export interface ConfigImportResponse {
  imported: string[];
  errors: string[];
  message: string;
}

/** Configuration backup */
export interface ConfigBackup {
  id: string;
  name: string;
  description?: string;
  categories: string[];
  created_by?: string;
  created_at: string;
}

/** Alert rule for rule builder */
export interface AlertRule {
  id: string;
  name: string;
  event_types: EventType[];
  min_severity: SeverityLevel;
  cooldown_minutes: number;
  is_active: boolean;
  tenant_id?: string;
  created_at: string;
  updated_at: string;
}

/** Alert rule creation/update */
export interface AlertRuleCreate {
  name: string;
  event_types: EventType[];
  min_severity: SeverityLevel;
  cooldown_minutes?: number;
  tenant_id?: string;
}

/** Alert rule update */
export interface AlertRuleUpdate {
  name?: string;
  event_types?: EventType[];
  min_severity?: SeverityLevel;
  cooldown_minutes?: number;
  is_active?: boolean;
}

/** Webhook configuration */
export interface WebhookConfig {
  id: string;
  name: string;
  webhook_type: 'discord' | 'slack';
  is_active: boolean;
  tenant_id?: string;
  created_at: string;
}

/** Webhook creation */
export interface WebhookCreate {
  name: string;
  webhook_url: string;
  webhook_type: 'discord' | 'slack';
  tenant_id?: string;
}

/** Webhook update */
export interface WebhookUpdate {
  name?: string;
  webhook_url?: string;
  webhook_type?: 'discord' | 'slack';
  is_active?: boolean;
}
