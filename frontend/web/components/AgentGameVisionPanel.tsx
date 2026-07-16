"use client";
import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/agent';

export default function AgentGameVisionPanel() {
  const [activeTab, setActiveTab] = useState('overview');
  const [stats, setStats] = useState<any>({});
  const [elements, setElements] = useState<any[]>([]);
  const [decisions, setDecisions] = useState<any[]>([]);
  const [coherenceResult, setCoherenceResult] = useState<any>(null);
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);

  // Identity form
  const [identityName, setIdentityName] = useState('');
  const [identityPillars, setIdentityPillars] = useState('');
  const [identityNarrative, setIdentityNarrative] = useState('heroic');
  const [identityVisual, setIdentityVisual] = useState('stylized');
  const [identityEmotional, setIdentityEmotional] = useState('exciting');

  // Element form
  const [elemName, setElemName] = useState('');
  const [elemType, setElemType] = useState('mechanic');
  const [elemDescription, setElemDescription] = useState('');

  // Decision form
  const [decTitle, setDecTitle] = useState('');
  const [decContext, setDecContext] = useState('');
  const [decChoice, setDecChoice] = useState('');
  const [decRationale, setDecRationale] = useState('');

  const fetchStats = useCallback(async () => {
    try { const r = await fetch(`${API_BASE}/game-vision/stats`); if (r.ok) setStats(await r.json()); } catch (e) { console.error(e); }
  }, []);

  const fetchElements = useCallback(async () => {
    try { const r = await fetch(`${API_BASE}/game-vision/elements`); if (r.ok) { const d = await r.json(); setElements(d.elements || d || []); } } catch (e) { console.error(e); }
  }, []);

  const fetchDecisions = useCallback(async () => {
    try { const r = await fetch(`${API_BASE}/game-vision/decisions`); if (r.ok) { const d = await r.json(); setDecisions(d.decisions || d || []); } } catch (e) { console.error(e); }
  }, []);

  useEffect(() => {
    fetchStats();
    fetchElements();
    fetchDecisions();
    const i = setInterval(fetchStats, 15000);
    return () => clearInterval(i);
  }, [fetchStats, fetchElements, fetchDecisions]);

  const handleSubmit = async (url: string, body: any) => {
    setLoading(true);
    try {
      const r = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      const data = await r.json();
      setMessage(r.ok ? 'Success' : data.error || 'Failed');
      setLoading(false);
      return data;
    } catch (e: any) { setMessage(e.message); setLoading(false); }
  };

  const narrativeStyles = ['heroic', 'dark', 'whimsical', 'mysterious', 'epic', 'intimate', 'satirical', 'dramatic'];
  const visualStyles = ['stylized', 'realistic', 'pixel_art', 'low_poly', 'cartoon', 'hand_drawn', 'voxel', 'cel_shaded'];
  const emotionalTones = ['exciting', 'calm', 'tense', 'joyful', 'melancholic', 'mysterious', 'empowering', 'humorous'];

  const tabs = ['overview', 'identity', 'elements', 'decisions', 'coherence'];

  return (
    <div className="h-full flex flex-col bg-[#1a1a1a] text-white">
      <div className="flex gap-1 p-3 border-b border-[#2a2a2a]">
        {tabs.map(t => (
          <button key={t} onClick={() => setActiveTab(t)}
            className={`px-4 py-2 rounded text-sm font-medium ${activeTab === t ? 'bg-[#f97316] text-black' : 'bg-[#0d0d0d] text-[#ccc] hover:bg-[#2a2a2a]'}`}>
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>
      {message && <div className="mx-4 mt-2 p-2 bg-[#0d0d0d] border border-[#2a2a2a] rounded text-sm text-[#f97316]">{message}</div>}
      <div className="flex-1 overflow-auto p-4">

        {/* Overview Tab */}
        {activeTab === 'overview' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#f97316]">Game Vision Summary</h2>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              {Object.entries(stats).map(([key, value]) => (
                <div key={key} className="bg-[#0d0d0d] p-4 rounded border border-[#2a2a2a]">
                  <h3 className="text-[#f97316] text-xs capitalize">{key.replace(/_/g, ' ')}</h3>
                  <p className="text-2xl font-bold mt-1">
                    {typeof value === 'number' ? value.toLocaleString() : String(value)}
                  </p>
                </div>
              ))}
              {Object.keys(stats).length === 0 && (
                <div className="col-span-full text-[#999] text-sm">No vision stats available</div>
              )}
            </div>
          </div>
        )}

        {/* Identity Tab */}
        {activeTab === 'identity' && (
          <div className="space-y-4">
            <div className="bg-[#0d0d0d] border border-[#2a2a2a] rounded-lg p-4">
              <h2 className="text-lg font-bold text-[#f97316] mb-3">Set Project Identity</h2>
              <div className="grid grid-cols-2 gap-3">
                <div className="col-span-2">
                  <label className="text-xs text-[#999] mb-1 block">Project Name</label>
                  <input type="text" value={identityName} onChange={e => setIdentityName(e.target.value)}
                    placeholder="My Game Project" className="w-full bg-[#1a1a1a] border border-[#2a2a2a] rounded px-3 py-2 text-white text-sm focus:border-[#f97316] focus:outline-none" />
                </div>
                <div className="col-span-2">
                  <label className="text-xs text-[#999] mb-1 block">Pillars (comma-separated)</label>
                  <input type="text" value={identityPillars} onChange={e => setIdentityPillars(e.target.value)}
                    placeholder="Exploration, Combat, Story" className="w-full bg-[#1a1a1a] border border-[#2a2a2a] rounded px-3 py-2 text-white text-sm focus:border-[#f97316] focus:outline-none" />
                </div>
                <div>
                  <label className="text-xs text-[#999] mb-1 block">Narrative Style</label>
                  <select value={identityNarrative} onChange={e => setIdentityNarrative(e.target.value)}
                    className="w-full bg-[#1a1a1a] border border-[#2a2a2a] rounded px-3 py-2 text-white text-sm focus:border-[#f97316] focus:outline-none">
                    {narrativeStyles.map(s => <option key={s} value={s}>{s}</option>)}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-[#999] mb-1 block">Visual Style</label>
                  <select value={identityVisual} onChange={e => setIdentityVisual(e.target.value)}
                    className="w-full bg-[#1a1a1a] border border-[#2a2a2a] rounded px-3 py-2 text-white text-sm focus:border-[#f97316] focus:outline-none">
                    {visualStyles.map(s => <option key={s} value={s}>{s}</option>)}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-[#999] mb-1 block">Emotional Tone</label>
                  <select value={identityEmotional} onChange={e => setIdentityEmotional(e.target.value)}
                    className="w-full bg-[#1a1a1a] border border-[#2a2a2a] rounded px-3 py-2 text-white text-sm focus:border-[#f97316] focus:outline-none">
                    {emotionalTones.map(s => <option key={s} value={s}>{s}</option>)}
                  </select>
                </div>
              </div>
              <button onClick={async () => {
                if (!identityName.trim()) { setMessage('Project name required'); return; }
                await handleSubmit(`${API_BASE}/game-vision/set-identity`, {
                  name: identityName,
                  pillars: identityPillars.split(',').map(s => s.trim()).filter(Boolean),
                  narrative: identityNarrative,
                  visual: identityVisual,
                  emotional: identityEmotional,
                });
                fetchStats();
              }} disabled={loading}
                className="mt-3 px-4 py-2 bg-[#f97316] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50">
                Set Identity
              </button>
            </div>
          </div>
        )}

        {/* Elements Tab */}
        {activeTab === 'elements' && (
          <div className="space-y-4">
            <div className="bg-[#0d0d0d] border border-[#2a2a2a] rounded-lg p-4">
              <h2 className="text-lg font-bold text-[#f97316] mb-3">Add Element</h2>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-[#999] mb-1 block">Element Name</label>
                  <input type="text" value={elemName} onChange={e => setElemName(e.target.value)}
                    placeholder="element_name" className="w-full bg-[#1a1a1a] border border-[#2a2a2a] rounded px-3 py-2 text-white text-sm focus:border-[#f97316] focus:outline-none" />
                </div>
                <div>
                  <label className="text-xs text-[#999] mb-1 block">Element Type</label>
                  <select value={elemType} onChange={e => setElemType(e.target.value)}
                    className="w-full bg-[#1a1a1a] border border-[#2a2a2a] rounded px-3 py-2 text-white text-sm focus:border-[#f97316] focus:outline-none">
                    <option value="mechanic">Mechanic</option>
                    <option value="story">Story</option>
                    <option value="character">Character</option>
                    <option value="environment">Environment</option>
                    <option value="audio">Audio</option>
                    <option value="ui">UI</option>
                  </select>
                </div>
                <div className="col-span-2">
                  <label className="text-xs text-[#999] mb-1 block">Description</label>
                  <textarea value={elemDescription} onChange={e => setElemDescription(e.target.value)}
                    rows={3} placeholder="Describe the element..."
                    className="w-full bg-[#1a1a1a] border border-[#2a2a2a] rounded px-3 py-2 text-white text-sm focus:border-[#f97316] focus:outline-none" />
                </div>
              </div>
              <button onClick={async () => {
                if (!elemName.trim()) { setMessage('Element name required'); return; }
                await handleSubmit(`${API_BASE}/game-vision/add-element`, {
                  name: elemName, type: elemType, description: elemDescription,
                });
                setElemName(''); setElemDescription('');
                fetchElements();
              }} disabled={loading}
                className="mt-3 px-4 py-2 bg-[#f97316] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50">
                Add Element
              </button>
            </div>

            <div className="bg-[#0d0d0d] border border-[#2a2a2a] rounded-lg p-4">
              <h2 className="text-lg font-bold text-[#f97316] mb-3">Elements ({elements.length})</h2>
              {elements.length > 0 ? (
                <div className="space-y-2">
                  {elements.map((el, i) => (
                    <div key={el.id || i} className="bg-[#1a1a1a] border border-[#2a2a2a] rounded-lg p-3">
                      <div className="flex items-center justify-between">
                        <span className="text-white text-sm font-medium">{el.name}</span>
                        <span className="text-xs bg-[#0d0d0d] text-[#f97316] px-2 py-0.5 rounded">{el.type || 'unknown'}</span>
                      </div>
                      {el.description && <div className="mt-1 text-xs text-[#999]">{el.description}</div>}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-[#999] text-xs">No elements added</div>
              )}
            </div>
          </div>
        )}

        {/* Decisions Tab */}
        {activeTab === 'decisions' && (
          <div className="space-y-4">
            <div className="bg-[#0d0d0d] border border-[#2a2a2a] rounded-lg p-4">
              <h2 className="text-lg font-bold text-[#f97316] mb-3">Record Decision</h2>
              <div className="grid grid-cols-2 gap-3">
                <div className="col-span-2">
                  <label className="text-xs text-[#999] mb-1 block">Decision Title</label>
                  <input type="text" value={decTitle} onChange={e => setDecTitle(e.target.value)}
                    placeholder="e.g. Art Style Direction" className="w-full bg-[#1a1a1a] border border-[#2a2a2a] rounded px-3 py-2 text-white text-sm focus:border-[#f97316] focus:outline-none" />
                </div>
                <div className="col-span-2">
                  <label className="text-xs text-[#999] mb-1 block">Context</label>
                  <input type="text" value={decContext} onChange={e => setDecContext(e.target.value)}
                    placeholder="e.g. Choosing between realistic and stylized" className="w-full bg-[#1a1a1a] border border-[#2a2a2a] rounded px-3 py-2 text-white text-sm focus:border-[#f97316] focus:outline-none" />
                </div>
                <div>
                  <label className="text-xs text-[#999] mb-1 block">Choice Made</label>
                  <input type="text" value={decChoice} onChange={e => setDecChoice(e.target.value)}
                    placeholder="e.g. stylized" className="w-full bg-[#1a1a1a] border border-[#2a2a2a] rounded px-3 py-2 text-white text-sm focus:border-[#f97316] focus:outline-none" />
                </div>
                <div>
                  <label className="text-xs text-[#999] mb-1 block">Rationale</label>
                  <input type="text" value={decRationale} onChange={e => setDecRationale(e.target.value)}
                    placeholder="e.g. Better performance" className="w-full bg-[#1a1a1a] border border-[#2a2a2a] rounded px-3 py-2 text-white text-sm focus:border-[#f97316] focus:outline-none" />
                </div>
              </div>
              <button onClick={async () => {
                if (!decTitle.trim()) { setMessage('Decision title required'); return; }
                await handleSubmit(`${API_BASE}/game-vision/record-decision`, {
                  title: decTitle, context: decContext, choice: decChoice, rationale: decRationale,
                });
                setDecTitle(''); setDecContext(''); setDecChoice(''); setDecRationale('');
                fetchDecisions();
              }} disabled={loading}
                className="mt-3 px-4 py-2 bg-[#f97316] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50">
                Record Decision
              </button>
            </div>

            <div className="bg-[#0d0d0d] border border-[#2a2a2a] rounded-lg p-4">
              <h2 className="text-lg font-bold text-[#f97316] mb-3">Decisions ({decisions.length})</h2>
              {decisions.length > 0 ? (
                <div className="space-y-2">
                  {decisions.map((d, i) => (
                    <div key={d.id || i} className="bg-[#1a1a1a] border border-[#2a2a2a] rounded-lg p-3">
                      <div className="flex items-center justify-between">
                        <span className="text-white text-sm font-medium">{d.title}</span>
                        <span className="text-xs text-[#f97316] font-mono">{d.choice}</span>
                      </div>
                      {d.context && <div className="mt-1 text-xs text-[#999]">{d.context}</div>}
                      {d.rationale && <div className="mt-1 text-xs text-[#666] italic">Rationale: {d.rationale}</div>}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-[#999] text-xs">No decisions recorded</div>
              )}
            </div>
          </div>
        )}

        {/* Coherence Tab */}
        {activeTab === 'coherence' && (
          <div className="space-y-4">
            <div className="bg-[#0d0d0d] border border-[#2a2a2a] rounded-lg p-4">
              <h2 className="text-lg font-bold text-[#f97316] mb-3">Validate Coherence</h2>
              <p className="text-[#999] text-sm mb-3">
                Check if all game vision elements, decisions, and identity form a coherent whole.
              </p>
              <button onClick={async () => {
                const result = await handleSubmit(`${API_BASE}/game-vision/validate-coherence`, {});
                if (result) setCoherenceResult(result);
              }} disabled={loading}
                className="px-4 py-2 bg-[#f97316] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50">
                {loading ? 'Validating...' : 'Validate Coherence'}
              </button>
            </div>

            {coherenceResult && (
              <div className="bg-[#0d0d0d] border border-[#2a2a2a] rounded-lg p-4">
                <h2 className="text-lg font-bold text-[#f97316] mb-3">Coherence Results</h2>
                <div className="space-y-3">
                  {coherenceResult.score !== undefined && (
                    <div className="flex items-center gap-4 mb-3">
                      <span className="text-[#999] text-sm">Coherence Score:</span>
                      <div className="flex-1 bg-[#1a1a1a] rounded-full h-4 overflow-hidden">
                        <div className="h-full rounded-full bg-[#f97316]"
                          style={{ width: `${Math.min(100, (coherenceResult.score || 0) * 100)}%` }} />
                      </div>
                      <span className="text-white text-sm font-mono">{((coherenceResult.score || 0) * 100).toFixed(0)}%</span>
                    </div>
                  )}
                  {coherenceResult.issues && coherenceResult.issues.length > 0 && (
                    <div>
                      <div className="text-yellow-400 text-sm font-medium mb-2">Issues Found:</div>
                      {coherenceResult.issues.map((issue: string, i: number) => (
                        <div key={i} className="text-yellow-300 text-xs bg-[#1a1a1a] rounded px-3 py-2 mb-1 border-l-2 border-yellow-500">
                          {issue}
                        </div>
                      ))}
                    </div>
                  )}
                  {coherenceResult.suggestions && coherenceResult.suggestions.length > 0 && (
                    <div>
                      <div className="text-green-400 text-sm font-medium mb-2">Suggestions:</div>
                      {coherenceResult.suggestions.map((s: string, i: number) => (
                        <div key={i} className="text-green-300 text-xs bg-[#1a1a1a] rounded px-3 py-2 mb-1 border-l-2 border-green-500">
                          {s}
                        </div>
                      ))}
                    </div>
                  )}
                  {Object.entries(coherenceResult).filter(([k]) => !['score', 'issues', 'suggestions'].includes(k)).map(([key, value]) => (
                    <div key={key} className="flex justify-between bg-[#1a1a1a] rounded px-3 py-2">
                      <span className="text-[#999] text-xs capitalize">{key.replace(/_/g, ' ')}</span>
                      <span className="text-white text-xs font-mono">{String(value)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  );
}