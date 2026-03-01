import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiService from '@/services/api';
import { 
  LoginFilters, 
  AlertFilters, 
  TenantCreate, 
  TenantUpdate
} from '@/types';

// Query keys
export const queryKeys = {
  logins: (filters: LoginFilters) => ['logins', filters] as const,
  userSummary: (userEmail: string, tenantId: string) => ['userSummary', userEmail, tenantId] as const,
  anomalies: (filters: AlertFilters) => ['anomalies', filters] as const,
  tenants: () => ['tenants'] as const,
  tenant: (id: string) => ['tenant', id] as const,
  alertHistory: (filters: AlertFilters) => ['alertHistory', filters] as const,
  dashboardStats: () => ['dashboardStats'] as const,
};

// ============== Login Analytics Hooks ==============

export function useLoginAnalytics(filters: LoginFilters) {
  return useQuery({
    queryKey: queryKeys.logins(filters),
    queryFn: () => apiService.getLoginAnalytics(filters),
    staleTime: 30000, // 30 seconds
  });
}

export function useUserLoginSummary(userEmail: string, tenantId: string) {
  return useQuery({
    queryKey: queryKeys.userSummary(userEmail, tenantId),
    queryFn: () => apiService.getUserLoginSummary(userEmail, tenantId),
    enabled: !!userEmail && !!tenantId,
  });
}

export function useRecentAnomalies(filters: AlertFilters) {
  return useQuery({
    queryKey: queryKeys.anomalies(filters),
    queryFn: () => apiService.getRecentAnomalies(filters),
    staleTime: 60000, // 1 minute
  });
}

// ============== Tenant Hooks ==============

export function useTenants() {
  return useQuery({
    queryKey: queryKeys.tenants(),
    queryFn: () => apiService.getTenants(),
    staleTime: 60000, // 1 minute
  });
}

export function useTenant(id: string) {
  return useQuery({
    queryKey: queryKeys.tenant(id),
    queryFn: () => apiService.getTenant(id),
    enabled: !!id,
  });
}

export function useCreateTenant() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (data: TenantCreate) => apiService.createTenant(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.tenants() });
    },
  });
}

export function useUpdateTenant(id: string) {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (data: TenantUpdate) => apiService.updateTenant(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.tenants() });
      queryClient.invalidateQueries({ queryKey: queryKeys.tenant(id) });
    },
  });
}

export function useDeleteTenant() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (id: string) => apiService.deleteTenant(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.tenants() });
    },
  });
}

export function useValidateTenant() {
  return useMutation({
    mutationFn: (data: TenantCreate) => apiService.validateTenant(data),
  });
}

// ============== Alert Hooks ==============

export function useAlertHistory(filters: AlertFilters) {
  return useQuery({
    queryKey: queryKeys.alertHistory(filters),
    queryFn: () => apiService.getAlertHistory(filters),
    staleTime: 30000, // 30 seconds
  });
}

// ============== Dashboard Hooks ==============

export function useDashboardStats() {
  return useQuery({
    queryKey: queryKeys.dashboardStats(),
    queryFn: () => apiService.getDashboardStats(),
    staleTime: 60000, // 1 minute
    refetchInterval: 60000, // Auto refresh every minute
  });
}

// ============== Export Hook ==============

export function useExportLogins() {
  return useMutation({
    mutationFn: async (filters: LoginFilters) => {
      const blob = await apiService.exportLoginsToCSV(filters);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `login-analytics-${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    },
  });
}
