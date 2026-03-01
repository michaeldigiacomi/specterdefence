import { useMemo } from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet';
import { Globe, AlertTriangle, Users } from 'lucide-react';
import 'leaflet/dist/leaflet.css';

interface GeoLocationData {
  country_code: string;
  country_name: string;
  latitude: number;
  longitude: number;
  login_count: number;
  user_count: number;
  risk_score_avg: number;
}

interface GeoHeatmapProps {
  data: GeoLocationData[];
  isLoading?: boolean;
  totalCountries?: number;
  topCountry?: string;
}

// Color scale based on risk score
const getRiskColor = (riskScore: number): string => {
  if (riskScore >= 70) return '#ef4444'; // Red
  if (riskScore >= 40) return '#f59e0b'; // Amber
  return '#10b981'; // Green
};

// Radius based on login count (scaled)
const getRadius = (count: number): number => {
  const baseRadius = 8;
  const maxRadius = 30;
  const scale = Math.min(count / 100, 1); // Scale based on count, max at 100
  return baseRadius + (maxRadius - baseRadius) * scale;
};

export function GeoHeatmap({
  data,
  isLoading = false,
  totalCountries = 0,
  topCountry,
}: GeoHeatmapProps) {
  // Calculate map center based on data
  const center = useMemo(() => {
    if (data.length === 0) return [20, 0] as [number, number];
    
    const avgLat = data.reduce((sum, d) => sum + d.latitude, 0) / data.length;
    const avgLng = data.reduce((sum, d) => sum + d.longitude, 0) / data.length;
    return [avgLat, avgLng] as [number, number];
  }, [data]);

  // Find max login count for scaling
  const maxLoginCount = useMemo(() => {
    if (data.length === 0) return 1;
    return Math.max(...data.map(d => d.login_count));
  }, [data]);

  if (isLoading) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
        <div className="animate-pulse">
          <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-1/3 mb-4"></div>
          <div className="h-80 bg-gray-200 dark:bg-gray-700 rounded"></div>
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
            Geographic Activity
          </h3>
          <div className="flex items-center gap-4 mt-1">
            <span className="text-sm text-gray-500 dark:text-gray-400 flex items-center gap-1">
              <Globe className="w-4 h-4" />
              {totalCountries} countries
            </span>
            {topCountry && (
              <span className="text-sm text-gray-500 dark:text-gray-400">
                Top: {topCountry}
              </span>
            )}
          </div>
        </div>

        {/* Legend */}
        <div className="flex items-center gap-3 text-xs">
          <div className="flex items-center gap-1">
            <span className="w-3 h-3 rounded-full bg-green-500"></span>
            <span className="text-gray-600 dark:text-gray-400">Low Risk</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="w-3 h-3 rounded-full bg-amber-500"></span>
            <span className="text-gray-600 dark:text-gray-400">Medium</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="w-3 h-3 rounded-full bg-red-500"></span>
            <span className="text-gray-600 dark:text-gray-400">High</span>
          </div>
        </div>
      </div>

      {/* Map */}
      <div className="h-80 rounded-lg overflow-hidden border border-gray-200 dark:border-gray-700">
        {data.length > 0 ? (
          <MapContainer
            center={center}
            zoom={2}
            scrollWheelZoom={false}
            className="h-full w-full"
          >
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            {data.map((location, index) => (
              <CircleMarker
                key={`${location.country_code}-${index}`}
                center={[location.latitude, location.longitude]}
                radius={getRadius(location.login_count)}
                fillColor={getRiskColor(location.risk_score_avg)}
                color={getRiskColor(location.risk_score_avg)}
                weight={2}
                opacity={0.8}
                fillOpacity={0.6}
              >
                <Popup>
                  <div className="p-2 min-w-[200px]">
                    <h4 className="font-semibold text-gray-900 mb-2">
                      {location.country_name}
                    </h4>
                    <div className="space-y-1 text-sm">
                      <div className="flex items-center gap-2">
                        <Users className="w-4 h-4 text-gray-400" />
                        <span>{location.user_count} users</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Globe className="w-4 h-4 text-gray-400" />
                        <span>{location.login_count} logins</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <AlertTriangle className="w-4 h-4 text-gray-400" />
                        <span>Risk Score: {location.risk_score_avg.toFixed(1)}</span>
                      </div>
                    </div>
                  </div>
                </Popup>
              </CircleMarker>
            ))}
          </MapContainer>
        ) : (
          <div className="h-full flex items-center justify-center bg-gray-50 dark:bg-gray-900">
            <div className="text-center">
              <Globe className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
              <p className="text-gray-500 dark:text-gray-400">No geographic data available</p>
            </div>
          </div>
        )}
      </div>

      {/* Stats Summary */}
      {data.length > 0 && (
        <div className="grid grid-cols-3 gap-4 mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
          <div className="text-center">
            <p className="text-2xl font-bold text-gray-900 dark:text-white">
              {data.reduce((sum, d) => sum + d.login_count, 0).toLocaleString()}
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-400">Total Logins</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-gray-900 dark:text-white">
              {data.reduce((sum, d) => sum + d.user_count, 0).toLocaleString()}
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-400">Unique Users</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-gray-900 dark:text-white">
              {(data.reduce((sum, d) => sum + d.risk_score_avg, 0) / data.length).toFixed(1)}
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-400">Avg Risk Score</p>
          </div>
        </div>
      )}
    </div>
  );
}
