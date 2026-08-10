import React, { useState } from 'react';
import { Hammer, Play, CheckCircle2, Box, Shield, Loader2 } from 'lucide-react';

interface BuildResult {
  scene_id: string;
  scene_name: string;
  entities: { id: string; name: string; kind: string }[];
  rules: { name: string }[];
  verification: { status: string; actions_fired?: number; fired_types?: string[] };
  message: string;
}

const EXAMPLES = [
  'collect coins',
  'survive the dungeon',
  'protect the village',
];

const AgentBuildPanel: React.FC = () => {
  const [concept, setConcept] = useState('');
  const [building, setBuilding] = useState(false);
  const [result, setResult] = useState<BuildResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const kindColor: Record<string, string> = {
    player: 'bg-emerald-500/20 text-emerald-300',
    collectible: 'bg-amber-500/20 text-amber-300',
    enemy: 'bg-red-500/20 text-red-300',
  };

  const buildGame = async (override?: string) => {
    const c = (override ?? concept).trim();
    if (!c) return;
    setBuilding(true);
    setError(null);
    setResult(null);
    try {
      const res = await fetch('/api/agent/systems/build-game', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ concept: c }),
      });
      const json = await res.json();
      if (json.status === 'success') {
        setResult(json.data);
      } else {
        setError(json.message || 'Build failed');
      }
    } catch (e: any) {
      setError(String(e.message || e));
    } finally {
      setBuilding(false);
    }
  };

  return (
    <div className="p-6 h-full overflow-y-auto">
      <div className="max-w-3xl mx-auto">
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2 rounded-xl bg-amber-500/20 text-amber-300">
            <Hammer className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white">Agent Game Build</h1>
            <p className="text-sm text-slate-400">
              Describe a game concept and the agent constructs a runnable world with rules, then verifies it.
            </p>
          </div>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-300 text-sm">
            {error}
          </div>
        )}

        <div className="flex gap-2 mb-3">
          {EXAMPLES.map((ex) => (
            <button
              key={ex}
              onClick={() => { setConcept(ex); buildGame(ex); }}
              disabled={building}
              className="px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 hover:border-amber-500/50 disabled:opacity-50 text-xs text-slate-300 transition"
            >
              {ex}
            </button>
          ))}
        </div>

        <div className="flex gap-2 mb-5">
          <input
            value={concept}
            onChange={(e) => setConcept(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && buildGame()}
            placeholder="Describe a game, e.g. a player collects coins and avoids enemies..."
            className="flex-1 px-4 py-3 rounded-lg bg-slate-800 border border-slate-700 focus:border-amber-500/60 outline-none text-white text-sm"
          />
          <button
            onClick={() => buildGame()}
            disabled={building || !concept.trim()}
            className="px-5 py-3 rounded-lg bg-amber-600 hover:bg-amber-500 disabled:opacity-50 text-white text-sm font-medium flex items-center gap-2 transition"
          >
            {building ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
            Build
          </button>
        </div>

        {result && (
          <div className="space-y-4">
            <div className="p-4 rounded-xl bg-slate-800/60 border border-slate-700/60">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2 text-sm font-medium text-white">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  {result.scene_name}
                </div>
                <span className="text-xs text-slate-400">scene {result.scene_id.slice(0, 8)}</span>
              </div>

              <div className="mb-3">
                <div className="text-xs text-slate-400 mb-2 flex items-center gap-1">
                  <Box className="w-3.5 h-3.5" /> Entities
                </div>
                <div className="flex flex-wrap gap-2">
                  {result.entities.map((e) => (
                    <span
                      key={e.id}
                      className={`px-2 py-1 rounded text-xs ${kindColor[e.kind] || 'bg-slate-700/40 text-slate-300'}`}
                    >
                      {e.name}
                    </span>
                  ))}
                </div>
              </div>

              <div className="mb-3">
                <div className="text-xs text-slate-400 mb-2 flex items-center gap-1">
                  <Shield className="w-3.5 h-3.5" /> Rules
                </div>
                <div className="flex flex-wrap gap-2">
                  {result.rules.map((r) => (
                    <span key={r.name} className="px-2 py-1 rounded bg-violet-500/20 text-violet-300 text-xs">
                      {r.name}
                    </span>
                  ))}
                </div>
              </div>

              <div className="p-3 rounded-lg bg-slate-900/50">
                <div className="text-xs text-slate-400 mb-1">Verification</div>
                {result.verification.status === 'verified' ? (
                  <div className="text-emerald-400 text-sm">
                    Confirmed: {result.verification.actions_fired} action(s) fired
                    {result.verification.fired_types?.length ? ` (${result.verification.fired_types.join(', ')})` : ''}
                  </div>
                ) : (
                  <div className="text-amber-400 text-sm">Rules registered but no action fired in test context.</div>
                )}
              </div>
            </div>

            <p className="text-xs text-slate-500">{result.message}</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default AgentBuildPanel;
