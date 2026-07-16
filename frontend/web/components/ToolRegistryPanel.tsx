"use client";

import { useState, useEffect, useCallback } from "react";
import { API_BASE as API_ROOT } from "../utils/api";

const API_BASE = `${API_ROOT}/agent`;

interface SubsystemStats {
  total_tools: number;
  active_tools: number;
  total_invocations: number;
  failed_invocations: number;
  [key: string]: any;
}

export default function ToolRegistryPanel() {
  const [stats, setStats] = useState<SubsystemStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");

  const [toolName, setToolName] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState("utility");
  const [parameters, setParameters] = useState("");

  const [invokeName, setInvokeName] = useState("");
  const [invokeParams, setInvokeParams] = useState("");

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/tool-registry/stats`);
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

  const handleRegister = async () => {
    if (!toolName.trim() || !description.trim()) {
      showMessage("Name and description are required");
      return;
    }
    let parsedParams: Record<string, any> = {};
    if (parameters.trim()) {
      try {
        parsedParams = JSON.parse(parameters);
      } catch {
        showMessage("Parameters must be valid JSON");
        return;
      }
    }
    try {
      const res = await fetch(`${API_BASE}/tool-registry/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: toolName.trim(),
          description: description.trim(),
          category,
          parameters: parsedParams,
        }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(`Error: ${data.error}`);
      } else {
        showMessage("Tool registered successfully");
        setToolName("");
        setDescription("");
        setParameters("");
        fetchStats();
      }
    } catch {
      showMessage("Failed to register tool");
    }
  };

  const handleInvoke = async () => {
    if (!invokeName.trim()) {
      showMessage("Tool name is required");
      return;
    }
    let parsedParams: Record<string, any> = {};
    if (invokeParams.trim()) {
      try {
        parsedParams = JSON.parse(invokeParams);
      } catch {
        showMessage("Parameters must be valid JSON");
        return;
      }
    }
    try {
      const res = await fetch(`${API_BASE}/tool-registry/invoke`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tool_name: invokeName.trim(),
          parameters: parsedParams,
        }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(`Error: ${data.error}`);
      } else {
        showMessage("Tool invoked successfully");
        setInvokeName("");
        setInvokeParams("");
        fetchStats();
      }
    } catch {
      showMessage("Failed to invoke tool");
    }
  };

  return (
    <div style={{ padding: "1.5rem", color: "#e0e0e0" }}>
      <h2 style={{ fontSize: "1.5rem", fontWeight: 700, marginBottom: "1rem", color: "#ffffff" }}>
        Tool Registry 🛠️
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
              <h4 style={{ fontSize: "0.8rem", color: "#aaa", marginBottom: "0.5rem" }}>Register Tool</h4>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                <input
                  type="text"
                  placeholder="Tool Name"
                  value={toolName}
                  onChange={(e) => setToolName(e.target.value)}
                  style={{
                    padding: "0.5rem", borderRadius: "0.375rem",
                    border: "1px solid #2a2a4a", background: "#0d0d0d", color: "#e0e0e0",
                    fontSize: "0.8rem"
                  }}
                />
                <input
                  type="text"
                  placeholder="Description"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  style={{
                    padding: "0.5rem", borderRadius: "0.375rem",
                    border: "1px solid #2a2a4a", background: "#0d0d0d", color: "#e0e0e0",
                    fontSize: "0.8rem"
                  }}
                />
                <div style={{ display: "flex", gap: "0.5rem" }}>
                  <select
                    value={category}
                    onChange={(e) => setCategory(e.target.value)}
                    style={{
                      flex: "1", padding: "0.5rem", borderRadius: "0.375rem",
                      border: "1px solid #2a2a4a", background: "#0d0d0d", color: "#e0e0e0",
                      fontSize: "0.8rem"
                    }}
                  >
                    <option value="utility">Utility</option>
                    <option value="computation">Computation</option>
                    <option value="data_access">Data Access</option>
                    <option value="external_api">External API</option>
                    <option value="rendering">Rendering</option>
                  </select>
                  <input
                    type="text"
                    placeholder="Parameters (JSON)"
                    value={parameters}
                    onChange={(e) => setParameters(e.target.value)}
                    style={{
                      flex: "1", padding: "0.5rem", borderRadius: "0.375rem",
                      border: "1px solid #2a2a4a", background: "#0d0d0d", color: "#e0e0e0",
                      fontSize: "0.8rem"
                    }}
                  />
                </div>
                <button
                  onClick={handleRegister}
                  style={{
                    padding: "0.5rem 1rem", borderRadius: "0.375rem",
                    border: "none", background: "#e94560", color: "#fff",
                    cursor: "pointer", fontSize: "0.8rem", fontWeight: 600,
                    alignSelf: "flex-start"
                  }}
                >
                  Register Tool
                </button>
              </div>
            </div>

            <div style={{
              background: "#1a1a2e", borderRadius: "0.5rem", padding: "0.75rem",
              border: "1px solid #2a2a4a"
            }}>
              <h4 style={{ fontSize: "0.8rem", color: "#aaa", marginBottom: "0.5rem" }}>Invoke Tool</h4>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                <input
                  type="text"
                  placeholder="Tool Name"
                  value={invokeName}
                  onChange={(e) => setInvokeName(e.target.value)}
                  style={{
                    padding: "0.5rem", borderRadius: "0.375rem",
                    border: "1px solid #2a2a4a", background: "#0d0d0d", color: "#e0e0e0",
                    fontSize: "0.8rem"
                  }}
                />
                <input
                  type="text"
                  placeholder="Parameters (JSON)"
                  value={invokeParams}
                  onChange={(e) => setInvokeParams(e.target.value)}
                  style={{
                    padding: "0.5rem", borderRadius: "0.375rem",
                    border: "1px solid #2a2a4a", background: "#0d0d0d", color: "#e0e0e0",
                    fontSize: "0.8rem"
                  }}
                />
                <button
                  onClick={handleInvoke}
                  style={{
                    padding: "0.5rem 1rem", borderRadius: "0.375rem",
                    border: "none", background: "#e94560", color: "#fff",
                    cursor: "pointer", fontSize: "0.8rem", fontWeight: 600,
                    alignSelf: "flex-start"
                  }}
                >
                  Invoke Tool
                </button>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}