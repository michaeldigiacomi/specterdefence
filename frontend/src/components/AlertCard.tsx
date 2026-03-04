import React, { useState } from 'react';
import { formatDistanceToNow } from 'date-fns';
import {
  Check,
  X,
  AlertTriangle,
  Info,
  AlertCircle,
  Flame,
  ChevronDown,
  ChevronUp,
  MapPin,
  User,
  Building2
} from 'lucide-react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import type { Alert } from '@/hooks/useWebSocket';

// Utility for tailwind class merging
function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface AlertCardProps {
  alert: Alert;
  onAcknowledge?: (id: string) => void;
  onDismiss?: (id: string) => void;
  compact?: boolean;
}

const severityConfig = {
  LOW: {
    color: 'bg-blue-50 border-blue-200 dark:bg-blue-900/20 dark:border-blue-800',
    iconColor: 'text-blue-500',
    badgeColor: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
    icon: Info,
    sound: '/sounds/notification-low.mp3',
  },
  MEDIUM: {
    color: 'bg-yellow-50 border-yellow-200 dark:bg-yellow-900/20 dark:border-yellow-800',
    iconColor: 'text-yellow-500',
    badgeColor: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
    icon: AlertTriangle,
    sound: '/sounds/notification-medium.mp3',
  },
  HIGH: {
    color: 'bg-orange-50 border-orange-200 dark:bg-orange-900/20 dark:border-orange-800',
    iconColor: 'text-orange-500',
    badgeColor: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
    icon: AlertCircle,
    sound: '/sounds/notification-high.mp3',
  },
  CRITICAL: {
    color: 'bg-red-50 border-red-200 dark:bg-red-900/20 dark:border-red-800',
    iconColor: 'text-red-500',
    badgeColor: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
    icon: Flame,
    sound: '/sounds/notification-critical.mp3',
  },
};

export function AlertCard({
  alert,
  onAcknowledge,
  onDismiss,
  compact = false
}: AlertCardProps) {
  const [expanded, setExpanded] = useState(false);
  const config = severityConfig[alert.severity];
  const Icon = config.icon;

  const handleAcknowledge = (e: React.MouseEvent) => {
    e.stopPropagation();
    onAcknowledge?.(alert.id);
  };

  const handleDismiss = (e: React.MouseEvent) => {
    e.stopPropagation();
    onDismiss?.(alert.id);
  };

  const toggleExpand = () => setExpanded(!expanded);

  // Format location data if available
  const location = (alert.metadata?.current_location as { city?: string; country?: string } | undefined)
    || (alert.metadata?.location as { city?: string; country?: string } | undefined);
  const ipAddress = alert.metadata?.ip_address as string | undefined;

  if (compact) {
    return (
      <div
        className={cn(
          'flex items-center gap-3 p-3 border rounded-lg transition-all',
          'hover:shadow-md cursor-pointer',
          config.color
        )}
        onClick={toggleExpand}
      >
        <Icon className={cn('w-5 h-5 flex-shrink-0', config.iconColor)} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className={cn(
              'text-xs font-medium px-2 py-0.5 rounded-full',
              config.badgeColor
            )}>
              {alert.severity}
            </span>
            <span className="text-xs text-gray-500 dark:text-gray-400">
              {formatDistanceToNow(new Date(alert.timestamp), { addSuffix: true })}
            </span>
          </div>
          <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate mt-1">
            {alert.title}
          </p>
        </div>
        <button
          onClick={handleDismiss}
          className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded transition-colors"
          title="Dismiss"
        >
          <X className="w-4 h-4 text-gray-500" />
        </button>
      </div>
    );
  }

  return (
    <div
      className={cn(
        'border rounded-lg transition-all overflow-hidden',
        'hover:shadow-lg',
        alert.status === 'acknowledged' && 'opacity-60',
        config.color
      )}
    >
      {/* Header */}
      <div
        className="p-4 cursor-pointer"
        onClick={toggleExpand}
      >
        <div className="flex items-start gap-3">
          <div className={cn(
            'p-2 rounded-full bg-white dark:bg-gray-800 flex-shrink-0',
            config.iconColor
          )}>
            <Icon className="w-5 h-5" />
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className={cn(
                'text-xs font-semibold px-2 py-1 rounded-full uppercase tracking-wide',
                config.badgeColor
              )}>
                {alert.severity}
              </span>
              <span className="text-xs text-gray-500 dark:text-gray-400">
                {alert.event_type_name}
              </span>
            </div>

            <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100 mt-2">
              {alert.title}
            </h3>

            <p className="text-sm text-gray-600 dark:text-gray-300 mt-1 line-clamp-2">
              {alert.message}
            </p>

            <div className="flex items-center gap-4 mt-3 text-xs text-gray-500 dark:text-gray-400">
              {alert.user_email && (
                <span className="flex items-center gap-1">
                  <User className="w-3 h-3" />
                  {alert.user_email}
                </span>
              )}
              {location && (
                <span className="flex items-center gap-1">
                  <MapPin className="w-3 h-3" />
                  {location.city || location.country || 'Unknown location'}
                </span>
              )}
              {ipAddress && (
                <span className="font-mono">{ipAddress}</span>
              )}
              <span className="flex items-center gap-1 ml-auto">
                {formatDistanceToNow(new Date(alert.timestamp), { addSuffix: true })}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-1">
            {alert.status !== 'acknowledged' && onAcknowledge && (
              <button
                onClick={handleAcknowledge}
                className={cn(
                  'p-2 rounded-lg transition-colors',
                  'hover:bg-green-100 dark:hover:bg-green-900/30',
                  'text-green-600 dark:text-green-400'
                )}
                title="Acknowledge"
              >
                <Check className="w-4 h-4" />
              </button>
            )}
            {onDismiss && (
              <button
                onClick={handleDismiss}
                className={cn(
                  'p-2 rounded-lg transition-colors',
                  'hover:bg-red-100 dark:hover:bg-red-900/30',
                  'text-red-600 dark:text-red-400'
                )}
                title="Dismiss"
              >
                <X className="w-4 h-4" />
              </button>
            )}
            <button className="p-2 text-gray-400">
              {expanded ? (
                <ChevronUp className="w-4 h-4" />
              ) : (
                <ChevronDown className="w-4 h-4" />
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Expanded Details */}
      {expanded && (
        <div className="px-4 pb-4 border-t border-gray-200 dark:border-gray-700 pt-3">
          <div className="space-y-3">
            {/* Metadata */}
            {Object.keys(alert.metadata).length > 0 && (
              <div>
                <h4 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2">
                  Details
                </h4>
                <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-3 overflow-x-auto">
                  <pre className="text-xs text-gray-700 dark:text-gray-300">
                    {JSON.stringify(alert.metadata, null, 2)}
                  </pre>
                </div>
              </div>
            )}

            {/* Alert ID and timestamps */}
            <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
              <span className="font-mono">ID: {alert.id}</span>
              <div className="flex items-center gap-4">
                {alert.tenant_id && (
                  <span className="flex items-center gap-1">
                    <Building2 className="w-3 h-3" />
                    Tenant: {alert.tenant_id.slice(0, 8)}...
                  </span>
                )}
                {alert.acknowledged_by && (
                  <span>
                    Acknowledged by {alert.acknowledged_by} at{' '}
                    {alert.acknowledged_at &&
                      formatDistanceToNow(new Date(alert.acknowledged_at), { addSuffix: true })
                    }
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default AlertCard;
