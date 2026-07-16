"use client";

import { useState, useEffect, useCallback } from "react";
import { API_BASE as API_ROOT } from "../utils/api";

const API_BASE = `${API_ROOT}/agent`;

interface SubsystemStats {
  experiments: number;
  total_trials: number;
  reports: number;
  [key: string]: any;
}

export default function ABTestRunnerPanel() {
  const [stats, setStats] = useState<SubsystemStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");

  const [expName, setExpName] = useState("");
  const [variantA, setVariantA] = useState("control");
  const [variantB, setVariantB] = useState("treatment");
  const [metricType, setMetricType] = useState("retention");

  const [experimentId, setExperimentId] = useState("");

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/ab-test-runner/stats`);
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

  const handleCreateExperiment = async () => {
    if (!expName.trim()) {
      showMessage("Experiment name is required");
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/ab-test-runner/create-experiment`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: expName,
          variant_a: variantA,
          variant_b: variantB,
          metric_type: metricType,
        }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(`Error: ${data.error}`);
      } else {
        showMessage("Experiment created successfully");
        setExpName("");
        fetchStats();
      }
    } catch {
      showMessage("Failed to create experiment");
    }
  };

  const handleAnalyzeResults = async () => {
    if (!experimentId.trim()) {
      showMessage("Experiment ID is required");
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/ab-test-runner/analyze-results`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ experiment_id: experimentId }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(`Error: ${data.error}`);
      } else {
        showMessage("Results analysis completed");
        setExperimentId("");
        fetchStats();
      }
    } catch {
      showMessage("Failed to analyze results");
    }
  };

  return (
    <div style={{ padding: "1.5rem", color: "#e0e0e0" }}>
      <h2 style={{ fontSize: "1.5rem", fontWeight: 700, marginBottom: "1rem", color: "#ffffff" }}>
        AB Test Runner 🔬
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
              <h4 style={{ fontSize: "0.8rem", color: "#aaa", marginBottom: "0.5rem" }}>Create Experiment</h4>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                <input
                  type="text"
                  placeholder="Experiment Name"
                  value={expName}
                  onChange={(e) => setExpName(e.target.value)}
                  style={{
                    padding: "0.5rem", borderRadius: "0.375rem",
                    border: "1px solid #2a2a4a", background: "#0d0d0d", color: "#e0e0e0",
                    fontSize: "0.8rem"
                  }}
                />
                <div style={{ display: "flex", gap: "0.5rem" }}>
                  <input
                    type="text"
                    placeholder="Variant A"
                    value={variantA}
                    onChange={(e) => setVariantA(e.target.value)}
                    style={{
                      flex: "1", padding: "0.5rem", borderRadius: "0.375rem",
                      border: "1px solid #2a2a4a", background: "#0d0d0d", color: "#e0e0e0",
                      fontSize: "0.8rem"
                    }}
                  />
                  <input
                    type="text"
                    placeholder="Variant B"
                    value={variantB}
                    onChange={(e) => setVariantB(e.target.value)}
                    style={{
                      flex: "1", padding: "0.5rem", borderRadius: "0.375rem",
                      border: "1px solid #2a2a4a", background: "#0d0d0d", color: "#e0e0e0",
                      fontSize: "0.8rem"
                    }}
                  />
                </div>
                <select
                  value={metricType}
                  onChange={(e) => setMetricType(e.target.value)}
                  style={{
                    padding: "0.5rem", borderRadius: "0.375rem",
                    border: "1px solid #2a2a4a", background: "#0d0d0d", color: "#e0e0e0",
                    fontSize: "0.8rem"
                  }}
                >
                  <option value="retention">Retention</option>
                  <option value="engagement">Engagement</option>
                  <option value="conversion">Conversion</option>
                  <option value="revenue">Revenue</option>
                  <option value="satisfaction">Satisfaction</option>
                  <option value="performance">Performance</option>
                  <option value="completion">Completion</option>
                </select>
                <button
                  onClick={handleCreateExperiment}
                  style={{
                    padding: "0.5rem 1rem", borderRadius: "0.375rem",
                    border: "none", background: "#e94560", color: "#fff",
                    cursor: "pointer", fontSize: "0.8rem", fontWeight: 600,
                    alignSelf: "flex-start"
                  }}
                >
                  Create Experiment
                </button>
              </div>
            </div>

            <div style={{
              background: "#1a1a2e", borderRadius: "0.5rem", padding: "0.75rem",
              border: "1px solid #2a2a4a"
            }}>
              <h4 style={{ fontSize: "0.8rem", color: "#aaa", marginBottom: "0.5rem" }}>Analyze Results</h4>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                <input
                  type="text"
                  placeholder="Experiment ID"
                  value={experimentId}
                  onChange={(e) => setExperimentId(e.target.value)}
                  style={{
                    padding: "0.5rem", borderRadius: "0.375rem",
                    border: "1px solid #2a2a4a", background: "#0d0d0d", color: "#e0e0e0",
                    fontSize: "0.8rem"
                  }}
                />
                <button
                  onClick={handleAnalyzeResults}
                  style={{
                    padding: "0.5rem 1rem", borderRadius: "0.375rem",
                    border: "none", background: "#e94560", color: "#fff",
                    cursor: "pointer", fontSize: "0.8rem", fontWeight: 600,
                    alignSelf: "flex-start"
                  }}
                >
                  Analyze Results
                </button>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}