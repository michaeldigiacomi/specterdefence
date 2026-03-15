import { useState, useMemo } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import { format, parseISO } from 'date-fns';
import { AlertTriangle, CheckCircle, XCircle, MapPin, Filter } from 'lucide-react';
import { LoginRecord } from '@/types';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import L from 'leaflet';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface LoginMapProps {
  logins: LoginRecord[];
  loading?: boolean;
  height?: string;
}

// Custom icons for different statuses
const successIcon = new L.DivIcon({
  className: 'custom-marker',
  html: `<div class="w-4 h-4 bg-green-500 rounded-full border-2 border-white shadow-lg"></div>`,
  iconSize: [16, 16],
  iconAnchor: [8, 8],
});

const failedIcon = new L.DivIcon({
  className: 'custom-marker',
  html: `<div class="w-4 h-4 bg-red-500 rounded-full border-2 border-white shadow-lg"></div>`,
  iconSize: [16, 16],
  iconAnchor: [8, 8],
});

const anomalyIcon = new L.DivIcon({
  className: 'custom-marker',
  html: `<div class="w-6 h-6 bg-amber-500 rounded-full border-2 border-white shadow-lg flex items-center justify-center">
    <svg xmlns="http://www.w3.org/2000/svg" class="w-3 h-3 text-white" viewBox="0 0 20 20" fill="currentColor">
      <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
    </svg>
  </div>`,
  iconSize: [24, 24],
  iconAnchor: [12, 12],
});

// Map bounds updater component
function MapBoundsUpdater({ bounds }: { bounds: L.LatLngBoundsExpression | null }) {
  const map = useMap();

  if (bounds) {
    map.fitBounds(bounds, { padding: [50, 50] });
  }

  return null;
}

