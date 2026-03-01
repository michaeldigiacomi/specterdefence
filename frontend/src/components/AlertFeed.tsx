import { useEffect, useRef, useCallback, useState } from 'react';
import { 
  Bell, 
  Pause, 
  Play, 
  Trash2, 
  Filter,
  Wifi,
  WifiOff,
  AlertCircle,
  Volume2,
  VolumeX
} from 'lucide-react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { toast } from 'react-hot-toast';
import { AlertCard } from './AlertCard';
import { useWebSocket, type WebSocketFilters } from '@/hooks/useWebSocket';

// Utility for tailwind class merging
function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// Severity options
const severityOptions = [
  { value: 'CRITICAL', label: 'Critical', color: 'bg-red-500' },
  { value: 'HIGH', label: 'High', color: 'bg-orange-500' },
  { value: 'MEDIUM', label: 'Medium', color: 'bg-yellow-500' },
  { value: 'LOW', label: 'Low', color: 'bg-blue-500' },
];

// Event type options
const eventTypeOptions = [
  { value: 'impossible_travel', label: 'Impossible Travel' },
  { value: 'new_country', label: 'New Country' },
  { value: 'brute_force', label: 'Brute Force' },
  { value: 'admin_action', label: 'Admin Action' },
  { value: 'new_ip', label: 'New IP' },
  { value: 'multiple_failures', label: 'Multiple Failures' },
  { value: 'suspicious_location', label: 'Suspicious Location' },
];

interface AlertFeedProps {
  className?: string;
  compact?: boolean;
  maxHeight?: string;
  tenantId?: string;
}

