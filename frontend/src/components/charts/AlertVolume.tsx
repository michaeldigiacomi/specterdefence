import { useState } from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { format, parseISO } from 'date-fns';
import { Bell } from 'lucide-react';
import clsx from 'clsx';

interface AlertVolumePoint {
  timestamp: string;
  critical: number;
  high: number;
  medium: number;
  low: number;
  total: number;
}

interface AlertVolumeChartProps {
  data: AlertVolumePoint[];
  totalBySeverity: Record<string, number>;
  peakVolume: number;
  isLoading?: boolean;
  timeRange: '7d' | '30d' | '90d';
  onTimeRangeChange: (range: '7d' | '30d' | '90d') => void;
}

const timeRangeOptions = [
  { value: '7d', label: '7 Days' },
  { value: '30d', label: '30 Days' },
  { value: '90d', label: '90 Days' },
] as const;

const severityConfig = {
  critical: { color: '#ef4444', label: 'Critical' },
  high: { color: '#f97316', label: 'High' },
  medium: { color: '#f59e0b', label: 'Medium' },
  low: { color: '#3b82f6', label: 'Low' },
};

export function AlertVolumeChart({
  data,
  totalBySeverity,
  peakVolume,
  isLoading = false,
  timeRange,
  onTimeRangeChange,
}: AlertVolumeChartProps) {
  const [hiddenSeverities, setHiddenSeverities] = useState<Set<string>>(new Set());

  const toggleSeverity = (severity: string) => {
    const newHidden = new Set(hiddenSeverities);
    if (newHidden.has(severity)) {
      newHidden.delete(severity);
    } else {
      newHidden.add(severity);
    }
    setHiddenSeverities(newHidden);
  };

  const totalAlerts = Object.values(totalBySeverity).reduce((a, b) => a + b, 0);

  const formatXAxis = (timestamp: string) => {
    const date = parseISO(timestamp);
    if (timeRange === '7d') {
      return format(date, 'EEE');
    } else {
      return format(date, 'MMM d');
    }
  };

  if (isLoading) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
        <div className="animate-pulse">
          <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-1/3 mb-4"></div>
          <div className="h-64 bg-gray-200 dark:bg-gray-700 rounded"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div>
          <div className="flex items-center gap-2">
            <Bell className="w-5 h-5 text-primary-500" />
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              Alert Volume
            </h3>
          </div>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-sm text-gray-500 dark:text-gray-400">
              {totalAlerts.toLocaleString()} total alerts
            </span>
            {peakVolume > 0 && (
              <span className="text-xs text-gray-500 dark:text-gray-400">
                • Peak: {peakVolume} alerts
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Time Range Selector */}
          <div className="flex bg-gray-100 dark:bg-gray-700 rounded-lg p-1">
            {timeRangeOptions.map((option) => (
              <button
                key={option.value}
                onClick={() => onTimeRangeChange(option.value)}
                className={clsx(
                  'px-3 py-1 text-sm font-medium rounded-md transition-colors',
                  timeRange === option.value
                    ? 'bg-white dark:bg-gray-600 text-gray-900 dark:text-white shadow-sm'
                    : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
                )}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Severity Stats */}
      <div className="grid grid-cols-4 gap-2 mb-4">
        {Object.entries(severityConfig).map(([severity, config]) => {
          const count = totalBySeverity[severity.toUpperCase()] || 0;
          const percentage = totalAlerts > 0 ? (count / totalAlerts) * 100 : 0;
          
          return (
            <button
              key={severity}
              onClick={() => toggleSeverity(severity)}
              className={clsx(
                'p-2 rounded-lg text-left transition-opacity',
                hiddenSeverities.has(severity) ? 'opacity-40' : 'opacity-100'
              )}
              style={{ backgroundColor: `${config.color}15` }}
            >
              <div className="flex items-center gap-1.5">
                <span
                  className="w-2 h-2 rounded-full"
                  style={{ backgroundColor: config.color }}
                />
                <span className="text-xs font-medium text-gray-600 dark:text-gray-400">
                  {config.label}
                </span>
              </div>
              <p className="text-lg font-bold mt-1" style={{ color: config.color }}>
                {count.toLocaleString()}
              </p>
              <p className="text-xs text-gray-500">{percentage.toFixed(1)}%</p>
            </button>
          );
        })}
      </div>

      {/* Chart */}
      <div className="h-56">
        {data.length > 0 ? (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 5, right: 5, left: 0, bottom: 5 }}>
              <defs>
                {Object.entries(severityConfig).map(([severity, config]) => (
                  <linearGradient
                    key={severity}
                    id={`color${severity}`}
                    x1="0"
                    y1="0"
                    x2="0"
                    y2="1"
                  >
                    <stop offset="5%" stopColor={config.color} stopOpacity={0.4} />
                    <stop offset="95%" stopColor={config.color} stopOpacity={0} />
                  </linearGradient>
                ))}
              </defs>
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="currentColor"
                className="text-gray-200 dark:text-gray-700"
                vertical={false}
              />
              <XAxis
                dataKey="timestamp"
                tickFormatter={formatXAxis}
                stroke="currentColor"
                className="text-gray-400 dark:text-gray-500"
                tick={{ fontSize: 12 }}
                minTickGap={30}
              />
              <YAxis
                stroke="currentColor"
                className="text-gray-400 dark:text-gray-500"
                tick={{ fontSize: 12 }}
                allowDecimals={false}
              />
              <Tooltip
                content={({ active, payload, label }) => {
                  if (active && payload && payload.length) {
                    return (
                      <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg p-3">
                        <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">
                          {format(parseISO(label as string), 'PPP')}
                        </p>
                        {payload.map((entry, index) => {
                          if (entry.dataKey === 'timestamp' || entry.dataKey === 'total') return null;
                          const config = severityConfig[entry.dataKey as keyof typeof severityConfig];
                          return (
                            <p
                              key={index}
                              className="text-sm font-medium"
                              style={{ color: config?.color }}
                            >
                              {config?.label}: {entry.value}
                            </p>
                          );
                        })}
                        <div className="border-t border-gray-200 dark:border-gray-700 mt-2 pt-2">
                          <p className="text-sm font-semibold text-gray-900 dark:text-white">
                            Total: {payload.find(p => p.dataKey === 'total')?.value}
                          </p>
                        </div>
                      </div>
                    );
                  }
                  return null;
                }}
              />
              
              {Object.entries(severityConfig).map(([severity, config]) => (
                !hiddenSeverities.has(severity) && (
                  <Area
                    key={severity}
                    type="monotone"
                    dataKey={severity}
                    name={config.label}
                    stroke={config.color}
                    strokeWidth={2}
                    fillOpacity={1}
                    fill={`url(#color${severity})`}
                    stackId="1"
                  />
                )
              ))}
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-full flex items-center justify-center">
            <div className="text-center">
              <Bell className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
              <p className="text-gray-500 dark:text-gray-400">No alert data available</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
