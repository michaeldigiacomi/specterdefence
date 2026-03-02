import { useEffect } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { useAppStore } from '@/store/appStore';
import { useAuthCheck } from '@/hooks/useAuth';

interface ProtectedRouteProps {
  children: React.ReactNode;
}

export default function ProtectedRoute({ children }: ProtectedRouteProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const isAuthenticated = useAppStore((state) => state.isAuthenticated);
  const token = useAppStore((state) => state.token);
  
  // Use auth check to verify token is still valid
  const { isLoading, isError } = useAuthCheck();

  useEffect(() => {
    // If we have a token but auth check failed, redirect to login
    if (token && isError) {
      navigate('/login', { replace: true });
    }
  }, [token, isError, navigate]);

  // Show loading state while checking auth
  if (isLoading && token) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
        <div className="flex flex-col items-center">
          <svg className="animate-spin h-10 w-10 text-primary-600 mb-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <p className="text-gray-600 dark:text-gray-400">Verifying session...</p>
        </div>
      </div>
    );
  }

  // Redirect to login if not authenticated
  if (!isAuthenticated || !token) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Render children if authenticated
  return <>{children}</>;
}
