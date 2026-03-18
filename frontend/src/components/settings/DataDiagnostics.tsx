import { useState, useEffect } from 'react';
import { RefreshCw, Database, FileText, CheckCircle, XCircle, Clock } from 'lucide-react';

interface DiagnosticsSummary {
  audit_logs_count: number;
  audit_logs_signin_count: number;
  audit_logs_latest: string | null;
  login_analytics_count: number;
  login_analytics_success_count: number;
  login_analytics_failed_count: number;
  login_analytics_latest: string | null;
  unprocessed_signin_count: number;
}

interface AuditLogRecord {
  id: string;
  created_at: string;
  log_type: string;
  operation: string | null;
  user_id: string | null;
  user_email: string | null;
  ip_address: string | null;
  result_status: string | null;
  processed: boolean;
}

interface LoginAnalyticsRecord {
  id: string;
  created_at: string;
  user_email: string | null;
  ip_address: string | null;
  is_success: boolean;
  failure_reason: string | null;
  country: string | null;
}

export default function DataDiagnostics() {
  const [loading, setLoading] = useState(true);
  const [summary, setSummary] = useState<DiagnosticsSummary | null>(null);
  const [auditLogs, setAuditLogs] = useState<AuditLogRecord[]>([]);
  const [loginAnalytics, setLoginAnalytics] = useState<LoginAnalyticsRecord[]>([]);
  const [activeView, setActiveView] = useState<'summary' | 'audit-logs' | 'login-analytics'>('summary');
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      // Fetch summary
      const summaryRes = await fetch('/api/v1/diagnostics/summary');
      if (!summaryRes.ok) throw new Error('Failed to fetch summary');
      const summaryData = await summaryRes.json();
      setSummary(summaryData);

      // Fetch recent audit logs
      const auditLogsRes = await fetch('/api/v1/diagnostics/audit-logs?limit=20');
      if (!auditLogsRes.ok) throw new Error('Failed to fetch audit logs');
      const auditLogsData = await auditLogsRes.json();
      setAuditLogs(auditLogsData);

      // Fetch recent login analytics
      const loginAnalyticsRes = await fetch('/api/v1/diagnostics/login-analytics?limit=20');
      if (!loginAnalyticsRes.ok) throw new Error('Failed to fetch login analytics');
      const loginAnalyticsData = await loginAnalyticsRes.json();
      setLoginAnalytics(loginAnalyticsData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return 'N/A';
    return new Date(dateStr).toLocaleString();
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <RefreshCw className="w-8 h-8 animate-spin text-primary-500" />
        <span className="ml-2 text-gray-500">Loading diagnostics...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-lg">
        <p className="text-red-600 dark:text-red-400">{error}</p>
        <button
          onClick={fetchData}
          className="mt-2 px-4 py-2 bg-red-100 dark:bg-red-800 rounded hover:bg-red-200 dark:hover:bg-red-700"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header with refresh button */}
      <div className="flex justify-between items-center">
        <div>
          <h3 className="text-lg font-medium text-gray-900 dark:text-white">
            Data Ingestion Diagnostics
          </h3>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            View what's being collected from the O365 cron job
          </p>
        </div>
        <button
          onClick={fetchData}
          className="flex items-center gap-2 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-gray-200 dark:border-gray-700">
        <button
          onClick={() => setActiveView('summary')}
          className={`px-4 py-2 border-b-2 transition-colors ${
            activeView === 'summary'
              ? 'border-primary-500 text-primary-600 dark:text-primary-400'
              : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'
          }`}
        >
          Summary
        </button>
        <button
          onClick={() => setActiveView('audit-logs')}
          className={`px-4 py-2 border-b-2 transition-colors ${
            activeView === 'audit-logs'
              ? 'border-primary-500 text-primary-600 dark:text-primary-400'
              : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'
          }`}
        >
          Raw Audit Logs
        </button>
        <button
          onClick={() => setActiveView('login-analytics')}
          className={`px-4 py-2 border-b-2 transition-colors ${
            activeView === 'login-analytics'
              ? 'border-primary-500 text-primary-600 dark:text-primary-400'
              : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'
          }`}
        >
          Login Analytics
        </button>
      </div>

      {/* Summary View */}
      {activeView === 'summary' && summary && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Audit Logs Card */}
          <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <Database className="w-5 h-5 text-blue-500" />
              <span className="font-medium text-gray-900 dark:text-white">Audit Logs</span>
            </div>
            <p className="text-2xl font-bold text-gray-900 dark:text-white">
              {summary.audit_logs_count}
            </p>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {summary.audit_logs_signin_count} sign-in records
            </p>
            <p className="text-xs text-gray-400 dark:text-gray-500 mt-2">
              Latest: {formatDate(summary.audit_logs_latest)}
            </p>
          </div>

          {/* Login Analytics Card */}
          <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <FileText className="w-5 h-5 text-green-500" />
              <span className="font-medium text-gray-900 dark:text-white">Login Analytics</span>
            </div>
            <p className="text-2xl font-bold text-gray-900 dark:text-white">
              {summary.login_analytics_count}
            </p>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {summary.login_analytics_success_count} success, {summary.login_analytics_failed_count} failed
            </p>
            <p className="text-xs text-gray-400 dark:text-gray-500 mt-2">
              Latest: {formatDate(summary.login_analytics_latest)}
            </p>
          </div>

          {/* Unprocessed Card */}
          <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <Clock className="w-5 h-5 text-yellow-500" />
              <span className="font-medium text-gray-900 dark:text-white">Unprocessed</span>
            </div>
            <p className="text-2xl font-bold text-gray-900 dark:text-white">
              {summary.unprocessed_signin_count}
            </p>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Sign-in records pending processing
            </p>
          </div>

          {/* Status Card */}
          <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              {summary.unprocessed_signin_count > 0 ? (
                <XCircle className="w-5 h-5 text-red-500" />
              ) : (
                <CheckCircle className="w-5 h-5 text-green-500" />
              )}
              <span className="font-medium text-gray-900 dark:text-white">Status</span>
            </div>
            <p className="text-lg font-bold text-gray-900 dark:text-white">
              {summary.unprocessed_signin_count > 0 ? 'Needs Attention' : 'Up to Date'}
            </p>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {summary.unprocessed_signin_count > 0 
                ? 'Some records not processed' 
                : 'All records processed'}
            </p>
          </div>
        </div>
      )}

      {/* Audit Logs View */}
      {activeView === 'audit-logs' && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 dark:bg-gray-700">
              <tr>
                <th className="px-4 py-2 text-left text-gray-500 dark:text-gray-400">Time</th>
                <th className="px-4 py-2 text-left text-gray-500 dark:text-gray-400">Type</th>
                <th className="px-4 py-2 text-left text-gray-500 dark:text-gray-400">Operation</th>
                <th className="px-4 py-2 text-left text-gray-500 dark:text-gray-400">User</th>
                <th className="px-4 py-2 text-left text-gray-500 dark:text-gray-400">IP Address</th>
                <th className="px-4 py-2 text-left text-gray-500 dark:text-gray-400">Status</th>
                <th className="px-4 py-2 text-left text-gray-500 dark:text-gray-400">Processed</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {auditLogs.map((log) => (
                <tr key={log.id} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                  <td className="px-4 py-2 text-gray-900 dark:text-white whitespace-nowrap">
                    {formatDate(log.created_at)}
                  </td>
                  <td className="px-4 py-2 text-gray-500 dark:text-gray-400">
                    {log.log_type}
                  </td>
                  <td className="px-4 py-2 text-gray-900 dark:text-white">
                    {log.operation || 'N/A'}
                  </td>
                  <td className="px-4 py-2 text-gray-900 dark:text-white">
                    {log.user_email || log.user_id || 'N/A'}
                  </td>
                  <td className="px-4 py-2 text-gray-900 dark:text-white">
                    {log.ip_address || 'N/A'}
                  </td>
                  <td className="px-4 py-2">
                    <span className={`px-2 py-1 rounded text-xs ${
                      log.result_status === 'Success'
                        ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400'
                        : 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400'
                    }`}>
                      {log.result_status || 'N/A'}
                    </span>
                  </td>
                  <td className="px-4 py-2">
                    {log.processed ? (
                      <CheckCircle className="w-4 h-4 text-green-500" />
                    ) : (
                      <XCircle className="w-4 h-4 text-red-500" />
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Login Analytics View */}
      {activeView === 'login-analytics' && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 dark:bg-gray-700">
              <tr>
                <th className="px-4 py-2 text-left text-gray-500 dark:text-gray-400">Time</th>
                <th className="px-4 py-2 text-left text-gray-500 dark:text-gray-400">User</th>
                <th className="px-4 py-2 text-left text-gray-500 dark:text-gray-400">IP Address</th>
                <th className="px-4 py-2 text-left text-gray-500 dark:text-gray-400">Country</th>
                <th className="px-4 py-2 text-left text-gray-500 dark:text-gray-400">Result</th>
                <th className="px-4 py-2 text-left text-gray-500 dark:text-gray-400">Failure Reason</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {loginAnalytics.map((record) => (
                <tr key={record.id} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                  <td className="px-4 py-2 text-gray-900 dark:text-white whitespace-nowrap">
                    {formatDate(record.created_at)}
                  </td>
                  <td className="px-4 py-2 text-gray-900 dark:text-white">
                    {record.user_email || 'N/A'}
                  </td>
                  <td className="px-4 py-2 text-gray-900 dark:text-white">
                    {record.ip_address || 'N/A'}
                  </td>
                  <td className="px-4 py-2 text-gray-900 dark:text-white">
                    {record.country || 'N/A'}
                  </td>
                  <td className="px-4 py-2">
                    <span className={`px-2 py-1 rounded text-xs ${
                      record.is_success
                        ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400'
                        : 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400'
                    }`}>
                      {record.is_success ? 'Success' : 'Failed'}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-gray-500 dark:text-gray-400">
                    {record.failure_reason || '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}