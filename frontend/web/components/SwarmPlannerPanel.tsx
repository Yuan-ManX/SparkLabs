"use client";

import { useState, useEffect, useCallback } from "react";

const API_BASE = "http://localhost:8000/api/agent";

interface SubsystemStats {
  groups: number;
  active_groups: number;
  total_agents: number;
  formations: number;
  [key: string]: any;
}

export default function SwarmPlannerPanel() {
  const [stats, setStats] = useState<SubsystemStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");

  const [groupName, setGroupName] = useState("");

  const [formationName, setFormationName] = useState("");
  const [formationType, setFormationType] = useState("line");
  const [slotCount, setSlotCount] = useState("10");
  const [spacing, setSpacing] = useState("2.0");

  const [tacticName, setTacticName] = useState("");
  const [tacticType, setTacticType] = useState("surround");

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/swarm-planner/stats`);
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

  const handleCreateGroup = async () => {
    if (!groupName.trim()) {
      showMessage("Group name is required");
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/swarm-planner/create-group`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: groupName, agent_ids: [] }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(`Error: ${data.error}`);
      } else {
        showMessage("Group created");
        setGroupName("");
        fetchStats();
      }
    } catch {
      showMessage("Failed to create group");
    }
  };

  const handleCreateFormation = async () => {
    if (!formationName.trim()) {
      showMessage("Formation name is required");
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/swarm-planner/create-formation`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: formationName,
          formation_type: formationType,
          slot_count: parseInt(slotCount, 10),
          spacing: parseFloat(spacing),
        }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(`Error: ${data.error}`);
      } else {
        showMessage("Formation created");
        setFormationName("");
        fetchStats();
      }
    } catch {
      showMessage("Failed to create formation");
    }
  };

  const handleCreateTactic = async () => {
    if (!tacticName.trim()) {
      showMessage("Tactic name is required");
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/swarm-planner/create-tactic`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: tacticName,
          tactic_type: tacticType,
        }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(`Error: ${data.error}`);
      } else {
        showMessage("Tactic created");
        setTacticName("");
        fetchStats();
      }
    } catch {
      showMessage("Failed to create tactic");
    }
  };

  return (
    <div style={{ padding: "1.5rem", color: "#e0e0e0" }}>
      <h2 style={{ fontSize: "1.5rem", fontWeight: 700, marginBottom: "1rem", color: "#ffffff" }}>
        Swarm Planner 🐝
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
              <h4 style={{ fontSize: "0.8rem", color: "#aaa", marginBottom: "0.5rem" }}>Create Swarm Group</h4>
              <div style={{ display: "flex", gap: "0.5rem" }}>
                <input type="text" placeholder="Group Name" value={groupName} onChange={(e) => setGroupName(e.target.value)}
                  style={{ flex: "1", padding: "0.5rem", borderRadius: "0.375rem", border: "1px solid #2a2a4a", background: "#0d0d1a", color: "#e0e0e0", fontSize: "0.8rem" }} />
                <button onClick={handleCreateGroup} style={{ padding: "0.5rem 1rem", borderRadius: "0.375rem", border: "none", background: "#e94560", color: "#fff", cursor: "pointer", fontSize: "0.8rem", fontWeight: 600 }}>
                  Create
                </button>
              </div>
            </div>
            <div style={{
              background: "#1a1a2e", borderRadius: "0.5rem", padding: "0.75rem",
              marginBottom: "0.75rem", border: "1px solid #2a2a4a"
            }}>
              <h4 style={{ fontSize: "0.8rem", color: "#aaa", marginBottom: "0.5rem" }}>Create Formation</h4>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                <input type="text" placeholder="Formation Name" value={formationName} onChange={(e) => setFormationName(e.target.value)}
                  style={{ padding: "0.5rem", borderRadius: "0.375rem", border: "1px solid #2a2a4a", background: "#0d0d1a", color: "#e0e0e0", fontSize: "0.8rem" }} />
                <div style={{ display: "flex", gap: "0.5rem" }}>
                  <select value={formationType} onChange={(e) => setFormationType(e.target.value)}
                    style={{ flex: "1", padding: "0.5rem", borderRadius: "0.375rem", border: "1px solid #2a2a4a", background: "#0d0d1a", color: "#e0e0e0", fontSize: "0.8rem" }}>
                    <option value="line">Line</option><option value="wedge">Wedge</option>
                    <option value="circle">Circle</option><option value="square">Square</option>
                    <option value="column">Column</option><option value="diamond">Diamond</option>
                    <option value="scatter">Scatter</option><option value="phalanx">Phalanx</option>
                  </select>
                  <input type="number" placeholder="Slots" value={slotCount} onChange={(e) => setSlotCount(e.target.value)} min="1" max="100"
                    style={{ flex: "1", padding: "0.5rem", borderRadius: "0.375rem", border: "1px solid #2a2a4a", background: "#0d0d1a", color: "#e0e0e0", fontSize: "0.8rem" }} />
                </div>
                <button onClick={handleCreateFormation} style={{ padding: "0.5rem 1rem", borderRadius: "0.375rem", border: "none", background: "#e94560", color: "#fff", cursor: "pointer", fontSize: "0.8rem", fontWeight: 600, alignSelf: "flex-start" }}>
                  Create Formation
                </button>
              </div>
            </div>
            <div style={{
              background: "#1a1a2e", borderRadius: "0.5rem", padding: "0.75rem",
              border: "1px solid #2a2a4a"
            }}>
              <h4 style={{ fontSize: "0.8rem", color: "#aaa", marginBottom: "0.5rem" }}>Create Tactic</h4>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                <input type="text" placeholder="Tactic Name" value={tacticName} onChange={(e) => setTacticName(e.target.value)}
                  style={{ padding: "0.5rem", borderRadius: "0.375rem", border: "1px solid #2a2a4a", background: "#0d0d1a", color: "#e0e0e0", fontSize: "0.8rem" }} />
                <select value={tacticType} onChange={(e) => setTacticType(e.target.value)}
                  style={{ padding: "0.5rem", borderRadius: "0.375rem", border: "1px solid #2a2a4a", background: "#0d0d1a", color: "#e0e0e0", fontSize: "0.8rem" }}>
                  <option value="surround">Surround</option><option value="ambush">Ambush</option>
                  <option value="retreat">Retreat</option><option value="sweep">Sweep</option>
                  <option value="hold_position">Hold Position</option><option value="patrol">Patrol</option>
                  <option value="charge">Charge</option><option value="defensive_circle">Defensive Circle</option>
                </select>
                <button onClick={handleCreateTactic} style={{ padding: "0.5rem 1rem", borderRadius: "0.375rem", border: "none", background: "#e94560", color: "#fff", cursor: "pointer", fontSize: "0.8rem", fontWeight: 600, alignSelf: "flex-start" }}>
                  Create Tactic
                </button>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}