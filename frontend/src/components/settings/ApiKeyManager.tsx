import { useState } from 'react';
import { Plus, Copy, Trash2, X, Key, Clock, Shield, CheckCircle, Save } from 'lucide-react';
import { useApiKeys, useCreateApiKey, useRevokeApiKey } from '@/hooks/useSettings';
import { useTenants } from '@/hooks/useApi';
import type { ApiKeyCreate } from '@/types';
import toast from 'react-hot-toast';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const AVAILABLE_SCOPES = [
  {
    value: 'read:analytics',
    label: 'Read Analytics',
    description: 'Access login analytics and data',
  },
  { value: 'read:alerts', label: 'Read Alerts', description: 'View alerts and alert history' },
  { value: 'write:alerts', label: 'Manage Alerts', description: 'Create and manage alert rules' },
  { value: 'read:tenants', label: 'Read Tenants', description: 'View tenant configurations' },
  { value: 'write:tenants', label: 'Manage Tenants', description: 'Create and modify tenants' },
  { value: 'read:settings', label: 'Read Settings', description: 'View system settings' },
  { value: 'write:settings', label: 'Manage Settings', description: 'Modify system settings' },
  { value: 'admin', label: 'Admin', description: 'Full administrative access' },
];

export default function ApiKeyManager() {
  const { data: apiKeys, isLoading } = useApiKeys();
  const { data: tenantsData } = useTenants();
  const createApiKey = useCreateApiKey();
  const revokeApiKey = useRevokeApiKey();

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [showNewKey, setShowNewKey] = useState<{ id: string; key: string; name: string } | null>(
    null
  );
  const [copiedKey, setCopiedKey] = useState(false);
  const [formData, setFormData] = useState<Partial<ApiKeyCreate>>({
    name: '',
    scopes: ['read:analytics'],
    expires_days: undefined,
  });

  const handleOpenModal = () => {
    setFormData({
      name: '',
      scopes: ['read:analytics'],
      expires_days: undefined,
    });
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setShowNewKey(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!formData.name || formData.scopes?.length === 0) {
      toast.error('Please fill in all required fields');
      return;
    }

    try {
      const result = await createApiKey.mutateAsync(formData as ApiKeyCreate);
      setShowNewKey({ id: result.id, key: result.key, name: result.name });
      toast.success('API key created successfully');
    } catch {
      toast.error('Failed to create API key');
    }
  };

  const handleRevoke = async (keyId: string) => {
    if (!confirm('Are you sure you want to revoke this API key? This action cannot be undone.'))
      return;

    try {
      await revokeApiKey.mutateAsync(keyId);
      toast.success('API key revoked');
    } catch {
      toast.error('Failed to revoke API key');
    }
  };

  const handleCopyKey = () => {
    if (showNewKey?.key) {
      navigator.clipboard.writeText(showNewKey.key);
      setCopiedKey(true);
      setTimeout(() => setCopiedKey(false), 2000);
      toast.success('API key copied to clipboard');
    }
  };

  const handleToggleScope = (scope: string) => {
    setFormData(prev => ({
      ...prev,
      scopes: prev.scopes?.includes(scope)
        ? prev.scopes.filter(s => s !== scope)
        : [...(prev.scopes || []), scope],
    }));
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return 'Never';
    return new Date(dateString).toLocaleDateString();
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
            Manage API keys for programmatic access
          </p>
        </div>
        <button
          onClick={handleOpenModal}
          className="flex items-center gap-2 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors"
        >
          <Plus className="w-4 h-4" />
          Create API Key
        </button>
      </div>

      {/* Security Notice */}
      <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-4 flex items-start gap-3">
        <Shield className="w-5 h-5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
        <div>
          <h4 className="font-medium text-amber-900 dark:text-amber-400">Security Notice</h4>
          <p className="text-sm text-amber-700 dark:text-amber-500">
            API keys provide full access to your SpecterDefence data. Store them securely and never
            commit them to version control. Keys are only shown once upon creation.
          </p>
        </div>
      </div>

      {/* API Keys List */}
      <div className="space-y-4">
        {apiKeys?.length === 0 ? (
          <div className="text-center py-12 bg-gray-50 dark:bg-gray-800 rounded-lg border-2 border-dashed border-gray-200 dark:border-gray-700">
            <Key className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
            <p className="text-gray-500 dark:text-gray-400">No API keys</p>
            <button
              onClick={handleOpenModal}
              className="mt-2 text-primary-600 hover:text-primary-700 dark:text-primary-400"
            >
              Create your first API key
            </button>
          </div>
        ) : (
          apiKeys?.map(key => (
            <div
              key={key.id}
              className={cn(
                'bg-white dark:bg-gray-800 rounded-lg border p-4 transition-all',
                key.is_active
                  ? 'border-gray-200 dark:border-gray-700'
                  : 'border-gray-200 dark:border-gray-700 opacity-60'
              )}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-4">
                  <div
                    className={cn(
                      'p-2 rounded-lg',
                      key.is_active
                        ? 'bg-primary-100 dark:bg-primary-900/30'
                        : 'bg-gray-100 dark:bg-gray-700'
                    )}
                  >
                    <Key className="w-5 h-5 text-primary-500" />
                  </div>

                  <div>
                    <div className="flex items-center gap-2">
                      <h4 className="font-semibold text-gray-900 dark:text-white">{key.name}</h4>
                      <span className="text-xs font-mono text-gray-500">{key.key_prefix}****</span>
                      {!key.is_active && (
                        <span className="text-xs bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400 px-2 py-0.5 rounded-full">
                          Revoked
                        </span>
                      )}
                      {key.expires_at && new Date(key.expires_at) < new Date() && (
                        <span className="text-xs bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400 px-2 py-0.5 rounded-full">
                          Expired
                        </span>
                      )}
                    </div>

                    <div className="flex flex-wrap gap-1 mt-2">
                      {key.scopes.map(scope => (
                        <span
                          key={scope}
                          className="text-xs bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 px-2 py-0.5 rounded"
                        >
                          {scope}
                        </span>
                      ))}
                    </div>

                    <div className="flex items-center gap-4 mt-2 text-sm text-gray-500">
                      <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        Created {formatDate(key.created_at)}
                      </span>
                      {key.expires_at && <span>Expires {formatDate(key.expires_at)}</span>}
                      {key.last_used_at && <span>Last used {formatDate(key.last_used_at)}</span>}
                    </div>
                  </div>
                </div>

                {key.is_active && (
                  <button
                    onClick={() => handleRevoke(key.id)}
                    className="flex items-center gap-1 px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                    Revoke
                  </button>
                )}
              </div>
            </div>
          ))
        )}
      </div>

      {/* Create Modal */}
      {isModalOpen && !showNewKey && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-lg w-full max-h-[90vh] overflow-y-auto">
            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                Create API Key
              </h2>
              <button
                onClick={handleCloseModal}
                className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="p-6 space-y-6">
              {/* Key Name */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Key Name *
                </label>
                <input
                  type="text"
                  required
                  value={formData.name || ''}
                  onChange={e => setFormData(prev => ({ ...prev, name: e.target.value }))}
                  className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:text-white"
                  placeholder="e.g., Production API Access"
                />
              </div>

              {/* Scopes */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Permissions *
                </label>
                <div className="space-y-2 max-h-60 overflow-y-auto">
                  {AVAILABLE_SCOPES.map(scope => (
                    <label
                      key={scope.value}
                      className={cn(
                        'flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-all',
                        formData.scopes?.includes(scope.value)
                          ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
                          : 'border-gray-200 dark:border-gray-700 hover:border-gray-300'
                      )}
                    >
                      <input
                        type="checkbox"
                        checked={formData.scopes?.includes(scope.value)}
                        onChange={() => handleToggleScope(scope.value)}
                        className="mt-0.5 w-4 h-4 text-primary-500 rounded border-gray-300 focus:ring-primary-500"
                      />
                      <div>
                        <span className="text-sm font-medium text-gray-900 dark:text-white">
                          {scope.label}
                        </span>
                        <p className="text-xs text-gray-500">{scope.description}</p>
                      </div>
                    </label>
                  ))}
                </div>
              </div>

              {/* Expiration */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Expiration (days, optional)
                </label>
                <input
                  type="number"
                  min={1}
                  max={365}
                  value={formData.expires_days || ''}
                  onChange={e =>
                    setFormData(prev => ({
                      ...prev,
                      expires_days: e.target.value ? parseInt(e.target.value) : undefined,
                    }))
                  }
                  className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:text-white"
                  placeholder="Never expires"
                />
              </div>

              {/* Tenant (optional) */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Restrict to Tenant (optional)
                </label>
                <select
                  value={formData.tenant_id || ''}
                  onChange={e =>
                    setFormData(prev => ({ ...prev, tenant_id: e.target.value || undefined }))
                  }
                  className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:text-white"
                >
                  <option value="">All Tenants</option>
                  {tenantsData?.items?.map(tenant => (
                    <option key={tenant.id} value={tenant.id}>
                      {tenant.name}
                    </option>
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
                  disabled={createApiKey.isPending}
                  className="flex items-center gap-2 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  <Save className="w-4 h-4" />
                  {createApiKey.isPending ? 'Creating...' : 'Create API Key'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Show New Key Modal */}
      {showNewKey && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-lg w-full">
            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                API Key Created
              </h2>
            </div>

            <div className="p-6 space-y-6">
              <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4">
                <div className="flex items-start gap-3">
                  <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-400 flex-shrink-0 mt-0.5" />
                  <div>
                    <h4 className="font-medium text-green-900 dark:text-green-400">Success!</h4>
                    <p className="text-sm text-green-700 dark:text-green-500">
                      Your API key "{showNewKey.name}" has been created. Copy it now - you won't be
                      able to see it again.
                    </p>
                  </div>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Your API Key
                </label>
                <div className="flex gap-2">
                  <div className="flex-1 px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg font-mono text-sm break-all">
                    {showNewKey.key}
                  </div>
                  <button
                    type="button"
                    onClick={handleCopyKey}
                    className="px-3 py-2 text-primary-600 bg-primary-50 dark:bg-primary-900/20 rounded-lg hover:bg-primary-100 transition-colors"
                  >
                    {copiedKey ? <CheckCircle className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-4 text-sm text-amber-700 dark:text-amber-500">
                <p>
                  Store this key securely. For security reasons, it will not be displayed again.
                </p>
              </div>

              <button
                onClick={handleCloseModal}
                className="w-full px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
