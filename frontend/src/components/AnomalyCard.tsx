import { AlertTriangle, MapPin, Clock, Shield } from 'lucide-react';
import { AnomalyDetail, SeverityLevel } from '@/types';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface AnomalyCardProps {
  anomaly: AnomalyDetail;
  compact?: boolean;
}

const severityColors: Record<string, { bg: string; text: string; border: string; icon: string }> = {
  CRITICAL: {
    bg: 'bg-red-50 dark:bg-red-900/20',
    text: 'text-red-700 dark:text-red-300',
    border: 'border-red-200 dark:border-red-800',
    icon: 'text-red-500',
  },
  HIGH: {
    bg: 'bg-orange-50 dark:bg-orange-900/20',
    text: 'text-orange-700 dark:text-orange-300',
    border: 'border-orange-200 dark:border-orange-800',
    icon: 'text-orange-500',
  },
  MEDIUM: {
    bg: 'bg-amber-50 dark:bg-amber-900/20',
    text: 'text-amber-700 dark:text-amber-300',
    border: 'border-amber-200 dark:border-amber-800',
    icon: 'text-amber-500',
  },
  LOW: {
    bg: 'bg-blue-50 dark:bg-blue-900/20',
    text: 'text-blue-700 dark:text-blue-300',
    border: 'border-blue-200 dark:border-blue-800',
    icon: 'text-blue-500',
  },
};

const typeLabels: Record<string, string> = {
  impossible_travel: 'Impossible Travel',
  new_country: 'New Country Login',
  brute_force: 'Brute Force Attack',
  admin_action: 'Admin Action',
  new_ip: 'New IP Address',
  multiple_failures: 'Multiple Failed Logins',
  suspicious_location: 'Suspicious Location',
  failed_login: 'Failed Login',
};

const typeIcons: Record<string, React.ElementType> = {
  impossible_travel: MapPin,
  new_country: MapPin,
  brute_force: Shield,
  admin_action: Shield,
  new_ip: MapPin,
  multiple_failures: AlertTriangle,
  suspicious_location: MapPin,
  failed_login: AlertTriangle,
};

function getSeverityFromRiskScore(score: number): SeverityLevel {
  if (score >= 80) return 'CRITICAL';
  if (score >= 60) return 'HIGH';
  if (score >= 40) return 'MEDIUM';
  return 'LOW';
}

export default function AnomalyCard({ anomaly, compact = false }: AnomalyCardProps) {
  const severity = getSeverityFromRiskScore(anomaly.risk_score);
  const colors = severityColors[severity] || severityColors.LOW;
  const Icon = typeIcons[anomaly.type] || AlertTriangle;
  const typeLabel = typeLabels[anomaly.type] || anomaly.type;

  if (compact) {
    return (
      <div className={cn(
        'flex items-center gap-3 p-3 rounded-lg border transition-all hover:shadow-sm',
        colors.bg,
        colors.border
      )}>
        <Icon className={cn('w-5 h-5', colors.icon)} />
        <div className="flex-1 min-w-0">
          <p className={cn('text-sm font-medium truncate', colors.text)}>{typeLabel}</p>
          <p className="text-xs text-gray-600 dark:text-gray-400 truncate">{anomaly.user}</p>
        </div>
        <span className={cn('text-xs font-semibold px-2 py-0.5 rounded-full', colors.bg, colors.text)}>
          {anomaly.risk_score}
        </span>
      </div>
    );
  }

  return (
    <div className={cn(
      'bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5 transition-all hover:shadow-md'
    )}>
      <div className="flex items-start gap-4">
        <div className={cn('p-3 rounded-lg', colors.bg)}>
          <Icon className={cn('w-6 h-6', colors.icon)} />
        </div>

        <div className="flex-1">
          <div className="flex items-start justify-between">
            <div>
              <h3 className="font-semibold text-gray-900 dark:text-white">{typeLabel}</h3>
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-0.5">{anomaly.user}</p>
            </div>
            <span className={cn(
              'px-2.5 py-1 rounded-full text-xs font-semibold',
              colors.bg,
              colors.text
            )}>
              Risk: {anomaly.risk_score}
            </span>
          </div>

          {anomaly.locations && anomaly.locations.length >= 2 && (
            <div className="mt-3 flex items-center gap-2 text-sm">
              <MapPin className="w-4 h-4 text-gray-400" />
              <span className="text-gray-600 dark:text-gray-400">
                {anomaly.locations[0]} → {anomaly.locations[1]}
              </span>
            </div>
          )}

          {anomaly.country && (
            <div className="mt-2 flex items-center gap-2 text-sm">
              <MapPin className="w-4 h-4 text-gray-400" />
              <span className="text-gray-600 dark:text-gray-400">{anomaly.country}</span>
            </div>
          )}

          {anomaly.time_diff_minutes && (
            <div className="mt-2 flex items-center gap-2 text-sm">
              <Clock className="w-4 h-4 text-gray-400" />
              <span className="text-gray-600 dark:text-gray-400">
                Time gap: {Math.round(anomaly.time_diff_minutes)} minutes
              </span>
            </div>
          )}

          {anomaly.previous_countries && anomaly.previous_countries.length > 0 && (
            <div className="mt-3">
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Previously seen in:</p>
              <div className="flex flex-wrap gap-1">
                {anomaly.previous_countries.map((country, idx) => (
                  <span 
                    key={idx}
                    className="px-2 py-0.5 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 text-xs rounded"
                  >
                    {country}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
