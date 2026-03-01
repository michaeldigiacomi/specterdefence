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

/** App state */
export interface AppState {
  theme: Theme;
  sidebarOpen: boolean;
  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
}
