import React, { useState, useCallback, useEffect } from 'react';
import { engineApi } from '../utils/api';

interface PlayerEntry {
  player_id: string;
  name: string;
  ping: number;
  state: string;
}

interface RpcLogEntry {
  log_id: string;
  timestamp: string;
  caller: string;
  method: string;
  target: string;
  data: string;
  status: string;
}

interface NetworkConfig {
  serverAddress: string;
  port: number;
  maxPlayers: number;
  protocol: string;
  syncInterval: number;
  interestManagement: boolean;
  relevancyDistance: number;
  authorityMode: string;
}

const PROTOCOLS = ['TCP', 'UDP', 'WebSocket', 'WebRTC'] as const;
const AUTHORITY_MODES = ['server_authoritative', 'client_authoritative', 'hybrid'] as const;

const STATE_COLORS: Record<string, string> = {
  connected: '#10b981',
  connecting: '#fbbf24',
  disconnected: '#ef4444',
  idle: '#888',
};

const STATUS_COLORS: Record<string, string> = {
  success: '#10b981',
  pending: '#fbbf24',
  failed: '#ef4444',
  timeout: '#f97316',
};

const NetworkPanel: React.FC = () => {
  const [config, setConfig] = useState<NetworkConfig>({
    serverAddress: 'localhost',
    port: 7777,
    maxPlayers: 32,
    protocol: 'WebSocket',
    syncInterval: 30,
    interestManagement: true,
    relevancyDistance: 100,
    authorityMode: 'server_authoritative',
  });
  const [players, setPlayers] = useState<PlayerEntry[]>([]);
  const [rpcLog, setRpcLog] = useState<RpcLogEntry[]>([]);
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);

  const [lagEnabled, setLagEnabled] = useState(false);
  const [lagMin, setLagMin] = useState(50);
  const [lagMax, setLagMax] = useState(200);
  const [packetLoss, setPacketLoss] = useState(0);

  const connectedPlayers = players.filter(p => p.state === 'connected').length;
  const avgPing = connectedPlayers > 0
    ? Math.round(players.filter(p => p.state === 'connected').reduce((s, p) => s + p.ping, 0) / connectedPlayers)
    : 0;

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      await engineApi.listScenes();
    } catch {}
    setPlayers([
      { player_id: 'p1', name: 'PlayerOne', ping: 24, state: 'connected' },
      { player_id: 'p2', name: 'DragonSlayer', ping: 56, state: 'connected' },
      { player_id: 'p3', name: 'MageKing', ping: 120, state: 'connected' },
      { player_id: 'p4', name: 'NewPlayer', ping: 0, state: 'connecting' },
      { player_id: 'p5', name: 'AFK_Farmer', ping: 999, state: 'disconnected' },
    ]);
    setRpcLog([
      { log_id: 'r1', timestamp: '12:34:01', caller: 'p1', method: 'MovePlayer', target: 'server', data: '{"x":10,"y":5}', status: 'success' },
      { log_id: 'r2', timestamp: '12:34:02', caller: 'p2', method: 'Attack', target: 'p3', data: '{"damage":25}', status: 'success' },
      { log_id: 'r3', timestamp: '12:34:03', caller: 'server', method: 'SpawnEnemy', target: 'all', data: '{"type":"goblin"}', status: 'success' },
      { log_id: 'r4', timestamp: '12:34:05', caller: 'p4', method: 'JoinGame', target: 'server', data: '{}', status: 'pending' },
      { log_id: 'r5', timestamp: '12:34:08', caller: 'p1', method: 'UseItem', target: 'server', data: '{"item":"potion"}', status: 'failed' },
    ]);
    setLoading(false);
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const updateConfig = <K extends keyof NetworkConfig>(key: K, value: NetworkConfig[K]) => {
    setConfig(prev => ({ ...prev, [key]: value }));
  };

  const handleConnect = async () => {
    try {
      setMessage(`Connecting to ${config.serverAddress}:${config.port}...`);
    } catch {
      setMessage('Connection failed.');
    }
  };

  const handleDisconnect = async () => {
    try {
      setMessage('Disconnected.');
    } catch {
      setMessage('Disconnect failed.');
    }
  };

  const handleSave = async () => {
    try {
      setMessage('Network configuration saved.');
    } catch {
      setMessage('Failed to save config.');
    }
  };

  return (
    <div className="h-full bg-[#111] text-[#e0e0e0] flex flex-col overflow-hidden" style={{ fontFamily: 'monospace' }}>
      <div className="flex items-center gap-3 px-4 py-2 border-b border-[#1e1e1e]">
        <h3 className="text-[13px] font-bold text-[#fbbf24] m-0">Network Panel</h3>
        <div className="flex-1" />
        {loading && <span className="text-[#555] text-[11px]">Loading...</span>}
        <button
          onClick={handleConnect}
          className="px-3 py-1 bg-[#10b981] text-white rounded text-[11px] font-bold border-none cursor-pointer"
        >
          Connect
        </button>
        <button
          onClick={handleDisconnect}
          className="px-3 py-1 bg-[#ef4444] text-white rounded text-[11px] font-bold border-none cursor-pointer"
        >
          Disconnect
        </button>
        <button
          onClick={handleSave}
          className="px-3 py-1 bg-[#3b82f6] text-white rounded text-[11px] font-bold border-none cursor-pointer"
        >
          Save
        </button>
      </div>

      {message && (
        <div className="mx-4 mt-2 px-3 py-1.5 bg-[#1a2a1a] rounded text-[#10b981] text-[11px] border border-[#1a3a1a]">
          {message}
        </div>
      )}

      <div className="flex-1 flex overflow-hidden">
        <div className="flex-1 overflow-y-auto p-3 space-y-4">
          <div className="bg-[#16213e] rounded border border-[#2a2a2a] p-4">
            <h4 className="text-[11px] font-bold text-[#888] mb-3">Connection Settings</h4>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-[9px] text-[#888] block mb-1">Server Address</label>
                <input
                  value={config.serverAddress}
                  onChange={e => updateConfig('serverAddress', e.target.value)}
                  className="w-full bg-[#1a1a2e] border border-[#333] text-[#e0e0e0] text-[10px] rounded px-2 py-1.5 outline-none"
                />
              </div>
              <div>
                <label className="text-[9px] text-[#888] block mb-1">Port</label>
                <input
                  type="number"
                  value={config.port}
                  onChange={e => updateConfig('port', parseInt(e.target.value) || 0)}
                  className="w-full bg-[#1a1a2e] border border-[#333] text-[#e0e0e0] text-[10px] rounded px-2 py-1.5 outline-none"
                />
              </div>
              <div>
                <label className="text-[9px] text-[#888] block mb-1">Protocol</label>
                <select
                  value={config.protocol}
                  onChange={e => updateConfig('protocol', e.target.value)}
                  className="w-full bg-[#1a1a2e] border border-[#333] text-[#e0e0e0] text-[10px] rounded px-1 py-1.5 outline-none"
                >
                  {PROTOCOLS.map(p => (
                    <option key={p} value={p}>{p}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-[9px] text-[#888] block mb-1">Max Players</label>
                <div className="flex items-center gap-2">
                  <input
                    type="range"
                    min={1}
                    max={64}
                    value={config.maxPlayers}
                    onChange={e => updateConfig('maxPlayers', parseInt(e.target.value))}
                    className="flex-1"
                  />
                  <span className="text-[10px] text-[#fbbf24] w-6 text-right">{config.maxPlayers}</span>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-[#16213e] rounded border border-[#2a2a2a] p-4">
            <h4 className="text-[11px] font-bold text-[#888] mb-3">Replication Settings</h4>
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <span className="text-[10px] text-[#888] w-36">Sync Interval</span>
                <input
                  type="range"
                  min={1}
                  max={60}
                  value={config.syncInterval}
                  onChange={e => updateConfig('syncInterval', parseInt(e.target.value))}
                  className="flex-1"
                />
                <span className="text-[10px] text-[#fbbf24] w-14 text-right">{config.syncInterval} Hz</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] text-[#888] w-36">Interest Management</span>
                <button
                  onClick={() => updateConfig('interestManagement', !config.interestManagement)}
                  className="px-3 py-1 rounded text-[10px] font-bold border cursor-pointer transition-colors"
                  style={{
                    backgroundColor: config.interestManagement ? '#10b981' : '#333',
                    color: config.interestManagement ? '#fff' : '#888',
                    borderColor: config.interestManagement ? '#10b981' : '#444',
                  }}
                >
                  {config.interestManagement ? 'Enabled' : 'Disabled'}
                </button>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] text-[#888] w-36">Relevancy Distance</span>
                <input
                  type="range"
                  min={10}
                  max={500}
                  step={10}
                  value={config.relevancyDistance}
                  onChange={e => updateConfig('relevancyDistance', parseInt(e.target.value))}
                  disabled={!config.interestManagement}
                  className="flex-1"
                />
                <span className="text-[10px] text-[#fbbf24] w-10 text-right">{config.relevancyDistance}m</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] text-[#888] w-36">Authority Mode</span>
                <div className="flex gap-2">
                  {AUTHORITY_MODES.map(mode => (
                    <label key={mode} className="flex items-center gap-1 text-[9px] text-[#aaa] cursor-pointer">
                      <input
                        type="radio"
                        name="authority"
                        value={mode}
                        checked={config.authorityMode === mode}
                        onChange={() => updateConfig('authorityMode', mode)}
                        className="accent-[#fbbf24]"
                      />
                      {mode.replace(/_/g, ' ')}
                    </label>
                  ))}
                </div>
              </div>
            </div>
          </div>

          <div className="bg-[#16213e] rounded border border-[#2a2a2a] p-4">
            <h4 className="text-[11px] font-bold text-[#888] mb-3">Players ({players.length})</h4>
            <div className="overflow-x-auto">
              <table className="w-full text-[10px]">
                <thead>
                  <tr className="text-[#555] text-left">
                    <th className="pb-1 font-normal">ID</th>
                    <th className="pb-1 font-normal">Name</th>
                    <th className="pb-1 font-normal">Ping</th>
                    <th className="pb-1 font-normal">State</th>
                  </tr>
                </thead>
                <tbody>
                  {players.map(player => (
                    <tr key={player.player_id} className="border-t border-[#1a1a1a]">
                      <td className="py-1.5 text-[#888]">{player.player_id}</td>
                      <td className="py-1.5 text-[#e0e0e0]">{player.name}</td>
                      <td className="py-1.5">
                        <span
                          className="font-bold"
                          style={{
                            color: player.state !== 'connected' ? '#555'
                              : player.ping < 50 ? '#10b981'
                              : player.ping < 150 ? '#fbbf24'
                              : '#ef4444',
                          }}
                        >
                          {player.state === 'connected' ? `${player.ping}ms` : '—'}
                        </span>
                      </td>
                      <td className="py-1.5">
                        <span
                          className="px-1.5 py-0.5 rounded text-[8px]"
                          style={{
                            backgroundColor: (STATE_COLORS[player.state] || '#888') + '20',
                            color: STATE_COLORS[player.state] || '#888',
                          }}
                        >
                          {player.state}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="bg-[#16213e] rounded border border-[#2a2a2a] p-4">
            <h4 className="text-[11px] font-bold text-[#888] mb-3">RPC Log ({rpcLog.length})</h4>
            <div className="overflow-x-auto">
              <table className="w-full text-[9px]">
                <thead>
                  <tr className="text-[#555] text-left">
                    <th className="pb-1 font-normal">Time</th>
                    <th className="pb-1 font-normal">Caller</th>
                    <th className="pb-1 font-normal">Method</th>
                    <th className="pb-1 font-normal">Target</th>
                    <th className="pb-1 font-normal">Data</th>
                    <th className="pb-1 font-normal">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {rpcLog.map(entry => (
                    <tr key={entry.log_id} className="border-t border-[#1a1a1a]">
                      <td className="py-1 pr-2 text-[#555]">{entry.timestamp}</td>
                      <td className="py-1 pr-2 text-[#aaa]">{entry.caller}</td>
                      <td className="py-1 pr-2 text-[#e0e0e0]">{entry.method}</td>
                      <td className="py-1 pr-2 text-[#aaa]">{entry.target}</td>
                      <td className="py-1 pr-2 text-[#555] max-w-[100px] truncate">{entry.data}</td>
                      <td className="py-1">
                        <span
                          className="px-1 py-0.5 rounded text-[7px]"
                          style={{
                            backgroundColor: (STATUS_COLORS[entry.status] || '#888') + '20',
                            color: STATUS_COLORS[entry.status] || '#888',
                          }}
                        >
                          {entry.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <div className="w-72 border-l border-[#1e1e1e] overflow-y-auto p-3 space-y-3 flex-shrink-0">
          <div className="bg-[#0a0a0a] rounded border border-[#2a2a2a] p-3">
            <h4 className="text-[11px] font-bold text-[#888] mb-2">Lag Simulation</h4>
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] text-[#aaa]">Enabled</span>
              <button
                onClick={() => setLagEnabled(!lagEnabled)}
                className="px-3 py-1 rounded text-[10px] font-bold border cursor-pointer transition-colors"
                style={{
                  backgroundColor: lagEnabled ? '#f97316' : '#333',
                  color: lagEnabled ? '#fff' : '#888',
                  borderColor: lagEnabled ? '#f97316' : '#444',
                }}
              >
                {lagEnabled ? 'Simulating' : 'Off'}
              </button>
            </div>
            <div className="space-y-2">
              <div>
                <div className="flex justify-between text-[8px] text-[#888] mb-0.5">
                  <span>Min Latency</span>
                  <span>{lagMin}ms</span>
                </div>
                <input
                  type="range"
                  min={0}
                  max={500}
                  step={10}
                  value={lagMin}
                  onChange={e => setLagMin(parseInt(e.target.value))}
                  disabled={!lagEnabled}
                  className="w-full"
                />
              </div>
              <div>
                <div className="flex justify-between text-[8px] text-[#888] mb-0.5">
                  <span>Max Latency</span>
                  <span>{lagMax}ms</span>
                </div>
                <input
                  type="range"
                  min={0}
                  max={1000}
                  step={10}
                  value={lagMax}
                  onChange={e => setLagMax(parseInt(e.target.value))}
                  disabled={!lagEnabled}
                  className="w-full"
                />
              </div>
              <div>
                <div className="flex justify-between text-[8px] text-[#888] mb-0.5">
                  <span>Packet Loss</span>
                  <span>{packetLoss}%</span>
                </div>
                <input
                  type="range"
                  min={0}
                  max={30}
                  step={0.5}
                  value={packetLoss}
                  onChange={e => setPacketLoss(parseFloat(e.target.value))}
                  disabled={!lagEnabled}
                  className="w-full"
                />
              </div>
            </div>
          </div>

          <div className="bg-[#0a0a0a] rounded border border-[#2a2a2a] p-3">
            <h4 className="text-[11px] font-bold text-[#888] mb-2">Stats</h4>
            <div className="space-y-2">
              <div className="flex justify-between text-[10px]">
                <span className="text-[#888]">Connected</span>
                <span className="text-[#10b981] font-bold">{connectedPlayers}</span>
              </div>
              <div className="flex justify-between text-[10px]">
                <span className="text-[#888]">Avg Ping</span>
                <span
                  className="font-bold"
                  style={{
                    color: avgPing < 50 ? '#10b981' : avgPing < 150 ? '#fbbf24' : '#ef4444',
                  }}
                >
                  {avgPing}ms
                </span>
              </div>
              <div className="flex justify-between text-[10px]">
                <span className="text-[#888]">Packets/sec</span>
                <span className="text-[#fbbf24] font-bold">{config.syncInterval * 2}</span>
              </div>
              <div className="flex justify-between text-[10px]">
                <span className="text-[#888]">Bandwidth</span>
                <span className="text-[#fbbf24] font-bold">
                  {(connectedPlayers * config.syncInterval * 0.05).toFixed(1)} KB/s
                </span>
              </div>
              <div className="flex justify-between text-[10px]">
                <span className="text-[#888]">Max Players</span>
                <span className="text-[#fbbf24] font-bold">{config.maxPlayers}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default NetworkPanel;