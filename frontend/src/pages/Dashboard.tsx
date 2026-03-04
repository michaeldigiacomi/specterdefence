import { useState } from 'react';
import {
  Download,
  RefreshCw,
  TrendingDown,
  Shield,
  AlertTriangle,
  Activity
} from 'lucide-react';
import { toast } from 'react-hot-toast';
import {
  LoginTimelineChart,
  GeoHeatmap,
  AnomalyTrendChart,
  AlertVolumeChart,
  TopRiskUsers,
  AnomalyBreakdownChart,
} from '@/components/charts';
import { useDashboardData, TimeRange } from '@/hooks/useDashboard';
import StatsCard from '@/components/StatsCard';
import clsx from 'clsx';

export default function Dashboard() {
  const [timeRange, setTimeRange] = useState<TimeRange>('30d');
  const [isExporting, setIsExporting] = useState(false);

  const { data, isLoading, refetch, isRefetching } = useDashboardData(timeRange);

  const handleExport = async (format: 'csv' | 'json' | 'pdf') => {
    setIsExporting(true);
    try {
      const blob = await fetch(`/api/v1/dashboard/export/download/${format}?time_range=${timeRange}`)
        .then(res => res.blob());

      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `dashboard-export-${new Date().toISOString().split('T')[0]}.${format}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      toast.success(`Dashboard exported as ${format.toUpperCase()}`);
    } catch (error) {
      toast.error('Failed to export dashboard');
    } finally {
      setIsExporting(false);
    }
  };

  const summary = data?.summary;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Security Dashboard
          </h1>
          <p className="mt-1 text-gray-500 dark:text-gray-400">
            Monitor security events, anomalies, and user activity across all tenants
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* Time Range Selector */}
          <div className="flex bg-gray-100 dark:bg-gray-700 rounded-lg p-1">
            {(['7d', '30d', '90d'] as TimeRange[]).map((range) => (
              <button
                key={range}
                onClick={() => setTimeRange(range)}
                className={clsx(
                  'px-3 py-1.5 text-sm font-medium rounded-md transition-colors',
                  timeRange === range
                    ? 'bg-white dark:bg-gray-600 text-gray-900 dark:text-white shadow-sm'
                    : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
                )}
              >
                {range === '7d' && '7 Days'}
                {range === '30d' && '30 Days'}
                {range === '90d' && '90 Days'}
              </button>
            ))}
          </div>

          {/* Refresh Button */}
          <button
            onClick={() => refetch()}
            disabled={isRefetching}
            className="p-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
            title="Refresh data"
          >
            <RefreshCw className={clsx('w-5 h-5', isRefetching && 'animate-spin')} />
          </button>

          {/* Export Dropdown */}
          <div className="relative group">
            <button
              disabled={isExporting}
              className="flex items-center gap-2 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors disabled:opacity-50"
            >
              <Download className="w-4 h-4" />
              Export
            </button>

            <div className="absolute right-0 mt-2 w-32 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-10">
              <button
                onClick={() => handleExport('csv')}
                className="block w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 first:rounded-t-lg"
              >
                Export CSV
              </button>
              <button
                onClick={() => handleExport('json')}
                className="block w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 last:rounded-b-lg"
              >
                Export JSON
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatsCard
          title="Total Logins (24h)"
          value={summary?.total_logins_24h?.toLocaleString() || 0}
          icon={Activity}
          color="blue"
          loading={isLoading}
          trend={
            summary && {
              value: Math.round(((summary.total_logins_24h - summary.failed_logins_24h) / (summary.total_logins_24h || 1)) * 100),
              label: 'success rate',
              positive: summary.failed_logins_24h < summary.total_logins_24h * 0.1
            }
          }
        />

        <StatsCard
          title="Failed Logins (24h)"
          value={summary?.failed_logins_24h?.toLocaleString() || 0}
          icon={TrendingDown}
          color="red"
          loading={isLoading}
        />

        <StatsCard
          title="Anomalies Detected"
          value={summary?.anomalies_today?.toLocaleString() || 0}
          icon={AlertTriangle}
          color="amber"
          loading={isLoading}
          trend={
            (summary?.anomalies_today || 0) > 0
              ? { value: summary?.anomalies_today || 0, label: 'today', positive: false }
              : undefined
          }
        />

        <StatsCard
          title="Avg Risk Score"
          value={summary?.avg_risk_score?.toFixed(1) || '0.0'}
          icon={Shield}
          color={
            (summary?.avg_risk_score || 0) >= 70
              ? 'red'
              : (summary?.avg_risk_score || 0) >= 40
              ? 'amber'
              : 'green'
          }
          loading={isLoading}
        />
      </div>

      {/* Main Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Login Activity Timeline */}
        <LoginTimelineChart
          data={data?.login_timeline?.data || []}
          changePercent={data?.login_timeline?.change_percent || 0}
          isLoading={isLoading}
          timeRange={timeRange}
          onTimeRangeChange={setTimeRange}
        />

        {/* Geographic Heatmap */}
        <GeoHeatmap
          data={data?.geo_heatmap?.locations || []}
          totalCountries={data?.geo_heatmap?.total_countries || 0}
          topCountry={data?.geo_heatmap?.top_country || undefined}
          isLoading={isLoading}
        />

        {/* Anomaly Trend */}
        <AnomalyTrendChart
          data={data?.anomaly_trend?.data || []}
          totalAnomalies={data?.anomaly_trend?.total_anomalies || 0}
          topType={data?.anomaly_trend?.top_type || undefined}
          changePercent={data?.anomaly_trend?.change_percent || 0}
          isLoading={isLoading}
          timeRange={timeRange}
          onTimeRangeChange={setTimeRange}
        />

        {/* Alert Volume */}
        <AlertVolumeChart
          data={data?.alert_volume?.data || []}
          totalBySeverity={data?.alert_volume?.total_by_severity || {}}
          peakVolume={data?.alert_volume?.peak_volume || 0}
          isLoading={isLoading}
          timeRange={timeRange}
          onTimeRangeChange={setTimeRange}
        />
      </div>

      {/* Bottom Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Top Risk Users */}
        <div className="lg:col-span-2">
          <TopRiskUsers
            users={data?.top_risk_users?.users || []}
            totalUsers={data?.top_risk_users?.total_users || 0}
            avgRiskScore={data?.top_risk_users?.avg_risk_score || 0}
            isLoading={isLoading}
          />
        </div>

        {/* Anomaly Breakdown */}
        <AnomalyBreakdownChart
          data={data?.anomaly_breakdown || []}
          isLoading={isLoading}
        />
      </div>

      {/* Last Updated */}
      {data?.generated_at && (
        <div className="text-center text-sm text-gray-500 dark:text-gray-400">
          Last updated: {new Date(data.generated_at).toLocaleString()}
        </div>
      )}
    </div>
  );
}
