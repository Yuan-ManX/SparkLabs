"use client";

import React, { useState, useCallback, useEffect } from 'react';
import {
  Bridge, Loader2, Play, Zap, Settings, Activity,
} from 'lucide-react';
import { aiRuntimeBridgeApi } from '../utils/api';

interface BridgeStatus {
  initialized: boolean;
  build_count: number;
  runtime_attached: boolean;
  architect_attached: boolean;
  conductor_attached: boolean;
  brain_attached: boolean;
  adapter: {
    adaptation_count: number;
    last_overrides: Record<string, number | string>;
  };
  last_build: {
    success: boolean;
    ai_session_id: string;
    ai_overrides_count: number;
    duration_s: number;
  } | null;
}

const formatDuration = (s: number): string => {
  if (s < 1) return `${(s * 1000).toFixed(0)}ms`;
  return `${s.toFixed(2)}s`;
};

const StatTile: React.FC<{ label: string; value: string | number; accent?: string }> = (
  { label, value, accent = '#fff' },
) => (
  <div style={{
    background: '#0a0a0a',
    border: '1px solid #1a1a1a',
    borderRadius: '4px',
    padding: '8px 10px',
    display: 'flex',
    flexDirection: 'column',
    gap: '2px',
  }}>
    <span style={{
      fontSize: '9px',
      color: '#666',
      textTransform: 'uppercase',
      letterSpacing: '0.1em',
    }}>{label}</span>
    <span style={{
      fontSize: '15px',
      fontWeight: 700,
      color: accent,
      fontFamily: 'monospace',
    }}>{value}</span>
  </div>
);

