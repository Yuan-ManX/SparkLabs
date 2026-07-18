"use client";

import React, { useState, useCallback } from 'react';
import {
  Rocket, Play, Loader2, CheckCircle2, AlertCircle,
  Package, Code2, Share2, Radio, Sliders, Copy, Check, ExternalLink,
} from 'lucide-react';
import { gamePublisherApi } from '../utils/api';

interface Manifest {
  version: string;
  artifact_id: string;
  checksum_sha256: string;
  size_bytes: number;
  size_kb: number;
  line_count: number;
  dependencies: string[];
  created_at: string;
  publisher: string;
  channel: string;
  license: string;
}

interface EmbedSnippet {
  kind: string;
  language: string;
  code: string;
  notes: string;
}

interface ShareCard {
  title: string;
  description: string;
  og_tags: Record<string, string>;
  twitter_tags: Record<string, string>;
  sparklabs_card: Record<string, string>;
  share_url: string;
  share_text: string;
}

interface DistributionChannel {
  channel_id: string;
  name: string;
  kind: string;
  enabled: boolean;
  requirements: string[];
  notes: string;
}

interface LiveOpsHook {
  hook_id: string;
  parameter: string;
  current_value: string | number | boolean;
  default_value: string | number | boolean;
  tunable: boolean;
  description: string;
}

interface PublishData {
  publish_id: string;
  success: boolean;
  game_title: string;
  version: string;
  manifest: Manifest | null;
  embed_snippets: EmbedSnippet[];
  share_card: ShareCard | null;
  channels: DistributionChannel[];
  live_ops_hooks: LiveOpsHook[];
  html_size: number;
  duration_s: number;
  error: string | null;
}

