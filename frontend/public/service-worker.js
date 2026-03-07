const CACHE_NAME = 'specterdefence-v1';
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/manifest.json',
  '/logo.svg',
  '/icons/icon-192x192.png',
  '/icons/icon-512x512.png',
];

// API routes to cache with network-first strategy
const API_ROUTES = [
  '/api/v1/dashboard/stats',
  '/api/v1/alerts',
  '/api/v1/tenants',
];

// Install event - cache static assets
self.addEventListener('install', (event) => {
  console.log('[SW] Installing service worker...');

  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('[SW] Caching static assets');
      return cache.addAll(STATIC_ASSETS);
    }).catch((err) => {
      console.error('[SW] Failed to cache static assets:', err);
    })
  );

  // Skip waiting to activate immediately
  self.skipWaiting();
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating service worker...');

  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name !== CACHE_NAME)
          .map((name) => {
            console.log('[SW] Deleting old cache:', name);
            return caches.delete(name);
          })
      );
    }).then(() => {
      console.log('[SW] Service worker activated');
      // Claim clients immediately
      return self.clients.claim();
    })
  );
});

// Fetch event - handle caching strategies
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== 'GET') {
    return;
  }

  // Skip cross-origin requests
  if (url.origin !== self.location.origin) {
    return;
  }

  // API routes - Network first, fallback to cache
  if (API_ROUTES.some((route) => url.pathname.startsWith(route))) {
    event.respondWith(networkFirstStrategy(request));
    return;
  }

  // Static assets - Cache first, fallback to network
  if (STATIC_ASSETS.includes(url.pathname) ||
      url.pathname.startsWith('/assets/') ||
      url.pathname.startsWith('/icons/')) {
    event.respondWith(cacheFirstStrategy(request));
    return;
  }

  // Default - Stale while revalidate
  event.respondWith(staleWhileRevalidateStrategy(request));
});

// Network first strategy - for API calls
async function networkFirstStrategy(request) {
  try {
    const networkResponse = await fetch(request);

    if (networkResponse.ok) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, networkResponse.clone());
    }

    return networkResponse;
  } catch (error) {
    console.log('[SW] Network failed, trying cache:', request.url);
    const cachedResponse = await caches.match(request);

    if (cachedResponse) {
      return cachedResponse;
    }

    // Return offline fallback for API
    return new Response(
      JSON.stringify({
        error: 'Offline',
        message: 'You are currently offline. Data may be outdated.',
        cached: true,
        timestamp: new Date().toISOString(),
      }),
      {
        status: 503,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }
}

// Cache first strategy - for static assets
async function cacheFirstStrategy(request) {
  const cachedResponse = await caches.match(request);

  if (cachedResponse) {
    // Update cache in background
    fetch(request).then((networkResponse) => {
      if (networkResponse.ok) {
        caches.open(CACHE_NAME).then((cache) => {
          cache.put(request, networkResponse);
        });
      }
    }).catch(() => {
      // Ignore network errors for background updates
    });

    return cachedResponse;
  }

  const networkResponse = await fetch(request);

  if (networkResponse.ok) {
    const cache = await caches.open(CACHE_NAME);
    cache.put(request, networkResponse.clone());
  }

  return networkResponse;
}

// Stale while revalidate strategy - for pages
async function staleWhileRevalidateStrategy(request) {
  const cachedResponse = await caches.match(request);

  const networkFetch = fetch(request).then((networkResponse) => {
    if (networkResponse.ok) {
      caches.open(CACHE_NAME).then((cache) => {
        cache.put(request, networkResponse.clone());
      });
    }
    return networkResponse;
  }).catch((error) => {
    console.log('[SW] Network fetch failed:', error);
    return null;
  });

  if (cachedResponse) {
    return cachedResponse;
  }

  const networkResponse = await networkFetch;

  if (networkResponse) {
    return networkResponse;
  }

  // Return offline page
  return caches.match('/index.html').then((response) => {
    return response || new Response('Offline', { status: 503 });
  });
}

// Push notification event
self.addEventListener('push', (event) => {
  console.log('[SW] Push notification received:', event);

  if (!event.data) {
    return;
  }

  let data;
  try {
    data = event.data.json();
  } catch {
    data = {
      title: 'SpecterDefence Alert',
      body: event.data.text(),
      icon: '/icons/icon-192x192.png',
      badge: '/icons/icon-72x72.png',
      tag: 'default',
    };
  }

  const options = {
    body: data.body,
    icon: data.icon || '/icons/icon-192x192.png',
    badge: data.badge || '/icons/icon-72x72.png',
    tag: data.tag || 'default',
    requireInteraction: data.requireInteraction ?? true,
    actions: data.actions || [
      { action: 'view', title: 'View Alert' },
      { action: 'dismiss', title: 'Dismiss' },
    ],
    data: data.data || {},
    timestamp: Date.now(),
    vibrate: data.vibrate || [200, 100, 200],
  };

  event.waitUntil(
    self.registration.showNotification(data.title, options)
  );
});

// Notification click event
self.addEventListener('notificationclick', (event) => {
  console.log('[SW] Notification clicked:', event);

  event.notification.close();

  const notificationData = event.notification.data;
  const action = event.action;

  if (action === 'dismiss') {
    // Just close the notification
    return;
  }

  // Default action or 'view' - open the app
  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
      const url = notificationData?.url || '/';

      // Check if there's already a window open
      for (const client of clientList) {
        if (client.url === url && 'focus' in client) {
          return client.focus();
        }
      }

      // Open new window
      if (self.clients.openWindow) {
        return self.clients.openWindow(url);
      }
    })
  );
});

