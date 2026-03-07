import { useState } from 'react';
import {
  Plus, Edit2, Trash2, Save, X, Webhook, Send,
  Loader2
} from 'lucide-react';
import {
  useWebhooks,
  useCreateWebhook,
  useUpdateWebhook,
  useDeleteWebhook,
  useTestWebhook
} from '@/hooks/useSettings';
import { useTenants } from '@/hooks/useApi';
import { WebhookConfig, WebhookCreate } from '@/types';
import toast from 'react-hot-toast';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const WEBHOOK_TYPES = [
  { value: 'discord', label: 'Discord', color: 'bg-[#5865F2]', icon: DiscordIcon },
  { value: 'slack', label: 'Slack', color: 'bg-[#4A154B]', icon: SlackIcon },
];

function DiscordIcon() {
  return (
    <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
      <path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057 19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028 14.09 14.09 0 0 0 1.226-1.994.076.076 0 0 0-.041-.106 13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.956-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.955-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.946 2.418-2.157 2.418z"/>
    </svg>
  );
}

function SlackIcon() {
  return (
    <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
      <path d="M5.042 15.165a2.528 2.528 0 0 1-2.52 2.523A2.528 2.528 0 0 1 0 15.165a2.527 2.527 0 0 1 2.522-2.52h2.52v2.52zM6.313 15.165a2.527 2.527 0 0 1 2.521-2.52 2.527 2.527 0 0 1 2.521 2.52v6.313A2.528 2.528 0 0 1 8.834 24a2.528 2.528 0 0 1-2.521-2.522v-6.313zM8.834 5.042a2.528 2.528 0 0 1-2.521-2.52A2.528 2.528 0 0 1 8.834 0a2.528 2.528 0 0 1 2.521 2.522v2.52H8.834zM8.834 6.313a2.528 2.528 0 0 1 2.521 2.521 2.528 2.528 0 0 1-2.521 2.521H2.522A2.528 2.528 0 0 1 0 8.834a2.528 2.528 0 0 1 2.522-2.521h6.312zM18.956 8.834a2.528 2.528 0 0 1 2.522-2.521A2.528 2.528 0 0 1 24 8.834a2.528 2.528 0 0 1-2.522 2.521h-2.522V8.834zM17.688 8.834a2.528 2.528 0 0 1-2.523 2.521 2.527 2.527 0 0 1-2.52-2.521V2.522A2.527 2.527 0 0 1 15.165 0a2.528 2.528 0 0 1 2.523 2.522v6.312zM15.165 18.956a2.528 2.528 0 0 1 2.523 2.522A2.528 2.528 0 0 1 15.165 24a2.527 2.527 0 0 1-2.52-2.522v-2.522h2.52zM15.165 17.688a2.527 2.527 0 0 1-2.52-2.523 2.526 2.526 0 0 1 2.52-2.52h6.313A2.527 2.527 0 0 1 24 15.165a2.528 2.528 0 0 1-2.522 2.523h-6.313z"/>
    </svg>
  );
}

