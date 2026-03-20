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
  Globe
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
    <div className="space-y-6">
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
        <div className="lg:col-span-2 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
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
                  <th className="px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Resource</th>
                  <th className="px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Type</th>
                  <th className="px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Sharer</th>
                  <th className="px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Created</th>
                  <th className="px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Link</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {isLinksLoading ? (
                  <tr>
                    <td colSpan={5} className="px-6 py-10 text-center text-gray-500">Loading links...</td>
                  </tr>
                ) : !links || links.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-6 py-10 text-center text-gray-500">No active sharing links found</td>
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
                      <td className="px-6 py-4">
                        <span className={clsx(
                          "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium",
                          link.sharing_type === 'Anonymous' 
                            ? "bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400"
                            : "bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400"
                        )}>
                          {link.sharing_type === 'Anonymous' ? <Unlock className="w-3 h-3 mr-1" /> : <Lock className="w-3 h-3 mr-1" />}
                          {link.sharing_type}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-2">
                          <div className="w-6 h-6 bg-gray-100 dark:bg-gray-700 rounded-full flex items-center justify-center">
                            <User className="w-3 h-3 text-gray-600 dark:text-gray-400" />
                          </div>
                          <span className="text-sm text-gray-600 dark:text-gray-400 truncate max-w-[120px]">
                            {link.user_email?.split('@')[0]}
                          </span>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400">
                          <Clock className="w-3 h-3" />
                          {formatDate(link.event_time)}
                        </div>
                      </td>
                      <td className="px-6 py-4">
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
                          <span className="text-xs text-gray-400 italic">No URL</span>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Sidebar: Top Sharers and Risks */}
        <div className="space-y-6">
          {/* Top SharersCard */}
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
              <User className="w-5 h-5 text-indigo-500" />
              Top Sharers
            </h3>
            <div className="space-y-4">
              {isMetricsLoading ? (
                <p className="text-sm text-gray-500">Loading sharers...</p>
              ) : Object.entries(metrics?.top_sharers ?? {}).length === 0 ? (
                <p className="text-sm text-gray-500">No sharing activity detected</p>
              ) : (
                Object.entries(metrics?.top_sharers ?? {})
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
          <div className="bg-amber-50 dark:bg-amber-900/20 rounded-xl border border-amber-200 dark:border-amber-800/50 p-6">
            <div className="flex items-start gap-3">
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
