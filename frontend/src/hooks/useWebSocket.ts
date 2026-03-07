/**
 * WebSocket hook for real-time alert streaming.
 */

import { useEffect, useRef, useState, useCallback } from 'react';

export interface Alert {
  id: string;
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  event_type: string;
  title: string;
  message: string;
  user_email?: string;
  tenant_id?: string;
  metadata: Record<string, unknown>;
  timestamp: string;
  status: 'new' | 'acknowledged' | 'dismissed';
  acknowledged_by?: string;
  acknowledged_at?: string;
  severity_color: number;
  severity_emoji: string;
  event_type_name: string;
}

export interface WebSocketFilters {
  severity?: string[];
  event_types?: string[];
  tenant_id?: string;
}

export interface WebSocketMessage {
  type: string;
  [key: string]: unknown;
}

export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

export interface UseWebSocketReturn {
  alerts: Alert[];
  connectionStatus: ConnectionStatus;
  isPaused: boolean;
  error: string | null;
  sendMessage: (message: unknown) => void;
  acknowledgeAlert: (alertId: string) => void;
  dismissAlert: (alertId: string) => void;
  pauseStream: () => void;
  resumeStream: () => void;
  clearAlerts: () => void;
  updateFilters: (filters: WebSocketFilters) => void;
  connectionStats: {
    connectedClients: number;
    timestamp?: string;
  };
}

// Derive WebSocket URL from current page origin so it works in production
function getWsBaseUrl(): string {
  // Allow override via env var for development
  // @ts-ignore - import.meta is not fully typed
  const envUrl = (import.meta as any).env?.VITE_WS_URL;
  if (envUrl) return envUrl;

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  
  // If we are in dev mode using a proxy, we still want to use the current host
  // and the proxy routing rule in vite.config.ts will handle it.
  return `${protocol}//${window.location.host}/ws/alerts`;
}


const RECONNECT_INTERVAL = 3000;
const MAX_RECONNECT_ATTEMPTS = 5;

// Helper to get JWT token from Zustand persisted state
function getAuthToken(): string | null {
  try {
    const stored = localStorage.getItem('specterdefence-storage');
    if (stored) {
      const parsed = JSON.parse(stored);
      return parsed.state?.token || null;
    }
  } catch {
    // Ignore parse errors
  }
  return null;
}

