import { useState } from 'react';
import { format, parseISO } from 'date-fns';
import {
  CheckCircle,
  XCircle,
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
  MapPin,
  Globe,
} from 'lucide-react';
import { LoginRecord } from '@/types';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface LoginTimelineProps {
  logins: LoginRecord[];
  total: number;
  page: number;
  pageSize: number;
  onPageChange: (page: number) => void;
  loading?: boolean;
}

export default function LoginTimeline({
  logins,
  total,
  page,
  pageSize,
  onPageChange,
  loading = false,
}: LoginTimelineProps) {
  const [expandedLogin, setExpandedLogin] = useState<string | null>(null);

  const totalPages = Math.ceil(total / pageSize);

  const toggleExpand = (id: string) => {
    setExpandedLogin(expandedLogin === id ? null : id);
  };

  if (loading) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="p-4 animate-pulse">
          {[1, 2, 3, 4, 5].map(i => (
            <div
              key={i}
              className="flex items-center gap-4 py-4 border-b border-gray-200 dark:border-gray-700 last:border-0"
            >
              <div className="w-10 h-10 bg-gray-200 dark:bg-gray-700 rounded-full"></div>
              <div className="flex-1">
                <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/4 mb-2"></div>
                <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-1/2"></div>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (logins.length === 0) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-12 text-center">
        <div className="w-16 h-16 bg-gray-100 dark:bg-gray-700 rounded-full flex items-center justify-center mx-auto mb-4">
          <Globe className="w-8 h-8 text-gray-400" />
        </div>
        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-1">No logins found</h3>
        <p className="text-gray-500 dark:text-gray-400">
          Try adjusting your filters to see more results.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Showing {(page - 1) * pageSize + 1} - {Math.min(page * pageSize, total)} of {total}{' '}
          results
        </p>
      </div>

      <div className="divide-y divide-gray-200 dark:divide-gray-700">
        {logins.map(login => (
          <div key={login.id} className="group">
            <div
              onClick={() => toggleExpand(login.id)}
              className="px-6 py-4 hover:bg-gray-50 dark:hover:bg-gray-700/50 cursor-pointer transition-colors"
            >
              <div className="flex items-start gap-4">
                <div
                  className={cn(
                    'w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0',
                    login.is_success
                      ? 'bg-green-100 text-green-600 dark:bg-green-900/20 dark:text-green-400'
                      : 'bg-red-100 text-red-600 dark:bg-red-900/20 dark:text-red-400'
                  )}
                >
                  {login.is_success ? (
                    <CheckCircle className="w-5 h-5" />
                  ) : (
                    <XCircle className="w-5 h-5" />
                  )}
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-medium text-gray-900 dark:text-white truncate">
                      {login.user_email}
                    </span>

                    {login.anomaly_flags.length > 0 && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-amber-100 text-amber-700 dark:bg-amber-900/20 dark:text-amber-400 text-xs rounded-full">
                        <AlertTriangle className="w-3 h-3" />
                        {login.anomaly_flags.length} anomaly
                        {login.anomaly_flags.length > 1 ? 'ies' : 'y'}
                      </span>
                    )}
                  </div>

                  <div className="mt-1 flex items-center gap-4 text-sm text-gray-500 dark:text-gray-400 flex-wrap">
                    <span>{format(parseISO(login.login_time), 'MMM d, yyyy HH:mm')}</span>
                    <span className="hidden sm:inline">•</span>
                    <span className="flex items-center gap-1">
                      <MapPin className="w-3 h-3" />
                      {login.city && login.country
                        ? `${login.city}, ${login.country}`
                        : login.country
                          ? login.country
                          : 'Unknown location'}
                    </span>
                    <span className="hidden sm:inline">•</span>
                    <span
                      className={
                        login.is_malicious ? 'text-red-600 dark:text-red-400 font-medium' : ''
                      }
                    >
                      {login.ip_address}
                    </span>
                    {login.is_malicious && (
                      <span className="ml-1 text-red-500" title="Known malicious IP">
                        ⚠️
                      </span>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <span
                    className={cn(
                      'px-2 py-1 text-xs font-medium rounded',
                      login.risk_score >= 80
                        ? 'bg-red-100 text-red-700 dark:bg-red-900/20 dark:text-red-400'
                        : login.risk_score >= 60
                          ? 'bg-orange-100 text-orange-700 dark:bg-orange-900/20 dark:text-orange-400'
                          : login.risk_score >= 40
                            ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/20 dark:text-amber-400'
                            : 'bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-400'
                    )}
                  >
                    Risk: {login.risk_score}
                  </span>
                </div>
              </div>

              {expandedLogin === login.id && (
                <div className="mt-4 pl-14 pt-4 border-t border-gray-200 dark:border-gray-700">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
                    <div>
                      <p className="text-gray-500 dark:text-gray-400">IP Address</p>
                      <p className="font-medium text-gray-900 dark:text-white">
                        {login.ip_address}
                      </p>
                    </div>

                    <div>
                      <p className="text-gray-500 dark:text-gray-400">Login Time</p>
                      <p className="font-medium text-gray-900 dark:text-white">
                        {format(parseISO(login.login_time), 'PPpp')}
                      </p>
                    </div>

                    <div>
                      <p className="text-gray-500 dark:text-gray-400">Country</p>
                      <p className="font-medium text-gray-900 dark:text-white">
                        {login.country || 'Unknown'} ({login.country_code || 'N/A'})
                      </p>
                    </div>

                    <div>
                      <p className="text-gray-500 dark:text-gray-400">Region</p>
                      <p className="font-medium text-gray-900 dark:text-white">
                        {login.region || 'Unknown'}
                      </p>
                    </div>

                    <div>
                      <p className="text-gray-500 dark:text-gray-400">Status</p>
                      <p
                        className={cn(
                          'font-medium',
                          login.is_success
                            ? 'text-green-600 dark:text-green-400'
                            : 'text-red-600 dark:text-red-400'
                        )}
                      >
                        {login.is_success ? 'Success' : 'Failed'}
                        {login.failure_reason && ` - ${login.failure_reason}`}
                      </p>
                    </div>

                    <div>
                      <p className="text-gray-500 dark:text-gray-400">Coordinates</p>
                      <p className="font-medium text-gray-900 dark:text-white">
                        {login.latitude && login.longitude
                          ? `${login.latitude.toFixed(4)}, ${login.longitude.toFixed(4)}`
                          : 'Unknown'}
                      </p>
                    </div>

                    {login.anomaly_flags.length > 0 && (
                      <div className="sm:col-span-2">
                        <p className="text-gray-500 dark:text-gray-400 mb-2">Detected Anomalies</p>
                        <div className="flex flex-wrap gap-2">
                          {login.anomaly_flags.map((flag, idx) => (
                            <span
                              key={idx}
                              className="px-2 py-1 bg-amber-100 text-amber-700 dark:bg-amber-900/20 dark:text-amber-400 text-xs rounded"
                            >
                              {flag}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Threat Intelligence */}
                    {(login.is_malicious ||
                      login.threat_score > 0 ||
                      login.threat_tags.length > 0) && (
                      <div className="sm:col-span-2">
                        <p className="text-gray-500 dark:text-gray-400 mb-2">Threat Intelligence</p>
                        <div className="flex flex-wrap gap-2 items-center">
                          {login.is_malicious && (
                            <span className="px-2 py-1 bg-red-100 text-red-700 dark:bg-red-900/20 dark:text-red-400 text-xs rounded font-medium">
                              ⚠️ Malicious IP
                            </span>
                          )}
                          {login.threat_score > 0 && (
                            <span
                              className={cn(
                                'px-2 py-1 text-xs rounded font-medium',
                                login.threat_score >= 80
                                  ? 'bg-red-100 text-red-700 dark:bg-red-900/20 dark:text-red-400'
                                  : login.threat_score >= 60
                                    ? 'bg-orange-100 text-orange-700 dark:bg-orange-900/20 dark:text-orange-400'
                                    : 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/20 dark:text-yellow-400'
                              )}
                            >
                              Threat Score: {login.threat_score}
                            </span>
                          )}
                          {login.threat_tags.map((tag, idx) => (
                            <span
                              key={idx}
                              className="px-2 py-1 bg-purple-100 text-purple-700 dark:bg-purple-900/20 dark:text-purple-400 text-xs rounded"
                            >
                              {tag}
                            </span>
                          ))}
                          {login.threat_sources.length > 0 && (
                            <span className="text-xs text-gray-500 dark:text-gray-400">
                              via {login.threat_sources.join(', ')}
                            </span>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {totalPages > 1 && (
        <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-700 flex items-center justify-between">
          <button
            onClick={() => onPageChange(page - 1)}
            disabled={page <= 1}
            className="flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <ChevronLeft className="w-4 h-4" />
            Previous
          </button>

          <div className="flex items-center gap-1">
            {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
              const pageNum = i + 1;
              return (
                <button
                  key={pageNum}
                  onClick={() => onPageChange(pageNum)}
                  className={cn(
                    'w-8 h-8 rounded-lg text-sm font-medium',
                    page === pageNum
                      ? 'bg-primary-500 text-white'
                      : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
                  )}
                >
                  {pageNum}
                </button>
              );
            })}
            {totalPages > 5 && <span className="text-gray-400">... {totalPages}</span>}
          </div>

          <button
            onClick={() => onPageChange(page + 1)}
            disabled={page >= totalPages}
            className="flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Next
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  );
}
