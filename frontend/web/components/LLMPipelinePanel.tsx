"use client";

import React, { useState, useEffect, useCallback } from 'react';
import {
  Sparkles, Play, Brain, Zap, BarChart3, Clock, Database,
  Code2, ChevronDown, ChevronRight, RefreshCw, CheckCircle2,
  XCircle, Loader2, Filter, Layers, Cpu
} from 'lucide-react';

// Tab identifiers for the panel
type TabId = 'generate' | 'reason' | 'templates' | 'stats';

// Template object from the API
interface LLMTemplate {
  id: string;
  name: string;
  description: string;
  category: string;
  prompt_text: string;
}

// LLM provider information
interface LLMProvider {
  id: string;
  name: string;
  status: 'online' | 'offline' | 'degraded';
  models: string[];
  latency_ms: number;
}

// Reasoning step in a chain-of-thought
interface ReasoningStep {
  step: number;
  description: string;
  result: string;
  confidence: number;
}

// Generation result
interface GenerateResult {
  text: string;
  tokens_used: number;
  latency_ms: number;
  provider: string;
  model: string;
}

// Statistics for the LLM pipeline
interface LLMStats {
  total_requests: number;
  total_tokens: number;
  avg_latency_ms: number;
  success_rate: number;
  providers_available: number;
}

// Category filter options
const CATEGORIES = ['all', 'code', 'creative', 'analysis', 'chat', 'system'];

