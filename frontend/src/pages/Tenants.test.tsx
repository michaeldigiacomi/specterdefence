import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '@/test/utils';
import Tenants from './Tenants';
import * as useApiModule from '@/hooks/useApi';
import { mockTenants } from '@/test/mocks/data';

// Mock the useApi hooks
vi.mock('@/hooks/useApi', () => ({
  useTenants: vi.fn(),
  useCreateTenant: vi.fn(),
  useUpdateTenant: vi.fn(),
  useDeleteTenant: vi.fn(),
  useValidateTenant: vi.fn(),
}));

describe('Tenants Page', () => {
  const mockCreateMutateAsync = vi.fn();
  const mockUpdateMutateAsync = vi.fn();
  const mockDeleteMutateAsync = vi.fn();
  const mockValidateMutateAsync = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    
    (useApiModule.useTenants as vi.Mock).mockReturnValue({
      data: { items: mockTenants, total: mockTenants.length },
      isLoading: false,
    });
    
    (useApiModule.useCreateTenant as vi.Mock).mockReturnValue({
      mutateAsync: mockCreateMutateAsync,
      isPending: false,
    });
    
    (useApiModule.useUpdateTenant as vi.Mock).mockReturnValue({
      mutateAsync: mockUpdateMutateAsync,
      isPending: false,
    });
    
    (useApiModule.useDeleteTenant as vi.Mock).mockReturnValue({
      mutateAsync: mockDeleteMutateAsync,
      isPending: false,
    });
    
    (useApiModule.useValidateTenant as vi.Mock).mockReturnValue({
      mutateAsync: mockValidateMutateAsync,
      isPending: false,
    });
  });

  it('renders tenants page header', () => {
    renderWithProviders(<Tenants />);

    expect(screen.getByText('Tenants')).toBeInTheDocument();
    expect(screen.getByText(/manage your microsoft 365 tenant connections/i)).toBeInTheDocument();
  });

  it('renders add tenant button', () => {
    renderWithProviders(<Tenants />);

    expect(screen.getByRole('button', { name: /add tenant/i })).toBeInTheDocument();
  });

  it('renders tenant stats cards', () => {
    renderWithProviders(<Tenants />);

    expect(screen.getByText(/total tenants/i)).toBeInTheDocument();
    expect(screen.getByText(/active/i)).toBeInTheDocument();
    expect(screen.getByText(/inactive/i)).toBeInTheDocument();
  });

  it('displays correct tenant count in stats', () => {
    renderWithProviders(<Tenants />);

    expect(screen.getByText('3')).toBeInTheDocument(); // Total
  });

  it('renders tenants table with data', () => {
    renderWithProviders(<Tenants />);

    expect(screen.getByText('Contoso Production')).toBeInTheDocument();
    expect(screen.getByText('Fabrikam Test')).toBeInTheDocument();
    expect(screen.getByText('Inactive Tenant')).toBeInTheDocument();
  });

  it('shows tenant IDs in the table', () => {
    renderWithProviders(<Tenants />);

    expect(screen.getByText('12345678-1234-1234-1234-123456789012')).toBeInTheDocument();
  });

  it('displays active status badge correctly', () => {
    renderWithProviders(<Tenants />);

    const activeBadges = screen.getAllByText(/active/i);
    expect(activeBadges.length).toBeGreaterThan(0);
  });

  it('displays inactive status badge correctly', () => {
    renderWithProviders(<Tenants />);

    expect(screen.getByText(/inactive/i)).toBeInTheDocument();
  });

  it('renders edit and delete buttons for each tenant', () => {
    renderWithProviders(<Tenants />);

    const editButtons = screen.getAllByRole('button', { name: /edit/i });
    const deleteButtons = screen.getAllByRole('button', { name: /delete/i });

    expect(editButtons.length).toBe(mockTenants.length);
    expect(deleteButtons.length).toBe(mockTenants.length);
  });

  it('opens add tenant modal when add button is clicked', async () => {
    renderWithProviders(<Tenants />);
    const user = userEvent.setup();

    const addButton = screen.getByRole('button', { name: /add tenant/i });
    await user.click(addButton);

    expect(screen.getByText('Add New Tenant')).toBeInTheDocument();
  });

  it('opens edit tenant modal when edit button is clicked', async () => {
    renderWithProviders(<Tenants />);
    const user = userEvent.setup();

    const editButtons = screen.getAllByRole('button', { name: /edit/i });
    await user.click(editButtons[0]);

    expect(screen.getByText('Edit Tenant')).toBeInTheDocument();
  });

  it('closes modal when cancel button is clicked', async () => {
    renderWithProviders(<Tenants />);
    const user = userEvent.setup();

    const addButton = screen.getByRole('button', { name: /add tenant/i });
    await user.click(addButton);

    const cancelButton = screen.getByRole('button', { name: /cancel/i });
    await user.click(cancelButton);

    await waitFor(() => {
      expect(screen.queryByText('Add New Tenant')).not.toBeInTheDocument();
    });
  });

  it('shows empty state when no tenants exist', () => {
    (useApiModule.useTenants as vi.Mock).mockReturnValue({
      data: { items: [], total: 0 },
      isLoading: false,
    });

    renderWithProviders(<Tenants />);

    expect(screen.getByText(/no tenants configured yet/i)).toBeInTheDocument();
    expect(screen.getByText(/add your first tenant/i)).toBeInTheDocument();
  });

  it('shows loading skeleton when loading', () => {
    (useApiModule.useTenants as vi.Mock).mockReturnValue({
      data: null,
      isLoading: true,
    });

    renderWithProviders(<Tenants />);

    const loadingElements = document.querySelectorAll('.animate-pulse');
    expect(loadingElements.length).toBeGreaterThan(0);
  });

  it('submits new tenant form with correct data', async () => {
    mockCreateMutateAsync.mockResolvedValue({ id: 'new-tenant' });
    mockValidateMutateAsync.mockResolvedValue({ valid: true });

    renderWithProviders(<Tenants />);
    const user = userEvent.setup();

    const addButton = screen.getByRole('button', { name: /add tenant/i });
    await user.click(addButton);

    // Use placeholder text since labels aren't properly associated
    const displayNameInput = screen.getByPlaceholderText(/contoso production/i);
    const tenantIdInput = screen.getByPlaceholderText(/xxxx-xxxx/i);
    const clientIdInput = screen.getAllByPlaceholderText(/xxxx-xxxx/i)[1];
    const clientSecretInput = screen.getByPlaceholderText(/enter client secret/i);

    await user.type(displayNameInput, 'New Tenant');
    await user.type(tenantIdInput, '12345678-1234-1234-1234-123456789012');
    await user.type(clientIdInput, 'abcdef12-3456-7890-abcd-ef1234567890');
    await user.type(clientSecretInput, 'super-secret-value');

    const submitButton = screen.getByRole('button', { name: /add tenant/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(mockValidateMutateAsync).toHaveBeenCalled();
    });
  });

  it('calls delete mutation when delete is confirmed', async () => {
    mockDeleteMutateAsync.mockResolvedValue({});
    vi.stubGlobal('confirm', vi.fn(() => true));

    renderWithProviders(<Tenants />);
    const user = userEvent.setup();

    const deleteButtons = screen.getAllByRole('button', { name: /delete/i });
    await user.click(deleteButtons[0]);

    await waitFor(() => {
      expect(mockDeleteMutateAsync).toHaveBeenCalledWith('tenant-1');
    });

    vi.unstubAllGlobals();
  });

  it('displays created date in tenant table', () => {
    renderWithProviders(<Tenants />);

    // Check for dates formatted as locale strings
    const dateElements = screen.getAllByText(/\/|\./);
    expect(dateElements.length).toBeGreaterThan(0);
  });
});
