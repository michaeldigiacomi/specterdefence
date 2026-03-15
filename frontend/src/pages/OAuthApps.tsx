import { useState, useEffect, ChangeEvent } from 'react';
import {
  AppWindow,
  ShieldAlert,
  AlertTriangle,
  RefreshCw,
  Mail,
  Users,
  FileText,
  Calendar,
  LayoutGrid,
  List,
  ShieldCheck,
  Search,
  ExternalLink,
  ChevronRight,
  UserCheck,
  X,
  CheckCircle2,
  Ban,
} from 'lucide-react';
import { apiService } from '@/services/api';
import type { OAuthApp, OAuthAppAlert } from '@/types/securityTypes';
import { Dialog, Transition } from '@headlessui/react';
import { Fragment } from 'react';
import clsx from 'clsx';

const riskColors: Record<string, string> = {
  LOW: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
  MEDIUM: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400',
  HIGH: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400',
  CRITICAL: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
};

const riskBorderColors: Record<string, string> = {
  LOW: 'border-blue-200 dark:border-blue-800',
  MEDIUM: 'border-amber-200 dark:border-amber-800',
  HIGH: 'border-orange-200 dark:border-orange-800',
  CRITICAL: 'border-red-200 dark:border-red-800',
};

const statusColors: Record<string, string> = {
  approved: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400',
  suspicious: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400',
  malicious: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
  revoked: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-400',
  pending_review: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
};

const publisherColors: Record<string, string> = {
  microsoft:
    'bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-300 border-blue-100 dark:border-blue-800',
  verified:
    'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-300 border-emerald-100 dark:border-emerald-800',
  unverified:
    'bg-amber-50 text-amber-700 dark:bg-amber-900/20 dark:text-amber-300 border-amber-100 dark:border-amber-800',
  unknown:
    'bg-gray-50 text-gray-700 dark:bg-gray-900/20 dark:text-gray-300 border-gray-100 dark:border-gray-800',
};