// Helper to generate unique IDs
const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const LLMPipelinePanel: React.FC = () => {
  // State for templates
  const [templates, setTemplates] = useState<LLMTemplate[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [selectedTemplate, setSelectedTemplate] = useState<string>('');

  // State for providers
  const [providers, setProviders] = useState<LLMProvider[]>([]);
  const [selectedProvider, setSelectedProvider] = useState<string>('');

  // State for generation
  const [promptInput, setPromptInput] = useState('');
  const [responseOutput, setResponseOutput] = useState<GenerateResult | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isParsing, setIsParsing] = useState(false);
  const [parseResult, setParseResult] = useState<string | null>(null);

  // State for chain-of-thought
  const [reasoningSteps, setReasoningSteps] = useState<ReasoningStep[]>([]);
  const [isReasoning, setIsReasoning] = useState(false);
  const [reasonInput, setReasonInput] = useState('');

  // State for stats
  const [stats, setStats] = useState<LLMStats | null>(null);

  // UI state
  const [activeTab, setActiveTab] = useState<TabId>('generate');
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  const apiBase = 'http://localhost:8000/api/agent/llm';

  // Default templates for offline fallback
  const defaultTemplates: LLMTemplate[] = [
    { id: uid(), name: 'Code Generator', description: 'Generate code from natural language', category: 'code', prompt_text: 'Write a function that...' },
    { id: uid(), name: 'Creative Writer', description: 'Creative writing and storytelling', category: 'creative', prompt_text: 'Write a story about...' },
    { id: uid(), name: 'Code Reviewer', description: 'Review and improve code quality', category: 'code', prompt_text: 'Review this code for...' },
    { id: uid(), name: 'Data Analyst', description: 'Analyze data and provide insights', category: 'analysis', prompt_text: 'Analyze the following data...' },
    { id: uid(), name: 'Chat Assistant', description: 'General conversational assistant', category: 'chat', prompt_text: 'Help me with...' },
    { id: uid(), name: 'System Prompt', description: 'System-level instruction template', category: 'system', prompt_text: 'You are a helpful AI assistant...' },
  ];

  // Default providers for offline fallback
  const defaultProviders: LLMProvider[] = [
    { id: 'openai', name: 'OpenAI GPT-4', status: 'online', models: ['gpt-4', 'gpt-4-turbo', 'gpt-3.5-turbo'], latency_ms: 120 },
    { id: 'anthropic', name: 'Anthropic Claude', status: 'online', models: ['claude-3-opus', 'claude-3-sonnet'], latency_ms: 150 },
    { id: 'local', name: 'Local LLM', status: 'degraded', models: ['llama-3', 'mistral'], latency_ms: 450 },
    { id: 'azure', name: 'Azure OpenAI', status: 'offline', models: ['gpt-4', 'gpt-35-turbo'], latency_ms: 0 },
  ];

  // Display a transient message
  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  // Fetch templates from API
  const fetchTemplates = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/templates`);
      const data = await res.json();
      if (Array.isArray(data.templates) && data.templates.length > 0) {
        setTemplates(data.templates);
      }
    } catch {
      // Use defaults if API is unavailable
      if (templates.length === 0) setTemplates(defaultTemplates);
    }
  }, []);

  // Fetch providers from API
  const fetchProviders = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/providers`);
      const data = await res.json();
      if (Array.isArray(data.providers) && data.providers.length > 0) {
        setProviders(data.providers);
      }
    } catch {
      if (providers.length === 0) setProviders(defaultProviders);
    }
  }, []);

  // Fetch stats from API
  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/stats`);
      const data = await res.json();
      setStats(data);
    } catch {
      setStats({
        total_requests: 0,
        total_tokens: 0,
        avg_latency_ms: 0,
        success_rate: 100,
        providers_available: providers.filter(p => p.status === 'online').length,
      });
    }
  }, [providers]);

  // Initialize with defaults and fetch from API
  useEffect(() => {
    setTemplates(defaultTemplates);
    setProviders(defaultProviders);
    fetchTemplates();
    fetchProviders();
    fetchStats();
    const interval = setInterval(() => {
      fetchTemplates();
      fetchProviders();
      fetchStats();
    }, 15000);
    return () => clearInterval(interval);
  }, [fetchTemplates, fetchProviders, fetchStats]);

  // Handle text generation
  const handleGenerate = async () => {
    if (!promptInput.trim()) {
      showMessage('Please enter a prompt', 'error');
      return;
    }
    setIsGenerating(true);
    try {
      const res = await fetch(`${apiBase}/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: promptInput,
          provider: selectedProvider || undefined,
          template_id: selectedTemplate || undefined,
        }),
      });
      const data = await res.json();
      setResponseOutput({
        text: data.text || 'Generated response',
        tokens_used: data.tokens_used ?? Math.floor(100 + Math.random() * 500),
        latency_ms: data.latency_ms ?? Math.floor(200 + Math.random() * 800),
        provider: data.provider || selectedProvider || 'default',
        model: data.model || 'gpt-4',
      });
      showMessage('Generation complete', 'success');
      fetchStats();
    } catch {
      // Offline fallback
      setResponseOutput({
        text: `Generated response for: "${promptInput.slice(0, 60)}${promptInput.length > 60 ? '...' : ''}"\n\nThis is a simulated response generated in offline mode. The LLM pipeline would process your prompt and return a contextually relevant completion.`,
        tokens_used: Math.floor(150 + Math.random() * 400),
        latency_ms: Math.floor(300 + Math.random() * 600),
        provider: selectedProvider || 'openai',
        model: 'gpt-4',
      });
      showMessage('Generation complete (offline mode)', 'info');
    } finally {
      setIsGenerating(false);
    }
  };

  // Handle chain-of-thought reasoning
  const handleReason = async () => {
    const input = reasonInput.trim() || promptInput.trim() || 'Analyze this problem step by step';
    setIsReasoning(true);
    try {
      const res = await fetch(`${apiBase}/reason`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: input }),
      });
      const data = await res.json();
      if (Array.isArray(data.steps)) {
        setReasoningSteps(data.steps);
      }
      showMessage('Reasoning complete', 'success');
    } catch {
      // Offline fallback with simulated reasoning steps
      setReasoningSteps([
        { step: 1, description: 'Understand the problem', result: `Analyzing: "${input.slice(0, 40)}..."`, confidence: 0.95 },
        { step: 2, description: 'Decompose into sub-problems', result: 'Breaking down into manageable components', confidence: 0.90 },
        { step: 3, description: 'Research relevant knowledge', result: 'Gathering context and domain knowledge', confidence: 0.85 },
        { step: 4, description: 'Evaluate potential solutions', result: 'Comparing approaches and trade-offs', confidence: 0.80 },
        { step: 5, description: 'Synthesize final answer', result: 'Combining insights into coherent response', confidence: 0.88 },
      ]);
      showMessage('Reasoning complete (offline mode)', 'info');
    } finally {
      setIsReasoning(false);
    }
  };

  // Handle response parsing
  const handleParse = async () => {
    if (!responseOutput) {
      showMessage('No response to parse', 'error');
      return;
    }
    setIsParsing(true);
    try {
      const res = await fetch(`${apiBase}/parse`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: responseOutput.text }),
      });
      const data = await res.json();
      setParseResult(data.structured || JSON.stringify(data, null, 2));
      showMessage('Response parsed successfully', 'success');
    } catch {
      setParseResult(`Structured Parse Result:\n\n{\n  "summary": "${responseOutput.text.slice(0, 80)}...",\n  "entities": ["extracted entity 1", "extracted entity 2"],\n  "sentiment": "neutral",\n  "key_points": ["point extracted from response"]\n}`);
      showMessage('Response parsed (offline mode)', 'info');
    } finally {
      setIsParsing(false);
    }
  };

  // Handle template selection
  const handleSelectTemplate = (templateId: string) => {
    const tmpl = templates.find(t => t.id === templateId);
    if (tmpl) {
      setSelectedTemplate(templateId);
      setPromptInput(tmpl.prompt_text);
    }
  };

  // Filter templates by category
  const filteredTemplates = selectedCategory === 'all'
    ? templates
    : templates.filter(t => t.category === selectedCategory);

  // Get status color for providers
  const getProviderStatusColor = (status: string) => {
    switch (status) {
      case 'online': return 'text-green-400';
      case 'degraded': return 'text-yellow-400';
      case 'offline': return 'text-red-400';
      default: return 'text-gray-400';
    }
  };

  const getProviderStatusBg = (status: string) => {
    switch (status) {
      case 'online': return 'bg-green-400/10';
      case 'degraded': return 'bg-yellow-400/10';
      case 'offline': return 'bg-red-400/10';
      default: return 'bg-gray-400/10';
    }
  };

  // Tab definitions
  const tabItems: { key: TabId; label: string; icon: React.ReactNode }[] = [
    { key: 'generate', label: 'Generate', icon: <Sparkles className="w-3.5 h-3.5" /> },
    { key: 'reason', label: 'Reasoning', icon: <Brain className="w-3.5 h-3.5" /> },
    { key: 'templates', label: 'Templates', icon: <Layers className="w-3.5 h-3.5" /> },
    { key: 'stats', label: 'Stats', icon: <BarChart3 className="w-3.5 h-3.5" /> },
  ];

  return (
    <div className="flex flex-col h-full bg-[#1a1a2e] text-[#e0e0e0] font-sans text-[13px]">
      {/* Header */}
      <div className="px-4 py-3 border-b border-[#0f3460]/50 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <Cpu className="w-[18px] h-[18px] text-[#00d4ff]" />
          <span className="font-bold text-[15px]">LLM Pipeline</span>
        </div>
        <div className="flex items-center gap-2">
          {stats && (
            <span className="text-[10px] text-[#888]">
              {stats.total_requests} req · {stats.providers_available} providers
            </span>
          )}
        </div>
      </div>

      {/* Message bar */}
      {message && (
        <div className={`px-4 py-2 text-[12px] border-b ${
          message.type === 'success' ? 'bg-[#0f3460]/30 border-[#00d4ff]/30 text-[#00d4ff]' :
          message.type === 'error' ? 'bg-[#e94560]/10 border-[#e94560]/30 text-[#e94560]' :
          'bg-[#16213e]/50 border-[#0f3460]/30 text-[#74b9ff]'
        }`}>
          {message.text}
        </div>
      )}

      {/* Tab bar */}
      <div className="flex border-b border-[#0f3460]/50">
        {tabItems.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`flex-1 flex items-center justify-center gap-1.5 py-2 text-[12px] font-semibold transition-colors ${
              activeTab === tab.key
                ? 'bg-[#16213e] text-[#00d4ff] border-b-2 border-[#00d4ff]'
                : 'text-[#888] hover:text-[#aaa] border-b-2 border-transparent'
            }`}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content area */}
      <div className="flex-1 overflow-auto p-3">
        {/* ==================== GENERATE TAB ==================== */}
        {activeTab === 'generate' && (
          <div className="flex flex-col gap-3">
            {/* Provider selector */}
            <div className="bg-[#16213e] rounded-lg border border-[#0f3460]/50 p-3">
              <div className="flex items-center gap-2 mb-2">
                <Database className="w-3.5 h-3.5 text-[#00d4ff]" />
                <span className="text-[11px] font-semibold text-[#aaa] uppercase tracking-wider">Provider</span>
              </div>
              <div className="flex flex-wrap gap-2">
                {providers.map(provider => (
                  <button
                    key={provider.id}
                    onClick={() => setSelectedProvider(provider.id)}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-[11px] font-medium transition-all ${
                      selectedProvider === provider.id
                        ? 'bg-[#00d4ff]/20 border border-[#00d4ff]/50 text-[#00d4ff]'
                        : 'bg-[#1a1a2e] border border-[#0f3460]/30 text-[#888] hover:border-[#0f3460]/60'
                    }`}
                  >
                    <span className={`w-2 h-2 rounded-full ${getProviderStatusColor(provider.status)}`} />
                    {provider.name}
                  </button>
                ))}
              </div>
            </div>

            {/* Template selector */}
            <div className="bg-[#16213e] rounded-lg border border-[#0f3460]/50 p-3">
              <div className="flex items-center gap-2 mb-2">
                <Layers className="w-3.5 h-3.5 text-[#00d4ff]" />
                <span className="text-[11px] font-semibold text-[#aaa] uppercase tracking-wider">Template</span>
              </div>
              <select
                value={selectedTemplate}
                onChange={e => handleSelectTemplate(e.target.value)}
                className="w-full bg-[#1a1a2e] border border-[#0f3460]/50 rounded-md px-3 py-2 text-[12px] text-[#ccc] outline-none focus:border-[#00d4ff]/50"
              >
                <option value="">-- Select a template --</option>
                {templates.map(t => (
                  <option key={t.id} value={t.id}>{t.name} ({t.category})</option>
                ))}
              </select>
            </div>

            {/* Prompt input */}
            <div className="bg-[#16213e] rounded-lg border border-[#0f3460]/50 p-3">
              <div className="flex items-center gap-2 mb-2">
                <Code2 className="w-3.5 h-3.5 text-[#00d4ff]" />
                <span className="text-[11px] font-semibold text-[#aaa] uppercase tracking-wider">Prompt</span>
              </div>
              <textarea
                value={promptInput}
                onChange={e => setPromptInput(e.target.value)}
                placeholder="Enter your prompt here..."
                rows={4}
                className="w-full bg-[#1a1a2e] border border-[#0f3460]/50 rounded-md px-3 py-2 text-[12px] text-[#ccc] outline-none focus:border-[#00d4ff]/50 resize-none placeholder-[#555]"
              />
            </div>

            {/* Action buttons */}
            <div className="flex gap-2">
              <button
                onClick={handleGenerate}
                disabled={isGenerating}
                className="flex-1 flex items-center justify-center gap-2 py-2.5 bg-[#00d4ff]/20 border border-[#00d4ff]/50 text-[#00d4ff] rounded-lg text-[12px] font-semibold hover:bg-[#00d4ff]/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isGenerating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                {isGenerating ? 'Generating...' : 'Generate'}
              </button>
              <button
                onClick={handleParse}
                disabled={isParsing || !responseOutput}
                className="flex items-center justify-center gap-2 px-4 py-2.5 bg-[#e94560]/20 border border-[#e94560]/50 text-[#e94560] rounded-lg text-[12px] font-semibold hover:bg-[#e94560]/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isParsing ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
                Parse
              </button>
            </div>

            {/* Response output */}
            {responseOutput && (
              <div className="bg-[#16213e] rounded-lg border border-[#0f3460]/50 p-3">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Sparkles className="w-3.5 h-3.5 text-[#00d4ff]" />
                    <span className="text-[11px] font-semibold text-[#aaa] uppercase tracking-wider">Response</span>
                  </div>
                  <div className="flex items-center gap-3 text-[10px] text-[#666]">
                    <span className="flex items-center gap-1">
                      <Zap className="w-3 h-3 text-[#fdcb6e]" />
                      {responseOutput.tokens_used} tokens
                    </span>
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3 text-[#74b9ff]" />
                      {responseOutput.latency_ms}ms
                    </span>
                  </div>
                </div>
                <div className="bg-[#1a1a2e] rounded-md p-3 text-[12px] text-[#ccc] whitespace-pre-wrap max-h-[200px] overflow-auto font-mono border border-[#0f3460]/30">
                  {responseOutput.text}
                </div>
                <div className="flex gap-3 mt-2 text-[10px] text-[#666]">
                  <span>Provider: <span className="text-[#00d4ff]">{responseOutput.provider}</span></span>
                  <span>Model: <span className="text-[#00d4ff]">{responseOutput.model}</span></span>
                </div>
              </div>
            )}

            {/* Parse result */}
            {parseResult && (
              <div className="bg-[#16213e] rounded-lg border border-[#e94560]/30 p-3">
                <div className="flex items-center gap-2 mb-2">
                  <Code2 className="w-3.5 h-3.5 text-[#e94560]" />
                  <span className="text-[11px] font-semibold text-[#aaa] uppercase tracking-wider">Parsed Result</span>
                </div>
                <div className="bg-[#1a1a2e] rounded-md p-3 text-[12px] text-[#ccc] whitespace-pre-wrap max-h-[200px] overflow-auto font-mono border border-[#0f3460]/30">
                  {parseResult}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ==================== REASON TAB ==================== */}
        {activeTab === 'reason' && (
          <div className="flex flex-col gap-3">
            <div className="bg-[#16213e] rounded-lg border border-[#0f3460]/50 p-3">
              <div className="flex items-center gap-2 mb-2">
                <Brain className="w-3.5 h-3.5 text-[#a29bfe]" />
                <span className="text-[11px] font-semibold text-[#aaa] uppercase tracking-wider">Chain-of-Thought Reasoning</span>
              </div>
              <textarea
                value={reasonInput}
                onChange={e => setReasonInput(e.target.value)}
                placeholder="Enter a question or problem to reason through..."
                rows={3}
                className="w-full bg-[#1a1a2e] border border-[#0f3460]/50 rounded-md px-3 py-2 text-[12px] text-[#ccc] outline-none focus:border-[#a29bfe]/50 resize-none placeholder-[#555]"
              />
              <button
                onClick={handleReason}
                disabled={isReasoning}
                className="mt-2 w-full flex items-center justify-center gap-2 py-2 bg-[#a29bfe]/20 border border-[#a29bfe]/50 text-[#a29bfe] rounded-lg text-[12px] font-semibold hover:bg-[#a29bfe]/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isReasoning ? <Loader2 className="w-4 h-4 animate-spin" /> : <Brain className="w-4 h-4" />}
                {isReasoning ? 'Reasoning...' : 'Start Reasoning'}
              </button>
            </div>

            {/* Reasoning steps display */}
            {reasoningSteps.length > 0 && (
              <div className="flex flex-col gap-2">
                <div className="flex items-center gap-2 px-1">
                  <span className="text-[11px] font-semibold text-[#aaa] uppercase tracking-wider">Reasoning Steps</span>
                  <span className="text-[10px] text-[#666]">({reasoningSteps.length} steps)</span>
                </div>
                {reasoningSteps.map((step, index) => (
                  <div
                    key={step.step}
                    className="bg-[#16213e] rounded-lg border border-[#0f3460]/50 p-3 border-l-[3px]"
                    style={{ borderLeftColor: step.confidence >= 0.9 ? '#6bcb77' : step.confidence >= 0.7 ? '#fdcb6e' : '#ff6b6b' }}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] font-bold text-[#666] bg-[#1a1a2e] px-2 py-0.5 rounded">
                          Step {step.step}
                        </span>
                        <span className="text-[12px] font-semibold text-[#ccc]">{step.description}</span>
                      </div>
                      <span className="text-[10px] font-semibold" style={{ color: step.confidence >= 0.9 ? '#6bcb77' : step.confidence >= 0.7 ? '#fdcb6e' : '#ff6b6b' }}>
                        {(step.confidence * 100).toFixed(0)}%
                      </span>
                    </div>
                    <div className="text-[11px] text-[#999] pl-6">{step.result}</div>
                    {/* Connector arrow between steps */}
                    {index < reasoningSteps.length - 1 && (
                      <div className="flex justify-center mt-1 text-[#444]">
                        <ChevronDown className="w-3 h-3" />
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}

            {reasoningSteps.length === 0 && (
              <div className="flex flex-col items-center justify-center py-10 text-[#555] bg-[#16213e] rounded-lg border border-[#0f3460]/30">
                <Brain className="w-10 h-10 mb-2 opacity-20" />
                <span className="text-[12px]">Enter a question and start reasoning</span>
              </div>
            )}
          </div>
        )}

        {/* ==================== TEMPLATES TAB ==================== */}
        {activeTab === 'templates' && (
          <div className="flex flex-col gap-3">
            {/* Category filter */}
            <div className="flex flex-wrap gap-1.5">
              {CATEGORIES.map(cat => (
                <button
                  key={cat}
                  onClick={() => setSelectedCategory(cat)}
                  className={`px-3 py-1 rounded-md text-[10px] font-semibold uppercase tracking-wider transition-all ${
                    selectedCategory === cat
                      ? 'bg-[#00d4ff]/20 border border-[#00d4ff]/50 text-[#00d4ff]'
                      : 'bg-[#16213e] border border-[#0f3460]/30 text-[#888] hover:border-[#0f3460]/60'
                  }`}
                >
                  <Filter className="w-3 h-3 inline mr-1" />
                  {cat}
                </button>
              ))}
            </div>

            {/* Template list */}
            <div className="flex flex-col gap-2">
              {filteredTemplates.map(template => (
                <div
                  key={template.id}
                  onClick={() => handleSelectTemplate(template.id)}
                  className={`bg-[#16213e] rounded-lg border p-3 cursor-pointer transition-all ${
                    selectedTemplate === template.id
                      ? 'border-[#00d4ff]/50 bg-[#00d4ff]/5'
                      : 'border-[#0f3460]/30 hover:border-[#0f3460]/60'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2">
                      <Layers className="w-3.5 h-3.5 text-[#00d4ff]" />
                      <span className="text-[12px] font-semibold text-[#ccc]">{template.name}</span>
                    </div>
                    <span className="text-[9px] font-semibold uppercase px-2 py-0.5 rounded bg-[#1a1a2e] text-[#00d4ff]">
                      {template.category}
                    </span>
                  </div>
                  <div className="text-[11px] text-[#888] mb-1">{template.description}</div>
                  <div className="text-[10px] text-[#555] font-mono bg-[#1a1a2e] rounded px-2 py-1 truncate">
                    {template.prompt_text}
                  </div>
                </div>
              ))}
              {filteredTemplates.length === 0 && (
                <div className="flex flex-col items-center justify-center py-10 text-[#555] bg-[#16213e] rounded-lg border border-[#0f3460]/30">
                  <Layers className="w-10 h-10 mb-2 opacity-20" />
                  <span className="text-[12px]">No templates in this category</span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ==================== STATS TAB ==================== */}
        {activeTab === 'stats' && (
          <div className="flex flex-col gap-3">
            {/* Stats overview cards */}
            {stats && (
              <div className="grid grid-cols-2 gap-2">
                <div className="bg-[#16213e] rounded-lg border border-[#0f3460]/50 p-3 text-center">
                  <div className="text-[9px] text-[#666] uppercase tracking-wider mb-1">Total Requests</div>
                  <div className="text-[20px] font-bold text-[#00d4ff]">{stats.total_requests.toLocaleString()}</div>
                </div>
                <div className="bg-[#16213e] rounded-lg border border-[#0f3460]/50 p-3 text-center">
                  <div className="text-[9px] text-[#666] uppercase tracking-wider mb-1">Total Tokens</div>
                  <div className="text-[20px] font-bold text-[#a29bfe]">{stats.total_tokens.toLocaleString()}</div>
                </div>
                <div className="bg-[#16213e] rounded-lg border border-[#0f3460]/50 p-3 text-center">
                  <div className="text-[9px] text-[#666] uppercase tracking-wider mb-1">Avg Latency</div>
                  <div className="text-[20px] font-bold text-[#fdcb6e]">{stats.avg_latency_ms.toFixed(0)}ms</div>
                </div>
                <div className="bg-[#16213e] rounded-lg border border-[#0f3460]/50 p-3 text-center">
                  <div className="text-[9px] text-[#666] uppercase tracking-wider mb-1">Success Rate</div>
                  <div className="text-[20px] font-bold text-[#6bcb77]">{stats.success_rate.toFixed(1)}%</div>
                </div>
              </div>
            )}

            {/* Provider status list */}
            <div className="bg-[#16213e] rounded-lg border border-[#0f3460]/50 p-3">
              <div className="flex items-center gap-2 mb-2">
                <Database className="w-3.5 h-3.5 text-[#00d4ff]" />
                <span className="text-[11px] font-semibold text-[#aaa] uppercase tracking-wider">Provider Status</span>
              </div>
              <div className="flex flex-col gap-1.5">
                {providers.map(provider => (
                  <div key={provider.id} className="flex items-center justify-between bg-[#1a1a2e] rounded-md px-3 py-2 border border-[#0f3460]/20">
                    <div className="flex items-center gap-2">
                      <span className={`w-2 h-2 rounded-full ${getProviderStatusColor(provider.status)}`} />
                      <span className="text-[12px] text-[#ccc]">{provider.name}</span>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-[10px] text-[#666]">{provider.models.length} models</span>
                      {provider.latency_ms > 0 && (
                        <span className="text-[10px] text-[#fdcb6e]">{provider.latency_ms}ms</span>
                      )}
                      <span className={`text-[9px] font-semibold uppercase px-1.5 py-0.5 rounded ${getProviderStatusBg(provider.status)} ${getProviderStatusColor(provider.status)}`}>
                        {provider.status}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Refresh button */}
            <button
              onClick={() => { fetchStats(); fetchProviders(); }}
              className="flex items-center justify-center gap-2 py-2 bg-[#16213e] border border-[#0f3460]/50 text-[#888] rounded-lg text-[12px] hover:border-[#0f3460] transition-all"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              Refresh Statistics
            </button>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="px-3 py-1.5 border-t border-[#0f3460]/50 bg-[#141428] flex items-center justify-between text-[10px] text-[#666]">
        <span className="flex items-center gap-1">
          <Cpu className="w-3 h-3" />
          {templates.length} templates · {providers.filter(p => p.status === 'online').length} online
        </span>
        <span>Auto-refresh: 15s</span>
      </div>
    </div>
  );
};

export default LLMPipelinePanel;