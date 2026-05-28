"use client";

import { useState, useEffect, useCallback } from "react";

const API_BASE = "http://localhost:8000/api/agent";

interface SubsystemStats {
  sessions_created: number;
  steps_completed: number;
  learner_count: number;
}

export default function TutorialOrchestratorPanel() {
  const [stats, setStats] = useState<SubsystemStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");

  const [genUserId, setGenUserId] = useState("");
  const [genObjective, setGenObjective] = useState("");
  const [genTutorialType, setGenTutorialType] = useState("interactive");
  const [trackUserId, setTrackUserId] = useState("");
  const [trackAction, setTrackAction] = useState("");
  const [trackContext, setTrackContext] = useState("");

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/tutorial-orchestrator/stats`);
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

  const handleGenerate = async () => {
    if (!genUserId.trim() || !genObjective.trim()) {
      showMessage("User ID and objective are required");
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/tutorial-orchestrator/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: genUserId,
          objective: genObjective,
          tutorial_type: genTutorialType,
        }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(`Error: ${data.error}`);
      } else {
        showMessage("Tutorial generated successfully");
        setGenUserId("");
        setGenObjective("");
        fetchStats();
      }
    } catch {
      showMessage("Failed to generate tutorial");
    }
  };

  const handleTrack = async () => {
    if (!trackUserId.trim() || !trackAction.trim()) {
      showMessage("User ID and action are required");
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/tutorial-orchestrator/track`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: trackUserId,
          action: trackAction,
          context: trackContext,
        }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(`Error: ${data.error}`);
      } else {
        showMessage("Action tracked successfully");
        setTrackUserId("");
        setTrackAction("");
        setTrackContext("");
        fetchStats();
      }
    } catch {
      showMessage("Failed to track action");
    }
  };

  return (
    <div style={{ padding: "1.5rem", color: "#e0e0e0" }}>
      <h2 style={{ fontSize: "1.5rem", fontWeight: 700, marginBottom: "1rem", color: "#ffffff" }}>
        Tutorial Orchestrator 🎓
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
                <div style={{
                  background: "#1a1a2e", borderRadius: "0.5rem", padding: "0.75rem",
                  border: "1px solid #2a2a4a"
                }}>
                  <div style={{ fontSize: "0.7rem", color: "#666", textTransform: "uppercase" }}>Sessions Created</div>
                  <div style={{ fontSize: "1.2rem", fontWeight: 700, color: "#e94560" }}>
                    {stats.sessions_created.toLocaleString()}
                  </div>
                </div>
                <div style={{
                  background: "#1a1a2e", borderRadius: "0.5rem", padding: "0.75rem",
                  border: "1px solid #2a2a4a"
                }}>
                  <div style={{ fontSize: "0.7rem", color: "#666", textTransform: "uppercase" }}>Steps Completed</div>
                  <div style={{ fontSize: "1.2rem", fontWeight: 700, color: "#e94560" }}>
                    {stats.steps_completed.toLocaleString()}
                  </div>
                </div>
                <div style={{
                  background: "#1a1a2e", borderRadius: "0.5rem", padding: "0.75rem",
                  border: "1px solid #2a2a4a"
                }}>
                  <div style={{ fontSize: "0.7rem", color: "#666", textTransform: "uppercase" }}>Learner Count</div>
                  <div style={{ fontSize: "1.2rem", fontWeight: 700, color: "#e94560" }}>
                    {stats.learner_count.toLocaleString()}
                  </div>
                </div>
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
              <h4 style={{ fontSize: "0.8rem", color: "#aaa", marginBottom: "0.5rem" }}>Generate Tutorial</h4>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                <input
                  type="text"
                  placeholder="User ID"
                  value={genUserId}
                  onChange={(e) => setGenUserId(e.target.value)}
                  style={{
                    padding: "0.5rem", borderRadius: "0.375rem",
                    border: "1px solid #2a2a4a", background: "#0d0d1a", color: "#e0e0e0",
                    fontSize: "0.8rem"
                  }}
                />
                <textarea
                  placeholder="Learning objective"
                  value={genObjective}
                  onChange={(e) => setGenObjective(e.target.value)}
                  rows={2}
                  style={{
                    padding: "0.5rem", borderRadius: "0.375rem",
                    border: "1px solid #2a2a4a", background: "#0d0d1a", color: "#e0e0e0",
                    fontSize: "0.8rem", resize: "vertical"
                  }}
                />
                <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                  <select
                    value={genTutorialType}
                    onChange={(e) => setGenTutorialType(e.target.value)}
                    style={{
                      padding: "0.5rem", borderRadius: "0.375rem",
                      border: "1px solid #2a2a4a", background: "#0d0d1a", color: "#e0e0e0",
                      fontSize: "0.8rem"
                    }}
                  >
                    <option value="interactive">Interactive</option>
                    <option value="video">Video</option>
                    <option value="walkthrough">Walkthrough</option>
                    <option value="quiz">Quiz</option>
                    <option value="sandbox">Sandbox</option>
                  </select>
                  <button
                    onClick={handleGenerate}
                    style={{
                      padding: "0.5rem 1rem", borderRadius: "0.375rem",
                      border: "none", background: "#e94560", color: "#fff",
                      cursor: "pointer", fontSize: "0.8rem", fontWeight: 600
                    }}
                  >
                    Generate
                  </button>
                </div>
              </div>
            </div>

            <div style={{
              background: "#1a1a2e", borderRadius: "0.5rem", padding: "0.75rem",
              border: "1px solid #2a2a4a"
            }}>
              <h4 style={{ fontSize: "0.8rem", color: "#aaa", marginBottom: "0.5rem" }}>Track Progress</h4>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                <input
                  type="text"
                  placeholder="User ID"
                  value={trackUserId}
                  onChange={(e) => setTrackUserId(e.target.value)}
                  style={{
                    padding: "0.5rem", borderRadius: "0.375rem",
                    border: "1px solid #2a2a4a", background: "#0d0d1a", color: "#e0e0e0",
                    fontSize: "0.8rem"
                  }}
                />
                <input
                  type="text"
                  placeholder="Action"
                  value={trackAction}
                  onChange={(e) => setTrackAction(e.target.value)}
                  style={{
                    padding: "0.5rem", borderRadius: "0.375rem",
                    border: "1px solid #2a2a4a", background: "#0d0d1a", color: "#e0e0e0",
                    fontSize: "0.8rem"
                  }}
                />
                <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                  <input
                    type="text"
                    placeholder="Context (optional)"
                    value={trackContext}
                    onChange={(e) => setTrackContext(e.target.value)}
                    style={{
                      flex: 1, padding: "0.5rem", borderRadius: "0.375rem",
                      border: "1px solid #2a2a4a", background: "#0d0d1a", color: "#e0e0e0",
                      fontSize: "0.8rem"
                    }}
                  />
                  <button
                    onClick={handleTrack}
                    style={{
                      padding: "0.5rem 1rem", borderRadius: "0.375rem",
                      border: "none", background: "#e94560", color: "#fff",
                      cursor: "pointer", fontSize: "0.8rem", fontWeight: 600
                    }}
                  >
                    Track
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