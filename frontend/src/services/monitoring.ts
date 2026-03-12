import axios from 'axios';

const API_BASE = '/api/v1/monitoring';

// Website types
export interface Website {
  id: string;
  tenant_id: string;
  name: string;
  url: string;
  is_enabled: boolean;
  check_interval_minutes: number;
  last_checked_at: string | null;
  last_status: string | null;
  last_response_code: number | null;
  last_response_time_ms: number | null;
  last_error: string | null;
  uptime_percentage: number;
  total_checks: number;
  successful_checks: number;
}

export interface WebsiteStats {
  total: number;
  up: number;
  down: number;
  error: number;
  unknown: number;
  average_uptime: number;
}

// SSL types
export interface SslCertificate {
  id: string;
  tenant_id: string;
  domain: string;
  port: number;
  issuer: string | null;
  subject: string | null;
  valid_from: string | null;
  valid_until: string | null;
  days_until_expiry: number | null;
  serial_number: string | null;
  signature_algorithm: string | null;
  is_valid: boolean;
  has_errors: boolean;
  error_message: string | null;
  last_checked_at: string | null;
}

export interface SslStats {
  total: number;
  valid: number;
  expired: number;
  expiring_soon: number;
  errors: number;
}

// Domain types
export interface Domain {
  id: string;
  tenant_id: string;
  domain: string;
  registrar: string | null;
  registration_date: string | null;
  expiry_date: string | null;
  days_until_expiry: number | null;
  is_expired: boolean;
  whois_error: string | null;
  last_checked_at: string | null;
}

export interface DomainStats {
  total: number;
  active: number;
  expired: number;
  expiring_soon: number;
  errors: number;
}

// Website API
export const websiteApi = {
  list: () => axios.get<Website[]>(`${API_BASE}/websites`),
  get: (id: string) => axios.get<Website>(`${API_BASE}/websites/${id}`),
  create: (data: { name: string; url: string; check_interval_minutes?: number }) =>
    axios.post<Website>(`${API_BASE}/websites`, data),
  delete: (id: string) => axios.delete(`${API_BASE}/websites/${id}`),
  check: (id: string) => axios.post<Website>(`${API_BASE}/websites/${id}/check`),
  checkAll: () => axios.post<{ checked: number }>(`${API_BASE}/websites/check-all`),
  stats: () => axios.get<WebsiteStats>(`${API_BASE}/websites/stats`),
};

// SSL API
export const sslApi = {
  list: () => axios.get<SslCertificate[]>(`${API_BASE}/ssl`),
  get: (id: string) => axios.get<SslCertificate>(`${API_BASE}/ssl/${id}`),
  create: (data: { domain: string; port?: number }) =>
    axios.post<SslCertificate>(`${API_BASE}/ssl`, data),
  delete: (id: string) => axios.delete(`${API_BASE}/ssl/${id}`),
  check: (id: string) => axios.post<SslCertificate>(`${API_BASE}/ssl/${id}/check`),
  checkAll: () => axios.post<{ checked: number }>(`${API_BASE}/ssl/check-all`),
  stats: () => axios.get<SslStats>(`${API_BASE}/ssl/stats`),
  expiring: (days?: number) => axios.get<SslCertificate[]>(`${API_BASE}/ssl/expiring`, { params: { days } }),
};

// Domain API
export const domainApi = {
  list: () => axios.get<Domain[]>(`${API_BASE}/domains`),
  get: (id: string) => axios.get<Domain>(`${API_BASE}/domains/${id}`),
  create: (data: { domain: string }) =>
    axios.post<Domain>(`${API_BASE}/domains`, data),
  delete: (id: string) => axios.delete(`${API_BASE}/domains/${id}`),
  check: (id: string) => axios.post<Domain>(`${API_BASE}/domains/${id}/check`),
  checkAll: () => axios.post<{ checked: number }>(`${API_BASE}/domains/check-all`),
  stats: () => axios.get<DomainStats>(`${API_BASE}/domains/stats`),
  expiring: (days?: number) => axios.get<Domain[]>(`${API_BASE}/domains/expiring`, { params: { days } }),
};
