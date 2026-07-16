"use client";

import { useState, useEffect, useCallback } from "react";
import { API_BASE as API_ROOT } from "../utils/api";

const API_BASE = `${API_ROOT}/engine`;

interface PlatformInfo {
  os_type: string;
  architecture: string;
  os_version: string;
  python_version: string;
  cpu_count: number;
  total_memory_mb: number;
  gpu_available: boolean;
  gpu_name: string;
  display_count: number;
  hostname: string;
}

interface SystemStats {
  platform: PlatformInfo;
  profile: string;
  uptime_seconds: number;
  budgets: { total: number; total_reserved_memory_mb: number; total_reserved_cpu: number };
  dependencies: { total: number; resolved: number; missing: number; incompatible: number };
  sandboxes: { total: number; by_level: Record<string, number> };
  initialized_subsystems: string[];
  env_variables_count: number;
  snapshots_count: number;
  resource_usage: { cpu_percent: number; memory_used_mb: number; memory_total_mb: number; memory_percent: number };
}

interface HealthInfo {
  healthy: boolean;
  issues: string[];
  profile: string;
  uptime_seconds: number;
  initialized_subsystems: string[];
  total_dependencies: number;
  total_sandboxes: number;
}

interface ResourceBudget {
  id: string;
  category: string;
  cpu_cores: number;
  memory_mb: number;
  gpu_memory_mb: number;
  priority: number;
  enabled: boolean;
}

interface DependencyNode {
  id: string;
  name: string;
  version: string;
  subsystem: string;
  status: string;
  dependencies: string[];
  optional: boolean;
  loaded: boolean;
}

interface SandboxConfig {
  id: string;
  subsystem: string;
  isolation_level: string;
  max_memory_mb: number;
  max_cpu_time_ms: number;
  network_access: boolean;
  file_access: boolean;
}

interface DependencyGraph {
  nodes: { id: string; name: string; subsystem: string; status: string }[];
  edges: { from: string; to: string }[];
}

type TabId = "overview" | "budgets" | "dependencies" | "sandboxes" | "env";

