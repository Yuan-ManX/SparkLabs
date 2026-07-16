"use client";

import { useState, useEffect, useCallback } from "react";
import { API_BASE as API_ROOT } from "../utils/api";

const API_BASE = `${API_ROOT}/agent`;

interface SubsystemStats {
  archetypes: number;
  batches: number;
  total_sessions: number;
  [key: string]: any;
}

export default function PlaytestOrchestratorPanel() {
  const [stats, setStats] = useState<SubsystemStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");

  const [batchName, setBatchName] = useState("");
  const [levelId, setLevelId] = useState("");
  const [targetSessions, setTargetSessions] = useState("1000");

  const [runBatchId, setRunBatchId] = useState("");

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/playtest-orchestrator/stats`);
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

  const handleCreateBatch = async () => {
    if (!batchName.trim()) { showMessage("Batch name is required"); return; }
    try {
      const res = await fetch(`${API_BASE}/playtest-orchestrator/create-batch`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: batchName, level_id: levelId, target_sessions: parseInt(targetSessions, 10) }),
      });
      const data = await res.json();
      if (data.error) showMessage(`Error: ${data.error}`);
      else { showMessage("Batch created"); setBatchName(""); fetchStats(); }
    } catch { showMessage("Failed to create batch"); }
  };

  const handleRunBatch = async () => {
    if (!runBatchId.trim()) { showMessage("Batch ID is required"); return; }
    try {
      const res = await fetch(`${API_BASE}/playtest-orchestrator/run-batch`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ batch_id: runBatchId }),
      });
      const data = await res.json();
      if (data.error) showMessage(`Error: ${data.error}`);
      else { showMessage("Batch running"); fetchStats(); }
    } catch { showMessage("Failed to run batch"); }
  };

  const handleGenerateReport = async () => {
    if (!runBatchId.trim()) { showMessage("Batch ID is required"); return; }
    try {
      const res = await fetch(`${API_BASE}/playtest-orchestrator/generate-report`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ batch_id: runBatchId }),
      });
      const data = await res.json();
      if (data.error) showMessage(`Error: ${data.error}`);
      else { showMessage("Report generated"); fetchStats(); }
    } catch { showMessage("Failed to generate report"); }
  };

  return (
    <div style={{ padding: "1.5rem", color: "#e0e0e0" }}>
      <h2 style={{ fontSize: "1.5rem", fontWeight: 700, marginBottom: "1rem", color: "#ffffff" }}>
        Playtest Orchestrator 🎮
      </h2>
      {message && (
        <div style={{ background: "#1b5e20", color: "#a5d6a7", padding: "0.5rem 1rem", borderRadius: "0.5rem", marginBottom: "1rem", fontSize: "0.875rem" }}>{message}</div>
      )}
      {loading ? (<div style={{ color: "#888", fontSize: "0.875rem" }}>Loading...</div>) : (
        <>
          <div style={{ background: "#16213e", borderRadius: "0.75rem", padding: "1rem", marginBottom: "1rem", border: "1px solid #2a2a4a" }}>
            <h3 style={{ fontSize: "0.875rem", color: "#888", marginBottom: "0.75rem", textTransform: "uppercase" }}>Statistics</h3>
            {stats ? (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))", gap: "0.75rem" }}>
                {Object.entries(stats).map(([key, value]) => (
                  <div key={key} style={{ background: "#1a1a2e", borderRadius: "0.5rem", padding: "0.75rem", border: "1px solid #2a2a4a" }}>
                    <div style={{ fontSize: "0.7rem", color: "#666", textTransform: "uppercase" }}>{key}</div>
                    <div style={{ fontSize: "1.2rem", fontWeight: 700, color: "#e94560" }}>{typeof value === "number" ? value.toLocaleString() : String(value)}</div>
                  </div>
                ))}
              </div>
            ) : (<div style={{ color: "#ff6b6b", fontSize: "0.875rem" }}>Subsystem not available</div>)}
          </div>

          <div style={{ background: "#16213e", borderRadius: "0.75rem", padding: "1rem", marginBottom: "1rem", border: "1px solid #2a2a4a" }}>
            <h3 style={{ fontSize: "0.875rem", color: "#888", marginBottom: "0.75rem", textTransform: "uppercase" }}>Actions</h3>

            <div style={{ background: "#1a1a2e", borderRadius: "0.5rem", padding: "0.75rem", marginBottom: "0.75rem", border: "1px solid #2a2a4a" }}>
              <h4 style={{ fontSize: "0.8rem", color: "#aaa", marginBottom: "0.5rem" }}>Create Playtest Batch</h4>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                <input type="text" placeholder="Batch Name" value={batchName} onChange={(e) => setBatchName(e.target.value)}
                  style={{ padding: "0.5rem", borderRadius: "0.375rem", border: "1px solid #2a2a4a", background: "#0d0d0d", color: "#e0e0e0", fontSize: "0.8rem" }} />
                <input type="text" placeholder="Level ID" value={levelId} onChange={(e) => setLevelId(e.target.value)}
                  style={{ padding: "0.5rem", borderRadius: "0.375rem", border: "1px solid #2a2a4a", background: "#0d0d0d", color: "#e0e0e0", fontSize: "0.8rem" }} />
                <input type="number" placeholder="Target Sessions" value={targetSessions} onChange={(e) => setTargetSessions(e.target.value)} min="10" max="100000" step="100"
                  style={{ padding: "0.5rem", borderRadius: "0.375rem", border: "1px solid #2a2a4a", background: "#0d0d0d", color: "#e0e0e0", fontSize: "0.8rem" }} />
                <button onClick={handleCreateBatch} style={{ padding: "0.5rem 1rem", borderRadius: "0.375rem", border: "none", background: "#e94560", color: "#fff", cursor: "pointer", fontSize: "0.8rem", fontWeight: 600, alignSelf: "flex-start" }}>
                  Create Batch
                </button>
              </div>
            </div>

            <div style={{ background: "#1a1a2e", borderRadius: "0.5rem", padding: "0.75rem", marginBottom: "0.75rem", border: "1px solid #2a2a4a" }}>
              <h4 style={{ fontSize: "0.8rem", color: "#aaa", marginBottom: "0.5rem" }}>Execute Batch</h4>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                <input type="text" placeholder="Batch ID" value={runBatchId} onChange={(e) => setRunBatchId(e.target.value)}
                  style={{ padding: "0.5rem", borderRadius: "0.375rem", border: "1px solid #2a2a4a", background: "#0d0d0d", color: "#e0e0e0", fontSize: "0.8rem" }} />
                <div style={{ display: "flex", gap: "0.5rem" }}>
                  <button onClick={handleRunBatch} style={{ padding: "0.5rem 1rem", borderRadius: "0.375rem", border: "none", background: "#e94560", color: "#fff", cursor: "pointer", fontSize: "0.8rem", fontWeight: 600 }}>
                    Run Batch
                  </button>
                  <button onClick={handleGenerateReport} style={{ padding: "0.5rem 1rem", borderRadius: "0.375rem", border: "none", background: "#1e1e1e", color: "#fff", cursor: "pointer", fontSize: "0.8rem", fontWeight: 600 }}>
                    Generate Report
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