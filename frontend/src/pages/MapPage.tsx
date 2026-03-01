import { Map } from 'lucide-react';
import LoginMap from '@/components/LoginMap';
import { useLoginAnalytics } from '@/hooks/useApi';

export default function MapPage() {
  const { data, isLoading } = useLoginAnalytics({ 
    page_size: 1000,
    start_time: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(), // Last 7 days
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
          <Map className="w-6 h-6 text-primary-500" />
          Geographic Map
        </h1>
        <p className="mt-1 text-gray-500 dark:text-gray-400">
          Visualize login locations and geographic patterns
        </p>
      </div>

      {/* Map */}
      <LoginMap 
        logins={data?.logins || []}
        loading={isLoading}
        height="600px"
      />

      {/* Legend */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
        <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-3">Map Legend</h3>
        <div className="flex flex-wrap gap-6">
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-green-500 rounded-full border-2 border-white shadow"></div>
            <span className="text-sm text-gray-600 dark:text-gray-400">Successful Login</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-red-500 rounded-full border-2 border-white shadow"></div>
            <span className="text-sm text-gray-600 dark:text-gray-400">Failed Login</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 bg-amber-500 rounded-full border-2 border-white shadow flex items-center justify-center">
              <svg xmlns="http://www.w3.org/2000/svg" className="w-3 h-3 text-white" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
            </div>
            <span className="text-sm text-gray-600 dark:text-gray-400">Anomaly Detected</span>
          </div>
        </div>
      </div>
    </div>
  );
}
