import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { TopRiskUsers } from './TopRiskUsers';

describe('TopRiskUsers', () => {
  it('renders without crashing', () => {
    const mockUsers = [
      {
        user_email: 'test@example.com',
        tenant_id: 'tenant1',
        risk_score: 80,
        anomaly_count: 5,
        last_anomaly_time: '2023-01-01T00:00:00Z',
        top_anomaly_types: ['login_failure'],
        country_count: 2,
      },
    ];

    render(
      <MemoryRouter>
        <TopRiskUsers users={mockUsers} totalUsers={1} avgRiskScore={80} />
      </MemoryRouter>
    );

    expect(screen.getByText('test@example.com')).toBeDefined();
  });
});
