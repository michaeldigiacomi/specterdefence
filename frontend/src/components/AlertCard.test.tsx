import { describe, it, expect, vi } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '@/test/utils';
import { AlertCard } from './AlertCard';
import { mockAlerts } from '@/test/mocks/data';

describe('AlertCard', () => {
  const mockOnAcknowledge = vi.fn();
  const mockOnDismiss = vi.fn();

  it('renders alert with correct severity styling for CRITICAL', () => {
    const criticalAlert = mockAlerts.find(a => a.severity === 'CRITICAL')!;
    
    renderWithProviders(
      <AlertCard
        alert={criticalAlert}
        onAcknowledge={mockOnAcknowledge}
        onDismiss={mockOnDismiss}
      />
    );

    expect(screen.getByText('CRITICAL')).toBeInTheDocument();
    expect(screen.getByText(criticalAlert.title)).toBeInTheDocument();
    expect(screen.getByText(criticalAlert.message)).toBeInTheDocument();
  });

  it('renders alert with correct severity styling for HIGH', () => {
    const highAlert = mockAlerts.find(a => a.severity === 'HIGH')!;
    
    renderWithProviders(
      <AlertCard
        alert={highAlert}
        onAcknowledge={mockOnAcknowledge}
        onDismiss={mockOnDismiss}
      />
    );

    expect(screen.getByText('HIGH')).toBeInTheDocument();
  });

  it('renders alert with correct severity styling for MEDIUM', () => {
    const mediumAlert = mockAlerts.find(a => a.severity === 'MEDIUM')!;
    
    renderWithProviders(
      <AlertCard
        alert={mediumAlert}
        onAcknowledge={mockOnAcknowledge}
        onDismiss={mockOnDismiss}
      />
    );

    expect(screen.getByText('MEDIUM')).toBeInTheDocument();
  });

  it('renders alert with correct severity styling for LOW', () => {
    const lowAlert = mockAlerts.find(a => a.severity === 'LOW')!;
    
    renderWithProviders(
      <AlertCard
        alert={lowAlert}
        onAcknowledge={mockOnAcknowledge}
        onDismiss={mockOnDismiss}
      />
    );

    expect(screen.getByText('LOW')).toBeInTheDocument();
  });

  it('displays user email when available', () => {
    const alert = mockAlerts[0];
    
    renderWithProviders(
      <AlertCard
        alert={alert}
        onAcknowledge={mockOnAcknowledge}
        onDismiss={mockOnDismiss}
      />
    );

    expect(screen.getByText(alert.user_email!)).toBeInTheDocument();
  });

  it('displays location information when available', () => {
    const alert = mockAlerts[0];
    
    renderWithProviders(
      <AlertCard
        alert={alert}
        onAcknowledge={mockOnAcknowledge}
        onDismiss={mockOnDismiss}
      />
    );

    expect(screen.getByText(/new york/i)).toBeInTheDocument();
  });

  it('displays IP address when available', () => {
    const alert = mockAlerts[0];
    
    renderWithProviders(
      <AlertCard
        alert={alert}
        onAcknowledge={mockOnAcknowledge}
        onDismiss={mockOnDismiss}
      />
    );

    expect(screen.getByText(alert.metadata.ip_address as string)).toBeInTheDocument();
  });

  it('calls onAcknowledge when acknowledge button is clicked', async () => {
    const user = userEvent.setup();
    const alert = mockAlerts[0];
    
    renderWithProviders(
      <AlertCard
        alert={alert}
        onAcknowledge={mockOnAcknowledge}
        onDismiss={mockOnDismiss}
      />
    );

    const acknowledgeButton = screen.getByRole('button', { name: /acknowledge/i });
    await user.click(acknowledgeButton);

    expect(mockOnAcknowledge).toHaveBeenCalledWith(alert.id);
  });

  it('calls onDismiss when dismiss button is clicked', async () => {
    const user = userEvent.setup();
    const alert = mockAlerts[0];
    
    renderWithProviders(
      <AlertCard
        alert={alert}
        onAcknowledge={mockOnAcknowledge}
        onDismiss={mockOnDismiss}
      />
    );

    const dismissButtons = screen.getAllByRole('button', { name: /dismiss/i });
    await user.click(dismissButtons[0]);

    expect(mockOnDismiss).toHaveBeenCalledWith(alert.id);
  });

  it('does not show acknowledge button for already acknowledged alerts', () => {
    const acknowledgedAlert = mockAlerts.find(a => a.status === 'acknowledged')!;
    
    renderWithProviders(
      <AlertCard
        alert={acknowledgedAlert}
        onAcknowledge={mockOnAcknowledge}
        onDismiss={mockOnDismiss}
      />
    );

    expect(screen.queryByRole('button', { name: /acknowledge/i })).not.toBeInTheDocument();
  });

  it('renders compact mode correctly', () => {
    const alert = mockAlerts[0];
    
    renderWithProviders(
      <AlertCard
        alert={alert}
        onAcknowledge={mockOnAcknowledge}
        onDismiss={mockOnDismiss}
        compact={true}
      />
    );

    expect(screen.getByText(alert.title)).toBeInTheDocument();
  });

  it('displays event type name', () => {
    const alert = mockAlerts[0];
    
    renderWithProviders(
      <AlertCard
        alert={alert}
        onAcknowledge={mockOnAcknowledge}
        onDismiss={mockOnDismiss}
      />
    );

    expect(screen.getByText(alert.event_type_name)).toBeInTheDocument();
  });

  it('renders without callback handlers', () => {
    const alert = mockAlerts[0];
    
    renderWithProviders(<AlertCard alert={alert} />);

    expect(screen.getByText(alert.title)).toBeInTheDocument();
  });
});
