import { useState, useEffect } from 'react';
import {
  ShieldCheck,
  ShieldAlert,
  ShieldOff,
  Eye,
  AlertTriangle,
  RefreshCw,
  CheckCircle2,
  XCircle,
} from 'lucide-react';
import { apiService } from '@/services/api';
import type {
  CAPolicy,
  CAPolicyChange,
  CAPolicyAlert,
  CAPolicyListResponse,
  CAPolicyChangeListResponse,
  CAPolicyAlertListResponse,
} from '@/types/securityTypes';
import clsx from 'clsx';

const stateColors: Record<string, string> = {
  enabled: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400',
  disabled: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
  reportOnly: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400',
};

const severityColors: Record<string, string> = {
  LOW: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
  MEDIUM: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400',
  HIGH: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400',
  CRITICAL: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
};

const changeTypeIcons: Record<string, string> = {
  created: '🆕',
  updated: '✏️',
  deleted: '🗑️',
  enabled: '✅',
  disabled: '⛔',
  baseline_drift: '⚠️',
};

export default function CAPolicies() {
  const [policies, setPolicies] = useState<CAPolicy[]>([]);
  const [changes, setChanges] = useState<CAPolicyChange[]>([]);
  const [alerts, setAlerts] = useState<CAPolicyAlert[]>([]);
  const [totalPolicies, setTotalPolicies] = useState(0);
  const [totalAlerts, setTotalAlerts] = useState(0);
  const [stateFilter, setStateFilter] = useState<string>('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [policiesRes, changesRes, alertsRes] = await Promise.all([
        apiService.getCAPolicies({ state: stateFilter || undefined, limit: 100 }),
        apiService.getCAPolicyChanges({ limit: 20 }),
        apiService.getCAPolicyAlerts({ acknowledged: false, limit: 20 }),
      ]);
      setPolicies(policiesRes.items);
      setTotalPolicies(policiesRes.total);
      setChanges(changesRes.items);
      setAlerts(alertsRes.items);
      setTotalAlerts(alertsRes.total);
    } catch (err) {
      setError('Failed to load Conditional Access policies data');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [stateFilter]);

  const enabledCount = policies.filter(p => p.state === 'enabled').length;
  const disabledCount = policies.filter(p => p.state === 'disabled').length;
  const mfaCount = policies.filter(p => p.is_mfa_required).length;
  const baselineViolations = policies.filter(
    p => p.is_baseline_policy && !p.baseline_compliant
  ).length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Conditional Access Policies
          </h1>
          <p className="mt-1 text-gray-500 dark:text-gray-400">
            Monitor and track Azure AD Conditional Access policy configurations
          </p>
        </div>
        <button
          onClick={fetchData}
          disabled={isLoading}
          className="flex items-center gap-2 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors disabled:opacity-50"
        >
          <RefreshCw className={clsx('w-4 h-4', isLoading && 'animate-spin')} />
          Refresh
        </button>
      </div>

      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 text-red-700 dark:text-red-400">
          {error}
        </div>
      )}

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-gray-800 rounded-xl p-5 border border-gray-200 dark:border-gray-700 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
              <ShieldCheck className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">Total Policies</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{totalPolicies}</p>
            </div>
          </div>
          <div className="mt-3 flex gap-3 text-xs">
            <span className="text-emerald-600 dark:text-emerald-400">{enabledCount} enabled</span>
            <span className="text-red-500">{disabledCount} disabled</span>
          </div>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-xl p-5 border border-gray-200 dark:border-gray-700 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-violet-100 dark:bg-violet-900/30 rounded-lg">
              <ShieldAlert className="w-5 h-5 text-violet-600 dark:text-violet-400" />
            </div>
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">MFA Policies</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{mfaCount}</p>
            </div>
          </div>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-xl p-5 border border-gray-200 dark:border-gray-700 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-amber-100 dark:bg-amber-900/30 rounded-lg">
              <ShieldOff className="w-5 h-5 text-amber-600 dark:text-amber-400" />
            </div>
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">Baseline Violations</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {baselineViolations}
              </p>
            </div>
          </div>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-xl p-5 border border-gray-200 dark:border-gray-700 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-red-100 dark:bg-red-900/30 rounded-lg">
              <AlertTriangle className="w-5 h-5 text-red-600 dark:text-red-400" />
            </div>
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">Unack. Alerts</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{totalAlerts}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Policies Table */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Policies</h2>
          <div className="flex bg-gray-100 dark:bg-gray-700 rounded-lg p-1">
            {['', 'enabled', 'disabled', 'reportOnly'].map(s => (
              <button
                key={s}
                onClick={() => setStateFilter(s)}
                className={clsx(
                  'px-3 py-1.5 text-xs font-medium rounded-md transition-colors',
                  stateFilter === s
                    ? 'bg-white dark:bg-gray-600 text-gray-900 dark:text-white shadow-sm'
                    : 'text-gray-600 dark:text-gray-400'
                )}
              >
                {s === ''
                  ? 'All'
                  : s === 'reportOnly'
                    ? 'Report Only'
                    : s.charAt(0).toUpperCase() + s.slice(1)}
              </button>
            ))}
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="bg-gray-50 dark:bg-gray-900/50">
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Policy Name
                </th>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  State
                </th>
                <th className="text-center px-6 py-3 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  MFA
                </th>
                <th className="text-center px-6 py-3 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Score
                </th>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Scope
                </th>
                <th className="text-center px-6 py-3 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Baseline
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {isLoading ? (
                <tr>
                  <td
                    colSpan={6}
                    className="px-6 py-12 text-center text-gray-500 dark:text-gray-400"
                  >
                    <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2" />
                    Loading policies...
                  </td>
                </tr>
              ) : policies.length === 0 ? (
                <tr>
                  <td
                    colSpan={6}
                    className="px-6 py-12 text-center text-gray-500 dark:text-gray-400"
                  >
                    No policies found
                  </td>
                </tr>
              ) : (
                policies.map(policy => (
                  <tr
                    key={policy.id}
                    className="hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
                  >
                    <td className="px-6 py-4">
                      <p className="text-sm font-medium text-gray-900 dark:text-white">
                        {policy.display_name}
                      </p>
                      {policy.description && (
                        <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5 truncate max-w-xs">
                          {policy.description}
                        </p>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      <span
                        className={clsx(
                          'px-2.5 py-1 rounded-full text-xs font-medium',
                          stateColors[policy.state] || 'bg-gray-100 text-gray-800'
                        )}
                      >
                        {policy.state}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-center">
                      {policy.is_mfa_required ? (
                        <CheckCircle2 className="w-5 h-5 text-emerald-500 mx-auto" />
                      ) : (
                        <XCircle className="w-5 h-5 text-gray-300 dark:text-gray-600 mx-auto" />
                      )}
                    </td>
                    <td className="px-6 py-4 text-center">
                      <span
                        className={clsx(
                          'text-sm font-semibold',
                          policy.security_score >= 70
                            ? 'text-emerald-600'
                            : policy.security_score >= 40
                              ? 'text-amber-600'
                              : 'text-red-600'
                        )}
                      >
                        {policy.security_score}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex gap-1 flex-wrap">
                        {policy.applies_to_all_users && (
                          <span className="px-2 py-0.5 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 text-xs rounded">
                            All Users
                          </span>
                        )}
                        {policy.applies_to_all_apps && (
                          <span className="px-2 py-0.5 bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400 text-xs rounded">
                            All Apps
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-center">
                      {policy.is_baseline_policy ? (
                        policy.baseline_compliant ? (
                          <CheckCircle2 className="w-5 h-5 text-emerald-500 mx-auto" />
                        ) : (
                          <AlertTriangle className="w-5 h-5 text-amber-500 mx-auto" />
                        )
                      ) : (
                        <span className="text-xs text-gray-400">—</span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Bottom Grid: Changes + Alerts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Changes */}
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm">
          <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Recent Changes</h2>
          </div>
          <div className="divide-y divide-gray-200 dark:divide-gray-700 max-h-96 overflow-y-auto">
            {changes.length === 0 ? (
              <p className="px-6 py-8 text-center text-gray-500 dark:text-gray-400">
                No recent changes
              </p>
            ) : (
              changes.map(change => (
                <div
                  key={change.id}
                  className="px-6 py-4 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
                >
                  <div className="flex items-start gap-3">
                    <span className="text-lg mt-0.5">
                      {changeTypeIcons[change.change_type] || '📝'}
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 dark:text-white capitalize">
                        {change.change_type.replace('_', ' ')}
                      </p>
                      {change.changes_summary.length > 0 && (
                        <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                          {change.changes_summary.join(', ')}
                        </p>
                      )}
                      <div className="flex items-center gap-2 mt-1.5">
                        <span
                          className={clsx(
                            'px-2 py-0.5 rounded text-xs font-medium',
                            severityColors[change.security_impact.toUpperCase()] ||
                              'bg-gray-100 text-gray-600'
                          )}
                        >
                          {change.security_impact}
                        </span>
                        {change.changed_by_email && (
                          <span className="text-xs text-gray-400">{change.changed_by_email}</span>
                        )}
                        <span className="text-xs text-gray-400">
                          {new Date(change.detected_at).toLocaleDateString()}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Alerts */}
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm">
          <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              Unacknowledged Alerts{' '}
              {totalAlerts > 0 && (
                <span className="ml-2 px-2 py-0.5 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 text-xs rounded-full">
                  {totalAlerts}
                </span>
              )}
            </h2>
          </div>
          <div className="divide-y divide-gray-200 dark:divide-gray-700 max-h-96 overflow-y-auto">
            {alerts.length === 0 ? (
              <p className="px-6 py-8 text-center text-gray-500 dark:text-gray-400">
                No unacknowledged alerts
              </p>
            ) : (
              alerts.map(alert => (
                <div
                  key={alert.id}
                  className="px-6 py-4 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-gray-900 dark:text-white">
                        {alert.title}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5 line-clamp-2">
                        {alert.description}
                      </p>
                    </div>
                    <span
                      className={clsx(
                        'px-2 py-0.5 rounded text-xs font-medium whitespace-nowrap',
                        severityColors[alert.severity]
                      )}
                    >
                      {alert.severity}
                    </span>
                  </div>
                  <p className="text-xs text-gray-400 mt-1.5">
                    {new Date(alert.created_at).toLocaleString()}
                  </p>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
