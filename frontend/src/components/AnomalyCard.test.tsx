import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import AnomalyCard from './AnomalyCard';
import type { AnomalyDetail } from '@/types';

describe('AnomalyCard', () => {
  const mockAnomaly: AnomalyDetail = {
    type: 'impossible_travel',
    user: 'test@example.com',
    locations: ['New York, USA', 'London, UK'],
    time_diff_minutes: 30,
    risk_score: 85,
    details: {
      previous_ip: '1.2.3.4',
      current_ip: '5.6.7.8',
    },
  };

  it('renders anomaly details', () => {
    render(<AnomalyCard anomaly={mockAnomaly} />);

    expect(screen.getByText('test@example.com')).toBeInTheDocument();
    expect(screen.getByText('Impossible Travel')).toBeInTheDocument();
    expect(screen.getByText('Risk: 85')).toBeInTheDocument();
  });

  it('renders compact mode', () => {
    render(<AnomalyCard anomaly={mockAnomaly} compact />);

    expect(screen.getByText('test@example.com')).toBeInTheDocument();
    // Compact should have smaller layout
    expect(document.querySelector('.p-3')).toBeInTheDocument();
  });

  it('renders new country anomaly', () => {
    const newCountryAnomaly: AnomalyDetail = {
      type: 'new_country',
      user: 'user@example.com',
      risk_score: 60,
      country: 'Germany',
      previous_countries: ['US', 'UK', 'FR'],
    };

    render(<AnomalyCard anomaly={newCountryAnomaly} />);

    expect(screen.getByText('New Country Login')).toBeInTheDocument();
    expect(screen.getByText('Germany')).toBeInTheDocument();
    expect(screen.getByText('Previously seen in:')).toBeInTheDocument();
  });

  it('renders failed login anomaly', () => {
    const failedLoginAnomaly: AnomalyDetail = {
      type: 'failed_login',
      user: 'user@example.com',
      risk_score: 30,
      details: {
        failure_reason: 'Invalid password',
        ip_address: '1.2.3.4',
      },
    };

    render(<AnomalyCard anomaly={failedLoginAnomaly} />);

    expect(screen.getByText('Failed Login')).toBeInTheDocument();
  });

  it('shows correct risk score color coding', () => {
    // Critical risk (>=80)
    const criticalAnomaly: AnomalyDetail = {
      type: 'impossible_travel',
      user: 'user@example.com',
      risk_score: 90,
    };

    const { rerender } = render(<AnomalyCard anomaly={criticalAnomaly} />);
    expect(document.querySelector('.bg-red-50')).toBeInTheDocument();

    // Medium risk
    const mediumAnomaly: AnomalyDetail = {
      type: 'new_country',
      user: 'user@example.com',
      risk_score: 50,
    };

    rerender(<AnomalyCard anomaly={mediumAnomaly} />);
    expect(document.querySelector('.bg-amber-50')).toBeInTheDocument();

    // Low risk
    const lowAnomaly: AnomalyDetail = {
      type: 'failed_login',
      user: 'user@example.com',
      risk_score: 20,
    };

    rerender(<AnomalyCard anomaly={lowAnomaly} />);
    expect(document.querySelector('.bg-blue-50')).toBeInTheDocument();
  });
});
