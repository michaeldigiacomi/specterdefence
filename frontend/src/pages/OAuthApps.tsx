import { useState, useEffect } from 'react';
import { AppWindow, ShieldAlert, AlertTriangle, RefreshCw, Mail, Users, FileText, Calendar } from 'lucide-react';
import { apiService } from '@/services/api';
import type { OAuthApp, OAuthAppAlert } from '@/types/securityTypes';
import clsx from 'clsx';

const riskColors: Record<string, string> = {
  LOW: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
  MEDIUM: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400',
  HIGH: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400',
  CRITICAL: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
};

const statusColors: Record<string, string> = {
  approved: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400',
  suspicious: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400',
  malicious: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
  revoked: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-400',
  pending_review: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
};

const publisherColors: Record<string, string> = {
  microsoft: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
  verified: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400',
  unverified: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400',
  unknown: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-400',
};

export default function OAuthApps() {
  const [apps, setApps] = useState<OAuthApp[]>([]);
  const [alerts, setAlerts] = useState<OAuthAppAlert[]>([]);
  const [totalApps, setTotalApps] = useState(0);
  const [totalAlerts, setTotalAlerts] = useState(0);
  const [riskFilter, setRiskFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [appsRes, alertsRes] = await Promise.all([
        apiService.getOAuthApps({
          risk_level: riskFilter || undefined,
          status: statusFilter || undefined,
          limit: 100,
        }),
        apiService.getOAuthAppAlerts({ acknowledged: false, limit: 20 }),
      ]);
      setApps(appsRes.items);
      setTotalApps(appsRes.total);
      setAlerts(alertsRes.items);
      setTotalAlerts(alertsRes.total);
    } catch {
      setError('Failed to load OAuth applications data');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, [riskFilter, statusFilter]);

  const highRiskCount = apps.filter(a => a.risk_level === 'HIGH' || a.risk_level === 'CRITICAL').length;
  const unverifiedCount = apps.filter(a => a.publisher_type === 'unverified' || a.publisher_type === 'unknown').length;
  const mailAccessCount = apps.filter(a => a.has_mail_permissions).length;

  return (
    <div className="space-y-6">
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">OAuth Applications</h1>
          <p className="mt-1 text-gray-500 dark:text-gray-400">Monitor third-party app integrations, permissions, and risk levels</p>
        </div>
        <button onClick={fetchData} disabled={isLoading}
          className="flex items-center gap-2 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors disabled:opacity-50">
          <RefreshCw className={clsx('w-4 h-4', isLoading && 'animate-spin')} /> Refresh
        </button>
      </div>

      {error && <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 text-red-700 dark:text-red-400">{error}</div>}

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-gray-800 rounded-xl p-5 border border-gray-200 dark:border-gray-700 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-blue-100 dark:bg-blue-900/30 rounded-lg"><AppWindow className="w-5 h-5 text-blue-600 dark:text-blue-400" /></div>
            <div><p className="text-sm text-gray-500 dark:text-gray-400">Total Apps</p><p className="text-2xl font-bold text-gray-900 dark:text-white">{totalApps}</p></div>
          </div>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-xl p-5 border border-gray-200 dark:border-gray-700 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-red-100 dark:bg-red-900/30 rounded-lg"><ShieldAlert className="w-5 h-5 text-red-600 dark:text-red-400" /></div>
            <div><p className="text-sm text-gray-500 dark:text-gray-400">High Risk</p><p className="text-2xl font-bold text-gray-900 dark:text-white">{highRiskCount}</p></div>
          </div>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-xl p-5 border border-gray-200 dark:border-gray-700 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-amber-100 dark:bg-amber-900/30 rounded-lg"><AlertTriangle className="w-5 h-5 text-amber-600 dark:text-amber-400" /></div>
            <div><p className="text-sm text-gray-500 dark:text-gray-400">Unverified</p><p className="text-2xl font-bold text-gray-900 dark:text-white">{unverifiedCount}</p></div>
          </div>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-xl p-5 border border-gray-200 dark:border-gray-700 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-violet-100 dark:bg-violet-900/30 rounded-lg"><Mail className="w-5 h-5 text-violet-600 dark:text-violet-400" /></div>
            <div><p className="text-sm text-gray-500 dark:text-gray-400">Mail Access</p><p className="text-2xl font-bold text-gray-900 dark:text-white">{mailAccessCount}</p></div>
          </div>
        </div>
      </div>

      {/* Apps Table */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Applications</h2>
          <div className="flex gap-2 flex-wrap">
            <select value={riskFilter} onChange={e => setRiskFilter(e.target.value)}
              className="px-3 py-1.5 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-xs text-gray-900 dark:text-white">
              <option value="">All Risk</option>
              <option value="CRITICAL">Critical</option>
              <option value="HIGH">High</option>
              <option value="MEDIUM">Medium</option>
              <option value="LOW">Low</option>
            </select>
            <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
              className="px-3 py-1.5 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-xs text-gray-900 dark:text-white">
              <option value="">All Status</option>
              <option value="suspicious">Suspicious</option>
              <option value="malicious">Malicious</option>
              <option value="approved">Approved</option>
              <option value="pending_review">Pending</option>
              <option value="revoked">Revoked</option>
            </select>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="bg-gray-50 dark:bg-gray-900/50">
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Application</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Publisher</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Risk</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Status</th>
                <th className="text-center px-6 py-3 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Perms</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Access Flags</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {isLoading ? (
                <tr><td colSpan={6} className="px-6 py-12 text-center text-gray-500"><RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2" />Loading...</td></tr>
              ) : apps.length === 0 ? (
                <tr><td colSpan={6} className="px-6 py-12 text-center text-gray-500">No apps found</td></tr>
              ) : apps.map(app => (
                <tr key={app.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      {app.is_new_app && <span className="px-1.5 py-0.5 bg-blue-500 text-white text-[10px] rounded font-medium">NEW</span>}
                      <div>
                        <p className="text-sm font-medium text-gray-900 dark:text-white">{app.display_name}</p>
                        <p className="text-xs text-gray-500 mt-0.5">{app.consent_count} consent(s)</p>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span className={clsx('px-2 py-0.5 rounded text-xs font-medium', publisherColors[app.publisher_type] || 'bg-gray-100 text-gray-600')}>
                      {app.publisher_name || app.publisher_type}
                    </span>
                  </td>
                  <td className="px-6 py-4"><span className={clsx('px-2.5 py-1 rounded-full text-xs font-medium', riskColors[app.risk_level])}>{app.risk_level}</span></td>
                  <td className="px-6 py-4"><span className={clsx('px-2.5 py-1 rounded-full text-xs font-medium', statusColors[app.status] || 'bg-gray-100 text-gray-800')}>{app.status.replace('_',' ')}</span></td>
                  <td className="px-6 py-4 text-center">
                    <span className="text-sm font-medium text-gray-900 dark:text-white">{app.permission_count}</span>
                    {app.high_risk_permissions.length > 0 && (
                      <span className="ml-1 text-xs text-red-500">({app.high_risk_permissions.length} risky)</span>
                    )}
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex gap-1 flex-wrap">
                      {app.has_mail_permissions && <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 text-[10px] rounded" title="Mail access"><Mail className="w-3 h-3" /></span>}
                      {app.has_user_read_all && <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400 text-[10px] rounded" title="User.Read.All"><Users className="w-3 h-3" /></span>}
                      {app.has_files_read_all && <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400 text-[10px] rounded" title="Files.Read.All"><FileText className="w-3 h-3" /></span>}
                      {app.has_calendar_access && <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 text-[10px] rounded" title="Calendar access"><Calendar className="w-3 h-3" /></span>}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Alerts */}
      {totalAlerts > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm">
          <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              Unacknowledged Alerts <span className="ml-2 px-2 py-0.5 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 text-xs rounded-full">{totalAlerts}</span>
            </h2>
          </div>
          <div className="divide-y divide-gray-200 dark:divide-gray-700 max-h-80 overflow-y-auto">
            {alerts.map(alert => (
              <div key={alert.id} className="px-6 py-4 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-gray-900 dark:text-white">{alert.title}</p>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5 line-clamp-2">{alert.description}</p>
                  </div>
                  <span className={clsx('px-2 py-0.5 rounded text-xs font-medium whitespace-nowrap', riskColors[alert.severity])}>{alert.severity}</span>
                </div>
                <p className="text-xs text-gray-400 mt-1.5">{new Date(alert.created_at).toLocaleString()}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
