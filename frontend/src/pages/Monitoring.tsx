import { useState, useEffect } from 'react';
import { 
  Globe, 
  Shield, 
  AlertTriangle, 
  CheckCircle, 
  XCircle, 
  Plus, 
  RefreshCw,
  Search,
  Trash2
} from 'lucide-react';
import { websiteApi, sslApi, domainApi, Website, SslCertificate, Domain, WebsiteStats, SslStats, DomainStats } from '../services/monitoring';
import { apiService } from '../services/api';
import type { Tenant } from '../types';

type TabType = 'websites' | 'ssl' | 'domains';

export default function Monitoring() {
  const [activeTab, setActiveTab] = useState<TabType>('websites');
  const [websites, setWebsites] = useState<Website[]>([]);
  const [sslCerts, setSslCerts] = useState<SslCertificate[]>([]);
  const [domains, setDomains] = useState<Domain[]>([]);
  const [websiteStats, setWebsiteStats] = useState<WebsiteStats | null>(null);
  const [sslStats, setSslStats] = useState<SslStats | null>(null);
  const [domainStats, setDomainStats] = useState<DomainStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [newItem, setNewItem] = useState({ name: '', url: '', domain: '', port: 443 });
  
  // Tenant selection
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [selectedTenant, setSelectedTenant] = useState<string>('');

  useEffect(() => {
    // Load tenants on mount
    apiService.getTenants().then(res => {
      const items = res.items || res;
      setTenants(items);
      if (items.length > 0) {
        setSelectedTenant(items[0].id);
      }
    });
  }, []);

  useEffect(() => {
    if (selectedTenant) {
      loadData();
    }
  }, [activeTab, selectedTenant]);

  const loadData = async () => {
    setLoading(true);
    try {
      if (activeTab === 'websites') {
        const [listRes, statsRes] = await Promise.all([
          websiteApi.list(selectedTenant),
          websiteApi.stats(selectedTenant)
        ]);
        setWebsites(listRes.data);
        setWebsiteStats(statsRes.data);
      } else if (activeTab === 'ssl') {
        const [listRes, statsRes] = await Promise.all([
          sslApi.list(selectedTenant),
          sslApi.stats(selectedTenant)
        ]);
        setSslCerts(listRes.data);
        setSslStats(statsRes.data);
      } else if (activeTab === 'domains') {
        const [listRes, statsRes] = await Promise.all([
          domainApi.list(selectedTenant),
          domainApi.stats(selectedTenant)
        ]);
        setDomains(listRes.data);
        setDomainStats(statsRes.data);
      }
    } catch (error) {
      console.error('Failed to load monitoring data:', error);
    }
    setLoading(false);
  };

  const handleAddWebsite = async () => {
    if (!newItem.name || !newItem.url) return;
    try {
      await websiteApi.create({ name: newItem.name, url: newItem.url }, selectedTenant);
      setShowAddModal(false);
      setNewItem({ name: '', url: '', domain: '', port: 443 });
      loadData();
    } catch (error) {
      console.error('Failed to add website:', error);
    }
  };

  const handleAddSsl = async () => {
    if (!newItem.domain) return;
    try {
      await sslApi.create({ domain: newItem.domain, port: newItem.port }, selectedTenant);
      setShowAddModal(false);
      setNewItem({ name: '', url: '', domain: '', port: 443 });
      loadData();
    } catch (error) {
      console.error('Failed to add SSL certificate:', error);
    }
  };

  const handleAddDomain = async () => {
    if (!newItem.domain) return;
    try {
      await domainApi.create({ domain: newItem.domain }, selectedTenant);
      setShowAddModal(false);
      setNewItem({ name: '', url: '', domain: '', port: 443 });
      loadData();
    } catch (error) {
      console.error('Failed to add domain:', error);
    }
  };

  const handleDelete = async (type: TabType, id: string) => {
    if (!confirm('Are you sure you want to delete this item?')) return;
    try {
      if (type === 'websites') {
        await websiteApi.delete(id, selectedTenant);
      } else if (type === 'ssl') {
        await sslApi.delete(id, selectedTenant);
      } else if (type === 'domains') {
        await domainApi.delete(id, selectedTenant);
      }
      loadData();
    } catch (error) {
      console.error('Failed to delete:', error);
    }
  };

  const handleCheck = async (type: TabType, id: string) => {
    try {
      if (type === 'websites') {
        await websiteApi.check(id, selectedTenant);
      } else if (type === 'ssl') {
        await sslApi.check(id, selectedTenant);
      } else if (type === 'domains') {
        await domainApi.check(id, selectedTenant);
      }
      loadData();
    } catch (error) {
      console.error('Failed to check:', error);
    }
  };

  const getStatusColor = (status: string | null) => {
    switch (status) {
      case 'up': return 'text-green-500';
      case 'down': return 'text-red-500';
      case 'error': return 'text-yellow-500';
      default: return 'text-gray-500';
    }
  };

  const getStatusIcon = (status: string | null) => {
    switch (status) {
      case 'up': return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'down': return <XCircle className="w-5 h-5 text-red-500" />;
      case 'error': return <AlertTriangle className="w-5 h-5 text-yellow-500" />;
      default: return <span className="w-5 h-5 text-gray-400">?</span>;
    }
  };

  const renderWebsites = () => (
    <div className="space-y-4">
      {/* Stats Cards */}
      {websiteStats && (
        <div className="grid grid-cols-2 md:grid-cols-6 gap-4 mb-6">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow">
            <div className="text-2xl font-bold">{websiteStats.total}</div>
            <div className="text-sm text-gray-500">Total</div>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow">
            <div className="text-2xl font-bold text-green-500">{websiteStats.up}</div>
            <div className="text-sm text-gray-500">Up</div>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow">
            <div className="text-2xl font-bold text-red-500">{websiteStats.down}</div>
            <div className="text-sm text-gray-500">Down</div>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow">
            <div className="text-2xl font-bold text-yellow-500">{websiteStats.error}</div>
            <div className="text-sm text-gray-500">Error</div>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow">
            <div className="text-2xl font-bold">{websiteStats.unknown}</div>
            <div className="text-sm text-gray-500">Unknown</div>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow">
            <div className="text-2xl font-bold">{websiteStats.average_uptime}%</div>
            <div className="text-sm text-gray-500">Uptime</div>
          </div>
        </div>
      )}

      {/* Website List */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead className="bg-gray-50 dark:bg-gray-900">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Status</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Name</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">URL</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Response</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Uptime</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
            {websites.map((site) => (
              <tr key={site.id}>
                <td className="px-6 py-4 whitespace-nowrap">
                  {getStatusIcon(site.last_status)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap font-medium">{site.name}</td>
                <td className="px-6 py-4 whitespace-nowrap text-gray-500">{site.url}</td>
                <td className="px-6 py-4 whitespace-nowrap">
                  {site.last_response_code ? (
                    <span className={site.last_response_code >= 400 ? 'text-red-500' : 'text-green-500'}>
                      {site.last_response_code}
                    </span>
                  ) : (
                    <span className="text-gray-400">-</span>
                  )}
                  {site.last_response_time_ms && (
                    <span className="ml-2 text-gray-400">{site.last_response_time_ms.toFixed(0)}ms</span>
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex items-center">
                    <div className="w-16 bg-gray-200 rounded-full h-2 mr-2">
                      <div className="bg-green-500 h-2 rounded-full" style={{ width: `${site.uptime_percentage}%` }}></div>
                    </div>
                    <span className="text-sm">{site.uptime_percentage.toFixed(1)}%</span>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right">
                  <button
                    onClick={() => handleCheck('websites', site.id)}
                    className="text-blue-500 hover:text-blue-700 mr-3"
                  >
                    <RefreshCw className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => handleDelete('websites', site.id)}
                    className="text-red-500 hover:text-red-700"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </td>
              </tr>
            ))}
            {websites.length === 0 && (
              <tr>
                <td colSpan={6} className="px-6 py-4 text-center text-gray-500">
                  No websites configured. Add one to get started.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );

  const renderSsl = () => (
    <div className="space-y-4">
      {/* Stats Cards */}
      {sslStats && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow">
            <div className="text-2xl font-bold">{sslStats.total}</div>
            <div className="text-sm text-gray-500">Total</div>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow">
            <div className="text-2xl font-bold text-green-500">{sslStats.valid}</div>
            <div className="text-sm text-gray-500">Valid</div>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow">
            <div className="text-2xl font-bold text-red-500">{sslStats.expired}</div>
            <div className="text-sm text-gray-500">Expired</div>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow">
            <div className="text-2xl font-bold text-yellow-500">{sslStats.expiring_soon}</div>
            <div className="text-sm text-gray-500">Expiring Soon</div>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow">
            <div className="text-2xl font-bold text-red-500">{sslStats.errors}</div>
            <div className="text-sm text-gray-500">Errors</div>
          </div>
        </div>
      )}

      {/* SSL List */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead className="bg-gray-50 dark:bg-gray-900">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Status</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Domain</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Issuer</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Expires</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
            {sslCerts.map((cert) => (
              <tr key={cert.id}>
                <td className="px-6 py-4 whitespace-nowrap">
                  {cert.has_errors ? (
                    <XCircle className="w-5 h-5 text-red-500" />
                  ) : cert.is_valid ? (
                    <CheckCircle className="w-5 h-5 text-green-500" />
                  ) : (
                    <XCircle className="w-5 h-5 text-red-500" />
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap font-medium">{cert.domain}</td>
                <td className="px-6 py-4 whitespace-nowrap text-gray-500 text-sm">{cert.issuer || '-'}</td>
                <td className="px-6 py-4 whitespace-nowrap">
                  {cert.days_until_expiry !== null ? (
                    <span className={cert.days_until_expiry <= 30 ? 'text-red-500 font-medium' : ''}>
                      {cert.days_until_expiry} days
                    </span>
                  ) : (
                    <span className="text-gray-400">-</span>
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right">
                  <button
                    onClick={() => handleCheck('ssl', cert.id)}
                    className="text-blue-500 hover:text-blue-700 mr-3"
                  >
                    <RefreshCw className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => handleDelete('ssl', cert.id)}
                    className="text-red-500 hover:text-red-700"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </td>
              </tr>
            ))}
            {sslCerts.length === 0 && (
              <tr>
                <td colSpan={5} className="px-6 py-4 text-center text-gray-500">
                  No SSL certificates configured. Add one to get started.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );

  const renderDomains = () => (
    <div className="space-y-4">
      {/* Stats Cards */}
      {domainStats && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow">
            <div className="text-2xl font-bold">{domainStats.total}</div>
            <div className="text-sm text-gray-500">Total</div>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow">
            <div className="text-2xl font-bold text-green-500">{domainStats.active}</div>
            <div className="text-sm text-gray-500">Active</div>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow">
            <div className="text-2xl font-bold text-red-500">{domainStats.expired}</div>
            <div className="text-sm text-gray-500">Expired</div>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow">
            <div className="text-2xl font-bold text-yellow-500">{domainStats.expiring_soon}</div>
            <div className="text-sm text-gray-500">Expiring Soon</div>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow">
            <div className="text-2xl font-bold text-red-500">{domainStats.errors}</div>
            <div className="text-sm text-gray-500">Errors</div>
          </div>
        </div>
      )}

      {/* Domain List */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead className="bg-gray-50 dark:bg-gray-900">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Status</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Domain</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Registrar</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Expires</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
            {domains.map((domain) => (
              <tr key={domain.id}>
                <td className="px-6 py-4 whitespace-nowrap">
                  {domain.whois_error ? (
                    <AlertTriangle className="w-5 h-5 text-yellow-500" />
                  ) : domain.is_expired ? (
                    <XCircle className="w-5 h-5 text-red-500" />
                  ) : (
                    <CheckCircle className="w-5 h-5 text-green-500" />
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap font-medium">{domain.domain}</td>
                <td className="px-6 py-4 whitespace-nowrap text-gray-500 text-sm">{domain.registrar || '-'}</td>
                <td className="px-6 py-4 whitespace-nowrap">
                  {domain.days_until_expiry !== null ? (
                    <span className={domain.days_until_expiry <= 30 ? 'text-red-500 font-medium' : ''}>
                      {domain.days_until_expiry} days
                    </span>
                  ) : (
                    <span className="text-gray-400">-</span>
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right">
                  <button
                    onClick={() => handleCheck('domains', domain.id)}
                    className="text-blue-500 hover:text-blue-700 mr-3"
                  >
                    <RefreshCw className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => handleDelete('domains', domain.id)}
                    className="text-red-500 hover:text-red-700"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </td>
              </tr>
            ))}
            {domains.length === 0 && (
              <tr>
                <td colSpan={5} className="px-6 py-4 text-center text-gray-500">
                  No domains configured. Add one to get started.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <div className="flex items-center space-x-4">
          <h1 className="text-2xl font-bold">Monitoring</h1>
          {tenants.length > 0 && (
            <select
              value={selectedTenant}
              onChange={(e) => setSelectedTenant(e.target.value)}
              className="ml-4 px-3 py-1 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-sm"
            >
              {tenants.map((tenant) => (
                <option key={tenant.id} value={tenant.id}>
                  {tenant.name}
                </option>
              ))}
            </select>
          )}
        </div>
        <button
          onClick={() => setShowAddModal(true)}
          className="flex items-center px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
        >
          <Plus className="w-5 h-5 mr-2" />
          Add {activeTab === 'websites' ? 'Website' : activeTab === 'ssl' ? 'Certificate' : 'Domain'}
        </button>
      </div>

      {/* Tabs */}
      <div className="flex space-x-4 mb-6 border-b border-gray-200 dark:border-gray-700">
        <button
          onClick={() => setActiveTab('websites')}
          className={`flex items-center pb-2 px-1 ${
            activeTab === 'websites'
              ? 'border-b-2 border-blue-500 text-blue-600'
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          <Globe className="w-5 h-5 mr-2" />
          Websites
        </button>
        <button
          onClick={() => setActiveTab('ssl')}
          className={`flex items-center pb-2 px-1 ${
            activeTab === 'ssl'
              ? 'border-b-2 border-blue-500 text-blue-600'
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          <Shield className="w-5 h-5 mr-2" />
          SSL Certificates
        </button>
        <button
          onClick={() => setActiveTab('domains')}
          className={`flex items-center pb-2 px-1 ${
            activeTab === 'domains'
              ? 'border-b-2 border-blue-500 text-blue-600'
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          <AlertTriangle className="w-5 h-5 mr-2" />
          Domain Expiry
        </button>
      </div>

      {/* Content */}
      {loading ? (
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
          <p className="mt-2 text-gray-500">Loading...</p>
        </div>
      ) : (
        <>
          {activeTab === 'websites' && renderWebsites()}
          {activeTab === 'ssl' && renderSsl()}
          {activeTab === 'domains' && renderDomains()}
        </>
      )}

      {/* Add Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-md">
            <h2 className="text-xl font-bold mb-4">
              Add {activeTab === 'websites' ? 'Website' : activeTab === 'ssl' ? 'SSL Certificate' : 'Domain'}
            </h2>
            {activeTab === 'websites' && (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Name</label>
                  <input
                    type="text"
                    value={newItem.name}
                    onChange={(e) => setNewItem({ ...newItem, name: e.target.value })}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm dark:bg-gray-700 dark:border-gray-600"
                    placeholder="My Website"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">URL</label>
                  <input
                    type="text"
                    value={newItem.url}
                    onChange={(e) => setNewItem({ ...newItem, url: e.target.value })}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm dark:bg-gray-700 dark:border-gray-600"
                    placeholder="https://example.com"
                  />
                </div>
                <div className="flex justify-end space-x-2">
                  <button
                    onClick={() => setShowAddModal(false)}
                    className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleAddWebsite}
                    className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
                  >
                    Add
                  </button>
                </div>
              </div>
            )}
            {activeTab === 'ssl' && (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Domain</label>
                  <input
                    type="text"
                    value={newItem.domain}
                    onChange={(e) => setNewItem({ ...newItem, domain: e.target.value })}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm dark:bg-gray-700 dark:border-gray-600"
                    placeholder="example.com"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Port</label>
                  <input
                    type="number"
                    value={newItem.port}
                    onChange={(e) => setNewItem({ ...newItem, port: parseInt(e.target.value) })}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm dark:bg-gray-700 dark:border-gray-600"
                  />
                </div>
                <div className="flex justify-end space-x-2">
                  <button
                    onClick={() => setShowAddModal(false)}
                    className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleAddSsl}
                    className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
                  >
                    Add
                  </button>
                </div>
              </div>
            )}
            {activeTab === 'domains' && (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Domain</label>
                  <input
                    type="text"
                    value={newItem.domain}
                    onChange={(e) => setNewItem({ ...newItem, domain: e.target.value })}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm dark:bg-gray-700 dark:border-gray-600"
                    placeholder="example.com"
                  />
                </div>
                <div className="flex justify-end space-x-2">
                  <button
                    onClick={() => setShowAddModal(false)}
                    className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleAddDomain}
                    className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
                  >
                    Add
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