const formatBytes = (n: number): string => {
  if (n >= 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${n} B`;
};

const shortHash = (h: string): string => {
  if (!h) return '';
  return `${h.slice(0, 12)}...${h.slice(-8)}`;
};

const channelColor = (kind: string): string => {
  switch (kind) {
    case 'web': return '#74b9ff';
    case 'mobile': return '#6bcb77';
    case 'embed': return '#fdcb6e';
    case 'social': return '#a29bfe';
    default: return '#888';
  }
};

const snippetLabel = (kind: string): string => {
  switch (kind) {
    case 'iframe': return 'Iframe Embed';
    case 'direct': return 'Direct Link';
    case 'popup': return 'Popup Widget';
    default: return kind;
  }
};

const GamePublisherPanel: React.FC = () => {
  const [htmlInput, setHtmlInput] = useState('');
  const [gameTitle, setGameTitle] = useState('');
  const [version, setVersion] = useState('');
  const [description, setDescription] = useState('');
  const [shareUrl, setShareUrl] = useState('');
  const [result, setResult] = useState<PublishData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeSnippet, setActiveSnippet] = useState(0);
  const [copiedIdx, setCopiedIdx] = useState<number | null>(null);

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 5000);
  };

  const runPublish = useCallback(async () => {
    if (!htmlInput.trim()) {
      showMessage('Please paste game HTML to publish', 'error');
      return;
    }
    setIsLoading(true);
    setResult(null);
    try {
      const res = await gamePublisherApi.publish(htmlInput, gameTitle, version, description, shareUrl) as any;
      const data = res.data || res;
      if (data && data.success) {
        setResult(data);
        setActiveSnippet(0);
        const hooksCount = data.live_ops_hooks?.length || 0;
        const channelsCount = data.channels?.length || 0;
        showMessage(
          `Published v${data.version} - ${formatBytes(data.html_size)}, ${hooksCount} live-ops hooks, ${channelsCount} channels`,
          'success',
        );
      } else {
        showMessage(data?.error || 'Publish failed', 'error');
      }
    } catch {
      showMessage('API unavailable - check backend connection', 'error');
    } finally {
      setIsLoading(false);
    }
  }, [htmlInput, gameTitle, version, description, shareUrl]);

  const copySnippet = useCallback((code: string, idx: number) => {
    navigator.clipboard.writeText(code);
    setCopiedIdx(idx);
    setTimeout(() => setCopiedIdx(null), 2000);
  }, []);

  return (
    <div className="flex flex-col h-full bg-[#0a0a0a] text-[#e0e0e0] font-sans text-[13px]">
      {/* Header */}
      <div className="px-4 py-3 border-b border-[#1e1e1e] flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <Rocket className="w-[18px] h-[18px] text-[#f97316]" />
          <span className="font-bold text-[15px]">AI Game Publisher</span>
        </div>
        <div className="text-[10px] text-[#666]">
          {result ? `v${result.version} published` : 'Ship-it distribution agent'}
        </div>
      </div>

      {message && (
        <div className={`px-4 py-2 text-[12px] border-b ${
          message.type === 'success' ? 'bg-[#6bcb77]/10 border-[#6bcb77]/30 text-[#6bcb77]' :
          message.type === 'error' ? 'bg-[#e94560]/10 border-[#e94560]/30 text-[#e94560]' :
          'bg-[#16213e]/50 border-[#1e1e1e]/30 text-[#74b9ff]'
        }`}>
          {message.text}
        </div>
      )}

      <div className="flex-1 overflow-auto p-3">
        {/* Input form */}
        <div className="bg-[#141414] rounded-lg border border-[#1e1e1e] p-3 flex flex-col gap-2 mb-3">
          <div className="grid grid-cols-3 gap-2">
            <input
              type="text"
              value={gameTitle}
              onChange={e => setGameTitle(e.target.value)}
              placeholder="Game title"
              className="w-full bg-[#0a0a0a] border border-[#1e1e1e] rounded px-2.5 py-1.5 text-[12px] text-[#e0e0e0] placeholder:text-[#444] focus:outline-none focus:border-[#f97316]/50"
            />
            <input
              type="text"
              value={version}
              onChange={e => setVersion(e.target.value)}
              placeholder="Version (e.g. 1.0.0)"
              className="w-full bg-[#0a0a0a] border border-[#1e1e1e] rounded px-2.5 py-1.5 text-[12px] text-[#e0e0e0] placeholder:text-[#444] focus:outline-none focus:border-[#f97316]/50"
            />
            <input
              type="text"
              value={shareUrl}
              onChange={e => setShareUrl(e.target.value)}
              placeholder="Share URL (optional)"
              className="w-full bg-[#0a0a0a] border border-[#1e1e1e] rounded px-2.5 py-1.5 text-[12px] text-[#e0e0e0] placeholder:text-[#444] focus:outline-none focus:border-[#f97316]/50"
            />
          </div>
          <input
            type="text"
            value={description}
            onChange={e => setDescription(e.target.value)}
            placeholder="Description (optional, for share cards)"
            className="w-full bg-[#0a0a0a] border border-[#1e1e1e] rounded px-2.5 py-1.5 text-[12px] text-[#e0e0e0] placeholder:text-[#444] focus:outline-none focus:border-[#f97316]/50"
          />
          <textarea
            value={htmlInput}
            onChange={e => setHtmlInput(e.target.value)}
            placeholder="Paste polished game HTML here to publish..."
            rows={4}
            className="w-full bg-[#0a0a0a] border border-[#1e1e1e] rounded px-2.5 py-1.5 text-[11px] text-[#e0e0e0] placeholder:text-[#444] focus:outline-none focus:border-[#f97316]/50 font-mono resize-y"
          />
          <button
            onClick={runPublish}
            disabled={isLoading || !htmlInput.trim()}
            className="flex items-center justify-center gap-1.5 bg-[#f97316] hover:bg-[#ea580c] disabled:opacity-40 disabled:cursor-not-allowed text-white text-[12px] font-semibold rounded px-3 py-1.5 transition-colors"
          >
            {isLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Rocket className="w-3.5 h-3.5" />}
            {isLoading ? 'Publishing...' : 'Publish Game'}
          </button>
        </div>

        {/* Results */}
        {result && (
          <div className="flex flex-col gap-3">
            {/* Publish hero card */}
            <div className="rounded-lg border border-[#f97316]/30 bg-gradient-to-br from-[#f97316]/10 to-[#141414] p-3">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-[#6bcb77]" />
                  <span className="font-semibold text-[13px]">Published: {result.game_title} v{result.version}</span>
                </div>
                <span className="text-[10px] text-[#666]">{result.duration_s.toFixed(3)}s</span>
              </div>
              <div className="text-[11px] text-[#888] font-mono">{result.publish_id}</div>
            </div>

            {/* Manifest */}
            {result.manifest && (
              <div className="bg-[#141414] rounded-lg border border-[#1e1e1e] p-3">
                <div className="flex items-center gap-2 mb-2.5">
                  <Package className="w-3.5 h-3.5 text-[#74b9ff]" />
                  <span className="font-semibold text-[12px]">Deployment Manifest</span>
                </div>
                <div className="grid grid-cols-2 gap-x-3 gap-y-1.5 text-[11px]">
                  <div>
                    <span className="text-[#666]">Artifact ID: </span>
                    <span className="text-[#e0e0e0] font-mono">{result.manifest.artifact_id}</span>
                  </div>
                  <div>
                    <span className="text-[#666]">Version: </span>
                    <span className="text-[#e0e0e0] font-mono">{result.manifest.version}</span>
                  </div>
                  <div>
                    <span className="text-[#666]">Size: </span>
                    <span className="text-[#e0e0e0]">{formatBytes(result.manifest.size_bytes)} ({result.manifest.line_count} lines)</span>
                  </div>
                  <div>
                    <span className="text-[#666]">Channel: </span>
                    <span className="text-[#e0e0e0]">{result.manifest.channel}</span>
                  </div>
                  <div className="col-span-2">
                    <span className="text-[#666]">Checksum (SHA-256): </span>
                    <span className="text-[#e0e0e0] font-mono break-all">{shortHash(result.manifest.checksum_sha256)}</span>
                  </div>
                  <div className="col-span-2">
                    <span className="text-[#666]">Created: </span>
                    <span className="text-[#e0e0e0]">{result.manifest.created_at}</span>
                  </div>
                  {result.manifest.dependencies.length > 0 && (
                    <div className="col-span-2">
                      <span className="text-[#666]">Dependencies: </span>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {result.manifest.dependencies.map((dep, i) => (
                          <span key={i} className="text-[10px] px-1.5 py-0.5 rounded bg-[#1e1e1e] text-[#aaa] font-mono">
                            {dep}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Embed Snippets */}
            {result.embed_snippets.length > 0 && (
              <div className="bg-[#141414] rounded-lg border border-[#1e1e1e] p-3">
                <div className="flex items-center gap-2 mb-2.5">
                  <Code2 className="w-3.5 h-3.5 text-[#fdcb6e]" />
                  <span className="font-semibold text-[12px]">Embed Snippets</span>
                </div>
                <div className="flex gap-1 mb-2 border-b border-[#1e1e1e] pb-1.5">
                  {result.embed_snippets.map((snip, idx) => (
                    <button
                      key={idx}
                      onClick={() => setActiveSnippet(idx)}
                      className={`px-2.5 py-1 text-[11px] rounded transition-colors ${
                        activeSnippet === idx
                          ? 'bg-[#f97316]/20 text-[#f97316] border border-[#f97316]/40'
                          : 'text-[#666] hover:text-[#aaa] border border-transparent'
                      }`}
                    >
                      {snippetLabel(snip.kind)}
                    </button>
                  ))}
                </div>
                {result.embed_snippets[activeSnippet] && (
                  <div>
                    <div className="relative">
                      <pre className="bg-[#0a0a0a] border border-[#1e1e1e] rounded p-2.5 text-[10px] text-[#e0e0e0] font-mono overflow-x-auto whitespace-pre-wrap break-all pr-9">
                        {result.embed_snippets[activeSnippet].code}
                      </pre>
                      <button
                        onClick={() => copySnippet(result.embed_snippets[activeSnippet].code, activeSnippet)}
                        className="absolute top-1.5 right-1.5 p-1 rounded hover:bg-[#1e1e1e] text-[#666] hover:text-[#e0e0e0] transition-colors"
                        title="Copy snippet"
                      >
                        {copiedIdx === activeSnippet
                          ? <Check className="w-3 h-3 text-[#6bcb77]" />
                          : <Copy className="w-3 h-3" />}
                      </button>
                    </div>
                    <div className="text-[10px] text-[#666] mt-1.5">
                      {result.embed_snippets[activeSnippet].notes}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Share Card */}
            {result.share_card && (
              <div className="bg-[#141414] rounded-lg border border-[#1e1e1e] p-3">
                <div className="flex items-center gap-2 mb-2.5">
                  <Share2 className="w-3.5 h-3.5 text-[#a29bfe]" />
                  <span className="font-semibold text-[12px]">Share Card</span>
                </div>
                <div className="mb-2">
                  <div className="text-[11px] text-[#e0e0e0] font-semibold">{result.share_card.title}</div>
                  <div className="text-[10px] text-[#888] mt-0.5">{result.share_card.description}</div>
                </div>
                <div className="grid grid-cols-2 gap-2 text-[10px]">
                  <div className="bg-[#0a0a0a] rounded p-2 border border-[#1e1e1e]">
                    <div className="text-[#a29bfe] mb-1 font-semibold">OpenGraph</div>
                    {Object.entries(result.share_card.og_tags).map(([k, v]) => (
                      <div key={k} className="text-[#888] truncate">
                        <span className="text-[#666]">{k}: </span>{v}
                      </div>
                    ))}
                  </div>
                  <div className="bg-[#0a0a0a] rounded p-2 border border-[#1e1e1e]">
                    <div className="text-[#74b9ff] mb-1 font-semibold">Twitter Card</div>
                    {Object.entries(result.share_card.twitter_tags).map(([k, v]) => (
                      <div key={k} className="text-[#888] truncate">
                        <span className="text-[#666]">{k}: </span>{v}
                      </div>
                    ))}
                  </div>
                </div>
                <div className="mt-2 flex items-center gap-2 text-[10px]">
                  <ExternalLink className="w-3 h-3 text-[#666]" />
                  <span className="text-[#888] font-mono truncate">{result.share_card.share_url}</span>
                </div>
              </div>
            )}

            {/* Distribution Channels */}
            {result.channels.length > 0 && (
              <div className="bg-[#141414] rounded-lg border border-[#1e1e1e] p-3">
                <div className="flex items-center gap-2 mb-2.5">
                  <Radio className="w-3.5 h-3.5 text-[#6bcb77]" />
                  <span className="font-semibold text-[12px]">Distribution Channels</span>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  {result.channels.map(ch => (
                    <div
                      key={ch.channel_id}
                      className={`rounded p-2 border ${
                        ch.enabled
                          ? 'bg-[#0a0a0a] border-[#1e1e1e]'
                          : 'bg-[#0a0a0a]/50 border-[#1e1e1e]/50 opacity-60'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-[11px] font-semibold" style={{ color: channelColor(ch.kind) }}>
                          {ch.name}
                        </span>
                        {ch.enabled ? (
                          <CheckCircle2 className="w-3 h-3 text-[#6bcb77]" />
                        ) : (
                          <AlertCircle className="w-3 h-3 text-[#666]" />
                        )}
                      </div>
                      <div className="text-[10px] text-[#888]">{ch.notes}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Live Ops Hooks */}
            {result.live_ops_hooks.length > 0 && (
              <div className="bg-[#141414] rounded-lg border border-[#1e1e1e] p-3">
                <div className="flex items-center gap-2 mb-2.5">
                  <Sliders className="w-3.5 h-3.5 text-[#e94560]" />
                  <span className="font-semibold text-[12px]">
                    Live Ops Hooks ({result.live_ops_hooks.length})
                  </span>
                </div>
                <div className="text-[10px] text-[#666] mb-2">
                  Remote-tunable parameters detected from CONFIG. Inject remote config at runtime to adjust gameplay post-launch.
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-[10px]">
                    <thead>
                      <tr className="text-[#666] border-b border-[#1e1e1e]">
                        <th className="text-left py-1 px-1.5 font-medium">Parameter</th>
                        <th className="text-left py-1 px-1.5 font-medium">Current</th>
                        <th className="text-left py-1 px-1.5 font-medium">Default</th>
                        <th className="text-left py-1 px-1.5 font-medium">Tunable</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.live_ops_hooks.map(hook => (
                        <tr key={hook.hook_id} className="border-b border-[#1e1e1e]/50">
                          <td className="py-1 px-1.5 text-[#e0e0e0] font-mono">{hook.parameter}</td>
                          <td className="py-1 px-1.5 text-[#fdcb6e] font-mono">
                            {String(hook.current_value)}
                          </td>
                          <td className="py-1 px-1.5 text-[#888] font-mono">
                            {String(hook.default_value)}
                          </td>
                          <td className="py-1 px-1.5">
                            {hook.tunable ? (
                              <Check className="w-3 h-3 text-[#6bcb77] inline" />
                            ) : (
                              <AlertCircle className="w-3 h-3 text-[#666] inline" />
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default GamePublisherPanel;
