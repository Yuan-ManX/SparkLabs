"use client";

import { useState, useEffect, useCallback } from "react";

const API_BASE = "http://localhost:8000/api/agent";

interface SubsystemStats {
  total_keys: number;
  total_languages: number;
  total_translations: number;
  pending_translations: number;
  [key: string]: any;
}

export default function LocalizationHubPanel() {
  const [stats, setStats] = useState<SubsystemStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");

  const [addKey, setAddKey] = useState("");
  const [addText, setAddText] = useState("");
  const [addLanguage, setAddLanguage] = useState("en");

  const [translateKey, setTranslateKey] = useState("");
  const [translateLanguage, setTranslateLanguage] = useState("zh");
  const [translateVars, setTranslateVars] = useState("");

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/localization-hub/stats`);
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

  const handleAdd = async () => {
    if (!addKey.trim() || !addText.trim()) {
      showMessage("Key and text are required");
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/localization-hub/add`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          key: addKey.trim(),
          text: addText.trim(),
          language: addLanguage,
        }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(`Error: ${data.error}`);
      } else {
        showMessage("Localization entry added successfully");
        setAddKey("");
        setAddText("");
        fetchStats();
      }
    } catch {
      showMessage("Failed to add entry");
    }
  };

  const handleTranslate = async () => {
    if (!translateKey.trim()) {
      showMessage("Key is required");
      return;
    }
    let parsedVars: Record<string, any> = {};
    if (translateVars.trim()) {
      try {
        parsedVars = JSON.parse(translateVars);
      } catch {
        showMessage("Variables must be valid JSON");
        return;
      }
    }
    try {
      const res = await fetch(`${API_BASE}/localization-hub/translate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          key: translateKey.trim(),
          language: translateLanguage,
          variables: parsedVars,
        }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(`Error: ${data.error}`);
      } else {
        showMessage("Translation retrieved successfully");
        setTranslateKey("");
        setTranslateVars("");
        fetchStats();
      }
    } catch {
      showMessage("Failed to translate");
    }
  };

  return (
    <div style={{ padding: "1.5rem", color: "#e0e0e0" }}>
      <h2 style={{ fontSize: "1.5rem", fontWeight: 700, marginBottom: "1rem", color: "#ffffff" }}>
        Localization Hub 🌍
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
              <h4 style={{ fontSize: "0.8rem", color: "#aaa", marginBottom: "0.5rem" }}>Add Localization Entry</h4>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                <div style={{ display: "flex", gap: "0.5rem" }}>
                  <input
                    type="text"
                    placeholder="Key"
                    value={addKey}
                    onChange={(e) => setAddKey(e.target.value)}
                    style={{
                      flex: "1", padding: "0.5rem", borderRadius: "0.375rem",
                      border: "1px solid #2a2a4a", background: "#0d0d1a", color: "#e0e0e0",
                      fontSize: "0.8rem"
                    }}
                  />
                  <select
                    value={addLanguage}
                    onChange={(e) => setAddLanguage(e.target.value)}
                    style={{
                      flex: "1", padding: "0.5rem", borderRadius: "0.375rem",
                      border: "1px solid #2a2a4a", background: "#0d0d1a", color: "#e0e0e0",
                      fontSize: "0.8rem"
                    }}
                  >
                    <option value="en">English</option>
                    <option value="zh">Chinese</option>
                    <option value="ja">Japanese</option>
                    <option value="ko">Korean</option>
                    <option value="es">Spanish</option>
                    <option value="fr">French</option>
                    <option value="de">German</option>
                    <option value="pt">Portuguese</option>
                  </select>
                </div>
                <textarea
                  placeholder="Text"
                  value={addText}
                  onChange={(e) => setAddText(e.target.value)}
                  rows={3}
                  style={{
                    padding: "0.5rem", borderRadius: "0.375rem",
                    border: "1px solid #2a2a4a", background: "#0d0d1a", color: "#e0e0e0",
                    fontSize: "0.8rem", resize: "vertical"
                  }}
                />
                <button
                  onClick={handleAdd}
                  style={{
                    padding: "0.5rem 1rem", borderRadius: "0.375rem",
                    border: "none", background: "#e94560", color: "#fff",
                    cursor: "pointer", fontSize: "0.8rem", fontWeight: 600,
                    alignSelf: "flex-start"
                  }}
                >
                  Add Entry
                </button>
              </div>
            </div>

            <div style={{
              background: "#1a1a2e", borderRadius: "0.5rem", padding: "0.75rem",
              border: "1px solid #2a2a4a"
            }}>
              <h4 style={{ fontSize: "0.8rem", color: "#aaa", marginBottom: "0.5rem" }}>Translate Key</h4>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                <input
                  type="text"
                  placeholder="Key"
                  value={translateKey}
                  onChange={(e) => setTranslateKey(e.target.value)}
                  style={{
                    padding: "0.5rem", borderRadius: "0.375rem",
                    border: "1px solid #2a2a4a", background: "#0d0d1a", color: "#e0e0e0",
                    fontSize: "0.8rem"
                  }}
                />
                <div style={{ display: "flex", gap: "0.5rem" }}>
                  <select
                    value={translateLanguage}
                    onChange={(e) => setTranslateLanguage(e.target.value)}
                    style={{
                      flex: "1", padding: "0.5rem", borderRadius: "0.375rem",
                      border: "1px solid #2a2a4a", background: "#0d0d1a", color: "#e0e0e0",
                      fontSize: "0.8rem"
                    }}
                  >
                    <option value="zh">Chinese</option>
                    <option value="ja">Japanese</option>
                    <option value="ko">Korean</option>
                    <option value="es">Spanish</option>
                    <option value="fr">French</option>
                    <option value="de">German</option>
                    <option value="pt">Portuguese</option>
                    <option value="en">English</option>
                  </select>
                  <input
                    type="text"
                    placeholder="Variables (JSON)"
                    value={translateVars}
                    onChange={(e) => setTranslateVars(e.target.value)}
                    style={{
                      flex: "1", padding: "0.5rem", borderRadius: "0.375rem",
                      border: "1px solid #2a2a4a", background: "#0d0d1a", color: "#e0e0e0",
                      fontSize: "0.8rem"
                    }}
                  />
                </div>
                <button
                  onClick={handleTranslate}
                  style={{
                    padding: "0.5rem 1rem", borderRadius: "0.375rem",
                    border: "none", background: "#e94560", color: "#fff",
                    cursor: "pointer", fontSize: "0.8rem", fontWeight: 600,
                    alignSelf: "flex-start"
                  }}
                >
                  Translate
                </button>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}