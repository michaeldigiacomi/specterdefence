import { useState } from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import { PieChart as PieChartIcon, AlertTriangle } from 'lucide-react';
import clsx from 'clsx';

interface AnomalyBreakdownItem {
  type: string;
  count: number;
  percentage: number;
  avg_risk_score: number;
}

interface AnomalyBreakdownChartProps {
  data: AnomalyBreakdownItem[];
  isLoading?: boolean;
}

const formatAnomalyType = (type: string): string => {
  return type
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
};

const COLORS = [
  '#ef4444', // Red
  '#f97316', // Orange
  '#f59e0b', // Amber
  '#3b82f6', // Blue
  '#8b5cf6', // Violet
  '#ec4899', // Pink
  '#10b981', // Green
  '#6b7280', // Gray
];

export function AnomalyBreakdownChart({ data, isLoading = false }: AnomalyBreakdownChartProps) {
  const [activeIndex, setActiveIndex] = useState<number | null>(null);

  const totalCount = data.reduce((sum, item) => sum + item.count, 0);

  const chartData = data.map((item, index) => ({
    name: formatAnomalyType(item.type),
    value: item.count,
    percentage: item.percentage,
    avgRiskScore: item.avg_risk_score,
    type: item.type,
    color: COLORS[index % COLORS.length],
  }));

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
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <PieChartIcon className="w-5 h-5 text-amber-500" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Anomaly Types</h3>
        </div>
        <span className="text-sm text-gray-500 dark:text-gray-400">
          {totalCount.toLocaleString()} total
        </span>
      </div>

      {data.length > 0 ? (
        <div className="flex flex-col gap-6">
          {/* Pie Chart */}
          <div className="h-48 sm:h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={chartData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={80}
                  paddingAngle={2}
                  dataKey="value"
                  onMouseEnter={(_, index) => setActiveIndex(index)}
                  onMouseLeave={() => setActiveIndex(null)}
                >
                  {chartData.map((entry, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={entry.color}
                      stroke="none"
                      opacity={activeIndex === null || activeIndex === index ? 1 : 0.3}
                    />
                  ))}
                </Pie>
                <Tooltip
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      const data = payload[0].payload;
                      return (
                        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg p-3">
                          <p className="font-medium text-gray-900 dark:text-white mb-1">
                            {data.name}
                          </p>
                          <p className="text-sm text-gray-600 dark:text-gray-400">
                            Count: {data.value.toLocaleString()}
                          </p>
                          <p className="text-sm text-gray-600 dark:text-gray-400">
                            {data.percentage.toFixed(1)}% of total
                          </p>
                          <p className="text-sm text-gray-600 dark:text-gray-400">
                            Avg Risk: {data.avgRiskScore.toFixed(1)}
                          </p>
                        </div>
                      );
                    }
                    return null;
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>

          {/* Legend/List */}
          <div className="space-y-2 max-h-48 sm:max-h-64 overflow-y-auto">
            {chartData.map((item, index) => (
              <div
                key={item.type}
                className={clsx(
                  'flex items-center justify-between p-3 rounded-lg transition-colors cursor-pointer',
                  activeIndex === index
                    ? 'bg-gray-100 dark:bg-gray-700'
                    : 'hover:bg-gray-50 dark:hover:bg-gray-700/50'
                )}
                onMouseEnter={() => setActiveIndex(index)}
                onMouseLeave={() => setActiveIndex(null)}
              >
                <div className="flex items-center gap-3">
                  <span
                    className="w-3 h-3 rounded-full flex-shrink-0"
                    style={{ backgroundColor: item.color }}
                  />
                  <div>
                    <p className="text-sm font-medium text-gray-900 dark:text-white">{item.name}</p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      Avg risk: {item.avgRiskScore.toFixed(1)}
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-sm font-semibold text-gray-900 dark:text-white">
                    {item.value.toLocaleString()}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    {item.percentage.toFixed(1)}%
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="h-64 flex items-center justify-center">
          <div className="text-center">
            <AlertTriangle className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
            <p className="text-gray-500 dark:text-gray-400">No anomaly data available</p>
          </div>
        </div>
      )}
    </div>
  );
}
