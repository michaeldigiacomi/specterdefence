import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import StatsCard from './StatsCard';
import { Users } from 'lucide-react';

describe('StatsCard', () => {
  it('renders with basic props', () => {
    render(<StatsCard title="Test Title" value={100} icon={Users} />);

    expect(screen.getByText('Test Title')).toBeInTheDocument();
    expect(screen.getByText('100')).toBeInTheDocument();
  });

  it('renders loading state', () => {
    render(<StatsCard title="Test Title" value={100} icon={Users} loading={true} />);

    // Loading state should have animate-pulse class
    const loadingElement = document.querySelector('.animate-pulse');
    expect(loadingElement).toBeInTheDocument();
  });

  it('renders with trend', () => {
    render(
      <StatsCard
        title="Test Title"
        value={100}
        icon={Users}
        trend={{ value: 15, label: 'vs last week', positive: true }}
      />
    );

    expect(screen.getByText('+15%')).toBeInTheDocument();
    expect(screen.getByText('vs last week')).toBeInTheDocument();
  });

  it('applies different color variants', () => {
    const { rerender } = render(<StatsCard title="Test" value={100} icon={Users} color="blue" />);

    // Check that blue styles are applied
    expect(document.querySelector('.text-blue-600')).toBeInTheDocument();

    rerender(<StatsCard title="Test" value={100} icon={Users} color="red" />);

    expect(document.querySelector('.text-red-600')).toBeInTheDocument();
  });

  it('formats string values', () => {
    render(<StatsCard title="Test" value="1,234" icon={Users} />);

    expect(screen.getByText('1,234')).toBeInTheDocument();
  });
});
