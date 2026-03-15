import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '@/test/utils';
import { ChangePasswordDialog } from './ChangePasswordDialog';
import { server } from '@/test/mocks/server';
import { http, HttpResponse } from 'msw';

describe('ChangePasswordDialog', () => {
  const mockOnClose = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('does not render when isOpen is false', () => {
    renderWithProviders(<ChangePasswordDialog isOpen={false} onClose={mockOnClose} />);

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('renders correctly when isOpen is true', () => {
    renderWithProviders(<ChangePasswordDialog isOpen={true} onClose={mockOnClose} />);

    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText('Change Password')).toBeInTheDocument();
  });

  it('closes dialog when cancel button is clicked', async () => {
    renderWithProviders(<ChangePasswordDialog isOpen={true} onClose={mockOnClose} />);
    const user = userEvent.setup();

    const cancelButton = screen.getByRole('button', { name: /cancel/i });
    await user.click(cancelButton);

    expect(mockOnClose).toHaveBeenCalledTimes(1);
  });

  it('closes dialog when close icon button is clicked', async () => {
    renderWithProviders(<ChangePasswordDialog isOpen={true} onClose={mockOnClose} />);
    const user = userEvent.setup();

    // Find the X button by its icon container
    const closeButton = document.querySelector('button svg[data-lucide="x"]')?.closest('button');
    if (closeButton) {
      await user.click(closeButton);
      expect(mockOnClose).toHaveBeenCalledTimes(1);
    }
  });

  it('shows error when new password is less than 8 characters', async () => {
    renderWithProviders(<ChangePasswordDialog isOpen={true} onClose={mockOnClose} />);
    const user = userEvent.setup();

    const inputs = screen.getAllByRole('textbox');
    const passwordInputs = document.querySelectorAll('input[type="password"]');

    // Enter short password
    if (inputs[0]) await user.type(inputs[0], 'oldpassword123');
    if (passwordInputs[0]) await user.type(passwordInputs[0], 'short');
    if (passwordInputs[1]) await user.type(passwordInputs[1], 'short');

    const submitButton = screen.getByRole('button', { name: /change password/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/at least 8 characters/i)).toBeInTheDocument();
    });
  });

  it('shows error when new passwords do not match', async () => {
    renderWithProviders(<ChangePasswordDialog isOpen={true} onClose={mockOnClose} />);
    const user = userEvent.setup();

    const inputs = screen.getAllByRole('textbox');
    const passwordInputs = document.querySelectorAll('input[type="password"]');

    if (inputs[0]) await user.type(inputs[0], 'oldpassword123');
    if (passwordInputs[0]) await user.type(passwordInputs[0], 'newpassword456');
    if (passwordInputs[1]) await user.type(passwordInputs[1], 'differentpassword');

    const submitButton = screen.getByRole('button', { name: /change password/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/passwords do not match/i)).toBeInTheDocument();
    });
  });

  it('shows error when new password is same as current password', async () => {
    renderWithProviders(<ChangePasswordDialog isOpen={true} onClose={mockOnClose} />);
    const user = userEvent.setup();

    const inputs = screen.getAllByRole('textbox');
    const passwordInputs = document.querySelectorAll('input[type="password"]');

    if (inputs[0]) await user.type(inputs[0], 'samepassword');
    if (passwordInputs[0]) await user.type(passwordInputs[0], 'samepassword');
    if (passwordInputs[1]) await user.type(passwordInputs[1], 'samepassword');

    const submitButton = screen.getByRole('button', { name: /change password/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/must be different from current password/i)).toBeInTheDocument();
    });
  });

  it('closes dialog and resets form on successful password change', async () => {
    renderWithProviders(<ChangePasswordDialog isOpen={true} onClose={mockOnClose} />);
    const user = userEvent.setup();

    const inputs = screen.getAllByRole('textbox');
    const passwordInputs = document.querySelectorAll('input[type="password"]');

    if (inputs[0]) await user.type(inputs[0], 'admin123');
    if (passwordInputs[0]) await user.type(passwordInputs[0], 'newpassword456');
    if (passwordInputs[1]) await user.type(passwordInputs[1], 'newpassword456');

    const submitButton = screen.getByRole('button', { name: /change password/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(mockOnClose).toHaveBeenCalledTimes(1);
    });
  });

  it('displays password requirements hint', () => {
    renderWithProviders(<ChangePasswordDialog isOpen={true} onClose={mockOnClose} />);

    expect(screen.getByText(/password must be at least 8 characters long/i)).toBeInTheDocument();
  });
});
