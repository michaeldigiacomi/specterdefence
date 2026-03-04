import { useState } from 'react';
import { Settings, Bell, Shield, Globe, Key, Upload } from 'lucide-react';
import {
  SystemSettings,
  UserPreferences,
  DetectionSettings,
  AlertRuleBuilder,
  WebhookManager,
  ApiKeyManager,
  ConfigImportExport,
} from '@/components/settings';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const tabs = [
  { id: 'general', label: 'General', icon: Settings, component: SystemSettings },
  { id: 'notifications', label: 'Notifications', icon: Bell, component: UserPreferences },
  { id: 'detection', label: 'Detection', icon: Shield, component: DetectionSettings },
  { id: 'rules', label: 'Alert Rules', icon: Bell, component: AlertRuleBuilder },
  { id: 'webhooks', label: 'Webhooks', icon: Globe, component: WebhookManager },
  { id: 'apikeys', label: 'API Keys', icon: Key, component: ApiKeyManager },
  { id: 'backup', label: 'Import/Export', icon: Upload, component: ConfigImportExport },
];

// Mock user email - in a real app, this would come from auth context
const CURRENT_USER_EMAIL = 'admin@specterdefence.local';

// Component renderer that handles props for components that need them
function renderActiveComponent(activeTab: string) {
  switch (activeTab) {
    case 'notifications':
      return <UserPreferences userEmail={CURRENT_USER_EMAIL} />;
    case 'general':
      return <SystemSettings />;
    case 'detection':
      return <DetectionSettings />;
    case 'rules':
      return <AlertRuleBuilder />;
    case 'webhooks':
      return <WebhookManager />;
    case 'apikeys':
      return <ApiKeyManager />;
    case 'backup':
      return <ConfigImportExport />;
    default:
      return <SystemSettings />;
  }
}

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState('general');

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
          <Settings className="w-6 h-6 text-primary-500" />
          Settings
        </h1>
        <p className="mt-1 text-gray-500 dark:text-gray-400">
          Manage your SpecterDefence configuration
        </p>
      </div>

      <div className="flex flex-col lg:flex-row gap-6">
        {/* Sidebar Navigation */}
        <aside className="w-full lg:w-64 flex-shrink-0">
          <nav className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
            <ul className="divide-y divide-gray-200 dark:divide-gray-700">
              {tabs.map((tab) => {
                const Icon = tab.icon;
                return (
                  <li key={tab.id}>
                    <button
                      onClick={() => setActiveTab(tab.id)}
                      className={cn(
                        'w-full flex items-center gap-3 px-4 py-3 text-left transition-colors',
                        activeTab === tab.id
                          ? 'bg-primary-50 text-primary-600 dark:bg-primary-900/20 dark:text-primary-400 border-r-2 border-primary-500'
                          : 'text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700'
                      )}
                    >
                      <Icon className="w-5 h-5" />
                      <span className="font-medium">{tab.label}</span>
                    </button>
                  </li>
                );
              })}
            </ul>
          </nav>
        </aside>

        {/* Main Content */}
        <main className="flex-1 min-w-0">
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
            <div className="mb-6">
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                {tabs.find(t => t.id === activeTab)?.label}
              </h2>
            </div>

            {renderActiveComponent(activeTab)}
          </div>
        </main>
      </div>
    </div>
  );
}
