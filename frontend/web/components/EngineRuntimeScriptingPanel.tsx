"use client";

import React, { useState, useEffect, useCallback } from "react";

// ── Types & Interfaces ──────────────────────────────────────────────

type TabId = "scripts" | "instances" | "events" | "scheduler" | "status";

type ScriptLanguage =
  | "Python"
  | "Lua"
  | "VisualBlock"
  | "Expression"
  | "StateMachine";

type ScriptScope =
  | "global"
  | "scene"
  | "entity"
  | "component"
  | "system"
  | "ui";

type InstanceState = "running" | "paused" | "error" | "completed";

type EventType =
  | "ON_START"
  | "ON_UPDATE"
  | "ON_COLLISION"
  | "ON_INPUT"
  | "ON_TIMER"
  | "ON_TRIGGER"
  | "ON_DESTROY"
  | "ON_CUSTOM";

interface ScriptInfo {
  id: string;
  name: string;
  language: ScriptLanguage;
  scope: ScriptScope;
  compiled: boolean;
}

interface InstanceInfo {
  id: string;
  script_name: string;
  target_entity: string;
  state: InstanceState;
  execution_count: number;
}

interface ExecutionResult {
  instance_id: string;
  output: string;
  delta_time: number;
}

interface StatusInfo {
  scripts_count: number;
  instances_count: number;
  running_count: number;
  paused_count: number;
  error_count: number;
  sandboxes_count: number;
  events_registered: number;
  scheduled_count: number;
}

interface ScheduleResult {
  schedule_id: string;
}

// ── Helpers ─────────────────────────────────────────────────────────

const API_BASE = "http://localhost:8000/api/engine";

