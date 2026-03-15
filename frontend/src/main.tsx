import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';
import './styles/mobile.css';

// Service Worker is registered via the useOffline hook (hooks/useOffline.ts)
// to centralize PWA lifecycle management (push, sync, caching)

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
