import React, { useState, useRef, useCallback } from 'react';
import { formatDistanceToNow } from 'date-fns';
import {
  Check,
  X,
  AlertTriangle,
  Info,
  AlertCircle,
  Flame,
  MapPin,
  User,
  Building2,
  ChevronRight,
  Bell,
} from 'lucide-react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import type { Alert } from '@/hooks/useWebSocket';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface MobileAlertCardProps {
  alert: Alert;
  onAcknowledge?: (id: string) => void;
  onDismiss?: (id: string) => void;
  onView?: (alert: Alert) => void;
}

const severityConfig = {
  LOW: {
    color: 'bg-blue-50 border-blue-200 dark:bg-blue-900/20 dark:border-blue-800',
    iconColor: 'text-blue-500',
    badgeColor: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
    icon: Info,
    label: 'Low',
  },
  MEDIUM: {
    color: 'bg-yellow-50 border-yellow-200 dark:bg-yellow-900/20 dark:border-yellow-800',
    iconColor: 'text-yellow-500',
    badgeColor: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
    icon: AlertTriangle,
    label: 'Medium',
  },
  HIGH: {
    color: 'bg-orange-50 border-orange-200 dark:bg-orange-900/20 dark:border-orange-800',
    iconColor: 'text-orange-500',
    badgeColor: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
    icon: AlertCircle,
    label: 'High',
  },
  CRITICAL: {
    color: 'bg-red-50 border-red-200 dark:bg-red-900/20 dark:border-red-800',
    iconColor: 'text-red-500',
    badgeColor: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
    icon: Flame,
    label: 'Critical',
  },
};

// Swipe threshold in pixels
const SWIPE_THRESHOLD = 100;

