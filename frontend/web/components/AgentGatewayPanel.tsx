import React, { useState, useEffect, useCallback } from 'react';

type ConnectionStatus = 'connected' | 'connecting' | 'disconnected' | 'error';
type MessagePriority = 'high' | 'normal' | 'low';
type DeliveryStatus = 'delivered' | 'pending' | 'failed' | 'queued';

interface GatewayEndpoint {
  id: string;
  name: string;
  url: string;
  protocol: 'ws' | 'http' | 'grpc' | 'mqtt';
  status: ConnectionStatus;
  messages_routed: number;
  last_activity: string;
  uptime: string;
}

interface ActiveConnection {
  id: string;
  endpoint_name: string;
  source: string;
  destination: string;
  status: ConnectionStatus;
  established_at: string;
  bytes_transferred: number;
  latency_ms: number;
}

interface MessageQueueEntry {
  id: string;
  endpoint: string;
  priority: MessagePriority;
  payload_preview: string;
  status: DeliveryStatus;
  size_bytes: number;
  retries: number;
  timestamp: number;
}

interface DeliveryLog {
  id: string;
  endpoint: string;
  message_id: string;
  status: DeliveryStatus;
  latency_ms: number;
  error_message: string | null;
  timestamp: number;
}

interface GatewayStats {
  total_endpoints: number;
  active_connections: number;
  queue_depth: number;
  messages_routed_total: number;
  bytes_transferred_total: number;
  avg_latency_ms: number;
  uptime: string;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const CONNECTION_STATUS_COLORS: Record<ConnectionStatus, string> = {
  connected: '#6bcb77',
  connecting: '#fdcb6e',
  disconnected: '#888',
  error: '#ff6b6b',
};

const CONNECTION_STATUS_LABELS: Record<ConnectionStatus, string> = {
  connected: 'Connected',
  connecting: 'Connecting',
  disconnected: 'Offline',
  error: 'Error',
};

const PRIORITY_COLORS: Record<MessagePriority, string> = {
  high: '#ff6b6b',
  normal: '#74b9ff',
  low: '#888',
};

const PRIORITY_LABELS: Record<MessagePriority, string> = {
  high: 'HIGH',
  normal: 'NORMAL',
  low: 'LOW',
};

const DELIVERY_COLORS: Record<DeliveryStatus, string> = {
  delivered: '#6bcb77',
  pending: '#fdcb6e',
  failed: '#ff6b6b',
  queued: '#74b9ff',
};

const DELIVERY_LABELS: Record<DeliveryStatus, string> = {
  delivered: 'Delivered',
  pending: 'Pending',
  failed: 'Failed',
  queued: 'Queued',
};

const PROTOCOL_COLORS: Record<string, string> = {
  ws: '#6bcb77',
  http: '#74b9ff',
  grpc: '#a29bfe',
  mqtt: '#fdcb6e',
};

const AgentGatewayPanel: React.FC = () => {
  const [endpoints, setEndpoints] = useState<GatewayEndpoint[]>([]);
  const [connections, setConnections] = useState<ActiveConnection[]>([]);
  const [messageQueue, setMessageQueue] = useState<MessageQueueEntry[]>([]);
  const [deliveryLogs, setDeliveryLogs] = useState<DeliveryLog[]>([]);
  const [stats, setStats] = useState<GatewayStats | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [selectedEndpoint, setSelectedEndpoint] = useState<string | null>(null);

  const apiBase = 'http://localhost:8000/api/agent';

  const defaultEndpoints: GatewayEndpoint[] = [
    { id: uid(), name: 'Game Director API', url: 'ws://localhost:9001/director', protocol: 'ws', status: 'connected', messages_routed: 45231, last_activity: '3s ago', uptime: '4h 22m' },
    { id: uid(), name: 'Balance Engine', url: 'http://localhost:9002/balance', protocol: 'http', status: 'connected', messages_routed: 12890, last_activity: '12s ago', uptime: '3h 15m' },
    { id: uid(), name: 'Narrative Service', url: 'grpc://localhost:9003/narrative', protocol: 'grpc', status: 'connecting', messages_routed: 7845, last_activity: '45s ago', uptime: '2h 08m' },
    { id: uid(), name: 'Player Analytics', url: 'mqtt://localhost:9004/analytics', protocol: 'mqtt', status: 'connected', messages_routed: 32100, last_activity: '5s ago', uptime: '4h 50m' },
    { id: uid(), name: 'Dev Assistant Hub', url: 'ws://localhost:9005/dev', protocol: 'ws', status: 'error', messages_routed: 340, last_activity: '5m ago', uptime: '10m' },
    { id: uid(), name: 'Playtest Simulator', url: 'http://localhost:9006/playtest', protocol: 'http', status: 'disconnected', messages_routed: 5600, last_activity: '1h ago', uptime: '0m' },
  ];

  const defaultConnections: ActiveConnection[] = [
    { id: uid(), endpoint_name: 'Game Director API', source: 'frontend', destination: 'director-service', status: 'connected', established_at: '4h 22m ago', bytes_transferred: 12400000, latency_ms: 8 },
    { id: uid(), endpoint_name: 'Balance Engine', source: 'orchestrator', destination: 'balance-service', status: 'connected', established_at: '3h 15m ago', bytes_transferred: 3400000, latency_ms: 24 },
    { id: uid(), endpoint_name: 'Player Analytics', source: 'game-server', destination: 'analytics-service', status: 'connected', established_at: '4h 50m ago', bytes_transferred: 8900000, latency_ms: 5 },
    { id: uid(), endpoint_name: 'Narrative Service', source: 'frontend', destination: 'narrative-service', status: 'connecting', established_at: '45s ago', bytes_transferred: 120000, latency_ms: 120 },
    { id: uid(), endpoint_name: 'Dev Assistant Hub', source: 'ide-plugin', destination: 'dev-service', status: 'error', established_at: '10m ago', bytes_transferred: 45000, latency_ms: 0 },
  ];

  const defaultQueue: MessageQueueEntry[] = [
    { id: uid(), endpoint: 'Game Director API', priority: 'high', payload_preview: '{ "action": "start_sprint", "sprint_id": 42 }', status: 'queued', size_bytes: 256, retries: 0, timestamp: Date.now() - 5000 },
    { id: uid(), endpoint: 'Balance Engine', priority: 'normal', payload_preview: '{ "action": "analyze_economy", "params": {...} }', status: 'pending', size_bytes: 512, retries: 1, timestamp: Date.now() - 30000 },
    { id: uid(), endpoint: 'Narrative Service', priority: 'high', payload_preview: '{ "action": "generate_dialogue", "npc": "innkeeper" }', status: 'queued', size_bytes: 384, retries: 0, timestamp: Date.now() - 12000 },
    { id: uid(), endpoint: 'Player Analytics', priority: 'low', payload_preview: '{ "action": "log_session", "session_id": "s887" }', status: 'pending', size_bytes: 128, retries: 2, timestamp: Date.now() - 60000 },
    { id: uid(), endpoint: 'Dev Assistant Hub', priority: 'high', payload_preview: '{ "action": "code_review", "file": "combat_system.py" }', status: 'failed', size_bytes: 768, retries: 3, timestamp: Date.now() - 120000 },
  ];

  const defaultLogs: DeliveryLog[] = [
    { id: uid(), endpoint: 'Game Director API', message_id: 'msg-001', status: 'delivered', latency_ms: 8, error_message: null, timestamp: Date.now() - 3000 },
    { id: uid(), endpoint: 'Player Analytics', message_id: 'msg-002', status: 'delivered', latency_ms: 5, error_message: null, timestamp: Date.now() - 5000 },
    { id: uid(), endpoint: 'Balance Engine', message_id: 'msg-003', status: 'delivered', latency_ms: 22, error_message: null, timestamp: Date.now() - 12000 },
    { id: uid(), endpoint: 'Narrative Service', message_id: 'msg-004', status: 'pending', latency_ms: 0, error_message: null, timestamp: Date.now() - 45000 },
    { id: uid(), endpoint: 'Dev Assistant Hub', message_id: 'msg-005', status: 'failed', latency_ms: 5000, error_message: 'Connection refused', timestamp: Date.now() - 120000 },
  ];

  const defaultStats: GatewayStats = {
    total_endpoints: 6,
    active_connections: 3,
    queue_depth: 5,
    messages_routed_total: 104006,
    bytes_transferred_total: 25365000,
    avg_latency_ms: 14,
    uptime: '5d 3h 42m',
  };

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/gateway/stats`);
      const data = await res.json();
      if (data.endpoints) setEndpoints(data.endpoints);
      if (data.stats) setStats(data.stats);
    } catch {}
  }, []);

  const fetchConnections = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/gateway/active-connections`);
      const data = await res.json();
      if (data.connections) setConnections(data.connections);
    } catch {}
  }, []);

  const fetchQueue = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/gateway/message-queue`);
      const data = await res.json();
      if (data.queue) setMessageQueue(data.queue);
      if (data.logs) setDeliveryLogs(data.logs);
    } catch {}
  }, []);

  useEffect(() => {
    setEndpoints(defaultEndpoints);
    setConnections(defaultConnections);
    setMessageQueue(defaultQueue);
    setDeliveryLogs(defaultLogs);
    setStats(defaultStats);
    fetchStats();
    fetchConnections();
    fetchQueue();
  }, [fetchStats, fetchConnections, fetchQueue]);

  const handleRegisterEndpoint = async () => {
    try {
      await fetch(`${apiBase}/gateway/register-endpoint`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: `New Endpoint ${endpoints.length + 1}`,
          url: `http://localhost:${9000 + endpoints.length + 1}/service`,
          protocol: 'http',
        }),
      });
      showMessage('Endpoint registered successfully', 'success');
      fetchStats();
    } catch {
      const newEndpoint: GatewayEndpoint = {
        id: uid(),
        name: `New Endpoint ${endpoints.length + 1}`,
        url: `http://localhost:${9000 + endpoints.length + 1}/service`,
        protocol: 'http',
        status: 'connecting',
        messages_routed: 0,
        last_activity: 'just now',
        uptime: '0m',
      };
      setEndpoints(prev => [...prev, newEndpoint]);
      showMessage('Endpoint registered (offline fallback)', 'info');
    }
  };

  const handleOpenConnection = async () => {
    if (!selectedEndpoint) {
      showMessage('Select an endpoint to connect to first', 'error');
      return;
    }
    const ep = endpoints.find(e => e.id === selectedEndpoint);
    try {
      await fetch(`${apiBase}/gateway/open-connection`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ endpoint_id: selectedEndpoint }),
      });
      showMessage(`Connection opened for ${ep?.name || 'endpoint'}`, 'success');
      fetchConnections();
    } catch {
      if (ep) {
        const newConn: ActiveConnection = {
          id: uid(),
          endpoint_name: ep.name,
          source: 'gateway',
          destination: ep.url,
          status: 'connected',
          established_at: 'just now',
          bytes_transferred: 0,
          latency_ms: Math.floor(Math.random() * 30) + 2,
        };
        setConnections(prev => [...prev, newConn]);
        setEndpoints(prev => prev.map(e => e.id === selectedEndpoint ? { ...e, status: 'connected' as ConnectionStatus } : e));
      }
      showMessage(`Connection opened for ${ep?.name || 'endpoint'} (offline fallback)`, 'info');
    }
  };

  const handleRouteMessage = async () => {
    if (!selectedEndpoint) {
      showMessage('Select an endpoint to route to first', 'error');
      return;
    }
    const ep = endpoints.find(e => e.id === selectedEndpoint);
    try {
      await fetch(`${apiBase}/gateway/route-message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          endpoint_id: selectedEndpoint,
          payload: { action: 'test', data: 'sample' },
          priority: 'normal',
        }),
      });
      showMessage(`Message routed to ${ep?.name || 'endpoint'}`, 'success');
      fetchStats();
      fetchQueue();
    } catch {
      const newEntry: MessageQueueEntry = {
        id: uid(),
        endpoint: ep?.name || 'Unknown',
        priority: 'normal',
        payload_preview: '{ "action": "test", "data": "sample" }',
        status: 'queued',
        size_bytes: 128,
        retries: 0,
        timestamp: Date.now(),
      };
      setMessageQueue(prev => [newEntry, ...prev].slice(0, 50));
      showMessage(`Message routed to ${ep?.name || 'endpoint'} (offline fallback)`, 'info');
    }
  };

  const handleBroadcast = async () => {
    try {
      await fetch(`${apiBase}/gateway/broadcast-message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          payload: { action: 'broadcast', type: 'health_check' },
          target_endpoints: endpoints.filter(e => e.status === 'connected').map(e => e.id),
        }),
      });
      showMessage('Broadcast sent to all connected endpoints', 'success');
      fetchStats();
    } catch {
      const connectedEps = endpoints.filter(e => e.status === 'connected');
      const newEntries: MessageQueueEntry[] = connectedEps.map(ep => ({
        id: uid(),
        endpoint: ep.name,
        priority: 'high' as MessagePriority,
        payload_preview: '{ "action": "broadcast", "type": "health_check" }',
        status: 'queued' as DeliveryStatus,
        size_bytes: 96,
        retries: 0,
        timestamp: Date.now(),
      }));
      setMessageQueue(prev => [...newEntries, ...prev].slice(0, 50));
      showMessage(`Broadcast sent to ${connectedEps.length} endpoints (offline fallback)`, 'info');
    }
  };

  const formatTime = (ts: number) => {
    const d = new Date(ts);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  const formatBytes = (bytes: number): string => {
    if (bytes >= 1000000) return `${(bytes / 1000000).toFixed(1)} MB`;
    if (bytes >= 1000) return `${(bytes / 1000).toFixed(1)} KB`;
    return `${bytes} B`;
  };

  const connectedCount = endpoints.filter(e => e.status === 'connected').length;

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', height: '100%',
      backgroundColor: '#1a1a2e', color: '#e0e0e0',
      fontFamily: 'system-ui, sans-serif', fontSize: 13,
    }}>
      <div style={{
        padding: '12px 16px', borderBottom: '1px solid #2a2a3e',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 18 }}>🌐</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Agent Gateway</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {stats && (
            <span style={{ fontSize: 10, color: '#888' }}>
              <span style={{ fontSize: 12, marginRight: 4 }}>📡</span>
              {connectedCount} connected · {(stats.bytes_transferred_total / 1000000).toFixed(0)} MB
            </span>
          )}
        </div>
      </div>

      {message && (
        <div style={{
          padding: '8px 16px', fontSize: 12,
          backgroundColor: message.type === 'success' ? '#1a3a1a' : message.type === 'error' ? '#3a1a1a' : '#1a2a3a',
          borderBottom: `1px solid ${message.type === 'success' ? '#2d5a2d' : message.type === 'error' ? '#5a2d2d' : '#2a3a4a'}`,
          color: message.type === 'success' ? '#6bcb77' : message.type === 'error' ? '#ff6b6b' : '#74b9ff',
        }}>
          {message.text}
        </div>
      )}

      <div style={{ padding: '10px 16px', borderBottom: '1px solid #2a2a3e', display: 'flex', gap: 6, flexWrap: 'wrap' }}>
        <button onClick={handleRegisterEndpoint} style={{
          padding: '6px 12px', fontSize: 11, fontWeight: 600,
          backgroundColor: '#2d3a4a', color: '#74b9ff',
          border: '1px solid #3d4a5a', borderRadius: 4, cursor: 'pointer',
        }}>
          <span style={{ marginRight: 4 }}>🌐</span>Register Endpoint
        </button>
        <button onClick={handleOpenConnection} style={{
          padding: '6px 12px', fontSize: 11, fontWeight: 600,
          backgroundColor: '#2d4a2d', color: '#6bcb77',
          border: '1px solid #3d5a3d', borderRadius: 4, cursor: 'pointer',
        }}>
          <span style={{ marginRight: 4 }}>📡</span>Open Connection
        </button>
        <button onClick={handleRouteMessage} style={{
          padding: '6px 12px', fontSize: 11, fontWeight: 600,
          backgroundColor: '#4a3d2d', color: '#fdcb6e',
          border: '1px solid #5a4d3d', borderRadius: 4, cursor: 'pointer',
        }}>
          <span style={{ marginRight: 4 }}>📨</span>Route Message
        </button>
        <button onClick={handleBroadcast} style={{
          padding: '6px 12px', fontSize: 11, fontWeight: 600,
          backgroundColor: '#3a2d3a', color: '#a29bfe',
          border: '1px solid #4a3d4a', borderRadius: 4, cursor: 'pointer',
        }}>
          <span style={{ marginRight: 4 }}>📡</span>Broadcast
        </button>
      </div>

      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        <div style={{
          width: 340, borderRight: '1px solid #2a2a3e',
          overflow: 'auto', padding: 12, display: 'flex', flexDirection: 'column', gap: 10,
        }}>
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 2, display: 'flex', alignItems: 'center', gap: 6 }}>
            <span>🌐</span>Endpoints
            <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({endpoints.length})</span>
          </div>

          {endpoints.map(ep => (
            <div key={ep.id} style={{
              padding: 10, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
              borderLeft: `3px solid ${CONNECTION_STATUS_COLORS[ep.status]}`,
              cursor: 'pointer',
              opacity: selectedEndpoint === ep.id ? 1 : 0.85,
              boxShadow: selectedEndpoint === ep.id ? '0 0 8px rgba(108, 92, 231, 0.3)' : 'none',
            }} onClick={() => setSelectedEndpoint(selectedEndpoint === ep.id ? null : ep.id)}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span style={{ fontSize: 14 }}>🌐</span>
                  <span style={{ fontWeight: 600, fontSize: 12 }}>{ep.name}</span>
                </div>
                <span style={{
                  fontSize: 9, padding: '2px 6px', borderRadius: 3,
                  backgroundColor: CONNECTION_STATUS_COLORS[ep.status] + '33',
                  color: CONNECTION_STATUS_COLORS[ep.status], fontWeight: 600,
                }}>
                  <i className="fa-solid fa-circle" style={{ fontSize: 5, marginRight: 3 }} />
                  {CONNECTION_STATUS_LABELS[ep.status]}
                </span>
              </div>
              <div style={{ fontSize: 10, color: '#666', marginBottom: 4 }}>
                <div style={{
                  padding: '1px 4px', borderRadius: 2, display: 'inline-block',
                  backgroundColor: PROTOCOL_COLORS[ep.protocol] + '33',
                  color: PROTOCOL_COLORS[ep.protocol], fontWeight: 600,
                }}>
                  {ep.protocol.toUpperCase()}
                </div>
                <span style={{ marginLeft: 6 }}>{ep.url}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: '#666' }}>
                <span>{ep.messages_routed.toLocaleString()} routed</span>
                <span>Uptime: {ep.uptime}</span>
              </div>
            </div>
          ))}
        </div>

        <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {stats && (
              <div style={{
                padding: 14, backgroundColor: '#22223a', borderRadius: 8,
                border: '1px solid #2a2a3e',
              }}>
                <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 10, display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span>📡</span>Gateway Stats
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
                  <div style={{ padding: 8, backgroundColor: '#1a1a2e', borderRadius: 4, textAlign: 'center' }}>
                    <div style={{ fontSize: 9, color: '#666', marginBottom: 2 }}>Endpoints</div>
                    <div style={{ fontSize: 16, fontWeight: 700, color: '#74b9ff' }}>{stats.total_endpoints}</div>
                  </div>
                  <div style={{ padding: 8, backgroundColor: '#1a1a2e', borderRadius: 4, textAlign: 'center' }}>
                    <div style={{ fontSize: 9, color: '#666', marginBottom: 2 }}>Active Conn.</div>
                    <div style={{ fontSize: 16, fontWeight: 700, color: '#6bcb77' }}>{stats.active_connections}</div>
                  </div>
                  <div style={{ padding: 8, backgroundColor: '#1a1a2e', borderRadius: 4, textAlign: 'center' }}>
                    <div style={{ fontSize: 9, color: '#666', marginBottom: 2 }}>Queue Depth</div>
                    <div style={{ fontSize: 16, fontWeight: 700, color: '#fdcb6e' }}>{stats.queue_depth}</div>
                  </div>
                  <div style={{ padding: 8, backgroundColor: '#1a1a2e', borderRadius: 4, textAlign: 'center' }}>
                    <div style={{ fontSize: 9, color: '#666', marginBottom: 2 }}>Messages Routed</div>
                    <div style={{ fontSize: 16, fontWeight: 700, color: '#a29bfe' }}>{stats.messages_routed_total.toLocaleString()}</div>
                  </div>
                  <div style={{ padding: 8, backgroundColor: '#1a1a2e', borderRadius: 4, textAlign: 'center' }}>
                    <div style={{ fontSize: 9, color: '#666', marginBottom: 2 }}>Data Transferred</div>
                    <div style={{ fontSize: 16, fontWeight: 700, color: '#ff9f43' }}>{formatBytes(stats.bytes_transferred_total)}</div>
                  </div>
                  <div style={{ padding: 8, backgroundColor: '#1a1a2e', borderRadius: 4, textAlign: 'center' }}>
                    <div style={{ fontSize: 9, color: '#666', marginBottom: 2 }}>Avg Latency</div>
                    <div style={{ fontSize: 16, fontWeight: 700, color: '#e0e0e0' }}>{stats.avg_latency_ms}ms</div>
                  </div>
                </div>
              </div>
            )}

            <div>
              <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
                <span>📡</span>Active Connections
                <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({connections.length})</span>
              </div>
              {connections.length > 0 ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {connections.map(conn => (
                    <div key={conn.id} style={{
                      padding: 8, backgroundColor: '#22223a', borderRadius: 6,
                      border: '1px solid #2a2a3e',
                      borderLeft: `3px solid ${CONNECTION_STATUS_COLORS[conn.status]}`,
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 3 }}>
                        <span style={{ fontSize: 11, fontWeight: 600, color: '#aaa' }}>{conn.endpoint_name}</span>
                        <span style={{
                          fontSize: 9, padding: '1px 5px', borderRadius: 3,
                          backgroundColor: CONNECTION_STATUS_COLORS[conn.status] + '33',
                          color: CONNECTION_STATUS_COLORS[conn.status], fontWeight: 600,
                        }}>
                          {CONNECTION_STATUS_LABELS[conn.status]}
                        </span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: '#888' }}>
                        <span>{conn.source} → {conn.destination}</span>
                        <span>{formatBytes(conn.bytes_transferred)} · {conn.latency_ms}ms</span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{
                  textAlign: 'center', padding: 20, color: '#555',
                  backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e',
                }}>
                  <span style={{ fontSize: 24, opacity: 0.3, display: 'block', marginBottom: 6 }}>📡</span>
                  No active connections
                </div>
              )}
            </div>

            <div>
              <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
                <span>📨</span>Message Queue
                <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({messageQueue.length})</span>
              </div>
              {messageQueue.length > 0 ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {messageQueue.slice(0, 5).map(qEntry => (
                    <div key={qEntry.id} style={{
                      padding: 8, backgroundColor: '#22223a', borderRadius: 6,
                      border: '1px solid #2a2a3e',
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 3 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                          <span style={{ fontSize: 11, fontWeight: 600, color: '#aaa' }}>{qEntry.endpoint}</span>
                          <span style={{
                            fontSize: 8, padding: '1px 4px', borderRadius: 2,
                            backgroundColor: PRIORITY_COLORS[qEntry.priority] + '33',
                            color: PRIORITY_COLORS[qEntry.priority], fontWeight: 700,
                          }}>
                            {PRIORITY_LABELS[qEntry.priority]}
                          </span>
                        </div>
                        <span style={{
                          fontSize: 9, padding: '1px 5px', borderRadius: 3,
                          backgroundColor: DELIVERY_COLORS[qEntry.status] + '33',
                          color: DELIVERY_COLORS[qEntry.status], fontWeight: 600,
                        }}>
                          {DELIVERY_LABELS[qEntry.status]}
                        </span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontSize: 10, color: '#888' }}>{qEntry.payload_preview}</span>
                        <div style={{ display: 'flex', gap: 8, fontSize: 10, color: '#666' }}>
                          <span>{qEntry.size_bytes}B</span>
                          {qEntry.retries > 0 && <span style={{ color: '#ff6b6b' }}>{qEntry.retries} retries</span>}
                          <span>{formatTime(qEntry.timestamp)}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{
                  textAlign: 'center', padding: 20, color: '#555',
                  backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e',
                }}>
                  <span style={{ fontSize: 24, opacity: 0.3, display: 'block', marginBottom: 6 }}>📨</span>
                  Message queue empty
                </div>
              )}
            </div>

            <div>
              <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
                <span>📨</span>Delivery Logs
                <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({deliveryLogs.length})</span>
              </div>
              {deliveryLogs.length > 0 ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                  {deliveryLogs.slice(0, 5).map(log => (
                    <div key={log.id} style={{
                      padding: 6, backgroundColor: '#22223a', borderRadius: 4,
                      border: '1px solid #2a2a3e',
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                          <span style={{ fontSize: 10, fontWeight: 600, color: '#aaa' }}>{log.endpoint}</span>
                          <span style={{
                            fontSize: 8, padding: '1px 4px', borderRadius: 2,
                            backgroundColor: DELIVERY_COLORS[log.status] + '33',
                            color: DELIVERY_COLORS[log.status], fontWeight: 600,
                          }}>
                            {DELIVERY_LABELS[log.status]}
                          </span>
                          {log.error_message && (
                            <span style={{ fontSize: 8, color: '#ff6b6b' }}>{log.error_message}</span>
                          )}
                        </div>
                        <div style={{ display: 'flex', gap: 8, fontSize: 9, color: '#666' }}>
                          <span>{log.latency_ms}ms</span>
                          <span>{formatTime(log.timestamp)}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{
                  textAlign: 'center', padding: 16, color: '#555',
                  backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e',
                }}>
                  <span style={{ fontSize: 20, opacity: 0.3, display: 'block', marginBottom: 6 }}>📨</span>
                  No delivery logs
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      <div style={{
        padding: '6px 12px', borderTop: '1px solid #2a2a3e',
        backgroundColor: '#141428', display: 'flex',
        alignItems: 'center', justifyContent: 'space-between',
        fontSize: 10, color: '#666',
      }}>
        <span>
          <span style={{ marginRight: 4 }}>🌐</span>
          {endpoints.length} endpoints · {connectedCount} connected · {stats ? `${stats.queue_depth} queued` : ''}
        </span>
        <span>
          {stats ? `${stats.uptime} uptime` : 'Connected'}
        </span>
      </div>
    </div>
  );
};

export default AgentGatewayPanel;