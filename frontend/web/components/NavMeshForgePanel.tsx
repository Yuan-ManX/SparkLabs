"use client";

import { useState, useEffect, useCallback } from "react";
import { API_BASE as API_ROOT } from "../utils/api";

const API_BASE = `${API_ROOT}/agent`;

interface SubsystemStats {
  meshes: number;
  total_regions: number;
  total_obstacles: number;
  total_links: number;
  [key: string]: any;
}

export default function NavMeshForgePanel() {
  const [stats, setStats] = useState<SubsystemStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");

  const [meshName, setMeshName] = useState("");
  const [cellSize, setCellSize] = useState("0.3");

  const [meshId, setMeshId] = useState("");
  const [regionName, setRegionName] = useState("");
  const [areaType, setAreaType] = useState("walkable");
  const [traversalCost, setTraversalCost] = useState("1.0");

  const [obstacleOwner, setObstacleOwner] = useState("");
  const [obsShape, setObsShape] = useState("box");
  const [obsPosX, setObsPosX] = useState("0");
  const [obsPosY, setObsPosY] = useState("0");
  const [obsPosZ, setObsPosZ] = useState("0");
  const [obsExtX, setObsExtX] = useState("1.0");
  const [obsExtY, setObsExtY] = useState("1.0");
  const [obsExtZ, setObsExtZ] = useState("1.0");

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/navmesh-forge/stats`);
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

  const handleCreateMesh = async () => {
    if (!meshName.trim()) { showMessage("Mesh name is required"); return; }
    try {
      const res = await fetch(`${API_BASE}/navmesh-forge/create-mesh`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: meshName, cell_size: parseFloat(cellSize) }),
      });
      const data = await res.json();
      if (data.error) showMessage(`Error: ${data.error}`);
      else { showMessage("NavMesh created"); setMeshName(""); fetchStats(); }
    } catch { showMessage("Failed to create mesh"); }
  };

  const handleAddRegion = async () => {
    if (!meshId.trim() || !regionName.trim()) { showMessage("Mesh ID and Region name are required"); return; }
    try {
      const res = await fetch(`${API_BASE}/navmesh-forge/add-region`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mesh_id: meshId, name: regionName, area_type: areaType, traversal_cost: parseFloat(traversalCost) }),
      });
      const data = await res.json();
      if (data.error) showMessage(`Error: ${data.error}`);
      else { showMessage("Region added"); setRegionName(""); fetchStats(); }
    } catch { showMessage("Failed to add region"); }
  };

  const handleAddObstacle = async () => {
    if (!meshId.trim() || !obstacleOwner.trim()) { showMessage("Mesh ID and Owner ID are required"); return; }
    try {
      const res = await fetch(`${API_BASE}/navmesh-forge/add-obstacle`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          mesh_id: meshId, owner_id: obstacleOwner, shape: obsShape,
          position: [parseFloat(obsPosX), parseFloat(obsPosY), parseFloat(obsPosZ)],
          extents: [parseFloat(obsExtX), parseFloat(obsExtY), parseFloat(obsExtZ)],
        }),
      });
      const data = await res.json();
      if (data.error) showMessage(`Error: ${data.error}`);
      else { showMessage("Obstacle added"); fetchStats(); }
    } catch { showMessage("Failed to add obstacle"); }
  };

  return (
    <div style={{ padding: "1.5rem", color: "#e0e0e0" }}>
      <h2 style={{ fontSize: "1.5rem", fontWeight: 700, marginBottom: "1rem", color: "#ffffff" }}>
        NavMesh Forge 🧭
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
                    <div style={{ fontSize: "1.2rem", fontWeight: 700, color: "#e94560" }}>{typeof value === "number" ? value.toLocaleString() : String(value)}</div>
                  </div>
                ))}
              </div>
            ) : (<div style={{ color: "#ff6b6b", fontSize: "0.875rem" }}>Subsystem not available</div>)}
          </div>

          <div style={{ background: "#16213e", borderRadius: "0.75rem", padding: "1rem", marginBottom: "1rem", border: "1px solid #2a2a4a" }}>
            <h3 style={{ fontSize: "0.875rem", color: "#888", marginBottom: "0.75rem", textTransform: "uppercase" }}>Actions</h3>

            <div style={{ background: "#1a1a2e", borderRadius: "0.5rem", padding: "0.75rem", marginBottom: "0.75rem", border: "1px solid #2a2a4a" }}>
              <h4 style={{ fontSize: "0.8rem", color: "#aaa", marginBottom: "0.5rem" }}>Create NavMesh</h4>
              <div style={{ display: "flex", gap: "0.5rem" }}>
                <input type="text" placeholder="Mesh Name" value={meshName} onChange={(e) => setMeshName(e.target.value)}
                  style={{ flex: "1", padding: "0.5rem", borderRadius: "0.375rem", border: "1px solid #2a2a4a", background: "#0d0d0d", color: "#e0e0e0", fontSize: "0.8rem" }} />
                <input type="number" placeholder="Cell Size" value={cellSize} onChange={(e) => setCellSize(e.target.value)} min="0.1" max="5" step="0.1"
                  style={{ width: "100px", padding: "0.5rem", borderRadius: "0.375rem", border: "1px solid #2a2a4a", background: "#0d0d0d", color: "#e0e0e0", fontSize: "0.8rem" }} />
                <button onClick={handleCreateMesh} style={{ padding: "0.5rem 1rem", borderRadius: "0.375rem", border: "none", background: "#e94560", color: "#fff", cursor: "pointer", fontSize: "0.8rem", fontWeight: 600 }}>Create</button>
              </div>
            </div>

            <div style={{ background: "#1a1a2e", borderRadius: "0.5rem", padding: "0.75rem", marginBottom: "0.75rem", border: "1px solid #2a2a4a" }}>
              <h4 style={{ fontSize: "0.8rem", color: "#aaa", marginBottom: "0.5rem" }}>Add Region</h4>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                <input type="text" placeholder="Mesh ID" value={meshId} onChange={(e) => setMeshId(e.target.value)}
                  style={{ padding: "0.5rem", borderRadius: "0.375rem", border: "1px solid #2a2a4a", background: "#0d0d0d", color: "#e0e0e0", fontSize: "0.8rem" }} />
                <div style={{ display: "flex", gap: "0.5rem" }}>
                  <input type="text" placeholder="Region Name" value={regionName} onChange={(e) => setRegionName(e.target.value)}
                    style={{ flex: "1", padding: "0.5rem", borderRadius: "0.375rem", border: "1px solid #2a2a4a", background: "#0d0d0d", color: "#e0e0e0", fontSize: "0.8rem" }} />
                  <select value={areaType} onChange={(e) => setAreaType(e.target.value)}
                    style={{ flex: "1", padding: "0.5rem", borderRadius: "0.375rem", border: "1px solid #2a2a4a", background: "#0d0d0d", color: "#e0e0e0", fontSize: "0.8rem" }}>
                    <option value="walkable">Walkable</option><option value="swimable">Swimable</option>
                    <option value="climbable">Climbable</option><option value="flyable">Flyable</option>
                  </select>
                  <input type="number" placeholder="Cost" value={traversalCost} onChange={(e) => setTraversalCost(e.target.value)} min="0.1" max="100" step="0.1"
                    style={{ width: "80px", padding: "0.5rem", borderRadius: "0.375rem", border: "1px solid #2a2a4a", background: "#0d0d0d", color: "#e0e0e0", fontSize: "0.8rem" }} />
                </div>
                <button onClick={handleAddRegion} style={{ padding: "0.5rem 1rem", borderRadius: "0.375rem", border: "none", background: "#e94560", color: "#fff", cursor: "pointer", fontSize: "0.8rem", fontWeight: 600, alignSelf: "flex-start" }}>Add Region</button>
              </div>
            </div>

            <div style={{ background: "#1a1a2e", borderRadius: "0.5rem", padding: "0.75rem", border: "1px solid #2a2a4a" }}>
              <h4 style={{ fontSize: "0.8rem", color: "#aaa", marginBottom: "0.5rem" }}>Add Obstacle</h4>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                <div style={{ display: "flex", gap: "0.5rem" }}>
                  <input type="text" placeholder="Owner ID" value={obstacleOwner} onChange={(e) => setObstacleOwner(e.target.value)}
                    style={{ flex: "1", padding: "0.5rem", borderRadius: "0.375rem", border: "1px solid #2a2a4a", background: "#0d0d0d", color: "#e0e0e0", fontSize: "0.8rem" }} />
                  <select value={obsShape} onChange={(e) => setObsShape(e.target.value)}
                    style={{ padding: "0.5rem", borderRadius: "0.375rem", border: "1px solid #2a2a4a", background: "#0d0d0d", color: "#e0e0e0", fontSize: "0.8rem" }}>
                    <option value="box">Box</option><option value="cylinder">Cylinder</option>
                    <option value="sphere">Sphere</option><option value="capsule">Capsule</option>
                  </select>
                </div>
                <div style={{ display: "flex", gap: "0.5rem" }}>
                  <input type="number" placeholder="Pos X" value={obsPosX} onChange={(e) => setObsPosX(e.target.value)} step="0.1"
                    style={{ flex: "1", padding: "0.5rem", borderRadius: "0.375rem", border: "1px solid #2a2a4a", background: "#0d0d0d", color: "#e0e0e0", fontSize: "0.8rem" }} />
                  <input type="number" placeholder="Pos Y" value={obsPosY} onChange={(e) => setObsPosY(e.target.value)} step="0.1"
                    style={{ flex: "1", padding: "0.5rem", borderRadius: "0.375rem", border: "1px solid #2a2a4a", background: "#0d0d0d", color: "#e0e0e0", fontSize: "0.8rem" }} />
                  <input type="number" placeholder="Pos Z" value={obsPosZ} onChange={(e) => setObsPosZ(e.target.value)} step="0.1"
                    style={{ flex: "1", padding: "0.5rem", borderRadius: "0.375rem", border: "1px solid #2a2a4a", background: "#0d0d0d", color: "#e0e0e0", fontSize: "0.8rem" }} />
                </div>
                <div style={{ display: "flex", gap: "0.5rem" }}>
                  <input type="number" placeholder="Ext X" value={obsExtX} onChange={(e) => setObsExtX(e.target.value)} min="0.1" step="0.1"
                    style={{ flex: "1", padding: "0.5rem", borderRadius: "0.375rem", border: "1px solid #2a2a4a", background: "#0d0d0d", color: "#e0e0e0", fontSize: "0.8rem" }} />
                  <input type="number" placeholder="Ext Y" value={obsExtY} onChange={(e) => setObsExtY(e.target.value)} min="0.1" step="0.1"
                    style={{ flex: "1", padding: "0.5rem", borderRadius: "0.375rem", border: "1px solid #2a2a4a", background: "#0d0d0d", color: "#e0e0e0", fontSize: "0.8rem" }} />
                  <input type="number" placeholder="Ext Z" value={obsExtZ} onChange={(e) => setObsExtZ(e.target.value)} min="0.1" step="0.1"
                    style={{ flex: "1", padding: "0.5rem", borderRadius: "0.375rem", border: "1px solid #2a2a4a", background: "#0d0d0d", color: "#e0e0e0", fontSize: "0.8rem" }} />
                </div>
                <button onClick={handleAddObstacle} style={{ padding: "0.5rem 1rem", borderRadius: "0.375rem", border: "none", background: "#e94560", color: "#fff", cursor: "pointer", fontSize: "0.8rem", fontWeight: 600, alignSelf: "flex-start" }}>Add Obstacle</button>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}