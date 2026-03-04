import { useState } from 'react';
import { Search, Filter, X, Download, Calendar } from 'lucide-react';
import { LoginFilters } from '@/types';
import { useTenants } from '@/hooks/useApi';

interface FilterPanelProps {
  filters: LoginFilters;
  onChange: (filters: LoginFilters) => void;
  onExport?: () => void;
  showExport?: boolean;
  compact?: boolean;
}

export default function FilterPanel({
  filters,
  onChange,
  onExport,
  showExport = false,
  compact = false
}: FilterPanelProps) {
  const { data: tenantsData } = useTenants();
  const [isExpanded, setIsExpanded] = useState(!compact);

  const handleChange = (key: keyof LoginFilters, value: unknown) => {
    onChange({ ...filters, [key]: value });
  };

  const clearFilters = () => {
    onChange({});
  };

  const hasFilters = Object.keys(filters).some(k => k !== 'page' && k !== 'page_size' && filters[k as keyof LoginFilters] !== undefined);

  if (compact) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search by user, IP, or country..."
              value={filters.user || filters.ip || filters.country || ''}
              onChange={(e) => handleChange('user', e.target.value || undefined)}
              className="w-full pl-9 pr-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 dark:text-white"
            />
          </div>

          <select
            value={filters.tenant_id || ''}
            onChange={(e) => handleChange('tenant_id', e.target.value || undefined)}
            className="px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 dark:text-white"
          >
            <option value="">All Tenants</option>
            {tenantsData?.items.map((tenant) => (
              <option key={tenant.id} value={tenant.id}>{tenant.name}</option>
            ))}
          </select>

          <select
            value={filters.status || ''}
            onChange={(e) => handleChange('status', e.target.value || undefined)}
            className="px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 dark:text-white"
          >
            <option value="">All Status</option>
            <option value="success">Success</option>
            <option value="failed">Failed</option>
          </select>

          <select
            value={filters.has_anomaly ? 'true' : ''}
            onChange={(e) => handleChange('has_anomaly', e.target.value === 'true' ? true : undefined)}
            className="px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 dark:text-white"
          >
            <option value="">All Logins</option>
            <option value="true">With Anomalies</option>
          </select>

          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="flex items-center gap-2 px-3 py-2 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
          >
            <Filter className="w-4 h-4" />
            {isExpanded ? 'Less' : 'More'}
          </button>

          {hasFilters && (
            <button
              onClick={clearFilters}
              className="flex items-center gap-1 px-3 py-2 text-sm text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg"
            >
              <X className="w-4 h-4" />
              Clear
            </button>
          )}

          {showExport && onExport && (
            <button
              onClick={onExport}
              className="flex items-center gap-2 px-3 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 text-sm"
            >
              <Download className="w-4 h-4" />
              Export
            </button>
          )}
        </div>

        {isExpanded && (
          <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">From Date</label>
              <div className="relative">
                <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="datetime-local"
                  value={filters.start_time || ''}
                  onChange={(e) => handleChange('start_time', e.target.value || undefined)}
                  className="w-full pl-9 pr-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 dark:text-white"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">To Date</label>
              <div className="relative">
                <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="datetime-local"
                  value={filters.end_time || ''}
                  onChange={(e) => handleChange('end_time', e.target.value || undefined)}
                  className="w-full pl-9 pr-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 dark:text-white"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Country Code</label>
              <input
                type="text"
                placeholder="e.g. US, UK"
                maxLength={2}
                value={filters.country_code || ''}
                onChange={(e) => handleChange('country_code', e.target.value.toUpperCase() || undefined)}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 dark:text-white"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Min Risk Score</label>
              <input
                type="number"
                min={0}
                max={100}
                placeholder="0-100"
                value={filters.min_risk_score || ''}
                onChange={(e) => handleChange('min_risk_score', e.target.value ? parseInt(e.target.value) : undefined)}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 dark:text-white"
              />
            </div>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
          <Filter className="w-5 h-5 text-primary-500" />
          Filters
        </h3>
        {hasFilters && (
          <button
            onClick={clearFilters}
            className="flex items-center gap-1 px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg"
          >
            <X className="w-4 h-4" />
            Clear All
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Search</label>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="User email, IP, or country"
              value={filters.user || filters.ip || filters.country || ''}
              onChange={(e) => handleChange('user', e.target.value || undefined)}
              className="w-full pl-9 pr-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 dark:text-white"
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Tenant</label>
          <select
            value={filters.tenant_id || ''}
            onChange={(e) => handleChange('tenant_id', e.target.value || undefined)}
            className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 dark:text-white"
          >
            <option value="">All Tenants</option>
            {tenantsData?.items.map((tenant) => (
              <option key={tenant.id} value={tenant.id}>{tenant.name}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Status</label>
          <select
            value={filters.status || ''}
            onChange={(e) => handleChange('status', e.target.value || undefined)}
            className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 dark:text-white"
          >
            <option value="">All Status</option>
            <option value="success">Success</option>
            <option value="failed">Failed</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">From Date</label>
          <input
            type="datetime-local"
            value={filters.start_time || ''}
            onChange={(e) => handleChange('start_time', e.target.value || undefined)}
            className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 dark:text-white"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">To Date</label>
          <input
            type="datetime-local"
            value={filters.end_time || ''}
            onChange={(e) => handleChange('end_time', e.target.value || undefined)}
            className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 dark:text-white"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Min Risk Score</label>
          <input
            type="number"
            min={0}
            max={100}
            placeholder="0-100"
            value={filters.min_risk_score || ''}
            onChange={(e) => handleChange('min_risk_score', e.target.value ? parseInt(e.target.value) : undefined)}
            className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 dark:text-white"
          />
        </div>
      </div>

      {showExport && onExport && (
        <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
          <button
            onClick={onExport}
            className="flex items-center gap-2 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600"
          >
            <Download className="w-4 h-4" />
            Export to CSV
          </button>
        </div>
      )}
    </div>
  );
}
