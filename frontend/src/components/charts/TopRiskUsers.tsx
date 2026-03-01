import { useState } from 'react';
import { User, AlertTriangle, Globe, ChevronUp, ChevronDown, Mail } from 'lucide-react';
import { Link } from 'react-router-dom';
import clsx from 'clsx';

interface RiskUser {
  user_email: string;
  tenant_id: string;
  risk_score: number;
  anomaly_count: number;
  last_anomaly_time?: string;
  top_anomaly_types: string[];
  country_count: number;
}

interface TopRiskUsersProps {
  users: RiskUser[];
  totalUsers: number;
  avgRiskScore: number;
  isLoading?: boolean;
}

const formatAnomalyType = (type: string): string => {
  return type
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
};

const getRiskColor = (score: number): string => {
  if (score >= 70) return 'text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20';
  if (score >= 40) return 'text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20';
  return 'text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/20';
};

const getRiskBadgeColor = (score: number): string => {
  if (score >= 70) return 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300';
  if (score >= 40) return 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300';
  return 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300';
};

export function TopRiskUsers({
  users,
  totalUsers,
  avgRiskScore,
  isLoading = false,
}: TopRiskUsersProps) {
  const [sortBy, setSortBy] = useState<'risk' | 'anomalies' | 'last_seen'>('risk');
  const [sortDesc, setSortDesc] = useState(true);

  const sortedUsers = [...users].sort((a, b) => {
    let comparison = 0;
    switch (sortBy) {
      case 'risk':
        comparison = a.risk_score - b.risk_score;
        break;
      case 'anomalies':
        comparison = a.anomaly_count - b.anomaly_count;
        break;
      case 'last_seen':
        const aTime = a.last_anomaly_time ? new Date(a.last_anomaly_time).getTime() : 0;
        const bTime = b.last_anomaly_time ? new Date(b.last_anomaly_time).getTime() : 0;
        comparison = aTime - bTime;
        break;
    }
    return sortDesc ? -comparison : comparison;
  });

  const handleSort = (column: 'risk' | 'anomalies' | 'last_seen') => {
    if (sortBy === column) {
      setSortDesc(!sortDesc);
    } else {
      setSortBy(column);
      setSortDesc(true);
    }
  };

  if (isLoading) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
        <div className="animate-pulse">
          <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-1/3 mb-4"></div>
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="h-16 bg-gray-200 dark:bg-gray-700 rounded mb-2"></div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700">
      {/* Header */}
      <div className="p-6 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <User className="w-5 h-5 text-red-500" />
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              Top Risk Users
            </h3>
          </div>
          <div className="text-right">
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {totalUsers} users with anomalies
            </p>
            <p className="text-xs text-gray-400 dark:text-gray-500">
              Avg risk: {avgRiskScore.toFixed(1)}
            </p>
          </div>
        </div>
      </div>

      {/* Table Header */}
      <div className="grid grid-cols-12 gap-4 px-6 py-3 bg-gray-50 dark:bg-gray-900/50 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
        <div className="col-span-4">User</div>
        <button
          onClick={() => handleSort('risk')}
          className="col-span-2 flex items-center gap-1 hover:text-gray-700 dark:hover:text-gray-300"
        >
          Risk Score
          {sortBy === 'risk' && (
            sortDesc ? <ChevronDown className="w-3 h-3" /> : <ChevronUp className="w-3 h-3" />
          )}
        </button>
        <button
          onClick={() => handleSort('anomalies')}
          className="col-span-2 flex items-center gap-1 hover:text-gray-700 dark:hover:text-gray-300"
        >
          Anomalies
          {sortBy === 'anomalies' && (
            sortDesc ? <ChevronDown className="w-3 h-3" /> : <ChevronUp className="w-3 h-3" />
          )}
        </button>
        <div className="col-span-2">Types</div>
        <button
          onClick={() => handleSort('last_seen')}
          className="col-span-2 flex items-center gap-1 hover:text-gray-700 dark:hover:text-gray-300"
        >
          Last Seen
          {sortBy === 'last_seen' && (
            sortDesc ? <ChevronDown className="w-3 h-3" /> : <ChevronUp className="w-3 h-3" />
          )}
        </button>
      </div>

      {/* User List */}
      <div className="divide-y divide-gray-200 dark:divide-gray-700">
        {sortedUsers.length > 0 ? (
          sortedUsers.map((user) => (
            <Link
              key={user.user_email}
              to={`/analytics?user=${encodeURIComponent(user.user_email)}`}
              className="grid grid-cols-12 gap-4 px-6 py-4 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
            >
              {/* User Info */}
              <div className="col-span-4">
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-full bg-gray-100 dark:bg-gray-700 flex items-center justify-center flex-shrink-0">
                    <Mail className="w-4 h-4 text-gray-500 dark:text-gray-400" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                      {user.user_email}
                    </p>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className="text-xs text-gray-500 dark:text-gray-400 flex items-center gap-1">
                        <Globe className="w-3 h-3" />
                        {user.country_count} countries
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Risk Score */}
              <div className="col-span-2 flex items-center">
                <span
                  className={clsx(
                    'px-2 py-1 rounded-full text-sm font-semibold',
                    getRiskBadgeColor(user.risk_score)
                  )}
                >
                  {user.risk_score}
                </span>
              </div>

              {/* Anomaly Count */}
              <div className="col-span-2 flex items-center">
                <span className="text-sm text-gray-900 dark:text-white">
                  {user.anomaly_count}
                </span>
              </div>

              {/* Anomaly Types */}
              <div className="col-span-2">
                <div className="flex flex-wrap gap-1">
                  {user.top_anomaly_types.slice(0, 2).map((type) => (
                    <span
                      key={type}
                      className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300"
                    >
                      {formatAnomalyType(type)}
                    </span>
                  ))}
                  {user.top_anomaly_types.length > 2 && (
                    <span className="text-xs text-gray-500 dark:text-gray-400">
                      +{user.top_anomaly_types.length - 2}
                    </span>
                  )}
                </div>
              </div>

              {/* Last Seen */}
              <div className="col-span-2 flex items-center">
                <span className="text-sm text-gray-500 dark:text-gray-400">
                  {user.last_anomaly_time
                    ? new Date(user.last_anomaly_time).toLocaleDateString()
                    : 'Never'}
                </span>
              </div>
            </Link>
          ))
        ) : (
          <div className="px-6 py-12 text-center">
            <AlertTriangle className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
            <p className="text-gray-500 dark:text-gray-400">No risk users found</p>
          </div>
        )}
      </div>

      {/* Footer */}
      {users.length > 0 && (
        <div className="p-4 border-t border-gray-200 dark:border-gray-700 text-center">
          <Link
            to="/anomalies"
            className="text-sm text-primary-600 hover:text-primary-700 dark:text-primary-400 font-medium"
          >
            View all anomalies →
          </Link>
        </div>
      )}
    </div>
  );
}
