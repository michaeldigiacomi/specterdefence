import { useState } from 'react';
import {
  Plus,
  Edit2,
  Trash2,
  Save,
  X,
  Bell,
  AlertTriangle,
  Shield,
  Globe,
  Lock,
  Clock,
} from 'lucide-react';
import {
  useAlertRules,
  useCreateAlertRule,
  useUpdateAlertRule,
  useDeleteAlertRule,
} from '@/hooks/useSettings';
import { useTenants } from '@/hooks/useApi';
import { AlertRule, EventType, SeverityLevel } from '@/types';
import toast from 'react-hot-toast';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const EVENT_TYPES: {
  value: EventType;
  label: string;
  icon: React.ReactNode;
  description: string;
}[] = [
  {
    value: 'impossible_travel',
    label: 'Impossible Travel',
    icon: <Globe className="w-4 h-4" />,
    description: 'Logins from geographically distant locations',
  },
  {
    value: 'new_country',
    label: 'New Country',
    icon: <Globe className="w-4 h-4" />,
    description: 'First login from a new country',
  },
  {
    value: 'brute_force',
    label: 'Brute Force',
    icon: <Lock className="w-4 h-4" />,
    description: 'Multiple failed login attempts',
  },
  {
    value: 'new_ip',
    label: 'New IP Address',
    icon: <Shield className="w-4 h-4" />,
    description: 'First login from a new IP',
  },
  {
    value: 'multiple_failures',
    label: 'Multiple Failures',
    icon: <AlertTriangle className="w-4 h-4" />,
    description: 'User with repeated auth failures',
  },
  {
    value: 'admin_action',
    label: 'Admin Action',
    icon: <Shield className="w-4 h-4" />,
    description: 'Administrative actions',
  },
];

const SEVERITY_LEVELS: { value: SeverityLevel; label: string; color: string; bgColor: string }[] = [
  {
    value: 'LOW',
    label: 'Low',
    color: 'text-green-700',
    bgColor: 'bg-green-100 dark:bg-green-900/30',
  },
  {
    value: 'MEDIUM',
    label: 'Medium',
    color: 'text-yellow-700',
    bgColor: 'bg-yellow-100 dark:bg-yellow-900/30',
  },
  {
    value: 'HIGH',
    label: 'High',
    color: 'text-orange-700',
    bgColor: 'bg-orange-100 dark:bg-orange-900/30',
  },
  {
    value: 'CRITICAL',
    label: 'Critical',
    color: 'text-red-700',
    bgColor: 'bg-red-100 dark:bg-red-900/30',
  },
];

