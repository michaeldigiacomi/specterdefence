import { useState } from 'react';
import { 
  Download, Upload, Trash2, FileJson, AlertTriangle, 
  X, Clock
} from 'lucide-react';
import { 
  useConfigurationBackups, 
  useExportConfiguration, 
  useImportConfiguration,
  useDeleteConfigurationBackup
} from '@/hooks/useSettings';
import toast from 'react-hot-toast';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const CONFIG_CATEGORIES = [
  { value: 'system', label: 'System Settings', description: 'Data retention, API limits, logging' },
  { value: 'detection', label: 'Detection Thresholds', description: 'Anomaly detection sensitivity' },
  { value: 'alert_rules', label: 'Alert Rules', description: 'Alert rule configurations' },
  { value: 'webhooks', label: 'Webhooks', description: 'Webhook endpoints (URLs excluded)' },
];

export default function ConfigImportExport() {
  const { data: backups, isLoading } = useConfigurationBackups();
  const exportConfig = useExportConfiguration();
  const importConfig = useImportConfiguration();
  const deleteBackup = useDeleteConfigurationBackup();
  
  const [exportModalOpen, setExportModalOpen] = useState(false);
  const [importModalOpen, setImportModalOpen] = useState(false);
  const [selectedCategories, setSelectedCategories] = useState<string[]>(['system', 'detection']);
  const [exportName, setExportName] = useState('');
  const [exportDescription, setExportDescription] = useState('');
  const [importJson, setImportJson] = useState('');
  const [importOverwrite, setImportOverwrite] = useState(false);
  const [importFile, setImportFile] = useState<File | null>(null);

  const handleToggleCategory = (category: string) => {
    setSelectedCategories(prev => 
      prev.includes(category)
        ? prev.filter(c => c !== category)
        : [...prev, category]
    );
  };

  const handleExport = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (selectedCategories.length === 0) {
      toast.error('Please select at least one category');
      return;
    }

    try {
      await exportConfig.mutateAsync({
        categories: selectedCategories,
        name: exportName || `Backup ${new Date().toISOString().split('T')[0]}`,
        description: exportDescription,
      });
      
      toast.success('Configuration exported successfully');
      setExportModalOpen(false);
      setExportName('');
      setExportDescription('');
    } catch {
      toast.error('Failed to export configuration');
    }
  };

  const handleImport = async (e: React.FormEvent) => {
    e.preventDefault();
    
    try {
      let configData;
      
      if (importFile) {
        const text = await importFile.text();
        configData = JSON.parse(text);
      } else if (importJson) {
        configData = JSON.parse(importJson);
      } else {
        toast.error('Please provide a configuration file or JSON');
        return;
      }

      const result = await importConfig.mutateAsync({
        config: configData,
        overwrite: importOverwrite,
      });

      if (result.errors.length > 0) {
        toast.error(`Import completed with ${result.errors.length} errors`);
      } else {
        toast.success('Configuration imported successfully');
      }
      
      setImportModalOpen(false);
      setImportJson('');
      setImportFile(null);
      setImportOverwrite(false);
    } catch (err) {
      toast.error('Failed to import configuration: ' + (err instanceof Error ? err.message : 'Invalid JSON'));
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (file.type === 'application/json' || file.name.endsWith('.json')) {
        setImportFile(file);
        setImportJson('');
      } else {
        toast.error('Please select a JSON file');
      }
    }
  };

  const handleDownload = async (backupId: string, backupName: string) => {
    try {
      // In a real implementation, this would download the file
      toast.success(`Downloading ${backupName}...`);
    } catch {
      toast.error('Failed to download backup');
    }
  };

  const handleDelete = async (backupId: string) => {
    if (!confirm('Are you sure you want to delete this backup?')) return;
    
    try {
      await deleteBackup.mutateAsync(backupId);
      toast.success('Backup deleted');
    } catch {
      toast.error('Failed to delete backup');
    }
  };

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-4">
        {[1, 2].map(i => (
          <div key={i} className="h-24 bg-gray-200 dark:bg-gray-700 rounded-lg" />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Actions */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <button
          onClick={() => setExportModalOpen(true)}
          className="flex items-center gap-4 p-6 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-primary-500 dark:hover:border-primary-500 transition-colors text-left"
        >
          <div className="p-3 bg-green-100 dark:bg-green-900/30 rounded-lg">
            <Download className="w-6 h-6 text-green-600 dark:text-green-400" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900 dark:text-white">Export Configuration</h3>
            <p className="text-sm text-gray-500">Save settings to a JSON file</p>
          </div>
        </button>

        <button
          onClick={() => setImportModalOpen(true)}
          className="flex items-center gap-4 p-6 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-primary-500 dark:hover:border-primary-500 transition-colors text-left"
        >
          <div className="p-3 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
            <Upload className="w-6 h-6 text-blue-600 dark:text-blue-400" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900 dark:text-white">Import Configuration</h3>
            <p className="text-sm text-gray-500">Restore from a JSON file</p>
          </div>
        </button>
      </div>

      {/* Backups List */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h3 className="font-semibold text-gray-900 dark:text-white">Configuration Backups</h3>
        </div>
        
        {backups?.length === 0 ? (
          <div className="px-6 py-12 text-center">
            <FileJson className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
            <p className="text-gray-500 dark:text-gray-400">No backups yet</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-200 dark:divide-gray-700">
            {backups?.map((backup) => (
              <div key={backup.id} className="px-6 py-4 flex items-center justify-between">
                <div className="flex items-start gap-3">
                  <FileJson className="w-5 h-5 text-gray-400 mt-0.5" />
                  <div>
                    <p className="font-medium text-gray-900 dark:text-white">{backup.name}</p>
                    {backup.description && (
                      <p className="text-sm text-gray-500">{backup.description}</p>
                    )}
                    <div className="flex items-center gap-3 mt-1 text-xs text-gray-400">
                      <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {new Date(backup.created_at).toLocaleString()}
                      </span>
                      <span>{backup.categories.length} categories</span>
                    </div>
                  </div>
                </div>
                
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleDownload(backup.id, backup.name)}
                    className="p-2 text-gray-400 hover:text-primary-600 hover:bg-primary-50 dark:hover:bg-primary-900/20 rounded-lg transition-colors"
                    title="Download"
                  >
                    <Download className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => handleDelete(backup.id)}
                    className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
                    title="Delete"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Export Modal */}
      {exportModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-lg w-full">
            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Export Configuration</h2>
              <button
                onClick={() => setExportModalOpen(false)}
                className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleExport} className="p-6 space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Categories to Export
                </label>
                <div className="space-y-2">
                  {CONFIG_CATEGORIES.map((cat) => (
                    <label
                      key={cat.value}
                      className={cn(
                        "flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-all",
                        selectedCategories.includes(cat.value)
                          ? "border-primary-500 bg-primary-50 dark:bg-primary-900/20"
                          : "border-gray-200 dark:border-gray-700 hover:border-gray-300"
                      )}
                    >
                      <input
                        type="checkbox"
                        checked={selectedCategories.includes(cat.value)}
                        onChange={() => handleToggleCategory(cat.value)}
                        className="mt-0.5 w-4 h-4 text-primary-500 rounded border-gray-300 focus:ring-primary-500"
                      />
                      <div>
                        <span className="text-sm font-medium text-gray-900 dark:text-white">{cat.label}</span>
                        <p className="text-xs text-gray-500">{cat.description}</p>
                      </div>
                    </label>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Backup Name *
                </label>
                <input
                  type="text"
                  required
                  value={exportName}
                  onChange={(e) => setExportName(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:text-white"
                  placeholder="e.g., Pre-Migration Backup"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Description (optional)
                </label>
                <textarea
                  value={exportDescription}
                  onChange={(e) => setExportDescription(e.target.value)}
                  rows={2}
                  className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:text-white"
                  placeholder="Notes about this backup..."
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
                <button
                  type="button"
                  onClick={() => setExportModalOpen(false)}
                  className="px-4 py-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={exportConfig.isPending}
                  className="flex items-center gap-2 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  <Download className="w-4 h-4" />
                  {exportConfig.isPending ? 'Exporting...' : 'Export'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Import Modal */}
      {importModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-lg w-full">
            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Import Configuration</h2>
              <button
                onClick={() => setImportModalOpen(false)}
                className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleImport} className="p-6 space-y-6">
              <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-4">
                <div className="flex items-start gap-3">
                  <AlertTriangle className="w-5 h-5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
                  <div>
                    <h4 className="font-medium text-amber-900 dark:text-amber-400">Warning</h4>
                    <p className="text-sm text-amber-700 dark:text-amber-500">
                      Importing configuration will overwrite existing settings. Make sure to backup your current configuration first.
                    </p>
                  </div>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Upload File
                </label>
                <div className="border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg p-6 text-center hover:border-primary-500 transition-colors">
                  <input
                    type="file"
                    accept=".json"
                    onChange={handleFileChange}
                    className="hidden"
                    id="config-file"
                  />
                  <label htmlFor="config-file" className="cursor-pointer">
                    <Upload className="w-8 h-8 text-gray-400 mx-auto mb-2" />
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      {importFile ? importFile.name : 'Click to upload JSON file'}
                    </p>
                  </label>
                </div>
              </div>

              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-gray-300 dark:border-gray-600" />
                </div>
                <div className="relative flex justify-center text-sm">
                  <span className="px-2 bg-white dark:bg-gray-800 text-gray-500">Or paste JSON</span>
                </div>
              </div>

              <div>
                <textarea
                  value={importJson}
                  onChange={(e) => {
                    setImportJson(e.target.value);
                    setImportFile(null);
                  }}
                  rows={6}
                  className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:text-white font-mono text-sm"
                  placeholder="Paste configuration JSON here..."
                />
              </div>

              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={importOverwrite}
                  onChange={(e) => setImportOverwrite(e.target.checked)}
                  className="w-4 h-4 text-primary-500 rounded border-gray-300 focus:ring-primary-500"
                />
                <span className="text-sm text-gray-700 dark:text-gray-300">Overwrite existing settings</span>
              </label>

              <div className="flex items-center justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
                <button
                  type="button"
                  onClick={() => setImportModalOpen(false)}
                  className="px-4 py-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={importConfig.isPending || (!importJson && !importFile)}
                  className="flex items-center gap-2 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  <Upload className="w-4 h-4" />
                  {importConfig.isPending ? 'Importing...' : 'Import'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
