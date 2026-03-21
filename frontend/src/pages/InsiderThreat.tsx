import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { ShieldAlert, AlertTriangle, Search, Download, User, Calendar, ExternalLink, Shield } from 'lucide-react';
import PageHeader from '@/components/PageHeader';
import StatsCard from '@/components/StatsCard';
import apiService from '@/services/api';

export default function InsiderThreat() {
  const [selectedTenant, setSelectedTenant] = React.useState<string>('all');
  
  const { data: tenantsRes } = useQuery({
    queryKey: ['tenants'],
    queryFn: () => apiService.getTenants()
  });

  const tenants = tenantsRes?.items || [];
  
  const fetchDlpStats = async () => {
    return apiService.getDlpStats(30, selectedTenant);
  };
  
  const fetchDlpEvents = async () => {
    const res = await apiService.getDlpEvents(50, selectedTenant);
    return res.items || [];
  };

  const { data: stats } = useQuery({
    queryKey: ['dlp-stats', selectedTenant],
    queryFn: fetchDlpStats
  });
  
  const { data: events, isLoading: isEventsLoading } = useQuery({
    queryKey: ['dlp-events', selectedTenant],
    queryFn: fetchDlpEvents
  });

  const totalViolations = stats?.stats?.reduce((acc: number, curr: any) => acc + curr.count, 0) || 0;

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <PageHeader 
          title="Insider Threat & DLP" 
          description="Monitor Data Loss Prevention and potentially malicious internal data handling."
        />
        <div className="flex items-center gap-3 bg-white dark:bg-gray-800 p-2 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm">
          <label className="text-xs font-bold text-gray-500 dark:text-gray-400 px-2 uppercase tracking-wider">
            Tenant Context
          </label>
          <select 
            value={selectedTenant}
            onChange={(e) => setSelectedTenant(e.target.value)}
            className="text-sm p-1.5 border-0 bg-transparent focus:ring-0 text-gray-900 dark:text-white font-medium min-w-[180px]"
          >
            <option value="all">All Visible Tenants</option>
            {tenants.map((t: any) => (
              <option key={t.id} value={t.id}>{t.name}</option>
            ))}
          </select>
        </div>
      </div>
      
      {/* Stats Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatsCard
          title="DLP Violations"
          value={totalViolations}
          icon={ShieldAlert}
          color="red"
          loading={!stats}
        />
        <StatsCard
          title="Active Policies"
          value={stats?.stats?.length || 0}
          icon={Shield}
          color="blue"
          loading={!stats}
        />
        <StatsCard
          title="At-Risk Users"
          value={stats?.top_users?.length || 0}
          icon={User}
          color="amber"
          loading={!stats}
        />
        <StatsCard
          title="Security Score"
          value={totalViolations > 50 ? "Poor" : totalViolations > 10 ? "Fair" : "Good"}
          icon={ShieldAlert}
          color={totalViolations > 50 ? "red" : totalViolations > 10 ? "amber" : "green"}
          loading={!stats}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Policy Distribution */}
        <div className="lg:col-span-1 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 shadow-sm">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-6 flex items-center gap-2">
            <Download className="w-5 h-5 text-blue-500" />
            Top Policy Impacts
          </h3>
          <div className="space-y-6">
            {!stats?.stats || stats.stats.length === 0 ? (
              <div className="py-10 text-center text-gray-400 text-sm italic">No data available</div>
            ) : (
              stats.stats.map((s: any, idx: number) => (
                <div key={idx} className="space-y-2">
                  <div className="flex justify-between items-center text-sm">
                    <span className="font-medium text-gray-700 dark:text-gray-300 truncate max-w-[200px]" title={s.action}>
                      {s.action}
                    </span>
                    <span className="font-bold text-gray-900 dark:text-white">{s.count}</span>
                  </div>
                  <div className="w-full h-2 bg-gray-100 dark:bg-gray-700 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-blue-500 rounded-full" 
                      style={{ width: `${Math.min(100, (s.count / totalViolations) * 100)}%` }}
                    />
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Top Risky Users */}
        <div className="lg:col-span-1 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 shadow-sm">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-6 flex items-center gap-2">
            <Search className="w-5 h-5 text-purple-500" />
            Highest Risk Accounts
          </h3>
          <div className="space-y-4">
            {!stats?.top_users || stats.top_users.length === 0 ? (
              <div className="py-10 text-center text-gray-400 text-sm italic">No users flagged</div>
            ) : (
              stats.top_users.map((u: any, idx: number) => (
                <div key={idx} className="flex items-center justify-between p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-red-50 dark:bg-red-900/20 rounded-xl flex items-center justify-center text-red-600 dark:text-red-400 font-bold">
                       {u.user_id.substring(0, 1).toUpperCase()}
                    </div>
                    <div>
                      <p className="text-sm font-bold text-gray-900 dark:text-white truncate max-w-[140px]" title={u.user_id}>
                        {u.user_id}
                      </p>
                      <p className="text-[10px] text-gray-500 uppercase tracking-wider font-semibold">Multiple Violations</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <span className="text-xs font-black text-red-600 dark:text-red-400 bg-red-100 dark:bg-red-900/40 px-2 py-1 rounded-md">
                      {u.count} HITS
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
        
        {/* DLP Info Card */}
        <div className="lg:col-span-1 space-y-4">
          <div className="bg-indigo-600 rounded-xl p-6 text-white shadow-lg shadow-indigo-200 dark:shadow-none relative overflow-hidden group">
            <div className="absolute -right-4 -bottom-4 opacity-10 group-hover:scale-110 transition-transform duration-500">
              <ShieldAlert className="w-32 h-32" />
            </div>
            <div className="relative z-10">
              <h4 className="text-lg font-bold">DLP Intelligence</h4>
              <p className="text-indigo-100 text-sm mt-2 leading-relaxed">
                We are actively monitoring Office 365 DLP policy matches across Exchange, SharePoint, and Teams content types.
              </p>
              <button className="mt-4 px-4 py-2 bg-white text-indigo-600 rounded-lg text-sm font-bold flex items-center gap-2 hover:bg-indigo-50 transition-colors shadow-sm">
                View Policy Guide
                <ExternalLink className="w-4 h-4" />
              </button>
            </div>
          </div>
          
          <div className="bg-amber-50 dark:bg-amber-900/10 border border-amber-200 dark:border-amber-900/30 rounded-xl p-6">
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 bg-amber-100 dark:bg-amber-900/40 rounded-full flex items-center justify-center flex-shrink-0 text-amber-600">
                <AlertTriangle className="w-5 h-5" />
              </div>
              <div>
                <h5 className="text-sm font-bold text-amber-900 dark:text-amber-300">Insider Threat Signal</h5>
                <p className="text-xs text-amber-800/80 dark:text-amber-400/80 mt-1 leading-relaxed">
                  Sudden spikes in "Blocked" actions are highly correlated with attempted mass exfiltration by disenfranchised employees.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Events Table Section */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm overflow-hidden">
        <div className="p-6 border-b border-gray-100 dark:border-gray-700 flex justify-between items-center">
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Policy Event Feed</h3>
            <p className="text-xs text-gray-500 mt-1">Detailed log of recent DLP triggers and resulting security actions.</p>
          </div>
          <button className="text-sm font-bold text-blue-600 hover:text-blue-700 flex items-center gap-2">
            <Download className="w-4 h-4" />
            Export CSV
          </button>
        </div>
        
        <div className="overflow-x-auto">
          {isEventsLoading ? (
            <div className="py-20 text-center">
               <div className="animate-spin w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full mx-auto mb-4"></div>
               <p className="text-sm text-gray-500 font-medium tracking-tight">Gathering security logs...</p>
            </div>
          ) : events?.length > 0 ? (
            <table className="w-full text-left">
              <thead>
                <tr className="bg-gray-50 dark:bg-gray-900/50 text-[10px] font-black text-gray-500 uppercase tracking-widest border-b border-gray-100 dark:border-gray-700">
                  <th className="px-6 py-4">Timestamp</th>
                  <th className="px-6 py-4">Identity</th>
                  <th className="px-6 py-4">Security Policy</th>
                  <th className="px-6 py-4">Resource Context</th>
                  <th className="px-6 py-4">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                {events.map((e: any) => (
                  <tr key={e.id} className="hover:bg-gray-50/80 dark:hover:bg-gray-700/20 transition-colors group">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
                        <Calendar className="w-3.5 h-3.5" />
                        {new Date(e.created_at).toLocaleString()}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="font-bold text-sm text-gray-900 dark:text-white group-hover:text-blue-600 transition-colors">
                        {e.user_id}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-400 rounded-md text-[10px] font-black uppercase tracking-tight">
                        <ShieldAlert className="w-3 h-3" />
                        {e.policy_name || 'DLP RULE MATCH'}
                      </div>
                    </td>
                    <td className="px-6 py-4 max-w-xs">
                      <div className="text-xs text-gray-600 dark:text-gray-400 truncate font-mono" title={e.file_name}>
                        {e.file_name || 'Multi-Resource Pattern'}
                      </div>
                      <div className="text-[10px] text-gray-400 mt-0.5 truncate italic">
                        {e.sensitive_info_types || 'PII/Financial Detection'}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`px-2.5 py-1 rounded-md text-[10px] font-black uppercase tracking-tighter ${
                        e.action_taken === 'Blocked' 
                          ? 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-400' 
                          : 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-400'
                      }`}>
                        {e.action_taken || 'Detect Only'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="py-20 text-center">
               <ShieldAlert className="w-12 h-12 text-gray-200 dark:text-gray-700 mx-auto mb-4" />
               <p className="text-sm text-gray-400 font-medium">No DLP violations have been detected in the current range.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