export function AlertFeed({ 
  className, 
  compact = false,
  maxHeight = '600px',
  tenantId 
}: AlertFeedProps) {
  const {
    alerts,
    connectionStatus,
    isPaused,
    error,
    acknowledgeAlert,
    dismissAlert,
    pauseStream,
    resumeStream,
    clearAlerts,
    updateFilters,
    connectionStats,
  } = useWebSocket({ tenant_id: tenantId });

  const [soundEnabled, setSoundEnabled] = useState(true);
  const [showFilters, setShowFilters] = useState(false);
  const [selectedSeverities, setSelectedSeverities] = useState<string[]>([]);
  const [selectedEventTypes, setSelectedEventTypes] = useState<string[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const prevAlertsLength = useRef(alerts.length);

  // Initialize audio context for critical alerts
  useEffect(() => {
    // Create audio element for critical alert sound
    audioRef.current = new Audio('/sounds/notification-critical.mp3');
    audioRef.current.volume = 0.5;
  }, []);

  // Play sound for new critical alerts
  useEffect(() => {
    if (alerts.length > prevAlertsLength.current && soundEnabled && !isPaused) {
      const newAlerts = alerts.slice(0, alerts.length - prevAlertsLength.current);
      const hasCritical = newAlerts.some(a => a.severity === 'CRITICAL');
      
      if (hasCritical && audioRef.current) {
        audioRef.current.play().catch(() => {
          // Audio play failed (likely due to autoplay policy)
        });
        toast.error('Critical alert received!', {
          icon: '🔥',
          duration: 5000,
        });
      }
    }
    prevAlertsLength.current = alerts.length;
  }, [alerts.length, soundEnabled, isPaused]);

  // Auto-scroll to top when new alerts arrive (if not paused)
  useEffect(() => {
    if (!isPaused && scrollRef.current) {
      scrollRef.current.scrollTop = 0;
    }
  }, [alerts.length, isPaused]);

  // Apply filters
  const handleApplyFilters = useCallback(() => {
    const filters: WebSocketFilters = {
      severity: selectedSeverities.length > 0 ? selectedSeverities : undefined,
      event_types: selectedEventTypes.length > 0 ? selectedEventTypes : undefined,
      tenant_id: tenantId,
    };
    updateFilters(filters);
  }, [selectedSeverities, selectedEventTypes, tenantId, updateFilters]);

  // Clear filters
  const handleClearFilters = useCallback(() => {
    setSelectedSeverities([]);
    setSelectedEventTypes([]);
    updateFilters({ tenant_id: tenantId });
  }, [tenantId, updateFilters]);

  // Toggle severity selection
  const toggleSeverity = (severity: string) => {
    setSelectedSeverities(prev => 
      prev.includes(severity) 
        ? prev.filter(s => s !== severity)
        : [...prev, severity]
    );
  };

  // Toggle event type selection
  const toggleEventType = (eventType: string) => {
    setSelectedEventTypes(prev => 
      prev.includes(eventType) 
        ? prev.filter(e => e !== eventType)
        : [...prev, eventType]
    );
  };

  // Connection status indicator
  const getStatusIcon = () => {
    switch (connectionStatus) {
      case 'connected':
        return <Wifi className="w-4 h-4 text-green-500" />;
      case 'connecting':
        return <Wifi className="w-4 h-4 text-yellow-500 animate-pulse" />;
      case 'error':
        return <AlertCircle className="w-4 h-4 text-red-500" />;
      default:
        return <WifiOff className="w-4 h-4 text-gray-400" />;
    }
  };

  // Count alerts by severity
  const alertCounts = alerts.reduce((acc, alert) => {
    acc[alert.severity] = (acc[alert.severity] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  // Compact mode for sidebar
  if (compact) {
    return (
      <div className={cn('flex flex-col h-full bg-white dark:bg-gray-900', className)}>
        {/* Header */}
        <div className="flex items-center justify-between p-3 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-2">
            <Bell className="w-4 h-4 text-gray-500" />
            <span className="font-semibold text-sm text-gray-900 dark:text-gray-100">
              Live Alerts
            </span>
            {alerts.length > 0 && (
              <span className="bg-red-500 text-white text-xs px-1.5 py-0.5 rounded-full">
                {alerts.length}
              </span>
            )}
          </div>
          <div className="flex items-center gap-1">
            {getStatusIcon()}
            <button
              onClick={isPaused ? resumeStream : pauseStream}
              className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-800 rounded transition-colors"
              title={isPaused ? 'Resume' : 'Pause'}
            >
              {isPaused ? (
                <Play className="w-3 h-3 text-gray-500" />
              ) : (
                <Pause className="w-3 h-3 text-gray-500" />
              )}
            </button>
          </div>
        </div>

        {/* Alert List */}
        <div 
          ref={scrollRef}
          className="flex-1 overflow-y-auto p-2 space-y-2"
          style={{ maxHeight }}
        >
          {alerts.length === 0 ? (
            <div className="text-center py-8 text-gray-500 dark:text-gray-400">
              <Bell className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p className="text-sm">No alerts yet</p>
              <p className="text-xs mt-1">Waiting for new alerts...</p>
            </div>
          ) : (
            alerts.slice(0, 20).map(alert => (
              <AlertCard
                key={alert.id}
                alert={alert}
                onDismiss={dismissAlert}
                compact
              />
            ))
          )}
        </div>

        {/* Footer */}
        <div className="p-2 border-t border-gray-200 dark:border-gray-700 text-xs text-gray-500">
          <div className="flex items-center justify-between">
            <span>{connectionStats.connectedClients} connected</span>
            {isPaused && (
              <span className="text-yellow-600 dark:text-yellow-400">Stream paused</span>
            )}
          </div>
        </div>
      </div>
    );
  }

  // Full mode
  return (
    <div className={cn('flex flex-col bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700', className)}>
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-3">
          <div className="relative">
            <Bell className="w-5 h-5 text-gray-700 dark:text-gray-300" />
            {alerts.length > 0 && (
              <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs w-4 h-4 flex items-center justify-center rounded-full">
                {Math.min(alerts.length, 99)}
              </span>
            )}
          </div>
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              Live Alert Feed
            </h2>
            <div className="flex items-center gap-2 mt-0.5">
              {severityOptions.map(({ value, label, color }) => (
                alertCounts[value] > 0 && (
                  <span 
                    key={value} 
                    className={cn(
                      'text-xs text-white px-1.5 py-0.5 rounded-full',
                      color
                    )}
                  >
                    {alertCounts[value]} {label}
                  </span>
                )
              ))}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Connection status */}
          <div 
            className="flex items-center gap-1.5 px-2 py-1 rounded-full bg-gray-100 dark:bg-gray-800"
            title={`${connectionStats.connectedClients} connected clients`}
          >
            {getStatusIcon()}
            <span className="text-xs text-gray-600 dark:text-gray-400">
              {connectionStatus === 'connected' ? 'Live' : connectionStatus}
            </span>
          </div>

          {/* Sound toggle */}
          <button
            onClick={() => setSoundEnabled(!soundEnabled)}
            className={cn(
              'p-2 rounded-lg transition-colors',
              soundEnabled 
                ? 'text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20' 
                : 'text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'
            )}
            title={soundEnabled ? 'Sound on' : 'Sound off'}
          >
            {soundEnabled ? (
              <Volume2 className="w-4 h-4" />
            ) : (
              <VolumeX className="w-4 h-4" />
            )}
          </button>

          {/* Filter button */}
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={cn(
              'p-2 rounded-lg transition-colors flex items-center gap-1',
              showFilters || selectedSeverities.length > 0 || selectedEventTypes.length > 0
                ? 'text-blue-600 bg-blue-50 dark:bg-blue-900/20'
                : 'text-gray-600 hover:bg-gray-100 dark:hover:bg-gray-800'
            )}
            title="Filters"
          >
            <Filter className="w-4 h-4" />
            {(selectedSeverities.length > 0 || selectedEventTypes.length > 0) && (
              <span className="text-xs">
                {selectedSeverities.length + selectedEventTypes.length}
              </span>
            )}
          </button>

          {/* Pause/Resume */}
          <button
            onClick={isPaused ? resumeStream : pauseStream}
            className={cn(
              'p-2 rounded-lg transition-colors',
              isPaused
                ? 'text-yellow-600 bg-yellow-50 dark:bg-yellow-900/20'
                : 'text-gray-600 hover:bg-gray-100 dark:hover:bg-gray-800'
            )}
            title={isPaused ? 'Resume stream' : 'Pause stream'}
          >
            {isPaused ? (
              <Play className="w-4 h-4" />
            ) : (
              <Pause className="w-4 h-4" />
            )}
          </button>

          {/* Clear */}
          <button
            onClick={clearAlerts}
            className="p-2 text-gray-600 hover:bg-gray-100 dark:hover:bg-gray-800 dark:text-gray-400 rounded-lg transition-colors"
            title="Clear all alerts"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Error message */}
      {error && (
        <div className="px-4 py-2 bg-red-50 dark:bg-red-900/20 border-b border-red-200 dark:border-red-800">
          <div className="flex items-center gap-2 text-sm text-red-600 dark:text-red-400">
            <AlertCircle className="w-4 h-4" />
            {error}
          </div>
        </div>
      )}

      {/* Filters panel */}
      {showFilters && (
        <div className="p-4 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
          <div className="space-y-4">
            {/* Severity filters */}
            <div>
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 block">
                Severity
              </label>
              <div className="flex flex-wrap gap-2">
                {severityOptions.map(({ value, label, color }) => (
                  <button
                    key={value}
                    onClick={() => toggleSeverity(value)}
                    className={cn(
                      'px-3 py-1.5 rounded-full text-sm font-medium transition-all',
                      selectedSeverities.includes(value)
                        ? `${color} text-white`
                        : 'bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300 border border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-600'
                    )}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>

            {/* Event type filters */}
            <div>
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 block">
                Event Types
              </label>
              <div className="flex flex-wrap gap-2">
                {eventTypeOptions.map(({ value, label }) => (
                  <button
                    key={value}
                    onClick={() => toggleEventType(value)}
                    className={cn(
                      'px-3 py-1.5 rounded-full text-sm transition-all',
                      selectedEventTypes.includes(value)
                        ? 'bg-blue-600 text-white'
                        : 'bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300 border border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-600'
                    )}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>

            {/* Filter actions */}
            <div className="flex items-center gap-2 pt-2">
              <button
                onClick={handleApplyFilters}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors"
              >
                Apply Filters
              </button>
              <button
                onClick={handleClearFilters}
                className="px-4 py-2 text-gray-600 hover:bg-gray-200 dark:text-gray-400 dark:hover:bg-gray-700 rounded-lg text-sm transition-colors"
              >
                Clear
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Alert list */}
      <div 
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-4 space-y-3"
        style={{ maxHeight }}
      >
        {alerts.length === 0 ? (
          <div className="text-center py-12 text-gray-500 dark:text-gray-400">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center">
              <Bell className="w-8 h-8 opacity-50" />
            </div>
            <p className="text-lg font-medium">No alerts yet</p>
            <p className="text-sm mt-1">The alert feed is live and waiting for security events</p>
          </div>
        ) : (
          alerts.map(alert => (
            <AlertCard
              key={alert.id}
              alert={alert}
              onAcknowledge={acknowledgeAlert}
              onDismiss={dismissAlert}
            />
          ))
        )}
      </div>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 rounded-b-lg">
        <div className="flex items-center justify-between text-sm text-gray-600 dark:text-gray-400">
          <div className="flex items-center gap-4">
            <span>{alerts.length} alerts in feed</span>
            <span className="text-gray-300 dark:text-gray-600">|</span>
            <span>{connectionStats.connectedClients} connected clients</span>
          </div>
          
          {isPaused && (
            <div className="flex items-center gap-2 text-yellow-600 dark:text-yellow-400">
              <Pause className="w-4 h-4" />
              <span>Stream paused - new alerts are queued</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default AlertFeed;
