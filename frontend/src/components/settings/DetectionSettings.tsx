import { useState } from 'react';
import { Save, RotateCcw, Plane, Globe, Lock, Wifi, AlertTriangle, TrendingUp } from 'lucide-react';
import { useDetectionThresholds, useUpdateDetectionThresholds } from '@/hooks/useSettings';
import toast from 'react-hot-toast';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface DetectionCardProps {
  title: string;
  description: string;
  icon: React.ReactNode;
  enabled: boolean;
  onToggle: (enabled: boolean) => void;
  children: React.ReactNode;
}

function DetectionCard({ title, description, icon, enabled, onToggle, children }: DetectionCardProps) {
  return (
    <div className={cn(
      "bg-white dark:bg-gray-800 rounded-lg border p-6 transition-all",
      enabled
        ? "border-primary-200 dark:border-primary-800"
        : "border-gray-200 dark:border-gray-700 opacity-75"
    )}>
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className={cn(
            "p-2 rounded-lg",
            enabled ? "bg-primary-100 dark:bg-primary-900/30" : "bg-gray-100 dark:bg-gray-700"
          )}>
            {icon}
          </div>
          <div>
            <h4 className="font-semibold text-gray-900 dark:text-white">{title}</h4>
            <p className="text-sm text-gray-500">{description}</p>
          </div>
        </div>

        <label className="relative inline-flex items-center cursor-pointer">
          <input
            type="checkbox"
            checked={enabled}
            onChange={(e) => onToggle(e.target.checked)}
            className="sr-only peer"
          />
          <div className={cn(
            "w-11 h-6 rounded-full peer peer-focus:ring-4 peer-focus:ring-primary-300",
            "after:content-[''] after:absolute after:top-[2px] after:left-[2px]",
            "after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5",
            "after:transition-all peer-checked:after:translate-x-full",
            enabled ? "bg-primary-500" : "bg-gray-200 dark:bg-gray-700"
          )}></div>
        </label>
      </div>

      {enabled && <div className="pt-4 border-t border-gray-100 dark:border-gray-700">{children}</div>}
    </div>
  );
}

interface DetectionSettingsProps {
  tenantId?: string;
}

