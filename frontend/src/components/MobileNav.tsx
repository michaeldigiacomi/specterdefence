import { useState, useEffect } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  BarChart3,
  Map,
  AlertTriangle,
  Building2,
  Bell,
  Menu,
  X,
  Sun,
  Moon,
  Shield,
  ChevronRight,
  Settings,
  User
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
  { path: '/map', icon: Map, label: 'Map' },
  { path: '/alerts', icon: Bell, label: 'Alerts', badge: true },
  { path: '/anomalies', icon: AlertTriangle, label: 'Anomalies' },
  { path: '/tenants', icon: Building2, label: 'Tenants' },
];

const bottomNavItems = [
  { path: '/', icon: LayoutDashboard, label: 'Home' },
  { path: '/alerts', icon: Bell, label: 'Alerts', badge: true },
  { path: '/analytics', icon: BarChart3, label: 'Stats' },
  { path: '/more', icon: Menu, label: 'More' },
];

export function MobileNav() {
  const [isOpen, setIsOpen] = useState(false);
  const [showInstallPrompt, setShowInstallPrompt] = useState(false);
  const { theme, toggleTheme } = useAppStore();
  const location = useLocation();

  // Handle body scroll lock when menu is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }

    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  // Check for PWA install prompt
  useEffect(() => {
    const handleBeforeInstallPrompt = (e: Event) => {
      e.preventDefault();
      setShowInstallPrompt(true);
    };

    window.addEventListener('beforeinstallprompt', handleBeforeInstallPrompt);

    return () => {
      window.removeEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
    };
  }, []);

  // Close menu on route change
  useEffect(() => {
    setIsOpen(false);
  }, [location.pathname]);

  const handleInstallClick = async () => {
    // @ts-expect-error - deferredPrompt is added by the browser
    const deferredPrompt = window.deferredPrompt;

    if (deferredPrompt) {
      deferredPrompt.prompt();
      const { outcome } = await deferredPrompt.userChoice;

      if (outcome === 'accepted') {
        setShowInstallPrompt(false);
      }
    }
  };

  return (
    <>
      {/* Mobile Header */}
      <header className="lg:hidden fixed top-0 left-0 right-0 z-50 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 safe-area-top">
        <div className="flex items-center justify-between h-14 px-4">
          {/* Logo */}
          <NavLink to="/" className="flex items-center gap-2">
            <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center">
              <Shield className="w-5 h-5 text-white" />
            </div>
            <span className="font-semibold text-gray-900 dark:text-white text-lg">
              SpecterDefence
            </span>
          </NavLink>

          {/* Right Actions */}
          <div className="flex items-center gap-2">
            {/* Install Prompt Button */}
            {showInstallPrompt && (
              <button
                onClick={handleInstallClick}
                className="px-3 py-1.5 bg-blue-500 text-white text-xs font-medium rounded-full"
              >
                Install
              </button>
            )}

            {/* Theme Toggle */}
            <button
              onClick={toggleTheme}
              className="p-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
              aria-label={theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'}
            >
              {theme === 'light' ? (
                <Moon className="w-5 h-5" />
              ) : (
                <Sun className="w-5 h-5" />
              )}
            </button>

            {/* Menu Toggle */}
            <button
              onClick={() => setIsOpen(true)}
              className="p-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
              aria-label="Open menu"
            >
              <Menu className="w-6 h-6" />
            </button>
          </div>
        </div>
      </header>

      {/* Spacer for fixed header */}
      <div className="lg:hidden h-14" />

      {/* Full-screen Navigation Menu */}
      <div
        className={cn(
          'lg:hidden fixed inset-0 z-[60] transition-opacity duration-300',
          isOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'
        )}
      >
        {/* Backdrop */}
        <div
          className="absolute inset-0 bg-black/50 backdrop-blur-sm"
          onClick={() => setIsOpen(false)}
        />

        {/* Menu Panel */}
        <div
          className={cn(
            'absolute right-0 top-0 bottom-0 w-[280px] bg-white dark:bg-gray-900 shadow-xl transition-transform duration-300 ease-out',
            isOpen ? 'translate-x-0' : 'translate-x-full'
          )}
        >
          {/* Menu Header */}
          <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-800 safe-area-top">
            <span className="font-semibold text-gray-900 dark:text-white">Menu</span>
            <button
              onClick={() => setIsOpen(false)}
              className="p-2 text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
              aria-label="Close menu"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Navigation Links */}
          <nav className="p-4 space-y-1">
            {navItems.map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) =>
                  cn(
                    'flex items-center justify-between px-4 py-3 rounded-xl transition-all',
                    isActive
                      ? 'bg-blue-50 text-blue-600 dark:bg-blue-900/20 dark:text-blue-400'
                      : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'
                  )
                }
              >
                <div className="flex items-center gap-3">
                  <item.icon className="w-5 h-5" />
                  <span className="font-medium">{item.label}</span>
                </div>
                {item.badge && (
                  <span className="w-2 h-2 bg-red-500 rounded-full" />
                )}
                <ChevronRight className="w-4 h-4 opacity-50" />
              </NavLink>
            ))}
          </nav>

          {/* Divider */}
          <div className="border-t border-gray-200 dark:border-gray-800 mx-4" />

          {/* Secondary Actions */}
          <div className="p-4 space-y-1">
            <button
              className="flex items-center gap-3 w-full px-4 py-3 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-xl transition-colors"
            >
              <Settings className="w-5 h-5" />
              <span className="font-medium">Settings</span>
            </button>
            <button
              className="flex items-center gap-3 w-full px-4 py-3 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-xl transition-colors"
            >
              <User className="w-5 h-5" />
              <span className="font-medium">Profile</span>
            </button>
          </div>

          {/* App Info */}
          <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-gray-200 dark:border-gray-800 safe-area-bottom">
            <p className="text-xs text-gray-500 dark:text-gray-400 text-center">
              SpecterDefence v1.0.0
            </p>
          </div>
        </div>
      </div>

      {/* Bottom Navigation Bar */}
      <nav className="lg:hidden fixed bottom-0 left-0 right-0 z-50 bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-800 safe-area-bottom">
        <div className="flex items-center justify-around h-16 pb-safe">
          {bottomNavItems.map((item) => {
            const isActive = location.pathname === item.path ||
              (item.path === '/more' && isOpen);

            if (item.path === '/more') {
              return (
                <button
                  key={item.path}
                  onClick={() => setIsOpen(true)}
                  className={cn(
                    'flex flex-col items-center justify-center flex-1 h-full transition-colors',
                    isActive
                      ? 'text-blue-600 dark:text-blue-400'
                      : 'text-gray-500 dark:text-gray-400'
                  )}
                >
                  <item.icon className="w-6 h-6" />
                  <span className="text-xs mt-0.5 font-medium">{item.label}</span>
                </button>
              );
            }

            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive: active }) =>
                  cn(
                    'flex flex-col items-center justify-center flex-1 h-full relative transition-colors',
                    active
                      ? 'text-blue-600 dark:text-blue-400'
                      : 'text-gray-500 dark:text-gray-400'
                  )
                }
              >
                <div className="relative">
                  <item.icon className="w-6 h-6" />
                  {item.badge && (
                    <span className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-red-500 rounded-full border-2 border-white dark:border-gray-900" />
                  )}
                </div>
                <span className="text-xs mt-0.5 font-medium">{item.label}</span>
                {isActive && (
                  <div className="absolute -top-px left-1/2 -translate-x-1/2 w-8 h-0.5 bg-blue-500 rounded-full" />
                )}
              </NavLink>
            );
          })}
        </div>
      </nav>

      {/* Bottom Spacer for fixed bottom nav */}
      <div className="lg:hidden h-16" />
    </>
  );
}

export default MobileNav;
