# SpecterDefence Frontend

React-based dashboard for SpecterDefence security monitoring platform.

## Features

- 📊 **Dashboard** - Overview of security metrics and recent anomalies
- 📈 **Analytics** - Login timeline with filtering and CSV export
- 🗺️ **Geographic Map** - Interactive map showing login locations
- 🚨 **Anomalies** - Review detected security anomalies
- 🏢 **Tenants** - Manage Microsoft 365 tenant connections
- 🌓 **Dark Mode** - Toggle between light and dark themes
- 📱 **Responsive** - Mobile-friendly design

## Tech Stack

- **React 18** - UI library
- **TypeScript** - Type safety
- **Vite** - Build tool
- **Tailwind CSS** - Styling
- **TanStack Query** - Data fetching
- **Recharts** - Charts
- **Leaflet** - Maps
- **Vitest** - Testing

## Getting Started

### Prerequisites

- Node.js 18+
- npm or yarn

### Installation

```bash
cd frontend
npm install
```

### Development

```bash
npm run dev
```

The dev server runs on `http://localhost:3000` and proxies API requests to `http://localhost:8000`.

### Build

```bash
npm run build
```

### Testing

```bash
# Run tests
npm test

# Run tests with coverage
npm run test:coverage

# Run tests with UI
npm run test:ui
```

### Docker

```bash
docker build -t specterdefence-frontend .
docker run -p 80:80 specterdefence-frontend
```

## Project Structure

```
src/
├── components/     # Reusable UI components
│   ├── Layout.tsx
│   ├── Sidebar.tsx
│   ├── StatsCard.tsx
│   ├── AnomalyCard.tsx
│   ├── FilterPanel.tsx
│   ├── LoginTimeline.tsx
│   └── LoginMap.tsx
├── pages/          # Page components
│   ├── Dashboard.tsx
│   ├── LoginAnalytics.tsx
│   ├── MapPage.tsx
│   ├── Anomalies.tsx
│   └── Tenants.tsx
├── hooks/          # Custom React hooks
│   └── useApi.ts
├── services/       # API services
│   └── api.ts
├── store/          # State management
│   └── appStore.ts
├── types/          # TypeScript types
│   └── index.ts
├── test/           # Test setup
│   └── setup.ts
├── App.tsx
├── main.tsx
└── index.css
```

## Environment Variables

No environment variables are required for development. The app uses proxy configuration in `vite.config.ts`.

For production, configure the API endpoint in `nginx.conf`.

## API Integration

The frontend integrates with the SpecterDefence FastAPI backend:

- `GET /api/v1/analytics/logins` - Login data
- `GET /api/v1/analytics/anomalies/recent` - Recent anomalies
- `GET /api/v1/tenants` - Tenant list
- `GET /api/v1/alerts/history` - Alert history

## License

MIT
