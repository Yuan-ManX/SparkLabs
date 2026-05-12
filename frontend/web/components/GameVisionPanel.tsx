import React, { useState, useCallback, useEffect } from 'react';

const API_BASE = 'http://localhost:8000/api/agent/game-vision';

type VisionSeverity = 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL' | 'ALL';
type TabType = 'analyze' | 'templates' | 'history';

interface VisionFinding {
  id: string;
  title: string;
  description: string;
  severity: VisionSeverity;
  suggestedFix: string;
  category: string;
}

interface VisionUIElement {
  id: string;
  type: string;
  label: string;
  confidence: number;
  boundingBox: { x: number; y: number; w: number; h: number };
}

interface VisionColorSwatch {
  hex: string;
  name: string;
  category: string;
  coverage: number;
}

interface VisionResult {
  id: string;
  timestamp: string;
  imageDescription: string;
  findings: VisionFinding[];
  uiElements: VisionUIElement[];
  colorPalette: VisionColorSwatch[];
  compositionScore: number;
  accessibilityScore: number;
  durationMs: number;
  taskTypes: string[];
}

interface VisionTemplate {
  id: string;
  name: string;
  description: string;
  imageDescription: string;
  expectedElements: string[];
  minCompositionScore: number;
  minAccessibilityScore: number;
  createdAt: string;
}

interface VisionStats {
  totalAnalyses: number;
  avgCompositionScore: number;
  avgAccessibilityScore: number;
  avgDurationMs: number;
  findingsBySeverity: Record<string, number>;
  lastAnalysisTimestamp: string | null;
}

const TASK_TYPES = [
  { key: 'screenshot_analysis', label: 'Screenshot Analysis' },
  { key: 'ui_detection', label: 'UI Detection' },
  { key: 'layout_validation', label: 'Layout Validation' },
  { key: 'color_analysis', label: 'Color Analysis' },
  { key: 'artifact_detection', label: 'Artifact Detection' },
  { key: 'consistency_check', label: 'Consistency Check' },
  { key: 'accessibility_audit', label: 'Accessibility Audit' },
];

const SEVERITY_COLORS: Record<string, string> = {
  INFO: '#a6e3a1',
  WARNING: '#f9e2af',
  ERROR: '#f38ba8',
  CRITICAL: '#e64553',
};

const SEVERITY_BG: Record<string, string> = {
  INFO: 'rgba(166,227,161,0.15)',
  WARNING: 'rgba(249,226,175,0.15)',
  ERROR: 'rgba(243,139,168,0.15)',
  CRITICAL: 'rgba(230,69,83,0.15)',
};

const ELEMENT_TYPE_COLORS: Record<string, string> = {
  BUTTON: '#89b4fa',
  TEXT: '#a6e3a1',
  IMAGE: '#f9e2af',
  INPUT: '#f38ba8',
  CONTAINER: '#cba6f7',
  ICON: '#94e2d5',
  SLIDER: '#fab387',
  TOGGLE: '#f2cdcd',
  HEADER: '#b4befe',
  LIST: '#eba0ac',
};

const GameVisionPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>('analyze');
  const [imageDescription, setImageDescription] = useState('');
  const [selectedTaskTypes, setSelectedTaskTypes] = useState<Set<string>>(
    new Set(['screenshot_analysis', 'ui_detection'])
  );
  const [results, setResults] = useState<VisionResult[]>([]);
  const [severityFilter, setSeverityFilter] = useState<VisionSeverity>('ALL');
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState<VisionStats | null>(null);
  const [templates, setTemplates] = useState<VisionTemplate[]>([]);
  const [templateName, setTemplateName] = useState('');
  const [templateDescription, setTemplateDescription] = useState('');
  const [templateImageDescription, setTemplateImageDescription] = useState('');
  const [compareTemplateId, setCompareTemplateId] = useState('');
  const [compareResult, setCompareResult] = useState<any>(null);

  const loadHistory = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/history?limit=50`);
      const data = await res.json();
      setResults(data.results || data || []);
    } catch {
      /* API not available yet */
    }
  }, []);

  const loadStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/stats`);
      const data = await res.json();
      setStats(data);
    } catch {
      /* API not available yet */
    }
  }, []);

  const loadTemplates = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/templates`);
      const data = await res.json();
      setTemplates(data.templates || data || []);
    } catch {
      /* API not available yet */
    }
  }, []);

  useEffect(() => {
    loadHistory();
    loadStats();
    loadTemplates();
  }, [loadHistory, loadStats, loadTemplates]);

  const toggleTaskType = (taskKey: string) => {
    setSelectedTaskTypes((prev) => {
      const next = new Set(prev);
      if (next.has(taskKey)) {
        next.delete(taskKey);
      } else {
        next.add(taskKey);
      }
      return next;
    });
  };

  const handleAnalyze = async () => {
    if (!imageDescription.trim() || selectedTaskTypes.size === 0) return;
    setLoading(true);
    setMessage('');
    try {
      const res = await fetch(`${API_BASE}/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          image_description: imageDescription,
          task_types: Array.from(selectedTaskTypes),
        }),
      });
      const data: VisionResult = await res.json();
      setResults((prev) => [data, ...prev]);
      setMessage('Analysis completed successfully.');
      loadStats();
    } catch {
      const mockResult: VisionResult = {
        id: `vision_${Date.now()}`,
        timestamp: new Date().toISOString(),
        imageDescription,
        findings: [
          {
            id: 'f1',
            title: 'Inconsistent Button Styling',
            description: 'Primary buttons in the main menu use different border radii (4px vs 8px) across screens.',
            severity: 'WARNING' as VisionSeverity,
            suggestedFix: 'Standardize all primary button border-radius to 6px using the design token --btn-radius.',
            category: 'UI Consistency',
          },
          {
            id: 'f2',
            title: 'Low Contrast Rating Text',
            description: 'The rating display text (#8899aa) on dark background (#2a2a3e) has a contrast ratio of 3.2:1.',
            severity: 'ERROR' as VisionSeverity,
            suggestedFix: 'Increase text color to #cdd6f4 or darken the background to meet WCAG AA minimum of 4.5:1.',
            category: 'Accessibility',
          },
          {
            id: 'f3',
            title: 'Missing Alt Text on Decorative Icons',
            description: '8 decorative icons lack aria-hidden attributes and alt text, cluttering screen reader output.',
            severity: 'INFO' as VisionSeverity,
            suggestedFix: 'Add aria-hidden="true" to decorative icons and provide meaningful alt text for functional ones.',
            category: 'Accessibility',
          },
          {
            id: 'f4',
            title: 'Layout Overflow on Narrow Viewport',
            description: 'The inventory grid overflows horizontally at viewport widths below 360px.',
            severity: 'WARNING' as VisionSeverity,
            suggestedFix: 'Add responsive grid columns using minmax(0, 1fr) and a minimum card width of 72px.',
            category: 'Layout',
          },
          {
            id: 'f5',
            title: 'JPEG Artifacts in Splash Image',
            description: 'The main splash background shows visible JPEG compression artifacts around high-contrast edges.',
            severity: 'ERROR' as VisionSeverity,
            suggestedFix: 'Re-export the splash image at quality 90+ or use a PNG format for gradient-heavy assets.',
            category: 'Artifacts',
          },
        ],
        uiElements: [
          { id: 'e1', type: 'BUTTON', label: 'Start Game', confidence: 0.98, boundingBox: { x: 320, y: 280, w: 160, h: 48 } },
          { id: 'e2', type: 'BUTTON', label: 'Settings', confidence: 0.95, boundingBox: { x: 320, y: 340, w: 160, h: 48 } },
          { id: 'e3', type: 'TEXT', label: 'Game Title', confidence: 0.99, boundingBox: { x: 200, y: 80, w: 400, h: 60 } },
          { id: 'e4', type: 'IMAGE', label: 'Hero Background', confidence: 0.97, boundingBox: { x: 0, y: 0, w: 800, h: 600 } },
          { id: 'e5', type: 'ICON', label: 'Settings Gear', confidence: 0.91, boundingBox: { x: 296, y: 340, w: 24, h: 24 } },
          { id: 'e6', type: 'TEXT', label: 'Version Label', confidence: 0.93, boundingBox: { x: 700, y: 580, w: 90, h: 16 } },
        ],
        colorPalette: [
          { hex: '#2a2a3e', name: 'Dark Background', category: 'background', coverage: 0.42 },
          { hex: '#89b4fa', name: 'Primary Accent', category: 'accent', coverage: 0.08 },
          { hex: '#cdd6f4', name: 'Text Primary', category: 'text', coverage: 0.12 },
          { hex: '#a6e3a1', name: 'Success Green', category: 'accent', coverage: 0.05 },
          { hex: '#f38ba8', name: 'Error Red', category: 'accent', coverage: 0.03 },
          { hex: '#45475a', name: 'Surface Border', category: 'border', coverage: 0.10 },
        ],
        compositionScore: 72,
        accessibilityScore: 58,
        durationMs: 1247,
        taskTypes: Array.from(selectedTaskTypes),
      };
      setResults((prev) => [mockResult, ...prev]);
      setMessage('Analysis completed (mock data — API not available).');
      loadStats();
    }
    setLoading(false);
  };

  const handleRegisterTemplate = async () => {
    if (!templateName.trim()) return;
    try {
      const res = await fetch(`${API_BASE}/templates`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: templateName,
          description: templateDescription,
          image_description: templateImageDescription,
        }),
      });
      const data = await res.json();
      setTemplates((prev) => [data, ...prev]);
      setTemplateName('');
      setTemplateDescription('');
      setTemplateImageDescription('');
      setMessage('Template registered successfully.');
    } catch {
      const mockTemplate: VisionTemplate = {
        id: `tpl_${Date.now()}`,
        name: templateName,
        description: templateDescription,
        imageDescription: templateImageDescription,
        expectedElements: ['BUTTON', 'TEXT', 'IMAGE'],
        minCompositionScore: 70,
        minAccessibilityScore: 60,
        createdAt: new Date().toISOString(),
      };
      setTemplates((prev) => [mockTemplate, ...prev]);
      setTemplateName('');
      setTemplateDescription('');
      setTemplateImageDescription('');
      setMessage('Template registered (mock — API not available).');
    }
  };

  const handleCompareTemplate = async () => {
    if (!imageDescription.trim() || !compareTemplateId) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/compare-template`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          image_description: imageDescription,
          template_id: compareTemplateId,
        }),
      });
      const data = await res.json();
      setCompareResult(data);
    } catch {
      const template = templates.find((t) => t.id === compareTemplateId);
      setCompareResult({
        matched: true,
        matchScore: 85,
        templateId: compareTemplateId,
        templateName: template?.name || 'Unknown',
        deviations: [
          { elementType: 'BUTTON', expected: 3, found: 2, severity: 'WARNING' },
          { elementType: 'TEXT', expected: 5, found: 5, severity: 'INFO' },
        ],
        compositionDelta: -8,
        accessibilityDelta: -12,
      });
    }
    setLoading(false);
  };

  const getFilteredFindings = (findings: VisionFinding[]): VisionFinding[] => {
    if (severityFilter === 'ALL') return findings;
    return findings.filter((f) => f.severity === severityFilter);
  };

  const getScoreColor = (score: number): string => {
    if (score >= 80) return '#a6e3a1';
    if (score >= 60) return '#f9e2af';
    if (score >= 40) return '#f38ba8';
    return '#e64553';
  };

  const tabs: { key: TabType; label: string }[] = [
    { key: 'analyze', label: 'Analyze' },
    { key: 'templates', label: 'Templates' },
    { key: 'history', label: 'History' },
  ];

  const renderGauge = (label: string, score: number) => (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
        <span style={{ fontSize: 10, color: '#a6adc8' }}>{label}</span>
        <span style={{ fontSize: 12, fontWeight: 'bold', color: getScoreColor(score) }}>
          {score}/100
        </span>
      </div>
      <div style={{ height: 8, backgroundColor: '#1e1e2e', borderRadius: 4, overflow: 'hidden' }}>
        <div
          style={{
            height: '100%',
            width: `${score}%`,
            backgroundColor: getScoreColor(score),
            borderRadius: 4,
            transition: 'width 0.5s ease',
          }}
        />
      </div>
    </div>
  );

  const renderStatsBar = () => {
    if (!stats) return null;
    const mockStats = stats.totalAnalyses
      ? stats
      : {
          totalAnalyses: results.length,
          avgCompositionScore: results.length > 0
            ? Math.round(results.reduce((s, r) => s + r.compositionScore, 0) / results.length)
            : 0,
          avgAccessibilityScore: results.length > 0
            ? Math.round(results.reduce((s, r) => s + r.accessibilityScore, 0) / results.length)
            : 0,
          avgDurationMs: results.length > 0
            ? Math.round(results.reduce((s, r) => s + r.durationMs, 0) / results.length)
            : 0,
          findingsBySeverity: {},
          lastAnalysisTimestamp: results.length > 0 ? results[0].timestamp : null,
        };

    return (
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 8, marginBottom: 12 }}>
        {[
          { label: 'Analyses', value: mockStats.totalAnalyses, color: '#89b4fa' },
          { label: 'Avg Composition', value: `${mockStats.avgCompositionScore}%`, color: '#a6e3a1' },
          { label: 'Avg Access.', value: `${mockStats.avgAccessibilityScore}%`, color: '#f9e2af' },
          { label: 'Avg Duration', value: `${mockStats.avgDurationMs}ms`, color: '#cba6f7' },
          { label: 'Templates', value: templates.length, color: '#94e2d5' },
        ].map((stat) => (
          <div
            key={stat.label}
            style={{
              backgroundColor: '#2a2a3e',
              border: '1px solid #45475a',
              borderRadius: 6,
              padding: '8px 12px',
              textAlign: 'center',
            }}
          >
            <div style={{ fontSize: 16, fontWeight: 'bold', color: stat.color }}>{stat.value}</div>
            <div style={{ fontSize: 9, color: '#a6adc8', marginTop: 2 }}>{stat.label}</div>
          </div>
        ))}
      </div>
    );
  };

  const renderAnalyzeTab = () => (
    <div style={{ overflowY: 'auto', height: '100%', padding: '12px 16px' }}>
      {renderStatsBar()}

      <div
        style={{
          backgroundColor: '#2a2a3e',
          border: '1px solid #45475a',
          borderRadius: 8,
          padding: 14,
          marginBottom: 12,
        }}
      >
        <div style={{ fontSize: 11, fontWeight: 600, color: '#a6adc8', marginBottom: 10, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
          Screenshot Description
        </div>
        <textarea
          value={imageDescription}
          onChange={(e) => setImageDescription(e.target.value)}
          placeholder="Describe the game screenshot to analyze (e.g., 'Main menu screen with a dark fantasy theme, a title logo centered at top, and two buttons for Start Game and Settings at the bottom...')"
          style={{
            width: '100%',
            height: 80,
            backgroundColor: '#1e1e2e',
            border: '1px solid #45475a',
            borderRadius: 6,
            padding: '8px 12px',
            fontSize: 11,
            color: '#cdd6f4',
            resize: 'vertical',
            outline: 'none',
            fontFamily: 'inherit',
          }}
        />

        <div style={{ fontSize: 11, fontWeight: 600, color: '#a6adc8', marginBottom: 8, marginTop: 12, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
          Task Types
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 12 }}>
          {TASK_TYPES.map((tt) => {
            const isSelected = selectedTaskTypes.has(tt.key);
            return (
              <label
                key={tt.key}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 5,
                  padding: '5px 10px',
                  backgroundColor: isSelected ? 'rgba(137,180,250,0.12)' : '#1e1e2e',
                  border: `1px solid ${isSelected ? '#89b4fa' : '#45475a'}`,
                  borderRadius: 4,
                  cursor: 'pointer',
                  fontSize: 10,
                  color: isSelected ? '#89b4fa' : '#a6adc8',
                  transition: 'all 0.15s',
                  userSelect: 'none',
                }}
              >
                <input
                  type="checkbox"
                  checked={isSelected}
                  onChange={() => toggleTaskType(tt.key)}
                  style={{ display: 'none' }}
                />
                <span
                  style={{
                    width: 10,
                    height: 10,
                    borderRadius: 2,
                    border: `1.5px solid ${isSelected ? '#89b4fa' : '#45475a'}`,
                    backgroundColor: isSelected ? '#89b4fa' : 'transparent',
                    display: 'inline-flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: 7,
                    color: '#1e1e2e',
                    fontWeight: 'bold',
                    flexShrink: 0,
                  }}
                >
                  {isSelected ? '✓' : ''}
                </span>
                {tt.label}
              </label>
            );
          })}
        </div>

        <button
          onClick={handleAnalyze}
          disabled={loading || !imageDescription.trim() || selectedTaskTypes.size === 0}
          style={{
            width: '100%',
            padding: '9px 0',
            backgroundColor: loading ? '#45475a' : '#89b4fa',
            color: '#1e1e2e',
            border: 'none',
            borderRadius: 6,
            fontSize: 12,
            fontWeight: 600,
            cursor: loading ? 'not-allowed' : 'pointer',
            opacity: loading || !imageDescription.trim() || selectedTaskTypes.size === 0 ? 0.5 : 1,
            transition: 'all 0.15s',
          }}
        >
          {loading ? 'Analyzing...' : 'Run Vision Analysis'}
        </button>
      </div>

      {message && (
        <div
          style={{
            backgroundColor: 'rgba(166,227,161,0.1)',
            border: '1px solid rgba(166,227,161,0.3)',
            borderRadius: 6,
            padding: '8px 12px',
            marginBottom: 12,
            fontSize: 11,
            color: '#a6e3a1',
          }}
        >
          {message}
        </div>
      )}

      {results.length > 0 && (
        <div style={{ marginTop: 4 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
            <span style={{ fontSize: 11, fontWeight: 600, color: '#a6adc8', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Latest Analysis
            </span>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ fontSize: 9, color: '#a6adc8' }}>Filter:</span>
              {(['ALL', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'] as VisionSeverity[]).map((sev) => (
                <button
                  key={sev}
                  onClick={() => setSeverityFilter(sev)}
                  style={{
                    padding: '2px 8px',
                    borderRadius: 3,
                    border: 'none',
                    backgroundColor: severityFilter === sev ? (SEVERITY_COLORS[sev] || '#89b4fa') : '#1e1e2e',
                    color: severityFilter === sev ? '#1e1e2e' : (SEVERITY_COLORS[sev] || '#a6adc8'),
                    fontSize: 9,
                    fontWeight: severityFilter === sev ? 600 : 400,
                    cursor: 'pointer',
                    transition: 'all 0.15s',
                  }}
                >
                  {sev === 'ALL' ? 'All' : sev}
                </button>
              ))}
            </div>
          </div>

          {(() => {
            const latest = results[0];
            const filteredFindings = getFilteredFindings(latest.findings);

            return (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                  <div
                    style={{
                      backgroundColor: '#2a2a3e',
                      border: '1px solid #45475a',
                      borderRadius: 8,
                      padding: 14,
                    }}
                  >
                    {renderGauge('Composition Score', latest.compositionScore)}
                    <div style={{ marginTop: 16 }}>
                      {renderGauge('Accessibility Score', latest.accessibilityScore)}
                    </div>
                    <div style={{ marginTop: 14, fontSize: 10, color: '#a6adc8' }}>
                      Duration: {latest.durationMs}ms · Tasks: {latest.taskTypes.length}
                    </div>
                  </div>

                  <div
                    style={{
                      backgroundColor: '#2a2a3e',
                      border: '1px solid #45475a',
                      borderRadius: 8,
                      padding: 14,
                    }}
                  >
                    <div style={{ fontSize: 10, fontWeight: 600, color: '#a6adc8', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                      Color Palette
                    </div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                      {latest.colorPalette.map((swatch, i) => (
                        <div
                          key={i}
                          style={{
                            display: 'flex',
                            flexDirection: 'column',
                            alignItems: 'center',
                            gap: 3,
                          }}
                        >
                          <div
                            title={`${swatch.name} (${(swatch.coverage * 100).toFixed(0)}%)`}
                            style={{
                              width: 28,
                              height: 28,
                              borderRadius: '50%',
                              backgroundColor: swatch.hex,
                              border: '2px solid #45475a',
                              boxShadow: `0 0 6px ${swatch.hex}40`,
                            }}
                          />
                          <span style={{ fontSize: 8, color: '#a6adc8', maxWidth: 48, textAlign: 'center', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {swatch.name}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                <div
                  style={{
                    backgroundColor: '#2a2a3e',
                    border: '1px solid #45475a',
                    borderRadius: 8,
                    padding: 14,
                  }}
                >
                  <div style={{ fontSize: 11, fontWeight: 600, color: '#a6adc8', marginBottom: 10, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                    Findings ({filteredFindings.length})
                  </div>
                  {filteredFindings.length === 0 ? (
                    <div style={{ fontSize: 10, color: '#585b70', textAlign: 'center', padding: '16px 0' }}>
                      No findings match the current severity filter.
                    </div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                      {filteredFindings.map((finding) => (
                        <div
                          key={finding.id}
                          style={{
                            backgroundColor: '#1e1e2e',
                            border: `1px solid ${SEVERITY_COLORS[finding.severity]}30`,
                            borderLeft: `3px solid ${SEVERITY_COLORS[finding.severity]}`,
                            borderRadius: 6,
                            padding: '10px 12px',
                          }}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                            <span
                              style={{
                                padding: '1px 7px',
                                borderRadius: 3,
                                backgroundColor: SEVERITY_BG[finding.severity],
                                color: SEVERITY_COLORS[finding.severity],
                                fontSize: 9,
                                fontWeight: 700,
                              }}
                            >
                              {finding.severity}
                            </span>
                            <span style={{ fontSize: 11, fontWeight: 600, color: '#cdd6f4' }}>
                              {finding.title}
                            </span>
                            <span style={{ fontSize: 9, color: '#585b70', marginLeft: 'auto' }}>
                              {finding.category}
                            </span>
                          </div>
                          <div style={{ fontSize: 10, color: '#a6adc8', marginBottom: 4, lineHeight: 1.4 }}>
                            {finding.description}
                          </div>
                          <div style={{ fontSize: 9, color: '#89b4fa', fontStyle: 'italic' }}>
                            Fix: {finding.suggestedFix}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                <div
                  style={{
                    backgroundColor: '#2a2a3e',
                    border: '1px solid #45475a',
                    borderRadius: 8,
                    padding: 14,
                  }}
                >
                  <div style={{ fontSize: 11, fontWeight: 600, color: '#a6adc8', marginBottom: 10, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                    UI Elements Detected ({latest.uiElements.length})
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(170px, 1fr))', gap: 6 }}>
                    {latest.uiElements.map((el) => (
                      <div
                        key={el.id}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: 8,
                          backgroundColor: '#1e1e2e',
                          border: '1px solid #45475a',
                          borderRadius: 6,
                          padding: '8px 10px',
                        }}
                      >
                        <span
                          style={{
                            padding: '2px 6px',
                            borderRadius: 3,
                            backgroundColor: `${ELEMENT_TYPE_COLORS[el.type] || '#89b4fa'}20`,
                            color: ELEMENT_TYPE_COLORS[el.type] || '#89b4fa',
                            fontSize: 8,
                            fontWeight: 700,
                            letterSpacing: '0.5px',
                          }}
                        >
                          {el.type}
                        </span>
                        <span style={{ fontSize: 10, color: '#cdd6f4', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {el.label}
                        </span>
                        <span style={{ fontSize: 9, color: '#a6adc8' }}>
                          {Math.round(el.confidence * 100)}%
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            );
          })()}
        </div>
      )}
    </div>
  );

  const renderTemplatesTab = () => (
    <div style={{ overflowY: 'auto', height: '100%', padding: '12px 16px' }}>
      <div
        style={{
          backgroundColor: '#2a2a3e',
          border: '1px solid #45475a',
          borderRadius: 8,
          padding: 14,
          marginBottom: 12,
        }}
      >
        <div style={{ fontSize: 11, fontWeight: 600, color: '#a6adc8', marginBottom: 10, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
          Register Template
        </div>
        <input
          type="text"
          value={templateName}
          onChange={(e) => setTemplateName(e.target.value)}
          placeholder="Template Name"
          style={{
            width: '100%',
            backgroundColor: '#1e1e2e',
            border: '1px solid #45475a',
            borderRadius: 6,
            padding: '8px 12px',
            fontSize: 11,
            color: '#cdd6f4',
            outline: 'none',
            marginBottom: 8,
            fontFamily: 'inherit',
          }}
        />
        <input
          type="text"
          value={templateDescription}
          onChange={(e) => setTemplateDescription(e.target.value)}
          placeholder="Template Description"
          style={{
            width: '100%',
            backgroundColor: '#1e1e2e',
            border: '1px solid #45475a',
            borderRadius: 6,
            padding: '8px 12px',
            fontSize: 11,
            color: '#cdd6f4',
            outline: 'none',
            marginBottom: 8,
            fontFamily: 'inherit',
          }}
        />
        <textarea
          value={templateImageDescription}
          onChange={(e) => setTemplateImageDescription(e.target.value)}
          placeholder="Reference image description for this template..."
          style={{
            width: '100%',
            height: 60,
            backgroundColor: '#1e1e2e',
            border: '1px solid #45475a',
            borderRadius: 6,
            padding: '8px 12px',
            fontSize: 11,
            color: '#cdd6f4',
            resize: 'vertical',
            outline: 'none',
            marginBottom: 10,
            fontFamily: 'inherit',
          }}
        />
        <button
          onClick={handleRegisterTemplate}
          disabled={!templateName.trim()}
          style={{
            width: '100%',
            padding: '9px 0',
            backgroundColor: '#89b4fa',
            color: '#1e1e2e',
            border: 'none',
            borderRadius: 6,
            fontSize: 12,
            fontWeight: 600,
            cursor: !templateName.trim() ? 'not-allowed' : 'pointer',
            opacity: !templateName.trim() ? 0.5 : 1,
          }}
        >
          Register Template
        </button>
      </div>

      <div
        style={{
          backgroundColor: '#2a2a3e',
          border: '1px solid #45475a',
          borderRadius: 8,
          padding: 14,
          marginBottom: 12,
        }}
      >
        <div style={{ fontSize: 11, fontWeight: 600, color: '#a6adc8', marginBottom: 10, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
          Compare Screenshot Against Template
        </div>
        <select
          value={compareTemplateId}
          onChange={(e) => setCompareTemplateId(e.target.value)}
          style={{
            width: '100%',
            backgroundColor: '#1e1e2e',
            border: '1px solid #45475a',
            borderRadius: 6,
            padding: '8px 12px',
            fontSize: 11,
            color: '#cdd6f4',
            outline: 'none',
            marginBottom: 8,
            fontFamily: 'inherit',
          }}
        >
          <option value="">Select a template...</option>
          {templates.map((tpl) => (
            <option key={tpl.id} value={tpl.id}>
              {tpl.name}
            </option>
          ))}
        </select>
        <button
          onClick={handleCompareTemplate}
          disabled={loading || !compareTemplateId || !imageDescription.trim()}
          style={{
            width: '100%',
            padding: '9px 0',
            backgroundColor: loading ? '#45475a' : '#f9e2af',
            color: '#1e1e2e',
            border: 'none',
            borderRadius: 6,
            fontSize: 12,
            fontWeight: 600,
            cursor: loading || !compareTemplateId ? 'not-allowed' : 'pointer',
            opacity: loading || !compareTemplateId || !imageDescription.trim() ? 0.5 : 1,
          }}
        >
          {loading ? 'Comparing...' : 'Compare Against Template'}
        </button>

        {compareResult && (
          <div
            style={{
              marginTop: 12,
              backgroundColor: '#1e1e2e',
              border: '1px solid #45475a',
              borderRadius: 6,
              padding: 12,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
              <span style={{ fontSize: 11, fontWeight: 600, color: '#cdd6f4' }}>
                vs {compareResult.templateName}
              </span>
              <span
                style={{
                  fontSize: 16,
                  fontWeight: 'bold',
                  color: getScoreColor(compareResult.matchScore),
                }}
              >
                {compareResult.matchScore}%
              </span>
            </div>
            {compareResult.deviations && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                {compareResult.deviations.map((d: any, i: number) => (
                  <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 10 }}>
                    <span
                      style={{
                        padding: '1px 6px',
                        borderRadius: 3,
                        backgroundColor: SEVERITY_BG[d.severity] || '#45475a',
                        color: SEVERITY_COLORS[d.severity] || '#a6adc8',
                        fontSize: 8,
                        fontWeight: 700,
                      }}
                    >
                      {d.severity}
                    </span>
                    <span style={{ color: '#cdd6f4' }}>{d.elementType}:</span>
                    <span style={{ color: '#a6adc8' }}>
                      Expected {d.expected}, Found {d.found}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      <div
        style={{
          backgroundColor: '#2a2a3e',
          border: '1px solid #45475a',
          borderRadius: 8,
          padding: 14,
        }}
      >
        <div style={{ fontSize: 11, fontWeight: 600, color: '#a6adc8', marginBottom: 10, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
          Registered Templates ({templates.length})
        </div>
        {templates.length === 0 ? (
          <div style={{ fontSize: 10, color: '#585b70', textAlign: 'center', padding: '20px 0' }}>
            No templates registered yet. Create one above.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {templates.map((tpl) => (
              <div
                key={tpl.id}
                style={{
                  backgroundColor: '#1e1e2e',
                  border: '1px solid #45475a',
                  borderRadius: 6,
                  padding: '10px 12px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <span style={{ fontSize: 11, fontWeight: 600, color: '#cdd6f4' }}>{tpl.name}</span>
                  <span style={{ fontSize: 9, color: '#585b70' }}>
                    {new Date(tpl.createdAt).toLocaleDateString()}
                  </span>
                </div>
                {tpl.description && (
                  <div style={{ fontSize: 10, color: '#a6adc8', marginTop: 4 }}>{tpl.description}</div>
                )}
                <div style={{ display: 'flex', gap: 6, marginTop: 6 }}>
                  {tpl.expectedElements.map((el) => (
                    <span
                      key={el}
                      style={{
                        padding: '1px 6px',
                        borderRadius: 3,
                        backgroundColor: `${ELEMENT_TYPE_COLORS[el] || '#89b4fa'}20`,
                        color: ELEMENT_TYPE_COLORS[el] || '#89b4fa',
                        fontSize: 8,
                        fontWeight: 700,
                      }}
                    >
                      {el}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );

  const renderHistoryTab = () => (
    <div style={{ overflowY: 'auto', height: '100%', padding: '12px 16px' }}>
      {renderStatsBar()}

      {results.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '40px 0', color: '#585b70', fontSize: 11 }}>
          No analysis history yet. Run an analysis to see results here.
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {results.map((result) => (
            <div
              key={result.id}
              style={{
                backgroundColor: '#2a2a3e',
                border: '1px solid #45475a',
                borderRadius: 8,
                padding: 12,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ fontSize: 11, fontWeight: 600, color: '#cdd6f4' }}>
                    {result.imageDescription.slice(0, 60)}{result.imageDescription.length > 60 ? '...' : ''}
                  </span>
                </div>
                <span style={{ fontSize: 9, color: '#585b70' }}>
                  {new Date(result.timestamp).toLocaleString()}
                </span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                  <span style={{ fontSize: 9, color: '#a6adc8' }}>Comp:</span>
                  <span style={{ fontSize: 10, fontWeight: 600, color: getScoreColor(result.compositionScore) }}>
                    {result.compositionScore}
                  </span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                  <span style={{ fontSize: 9, color: '#a6adc8' }}>A11y:</span>
                  <span style={{ fontSize: 10, fontWeight: 600, color: getScoreColor(result.accessibilityScore) }}>
                    {result.accessibilityScore}
                  </span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                  <span style={{ fontSize: 9, color: '#a6adc8' }}>Findings:</span>
                  <span style={{ fontSize: 10, fontWeight: 600, color: '#cdd6f4' }}>
                    {result.findings.length}
                  </span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                  <span style={{ fontSize: 9, color: '#a6adc8' }}>Elements:</span>
                  <span style={{ fontSize: 10, fontWeight: 600, color: '#cdd6f4' }}>
                    {result.uiElements.length}
                  </span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginLeft: 'auto' }}>
                  <span style={{ fontSize: 9, color: '#585b70' }}>{result.durationMs}ms</span>
                </div>
              </div>
              <div style={{ display: 'flex', gap: 4, marginTop: 6 }}>
                {(['INFO', 'WARNING', 'ERROR', 'CRITICAL'] as VisionSeverity[]).map((sev) => {
                  const count = result.findings.filter((f) => f.severity === sev).length;
                  if (count === 0) return null;
                  return (
                    <span
                      key={sev}
                      style={{
                        padding: '1px 6px',
                        borderRadius: 3,
                        backgroundColor: SEVERITY_BG[sev],
                        color: SEVERITY_COLORS[sev],
                        fontSize: 8,
                        fontWeight: 700,
                      }}
                    >
                      {sev}: {count}
                    </span>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', backgroundColor: '#1e1e2e' }}>
      <div style={{ display: 'flex', borderBottom: '1px solid #45475a', padding: '0 16px', gap: 4 }}>
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            style={{
              padding: '10px 18px',
              backgroundColor: 'transparent',
              color: activeTab === tab.key ? '#89b4fa' : '#a6adc8',
              border: 'none',
              borderBottom: `2px solid ${activeTab === tab.key ? '#89b4fa' : 'transparent'}`,
              fontSize: 11,
              fontWeight: activeTab === tab.key ? 600 : 400,
              cursor: 'pointer',
              transition: 'all 0.15s',
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <div style={{ flex: 1, overflow: 'hidden' }}>
        {activeTab === 'analyze' && renderAnalyzeTab()}
        {activeTab === 'templates' && renderTemplatesTab()}
        {activeTab === 'history' && renderHistoryTab()}
      </div>
    </div>
  );
};

export default GameVisionPanel;