export function useWebSocket(initialFilters?: WebSocketFilters): UseWebSocketReturn {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected');
  const [isPaused, setIsPaused] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [connectionStats, setConnectionStats] = useState<{ connectedClients: number; timestamp?: string }>({ connectedClients: 0 });

  const ws = useRef<WebSocket | null>(null);
  const reconnectAttempts = useRef(0);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const filters = useRef<WebSocketFilters>(initialFilters || {});
  const pendingAlerts = useRef<Alert[]>([]);

  const buildWsUrl = useCallback((): string => {
    const baseUrl = getWsBaseUrl();
    const params = new URLSearchParams();

    // Include auth token
    const token = getAuthToken();
    if (token) {
      params.append('token', token);
    }

    if (filters.current.severity?.length) {
      params.append('severity', filters.current.severity.join(','));
    }
    if (filters.current.event_types?.length) {
      params.append('event_types', filters.current.event_types.join(','));
    }
    if (filters.current.tenant_id) {
      params.append('tenant_id', filters.current.tenant_id);
    }

    const queryString = params.toString();
    return queryString ? `${baseUrl}?${queryString}` : baseUrl;
  }, []);

  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      return;
    }

    setConnectionStatus('connecting');
    setError(null);

    try {
      const url = buildWsUrl();
      ws.current = new WebSocket(url);

      ws.current.onopen = () => {
        setConnectionStatus('connected');
        reconnectAttempts.current = 0;

        // Process any pending alerts that arrived while disconnected
        if (pendingAlerts.current.length > 0 && !isPaused) {
          setAlerts(prev => [...pendingAlerts.current, ...prev].slice(0, 100));
          pendingAlerts.current = [];
        }
      };

      ws.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as WebSocketMessage;
          handleMessage(data);
        } catch (err) {
          console.error('Failed to parse WebSocket message:', err);
        }
      };

      ws.current.onclose = () => {
        setConnectionStatus('disconnected');
        attemptReconnect();
      };

      ws.current.onerror = (err) => {
        setConnectionStatus('error');
        setError('WebSocket connection error');
        console.error('WebSocket error:', err);
      };
    } catch (err) {
      setConnectionStatus('error');
      setError('Failed to create WebSocket connection');
      attemptReconnect();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [buildWsUrl, isPaused]);

  const attemptReconnect = useCallback(() => {
    if (reconnectAttempts.current >= MAX_RECONNECT_ATTEMPTS) {
      setError('Max reconnection attempts reached. Please refresh the page.');
      return;
    }

    reconnectAttempts.current += 1;

    if (reconnectTimer.current) {
      clearTimeout(reconnectTimer.current);
    }

    reconnectTimer.current = setTimeout(() => {
      connect();
    }, RECONNECT_INTERVAL * reconnectAttempts.current);
  }, [connect]);

  const handleMessage = useCallback((data: WebSocketMessage) => {
    switch (data.type) {
      case 'connection':
        console.log('WebSocket connected:', data);
        break;

      case 'initial_alerts': {
        const initialAlerts = (data.alerts as Alert[]) || [];
        setAlerts(initialAlerts);
        break;
      }

      case 'new_alert': {
        const newAlert = data.alert as Alert;
        if (isPaused) {
          pendingAlerts.current.unshift(newAlert);
        } else {
          setAlerts(prev => [newAlert, ...prev].slice(0, 100));
        }
        break;
      }

      case 'acknowledged': {
        const ackId = data.alert_id as string;
        setAlerts(prev =>
          prev.map(a =>
            a.id === ackId
              ? { ...a, status: 'acknowledged', acknowledged_by: data.acknowledged_by as string }
              : a
          )
        );
        break;
      }

      case 'dismissed': {
        const dismissId = data.alert_id as string;
        setAlerts(prev => prev.filter(a => a.id !== dismissId));
        break;
      }

      case 'stats':
        setConnectionStats({
          connectedClients: (data.connected_clients as number) || 0,
          timestamp: data.timestamp as string,
        });
        break;

      case 'pong':
        // Keepalive response
        break;

      case 'error':
        setError(data.message as string);
        break;

      default:
        console.log('Unknown message type:', data.type);
    }
  }, [isPaused]);

  const sendMessage = useCallback((message: unknown) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket not connected, message not sent');
    }
  }, []);

  const acknowledgeAlert = useCallback((alertId: string) => {
    sendMessage({
      type: 'acknowledge',
      alert_id: alertId,
    });
  }, [sendMessage]);

  const dismissAlert = useCallback((alertId: string) => {
    sendMessage({
      type: 'dismiss',
      alert_id: alertId,
    });
  }, [sendMessage]);

  const pauseStream = useCallback(() => {
    setIsPaused(true);
  }, []);

  const resumeStream = useCallback(() => {
    setIsPaused(false);
    // Process pending alerts
    if (pendingAlerts.current.length > 0) {
      setAlerts(prev => [...pendingAlerts.current, ...prev].slice(0, 100));
      pendingAlerts.current = [];
    }
  }, []);

  const clearAlerts = useCallback(() => {
    setAlerts([]);
    pendingAlerts.current = [];
  }, []);

  const updateFilters = useCallback((newFilters: WebSocketFilters) => {
    filters.current = newFilters;
    // Reconnect with new filters
    if (ws.current) {
      ws.current.close();
    }
    connect();
  }, [connect]);

  // Keepalive ping
  useEffect(() => {
    if (connectionStatus !== 'connected') return;

    const pingInterval = setInterval(() => {
      sendMessage({ type: 'ping' });
    }, 30000);

    return () => clearInterval(pingInterval);
  }, [connectionStatus, sendMessage]);

  // Initial connection
  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimer.current) {
        clearTimeout(reconnectTimer.current);
      }
      if (ws.current) {
        ws.current.close();
      }
    };
  }, [connect]);

  return {
    alerts,
    connectionStatus,
    isPaused,
    error,
    sendMessage,
    acknowledgeAlert,
    dismissAlert,
    pauseStream,
    resumeStream,
    clearAlerts,
    updateFilters,
    connectionStats,
  };
}
