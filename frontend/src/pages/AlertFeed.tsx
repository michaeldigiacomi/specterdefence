import { AlertFeed } from '@/components/AlertFeed';
import { PageHeader } from '@/components/PageHeader';
import { Bell } from 'lucide-react';

export function AlertFeedPage() {
  return (
    <div className="p-6 max-w-7xl mx-auto">
      <PageHeader
        title="Live Alert Feed"
        description="Real-time security alerts from your Microsoft 365 environment"
        icon={Bell}
      />

      <div className="mt-6">
        <AlertFeed maxHeight="calc(100vh - 250px)" />
      </div>
    </div>
  );
}

export default AlertFeedPage;
