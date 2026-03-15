import { useState, useEffect } from 'react';
import { Save, Globe, Bell, Monitor, RotateCcw, Palette } from 'lucide-react';
import { useUserPreferences, useUpdateUserPreferences } from '@/hooks/useSettings';
import toast from 'react-hot-toast';
import { SeverityLevel } from '@/types';

const TIMEZONES = [
  { value: 'UTC', label: 'UTC (Coordinated Universal Time)' },
  { value: 'America/New_York', label: 'Eastern Time (ET)' },
  { value: 'America/Chicago', label: 'Central Time (CT)' },
  { value: 'America/Denver', label: 'Mountain Time (MT)' },
  { value: 'America/Los_Angeles', label: 'Pacific Time (PT)' },
  { value: 'Europe/London', label: 'London (GMT)' },
  { value: 'Europe/Paris', label: 'Paris (CET)' },
  { value: 'Europe/Berlin', label: 'Berlin (CET)' },
  { value: 'Asia/Tokyo', label: 'Tokyo (JST)' },
  { value: 'Asia/Singapore', label: 'Singapore (SGT)' },
  { value: 'Australia/Sydney', label: 'Sydney (AEST)' },
];

const DATE_FORMATS = [
  { value: 'ISO', label: 'ISO 8601 (2024-01-15)', example: '2024-01-15 14:30:00' },
  { value: 'US', label: 'US (01/15/2024)', example: '01/15/2024 02:30 PM' },
  { value: 'EU', label: 'European (15/01/2024)', example: '15/01/2024 14:30' },
];

const THEMES = [
  { value: 'light', label: 'Light', icon: SunIcon },
  { value: 'dark', label: 'Dark', icon: MoonIcon },
  { value: 'system', label: 'System', icon: MonitorIcon },
];

const SEVERITY_OPTIONS: { value: SeverityLevel; label: string; color: string }[] = [
  { value: 'LOW', label: 'Low', color: 'text-green-600' },
  { value: 'MEDIUM', label: 'Medium', color: 'text-yellow-600' },
  { value: 'HIGH', label: 'High', color: 'text-orange-600' },
  { value: 'CRITICAL', label: 'Critical', color: 'text-red-600' },
];

function SunIcon() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <circle cx="12" cy="12" r="5" strokeWidth="2" />
      <path
        strokeWidth="2"
        strokeLinecap="round"
        d="M12 1v2m0 18v2M4.22 4.22l1.42 1.42m12.72 12.72l1.42 1.42M1 12h2m18 0h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"
      />
    </svg>
  );
}

function MoonIcon() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"
      />
    </svg>
  );
}

function MonitorIcon() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <rect x="2" y="3" width="20" height="14" rx="2" strokeWidth="2" />
      <path strokeWidth="2" strokeLinecap="round" d="M8 21h8m-4-4v4" />
    </svg>
  );
}

interface UserPreferencesProps {
  userEmail: string;
}

