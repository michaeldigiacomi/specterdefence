import { useState, useEffect, useCallback, useRef } from 'react';

/**
 * Offline state and cache management hook
 * Provides real-time online/offline status, cached data access, and background sync
 */

export interface CachedData<T> {
  data: T;
  timestamp: number;
  isStale: boolean;
}

export interface SyncQueueItem {
  id: string;
  url: string;
  method: string;
  headers: Record<string, string>;
  body: unknown;
  timestamp: number;
  retries: number;
}

export interface UseOfflineReturn {
  /** Whether the device is currently online */
  isOnline: boolean;
  /** Whether the app was recently offline */
  wasOffline: boolean;
  /** Whether a sync is currently in progress */
  isSyncing: boolean;
  /** Last time the device was online */
  lastOnlineTime: Date | null;
  /** Get cached data if available */
  getCachedData: <T>(key: string) => CachedData<T> | null;
  /** Set cached data */
  setCachedData: <T>(key: string, data: T) => void;
  /** Queue an action for when back online */
  queueForSync: (item: Omit<SyncQueueItem, 'id' | 'timestamp' | 'retries'>) => string;
  /** Manually trigger sync of queued items */
  triggerSync: () => Promise<void>;
  /** Clear all cached data */
  clearCache: () => void;
  /** Register for push notifications */
  registerPushNotifications: () => Promise<boolean>;
  /** Push subscription status */
  pushSubscription: PushSubscription | null;
}

const CACHE_KEY = 'specterdefence-offline-cache';
const SYNC_QUEUE_KEY = 'specterdefence-sync-queue';
const MAX_CACHE_AGE = 24 * 60 * 60 * 1000; // 24 hours
const MAX_RETRIES = 3;

