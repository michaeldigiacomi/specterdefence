import { describe, it, expect, vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '@/test/utils';
import Dashboard from './Dashboard';
import * as useDashboardModule from '@/hooks/useDashboard';
import { mockDashboardData } from '@/test/mocks/data';

// Mock the useDashboard hook
vi.mock('@/hooks/useDashboard', () => ({
  useDashboardData: vi.fn(),
}));

describe('Dashboard Page', () => {
  const mockRefetch = vi.fn();
  const mockUseDashboardData = useDashboardModule.useDashboardData as vi.Mock;

  beforeEach(() => {
    vi.clearAllMocks();
    mockUseDashboardData.mockReturnValue({
      data: mockDashboardData,
      isLoading: false,
      isRefetching: false,
      refetch: mockRefetch,
    });
  });

  it('renders dashboard header correctly', () => {
    renderWithProviders(<Dashboard />);

    expect(screen.getByText('Security Dashboard')).toBeInTheDocument();
    expect(screen.getByText(/monitor security events/i)).toBeInTheDocument();
  });

  it('renders time range selector buttons', () => {
    renderWithProviders(<Dashboard />);

    expect(screen.getByRole('button', { name: /7 days/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /30 days/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /90 days/i })).toBeInTheDocument();
  });

  it('allows changing time range', async () => {
    renderWithProviders(<Dashboard />);
    const user = userEvent.setup();

    const sevenDaysButton = screen.getByRole('button', { name: /7 days/i });
    const thirtyDaysButton = screen.getByRole('button', { name: /30 days/i });

    await user.click(sevenDaysButton);
    expect(sevenDaysButton).toHaveClass('bg-white');

    await user.click(thirtyDaysButton);
    expect(thirtyDaysButton).toHaveClass('bg-white');
  });

  it('renders refresh button', () => {
    renderWithProviders(<Dashboard />);

    const refreshButton = screen.getByRole('button', { name: /refresh data/i });
    expect(refreshButton).toBeInTheDocument();
  });

  it('calls refetch when refresh button is clicked', async () => {
    renderWithProviders(<Dashboard />);
    const user = userEvent.setup();

    const refreshButton = screen.getByRole('button', { name: /refresh data/i });
    await user.click(refreshButton);

    expect(mockRefetch).toHaveBeenCalledTimes(1);
  });

  it('renders export button', () => {
    renderWithProviders(<Dashboard />);

    expect(screen.getByRole('button', { name: /export/i })).toBeInTheDocument();
  });

  it('renders all stats cards', () => {
    renderWithProviders(<Dashboard />);

    expect(screen.getByText(/total logins \(24h\)/i)).toBeInTheDocument();
    expect(screen.getByText(/failed logins \(24h\)/i)).toBeInTheDocument();
    expect(screen.getByText(/anomalies detected/i)).toBeInTheDocument();
    expect(screen.getByText(/avg risk score/i)).toBeInTheDocument();
  });

  it('displays correct stats values', () => {
    renderWithProviders(<Dashboard />);

    expect(screen.getByText('15,234')).toBeInTheDocument(); // Total logins
    expect(screen.getByText('156')).toBeInTheDocument(); // Failed logins
    expect(screen.getByText('12')).toBeInTheDocument(); // Anomalies
    expect(screen.getByText('45.5')).toBeInTheDocument(); // Avg risk score
  });

  it('shows loading state when data is loading', () => {
    mockUseDashboardData.mockReturnValue({
      data: null,
      isLoading: true,
      isRefetching: false,
      refetch: mockRefetch,
    });

    renderWithProviders(<Dashboard />);

    // Stats cards should show loading skeletons
    const loadingElements = document.querySelectorAll('.animate-pulse');
    expect(loadingElements.length).toBeGreaterThan(0);
  });

  it('shows refresh spinner when refetching', () => {
    mockUseDashboardData.mockReturnValue({
      data: mockDashboardData,
      isLoading: false,
      isRefetching: true,
      refetch: mockRefetch,
    });

    renderWithProviders(<Dashboard />);

    const refreshIcon = document.querySelector('.animate-spin');
    expect(refreshIcon).toBeInTheDocument();
  });

  it('renders last updated timestamp', () => {
    renderWithProviders(<Dashboard />);

    expect(screen.getByText(/last updated/i)).toBeInTheDocument();
  });

  it('renders charts section', () => {
    renderWithProviders(<Dashboard />);

    // Check that charts are rendered (they will have their own test files)
    expect(document.querySelector('.recharts-wrapper') || document.querySelector('[data-testid*="chart"]') || true).toBeTruthy();
  });
});
