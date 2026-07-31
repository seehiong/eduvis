import React, { useState, useEffect } from "react";

interface InspectorPanelProps {
  activeNodeId: string | null;
  onClose: () => void;
  curriculumData: any;
  learnerData?: any;
  onUpdateNode?: (nodeType: string, code: string, updates: any) => void;
}

export const InspectorPanel: React.FC<InspectorPanelProps> = ({
  activeNodeId,
  onClose,
  curriculumData,
  learnerData,
  onUpdateNode,
}) => {
  const [localNode, setLocalNode] = useState<any>(null);

  useEffect(() => {
    if (!activeNodeId || !curriculumData) {
      setLocalNode(null);
      return;
    }

    let found = null;
    let type = "";
    if (curriculumData.concepts) {
      found = curriculumData.concepts.find((c: any) => c.code === activeNodeId);
      if (found) type = "concept";
    }
    if (!found && curriculumData.skills) {
      found = curriculumData.skills.find((s: any) => s.code === activeNodeId);
      if (found) type = "skill";
    }
    if (!found && curriculumData.misconceptions) {
      found = curriculumData.misconceptions.find((m: any) => m.code === activeNodeId);
      if (found) type = "misconception";
    }

    if (found) {
      setLocalNode({ ...found, type });
    } else {
      setLocalNode(null);
    }
  }, [activeNodeId, curriculumData]);

  if (!activeNodeId) return null;

  const nodeType = localNode ? localNode.type.charAt(0).toUpperCase() + localNode.type.slice(1) : "Unknown";

  // Find upstream/downstream dependencies
  const upstream = curriculumData?.dependencies?.filter((d: any) => d.to === activeNodeId) || [];
  const downstream = curriculumData?.dependencies?.filter((d: any) => d.from === activeNodeId) || [];

  // Find telemetry from learner state
  let telemetry = null;
  if (learnerData) {
    if (nodeType === "Concept" && learnerData.concepts && learnerData.concepts[activeNodeId]) {
      telemetry = learnerData.concepts[activeNodeId];
    } else if (nodeType === "Skill" && learnerData.skills && learnerData.skills[activeNodeId]) {
      telemetry = learnerData.skills[activeNodeId];
    } else if (nodeType === "Misconception" && learnerData.misconceptions && learnerData.misconceptions[activeNodeId]) {
      telemetry = learnerData.misconceptions[activeNodeId];
    }
  }

  const handleInputChange = (field: string, value: any) => {
    if (!localNode) return;
    setLocalNode({ ...localNode, [field]: value });
  };

  const handleBlur = (field: string) => {
    if (!localNode || !onUpdateNode) return;
    const { code, type } = localNode;
    let val = localNode[field];
    if (field === "exam_weight" || field === "remediation_weight") {
      val = parseFloat(val) || 0.0;
    }
    onUpdateNode(type, code, { [field]: val });
  };

  const inputStyle: React.CSSProperties = {
    width: "100%",
    background: "rgba(255, 255, 255, 0.04)",
    border: "1px solid var(--border-color)",
    borderRadius: "6px",
    color: "#f8fafc",
    padding: "8px 12px",
    fontSize: "0.85rem",
    marginTop: "6px",
    outline: "none",
    fontFamily: "inherit",
  };

  return (
    <div style={{
      width: "320px",
      borderLeft: "1px solid var(--border-color)",
      background: "var(--bg-panel)",
      display: "flex",
      flexDirection: "column",
      height: "100%",
      position: "absolute",
      right: 0,
      top: 0,
      zIndex: 100,
      boxShadow: "-5px 0 15px rgba(0,0,0,0.2)",
    }}>
      <div style={{
        padding: "16px",
        borderBottom: "1px solid var(--border-color)",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
      }}>
        <h3 style={{ margin: 0, fontSize: "1.1rem", color: "var(--primary)" }}>Universal Inspector</h3>
        <button onClick={onClose} style={{ background: "transparent", border: "none", color: "var(--text-muted)", cursor: "pointer", fontSize: "1.2rem" }}>&times;</button>
      </div>
      
      <div style={{ padding: "16px", overflowY: "auto", flex: 1 }}>
        <div style={{ marginBottom: "20px" }}>
          <span style={{ fontSize: "0.75rem", textTransform: "uppercase", color: "var(--accent)", fontWeight: 700 }}>{nodeType}</span>
          <div style={{ marginTop: "4px" }}>
            <span style={{ fontSize: "0.8rem", color: "var(--text-muted)", fontFamily: "monospace" }}>ID: {activeNodeId}</span>
          </div>
        </div>

        {/* Editable node attributes */}
        {localNode && (
          <div style={{ display: "flex", flexDirection: "column", gap: "16px", marginBottom: "24px" }}>
            {/* Title / Name */}
            <div>
              <label style={{ fontSize: "0.8rem", color: "#94a3b8", fontWeight: 600 }}>Title</label>
              <input
                type="text"
                style={inputStyle}
                value={localNode.name || ""}
                onChange={(e) => handleInputChange("name", e.target.value)}
                onBlur={() => handleBlur("name")}
              />
            </div>

            {/* Description (Concepts only) */}
            {localNode.type === "concept" && (
              <div>
                <label style={{ fontSize: "0.8rem", color: "#94a3b8", fontWeight: 600 }}>Description</label>
                <textarea
                  style={{ ...inputStyle, minHeight: "80px", resize: "vertical" }}
                  value={localNode.description || ""}
                  onChange={(e) => handleInputChange("description", e.target.value)}
                  onBlur={() => handleBlur("description")}
                />
              </div>
            )}

            {/* Weights (Concept/Skill/Misconception) */}
            {(localNode.type === "concept" || localNode.type === "skill") && (
              <div>
                <label style={{ fontSize: "0.8rem", color: "#94a3b8", fontWeight: 600 }}>
                  Exam Weight ({(localNode.exam_weight * 100).toFixed(0)}%)
                </label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  style={{ width: "100%", marginTop: "6px" }}
                  value={localNode.exam_weight !== undefined ? localNode.exam_weight : 0.5}
                  onChange={(e) => handleInputChange("exam_weight", parseFloat(e.target.value))}
                  onMouseUp={() => handleBlur("exam_weight")}
                  onTouchEnd={() => handleBlur("exam_weight")}
                />
              </div>
            )}

            {localNode.type === "misconception" && (
              <div>
                <label style={{ fontSize: "0.8rem", color: "#94a3b8", fontWeight: 600 }}>
                  Remediation Weight ({(localNode.remediation_weight * 100).toFixed(0)}%)
                </label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  style={{ width: "100%", marginTop: "6px" }}
                  value={localNode.remediation_weight !== undefined ? localNode.remediation_weight : 0.5}
                  onChange={(e) => handleInputChange("remediation_weight", parseFloat(e.target.value))}
                  onMouseUp={() => handleBlur("remediation_weight")}
                  onTouchEnd={() => handleBlur("remediation_weight")}
                />
              </div>
            )}
          </div>
        )}

        <div style={{ borderTop: "1px solid var(--border-color)", margin: "20px 0" }} />

        {/* Upstream Dependencies */}
        <div style={{ marginBottom: "20px" }}>
          <h5 style={{ margin: "0 0 8px 0", color: "#94a3b8", fontSize: "0.85rem", fontWeight: 600 }}>Upstream Dependencies</h5>
          {upstream.length === 0 ? (
            <p style={{ margin: 0, fontSize: "0.8rem", color: "var(--text-muted)" }}>None</p>
          ) : (
            <ul style={{ margin: 0, paddingLeft: "20px", fontSize: "0.8rem", color: "#e2e8f0" }}>
              {upstream.map((d: any, i: number) => (
                <li key={i} style={{ marginBottom: "4px" }}>
                  <span style={{ fontFamily: "monospace" }}>{d.from}</span> <span style={{ color: "var(--text-muted)" }}>({d.rel_type})</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Downstream Dependencies */}
        <div style={{ marginBottom: "20px" }}>
          <h5 style={{ margin: "0 0 8px 0", color: "#94a3b8", fontSize: "0.85rem", fontWeight: 600 }}>Downstream Outcomes</h5>
          {downstream.length === 0 ? (
            <p style={{ margin: 0, fontSize: "0.8rem", color: "var(--text-muted)" }}>None</p>
          ) : (
            <ul style={{ margin: 0, paddingLeft: "20px", fontSize: "0.8rem", color: "#e2e8f0" }}>
              {downstream.map((d: any, i: number) => (
                <li key={i} style={{ marginBottom: "4px" }}>
                  <span style={{ fontFamily: "monospace" }}>{d.to}</span> <span style={{ color: "var(--text-muted)" }}>({d.rel_type})</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Telemetry / Mastery */}
        <div style={{ marginBottom: "20px" }}>
          <h5 style={{ margin: "0 0 8px 0", color: "#94a3b8", fontSize: "0.85rem", fontWeight: 600 }}>Learner Telemetry</h5>
          {!telemetry ? (
            <p style={{ margin: 0, fontSize: "0.8rem", color: "var(--text-muted)" }}>No telemetry data available.</p>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "8px", fontSize: "0.8rem" }}>
              {telemetry.mastery !== undefined && (
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span>Mastery</span>
                  <span style={{ fontWeight: 600, color: telemetry.mastery >= 0.8 ? "var(--success)" : "var(--warning)" }}>
                    {(telemetry.mastery * 100).toFixed(0)}%
                  </span>
                </div>
              )}
              {telemetry.confidence !== undefined && (
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span>Confidence</span>
                  <span style={{ fontWeight: 600 }}>
                    {(telemetry.confidence * 100).toFixed(0)}%
                  </span>
                </div>
              )}
              {telemetry.weight !== undefined && (
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span>Remediation Weight</span>
                  <span style={{ fontWeight: 600, color: "var(--error)" }}>
                    {(telemetry.weight * 100).toFixed(0)}%
                  </span>
                </div>
              )}
            </div>
          )}
        </div>

      </div>
    </div>
  );
};
