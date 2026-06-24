import React, { useState, useEffect, useCallback } from 'react';

const API_BASE = 'http://localhost:8000/api/agent';

interface VisionProfile {
  vision_id: string;
  game_concept: string;
  genre: string;
  target_audience: string[];
  pillars: Array<{
    pillar: string;
    score: number;
    strengths: string[];
    weaknesses: string[];
    opportunities: string[];
    design_notes: string[];
    priority: string;
  }>;
  coherence_score: number;
  feasibility_score: number;
  innovation_score: number;
  overall_score: number;
  phase: string;
  unique_selling_points: string[];
  design_constraints: string[];
  inspiration_sources: string[];
  mood_descriptors: string[];
  created_at: number;
}

interface GameplayAnalysis {
  analysis_id: string;
  core_mechanics: Array<Record<string, unknown>>;
  secondary_mechanics: Array<Record<string, unknown>>;
  progression_systems: Array<Record<string, unknown>>;
  feedback_systems: Array<Record<string, unknown>>;
  balance_considerations: string[];
  pacing_analysis: Record<string, unknown>;
  skill_ceiling: number;
  accessibility_rating: number;
  depth_rating: number;
}

const GameVisionPanel: React.FC = () => {
  const [concept, setConcept] = useState('');
  const [genre, setGenre] = useState('action-adventure');
  const [audience, setAudience] = useState('');
  const [visions, setVisions] = useState<VisionProfile[]>([]);
  const [gameplayAnalysis, setGameplayAnalysis] = useState<GameplayAnalysis | null>(null);
  const [isInitialized, setIsInitialized] = useState(false);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ text: string; type: string } | null>(null);
  const [activeTab, setActiveTab] = useState<'create' | 'visions' | 'gameplay'>('create');

  const showMessage = (text: string, type: string) => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 3000);
  };

  const initialize = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/vision/initialize`, { method: 'POST' });
      const json = await res.json();
      if (json.status === 'success') {
        setIsInitialized(true);
        showMessage('Game vision engine initialized', 'success');
      }
    } catch {
      setIsInitialized(true);
      showMessage('Running in offline mode', 'info');
    }
    try {
      const res = await fetch(`${API_BASE}/vision/list?limit=20`);
      const json = await res.json();
      if (json.status === 'success') setVisions(json.data);
    } catch { /* offline */ }
  }, []);

  const handleCreateVision = async () => {
    if (!concept.trim()) {
      showMessage('Please enter a game concept', 'error');
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/vision/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          game_concept: concept.trim(),
          genre,
          target_audience: audience ? audience.split(',').map((s) => s.trim()) : [],
        }),
      });
      const json = await res.json();
      if (json.status === 'success') {
        showMessage('Vision profile created', 'success');
        setVisions((prev) => [json.data, ...prev].slice(0, 20));
        setActiveTab('visions');
      }
    } catch {
      showMessage('Vision created (simulated)', 'info');
      const sim: VisionProfile = {
        vision_id: `sim_${Date.now()}`,
        game_concept: concept.trim(),
        genre,
        target_audience: audience ? audience.split(',').map((s) => s.trim()) : [],
        pillars: [
          { pillar: 'gameplay_depth', score: 0.72, strengths: ['Strong gameplay depth foundation'], weaknesses: ['Needs deeper gameplay depth exploration'], opportunities: ['Opportunity to innovate in gameplay depth'], design_notes: ['Initial analysis'], priority: 'high' },
          { pillar: 'narrative_immersion', score: 0.68, strengths: ['Strong narrative immersion foundation'], weaknesses: ['Needs deeper narrative immersion exploration'], opportunities: ['Opportunity to innovate in narrative immersion'], design_notes: ['Initial analysis'], priority: 'high' },
          { pillar: 'visual_identity', score: 0.75, strengths: ['Strong visual identity foundation'], weaknesses: ['Needs deeper visual identity exploration'], opportunities: ['Opportunity to innovate in visual identity'], design_notes: ['Initial analysis'], priority: 'medium' },
          { pillar: 'player_agency', score: 0.70, strengths: ['Strong player agency foundation'], weaknesses: ['Needs deeper player agency exploration'], opportunities: ['Opportunity to innovate in player agency'], design_notes: ['Initial analysis'], priority: 'medium' },
        ],
        coherence_score: 0.82,
        feasibility_score: 0.78,
        innovation_score: 0.70,
        overall_score: 0.77,
        phase: 'vision_synthesis',
        unique_selling_points: [],
        design_constraints: [],
        inspiration_sources: [],
        mood_descriptors: [],
        created_at: Date.now() / 1000,
      };
      setVisions((prev) => [sim, ...prev].slice(0, 20));
      setActiveTab('visions');
    }
    setLoading(false);
    setConcept('');
  };

  const handleGameplayAnalysis = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/vision/analyze-gameplay`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ concept: concept || 'Generic game', mechanics: ['movement', 'combat', 'progression'] }),
      });
      const json = await res.json();
      if (json.status === 'success') {
        setGameplayAnalysis(json.data);
        showMessage('Gameplay analysis complete', 'success');
      }
    } catch {
      showMessage('Analysis completed (simulated)', 'info');
      setGameplayAnalysis({
        analysis_id: `sim_${Date.now()}`,
        core_mechanics: [
          { name: 'movement', type: 'core', complexity: 'medium', player_skill_required: 'moderate', innovation_potential: 'high' },
          { name: 'combat', type: 'core', complexity: 'medium', player_skill_required: 'moderate', innovation_potential: 'high' },
          { name: 'progression', type: 'core', complexity: 'medium', player_skill_required: 'moderate', innovation_potential: 'high' },
        ],
        secondary_mechanics: [
          { name: 'resource_management', type: 'secondary', complexity: 'low' },
          { name: 'progression_tracking', type: 'secondary', complexity: 'medium' },
        ],
        progression_systems: [
          { type: 'skill_tree', depth: 'medium', branching_factor: 3 },
          { type: 'equipment_upgrade', depth: 'high', tiers: 5 },
        ],
        feedback_systems: [
          { type: 'visual', responsiveness: 'high' },
          { type: 'audio', responsiveness: 'high' },
          { type: 'haptic', responsiveness: 'medium' },
        ],
        balance_considerations: ['Difficulty curve optimization', 'Resource economy balance', 'Player skill progression pacing'],
        pacing_analysis: { tutorial_phase: 'gradual', mid_game: 'escalating', end_game: 'mastery' },
        skill_ceiling: 0.75,
        accessibility_rating: 0.8,
        depth_rating: 0.85,
      });
    }
    setLoading(false);
    setActiveTab('gameplay');
  };

  useEffect(() => {
    initialize();
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${API_BASE}/vision/list?limit=20`);
        const json = await res.json();
        if (json.status === 'success') setVisions(json.data);
      } catch { /* offline */ }
    }, 15000);
    return () => clearInterval(interval);
  }, [initialize]);

  const genres = [
    'action-adventure', 'rpg', 'strategy', 'simulation', 'puzzle',
    'platformer', 'shooter', 'racing', 'sports', 'horror', 'roguelike',
    'metroidvania', 'visual-novel', 'sandbox', 'survival',
  ];

  return (
    <div className="h-full flex flex-col bg-[#0a0a1a] text-gray-200 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#1a1a3e] bg-[#0f0f2a]">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center text-sm font-bold">
            GV
          </div>
          <div>
            <h2 className="text-sm font-semibold">Game Vision</h2>
            <p className="text-[10px] text-gray-500">Design intelligence analysis</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${isInitialized ? 'bg-green-400' : 'bg-yellow-400'}`} />
          <span className="text-[10px] text-gray-500">{isInitialized ? 'Active' : 'Initializing...'}</span>
        </div>
      </div>

      {message && (
        <div className={`mx-4 mt-2 px-3 py-1.5 rounded text-xs ${
          message.type === 'success' ? 'bg-green-900/50 text-green-300 border border-green-700/50' :
          message.type === 'error' ? 'bg-red-900/50 text-red-300 border border-red-700/50' :
          'bg-blue-900/50 text-blue-300 border border-blue-700/50'
        }`}>
          {message.text}
        </div>
      )}

      <div className="flex border-b border-[#1a1a3e]">
        {(['create', 'visions', 'gameplay'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-xs font-medium transition-colors ${
              activeTab === tab
                ? 'text-amber-400 border-b-2 border-amber-500 bg-amber-500/5'
                : 'text-gray-500 hover:text-gray-300'
            }`}
          >
            {tab === 'create' ? 'Create Vision' : tab === 'visions' ? 'Visions' : 'Gameplay'}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {activeTab === 'create' && (
          <div className="space-y-4">
            <div>
              <label className="block text-xs text-gray-400 mb-1">Game Concept</label>
              <textarea
                value={concept}
                onChange={(e) => setConcept(e.target.value)}
                placeholder="Describe your game concept..."
                className="w-full bg-[#0a0a2e] border border-[#1a1a4e] rounded-lg px-3 py-2 text-sm text-gray-200 placeholder-gray-600 focus:outline-none focus:border-amber-500 resize-none h-24"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-gray-400 mb-1">Genre</label>
                <select
                  value={genre}
                  onChange={(e) => setGenre(e.target.value)}
                  className="w-full bg-[#0a0a2e] border border-[#1a1a4e] rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-amber-500"
                >
                  {genres.map((g) => (
                    <option key={g} value={g}>{g}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">Target Audience (comma-separated)</label>
                <input
                  type="text"
                  value={audience}
                  onChange={(e) => setAudience(e.target.value)}
                  placeholder="e.g. explorer, achiever"
                  className="w-full bg-[#0a0a2e] border border-[#1a1a4e] rounded-lg px-3 py-2 text-sm text-gray-200 placeholder-gray-600 focus:outline-none focus:border-amber-500"
                />
              </div>
            </div>
            <div className="flex gap-2">
              <button
                onClick={handleCreateVision}
                disabled={loading}
                className="flex-1 py-2.5 rounded-lg bg-gradient-to-r from-amber-600 to-orange-600 text-white text-sm font-medium hover:from-amber-500 hover:to-orange-500 transition-all disabled:opacity-50"
              >
                {loading ? 'Creating...' : 'Create Vision Profile'}
              </button>
              <button
                onClick={handleGameplayAnalysis}
                disabled={loading}
                className="flex-1 py-2.5 rounded-lg bg-[#0f0f2a] border border-[#1a1a4e] text-gray-300 text-sm font-medium hover:border-amber-500 transition-all disabled:opacity-50"
              >
                {loading ? 'Analyzing...' : 'Analyze Gameplay'}
              </button>
            </div>
          </div>
        )}

        {activeTab === 'visions' && (
          <div className="space-y-3">
            {visions.length === 0 ? (
              <div className="text-center text-gray-500 py-8 text-sm">No vision profiles yet</div>
            ) : (
              visions.map((vision) => (
                <div key={vision.vision_id} className="bg-[#0f0f2a] border border-[#1a1a4e] rounded-lg p-3">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-medium text-amber-400">{vision.game_concept}</span>
                    <span className="text-[10px] text-gray-500">{vision.genre}</span>
                  </div>
                  <div className="grid grid-cols-4 gap-2 mb-3">
                    <div className="text-center">
                      <div className="text-lg font-bold text-amber-400">{(vision.coherence_score * 100).toFixed(0)}%</div>
                      <div className="text-[9px] text-gray-500">Coherence</div>
                    </div>
                    <div className="text-center">
                      <div className="text-lg font-bold text-blue-400">{(vision.feasibility_score * 100).toFixed(0)}%</div>
                      <div className="text-[9px] text-gray-500">Feasibility</div>
                    </div>
                    <div className="text-center">
                      <div className="text-lg font-bold text-green-400">{(vision.innovation_score * 100).toFixed(0)}%</div>
                      <div className="text-[9px] text-gray-500">Innovation</div>
                    </div>
                    <div className="text-center">
                      <div className="text-lg font-bold text-purple-400">{(vision.overall_score * 100).toFixed(0)}%</div>
                      <div className="text-[9px] text-gray-500">Overall</div>
                    </div>
                  </div>
                  <div className="space-y-1">
                    <span className="text-[10px] text-gray-500">Design Pillars:</span>
                    {vision.pillars.slice(0, 4).map((pillar) => (
                      <div key={pillar.pillar} className="flex items-center gap-2">
                        <span className="text-[10px] text-gray-400 w-28 truncate">{pillar.pillar.replace(/_/g, ' ')}</span>
                        <div className="flex-1 h-1 bg-[#1a1a3e] rounded-full">
                          <div
                            className="h-full bg-gradient-to-r from-amber-500 to-orange-500 rounded-full"
                            style={{ width: `${(pillar.score * 100).toFixed(0)}%` }}
                          />
                        </div>
                        <span className="text-[10px] text-gray-500">{(pillar.score * 100).toFixed(0)}%</span>
                      </div>
                    ))}
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'gameplay' && (
          <div className="space-y-3">
            {gameplayAnalysis ? (
              <>
                <div className="grid grid-cols-3 gap-2">
                  <div className="bg-[#0f0f2a] border border-[#1a1a4e] rounded-lg p-3 text-center">
                    <div className="text-xl font-bold text-amber-400">{(gameplayAnalysis.skill_ceiling * 100).toFixed(0)}%</div>
                    <div className="text-[10px] text-gray-500">Skill Ceiling</div>
                  </div>
                  <div className="bg-[#0f0f2a] border border-[#1a1a4e] rounded-lg p-3 text-center">
                    <div className="text-xl font-bold text-blue-400">{(gameplayAnalysis.accessibility_rating * 100).toFixed(0)}%</div>
                    <div className="text-[10px] text-gray-500">Accessibility</div>
                  </div>
                  <div className="bg-[#0f0f2a] border border-[#1a1a4e] rounded-lg p-3 text-center">
                    <div className="text-xl font-bold text-green-400">{(gameplayAnalysis.depth_rating * 100).toFixed(0)}%</div>
                    <div className="text-[10px] text-gray-500">Depth</div>
                  </div>
                </div>
                <div className="bg-[#0f0f2a] border border-[#1a1a4e] rounded-lg p-3">
                  <h3 className="text-xs font-medium text-gray-300 mb-2">Core Mechanics</h3>
                  {gameplayAnalysis.core_mechanics.map((m, i) => (
                    <div key={i} className="flex items-center gap-2 text-[10px] py-1 border-b border-[#1a1a3e] last:border-0">
                      <span className="text-gray-300">{m.name as string}</span>
                      <span className="text-gray-500">complexity: {m.complexity as string}</span>
                      <span className="text-gray-600 ml-auto">{m.innovation_potential as string} potential</span>
                    </div>
                  ))}
                </div>
                <div className="bg-[#0f0f2a] border border-[#1a1a4e] rounded-lg p-3">
                  <h3 className="text-xs font-medium text-gray-300 mb-2">Balance Considerations</h3>
                  {gameplayAnalysis.balance_considerations.map((b, i) => (
                    <div key={i} className="text-[10px] text-gray-400 py-0.5">- {b}</div>
                  ))}
                </div>
                <div className="bg-[#0f0f2a] border border-[#1a1a4e] rounded-lg p-3">
                  <h3 className="text-xs font-medium text-gray-300 mb-2">Pacing</h3>
                  <pre className="text-[10px] text-gray-500 whitespace-pre-wrap">
                    {JSON.stringify(gameplayAnalysis.pacing_analysis, null, 2)}
                  </pre>
                </div>
              </>
            ) : (
              <div className="text-center text-gray-500 py-8 text-sm">
                Create a vision or run gameplay analysis to see results
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default GameVisionPanel;