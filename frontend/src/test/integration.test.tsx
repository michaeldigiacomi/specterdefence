import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '@/test/utils';
import { server } from '@/test/mocks/server';
import { http, HttpResponse } from 'msw';
import Login from '@/pages/Login';

describe('Authentication Flow Integration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it('renders login form correctly', () => {
    renderWithProviders(<Login />);

    expect(screen.getByText('Welcome Back')).toBeInTheDocument();
    expect(screen.getByLabelText('Username')).toBeInTheDocument();
    expect(screen.getByLabelText('Password')).toBeInTheDocument();
  });

  it('shows error on failed login', async () => {
    const user = userEvent.setup();
    
    server.use(
      http.post('/api/v1/auth/login', () => {
        return HttpResponse.json(
          { detail: 'Invalid credentials' },
          { status: 401 }
        );
      })
    );

    renderWithProviders(<Login />);

    const usernameInput = screen.getByLabelText('Username');
    const passwordInput = screen.getByLabelText('Password');
    const submitButton = screen.getByRole('button', { name: /sign in/i });

    await user.type(usernameInput, 'wronguser');
    await user.type(passwordInput, 'wrongpass');
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/network error|login failed|invalid credentials/i)).toBeInTheDocument();
    });
  });
});
