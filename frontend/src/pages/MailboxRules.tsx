import { useState, useEffect } from 'react';
import { Mail, MailWarning, Shield, RefreshCw, ExternalLink, Clock, UserX } from 'lucide-react';
import { apiService } from '@/services/api';
import type { MailboxRule, MailboxRuleAlert } from '@/types/securityTypes';
import clsx from 'clsx';

const statusColors: Record<string, string> = {
  active: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
  suspicious: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400',
  malicious: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
  benign: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400',
  disabled: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-400',
};

const severityColors: Record<string, string> = {
  LOW: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
  MEDIUM: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400',
  HIGH: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400',
  CRITICAL: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
};

export default function MailboxRules() {
  const [rules, setRules] = useState<MailboxRule[]>([]);
  const [alerts, setAlerts] = useState<MailboxRuleAlert[]>([]);
  const [totalRules, setTotalRules] = useState(0);
  const [totalAlerts, setTotalAlerts] = useState(0);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [rulesRes, alertsRes] = await Promise.all([
        apiService.getMailboxRules({ status: statusFilter || undefined, limit: 100 }),
        apiService.getMailboxRuleAlerts({ acknowledged: false, limit: 20 }),
      ]);
      setRules(rulesRes.items);
      setTotalRules(rulesRes.total);
      setAlerts(alertsRes.items);
      setTotalAlerts(alertsRes.total);
    } catch (err) {
      setError('Failed to load mailbox rules data');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, [statusFilter]);

  const suspiciousCount = rules.filter(r => r.status === 'suspicious').length;
  const maliciousCount = rules.filter(r => r.status === 'malicious').length;
  const externalForwardCount = rules.filter(r => r.forward_to_external).length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Mailbox Rules</h1>
          <p className="mt-1 text-gray-500 dark:text-gray-400">Monitor mailbox forwarding rules and detect suspicious configurations</p>
        </div>
        <button onClick={fetchData} disabled={isLoading}
          className="flex items-center gap-2 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors disabled:opacity-50">
          <RefreshCw className={clsx('w-4 h-4', isLoading && 'animate-spin')} /> Refresh
        </button>
      </div>

      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 text-red-700 dark:text-red-400">{error}</div>
      )}

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-gray-800 rounded-xl p-5 border border-gray-200 dark:border-gray-700 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-blue-100 dark:bg-blue-900/30 rounded-lg"><Mail className="w-5 h-5 text-blue-600 dark:text-blue-400" /></div>
            <div><p className="text-sm text-gray-500 dark:text-gray-400">Total Rules</p><p className="text-2xl font-bold text-gray-900 dark:text-white">{totalRules}</p></div>
          </div>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-xl p-5 border border-gray-200 dark:border-gray-700 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-amber-100 dark:bg-amber-900/30 rounded-lg"><MailWarning className="w-5 h-5 text-amber-600 dark:text-amber-400" /></div>
            <div><p className="text-sm text-gray-500 dark:text-gray-400">Suspicious</p><p className="text-2xl font-bold text-gray-900 dark:text-white">{suspiciousCount}</p></div>
          </div>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-xl p-5 border border-gray-200 dark:border-gray-700 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-red-100 dark:bg-red-900/30 rounded-lg"><Shield className="w-5 h-5 text-red-600 dark:text-red-400" /></div>
            <div><p className="text-sm text-gray-500 dark:text-gray-400">Malicious</p><p className="text-2xl font-bold text-gray-900 dark:text-white">{maliciousCount}</p></div>
          </div>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-xl p-5 border border-gray-200 dark:border-gray-700 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-violet-100 dark:bg-violet-900/30 rounded-lg"><ExternalLink className="w-5 h-5 text-violet-600 dark:text-violet-400" /></div>
            <div><p className="text-sm text-gray-500 dark:text-gray-400">External Fwd</p><p className="text-2xl font-bold text-gray-900 dark:text-white">{externalForwardCount}</p></div>
          </div>
        </div>
      </div>

      {/* Rules Table */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Rules</h2>
          <div className="flex bg-gray-100 dark:bg-gray-700 rounded-lg p-1 flex-wrap">
            {['', 'suspicious', 'malicious', 'active', 'benign'].map(s => (
              <button key={s} onClick={() => setStatusFilter(s)}
                className={clsx('px-3 py-1.5 text-xs font-medium rounded-md transition-colors',
                  statusFilter === s ? 'bg-white dark:bg-gray-600 text-gray-900 dark:text-white shadow-sm' : 'text-gray-600 dark:text-gray-400')}>
                {s === '' ? 'All' : s.charAt(0).toUpperCase() + s.slice(1)}
              </button>
            ))}
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="bg-gray-50 dark:bg-gray-900/50">
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">User</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Rule Name</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Type</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Status</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Severity</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Flags</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {isLoading ? (
                <tr><td colSpan={6} className="px-6 py-12 text-center text-gray-500 dark:text-gray-400">
                  <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2" />Loading rules...
                </td></tr>
              ) : rules.length === 0 ? (
                <tr><td colSpan={6} className="px-6 py-12 text-center text-gray-500 dark:text-gray-400">No rules found</td></tr>
              ) : rules.map(rule => (
                <tr key={rule.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
                  <td className="px-6 py-4">
                    <p className="text-sm text-gray-900 dark:text-white truncate max-w-[200px]">{rule.user_email}</p>
                  </td>
                  <td className="px-6 py-4">
                    <p className="text-sm font-medium text-gray-900 dark:text-white">{rule.rule_name}</p>
                    {rule.forward_to && <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">→ {rule.forward_to}</p>}
                  </td>
                  <td className="px-6 py-4"><span className="text-sm text-gray-600 dark:text-gray-300 capitalize">{rule.rule_type.replace('_', ' ')}</span></td>
                  <td className="px-6 py-4"><span className={clsx('px-2.5 py-1 rounded-full text-xs font-medium', statusColors[rule.status] || 'bg-gray-100 text-gray-800')}>{rule.status}</span></td>
                  <td className="px-6 py-4"><span className={clsx('px-2.5 py-1 rounded-full text-xs font-medium', severityColors[rule.severity] || 'bg-gray-100 text-gray-800')}>{rule.severity}</span></td>
                  <td className="px-6 py-4">
                    <div className="flex gap-1.5 flex-wrap">
                      {rule.forward_to_external && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 text-xs rounded" title="External forwarding">
                          <ExternalLink className="w-3 h-3" />Ext
                        </span>
                      )}
                      {rule.created_outside_business_hours && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400 text-xs rounded" title="Created outside business hours">
                          <Clock className="w-3 h-3" />Off-hrs
                        </span>
                      )}
                      {rule.created_by_non_owner && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400 text-xs rounded" title="Created by non-owner">
                          <UserX className="w-3 h-3" />Non-owner
                        </span>
                      )}
                      {rule.is_hidden_folder_redirect && (
                        <span className="px-2 py-0.5 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 text-xs rounded" title="Hidden folder redirect">Hidden</span>
                      )}
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
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{alert.user_email} · {alert.description}</p>
                  </div>
                  <span className={clsx('px-2 py-0.5 rounded text-xs font-medium whitespace-nowrap', severityColors[alert.severity])}>{alert.severity}</span>
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
