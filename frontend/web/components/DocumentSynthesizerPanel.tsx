import React, { useState, useEffect, useCallback } from 'react';

type TabId = 'templates' | 'synthesize' | 'documents';

interface Template {
  id: string;
  name: string;
  doc_type: string;
  format: string;
  created_at: number;
}

interface SynthesizedDoc {
  id: string;
  template_id: string;
  title: string;
  doc_type: string;
  format: string;
  status: string;
  created_at: number;
}

interface RenderedDoc {
  id: string;
  document_id: string;
  title: string;
  format: string;
  rendered_content: string;
  rendered_at: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const DocumentSynthesizerPanel: React.FC = () => {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [documents, setDocuments] = useState<SynthesizedDoc[]>([]);
  const [renderedDocs, setRenderedDocs] = useState<RenderedDoc[]>([]);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('templates');

  const [tmplName, setTmplName] = useState('');
  const [tmplDocType, setTmplDocType] = useState('report');
  const [tmplFormat, setTmplFormat] = useState('markdown');

  const [synthTemplateId, setSynthTemplateId] = useState('');
  const [synthTitle, setSynthTitle] = useState('');
  const [synthContentData, setSynthContentData] = useState('{"summary":"Sample content","sections":[{"heading":"Overview","body":"This is a test document."}]}');

  const [renderDocId, setRenderDocId] = useState('');
  const [renderFormat, setRenderFormat] = useState('pdf');

  const apiBase = 'http://localhost:8000/api/agent';

  const defaultTemplates: Template[] = [
    { id: uid(), name: 'Weekly Report', doc_type: 'report', format: 'markdown', created_at: Date.now() - 86400000 },
    { id: uid(), name: 'API Documentation', doc_type: 'documentation', format: 'html', created_at: Date.now() - 172800000 },
    { id: uid(), name: 'Meeting Notes', doc_type: 'notes', format: 'markdown', created_at: Date.now() - 259200000 },
    { id: uid(), name: 'Code Review Summary', doc_type: 'review', format: 'pdf', created_at: Date.now() - 345600000 },
  ];

  const defaultDocuments: SynthesizedDoc[] = [
    { id: uid(), template_id: 'tmpl-1', title: 'Sprint 42 Review', doc_type: 'report', format: 'markdown', status: 'completed', created_at: Date.now() - 3600000 },
    { id: uid(), template_id: 'tmpl-2', title: 'Agent API v2 Docs', doc_type: 'documentation', format: 'html', status: 'completed', created_at: Date.now() - 7200000 },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/document-synthesizer/stats`);
      const data = await res.json();
      if (data.templates) setTemplates(data.templates);
      if (data.documents) setDocuments(data.documents);
    } catch {
      // use defaults
    }
  }, []);

  useEffect(() => {
    setTemplates(defaultTemplates);
    setDocuments(defaultDocuments);
    fetchStats();
  }, [fetchStats]);

  const handleCreateTemplate = async () => {
    if (!tmplName.trim()) {
      showMessage('Template name is required', 'error');
      return;
    }
    try {
      await fetch(`${apiBase}/document-synthesizer/create-template`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: tmplName, doc_type: tmplDocType, format: tmplFormat }),
      });
      const newTmpl: Template = {
        id: uid(), name: tmplName, doc_type: tmplDocType, format: tmplFormat, created_at: Date.now(),
      };
      setTemplates(prev => [...prev, newTmpl]);
      setTmplName('');
      showMessage(`Template "${tmplName}" created`, 'success');
    } catch {
      const newTmpl: Template = {
        id: uid(), name: tmplName, doc_type: tmplDocType, format: tmplFormat, created_at: Date.now(),
      };
      setTemplates(prev => [...prev, newTmpl]);
      setTmplName('');
      showMessage(`Template "${tmplName}" created (offline fallback)`, 'info');
    }
  };

  const handleSynthesize = async () => {
    if (!synthTemplateId.trim() || !synthTitle.trim()) {
      showMessage('Template ID and title are required', 'error');
      return;
    }
    try {
      await fetch(`${apiBase}/document-synthesizer/synthesize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          template_id: synthTemplateId,
          title: synthTitle,
          content_data: synthContentData,
        }),
      });
      const newDoc: SynthesizedDoc = {
        id: uid(),
        template_id: synthTemplateId,
        title: synthTitle,
        doc_type: templates.find(t => t.id === synthTemplateId)?.doc_type || 'report',
        format: templates.find(t => t.id === synthTemplateId)?.format || 'markdown',
        status: 'completed',
        created_at: Date.now(),
      };
      setDocuments(prev => [newDoc, ...prev]);
      setSynthTitle('');
      showMessage(`Document "${synthTitle}" synthesized`, 'success');
    } catch {
      const newDoc: SynthesizedDoc = {
        id: uid(),
        template_id: synthTemplateId,
        title: synthTitle,
        doc_type: 'report',
        format: 'markdown',
        status: 'completed',
        created_at: Date.now(),
      };
      setDocuments(prev => [newDoc, ...prev]);
      setSynthTitle('');
      showMessage(`Document "${synthTitle}" synthesized (offline fallback)`, 'info');
    }
  };

  const handleRender = async () => {
    if (!renderDocId.trim()) {
      showMessage('Document ID is required', 'error');
      return;
    }
    try {
      const res = await fetch(`${apiBase}/document-synthesizer/render?document_id=${renderDocId}&format=${renderFormat}`);
      const data = await res.json();
      if (data) {
        setRenderedDocs(prev => [data, ...prev]);
      }
      showMessage(`Document rendered as ${renderFormat.toUpperCase()}`, 'success');
    } catch {
      const doc = documents.find(d => d.id === renderDocId);
      const rendered: RenderedDoc = {
        id: uid(),
        document_id: renderDocId,
        title: doc?.title || 'Untitled',
        format: renderFormat,
        rendered_content: `Rendered content for document ${renderDocId} in ${renderFormat} format.`,
        rendered_at: Date.now(),
      };
      setRenderedDocs(prev => [rendered, ...prev]);
      showMessage(`Document rendered as ${renderFormat.toUpperCase()} (offline fallback)`, 'info');
    }
  };

  const formatTime = (ts: number) => {
    const d = new Date(ts);
    return d.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  };

  const tabItems: { key: TabId; label: string; icon: string; count: number }[] = [
    { key: 'templates', label: 'Templates', icon: '\uD83D\uDCC4', count: templates.length },
    { key: 'synthesize', label: 'Synthesize', icon: '\u2699\uFE0F', count: documents.length },
    { key: 'documents', label: 'Documents', icon: '\uD83D\uDCC1', count: documents.length + renderedDocs.length },
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
          <span style={{ fontSize: 18 }}>{'\uD83D\uDCC4'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Document Synthesizer</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 10, color: '#888' }}>
            {templates.length} templates · {documents.length} documents
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
        {activeTab === 'templates' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{
              padding: 12, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\uD83D\uDCC4'} create-template
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Name</div>
                  <input value={tmplName} onChange={e => setTmplName(e.target.value)} placeholder="e.g. Weekly Report" style={{
                    padding: '6px 10px', fontSize: 11, width: 150,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Doc Type</div>
                  <select value={tmplDocType} onChange={e => setTmplDocType(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }}>
                    <option value="report">Report</option>
                    <option value="documentation">Documentation</option>
                    <option value="notes">Notes</option>
                    <option value="review">Review</option>
                    <option value="proposal">Proposal</option>
                  </select>
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Format</div>
                  <select value={tmplFormat} onChange={e => setTmplFormat(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }}>
                    <option value="markdown">Markdown</option>
                    <option value="html">HTML</option>
                    <option value="pdf">PDF</option>
                    <option value="docx">DOCX</option>
                  </select>
                </div>
                <button onClick={handleCreateTemplate} style={{
                  padding: '6px 14px', backgroundColor: '#2d3a5a', color: '#74b9ff',
                  border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600,
                }}>Create</button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>
              {'\uD83D\uDCC4'} Templates <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({templates.length})</span>
            </div>
            {templates.map(tmpl => (
              <div key={tmpl.id} style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e', borderLeft: '3px solid #74b9ff',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <span style={{ fontWeight: 600, fontSize: 13, color: '#ccc' }}>{tmpl.name}</span>
                  <span style={{
                    fontSize: 9, padding: '2px 8px', borderRadius: 3,
                    backgroundColor: '#1a2a3a', color: '#74b9ff', fontWeight: 600,
                    textTransform: 'uppercase',
                  }}>{tmpl.format}</span>
                </div>
                <div style={{ display: 'flex', gap: 16, fontSize: 10, color: '#888' }}>
                  <span>Type: <span style={{ color: '#a29bfe', fontWeight: 600 }}>{tmpl.doc_type}</span></span>
                  <span>Created: <span style={{ color: '#aaa' }}>{formatTime(tmpl.created_at)}</span></span>
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'synthesize' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{
              padding: 12, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\u2699\uFE0F'} synthesize
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Template ID</div>
                  <input value={synthTemplateId} onChange={e => setSynthTemplateId(e.target.value)} placeholder="Select template" style={{
                    padding: '6px 10px', fontSize: 11, width: 130,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div style={{ flex: 1, minWidth: 200 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Title</div>
                  <input value={synthTitle} onChange={e => setSynthTitle(e.target.value)} placeholder="Document title..." style={{
                    padding: '6px 10px', fontSize: 11, width: '100%',
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <button onClick={handleSynthesize} style={{
                  padding: '6px 14px', backgroundColor: '#2d4a2d', color: '#6bcb77',
                  border: '1px solid #3d5a3d', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600,
                }}>Synthesize</button>
              </div>
              <div style={{ marginTop: 8 }}>
                <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Content Data (JSON)</div>
                <textarea value={synthContentData} onChange={e => setSynthContentData(e.target.value)} rows={4} style={{
                  padding: '8px 10px', fontSize: 11, width: '100%', resize: 'vertical',
                  backgroundColor: '#141428', color: '#ccc',
                  border: '1px solid #333', borderRadius: 4, outline: 'none',
                  fontFamily: 'monospace',
                }} />
              </div>
            </div>

            <div style={{
              padding: 10, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 11, fontWeight: 600, color: '#aaa', marginBottom: 6 }}>render</div>
              <div style={{ display: 'flex', gap: 6, alignItems: 'flex-end' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Document ID</div>
                  <input value={renderDocId} onChange={e => setRenderDocId(e.target.value)} placeholder="e.g. doc-1" style={{
                    padding: '6px 10px', fontSize: 11, width: '100%',
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Format</div>
                  <select value={renderFormat} onChange={e => setRenderFormat(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }}>
                    <option value="pdf">PDF</option>
                    <option value="html">HTML</option>
                    <option value="markdown">Markdown</option>
                    <option value="docx">DOCX</option>
                  </select>
                </div>
                <button onClick={handleRender} style={{
                  padding: '6px 14px', backgroundColor: '#4a3d2d', color: '#fdcb6e',
                  border: '1px solid #5a4d3d', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600,
                }}>Render</button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>
              {'\uD83D\uDCC1'} Synthesized Documents <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({documents.length})</span>
            </div>
            {documents.map(doc => (
              <div key={doc.id} style={{
                padding: 10, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e', borderLeft: '3px solid #6bcb77',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <span style={{ fontWeight: 600, fontSize: 12, color: '#ccc' }}>{doc.title}</span>
                  <span style={{
                    fontSize: 9, padding: '2px 8px', borderRadius: 3,
                    backgroundColor: '#1a3a1a', color: '#6bcb77', fontWeight: 600,
                    textTransform: 'uppercase',
                  }}>{doc.format}</span>
                </div>
                <div style={{ display: 'flex', gap: 16, fontSize: 10, color: '#888' }}>
                  <span>Type: <span style={{ color: '#74b9ff' }}>{doc.doc_type}</span></span>
                  <span>Status: <span style={{ color: '#fdcb6e' }}>{doc.status}</span></span>
                  <span>{formatTime(doc.created_at)}</span>
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'documents' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>
              {'\uD83D\uDCC1'} All Documents
            </div>
            {documents.map(doc => (
              <div key={doc.id} style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e', borderLeft: '3px solid #74b9ff',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                  <span style={{ fontWeight: 600, fontSize: 13, color: '#ccc' }}>{doc.title}</span>
                  <span style={{ fontSize: 10, color: '#888' }}>{doc.template_id}</span>
                </div>
                <div style={{ display: 'flex', gap: 16, fontSize: 10, color: '#888' }}>
                  <span>Type: <span style={{ color: '#74b9ff' }}>{doc.doc_type}</span></span>
                  <span>Format: <span style={{ color: '#a29bfe' }}>{doc.format}</span></span>
                  <span>Status: <span style={{ color: '#6bcb77' }}>{doc.status}</span></span>
                </div>
              </div>
            ))}
            {renderedDocs.length > 0 && (
              <>
                <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa', marginTop: 6 }}>
                  {'\uD83D\uDCC4'} Rendered Documents <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({renderedDocs.length})</span>
                </div>
                {renderedDocs.map(rd => (
                  <div key={rd.id} style={{
                    padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                    border: '1px solid #2a2a3e', borderLeft: '3px solid #fdcb6e',
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <span style={{ fontWeight: 600, fontSize: 12, color: '#ccc' }}>{rd.title}</span>
                      <span style={{
                        fontSize: 9, padding: '2px 8px', borderRadius: 3,
                        backgroundColor: '#3a3a1a', color: '#fdcb6e', fontWeight: 600,
                        textTransform: 'uppercase',
                      }}>{rd.format}</span>
                    </div>
                    <div style={{ fontSize: 10, color: '#888' }}>Document ID: {rd.document_id}</div>
                    <div style={{
                      padding: 8, backgroundColor: '#141428', borderRadius: 4, marginTop: 6,
                      fontSize: 10, color: '#aaa', fontStyle: 'italic',
                    }}>
                      {rd.rendered_content.substring(0, 100)}{rd.rendered_content.length > 100 ? '...' : ''}
                    </div>
                  </div>
                ))}
              </>
            )}
            {(documents.length === 0 && renderedDocs.length === 0) && (
              <div style={{
                textAlign: 'center', padding: 40, color: '#555',
                backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e',
              }}>
                <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\uD83D\uDCC1'}</span>
                No documents yet
              </div>
            )}
          </div>
        )}
      </div>

      <div style={{
        padding: '6px 12px', borderTop: '1px solid #2a2a3e',
        backgroundColor: '#141428', display: 'flex',
        alignItems: 'center', justifyContent: 'space-between',
        fontSize: 10, color: '#666',
      }}>
        <span>{'\uD83D\uDCC4'} {templates.length} templates · {documents.length} documents · {renderedDocs.length} rendered</span>
        <span>Connected</span>
      </div>
    </div>
  );
};

export default DocumentSynthesizerPanel;