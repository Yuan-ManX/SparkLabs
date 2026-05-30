"use client";

import { useState, useEffect, useCallback } from "react";

const API_BASE = "http://localhost:8000/api/agent";

interface SubsystemStats {
  active_emitters: number;
  total_configs: number;
  force_fields: number;
  alive_particles: number;
  [key: string]: any;
}

export default function ParticleEmitterPanel() {
  const [stats, setStats] = useState<SubsystemStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");

  const [configName, setConfigName] = useState("");
  const [emissionRate, setEmissionRate] = useState("50");
  const [maxParticles, setMaxParticles] = useState("500");
  const [lifetimeMin, setLifetimeMin] = useState("1.0");
  const [lifetimeMax, setLifetimeMax] = useState("3.0");
  const [shape, setShape] = useState("point");

  const [presetEffect, setPresetEffect] = useState("fire");
  const [posX, setPosX] = useState("0");
  const [posY, setPosY] = useState("0");
  const [posZ, setPosZ] = useState("0");

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/particle-emitter/stats`);
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

  const handleCreateConfig = async () => {
    if (!configName.trim()) { showMessage("Config name is required"); return; }
    try {
      const res = await fetch(`${API_BASE}/particle-emitter/create-config`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: configName, emission_rate: parseFloat(emissionRate), max_particles: parseInt(maxParticles, 10), lifetime_min: parseFloat(lifetimeMin), lifetime_max: parseFloat(lifetimeMax), shape }),
      });
      const data = await res.json();
      if (data.error) showMessage(`Error: ${data.error}`);
      else { showMessage("Config created"); setConfigName(""); fetchStats(); }
    } catch { showMessage("Failed to create config"); }
  };

  const handleSpawnPreset = async () => {
    try {
      const res = await fetch(`${API_BASE}/particle-emitter/spawn-preset`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ effect: presetEffect, position: [parseFloat(posX), parseFloat(posY), parseFloat(posZ)] }),
      });
      const data = await res.json();
      if (data.error) showMessage(`Error: ${data.error}`);
      else { showMessage("Preset spawned"); fetchStats(); }
    } catch { showMessage("Failed to spawn preset"); }
  };

  return (
    <div style={{ padding: "1.5rem", color: "#e0e0e0" }}>
      <h2 style={{ fontSize: "1.5rem", fontWeight: 700, marginBottom: "1rem", color: "#ffffff" }}>
        Particle Emitter ✨
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
              <h4 style={{ fontSize: "0.8rem", color: "#aaa", marginBottom: "0.5rem" }}>Create Emitter Config</h4>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                <input type="text" placeholder="Config Name" value={configName} onChange={(e) => setConfigName(e.target.value)}
                  style={{ padding: "0.5rem", borderRadius: "0.375rem", border: "1px solid #2a2a4a", background: "#0d0d1a", color: "#e0e0e0", fontSize: "0.8rem" }} />
                <div style={{ display: "flex", gap: "0.5rem" }}>
                  <input type="number" placeholder="Rate" value={emissionRate} onChange={(e) => setEmissionRate(e.target.value)} min="1" max="10000"
                    style={{ flex: "1", padding: "0.5rem", borderRadius: "0.375rem", border: "1px solid #2a2a4a", background: "#0d0d1a", color: "#e0e0e0", fontSize: "0.8rem" }} />
                  <input type="number" placeholder="Max" value={maxParticles} onChange={(e) => setMaxParticles(e.target.value)} min="1" max="100000"
                    style={{ flex: "1", padding: "0.5rem", borderRadius: "0.375rem", border: "1px solid #2a2a4a", background: "#0d0d1a", color: "#e0e0e0", fontSize: "0.8rem" }} />
                </div>
                <div style={{ display: "flex", gap: "0.5rem" }}>
                  <input type="number" placeholder="Life Min" value={lifetimeMin} onChange={(e) => setLifetimeMin(e.target.value)} min="0.1" max="60" step="0.1"
                    style={{ flex: "1", padding: "0.5rem", borderRadius: "0.375rem", border: "1px solid #2a2a4a", background: "#0d0d1a", color: "#e0e0e0", fontSize: "0.8rem" }} />
                  <input type="number" placeholder="Life Max" value={lifetimeMax} onChange={(e) => setLifetimeMax(e.target.value)} min="0.1" max="60" step="0.1"
                    style={{ flex: "1", padding: "0.5rem", borderRadius: "0.375rem", border: "1px solid #2a2a4a", background: "#0d0d1a", color: "#e0e0e0", fontSize: "0.8rem" }} />
                </div>
                <select value={shape} onChange={(e) => setShape(e.target.value)}
                  style={{ padding: "0.5rem", borderRadius: "0.375rem", border: "1px solid #2a2a4a", background: "#0d0d1a", color: "#e0e0e0", fontSize: "0.8rem" }}>
                  <option value="point">Point</option><option value="sphere">Sphere</option>
                  <option value="cone">Cone</option><option value="box">Box</option>
                  <option value="circle">Circle</option>
                </select>
                <button onClick={handleCreateConfig} style={{ padding: "0.5rem 1rem", borderRadius: "0.375rem", border: "none", background: "#e94560", color: "#fff", cursor: "pointer", fontSize: "0.8rem", fontWeight: 600, alignSelf: "flex-start" }}>
                  Create Config
                </button>
              </div>
            </div>

            <div style={{ background: "#1a1a2e", borderRadius: "0.5rem", padding: "0.75rem", border: "1px solid #2a2a4a" }}>
              <h4 style={{ fontSize: "0.8rem", color: "#aaa", marginBottom: "0.5rem" }}>Spawn Preset Effect</h4>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                <select value={presetEffect} onChange={(e) => setPresetEffect(e.target.value)}
                  style={{ padding: "0.5rem", borderRadius: "0.375rem", border: "1px solid #2a2a4a", background: "#0d0d1a", color: "#e0e0e0", fontSize: "0.8rem" }}>
                  <option value="fire">Fire</option><option value="smoke">Smoke</option>
                  <option value="magic_sparkle">Magic Sparkle</option><option value="explosion">Explosion</option>
                  <option value="rain">Rain</option><option value="snow">Snow</option>
                  <option value="confetti">Confetti</option><option value="bubbles">Bubbles</option>
                  <option value="sparks">Spark</option><option value="dust">Dust</option>
                </select>
                <div style={{ display: "flex", gap: "0.5rem" }}>
                  <input type="number" placeholder="X" value={posX} onChange={(e) => setPosX(e.target.value)} step="0.1"
                    style={{ flex: "1", padding: "0.5rem", borderRadius: "0.375rem", border: "1px solid #2a2a4a", background: "#0d0d1a", color: "#e0e0e0", fontSize: "0.8rem" }} />
                  <input type="number" placeholder="Y" value={posY} onChange={(e) => setPosY(e.target.value)} step="0.1"
                    style={{ flex: "1", padding: "0.5rem", borderRadius: "0.375rem", border: "1px solid #2a2a4a", background: "#0d0d1a", color: "#e0e0e0", fontSize: "0.8rem" }} />
                  <input type="number" placeholder="Z" value={posZ} onChange={(e) => setPosZ(e.target.value)} step="0.1"
                    style={{ flex: "1", padding: "0.5rem", borderRadius: "0.375rem", border: "1px solid #2a2a4a", background: "#0d0d1a", color: "#e0e0e0", fontSize: "0.8rem" }} />
                </div>
                <button onClick={handleSpawnPreset} style={{ padding: "0.5rem 1rem", borderRadius: "0.375rem", border: "none", background: "#e94560", color: "#fff", cursor: "pointer", fontSize: "0.8rem", fontWeight: 600, alignSelf: "flex-start" }}>
                  Spawn Preset
                </button>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}