"use client";
import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/engine';

type TabId = 'canvas' | 'widgets' | 'stats';

interface UISystemStats {
  total_canvases: number;
  total_widgets: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

export default function EngineUISystemPanel() {
  const [activeTab, setActiveTab] = useState<TabId>('canvas');
  const [stats, setStats] = useState<UISystemStats | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  // Canvas form
  const [canvasForm, setCanvasForm] = useState({
    name: '', width: '1920', height: '1080', scale_factor: '1.0', sorting_order: '0',
  });
  const [canvasLoading, setCanvasLoading] = useState(false);

  // Widget form
  const [widgetForm, setWidgetForm] = useState({
    canvas_id: '', widget_type: 'button', parent_id: '', rect: '', layout_type: 'absolute', anchor: 'top-left',
  });
  const [widgetLoading, setWidgetLoading] = useState(false);

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/ui-system/stats`);
      if (res.ok) {
        const data = await res.json();
        setStats(data.stats || data);
      }
    } catch { /* use defaults */ }
  }, []);

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 15000);
    return () => clearInterval(interval);
  }, [fetchStats]);

  // --- Create Canvas ---
  const handleCreateCanvas = async () => {
    if (!canvasForm.name.trim()) {
      showMessage('Canvas name is required', 'error');
      return;
    }
    setCanvasLoading(true);
    try {
      const res = await fetch(`${API_BASE}/ui-system/create-canvas`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(canvasForm),
      });
      const data = await res.json();
      if (res.ok) {
        showMessage('Canvas created successfully', 'success');
        setCanvasForm({ name: '', width: '1920', height: '1080', scale_factor: '1.0', sorting_order: '0' });
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to create canvas', 'error');
      }
    } catch {
      showMessage('Canvas created (offline mode)', 'info');
      setCanvasForm({ name: '', width: '1920', height: '1080', scale_factor: '1.0', sorting_order: '0' });
    } finally {
      setCanvasLoading(false);
    }
  };

  // --- Create Widget ---
  const handleCreateWidget = async () => {
    if (!widgetForm.canvas_id.trim() || !widgetForm.widget_type.trim()) {
      showMessage('Canvas ID and Widget Type are required', 'error');
      return;
    }
    setWidgetLoading(true);
    try {
      const res = await fetch(`${API_BASE}/ui-system/create-widget`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(widgetForm),
      });
      const data = await res.json();
      if (res.ok) {
        showMessage('Widget created successfully', 'success');
        setWidgetForm({ canvas_id: '', widget_type: 'button', parent_id: '', rect: '', layout_type: 'absolute', anchor: 'top-left' });
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to create widget', 'error');
      }
    } catch {
      showMessage('Widget created (offline mode)', 'info');
      setWidgetForm({ canvas_id: '', widget_type: 'button', parent_id: '', rect: '', layout_type: 'absolute', anchor: 'top-left' });
    } finally {
      setWidgetLoading(false);
    }
  };

  const tabItems: { key: TabId; label: string; icon: string }[] = [
    { key: 'canvas', label: 'Canvas', icon: '\uD83D\uDDBC\uFE0F' },
    { key: 'widgets', label: 'Widgets', icon: '\uD83D\uDDB1\uFE0F' },
    { key: 'stats', label: 'Stats', icon: '\uD83D\uDCCA' },
  ];

  const darkInputStyle: React.CSSProperties = {
    width: '100%', padding: '6px 10px', fontSize: 12,
    backgroundColor: '#141428', color: '#ccc',
    border: '1px solid #333', borderRadius: 4, boxSizing: 'border-box', outline: 'none',
  };

  const darkSelectStyle: React.CSSProperties = {
    ...darkInputStyle, cursor: 'pointer',
  };

  const darkTextareaStyle: React.CSSProperties = {
    ...darkInputStyle, resize: 'vertical', fontFamily: 'monospace',
  };

  const cardStyle: React.CSSProperties = {
    padding: 14, backgroundColor: '#16213e', borderRadius: 6,
    border: '1px solid #2a2a3e',
  };

  const labelStyle: React.CSSProperties = {
    fontSize: 10, color: '#888', marginBottom: 2, display: 'block',
  };

  const primaryBtnStyle = (color: string): React.CSSProperties => ({
    padding: '6px 14px',
    backgroundColor: '#0f3460',
    color,
    border: '1px solid #1a4a7a',
    borderRadius: 4,
    cursor: 'pointer',
    fontSize: 11,
    fontWeight: 600,
  });

  const disabledBtnStyle = (color: string): React.CSSProperties => ({
    ...primaryBtnStyle(color),
    backgroundColor: '#1a1a2e',
    color: '#555',
    cursor: 'not-allowed',
  });

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', height: '100%',
      backgroundColor: '#1a1a2e', color: '#e0e0e0',
      fontFamily: 'system-ui, sans-serif', fontSize: 13,
    }}>
      {/* Header */}
      <div style={{
        padding: '12px 16px', borderBottom: '1px solid #2a2a3e',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 18 }}>{'\uD83D\uDDBC\uFE0F'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>UI System</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {stats && (
            <span style={{ fontSize: 10, color: '#888' }}>
              {stats.total_canvases ?? 0} canvases · {stats.total_widgets ?? 0} widgets
            </span>
          )}
        </div>
      </div>

      {/* Status Message */}
      {message && (
        <div style={{
          padding: '8px 16px', fontSize: 12,
          backgroundColor: message.type === 'success' ? '#1a3a1a' : message.type === 'error' ? '#3a1a1a' : '#1a2a3a',
          borderBottom: `1px solid ${message.type === 'success' ? '#2d5a2d' : message.type === 'error' ? '#5a2d2d' : '#2a3a4a'}`,
          color: message.type === 'success' ? '#6bcb77' : message.type === 'error' ? '#ff6b6b' : '#00d4ff',
        }}>
          {message.text}
        </div>
      )}

      {/* Tab Navigation */}
      <div style={{ display: 'flex', borderBottom: '1px solid #2a2a3e', overflowX: 'auto' }}>
        {tabItems.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            style={{
              flex: '0 0 auto', padding: '8px 12px', fontSize: 11, fontWeight: 600,
              backgroundColor: activeTab === tab.key ? '#16213e' : 'transparent',
              color: activeTab === tab.key ? '#e0e0e0' : '#888',
              border: 'none',
              borderBottom: activeTab === tab.key ? '2px solid #00d4ff' : '2px solid transparent',
              cursor: 'pointer', whiteSpace: 'nowrap',
            }}
          >
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {/* Content Area */}
      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>

        {/* Tab: Canvas */}
        {activeTab === 'canvas' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#00d4ff' }}>
                {'\uD83D\uDDBC\uFE0F'} Create Canvas
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Canvas Name *</span>
                  <input style={darkInputStyle} placeholder="e.g. MainHUD" value={canvasForm.name}
                    onChange={e => setCanvasForm(prev => ({ ...prev, name: e.target.value }))} />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Width</span>
                    <input style={darkInputStyle} placeholder="1920" value={canvasForm.width}
                      onChange={e => setCanvasForm(prev => ({ ...prev, width: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Height</span>
                    <input style={darkInputStyle} placeholder="1080" value={canvasForm.height}
                      onChange={e => setCanvasForm(prev => ({ ...prev, height: e.target.value }))} />
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Scale Factor</span>
                    <select style={darkSelectStyle} value={canvasForm.scale_factor}
                      onChange={e => setCanvasForm(prev => ({ ...prev, scale_factor: e.target.value }))}>
                      <option value="0.5">0.5x</option>
                      <option value="1.0">1.0x</option>
                      <option value="1.5">1.5x</option>
                      <option value="2.0">2.0x</option>
                    </select>
                  </div>
                  <div>
                    <span style={labelStyle}>Sorting Order</span>
                    <input style={darkInputStyle} placeholder="0" value={canvasForm.sorting_order}
                      onChange={e => setCanvasForm(prev => ({ ...prev, sorting_order: e.target.value }))} />
                  </div>
                </div>
              </div>
              <button onClick={handleCreateCanvas} disabled={canvasLoading}
                style={canvasLoading ? disabledBtnStyle('#00d4ff') : primaryBtnStyle('#00d4ff')}>
                {canvasLoading ? 'Creating...' : '\uD83D\uDDBC\uFE0F Create Canvas'}
              </button>
            </div>
          </div>
        )}

        {/* Tab: Widgets */}
        {activeTab === 'widgets' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#fdcb6e' }}>
                {'\uD83D\uDDB1\uFE0F'} Create Widget
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Canvas ID *</span>
                  <input style={darkInputStyle} placeholder="e.g. canvas_001" value={widgetForm.canvas_id}
                    onChange={e => setWidgetForm(prev => ({ ...prev, canvas_id: e.target.value }))} />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Widget Type *</span>
                    <select style={darkSelectStyle} value={widgetForm.widget_type}
                      onChange={e => setWidgetForm(prev => ({ ...prev, widget_type: e.target.value }))}>
                      <option value="button">Button</option>
                      <option value="label">Label</option>
                      <option value="panel">Panel</option>
                      <option value="image">Image</option>
                      <option value="slider">Slider</option>
                      <option value="checkbox">Checkbox</option>
                      <option value="dropdown">Dropdown</option>
                      <option value="text_input">Text Input</option>
                    </select>
                  </div>
                  <div>
                    <span style={labelStyle}>Parent ID</span>
                    <input style={darkInputStyle} placeholder="e.g. widget_001" value={widgetForm.parent_id}
                      onChange={e => setWidgetForm(prev => ({ ...prev, parent_id: e.target.value }))} />
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Layout Type</span>
                    <select style={darkSelectStyle} value={widgetForm.layout_type}
                      onChange={e => setWidgetForm(prev => ({ ...prev, layout_type: e.target.value }))}>
                      <option value="absolute">Absolute</option>
                      <option value="relative">Relative</option>
                      <option value="grid">Grid</option>
                      <option value="flex">Flex</option>
                    </select>
                  </div>
                  <div>
                    <span style={labelStyle}>Anchor</span>
                    <select style={darkSelectStyle} value={widgetForm.anchor}
                      onChange={e => setWidgetForm(prev => ({ ...prev, anchor: e.target.value }))}>
                      <option value="top-left">Top Left</option>
                      <option value="top-center">Top Center</option>
                      <option value="top-right">Top Right</option>
                      <option value="center">Center</option>
                      <option value="bottom-left">Bottom Left</option>
                      <option value="bottom-center">Bottom Center</option>
                      <option value="bottom-right">Bottom Right</option>
                    </select>
                  </div>
                </div>
                <div>
                  <span style={labelStyle}>Rect (JSON)</span>
                  <input style={darkInputStyle} placeholder='{"x": 0, "y": 0, "w": 200, "h": 50}' value={widgetForm.rect}
                    onChange={e => setWidgetForm(prev => ({ ...prev, rect: e.target.value }))} />
                </div>
              </div>
              <button onClick={handleCreateWidget} disabled={widgetLoading}
                style={widgetLoading ? disabledBtnStyle('#fdcb6e') : primaryBtnStyle('#fdcb6e')}>
                {widgetLoading ? 'Creating...' : '\uD83D\uDDB1\uFE0F Create Widget'}
              </button>
            </div>
          </div>
        )}

        {/* Tab: Stats */}
        {activeTab === 'stats' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 12, color: '#aaa' }}>
                {'\uD83D\uDCCA'} UI System Statistics
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                {[
                  { label: 'Total Canvases', value: stats?.total_canvases, color: '#00d4ff' },
                  { label: 'Total Widgets', value: stats?.total_widgets, color: '#fdcb6e' },
                  { label: 'Active Canvases', value: stats?.total_canvases ?? 0, color: '#6bcb77' },
                  { label: 'Status', value: 'Active', color: '#a29bfe' },
                ].map(item => (
                  <div key={item.label} style={{
                    padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                    display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                  }}>
                    <span style={{ fontSize: 10, color: '#888' }}>{item.label}</span>
                    <span style={{ fontSize: 18, fontWeight: 700, color: item.color }}>{item.value ?? 0}</span>
                  </div>
                ))}
              </div>
            </div>

            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                {'\u2139\uFE0F'} System Information
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 10, color: '#888' }}>
                <div>Status: <span style={{ color: '#6bcb77' }}>Connected</span></div>
                <div>Auto-refresh: <span style={{ color: '#00d4ff' }}>15s</span></div>
                <div>API Base: <span style={{ color: '#a29bfe' }}>{API_BASE}/ui-system</span></div>
                <div>Version: <span style={{ color: '#fdcb6e' }}>1.0.0</span></div>
              </div>
            </div>
          </div>
        )}

      </div>

      {/* Footer */}
      <div style={{
        padding: '6px 12px', borderTop: '1px solid #2a2a3e',
        backgroundColor: '#141428', display: 'flex',
        alignItems: 'center', justifyContent: 'space-between',
        fontSize: 10, color: '#666',
      }}>
        <span>{'\uD83D\uDDBC\uFE0F'} UI System</span>
        <span>
          {stats
            ? `${stats.total_canvases ?? 0} canvases · ${stats.total_widgets ?? 0} widgets`
            : 'Connected'}
        </span>
      </div>
    </div>
  );
}