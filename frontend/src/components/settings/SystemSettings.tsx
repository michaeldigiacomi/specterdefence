import { useState } from 'react';
import { Save, RotateCcw, Database, Clock, Server, FileText } from 'lucide-react';
import { useSystemSettings, useUpdateSystemSettings } from '@/hooks/useSettings';
import toast from 'react-hot-toast';

const LOG_LEVELS = [
  { value: 'DEBUG', label: 'Debug', description: 'Detailed debugging information' },
  { value: 'INFO', label: 'Info', description: 'General operational information' },
  { value: 'WARNING', label: 'Warning', description: 'Warning messages only' },
  { value: 'ERROR', label: 'Error', description: 'Error messages only' },
  { value: 'CRITICAL', label: 'Critical', description: 'Critical errors only' },
];

export default function SystemSettings() {
  const { data: settings, isLoading } = useSystemSettings();
  const updateSettings = useUpdateSystemSettings();
  const [formData, setFormData] = useState<Record<string, number | boolean | string>>({});

  // Apply loaded settings to form when available
  const currentSettings = { ...settings, ...formData };

  const handleChange = (field: string, value: number | boolean | string) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    try {
      await updateSettings.mutateAsync({
        audit_log_retention_days: currentSettings.audit_log_retention_days,
        login_history_retention_days: currentSettings.login_history_retention_days,
        alert_history_retention_days: currentSettings.alert_history_retention_days,
        auto_cleanup_enabled: currentSettings.auto_cleanup_enabled,
        cleanup_schedule: currentSettings.cleanup_schedule,
        api_rate_limit: currentSettings.api_rate_limit,
        max_export_rows: currentSettings.max_export_rows,
        log_level: currentSettings.log_level,
      });
      setFormData({}); // Clear local changes
      toast.success('System settings updated successfully');
    } catch {
      toast.error('Failed to update system settings');
    }
  };

  const handleReset = () => {
    setFormData({});
    toast('Settings reset to saved values', { icon: '↩️' });
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
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Data Retention Section */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
        <div className="flex items-center gap-2 mb-4">
          <Database className="w-5 h-5 text-primary-500" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Data Retention</h3>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Audit Log Retention (days)
            </label>
            <input
              type="number"
              min={1}
              max={3650}
              value={currentSettings.audit_log_retention_days || 90}
              onChange={(e) => handleChange('audit_log_retention_days', parseInt(e.target.value))}
              className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:text-white"
            />
            <p className="mt-1 text-xs text-gray-500">Days to keep audit logs</p>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Login History Retention (days)
            </label>
            <input
              type="number"
              min={1}
              max={3650}
              value={currentSettings.login_history_retention_days || 365}
              onChange={(e) => handleChange('login_history_retention_days', parseInt(e.target.value))}
              className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:text-white"
            />
            <p className="mt-1 text-xs text-gray-500">Days to keep login history</p>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Alert History Retention (days)
            </label>
            <input
              type="number"
              min={1}
              max={3650}
              value={currentSettings.alert_history_retention_days || 180}
              onChange={(e) => handleChange('alert_history_retention_days', parseInt(e.target.value))}
              className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:text-white"
            />
            <p className="mt-1 text-xs text-gray-500">Days to keep alert history</p>
          </div>
        </div>
        
        <div className="mt-6 flex items-center gap-4">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={currentSettings.auto_cleanup_enabled !== false}
              onChange={(e) => handleChange('auto_cleanup_enabled', e.target.checked)}
              className="w-4 h-4 text-primary-500 rounded border-gray-300 focus:ring-primary-500"
            />
            <span className="text-sm text-gray-700 dark:text-gray-300">Enable automatic cleanup</span>
          </label>
        </div>
      </div>

      {/* API Settings Section */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
        <div className="flex items-center gap-2 mb-4">
          <Server className="w-5 h-5 text-primary-500" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">API Settings</h3>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Rate Limit (requests/hour)
            </label>
            <input
              type="number"
              min={10}
              max={10000}
              value={currentSettings.api_rate_limit || 1000}
              onChange={(e) => handleChange('api_rate_limit', parseInt(e.target.value))}
              className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:text-white"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Max Export Rows
            </label>
            <input
              type="number"
              min={100}
              max={100000}
              value={currentSettings.max_export_rows || 10000}
              onChange={(e) => handleChange('max_export_rows', parseInt(e.target.value))}
              className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:text-white"
            />
          </div>
        </div>
      </div>

      {/* Logging Section */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
        <div className="flex items-center gap-2 mb-4">
          <FileText className="w-5 h-5 text-primary-500" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Logging</h3>
        </div>
        
        <div className="space-y-3">
          {LOG_LEVELS.map((level) => (
            <label key={level.value} className="flex items-start gap-3 cursor-pointer">
              <input
                type="radio"
                name="log_level"
                value={level.value}
                checked={(currentSettings.log_level || 'INFO') === level.value}
                onChange={(e) => handleChange('log_level', e.target.value)}
                className="mt-1 w-4 h-4 text-primary-500 border-gray-300 focus:ring-primary-500"
              />
              <div>
                <span className="text-sm font-medium text-gray-900 dark:text-white">{level.label}</span>
                <p className="text-xs text-gray-500">{level.description}</p>
              </div>
            </label>
          ))}
        </div>
      </div>

      {/* Cleanup Schedule Section */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
        <div className="flex items-center gap-2 mb-4">
          <Clock className="w-5 h-5 text-primary-500" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Cleanup Schedule</h3>
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Cron Schedule
          </label>
          <input
            type="text"
            value={currentSettings.cleanup_schedule || '0 2 * * *'}
            onChange={(e) => handleChange('cleanup_schedule', e.target.value)}
            placeholder="0 2 * * *"
            className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:text-white font-mono"
          />
          <p className="mt-1 text-xs text-gray-500">
            Cron expression (default: 2:00 AM daily). Format: minute hour day month weekday
          </p>
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center justify-end gap-3">
        <button
          type="button"
          onClick={handleReset}
          className="flex items-center gap-2 px-4 py-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
        >
          <RotateCcw className="w-4 h-4" />
          Reset
        </button>
        <button
          type="submit"
          disabled={updateSettings.isPending}
          className="flex items-center gap-2 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <Save className="w-4 h-4" />
          {updateSettings.isPending ? 'Saving...' : 'Save Changes'}
        </button>
      </div>
    </form>
  );
}
