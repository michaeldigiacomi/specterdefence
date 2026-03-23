import { useState, useEffect } from 'react';
import {
  Monitor,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Clock,
  RefreshCw,
  Shield,
  Copy,
  Terminal,
  ChevronDown,
  ChevronRight,
  Wifi,
  WifiOff,
} from 'lucide-react';
import { apiService } from '../services/api';
import type { Tenant } from '../types';

type TabType = 'devices' | 'events';

interface EndpointDevice {
  id: string;
  hostname: string;
  os_version: string | null;
  agent_version: string | null;
  status: string;
  last_heartbeat: string | null;
  ip_address: string | null;
  enrolled_at: string;
  event_count: number;
}

interface EndpointEvent {
  id: string;
  device_id: string;
  hostname: string | null;
  event_type: string;
  severity: string;
  title: string;
  description: string | null;
  process_name: string | null;
  command_line: string | null;
  user_context: string | null;
  source_ip: string | null;
  metadata: Record<string, unknown>;
  detected_at: string;
  received_at: string;
}

interface EndpointSummaryData {
  total_devices: number;
  active_devices: number;
  total_events_24h: number;
  critical_events_24h: number;
  high_events_24h: number;
}

const EVENT_TYPE_LABELS: Record<string, string> = {
  suspicious_process: 'Suspicious Process',
  powershell_abuse: 'PowerShell Abuse',
  usb_insertion: 'USB Insertion',
  credential_dump: 'Credential Dump',
  persistence_mechanism: 'Persistence Mechanism',
  defender_tamper: 'Defender Tamper',
  local_account_change: 'Local Account Change',
};

const SEVERITY_COLORS: Record<string, string> = {
  CRITICAL: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
  HIGH: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400',
  MEDIUM: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400',
  LOW: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
};

