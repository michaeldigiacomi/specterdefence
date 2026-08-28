# SpecterDefence Frontend

React 18 + TypeScript dashboard for the SpecterDefence backend. Built with Vite, Tailwind CSS, TanStack Query, Zustand, Recharts, and Leaflet. Tests use Vitest (jsdom, v8 coverage, 70% global thresholds).

## Getting started

```bash
cd frontend
npm install
npm run dev        # dev server on http://localhost:3000
npm run build      # production build to dist/
npm test           # vitest
npm run test:coverage
```

**API access in dev**: `vite.config.ts` proxies `/api` (HTTP+WS) and `/ws` to `https://app.specterdefence.digitaladrenalin.net`. Point it at a local backend (`http://localhost:8000`, `ws://localhost:8000`) if you're running one.

## Structure

```
src/
├── pages/       # Dashboard, Tenants, LoginAnalytics, Anomalies, MapPage, AlertFeed,
│                # Settings, CAPolicies, MailboxRules, MFAReport, OAuthApps, Monitoring,
│                # SharePoint, InsiderThreat, MailboxSecurity, Endpoints, Users, Login
├── components/  # Shared UI incl. charts/ and settings/ subfolders
├── hooks/       # useApi, useAuth, useWebSocket, useDashboard, useOffline, useSettings
├── services/    # api.ts (API client), monitoring.ts
├── store/       # appStore.ts (Zustand, persisted)
├── types/       # Shared TypeScript types
└── test/        # Vitest setup
```

Auth: JWT from `/api/v1/auth/local/login`, stored via the Zustand `specterdefence-storage` persist key; `ProtectedRoute` guards pages.

## Production

Docker image (`frontend/Dockerfile`) serves the build with Nginx (`nginx.conf`), container port 80. Deployed via `k8s/prod/frontend.yaml` behind the Traefik ingress.

Coding standards: [STANDARDS.md](STANDARDS.md).
