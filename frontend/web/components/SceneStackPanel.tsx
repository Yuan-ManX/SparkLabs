"use client";

import { useState, useEffect, useCallback } from "react";

const API_BASE = "http://localhost:8000/api/agent";

interface SubsystemStats {
  total_scenes: number;
  active_scenes: number;
  snapshots: number;
  [key: string]: any;
}

export default function SceneStackPanel() {
  const [stats, setStats] = useState<SubsystemStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");

  const [sceneName, setSceneName] = useState("");
  const [sceneLayer, setSceneLayer] = useState("base");
  const [transitionType, setTransitionType] = useState("fade");
  const [transitionDuration, setTransitionDuration] = useState("0.5");

  const [overlayName, setOverlayName] = useState("");

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/scene-stack/stats`);
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

  const handleRegisterScene = async () => {
    if (!sceneName.trim()) { showMessage("Scene name is required"); return; }
    try {
      const res = await fetch(`${API_BASE}/scene-stack/register-scene`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: sceneName, layer: sceneLayer }),
      });
      const data = await res.json();
      if (data.error) showMessage(`Error: ${data.error}`);
      else { showMessage("Scene registered"); fetchStats(); }
    } catch { showMessage("Failed to register scene"); }
  };

  const handleLoadScene = async () => {
    if (!sceneName.trim()) { showMessage("Scene name is required"); return; }
    try {
      const res = await fetch(`${API_BASE}/scene-stack/load-scene`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: sceneName, transition_type: transitionType, transition_duration: parseFloat(transitionDuration) }),
      });
      const data = await res.json();
      if (data.error) showMessage(`Error: ${data.error}`);
      else { showMessage("Scene loaded"); fetchStats(); }
    } catch { showMessage("Failed to load scene"); }
  };

  const handlePushOverlay = async () => {
    if (!overlayName.trim()) { showMessage("Overlay name is required"); return; }
    try {
      const res = await fetch(`${API_BASE}/scene-stack/push-overlay`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: overlayName, transition_type: "fade" }),
      });
      const data = await res.json();
      if (data.error) showMessage(`Error: ${data.error}`);
      else { showMessage("Overlay pushed"); fetchStats(); }
    } catch { showMessage("Failed to push overlay"); }
  };

  return (
    <div style={{ padding: "1.5rem", color: "#e0e0e0" }}>
      <h2 style={{ fontSize: "1.5rem", fontWeight: 700, marginBottom: "1rem", color: "#ffffff" }}>
        Scene Stack 🎬
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
              <h4 style={{ fontSize: "0.8rem", color: "#aaa", marginBottom: "0.5rem" }}>Scene Management</h4>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                <input type="text" placeholder="Scene Name" value={sceneName} onChange={(e) => setSceneName(e.target.value)}
                  style={{ padding: "0.5rem", borderRadius: "0.375rem", border: "1px solid #2a2a4a", background: "#0d0d1a", color: "#e0e0e0", fontSize: "0.8rem" }} />
                <div style={{ display: "flex", gap: "0.5rem" }}>
                  <select value={sceneLayer} onChange={(e) => setSceneLayer(e.target.value)}
                    style={{ flex: "1", padding: "0.5rem", borderRadius: "0.375rem", border: "1px solid #2a2a4a", background: "#0d0d1a", color: "#e0e0e0", fontSize: "0.8rem" }}>
                    <option value="base">Base</option><option value="overlay">Overlay</option>
                    <option value="popup">Popup</option><option value="hud">HUD</option>
                    <option value="system">System</option>
                  </select>
                  <select value={transitionType} onChange={(e) => setTransitionType(e.target.value)}
                    style={{ flex: "1", padding: "0.5rem", borderRadius: "0.375rem", border: "1px solid #2a2a4a", background: "#0d0d1a", color: "#e0e0e0", fontSize: "0.8rem" }}>
                    <option value="fade">Fade</option><option value="crossfade">Crossfade</option>
                    <option value="wipe_left">Wipe Left</option><option value="wipe_right">Wipe Right</option>
                    <option value="zoom_in">Zoom In</option><option value="zoom_out">Zoom Out</option>
                    <option value="none">None</option>
                  </select>
                  <input type="number" placeholder="Duration" value={transitionDuration} onChange={(e) => setTransitionDuration(e.target.value)} min="0.1" max="5" step="0.1"
                    style={{ width: "80px", padding: "0.5rem", borderRadius: "0.375rem", border: "1px solid #2a2a4a", background: "#0d0d1a", color: "#e0e0e0", fontSize: "0.8rem" }} />
                </div>
                <div style={{ display: "flex", gap: "0.5rem" }}>
                  <button onClick={handleRegisterScene} style={{ padding: "0.5rem 1rem", borderRadius: "0.375rem", border: "none", background: "#0f3460", color: "#fff", cursor: "pointer", fontSize: "0.8rem", fontWeight: 600 }}>Register</button>
                  <button onClick={handleLoadScene} style={{ padding: "0.5rem 1rem", borderRadius: "0.375rem", border: "none", background: "#e94560", color: "#fff", cursor: "pointer", fontSize: "0.8rem", fontWeight: 600 }}>Load Scene</button>
                </div>
              </div>
            </div>

            <div style={{ background: "#1a1a2e", borderRadius: "0.5rem", padding: "0.75rem", border: "1px solid #2a2a4a" }}>
              <h4 style={{ fontSize: "0.8rem", color: "#aaa", marginBottom: "0.5rem" }}>Push Overlay</h4>
              <div style={{ display: "flex", gap: "0.5rem" }}>
                <input type="text" placeholder="Overlay Name" value={overlayName} onChange={(e) => setOverlayName(e.target.value)}
                  style={{ flex: "1", padding: "0.5rem", borderRadius: "0.375rem", border: "1px solid #2a2a4a", background: "#0d0d1a", color: "#e0e0e0", fontSize: "0.8rem" }} />
                <button onClick={handlePushOverlay} style={{ padding: "0.5rem 1rem", borderRadius: "0.375rem", border: "none", background: "#e94560", color: "#fff", cursor: "pointer", fontSize: "0.8rem", fontWeight: 600 }}>Push Overlay</button>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}