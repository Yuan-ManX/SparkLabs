import React, { useState, useCallback, useEffect } from 'react';
import { Play, RotateCcw, CheckCircle2, History, Zap, FlaskConical, RefreshCw } from 'lucide-react';

interface CheckpointInfo {
  id: string;
  reason: string;
  created_at: number;
  scene_count: number;
  engine_tick: number;
  score: number;
  logic_events: number;
}

interface DiffEntry {
  entity_id: string;
  entity_name: string;
  change: string;
}

interface SimResult {
  committed: boolean;
  frames_run: number;
  delta_time: number;
  summary: string;
  diff: DiffEntry[];
  status?: string;
}

const PredictiveSimulationPanel: React.FC = () => {
  const [frames, setFrames] = useState(60);
  const [deltaTime, setDeltaTime] = useState(0.016);
  const [commit, setCommit] = useState(false);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<SimResult | null>(null);
  const [checkpoints, setCheckpoints] = useState<CheckpointInfo[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchCheckpoints = useCallback(async () => {
    try {
      const res = await fetch('/api/engine/checkpoints');
      const json = await res.json();
      if (json.status === 'success') {
        setCheckpoints(json.data.checkpoints || []);
      }
    } catch {
      setCheckpoints([]);
    }
  }, []);

  useEffect(() => {
    fetchCheckpoints();
  }, [fetchCheckpoints]);

  const runSimulation = async () => {
    setRunning(true);
    setError(null);
    setResult(null);
    setLoading(true);
    try {
      const res = await fetch('/api/engine/simulate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ frames, delta_time: deltaTime, commit }),
      });
      const json = await res.json();
      if (json.status === 'success') {
        setResult(json.data);
      } else {
        setError(json.message || 'Simulation failed');
      }
    } catch (e: any) {
      setError(String(e.message || e));
    } finally {
      setLoading(false);
      setRunning(false);
      fetchCheckpoints();
    }
  };

  const createCheckpoint = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/engine/checkpoints', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: 'manual-snapshot' }),
      });
      const json = await res.json();
      if (json.status !== 'success') {
        setError(json.message || 'Checkpoint failed');
      }
    } catch (e: any) {
      setError(String(e.message || e));
    } finally {
      setLoading(false);
      fetchCheckpoints();
    }
  };

  const restoreCheckpoint = async (id: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/engine/checkpoints/restore', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ checkpoint_id: id }),
      });
      const json = await res.json();
      if (json.status !== 'success') {
        setError(json.message || 'Restore failed');
      }
    } catch (e: any) {
      setError(String(e.message || e));
    } finally {
      setLoading(false);
      fetchCheckpoints();
    }
  };

  const formatTime = (ts: number) =>
    new Date(ts * 1000).toLocaleTimeString();

  return (
    <div className="p-6 h-full overflow-y-auto">
      <div className="max-w-3xl mx-auto">
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2 rounded-xl bg-violet-500/20 text-violet-300">
            <FlaskConical className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white">Predictive Simulation</h1>
            <p className="text-sm text-slate-400">
              Step the world forward in a sandbox and inspect predicted outcomes before committing.
            </p>
          </div>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-300 text-sm">
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-4 gap-3 mb-5">
          <div>
            <label className="text-xs text-slate-400 mb-1 block">Frames</label>
            <input
              type="number"
              value={frames}
              min={1}
              max={1000}
              onChange={(e) => setFrames(Number(e.target.value))}
              className="w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-white text-sm"
            />
          </div>
          <div>
            <label className="text-xs text-slate-400 mb-1 block">Delta time</label>
            <input
              type="number"
              step={0.001}
              value={deltaTime}
              onChange={(e) => setDeltaTime(Number(e.target.value))}
              className="w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-white text-sm"
            />
          </div>
          <div>
            <label className="text-xs text-slate-400 mb-1 block">Commit outcome</label>
            <button
              onClick={() => setCommit(!commit)}
              className={`w-full px-3 py-2 rounded-lg border text-sm font-medium transition ${
                commit
                  ? 'bg-emerald-500/20 border-emerald-500/40 text-emerald-300'
                  : 'bg-slate-800 border-slate-700 text-slate-300'
              }`}
            >
              {commit ? 'Committed' : 'Rolled back'}
            </button>
          </div>
          <div className="flex items-end">
            <button
              onClick={runSimulation}
              disabled={loading}
              className="w-full px-4 py-2 rounded-lg bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-white text-sm font-medium flex items-center justify-center gap-2 transition"
            >
              {running ? <Zap className="w-4 h-4 animate-pulse" /> : <Play className="w-4 h-4" />}
              {running ? 'Simulating...' : 'Simulate'}
            </button>
          </div>
        </div>

        {result && (
          <div className="mb-5 p-4 rounded-xl bg-slate-800/60 border border-slate-700/60">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2 text-sm font-medium text-white">
                {result.committed ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                ) : (
                  <RotateCcw className="w-4 h-4 text-amber-400" />
                )}
                {result.committed ? 'Outcome committed' : 'Outcome predicted & rolled back'}
              </div>
              <span className="text-xs text-slate-400">
                {result.frames_run} frames @ {result.delta_time}s
              </span>
            </div>
            <p className="text-sm text-slate-300 mb-3">{result.summary}</p>
            {result.diff.length > 0 ? (
              <div className="space-y-1">
                {result.diff.slice(0, 10).map((d, i) => (
                  <div
                    key={i}
                    className="flex items-center gap-2 text-xs px-2 py-1 rounded bg-slate-900/50"
                  >
                    <span className="text-slate-400">{d.entity_name}</span>
                    <span className="text-violet-300">{d.change}</span>
                  </div>
                ))}
                {result.diff.length > 10 && (
                  <div className="text-xs text-slate-500">+{result.diff.length - 10} more</div>
                )}
              </div>
            ) : (
              <div className="text-xs text-slate-500">No observable world change.</div>
            )}
          </div>
        )}

        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2 text-slate-300">
            <History className="w-4 h-4" />
            <span className="text-sm font-medium">World Checkpoints</span>
          </div>
          <button
            onClick={createCheckpoint}
            disabled={loading}
            className="px-3 py-1.5 rounded-lg bg-slate-700 hover:bg-slate-600 disabled:opacity-50 text-xs text-white flex items-center gap-1.5 transition"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Snapshot
          </button>
        </div>

        {checkpoints.length === 0 ? (
          <div className="text-sm text-slate-500 p-6 text-center rounded-xl bg-slate-800/30 border border-dashed border-slate-700">
            No checkpoints captured yet. Snapshots let you roll back to a known-good state.
          </div>
        ) : (
          <div className="space-y-2">
            {checkpoints.map((cp) => (
              <div
                key={cp.id}
                className="flex items-center gap-3 p-3 rounded-xl bg-slate-800/50 border border-slate-700/60"
              >
                <div className="flex-1 min-w-0">
                  <div className="text-sm text-white font-medium truncate">{cp.reason}</div>
                  <div className="text-xs text-slate-400">
                    {formatTime(cp.created_at)} · {cp.scene_count} scenes · tick {cp.engine_tick} · score {cp.score}
                  </div>
                </div>
                <button
                  onClick={() => restoreCheckpoint(cp.id)}
                  disabled={loading}
                  className="px-3 py-1.5 rounded-lg bg-amber-500/20 hover:bg-amber-500/30 disabled:opacity-50 text-amber-300 text-xs font-medium flex items-center gap-1.5 transition"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  Restore
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default PredictiveSimulationPanel;