// Background sync event
self.addEventListener('sync', (event) => {
  const syncEvent = event;
  console.log('[SW] Background sync:', syncEvent.tag);

  if (syncEvent.tag === 'sync-alerts') {
    syncEvent.waitUntil(syncPendingAlerts());
  } else if (syncEvent.tag === 'sync-acknowledgments') {
    syncEvent.waitUntil(syncPendingAcknowledgments());
  }
});

// Sync pending alerts
async function syncPendingAlerts() {
  try {
    const cache = await caches.open(CACHE_NAME);
    const pendingRequests = await cache.match('pending-alerts');

    if (!pendingRequests) {
      return;
    }

    const requests = await pendingRequests.json();

    for (const request of requests) {
      try {
        await fetch(request.url, {
          method: request.method,
          headers: request.headers,
          body: JSON.stringify(request.body),
        });
      } catch (error) {
        console.error('[SW] Failed to sync pending alert:', error);
      }
    }

    // Clear pending alerts after sync
    await cache.delete('pending-alerts');
  } catch (error) {
    console.error('[SW] Error syncing pending alerts:', error);
  }
}

// Sync pending acknowledgments
async function syncPendingAcknowledgments() {
  try {
    const cache = await caches.open(CACHE_NAME);
    const pendingRequests = await cache.match('pending-acknowledgments');

    if (!pendingRequests) {
      return;
    }

    const requests = await pendingRequests.json();

    for (const request of requests) {
      try {
        await fetch(request.url, {
          method: request.method,
          headers: request.headers,
          body: JSON.stringify(request.body),
        });
      } catch (error) {
        console.error('[SW] Failed to sync pending acknowledgment:', error);
      }
    }

    // Clear pending acknowledgments after sync
    await cache.delete('pending-acknowledgments');
  } catch (error) {
    console.error('[SW] Error syncing pending acknowledgments:', error);
  }
}

// Message handling from main thread
self.addEventListener('message', (event) => {
  const { type, payload } = event.data;

  switch (type) {
    case 'SKIP_WAITING':
      self.skipWaiting();
      break;

    case 'GET_VERSION':
      if (event.ports[0]) {
        event.ports[0].postMessage({ version: CACHE_NAME });
      }
      break;

    case 'CACHE_URLS':
      event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
          return cache.addAll(payload.urls || []);
        })
      );
      break;

    case 'CLEAR_CACHE':
      event.waitUntil(
        caches.delete(CACHE_NAME).then(() => {
          return caches.open(CACHE_NAME);
        })
      );
      break;

    default:
      console.log('[SW] Unknown message type:', type);
  }
});
