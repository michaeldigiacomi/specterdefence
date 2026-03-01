import { useEffect } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'react-hot-toast';
import { useAppStore } from '@/store/appStore';
import Layout from '@/components/Layout';
import Dashboard from '@/pages/Dashboard';
import LoginAnalytics from '@/pages/LoginAnalytics';
import Anomalies from '@/pages/Anomalies';
import Tenants from '@/pages/Tenants';
import MapPage from '@/pages/MapPage';
import AlertFeed from '@/pages/AlertFeed';
import Settings from '@/pages/Settings';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      refetchOnWindowFocus: false,
    },
  },
});

function ThemeProvider({ children }: { children: React.ReactNode }) {
  const { theme } = useAppStore();

  useEffect(() => {
    const root = document.documentElement;
    if (theme === 'dark') {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
  }, [theme]);

  return <>{children}</>;
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Layout />}>
              <Route index element={<Dashboard />} />
              <Route path="analytics" element={<LoginAnalytics />} />
              <Route path="map" element={<MapPage />} />
              <Route path="anomalies" element={<Anomalies />} />
              <Route path="tenants" element={<Tenants />} />
              <Route path="alerts" element={<AlertFeed />} />
              <Route path="settings" element={<Settings />} />
            </Route>
          </Routes>
        </BrowserRouter>
        <Toaster 
          position="top-right"
          toastOptions={{
            duration: 4000,
            className: 'dark:bg-gray-800 dark:text-white',
          }}
        />
      </ThemeProvider>
    </QueryClientProvider>
  );
}

export default App;