export default function LoginMap({ logins, loading = false, height = '500px' }: LoginMapProps) {
  const [showSuccess, setShowSuccess] = useState(true);
  const [showFailed, setShowFailed] = useState(true);
  const [showAnomalies, setShowAnomalies] = useState(true);

  const filteredLogins = useMemo(() => {
    return logins.filter(login => {
      if (login.anomaly_flags.length > 0 && showAnomalies) return true;
      if (login.is_success && showSuccess) return true;
      if (!login.is_success && showFailed) return true;
      return false;
    });
  }, [logins, showSuccess, showFailed, showAnomalies]);

  const mapBounds = useMemo(() => {
    if (filteredLogins.length === 0) return null;

    const validLogins = filteredLogins.filter(l => l.latitude && l.longitude);
    if (validLogins.length === 0) return null;

    const coords = validLogins.map(l => [l.latitude!, l.longitude!] as [number, number]);
    return L.latLngBounds(coords);
  }, [filteredLogins]);

  const defaultCenter: [number, number] = [20, 0];

  if (loading) {
    return (
      <div
        className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 animate-pulse"
        style={{ height }}
      >
        <div className="h-full bg-gray-200 dark:bg-gray-700 rounded-lg"></div>
      </div>
    );
  }

  const validLogins = filteredLogins.filter(l => l.latitude && l.longitude);

  if (validLogins.length === 0) {
    return (
      <div
        className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 flex items-center justify-center"
        style={{ height }}
      >
        <div className="text-center">
          <MapPin className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-1">
            No location data
          </h3>
          <p className="text-gray-500 dark:text-gray-400">
            No logins with geographic coordinates found.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
      {/* Filter Controls */}
      <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700 flex items-center gap-4 flex-wrap">
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-gray-500" />
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Show:</span>
        </div>

        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={showSuccess}
            onChange={e => setShowSuccess(e.target.checked)}
            className="w-4 h-4 text-green-500 rounded border-gray-300 focus:ring-green-500"
          />
          <span className="flex items-center gap-1 text-sm text-gray-600 dark:text-gray-400">
            <CheckCircle className="w-4 h-4 text-green-500" />
            Success
          </span>
        </label>

        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={showFailed}
            onChange={e => setShowFailed(e.target.checked)}
            className="w-4 h-4 text-red-500 rounded border-gray-300 focus:ring-red-500"
          />
          <span className="flex items-center gap-1 text-sm text-gray-600 dark:text-gray-400">
            <XCircle className="w-4 h-4 text-red-500" />
            Failed
          </span>
        </label>

        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={showAnomalies}
            onChange={e => setShowAnomalies(e.target.checked)}
            className="w-4 h-4 text-amber-500 rounded border-gray-300 focus:ring-amber-500"
          />
          <span className="flex items-center gap-1 text-sm text-gray-600 dark:text-gray-400">
            <AlertTriangle className="w-4 h-4 text-amber-500" />
            Anomalies
          </span>
        </label>

        <div className="ml-auto text-sm text-gray-500 dark:text-gray-400">
          Showing {validLogins.length} markers
        </div>
      </div>

      {/* Map */}
      <div style={{ height }} className="relative">
        <MapContainer
          center={defaultCenter}
          zoom={2}
          scrollWheelZoom={true}
          style={{ height: '100%', width: '100%' }}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          {validLogins.map(login => {
            const hasAnomaly = login.anomaly_flags.length > 0;
            const icon = hasAnomaly ? anomalyIcon : login.is_success ? successIcon : failedIcon;

            return (
              <Marker key={login.id} position={[login.latitude!, login.longitude!]} icon={icon}>
                <Popup>
                  <div className="min-w-[200px]">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="font-semibold text-gray-900">{login.user_email}</span>
                    </div>

                    <div className="space-y-1 text-sm">
                      <div className="flex items-center gap-2">
                        {login.is_success ? (
                          <CheckCircle className="w-4 h-4 text-green-500" />
                        ) : (
                          <XCircle className="w-4 h-4 text-red-500" />
                        )}
                        <span className={login.is_success ? 'text-green-700' : 'text-red-700'}>
                          {login.is_success ? 'Success' : 'Failed'}
                        </span>
                      </div>

                      <div className="flex items-center gap-2">
                        <MapPin className="w-4 h-4 text-gray-400" />
                        <span className="text-gray-600">
                          {login.city && login.country
                            ? `${login.city}, ${login.country}`
                            : login.country || 'Unknown location'}
                        </span>
                      </div>

                      <div className="flex items-center gap-2">
                        <span className="text-gray-400 font-mono text-xs">{login.ip_address}</span>
                      </div>

                      <div className="text-xs text-gray-500">
                        {format(parseISO(login.login_time), 'PPp')}
                      </div>

                      {hasAnomaly && (
                        <div className="mt-2 pt-2 border-t border-gray-200">
                          <div className="flex items-center gap-1 text-amber-600">
                            <AlertTriangle className="w-4 h-4" />
                            <span className="font-medium">Anomalies Detected</span>
                          </div>
                          <div className="mt-1 flex flex-wrap gap-1">
                            {login.anomaly_flags.map((flag, idx) => (
                              <span
                                key={idx}
                                className="px-1.5 py-0.5 bg-amber-100 text-amber-700 text-xs rounded"
                              >
                                {flag}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      <div className="mt-2">
                        <span
                          className={cn(
                            'px-2 py-0.5 rounded text-xs font-medium',
                            login.risk_score >= 80
                              ? 'bg-red-100 text-red-700'
                              : login.risk_score >= 60
                                ? 'bg-orange-100 text-orange-700'
                                : login.risk_score >= 40
                                  ? 'bg-amber-100 text-amber-700'
                                  : 'bg-green-100 text-green-700'
                          )}
                        >
                          Risk Score: {login.risk_score}
                        </span>
                      </div>
                    </div>
                  </div>
                </Popup>
              </Marker>
            );
          })}

          {mapBounds && <MapBoundsUpdater bounds={mapBounds} />}
        </MapContainer>
      </div>
    </div>
  );
}
