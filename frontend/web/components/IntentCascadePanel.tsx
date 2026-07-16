"use client";

import { useState, useEffect, useCallback } from "react";
import { API_BASE as API_ROOT } from "../utils/api";

const API_BASE = `${API_ROOT}/agent`;

interface SubsystemStats {
  total_resolutions: number;
  domain_distribution: Record<string, number>;
  cascade_paths: number;
}

export default function IntentCascadePanel() {
  const [stats, setStats] = useState<SubsystemStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");

  const [resolveText, setResolveText] = useState("");
  const [resolveContext, setResolveContext] = useState("");
  const [resolveStrategy, setResolveStrategy] = useState("recursive");
  const [ruleDomain, setRuleDomain] = useState("");
  const [rulePatterns, setRulePatterns] = useState("");
  const [ruleAction, setRuleAction] = useState("");

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/intent-cascade/stats`);
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

  const handleResolve = async () => {
    if (!resolveText.trim()) {
      showMessage("Intent text is required");
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/intent-cascade/resolve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: resolveText,
          context: resolveContext,
          strategy: resolveStrategy,
        }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(`Error: ${data.error}`);
      } else {
        showMessage("Intent resolved successfully");
        setResolveText("");
        setResolveContext("");
        fetchStats();
      }
    } catch {
      showMessage("Failed to resolve intent");
    }
  };

  const handleAddRules = async () => {
    if (!ruleDomain.trim() || !rulePatterns.trim() || !ruleAction.trim()) {
      showMessage("Domain, patterns, and action are required");
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/intent-cascade/rules`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          domain: ruleDomain,
          patterns: rulePatterns.split(",").map((p) => p.trim()),
          action: ruleAction,
        }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(`Error: ${data.error}`);
      } else {
        showMessage("Cascade rules added successfully");
        setRuleDomain("");
        setRulePatterns("");
        setRuleAction("");
        fetchStats();
      }
    } catch {
      showMessage("Failed to add cascade rules");
    }
  };

  const formatDomainDistribution = (dist: Record<string, number>) => {
    return Object.entries(dist)
      .map(([k, v]) => `${k}: ${v}`)
      .join(", ");
  };

  return (
    <div style={{ padding: "1.5rem", color: "#e0e0e0" }}>
      <h2 style={{ fontSize: "1.5rem", fontWeight: 700, marginBottom: "1rem", color: "#ffffff" }}>
        Intent Cascade 🔀
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
                  <div style={{ fontSize: "0.7rem", color: "#666", textTransform: "uppercase" }}>Total Resolutions</div>
                  <div style={{ fontSize: "1.2rem", fontWeight: 700, color: "#e94560" }}>
                    {stats.total_resolutions.toLocaleString()}
                  </div>
                </div>
                <div style={{
                  background: "#1a1a2e", borderRadius: "0.5rem", padding: "0.75rem",
                  border: "1px solid #2a2a4a"
                }}>
                  <div style={{ fontSize: "0.7rem", color: "#666", textTransform: "uppercase" }}>Domain Distribution</div>
                  <div style={{ fontSize: "0.8rem", fontWeight: 600, color: "#e94560" }}>
                    {formatDomainDistribution(stats.domain_distribution)}
                  </div>
                </div>
                <div style={{
                  background: "#1a1a2e", borderRadius: "0.5rem", padding: "0.75rem",
                  border: "1px solid #2a2a4a"
                }}>
                  <div style={{ fontSize: "0.7rem", color: "#666", textTransform: "uppercase" }}>Cascade Paths</div>
                  <div style={{ fontSize: "1.2rem", fontWeight: 700, color: "#e94560" }}>
                    {stats.cascade_paths.toLocaleString()}
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
              <h4 style={{ fontSize: "0.8rem", color: "#aaa", marginBottom: "0.5rem" }}>Resolve Intent</h4>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                <input
                  type="text"
                  placeholder="Intent text"
                  value={resolveText}
                  onChange={(e) => setResolveText(e.target.value)}
                  style={{
                    padding: "0.5rem", borderRadius: "0.375rem",
                    border: "1px solid #2a2a4a", background: "#0d0d0d", color: "#e0e0e0",
                    fontSize: "0.8rem"
                  }}
                />
                <textarea
                  placeholder="Context (optional)"
                  value={resolveContext}
                  onChange={(e) => setResolveContext(e.target.value)}
                  rows={2}
                  style={{
                    padding: "0.5rem", borderRadius: "0.375rem",
                    border: "1px solid #2a2a4a", background: "#0d0d0d", color: "#e0e0e0",
                    fontSize: "0.8rem", resize: "vertical"
                  }}
                />
                <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                  <select
                    value={resolveStrategy}
                    onChange={(e) => setResolveStrategy(e.target.value)}
                    style={{
                      padding: "0.5rem", borderRadius: "0.375rem",
                      border: "1px solid #2a2a4a", background: "#0d0d0d", color: "#e0e0e0",
                      fontSize: "0.8rem"
                    }}
                  >
                    <option value="recursive">Recursive</option>
                    <option value="breadth-first">Breadth-First</option>
                    <option value="depth-first">Depth-First</option>
                    <option value="priority">Priority</option>
                  </select>
                  <button
                    onClick={handleResolve}
                    style={{
                      padding: "0.5rem 1rem", borderRadius: "0.375rem",
                      border: "none", background: "#e94560", color: "#fff",
                      cursor: "pointer", fontSize: "0.8rem", fontWeight: 600
                    }}
                  >
                    Resolve
                  </button>
                </div>
              </div>
            </div>

            <div style={{
              background: "#1a1a2e", borderRadius: "0.5rem", padding: "0.75rem",
              border: "1px solid #2a2a4a"
            }}>
              <h4 style={{ fontSize: "0.8rem", color: "#aaa", marginBottom: "0.5rem" }}>Add Cascade Rules</h4>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                <input
                  type="text"
                  placeholder="Domain"
                  value={ruleDomain}
                  onChange={(e) => setRuleDomain(e.target.value)}
                  style={{
                    padding: "0.5rem", borderRadius: "0.375rem",
                    border: "1px solid #2a2a4a", background: "#0d0d0d", color: "#e0e0e0",
                    fontSize: "0.8rem"
                  }}
                />
                <input
                  type="text"
                  placeholder="Patterns (comma-separated)"
                  value={rulePatterns}
                  onChange={(e) => setRulePatterns(e.target.value)}
                  style={{
                    padding: "0.5rem", borderRadius: "0.375rem",
                    border: "1px solid #2a2a4a", background: "#0d0d0d", color: "#e0e0e0",
                    fontSize: "0.8rem"
                  }}
                />
                <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                  <input
                    type="text"
                    placeholder="Action"
                    value={ruleAction}
                    onChange={(e) => setRuleAction(e.target.value)}
                    style={{
                      flex: 1, padding: "0.5rem", borderRadius: "0.375rem",
                      border: "1px solid #2a2a4a", background: "#0d0d0d", color: "#e0e0e0",
                      fontSize: "0.8rem"
                    }}
                  />
                  <button
                    onClick={handleAddRules}
                    style={{
                      padding: "0.5rem 1rem", borderRadius: "0.375rem",
                      border: "none", background: "#e94560", color: "#fff",
                      cursor: "pointer", fontSize: "0.8rem", fontWeight: 600
                    }}
                  >
                    Add Rules
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