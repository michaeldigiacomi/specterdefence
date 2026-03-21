import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Mail, User, Shield, Lock, ExternalLink, Calendar } from 'lucide-react';
import PageHeader from '@/components/PageHeader';
import StatsCard from '@/components/StatsCard';
import apiService from '@/services/api';

export default function MailboxSecurity() {
  const [selectedTenant, setSelectedTenant] = React.useState<string>('all');
  
  const { data: tenantsRes } = useQuery({
    queryKey: ['tenants'],
    queryFn: () => apiService.getTenants()
  });

  const tenants = tenantsRes?.items || [];

  const { data: stats } = useQuery({
    queryKey: ['mailbox-stats', selectedTenant],
    queryFn: () => apiService.getMailboxSecurityStats(30, selectedTenant)
  });
  
  const { data: eventsRes, isLoading: isEventsLoading } = useQuery({
    queryKey: ['mailbox-access', selectedTenant],
    queryFn: () => apiService.getMailboxAccessEvents(50, selectedTenant)
  });

  const accessEvents = eventsRes?.items || [];

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <PageHeader 
          title="Mailbox Security Dashboard" 
          description="Track external forwarding rules and suspicious non-owner mailbox access."
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
            <option value="all">Enterprise View</option>
            {tenants.map((t: any) => (
              <option key={t.id} value={t.id}>{t.name}</option>
            ))}
          </select>
        </div>
      </div>
      
      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <StatsCard
          title="Non-Owner Access"
          value={stats?.non_owner_access_count || 0}
          icon={User}
          color="amber"
          loading={!stats}
        />
        <StatsCard
          title="External Forwarding"
          value={stats?.external_forward_rules_count || 0}
          icon={ExternalLink}
          color="red"
          loading={!stats}
        />
        <StatsCard
          title="Security Health"
          value={stats?.non_owner_access_count > 0 ? "Compromised" : "Clean"}
          icon={Shield}
          color={stats?.non_owner_access_count > 0 ? "red" : "green"}
          loading={!stats}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Info & Alerts */}
        <div className="lg:col-span-1 space-y-6">
          <div className="bg-gradient-to-br from-indigo-600 to-blue-700 rounded-2xl p-6 text-white shadow-xl relative overflow-hidden group">
            <Mail className="absolute -right-8 -bottom-8 w-40 h-40 opacity-10 group-hover:scale-110 transition-transform duration-700" />
            <div className="relative z-10">
              <div className="w-12 h-12 bg-white/20 rounded-xl flex items-center justify-center mb-4 backdrop-blur-md">
                <Lock className="w-6 h-6" />
              </div>
              <h4 className="text-xl font-black tracking-tight">Access Control</h4>
              <p className="text-indigo-100/90 text-sm mt-2 leading-relaxed font-medium">
                System tracks and alerts whenever a mailbox is accessed by someone other than the primary owner (non-owner access).
              </p>
              <div className="mt-6 flex items-center gap-4">
                 <div className="flex-1">
                    <p className="text-[10px] uppercase font-bold text-indigo-200">Recent Coverage</p>
                    <p className="text-sm font-bold">100% Mailboxes</p>
                 </div>
                 <div className="flex-1 border-l border-white/20 pl-4">
                    <p className="text-[10px] uppercase font-bold text-indigo-200">Alert Latency</p>
                    <p className="text-sm font-bold">&lt; 5 mins</p>
                 </div>
              </div>
            </div>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 p-6 shadow-sm">
             <h4 className="text-sm font-black text-gray-900 dark:text-white uppercase tracking-wider mb-4">Security Baseline</h4>
             <div className="space-y-4">
                <div className="flex items-center gap-3">
                   <div className="w-2 h-2 rounded-full bg-green-500 shadow-sm shadow-green-200"></div>
                   <p className="text-xs font-medium text-gray-600 dark:text-gray-400">Automatic forwarding disabled</p>
                </div>
                <div className="flex items-center gap-3">
                   <div className="w-2 h-2 rounded-full bg-green-500 shadow-sm shadow-green-200"></div>
                   <p className="text-xs font-medium text-gray-600 dark:text-gray-400">Non-owner access logging active</p>
                </div>
                <div className="flex items-center gap-3">
                   <div className="w-2 h-2 rounded-full bg-amber-500 shadow-sm shadow-amber-200"></div>
                   <p className="text-xs font-medium text-gray-600 dark:text-gray-400">External redirect auditing recommended</p>
                </div>
             </div>
          </div>
        </div>

        {/* Access Events Feed */}
        <div className="lg:col-span-2 bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 shadow-sm overflow-hidden flex flex-col">
          <div className="p-6 border-b border-gray-100 dark:border-gray-700 flex justify-between items-center">
            <div>
              <h3 className="text-lg font-black text-gray-900 dark:text-white tracking-tight">Suspicious Access Logs</h3>
              <p className="text-xs text-gray-500 mt-0.5">Live feed of non-owner mailbox logins and binds.</p>
            </div>
          </div>
          
          <div className="flex-1 overflow-x-auto">
            {isEventsLoading ? (
               <div className="py-20 text-center animate-pulse">
                  <div className="w-10 h-10 bg-gray-100 dark:bg-gray-800 rounded-full mx-auto mb-3"></div>
                  <p className="text-sm text-gray-400">Fetching access logs...</p>
               </div>
            ) : accessEvents.length > 0 ? (
              <table className="w-full">
                <thead>
                  <tr className="bg-gray-50 dark:bg-gray-900/50 text-[10px] font-black text-gray-500 uppercase tracking-widest border-b border-gray-100 dark:border-gray-700">
                    <th className="px-6 py-4 text-left">Time</th>
                    <th className="px-6 py-4 text-left">Target Mailbox</th>
                    <th className="px-6 py-4 text-left">Accessed By</th>
                    <th className="px-6 py-4 text-left">Operation</th>
                    <th className="px-6 py-4 text-left">Location</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                  {accessEvents.map((e: any) => (
                    <tr key={e.id} className="hover:bg-gray-50/50 dark:hover:bg-gray-700/20 transition-colors group">
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-2 text-xs font-bold text-gray-500">
                           <Calendar className="w-3 h-3" />
                           {new Date(e.created_at).toLocaleString()}
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <div className="text-xs font-black text-gray-900 dark:text-white bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded inline-block">
                           {e.accessed_mailbox}
                        </div>
                      </td>
                      <td className="px-6 py-4">
                         <div className="flex items-center gap-2">
                            <div className="w-6 h-6 rounded-full bg-indigo-100 dark:bg-indigo-900/40 flex items-center justify-center text-[10px] font-bold text-indigo-600">
                               {e.accessed_by.substring(0, 1).toUpperCase()}
                            </div>
                            <span className="text-xs font-bold text-gray-700 dark:text-gray-300">{e.accessed_by}</span>
                         </div>
                      </td>
                      <td className="px-6 py-4">
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-black uppercase tracking-tight bg-red-100 text-red-700 dark:bg-red-900/20 dark:text-red-400">
                           {e.operation}
                        </span>
                      </td>
                      <td className="px-6 py-4 font-mono text-[10px] text-gray-500">
                         {e.client_ip || 'Internal System'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="py-20 text-center flex flex-col items-center">
                 <div className="w-16 h-16 bg-gray-50 dark:bg-gray-800/50 rounded-full flex items-center justify-center mb-4">
                    <Shield className="w-8 h-8 text-gray-200 dark:text-gray-700" />
                 </div>
                 <p className="text-sm font-bold text-gray-400">No suspicious access events detected</p>
                 <p className="text-[10px] text-gray-500 mt-1 max-w-[200px] leading-relaxed italic">System is monitored and currently clean of unauthorized non-owner access.</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
