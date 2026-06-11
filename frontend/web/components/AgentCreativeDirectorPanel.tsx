"use client";

import React, { useState, useEffect, useCallback } from 'react';

const API_BASE = 'http://localhost:8000/api';

interface ProjectStats {
  total_projects: number;
  total_ideas: number;
  active_sessions: number;
  generated_prompts: number;
  [key: string]: any;
}

type TabId = 'status' | 'projects' | 'ideas' | 'sessions' | 'prompts' | 'combos' | 'export';

const AgentCreativeDirectorPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabId>('status');
  const [data, setData] = useState<ProjectStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Project fields
  const [projectId, setProjectId] = useState('');
  const [projectName, setProjectName] = useState('');
  const [projectGenre, setProjectGenre] = useState('adventure');
  const [projectAudience, setProjectAudience] = useState('core');
  const [projectStyle, setProjectStyle] = useState('stylized');
  const [projectTone, setProjectTone] = useState('hopeful');

  // Idea fields
  const [ideaProjectId, setIdeaProjectId] = useState('');
  const [ideaTitle, setIdeaTitle] = useState('');
  const [ideaDescription, setIdeaDescription] = useState('');
  const [ideaCategory, setIdeaCategory] = useState('mechanic');
  const [iterateIdeaId, setIterateIdeaId] = useState('');
  const [iterateFeedback, setIterateFeedback] = useState('');
  const [approveIdeaId, setApproveIdeaId] = useState('');
  const [feedbackIdeaId, setFeedbackIdeaId] = useState('');
  const [feedbackText, setFeedbackText] = useState('');

  // Session fields
  const [sessionProjectId, setSessionProjectId] = useState('');
  const [sessionId, setSessionId] = useState('');

  // Prompt fields
  const [promptProjectId, setPromptProjectId] = useState('');
  const [promptCount, setPromptCount] = useState('5');
  const [promptTheme, setPromptTheme] = useState('');
  const [generatedPrompts, setGeneratedPrompts] = useState<any>(null);

  // Combo fields
  const [comboProjectId, setComboProjectId] = useState('');
  const [comboCount, setComboCount] = useState('10');
  const [generatedCombos, setGeneratedCombos] = useState<any>(null);

  // Export fields
  const [exportProjectId, setExportProjectId] = useState('');
  const [exportFormat, setExportFormat] = useState('markdown');
  const [exportResult, setExportResult] = useState<string>('');

  const tabs = [
    { id: 'status' as TabId, label: 'Status' },
    { id: 'projects' as TabId, label: 'Projects' },
    { id: 'ideas' as TabId, label: 'Ideas' },
    { id: 'sessions' as TabId, label: 'Sessions' },
    { id: 'prompts' as TabId, label: 'Prompts' },
    { id: 'combos' as TabId, label: 'Combos' },
    { id: 'export' as TabId, label: 'Export' },
  ];

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const endpoint = projectId
        ? `${API_BASE}/agent/creative-director/project-stats?project_id=${projectId}`
        : `${API_BASE}/agent/creative-director/project-stats`;
      const res = await fetch(endpoint);
      if (res.ok) setData(await res.json());
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  }, [projectId]);

  useEffect(() => {
    fetchData();
    const i = setInterval(fetchData, 15000);
    return () => clearInterval(i);
  }, [fetchData]);

  const showMessage = (type: 'success' | 'error', text: string) => {
    setMessage({ type, text });
    setTimeout(() => setMessage(null), 4000);
  };

  const handleSubmit = async (endpoint: string, body: any) => {
    try {
      const res = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (res.ok) {
        showMessage('success', 'Operation successful');
        return await res.json();
      } else {
        showMessage('error', `Error: ${res.status}`);
        return null;
      }
    } catch (e: any) {
      showMessage('error', e.message);
      return null;
    }
  };

  const renderStatusTab = () => (
    <div>
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Project Stats Query</div>
        <div className="grid grid-cols-2 gap-3 mb-3">
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Project ID (optional)</label>
            <input type="text" value={projectId} onChange={(e) => setProjectId(e.target.value)} placeholder="proj_001" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
        </div>
        <button onClick={fetchData} className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]">
          Refresh Stats
        </button>
      </div>
      {data ? (
        <div className="grid grid-cols-2 gap-3">
          {Object.entries(data).map(([key, value]) => (
            <div key={key} className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
              <span className="text-gray-400 text-xs">{key.replace(/_/g, ' ')}</span>
              <div className="text-white text-sm font-mono mt-1">
                {typeof value === 'number' ? value.toLocaleString() : String(value)}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-gray-400 text-sm">No project stats available</div>
      )}
    </div>
  );

  const renderProjectsTab = () => (
    <div>
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Create Project</div>
        <div className="grid grid-cols-2 gap-3">
          <div className="col-span-2">
            <label className="text-xs text-gray-400 mb-1 block">Project Name</label>
            <input type="text" value={projectName} onChange={(e) => setProjectName(e.target.value)} placeholder="My Epic RPG" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Genre</label>
            <select value={projectGenre} onChange={(e) => setProjectGenre(e.target.value)} className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm">
              <option value="adventure">Adventure</option>
              <option value="rpg">RPG</option>
              <option value="action">Action</option>
              <option value="strategy">Strategy</option>
              <option value="simulation">Simulation</option>
              <option value="puzzle">Puzzle</option>
              <option value="platformer">Platformer</option>
              <option value="shooter">Shooter</option>
              <option value="roguelike">Roguelike</option>
              <option value="horror">Horror</option>
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Target Audience</label>
            <select value={projectAudience} onChange={(e) => setProjectAudience(e.target.value)} className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm">
              <option value="casual">Casual</option>
              <option value="core">Core</option>
              <option value="hardcore">Hardcore</option>
              <option value="family">Family</option>
              <option value="indie">Indie</option>
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Visual Style</label>
            <select value={projectStyle} onChange={(e) => setProjectStyle(e.target.value)} className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm">
              <option value="stylized">Stylized</option>
              <option value="pixel_art">Pixel Art</option>
              <option value="low_poly">Low Poly</option>
              <option value="realistic">Realistic</option>
              <option value="cel_shaded">Cel Shaded</option>
              <option value="hand_drawn">Hand Drawn</option>
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Emotional Tone</label>
            <select value={projectTone} onChange={(e) => setProjectTone(e.target.value)} className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm">
              <option value="hopeful">Hopeful</option>
              <option value="mysterious">Mysterious</option>
              <option value="tense">Tense</option>
              <option value="joyful">Joyful</option>
              <option value="dark">Dark</option>
              <option value="epic">Epic</option>
            </select>
          </div>
        </div>
        <button onClick={() => handleSubmit('/agent/creative-director/create-project', { name: projectName, genre: projectGenre, target_audience: projectAudience, visual_style: projectStyle, emotional_tone: projectTone })} className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]">
          Create Project
        </button>
      </div>
    </div>
  );

  const renderIdeasTab = () => (
    <div>
      {/* Create Idea */}
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Create Idea</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Project ID</label>
            <input type="text" value={ideaProjectId} onChange={(e) => setIdeaProjectId(e.target.value)} placeholder="proj_001" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Category</label>
            <select value={ideaCategory} onChange={(e) => setIdeaCategory(e.target.value)} className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm">
              <option value="mechanic">Mechanic</option>
              <option value="story">Story</option>
              <option value="art">Art</option>
              <option value="audio">Audio</option>
              <option value="level">Level Design</option>
            </select>
          </div>
          <div className="col-span-2">
            <label className="text-xs text-gray-400 mb-1 block">Idea Title</label>
            <input type="text" value={ideaTitle} onChange={(e) => setIdeaTitle(e.target.value)} placeholder="Double Jump Mechanic" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div className="col-span-2">
            <label className="text-xs text-gray-400 mb-1 block">Description</label>
            <textarea value={ideaDescription} onChange={(e) => setIdeaDescription(e.target.value)} rows={3} placeholder="Describe the idea in detail..." className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
        </div>
        <button onClick={() => handleSubmit('/agent/creative-director/create-idea', { project_id: ideaProjectId, title: ideaTitle, description: ideaDescription, category: ideaCategory })} className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]">
          Create Idea
        </button>
      </div>

      {/* Iterate Idea */}
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Iterate Idea</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Idea ID</label>
            <input type="text" value={iterateIdeaId} onChange={(e) => setIterateIdeaId(e.target.value)} placeholder="idea_001" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Feedback</label>
            <input type="text" value={iterateFeedback} onChange={(e) => setIterateFeedback(e.target.value)} placeholder="Make it more complex" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
        </div>
        <button onClick={() => handleSubmit('/agent/creative-director/iterate-idea', { idea_id: iterateIdeaId, feedback: iterateFeedback })} className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]">
          Iterate Idea
        </button>
      </div>

      {/* Approve Idea */}
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Approve Idea</div>
        <div>
          <label className="text-xs text-gray-400 mb-1 block">Idea ID</label>
          <input type="text" value={approveIdeaId} onChange={(e) => setApproveIdeaId(e.target.value)} placeholder="idea_001" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
        </div>
        <button onClick={() => handleSubmit('/agent/creative-director/approve-idea', { idea_id: approveIdeaId })} className="mt-3 px-4 py-2 bg-green-600 text-white rounded text-sm font-medium hover:bg-green-500">
          Approve Idea
        </button>
      </div>

      {/* Add Feedback */}
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Add Feedback</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Idea ID</label>
            <input type="text" value={feedbackIdeaId} onChange={(e) => setFeedbackIdeaId(e.target.value)} placeholder="idea_001" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Feedback</label>
            <input type="text" value={feedbackText} onChange={(e) => setFeedbackText(e.target.value)} placeholder="Needs more polish" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
        </div>
        <button onClick={() => handleSubmit('/agent/creative-director/add-feedback', { idea_id: feedbackIdeaId, feedback: feedbackText })} className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]">
          Add Feedback
        </button>
      </div>
    </div>
  );

  const renderSessionsTab = () => (
    <div>
      {/* Create Session */}
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Create Session</div>
        <div>
          <label className="text-xs text-gray-400 mb-1 block">Project ID</label>
          <input type="text" value={sessionProjectId} onChange={(e) => setSessionProjectId(e.target.value)} placeholder="proj_001" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
        </div>
        <button onClick={() => handleSubmit('/agent/creative-director/create-session', { project_id: sessionProjectId })} className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]">
          Create Session
        </button>
      </div>

      {/* End Session */}
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">End Session</div>
        <div>
          <label className="text-xs text-gray-400 mb-1 block">Session ID</label>
          <input type="text" value={sessionId} onChange={(e) => setSessionId(e.target.value)} placeholder="sess_001" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
        </div>
        <button onClick={() => handleSubmit('/agent/creative-director/end-session', { session_id: sessionId })} className="mt-3 px-4 py-2 bg-red-700 text-white rounded text-sm font-medium hover:bg-red-600">
          End Session
        </button>
      </div>
    </div>
  );

  const renderPromptsTab = () => (
    <div>
      {/* Generate Prompts */}
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Generate Prompts</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Project ID</label>
            <input type="text" value={promptProjectId} onChange={(e) => setPromptProjectId(e.target.value)} placeholder="proj_001" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Count</label>
            <input type="number" value={promptCount} onChange={(e) => setPromptCount(e.target.value)} className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div className="col-span-2">
            <label className="text-xs text-gray-400 mb-1 block">Theme (optional)</label>
            <input type="text" value={promptTheme} onChange={(e) => setPromptTheme(e.target.value)} placeholder="combat mechanics" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
        </div>
        <button
          onClick={async () => {
            const result = await handleSubmit('/agent/creative-director/generate-prompts', { project_id: promptProjectId, count: parseInt(promptCount, 10), theme: promptTheme || undefined });
            if (result) setGeneratedPrompts(result);
          }}
          className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]"
        >
          Generate Prompts
        </button>
      </div>

      {/* Generate From Prompt */}
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Generate From Prompt</div>
        <div>
          <label className="text-xs text-gray-400 mb-1 block">Project ID</label>
          <input type="text" value={promptProjectId} onChange={(e) => setPromptProjectId(e.target.value)} placeholder="proj_001" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
        </div>
        <div className="mt-2">
          <label className="text-xs text-gray-400 mb-1 block">Prompt</label>
          <textarea
            value={promptTheme}
            onChange={(e) => setPromptTheme(e.target.value)}
            rows={2}
            placeholder="Design a stealth system for a top-down game"
            className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
          />
        </div>
        <button
          onClick={async () => {
            const result = await handleSubmit('/agent/creative-director/generate-from-prompt', { project_id: promptProjectId, prompt: promptTheme });
            if (result) setGeneratedPrompts(result);
          }}
          className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]"
        >
          Generate From Prompt
        </button>
      </div>

      {/* Generated Prompts Display */}
      {generatedPrompts && (
        <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mt-3">
          <div className="text-sm font-medium text-[#00d4ff] mb-2">Generated Results</div>
          <textarea readOnly value={JSON.stringify(generatedPrompts, null, 2)} className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm font-mono h-40" />
        </div>
      )}
    </div>
  );

  const renderCombosTab = () => (
    <div>
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Generate Mechanic Combos</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Project ID</label>
            <input type="text" value={comboProjectId} onChange={(e) => setComboProjectId(e.target.value)} placeholder="proj_001" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Count</label>
            <input type="number" value={comboCount} onChange={(e) => setComboCount(e.target.value)} className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
        </div>
        <button
          onClick={async () => {
            const result = await handleSubmit('/agent/creative-director/generate-mechanic-combos', { project_id: comboProjectId, count: parseInt(comboCount, 10) });
            if (result) setGeneratedCombos(result);
          }}
          className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]"
        >
          Generate Combos
        </button>
      </div>

      {generatedCombos && (
        <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mt-3">
          <div className="text-sm font-medium text-[#00d4ff] mb-2">Generated Combos</div>
          <textarea readOnly value={JSON.stringify(generatedCombos, null, 2)} className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm font-mono h-40" />
        </div>
      )}
    </div>
  );

  const renderExportTab = () => (
    <div>
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Export Design Document</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Project ID</label>
            <input type="text" value={exportProjectId} onChange={(e) => setExportProjectId(e.target.value)} placeholder="proj_001" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Format</label>
            <select value={exportFormat} onChange={(e) => setExportFormat(e.target.value)} className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm">
              <option value="markdown">Markdown</option>
              <option value="json">JSON</option>
              <option value="pdf">PDF</option>
              <option value="html">HTML</option>
            </select>
          </div>
        </div>
        <button
          onClick={async () => {
            const result = await handleSubmit('/agent/creative-director/export-design-doc', { project_id: exportProjectId, format: exportFormat });
            if (result) setExportResult(JSON.stringify(result, null, 2));
          }}
          className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]"
        >
          Export Design Doc
        </button>
      </div>

      {exportResult && (
        <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mt-3">
          <div className="text-sm font-medium text-[#00d4ff] mb-2">Export Result</div>
          <textarea readOnly value={exportResult} className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm font-mono h-48" />
        </div>
      )}
    </div>
  );

  const renderTab = () => {
    switch (activeTab) {
      case 'status': return renderStatusTab();
      case 'projects': return renderProjectsTab();
      case 'ideas': return renderIdeasTab();
      case 'sessions': return renderSessionsTab();
      case 'prompts': return renderPromptsTab();
      case 'combos': return renderCombosTab();
      case 'export': return renderExportTab();
      default: return null;
    }
  };

  return (
    <div className="h-full flex flex-col bg-[#0f0f23]">
      {message && (
        <div className={`mx-4 mt-2 px-3 py-2 rounded text-sm ${message.type === 'success' ? 'bg-green-900/50 text-green-300 border border-green-700' : 'bg-red-900/50 text-red-300 border border-red-700'}`}>
          {message.text}
        </div>
      )}
      <div className="flex gap-1 border-b border-[#2a2a4a] px-4 pt-2">
        {tabs.map((t) => (
          <button key={t.id} onClick={() => setActiveTab(t.id)}
            className={`px-4 py-2 text-sm ${activeTab === t.id ? 'bg-[#1a1a2e] text-[#00d4ff] border-t border-x border-[#2a2a4a] rounded-t' : 'text-gray-400 hover:text-white'}`}>
            {t.label}
          </button>
        ))}
      </div>
      <div className="flex-1 overflow-auto p-4">
        {loading && <div className="text-gray-400 text-sm mb-2">Loading...</div>}
        {renderTab()}
      </div>
    </div>
  );
};

export default AgentCreativeDirectorPanel;