export default function DetectionSettings({ tenantId }: DetectionSettingsProps) {
  const { data: thresholds, isLoading } = useDetectionThresholds(tenantId);
  const updateThresholds = useUpdateDetectionThresholds(tenantId);
  const [formData, setFormData] = useState<Record<string, number | boolean>>({});

  const currentThresholds = { ...thresholds, ...formData };

  const handleChange = (field: string, value: number | boolean) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      await updateThresholds.mutateAsync({
        impossible_travel_enabled: currentThresholds.impossible_travel_enabled,
        impossible_travel_min_speed_kmh: currentThresholds.impossible_travel_min_speed_kmh,
        impossible_travel_time_window_minutes: currentThresholds.impossible_travel_time_window_minutes,
        new_country_enabled: currentThresholds.new_country_enabled,
        new_country_learning_period_days: currentThresholds.new_country_learning_period_days,
        brute_force_enabled: currentThresholds.brute_force_enabled,
        brute_force_threshold: currentThresholds.brute_force_threshold,
        brute_force_window_minutes: currentThresholds.brute_force_window_minutes,
        new_ip_enabled: currentThresholds.new_ip_enabled,
        new_ip_learning_period_days: currentThresholds.new_ip_learning_period_days,
        multiple_failures_enabled: currentThresholds.multiple_failures_enabled,
        multiple_failures_threshold: currentThresholds.multiple_failures_threshold,
        multiple_failures_window_minutes: currentThresholds.multiple_failures_window_minutes,
        risk_score_base_multiplier: currentThresholds.risk_score_base_multiplier,
      });
      setFormData({});
      toast.success('Detection thresholds updated successfully');
    } catch {
      toast.error('Failed to update detection thresholds');
    }
  };

  const handleReset = () => {
    setFormData({});
    toast('Settings reset to saved values', { icon: '↩️' });
  };

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-4">
        {[1, 2, 3, 4].map(i => (
          <div key={i} className="h-48 bg-gray-200 dark:bg-gray-700 rounded-lg" />
        ))}
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Risk Score Multiplier */}
      <div className="bg-gradient-to-r from-primary-500 to-primary-600 rounded-lg p-6 text-white">
        <div className="flex items-center gap-3 mb-4">
          <TrendingUp className="w-6 h-6" />
          <h3 className="text-lg font-semibold">Risk Score Multiplier</h3>
        </div>

        <div className="flex items-center gap-6">
          <div className="flex-1">
            <input
              type="range"
              min={0.1}
              max={10}
              step={0.1}
              value={currentThresholds.risk_score_base_multiplier || 1}
              onChange={(e) => handleChange('risk_score_base_multiplier', parseFloat(e.target.value))}
              className="w-full h-2 bg-white/30 rounded-lg appearance-none cursor-pointer"
            />
            <div className="flex justify-between mt-2 text-sm opacity-80">
              <span>Conservative (0.1x)</span>
              <span>Aggressive (10x)</span>
            </div>
          </div>
          <div className="text-center min-w-[100px]">
            <span className="text-3xl font-bold">{currentThresholds.risk_score_base_multiplier || 1}x</span>
          </div>
        </div>
        <p className="mt-4 text-sm opacity-90">
          Adjust the base multiplier for all risk scores. Higher values make the system more sensitive.
        </p>
      </div>

      {/* Detection Cards Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Impossible Travel */}
        <DetectionCard
          title="Impossible Travel"
          description="Detect logins from geographically distant locations in unrealistic timeframes"
          icon={<Plane className="w-5 h-5 text-primary-500" />}
          enabled={currentThresholds.impossible_travel_enabled !== false}
          onToggle={(v) => handleChange('impossible_travel_enabled', v)}
        >
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Minimum Speed (km/h)
              </label>
              <input
                type="number"
                min={100}
                max={5000}
                value={currentThresholds.impossible_travel_min_speed_kmh || 800}
                onChange={(e) => handleChange('impossible_travel_min_speed_kmh', parseInt(e.target.value))}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:text-white"
              />
              <p className="mt-1 text-xs text-gray-500">Speed threshold to trigger alert (commercial flights ~900 km/h)</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Time Window (minutes)
              </label>
              <input
                type="number"
                min={5}
                max={1440}
                value={currentThresholds.impossible_travel_time_window_minutes || 60}
                onChange={(e) => handleChange('impossible_travel_time_window_minutes', parseInt(e.target.value))}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:text-white"
              />
            </div>
          </div>
        </DetectionCard>

        {/* New Country */}
        <DetectionCard
          title="New Country Login"
          description="Flag logins from countries not previously seen for a user"
          icon={<Globe className="w-5 h-5 text-green-500" />}
          enabled={currentThresholds.new_country_enabled !== false}
          onToggle={(v) => handleChange('new_country_enabled', v)}
        >
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Learning Period (days)
            </label>
            <input
              type="number"
              min={1}
              max={90}
              value={currentThresholds.new_country_learning_period_days || 30}
              onChange={(e) => handleChange('new_country_learning_period_days', parseInt(e.target.value))}
              className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:text-white"
            />
            <p className="mt-1 text-xs text-gray-500">
              Days of login history to establish baseline countries
            </p>
          </div>
        </DetectionCard>

        {/* Brute Force */}
        <DetectionCard
          title="Brute Force Detection"
          description="Detect multiple failed login attempts in a short time window"
          icon={<Lock className="w-5 h-5 text-red-500" />}
          enabled={currentThresholds.brute_force_enabled !== false}
          onToggle={(v) => handleChange('brute_force_enabled', v)}
        >
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Failed Attempts Threshold
              </label>
              <input
                type="number"
                min={1}
                max={100}
                value={currentThresholds.brute_force_threshold || 5}
                onChange={(e) => handleChange('brute_force_threshold', parseInt(e.target.value))}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:text-white"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Time Window (minutes)
              </label>
              <input
                type="number"
                min={5}
                max={1440}
                value={currentThresholds.brute_force_window_minutes || 30}
                onChange={(e) => handleChange('brute_force_window_minutes', parseInt(e.target.value))}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:text-white"
              />
            </div>
          </div>
        </DetectionCard>

        {/* New IP */}
        <DetectionCard
          title="New IP Address"
          description="Flag logins from new IP addresses"
          icon={<Wifi className="w-5 h-5 text-blue-500" />}
          enabled={currentThresholds.new_ip_enabled !== false}
          onToggle={(v) => handleChange('new_ip_enabled', v)}
        >
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Learning Period (days)
            </label>
            <input
              type="number"
              min={1}
              max={90}
              value={currentThresholds.new_ip_learning_period_days || 7}
              onChange={(e) => handleChange('new_ip_learning_period_days', parseInt(e.target.value))}
              className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:text-white"
            />
            <p className="mt-1 text-xs text-gray-500">
              Days of login history to establish known IPs
            </p>
          </div>
        </DetectionCard>

        {/* Multiple Failures */}
        <DetectionCard
          title="Multiple Login Failures"
          description="Detect users with repeated authentication failures"
          icon={<AlertTriangle className="w-5 h-5 text-orange-500" />}
          enabled={currentThresholds.multiple_failures_enabled !== false}
          onToggle={(v) => handleChange('multiple_failures_enabled', v)}
        >
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Failed Attempts Threshold
              </label>
              <input
                type="number"
                min={1}
                max={100}
                value={currentThresholds.multiple_failures_threshold || 3}
                onChange={(e) => handleChange('multiple_failures_threshold', parseInt(e.target.value))}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:text-white"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Time Window (minutes)
              </label>
              <input
                type="number"
                min={5}
                max={1440}
                value={currentThresholds.multiple_failures_window_minutes || 60}
                onChange={(e) => handleChange('multiple_failures_window_minutes', parseInt(e.target.value))}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:text-white"
              />
            </div>
          </div>
        </DetectionCard>
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
          disabled={updateThresholds.isPending}
          className="flex items-center gap-2 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <Save className="w-4 h-4" />
          {updateThresholds.isPending ? 'Saving...' : 'Save Changes'}
        </button>
      </div>
    </form>
  );
}