export default function Endpoints() {
  const [activeTab, setActiveTab] = useState<TabType>('devices');
  const [devices, setDevices] = useState<EndpointDevice[]>([]);
  const [events, setEvents] = useState<EndpointEvent[]>([]);
  const [summary, setSummary] = useState<EndpointSummaryData | null>(null);
  const [loading, setLoading] = useState(true);
  const [expandedDevice, setExpandedDevice] = useState<string | null>(null);
  const [deviceEvents, setDeviceEvents] = useState<EndpointEvent[]>([]);
  const [showTokenModal, setShowTokenModal] = useState(false);
  const [enrollmentToken, setEnrollmentToken] = useState<string>('');
  const [generatingToken, setGeneratingToken] = useState(false);

  // Tenant selection
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [selectedTenant, setSelectedTenant] = useState<string>('');

  // Filters
  const [severityFilter, setSeverityFilter] = useState<string>('');
  const [eventTypeFilter, setEventTypeFilter] = useState<string>('');

  useEffect(() => {
    apiService.getTenants().then(res => {
      const items = res.items ?? [];
      setTenants(items);
      if (items.length > 0 && items[0]) {
        setSelectedTenant(items[0].id);
      }
    });
  }, []);

  useEffect(() => {
    if (selectedTenant) {
      loadData();
    }
  }, [activeTab, selectedTenant, severityFilter, eventTypeFilter]);

  const loadData = async () => {
    setLoading(true);
    try {
      const summaryData = await apiService.getEndpointSummary(selectedTenant);
      setSummary(summaryData);

      if (activeTab === 'devices') {
        const devicesData = await apiService.getEndpointDevices({
          tenant_id: selectedTenant,
        });
        setDevices(devicesData.items || []);
      } else {
        const eventsParams: { tenant_id?: string; severity?: string; event_type?: string; limit?: number } = {
          tenant_id: selectedTenant,
          limit: 100,
        };
        if (severityFilter) eventsParams.severity = severityFilter;
        if (eventTypeFilter) eventsParams.event_type = eventTypeFilter;
        const eventsData = await apiService.getEndpointEvents(eventsParams);
        setEvents(eventsData.items || []);
      }
    } catch (error) {
      console.error('Failed to load endpoint data:', error);
    }
    setLoading(false);
  };

  const handleExpandDevice = async (deviceId: string) => {
    if (expandedDevice === deviceId) {
      setExpandedDevice(null);
      return;
    }
    setExpandedDevice(deviceId);
    try {
      const data = await apiService.getEndpointDeviceEvents(deviceId, { limit: 20 });
      setDeviceEvents(data.items || []);
    } catch (error) {
      console.error('Failed to load device events:', error);
    }
  };

  const handleGenerateToken = async () => {
    setGeneratingToken(true);
    try {
      const data = await apiService.generateEndpointEnrollmentToken(selectedTenant);
      setEnrollmentToken(data.enrollment_token);
      setShowTokenModal(true);
    } catch (error) {
      console.error('Failed to generate token:', error);
    }
    setGeneratingToken(false);
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  const timeAgo = (ts: string | null) => {
    if (!ts) return 'Never';
    const now = new Date();
    const then = new Date(ts);
    const diff = Math.floor((now.getTime() - then.getTime()) / 1000);
    if (diff < 60) return `${diff}s ago`;
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return `${Math.floor(diff / 86400)}d ago`;
  };

  const getStatusBadge = (status: string, lastHeartbeat: string | null) => {
    const isOnline =
      lastHeartbeat && new Date().getTime() - new Date(lastHeartbeat).getTime() < 600000;
    if (status === 'active' && isOnline) {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400">
          <Wifi className="w-3 h-3" /> Online
        </span>
      );
    }
    if (status === 'active') {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400">
          <WifiOff className="w-3 h-3" /> Offline
        </span>
      );
    }
    if (status === 'revoked') {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400">
          <XCircle className="w-3 h-3" /> Revoked
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400">
        <Clock className="w-3 h-3" /> {status}
      </span>
    );
  };

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <div className="flex items-center space-x-4">
          <h1 className="text-2xl font-bold">Endpoints</h1>
          {tenants.length > 0 && (
            <select
              value={selectedTenant}
              onChange={e => setSelectedTenant(e.target.value)}
              className="ml-4 px-3 py-1 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-sm"
            >
              {tenants.map(tenant => (
                <option key={tenant.id} value={tenant.id}>
                  {tenant.name}
                </option>
              ))}
            </select>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={loadData}
            className="flex items-center px-3 py-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
            title="Refresh"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            onClick={handleGenerateToken}
            disabled={generatingToken}
            className="flex items-center px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50"
          >
            <Terminal className="w-4 h-4 mr-2" />
            {generatingToken ? 'Generating...' : 'Generate Enrollment Token'}
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow">
            <div className="flex items-center gap-2 mb-1">
              <Monitor className="w-4 h-4 text-gray-500" />
              <span className="text-sm text-gray-500">Total Devices</span>
            </div>
            <div className="text-2xl font-bold">{summary.total_devices}</div>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow">
            <div className="flex items-center gap-2 mb-1">
              <CheckCircle className="w-4 h-4 text-green-500" />
              <span className="text-sm text-gray-500">Active</span>
            </div>
            <div className="text-2xl font-bold text-green-500">{summary.active_devices}</div>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow">
            <div className="flex items-center gap-2 mb-1">
              <AlertTriangle className="w-4 h-4 text-gray-500" />
              <span className="text-sm text-gray-500">Events (24h)</span>
            </div>
            <div className="text-2xl font-bold">{summary.total_events_24h}</div>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow">
            <div className="flex items-center gap-2 mb-1">
              <XCircle className="w-4 h-4 text-red-500" />
              <span className="text-sm text-gray-500">Critical (24h)</span>
            </div>
            <div className="text-2xl font-bold text-red-500">{summary.critical_events_24h}</div>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow">
            <div className="flex items-center gap-2 mb-1">
              <Shield className="w-4 h-4 text-orange-500" />
              <span className="text-sm text-gray-500">High (24h)</span>
            </div>
            <div className="text-2xl font-bold text-orange-500">{summary.high_events_24h}</div>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex space-x-4 mb-6 border-b border-gray-200 dark:border-gray-700">
        <button
          onClick={() => setActiveTab('devices')}
          className={`flex items-center pb-2 px-1 ${
            activeTab === 'devices'
              ? 'border-b-2 border-blue-500 text-blue-600'
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          <Monitor className="w-5 h-5 mr-2" />
          Devices
        </button>
        <button
          onClick={() => setActiveTab('events')}
          className={`flex items-center pb-2 px-1 ${
            activeTab === 'events'
              ? 'border-b-2 border-blue-500 text-blue-600'
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          <AlertTriangle className="w-5 h-5 mr-2" />
          Events
        </button>
      </div>

      {/* Filters for Events tab */}
      {activeTab === 'events' && (
        <div className="flex gap-4 mb-4">
          <select
            value={severityFilter}
            onChange={e => setSeverityFilter(e.target.value)}
            className="px-3 py-1.5 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-sm"
          >
            <option value="">All Severities</option>
            <option value="CRITICAL">Critical</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
          </select>
          <select
            value={eventTypeFilter}
            onChange={e => setEventTypeFilter(e.target.value)}
            className="px-3 py-1.5 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-sm"
          >
            <option value="">All Types</option>
            {Object.entries(EVENT_TYPE_LABELS).map(([key, label]) => (
              <option key={key} value={key}>
                {label}
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Content */}
      {loading ? (
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
          <p className="mt-2 text-gray-500">Loading...</p>
        </div>
      ) : (
        <>
          {/* Devices Tab */}
          {activeTab === 'devices' && (
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
              <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                <thead className="bg-gray-50 dark:bg-gray-900">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider w-8"></th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Status
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Hostname
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      OS Version
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Agent
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      IP Address
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Last Heartbeat
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Events
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                  {devices.map(device => (
                    <>
                      <tr
                        key={device.id}
                        className="cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
                        onClick={() => handleExpandDevice(device.id)}
                      >
                        <td className="px-6 py-4">
                          {expandedDevice === device.id ? (
                            <ChevronDown className="w-4 h-4 text-gray-400" />
                          ) : (
                            <ChevronRight className="w-4 h-4 text-gray-400" />
                          )}
                        </td>
                        <td className="px-6 py-4">
                          {getStatusBadge(device.status, device.last_heartbeat)}
                        </td>
                        <td className="px-6 py-4 font-medium">{device.hostname}</td>
                        <td className="px-6 py-4 text-gray-500 text-sm">
                          {device.os_version || '-'}
                        </td>
                        <td className="px-6 py-4 text-gray-500 text-sm">
                          {device.agent_version ? (
                            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-400">
                              v{device.agent_version}
                            </span>
                          ) : (
                            '-'
                          )}
                        </td>
                        <td className="px-6 py-4 text-gray-500 text-sm font-mono">
                          {device.ip_address || '-'}
                        </td>
                        <td className="px-6 py-4 text-gray-500 text-sm">
                          {timeAgo(device.last_heartbeat)}
                        </td>
                        <td className="px-6 py-4">
                          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300">
                            {device.event_count}
                          </span>
                        </td>
                      </tr>
                      {/* Expanded Device Events */}
                      {expandedDevice === device.id && (
                        <tr key={`${device.id}-events`}>
                          <td colSpan={8} className="px-0 py-0">
                            <div className="bg-gray-50 dark:bg-gray-900/50 px-8 py-4 border-t border-gray-200 dark:border-gray-700">
                              <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
                                Recent Events for {device.hostname}
                              </h4>
                              {deviceEvents.length === 0 ? (
                                <p className="text-sm text-gray-500 py-2">
                                  No events recorded for this device.
                                </p>
                              ) : (
                                <div className="space-y-2">
                                  {deviceEvents.map(evt => (
                                    <div
                                      key={evt.id}
                                      className="flex items-start gap-3 bg-white dark:bg-gray-800 rounded-lg p-3 border border-gray-200 dark:border-gray-700"
                                    >
                                      <span
                                        className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${SEVERITY_COLORS[evt.severity] || 'bg-gray-100 text-gray-600'}`}
                                      >
                                        {evt.severity}
                                      </span>
                                      <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2">
                                          <span className="text-sm font-medium text-gray-900 dark:text-white">
                                            {evt.title}
                                          </span>
                                          <span className="text-xs text-gray-400 px-1.5 py-0.5 bg-gray-100 dark:bg-gray-700 rounded">
                                            {EVENT_TYPE_LABELS[evt.event_type] || evt.event_type}
                                          </span>
                                        </div>
                                        {evt.description && (
                                          <p className="text-xs text-gray-500 mt-0.5 truncate">
                                            {evt.description}
                                          </p>
                                        )}
                                        {evt.command_line && (
                                          <code className="block text-xs text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-900 rounded px-2 py-1 mt-1 font-mono truncate">
                                            {evt.command_line}
                                          </code>
                                        )}
                                      </div>
                                      <span className="text-xs text-gray-400 whitespace-nowrap">
                                        {timeAgo(evt.detected_at)}
                                      </span>
                                    </div>
                                  ))}
                                </div>
                              )}
                            </div>
                          </td>
                        </tr>
                      )}
                    </>
                  ))}
                  {devices.length === 0 && (
                    <tr>
                      <td colSpan={8} className="px-6 py-12 text-center">
                        <Monitor className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
                        <p className="text-gray-500 dark:text-gray-400 text-lg font-medium">
                          No devices enrolled
                        </p>
                        <p className="text-gray-400 dark:text-gray-500 text-sm mt-1">
                          Generate an enrollment token and install the agent on a Windows device to
                          get started.
                        </p>
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}

          {/* Events Tab */}
          {activeTab === 'events' && (
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
              <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                <thead className="bg-gray-50 dark:bg-gray-900">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Severity
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Type
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Title
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Device
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      User
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Process
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Detected
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                  {events.map(evt => (
                    <tr key={evt.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                      <td className="px-6 py-4">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${SEVERITY_COLORS[evt.severity] || 'bg-gray-100 text-gray-600'}`}
                        >
                          {evt.severity}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-500">
                        {EVENT_TYPE_LABELS[evt.event_type] || evt.event_type}
                      </td>
                      <td className="px-6 py-4">
                        <div className="text-sm font-medium text-gray-900 dark:text-white">
                          {evt.title}
                        </div>
                        {evt.command_line && (
                          <code className="text-xs text-gray-500 font-mono block truncate max-w-xs">
                            {evt.command_line}
                          </code>
                        )}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-500">
                        {evt.hostname || evt.device_id.substring(0, 8)}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-500">
                        {evt.user_context || '-'}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-500 font-mono">
                        {evt.process_name || '-'}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-500">
                        {timeAgo(evt.detected_at)}
                      </td>
                    </tr>
                  ))}
                  {events.length === 0 && (
                    <tr>
                      <td colSpan={7} className="px-6 py-12 text-center">
                        <Shield className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
                        <p className="text-gray-500 dark:text-gray-400 text-lg font-medium">
                          No events detected
                        </p>
                        <p className="text-gray-400 dark:text-gray-500 text-sm mt-1">
                          Events will appear here once endpoint agents start reporting.
                        </p>
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {/* Enrollment Token Modal */}
      {showTokenModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-lg shadow-xl">
            <h2 className="text-xl font-bold mb-2">Enrollment Token Generated</h2>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
              Copy this token and use it when installing the SpecterDefence agent. It cannot be
              retrieved again after closing this dialog.
            </p>
            <div className="relative">
              <code className="block bg-gray-100 dark:bg-gray-900 rounded-lg p-4 text-sm font-mono break-all select-all">
                {enrollmentToken}
              </code>
              <button
                onClick={() => copyToClipboard(enrollmentToken)}
                className="absolute top-2 right-2 p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                title="Copy to clipboard"
              >
                <Copy className="w-4 h-4" />
              </button>
            </div>
            <div className="mt-4 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
              <p className="text-xs text-blue-700 dark:text-blue-400 font-medium mb-1">
                Installation Command:
              </p>
              <code className="text-xs text-blue-600 dark:text-blue-300 font-mono">
                msiexec /i SpecterAgent.msi /quiet ENROLLMENT_TOKEN={enrollmentToken}
              </code>
            </div>
            <div className="flex justify-end mt-4">
              <button
                onClick={() => {
                  setShowTokenModal(false);
                  setEnrollmentToken('');
                }}
                className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