export function useOffline(): UseOfflineReturn {
  const [isOnline, setIsOnline] = useState<boolean>(() => navigator.onLine);
  const [wasOffline, setWasOffline] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [lastOnlineTime, setLastOnlineTime] = useState<Date | null>(
    () => navigator.onLine ? new Date() : null
  );
  const [pushSubscription, setPushSubscription] = useState<PushSubscription | null>(null);

  const cacheRef = useRef<Map<string, CachedData<unknown>>>(new Map());
  const syncQueueRef = useRef<SyncQueueItem[]>([]);

  // Initialize cache from localStorage
  useEffect(() => {
    try {
      const cached = localStorage.getItem(CACHE_KEY);
      if (cached) {
        const parsed = JSON.parse(cached);
        Object.entries(parsed).forEach(([key, value]) => {
          cacheRef.current.set(key, value as CachedData<unknown>);
        });
      }

      const queue = localStorage.getItem(SYNC_QUEUE_KEY);
      if (queue) {
        syncQueueRef.current = JSON.parse(queue);
      }
    } catch (error) {
      console.error('[useOffline] Error loading cache:', error);
    }
  }, []);

  // Handle online/offline events
  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true);
      setWasOffline(true);
      setLastOnlineTime(new Date());

      // Auto-trigger sync when coming back online
      setTimeout(() => {
        triggerSync();
      }, 1000);
    };

    const handleOffline = () => {
      setIsOnline(false);
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Register service worker
  useEffect(() => {
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker
        .register('/service-worker.js')
        .then((registration) => {
          console.log('[useOffline] Service Worker registered:', registration.scope);

          // Check for push subscription
          registration.pushManager.getSubscription().then((subscription) => {
            setPushSubscription(subscription);
          });
        })
        .catch((error) => {
          console.error('[useOffline] Service Worker registration failed:', error);
        });
    }
  }, []);

  // Save cache to localStorage
  const saveCache = useCallback(() => {
    try {
      const cacheObj: Record<string, unknown> = {};
      cacheRef.current.forEach((value, key) => {
        cacheObj[key] = value;
      });
      localStorage.setItem(CACHE_KEY, JSON.stringify(cacheObj));
    } catch (error) {
      console.error('[useOffline] Error saving cache:', error);
    }
  }, []);

  // Save sync queue to localStorage
  const saveQueue = useCallback(() => {
    try {
      localStorage.setItem(SYNC_QUEUE_KEY, JSON.stringify(syncQueueRef.current));
    } catch (error) {
      console.error('[useOffline] Error saving sync queue:', error);
    }
  }, []);

  // Get cached data
  const getCachedData = useCallback(<T>(key: string): CachedData<T> | null => {
    const cached = cacheRef.current.get(key);
    if (!cached) return null;

    const isStale = Date.now() - cached.timestamp > MAX_CACHE_AGE;
    return {
      data: cached.data as T,
      timestamp: cached.timestamp,
      isStale,
    };
  }, []);

  // Set cached data
  const setCachedData = useCallback(<T>(key: string, data: T) => {
    cacheRef.current.set(key, {
      data,
      timestamp: Date.now(),
      isStale: false,
    });
    saveCache();
  }, [saveCache]);

  // Queue an action for sync
  const queueForSync = useCallback(
    (item: Omit<SyncQueueItem, 'id' | 'timestamp' | 'retries'>): string => {
      const id = `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
      const queueItem: SyncQueueItem = {
        ...item,
        id,
        timestamp: Date.now(),
        retries: 0,
      };

      syncQueueRef.current.push(queueItem);
      saveQueue();

      // Try to trigger background sync if available
      if ('serviceWorker' in navigator && 'SyncManager' in window) {
        navigator.serviceWorker.ready.then((registration) => {
          // @ts-expect-error - BackgroundSync not fully typed
          registration.sync.register('sync-alerts').catch(() => {
            // Fallback: will sync when online event fires
          });
        });
      }

      return id;
    },
    [saveQueue]
  );

  // Trigger sync of queued items
  const triggerSync = useCallback(async () => {
    if (syncQueueRef.current.length === 0 || !isOnline) return;

    setIsSyncing(true);

    const queue = [...syncQueueRef.current];
    const failedItems: SyncQueueItem[] = [];

    for (const item of queue) {
      try {
        const response = await fetch(item.url, {
          method: item.method,
          headers: item.headers,
          body: item.body ? JSON.stringify(item.body) : undefined,
        });

        if (!response.ok && response.status >= 500) {
          // Server error - retry
          throw new Error(`Server error: ${response.status}`);
        }

        // Success or client error (don't retry 4xx)
        console.log('[useOffline] Synced item:', item.id);
      } catch (error) {
        console.error('[useOffline] Sync failed for item:', item.id, error);

        if (item.retries < MAX_RETRIES) {
          failedItems.push({
            ...item,
            retries: item.retries + 1,
          });
        }
      }
    }

    syncQueueRef.current = failedItems;
    saveQueue();
    setIsSyncing(false);

    // Clear wasOffline flag after successful sync
    if (failedItems.length === 0) {
      setWasOffline(false);
    }
  }, [isOnline, saveQueue]);

  // Clear all cached data
  const clearCache = useCallback(() => {
    cacheRef.current.clear();
    syncQueueRef.current = [];
    localStorage.removeItem(CACHE_KEY);
    localStorage.removeItem(SYNC_QUEUE_KEY);
  }, []);

  // Register for push notifications
  const registerPushNotifications = useCallback(async (): Promise<boolean> => {
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
      console.warn('[useOffline] Push notifications not supported');
      return false;
    }

    try {
      const registration = await navigator.serviceWorker.ready;

      // Check existing subscription
      let subscription = await registration.pushManager.getSubscription();

      if (!subscription) {
        // Subscribe
        const applicationServerKey = urlBase64ToUint8Array(
          // @ts-expect-error - import.meta.env is not typed
          import.meta.env?.VITE_VAPID_PUBLIC_KEY || ''
        );

        subscription = await registration.pushManager.subscribe({
          userVisibleOnly: true,
          // @ts-expect-error - applicationServerKey type mismatch
          applicationServerKey: applicationServerKey,
        });
      }

      setPushSubscription(subscription);

      // Send subscription to server
      await fetch('/api/v1/push/subscribe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(subscription),
      });

      return true;
    } catch (error) {
      console.error('[useOffline] Push registration failed:', error);
      return false;
    }
  }, []);

  return {
    isOnline,
    wasOffline,
    isSyncing,
    lastOnlineTime,
    getCachedData,
    setCachedData,
    queueForSync,
    triggerSync,
    clearCache,
    registerPushNotifications,
    pushSubscription,
  };
}

// Helper function to convert VAPID key
function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
  const rawData = window.atob(base64);
  return Uint8Array.from([...rawData].map((char) => char.charCodeAt(0)));
}

export default useOffline;
