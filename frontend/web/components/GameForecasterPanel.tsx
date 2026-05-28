"use client";

import { useState, useEffect, useCallback } from "react";

const API_BASE = "http://localhost:8000/api/agent";

interface SubsystemStats {
  forecasts_run: number;
  confidence_distribution: Record<string, number>;
  domains_analyzed: number;
}

export default function GameForecasterPanel() {
  const [stats, setStats] = useState<SubsystemStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");

  const [simState, setSimState] = useState("");
  const [simParams, setSimParams] = useState("");
  const [simDepth, setSimDepth] = useState("3");
  const [simHorizon, setSimHorizon] = useState("30");
  const [analyzeParamName, setAnalyzeParamName] = useState("");
  const [analyzeCurrentValue, setAnalyzeCurrentValue] = useState("");
  const [analyzeConstraints, setAnalyzeConstraints] = useState("");

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/game-forecaster/stats`);
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

  const handleSimulate = async () => {
    if (!simState.trim() || !simParams.trim()) {
      showMessage("Current state and parameters are required");
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/game-forecaster/simulate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          current_state: simState,
          parameters: simParams.split(",").map((p) => p.trim()).filter(Boolean),
          depth: parseInt(simDepth, 10),
          horizon: parseInt(simHorizon, 10),
        }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(`Error: ${data.error}`);
      } else {
        showMessage("Simulation completed successfully");
        setSimState("");
        setSimParams("");
        fetchStats();
      }
    } catch {
      showMessage("Failed to run simulation");
    }
  };

  const handleAnalyze = async () => {
    if (!analyzeParamName.trim() || !analyzeCurrentValue.trim()) {
      showMessage("Parameter name and current value are required");
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/game-forecaster/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          parameter_name: analyzeParamName,
          current_value: analyzeCurrentValue,
          constraints: analyzeConstraints,
        }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(`Error: ${data.error}`);
      } else {
        showMessage("Analysis completed successfully");
        setAnalyzeParamName("");
        setAnalyzeCurrentValue("");
        setAnalyzeConstraints("");
        fetchStats();
      }
    } catch {
      showMessage("Failed to analyze parameter");
    }
  };

  const formatConfidence = (conf: Record<string, number>) => {
    return Object.entries(conf)
      .map(([k, v]) => `${k}: ${(v * 100).toFixed(0)}%`)
      .join(", ");
  };

  return (
    <div style={{ padding: "1.5rem", color: "#e0e0e0" }}>
      <h2 style={{ fontSize: "1.5rem", fontWeight: 700, marginBottom: "1rem", color: "#ffffff" }}>
        Game Forecaster 📡
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
                  <div style={{ fontSize: "0.7rem", color: "#666", textTransform: "uppercase" }}>Forecasts Run</div>
                  <div style={{ fontSize: "1.2rem", fontWeight: 700, color: "#e94560" }}>
                    {stats.forecasts_run.toLocaleString()}
                  </div>
                </div>
                <div style={{
                  background: "#1a1a2e", borderRadius: "0.5rem", padding: "0.75rem",
                  border: "1px solid #2a2a4a"
                }}>
                  <div style={{ fontSize: "0.7rem", color: "#666", textTransform: "uppercase" }}>Confidence Distribution</div>
                  <div style={{ fontSize: "0.8rem", fontWeight: 600, color: "#e94560" }}>
                    {formatConfidence(stats.confidence_distribution)}
                  </div>
                </div>
                <div style={{
                  background: "#1a1a2e", borderRadius: "0.5rem", padding: "0.75rem",
                  border: "1px solid #2a2a4a"
                }}>
                  <div style={{ fontSize: "0.7rem", color: "#666", textTransform: "uppercase" }}>Domains Analyzed</div>
                  <div style={{ fontSize: "1.2rem", fontWeight: 700, color: "#e94560" }}>
                    {stats.domains_analyzed.toLocaleString()}
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
              <h4 style={{ fontSize: "0.8rem", color: "#aaa", marginBottom: "0.5rem" }}>Run Simulation</h4>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                <textarea
                  placeholder="Current state"
                  value={simState}
                  onChange={(e) => setSimState(e.target.value)}
                  rows={2}
                  style={{
                    padding: "0.5rem", borderRadius: "0.375rem",
                    border: "1px solid #2a2a4a", background: "#0d0d1a", color: "#e0e0e0",
                    fontSize: "0.8rem", resize: "vertical"
                  }}
                />
                <input
                  type="text"
                  placeholder="Parameters (comma-separated)"
                  value={simParams}
                  onChange={(e) => setSimParams(e.target.value)}
                  style={{
                    padding: "0.5rem", borderRadius: "0.375rem",
                    border: "1px solid #2a2a4a", background: "#0d0d1a", color: "#e0e0e0",
                    fontSize: "0.8rem"
                  }}
                />
                <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                  <input
                    type="number"
                    placeholder="Depth"
                    value={simDepth}
                    onChange={(e) => setSimDepth(e.target.value)}
                    style={{
                      width: "80px", padding: "0.5rem", borderRadius: "0.375rem",
                      border: "1px solid #2a2a4a", background: "#0d0d1a", color: "#e0e0e0",
                      fontSize: "0.8rem"
                    }}
                  />
                  <input
                    type="number"
                    placeholder="Horizon"
                    value={simHorizon}
                    onChange={(e) => setSimHorizon(e.target.value)}
                    style={{
                      width: "80px", padding: "0.5rem", borderRadius: "0.375rem",
                      border: "1px solid #2a2a4a", background: "#0d0d1a", color: "#e0e0e0",
                      fontSize: "0.8rem"
                    }}
                  />
                  <button
                    onClick={handleSimulate}
                    style={{
                      padding: "0.5rem 1rem", borderRadius: "0.375rem",
                      border: "none", background: "#e94560", color: "#fff",
                      cursor: "pointer", fontSize: "0.8rem", fontWeight: 600
                    }}
                  >
                    Simulate
                  </button>
                </div>
              </div>
            </div>

            <div style={{
              background: "#1a1a2e", borderRadius: "0.5rem", padding: "0.75rem",
              border: "1px solid #2a2a4a"
            }}>
              <h4 style={{ fontSize: "0.8rem", color: "#aaa", marginBottom: "0.5rem" }}>Analyze Parameter</h4>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                <input
                  type="text"
                  placeholder="Parameter name"
                  value={analyzeParamName}
                  onChange={(e) => setAnalyzeParamName(e.target.value)}
                  style={{
                    padding: "0.5rem", borderRadius: "0.375rem",
                    border: "1px solid #2a2a4a", background: "#0d0d1a", color: "#e0e0e0",
                    fontSize: "0.8rem"
                  }}
                />
                <input
                  type="text"
                  placeholder="Current value"
                  value={analyzeCurrentValue}
                  onChange={(e) => setAnalyzeCurrentValue(e.target.value)}
                  style={{
                    padding: "0.5rem", borderRadius: "0.375rem",
                    border: "1px solid #2a2a4a", background: "#0d0d1a", color: "#e0e0e0",
                    fontSize: "0.8rem"
                  }}
                />
                <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                  <input
                    type="text"
                    placeholder="Constraints (optional)"
                    value={analyzeConstraints}
                    onChange={(e) => setAnalyzeConstraints(e.target.value)}
                    style={{
                      flex: 1, padding: "0.5rem", borderRadius: "0.375rem",
                      border: "1px solid #2a2a4a", background: "#0d0d1a", color: "#e0e0e0",
                      fontSize: "0.8rem"
                    }}
                  />
                  <button
                    onClick={handleAnalyze}
                    style={{
                      padding: "0.5rem 1rem", borderRadius: "0.375rem",
                      border: "none", background: "#e94560", color: "#fff",
                      cursor: "pointer", fontSize: "0.8rem", fontWeight: 600
                    }}
                  >
                    Analyze
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