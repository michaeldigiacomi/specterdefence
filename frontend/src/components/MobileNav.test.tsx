import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen } from '@testing-library/react';
import { renderWithProviders } from '@/test/utils';
import { MobileNav } from './MobileNav';

// Mock the store
vi.mock('@/store/appStore', () => ({
  useAppStore: vi.fn(),
}));

import { useAppStore } from '@/store/appStore';

describe('MobileNav', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    
    (useAppStore as vi.Mock).mockReturnValue({
      sidebarOpen: false,
      toggleSidebar: vi.fn(),
      setSidebarOpen: vi.fn(),
      user: { username: 'admin', is_authenticated: true },
    });
  });

  it('renders mobile navigation button', () => {
    renderWithProviders(<MobileNav />);

    const menuButton = screen.getByRole('button', { name: /open menu/i });
    expect(menuButton).toBeInTheDocument();
  });
});
