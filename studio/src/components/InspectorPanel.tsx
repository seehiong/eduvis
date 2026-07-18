import React from "react";

interface InspectorPanelProps {
  activeNodeId: string | null;
  onClose: () => void;
  curriculumData: any;
  learnerData?: any;
}

export const InspectorPanel: React.FC<InspectorPanelProps> = ({
  activeNodeId,
  onClose,
  curriculumData,
  learnerData,
}) => {
  if (!activeNodeId) return null;

  // Find node details from curriculum data
  let nodeType = "Unknown";
  let nodeName = "Unknown Element";
  
  if (curriculumData?.concepts?.some((c: any) => c.code === activeNodeId)) {
    nodeType = "Concept";
    nodeName = curriculumData.concepts.find((c: any) => c.code === activeNodeId).name;
  } else if (curriculumData?.skills?.some((s: any) => s.code === activeNodeId)) {
    nodeType = "Skill";
    nodeName = curriculumData.skills.find((s: any) => s.code === activeNodeId).name;
  } else if (curriculumData?.misconceptions?.some((m: any) => m.code === activeNodeId)) {
    nodeType = "Misconception";
    nodeName = curriculumData.misconceptions.find((m: any) => m.code === activeNodeId).name;
  }

  // Find upstream/downstream dependencies
  const upstream = curriculumData?.dependencies?.filter((d: any) => d.to === activeNodeId) || [];
  const downstream = curriculumData?.dependencies?.filter((d: any) => d.from === activeNodeId) || [];

  // Find telemetry from learner state (projectMastery API output returns it in concepts/skills/misconceptions maps)
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

  return (
    <div style={{
      width: "300px",
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
          <span style={{ fontSize: "0.75rem", textTransform: "uppercase", color: "var(--accent)" }}>{nodeType}</span>
          <h4 style={{ margin: "4px 0", fontSize: "1.1rem" }}>{nodeName}</h4>
          <span style={{ fontSize: "0.8rem", color: "var(--text-muted)", fontFamily: "monospace" }}>{activeNodeId}</span>
        </div>

        {/* Upstream Dependencies */}
        <div style={{ marginBottom: "20px" }}>
          <h5 style={{ margin: "0 0 8px 0", color: "var(--text)", fontSize: "0.85rem" }}>Upstream Dependencies</h5>
          {upstream.length === 0 ? (
            <p style={{ margin: 0, fontSize: "0.8rem", color: "var(--text-muted)" }}>None</p>
          ) : (
            <ul style={{ margin: 0, paddingLeft: "20px", fontSize: "0.8rem" }}>
              {upstream.map((d: any, i: number) => (
                <li key={i}>{d.from} <span style={{ color: "var(--text-muted)" }}>({d.type})</span></li>
              ))}
            </ul>
          )}
        </div>

        {/* Downstream Dependencies */}
        <div style={{ marginBottom: "20px" }}>
          <h5 style={{ margin: "0 0 8px 0", color: "var(--text)", fontSize: "0.85rem" }}>Downstream Outcomes</h5>
          {downstream.length === 0 ? (
            <p style={{ margin: 0, fontSize: "0.8rem", color: "var(--text-muted)" }}>None</p>
          ) : (
            <ul style={{ margin: 0, paddingLeft: "20px", fontSize: "0.8rem" }}>
              {downstream.map((d: any, i: number) => (
                <li key={i}>{d.to} <span style={{ color: "var(--text-muted)" }}>({d.type})</span></li>
              ))}
            </ul>
          )}
        </div>

        {/* Telemetry / Mastery */}
        <div style={{ marginBottom: "20px" }}>
          <h5 style={{ margin: "0 0 8px 0", color: "var(--text)", fontSize: "0.85rem" }}>Learner Telemetry</h5>
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
