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
  Settings,
  LogOut,
  User,
  KeyRound,
  ShieldCheck,
  Mail,
  AppWindow,
  Users as UserIcon,
  Globe,
} from 'lucide-react';
import { useAppStore } from '@/store/appStore';
import { useLogout } from '@/hooks/useAuth';
import { ChangePasswordDialog } from './ChangePasswordDialog';
import { useState, useEffect } from 'react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const FRONTEND_SHA = import.meta.env.VITE_GIT_SHA || 'dev';

const navItems = [
  { path: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { path: '/analytics', icon: BarChart3, label: 'Analytics' },
  { path: '/map', icon: Map, label: 'Geographic Map' },
  { path: '/alerts', icon: Bell, label: 'Live Alerts' },
  { path: '/anomalies', icon: AlertTriangle, label: 'Anomalies' },
  { path: '/ca-policies', icon: ShieldCheck, label: 'CA Policies' },
  { path: '/mailbox-rules', icon: Mail, label: 'Mailbox Rules' },
  { path: '/mfa-report', icon: KeyRound, label: 'MFA Report' },
  { path: '/oauth-apps', icon: AppWindow, label: 'OAuth Apps' },
  { path: '/monitoring', icon: Globe, label: 'Monitoring' },
  { path: '/tenants', icon: Building2, label: 'Tenants' },
  { path: '/users', icon: UserIcon, label: 'Users' },
  { path: '/settings', icon: Settings, label: 'Settings' },
];

export default function Sidebar() {
  const { sidebarOpen, toggleSidebar, theme, toggleTheme, user } = useAppStore();
  const logoutMutation = useLogout();
  const [isChangePasswordOpen, setIsChangePasswordOpen] = useState(false);
  const [backendSha, setBackendSha] = useState<string>('...');

  useEffect(() => {
    fetch('/api/v1/version')
      .then(res => {
        if (!res.ok) throw new Error('not ok');
        return res.json();
      })
      .then(data => setBackendSha(data.git_sha || 'unknown'))
      .catch(() => setBackendSha('unknown'));
  }, []);

  const handleLogout = () => {
    logoutMutation.mutate();
  };

  const shortSha = (sha: string) => (sha.length > 7 ? sha.substring(0, 7) : sha);

  return (
    <aside
      className={cn(
        'fixed left-0 top-0 z-50 h-screen bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 transition-all duration-300 flex flex-col',
        sidebarOpen ? 'w-64' : 'w-16'
      )}
    >
      {/* Logo Section */}
      <div
        className="flex items-center justify-between px-4 border-b border-gray-200 dark:border-gray-700"
        style={{ minHeight: sidebarOpen ? '4.5rem' : '4rem' }}
      >
        <div className="flex items-center gap-3 overflow-hidden">
          <div className="flex-shrink-0 w-8 h-8 bg-primary-500 rounded-lg flex items-center justify-center">
            <Shield className="w-5 h-5 text-white" />
          </div>
          <div
            className={cn(
              'whitespace-nowrap transition-opacity duration-300',
              sidebarOpen ? 'opacity-100' : 'opacity-0'
            )}
          >
            <span className="font-semibold text-lg text-gray-900 dark:text-white block leading-tight">
              SpecterDefence
            </span>
            {sidebarOpen && (
              <div className="flex gap-3 text-[10px] font-mono text-gray-400 dark:text-gray-500 mt-0.5">
                <span title={`Frontend: ${FRONTEND_SHA}`}>FE: {shortSha(FRONTEND_SHA)}</span>
                <span title={`Backend: ${backendSha}`}>BE: {shortSha(backendSha)}</span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4 overflow-y-auto">
        <ul className="space-y-1 px-2">
          {navItems.map(item => (
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
        {/* User Info (when expanded) */}
        {user && sidebarOpen && (
          <div className="mb-3 px-3 py-2 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-primary-100 dark:bg-primary-900/30 rounded-full flex items-center justify-center">
                <User className="w-4 h-4 text-primary-600 dark:text-primary-400" />
              </div>
              <div className="overflow-hidden">
                <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                  {user.username}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                  {user.is_admin ? 'Administrator' : 'User'}
                </p>
              </div>
            </div>
            {/* Change Password Button */}
            <button
              onClick={() => setIsChangePasswordOpen(true)}
              className="flex items-center gap-2 w-full mt-2 px-2 py-1.5 text-xs text-primary-600 dark:text-primary-400 hover:bg-primary-50 dark:hover:bg-primary-900/20 rounded-md transition-colors"
              title="Change Password"
            >
              <KeyRound className="w-3.5 h-3.5" />
              <span>Change Password</span>
            </button>
          </div>
        )}

        {/* Change Password Dialog */}
        <ChangePasswordDialog
          isOpen={isChangePasswordOpen}
          onClose={() => setIsChangePasswordOpen(false)}
        />

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
          <Menu
            className={cn(
              'w-5 h-5 flex-shrink-0 transition-transform duration-300',
              sidebarOpen && 'rotate-180'
            )}
          />
          <span
            className={cn(
              'whitespace-nowrap transition-opacity duration-300',
              sidebarOpen ? 'opacity-100' : 'opacity-0'
            )}
          >
            Collapse
          </span>
        </button>

        {/* Logout Button */}
        <button
          onClick={handleLogout}
          disabled={logoutMutation.isPending}
          className="flex items-center gap-3 w-full px-3 py-2.5 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors mt-1 disabled:opacity-50"
          title="Logout"
        >
          {logoutMutation.isPending ? (
            <>
              <svg
                className="animate-spin h-5 w-5 flex-shrink-0"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                ></circle>
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                ></path>
              </svg>
              <span
                className={cn(
                  'whitespace-nowrap transition-opacity duration-300',
                  sidebarOpen ? 'opacity-100' : 'opacity-0'
                )}
              >
                Logging out...
              </span>
            </>
          ) : (
            <>
              <LogOut className="w-5 h-5 flex-shrink-0" />
              <span
                className={cn(
                  'whitespace-nowrap transition-opacity duration-300',
                  sidebarOpen ? 'opacity-100' : 'opacity-0'
                )}
              >
                Logout
              </span>
            </>
          )}
        </button>
      </div>
    </aside>
  );
}