export function MobileAlertCard({ alert, onAcknowledge, onDismiss, onView }: MobileAlertCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [swipeOffset, setSwipeOffset] = useState(0);
  const [isSwiping, setIsSwiping] = useState(false);
  const touchStartX = useRef(0);
  const touchStartY = useRef(0);
  const cardRef = useRef<HTMLDivElement>(null);

  const config = severityConfig[alert.severity];
  const Icon = config.icon;

  // Handle touch start
  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    touchStartX.current = e.touches[0].clientX;
    touchStartY.current = e.touches[0].clientY;
    setIsSwiping(false);
  }, []);

  // Handle touch move
  const handleTouchMove = useCallback((e: React.TouchEvent) => {
    if (!touchStartX.current) return;

    const touchX = e.touches[0].clientX;
    const touchY = e.touches[0].clientY;
    const deltaX = touchX - touchStartX.current;
    const deltaY = touchY - touchStartY.current;

    // Determine if horizontal swipe
    if (Math.abs(deltaX) > Math.abs(deltaY) && Math.abs(deltaX) > 10) {
      setIsSwiping(true);
      e.preventDefault();

      // Limit swipe distance
      const maxSwipe = 150;
      const limitedDelta = Math.max(-maxSwipe, Math.min(maxSwipe, deltaX));
      setSwipeOffset(limitedDelta);
    }
  }, []);

  // Handle touch end
  const handleTouchEnd = useCallback(() => {
    if (Math.abs(swipeOffset) > SWIPE_THRESHOLD) {
      if (swipeOffset > 0 && onAcknowledge) {
        // Swiped right - acknowledge
        onAcknowledge(alert.id);
      } else if (swipeOffset < 0 && onDismiss) {
        // Swiped left - dismiss
        onDismiss(alert.id);
      }
    }

    setSwipeOffset(0);
    setIsSwiping(false);
    touchStartX.current = 0;
    touchStartY.current = 0;
  }, [swipeOffset, alert.id, onAcknowledge, onDismiss]);

  // Handle card click
  const handleCardClick = () => {
    if (!isSwiping) {
      if (onView) {
        onView(alert);
      } else {
        setExpanded(!expanded);
      }
    }
  };

  const handleAcknowledge = (e: React.MouseEvent) => {
    e.stopPropagation();
    onAcknowledge?.(alert.id);
  };

  const handleDismiss = (e: React.MouseEvent) => {
    e.stopPropagation();
    onDismiss?.(alert.id);
  };

  // Format location data
  const location =
    (alert.metadata?.current_location as { city?: string; country?: string } | undefined) ||
    (alert.metadata?.location as { city?: string; country?: string } | undefined);
  const ipAddress = alert.metadata?.ip_address as string | undefined;

  // Calculate swipe background color
  const getSwipeBackground = () => {
    if (swipeOffset > 0) {
      return 'bg-green-500';
    } else if (swipeOffset < 0) {
      return 'bg-red-500';
    }
    return 'bg-gray-200 dark:bg-gray-700';
  };

  return (
    <div className="relative overflow-hidden rounded-xl mb-3 touch-pan-y">
      {/* Swipe Background Actions */}
      <div
        className={cn(
          'absolute inset-0 flex items-center justify-between px-4 transition-colors duration-200',
          getSwipeBackground()
        )}
      >
        {/* Right swipe - Acknowledge */}
        <div
          className={cn(
            'flex items-center gap-2 text-white transition-opacity duration-200',
            swipeOffset > 0 ? 'opacity-100' : 'opacity-0'
          )}
        >
          <Check className="w-6 h-6" />
          <span className="font-medium">Acknowledge</span>
        </div>

        {/* Left swipe - Dismiss */}
        <div
          className={cn(
            'flex items-center gap-2 text-white transition-opacity duration-200',
            swipeOffset < 0 ? 'opacity-100' : 'opacity-0'
          )}
        >
          <span className="font-medium">Dismiss</span>
          <X className="w-6 h-6" />
        </div>
      </div>

      {/* Main Card */}
      <div
        ref={cardRef}
        className={cn(
          'relative bg-white dark:bg-gray-800 border rounded-xl transition-transform duration-200 ease-out',
          config.color,
          isSwiping && 'cursor-grabbing'
        )}
        style={{
          transform: `translateX(${swipeOffset}px)`,
        }}
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
        onClick={handleCardClick}
      >
        {/* Card Content */}
        <div className="p-4">
          {/* Header Row */}
          <div className="flex items-start gap-3">
            {/* Icon */}
            <div
              className={cn(
                'w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0',
                'bg-white dark:bg-gray-700 shadow-sm',
                config.iconColor
              )}
            >
              <Icon className="w-5 h-5" />
            </div>

            {/* Content */}
            <div className="flex-1 min-w-0">
              {/* Badge and Time */}
              <div className="flex items-center gap-2 flex-wrap">
                <span
                  className={cn(
                    'text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider',
                    config.badgeColor
                  )}
                >
                  {config.label}
                </span>
                <span className="text-xs text-gray-500 dark:text-gray-400">
                  {formatDistanceToNow(new Date(alert.timestamp), { addSuffix: true })}
                </span>
              </div>

              {/* Title */}
              <h3 className="text-sm font-semibold text-gray-900 dark:text-white mt-1 leading-tight">
                {alert.title}
              </h3>

              {/* Message */}
              <p className="text-xs text-gray-600 dark:text-gray-300 mt-1 line-clamp-2">
                {alert.message}
              </p>
            </div>

            {/* Chevron */}
            <ChevronRight
              className={cn(
                'w-5 h-5 text-gray-400 flex-shrink-0 transition-transform duration-200',
                expanded && 'rotate-90'
              )}
            />
          </div>

          {/* Meta Info Row */}
          <div className="flex items-center gap-3 mt-3 flex-wrap">
            {alert.user_email && (
              <span className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
                <User className="w-3 h-3" />
                <span className="truncate max-w-[120px]">{alert.user_email}</span>
              </span>
            )}
            {location && (location.city || location.country) && (
              <span className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
                <MapPin className="w-3 h-3" />
                {location.city || location.country}
              </span>
            )}
            {ipAddress && (
              <span className="text-xs text-gray-500 dark:text-gray-400 font-mono">
                {ipAddress}
              </span>
            )}
          </div>

          {/* Action Buttons */}
          <div className="flex items-center gap-2 mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
            {alert.status !== 'acknowledged' && onAcknowledge && (
              <button
                onClick={handleAcknowledge}
                className={cn(
                  'flex-1 flex items-center justify-center gap-2 py-2 rounded-lg text-xs font-medium',
                  'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
                  'active:scale-95 transition-transform'
                )}
              >
                <Check className="w-4 h-4" />
                Acknowledge
              </button>
            )}
            {onDismiss && (
              <button
                onClick={handleDismiss}
                className={cn(
                  'flex-1 flex items-center justify-center gap-2 py-2 rounded-lg text-xs font-medium',
                  'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
                  'active:scale-95 transition-transform'
                )}
              >
                <X className="w-4 h-4" />
                Dismiss
              </button>
            )}
          </div>
        </div>

        {/* Expanded Details */}
        {expanded && (
          <div className="px-4 pb-4 border-t border-gray-200 dark:border-gray-700">
            <div className="pt-3 space-y-3">
              {/* Event Type */}
              <div className="flex items-center gap-2">
                <Bell className="w-4 h-4 text-gray-400" />
                <span className="text-xs text-gray-600 dark:text-gray-300">
                  {alert.event_type_name}
                </span>
              </div>

              {/* Metadata */}
              {Object.keys(alert.metadata).length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase mb-2">
                    Details
                  </p>
                  <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-3 overflow-x-auto">
                    <pre className="text-xs text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                      {JSON.stringify(alert.metadata, null, 2)}
                    </pre>
                  </div>
                </div>
              )}

              {/* Alert ID and Tenant */}
              <div className="flex flex-col gap-1 text-xs text-gray-500 dark:text-gray-400">
                <span className="font-mono">ID: {alert.id.slice(0, 16)}...</span>
                {alert.tenant_id && (
                  <span className="flex items-center gap-1">
                    <Building2 className="w-3 h-3" />
                    Tenant: {alert.tenant_id.slice(0, 8)}...
                  </span>
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Swipe Hints */}
      <div className="absolute bottom-1 left-0 right-0 flex justify-between px-4 pointer-events-none">
        <span className="text-[10px] text-gray-400 dark:text-gray-600 opacity-0">
          Swipe right to acknowledge
        </span>
        <span className="text-[10px] text-gray-400 dark:text-gray-600 opacity-0">
          Swipe left to dismiss
        </span>
      </div>
    </div>
  );
}

export default MobileAlertCard;
