import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '@/test/utils';
import { server } from '@/test/mocks/server';
import { http, HttpResponse } from 'msw';
import Login from './Login';

describe('Login Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders login form correctly', () => {
    renderWithProviders(<Login />);

    expect(screen.getByText('SpecterDefence')).toBeInTheDocument();
    expect(screen.getByText('Microsoft 365 Security Monitoring')).toBeInTheDocument();
    expect(screen.getByLabelText('Username')).toBeInTheDocument();
    expect(screen.getByLabelText('Password')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
  });

  it('allows entering username and password', async () => {
    renderWithProviders(<Login />);
    const user = userEvent.setup();

    const usernameInput = screen.getByLabelText('Username');
    const passwordInput = screen.getByLabelText('Password');

    await user.type(usernameInput, 'admin');
    await user.type(passwordInput, 'admin123');

    expect(usernameInput).toHaveValue('admin');
    expect(passwordInput).toHaveValue('admin123');
  });

  it('toggles password visibility', async () => {
    renderWithProviders(<Login />);
    const user = userEvent.setup();

    const passwordInput = screen.getByLabelText('Password');
    const toggleButton = screen.getByRole('button', { name: '' });

    expect(passwordInput).toHaveAttribute('type', 'password');

    await user.click(toggleButton);
    expect(passwordInput).toHaveAttribute('type', 'text');

    await user.click(toggleButton);
    expect(passwordInput).toHaveAttribute('type', 'password');
  });

  it('disables submit button when fields are empty', () => {
    renderWithProviders(<Login />);

    const submitButton = screen.getByRole('button', { name: /sign in/i });
    expect(submitButton).toBeDisabled();
  });

  it('enables submit button when fields are filled', async () => {
    renderWithProviders(<Login />);
    const user = userEvent.setup();

    const usernameInput = screen.getByLabelText('Username');
    const passwordInput = screen.getByLabelText('Password');
    const submitButton = screen.getByRole('button', { name: /sign in/i });

    await user.type(usernameInput, 'admin');
    await user.type(passwordInput, 'admin123');

    expect(submitButton).toBeEnabled();
  });

  it('shows loading state during submission', async () => {
    renderWithProviders(<Login />);
    const user = userEvent.setup();

    const usernameInput = screen.getByLabelText('Username');
    const passwordInput = screen.getByLabelText('Password');
    const submitButton = screen.getByRole('button', { name: /sign in/i });

    await user.type(usernameInput, 'admin');
    await user.type(passwordInput, 'admin123');
    await user.click(submitButton);

    expect(screen.getByText(/signing in/i)).toBeInTheDocument();
  });

  it('displays error message on invalid credentials', async () => {
    server.use(
      http.post('/api/v1/auth/local/login', () => {
        return HttpResponse.json({ detail: 'Invalid credentials' }, { status: 401 });
      })
    );

    renderWithProviders(<Login />);
    const user = userEvent.setup();

    const usernameInput = screen.getByLabelText('Username');
    const passwordInput = screen.getByLabelText('Password');
    const submitButton = screen.getByRole('button', { name: /sign in/i });

    await user.type(usernameInput, 'wronguser');
    await user.type(passwordInput, 'wrongpass');
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/login failed/i)).toBeInTheDocument();
    });
  });

  it('disables inputs during submission', async () => {
    renderWithProviders(<Login />);
    const user = userEvent.setup();

    const usernameInput = screen.getByLabelText('Username');
    const passwordInput = screen.getByLabelText('Password');
    const submitButton = screen.getByRole('button', { name: /sign in/i });

    await user.type(usernameInput, 'admin');
    await user.type(passwordInput, 'admin123');
    await user.click(submitButton);

    expect(usernameInput).toBeDisabled();
    expect(passwordInput).toBeDisabled();
  });

  it('shows default credentials hint', () => {
    renderWithProviders(<Login />);

    expect(screen.getByText(/default credentials/i)).toBeInTheDocument();
    expect(screen.getByText(/admin \/ admin123/)).toBeInTheDocument();
  });
});
