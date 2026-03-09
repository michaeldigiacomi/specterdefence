import { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'react-hot-toast';
import { useAppStore } from '@/store/appStore';
import Layout from '@/components/Layout';
import ProtectedRoute from '@/components/ProtectedRoute';
import Dashboard from '@/pages/Dashboard';
import Login from '@/pages/Login';
import LoginAnalytics from '@/pages/LoginAnalytics';
import Anomalies from '@/pages/Anomalies';
import Tenants from '@/pages/Tenants';
import MapPage from '@/pages/MapPage';
import AlertFeed from '@/pages/AlertFeed';
import Users from '@/pages/Users';
import Settings from '@/pages/Settings';
import CAPolicies from '@/pages/CAPolicies';
import MailboxRules from '@/pages/MailboxRules';
import MFAReport from '@/pages/MFAReport';
import OAuthApps from '@/pages/OAuthApps';

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

// Public route that redirects to home if already authenticated
function PublicRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAppStore((state) => state.isAuthenticated);

  if (isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <BrowserRouter>
          <Routes>
            {/* Public login route */}
            <Route
              path="/login"
              element={
                <PublicRoute>
                  <Login />
                </PublicRoute>
              }
            />

            {/* Protected routes */}
            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <Layout />
                </ProtectedRoute>
              }
            >
              <Route index element={<Dashboard />} />
              <Route path="analytics" element={<LoginAnalytics />} />
              <Route path="map" element={<MapPage />} />
              <Route path="anomalies" element={<Anomalies />} />
              <Route path="tenants" element={<Tenants />} />
              <Route path="alerts" element={<AlertFeed />} />
              <Route path="users" element={<Users />} />
              <Route path="settings" element={<Settings />} />
              <Route path="ca-policies" element={<CAPolicies />} />
              <Route path="mailbox-rules" element={<MailboxRules />} />
              <Route path="mfa-report" element={<MFAReport />} />
              <Route path="oauth-apps" element={<OAuthApps />} />
            </Route>

            {/* Catch all - redirect to login */}
            <Route path="*" element={<Navigate to="/login" replace />} />
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
