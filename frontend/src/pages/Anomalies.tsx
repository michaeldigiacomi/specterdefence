import { useState } from 'react';
import { AlertTriangle, Filter, Shield, MapPin, Clock, Flame } from 'lucide-react';
import AnomalyCard from '@/components/AnomalyCard';
import { useRecentAnomalies, useTenants } from '@/hooks/useApi';
import { AlertFilters, EventType, SeverityLevel } from '@/types';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const eventTypeFilters: { value: EventType; label: string; icon: React.ElementType }[] = [
  { value: 'impossible_travel', label: 'Impossible Travel', icon: MapPin },
  { value: 'new_country', label: 'New Country', icon: MapPin },
  { value: 'brute_force', label: 'Brute Force', icon: Shield },
  { value: 'multiple_failures', label: 'Multiple Failures', icon: Clock },
  { value: 'suspicious_location', label: 'Suspicious Location', icon: AlertTriangle },
];

const severityFilters: { value: SeverityLevel; label: string; color: string }[] = [
  { value: 'CRITICAL', label: 'Critical', color: 'bg-red-500' },
  { value: 'HIGH', label: 'High', color: 'bg-orange-500' },
  { value: 'MEDIUM', label: 'Medium', color: 'bg-amber-500' },
  { value: 'LOW', label: 'Low', color: 'bg-blue-500' },
];

export default function Anomalies() {
  const [filters, setFilters] = useState<AlertFilters>({
    hours: 24,
    limit: 50,
  });
  const [selectedTypes, setSelectedTypes] = useState<EventType[]>([]);
  const [selectedSeverities, setSelectedSeverities] = useState<SeverityLevel[]>([]);

  const { data: anomalies, isLoading } = useRecentAnomalies(filters);
  const { data: tenantsData } = useTenants();

  const toggleType = (type: EventType) => {
    setSelectedTypes(prev =>
      prev.includes(type)
        ? prev.filter(t => t !== type)
        : [...prev, type]
    );
  };

  const toggleSeverity = (severity: SeverityLevel) => {
    setSelectedSeverities(prev =>
      prev.includes(severity)
        ? prev.filter(s => s !== severity)
        : [...prev, severity]
    );
  };

  // Filter anomalies client-side
  const filteredAnomalies = anomalies?.filter(anomaly => {
    const matchesType = selectedTypes.length === 0 || selectedTypes.some(t =>
      anomaly.type.toLowerCase().includes(t.toLowerCase())
    );
    const matchesSeverity = selectedSeverities.length === 0 || selectedSeverities.some(s => {
      if (s === 'CRITICAL') return anomaly.risk_score >= 80;
      if (s === 'HIGH') return anomaly.risk_score >= 60 && anomaly.risk_score < 80;
      if (s === 'MEDIUM') return anomaly.risk_score >= 40 && anomaly.risk_score < 60;
      return anomaly.risk_score < 40;
    });
    return matchesType && matchesSeverity;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <AlertTriangle className="w-6 h-6 text-amber-500" />
            Anomalies
          </h1>
          <p className="mt-1 text-gray-500 dark:text-gray-400">
            Review detected security anomalies and potential threats
          </p>
        </div>

        <div className="flex items-center gap-2">
          <select
            value={filters.hours}
            onChange={(e) => setFilters({ ...filters, hours: parseInt(e.target.value) })}
            className="px-3 py-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 dark:text-white"
          >
            <option value={1}>Last Hour</option>
            <option value={24}>Last 24 Hours</option>
            <option value={168}>Last 7 Days</option>
          </select>

          <select
            value={filters.tenant_id || ''}
            onChange={(e) => setFilters({ ...filters, tenant_id: e.target.value || undefined })}
            className="px-3 py-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 dark:text-white"
          >
            <option value="">All Tenants</option>
            {tenantsData?.items.map((tenant) => (
              <option key={tenant.id} value={tenant.id}>{tenant.name}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
        <div className="flex items-center gap-2 mb-3">
          <Filter className="w-4 h-4 text-gray-500" />
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Filter by Type</span>
        </div>

        <div className="flex flex-wrap gap-2">
          {eventTypeFilters.map(({ value, label, icon: Icon }) => (
            <button
              key={value}
              onClick={() => toggleType(value)}
              className={cn(
                'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm transition-colors',
                selectedTypes.includes(value)
                  ? 'bg-primary-100 text-primary-700 dark:bg-primary-900/20 dark:text-primary-400'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-400 dark:hover:bg-gray-600'
              )}
            >
              <Icon className="w-4 h-4" />
              {label}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2 mt-4 mb-3">
          <Flame className="w-4 h-4 text-gray-500" />
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Filter by Severity</span>
        </div>

        <div className="flex flex-wrap gap-2">
          {severityFilters.map(({ value, label, color }) => (
            <button
              key={value}
              onClick={() => toggleSeverity(value)}
              className={cn(
                'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm transition-colors',
                selectedSeverities.includes(value)
                  ? 'bg-gray-200 text-gray-900 dark:bg-gray-600 dark:text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-400 dark:hover:bg-gray-600'
              )}
            >
              <span className={cn('w-2 h-2 rounded-full', color)} />
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Stats Summary */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
          <p className="text-sm text-gray-500 dark:text-gray-400">Total Anomalies</p>
          <p className="text-2xl font-bold text-gray-900 dark:text-white">{filteredAnomalies?.length || 0}</p>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
          <p className="text-sm text-gray-500 dark:text-gray-400">Critical</p>
          <p className="text-2xl font-bold text-red-600">
            {filteredAnomalies?.filter(a => a.risk_score >= 80).length || 0}
          </p>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
          <p className="text-sm text-gray-500 dark:text-gray-400">High Risk</p>
          <p className="text-2xl font-bold text-orange-600">
            {filteredAnomalies?.filter(a => a.risk_score >= 60 && a.risk_score < 80).length || 0}
          </p>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
          <p className="text-sm text-gray-500 dark:text-gray-400">Impossible Travel</p>
          <p className="text-2xl font-bold text-primary-600">
            {filteredAnomalies?.filter(a => a.type === 'impossible_travel').length || 0}
          </p>
        </div>
      </div>

      {/* Anomalies List */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Detected Anomalies
        </h2>

        <div className="space-y-4">
          {isLoading ? (
            [1, 2, 3, 4].map((i) => (
              <div
                key={i}
                className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5 animate-pulse"
              >
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 bg-gray-200 dark:bg-gray-700 rounded-lg"></div>
                  <div className="flex-1">
                    <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/3 mb-2"></div>
                    <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-1/2"></div>
                  </div>
                </div>
              </div>
            ))
          ) : filteredAnomalies && filteredAnomalies.length > 0 ? (
            filteredAnomalies.map((anomaly, idx) => (
              <AnomalyCard key={idx} anomaly={anomaly} />
            ))
          ) : (
            <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-12 text-center">
              <div className="w-16 h-16 bg-green-100 dark:bg-green-900/20 rounded-full flex items-center justify-center mx-auto mb-4">
                <Shield className="w-8 h-8 text-green-600 dark:text-green-400" />
              </div>
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-1">No anomalies found</h3>
              <p className="text-gray-500 dark:text-gray-400">No anomalies match your current filters.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