const uid = (): string =>
  `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const LANGUAGES: ScriptLanguage[] = [
  "Python",
  "Lua",
  "VisualBlock",
  "Expression",
  "StateMachine",
];

const SCOPES: ScriptScope[] = [
  "global",
  "scene",
  "entity",
  "component",
  "system",
  "ui",
];

const EVENT_TYPES: EventType[] = [
  "ON_START",
  "ON_UPDATE",
  "ON_COLLISION",
  "ON_INPUT",
  "ON_TIMER",
  "ON_TRIGGER",
  "ON_DESTROY",
  "ON_CUSTOM",
];

const instanceStateColor = (s: InstanceState): string =>
  s === "running"
    ? "#6bcb77"
    : s === "paused"
    ? "#fdcb6e"
    : s === "error"
    ? "#ff6b6b"
    : "#888";

// ── Component ───────────────────────────────────────────────────────

const EngineRuntimeScriptingPanel: React.FC = () => {
  // ── Shared state ──────────────────────────────────────────────────
  const [activeTab, setActiveTab] = useState<TabId>("scripts");
  const [message, setMessage] = useState<{
    text: string;
    type: "success" | "error" | "info";
  } | null>(null);
  const [status, setStatus] = useState<StatusInfo | null>(null);

  const showMessage = (
    text: string,
    type: "success" | "error" | "info" = "info"
  ) => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/runtime-scripting/status`);
      const data = await res.json();
      if (!data.error) setStatus(data);
    } catch {
      /* use defaults */
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 15000);
    return () => clearInterval(interval);
  }, [fetchStatus]);

  // ── Scripts Tab state ─────────────────────────────────────────────
  const [scripts, setScripts] = useState<ScriptInfo[]>([]);
  const [scriptName, setScriptName] = useState("");
  const [scriptLanguage, setScriptLanguage] = useState<ScriptLanguage>("Python");
  const [scriptScope, setScriptScope] = useState<ScriptScope>("global");
  const [scriptSource, setScriptSource] = useState("");
  const [scriptEvents, setScriptEvents] = useState("");
  const [hotReloadScriptId, setHotReloadScriptId] = useState("");
  const [hotReloadSource, setHotReloadSource] = useState("");

  // ── Instances Tab state ───────────────────────────────────────────
  const [instances, setInstances] = useState<InstanceInfo[]>([]);
  const [instantiateScriptId, setInstantiateScriptId] = useState("");
  const [targetEntityId, setTargetEntityId] = useState("");
  const [initialVariables, setInitialVariables] = useState("{}");
  const [executeInstanceId, setExecuteInstanceId] = useState("");
  const [executeDeltaTime, setExecuteDeltaTime] = useState("0.016");
  const [varInstanceId, setVarInstanceId] = useState("");
  const [varName, setVarName] = useState("");
  const [varValue, setVarValue] = useState("");

  // ── Events Tab state ──────────────────────────────────────────────
  const [executionResults, setExecutionResults] = useState<
    ExecutionResult[]
  >([]);
  const [eventScriptId, setEventScriptId] = useState("");
  const [eventType, setEventType] = useState<EventType>("ON_START");
  const [eventData, setEventData] = useState("{}");
  const [handlerScriptId, setHandlerScriptId] = useState("");
  const [handlerEventType, setHandlerEventType] =
    useState<EventType>("ON_START");
  const [handlerCode, setHandlerCode] = useState("");

  // ── Scheduler Tab state ───────────────────────────────────────────
  const [schedScriptId, setSchedScriptId] = useState("");
  const [delayMs, setDelayMs] = useState("1000");
  const [repeat, setRepeat] = useState(false);
  const [schedContext, setSchedContext] = useState("{}");
  const [scheduleId, setScheduleId] = useState<string | null>(null);

  // ═══════════════════════════════════════════════════════════════════
  //  SCRIPTS TAB handlers
  // ═══════════════════════════════════════════════════════════════════

  const handleRegisterScript = async () => {
    if (!scriptName.trim()) {
      showMessage("Script name is required", "error");
      return;
    }
    if (!scriptSource.trim()) {
      showMessage("Source code is required", "error");
      return;
    }
    const events = scriptEvents
      .split(",")
      .map((e) => e.trim())
      .filter(Boolean);

    try {
      const res = await fetch(`${API_BASE}/runtime-scripting/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: scriptName.trim(),
          language: scriptLanguage,
          scope: scriptScope,
          source_code: scriptSource,
          events,
        }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(`Error: ${data.error}`, "error");
        return;
      }
      const newScript: ScriptInfo = {
        id: data.id || uid(),
        name: scriptName.trim(),
        language: scriptLanguage,
        scope: scriptScope,
        compiled: false,
      };
      setScripts((prev) => [...prev, newScript]);
      setScriptName("");
      setScriptSource("");
      setScriptEvents("");
      showMessage(`Script "${scriptName}" registered`, "success");
    } catch {
      const newScript: ScriptInfo = {
        id: uid(),
        name: scriptName.trim(),
        language: scriptLanguage,
        scope: scriptScope,
        compiled: false,
      };
      setScripts((prev) => [...prev, newScript]);
      setScriptName("");
      setScriptSource("");
      setScriptEvents("");
      showMessage("Script registered (offline fallback)", "info");
    }
  };

  const handleCompileScript = async (scriptId: string) => {
    try {
      const res = await fetch(`${API_BASE}/runtime-scripting/compile`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ script_id: scriptId }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(`Compile error: ${data.error}`, "error");
        return;
      }
      setScripts((prev) =>
        prev.map((s) => (s.id === scriptId ? { ...s, compiled: true } : s))
      );
      showMessage("Script compiled successfully", "success");
    } catch {
      setScripts((prev) =>
        prev.map((s) => (s.id === scriptId ? { ...s, compiled: true } : s))
      );
      showMessage("Script compiled (offline fallback)", "info");
    }
  };

  const handleHotReload = async () => {
    if (!hotReloadScriptId.trim() || !hotReloadSource.trim()) {
      showMessage("Script ID and new source are required", "error");
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/runtime-scripting/hot-reload`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          script_id: hotReloadScriptId.trim(),
          new_source: hotReloadSource,
        }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(`Hot reload error: ${data.error}`, "error");
        return;
      }
      setHotReloadSource("");
      showMessage("Hot reload successful", "success");
    } catch {
      setHotReloadSource("");
      showMessage("Hot reload (offline fallback)", "info");
    }
  };

  // ═══════════════════════════════════════════════════════════════════
  //  INSTANCES TAB handlers
  // ═══════════════════════════════════════════════════════════════════

  const handleInstantiate = async () => {
    if (!instantiateScriptId.trim() || !targetEntityId.trim()) {
      showMessage("Script ID and target entity are required", "error");
      return;
    }
    let parsedVars: Record<string, any> = {};
    try {
      parsedVars = JSON.parse(initialVariables || "{}");
    } catch {
      showMessage("Invalid JSON in initial variables", "error");
      return;
    }
    try {
      const res = await fetch(
        `${API_BASE}/runtime-scripting/instantiate`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            script_id: instantiateScriptId.trim(),
            target_entity_id: targetEntityId.trim(),
            initial_variables: parsedVars,
          }),
        }
      );
      const data = await res.json();
      if (data.error) {
        showMessage(`Error: ${data.error}`, "error");
        return;
      }
      const script = scripts.find((s) => s.id === instantiateScriptId);
      const newInstance: InstanceInfo = {
        id: data.id || uid(),
        script_name: script?.name || instantiateScriptId,
        target_entity: targetEntityId.trim(),
        state: "running",
        execution_count: 0,
      };
      setInstances((prev) => [...prev, newInstance]);
      setTargetEntityId("");
      setInitialVariables("{}");
      showMessage("Instance created", "success");
    } catch {
      const script = scripts.find((s) => s.id === instantiateScriptId);
      const newInstance: InstanceInfo = {
        id: uid(),
        script_name: script?.name || instantiateScriptId,
        target_entity: targetEntityId.trim(),
        state: "running",
        execution_count: 0,
      };
      setInstances((prev) => [...prev, newInstance]);
      setTargetEntityId("");
      setInitialVariables("{}");
      showMessage("Instance created (offline fallback)", "info");
    }
  };

  const handleExecute = async () => {
    if (!executeInstanceId.trim()) {
      showMessage("Instance ID is required", "error");
      return;
    }
    const dt = parseFloat(executeDeltaTime) || 0.016;
    try {
      const res = await fetch(`${API_BASE}/runtime-scripting/execute`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          instance_id: executeInstanceId.trim(),
          delta_time: dt,
        }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(`Error: ${data.error}`, "error");
        return;
      }
      setInstances((prev) =>
        prev.map((inst) =>
          inst.id === executeInstanceId.trim()
            ? { ...inst, execution_count: inst.execution_count + 1 }
            : inst
        )
      );
      showMessage(`Executed (dt=${dt}s)`, "success");
    } catch {
      setInstances((prev) =>
        prev.map((inst) =>
          inst.id === executeInstanceId.trim()
            ? { ...inst, execution_count: inst.execution_count + 1 }
            : inst
        )
      );
      showMessage("Executed (offline fallback)", "info");
    }
  };

  const handlePauseInstance = async (instanceId: string) => {
    try {
      await fetch(`${API_BASE}/runtime-scripting/pause`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ instance_id: instanceId }),
      });
      setInstances((prev) =>
        prev.map((inst) =>
          inst.id === instanceId ? { ...inst, state: "paused" } : inst
        )
      );
      showMessage("Instance paused", "success");
    } catch {
      setInstances((prev) =>
        prev.map((inst) =>
          inst.id === instanceId ? { ...inst, state: "paused" } : inst
        )
      );
      showMessage("Instance paused (offline fallback)", "info");
    }
  };

  const handleResumeInstance = async (instanceId: string) => {
    try {
      await fetch(`${API_BASE}/runtime-scripting/resume`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ instance_id: instanceId }),
      });
      setInstances((prev) =>
        prev.map((inst) =>
          inst.id === instanceId ? { ...inst, state: "running" } : inst
        )
      );
      showMessage("Instance resumed", "success");
    } catch {
      setInstances((prev) =>
        prev.map((inst) =>
          inst.id === instanceId ? { ...inst, state: "running" } : inst
        )
      );
      showMessage("Instance resumed (offline fallback)", "info");
    }
  };

  const handleSetVariable = async () => {
    if (!varInstanceId.trim() || !varName.trim()) {
      showMessage("Instance ID and variable name are required", "error");
      return;
    }
    try {
      const res = await fetch(
        `${API_BASE}/runtime-scripting/set-variable`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            instance_id: varInstanceId.trim(),
            name: varName.trim(),
            value: varValue,
          }),
        }
      );
      const data = await res.json();
      if (data.error) {
        showMessage(`Error: ${data.error}`, "error");
        return;
      }
      setVarName("");
      setVarValue("");
      showMessage("Variable set", "success");
    } catch {
      setVarName("");
      setVarValue("");
      showMessage("Variable set (offline fallback)", "info");
    }
  };

  // ═══════════════════════════════════════════════════════════════════
  //  EVENTS TAB handlers
  // ═══════════════════════════════════════════════════════════════════

  const handleTriggerEvent = async () => {
    if (!eventScriptId.trim()) {
      showMessage("Script ID is required", "error");
      return;
    }
    let parsedData: Record<string, any> = {};
    try {
      parsedData = JSON.parse(eventData || "{}");
    } catch {
      showMessage("Invalid JSON in event data", "error");
      return;
    }
    try {
      const res = await fetch(
        `${API_BASE}/runtime-scripting/trigger-event`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            script_id: eventScriptId.trim(),
            event_type: eventType,
            event_data: parsedData,
          }),
        }
      );
      const data = await res.json();
      if (data.error) {
        showMessage(`Error: ${data.error}`, "error");
        return;
      }
      setExecutionResults((prev) => [
        ...prev.slice(-9),
        {
          instance_id: eventScriptId.trim(),
          output:
            typeof data.output === "string"
              ? data.output
              : JSON.stringify(data),
          delta_time: data.delta_time || 0,
        },
      ]);
      showMessage(`Event "${eventType}" triggered`, "success");
    } catch {
      setExecutionResults((prev) => [
        ...prev.slice(-9),
        {
          instance_id: eventScriptId.trim(),
          output: `[offline] Event ${eventType} triggered`,
          delta_time: 0,
        },
      ]);
      showMessage("Event triggered (offline fallback)", "info");
    }
  };

  const handleRegisterHandler = async () => {
    if (!handlerScriptId.trim() || !handlerCode.trim()) {
      showMessage("Script ID and handler code are required", "error");
      return;
    }
    try {
      const res = await fetch(
        `${API_BASE}/runtime-scripting/register-handler`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            script_id: handlerScriptId.trim(),
            event_type: handlerEventType,
            handler_code: handlerCode,
          }),
        }
      );
      const data = await res.json();
      if (data.error) {
        showMessage(`Error: ${data.error}`, "error");
        return;
      }
      setHandlerCode("");
      showMessage(
        `Handler for "${handlerEventType}" registered`,
        "success"
      );
    } catch {
      setHandlerCode("");
      showMessage("Handler registered (offline fallback)", "info");
    }
  };

  // ═══════════════════════════════════════════════════════════════════
  //  SCHEDULER TAB handlers
  // ═══════════════════════════════════════════════════════════════════

  const handleSchedule = async () => {
    if (!schedScriptId.trim()) {
      showMessage("Script ID is required", "error");
      return;
    }
    let parsedCtx: Record<string, any> = {};
    try {
      parsedCtx = JSON.parse(schedContext || "{}");
    } catch {
      showMessage("Invalid JSON in context", "error");
      return;
    }
    const ms = parseInt(delayMs) || 1000;
    try {
      const res = await fetch(`${API_BASE}/runtime-scripting/schedule`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          script_id: schedScriptId.trim(),
          delay_ms: ms,
          repeat,
          context: parsedCtx,
        }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(`Error: ${data.error}`, "error");
        return;
      }
      const sid: string =
        (data as ScheduleResult).schedule_id || data.id || uid();
      setScheduleId(sid);
      setDelayMs("1000");
      setRepeat(false);
      setSchedContext("{}");
      showMessage(`Scheduled (ID: ${sid})`, "success");
    } catch {
      const sid = uid();
      setScheduleId(sid);
      setDelayMs("1000");
      setRepeat(false);
      setSchedContext("{}");
      showMessage(`Scheduled (offline, ID: ${sid})`, "info");
    }
  };

  // ═══════════════════════════════════════════════════════════════════
  //  Shared style constants
  // ═══════════════════════════════════════════════════════════════════

  const inputStyle: React.CSSProperties = {
    padding: "6px 10px",
    fontSize: 11,
    backgroundColor: "#141428",
    color: "#ccc",
    border: "1px solid #333",
    borderRadius: 4,
    outline: "none",
  };

  const selectStyle: React.CSSProperties = {
    padding: "6px 10px",
    fontSize: 11,
    backgroundColor: "#141428",
    color: "#ccc",
    border: "1px solid #333",
    borderRadius: 4,
    outline: "none",
  };

  const textareaStyle: React.CSSProperties = {
    padding: "6px 10px",
    fontSize: 11,
    backgroundColor: "#141428",
    color: "#ccc",
    border: "1px solid #333",
    borderRadius: 4,
    outline: "none",
    resize: "vertical",
    fontFamily: "monospace",
  };

  const btnPrimary: React.CSSProperties = {
    padding: "6px 14px",
    backgroundColor: "#2d3a5a",
    color: "#74b9ff",
    border: "1px solid #3d4a6a",
    borderRadius: 4,
    cursor: "pointer",
    fontSize: 11,
    fontWeight: 600,
  };

  const btnSmall: React.CSSProperties = {
    padding: "4px 10px",
    fontSize: 10,
    backgroundColor: "#2d3a5a",
    color: "#74b9ff",
    border: "1px solid #3d4a6a",
    borderRadius: 4,
    cursor: "pointer",
    fontWeight: 600,
  };

  const btnDanger: React.CSSProperties = {
    ...btnSmall,
    backgroundColor: "#3a2d2d",
    color: "#ff6b6b",
    border: "1px solid #5a3d3d",
  };

  const btnSuccess: React.CSSProperties = {
    ...btnSmall,
    backgroundColor: "#2d3a2d",
    color: "#6bcb77",
    border: "1px solid #3d5a3d",
  };

  const panelStyle: React.CSSProperties = {
    padding: 12,
    backgroundColor: "#22223a",
    borderRadius: 6,
    border: "1px solid #2a2a3e",
  };

  const labelStyle: React.CSSProperties = {
    fontSize: 10,
    color: "#888",
    marginBottom: 2,
  };

  const tabItems: { key: TabId; label: string }[] = [
    { key: "scripts", label: "Scripts" },
    { key: "instances", label: "Instances" },
    { key: "events", label: "Events" },
    { key: "scheduler", label: "Scheduler" },
    { key: "status", label: "Status" },
  ];

  // ═══════════════════════════════════════════════════════════════════
  //  Render helper: script selector dropdown
  // ═══════════════════════════════════════════════════════════════════

  const renderScriptSelector = (
    value: string,
    onChange: (v: string) => void
  ) => (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      style={{ ...selectStyle, minWidth: 200 }}
    >
      <option value="">-- Select Script --</option>
      {scripts.map((s) => (
        <option key={s.id} value={s.id}>
          {s.name} ({s.language})
        </option>
      ))}
    </select>
  );

  const renderInstanceSelector = (
    value: string,
    onChange: (v: string) => void
  ) => (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      style={{ ...selectStyle, minWidth: 200 }}
    >
      <option value="">-- Select Instance --</option>
      {instances.map((inst) => (
        <option key={inst.id} value={inst.id}>
          {inst.script_name} → {inst.target_entity}
        </option>
      ))}
    </select>
  );

  // ═══════════════════════════════════════════════════════════════════
  //  Render
  // ═══════════════════════════════════════════════════════════════════

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        backgroundColor: "#1a1a2e",
        color: "#e0e0e0",
        fontFamily: "system-ui, sans-serif",
        fontSize: 13,
      }}
    >
      {/* ── Header ──────────────────────────────────────────────── */}
      <div
        style={{
          padding: "12px 16px",
          borderBottom: "1px solid #2a2a3e",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ fontSize: 18 }}>⚡</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>
            Engine Runtime Scripting
          </span>
        </div>
        <span style={{ fontSize: 10, color: "#888" }}>
          {scripts.length} scripts · {instances.length} instances
        </span>
      </div>

      {/* ── Message Banner ──────────────────────────────────────── */}
      {message && (
        <div
          style={{
            padding: "8px 16px",
            fontSize: 12,
            backgroundColor:
              message.type === "success"
                ? "#1a3a1a"
                : message.type === "error"
                ? "#3a1a1a"
                : "#1a2a3a",
            borderBottom: `1px solid ${
              message.type === "success"
                ? "#2d5a2d"
                : message.type === "error"
                ? "#5a2d2d"
                : "#2a3a4a"
            }`,
            color:
              message.type === "success"
                ? "#6bcb77"
                : message.type === "error"
                ? "#ff6b6b"
                : "#74b9ff",
          }}
        >
          {message.text}
        </div>
      )}

      {/* ── Tab Bar ─────────────────────────────────────────────── */}
      <div style={{ display: "flex", borderBottom: "1px solid #2a2a3e" }}>
        {tabItems.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            style={{
              flex: 1,
              padding: "8px 12px",
              fontSize: 12,
              fontWeight: 600,
              backgroundColor:
                activeTab === tab.key ? "#22223a" : "transparent",
              color: activeTab === tab.key ? "#e0e0e0" : "#888",
              border: "none",
              borderBottom:
                activeTab === tab.key
                  ? "2px solid #74b9ff"
                  : "2px solid transparent",
              cursor: "pointer",
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* ── Tab Content ─────────────────────────────────────────── */}
      <div style={{ flex: 1, overflow: "auto", padding: 12 }}>
        {/* ═══════════════════════════════════════ SCRIPTS ════════ */}
        {activeTab === "scripts" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {/* Register Script Form */}
            <div style={panelStyle}>
              <div
                style={{
                  fontSize: 12,
                  fontWeight: 600,
                  color: "#aaa",
                  marginBottom: 8,
                }}
              >
                Register Script
              </div>
              <div
                style={{
                  display: "flex",
                  gap: 8,
                  flexWrap: "wrap",
                  alignItems: "flex-end",
                }}
              >
                <div style={{ flex: 1, minWidth: 120 }}>
                  <div style={labelStyle}>Name</div>
                  <input
                    value={scriptName}
                    onChange={(e) => setScriptName(e.target.value)}
                    placeholder="my_script"
                    style={{ ...inputStyle, width: "100%" }}
                  />
                </div>
                <div>
                  <div style={labelStyle}>Language</div>
                  <select
                    value={scriptLanguage}
                    onChange={(e) =>
                      setScriptLanguage(e.target.value as ScriptLanguage)
                    }
                    style={selectStyle}
                  >
                    {LANGUAGES.map((l) => (
                      <option key={l} value={l}>
                        {l}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <div style={labelStyle}>Scope</div>
                  <select
                    value={scriptScope}
                    onChange={(e) =>
                      setScriptScope(e.target.value as ScriptScope)
                    }
                    style={selectStyle}
                  >
                    {SCOPES.map((s) => (
                      <option key={s} value={s}>
                        {s}
                      </option>
                    ))}
                  </select>
                </div>
                <div style={{ flex: 1, minWidth: 120 }}>
                  <div style={labelStyle}>Events (comma-separated)</div>
                  <input
                    value={scriptEvents}
                    onChange={(e) => setScriptEvents(e.target.value)}
                    placeholder="ON_START, ON_UPDATE"
                    style={{ ...inputStyle, width: "100%" }}
                  />
                </div>
              </div>
              <div style={{ marginTop: 8 }}>
                <div style={labelStyle}>Source Code</div>
                <textarea
                  value={scriptSource}
                  onChange={(e) => setScriptSource(e.target.value)}
                  placeholder="def on_start(): ..."
                  rows={4}
                  style={{ ...textareaStyle, width: "100%" }}
                />
              </div>
              <button
                onClick={handleRegisterScript}
                style={{ ...btnPrimary, marginTop: 8 }}
              >
                Register Script
              </button>
            </div>

            {/* Current Scripts List */}
            <div
              style={{
                fontSize: 13,
                fontWeight: 600,
                color: "#aaa",
              }}
            >
              Current Scripts{" "}
              <span style={{ fontSize: 10, color: "#888", marginLeft: 4 }}>
                ({scripts.length})
              </span>
            </div>
            {scripts.length === 0 && (
              <div
                style={{
                  padding: 16,
                  textAlign: "center",
                  color: "#555",
                  fontSize: 12,
                }}
              >
                No scripts registered yet.
              </div>
            )}
            {scripts.map((s) => (
              <div
                key={s.id}
                style={{
                  ...panelStyle,
                  borderLeft: `3px solid ${
                    s.compiled ? "#6bcb77" : "#fdcb6e"
                  }`,
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                  }}
                >
                  <div>
                    <span style={{ fontWeight: 600, fontSize: 12, color: "#ccc" }}>
                      {s.name}
                    </span>
                    <span
                      style={{
                        fontSize: 9,
                        marginLeft: 8,
                        padding: "1px 6px",
                        borderRadius: 3,
                        backgroundColor: "#141428",
                        color: s.compiled ? "#6bcb77" : "#fdcb6e",
                      }}
                    >
                      {s.compiled ? "compiled" : "uncompiled"}
                    </span>
                  </div>
                  <button
                    onClick={() => handleCompileScript(s.id)}
                    style={{
                      ...btnSmall,
                      opacity: s.compiled ? 0.5 : 1,
                    }}
                    disabled={s.compiled}
                  >
                    Compile
                  </button>
                </div>
                <div
                  style={{
                    display: "flex",
                    gap: 8,
                    marginTop: 4,
                    fontSize: 10,
                    color: "#888",
                  }}
                >
                  <span>{s.language}</span>
                  <span>·</span>
                  <span>{s.scope}</span>
                  <span>·</span>
                  <span style={{ color: "#74b9ff" }}>{s.id}</span>
                </div>
              </div>
            ))}

            {/* Hot Reload */}
            <div style={panelStyle}>
              <div
                style={{
                  fontSize: 12,
                  fontWeight: 600,
                  color: "#aaa",
                  marginBottom: 8,
                }}
              >
                Hot Reload
              </div>
              <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
                <div style={{ flex: 1 }}>
                  <div style={labelStyle}>Script ID</div>
                  {renderScriptSelector(hotReloadScriptId, setHotReloadScriptId)}
                </div>
              </div>
              <div>
                <div style={labelStyle}>New Source</div>
                <textarea
                  value={hotReloadSource}
                  onChange={(e) => setHotReloadSource(e.target.value)}
                  placeholder="Updated source code..."
                  rows={4}
                  style={{ ...textareaStyle, width: "100%" }}
                />
              </div>
              <button
                onClick={handleHotReload}
                style={{ ...btnPrimary, marginTop: 8 }}
              >
                Hot Reload
              </button>
            </div>
          </div>
        )}

        {/* ═══════════════════════════════════════ INSTANCES ═══════ */}
        {activeTab === "instances" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {/* Instantiate Form */}
            <div style={panelStyle}>
              <div
                style={{
                  fontSize: 12,
                  fontWeight: 600,
                  color: "#aaa",
                  marginBottom: 8,
                }}
              >
                Instantiate Script
              </div>
              <div
                style={{
                  display: "flex",
                  gap: 8,
                  flexWrap: "wrap",
                  alignItems: "flex-end",
                }}
              >
                <div>
                  <div style={labelStyle}>Script</div>
                  {renderScriptSelector(
                    instantiateScriptId,
                    setInstantiateScriptId
                  )}
                </div>
                <div style={{ flex: 1, minWidth: 150 }}>
                  <div style={labelStyle}>Target Entity ID</div>
                  <input
                    value={targetEntityId}
                    onChange={(e) => setTargetEntityId(e.target.value)}
                    placeholder="entity_001"
                    style={{ ...inputStyle, width: "100%" }}
                  />
                </div>
              </div>
              <div style={{ marginTop: 8 }}>
                <div style={labelStyle}>Initial Variables (JSON)</div>
                <textarea
                  value={initialVariables}
                  onChange={(e) => setInitialVariables(e.target.value)}
                  placeholder='{"speed": 10}'
                  rows={2}
                  style={{ ...textareaStyle, width: "100%" }}
                />
              </div>
              <button
                onClick={handleInstantiate}
                style={{ ...btnPrimary, marginTop: 8 }}
              >
                Instantiate
              </button>
            </div>

            {/* Execute Form */}
            <div style={panelStyle}>
              <div
                style={{
                  fontSize: 12,
                  fontWeight: 600,
                  color: "#aaa",
                  marginBottom: 8,
                }}
              >
                Execute Instance
              </div>
              <div
                style={{
                  display: "flex",
                  gap: 8,
                  flexWrap: "wrap",
                  alignItems: "flex-end",
                }}
              >
                <div>
                  <div style={labelStyle}>Instance</div>
                  {renderInstanceSelector(
                    executeInstanceId,
                    setExecuteInstanceId
                  )}
                </div>
                <div>
                  <div style={labelStyle}>Delta Time (s)</div>
                  <input
                    value={executeDeltaTime}
                    onChange={(e) => setExecuteDeltaTime(e.target.value)}
                    type="number"
                    step="0.001"
                    min="0"
                    style={{ ...inputStyle, width: 80 }}
                  />
                </div>
                <button onClick={handleExecute} style={btnPrimary}>
                  Execute
                </button>
              </div>
            </div>

            {/* Set Variable Form */}
            <div style={panelStyle}>
              <div
                style={{
                  fontSize: 12,
                  fontWeight: 600,
                  color: "#aaa",
                  marginBottom: 8,
                }}
              >
                Set Variable
              </div>
              <div
                style={{
                  display: "flex",
                  gap: 8,
                  flexWrap: "wrap",
                  alignItems: "flex-end",
                }}
              >
                <div>
                  <div style={labelStyle}>Instance</div>
                  {renderInstanceSelector(
                    varInstanceId,
                    setVarInstanceId
                  )}
                </div>
                <div style={{ flex: 1, minWidth: 100 }}>
                  <div style={labelStyle}>Variable Name</div>
                  <input
                    value={varName}
                    onChange={(e) => setVarName(e.target.value)}
                    placeholder="health"
                    style={{ ...inputStyle, width: "100%" }}
                  />
                </div>
                <div style={{ flex: 1, minWidth: 100 }}>
                  <div style={labelStyle}>Value</div>
                  <input
                    value={varValue}
                    onChange={(e) => setVarValue(e.target.value)}
                    placeholder="100"
                    style={{ ...inputStyle, width: "100%" }}
                  />
                </div>
                <button onClick={handleSetVariable} style={btnPrimary}>
                  Set Variable
                </button>
              </div>
            </div>

            {/* Instance List */}
            <div
              style={{
                fontSize: 13,
                fontWeight: 600,
                color: "#aaa",
              }}
            >
              Instances{" "}
              <span style={{ fontSize: 10, color: "#888", marginLeft: 4 }}>
                ({instances.length})
              </span>
            </div>
            {instances.length === 0 && (
              <div
                style={{
                  padding: 16,
                  textAlign: "center",
                  color: "#555",
                  fontSize: 12,
                }}
              >
                No instances created yet.
              </div>
            )}
            {instances.map((inst) => (
              <div
                key={inst.id}
                style={{
                  ...panelStyle,
                  borderLeft: `3px solid ${instanceStateColor(inst.state)}`,
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                  }}
                >
                  <div>
                    <span
                      style={{ fontWeight: 600, fontSize: 12, color: "#ccc" }}
                    >
                      {inst.script_name}
                    </span>
                    <span
                      style={{
                        fontSize: 9,
                        marginLeft: 8,
                        padding: "1px 6px",
                        borderRadius: 3,
                        backgroundColor: "#141428",
                        color: instanceStateColor(inst.state),
                        textTransform: "uppercase",
                      }}
                    >
                      {inst.state}
                    </span>
                  </div>
                  <div style={{ display: "flex", gap: 4 }}>
                    {inst.state === "running" ? (
                      <button
                        onClick={() => handlePauseInstance(inst.id)}
                        style={btnDanger}
                      >
                        Pause
                      </button>
                    ) : (
                      <button
                        onClick={() => handleResumeInstance(inst.id)}
                        style={btnSuccess}
                      >
                        Resume
                      </button>
                    )}
                  </div>
                </div>
                <div
                  style={{
                    display: "flex",
                    gap: 8,
                    marginTop: 4,
                    fontSize: 10,
                    color: "#888",
                  }}
                >
                  <span>Entity: {inst.target_entity}</span>
                  <span>·</span>
                  <span>Executions: {inst.execution_count}</span>
                  <span>·</span>
                  <span style={{ color: "#74b9ff" }}>{inst.id}</span>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* ════════════════════════════════════════ EVENTS ════════ */}
        {activeTab === "events" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {/* Trigger Event */}
            <div style={panelStyle}>
              <div
                style={{
                  fontSize: 12,
                  fontWeight: 600,
                  color: "#aaa",
                  marginBottom: 8,
                }}
              >
                Trigger Event
              </div>
              <div
                style={{
                  display: "flex",
                  gap: 8,
                  flexWrap: "wrap",
                  alignItems: "flex-end",
                }}
              >
                <div>
                  <div style={labelStyle}>Script</div>
                  {renderScriptSelector(eventScriptId, setEventScriptId)}
                </div>
                <div>
                  <div style={labelStyle}>Event Type</div>
                  <select
                    value={eventType}
                    onChange={(e) =>
                      setEventType(e.target.value as EventType)
                    }
                    style={selectStyle}
                  >
                    {EVENT_TYPES.map((et) => (
                      <option key={et} value={et}>
                        {et}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <div style={{ marginTop: 8 }}>
                <div style={labelStyle}>Event Data (JSON)</div>
                <textarea
                  value={eventData}
                  onChange={(e) => setEventData(e.target.value)}
                  placeholder='{"key": "value"}'
                  rows={2}
                  style={{ ...textareaStyle, width: "100%" }}
                />
              </div>
              <button
                onClick={handleTriggerEvent}
                style={{ ...btnPrimary, marginTop: 8 }}
              >
                Trigger Event
              </button>
            </div>

            {/* Execution Results */}
            {executionResults.length > 0 && (
              <div style={panelStyle}>
                <div
                  style={{
                    fontSize: 12,
                    fontWeight: 600,
                    color: "#aaa",
                    marginBottom: 8,
                  }}
                >
                  Execution Results
                </div>
                {executionResults.map((r, i) => (
                  <div
                    key={i}
                    style={{
                      padding: "6px 8px",
                      marginTop: i > 0 ? 4 : 0,
                      backgroundColor: "#141428",
                      borderRadius: 4,
                      fontSize: 10,
                      color: "#aaa",
                    }}
                  >
                    <div style={{ color: "#74b9ff", marginBottom: 2 }}>
                      [{r.instance_id}] dt={r.delta_time}s
                    </div>
                    <div
                      style={{
                        fontFamily: "monospace",
                        whiteSpace: "pre-wrap",
                        wordBreak: "break-all",
                      }}
                    >
                      {r.output}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Register Handler */}
            <div style={panelStyle}>
              <div
                style={{
                  fontSize: 12,
                  fontWeight: 600,
                  color: "#aaa",
                  marginBottom: 8,
                }}
              >
                Register Handler
              </div>
              <div
                style={{
                  display: "flex",
                  gap: 8,
                  flexWrap: "wrap",
                  alignItems: "flex-end",
                }}
              >
                <div>
                  <div style={labelStyle}>Script</div>
                  {renderScriptSelector(
                    handlerScriptId,
                    setHandlerScriptId
                  )}
                </div>
                <div>
                  <div style={labelStyle}>Event Type</div>
                  <select
                    value={handlerEventType}
                    onChange={(e) =>
                      setHandlerEventType(e.target.value as EventType)
                    }
                    style={selectStyle}
                  >
                    {EVENT_TYPES.map((et) => (
                      <option key={et} value={et}>
                        {et}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <div style={{ marginTop: 8 }}>
                <div style={labelStyle}>Handler Code</div>
                <textarea
                  value={handlerCode}
                  onChange={(e) => setHandlerCode(e.target.value)}
                  placeholder="def on_collision(entity): ..."
                  rows={4}
                  style={{ ...textareaStyle, width: "100%" }}
                />
              </div>
              <button
                onClick={handleRegisterHandler}
                style={{ ...btnPrimary, marginTop: 8 }}
              >
                Register Handler
              </button>
            </div>
          </div>
        )}

        {/* ════════════════════════════════════ SCHEDULER ════════ */}
        {activeTab === "scheduler" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <div style={panelStyle}>
              <div
                style={{
                  fontSize: 12,
                  fontWeight: 600,
                  color: "#aaa",
                  marginBottom: 8,
                }}
              >
                Schedule Execution
              </div>
              <div
                style={{
                  display: "flex",
                  gap: 8,
                  flexWrap: "wrap",
                  alignItems: "flex-end",
                }}
              >
                <div>
                  <div style={labelStyle}>Script</div>
                  {renderScriptSelector(schedScriptId, setSchedScriptId)}
                </div>
                <div>
                  <div style={labelStyle}>Delay (ms)</div>
                  <input
                    value={delayMs}
                    onChange={(e) => setDelayMs(e.target.value)}
                    type="number"
                    min="0"
                    step="100"
                    style={{ ...inputStyle, width: 80 }}
                  />
                </div>
                <div style={{ alignSelf: "center", paddingTop: 12 }}>
                  <label
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 4,
                      fontSize: 11,
                      color: "#ccc",
                      cursor: "pointer",
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={repeat}
                      onChange={(e) => setRepeat(e.target.checked)}
                    />
                    Repeat
                  </label>
                </div>
              </div>
              <div style={{ marginTop: 8 }}>
                <div style={labelStyle}>Context (JSON)</div>
                <textarea
                  value={schedContext}
                  onChange={(e) => setSchedContext(e.target.value)}
                  placeholder='{"param": "value"}'
                  rows={2}
                  style={{ ...textareaStyle, width: "100%" }}
                />
              </div>
              <button
                onClick={handleSchedule}
                style={{ ...btnPrimary, marginTop: 8 }}
              >
                Schedule
              </button>

              {scheduleId && (
                <div
                  style={{
                    marginTop: 8,
                    padding: "6px 10px",
                    backgroundColor: "#141428",
                    borderRadius: 4,
                    fontSize: 11,
                    color: "#6bcb77",
                  }}
                >
                  Schedule ID:{" "}
                  <span style={{ fontFamily: "monospace" }}>
                    {scheduleId}
                  </span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ════════════════════════════════════════ STATUS ════════ */}
        {activeTab === "status" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <div style={panelStyle}>
              <div
                style={{
                  fontSize: 12,
                  fontWeight: 600,
                  color: "#aaa",
                  marginBottom: 8,
                }}
              >
                Runtime Scripting Status
              </div>
              {status ? (
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))",
                    gap: 8,
                  }}
                >
                  <StatusCard
                    label="Scripts"
                    value={status.scripts_count}
                    color="#74b9ff"
                  />
                  <StatusCard
                    label="Instances"
                    value={status.instances_count}
                    color="#74b9ff"
                  />
                  <StatusCard
                    label="Running"
                    value={status.running_count}
                    color="#6bcb77"
                  />
                  <StatusCard
                    label="Paused"
                    value={status.paused_count}
                    color="#fdcb6e"
                  />
                  <StatusCard
                    label="Errors"
                    value={status.error_count}
                    color="#ff6b6b"
                  />
                  <StatusCard
                    label="Sandboxes"
                    value={status.sandboxes_count}
                    color="#74b9ff"
                  />
                  <StatusCard
                    label="Events Registered"
                    value={status.events_registered}
                    color="#6bcb77"
                  />
                  <StatusCard
                    label="Scheduled"
                    value={status.scheduled_count}
                    color="#fdcb6e"
                  />
                </div>
              ) : (
                <div
                  style={{
                    padding: 16,
                    textAlign: "center",
                    color: "#555",
                    fontSize: 12,
                  }}
                >
                  Loading status...
                </div>
              )}
              <div
                style={{
                  marginTop: 8,
                  fontSize: 9,
                  color: "#555",
                  textAlign: "right",
                }}
              >
                Auto-refreshes every 15s
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

// ── Status Card Sub-component ───────────────────────────────────────

const StatusCard: React.FC<{
  label: string;
  value: number;
  color: string;
}> = ({ label, value, color }) => (
  <div
    style={{
      padding: 10,
      backgroundColor: "#141428",
      borderRadius: 6,
      border: "1px solid #2a2a3e",
      textAlign: "center",
    }}
  >
    <div style={{ fontSize: 10, color: "#888", marginBottom: 4 }}>
      {label}
    </div>
    <div style={{ fontSize: 20, fontWeight: 700, color }}>{value}</div>
  </div>
);

export default EngineRuntimeScriptingPanel;