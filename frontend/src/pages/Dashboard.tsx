import { useState } from 'react';
import { 
  Users, 
  XCircle, 
  AlertTriangle, 
  Building2, 
  ArrowRight
} from 'lucide-react';
import { Link } from 'react-router-dom';
import StatsCard from '@/components/StatsCard';
import AnomalyCard from '@/components/AnomalyCard';
import FilterPanel from '@/components/FilterPanel';
import { useDashboardStats, useRecentAnomalies } from '@/hooks/useApi';
import { LoginFilters } from '@/types';

export default function Dashboard() {
  const [filters, setFilters] = useState<LoginFilters>({ page_size: 10 });
  
  const { data: stats, isLoading: statsLoading } = useDashboardStats();
  const { data: anomalies, isLoading: anomaliesLoading } = useRecentAnomalies({ hours: 24, limit: 5 });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Dashboard</h1>
          <p className="mt-1 text-gray-500 dark:text-gray-400">
            Overview of your security posture and recent activity
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link
            to="/analytics"
            className="flex items-center gap-2 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors"
          >
            View Analytics
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatsCard
          title="Total Logins (24h)"
          value={stats?.total_logins?.toLocaleString() || 0}
          icon={Users}
          color="blue"
          loading={statsLoading}
          trend={{ value: 12, label: 'vs yesterday', positive: true }}
        />

        <StatsCard
          title="Failed Logins (24h)"
          value={stats?.failed_logins?.toLocaleString() || 0}
          icon={XCircle}
          color="red"
          loading={statsLoading}
          trend={{ value: -5, label: 'vs yesterday', positive: true }}
        />

        <StatsCard
          title="Anomalies Today"
          value={stats?.anomalies_today?.toLocaleString() || 0}
          icon={AlertTriangle}
          color="amber"
          loading={statsLoading}
        />

        <StatsCard
          title="Active Tenants"
          value={stats?.active_tenants?.toLocaleString() || 0}
          icon={Building2}
          color="green"
          loading={statsLoading}
        />
      </div>

      {/* Quick Filters */}
      <FilterPanel
        filters={filters}
        onChange={setFilters}
        compact={true}
      />

      {/* Recent Activity Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Anomalies */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              Recent Anomalies
            </h2>
            <Link
              to="/anomalies"
              className="text-sm text-primary-600 hover:text-primary-700 dark:text-primary-400 flex items-center gap-1"
            >
              View all
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>

          <div className="space-y-3">
            {anomaliesLoading ? (
              [1, 2, 3].map((i) => (
                <div 
                  key={i} 
                  className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5 animate-pulse"
                >
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 bg-gray-200 dark:bg-gray-700 rounded-lg"></div>
                    <div className="flex-1">
                      <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/3 mb-2"></div>
                      <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-1/2"></div>
                    </div>
                  </div>
                </div>
              ))
            ) : anomalies && anomalies.length > 0 ? (
              anomalies.slice(0, 5).map((anomaly, idx) => (
                <AnomalyCard key={idx} anomaly={anomaly} compact />
              ))
            ) : (
              <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-8 text-center">
                <AlertTriangle className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
                <p className="text-gray-500 dark:text-gray-400">No anomalies detected in the last 24 hours</p>
              </div>
            )}
          </div>
        </div>

        {/* Quick Stats / Trends */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              Security Trends
            </h2>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
            <div className="space-y-6">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-600 dark:text-gray-400">Login Success Rate</span>
                  <span className="text-sm font-semibold text-green-600">98.5%</span>
                </div>
                <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                  <div className="bg-green-500 h-2 rounded-full" style={{ width: '98.5%' }} />
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-600 dark:text-gray-400">Anomaly Detection Rate</span>
                  <span className="text-sm font-semibold text-amber-600">2.3%</span>
                </div>
                <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                  <div className="bg-amber-500 h-2 rounded-full" style={{ width: '2.3%' }} />
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-600 dark:text-gray-400">Tenant Health Score</span>
                  <span className="text-sm font-semibold text-primary-600">92%</span>
                </div>
                <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                  <div className="bg-primary-500 h-2 rounded-full" style={{ width: '92%' }} />
                </div>
              </div>
            </div>

            <div className="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
              <div className="grid grid-cols-3 gap-4 text-center">
                <div>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">{stats?.total_logins || 0}</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">Total Logins</p>
                </div>
                <div>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">{anomalies?.length || 0}</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">Recent Anomalies</p>
                </div>
                <div>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">{stats?.active_tenants || 0}</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">Active Tenants</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