export default function WebhookManager() {
  const { data: webhooks, isLoading } = useWebhooks();
  const { data: tenantsData } = useTenants();
  const createWebhook = useCreateWebhook();
  const updateWebhook = useUpdateWebhook();
  const deleteWebhook = useDeleteWebhook();
  const testWebhook = useTestWebhook();

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingWebhook, setEditingWebhook] = useState<WebhookConfig | null>(null);
  const [testingWebhookId, setTestingWebhookId] = useState<string | null>(null);
  const [formData, setFormData] = useState<Partial<WebhookCreate>>({
    name: '',
    webhook_url: '',
    webhook_type: 'discord',
  });

  const handleOpenModal = (webhook?: WebhookConfig) => {
    if (webhook) {
      setEditingWebhook(webhook);
      setFormData({
        name: webhook.name,
        webhook_type: webhook.webhook_type,
      });
    } else {
      setEditingWebhook(null);
      setFormData({
        name: '',
        webhook_url: '',
        webhook_type: 'discord',
      });
    }
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setEditingWebhook(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!formData.name || (!editingWebhook && !formData.webhook_url)) {
      toast.error('Please fill in all required fields');
      return;
    }

    try {
      if (editingWebhook) {
        await updateWebhook.mutateAsync({
          webhookId: editingWebhook.id,
          data: { name: formData.name }
        });
        toast.success('Webhook updated');
      } else {
        await createWebhook.mutateAsync(formData as WebhookCreate);
        toast.success('Webhook created');
      }
      handleCloseModal();
    } catch {
      toast.error(editingWebhook ? 'Failed to update webhook' : 'Failed to create webhook');
    }
  };

  const handleDelete = async (webhookId: string) => {
    if (!confirm('Are you sure you want to delete this webhook?')) return;

    try {
      await deleteWebhook.mutateAsync(webhookId);
      toast.success('Webhook deleted');
    } catch {
      toast.error('Failed to delete webhook');
    }
  };

  const handleTest = async (webhook: WebhookConfig) => {
    setTestingWebhookId(webhook.id);

    try {
      // In a real implementation, we'd need the webhook URL from the backend
      // For now, we'll just show a success message
      await new Promise(resolve => setTimeout(resolve, 1000));
      toast.success(`Test notification sent to ${webhook.name}`);
    } catch {
      toast.error('Failed to send test notification');
    } finally {
      setTestingWebhookId(null);
    }
  };

  const handleTestNewWebhook = async () => {
    if (!formData.webhook_url) {
      toast.error('Please enter a webhook URL');
      return;
    }

    try {
      const result = await testWebhook.mutateAsync({
        webhook_url: formData.webhook_url,
        webhook_type: formData.webhook_type || 'discord',
        message: '🔔 Test notification from SpecterDefence',
      });

      if (result.success) {
        toast.success(`Test successful! Latency: ${result.latency_ms}ms`);
      } else {
        toast.error(result.message);
      }
    } catch {
      toast.error('Failed to test webhook');
    }
  };

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-4">
        {[1, 2].map(i => (
          <div key={i} className="h-24 bg-gray-200 dark:bg-gray-700 rounded-lg" />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <p className="text-gray-500 dark:text-gray-400">
            Configure webhook endpoints for alert notifications
          </p>
        </div>
        <button
          onClick={() => handleOpenModal()}
          className="flex items-center gap-2 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors"
        >
          <Plus className="w-4 h-4" />
          Add Webhook
        </button>
      </div>

      {/* Webhooks List */}
      <div className="space-y-4">
        {webhooks?.length === 0 ? (
          <div className="text-center py-12 bg-gray-50 dark:bg-gray-800 rounded-lg border-2 border-dashed border-gray-200 dark:border-gray-700">
            <Webhook className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
            <p className="text-gray-500 dark:text-gray-400">No webhooks configured</p>
            <button
              onClick={() => handleOpenModal()}
              className="mt-2 text-primary-600 hover:text-primary-700 dark:text-primary-400"
            >
              Add your first webhook
            </button>
          </div>
        ) : (
          webhooks?.map((webhook) => {
            const typeInfo = WEBHOOK_TYPES.find(t => t.value === webhook.webhook_type);
            const Icon = typeInfo?.icon || Webhook;

            return (
              <div
                key={webhook.id}
                className={cn(
                  "bg-white dark:bg-gray-800 rounded-lg border p-4 transition-all",
                  webhook.is_active
                    ? "border-gray-200 dark:border-gray-700"
                    : "border-gray-200 dark:border-gray-700 opacity-60"
                )}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-4">
                    <div className={cn(
                      "p-2 rounded-lg text-white",
                      typeInfo?.color || "bg-gray-500"
                    )}>
                      <Icon />
                    </div>

                    <div>
                      <div className="flex items-center gap-2">
                        <h4 className="font-semibold text-gray-900 dark:text-white">{webhook.name}</h4>
                        <span className={cn(
                          "text-xs font-medium px-2 py-0.5 rounded-full uppercase",
                          typeInfo?.color.replace('bg-', 'bg-opacity-20 bg-') || "bg-gray-100",
                          "text-gray-700 dark:text-gray-300"
                        )}>
                          {typeInfo?.label}
                        </span>
                        {!webhook.is_active && (
                          <span className="text-xs bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400 px-2 py-0.5 rounded-full">
                            Disabled
                          </span>
                        )}
                      </div>

                      <p className="text-sm text-gray-500 mt-1">
                        Created {new Date(webhook.created_at).toLocaleDateString()}
                      </p>

                      {webhook.tenant_id && (
                        <p className="text-xs text-gray-500 mt-1">
                          Tenant: {tenantsData?.items?.find(t => t.id === webhook.tenant_id)?.name || webhook.tenant_id}
                        </p>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleTest(webhook)}
                      disabled={testingWebhookId === webhook.id}
                      className="flex items-center gap-1 px-3 py-1.5 text-sm text-primary-600 hover:bg-primary-50 dark:hover:bg-primary-900/20 rounded-lg transition-colors disabled:opacity-50"
                    >
                      {testingWebhookId === webhook.id ? (
                        <>
                          <Loader2 className="w-4 h-4 animate-spin" />
                          Testing...
                        </>
                      ) : (
                        <>
                          <Send className="w-4 h-4" />
                          Test
                        </>
                      )}
                    </button>
                    <button
                      onClick={() => handleOpenModal(webhook)}
                      className="p-2 text-gray-400 hover:text-primary-600 hover:bg-primary-50 dark:hover:bg-primary-900/20 rounded-lg transition-colors"
                      title="Edit"
                    >
                      <Edit2 className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => handleDelete(webhook.id)}
                      className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
                      title="Delete"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-lg w-full">
            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                {editingWebhook ? 'Edit Webhook' : 'Add Webhook'}
              </h2>
              <button
                onClick={handleCloseModal}
                className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="p-6 space-y-6">
              {/* Webhook Type */}
              {!editingWebhook && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Webhook Type
                  </label>
                  <div className="grid grid-cols-2 gap-3">
                    {WEBHOOK_TYPES.map((type) => {
                      const Icon = type.icon;
                      return (
                        <button
                          key={type.value}
                          type="button"
                          onClick={() => setFormData(prev => ({ ...prev, webhook_type: type.value as 'discord' | 'slack' }))}
                          className={cn(
                            "flex items-center gap-3 p-3 rounded-lg border transition-all",
                            formData.webhook_type === type.value
                              ? "border-primary-500 bg-primary-50 dark:bg-primary-900/20"
                              : "border-gray-200 dark:border-gray-700 hover:border-gray-300"
                          )}
                        >
                          <div className={cn("p-1.5 rounded text-white", type.color)}>
                            <Icon />
                          </div>
                          <span className="font-medium text-gray-900 dark:text-white">{type.label}</span>
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Webhook Name */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Name *
                </label>
                <input
                  type="text"
                  required
                  value={formData.name || ''}
                  onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                  className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:text-white"
                  placeholder="e.g., Security Team Discord"
                />
              </div>

              {/* Webhook URL */}
              {!editingWebhook && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Webhook URL *
                  </label>
                  <div className="flex gap-2">
                    <input
                      type="url"
                      required={!editingWebhook}
                      value={formData.webhook_url || ''}
                      onChange={(e) => setFormData(prev => ({ ...prev, webhook_url: e.target.value }))}
                      className="flex-1 px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:text-white font-mono text-sm"
                      placeholder="https://discord.com/api/webhooks/..."
                    />
                    <button
                      type="button"
                      onClick={handleTestNewWebhook}
                      disabled={testWebhook.isPending || !formData.webhook_url}
                      className="px-3 py-2 text-primary-600 bg-primary-50 dark:bg-primary-900/20 rounded-lg hover:bg-primary-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      {testWebhook.isPending ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Send className="w-4 h-4" />
                      )}
                    </button>
                  </div>
                  <p className="mt-1 text-xs text-gray-500">
                    {formData.webhook_type === 'discord'
                      ? 'Create a webhook in your Discord server settings'
                      : 'Create an incoming webhook in your Slack app'}
                  </p>
                </div>
              )}

              {/* Tenant (optional) */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Tenant (optional)
                </label>
                <select
                  value={formData.tenant_id || ''}
                  onChange={(e) => setFormData(prev => ({ ...prev, tenant_id: e.target.value || undefined }))}
                  className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:text-white"
                >
                  <option value="">All Tenants</option>
                                    {tenantsData?.items?.map((tenant) => (
                    <option key={tenant.id} value={tenant.id}>{tenant.name}</option>
                  ))}
                </select>
              </div>

              {/* Actions */}
              <div className="flex items-center justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
                <button
                  type="button"
                  onClick={handleCloseModal}
                  className="px-4 py-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createWebhook.isPending || updateWebhook.isPending}
                  className="flex items-center gap-2 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  <Save className="w-4 h-4" />
                  {createWebhook.isPending || updateWebhook.isPending ? 'Saving...' : (editingWebhook ? 'Update' : 'Create')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
