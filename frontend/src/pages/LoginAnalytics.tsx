import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { BarChart3, Download } from 'lucide-react';
import FilterPanel from '@/components/FilterPanel';
import LoginTimeline from '@/components/LoginTimeline';
import { useLoginAnalytics, useExportLogins } from '@/hooks/useApi';
import { LoginFilters } from '@/types';
import toast from 'react-hot-toast';

export default function LoginAnalytics() {
  const [searchParams] = useSearchParams();
  const initialUser = searchParams.get('user');

  const [filters, setFilters] = useState<LoginFilters>({
    page: 1,
    page_size: 20,
    ...(initialUser ? { user: initialUser } : {})
  });

  const { data, isLoading, error } = useLoginAnalytics(filters);
  const exportMutation = useExportLogins();

  const handleExport = async () => {
    try {
      await exportMutation.mutateAsync(filters);
      toast.success('Export downloaded successfully');
    } catch (err) {
      toast.error('Failed to export data');
    }
  };

  // Prepare chart data from logins
  const chartData = data?.logins.reduce((acc, login) => {
    const hour = new Date(login.login_time).getHours();
    const key = `${hour}:00`;

    if (!acc[key]) {
      acc[key] = { time: key, success: 0, failed: 0 };
    }

    if (login.is_success) {
      acc[key].success++;
    } else {
      acc[key].failed++;
    }

    return acc;
  }, {} as Record<string, { time: string; success: number; failed: number }>);

  const chartDataArray = chartData ? Object.values(chartData).sort((a, b) => {
    const hourA = parseInt(a.time);
    const hourB = parseInt(b.time);
    return hourA - hourB;
  }) : [];

  if (error) {
    return (
      <div className="text-center py-12">
        <p className="text-red-500">Error loading analytics data</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <BarChart3 className="w-6 h-6 text-primary-500" />
            Login Analytics
          </h1>
          <p className="mt-1 text-gray-500 dark:text-gray-400">
            Analyze login patterns and detect anomalies
          </p>
        </div>

        <button
          onClick={handleExport}
          disabled={exportMutation.isPending || !data}
          className="flex items-center gap-2 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <Download className="w-4 h-4" />
          {exportMutation.isPending ? 'Exporting...' : 'Export CSV'}
        </button>
      </div>

      {/* Filters */}
      <FilterPanel
        filters={filters}
        onChange={setFilters}
        onExport={handleExport}
        showExport={true}
      />

      {/* Chart */}
      {chartDataArray.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Login Activity by Hour
          </h2>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartDataArray}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.2} />
                <XAxis
                  dataKey="time"
                  stroke="#6B7280"
                  fontSize={12}
                  tickLine={false}
                />
                <YAxis
                  stroke="#6B7280"
                  fontSize={12}
                  tickLine={false}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'rgba(17, 24, 39, 0.9)',
                    border: 'none',
                    borderRadius: '8px',
                    color: '#fff',
                  }}
                />
                <Bar dataKey="success" name="Success" fill="#22c55e" radius={[4, 4, 0, 0]} />
                <Bar dataKey="failed" name="Failed" fill="#ef4444" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Login Timeline */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Login Timeline
        </h2>
        <LoginTimeline
          logins={data?.logins || []}
          total={data?.total || 0}
          page={filters.page || 1}
          pageSize={filters.page_size || 20}
          onPageChange={(page) => setFilters({ ...filters, page })}
          loading={isLoading}
        />
      </div>
    </div>
  );
}
