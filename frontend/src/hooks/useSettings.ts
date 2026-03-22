import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiService from '@/services/api';
import {
  SystemSettingsUpdate,
  UserPreferencesUpdate,
  DetectionThresholdsUpdate,
  ApiKeyCreate,
  ApiKeyUpdate,
  WebhookTestRequest,
  ConfigExportRequest,
  ConfigImportRequest,
  AlertRuleCreate,
  AlertRuleUpdate,
  WebhookCreate,
  WebhookUpdate,
} from '@/types';

// Query keys
export const settingsQueryKeys = {
  systemSettings: () => ['systemSettings'] as const,
  userPreferences: (email: string) => ['userPreferences', email] as const,
  detectionThresholds: (tenantId?: string) => ['detectionThresholds', tenantId] as const,
  apiKeys: () => ['apiKeys'] as const,
  configBackups: () => ['configBackups'] as const,
  alertRules: () => ['alertRules'] as const,
  webhooks: () => ['webhooks'] as const,
};

// ============== System Settings Hooks ==============

export function useSystemSettings() {
  return useQuery({
    queryKey: settingsQueryKeys.systemSettings(),
    queryFn: () => apiService.getSystemSettings(),
    staleTime: 60000,
  });
}

export function useUpdateSystemSettings() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: SystemSettingsUpdate) => apiService.updateSystemSettings(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: settingsQueryKeys.systemSettings() });
    },
  });
}

// ============== User Preferences Hooks ==============

export function useUserPreferences(userEmail: string) {
  return useQuery({
    queryKey: settingsQueryKeys.userPreferences(userEmail),
    queryFn: () => apiService.getUserPreferences(userEmail),
    enabled: !!userEmail,
    staleTime: 60000,
  });
}

export function useUpdateUserPreferences(userEmail: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: UserPreferencesUpdate) => apiService.updateUserPreferences(userEmail, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: settingsQueryKeys.userPreferences(userEmail) });
    },
  });
}

// ============== Detection Thresholds Hooks ==============

export function useDetectionThresholds(tenantId?: string) {
  return useQuery({
    queryKey: settingsQueryKeys.detectionThresholds(tenantId),
    queryFn: () => apiService.getDetectionThresholds(tenantId),
    staleTime: 60000,
  });
}

export function useUpdateDetectionThresholds(tenantId?: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: DetectionThresholdsUpdate) =>
      apiService.updateDetectionThresholds(data, tenantId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: settingsQueryKeys.detectionThresholds(tenantId) });
    },
  });
}

// ============== API Key Hooks ==============

export function useApiKeys(includeInactive?: boolean) {
  return useQuery({
    queryKey: [...settingsQueryKeys.apiKeys(), includeInactive],
    queryFn: () => apiService.getApiKeys(undefined, includeInactive),
    staleTime: 30000,
  });
}

export function useCreateApiKey() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: ApiKeyCreate) => apiService.createApiKey(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: settingsQueryKeys.apiKeys() });
    },
  });
}

export function useUpdateApiKey() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ keyId, data }: { keyId: string; data: ApiKeyUpdate }) =>
      apiService.updateApiKey(keyId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: settingsQueryKeys.apiKeys() });
    },
  });
}

export function useRevokeApiKey() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (keyId: string) => apiService.revokeApiKey(keyId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: settingsQueryKeys.apiKeys() });
    },
  });
}

// ============== Webhook Test Hook ==============

export function useTestWebhook() {
  return useMutation({
    mutationFn: (data: WebhookTestRequest) => apiService.testWebhook(data),
  });
}

export function useTestExistingWebhook() {
  return useMutation({
    mutationFn: (webhookId: string) => apiService.testExistingWebhook(webhookId),
  });
}

// ============== Configuration Import/Export Hooks ==============

export function useConfigurationBackups() {
  return useQuery({
    queryKey: settingsQueryKeys.configBackups(),
    queryFn: () => apiService.getConfigurationBackups(),
    staleTime: 30000,
  });
}

export function useExportConfiguration() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: ConfigExportRequest) => apiService.exportConfiguration(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: settingsQueryKeys.configBackups() });
    },
  });
}

export function useImportConfiguration() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: ConfigImportRequest) => apiService.importConfiguration(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: settingsQueryKeys.systemSettings() });
      queryClient.invalidateQueries({ queryKey: settingsQueryKeys.detectionThresholds() });
    },
  });
}

export function useDeleteConfigurationBackup() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (backupId: string) => apiService.deleteConfigurationBackup(backupId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: settingsQueryKeys.configBackups() });
    },
  });
}

// ============== Alert Rules Hooks ==============

export function useAlertRules() {
  return useQuery({
    queryKey: settingsQueryKeys.alertRules(),
    queryFn: () => apiService.getAlertRules(),
    staleTime: 30000,
  });
}

export function useCreateAlertRule() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: AlertRuleCreate) => apiService.createAlertRule(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: settingsQueryKeys.alertRules() });
    },
  });
}

export function useUpdateAlertRule() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ ruleId, data }: { ruleId: string; data: AlertRuleUpdate }) =>
      apiService.updateAlertRule(ruleId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: settingsQueryKeys.alertRules() });
    },
  });
}

export function useDeleteAlertRule() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (ruleId: string) => apiService.deleteAlertRule(ruleId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: settingsQueryKeys.alertRules() });
    },
  });
}

// ============== Webhooks Hooks ==============

export function useWebhooks() {
  return useQuery({
    queryKey: settingsQueryKeys.webhooks(),
    queryFn: () => apiService.getWebhooks(),
    staleTime: 30000,
  });
}

export function useCreateWebhook() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: WebhookCreate) => apiService.createWebhook(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: settingsQueryKeys.webhooks() });
    },
  });
}

export function useUpdateWebhook() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ webhookId, data }: { webhookId: string; data: WebhookUpdate }) =>
      apiService.updateWebhook(webhookId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: settingsQueryKeys.webhooks() });
    },
  });
}

export function useDeleteWebhook() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (webhookId: string) => apiService.deleteWebhook(webhookId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: settingsQueryKeys.webhooks() });
    },
  });
}

// ============== Tenant Settings Hook ==============

export function useTenantSettings(tenantId: string) {
  return useQuery({
    queryKey: ['tenantSettings', tenantId],
    queryFn: () => apiService.getTenantSettings(tenantId),
    enabled: !!tenantId,
    staleTime: 60000,
  });
}
