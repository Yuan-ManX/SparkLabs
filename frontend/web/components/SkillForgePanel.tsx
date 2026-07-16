"use client";

import { useState, useEffect, useCallback } from "react";
import { API_BASE as API_ROOT } from "../utils/api";

const API_BASE = `${API_ROOT}/agent`;

interface SubsystemStats {
  total_skills: number;
  active_skills: number;
  executions: number;
  success_rate: number;
  [key: string]: any;
}

const CATEGORIES = [
  "GAME_LOGIC", "ASSET_GENERATION", "LEVEL_DESIGN", "UI_LAYOUT",
  "AI_BEHAVIOR", "ANIMATION", "PHYSICS", "AUDIO", "NETWORKING", "UTILITY"
] as const;

export default function SkillForgePanel() {
  const [stats, setStats] = useState<SubsystemStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");

  const [description, setDescription] = useState("");
  const [resultJson, setResultJson] = useState("");
  const [category, setCategory] = useState("UTILITY");
  const [tags, setTags] = useState("");

  const [skillId, setSkillId] = useState("");
  const [dryRun, setDryRun] = useState(false);

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/skill-forge/stats`);
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

  const handleCreateSkill = async () => {
    if (!description.trim()) {
      showMessage("Description is required");
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/skill-forge/create-skill`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          description: description.trim(),
          result_json: resultJson.trim() || "{}",
          category,
          tags: tags.trim() ? tags.split(",").map(t => t.trim()) : [],
        }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(`Error: ${data.error}`);
      } else {
        showMessage("Skill created successfully");
        setDescription("");
        setResultJson("");
        setTags("");
        fetchStats();
      }
    } catch {
      showMessage("Failed to create skill");
    }
  };

  const handleExecuteSkill = async () => {
    if (!skillId.trim()) {
      showMessage("Skill ID is required");
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/skill-forge/execute-skill`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          skill_id: skillId.trim(),
          dry_run: dryRun,
        }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(`Error: ${data.error}`);
      } else {
        showMessage(`Skill executed${dryRun ? " (dry run)" : ""} successfully`);
        setSkillId("");
        setDryRun(false);
        fetchStats();
      }
    } catch {
      showMessage("Failed to execute skill");
    }
  };

  return (
    <div style={{ padding: "1.5rem", color: "#e0e0e0" }}>
      <h2 style={{ fontSize: "1.5rem", fontWeight: 700, marginBottom: "1rem", color: "#ffffff" }}>
        Skill Forge ⚒️
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
              <h4 style={{ fontSize: "0.8rem", color: "#aaa", marginBottom: "0.5rem" }}>Create Skill</h4>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                <textarea
                  placeholder="Skill description"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={3}
                  style={{
                    padding: "0.5rem", borderRadius: "0.375rem",
                    border: "1px solid #2a2a4a", background: "#0d0d0d", color: "#e0e0e0",
                    fontSize: "0.8rem", resize: "vertical"
                  }}
                />
                <textarea
                  placeholder="Result JSON"
                  value={resultJson}
                  onChange={(e) => setResultJson(e.target.value)}
                  rows={2}
                  style={{
                    padding: "0.5rem", borderRadius: "0.375rem",
                    border: "1px solid #2a2a4a", background: "#0d0d0d", color: "#e0e0e0",
                    fontSize: "0.8rem", resize: "vertical"
                  }}
                />
                <div style={{ display: "flex", gap: "0.5rem" }}>
                  <select
                    value={category}
                    onChange={(e) => setCategory(e.target.value)}
                    style={{
                      flex: "1", padding: "0.5rem", borderRadius: "0.375rem",
                      border: "1px solid #2a2a4a", background: "#0d0d0d", color: "#e0e0e0",
                      fontSize: "0.8rem"
                    }}
                  >
                    {CATEGORIES.map((cat) => (
                      <option key={cat} value={cat}>{cat}</option>
                    ))}
                  </select>
                  <input
                    type="text"
                    placeholder="Tags (comma separated)"
                    value={tags}
                    onChange={(e) => setTags(e.target.value)}
                    style={{
                      flex: "1", padding: "0.5rem", borderRadius: "0.375rem",
                      border: "1px solid #2a2a4a", background: "#0d0d0d", color: "#e0e0e0",
                      fontSize: "0.8rem"
                    }}
                  />
                </div>
                <button
                  onClick={handleCreateSkill}
                  style={{
                    padding: "0.5rem 1rem", borderRadius: "0.375rem",
                    border: "none", background: "#e94560", color: "#fff",
                    cursor: "pointer", fontSize: "0.8rem", fontWeight: 600,
                    alignSelf: "flex-start"
                  }}
                >
                  Create Skill
                </button>
              </div>
            </div>

            <div style={{
              background: "#1a1a2e", borderRadius: "0.5rem", padding: "0.75rem",
              border: "1px solid #2a2a4a"
            }}>
              <h4 style={{ fontSize: "0.8rem", color: "#aaa", marginBottom: "0.5rem" }}>Execute Skill</h4>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                <input
                  type="text"
                  placeholder="Skill ID"
                  value={skillId}
                  onChange={(e) => setSkillId(e.target.value)}
                  style={{
                    padding: "0.5rem", borderRadius: "0.375rem",
                    border: "1px solid #2a2a4a", background: "#0d0d0d", color: "#e0e0e0",
                    fontSize: "0.8rem"
                  }}
                />
                <label style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "0.8rem", color: "#aaa", cursor: "pointer" }}>
                  <input
                    type="checkbox"
                    checked={dryRun}
                    onChange={(e) => setDryRun(e.target.checked)}
                    style={{ accentColor: "#e94560" }}
                  />
                  Dry Run
                </label>
                <button
                  onClick={handleExecuteSkill}
                  style={{
                    padding: "0.5rem 1rem", borderRadius: "0.375rem",
                    border: "none", background: "#e94560", color: "#fff",
                    cursor: "pointer", fontSize: "0.8rem", fontWeight: 600,
                    alignSelf: "flex-start"
                  }}
                >
                  Execute Skill
                </button>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}