export default function EngineEnvironmentManagerPanel() {
  const [activeTab, setActiveTab] = useState<TabId>("overview");
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [health, setHealth] = useState<HealthInfo | null>(null);
  const [budgets, setBudgets] = useState<ResourceBudget[]>([]);
  const [dependencies, setDependencies] = useState<DependencyNode[]>([]);
  const [depGraph, setDepGraph] = useState<DependencyGraph | null>(null);
  const [sandboxes, setSandboxes] = useState<SandboxConfig[]>([]);
  const [subsystems, setSubsystems] = useState<string[]>([]);
  const [envVars, setEnvVars] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");

  // Budget form
  const [budgetCategory, setBudgetCategory] = useState("general");
  const [budgetCpu, setBudgetCpu] = useState("1.0");
  const [budgetMem, setBudgetMem] = useState("256");

  // Dependency form
  const [depName, setDepName] = useState("");
  const [depVersion, setDepVersion] = useState("1.0.0");
  const [depSubsystem, setDepSubsystem] = useState("custom");

  // Sandbox form
  const [sbSubsystem, setSbSubsystem] = useState("custom");
  const [sbIsolation, setSbIsolation] = useState("none");
  const [sbMaxMem, setSbMaxMem] = useState("512");

  // Env var form
  const [envKey, setEnvKey] = useState("");
  const [envValue, setEnvValue] = useState("");

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/environment/stats`);
      const data = await res.json();
      if (!data.error) setStats(data);
    } catch {}
  }, []);

  const fetchHealth = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/environment/health`);
      const data = await res.json();
      if (!data.error) setHealth(data);
    } catch {}
  }, []);

  const fetchBudgets = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/environment/budgets`);
      const data = await res.json();
      if (data.budgets) setBudgets(data.budgets);
    } catch {}
  }, []);

  const fetchDependencies = useCallback(async () => {
    try {
      const [depsRes, graphRes] = await Promise.all([
        fetch(`${API_BASE}/environment/dependencies`),
        fetch(`${API_BASE}/environment/dependencies/graph`),
      ]);
      const depsData = await depsRes.json();
      const graphData = await graphRes.json();
      if (depsData.dependencies) setDependencies(depsData.dependencies);
      if (!graphData.error) setDepGraph(graphData);
    } catch {}
  }, []);

  const fetchSandboxes = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/environment/sandboxes`);
      const data = await res.json();
      if (data.sandboxes) setSandboxes(data.sandboxes);
    } catch {}
  }, []);

  const fetchSubsystems = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/environment/subsystems`);
      const data = await res.json();
      if (data.subsystems) setSubsystems(data.subsystems);
    } catch {}
  }, []);

  const fetchEnvVars = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/environment/env-vars`);
      const data = await res.json();
      if (data.variables) setEnvVars(data.variables);
    } catch {}
  }, []);

  useEffect(() => {
    fetchStats();
    fetchHealth();
    const interval = setInterval(fetchStats, 15000);
    return () => clearInterval(interval);
  }, [fetchStats, fetchHealth]);

  useEffect(() => {
    if (activeTab === "budgets") fetchBudgets();
    if (activeTab === "dependencies") fetchDependencies();
    if (activeTab === "sandboxes") fetchSandboxes();
    if (activeTab === "env") fetchEnvVars();
    fetchSubsystems();
  }, [activeTab, fetchBudgets, fetchDependencies, fetchSandboxes, fetchSubsystems, fetchEnvVars]);

  const showMessage = (msg: string) => {
    setMessage(msg);
    setTimeout(() => setMessage(""), 3000);
  };

  const handleCreateBudget = async () => {
    try {
      const res = await fetch(`${API_BASE}/environment/budgets`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          category: budgetCategory,
          cpu_cores: parseFloat(budgetCpu),
          memory_mb: parseFloat(budgetMem),
          priority: 0,
        }),
      });
      const data = await res.json();
      if (!data.error) {
        showMessage("Budget created");
        fetchBudgets();
      }
    } catch {
      showMessage("Failed to create budget");
    }
  };

  const handleRegisterDependency = async () => {
    if (!depName.trim()) return;
    try {
      const res = await fetch(`${API_BASE}/environment/dependencies`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: depName,
          version: depVersion,
          subsystem: depSubsystem,
        }),
      });
      const data = await res.json();
      if (!data.error) {
        showMessage("Dependency registered");
        fetchDependencies();
        setDepName("");
      }
    } catch {
      showMessage("Failed to register dependency");
    }
  };

  const handleCreateSandbox = async () => {
    try {
      const res = await fetch(`${API_BASE}/environment/sandboxes`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          subsystem: sbSubsystem,
          isolation_level: sbIsolation,
          max_memory_mb: parseFloat(sbMaxMem),
        }),
      });
      const data = await res.json();
      if (!data.error) {
        showMessage("Sandbox created");
        fetchSandboxes();
      }
    } catch {
      showMessage("Failed to create sandbox");
    }
  };

  const handleInitializeSubsystem = async (subsystem: string) => {
    try {
      const res = await fetch(`${API_BASE}/environment/subsystems/${subsystem}/initialize`, {
        method: "POST",
      });
      const data = await res.json();
      if (!data.error) {
        showMessage(`Initialized ${subsystem}: ${data.resolved} resolved, ${data.failed} failed`);
        fetchSubsystems();
      }
    } catch {
      showMessage("Failed to initialize subsystem");
    }
  };

  const handleSetEnvVar = async () => {
    if (!envKey.trim()) return;
    try {
      const res = await fetch(`${API_BASE}/environment/env-vars`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ key: envKey, value: envValue }),
      });
      const data = await res.json();
      if (data.success) {
        showMessage(`Set ${envKey}`);
        fetchEnvVars();
        setEnvKey("");
        setEnvValue("");
      }
    } catch {
      showMessage("Failed to set env var");
    }
  };

  const handleCreateSnapshot = async () => {
    try {
      await fetch(`${API_BASE}/environment/snapshots`, { method: "POST" });
      showMessage("Snapshot created");
    } catch {
      showMessage("Failed to create snapshot");
    }
  };

  const TABS: { id: TabId; label: string }[] = [
    { id: "overview", label: "Overview" },
    { id: "budgets", label: "Budgets" },
    { id: "dependencies", label: "Dependencies" },
    { id: "sandboxes", label: "Sandboxes" },
    { id: "env", label: "Environment" },
  ];

  const CATEGORIES = ["rendering", "physics", "audio", "ai", "network", "io", "general"];
  const SUBSYSTEM_TYPES = ["render", "physics", "audio", "input", "network", "ai", "script", "asset", "scene", "ui", "custom"];
  const ISOLATION_LEVELS = ["none", "process", "thread", "container", "full"];

  if (loading) {
    return (
      <div style={{ padding: 24, color: "#a0a0b0" }}>
        Loading Environment Manager...
      </div>
    );
  }

  return (
    <div style={{ padding: 24, color: "#e0e0e0" }}>
      <h2 style={{ margin: "0 0 8px 0", fontSize: 20, color: "#fff" }}>
        Environment Manager
      </h2>
      <p style={{ margin: "0 0 16px 0", fontSize: 12, color: "#888" }}>
        Engine runtime environment lifecycle, resource allocation, and dependency management
      </p>

      {/* Tab Navigation */}
      <div style={{ display: "flex", gap: 4, marginBottom: 16, borderBottom: "1px solid #333" }}>
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              padding: "8px 16px",
              background: "none",
              border: "none",
              borderBottom: activeTab === tab.id ? "2px solid #10b981" : "2px solid transparent",
              color: activeTab === tab.id ? "#10b981" : "#888",
              cursor: "pointer",
              fontSize: 13,
              fontWeight: activeTab === tab.id ? 600 : 400,
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {message && (
        <div style={{
          padding: "8px 12px",
          background: "#1a1a2e",
          border: "1px solid #10b981",
          borderRadius: 6,
          marginBottom: 12,
          fontSize: 12,
          color: "#6ee7b7",
        }}>
          {message}
        </div>
      )}

      {/* Overview Tab */}
      {activeTab === "overview" && (
        <div>
          {/* Health Status */}
          {health && (
            <div style={{
              padding: "12px 16px",
              background: health.healthy ? "#064e3b" : "#7f1d1d",
              borderRadius: 8,
              marginBottom: 16,
              display: "flex",
              alignItems: "center",
              gap: 12,
            }}>
              <div style={{
                width: 12, height: 12, borderRadius: "50%",
                background: health.healthy ? "#10b981" : "#ef4444",
              }} />
              <span style={{ fontSize: 14, fontWeight: 600 }}>
                {health.healthy ? "System Healthy" : "Issues Detected"}
              </span>
              <span style={{ fontSize: 12, color: "#aaa" }}>
                {health.uptime_seconds.toFixed(0)}s uptime
              </span>
            </div>
          )}

          {health?.issues && health.issues.length > 0 && (
            <div style={{ marginBottom: 16 }}>
              {health.issues.map((issue, i) => (
                <div key={i} style={{
                  padding: "6px 12px",
                  background: "#1a1a2e",
                  border: "1px solid #ef444466",
                  borderRadius: 4,
                  fontSize: 12,
                  color: "#fca5a5",
                  marginBottom: 4,
                }}>
                  {issue}
                </div>
              ))}
            </div>
          )}

          {/* Platform */}
          {stats?.platform && (
            <div style={{ marginBottom: 16 }}>
              <h3 style={{ fontSize: 14, color: "#aaa", margin: "0 0 8px" }}>Platform</h3>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))", gap: 8 }}>
                <StatCard label="OS" value={stats.platform.os_type} />
                <StatCard label="Architecture" value={stats.platform.architecture} />
                <StatCard label="CPU Cores" value={String(stats.platform.cpu_count)} />
                <StatCard label="Memory" value={`${stats.platform.total_memory_mb.toFixed(0)} MB`} />
                <StatCard label="Python" value={stats.platform.python_version} />
                <StatCard label="Hostname" value={stats.platform.hostname} />
              </div>
            </div>
          )}

          {/* Resource Usage */}
          {stats?.resource_usage && (
            <div style={{ marginBottom: 16 }}>
              <h3 style={{ fontSize: 14, color: "#aaa", margin: "0 0 8px" }}>Resource Usage</h3>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))", gap: 8 }}>
                <StatCard label="CPU" value={`${stats.resource_usage.cpu_percent.toFixed(1)}%`} />
                <StatCard label="Memory Used" value={`${stats.resource_usage.memory_used_mb.toFixed(0)} MB`} />
                <StatCard label="Memory Total" value={`${stats.resource_usage.memory_total_mb.toFixed(0)} MB`} />
                <StatCard label="Memory %" value={`${stats.resource_usage.memory_percent.toFixed(1)}%`} />
              </div>
            </div>
          )}

          {/* Subsystems */}
          <div style={{ marginBottom: 16 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
              <h3 style={{ fontSize: 14, color: "#aaa", margin: 0 }}>Initialized Subsystems</h3>
              <button onClick={handleCreateSnapshot} style={buttonStyle}>Create Snapshot</button>
            </div>
            {subsystems.length > 0 ? (
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                {subsystems.map((s) => (
                  <span key={s} style={{
                    padding: "4px 10px",
                    background: "#064e3b",
                    borderRadius: 4,
                    fontSize: 11,
                    color: "#6ee7b7",
                  }}>
                    {s}
                  </span>
                ))}
              </div>
            ) : (
              <p style={{ color: "#666", fontSize: 12 }}>No subsystems initialized</p>
            )}
          </div>

          {/* Quick Stats */}
          {stats && (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(150px, 1fr))", gap: 8 }}>
              <StatCard label="Profile" value={stats.profile} />
              <StatCard label="Budget Count" value={String(stats.budgets.total)} />
              <StatCard label="Dependencies" value={`${stats.dependencies.resolved}/${stats.dependencies.total}`} />
              <StatCard label="Sandboxes" value={String(stats.sandboxes.total)} />
              <StatCard label="Env Vars" value={String(stats.env_variables_count)} />
              <StatCard label="Snapshots" value={String(stats.snapshots_count)} />
            </div>
          )}
        </div>
      )}

      {/* Budgets Tab */}
      {activeTab === "budgets" && (
        <div>
          <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap", alignItems: "center" }}>
            <select value={budgetCategory} onChange={(e) => setBudgetCategory(e.target.value)}
              style={selectStyle}>
              {CATEGORIES.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
            <input type="number" value={budgetCpu} onChange={(e) => setBudgetCpu(e.target.value)}
              placeholder="CPU Cores" style={{ ...inputStyle, width: 100 }} />
            <input type="number" value={budgetMem} onChange={(e) => setBudgetMem(e.target.value)}
              placeholder="Memory MB" style={{ ...inputStyle, width: 120 }} />
            <button onClick={handleCreateBudget} style={buttonStyle}>Create Budget</button>
          </div>

          {budgets.length > 0 ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {budgets.map((b) => (
                <div key={b.id} style={{
                  padding: "10px 14px",
                  background: "#1a1a2e",
                  borderRadius: 6,
                  fontSize: 12,
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}>
                  <div>
                    <span style={{ color: "#10b981", fontWeight: 600 }}>{b.category}</span>
                    <span style={{ color: "#888", marginLeft: 12 }}>
                      CPU: {b.cpu_cores} | Mem: {b.memory_mb}MB | GPU: {b.gpu_memory_mb}MB
                    </span>
                  </div>
                  <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
                    <span style={{ color: "#888" }}>Priority: {b.priority}</span>
                    <span style={{
                      color: b.enabled ? "#10b981" : "#ef4444",
                      fontSize: 11,
                    }}>
                      {b.enabled ? "Enabled" : "Disabled"}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p style={{ color: "#666", fontSize: 12 }}>No budgets configured</p>
          )}
        </div>
      )}

      {/* Dependencies Tab */}
      {activeTab === "dependencies" && (
        <div>
          <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap", alignItems: "center" }}>
            <input type="text" value={depName} onChange={(e) => setDepName(e.target.value)}
              placeholder="Dependency name" style={inputStyle} />
            <input type="text" value={depVersion} onChange={(e) => setDepVersion(e.target.value)}
              placeholder="Version" style={{ ...inputStyle, width: 100 }} />
            <select value={depSubsystem} onChange={(e) => setDepSubsystem(e.target.value)}
              style={selectStyle}>
              {SUBSYSTEM_TYPES.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
            <button onClick={handleRegisterDependency} style={buttonStyle}>Register</button>
          </div>

          {depGraph && (
            <div style={{ marginBottom: 16 }}>
              <h4 style={{ fontSize: 13, color: "#aaa", margin: "0 0 8px" }}>
                Graph ({depGraph.nodes.length} nodes, {depGraph.edges.length} edges)
              </h4>
            </div>
          )}

          {dependencies.length > 0 ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {dependencies.map((d) => (
                <div key={d.id} style={{
                  padding: "10px 14px",
                  background: "#1a1a2e",
                  borderRadius: 6,
                  fontSize: 12,
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}>
                  <div>
                    <span style={{ color: "#10b981", fontWeight: 600 }}>{d.name}</span>
                    <span style={{ color: "#888", marginLeft: 8 }}>v{d.version}</span>
                    <span style={{ color: "#666", marginLeft: 8 }}>[{d.subsystem}]</span>
                  </div>
                  <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
                    {d.dependencies.length > 0 && (
                      <span style={{ color: "#888", fontSize: 11 }}>
                        deps: {d.dependencies.length}
                      </span>
                    )}
                    <span style={{
                      padding: "2px 8px",
                      borderRadius: 4,
                      fontSize: 11,
                      background: d.status === "resolved" ? "#064e3b" : d.status === "missing" ? "#7f1d1d" : "#1a1a2e",
                      color: d.status === "resolved" ? "#6ee7b7" : d.status === "missing" ? "#fca5a5" : "#fbbf24",
                    }}>
                      {d.status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p style={{ color: "#666", fontSize: 12 }}>No dependencies registered</p>
          )}

          {/* Subsystem Init */}
          <h4 style={{ fontSize: 13, color: "#aaa", margin: "16px 0 8px" }}>Initialize Subsystem</h4>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            {SUBSYSTEM_TYPES.map((s) => (
              <button key={s} onClick={() => handleInitializeSubsystem(s)}
                style={{
                  ...buttonStyle,
                  background: subsystems.includes(s) ? "#064e3b" : "#374151",
                  color: subsystems.includes(s) ? "#6ee7b7" : "#aaa",
                  fontSize: 11,
                }}>
                {s}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Sandboxes Tab */}
      {activeTab === "sandboxes" && (
        <div>
          <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap", alignItems: "center" }}>
            <select value={sbSubsystem} onChange={(e) => setSbSubsystem(e.target.value)}
              style={selectStyle}>
              {SUBSYSTEM_TYPES.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
            <select value={sbIsolation} onChange={(e) => setSbIsolation(e.target.value)}
              style={selectStyle}>
              {ISOLATION_LEVELS.map((l) => (
                <option key={l} value={l}>{l}</option>
              ))}
            </select>
            <input type="number" value={sbMaxMem} onChange={(e) => setSbMaxMem(e.target.value)}
              placeholder="Max Memory MB" style={{ ...inputStyle, width: 130 }} />
            <button onClick={handleCreateSandbox} style={buttonStyle}>Create Sandbox</button>
          </div>

          {sandboxes.length > 0 ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {sandboxes.map((s) => (
                <div key={s.id} style={{
                  padding: "10px 14px",
                  background: "#1a1a2e",
                  borderRadius: 6,
                  fontSize: 12,
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}>
                  <div>
                    <span style={{ color: "#10b981", fontWeight: 600 }}>{s.subsystem}</span>
                    <span style={{ color: "#888", marginLeft: 12 }}>
                      Level: {s.isolation_level}
                    </span>
                  </div>
                  <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
                    <span style={{ color: "#888" }}>Mem: {s.max_memory_mb}MB</span>
                    <span style={{ color: "#888" }}>CPU: {s.max_cpu_time_ms}ms</span>
                    <span style={{
                      color: s.network_access ? "#10b981" : "#888",
                      fontSize: 11,
                    }}>
                      Net: {s.network_access ? "Yes" : "No"}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p style={{ color: "#666", fontSize: 12 }}>No sandboxes configured</p>
          )}
        </div>
      )}

      {/* Environment Tab */}
      {activeTab === "env" && (
        <div>
          <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap", alignItems: "center" }}>
            <input type="text" value={envKey} onChange={(e) => setEnvKey(e.target.value)}
              placeholder="Key" style={inputStyle} />
            <input type="text" value={envValue} onChange={(e) => setEnvValue(e.target.value)}
              placeholder="Value" style={{ ...inputStyle, width: 200 }} />
            <button onClick={handleSetEnvVar} style={buttonStyle}>Set</button>
          </div>

          {Object.keys(envVars).length > 0 ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              {Object.entries(envVars).map(([key, value]) => (
                <div key={key} style={{
                  display: "flex",
                  padding: "8px 12px",
                  background: "#1a1a2e",
                  borderRadius: 6,
                  fontSize: 12,
                }}>
                  <span style={{ color: "#10b981", fontWeight: 600, minWidth: 200, fontFamily: "monospace" }}>
                    {key}
                  </span>
                  <span style={{ color: "#ccc", fontFamily: "monospace", wordBreak: "break-all" }}>
                    {value}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p style={{ color: "#666", fontSize: 12 }}>No environment variables set</p>
          )}
        </div>
      )}
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div style={{
      padding: "10px 14px",
      background: "#1a1a2e",
      borderRadius: 8,
      border: "1px solid #2a2a3e",
    }}>
      <div style={{ fontSize: 11, color: "#888", marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: 14, fontWeight: 600, color: "#10b981" }}>{value}</div>
    </div>
  );
}

const inputStyle: React.CSSProperties = {
  padding: "6px 10px",
  background: "#0d0d0d",
  border: "1px solid #333",
  borderRadius: 4,
  color: "#e0e0e0",
  fontSize: 12,
  width: 160,
};

const selectStyle: React.CSSProperties = {
  padding: "6px 10px",
  background: "#0d0d0d",
  border: "1px solid #333",
  borderRadius: 4,
  color: "#e0e0e0",
  fontSize: 12,
};

const buttonStyle: React.CSSProperties = {
  padding: "6px 14px",
  background: "#10b981",
  color: "#fff",
  border: "none",
  borderRadius: 4,
  cursor: "pointer",
  fontSize: 12,
  fontWeight: 500,
};