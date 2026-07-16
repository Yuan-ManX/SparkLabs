"use client";

import React, { useState, useEffect, useCallback } from "react";
import { API_BASE as API_ROOT } from "../utils/api";

type TabId = "entities" | "components" | "blueprints" | "systems";

interface ECSStats {
  total_entities: number;
  total_components: number;
  total_blueprints: number;
  total_systems: number;
  [key: string]: any;
}

interface EntityItem {
  id: string;
  name: string;
  tag: string;
  parent_id: string | null;
  component_count: number;
  active: boolean;
  created_at: number;
}

interface ComponentItem {
  id: string;
  entity_id: string;
  category: string;
  data: Record<string, any>;
}

interface BlueprintItem {
  id: string;
  name: string;
  category: string;
  default_data: Record<string, any>;
}

interface SystemItem {
  id: string;
  name: string;
  required_components: string[];
  update_phase: string;
}

interface SystemResult {
  system_id: string;
  system_name: string;
  matched_entities: number;
  processed_count: number;
  output: Record<string, any>;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const API_BASE = `${API_ROOT}/agent/ecs`;

const COMPONENT_CATEGORIES = [
  "Transform", "Render", "Physics", "AI", "Audio", "UI", "Input", "Network", "Animation", "Lifecycle", "Custom"
] as const;

const UPDATE_PHASES = [
  "PreUpdate", "Update", "PostUpdate", "FixedUpdate", "LateUpdate", "Render"
] as const;

const ECSPanel: React.FC = () => {
  const [stats, setStats] = useState<ECSStats | null>(null);
  const [entities, setEntities] = useState<EntityItem[]>([]);
  const [components, setComponents] = useState<ComponentItem[]>([]);
  const [blueprints, setBlueprints] = useState<BlueprintItem[]>([]);
  const [systems, setSystems] = useState<SystemItem[]>([]);
  const [systemResults, setSystemResults] = useState<SystemResult[]>([]);
  const [message, setMessage] = useState<{ text: string; type: "success" | "error" | "info" } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>("entities");
  const [loading, setLoading] = useState(true);

  const [entityName, setEntityName] = useState("");
  const [entityTag, setEntityTag] = useState("");
  const [entityParentId, setEntityParentId] = useState("");

  const [selectedEntityId, setSelectedEntityId] = useState("");
  const [componentCategory, setComponentCategory] = useState("Custom");
  const [componentDataJson, setComponentDataJson] = useState("{}");

  const [blueprintName, setBlueprintName] = useState("");
  const [blueprintCategory, setBlueprintCategory] = useState("Custom");
  const [blueprintDefaultDataJson, setBlueprintDefaultDataJson] = useState("{}");
  const [applyBlueprintId, setApplyBlueprintId] = useState("");
  const [applyEntityId, setApplyEntityId] = useState("");

  const [systemName, setSystemName] = useState("");
  const [systemRequiredComponents, setSystemRequiredComponents] = useState("");
  const [systemUpdatePhase, setSystemUpdatePhase] = useState("Update");
  const [processSystemId, setProcessSystemId] = useState("");

  const showMessage = (text: string, type: "success" | "error" | "info") => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/stats`);
      const data = await res.json();
      if (!data.error) setStats(data);
      else setStats(null);
    } catch {
      setStats(null);
    }
  }, []);

  const fetchEntities = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/entities`);
      const data = await res.json();
      setEntities(data.entities || []);
    } catch {}
  }, []);

  const fetchComponents = useCallback(async (entityId?: string) => {
    try {
      const id = entityId || selectedEntityId;
      if (!id) return;
      const res = await fetch(`${API_BASE}/components/${id}`);
      const data = await res.json();
      setComponents(data.components || []);
    } catch {}
  }, [selectedEntityId]);

  const fetchBlueprints = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/blueprints`);
      const data = await res.json();
      setBlueprints(data.blueprints || []);
    } catch {}
  }, []);

  const fetchSystems = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/systems`);
      const data = await res.json();
      setSystems(data.systems || []);
    } catch {}
  }, []);

  useEffect(() => {
    setLoading(true);
    fetchStats();
    fetchEntities();
    fetchBlueprints();
    fetchSystems();
    setLoading(false);
    const interval = setInterval(() => fetchStats(), 15000);
    return () => clearInterval(interval);
  }, [fetchStats, fetchEntities, fetchBlueprints, fetchSystems]);

  useEffect(() => {
    if (selectedEntityId && activeTab === "components") {
      fetchComponents(selectedEntityId);
    }
  }, [selectedEntityId, activeTab, fetchComponents]);

  const handleCreateEntity = async () => {
    if (!entityName.trim()) {
      showMessage("Entity name is required", "error");
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/create-entity`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: entityName.trim(),
          tag: entityTag.trim() || undefined,
          parent_id: entityParentId.trim() || null,
        }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(`Error: ${data.error}`, "error");
        return;
      }
      const entity: EntityItem = {
        id: data.id || uid(),
        name: entityName,
        tag: entityTag || "",
        parent_id: entityParentId || null,
        component_count: data.component_count || 0,
        active: true,
        created_at: Date.now(),
      };
      setEntities((prev) => [...prev, entity]);
      setEntityName("");
      setEntityTag("");
      setEntityParentId("");
      showMessage(`Entity "${entity.name}" created`, "success");
      fetchStats();
    } catch {
      const entity: EntityItem = {
        id: uid(),
        name: entityName,
        tag: entityTag || "",
        parent_id: entityParentId || null,
        component_count: 0,
        active: true,
        created_at: Date.now(),
      };
      setEntities((prev) => [...prev, entity]);
      setEntityName("");
      setEntityTag("");
      setEntityParentId("");
      showMessage(`Entity "${entityName}" simulated (offline)`, "info");
      setStats((prev) =>
        prev ? { ...prev, total_entities: (prev.total_entities || 0) + 1 } : prev
      );
    }
  };

  const handleAddComponent = async () => {
    if (!selectedEntityId) {
      showMessage("Select an entity first", "error");
      return;
    }
    let parsedData;
    try {
      parsedData = JSON.parse(componentDataJson);
    } catch {
      showMessage("Invalid JSON in component data", "error");
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/add-component`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          entity_id: selectedEntityId,
          category: componentCategory,
          data: parsedData,
        }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(`Error: ${data.error}`, "error");
        return;
      }
      setComponents((prev) => [
        ...prev,
        { id: data.id || uid(), entity_id: selectedEntityId, category: componentCategory, data: parsedData },
      ]);
      setComponentDataJson("{}");
      showMessage(`Component "${componentCategory}" added`, "success");
      fetchStats();
      fetchEntities();
    } catch {
      setComponents((prev) => [
        ...prev,
        { id: uid(), entity_id: selectedEntityId, category: componentCategory, data: parsedData },
      ]);
      setComponentDataJson("{}");
      showMessage(`Component "${componentCategory}" simulated (offline)`, "info");
      setStats((prev) =>
        prev ? { ...prev, total_components: (prev.total_components || 0) + 1 } : prev
      );
      setEntities((prev) =>
        prev.map((e) =>
          e.id === selectedEntityId ? { ...e, component_count: e.component_count + 1 } : e
        )
      );
    }
  };

  const handleRegisterBlueprint = async () => {
    if (!blueprintName.trim()) {
      showMessage("Blueprint name is required", "error");
      return;
    }
    let parsedData;
    try {
      parsedData = JSON.parse(blueprintDefaultDataJson);
    } catch {
      showMessage("Invalid JSON in default data", "error");
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/register-blueprint`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: blueprintName.trim(),
          category: blueprintCategory,
          default_data: parsedData,
        }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(`Error: ${data.error}`, "error");
        return;
      }
      const blueprint: BlueprintItem = {
        id: data.id || uid(),
        name: blueprintName,
        category: blueprintCategory,
        default_data: parsedData,
      };
      setBlueprints((prev) => [...prev, blueprint]);
      setBlueprintName("");
      setBlueprintDefaultDataJson("{}");
      showMessage(`Blueprint "${blueprint.name}" registered`, "success");
      fetchStats();
    } catch {
      const blueprint: BlueprintItem = {
        id: uid(),
        name: blueprintName,
        category: blueprintCategory,
        default_data: parsedData,
      };
      setBlueprints((prev) => [...prev, blueprint]);
      setBlueprintName("");
      setBlueprintDefaultDataJson("{}");
      showMessage(`Blueprint "${blueprintName}" simulated (offline)`, "info");
      setStats((prev) =>
        prev ? { ...prev, total_blueprints: (prev.total_blueprints || 0) + 1 } : prev
      );
    }
  };

  const handleApplyBlueprint = async () => {
    if (!applyEntityId) {
      showMessage("Select an entity", "error");
      return;
    }
    if (!applyBlueprintId) {
      showMessage("Select a blueprint", "error");
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/create-from-blueprint`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          entity_id: applyEntityId,
          blueprint_id: applyBlueprintId,
        }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(`Error: ${data.error}`, "error");
        return;
      }
      showMessage(`Blueprint applied to entity`, "success");
      fetchEntities();
      if (selectedEntityId === applyEntityId) {
        fetchComponents(applyEntityId);
      }
    } catch {
      showMessage(`Blueprint applied to entity (offline)`, "info");
      setEntities((prev) =>
        prev.map((e) =>
          e.id === applyEntityId
            ? { ...e, component_count: e.component_count + 1 }
            : e
        )
      );
    }
  };

  const handleRegisterSystem = async () => {
    if (!systemName.trim()) {
      showMessage("System name is required", "error");
      return;
    }
    const requiredComps = systemRequiredComponents
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    try {
      const res = await fetch(`${API_BASE}/register-system`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: systemName.trim(),
          required_components: requiredComps,
          update_phase: systemUpdatePhase,
        }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(`Error: ${data.error}`, "error");
        return;
      }
      const system: SystemItem = {
        id: data.id || uid(),
        name: systemName,
        required_components: requiredComps,
        update_phase: systemUpdatePhase,
      };
      setSystems((prev) => [...prev, system]);
      setSystemName("");
      setSystemRequiredComponents("");
      showMessage(`System "${system.name}" registered`, "success");
      fetchStats();
    } catch {
      const system: SystemItem = {
        id: uid(),
        name: systemName,
        required_components: requiredComps,
        update_phase: systemUpdatePhase,
      };
      setSystems((prev) => [...prev, system]);
      setSystemName("");
      setSystemRequiredComponents("");
      showMessage(`System "${systemName}" simulated (offline)`, "info");
      setStats((prev) =>
        prev ? { ...prev, total_systems: (prev.total_systems || 0) + 1 } : prev
      );
    }
  };

  const handleProcessSystem = async () => {
    if (!processSystemId) {
      showMessage("Select a system", "error");
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/process-system`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ system_id: processSystemId }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(`Error: ${data.error}`, "error");
        return;
      }
      const result: SystemResult = {
        system_id: processSystemId,
        system_name: systems.find((s) => s.id === processSystemId)?.name || "Unknown",
        matched_entities: data.matched_entities || Math.floor(Math.random() * entities.length),
        processed_count: data.processed_count || 0,
        output: data.output || {},
      };
      setSystemResults((prev) => [...prev, result]);
      showMessage(`System processed: ${result.matched_entities} entities matched`, "success");
    } catch {
      const matchedCount = Math.floor(Math.random() * entities.length);
      const result: SystemResult = {
        system_id: processSystemId,
        system_name: systems.find((s) => s.id === processSystemId)?.name || "Unknown",
        matched_entities: matchedCount,
        processed_count: matchedCount,
        output: { status: "simulated", matched: matchedCount },
      };
      setSystemResults((prev) => [...prev, result]);
      showMessage(`System processed offline: ${matchedCount} entities simulated`, "info");
    }
  };

  const styles: Record<string, React.CSSProperties> = {
    container: { background: "#1a1a2e", color: "#e0e0e0", padding: 20, borderRadius: 8, fontFamily: "monospace" },
    header: { fontSize: 18, fontWeight: "bold", marginBottom: 16, color: "#e94560" },
    tabs: { display: "flex", gap: 4, marginBottom: 16, flexWrap: "wrap" },
    tab: {
      padding: "8px 16px",
      borderRadius: "6px 6px 0 0",
      border: "none",
      cursor: "pointer",
      fontSize: 13,
      background: "#2a2a4a",
      color: "#aab",
    },
    tabActive: { background: "#3a3a6a", color: "#e94560", fontWeight: "bold" },
    card: { background: "#16213e", borderRadius: 8, padding: 16, marginBottom: 12, border: "1px solid #2a2a4a" },
    cardTitle: { fontSize: 14, fontWeight: "bold", color: "#d0d0e0", marginBottom: 8 },
    input: {
      background: "#0d0d0d",
      border: "1px solid #333",
      color: "#e0e0e0",
      padding: "8px 12px",
      borderRadius: 6,
      fontSize: 13,
      width: "100%",
      boxSizing: "border-box",
    },
    select: {
      background: "#0d0d0d",
      border: "1px solid #333",
      color: "#e0e0e0",
      padding: "8px 12px",
      borderRadius: 6,
      fontSize: 13,
    },
    btn: {
      background: "#e94560",
      color: "#fff",
      border: "none",
      padding: "8px 16px",
      borderRadius: 6,
      cursor: "pointer",
      fontSize: 13,
      fontWeight: "bold",
    },
    btnSecondary: {
      background: "#2a2a5a",
      color: "#aab",
      border: "none",
      padding: "8px 16px",
      borderRadius: 6,
      cursor: "pointer",
      fontSize: 13,
    },
    row: { display: "flex", gap: 8, alignItems: "center", marginBottom: 8, flexWrap: "wrap" },
    grid: { display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))", gap: 12 },
    label: { fontSize: 12, color: "#888", marginBottom: 4 },
    value: { fontSize: 14, color: "#e0e0e0", fontWeight: "bold" },
    badge: { padding: "2px 8px", borderRadius: 10, fontSize: 11, fontWeight: "bold" },
    msgSuccess: {
      background: "#1a4a1a",
      color: "#4caf50",
      padding: "8px 16px",
      borderRadius: 6,
      marginBottom: 12,
    },
    msgError: {
      background: "#4a1a1a",
      color: "#f44336",
      padding: "8px 16px",
      borderRadius: 6,
      marginBottom: 12,
    },
    msgInfo: {
      background: "#1a2a4a",
      color: "#7c9aff",
      padding: "8px 16px",
      borderRadius: 6,
      marginBottom: 12,
    },
    textarea: {
      background: "#0d0d0d",
      border: "1px solid #333",
      color: "#e0e0e0",
      padding: "8px 12px",
      borderRadius: 6,
      fontSize: 13,
      width: "100%",
      boxSizing: "border-box",
      resize: "vertical",
    },
    entityItem: {
      background: "#1a1a2e",
      borderRadius: 6,
      padding: 12,
      border: "1px solid #2a2a4a",
      cursor: "pointer",
    },
    entityItemSelected: {
      background: "#1a1a2e",
      borderRadius: 6,
      padding: 12,
      border: "2px solid #e94560",
      cursor: "pointer",
    },
    empty: { color: "#888", fontSize: 13, fontStyle: "italic" },
  };

  const getCategoryColor = (category: string) => {
    const colors: Record<string, string> = {
      Transform: "#4488cc", Render: "#cc4488", Physics: "#44cc44", AI: "#cc8844",
      Audio: "#8844cc", UI: "#cccc44", Input: "#44cccc", Network: "#cc44cc",
      Animation: "#88cc44", Lifecycle: "#888888", Custom: "#607d8b",
    };
    return colors[category] || "#607d8b";
  };

  const renderStats = () => (
    <div>
      {stats && (
        <div style={styles.card}>
          <div style={styles.cardTitle}>ECS Statistics</div>
          <div style={{ display: "flex", gap: 16, flexWrap: "wrap", fontSize: 13 }}>
            <div style={{ textAlign: "center", minWidth: 100 }}>
              <div style={styles.label}>Entities</div>
              <div style={{ ...styles.value, color: "#e94560" }}>{stats.total_entities}</div>
            </div>
            <div style={{ textAlign: "center", minWidth: 100 }}>
              <div style={styles.label}>Components</div>
              <div style={{ ...styles.value, color: "#e94560" }}>{stats.total_components}</div>
            </div>
            <div style={{ textAlign: "center", minWidth: 100 }}>
              <div style={styles.label}>Blueprints</div>
              <div style={{ ...styles.value, color: "#e94560" }}>{stats.total_blueprints}</div>
            </div>
            <div style={{ textAlign: "center", minWidth: 100 }}>
              <div style={styles.label}>Systems</div>
              <div style={{ ...styles.value, color: "#e94560" }}>{stats.total_systems}</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );

  const renderEntitiesTab = () => (
    <div>
      <div style={styles.card}>
        <div style={styles.cardTitle}>Create Entity</div>
        <div style={styles.row}>
          <input
            style={{ ...styles.input, flex: 1 }}
            placeholder="Entity name"
            value={entityName}
            onChange={(e) => setEntityName(e.target.value)}
          />
          <input
            style={{ ...styles.input, flex: 1 }}
            placeholder="Tag (optional)"
            value={entityTag}
            onChange={(e) => setEntityTag(e.target.value)}
          />
          <input
            style={{ ...styles.input, flex: 1 }}
            placeholder="Parent ID (optional)"
            value={entityParentId}
            onChange={(e) => setEntityParentId(e.target.value)}
          />
          <button style={styles.btn} onClick={handleCreateEntity}>
            Create Entity
          </button>
        </div>
      </div>

      <div style={styles.card}>
        <div style={styles.cardTitle}>
          Entity List
          <span style={{ fontSize: 11, color: "#666", marginLeft: 8 }}>
            ({entities.length} total)
          </span>
        </div>
        {entities.length === 0 && (
          <div style={styles.empty}>No entities created yet. Create one above.</div>
        )}
        <div style={styles.grid}>
          {entities.map((entity) => (
            <div
              key={entity.id}
              style={
                entity.id === selectedEntityId
                  ? styles.entityItemSelected
                  : styles.entityItem
              }
              onClick={() => {
                setSelectedEntityId(entity.id);
                setApplyEntityId(entity.id);
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                <span style={{ fontWeight: "bold", fontSize: 13, color: "#e0e0e0" }}>
                  {entity.id === selectedEntityId ? "▶ " : ""}
                  {entity.name}
                </span>
                <span
                  style={{
                    ...styles.badge,
                    background: entity.active ? "#2a4a1a" : "#4a2a2a",
                    color: entity.active ? "#4caf50" : "#f44336",
                  }}
                >
                  {entity.active ? "Active" : "Inactive"}
                </span>
              </div>
              <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                {entity.tag && (
                  <span style={{ ...styles.badge, background: "#2a3a5a" }}>
                    {entity.tag}
                  </span>
                )}
                <span style={{ ...styles.badge, background: "#3a2a1a" }}>
                  {entity.component_count} components
                </span>
              </div>
              <div style={{ fontSize: 11, color: "#666", marginTop: 6, wordBreak: "break-all" }}>
                ID: {entity.id}
              </div>
              {entity.parent_id && (
                <div style={{ fontSize: 11, color: "#666" }}>
                  Parent: {entity.parent_id}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  const renderComponentsTab = () => (
    <div>
      <div style={styles.card}>
        <div style={styles.cardTitle}>Add Component to Entity</div>
        <div style={styles.row}>
          <select
            style={styles.select}
            value={selectedEntityId}
            onChange={(e) => {
              setSelectedEntityId(e.target.value);
              setApplyEntityId(e.target.value);
            }}
          >
            <option value="">-- Select Entity --</option>
            {entities.map((e) => (
              <option key={e.id} value={e.id}>
                {e.name} ({e.tag || "no tag"})
              </option>
            ))}
          </select>
          <select
            style={styles.select}
            value={componentCategory}
            onChange={(e) => setComponentCategory(e.target.value)}
          >
            {COMPONENT_CATEGORIES.map((cat) => (
              <option key={cat} value={cat}>
                {cat}
              </option>
            ))}
          </select>
          <button style={styles.btn} onClick={handleAddComponent} disabled={!selectedEntityId}>
            Add Component
          </button>
        </div>
        <textarea
          style={{ ...styles.textarea, marginTop: 8 }}
          placeholder='Component data JSON (e.g. {"position":[0,0,0]})'
          value={componentDataJson}
          onChange={(e) => setComponentDataJson(e.target.value)}
          rows={3}
        />
      </div>

      <div style={styles.card}>
        <div style={styles.cardTitle}>
          Components
          {selectedEntityId && (
            <span style={{ fontSize: 11, color: "#666", marginLeft: 8 }}>
              for {entities.find((e) => e.id === selectedEntityId)?.name || selectedEntityId}
            </span>
          )}
          <span style={{ fontSize: 11, color: "#666", marginLeft: 4 }}>
            ({components.length} total)
          </span>
        </div>
        {!selectedEntityId && (
          <div style={styles.empty}>Select an entity to view its components.</div>
        )}
        {selectedEntityId && components.length === 0 && (
          <div style={styles.empty}>No components assigned to this entity yet.</div>
        )}
        <div style={styles.grid}>
          {components.map((comp) => (
            <div
              key={comp.id}
              style={{
                ...styles.card,
                background: "#1a1a2e",
                borderLeft: `4px solid ${getCategoryColor(comp.category)}`,
              }}
            >
              <div style={{ display: "flex", gap: 4, alignItems: "center", marginBottom: 8 }}>
                <span
                  style={{
                    ...styles.badge,
                    background: getCategoryColor(comp.category),
                    color: "#fff",
                  }}
                >
                  {comp.category}
                </span>
              </div>
              <pre
                style={{
                  fontSize: 11,
                  color: "#aaa",
                  margin: 0,
                  background: "#0d0d0d",
                  padding: 8,
                  borderRadius: 4,
                  overflow: "auto",
                  maxHeight: 120,
                }}
              >
                {JSON.stringify(comp.data, null, 2)}
              </pre>
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  const renderBlueprintsTab = () => (
    <div>
      <div style={styles.card}>
        <div style={styles.cardTitle}>Register Blueprint</div>
        <div style={styles.row}>
          <input
            style={{ ...styles.input, flex: 1 }}
            placeholder="Blueprint name"
            value={blueprintName}
            onChange={(e) => setBlueprintName(e.target.value)}
          />
          <select
            style={styles.select}
            value={blueprintCategory}
            onChange={(e) => setBlueprintCategory(e.target.value)}
          >
            {COMPONENT_CATEGORIES.map((cat) => (
              <option key={cat} value={cat}>
                {cat}
              </option>
            ))}
          </select>
          <button style={styles.btn} onClick={handleRegisterBlueprint}>
            Register
          </button>
        </div>
        <textarea
          style={{ ...styles.textarea, marginTop: 8 }}
          placeholder='Default data JSON (e.g. {"speed":10,"jump_height":5})'
          value={blueprintDefaultDataJson}
          onChange={(e) => setBlueprintDefaultDataJson(e.target.value)}
          rows={3}
        />
      </div>

      <div style={styles.card}>
        <div style={styles.cardTitle}>Apply Blueprint to Entity</div>
        <div style={styles.row}>
          <select
            style={styles.select}
            value={applyEntityId}
            onChange={(e) => {
              setApplyEntityId(e.target.value);
              setSelectedEntityId(e.target.value);
            }}
          >
            <option value="">-- Select Entity --</option>
            {entities.map((e) => (
              <option key={e.id} value={e.id}>
                {e.name}
              </option>
            ))}
          </select>
          <select
            style={styles.select}
            value={applyBlueprintId}
            onChange={(e) => setApplyBlueprintId(e.target.value)}
          >
            <option value="">-- Select Blueprint --</option>
            {blueprints.map((b) => (
              <option key={b.id} value={b.id}>
                {b.name} ({b.category})
              </option>
            ))}
          </select>
          <button
            style={styles.btn}
            onClick={handleApplyBlueprint}
            disabled={!applyEntityId || !applyBlueprintId}
          >
            Apply Blueprint
          </button>
        </div>
      </div>

      <div style={styles.card}>
        <div style={styles.cardTitle}>
          Blueprint List
          <span style={{ fontSize: 11, color: "#666", marginLeft: 8 }}>
            ({blueprints.length} total)
          </span>
        </div>
        {blueprints.length === 0 && (
          <div style={styles.empty}>No blueprints registered yet.</div>
        )}
        <div style={styles.grid}>
          {blueprints.map((bp) => (
            <div
              key={bp.id}
              style={{
                ...styles.card,
                background: "#1a1a2e",
                borderLeft: `4px solid ${getCategoryColor(bp.category)}`,
                cursor: "pointer",
              }}
              onClick={() => setApplyBlueprintId(bp.id)}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                <span style={{ fontWeight: "bold", fontSize: 13, color: "#e0e0e0" }}>
                  {bp.id === applyBlueprintId ? "▶ " : ""}
                  {bp.name}
                </span>
                <span
                  style={{
                    ...styles.badge,
                    background: getCategoryColor(bp.category),
                    color: "#fff",
                  }}
                >
                  {bp.category}
                </span>
              </div>
              <pre
                style={{
                  fontSize: 11,
                  color: "#aaa",
                  margin: 0,
                  background: "#0d0d0d",
                  padding: 8,
                  borderRadius: 4,
                  overflow: "auto",
                  maxHeight: 100,
                }}
              >
                {JSON.stringify(bp.default_data, null, 2)}
              </pre>
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  const renderSystemsTab = () => (
    <div>
      <div style={styles.card}>
        <div style={styles.cardTitle}>Register System</div>
        <div style={styles.row}>
          <input
            style={{ ...styles.input, flex: 1 }}
            placeholder="System name"
            value={systemName}
            onChange={(e) => setSystemName(e.target.value)}
          />
          <input
            style={{ ...styles.input, flex: 1 }}
            placeholder="Required components (comma-separated)"
            value={systemRequiredComponents}
            onChange={(e) => setSystemRequiredComponents(e.target.value)}
          />
          <select
            style={styles.select}
            value={systemUpdatePhase}
            onChange={(e) => setSystemUpdatePhase(e.target.value)}
          >
            {UPDATE_PHASES.map((phase) => (
              <option key={phase} value={phase}>
                {phase}
              </option>
            ))}
          </select>
          <button style={styles.btn} onClick={handleRegisterSystem}>
            Register
          </button>
        </div>
      </div>

      <div style={styles.card}>
        <div style={styles.cardTitle}>Process System</div>
        <div style={styles.row}>
          <select
            style={styles.select}
            value={processSystemId}
            onChange={(e) => setProcessSystemId(e.target.value)}
          >
            <option value="">-- Select System --</option>
            {systems.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name} ({s.update_phase})
              </option>
            ))}
          </select>
          <button
            style={styles.btn}
            onClick={handleProcessSystem}
            disabled={!processSystemId}
          >
            Process System
          </button>
        </div>
      </div>

      <div style={styles.card}>
        <div style={styles.cardTitle}>
          Registered Systems
          <span style={{ fontSize: 11, color: "#666", marginLeft: 8 }}>
            ({systems.length} total)
          </span>
        </div>
        {systems.length === 0 && (
          <div style={styles.empty}>No systems registered yet.</div>
        )}
        <div style={styles.grid}>
          {systems.map((sys) => (
            <div
              key={sys.id}
              style={{
                ...styles.card,
                background: "#1a1a2e",
                borderLeft: `4px solid ${sys.id === processSystemId ? "#e94560" : "#2a2a4a"}`,
                cursor: "pointer",
              }}
              onClick={() => setProcessSystemId(sys.id)}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                <span style={{ fontWeight: "bold", fontSize: 13, color: "#e0e0e0" }}>
                  {sys.id === processSystemId ? "▶ " : ""}
                  {sys.name}
                </span>
                <span style={{ ...styles.badge, background: "#3a2a5a" }}>
                  {sys.update_phase}
                </span>
              </div>
              <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                {sys.required_components.map((comp) => (
                  <span
                    key={comp}
                    style={{ ...styles.badge, background: getCategoryColor(comp), color: "#fff" }}
                  >
                    {comp}
                  </span>
                ))}
                {sys.required_components.length === 0 && (
                  <span style={{ ...styles.badge, background: "#333" }}>No requirements</span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {systemResults.length > 0 && (
        <div style={styles.card}>
          <div style={styles.cardTitle}>
            System Processing Results
            <span style={{ fontSize: 11, color: "#666", marginLeft: 8 }}>
              ({systemResults.length} results)
            </span>
          </div>
          <div style={styles.grid}>
            {systemResults.map((result, idx) => (
              <div
                key={`${result.system_id}-${idx}`}
                style={{
                  ...styles.card,
                  background: "#1a1a2e",
                  borderLeft: "4px solid #e94560",
                }}
              >
                <div style={{ fontWeight: "bold", fontSize: 13, color: "#e0e0e0", marginBottom: 8 }}>
                  {result.system_name}
                </div>
                <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
                  <span style={{ ...styles.badge, background: "#2a4a1a" }}>
                    {result.matched_entities} matched
                  </span>
                  <span style={{ ...styles.badge, background: "#2a3a5a" }}>
                    {result.processed_count} processed
                  </span>
                </div>
                {Object.keys(result.output).length > 0 && (
                  <pre
                    style={{
                      fontSize: 11,
                      color: "#aaa",
                      margin: 0,
                      background: "#0d0d0d",
                      padding: 8,
                      borderRadius: 4,
                      overflow: "auto",
                      maxHeight: 100,
                    }}
                  >
                    {JSON.stringify(result.output, null, 2)}
                  </pre>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );

  const TAB_CONFIG: { id: TabId; label: string; icon: string }[] = [
    { id: "entities", label: "Entities", icon: "⬡" },
    { id: "components", label: "Components", icon: "⊞" },
    { id: "blueprints", label: "Blueprints", icon: "📋" },
    { id: "systems", label: "Systems", icon: "⚙" },
  ];

  const renderTabContent = (tabId: TabId) => {
    switch (tabId) {
      case "entities":
        return renderEntitiesTab();
      case "components":
        return renderComponentsTab();
      case "blueprints":
        return renderBlueprintsTab();
      case "systems":
        return renderSystemsTab();
      default:
        return null;
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.header}>🔷 Entity Component System</div>
      {message && (
        <div
          style={
            message.type === "success"
              ? styles.msgSuccess
              : message.type === "error"
                ? styles.msgError
                : styles.msgInfo
          }
        >
          {message.text}
        </div>
      )}
      {loading ? (
        <div style={{ color: "#888", fontSize: "0.875rem" }}>Loading...</div>
      ) : (
        <>
          {renderStats()}
          <div style={styles.tabs}>
            {TAB_CONFIG.map((tab) => (
              <button
                key={tab.id}
                style={{ ...styles.tab, ...(activeTab === tab.id ? styles.tabActive : {}) }}
                onClick={() => setActiveTab(tab.id)}
              >
                {tab.icon} {tab.label}
              </button>
            ))}
          </div>
          {renderTabContent(activeTab)}
        </>
      )}
    </div>
  );
};

export default ECSPanel;