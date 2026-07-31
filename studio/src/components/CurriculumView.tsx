import React, { useState, useEffect } from "react";
import ReactFlow, {
  Controls,
  Background,
  Handle,
  Position,
  useNodesState,
  useEdgesState,
} from "reactflow";
import type { Node, Edge, Connection } from "reactflow";
import "reactflow/dist/style.css";
import { pyodideBridge } from "../pyodideBridge";
import { usePanelResizer } from "../hooks/usePanelResizer";

// Custom node rendering component
const CustomNode = ({ data }: any) => {
  let nodeClass = "custom-node custom-node-concept";
  if (data.type === "skill") nodeClass = "custom-node custom-node-skill";
  if (data.type === "misconception") nodeClass = "custom-node custom-node-misconception";

  return (
    <div className={nodeClass}>
      {/* Concept input handle for prerequisite */}
      {data.type === "concept" && (
        <Handle type="target" position={Position.Top} id="pre" style={{ background: "#8b5cf6", width: 8, height: 8 }} />
      )}

      {/* Left/Right handles for concept side connections */}
      {data.type === "concept" && (
        <>
          <Handle type="source" position={Position.Left} id="to-skill" style={{ background: "#06b6d4", width: 6, height: 6 }} />
          <Handle type="source" position={Position.Right} id="to-misconception" style={{ background: "#f97316", width: 6, height: 6 }} />
        </>
      )}

      {/* Inputs for child nodes */}
      {data.type === "skill" && (
        <Handle type="target" position={Position.Right} style={{ background: "#06b6d4", width: 6, height: 6 }} />
      )}
      {data.type === "misconception" && (
        <Handle type="target" position={Position.Left} style={{ background: "#f97316", width: 6, height: 6 }} />
      )}

      <div className="node-title">{data.label}</div>
      <div className="node-code">{data.code}</div>

      {/* Concept output handle for prerequisites */}
      {data.type === "concept" && (
        <Handle type="source" position={Position.Bottom} id="post" style={{ background: "#8b5cf6", width: 8, height: 8 }} />
      )}
    </div>
  );
};

const nodeTypes = {
  custom: CustomNode,
};

interface CurriculumViewProps {
  initialYaml: string;
  onChangeCurriculumYaml: (text: string) => void;
  onNodeClick?: (nodeId: string) => void;
}

