import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import { MobileNav } from './MobileNav';
import { useAppStore } from '@/store/appStore';

export default function Layout() {
  const { sidebarOpen } = useAppStore();

  return (
    <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
      {/* Desktop Sidebar */}
      <div className="hidden lg:block">
        <Sidebar />
      </div>
      
      {/* Mobile Navigation */}
      <MobileNav />
      
      {/* Main Content */}
      <main 
        className={`flex-1 overflow-auto transition-all duration-300 lg:ml-0 ${
          sidebarOpen ? 'lg:ml-64' : 'lg:ml-16'
        }`}
      >
        <div className="p-4 lg:p-6">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