export default function OAuthApps() {
  const [apps, setApps] = useState<OAuthApp[]>([]);
  const [alerts, setAlerts] = useState<OAuthAppAlert[]>([]);
  const [totalApps, setTotalApps] = useState(0);
  const [totalAlerts, setTotalAlerts] = useState(0);
  const [viewMode, setViewMode] = useState<'grid' | 'table'>('grid');
  const [searchQuery, setSearchQuery] = useState('');
  const [riskFilter, setRiskFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [audienceFilter, setAudienceFilter] = useState<'all' | 'internal' | 'external'>('all');
  const [excludeMicrosoft, setExcludeMicrosoft] = useState(true);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedApp, setSelectedApp] = useState<OAuthApp | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const fetchData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [appsRes, alertsRes] = await Promise.all([
        apiService.getOAuthApps({
          risk_level: riskFilter || undefined,
          status: statusFilter || undefined,
          is_internal: audienceFilter === 'all' ? undefined : audienceFilter === 'internal',
          exclude_microsoft: excludeMicrosoft,
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

  useEffect(() => {
    fetchData();
  }, [riskFilter, statusFilter, audienceFilter, excludeMicrosoft]);

  const filteredApps = apps.filter(
    app =>
      app.display_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (app.publisher_name || '').toLowerCase().includes(searchQuery.toLowerCase())
  );

  const highRiskCount = apps.filter(
    a => a.risk_level === 'HIGH' || a.risk_level === 'CRITICAL'
  ).length;
  const unverifiedCount = apps.filter(
    a => a.publisher_type === 'unverified' || a.publisher_type === 'unknown'
  ).length;
  const mailAccessCount = apps.filter(a => a.has_mail_permissions).length;

  const openAppDetails = (app: OAuthApp) => {
    setSelectedApp(app);
    setIsModalOpen(true);
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      {/* Page Header */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
        <div>
          <h1 className="text-3xl font-extrabold text-gray-900 dark:text-white tracking-tight">
            OAuth Risk Center
          </h1>
          <p className="mt-2 text-gray-500 dark:text-gray-400 max-w-2xl text-lg font-light">
            Assess and manage third-party integrations. Monitor unverified publishers and high-risk
            permission grants.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={fetchData}
            disabled={isLoading}
            className="flex items-center gap-2 px-5 py-2.5 bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 rounded-xl hover:bg-gray-200 dark:hover:bg-gray-700 transition-all font-medium disabled:opacity-50 border border-gray-200 dark:border-gray-700"
          >
            <RefreshCw className={clsx('w-4 h-4', isLoading && 'animate-spin')} /> Refresh Scan
          </button>
          <div className="p-1 bg-gray-100 dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 flex">
            <button
              onClick={() => setViewMode('grid')}
              className={clsx(
                'p-2 rounded-lg transition-all',
                viewMode === 'grid'
                  ? 'bg-white dark:bg-gray-700 shadow-sm text-primary-600 dark:text-primary-400'
                  : 'text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
              )}
            >
              <LayoutGrid className="w-5 h-5" />
            </button>
            <button
              onClick={() => setViewMode('table')}
              className={clsx(
                'p-2 rounded-lg transition-all',
                viewMode === 'table'
                  ? 'bg-white dark:bg-gray-700 shadow-sm text-primary-600 dark:text-primary-400'
                  : 'text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
              )}
            >
              <List className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-2xl p-4 text-red-700 dark:text-red-400 flex items-center gap-3">
          <Ban className="w-5 h-5 flex-shrink-0" />
          <span className="font-medium">{error}</span>
        </div>
      )}

      {/* Hero Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard title="Total Integrated Apps" value={totalApps} icon={AppWindow} color="blue" />
        <StatCard
          title="Critical/High Risk"
          value={highRiskCount}
          icon={ShieldAlert}
          color="red"
          trend={`${((highRiskCount / totalApps) * 100).toFixed(0)}% of total`}
        />
        <StatCard
          title="Unverified Apps"
          value={unverifiedCount}
          icon={AlertTriangle}
          color="amber"
        />
        <StatCard title="Mail Access Apps" value={mailAccessCount} icon={Mail} color="violet" />
      </div>

      {/* Main Content Area */}
      <div className="space-y-6">
        {/* Filters & Search */}
        <div className="flex flex-col md:flex-row gap-4">
          <div className="relative flex-1 group">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400 group-focus-within:text-primary-500 transition-colors" />
            <input
              type="text"
              placeholder="Search by app name or publisher..."
              value={searchQuery}
              onChange={(e: ChangeEvent<HTMLInputElement>) => setSearchQuery(e.target.value)}
              className="w-full pl-12 pr-4 py-3.5 bg-gray-50 dark:bg-gray-900 border-none rounded-2xl text-sm outline-none focus:ring-2 focus:ring-primary-500 transition-all font-medium"
            />
          </div>
          <div className="flex gap-2">
            <select
              value={riskFilter}
              onChange={(e: ChangeEvent<HTMLSelectElement>) => setRiskFilter(e.target.value)}
              className="px-4 py-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-2xl text-sm font-medium outline-none focus:ring-2 focus:ring-primary-500 shadow-sm"
            >
              <option value="">All Risk Levels</option>
              <option value="CRITICAL">Critical</option>
              <option value="HIGH">High</option>
              <option value="MEDIUM">Medium</option>
              <option value="LOW">Low</option>
            </select>
            <select
              value={statusFilter}
              onChange={(e: ChangeEvent<HTMLSelectElement>) => setStatusFilter(e.target.value)}
              className="px-4 py-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-2xl text-sm font-medium outline-none focus:ring-2 focus:ring-primary-500 shadow-sm"
            >
              <option value="">All Statuses</option>
              <option value="suspicious">Suspicious</option>
              <option value="malicious">Malicious</option>
              <option value="approved">Approved</option>
              <option value="pending_review">Pending Review</option>
              <option value="revoked">Revoked</option>
            </select>
            <select
              value={audienceFilter}
              onChange={(e: ChangeEvent<HTMLSelectElement>) =>
                setAudienceFilter(e.target.value as any)
              }
              className="px-4 py-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-2xl text-sm font-medium outline-none focus:ring-2 focus:ring-primary-500 shadow-sm"
            >
              <option value="all">All Audiences</option>
              <option value="internal">Internal Only</option>
              <option value="external">External Only</option>
            </select>
          </div>
          <div className="flex items-center gap-3 px-6 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-2xl shadow-sm">
            <label className="flex items-center gap-3 cursor-pointer whitespace-nowrap">
              <input
                type="checkbox"
                checked={excludeMicrosoft}
                onChange={e => setExcludeMicrosoft(e.target.checked)}
                className="w-5 h-5 rounded-lg border-gray-300 text-primary-600 focus:ring-primary-500 transition-all cursor-pointer"
              />
              <span className="text-sm font-bold text-gray-700 dark:text-gray-300">
                Hide Microsoft Apps
              </span>
            </label>
          </div>
        </div>

        {/* View Layouts */}
        {isLoading ? (
          <div className="py-24 flex flex-col items-center justify-center text-gray-500">
            <RefreshCw className="w-10 h-10 animate-spin text-primary-500 mb-4" />
            <p className="text-lg font-medium">Scanning Applications...</p>
          </div>
        ) : filteredApps.length === 0 ? (
          <div className="py-24 bg-white dark:bg-gray-800 rounded-3xl border-2 border-dashed border-gray-200 dark:border-gray-700 text-center flex flex-col items-center">
            <div className="p-4 bg-gray-50 dark:bg-gray-900 rounded-full mb-4">
              <Search className="w-8 h-8 text-gray-400" />
            </div>
            <h3 className="text-xl font-bold text-gray-900 dark:text-white">
              No applications found
            </h3>
            <p className="text-gray-500 dark:text-gray-400 mt-2 max-w-xs mx-auto">
              Try adjusting your filters or search query to find the applications you are looking
              for.
            </p>
          </div>
        ) : viewMode === 'grid' ? (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
            {filteredApps.map(app => (
              <AppCard key={app.id} app={app} onClick={() => openAppDetails(app)} />
            ))}
          </div>
        ) : (
          <div className="bg-white dark:bg-gray-800 rounded-3xl border border-gray-200 dark:border-gray-700 shadow-xl overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="bg-gray-50 dark:bg-gray-900/50 border-b border-gray-200 dark:border-gray-700">
                    <th className="text-left px-8 py-4 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Application
                    </th>
                    <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Publisher
                    </th>
                    <th className="text-left px-6 py-4 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Risk Level
                    </th>
                    <th className="text-center px-6 py-4 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Access Score
                    </th>
                    <th className="text-right px-8 py-4 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 dark:divide-gray-700/50">
                  {filteredApps.map(app => (
                    <tr
                      key={app.id}
                      className="hover:bg-gray-50/80 dark:hover:bg-gray-700/30 transition-colors group"
                    >
                      <td className="px-8 py-5">
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 rounded-xl bg-gray-100 dark:bg-gray-700 flex items-center justify-center text-gray-500 dark:text-gray-400 font-bold text-lg">
                            {app.display_name.charAt(0)}
                          </div>
                          <div>
                            <div className="flex items-center gap-2">
                              <p className="text-sm font-semibold text-gray-900 dark:text-white">
                                {app.display_name}
                              </p>
                              {app.is_new_app && (
                                <span className="px-1.5 py-0.5 bg-blue-500 text-white text-[10px] rounded-lg font-bold">
                                  NEW
                                </span>
                              )}
                            </div>
                            <p className="text-xs text-gray-500 mt-1">
                              {app.consent_count} user consents
                            </p>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-5">
                        <span
                          className={clsx(
                            'px-3 py-1 rounded-full text-xs font-bold border transition-colors',
                            publisherColors[app.publisher_type] ||
                              'bg-gray-100 text-gray-600 border-gray-200'
                          )}
                        >
                          {app.publisher_name || app.publisher_type}
                        </span>
                      </td>
                      <td className="px-6 py-5">
                        <span
                          className={clsx(
                            'px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest transition-all',
                            riskColors[app.risk_level]
                          )}
                        >
                          {app.risk_level}
                        </span>
                      </td>
                      <td className="px-6 py-5">
                        <div className="flex items-center justify-center gap-3">
                          <div className="w-full max-w-[60px] bg-gray-100 dark:bg-gray-700 rounded-full h-1.5 overflow-hidden">
                            <div
                              className={clsx(
                                'h-full transition-all duration-1000',
                                app.risk_score > 60
                                  ? 'bg-red-500'
                                  : app.risk_score > 30
                                    ? 'bg-amber-500'
                                    : 'bg-blue-500'
                              )}
                              style={{ width: `${app.risk_score}%` }}
                            />
                          </div>
                          <span className="text-sm font-black text-gray-900 dark:text-white">
                            {app.risk_score}
                          </span>
                        </div>
                      </td>
                      <td className="px-8 py-5 text-right">
                        <button
                          onClick={() => openAppDetails(app)}
                          className="p-2 text-gray-400 hover:text-primary-500 hover:bg-primary-50 dark:hover:bg-primary-900/20 rounded-xl transition-all"
                        >
                          <ChevronRight className="w-5 h-5" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* Details Side-Panel / Modal */}
      <AppDetailsModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        app={selectedApp}
      />
    </div>
  );
}

// Sub-components to keep the main component clean

function StatCard({ title, value, icon: Icon, color, trend }: any) {
  const colors: any = {
    blue: 'bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 border-blue-100 dark:border-blue-800',
    red: 'bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 border-red-100 dark:border-red-800',
    amber:
      'bg-amber-50 dark:bg-amber-900/20 text-amber-600 dark:text-amber-400 border-amber-100 dark:border-amber-800',
    violet:
      'bg-violet-50 dark:bg-violet-900/20 text-violet-600 dark:text-violet-400 border-violet-100 dark:border-violet-800',
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-3xl p-6 border border-gray-200 dark:border-gray-700 shadow-sm hover:shadow-md transition-all group">
      <div className="flex items-start justify-between">
        <div
          className={clsx(
            'p-3 rounded-2xl border transition-all duration-300 transform group-hover:scale-110',
            colors[color]
          )}
        >
          <Icon className="w-6 h-6" />
        </div>
        {trend && (
          <span className="text-[10px] font-black uppercase text-gray-400 tracking-tighter">
            {trend}
          </span>
        )}
      </div>
      <div className="mt-5">
        <p className="text-3xl font-black text-gray-900 dark:text-white leading-none tracking-tight">
          {value}
        </p>
        <p className="mt-2 text-xs font-bold text-gray-500 dark:text-gray-400 uppercase tracking-widest">
          {title}
        </p>
      </div>
    </div>
  );
}

function AppCard({ app, onClick }: { app: OAuthApp; onClick: () => void }) {
  return (
    <div
      onClick={onClick}
      className={clsx(
        'group cursor-pointer bg-white dark:bg-gray-800 rounded-3xl p-6 border-2 transition-all duration-300 hover:shadow-2xl hover:-translate-y-1',
        riskBorderColors[app.risk_level] || 'border-transparent'
      )}
    >
      <div className="flex justify-between items-start mb-6">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-2xl bg-gray-100 dark:bg-gray-700 flex items-center justify-center text-xl font-black text-gray-400 dark:text-gray-500 transition-all group-hover:bg-primary-500 group-hover:text-white">
            {app.display_name.charAt(0)}
          </div>
          <div>
            <h3 className="font-extrabold text-gray-900 dark:text-white leading-tight line-clamp-1">
              {app.display_name}
            </h3>
            <p className="text-xs font-medium text-gray-500 mt-0.5">
              {app.publisher_name || 'Internal/Private'}
            </p>
          </div>
        </div>
        <div className="text-right">
          <div className="text-xs font-black text-gray-400 dark:text-gray-500 uppercase tracking-wider mb-1">
            Risk Score
          </div>
          <div
            className={clsx(
              'text-xl font-black transition-colors',
              app.risk_score > 60
                ? 'text-red-500'
                : app.risk_score > 30
                  ? 'text-amber-500'
                  : 'text-primary-500'
            )}
          >
            {app.risk_score}
          </div>
        </div>
      </div>

      <div className="flex gap-2 mb-6">
        <span
          className={clsx(
            'px-2.5 py-1 rounded-lg text-[10px] font-black uppercase tracking-widest border transition-all group-hover:border-transparent group-hover:bg-opacity-100',
            publisherColors[app.publisher_type] || 'bg-gray-100'
          )}
        >
          {app.publisher_type}
        </span>
        <span
          className={clsx(
            'px-2.5 py-1 rounded-lg text-[10px] font-black uppercase tracking-widest',
            riskColors[app.risk_level]
          )}
        >
          {app.risk_level}
        </span>
      </div>

      <div className="space-y-4">
        <div className="flex justify-between items-center text-xs">
          <span className="text-gray-500 font-bold uppercase tracking-widest">Capabilities</span>
          <span className="text-gray-400">{app.permission_count} permissions</span>
        </div>
        <div className="flex gap-2">
          <CapIcon icon={Mail} active={app.has_mail_permissions} color="red" />
          <CapIcon icon={Users} active={app.has_user_read_all} color="amber" />
          <CapIcon icon={FileText} active={app.has_files_read_all} color="purple" />
          <CapIcon icon={Calendar} active={app.has_calendar_access} color="blue" />
          <CapIcon icon={ShieldCheck} active={app.has_admin_consent} color="emerald" />
        </div>
      </div>

      <div className="mt-8 pt-6 border-t border-gray-100 dark:border-gray-700 flex items-center justify-between">
        <div className="flex -space-x-2">
          {[...Array(Math.min(3, app.consent_count))].map((_, i) => (
            <div
              key={i}
              className="w-7 h-7 rounded-full bg-gray-200 dark:bg-gray-600 border-2 border-white dark:border-gray-800 flex items-center justify-center text-[10px] font-bold text-gray-500"
            >
              <UserCheck className="w-3 h-3" />
            </div>
          ))}
          {app.consent_count > 3 && (
            <div className="text-[10px] font-bold text-gray-400 pl-4">
              +{app.consent_count - 3} more
            </div>
          )}
          {app.consent_count === 0 && (
            <span className="text-[10px] font-bold text-gray-400">No user consents</span>
          )}
        </div>
        <button className="text-xs font-black uppercase text-primary-600 dark:text-primary-400 group-hover:translate-x-1 transition-transform inline-flex items-center gap-1">
          Review <ChevronRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}

function CapIcon({ icon: Icon, active, color }: any) {
  const activeColors: any = {
    red: 'bg-red-500 text-white shadow-lg shadow-red-200 dark:shadow-red-900/20',
    amber: 'bg-amber-500 text-white shadow-lg shadow-amber-200 dark:shadow-amber-900/20',
    purple: 'bg-purple-500 text-white shadow-lg shadow-purple-200 dark:shadow-purple-900/20',
    blue: 'bg-blue-500 text-white shadow-lg shadow-blue-200 dark:shadow-blue-900/20',
    emerald: 'bg-emerald-500 text-white shadow-lg shadow-emerald-200 dark:shadow-emerald-900/20',
  };

  return (
    <div
      className={clsx(
        'p-2 rounded-xl border transition-all duration-300',
        active
          ? activeColors[color]
          : 'bg-gray-50 dark:bg-gray-800 text-gray-300 dark:text-gray-600 border-gray-200 dark:border-gray-700 grayscale'
      )}
    >
      <Icon className="w-4 h-4" />
    </div>
  );
}

function AppDetailsModal({
  isOpen,
  onClose,
  app,
}: {
  isOpen: boolean;
  onClose: () => void;
  app: OAuthApp | null;
}) {
  if (!app) return null;

  return (
    <Transition.Root show={isOpen} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={onClose}>
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-gray-900/80 backdrop-blur-sm transition-opacity" />
        </Transition.Child>

        <div className="fixed inset-0 z-10 overflow-y-auto">
          <div className="flex min-h-full items-center justify-center p-4 sm:p-6 lg:p-8">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 scale-95 translate-y-4"
              enterTo="opacity-100 scale-100 translate-y-0"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 scale-100 translate-y-0"
              leaveTo="opacity-0 scale-95 translate-y-4"
            >
              <Dialog.Panel className="relative w-full max-w-4xl rounded-3xl bg-white dark:bg-gray-900 shadow-2xl overflow-hidden">
                {/* Modal Header */}
                <div className="bg-gray-50 dark:bg-gray-800/50 p-8 border-b border-gray-200 dark:border-gray-700">
                  <div className="flex justify-between items-start">
                    <div className="flex gap-6">
                      <div className="w-20 h-20 rounded-3xl bg-primary-500 text-white flex items-center justify-center text-4xl font-black shadow-xl shadow-primary-500/20">
                        {app.display_name.charAt(0)}
                      </div>
                      <div>
                        <Dialog.Title className="text-3xl font-black text-gray-900 dark:text-white tracking-tight">
                          {app.display_name}
                        </Dialog.Title>
                        <p className="text-gray-500 dark:text-gray-400 mt-1 font-medium">
                          {app.publisher_name || 'Self-published / Private Application'}
                        </p>
                        <div className="mt-4 flex gap-2">
                          <span
                            className={clsx(
                              'px-3 py-1 rounded-full text-xs font-bold uppercase tracking-widest',
                              riskColors[app.risk_level]
                            )}
                          >
                            {app.risk_level} Risk
                          </span>
                          <span
                            className={clsx(
                              'px-3 py-1 rounded-full text-xs font-bold uppercase tracking-widest border transition-colors',
                              publisherColors[app.publisher_type] || 'bg-gray-100 text-gray-600'
                            )}
                          >
                            {app.publisher_type} Publisher
                          </span>
                        </div>
                      </div>
                    </div>
                    <button
                      onClick={onClose}
                      className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition-colors"
                    >
                      <X className="w-6 h-6" />
                    </button>
                  </div>
                </div>

                <div className="p-8 grid grid-cols-1 lg:grid-cols-3 gap-8">
                  {/* Left Column: Risk & Detection */}
                  <div className="lg:col-span-2 space-y-8">
                    <section>
                      <h4 className="text-sm font-black text-gray-400 uppercase tracking-widest mb-4">
                        Risk Analysis
                      </h4>
                      <div className="bg-gray-50 dark:bg-gray-800/50 rounded-2xl p-6 border border-gray-100 dark:border-gray-700">
                        <div className="flex items-center gap-6 mb-6">
                          <div className="text-center">
                            <div
                              className={clsx(
                                'text-4xl font-black',
                                app.risk_score > 60
                                  ? 'text-red-500'
                                  : app.risk_score > 30
                                    ? 'text-amber-500'
                                    : 'text-primary-500'
                              )}
                            >
                              {app.risk_score}
                            </div>
                            <div className="text-[10px] font-black uppercase text-gray-400 tracking-tighter">
                              Aggregate Score
                            </div>
                          </div>
                          <div className="h-12 w-px bg-gray-200 dark:bg-gray-700" />
                          <p className="text-sm text-gray-600 dark:text-gray-300 font-medium">
                            This application has been flagged based on its permission breadth,
                            publisher reputation, and historical usage patterns in the tenant.
                          </p>
                        </div>

                        <div className="space-y-3">
                          {app.detection_reasons.map((reason, i) => (
                            <div
                              key={i}
                              className="flex gap-3 text-sm font-bold text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-800 p-3 rounded-xl border border-gray-100 dark:border-gray-700"
                            >
                              <AlertTriangle className="w-5 h-5 text-amber-500 flex-shrink-0" />
                              {reason}
                            </div>
                          ))}
                        </div>
                      </div>
                    </section>

                    <section>
                      <h4 className="text-sm font-black text-gray-400 uppercase tracking-widest mb-4">
                        High Risk Permissions
                      </h4>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        {app.high_risk_permissions.map((perm, i) => (
                          <div
                            key={i}
                            className="flex items-center gap-3 p-4 bg-red-50 dark:bg-red-900/10 border border-red-100 dark:border-red-900/30 rounded-2xl"
                          >
                            <ShieldAlert className="w-5 h-5 text-red-500" />
                            <span className="text-sm font-black text-red-700 dark:text-red-400">
                              {perm}
                            </span>
                          </div>
                        ))}
                        {app.high_risk_permissions.length === 0 && (
                          <div className="col-span-2 py-8 text-center bg-gray-50 dark:bg-gray-800/50 rounded-2xl border-2 border-dashed border-gray-200 dark:border-gray-700">
                            <CheckCircle2 className="w-8 h-8 text-emerald-500 mx-auto mb-2" />
                            <p className="text-sm font-bold text-gray-500">
                              No high-risk permissions detected
                            </p>
                          </div>
                        )}
                      </div>
                    </section>
                  </div>

                  {/* Right Column: App Metadata */}
                  <div className="space-y-8">
                    <section>
                      <h4 className="text-sm font-black text-gray-400 uppercase tracking-widest mb-4">
                        App Identity
                      </h4>
                      <div className="space-y-4">
                        <MetaItem label="App ID" value={app.app_id} code />
                        <MetaItem label="Tenant ID" value={app.tenant_id} code />
                        <MetaItem
                          label="Publisher ID"
                          value={app.publisher_id || 'Not Available'}
                        />
                        <MetaItem
                          label="Created At"
                          value={
                            app.app_created_at
                              ? new Date(app.app_created_at).toLocaleDateString()
                              : 'Unknown'
                          }
                        />
                      </div>
                    </section>

                    <section>
                      <h4 className="text-sm font-black text-gray-400 uppercase tracking-widest mb-4">
                        Usage Stats
                      </h4>
                      <div className="grid grid-cols-2 gap-4">
                        <div className="bg-gray-50 dark:bg-gray-800 rounded-2xl p-4 border border-gray-100 dark:border-gray-700">
                          <div className="text-2xl font-black text-gray-900 dark:text-white">
                            {app.consent_count}
                          </div>
                          <div className="text-[10px] font-black text-gray-400 uppercase mt-1">
                            Total Users
                          </div>
                        </div>
                        <div className="bg-gray-50 dark:bg-gray-800 rounded-2xl p-4 border border-gray-100 dark:border-gray-700">
                          <div className="text-2xl font-black text-gray-900 dark:text-white">
                            {app.permission_count}
                          </div>
                          <div className="text-[10px] font-black text-gray-400 uppercase mt-1">
                            Total Scopes
                          </div>
                        </div>
                      </div>
                    </section>

                    <div className="pt-6">
                      <button
                        onClick={() =>
                          window.open(
                            `https://portal.azure.com/#blade/Microsoft_AAD_IAM/StartboardApplicationsMenuBlade/AppDetails/appId/${app.app_id}/activeTab/overview`,
                            '_blank'
                          )
                        }
                        className="w-full py-4 bg-primary-600 text-white rounded-2xl font-black uppercase text-xs tracking-widest hover:bg-primary-700 transition-all shadow-xl shadow-primary-500/20 flex items-center justify-center gap-2"
                      >
                        View in Entra Portal <ExternalLink className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition.Root>
  );
}

function MetaItem({ label, value, code }: { label: string; value: string; code?: boolean }) {
  return (
    <div>
      <p className="text-[10px] font-black text-gray-400 uppercase tracking-wider mb-1">{label}</p>
      <p
        className={clsx(
          'text-sm font-medium text-gray-900 dark:text-white break-all',
          code && 'font-mono bg-gray-100 dark:bg-gray-800 px-2 py-0.5 rounded text-xs'
        )}
      >
        {value}
      </p>
    </div>
  );
}
