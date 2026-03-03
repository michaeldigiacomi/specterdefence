import { useState } from 'react';
import {

  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  Line,
  ComposedChart
} from 'recharts';
import { format, parseISO } from 'date-fns';
import { TrendingUp, TrendingDown, Minus, AlertTriangle } from 'lucide-react';
import clsx from 'clsx';

interface AnomalyTrendPoint {
  date: string;
  count: number;
  types: Record<string, number>;
}

interface AnomalyTrendChartProps {
  data: AnomalyTrendPoint[];
  totalAnomalies: number;
  topType?: string;
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

const anomalyTypeColors: Record<string, string> = {
  impossible_travel: '#ef4444',
  new_country: '#f59e0b',
  new_ip: '#3b82f6',
  failed_login: '#6b7280',
  multiple_failures: '#8b5cf6',
  suspicious_location: '#ec4899',
  default: '#9ca3af',
};

const formatAnomalyType = (type: string): string => {
  return type
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
};

export function AnomalyTrendChart({
  data,
  totalAnomalies,
  topType,
  changePercent,
  isLoading = false,
  timeRange,
  onTimeRangeChange,
}: AnomalyTrendChartProps) {
  const [selectedTypes, setSelectedTypes] = useState<Set<string>>(new Set());

  // Get all unique anomaly types
  const allTypes = new Set<string>();
  data.forEach(point => {
    Object.keys(point.types).forEach(type => allTypes.add(type));
  });

  const typesList = Array.from(allTypes);

  // Prepare data for stacked bar chart
  const chartData = data.map(point => ({
    date: point.date,
    total: point.count,
    ...point.types,
  }));

  const formatXAxis = (date: string) => {
    const d = parseISO(date);
    if (timeRange === '7d') {
      return format(d, 'EEE');
    } else if (timeRange === '30d') {
      return format(d, 'MMM d');
    } else {
      return format(d, 'MMM d');
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
            <AlertTriangle className="w-5 h-5 text-amber-500" />
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              Anomaly Trends
            </h3>
          </div>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-sm text-gray-500 dark:text-gray-400">
              {totalAnomalies.toLocaleString()} total anomalies
            </span>
            {topType && (
              <span className="text-xs text-gray-500 dark:text-gray-400">
                • Top: {formatAnomalyType(topType)}
              </span>
            )}
            {changePercent !== 0 && (
              <span
                className={clsx(
                  'inline-flex items-center gap-1 text-xs font-medium',
                  changePercent > 0
                    ? 'text-red-600 dark:text-red-400'
                    : changePercent < 0
                    ? 'text-green-600 dark:text-green-400'
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

      {/* Type Legend */}
      {typesList.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-4">
          {typesList.map((type) => (
            <button
              key={type}
              onClick={() => {
                const newSelected = new Set(selectedTypes);
                if (newSelected.has(type)) {
                  newSelected.delete(type);
                } else {
                  newSelected.add(type);
                }
                setSelectedTypes(newSelected);
              }}
              className={clsx(
                'flex items-center gap-1 px-2 py-1 text-xs rounded-full transition-opacity',
                selectedTypes.has(type)
                  ? 'opacity-40'
                  : 'opacity-100'
              )}
              style={{
                backgroundColor: `${anomalyTypeColors[type] || anomalyTypeColors.default}20`,
                color: anomalyTypeColors[type] || anomalyTypeColors.default,
              }}
            >
              <span
                className="w-2 h-2 rounded-full"
                style={{ backgroundColor: anomalyTypeColors[type] || anomalyTypeColors.default }}
              />
              {formatAnomalyType(type)}
            </button>
          ))}
        </div>
      )}

      {/* Chart */}
      <div className="h-64">
        {chartData.length > 0 ? (
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={chartData} margin={{ top: 5, right: 5, left: 0, bottom: 5 }}>
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="currentColor"
                className="text-gray-200 dark:text-gray-700"
                vertical={false}
              />
              <XAxis
                dataKey="date"
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
                        <p className="text-sm font-medium text-gray-900 dark:text-white mb-2">
                          {format(parseISO(label as string), 'PPP')}
                        </p>
                        {payload.map((entry, index) => {
                          if (entry.dataKey === 'date' || entry.dataKey === 'total') return null;
                          return (
                            <p
                              key={index}
                              className="text-sm"
                              style={{ color: entry.color }}
                            >
                              {formatAnomalyType(entry.dataKey as string)}: {entry.value}
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
              <Legend />
              
              {/* Total line */}
              <Line
                type="monotone"
                dataKey="total"
                name="Total"
                stroke="#6b7280"
                strokeWidth={2}
                dot={false}
                strokeDasharray="5 5"
              />

              {/* Stacked bars for each type */}
              {typesList.map((type) => (
                <Bar
                  key={type}
                  dataKey={type}
                  name={formatAnomalyType(type)}
                  stackId="anomalies"
                  fill={anomalyTypeColors[type] || anomalyTypeColors.default}
                  hide={selectedTypes.has(type)}
                />
              ))}
            </ComposedChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-full flex items-center justify-center">
            <div className="text-center">
              <AlertTriangle className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
              <p className="text-gray-500 dark:text-gray-400">No anomaly data available</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
