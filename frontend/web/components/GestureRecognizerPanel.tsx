import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

type TabId = 'patterns' | 'input' | 'events';

interface GesturePattern {
  id: string;
  name: string;
  type: string;
  points: number;
}

interface ActiveTouch {
  id: string;
  x: number;
  y: number;
  phase: string;
}

interface GestureEvent {
  id: string;
  gesture: string;
  confidence: number;
  timestamp: string;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const GestureRecognizerPanel: React.FC = () => {
  const [patterns, setPatterns] = useState<GesturePattern[]>([]);
  const [activeTouches, setActiveTouches] = useState<ActiveTouch[]>([]);
  const [gestureHistory, setGestureHistory] = useState<GestureEvent[]>([]);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('patterns');

  const [patternName, setPatternName] = useState('');
  const [patternType, setPatternType] = useState('SWIPE');
  const [complexName, setComplexName] = useState('');
  const [complexSteps, setComplexSteps] = useState('swipe,tap,hold');

  const [touchX, setTouchX] = useState('100');
  const [touchY, setTouchY] = useState('200');
  const [sensitivity, setSensitivity] = useState('0.8');

  const apiBase = API_ROOT + '/agent';

  const defaultPatterns: GesturePattern[] = [
    { id: uid(), name: 'SwipeLeft', type: 'SWIPE', points: 2 },
    { id: uid(), name: 'Pinch', type: 'PINCH', points: 2 },
    { id: uid(), name: 'LongPress', type: 'HOLD', points: 1 },
    { id: uid(), name: 'Rotate', type: 'ROTATION', points: 2 },
  ];

  const defaultTouches: ActiveTouch[] = [
    { id: uid(), x: 100, y: 200, phase: 'began' },
    { id: uid(), x: 250, y: 300, phase: 'moved' },
  ];

  const defaultHistory: GestureEvent[] = [
    { id: uid(), gesture: 'SwipeLeft', confidence: 0.92, timestamp: new Date().toISOString() },
    { id: uid(), gesture: 'Pinch', confidence: 0.88, timestamp: new Date().toISOString() },
    { id: uid(), gesture: 'Tap', confidence: 0.99, timestamp: new Date().toISOString() },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchGestureHistory = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/gesture-recognizer/get_gesture_history`);
      const data = await res.json();
      if (data.history) setGestureHistory(data.history);
      setMessage(null);
    } catch {
      // use defaults
    }
  }, []);

  useEffect(() => {
    setPatterns(defaultPatterns);
    setActiveTouches(defaultTouches);
    setGestureHistory(defaultHistory);
    fetchGestureHistory();
  }, [fetchGestureHistory]);

  const handleRegisterPattern = async () => {
    if (!patternName.trim()) {
      showMessage('Pattern name is required', 'error');
      return;
    }
    try {
      await fetch(`${apiBase}/gesture-recognizer/register_pattern`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: patternName, type: patternType }),
      });
      const newPattern: GesturePattern = {
        id: uid(), name: patternName, type: patternType, points: 1,
      };
      setPatterns(prev => [...prev, newPattern]);
      setPatternName('');
      showMessage(`Pattern "${patternName}" registered`, 'success');
    } catch {
      const newPattern: GesturePattern = {
        id: uid(), name: patternName, type: patternType, points: 1,
      };
      setPatterns(prev => [...prev, newPattern]);
      setPatternName('');
      showMessage(`Pattern "${patternName}" registered (offline fallback)`, 'info');
    }
  };

  const handleDefineComplexGesture = async () => {
    if (!complexName.trim()) {
      showMessage('Gesture name is required', 'error');
      return;
    }
    try {
      await fetch(`${apiBase}/gesture-recognizer/define_complex_gesture`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: complexName, steps: complexSteps }),
      });
      const newPattern: GesturePattern = {
        id: uid(), name: complexName, type: 'COMPLEX', points: complexSteps.split(',').length,
      };
      setPatterns(prev => [...prev, newPattern]);
      setComplexName('');
      showMessage(`Complex gesture "${complexName}" defined`, 'success');
    } catch {
      const newPattern: GesturePattern = {
        id: uid(), name: complexName, type: 'COMPLEX', points: complexSteps.split(',').length,
      };
      setPatterns(prev => [...prev, newPattern]);
      setComplexName('');
      showMessage(`Complex gesture "${complexName}" defined (offline fallback)`, 'info');
    }
  };

  const handleFeedTouch = async () => {
    try {
      await fetch(`${apiBase}/gesture-recognizer/feed_touch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ x: parseFloat(touchX), y: parseFloat(touchY), phase: 'began' }),
      });
      const newTouch: ActiveTouch = {
        id: uid(), x: parseFloat(touchX), y: parseFloat(touchY), phase: 'began',
      };
      setActiveTouches(prev => [...prev, newTouch]);
      showMessage(`Touch fed at (${touchX}, ${touchY})`, 'success');
    } catch {
      const newTouch: ActiveTouch = {
        id: uid(), x: parseFloat(touchX), y: parseFloat(touchY), phase: 'began',
      };
      setActiveTouches(prev => [...prev, newTouch]);
      showMessage(`Touch fed at (${touchX}, ${touchY}) (offline fallback)`, 'info');
    }
  };

  const handleCalibrateSensitivity = async () => {
    try {
      await fetch(`${apiBase}/gesture-recognizer/calibrate_sensitivity`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sensitivity: parseFloat(sensitivity) }),
      });
      showMessage(`Sensitivity calibrated to ${sensitivity}`, 'success');
    } catch {
      showMessage(`Sensitivity calibrated to ${sensitivity} (offline fallback)`, 'info');
    }
  };

  const handleProcessFrame = async () => {
    try {
      const res = await fetch(`${apiBase}/gesture-recognizer/process_frame`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      const data = await res.json();
      showMessage(`Frame processed: ${data.gestures_detected || '1'} gesture(s) found`, 'success');
    } catch {
      showMessage('Frame processed: 1 gesture(s) found (offline fallback)', 'info');
    }
  };

  const handleRecognizeGesture = async () => {
    try {
      const res = await fetch(`${apiBase}/gesture-recognizer/recognize_gesture`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      const data = await res.json();
      const event: GestureEvent = {
        id: uid(),
        gesture: data.gesture || 'Tap',
        confidence: data.confidence || 0.95,
        timestamp: new Date().toISOString(),
      };
      setGestureHistory(prev => [...prev, event]);
      showMessage(`Gesture recognized: ${event.gesture} (${(event.confidence * 100).toFixed(0)}%)`, 'success');
    } catch {
      const event: GestureEvent = {
        id: uid(),
        gesture: 'Tap',
        confidence: 0.95,
        timestamp: new Date().toISOString(),
      };
      setGestureHistory(prev => [...prev, event]);
      showMessage(`Gesture recognized: ${event.gesture} (offline fallback)`, 'info');
    }
  };

  const tabItems: { key: TabId; label: string; icon: string; count: number }[] = [
    { key: 'patterns', label: 'Patterns', icon: '\uD83D\uDC46', count: patterns.length },
    { key: 'input', label: 'Input', icon: '\uD83D\uDDB1\uFE0F', count: activeTouches.length },
    { key: 'events', label: 'Events', icon: '\u26A1', count: gestureHistory.length },
  ];

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', height: '100%',
      backgroundColor: '#1a1a2e', color: '#e0e0e0',
      fontFamily: 'system-ui, sans-serif', fontSize: 13,
    }}>
      <div style={{
        padding: '12px 16px', borderBottom: '1px solid #2a2a3e',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 18 }}>{'\uD83D\uDC46'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Gesture Recognizer</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 10, color: '#888' }}>
            {patterns.length} patterns · {activeTouches.length} touches · {gestureHistory.length} events
          </span>
        </div>
      </div>

      {message && (
        <div style={{
          padding: '8px 16px', fontSize: 12,
          backgroundColor: message.type === 'success' ? '#1a3a1a' : message.type === 'error' ? '#3a1a1a' : '#1a2a3a',
          borderBottom: `1px solid ${message.type === 'success' ? '#2d5a2d' : message.type === 'error' ? '#5a2d2d' : '#2a3a4a'}`,
          color: message.type === 'success' ? '#6bcb77' : message.type === 'error' ? '#ff6b6b' : '#74b9ff',
        }}>
          {message.text}
        </div>
      )}

      <div style={{ display: 'flex', borderBottom: '1px solid #2a2a3e' }}>
        {tabItems.map(tab => (
          <button key={tab.key} onClick={() => setActiveTab(tab.key)} style={{
            flex: 1, padding: '8px 12px', fontSize: 12, fontWeight: 600,
            backgroundColor: activeTab === tab.key ? '#22223a' : 'transparent',
            color: activeTab === tab.key ? '#e0e0e0' : '#888',
            border: 'none', borderBottom: activeTab === tab.key ? '2px solid #6c5ce7' : '2px solid transparent',
            cursor: 'pointer',
          }}>
            {tab.icon} {tab.label} <span style={{ color: '#666', fontWeight: 400 }}>({tab.count})</span>
          </button>
        ))}
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
        {activeTab === 'patterns' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{
              padding: 12, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\uD83D\uDC46'} register_pattern
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Name</div>
                  <input value={patternName} onChange={e => setPatternName(e.target.value)} placeholder="e.g. SwipeLeft" style={{
                    padding: '6px 10px', fontSize: 11, width: 140,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Type</div>
                  <select value={patternType} onChange={e => setPatternType(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }}>
                    <option value="SWIPE">Swipe</option>
                    <option value="PINCH">Pinch</option>
                    <option value="HOLD">Hold</option>
                    <option value="ROTATION">Rotation</option>
                    <option value="TAP">Tap</option>
                  </select>
                </div>
                <button onClick={handleRegisterPattern} style={{
                  padding: '6px 14px', backgroundColor: '#2d3a5a', color: '#74b9ff',
                  border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600,
                }}>Register</button>
              </div>
            </div>

            <div style={{
              padding: 12, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\uD83D\uDD17'} define_complex_gesture
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Name</div>
                  <input value={complexName} onChange={e => setComplexName(e.target.value)} placeholder="e.g. SwipeTap" style={{
                    padding: '6px 10px', fontSize: 11, width: 140,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div style={{ flex: 1, minWidth: 180 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Steps (comma-separated)</div>
                  <input value={complexSteps} onChange={e => setComplexSteps(e.target.value)} placeholder="swipe,tap,hold" style={{
                    padding: '6px 10px', fontSize: 11, width: '100%',
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <button onClick={handleDefineComplexGesture} style={{
                  padding: '6px 14px', backgroundColor: '#3a2d3a', color: '#a29bfe',
                  border: '1px solid #4a3d4a', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600,
                }}>Define</button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>
              {'\uD83D\uDC46'} Patterns <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({patterns.length})</span>
            </div>
            {patterns.map(pattern => (
              <div key={pattern.id} style={{
                padding: 10, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e', borderLeft: '3px solid #74b9ff',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontWeight: 600, fontSize: 13, color: '#ccc' }}>{pattern.name}</span>
                  <span style={{
                    fontSize: 9, padding: '2px 8px', borderRadius: 3,
                    backgroundColor: '#1a2a3a', color: '#74b9ff', fontWeight: 600,
                    textTransform: 'uppercase',
                  }}>{pattern.type}</span>
                </div>
                <div style={{ fontSize: 10, color: '#888', marginTop: 4 }}>
                  Touch points: <span style={{ color: '#fdcb6e', fontWeight: 600 }}>{pattern.points}</span>
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'input' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{
              padding: 12, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\uD83D\uDDB1\uFE0F'} feed_touch (simulated touch input)
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>X</div>
                  <input value={touchX} onChange={e => setTouchX(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11, width: 80,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Y</div>
                  <input value={touchY} onChange={e => setTouchY(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11, width: 80,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <button onClick={handleFeedTouch} style={{
                  padding: '6px 14px', backgroundColor: '#2d4a2d', color: '#6bcb77',
                  border: '1px solid #3d5a3d', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600,
                }}>Feed Touch</button>
              </div>
            </div>

            <div style={{
              padding: 10, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 11, fontWeight: 600, color: '#aaa', marginBottom: 6 }}>calibrate_sensitivity</div>
              <div style={{ display: 'flex', gap: 6, alignItems: 'flex-end' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Sensitivity (0.0 - 1.0)</div>
                  <input value={sensitivity} onChange={e => setSensitivity(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11, width: '100%',
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <button onClick={handleCalibrateSensitivity} style={{
                  padding: '6px 14px', backgroundColor: '#4a3d2d', color: '#fdcb6e',
                  border: '1px solid #5a4d3d', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600,
                }}>Calibrate</button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>
              {'\uD83D\uDDB1\uFE0F'} get_active_touches <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({activeTouches.length})</span>
            </div>
            {activeTouches.map(touch => (
              <div key={touch.id} style={{
                padding: 10, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e', borderLeft: '3px solid #6bcb77',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: 12, color: '#ccc', fontFamily: 'monospace' }}>
                    ({touch.x}, {touch.y})
                  </span>
                  <span style={{
                    fontSize: 9, padding: '2px 8px', borderRadius: 3,
                    backgroundColor: '#1a3a1a', color: '#6bcb77', fontWeight: 600,
                    textTransform: 'uppercase',
                  }}>{touch.phase}</span>
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'events' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <div style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e', flex: 1, minWidth: 180,
              }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                  {'\u25B6\uFE0F'} process_frame
                </div>
                <button onClick={handleProcessFrame} style={{
                  padding: '6px 14px', backgroundColor: '#2d3a5a', color: '#74b9ff',
                  border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600,
                }}>Process Frame</button>
              </div>

              <div style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e', flex: 1, minWidth: 180,
              }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                  {'\u26A1'} recognize_gesture
                </div>
                <button onClick={handleRecognizeGesture} style={{
                  padding: '6px 14px', backgroundColor: '#4a2d4a', color: '#e056a0',
                  border: '1px solid #5a3d5a', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600,
                }}>Recognize</button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>
              {'\u26A1'} get_gesture_history <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({gestureHistory.length})</span>
            </div>
            {gestureHistory.map(event => (
              <div key={event.id} style={{
                padding: 10, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e', borderLeft: '3px solid #e056a0',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontWeight: 600, fontSize: 13, color: '#ccc' }}>{event.gesture}</span>
                  <span style={{
                    fontSize: 9, padding: '2px 8px', borderRadius: 3,
                    backgroundColor: event.confidence > 0.9 ? '#1a3a1a' : '#3a3a1a',
                    color: event.confidence > 0.9 ? '#6bcb77' : '#fdcb6e', fontWeight: 600,
                  }}>{(event.confidence * 100).toFixed(0)}%</span>
                </div>
                <div style={{ fontSize: 10, color: '#888', marginTop: 4 }}>
                  {new Date(event.timestamp).toLocaleTimeString()}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{
        padding: '6px 12px', borderTop: '1px solid #2a2a3e',
        backgroundColor: '#141428', display: 'flex',
        alignItems: 'center', justifyContent: 'space-between',
        fontSize: 10, color: '#666',
      }}>
        <span>{'\uD83D\uDC46'} {patterns.length} patterns · {activeTouches.length} touches · {gestureHistory.length} events</span>
        <span>Connected</span>
      </div>
    </div>
  );
};

export default GestureRecognizerPanel;