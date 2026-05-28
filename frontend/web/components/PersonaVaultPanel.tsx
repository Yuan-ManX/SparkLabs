"use client";

import { useState, useEffect, useCallback } from "react";

const API_BASE = "http://localhost:8000/api/agent";

interface SubsystemStats {
  total_personas: number;
  active_personas: number;
  total_packs: number;
  total_swaps: number;
}

export default function PersonaVaultPanel() {
  const [stats, setStats] = useState<SubsystemStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");

  const [personaName, setPersonaName] = useState("");
  const [personaRole, setPersonaRole] = useState("");
  const [personaTone, setPersonaTone] = useState("professional");
  const [personaPrompt, setPersonaPrompt] = useState("");
  const [exportPersonaId, setExportPersonaId] = useState("");

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/persona-vault/stats`);
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

  const handleCreatePersona = async () => {
    if (!personaName.trim() || !personaRole.trim()) {
      showMessage("Name and role are required");
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/persona-vault/create-persona`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: personaName,
          role: personaRole,
          tone: personaTone,
          system_prompt: personaPrompt,
        }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(`Error: ${data.error}`);
      } else {
        showMessage("Persona created successfully");
        setPersonaName("");
        setPersonaRole("");
        setPersonaPrompt("");
        fetchStats();
      }
    } catch {
      showMessage("Failed to create persona");
    }
  };

  const handleExportPersona = async () => {
    if (!exportPersonaId.trim()) {
      showMessage("Persona ID is required");
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/persona-vault/export-persona`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          persona_id: exportPersonaId,
          export_format: "json",
        }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(`Error: ${data.error}`);
      } else {
        showMessage("Persona exported successfully");
        setExportPersonaId("");
      }
    } catch {
      showMessage("Failed to export persona");
    }
  };

  return (
    <div style={{ padding: "1.5rem", color: "#e0e0e0" }}>
      <h2 style={{ fontSize: "1.5rem", fontWeight: 700, marginBottom: "1rem", color: "#ffffff" }}>
        Persona Vault 🎭
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
              <h4 style={{ fontSize: "0.8rem", color: "#aaa", marginBottom: "0.5rem" }}>Create Persona</h4>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                <div style={{ display: "flex", gap: "0.5rem" }}>
                  <input
                    type="text"
                    placeholder="Name"
                    value={personaName}
                    onChange={(e) => setPersonaName(e.target.value)}
                    style={{
                      flex: "1", padding: "0.5rem", borderRadius: "0.375rem",
                      border: "1px solid #2a2a4a", background: "#0d0d1a", color: "#e0e0e0",
                      fontSize: "0.8rem"
                    }}
                  />
                  <input
                    type="text"
                    placeholder="Role"
                    value={personaRole}
                    onChange={(e) => setPersonaRole(e.target.value)}
                    style={{
                      flex: "1", padding: "0.5rem", borderRadius: "0.375rem",
                      border: "1px solid #2a2a4a", background: "#0d0d1a", color: "#e0e0e0",
                      fontSize: "0.8rem"
                    }}
                  />
                </div>
                <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                  <select
                    value={personaTone}
                    onChange={(e) => setPersonaTone(e.target.value)}
                    style={{
                      flex: "1", padding: "0.5rem", borderRadius: "0.375rem",
                      border: "1px solid #2a2a4a", background: "#0d0d1a", color: "#e0e0e0",
                      fontSize: "0.8rem"
                    }}
                  >
                    <option value="professional">Professional</option>
                    <option value="casual">Casual</option>
                    <option value="creative">Creative</option>
                    <option value="technical">Technical</option>
                  </select>
                </div>
                <textarea
                  placeholder="System prompt (optional)"
                  value={personaPrompt}
                  onChange={(e) => setPersonaPrompt(e.target.value)}
                  rows={3}
                  style={{
                    padding: "0.5rem", borderRadius: "0.375rem",
                    border: "1px solid #2a2a4a", background: "#0d0d1a", color: "#e0e0e0",
                    fontSize: "0.8rem", resize: "vertical"
                  }}
                />
                <button
                  onClick={handleCreatePersona}
                  style={{
                    padding: "0.5rem 1rem", borderRadius: "0.375rem",
                    border: "none", background: "#7c4dff", color: "#fff",
                    cursor: "pointer", fontSize: "0.8rem", fontWeight: 600,
                    alignSelf: "flex-start"
                  }}
                >
                  Create Persona
                </button>
              </div>
            </div>

            <div style={{
              background: "#1a1a2e", borderRadius: "0.5rem", padding: "0.75rem",
              border: "1px solid #2a2a4a"
            }}>
              <h4 style={{ fontSize: "0.8rem", color: "#aaa", marginBottom: "0.5rem" }}>Export Persona</h4>
              <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                <input
                  type="text"
                  placeholder="Persona ID"
                  value={exportPersonaId}
                  onChange={(e) => setExportPersonaId(e.target.value)}
                  style={{
                    flex: "1", padding: "0.5rem", borderRadius: "0.375rem",
                    border: "1px solid #2a2a4a", background: "#0d0d1a", color: "#e0e0e0",
                    fontSize: "0.8rem"
                  }}
                />
                <button
                  onClick={handleExportPersona}
                  style={{
                    padding: "0.5rem 1rem", borderRadius: "0.375rem",
                    border: "none", background: "#7c4dff", color: "#fff",
                    cursor: "pointer", fontSize: "0.8rem", fontWeight: 600
                  }}
                >
                  Export
                </button>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}