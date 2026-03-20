import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { 
  Share2, 
  ExternalLink, 
  Lock, 
  Unlock, 
  FileText, 
  User, 
  AlertCircle,
  Clock,
  Globe,
  Layout,
  History
} from 'lucide-react';
import PageHeader from '@/components/PageHeader';
import StatsCard from '@/components/StatsCard';
import { useAppStore } from '@/store/appStore';
import { apiService } from '@/services/api';
import { clsx } from 'clsx';

interface SharePointMetrics {
  active_links_count: number;
  by_type: Record<string, number>;
  top_sharers: Record<string, number>;
  by_site: Record<string, number>;
  recent_activity: {
    file_name: string;
    operation: string;
    user: string;
    time: string;
  }[];
}

interface SharingLink {
  id: string;
  event_time: string;
  operation: string;
  file_name: string;
  file_path: string;
  site_url: string;
  user_email: string;
  sharing_type: string;
  share_link_url?: string;
  target_user?: string;
  is_active: boolean;
}

const SharePoint: React.FC = () => {
  const { selectedTenant } = useAppStore();

  const { data: metrics, isLoading: isMetricsLoading } = useQuery<SharePointMetrics>({
    queryKey: ['sharepoint-metrics', selectedTenant],
    queryFn: () => apiService.getSharePointMetrics(selectedTenant || undefined),
  });

  const { data: links, isLoading: isLinksLoading } = useQuery<SharingLink[]>({
    queryKey: ['sharepoint-links', selectedTenant],
    queryFn: () => apiService.getSharePointLinks(selectedTenant || undefined),
  });

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString();
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <PageHeader 
        title="SharePoint Analytics" 
        subtitle="Monitor external sharing and public links across SharePoint and OneDrive"
      />

      {/* Stats Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatsCard
          title="Active Public Links"
          value={metrics?.active_links_count ?? 0}
          icon={Globe}
          status="warning"
          isLoading={isMetricsLoading}
        />
        <StatsCard
          title="Anonymous Shares"
          value={metrics?.by_type?.Anonymous ?? 0}
          icon={Unlock}
          status="danger"
          isLoading={isMetricsLoading}
        />
        <StatsCard
          title="Secure Shares"
          value={metrics?.by_type?.Secure ?? 0}
          icon={Lock}
          status="success"
          isLoading={isMetricsLoading}
        />
        <StatsCard
          title="Unique Sharers"
          value={Object.keys(metrics?.top_sharers ?? {}).length}
          icon={User}
          status="info"
          isLoading={isMetricsLoading}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Active Sharing Links Table */}
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden shadow-sm">
            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                <Share2 className="w-5 h-5 text-primary-500" />
                Active Sharing Links
              </h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-gray-50 dark:bg-gray-900/50">
                    <th className="px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider text-center">Resource</th>
                    <th className="px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider text-center">Type</th>
                    <th className="px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider text-center">Sharer</th>
                    <th className="px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider text-center">Created</th>
                    <th className="px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider text-center">Link</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                  {isLinksLoading ? (
                    <tr>
                      <td colSpan={5} className="px-6 py-10 text-center text-gray-500">Loading links...</td>
                    </tr>
                  ) : !links || links.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="px-6 py-14 text-center">
                        <div className="flex flex-col items-center gap-3">
                          <div className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-full text-gray-300 dark:text-gray-600">
                            <Share2 className="w-10 h-10" />
                          </div>
                          <p className="text-gray-500 dark:text-gray-400 font-medium text-sm">No active sharing links found</p>
                          <p className="text-gray-400 dark:text-gray-500 text-xs max-w-xs text-center">
                            New sharing events will appear here once the next collection cycle completes.
                          </p>
                        </div>
                      </td>
                    </tr>
                  ) : (
                    links.map((link) => (
                      <tr key={link.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-3">
                            <div className="p-2 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                              <FileText className="w-4 h-4 text-blue-600 dark:text-blue-400" />
                            </div>
                            <div className="max-w-[200px]">
                              <p className="text-sm font-medium text-gray-900 dark:text-white truncate" title={link.file_name}>
                                {link.file_name || 'Unknown File'}
                              </p>
                              <p className="text-xs text-gray-500 dark:text-gray-400 truncate" title={link.file_path}>
                                {link.file_path}
                              </p>
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-4 border-l dark:border-gray-700/50">
                          <div className="flex justify-center">
                            <span className={clsx(
                              "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium whitespace-nowrap",
                              link.sharing_type === 'Anonymous' 
                                ? "bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400"
                                : "bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400"
                            )}>
                              {link.sharing_type === 'Anonymous' ? <Unlock className="w-3 h-3 mr-1" /> : <Lock className="w-3 h-3 mr-1" />}
                              {link.sharing_type}
                            </span>
                          </div>
                        </td>
                        <td className="px-6 py-4 border-l dark:border-gray-700/50">
                          <div className="flex items-center gap-2 justify-center">
                            <div className="w-6 h-6 bg-gray-100 dark:bg-gray-700 rounded-full flex items-center justify-center">
                              <User className="w-3 h-3 text-gray-600 dark:text-gray-400" />
                            </div>
                            <span className="text-sm text-gray-600 dark:text-gray-400 truncate max-w-[120px]">
                              {link.user_email?.split('@')[0]}
                            </span>
                          </div>
                        </td>
                        <td className="px-6 py-4 border-l dark:border-gray-700/50">
                          <div className="flex items-center gap-1.5 text-[10px] text-gray-500 dark:text-gray-400 justify-center">
                            <Clock className="w-3 h-3" />
                            {formatDate(link.event_time)}
                          </div>
                        </td>
                        <td className="px-6 py-4 border-l dark:border-gray-700/50">
                          <div className="flex justify-center">
                            {link.share_link_url ? (
                              <a 
                                href={link.share_link_url} 
                                target="_blank" 
                                rel="noopener noreferrer"
                                className="p-1.5 text-primary-600 hover:bg-primary-50 dark:hover:bg-primary-900/20 rounded-md transition-colors block"
                                title="Open sharing link"
                              >
                                <ExternalLink className="w-4 h-4" />
                              </a>
                            ) : (
                              <span className="text-[10px] text-gray-400 italic">No URL</span>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Recent Activity Feed */}
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 shadow-sm">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-6 flex items-center gap-2">
              <History className="w-5 h-5 text-green-500" />
              Recent Operations
            </h3>
            <div className="space-y-6">
              {!metrics?.recent_activity || metrics.recent_activity.length === 0 ? (
                <p className="text-sm text-gray-500 py-4 text-center">No recent SharePoint activity recorded</p>
              ) : (
                metrics.recent_activity.map((activity, idx) => (
                  <div key={idx} className="relative pl-8 pb-6 last:pb-0 border-l border-gray-100 dark:border-gray-700 ml-3">
                    <div className="absolute left-[-13px] top-0 w-6 h-6 rounded-full bg-white dark:bg-gray-800 border-2 border-primary-500 flex items-center justify-center">
                      <div className="w-2 h-2 rounded-full bg-primary-500" />
                    </div>
                    <div>
                      <div className="flex justify-between items-start mb-1">
                        <p className="text-sm font-bold text-gray-900 dark:text-white">
                          {activity.operation.replace(/([A-Z])/g, ' $1').trim()}
                        </p>
                        <span className="text-[10px] text-gray-400 font-medium">
                          {formatDate(activity.time)}
                        </span>
                      </div>
                      <p className="text-xs text-gray-600 dark:text-gray-400 leading-relaxed">
                        <span className="font-semibold text-gray-700 dark:text-gray-300">{activity.user?.split('@')[0]}</span>
                        {' performed a '}
                        <span className="italic">{activity.operation}</span>
                        {' on '}
                        <span className="font-medium text-primary-600 dark:text-primary-400 break-all">{activity.file_name || 'a file'}</span>
                      </p>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Sidebar: Top Sharers and Risks */}
        <div className="space-y-6">
          {/* Breakdown by Site */}
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 shadow-sm">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
              <Layout className="w-5 h-5 text-blue-500" />
              Activity by Site
            </h3>
            <div className="space-y-4">
              {isMetricsLoading ? (
                <p className="text-sm text-gray-500">Loading sites...</p>
              ) : !metrics?.by_site || Object.keys(metrics.by_site).length === 0 ? (
                <p className="text-sm text-gray-500">No site data available</p>
              ) : (
                Object.entries(metrics.by_site)
                  .sort(([, a], [, b]) => b - a)
                  .map(([site, count]) => (
                    <div key={site} className="space-y-2">
                      <div className="flex justify-between items-center text-xs">
                        <p className="font-medium text-gray-600 dark:text-gray-400 truncate max-w-[160px]" title={site}>
                          {site.split('/').pop() || site}
                        </p>
                        <span className="font-bold text-gray-900 dark:text-white">{count}</span>
                      </div>
                      <div className="w-full h-1.5 bg-gray-100 dark:bg-gray-700 rounded-full overflow-hidden">
                        <div 
                          className="h-full bg-blue-500" 
                          style={{ width: `${Math.min(100, (count / metrics.active_links_count) * 100)}%` }}
                        />
                      </div>
                    </div>
                  ))
              )}
            </div>
          </div>

          {/* Top SharersCard */}
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 shadow-sm">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
              <User className="w-5 h-5 text-indigo-500" />
              Top Sharers
            </h3>
            <div className="space-y-4">
              {isMetricsLoading ? (
                <p className="text-sm text-gray-500">Loading sharers...</p>
              ) : !metrics?.top_sharers || Object.keys(metrics.top_sharers).length === 0 ? (
                <p className="text-sm text-gray-500">No sharing activity detected</p>
              ) : (
                Object.entries(metrics.top_sharers)
                  .sort(([, a], [, b]) => b - a)
                  .map(([email, count]) => (
                    <div key={email} className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 bg-indigo-50 dark:bg-indigo-900/20 rounded-lg flex items-center justify-center text-indigo-600 dark:text-indigo-400 font-bold text-xs">
                          {email.substring(0, 2).toUpperCase()}
                        </div>
                        <div className="max-w-[140px]">
                          <p className="text-sm font-medium text-gray-900 dark:text-white truncate" title={email}>
                            {email}
                          </p>
                        </div>
                      </div>
                      <span className="text-sm font-bold text-gray-900 dark:text-white bg-gray-100 dark:bg-gray-700 px-2 py-0.5 rounded-md">
                        {count}
                      </span>
                    </div>
                  ))
              )}
            </div>
          </div>

          {/* Security Tip */}
          <div className="bg-amber-50 dark:bg-amber-900/20 rounded-xl border border-amber-200 dark:border-amber-800/50 p-6 relative overflow-hidden">
            <div className="absolute top-0 right-0 p-4 opacity-10">
              <AlertCircle className="w-20 h-20 text-amber-500" />
            </div>
            <div className="flex items-start gap-3 relative z-10">
              <AlertCircle className="w-5 h-5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
              <div>
                <h4 className="text-sm font-bold text-amber-900 dark:text-amber-300">Security Recommendation</h4>
                <p className="text-xs text-amber-800 dark:text-amber-400 mt-1 leading-relaxed">
                  Anonymous links should have an expiration date. Regularly review files with "Anonymous" sharing type as anyone with the link can access them without authentication.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SharePoint;