export default function AlertRuleBuilder() {
  const { data: rules, isLoading } = useAlertRules();
  const { data: tenantsData } = useTenants();
  const createRule = useCreateAlertRule();
  const updateRule = useUpdateAlertRule();
  const deleteRule = useDeleteAlertRule();

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingRule, setEditingRule] = useState<AlertRule | null>(null);
  const [formData, setFormData] = useState<Partial<AlertRule>>({
    name: '',
    event_types: [],
    min_severity: 'MEDIUM',
    cooldown_minutes: 30,
    is_active: true,
  });

  const handleOpenModal = (rule?: AlertRule) => {
    if (rule) {
      setEditingRule(rule);
      setFormData({
        name: rule.name,
        event_types: [...rule.event_types],
        min_severity: rule.min_severity,
        cooldown_minutes: rule.cooldown_minutes,
        is_active: rule.is_active,
        tenant_id: rule.tenant_id,
      });
    } else {
      setEditingRule(null);
      setFormData({
        name: '',
        event_types: [],
        min_severity: 'MEDIUM',
        cooldown_minutes: 30,
        is_active: true,
      });
    }
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setEditingRule(null);
  };

  const handleToggleEventType = (eventType: EventType) => {
    setFormData(prev => ({
      ...prev,
      event_types: prev.event_types?.includes(eventType)
        ? prev.event_types.filter(et => et !== eventType)
        : [...(prev.event_types || []), eventType],
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!formData.name || formData.event_types?.length === 0) {
      toast.error('Please fill in all required fields');
      return;
    }

    try {
      if (editingRule) {
        await updateRule.mutateAsync({
          ruleId: editingRule.id,
          data: {
            name: formData.name,
            event_types: formData.event_types,
            min_severity: formData.min_severity,
            cooldown_minutes: formData.cooldown_minutes,
            is_active: formData.is_active,
          },
        });
        toast.success('Alert rule updated');
      } else {
        await createRule.mutateAsync({
          name: formData.name,
          event_types: formData.event_types as EventType[],
          min_severity: formData.min_severity as SeverityLevel,
          cooldown_minutes: formData.cooldown_minutes,
          tenant_id: formData.tenant_id,
        });
        toast.success('Alert rule created');
      }
      handleCloseModal();
    } catch {
      toast.error(editingRule ? 'Failed to update rule' : 'Failed to create rule');
    }
  };

  const handleDelete = async (ruleId: string) => {
    if (!confirm('Are you sure you want to delete this alert rule?')) return;

    try {
      await deleteRule.mutateAsync(ruleId);
      toast.success('Alert rule deleted');
    } catch {
      toast.error('Failed to delete rule');
    }
  };

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-4">
        {[1, 2, 3].map(i => (
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
            Configure when and how alerts are triggered
          </p>
        </div>
        <button
          onClick={() => handleOpenModal()}
          className="flex items-center gap-2 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors"
        >
          <Plus className="w-4 h-4" />
          New Rule
        </button>
      </div>

      {/* Rules List */}
      <div className="space-y-4">
        {rules?.length === 0 ? (
          <div className="text-center py-12 bg-gray-50 dark:bg-gray-800 rounded-lg border-2 border-dashed border-gray-200 dark:border-gray-700">
            <Bell className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
            <p className="text-gray-500 dark:text-gray-400">No alert rules configured</p>
            <button
              onClick={() => handleOpenModal()}
              className="mt-2 text-primary-600 hover:text-primary-700 dark:text-primary-400"
            >
              Create your first rule
            </button>
          </div>
        ) : (
          rules?.map(rule => (
            <div
              key={rule.id}
              className={cn(
                'bg-white dark:bg-gray-800 rounded-lg border p-4 transition-all',
                rule.is_active
                  ? 'border-gray-200 dark:border-gray-700'
                  : 'border-gray-200 dark:border-gray-700 opacity-60'
              )}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-4">
                  <div
                    className={cn(
                      'p-2 rounded-lg',
                      rule.is_active
                        ? 'bg-primary-100 dark:bg-primary-900/30'
                        : 'bg-gray-100 dark:bg-gray-700'
                    )}
                  >
                    <Bell className="w-5 h-5 text-primary-500" />
                  </div>

                  <div>
                    <div className="flex items-center gap-2">
                      <h4 className="font-semibold text-gray-900 dark:text-white">{rule.name}</h4>
                      <span
                        className={cn(
                          'text-xs font-medium px-2 py-0.5 rounded-full',
                          SEVERITY_LEVELS.find(s => s.value === rule.min_severity)?.bgColor,
                          SEVERITY_LEVELS.find(s => s.value === rule.min_severity)?.color
                        )}
                      >
                        {rule.min_severity}
                      </span>
                      {!rule.is_active && (
                        <span className="text-xs bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400 px-2 py-0.5 rounded-full">
                          Disabled
                        </span>
                      )}
                    </div>

                    <div className="flex flex-wrap gap-2 mt-2">
                      {rule.event_types.map(et => {
                        const eventType = EVENT_TYPES.find(e => e.value === et);
                        return (
                          <span
                            key={et}
                            className="inline-flex items-center gap-1 text-xs bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 px-2 py-1 rounded"
                          >
                            {eventType?.icon}
                            {eventType?.label}
                          </span>
                        );
                      })}
                    </div>

                    <div className="flex items-center gap-4 mt-2 text-sm text-gray-500">
                      <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {rule.cooldown_minutes}min cooldown
                      </span>
                      {rule.tenant_id && (
                        <span>
                          Tenant:{' '}
                          {tenantsData?.items?.find(t => t.id === rule.tenant_id)?.name ||
                            rule.tenant_id}
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleOpenModal(rule)}
                    className="p-2 text-gray-400 hover:text-primary-600 hover:bg-primary-50 dark:hover:bg-primary-900/20 rounded-lg transition-colors"
                    title="Edit"
                  >
                    <Edit2 className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => handleDelete(rule.id)}
                    className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
                    title="Delete"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                {editingRule ? 'Edit Alert Rule' : 'Create Alert Rule'}
              </h2>
              <button
                onClick={handleCloseModal}
                className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="p-6 space-y-6">
              {/* Rule Name */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Rule Name *
                </label>
                <input
                  type="text"
                  required
                  value={formData.name || ''}
                  onChange={e => setFormData(prev => ({ ...prev, name: e.target.value }))}
                  className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:text-white"
                  placeholder="e.g., High Risk Travel Alerts"
                />
              </div>

              {/* Event Types */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Event Types *
                </label>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {EVENT_TYPES.map(et => (
                    <label
                      key={et.value}
                      className={cn(
                        'flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-all',
                        formData.event_types?.includes(et.value)
                          ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
                          : 'border-gray-200 dark:border-gray-700 hover:border-gray-300'
                      )}
                    >
                      <input
                        type="checkbox"
                        checked={formData.event_types?.includes(et.value)}
                        onChange={() => handleToggleEventType(et.value)}
                        className="mt-0.5 w-4 h-4 text-primary-500 rounded border-gray-300 focus:ring-primary-500"
                      />
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          {et.icon}
                          <span className="text-sm font-medium text-gray-900 dark:text-white">
                            {et.label}
                          </span>
                        </div>
                        <p className="text-xs text-gray-500 mt-0.5">{et.description}</p>
                      </div>
                    </label>
                  ))}
                </div>
              </div>

              {/* Minimum Severity */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Minimum Severity
                </label>
                <div className="flex gap-2">
                  {SEVERITY_LEVELS.map(sev => (
                    <button
                      key={sev.value}
                      type="button"
                      onClick={() => setFormData(prev => ({ ...prev, min_severity: sev.value }))}
                      className={cn(
                        'flex-1 py-2 px-3 text-sm font-medium rounded-lg border transition-all',
                        formData.min_severity === sev.value
                          ? cn('border-transparent', sev.bgColor, sev.color)
                          : 'border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400 hover:border-gray-300'
                      )}
                    >
                      {sev.label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                {/* Cooldown */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Cooldown (minutes)
                  </label>
                  <input
                    type="number"
                    min={0}
                    max={1440}
                    value={formData.cooldown_minutes || 30}
                    onChange={e =>
                      setFormData(prev => ({ ...prev, cooldown_minutes: parseInt(e.target.value) }))
                    }
                    className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:text-white"
                  />
                  <p className="mt-1 text-xs text-gray-500">Time before duplicate alerts</p>
                </div>

                {/* Tenant (optional) */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Tenant (optional)
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
              </div>

              {/* Active Status */}
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={formData.is_active !== false}
                  onChange={e => setFormData(prev => ({ ...prev, is_active: e.target.checked }))}
                  className="w-4 h-4 text-primary-500 rounded border-gray-300 focus:ring-primary-500"
                />
                <span className="text-sm text-gray-700 dark:text-gray-300">Rule is active</span>
              </label>

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
                  disabled={createRule.isPending || updateRule.isPending}
                  className="flex items-center gap-2 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  <Save className="w-4 h-4" />
                  {createRule.isPending || updateRule.isPending
                    ? 'Saving...'
                    : editingRule
                      ? 'Update'
                      : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