export default function UserPreferences({ userEmail }: UserPreferencesProps) {
  const { data: preferences, isLoading } = useUserPreferences(userEmail);
  const updatePreferences = useUpdateUserPreferences(userEmail);
  const [formData, setFormData] = useState<Record<string, string | boolean | number>>({});

  // Reset form when preferences load
  useEffect(() => {
    if (preferences) {
      setFormData({});
    }
  }, [preferences]);

  const currentPrefs = { ...preferences, ...formData };

  const handleChange = (field: string, value: string | boolean | number) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      await updatePreferences.mutateAsync({
        timezone: currentPrefs.timezone,
        date_format: currentPrefs.date_format,
        theme: currentPrefs.theme,
        email_notifications: currentPrefs.email_notifications,
        discord_notifications: currentPrefs.discord_notifications,
        notification_min_severity: currentPrefs.notification_min_severity,
        default_dashboard_view: currentPrefs.default_dashboard_view,
        refresh_interval_seconds: currentPrefs.refresh_interval_seconds,
      });
      setFormData({});
      toast.success('Preferences updated successfully');
    } catch {
      toast.error('Failed to update preferences');
    }
  };

  const handleReset = () => {
    setFormData({});
    toast('Preferences reset to saved values', { icon: '↩️' });
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
      {/* Display Preferences */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
        <div className="flex items-center gap-2 mb-4">
          <Palette className="w-5 h-5 text-primary-500" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Display</h3>
        </div>

        <div className="space-y-6">
          {/* Theme Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
              Theme
            </label>
            <div className="grid grid-cols-3 gap-3">
              {THEMES.map(theme => {
                const Icon = theme.icon;
                return (
                  <button
                    key={theme.value}
                    type="button"
                    onClick={() => handleChange('theme', theme.value)}
                    className={`flex flex-col items-center gap-2 p-4 rounded-lg border-2 transition-all ${
                      (currentPrefs.theme || 'system') === theme.value
                        ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
                        : 'border-gray-200 dark:border-gray-700 hover:border-gray-300'
                    }`}
                  >
                    <Icon />
                    <span className="text-sm font-medium text-gray-900 dark:text-white">
                      {theme.label}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Date Format */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Date Format
            </label>
            <select
              value={currentPrefs.date_format || 'ISO'}
              onChange={e => handleChange('date_format', e.target.value)}
              className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:text-white"
            >
              {DATE_FORMATS.map(format => (
                <option key={format.value} value={format.value}>
                  {format.label}
                </option>
              ))}
            </select>
            <p className="mt-1 text-xs text-gray-500">
              Example:{' '}
              {DATE_FORMATS.find(f => f.value === (currentPrefs.date_format || 'ISO'))?.example}
            </p>
          </div>
        </div>
      </div>

      {/* Timezone */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
        <div className="flex items-center gap-2 mb-4">
          <Globe className="w-5 h-5 text-primary-500" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Timezone</h3>
        </div>

        <select
          value={currentPrefs.timezone || 'UTC'}
          onChange={e => handleChange('timezone', e.target.value)}
          className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:text-white"
        >
          {TIMEZONES.map(tz => (
            <option key={tz.value} value={tz.value}>
              {tz.label}
            </option>
          ))}
        </select>
        <p className="mt-2 text-sm text-gray-500">
          All times will be displayed in your selected timezone
        </p>
      </div>

      {/* Notifications */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
        <div className="flex items-center gap-2 mb-4">
          <Bell className="w-5 h-5 text-primary-500" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Notifications</h3>
        </div>

        <div className="space-y-4">
          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={currentPrefs.email_notifications !== false}
              onChange={e => handleChange('email_notifications', e.target.checked)}
              className="w-4 h-4 text-primary-500 rounded border-gray-300 focus:ring-primary-500"
            />
            <div>
              <span className="text-sm font-medium text-gray-900 dark:text-white">
                Email Notifications
              </span>
              <p className="text-xs text-gray-500">Receive alerts via email</p>
            </div>
          </label>

          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={currentPrefs.discord_notifications !== false}
              onChange={e => handleChange('discord_notifications', e.target.checked)}
              className="w-4 h-4 text-primary-500 rounded border-gray-300 focus:ring-primary-500"
            />
            <div>
              <span className="text-sm font-medium text-gray-900 dark:text-white">
                Discord Notifications
              </span>
              <p className="text-xs text-gray-500">Receive alerts via Discord</p>
            </div>
          </label>

          <div className="pt-2">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Minimum Severity
            </label>
            <div className="flex gap-3">
              {SEVERITY_OPTIONS.map(sev => (
                <button
                  key={sev.value}
                  type="button"
                  onClick={() => handleChange('notification_min_severity', sev.value)}
                  className={`px-3 py-1.5 text-sm font-medium rounded-full transition-colors ${
                    (currentPrefs.notification_min_severity || 'MEDIUM') === sev.value
                      ? 'bg-primary-100 text-primary-700 dark:bg-primary-900/30 dark:text-primary-400'
                      : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400 hover:bg-gray-200'
                  }`}
                >
                  {sev.label}
                </button>
              ))}
            </div>
            <p className="mt-2 text-xs text-gray-500">
              Only receive notifications for alerts at or above this severity level
            </p>
          </div>
        </div>
      </div>

      {/* Dashboard */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
        <div className="flex items-center gap-2 mb-4">
          <Monitor className="w-5 h-5 text-primary-500" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Dashboard</h3>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Auto-refresh Interval (seconds)
          </label>
          <input
            type="number"
            min={10}
            max={3600}
            value={currentPrefs.refresh_interval_seconds || 60}
            onChange={e => handleChange('refresh_interval_seconds', parseInt(e.target.value))}
            className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:text-white"
          />
          <p className="mt-1 text-xs text-gray-500">
            Dashboard will automatically refresh every {currentPrefs.refresh_interval_seconds || 60}{' '}
            seconds
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
          disabled={updatePreferences.isPending}
          className="flex items-center gap-2 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <Save className="w-4 h-4" />
          {updatePreferences.isPending ? 'Saving...' : 'Save Changes'}
        </button>
      </div>
    </form>
  );
}