const AIRuntimeBridgePanel: React.FC = () => {
  const [status, setStatus] = useState<BridgeStatus | null>(null);
  const [prompt, setPrompt] = useState('');
  const [genreHint, setGenreHint] = useState('');
  const [buildResult, setBuildResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const res = await aiRuntimeBridgeApi.status() as any;
      setStatus((res.data || res) as BridgeStatus);
    } catch { /* backend may be unreachable */ }
  }, []);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 4000);
    return () => clearInterval(id);
  }, [refresh]);

  const buildFromPrompt = useCallback(async () => {
    if (!prompt.trim()) return;
    setLoading(true);
    setBuildResult(null);
    try {
      const res = await aiRuntimeBridgeApi.buildFromPrompt(
        prompt, genreHint || undefined,
      ) as any;
      setBuildResult(res.data || res);
      refresh();
    } catch { /* ignore */ } finally {
      setLoading(false);
    }
  }, [prompt, genreHint, refresh]);

  return (
    <div style={{
      height: '100%',
      background: '#000',
      color: '#fff',
      padding: '12px',
      overflowY: 'auto',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
    }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        padding: '8px 0',
        borderBottom: '1px solid #1a1a1a',
        marginBottom: '10px',
      }}>
        <Bridge size={16} color="#fff" />
        <span style={{
          fontSize: '12px',
          fontWeight: 700,
          color: '#fff',
          textTransform: 'uppercase',
          letterSpacing: '0.1em',
        }}>AI Runtime Bridge</span>
        {status && (
          <span style={{
            marginLeft: 'auto',
            fontSize: '9px',
            color: '#666',
            fontFamily: 'monospace',
          }}>
            builds: {status.build_count}
          </span>
        )}
      </div>

      {/* Stats grid */}
      {status && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: '6px',
          marginBottom: '10px',
        }}>
          <StatTile label="Builds" value={status.build_count} />
          <StatTile label="Adaptations" value={status.adapter.adaptation_count} accent="#74b9ff" />
          <StatTile label="Runtime" value={status.runtime_attached ? 'ON' : 'OFF'} accent={status.runtime_attached ? '#6bcb77' : '#e94560'} />
          <StatTile label="Architect" value={status.architect_attached ? 'ON' : 'OFF'} accent={status.architect_attached ? '#6bcb77' : '#e94560'} />
          <StatTile label="Conductor" value={status.conductor_attached ? 'ON' : 'OFF'} accent={status.conductor_attached ? '#6bcb77' : '#e94560'} />
          <StatTile label="Brain" value={status.brain_attached ? 'ON' : 'OFF'} accent={status.brain_attached ? '#6bcb77' : '#e94560'} />
          <StatTile label="Overrides" value={Object.keys(status.adapter.last_overrides).length} accent="#fdcb6e" />
          <StatTile label="Last Build" value={status.last_build ? formatDuration(status.last_build.duration_s) : '-'} />
        </div>
      )}

      {/* Last overrides */}
      {status && status.adapter.last_overrides && Object.keys(status.adapter.last_overrides).length > 0 && (
        <div style={{
          background: '#0a0a0a',
          border: '1px solid #1a1a1a',
          borderRadius: '4px',
          padding: '10px',
          marginBottom: '10px',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
            <Settings size={11} color="#888" />
            <span style={{
              fontSize: '9px',
              color: '#666',
              textTransform: 'uppercase',
              letterSpacing: '0.1em',
            }}>Last AI Overrides</span>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
            {Object.entries(status.adapter.last_overrides).map(([key, val]) => (
              <span key={key} style={{
                fontSize: '10px',
                padding: '2px 6px',
                background: '#141414',
                border: '1px solid #1a1a1a',
                borderRadius: '3px',
                color: '#aaa',
                fontFamily: 'monospace',
              }}>
                {key}: {typeof val === 'number' ? val.toFixed(2) : String(val)}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Build from prompt */}
      <div style={{
        background: '#0a0a0a',
        border: '1px solid #1a1a1a',
        borderRadius: '4px',
        padding: '10px',
        display: 'flex',
        flexDirection: 'column',
        gap: '6px',
        marginBottom: '10px',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Zap size={11} color="#fdcb6e" />
          <span style={{
            fontSize: '9px',
            color: '#666',
            textTransform: 'uppercase',
            letterSpacing: '0.1em',
          }}>Build AI-Native Game</span>
        </div>
        <textarea
          value={prompt}
          onChange={e => setPrompt(e.target.value)}
          placeholder="Describe the game you want to build..."
          rows={3}
          style={{
            width: '100%',
            background: '#000',
            border: '1px solid #1a1a1a',
            borderRadius: '3px',
            padding: '6px 8px',
            color: '#fff',
            fontSize: '11px',
            fontFamily: 'monospace',
            outline: 'none',
            resize: 'vertical',
          }}
        />
        <div style={{ display: 'flex', gap: '6px' }}>
          <input
            value={genreHint}
            onChange={e => setGenreHint(e.target.value)}
            placeholder="genre hint (optional)..."
            style={{
              flex: 1,
              background: '#000',
              border: '1px solid #1a1a1a',
              borderRadius: '3px',
              padding: '6px 8px',
              color: '#fff',
              fontSize: '11px',
              fontFamily: 'monospace',
              outline: 'none',
            }}
          />
          <button
            onClick={buildFromPrompt}
            disabled={loading || !prompt.trim()}
            style={{
              background: '#fff',
              color: '#000',
              border: 'none',
              borderRadius: '3px',
              padding: '6px 12px',
              fontSize: '11px',
              fontWeight: 700,
              cursor: loading || !prompt.trim() ? 'not-allowed' : 'pointer',
              opacity: loading || !prompt.trim() ? 0.4 : 1,
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
            }}
          >
            {loading ? <Loader2 size={12} className="animate-spin" /> : <Play size={12} />}
            BUILD
          </button>
        </div>
      </div>

      {/* Build result */}
      {buildResult && (
        <div style={{
          background: '#0a0a0a',
          border: `1px solid ${buildResult.success ? '#6bcb77' : '#e94560'}`,
          borderRadius: '4px',
          padding: '10px',
          fontSize: '10px',
          fontFamily: 'monospace',
          color: '#ccc',
        }}>
          <div style={{
            color: buildResult.success ? '#6bcb77' : '#e94560',
            marginBottom: '6px',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
          }}>
            <Activity size={11} />
            {buildResult.success ? 'BUILD SUCCEEDED' : 'BUILD FAILED'}
            <span style={{ marginLeft: 'auto', color: '#666' }}>
              {formatDuration(buildResult.duration_s || 0)}
            </span>
          </div>
          {buildResult.ai_session_id && (
            <div style={{ marginBottom: '4px' }}>
              <span style={{ color: '#666' }}>session:</span>{' '}
              <span style={{ color: '#74b9ff' }}>{buildResult.ai_session_id}</span>
            </div>
          )}
          {buildResult.ai_reasoning_conclusion && (
            <div style={{ marginBottom: '4px' }}>
              <span style={{ color: '#666' }}>reasoning:</span>{' '}
              <span style={{ color: '#fdcb6e' }}>{buildResult.ai_reasoning_conclusion}</span>
            </div>
          )}
          {buildResult.html_length > 0 && (
            <div style={{ marginBottom: '4px' }}>
              <span style={{ color: '#666' }}>html:</span>{' '}
              <span style={{ color: '#6bcb77' }}>{buildResult.html_length} bytes</span>
              {buildResult.html_truncated && (
                <span style={{ color: '#fdcb6e' }}> (truncated)</span>
              )}
            </div>
          )}
          {buildResult.ai_overrides && Object.keys(buildResult.ai_overrides).length > 0 && (
            <div style={{ marginTop: '6px' }}>
              <span style={{ color: '#666' }}>overrides:</span>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginTop: '4px' }}>
                {Object.entries(buildResult.ai_overrides).map(([key, val]) => (
                  <span key={key} style={{
                    fontSize: '9px',
                    padding: '1px 4px',
                    background: '#141414',
                    border: '1px solid #1a1a1a',
                    borderRadius: '2px',
                    color: '#aaa',
                  }}>
                    {key}: {typeof val === 'number' ? val.toFixed(2) : String(val)}
                  </span>
                ))}
              </div>
            </div>
          )}
          {buildResult.error && (
            <div style={{ marginTop: '6px', color: '#e94560' }}>
              error: {buildResult.error}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default AIRuntimeBridgePanel;
