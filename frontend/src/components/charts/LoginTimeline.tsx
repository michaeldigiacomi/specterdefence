import { useState } from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from 'recharts';
import { format, parseISO } from 'date-fns';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import clsx from 'clsx';

interface LoginTimelineData {
  timestamp: string;
  successful_logins: number;
  failed_logins: number;
  total_logins: number;
}

interface LoginTimelineChartProps {
  data: LoginTimelineData[];
  changePercent: number;
  isLoading?: boolean;
  timeRange: '7d' | '30d' | '90d';
  onTimeRangeChange: (range: '7d' | '30d' | '90d') => void;
}

const timeRangeOptions = [
  { value: '7d', label: '7 Days' },
  { value: '30d', label: '30 Days' },
  { value: '90d', label: '90 Days' },
] as const;

export function LoginTimelineChart({
  data,
  changePercent,
  isLoading = false,
  timeRange,
  onTimeRangeChange,
}: LoginTimelineChartProps) {
  const [showFailed, setShowFailed] = useState(true);

  const formatXAxis = (timestamp: string) => {
    const date = parseISO(timestamp);
    if (timeRange === '7d') {
      return format(date, 'HH:mm');
    } else if (timeRange === '30d') {
      return format(date, 'MMM d');
    } else {
      return format(date, 'MMM d');
    }
  };

  const formatTooltipDate = (timestamp: string) => {
    const date = parseISO(timestamp);
    return format(date, 'PPp');
  };

  const totalSuccessful = data.reduce((sum, d) => sum + d.successful_logins, 0);
  const totalFailed = data.reduce((sum, d) => sum + d.failed_logins, 0);

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
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            Login Activity
          </h3>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-sm text-gray-500 dark:text-gray-400">
              {totalSuccessful.toLocaleString()} successful, {totalFailed.toLocaleString()} failed
            </span>
            {changePercent !== 0 && (
              <span
                className={clsx(
                  'inline-flex items-center gap-1 text-xs font-medium',
                  changePercent > 0
                    ? 'text-green-600 dark:text-green-400'
                    : changePercent < 0
                    ? 'text-red-600 dark:text-red-400'
                    : 'text-gray-500 dark:text-gray-400'
                )}
              >
                {changePercent > 0 ? (
                  <TrendingUp className="w-3 h-3" />
                ) : changePercent < 0 ? (
                  <TrendingDown className="w-3 h-3" />
                ) : (
                  <Minus className="w-3 h-3" />
                )}
                {Math.abs(changePercent)}% vs previous period
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

      {/* Legend Toggle */}
      <div className="flex items-center gap-4 mb-4">
        <button
          onClick={() => setShowFailed(!showFailed)}
          className="flex items-center gap-2 text-sm"
        >
          <span className="w-3 h-3 rounded-full bg-primary-500"></span>
          <span className="text-gray-700 dark:text-gray-300">Successful</span>
        </button>
        <button
          onClick={() => setShowFailed(!showFailed)}
          className={clsx(
            'flex items-center gap-2 text-sm transition-opacity',
            showFailed ? 'opacity-100' : 'opacity-50'
          )}
        >
          <span className="w-3 h-3 rounded-full bg-red-500"></span>
          <span className="text-gray-700 dark:text-gray-300">Failed</span>
        </button>
      </div>

      {/* Chart */}
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 5, right: 5, left: 0, bottom: 5 }}>
            <defs>
              <linearGradient id="colorSuccess" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="colorFailed" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
              </linearGradient>
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
                        {formatTooltipDate(label as string)}
                      </p>
                      {payload.map((entry, index) => (
                        <p
                          key={index}
                          className="text-sm font-medium"
                          style={{ color: entry.color }}
                        >
                          {entry.name}: {entry.value?.toLocaleString()}
                        </p>
                      ))}
                    </div>
                  );
                }
                return null;
              }}
            />
            <Area
              type="monotone"
              dataKey="successful_logins"
              name="Successful"
              stroke="#3b82f6"
              strokeWidth={2}
              fillOpacity={1}
              fill="url(#colorSuccess)"
            />
            {showFailed && (
              <Area
                type="monotone"
                dataKey="failed_logins"
                name="Failed"
                stroke="#ef4444"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#colorFailed)"
              />
            )}
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
