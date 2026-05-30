"use client";

import { useState, useEffect, useCallback } from "react";

const API_BASE = "http://localhost:8000/api/agent";

interface SubsystemStats {
  total_templates: number;
  total_assemblies: number;
  active_templates: number;
  total_categories: number;
  [key: string]: any;
}

export default function PromptLibraryPanel() {
  const [stats, setStats] = useState<SubsystemStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");

  const [templateName, setTemplateName] = useState("");
  const [templateCategory, setTemplateCategory] = useState("system");
  const [templateContent, setTemplateContent] = useState("");
  const [templateVariables, setTemplateVariables] = useState("");

  const [assemblyNames, setAssemblyNames] = useState("");
  const [assemblyVars, setAssemblyVars] = useState("");

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/prompt-library/stats`);
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

  const handleCreate = async () => {
    if (!templateName.trim() || !templateContent.trim()) {
      showMessage("Name and content are required");
      return;
    }
    let parsedVars: Record<string, any> = {};
    if (templateVariables.trim()) {
      try {
        parsedVars = JSON.parse(templateVariables);
      } catch {
        showMessage("Variables must be valid JSON");
        return;
      }
    }
    try {
      const res = await fetch(`${API_BASE}/prompt-library/create`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: templateName.trim(),
          category: templateCategory,
          content: templateContent.trim(),
          variables: parsedVars,
        }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(`Error: ${data.error}`);
      } else {
        showMessage("Prompt template created successfully");
        setTemplateName("");
        setTemplateContent("");
        setTemplateVariables("");
        fetchStats();
      }
    } catch {
      showMessage("Failed to create template");
    }
  };

  const handleAssemble = async () => {
    if (!assemblyNames.trim()) {
      showMessage("Template names are required");
      return;
    }
    let parsedVars: Record<string, any> = {};
    if (assemblyVars.trim()) {
      try {
        parsedVars = JSON.parse(assemblyVars);
      } catch {
        showMessage("Variables must be valid JSON");
        return;
      }
    }
    try {
      const res = await fetch(`${API_BASE}/prompt-library/assemble`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          template_names: assemblyNames.split(",").map((t) => t.trim()).filter(Boolean),
          variables: parsedVars,
        }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(`Error: ${data.error}`);
      } else {
        showMessage("Prompt assembled successfully");
        setAssemblyNames("");
        setAssemblyVars("");
        fetchStats();
      }
    } catch {
      showMessage("Failed to assemble prompt");
    }
  };

  return (
    <div style={{ padding: "1.5rem", color: "#e0e0e0" }}>
      <h2 style={{ fontSize: "1.5rem", fontWeight: 700, marginBottom: "1rem", color: "#ffffff" }}>
        Prompt Library 📝
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
                    <div style={{ fontSize: "1.2rem", fontWeight: 700, color: "#e94560" }}>
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
              <h4 style={{ fontSize: "0.8rem", color: "#aaa", marginBottom: "0.5rem" }}>Create Prompt Template</h4>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                <div style={{ display: "flex", gap: "0.5rem" }}>
                  <input
                    type="text"
                    placeholder="Template Name"
                    value={templateName}
                    onChange={(e) => setTemplateName(e.target.value)}
                    style={{
                      flex: "1", padding: "0.5rem", borderRadius: "0.375rem",
                      border: "1px solid #2a2a4a", background: "#0d0d1a", color: "#e0e0e0",
                      fontSize: "0.8rem"
                    }}
                  />
                  <select
                    value={templateCategory}
                    onChange={(e) => setTemplateCategory(e.target.value)}
                    style={{
                      flex: "1", padding: "0.5rem", borderRadius: "0.375rem",
                      border: "1px solid #2a2a4a", background: "#0d0d1a", color: "#e0e0e0",
                      fontSize: "0.8rem"
                    }}
                  >
                    <option value="system">System</option>
                    <option value="user">User</option>
                    <option value="assistant">Assistant</option>
                    <option value="tool">Tool</option>
                    <option value="function">Function</option>
                  </select>
                </div>
                <textarea
                  placeholder="Template Content"
                  value={templateContent}
                  onChange={(e) => setTemplateContent(e.target.value)}
                  rows={3}
                  style={{
                    padding: "0.5rem", borderRadius: "0.375rem",
                    border: "1px solid #2a2a4a", background: "#0d0d1a", color: "#e0e0e0",
                    fontSize: "0.8rem", resize: "vertical"
                  }}
                />
                <input
                  type="text"
                  placeholder="Variables (JSON)"
                  value={templateVariables}
                  onChange={(e) => setTemplateVariables(e.target.value)}
                  style={{
                    padding: "0.5rem", borderRadius: "0.375rem",
                    border: "1px solid #2a2a4a", background: "#0d0d1a", color: "#e0e0e0",
                    fontSize: "0.8rem"
                  }}
                />
                <button
                  onClick={handleCreate}
                  style={{
                    padding: "0.5rem 1rem", borderRadius: "0.375rem",
                    border: "none", background: "#e94560", color: "#fff",
                    cursor: "pointer", fontSize: "0.8rem", fontWeight: 600,
                    alignSelf: "flex-start"
                  }}
                >
                  Create Template
                </button>
              </div>
            </div>

            <div style={{
              background: "#1a1a2e", borderRadius: "0.5rem", padding: "0.75rem",
              border: "1px solid #2a2a4a"
            }}>
              <h4 style={{ fontSize: "0.8rem", color: "#aaa", marginBottom: "0.5rem" }}>Assemble Prompt</h4>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                <input
                  type="text"
                  placeholder="Template Names (comma-separated)"
                  value={assemblyNames}
                  onChange={(e) => setAssemblyNames(e.target.value)}
                  style={{
                    padding: "0.5rem", borderRadius: "0.375rem",
                    border: "1px solid #2a2a4a", background: "#0d0d1a", color: "#e0e0e0",
                    fontSize: "0.8rem"
                  }}
                />
                <input
                  type="text"
                  placeholder="Variables (JSON)"
                  value={assemblyVars}
                  onChange={(e) => setAssemblyVars(e.target.value)}
                  style={{
                    padding: "0.5rem", borderRadius: "0.375rem",
                    border: "1px solid #2a2a4a", background: "#0d0d1a", color: "#e0e0e0",
                    fontSize: "0.8rem"
                  }}
                />
                <button
                  onClick={handleAssemble}
                  style={{
                    padding: "0.5rem 1rem", borderRadius: "0.375rem",
                    border: "none", background: "#e94560", color: "#fff",
                    cursor: "pointer", fontSize: "0.8rem", fontWeight: 600,
                    alignSelf: "flex-start"
                  }}
                >
                  Assemble Prompt
                </button>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}