import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, 
  BarChart3, 
  Map, 
  AlertTriangle, 
  Building2, 
  Menu,
  Sun,
  Moon,
  Shield,
  Bell,
  Settings
} from 'lucide-react';
import { useAppStore } from '@/store/appStore';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const navItems = [
  { path: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { path: '/analytics', icon: BarChart3, label: 'Analytics' },
  { path: '/map', icon: Map, label: 'Geographic Map' },
  { path: '/alerts', icon: Bell, label: 'Live Alerts' },
  { path: '/anomalies', icon: AlertTriangle, label: 'Anomalies' },
  { path: '/tenants', icon: Building2, label: 'Tenants' },
  { path: '/settings', icon: Settings, label: 'Settings' },
];

export default function Sidebar() {
  const { sidebarOpen, toggleSidebar, theme, toggleTheme } = useAppStore();

  return (
    <aside
      className={cn(
        'fixed left-0 top-0 z-50 h-screen bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 transition-all duration-300 flex flex-col',
        sidebarOpen ? 'w-64' : 'w-16'
      )}
    >
      {/* Logo Section */}
      <div className="flex items-center justify-between h-16 px-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-3 overflow-hidden">
          <div className="flex-shrink-0 w-8 h-8 bg-primary-500 rounded-lg flex items-center justify-center">
            <Shield className="w-5 h-5 text-white" />
          </div>
          <span 
            className={cn(
              'font-semibold text-lg text-gray-900 dark:text-white whitespace-nowrap transition-opacity duration-300',
              sidebarOpen ? 'opacity-100' : 'opacity-0'
            )}
          >
            SpecterDefence
          </span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4 overflow-y-auto">
        <ul className="space-y-1 px-2">
          {navItems.map((item) => (
            <li key={item.path}>
              <NavLink
                to={item.path}
                className={({ isActive }) =>
                  cn(
                    'flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors',
                    isActive
                      ? 'bg-primary-50 text-primary-600 dark:bg-primary-900/20 dark:text-primary-400'
                      : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
                  )
                }
              >
                <item.icon className="w-5 h-5 flex-shrink-0" />
                <span 
                  className={cn(
                    'whitespace-nowrap transition-opacity duration-300',
                    sidebarOpen ? 'opacity-100' : 'opacity-0'
                  )}
                >
                  {item.label}
                </span>
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      {/* Bottom Actions */}
      <div className="p-2 border-t border-gray-200 dark:border-gray-700">
        <button
          onClick={toggleTheme}
          className="flex items-center gap-3 w-full px-3 py-2.5 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
          title={theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'}
        >
          {theme === 'light' ? (
            <Moon className="w-5 h-5 flex-shrink-0" />
          ) : (
            <Sun className="w-5 h-5 flex-shrink-0" />
          )}
          <span 
            className={cn(
              'whitespace-nowrap transition-opacity duration-300',
              sidebarOpen ? 'opacity-100' : 'opacity-0'
            )}
          >
            {theme === 'light' ? 'Dark Mode' : 'Light Mode'}
          </span>
        </button>

        <button
          onClick={toggleSidebar}
          className="flex items-center gap-3 w-full px-3 py-2.5 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors mt-1"
          title={sidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}
        >
          <Menu className={cn(
            'w-5 h-5 flex-shrink-0 transition-transform duration-300',
            sidebarOpen && 'rotate-180'
          )} />
          <span 
            className={cn(
              'whitespace-nowrap transition-opacity duration-300',
              sidebarOpen ? 'opacity-100' : 'opacity-0'
            )}
          >
            Collapse
          </span>
        </button>
      </div>
    </aside>
  );
}
