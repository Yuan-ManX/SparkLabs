"use client";

import { useState, useEffect, useCallback } from "react";
import { API_BASE as API_ROOT } from "../utils/api";

const API_BASE = `${API_ROOT}/agent`;

interface SubsystemStats {
  total_documents: number;
  total_bindings: number;
  active_documents: number;
}

export default function ContextWeaverPanel() {
  const [stats, setStats] = useState<SubsystemStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");

  const [docName, setDocName] = useState("");
  const [docContent, setDocContent] = useState("");
  const [docType, setDocType] = useState("markdown");
  const [weaveQuery, setWeaveQuery] = useState("");
  const [weaveStrategy, setWeaveStrategy] = useState("semantic");

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/context-weaver/stats`);
      const data = await res.json();
      if (!data.error) setStats(data);
      else setStats(null);
    } catch {
      setStats(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 15000);
    return () => clearInterval(interval);
  }, [fetchStats]);

  const showMessage = (msg: string) => {
    setMessage(msg);
    setTimeout(() => setMessage(""), 3000);
  };

  const handleCreateDocument = async () => {
    if (!docName.trim() || !docContent.trim()) {
      showMessage("Name and content are required");
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/context-weaver/create-document`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: docName,
          content: docContent,
          doc_type: docType,
        }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(`Error: ${data.error}`);
      } else {
        showMessage("Document created successfully");
        setDocName("");
        setDocContent("");
        fetchStats();
      }
    } catch {
      showMessage("Failed to create document");
    }
  };

  const handleWeaveContext = async () => {
    if (!weaveQuery.trim()) {
      showMessage("Query is required");
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/context-weaver/weave-context`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: weaveQuery,
          strategy: weaveStrategy,
        }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(`Error: ${data.error}`);
      } else {
        showMessage("Context woven successfully");
        setWeaveQuery("");
      }
    } catch {
      showMessage("Failed to weave context");
    }
  };

  return (
    <div style={{ padding: "1.5rem", color: "#e0e0e0" }}>
      <h2 style={{ fontSize: "1.5rem", fontWeight: 700, marginBottom: "1rem", color: "#ffffff" }}>
        Context Weave 🕸️
      </h2>
      {message && (
        <div style={{
          background: "#1b5e20", color: "#a5d6a7", padding: "0.5rem 1rem",
          borderRadius: "0.5rem", marginBottom: "1rem", fontSize: "0.875rem"
        }}>
          {message}
        </div>
      )}
      {loading ? (
        <div style={{ color: "#888", fontSize: "0.875rem" }}>Loading...</div>
      ) : (
        <>
          <div style={{
            background: "#16213e", borderRadius: "0.75rem", padding: "1rem",
            marginBottom: "1rem", border: "1px solid #2a2a4a"
          }}>
            <h3 style={{ fontSize: "0.875rem", color: "#888", marginBottom: "0.75rem", textTransform: "uppercase" }}>
              Statistics
            </h3>
            {stats ? (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))", gap: "0.75rem" }}>
                {Object.entries(stats).map(([key, value]) => (
                  <div key={key} style={{
                    background: "#1a1a2e", borderRadius: "0.5rem", padding: "0.75rem",
                    border: "1px solid #2a2a4a"
                  }}>
                    <div style={{ fontSize: "0.7rem", color: "#666", textTransform: "uppercase" }}>{key}</div>
                    <div style={{ fontSize: "1.2rem", fontWeight: 700, color: "#7c4dff" }}>
                      {typeof value === "number" ? value.toLocaleString() : String(value)}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ color: "#ff6b6b", fontSize: "0.875rem" }}>Subsystem not available</div>
            )}
          </div>

          <div style={{
            background: "#16213e", borderRadius: "0.75rem", padding: "1rem",
            marginBottom: "1rem", border: "1px solid #2a2a4a"
          }}>
            <h3 style={{ fontSize: "0.875rem", color: "#888", marginBottom: "0.75rem", textTransform: "uppercase" }}>
              Actions
            </h3>

            <div style={{
              background: "#1a1a2e", borderRadius: "0.5rem", padding: "0.75rem",
              marginBottom: "0.75rem", border: "1px solid #2a2a4a"
            }}>
              <h4 style={{ fontSize: "0.8rem", color: "#aaa", marginBottom: "0.5rem" }}>Create Document</h4>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                <input
                  type="text"
                  placeholder="Document name"
                  value={docName}
                  onChange={(e) => setDocName(e.target.value)}
                  style={{
                    padding: "0.5rem", borderRadius: "0.375rem",
                    border: "1px solid #2a2a4a", background: "#0d0d0d", color: "#e0e0e0",
                    fontSize: "0.8rem"
                  }}
                />
                <textarea
                  placeholder="Document content"
                  value={docContent}
                  onChange={(e) => setDocContent(e.target.value)}
                  rows={3}
                  style={{
                    padding: "0.5rem", borderRadius: "0.375rem",
                    border: "1px solid #2a2a4a", background: "#0d0d0d", color: "#e0e0e0",
                    fontSize: "0.8rem", resize: "vertical"
                  }}
                />
                <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                  <select
                    value={docType}
                    onChange={(e) => setDocType(e.target.value)}
                    style={{
                      padding: "0.5rem", borderRadius: "0.375rem",
                      border: "1px solid #2a2a4a", background: "#0d0d0d", color: "#e0e0e0",
                      fontSize: "0.8rem"
                    }}
                  >
                    <option value="markdown">Markdown</option>
                    <option value="code">Code</option>
                    <option value="text">Plain Text</option>
                    <option value="json">JSON</option>
                  </select>
                  <button
                    onClick={handleCreateDocument}
                    style={{
                      padding: "0.5rem 1rem", borderRadius: "0.375rem",
                      border: "none", background: "#7c4dff", color: "#fff",
                      cursor: "pointer", fontSize: "0.8rem", fontWeight: 600
                    }}
                  >
                    Create
                  </button>
                </div>
              </div>
            </div>

            <div style={{
              background: "#1a1a2e", borderRadius: "0.5rem", padding: "0.75rem",
              border: "1px solid #2a2a4a"
            }}>
              <h4 style={{ fontSize: "0.8rem", color: "#aaa", marginBottom: "0.5rem" }}>Weave Context</h4>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                <textarea
                  placeholder="Enter query to weave context..."
                  value={weaveQuery}
                  onChange={(e) => setWeaveQuery(e.target.value)}
                  rows={3}
                  style={{
                    padding: "0.5rem", borderRadius: "0.375rem",
                    border: "1px solid #2a2a4a", background: "#0d0d0d", color: "#e0e0e0",
                    fontSize: "0.8rem", resize: "vertical"
                  }}
                />
                <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                  <select
                    value={weaveStrategy}
                    onChange={(e) => setWeaveStrategy(e.target.value)}
                    style={{
                      padding: "0.5rem", borderRadius: "0.375rem",
                      border: "1px solid #2a2a4a", background: "#0d0d0d", color: "#e0e0e0",
                      fontSize: "0.8rem"
                    }}
                  >
                    <option value="semantic">Semantic</option>
                    <option value="keyword">Keyword</option>
                    <option value="hybrid">Hybrid</option>
                    <option value="graph">Graph</option>
                  </select>
                  <button
                    onClick={handleWeaveContext}
                    style={{
                      padding: "0.5rem 1rem", borderRadius: "0.375rem",
                      border: "none", background: "#7c4dff", color: "#fff",
                      cursor: "pointer", fontSize: "0.8rem", fontWeight: 600
                    }}
                  >
                    Weave
                  </button>
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}