export const CurriculumView: React.FC<CurriculumViewProps> = ({ initialYaml, onChangeCurriculumYaml, onNodeClick: onNodeClickProp }) => {
  const [yamlText, setYamlText] = useState(initialYaml);
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedElement, setSelectedElement] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const { sidebarWidth, editorWidth, startResizing } = usePanelResizer(
    typeof window !== "undefined" ? Math.round((window.innerWidth - 300) / 2) : 450,
    typeof window !== "undefined" ? Math.round((window.innerWidth - 300) / 2) : 450
  );

  useEffect(() => {
    setYamlText(initialYaml);
  }, [initialYaml]);

  // Main effect to parse YAML script and update graph nodes
  useEffect(() => {
    const updateGraph = async () => {
      try {
        const parsed = await pyodideBridge.parseCurriculum(yamlText);
        if (parsed.error) {
          setError(parsed.error);
          return;
        }
        setError(null);

        const { concepts = [], skills = [], misconceptions = [], dependencies = [] } = parsed;
        const initialNodes: Node[] = [];
        const initialEdges: Edge[] = [];

        // Lay out concepts in vertical sequence down the center
        concepts.forEach((concept: any, index: number) => {
          const conceptY = index * 360 + 80; // wider vertical spacing (360px)
          const conceptX = 280;

          // Add concept node
          initialNodes.push({
            id: `concept-${concept.code}`,
            type: "custom",
            position: { x: conceptX, y: conceptY },
            data: {
              label: concept.name,
              code: concept.code,
              type: "concept",
              description: concept.description,
              exam_weight: concept.exam_weight,
              raw: concept,
            },
          });

          // Symmetrical vertical stack for skills on the left
          const conceptSkills = skills.filter((s: any) => s.concept === concept.code);
          conceptSkills.forEach((skill: any, sIdx: number) => {
            const skillX = conceptX - 320; // wider horizontal span (320px)
            const skillY = conceptY + (sIdx - (conceptSkills.length - 1) / 2) * 110;

            initialNodes.push({
              id: `skill-${skill.code}`,
              type: "custom",
              position: { x: skillX, y: skillY },
              data: {
                label: skill.name,
                code: skill.code,
                type: "skill",
                concept: skill.concept,
                exam_weight: skill.exam_weight,
                raw: skill,
              },
            });

            // Edge from concept to skill
            initialEdges.push({
              id: `edge-concept-${concept.code}-skill-${skill.code}`,
              source: `concept-${concept.code}`,
              target: `skill-${skill.code}`,
              sourceHandle: "to-skill",
              style: { stroke: "#06b6d4", strokeWidth: 2, strokeDasharray: "4 4" },
            });
          });

          // Symmetrical vertical stack for misconceptions on the right
          const conceptMisconceptions = misconceptions.filter((m: any) => m.concept === concept.code);
          conceptMisconceptions.forEach((misconception: any, mIdx: number) => {
            const misconceptionX = conceptX + 320;
            const misconceptionY = conceptY + (mIdx - (conceptMisconceptions.length - 1) / 2) * 110;

            initialNodes.push({
              id: `misconception-${misconception.code}`,
              type: "custom",
              position: { x: misconceptionX, y: misconceptionY },
              data: {
                label: misconception.name,
                code: misconception.code,
                type: "misconception",
                concept: misconception.concept,
                remediation_weight: misconception.remediation_weight,
                raw: misconception,
              },
            });

            // Edge from concept to misconception
            initialEdges.push({
              id: `edge-concept-${concept.code}-misconception-${misconception.code}`,
              source: `concept-${concept.code}`,
              target: `misconception-${misconception.code}`,
              sourceHandle: "to-misconception",
              style: { stroke: "#f97316", strokeWidth: 2, strokeDasharray: "4 4" },
            });
          });
        });

        // Add prerequisite edges between concepts
        dependencies.forEach((dep: any) => {
          if (dep.rel_type === "prerequisite") {
            initialEdges.push({
              id: `edge-prereq-${dep.from}-${dep.to}`,
              source: `concept-${dep.from}`,
              target: `concept-${dep.to}`,
              sourceHandle: "post",
              targetHandle: "pre",
              animated: true,
              style: { stroke: "#8b5cf6", strokeWidth: 3 },
            });
          }
        });

        setNodes(initialNodes);
        setEdges(initialEdges);
      } catch (err: any) {
        setError(err.message);
      }
    };

    if (yamlText) {
      updateGraph();
    }
  }, [yamlText]);

  // Handle node selection to show details in drawer
  const onNodeClick = (_event: React.MouseEvent, node: Node) => {
    setSelectedElement(node.data);
    if (onNodeClickProp) onNodeClickProp(node.data.code);
  };

  // Add a prerequisite dependency edge visually
  const onConnect = async (params: Connection) => {
    if (
      params.source &&
      params.target &&
      params.sourceHandle === "post" &&
      params.targetHandle === "pre"
    ) {
      const fromCode = params.source.replace("concept-", "");
      const toCode = params.target.replace("concept-", "");
      try {
        const newYaml = await pyodideBridge.addDependency(yamlText, fromCode, toCode);
        setYamlText(newYaml);
        onChangeCurriculumYaml(newYaml);
      } catch (err) {
        console.error("Failed to add dependency visually:", err);
      }
    }
  };

  // Remove a prerequisite dependency edge visually (press Delete key on selected edge)
  const onEdgesDelete = async (edgesToDelete: Edge[]) => {
    let currentYaml = yamlText;
    let changed = false;
    for (const edge of edgesToDelete) {
      if (edge.id.startsWith("edge-prereq-")) {
        const fromCode = edge.source.replace("concept-", "");
        const toCode = edge.target.replace("concept-", "");
        try {
          currentYaml = await pyodideBridge.removeDependency(currentYaml, fromCode, toCode);
          changed = true;
        } catch (err) {
          console.error("Failed to remove dependency visually:", err);
        }
      }
    }
    if (changed) {
      setYamlText(currentYaml);
      onChangeCurriculumYaml(currentYaml);
    }
  };

  return (
    <div className="lesson-layout" style={{ display: "flex", width: "100%", height: "100%" }}>
      {/* 1. LEFT COLUMN: CURRICULUM SPECIFICATION EDITOR */}
      <div className="editor-area" style={{ width: `${sidebarWidth}px`, flexShrink: 0, display: "flex", flexDirection: "column" }}>
        <div className="editor-header" style={{ borderBottom: "1px solid var(--border-color)", flexShrink: 0 }}>
          <span className="pane-title">Curriculum Specification</span>
        </div>
        <textarea
          className="yaml-textarea"
          value={yamlText}
          onChange={(e) => {
            setYamlText(e.target.value);
            onChangeCurriculumYaml(e.target.value);
          }}
          spellCheck="false"
          placeholder="# Author curriculum graph nodes and dependencies..."
          style={{ fontSize: "0.95rem", lineHeight: "1.6", letterSpacing: "0.2px" }}
        />

        {error && (
          <div className="errors-panel">
            <h4 className="drawer-section-title" style={{ color: "#fca5a5", fontSize: "0.75rem" }}>Compilation Error</h4>
            <div className="error-item">{error}</div>
          </div>
        )}
      </div>

      {/* Resizer Divider 1 */}
      <div className="resizer-col" onMouseDown={(e) => startResizing(e, "sidebar")} />

      {/* 2. MIDDLE COLUMN: REACT FLOW CANVAS */}
      <div className="editor-area" style={{ width: `${editorWidth}px`, flexShrink: 0, height: "100%", position: "relative", display: "flex", flexDirection: "column" }}>
        <div className="editor-header" style={{ borderBottom: "1px solid var(--border-color)", flexShrink: 0 }}>
          <span className="pane-title">Interactive Graph Visualizer</span>
        </div>

        <div style={{ flex: 1, position: "relative", minHeight: 0 }}>
          {/* Floating Legend */}
          <div className="graph-legend glass-panel" style={{
            position: "absolute",
            top: "16px",
            left: "16px",
            zIndex: 10,
            padding: "12px 16px",
            display: "flex",
            flexDirection: "column",
            gap: "8px",
            fontSize: "0.72rem",
            pointerEvents: "none",
            background: "rgba(15, 23, 42, 0.75)",
            border: "1px solid var(--border-color)",
            borderRadius: "8px",
            backdropFilter: "blur(8px)"
          }}>
            <div style={{ fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.5px", color: "var(--text-muted)", marginBottom: "4px" }}>
              Curriculum Legend
            </div>
            
            {/* Concept */}
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span style={{ width: "10px", height: "10px", borderRadius: "3px", background: "rgba(139, 92, 246, 0.25)", border: "1.5px solid var(--primary)", display: "inline-block" }} />
              <span style={{ fontWeight: 600, color: "#e2e8f0" }}>Concept Node</span>
            </div>
            
            {/* Skill */}
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span style={{ width: "10px", height: "10px", borderRadius: "3px", background: "rgba(6, 182, 212, 0.25)", border: "1.5px solid var(--secondary)", display: "inline-block" }} />
              <span style={{ fontWeight: 600, color: "#e2e8f0" }}>Skill Node</span>
            </div>
            
            {/* Misconception */}
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span style={{ width: "10px", height: "10px", borderRadius: "3px", background: "rgba(249, 115, 22, 0.25)", border: "1.5px solid var(--accent)", display: "inline-block" }} />
              <span style={{ fontWeight: 600, color: "#e2e8f0" }}>Misconception Node</span>
            </div>

            <div style={{ borderTop: "1px solid var(--border-color)", margin: "4px 0", paddingTop: "4px" }} />

            {/* Prerequisite line */}
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span style={{ width: "16px", height: "2px", background: "#8b5cf6", display: "inline-block" }} />
              <span style={{ color: "var(--text-muted)" }}>Prerequisite connection</span>
            </div>

            {/* Teaches line */}
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span style={{ width: "16px", height: "2px", background: "#06b6d4", display: "inline-block" }} />
              <span style={{ color: "var(--text-muted)" }}>Teaches mapping</span>
            </div>

            {/* Misconception line */}
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span style={{ width: "16px", height: "2px", borderTop: "2px dashed #f97316", display: "inline-block" }} />
              <span style={{ color: "var(--text-muted)" }}>Diagnoses mapping</span>
            </div>
          </div>

          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            nodeTypes={nodeTypes}
            onNodeClick={onNodeClick}
            onConnect={onConnect}
            onEdgesDelete={onEdgesDelete}
            fitView
            attributionPosition="bottom-right"
          >
            <Background color="rgba(255,255,255,0.05)" gap={16} />
            <Controls />
          </ReactFlow>
        </div>
      </div>

      {/* Resizer Divider 2 */}
      <div className="resizer-col" onMouseDown={(e) => startResizing(e, "editor")} />

      {/* 3. RIGHT COLUMN: DETAILS DRAW PANELS */}
      <div className="lesson-preview-area" style={{ flex: 1, display: "flex", flexDirection: "column", height: "100%", overflowY: "auto" }}>
        <div className="editor-header" style={{ borderBottom: "1px solid var(--border-color)", flexShrink: 0 }}>
          <span className="pane-title">Element Inspector</span>
        </div>

        <div className="details-drawer glass-panel" style={{ flex: 1, borderLeft: "none", width: "100%", height: "100%", padding: "20px", display: "flex", flexDirection: "column", gap: "20px", overflowY: "auto" }}>
          {selectedElement ? (
            <>
              <div className="drawer-header">
                <span className={`drawer-badge badge-${selectedElement.type}`}>
                  {selectedElement.type}
                </span>
                <h2 className="drawer-title" style={{ marginTop: 8 }}>{selectedElement.label}</h2>
                <p className="node-code" style={{ marginTop: 4 }}>ID: {selectedElement.code}</p>
              </div>

              {selectedElement.type === "concept" && (
                <>
                  <div>
                    <h4 className="drawer-section-title">Description</h4>
                    <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", lineHeight: 1.5 }}>
                      {selectedElement.description || "No description provided."}
                    </p>
                  </div>
                  <div>
                    <h4 className="drawer-section-title">Exam Weight</h4>
                    <p style={{ fontSize: "1.1rem", fontWeight: "bold", color: "var(--secondary)" }}>
                      {selectedElement.exam_weight ? (selectedElement.exam_weight * 100).toFixed(0) + "%" : "N/A"}
                    </p>
                  </div>
                </>
              )}

              {selectedElement.type === "skill" && (
                <>
                  <div>
                    <h4 className="drawer-section-title">Belongs to Concept</h4>
                    <p style={{ fontSize: "0.85rem", color: "var(--primary-hover)" }}>
                      {selectedElement.concept}
                    </p>
                  </div>
                  <div>
                    <h4 className="drawer-section-title">Exam Importance</h4>
                    <p style={{ fontSize: "1.1rem", fontWeight: "bold", color: "var(--secondary)" }}>
                      {selectedElement.exam_weight ? (selectedElement.exam_weight * 100).toFixed(0) + "%" : "N/A"}
                    </p>
                  </div>
                </>
              )}

              {selectedElement.type === "misconception" && (
                <>
                  <div>
                    <h4 className="drawer-section-title">Belongs to Concept</h4>
                    <p style={{ fontSize: "0.85rem", color: "var(--primary-hover)" }}>
                      {selectedElement.concept}
                    </p>
                  </div>
                  <div>
                    <h4 className="drawer-section-title">Remediation Weight</h4>
                    <p style={{ fontSize: "1.1rem", fontWeight: "bold", color: "var(--accent)" }}>
                      {selectedElement.remediation_weight ? (selectedElement.remediation_weight * 100).toFixed(0) + "%" : "N/A"}
                    </p>
                  </div>
                </>
              )}
            </>
          ) : (
            <div style={{ display: "flex", flex: 1, alignItems: "center", justifyContent: "center", color: "var(--text-muted)", fontSize: "0.85rem", textAlign: "center" }}>
              Click on any node in the graph to inspect its properties.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
