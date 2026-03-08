import { useState, useEffect } from 'react';
import { KeyRound, ShieldAlert, Users, UserCheck, AlertTriangle, RefreshCw, CheckCircle2, XCircle } from 'lucide-react';
import { apiService } from '@/services/api';
import type { MFAEnrollmentSummary, MFAUser } from '@/types/securityTypes';
import type { Tenant } from '@/types';
import clsx from 'clsx';

const strengthColors: Record<string, string> = {
  strong: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400',
  moderate: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
  weak: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400',
  none: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
};

const complianceColors: Record<string, string> = {
  compliant: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400',
  non_compliant: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
  exempt: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-400',
  pending: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400',
};

export default function MFAReport() {
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [selectedTenant, setSelectedTenant] = useState('');
  const [summary, setSummary] = useState<MFAEnrollmentSummary | null>(null);
  const [users, setUsers] = useState<MFAUser[]>([]);
  const [adminsWithoutMFA, setAdminsWithoutMFA] = useState<MFAUser[]>([]);
  const [totalUsers, setTotalUsers] = useState(0);
  const [userFilter, setUserFilter] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiService.getTenants().then(res => {
      setTenants(res.items);
      if (res.items.length > 0) setSelectedTenant(res.items[0].id);
    }).catch(console.error);
  }, []);

  const fetchData = async () => {
    if (!selectedTenant) return;
    setIsLoading(true);
    setError(null);
    try {
      const fp: Parameters<typeof apiService.getMFAUsers>[0] = { tenant_id: selectedTenant, limit: 50 };
      if (userFilter === 'needs_attention') fp.needs_attention = true;
      else if (userFilter === 'admin') fp.is_admin = true;
      else if (userFilter === 'no_mfa') fp.is_mfa_registered = false;

      const [sRes, uRes, aRes] = await Promise.all([
        apiService.getMFASummary(selectedTenant),
        apiService.getMFAUsers(fp),
        apiService.getAdminsWithoutMFA(selectedTenant),
      ]);
      setSummary(sRes);
      setUsers(uRes.items);
      setTotalUsers(uRes.total);
      setAdminsWithoutMFA(aRes.items);
    } catch {
      setError('Failed to load MFA report data');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, [selectedTenant, userFilter]);

  const cov = summary?.mfa_coverage_percentage ?? 0;
  const aCov = summary?.admin_mfa_coverage_percentage ?? 0;

  return (
    <div className="space-y-6">
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">MFA Enrollment Report</h1>
          <p className="mt-1 text-gray-500 dark:text-gray-400">Track MFA enrollment, compliance, and authentication method strength</p>
        </div>
        <div className="flex items-center gap-2">
          <select value={selectedTenant} onChange={e => setSelectedTenant(e.target.value)}
            className="px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white">
            {tenants.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
          </select>
          <button onClick={fetchData} disabled={isLoading}
            className="flex items-center gap-2 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors disabled:opacity-50">
            <RefreshCw className={clsx('w-4 h-4', isLoading && 'animate-spin')} /> Refresh
          </button>
        </div>
      </div>

      {error && <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 text-red-700 dark:text-red-400">{error}</div>}

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-gray-800 rounded-xl p-5 border border-gray-200 dark:border-gray-700 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-blue-100 dark:bg-blue-900/30 rounded-lg"><Users className="w-5 h-5 text-blue-600 dark:text-blue-400" /></div>
            <div><p className="text-sm text-gray-500 dark:text-gray-400">MFA Coverage</p><p className="text-2xl font-bold text-gray-900 dark:text-white">{cov.toFixed(1)}%</p></div>
          </div>
          <div className="mt-3 w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
            <div className={clsx('h-2 rounded-full', cov >= 95 ? 'bg-emerald-500' : cov >= 70 ? 'bg-amber-500' : 'bg-red-500')} style={{ width: `${Math.min(cov,100)}%` }} />
          </div>
          <p className="mt-1.5 text-xs text-gray-500 dark:text-gray-400">{summary?.mfa_registered_users ?? 0} / {summary?.total_users ?? 0} enrolled</p>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-xl p-5 border border-gray-200 dark:border-gray-700 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-violet-100 dark:bg-violet-900/30 rounded-lg"><UserCheck className="w-5 h-5 text-violet-600 dark:text-violet-400" /></div>
            <div><p className="text-sm text-gray-500 dark:text-gray-400">Admin MFA</p><p className="text-2xl font-bold text-gray-900 dark:text-white">{aCov.toFixed(1)}%</p></div>
          </div>
          <div className="mt-3 w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
            <div className={clsx('h-2 rounded-full', aCov >= 100 ? 'bg-emerald-500' : 'bg-red-500')} style={{ width: `${Math.min(aCov,100)}%` }} />
          </div>
          <p className="mt-1.5 text-xs text-gray-500 dark:text-gray-400">{summary?.admins_with_mfa ?? 0} / {summary?.total_admins ?? 0} admins</p>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-xl p-5 border border-gray-200 dark:border-gray-700 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-red-100 dark:bg-red-900/30 rounded-lg"><ShieldAlert className="w-5 h-5 text-red-600 dark:text-red-400" /></div>
            <div><p className="text-sm text-gray-500 dark:text-gray-400">Non-Compliant</p><p className="text-2xl font-bold text-gray-900 dark:text-white">{summary?.non_compliant_users ?? 0}</p></div>
          </div>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-xl p-5 border border-gray-200 dark:border-gray-700 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-emerald-100 dark:bg-emerald-900/30 rounded-lg"><KeyRound className="w-5 h-5 text-emerald-600 dark:text-emerald-400" /></div>
            <div><p className="text-sm text-gray-500 dark:text-gray-400">Strong MFA</p><p className="text-2xl font-bold text-gray-900 dark:text-white">{summary?.strong_mfa_users ?? 0}</p></div>
          </div>
          <p className="mt-3 text-xs text-gray-500 dark:text-gray-400">{summary?.moderate_mfa_users ?? 0} moderate · {summary?.weak_mfa_users ?? 0} weak</p>
        </div>
      </div>

      {/* Admins Without MFA */}
      {adminsWithoutMFA.length > 0 && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-5">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-6 h-6 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="text-lg font-semibold text-red-800 dark:text-red-300">Critical: {adminsWithoutMFA.length} Admin(s) Without MFA</h3>
              <div className="mt-3 space-y-2">
                {adminsWithoutMFA.map(a => (
                  <div key={a.id} className="flex items-center gap-3 bg-white dark:bg-gray-800 rounded-lg px-4 py-2.5 border border-red-200 dark:border-red-800">
                    <XCircle className="w-4 h-4 text-red-500 flex-shrink-0" />
                    <div>
                      <p className="text-sm font-medium text-gray-900 dark:text-white">{a.display_name}</p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">{a.user_principal_name} · {a.admin_roles.join(', ')}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Users Table */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Users ({totalUsers})</h2>
          <div className="flex bg-gray-100 dark:bg-gray-700 rounded-lg p-1 flex-wrap">
            {[{ key: '', label: 'All' }, { key: 'needs_attention', label: 'Needs Attention' }, { key: 'admin', label: 'Admins' }, { key: 'no_mfa', label: 'No MFA' }].map(f => (
              <button key={f.key} onClick={() => setUserFilter(f.key)}
                className={clsx('px-3 py-1.5 text-xs font-medium rounded-md transition-colors',
                  userFilter === f.key ? 'bg-white dark:bg-gray-600 text-gray-900 dark:text-white shadow-sm' : 'text-gray-600 dark:text-gray-400')}>
                {f.label}
              </button>
            ))}
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="bg-gray-50 dark:bg-gray-900/50">
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">User</th>
                <th className="text-center px-6 py-3 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">MFA</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Strength</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Methods</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Compliance</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Role</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {isLoading ? (
                <tr><td colSpan={6} className="px-6 py-12 text-center text-gray-500"><RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2" />Loading...</td></tr>
              ) : users.length === 0 ? (
                <tr><td colSpan={6} className="px-6 py-12 text-center text-gray-500">No users found</td></tr>
              ) : users.map(u => (
                <tr key={u.id} className={clsx('hover:bg-gray-50 dark:hover:bg-gray-700/50', u.needs_attention && 'bg-red-50/50 dark:bg-red-900/10')}>
                  <td className="px-6 py-4"><p className="text-sm font-medium text-gray-900 dark:text-white">{u.display_name}</p><p className="text-xs text-gray-500">{u.user_principal_name}</p></td>
                  <td className="px-6 py-4 text-center">{u.is_mfa_registered ? <CheckCircle2 className="w-5 h-5 text-emerald-500 mx-auto" /> : <XCircle className="w-5 h-5 text-red-500 mx-auto" />}</td>
                  <td className="px-6 py-4"><span className={clsx('px-2.5 py-1 rounded-full text-xs font-medium', strengthColors[u.mfa_strength])}>{u.mfa_strength}</span></td>
                  <td className="px-6 py-4"><span className="text-sm text-gray-600 dark:text-gray-300">{u.mfa_methods.length > 0 ? u.mfa_methods.join(', ') : '—'}</span></td>
                  <td className="px-6 py-4"><span className={clsx('px-2.5 py-1 rounded-full text-xs font-medium', complianceColors[u.compliance_status])}>{u.compliance_status.replace('_',' ')}</span></td>
                  <td className="px-6 py-4">{u.is_admin ? <span className="px-2 py-0.5 bg-violet-100 dark:bg-violet-900/30 text-violet-700 dark:text-violet-400 text-xs rounded font-medium">Admin</span> : <span className="text-xs text-gray-400">{u.user_type}</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
