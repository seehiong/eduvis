import React, { useState, useEffect } from "react";
import { pyodideBridge } from "../pyodideBridge";
import { load as yamlLoad, dump as yamlDump } from "js-yaml";

import { usePanelResizer } from "../hooks/usePanelResizer";

interface LearnerViewProps {
  curriculumYaml: string;
  initialStateYaml: string;
  onChangeStateYaml: (text: string) => void;
}

export const LearnerView: React.FC<LearnerViewProps> = ({ curriculumYaml, initialStateYaml, onChangeStateYaml }) => {
  const [stateYaml, setStateYaml] = useState(initialStateYaml);
  const [masteryData, setMasteryData] = useState<any>(null);
  const [activeMisconceptions, setActiveMisconceptions] = useState<Record<string, boolean>>({});
  
  // Study plan configurations
  const [studyPlanYaml, setStudyPlanYaml] = useState<string>("");
  const [hoursBudget, setHoursBudget] = useState(2);
  const [mode, setMode] = useState("exam_prep");
  const [isGenerating, setIsGenerating] = useState(false);

  const { sidebarWidth, editorWidth, startResizing } = usePanelResizer(250);

  useEffect(() => {
    setStateYaml(initialStateYaml);
  }, [initialStateYaml]);

  // Run mastery projection using current curriculum and state
  const handleProjectMastery = async (currentYaml: string) => {
    try {
      const data = await pyodideBridge.projectMastery(curriculumYaml, currentYaml);
      setMasteryData(data);
      
      // Seed active misconceptions toggles
      if (data && data.misconceptions) {
        const active: Record<string, boolean> = {};
        Object.entries(data.misconceptions).forEach(([code, value]: any) => {
          active[code] = value.state === "active";
        });
        setActiveMisconceptions(active);
      }
    } catch (err) {
      console.error("Mastery projection failed:", err);
    }
  };

  useEffect(() => {
    if (stateYaml && curriculumYaml) {
      handleProjectMastery(stateYaml);
    }
  }, [stateYaml, curriculumYaml]);

  // Auto-regenerate study plan when configuration parameters change
  useEffect(() => {
    if (studyPlanYaml && stateYaml) {
      handleGenerateStudyPlan(stateYaml);
    }
  }, [mode, hoursBudget]);

  // Toggle misconception state and update the underlying YAML
  const handleToggleMisconception = (code: string) => {
    try {
      const doc = yamlLoad(stateYaml) as any;
      if (doc && doc.misconceptions && doc.misconceptions[code]) {
        const currentState = doc.misconceptions[code].state;
        doc.misconceptions[code].state = currentState === "active" ? "remediated" : "active";
        
        const updated = yamlDump(doc, { lineWidth: -1 });
        setStateYaml(updated);
        onChangeStateYaml(updated);
        handleProjectMastery(updated);

        // Auto-regenerate study plan if one is already active
        if (studyPlanYaml) {
          handleGenerateStudyPlan(updated);
        }
      }
    } catch (err) {
      console.error("Failed to update misconception YAML:", err);
    }
  };

  // Update concept mastery and confidence directly and trigger re-projection
  const handleUpdateConceptMastery = (code: string, newMastery: number) => {
    try {
      const doc = yamlLoad(stateYaml) as any;
      if (doc && doc.concepts) {
        if (!doc.concepts[code]) {
          doc.concepts[code] = { mastery: 0, confidence: 0 };
        }
        doc.concepts[code].mastery = newMastery;
        
        // If mastery goes above threshold (0.8), boost confidence slightly to match
        if (newMastery >= 0.8) {
          doc.concepts[code].confidence = Math.max(doc.concepts[code].confidence || 0, 0.8);
        } else {
          // If mastery falls low, decrease confidence to match
          doc.concepts[code].confidence = Math.min(doc.concepts[code].confidence || 0, newMastery);
        }
        
        const updated = yamlDump(doc, { lineWidth: -1 });
        setStateYaml(updated);
        onChangeStateYaml(updated);
        handleProjectMastery(updated);

        // Auto-regenerate study plan if one is already active
        if (studyPlanYaml) {
          handleGenerateStudyPlan(updated);
        }
      }
    } catch (err) {
      console.error("Failed to update concept mastery YAML:", err);
    }
  };

  // Generate study plan
  const handleGenerateStudyPlan = async (customStateYaml?: any) => {
    setIsGenerating(true);
    try {
      const targetState = (typeof customStateYaml === "string") ? customStateYaml : stateYaml;
      const plan = await pyodideBridge.generateStudyPlan(curriculumYaml, targetState, mode, hoursBudget);
      setStudyPlanYaml(plan);
    } catch (err: any) {
      setStudyPlanYaml(`# Failed to generate study plan: ${err.message}`);
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="lesson-layout" style={{ display: "flex", width: "100%", height: "100%" }}>
      {/* 1. LEFT COLUMN: SIMULATOR CONTROLS */}
      <div className="lesson-sidebar" style={{ width: `${sidebarWidth}px`, flexShrink: 0, padding: "20px", overflowY: "auto", display: "flex", flexDirection: "column", gap: "20px" }}>
        <h3 className="drawer-title" style={{ fontSize: "1.2rem", marginBottom: "6px" }}>Student Simulator</h3>
        <p style={{ fontSize: "0.8rem", color: "var(--text-muted)", lineHeight: "1.4" }}>
          Simulate a learner's state by toggling active misconceptions. The simulator dynamically re-calculates concept mastery and suggests study plans.
        </p>
        
        <div>
          <h4 className="drawer-section-title">Toggle Active Misconceptions</h4>
          <div style={{ display: "flex", flexDirection: "column", gap: "10px", marginTop: "10px" }}>
            {masteryData?.misconceptions && Object.keys(masteryData.misconceptions).map((code) => {
              const info = masteryData.misconceptions[code];
              const isActive = activeMisconceptions[code];
              return (
                <label key={code} style={{ display: "flex", alignItems: "center", gap: "10px", fontSize: "0.85rem", cursor: "pointer" }}>
                  <input
                    type="checkbox"
                    checked={isActive}
                    onChange={() => handleToggleMisconception(code)}
                    style={{ cursor: "pointer", width: 16, height: 16, accentColor: "var(--accent)" }}
                  />
                  <span style={{ color: isActive ? "var(--accent)" : "var(--text-muted)" }}>
                    {code.replace(/_/g, " ")} ({info.attempts} attempts)
                  </span>
                </label>
              );
            })}
          </div>
        </div>

        {/* Adjust Concept Mastery */}
        <div style={{ borderTop: "1px solid var(--border-color)", paddingTop: "20px" }}>
          <h4 className="drawer-section-title">Adjust Concept Mastery</h4>
          <p style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "4px", marginBottom: "12px", lineHeight: "1.4" }}>
            Slide to adjust concept values. Mastery below 80% (0.8) creates prerequisite gaps.
          </p>
          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            {masteryData?.concepts && Object.entries(masteryData.concepts).map(([code, metrics]: any) => (
              <div key={code} style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8rem" }}>
                  <span style={{ color: "var(--text-muted)", fontWeight: 500 }}>{code.replace(/_/g, " ").toUpperCase()}</span>
                  <span style={{ color: "var(--accent)", fontWeight: 600 }}>{Math.round(metrics.mastery * 100)}%</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={Math.round(metrics.mastery * 100)}
                  onChange={(e) => handleUpdateConceptMastery(code, parseInt(e.target.value) / 100)}
                  style={{ width: "100%", accentColor: "var(--accent)", cursor: "pointer" }}
                />
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Resizer Divider 1 */}
      <div className="resizer-col" onMouseDown={(e) => startResizing(e, "sidebar")} />

      {/* 2. MIDDLE COLUMN: GENERATED STUDY PLAN */}
      <div className="editor-area" style={{ width: `${editorWidth}px`, flexShrink: 0, display: "flex", flexDirection: "column", padding: "20px", overflowY: "auto", gap: "20px" }}>
        <div className="editor-header" style={{ padding: "0 0 10px 0", borderBottom: "1px solid var(--border-color)", flexShrink: 0 }}>
          <span className="pane-title">Generated Study Plan</span>
        </div>

        {/* Study Plan config */}
        <div className="glass-panel" style={{ padding: "16px", display: "flex", flexDirection: "column", gap: "12px" }}>
          <div style={{ display: "flex", gap: "16px" }}>
            <div className="form-group" style={{ flex: 1, marginBottom: 0 }}>
              <label className="form-label">Plan Mode</label>
              <select className="form-input" value={mode} onChange={(e) => setMode(e.target.value)}>
                <option value="exam_prep">Exam Prep (High exam-weight gaps first)</option>
                <option value="revision">Remediation (Weakest concepts first)</option>
                <option value="crash_course">Crash Course (Critical bottlenecks first)</option>
                <option value="lesson">Lesson Order (Prerequisites first)</option>
              </select>
            </div>

            <div className="form-group" style={{ width: "120px", marginBottom: 0 }}>
              <label className="form-label">Available Hours</label>
              <input
                type="number"
                className="form-input"
                value={hoursBudget}
                onChange={(e) => setHoursBudget(parseInt(e.target.value) || 2)}
                min={1}
                max={10}
              />
            </div>
          </div>

          <button className="btn-primary" style={{ width: "100%" }} onClick={() => handleGenerateStudyPlan()} disabled={isGenerating}>
            {isGenerating ? "Planning..." : "Generate Study Plan"}
          </button>
        </div>

        {studyPlanYaml ? (
          <div style={{ flex: 1, display: "flex", flexDirection: "column", minHeight: 0 }}>
            <pre className="paper-viewer" style={{ flex: 1, maxHeight: "none", overflowY: "auto", margin: 0 }}>{studyPlanYaml}</pre>
          </div>
        ) : (
          <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", border: "1px dashed var(--border-color)", borderRadius: "8px", color: "var(--text-muted)", fontSize: "0.85rem", minHeight: "200px" }}>
            Click "Generate Study Plan" to compute revision sequence.
          </div>
        )}
      </div>

      {/* Resizer Divider 2 */}
      <div className="resizer-col" onMouseDown={(e) => startResizing(e, "editor")} />

      {/* 3. RIGHT COLUMN: COGNITIVE MASTERY PROJECTION */}
      <div className="lesson-preview-area" style={{ flex: 1, padding: "20px", overflowY: "auto", display: "flex", flexDirection: "column", gap: "25px" }}>
        <div className="editor-header" style={{ padding: "0 0 10px 0", borderBottom: "1px solid var(--border-color)", flexShrink: 0 }}>
          <span className="pane-title">Cognitive Mastery Projection</span>
        </div>
        
        <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", lineHeight: "1.5", margin: 0 }}>
          Visualizing projected concept mastery and confidence. Prerequisite gaps propagate downstream to bottleneck advanced topics.
        </p>

        {masteryData ? (
          masteryData.error ? (
            <div className="errors-panel" style={{ margin: 0 }}>
              <h4 className="drawer-section-title" style={{ color: "#fca5a5", fontSize: "0.85rem", marginBottom: "8px" }}>
                Compilation / Projection Error
              </h4>
              <div className="error-item" style={{ color: "#fca5a5", fontSize: "0.8", whiteSpace: "pre-wrap" }}>
                {masteryData.error}
              </div>
            </div>
          ) : (
            <>
              {masteryData.concepts && (
                <div>
                  <h4 className="drawer-section-title">Concept Mastery Levels</h4>
                  <div className="mastery-grid">
                    {Object.entries(masteryData.concepts).map(([code, metrics]: any) => {
                      const masteryPercent = (metrics.mastery * 100).toFixed(0);
                      const confidencePercent = metrics.confidence !== undefined ? (metrics.confidence * 100).toFixed(0) : null;
                      
                      return (
                        <div className="mastery-card" key={code}>
                          <div className="mastery-card-header">
                            <span style={{ fontWeight: 600, fontSize: "0.9rem" }}>{code.replace(/_/g, " ").toUpperCase()}</span>
                            <span style={{ color: "var(--secondary)", fontWeight: 700, fontSize: "0.85rem" }}>
                              Mastery: {masteryPercent}% {confidencePercent !== null && `| Conf: ${confidencePercent}%`}
                            </span>
                          </div>
                          <div className="mastery-bar-track">
                            <div className="mastery-bar-fill" style={{ width: `${metrics.mastery * 100}%` }}></div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {masteryData.gaps && masteryData.gaps.length > 0 && (
                <div>
                  <h4 className="drawer-section-title" style={{ color: "#fca5a5" }}>Prerequisite Gaps & Learning Blockers</h4>
                  <div style={{ display: "flex", flexDirection: "column", gap: "10px", marginTop: "10px" }}>
                    {masteryData.gaps.map((gap: any, idx: number) => (
                      <div key={idx} className="glass-panel" style={{ padding: "12px", borderLeft: "4px solid #ef4444", background: "rgba(239, 68, 68, 0.03)" }}>
                        <div style={{ fontSize: "0.85rem", fontWeight: 600, color: "#f87171" }}>
                          Concept "{gap.concept.replace(/_/g, " ").toUpperCase()}" is blocked
                        </div>
                        <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: "4px" }}>
                          Prerequisite <strong>{gap.missing_prerequisite.replace(/_/g, " ").toUpperCase()}</strong> is under-mastered ({Math.round(gap.current_mastery * 100)}% mastery, but requires {Math.round(masteryData.mastery_threshold * 100)}% to unlock).
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )
        ) : (
          <div style={{ display: "flex", flex: 1, alignItems: "center", justifyContent: "center", color: "var(--text-muted)", fontSize: "0.85rem" }}>
            Loading cognitive mastery projection data...
          </div>
        )}
      </div>
    </div>
  );
};
