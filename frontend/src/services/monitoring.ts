import axios, { AxiosInstance } from 'axios';

const API_BASE = '/api/v1/monitoring';

// Create axios instance with auth interceptor
const createAuthAxios = (): AxiosInstance => {
  const client = axios.create({
    baseURL: API_BASE,
    headers: {
      'Content-Type': 'application/json',
    },
    timeout: 30000,
  });

  // Add request interceptor to include auth token
  client.interceptors.request.use(
    (config) => {
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
    (error) => Promise.reject(error)
  );

  return client;
};

const authAxios = createAuthAxios();

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

// Helper to build query params with optional tenant_id
const buildParams = (tenantId?: string, extra?: Record<string, unknown>) => {
  const params: Record<string, unknown> = {};
  if (tenantId) params.tenant_id = tenantId;
  if (extra) Object.assign(params, extra);
  return params;
};

// Website API
export const websiteApi = {
  list: (tenantId?: string) => authAxios.get<Website[]>('/websites', { params: buildParams(tenantId) }),
  get: (id: string, tenantId?: string) => authAxios.get<Website>(`/websites/${id}`, { params: buildParams(tenantId) }),
  create: (data: { name: string; url: string; check_interval_minutes?: number }, tenantId?: string) =>
    authAxios.post<Website>('/websites', data, { params: buildParams(tenantId) }),
  delete: (id: string, tenantId?: string) => authAxios.delete(`/websites/${id}`, { params: buildParams(tenantId) }),
  check: (id: string, tenantId?: string) => authAxios.post<Website>(`/websites/${id}/check`, null, { params: buildParams(tenantId) }),
  checkAll: (tenantId?: string) => authAxios.post<{ checked: number }>('/websites/check-all', null, { params: buildParams(tenantId) }),
  stats: (tenantId?: string) => authAxios.get<WebsiteStats>('/websites/stats', { params: buildParams(tenantId) }),
};

// SSL API
export const sslApi = {
  list: (tenantId?: string) => authAxios.get<SslCertificate[]>('/ssl', { params: buildParams(tenantId) }),
  get: (id: string, tenantId?: string) => authAxios.get<SslCertificate>(`/ssl/${id}`, { params: buildParams(tenantId) }),
  create: (data: { domain: string; port?: number }, tenantId?: string) =>
    authAxios.post<SslCertificate>('/ssl', data, { params: buildParams(tenantId) }),
  delete: (id: string, tenantId?: string) => authAxios.delete(`/ssl/${id}`, { params: buildParams(tenantId) }),
  check: (id: string, tenantId?: string) => authAxios.post<SslCertificate>(`/ssl/${id}/check`, null, { params: buildParams(tenantId) }),
  checkAll: (tenantId?: string) => authAxios.post<{ checked: number }>('/ssl/check-all', null, { params: buildParams(tenantId) }),
  stats: (tenantId?: string) => authAxios.get<SslStats>('/ssl/stats', { params: buildParams(tenantId) }),
  expiring: (days?: number, tenantId?: string) => authAxios.get<SslCertificate[]>('/ssl/expiring', { params: buildParams(tenantId, { days }) }),
};

// Domain API
export const domainApi = {
  list: (tenantId?: string) => authAxios.get<Domain[]>('/domains', { params: buildParams(tenantId) }),
  get: (id: string, tenantId?: string) => authAxios.get<Domain>(`/domains/${id}`, { params: buildParams(tenantId) }),
  create: (data: { domain: string }, tenantId?: string) =>
    authAxios.post<Domain>('/domains', data, { params: buildParams(tenantId) }),
  delete: (id: string, tenantId?: string) => authAxios.delete(`/domains/${id}`, { params: buildParams(tenantId) }),
  check: (id: string, tenantId?: string) => authAxios.post<Domain>(`/domains/${id}/check`, null, { params: buildParams(tenantId) }),
  checkAll: (tenantId?: string) => authAxios.post<{ checked: number }>('/domains/check-all', null, { params: buildParams(tenantId) }),
  stats: (tenantId?: string) => authAxios.get<DomainStats>('/domains/stats', { params: buildParams(tenantId) }),
  expiring: (days?: number, tenantId?: string) => authAxios.get<Domain[]>('/domains/expiring', { params: buildParams(tenantId, { days }) }),
};
