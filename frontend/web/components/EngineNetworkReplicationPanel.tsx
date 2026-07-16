"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT;

interface ReplicationStats {
  active_connections: number;
  total_events: number;
  avg_latency_ms: number;
  bandwidth_usage_kbps: number;
  packet_loss_pct: number;
  entities_replicated: number;
  uptime_seconds: number;
  [key: string]: any;
}

interface NetworkIdentity {
  id: string;
  entity_type: string;
  owner_client_id: string;
  is_authoritative: boolean;
  replication_mode: string;
  spawn_position: { x: number; y: number; z: number };
  priority: number;
}

interface StateEntry {
  identity_id: string;
  position: { x: number; y: number; z: number };
  rotation: { x: number; y: number; z: number };
  velocity: { x: number; y: number; z: number };
  custom_state: any;
  timestamp: string;
}

interface NetworkEvent {
  event_type: string;
  source_id: string;
  target_id: string;
  payload: any;
  reliable: boolean;
}

interface Client {
  id: string;
  address: string;
  port: number;
  role: string;
  status: string;
  connected_at: string;
}

interface Match {
  id: string;
  room_name: string;
  max_players: number;
  game_mode: string;
  status: string;
  player_count: number;
}

const EVENT_TYPES = ['connect', 'disconnect', 'spawn', 'despawn', 'rpc', 'sync', 'matchmake'];
const REPLICATION_MODES = ['full', 'lerp', 'snap', 'interpolation', 'prediction'];
const ROLES = ['server', 'client', 'host', 'spectator'];
const GAME_MODES = ['deathmatch', 'team_deathmatch', 'capture_flag', 'battle_royale', 'coop', 'custom'];

type TabId = 'status' | 'entities' | 'state' | 'events' | 'clients' | 'matches';

const EngineNetworkReplicationPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabId>('status');
  const [data, setData] = useState<ReplicationStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Entities
  const [eType, setEType] = useState('player');
  const [eOwnerId, setEOwnerId] = useState('');
  const [eAuthoritative, setEAuthoritative] = useState(true);
  const [eReplicationMode, setEReplicationMode] = useState('full');
  const [ePriority, setEPriority] = useState('1');
  const [ePosX, setEPosX] = useState('0');
  const [ePosY, setEPosY] = useState('0');
  const [ePosZ, setEPosZ] = useState('0');
  const [stateHistory, setStateHistory] = useState<StateEntry[]>([]);

  // State
  const [stIdentityId, setStIdentityId] = useState('');
  const [stPosX, setStPosX] = useState('0');
  const [stPosY, setStPosY] = useState('0');
  const [stPosZ, setStPosZ] = useState('0');
  const [stRotX, setStRotX] = useState('0');
  const [stRotY, setStRotY] = useState('0');
  const [stRotZ, setStRotZ] = useState('0');
  const [stVelX, setStVelX] = useState('0');
  const [stVelY, setStVelY] = useState('0');
  const [stVelZ, setStVelZ] = useState('0');
  const [stCustom, setStCustom] = useState('');

  // Events
  const [evType, setEvType] = useState('sync');
  const [evSourceId, setEvSourceId] = useState('');
  const [evTargetId, setEvTargetId] = useState('');
  const [evPayload, setEvPayload] = useState('');
  const [evReliable, setEvReliable] = useState(true);

  // Clients
  const [cAddress, setCAddress] = useState('127.0.0.1');
  const [cPort, setCPort] = useState('7777');
  const [cRole, setCRole] = useState('client');
  const [clients, setClients] = useState<Client[]>([]);

  // Matches
  const [mRoomName, setMRoomName] = useState('');
  const [mMaxPlayers, setMMaxPlayers] = useState('4');
  const [mGameMode, setMGameMode] = useState('deathmatch');
  const [interestClientId, setInterestClientId] = useState('');
  const [interestRadius, setInterestRadius] = useState('100');
  const [reconcileClientId, setReconcileClientId] = useState('');
  const [reconcileState, setReconcileState] = useState('');

  const tabs = [
    { id: 'status' as TabId, label: 'Status' },
    { id: 'entities' as TabId, label: 'Entities' },
    { id: 'state' as TabId, label: 'State' },
    { id: 'events' as TabId, label: 'Events' },
    { id: 'clients' as TabId, label: 'Clients' },
    { id: 'matches' as TabId, label: 'Matches' },
  ];

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/engine/network-replication/stats`);
      if (res.ok) setData(await res.json());
    } catch (e) { console.error(e); }
  }, []);

  const fetchClients = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/engine/network-replication/clients`);
      if (res.ok) {
        const json = await res.json();
        setClients(json.clients || json || []);
      }
    } catch (e) { console.error(e); }
  }, []);

  useEffect(() => {
    fetchStats();
    fetchClients();
    const i = setInterval(fetchStats, 15000);
    return () => clearInterval(i);
  }, [fetchStats, fetchClients]);

  const showMessage = (type: 'success' | 'error', text: string) => {
    setMessage({ type, text });
    setTimeout(() => setMessage(null), 4000);
  };

  const handleSubmit = async (endpoint: string, body: any) => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (res.ok) {
        const result = await res.json();
        showMessage('success', 'Operation successful');
        setLoading(false);
        return result;
      } else {
        showMessage('error', `Error: ${res.status}`);
        setLoading(false);
        return null;
      }
    } catch (e: any) {
      showMessage('error', e.message);
      setLoading(false);
      return null;
    }
  };

  const renderStatusTab = () => (
    <div>
      {data ? (
        <div className="grid grid-cols-2 gap-3">
          {[
            { key: 'active_connections', label: 'Active Connections', icon: 'C' },
            { key: 'total_events', label: 'Total Events', icon: 'E' },
            { key: 'avg_latency_ms', label: 'Avg Latency (ms)', icon: 'L' },
            { key: 'bandwidth_usage_kbps', label: 'Bandwidth (kbps)', icon: 'B' },
            { key: 'packet_loss_pct', label: 'Packet Loss (%)', icon: 'PL' },
            { key: 'entities_replicated', label: 'Entities Replicated', icon: 'ER' },
            { key: 'uptime_seconds', label: 'Uptime (s)', icon: 'U' },
          ].map(({ key, label, icon }) => (
            <div key={key} className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-[#00d4ff] text-xs font-bold bg-[#0d0d0d] px-2 py-0.5 rounded">{icon}</span>
                <span className="text-[#999] text-xs">{label}</span>
              </div>
              <div className="text-white text-2xl font-bold">
                {key === 'avg_latency_ms' || key === 'bandwidth_usage_kbps' || key === 'packet_loss_pct'
                  ? Number(data[key]).toFixed(2)
                  : data[key] !== undefined ? Number(data[key]).toLocaleString() : 'N/A'}
              </div>
            </div>
          ))}
          {Object.entries(data).filter(([k]) => !['active_connections', 'total_events', 'avg_latency_ms', 'bandwidth_usage_kbps', 'packet_loss_pct', 'entities_replicated', 'uptime_seconds'].includes(k)).map(([key, value]) => (
            <div key={key} className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
              <span className="text-[#999] text-xs">{key.replace(/_/g, ' ')}</span>
              <div className="text-white text-sm font-mono mt-1">{typeof value === 'number' ? value.toLocaleString() : String(value)}</div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-[#999] text-sm">No network replication stats available</div>
      )}
    </div>
  );

  const renderEntitiesTab = () => (
    <div className="space-y-4">
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
        <div className="text-sm font-medium text-[#00d4ff] mb-3">Register Network Identity</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-[#999] mb-1 block">Entity Type</label>
            <input type="text" value={eType} onChange={(e) => setEType(e.target.value)} placeholder="player" className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Owner Client ID</label>
            <input type="text" value={eOwnerId} onChange={(e) => setEOwnerId(e.target.value)} placeholder="client_001" className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Replication Mode</label>
            <select value={eReplicationMode} onChange={(e) => setEReplicationMode(e.target.value)} className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none">
              {REPLICATION_MODES.map((m) => <option key={m} value={m}>{m}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Priority</label>
            <input type="number" value={ePriority} onChange={(e) => setEPriority(e.target.value)} className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Authoritative</label>
            <label className="flex items-center gap-2 cursor-pointer mt-1">
              <input type="checkbox" checked={eAuthoritative} onChange={(e) => setEAuthoritative(e.target.checked)} className="accent-[#00d4ff]" />
              <span className="text-white text-xs">Server has authority</span>
            </label>
          </div>
          <div></div>
          <div className="col-span-2">
            <label className="text-xs text-[#999] mb-1 block">Spawn Position</label>
            <div className="grid grid-cols-3 gap-2">
              <input type="number" value={ePosX} onChange={(e) => setEPosX(e.target.value)} placeholder="X" className="bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
              <input type="number" value={ePosY} onChange={(e) => setEPosY(e.target.value)} placeholder="Y" className="bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
              <input type="number" value={ePosZ} onChange={(e) => setEPosZ(e.target.value)} placeholder="Z" className="bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
            </div>
          </div>
        </div>
        <button
          onClick={async () => {
            if (!eType.trim()) { showMessage('error', 'Entity type required'); return; }
            const result = await handleSubmit('/engine/network-replication/register-identity', {
              entity_type: eType,
              owner_client_id: eOwnerId,
              is_authoritative: eAuthoritative,
              replication_mode: eReplicationMode,
              spawn_position: { x: parseFloat(ePosX) || 0, y: parseFloat(ePosY) || 0, z: parseFloat(ePosZ) || 0 },
              priority: parseInt(ePriority) || 1,
            });
            if (result) {
              const entry: StateEntry = {
                identity_id: result.identity_id || result.id || 'registered',
                position: { x: parseFloat(ePosX) || 0, y: parseFloat(ePosY) || 0, z: parseFloat(ePosZ) || 0 },
                rotation: { x: 0, y: 0, z: 0 },
                velocity: { x: 0, y: 0, z: 0 },
                custom_state: null,
                timestamp: new Date().toISOString(),
              };
              setStateHistory((prev) => [...prev, entry]);
            }
          }}
          disabled={loading}
          className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50"
        >
          Register Identity
        </button>
      </div>

      {stateHistory.length > 0 && (
        <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
          <div className="text-sm font-medium text-[#00d4ff] mb-3">State History ({stateHistory.length})</div>
          <div className="space-y-1 max-h-64 overflow-auto">
            {stateHistory.map((entry, i) => (
              <div key={i} className="bg-[#0d0d0d] border border-[#2a2a4a] rounded p-2 text-xs">
                <div className="flex items-center justify-between">
                  <span className="text-white font-mono">{entry.identity_id}</span>
                  <span className="text-[#666]">{new Date(entry.timestamp).toLocaleTimeString()}</span>
                </div>
                <div className="text-[#999] mt-1">
                  Pos: ({entry.position.x}, {entry.position.y}, {entry.position.z})
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );

  const renderStateTab = () => (
    <div className="space-y-4">
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
        <div className="text-sm font-medium text-[#00d4ff] mb-3">Submit State Update</div>
        <div className="grid grid-cols-2 gap-3">
          <div className="col-span-2">
            <label className="text-xs text-[#999] mb-1 block">Identity ID</label>
            <input type="text" value={stIdentityId} onChange={(e) => setStIdentityId(e.target.value)} placeholder="identity_001" className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>

          <div className="col-span-2">
            <label className="text-xs text-[#999] mb-1 block">Position (X, Y, Z)</label>
            <div className="grid grid-cols-3 gap-2">
              <input type="number" value={stPosX} onChange={(e) => setStPosX(e.target.value)} placeholder="X" className="bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
              <input type="number" value={stPosY} onChange={(e) => setStPosY(e.target.value)} placeholder="Y" className="bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
              <input type="number" value={stPosZ} onChange={(e) => setStPosZ(e.target.value)} placeholder="Z" className="bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
            </div>
          </div>

          <div className="col-span-2">
            <label className="text-xs text-[#999] mb-1 block">Rotation (X, Y, Z)</label>
            <div className="grid grid-cols-3 gap-2">
              <input type="number" value={stRotX} onChange={(e) => setStRotX(e.target.value)} placeholder="X" className="bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
              <input type="number" value={stRotY} onChange={(e) => setStRotY(e.target.value)} placeholder="Y" className="bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
              <input type="number" value={stRotZ} onChange={(e) => setStRotZ(e.target.value)} placeholder="Z" className="bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
            </div>
          </div>

          <div className="col-span-2">
            <label className="text-xs text-[#999] mb-1 block">Velocity (X, Y, Z)</label>
            <div className="grid grid-cols-3 gap-2">
              <input type="number" value={stVelX} onChange={(e) => setStVelX(e.target.value)} placeholder="X" className="bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
              <input type="number" value={stVelY} onChange={(e) => setStVelY(e.target.value)} placeholder="Y" className="bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
              <input type="number" value={stVelZ} onChange={(e) => setStVelZ(e.target.value)} placeholder="Z" className="bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
            </div>
          </div>

          <div className="col-span-2">
            <label className="text-xs text-[#999] mb-1 block">Custom State (JSON)</label>
            <textarea value={stCustom} onChange={(e) => setStCustom(e.target.value)} placeholder='{"health": 100, "ammo": 30}' rows={3} className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm font-mono focus:border-[#00d4ff] focus:outline-none" />
          </div>
        </div>
        <button
          onClick={async () => {
            if (!stIdentityId.trim()) { showMessage('error', 'Identity ID required'); return; }
            let customState = null;
            if (stCustom.trim()) {
              try { customState = JSON.parse(stCustom); } catch { showMessage('error', 'Invalid JSON in custom state'); return; }
            }
            await handleSubmit('/engine/network-replication/submit-state', {
              identity_id: stIdentityId,
              position: { x: parseFloat(stPosX) || 0, y: parseFloat(stPosY) || 0, z: parseFloat(stPosZ) || 0 },
              rotation: { x: parseFloat(stRotX) || 0, y: parseFloat(stRotY) || 0, z: parseFloat(stRotZ) || 0 },
              velocity: { x: parseFloat(stVelX) || 0, y: parseFloat(stVelY) || 0, z: parseFloat(stVelZ) || 0 },
              custom_state: customState,
            });
          }}
          disabled={loading}
          className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50"
        >
          Submit State
        </button>
      </div>
    </div>
  );

  const renderEventsTab = () => (
    <div className="space-y-4">
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
        <div className="text-sm font-medium text-[#00d4ff] mb-3">Send Network Event</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-[#999] mb-1 block">Event Type</label>
            <select value={evType} onChange={(e) => setEvType(e.target.value)} className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none">
              {EVENT_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Reliable</label>
            <label className="flex items-center gap-2 cursor-pointer mt-2">
              <input type="checkbox" checked={evReliable} onChange={(e) => setEvReliable(e.target.checked)} className="accent-[#00d4ff]" />
              <span className="text-white text-xs">Guaranteed delivery</span>
            </label>
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Source ID</label>
            <input type="text" value={evSourceId} onChange={(e) => setEvSourceId(e.target.value)} placeholder="client_001" className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Target ID</label>
            <input type="text" value={evTargetId} onChange={(e) => setEvTargetId(e.target.value)} placeholder="client_002" className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div className="col-span-2">
            <label className="text-xs text-[#999] mb-1 block">Payload (JSON)</label>
            <textarea value={evPayload} onChange={(e) => setEvPayload(e.target.value)} placeholder='{"action": "shoot", "damage": 25}' rows={3} className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm font-mono focus:border-[#00d4ff] focus:outline-none" />
          </div>
        </div>
        <button
          onClick={async () => {
            if (!evSourceId.trim()) { showMessage('error', 'Source ID required'); return; }
            let payload = null;
            if (evPayload.trim()) {
              try { payload = JSON.parse(evPayload); } catch { showMessage('error', 'Invalid JSON in payload'); return; }
            }
            await handleSubmit('/engine/network-replication/send-event', {
              event_type: evType,
              source_id: evSourceId,
              target_id: evTargetId,
              payload,
              reliable: evReliable,
            });
            fetchStats();
          }}
          disabled={loading}
          className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50"
        >
          Send Event
        </button>
      </div>
    </div>
  );

  const renderClientsTab = () => (
    <div className="space-y-4">
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
        <div className="text-sm font-medium text-[#00d4ff] mb-3">Register Client</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-[#999] mb-1 block">Address</label>
            <input type="text" value={cAddress} onChange={(e) => setCAddress(e.target.value)} placeholder="192.168.1.100" className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Port</label>
            <input type="number" value={cPort} onChange={(e) => setCPort(e.target.value)} className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Role</label>
            <select value={cRole} onChange={(e) => setCRole(e.target.value)} className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none">
              {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
            </select>
          </div>
        </div>
        <button
          onClick={async () => {
            if (!cAddress.trim()) { showMessage('error', 'Address required'); return; }
            await handleSubmit('/engine/network-replication/register-client', {
              address: cAddress,
              port: parseInt(cPort) || 7777,
              role: cRole,
            });
            fetchClients();
            fetchStats();
          }}
          disabled={loading}
          className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50"
        >
          Register Client
        </button>
      </div>

      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
        <div className="text-sm font-medium text-[#00d4ff] mb-3">Connected Clients ({clients.length})</div>
        {clients.length > 0 ? (
          <div className="space-y-2">
            {clients.map((c) => (
              <div key={c.id} className="bg-[#0d0d0d] border border-[#2a2a4a] rounded-lg p-3">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-white text-sm font-medium">{c.address}:{c.port}</span>
                  <div className="flex gap-1">
                    <span className={`text-xs px-2 py-0.5 rounded ${c.status === 'connected' ? 'bg-green-900 text-green-300' : c.status === 'disconnected' ? 'bg-red-900 text-red-300' : 'bg-[#1a1a1a] text-[#ccc]'}`}>
                      {c.status || 'unknown'}
                    </span>
                    <span className="text-xs bg-[#1a1a2e] text-[#ccc] px-2 py-0.5 rounded">{c.role}</span>
                  </div>
                </div>
                {c.id && (
                  <div className="flex gap-2 mt-2">
                    <button
                      onClick={async () => {
                        await handleSubmit('/engine/network-replication/send-event', {
                          event_type: 'sync',
                          source_id: 'server',
                          target_id: c.id,
                          payload: { type: 'heartbeat' },
                          reliable: false,
                        });
                      }}
                      className="px-3 py-1 bg-green-800 text-green-300 rounded text-xs hover:bg-green-700"
                    >
                      Heartbeat
                    </button>
                    <button
                      onClick={async () => {
                        await handleSubmit('/engine/network-replication/send-event', {
                          event_type: 'disconnect',
                          source_id: 'server',
                          target_id: c.id,
                          payload: { reason: 'admin' },
                          reliable: true,
                        });
                        fetchClients();
                      }}
                      className="px-3 py-1 bg-red-800 text-red-300 rounded text-xs hover:bg-red-700"
                    >
                      Disconnect
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="text-[#999] text-xs">No clients connected</div>
        )}
      </div>
    </div>
  );

  const renderMatchesTab = () => (
    <div className="space-y-4">
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
        <div className="text-sm font-medium text-[#00d4ff] mb-3">Create Match</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-[#999] mb-1 block">Room Name</label>
            <input type="text" value={mRoomName} onChange={(e) => setMRoomName(e.target.value)} placeholder="Deathmatch Arena #1" className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Max Players</label>
            <input type="number" value={mMaxPlayers} onChange={(e) => setMMaxPlayers(e.target.value)} className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div className="col-span-2">
            <label className="text-xs text-[#999] mb-1 block">Game Mode</label>
            <select value={mGameMode} onChange={(e) => setMGameMode(e.target.value)} className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none">
              {GAME_MODES.map((m) => <option key={m} value={m}>{m.replace(/_/g, ' ')}</option>)}
            </select>
          </div>
        </div>
        <button
          onClick={async () => {
            if (!mRoomName.trim()) { showMessage('error', 'Room name required'); return; }
            await handleSubmit('/engine/network-replication/create-match', {
              room_name: mRoomName,
              max_players: parseInt(mMaxPlayers) || 4,
              game_mode: mGameMode,
            });
            setMRoomName('');
          }}
          disabled={loading}
          className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50"
        >
          Create Match
        </button>
      </div>

      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
        <div className="text-sm font-medium text-[#00d4ff] mb-3">Interest Management</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-[#999] mb-1 block">Client ID</label>
            <input type="text" value={interestClientId} onChange={(e) => setInterestClientId(e.target.value)} placeholder="client_001" className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">View Radius</label>
            <input type="number" value={interestRadius} onChange={(e) => setInterestRadius(e.target.value)} className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
        </div>
        <button
          onClick={async () => {
            if (!interestClientId.trim()) { showMessage('error', 'Client ID required'); return; }
            await handleSubmit('/engine/network-replication/interested-entities', {
              client_id: interestClientId,
              view_radius: parseFloat(interestRadius) || 100,
            });
          }}
          disabled={loading}
          className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50"
        >
          Get Interested Entities
        </button>
      </div>

      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
        <div className="text-sm font-medium text-[#00d4ff] mb-3">State Reconciliation</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-[#999] mb-1 block">Client ID</label>
            <input type="text" value={reconcileClientId} onChange={(e) => setReconcileClientId(e.target.value)} placeholder="client_001" className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div></div>
          <div className="col-span-2">
            <label className="text-xs text-[#999] mb-1 block">Server State (JSON)</label>
            <textarea value={reconcileState} onChange={(e) => setReconcileState(e.target.value)} placeholder='{"pos": [100, 200, 0], "health": 80}' rows={4} className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm font-mono focus:border-[#00d4ff] focus:outline-none" />
          </div>
        </div>
        <button
          onClick={async () => {
            if (!reconcileClientId.trim()) { showMessage('error', 'Client ID required'); return; }
            let serverState = null;
            if (reconcileState.trim()) {
              try { serverState = JSON.parse(reconcileState); } catch { showMessage('error', 'Invalid JSON in server state'); return; }
            }
            await handleSubmit('/engine/network-replication/reconcile', {
              client_id: reconcileClientId,
              server_state: serverState,
            });
          }}
          disabled={loading}
          className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50"
        >
          Reconcile
        </button>
      </div>
    </div>
  );

  return (
    <div className="h-full flex flex-col bg-[#1a1a2e] text-white">
      <div className="flex gap-1 p-3 border-b border-[#2a2a4a] flex-wrap">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 rounded text-sm font-medium ${activeTab === tab.id ? 'bg-[#00d4ff] text-black' : 'bg-[#0d0d0d] text-[#ccc] hover:bg-[#2a2a4a]'}`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {message && (
        <div className={`mx-4 mt-3 px-4 py-2 rounded text-sm font-medium ${message.type === 'success' ? 'bg-green-900 text-green-300 border border-green-700' : 'bg-red-900 text-red-300 border border-red-700'}`}>
          {message.text}
        </div>
      )}

      <div className="flex-1 overflow-auto p-4">
        {activeTab === 'status' && renderStatusTab()}
        {activeTab === 'entities' && renderEntitiesTab()}
        {activeTab === 'state' && renderStateTab()}
        {activeTab === 'events' && renderEventsTab()}
        {activeTab === 'clients' && renderClientsTab()}
        {activeTab === 'matches' && renderMatchesTab()}
      </div>
    </div>
  );
};

export default EngineNetworkReplicationPanel;