"use client";

import { useState, useEffect, useCallback } from "react";
import { API_BASE as API_ROOT } from "../utils/api";

const API_BASE = `${API_ROOT}/agent`;

interface SubsystemStats {
  lod_groups: number;
  active_profile: string;
  profiles: number;
  total_transitions: number;
  [key: string]: any;
}

export default function LODGatePanel() {
  const [stats, setStats] = useState<SubsystemStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");

  const [groupName, setGroupName] = useState("");
  const [objectId, setObjectId] = useState("");

  const [lodGroupId, setLodGroupId] = useState("");
  const [distance, setDistance] = useState("10.0");
  const [triangleReduction, setTriangleReduction] = useState("0.5");
  const [textureMip, setTextureMip] = useState("1");

  const [profileName, setProfileName] = useState("");
  const [qualityTier, setQualityTier] = useState("high");
  const [bias, setBias] = useState("1.0");

  const [camX, setCamX] = useState("0");
  const [camY, setCamY] = useState("0");
  const [camZ, setCamZ] = useState("0");

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/lod-gate/stats`);
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

  const showMessage = (msg: string) => { setMessage(msg); setTimeout(() => setMessage(""), 3000); };

  const handleRegisterGroup = async () => {
    if (!groupName.trim()) { showMessage("Group name is required"); return; }
    try {
      const res = await fetch(`${API_BASE}/lod-gate/register-group`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: groupName, object_id: objectId }),
      });
      const data = await res.json();
      if (data.error) showMessage(`Error: ${data.error}`);
      else { showMessage("Group registered"); setGroupName(""); fetchStats(); }
    } catch { showMessage("Failed to register group"); }
  };

  const handleAddLevel = async () => {
    if (!lodGroupId.trim()) { showMessage("Group ID is required"); return; }
    try {
      const res = await fetch(`${API_BASE}/lod-gate/add-level`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ group_id: lodGroupId, distance: parseFloat(distance), triangle_reduction: parseFloat(triangleReduction), texture_mip: parseInt(textureMip, 10) }),
      });
      const data = await res.json();
      if (data.error) showMessage(`Error: ${data.error}`);
      else { showMessage("LOD level added"); fetchStats(); }
    } catch { showMessage("Failed to add LOD level"); }
  };

  const handleCreateProfile = async () => {
    if (!profileName.trim()) { showMessage("Profile name is required"); return; }
    try {
      const res = await fetch(`${API_BASE}/lod-gate/create-profile`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: profileName, quality_tier: qualityTier, bias: parseFloat(bias) }),
      });
      const data = await res.json();
      if (data.error) showMessage(`Error: ${data.error}`);
      else { showMessage("Profile created"); setProfileName(""); fetchStats(); }
    } catch { showMessage("Failed to create profile"); }
  };

  const handleUpdateCamera = async () => {
    try {
      const res = await fetch(`${API_BASE}/lod-gate/update-camera`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ position: [parseFloat(camX), parseFloat(camY), parseFloat(camZ)] }),
      });
      const data = await res.json();
      if (!data.error) { showMessage("Camera updated"); fetchStats(); }
    } catch { showMessage("Failed to update camera"); }
  };

  return (
    <div style={{ padding: "1.5rem", color: "#e0e0e0" }}>
      <h2 style={{ fontSize: "1.5rem", fontWeight: 700, marginBottom: "1rem", color: "#ffffff" }}>
        LOD Gate 🔍
      </h2>
      {message && (<div style={{ background: "#1b5e20", color: "#a5d6a7", padding: "0.5rem 1rem", borderRadius: "0.5rem", marginBottom: "1rem", fontSize: "0.875rem" }}>{message}</div>)}
      {loading ? (<div style={{ color: "#888", fontSize: "0.875rem" }}>Loading...</div>) : (
        <>
          <div style={{ background: "#16213e", borderRadius: "0.75rem", padding: "1rem", marginBottom: "1rem", border: "1px solid #2a2a4a" }}>
            <h3 style={{ fontSize: "0.875rem", color: "#888", marginBottom: "0.75rem", textTransform: "uppercase" }}>Statistics</h3>
            {stats ? (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))", gap: "0.75rem" }}>
                {Object.entries(stats).map(([key, value]) => (
                  <div key={key} style={{ background: "#1a1a2e", borderRadius: "0.5rem", padding: "0.75rem", border: "1px solid #2a2a4a" }}>
                    <div style={{ fontSize: "0.7rem", color: "#666", textTransform: "uppercase" }}>{key}</div>
                    <div style={{ fontSize: "1.2rem", fontWeight: 700, color: "#e94560" }}>{String(value)}</div>
                  </div>
                ))}
              </div>
            ) : (<div style={{ color: "#ff6b6b", fontSize: "0.875rem" }}>Subsystem not available</div>)}
          </div>

          <div style={{ background: "#16213e", borderRadius: "0.75rem", padding: "1rem", marginBottom: "1rem", border: "1px solid #2a2a4a" }}>
            <h3 style={{ fontSize: "0.875rem", color: "#888", marginBottom: "0.75rem", textTransform: "uppercase" }}>Actions</h3>

            <div style={{ background: "#1a1a2e", borderRadius: "0.5rem", padding: "0.75rem", marginBottom: "0.75rem", border: "1px solid #2a2a4a" }}>
              <h4 style={{ fontSize: "0.8rem", color: "#aaa", marginBottom: "0.5rem" }}>Register LOD Group</h4>
              <div style={{ display: "flex", gap: "0.5rem" }}>
                <input type="text" placeholder="Group Name" value={groupName} onChange={(e) => setGroupName(e.target.value)}
                  style={{ flex: "1", padding: "0.5rem", borderRadius: "0.375rem", border: "1px solid #2a2a4a", background: "#0d0d0d", color: "#e0e0e0", fontSize: "0.8rem" }} />
                <input type="text" placeholder="Object ID" value={objectId} onChange={(e) => setObjectId(e.target.value)}
                  style={{ flex: "1", padding: "0.5rem", borderRadius: "0.375rem", border: "1px solid #2a2a4a", background: "#0d0d0d", color: "#e0e0e0", fontSize: "0.8rem" }} />
                <button onClick={handleRegisterGroup} style={{ padding: "0.5rem 1rem", borderRadius: "0.375rem", border: "none", background: "#e94560", color: "#fff", cursor: "pointer", fontSize: "0.8rem", fontWeight: 600 }}>Register</button>
              </div>
            </div>

            <div style={{ background: "#1a1a2e", borderRadius: "0.5rem", padding: "0.75rem", marginBottom: "0.75rem", border: "1px solid #2a2a4a" }}>
              <h4 style={{ fontSize: "0.8rem", color: "#aaa", marginBottom: "0.5rem" }}>Add LOD Level</h4>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                <input type="text" placeholder="Group ID" value={lodGroupId} onChange={(e) => setLodGroupId(e.target.value)}
                  style={{ padding: "0.5rem", borderRadius: "0.375rem", border: "1px solid #2a2a4a", background: "#0d0d0d", color: "#e0e0e0", fontSize: "0.8rem" }} />
                <div style={{ display: "flex", gap: "0.5rem" }}>
                  <input type="number" placeholder="Distance Threshold" value={distance} onChange={(e) => setDistance(e.target.value)} min="0" step="0.1"
                    style={{ flex: "1", padding: "0.5rem", borderRadius: "0.375rem", border: "1px solid #2a2a4a", background: "#0d0d0d", color: "#e0e0e0", fontSize: "0.8rem" }} />
                  <input type="number" placeholder="Tri Reduction" value={triangleReduction} onChange={(e) => setTriangleReduction(e.target.value)} min="0" max="1" step="0.1"
                    style={{ flex: "1", padding: "0.5rem", borderRadius: "0.375rem", border: "1px solid #2a2a4a", background: "#0d0d0d", color: "#e0e0e0", fontSize: "0.8rem" }} />
                  <input type="number" placeholder="Mip Level" value={textureMip} onChange={(e) => setTextureMip(e.target.value)} min="0" max="12"
                    style={{ flex: "1", padding: "0.5rem", borderRadius: "0.375rem", border: "1px solid #2a2a4a", background: "#0d0d0d", color: "#e0e0e0", fontSize: "0.8rem" }} />
                </div>
                <button onClick={handleAddLevel} style={{ padding: "0.5rem 1rem", borderRadius: "0.375rem", border: "none", background: "#e94560", color: "#fff", cursor: "pointer", fontSize: "0.8rem", fontWeight: 600, alignSelf: "flex-start" }}>Add Level</button>
              </div>
            </div>

            <div style={{ background: "#1a1a2e", borderRadius: "0.5rem", padding: "0.75rem", marginBottom: "0.75rem", border: "1px solid #2a2a4a" }}>
              <h4 style={{ fontSize: "0.8rem", color: "#aaa", marginBottom: "0.5rem" }}>Camera Position</h4>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                <div style={{ display: "flex", gap: "0.5rem" }}>
                  <input type="number" placeholder="X" value={camX} onChange={(e) => setCamX(e.target.value)} step="0.1"
                    style={{ flex: "1", padding: "0.5rem", borderRadius: "0.375rem", border: "1px solid #2a2a4a", background: "#0d0d0d", color: "#e0e0e0", fontSize: "0.8rem" }} />
                  <input type="number" placeholder="Y" value={camY} onChange={(e) => setCamY(e.target.value)} step="0.1"
                    style={{ flex: "1", padding: "0.5rem", borderRadius: "0.375rem", border: "1px solid #2a2a4a", background: "#0d0d0d", color: "#e0e0e0", fontSize: "0.8rem" }} />
                  <input type="number" placeholder="Z" value={camZ} onChange={(e) => setCamZ(e.target.value)} step="0.1"
                    style={{ flex: "1", padding: "0.5rem", borderRadius: "0.375rem", border: "1px solid #2a2a4a", background: "#0d0d0d", color: "#e0e0e0", fontSize: "0.8rem" }} />
                </div>
                <div style={{ display: "flex", gap: "0.5rem" }}>
                  <button onClick={handleUpdateCamera} style={{ padding: "0.5rem 1rem", borderRadius: "0.375rem", border: "none", background: "#e94560", color: "#fff", cursor: "pointer", fontSize: "0.8rem", fontWeight: 600 }}>Update Camera</button>
                  <input type="text" placeholder="Profile Name" value={profileName} onChange={(e) => setProfileName(e.target.value)}
                    style={{ flex: "1", padding: "0.5rem", borderRadius: "0.375rem", border: "1px solid #2a2a4a", background: "#0d0d0d", color: "#e0e0e0", fontSize: "0.8rem" }} />
                  <select value={qualityTier} onChange={(e) => setQualityTier(e.target.value)}
                    style={{ padding: "0.5rem", borderRadius: "0.375rem", border: "1px solid #2a2a4a", background: "#0d0d0d", color: "#e0e0e0", fontSize: "0.8rem" }}>
                    <option value="ultra">Ultra</option><option value="high">High</option>
                    <option value="medium">Medium</option><option value="low">Low</option>
                  </select>
                  <button onClick={handleCreateProfile} style={{ padding: "0.5rem 1rem", borderRadius: "0.375rem", border: "none", background: "#e94560", color: "#fff", cursor: "pointer", fontSize: "0.8rem", fontWeight: 600 }}>Profile</button>
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}