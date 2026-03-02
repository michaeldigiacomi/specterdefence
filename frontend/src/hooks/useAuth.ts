import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import apiService from '@/services/api';
import { useAppStore } from '@/store/appStore';
import { LoginRequest } from '@/types';

export const queryKeys = {
  auth: () => ['auth'] as const,
  user: () => ['user'] as const,
};

// ============== Authentication Hooks ==============

export function useLogin() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const login = useAppStore((state) => state.login);
  const setUser = useAppStore((state) => state.setUser);

  return useMutation({
    mutationFn: (data: LoginRequest) => apiService.login(data),
    onSuccess: async (data) => {
      // Store token in app state
      login(data.access_token);
      
      // Fetch current user info
      try {
        const user = await apiService.getCurrentUser();
        setUser(user);
      } catch {
        // If fetching user fails, still continue with login
        setUser({ username: 'admin', is_authenticated: true });
      }
      
      // Invalidate and refetch auth queries
      queryClient.invalidateQueries({ queryKey: queryKeys.auth() });
      
      toast.success('Login successful!');
      navigate('/');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Login failed. Please check your credentials.');
    },
  });
}

export function useLogout() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const logout = useAppStore((state) => state.logout);

  return useMutation({
    mutationFn: () => apiService.logout(),
    onSuccess: () => {
      // Clear auth state
      logout();
      
      // Clear all queries from cache
      queryClient.clear();
      
      toast.success('Logged out successfully');
      navigate('/login');
    },
    onError: () => {
      // Even if server logout fails, clear local state
      logout();
      queryClient.clear();
      navigate('/login');
    },
  });
}

export function useAuthCheck() {
  const setUser = useAppStore((state) => state.setUser);
  const login = useAppStore((state) => state.login);
  const logout = useAppStore((state) => state.logout);
  const token = useAppStore((state) => state.token);

  return useQuery({
    queryKey: queryKeys.auth(),
    queryFn: async () => {
      try {
        const response = await apiService.checkAuth();
        if (response.authenticated) {
          setUser({ username: response.username, is_authenticated: true });
          return response;
        }
        // If not authenticated, clear state
        logout();
        return null;
      } catch {
        // If check fails, clear state
        logout();
        return null;
      }
    },
    enabled: !!token, // Only run if we have a token
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: false,
  });
}

export function useCurrentUser() {
  return useQuery({
    queryKey: queryKeys.user(),
    queryFn: () => apiService.getCurrentUser(),
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: false,
  });
}
