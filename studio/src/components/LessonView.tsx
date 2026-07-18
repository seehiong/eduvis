import React, { useState, useEffect } from "react";
import { pyodideBridge, type LessonStructure } from "../pyodideBridge";
import { load as yamlLoad, dump as yamlDump } from "js-yaml";
import { usePanelResizer } from "../hooks/usePanelResizer";

interface LessonViewProps {
  initialYaml: string;
  onChangeYaml: (text: string) => void;
}

type EditorTab = "yaml" | "gui";

export const LessonView: React.FC<LessonViewProps> = ({ initialYaml, onChangeYaml }) => {
  const [yamlText, setYamlText] = useState(initialYaml);
  const [editorTab, setEditorTab] = useState<EditorTab>("yaml");
  const [structure, setStructure] = useState<LessonStructure | null>(null);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [selectedSlideIndex, setSelectedSlideIndex] = useState<number>(0);
  const [svgHtml, setSvgHtml] = useState<string>("");
  const [isCompiling, setIsCompiling] = useState(false);

  const { sidebarWidth, editorWidth, startResizing } = usePanelResizer(220);

  useEffect(() => {
    setYamlText(initialYaml);
  }, [initialYaml]);

  // Extract currently active element from YAML
  const getActiveElement = (): any => {
    try {
      const doc = yamlLoad(yamlText) as any;
      if (doc && Array.isArray(doc.content)) {
        return doc.content[selectedSlideIndex] || null;
      }
    } catch (err) {}
    return null;
  };

  const activeElement = getActiveElement();

  // Compile and sync structural properties
  const handleCompile = async () => {
    setIsCompiling(true);
    try {
      const lessonStruct = await pyodideBridge.parseLessonStructure(yamlText);
      setStructure(lessonStruct);
      setWarnings(lessonStruct.warnings || []);

      if (lessonStruct.slides && lessonStruct.slides.length > 0) {
        const indexToRender = selectedSlideIndex < lessonStruct.slides.length ? selectedSlideIndex : 0;
        setSelectedSlideIndex(indexToRender);
        const svg = await pyodideBridge.renderSlide(yamlText, "", indexToRender);
        setSvgHtml(svg);
      } else {
        setSvgHtml("<svg><text y='20' fill='yellow'>No content elements to display</text></svg>");
      }
    } catch (err: any) {
      setWarnings([`ERROR: ${err.message}`]);
      setSvgHtml(`<svg><text y='20' fill='red'>Compilation failed: ${err.message}</text></svg>`);
    } finally {
      setIsCompiling(false);
    }
  };

  // Compile on yaml change
  useEffect(() => {
    if (yamlText) {
      handleCompile();
    }
  }, [yamlText]);

  // Select slide from Navigator
  const handleSelectSlide = async (index: number) => {
    setSelectedSlideIndex(index);
    try {
      const svg = await pyodideBridge.renderSlide(yamlText, "", index);
      setSvgHtml(svg);
    } catch (err: any) {
      setSvgHtml(`<svg><text y='20' fill='red'>Failed to render slide: ${err.message}</text></svg>`);
    }
  };

  // Handle GUI Form edits and synchronize them back to the YAML representation
  const handleFormChange = (path: string, value: any) => {
    try {
      const doc = yamlLoad(yamlText) as any;
      if (!doc || !Array.isArray(doc.content)) return;
      const element = doc.content[selectedSlideIndex];
      if (!element) return;

      if (path === "id") {
        element.id = value;
      } else if (path === "phase") {
        if (!element.placement) element.placement = {};
        element.placement.lesson_phase = value;
      } else if (path === "weight") {
        if (!element.placement) element.placement = {};
        element.placement.visual_weight = value;
      } else if (path === "role") {
        if (!element.placement) element.placement = {};
        element.placement.memory_role = value;
      } else if (path === "question") {
        element.question = value;
      } else if (path === "answer") {
        element.answer = value;
      } else if (path === "range_min") {
        if (!Array.isArray(element.range)) element.range = [0, 10];
        element.range[0] = Number(value);
      } else if (path === "range_max") {
        if (!Array.isArray(element.range)) element.range = [0, 10];
        element.range[1] = Number(value);
      }

      const newYaml = yamlDump(doc, { lineWidth: -1 });
      setYamlText(newYaml);
      onChangeYaml(newYaml);

      // Instant preview update
      pyodideBridge.renderSlide(newYaml, "", selectedSlideIndex).then((svg) => {
        setSvgHtml(svg);
      });
    } catch (err) {
      console.error("Form synchronization failed:", err);
    }
  };

  const handleInsertSnippet = (snippetType: string) => {
    let snippet = "";
    if (snippetType === "number_line") {
      snippet = `
- id: explore_number_line
  type: number_line
  placement:
    lesson_phase: explore
    layout_zone: center
    memory_role: example
  range: [-5, 5]
  highlight:
  - value: -2
    label: "Neg 2"
    color: red`;
    } else if (snippetType === "fact_boxes") {
      snippet = `
- id: hook_fact_boxes
  type: fact_boxes
  placement:
    lesson_phase: hook
    layout_zone: center
    memory_role: anchor
  items:
  - text: "Temperature: 5 below zero"
    border_color: blue`;
    } else if (snippetType === "mcq") {
      snippet = `
- id: practice_check
  type: multiple_choice
  concepts:
  - negative_numbers
  placement:
    lesson_phase: independent_practice
    difficulty: starter
    layout_zone: center
    memory_role: practice
  question: "Compare magnitudes: Is -5 smaller than 3?"
  options:
    A: "Yes (-5 is further left)"
    B: "No"
  answer: "A"`;
    }

    const newYaml = yamlText + snippet;
    setYamlText(newYaml);
    onChangeYaml(newYaml);
  };

  return (
    <div className="lesson-layout" style={{ display: "flex", width: "100%", height: "100%" }}>
      {/* 1. LEFT COLUMN: OUTLINE EXPLORER */}
      <div className="lesson-sidebar" style={{ width: `${sidebarWidth}px`, flexShrink: 0 }}>
        <h3 className="outline-title">Lesson Outline</h3>
        
        {structure?.slides && structure.slides.length > 0 ? (
          <div className="phase-outline-list">
            {structure.slides.map((slide) => (
              <button
                key={slide.id}
                className={`phase-outline-item ${selectedSlideIndex === slide.index ? "active" : ""}`}
                onClick={() => handleSelectSlide(slide.index)}
              >
                <span className="phase-name">
                  {slide.index + 1}. {slide.title}
                </span>
                <span className="element-id">
                  Type: {slide.type}
                </span>
              </button>
            ))}
          </div>
        ) : (
          <div style={{ color: "var(--text-muted)", fontSize: "0.8rem", textAlign: "center", marginTop: 20 }}>
            No elements found.
          </div>
        )}
      </div>

      {/* Resizer Divider 1 */}
      <div className="resizer-col" onMouseDown={(e) => startResizing(e, "sidebar")} />

      {/* 2. CENTER COLUMN: EDITOR / FORM BUILDER */}
      <div className="lesson-editor-area" style={{ width: `${editorWidth}px`, flexShrink: 0 }}>
        <div className="editor-tabs">
          <button
            className={`editor-tab-button ${editorTab === "yaml" ? "active" : ""}`}
            onClick={() => setEditorTab("yaml")}
            title="Educational Specification View"
          >
            Specification
          </button>
          <button
            className={`editor-tab-button ${editorTab === "gui" ? "active" : ""}`}
            onClick={() => setEditorTab("gui")}
            title="Visual Editor View"
          >
            Visual Editor
          </button>
        </div>

        {editorTab === "yaml" ? (
          /* YAML EDITOR */
          <textarea
            className="yaml-textarea"
            value={yamlText}
            onChange={(e) => {
              setYamlText(e.target.value);
              onChangeYaml(e.target.value);
            }}
            spellCheck="false"
            placeholder="# Author lesson content elements..."
            style={{ fontSize: "0.95rem", lineHeight: "1.6", letterSpacing: "0.2px" }}
          />
        ) : (
          /* GUI FORM EDITOR */
          <div className="form-editor-container">
            {activeElement ? (
              <>
                <h4 className="outline-title" style={{ color: "var(--primary-hover)" }}>Active Component Fields</h4>
                
                {/* Element ID */}
                <div className="form-group">
                  <label className="form-label">Element ID</label>
                  <input
                    type="text"
                    className="form-input"
                    value={activeElement.id || ""}
                    onChange={(e) => handleFormChange("id", e.target.value)}
                  />
                </div>

                {/* Element Type */}
                <div className="form-group">
                  <label className="form-label">Element Type (Read-only)</label>
                  <input
                    type="text"
                    className="form-input"
                    value={activeElement.type || ""}
                    disabled
                    style={{ opacity: 0.6 }}
                  />
                </div>

                {/* Placement Phase */}
                <div className="form-group">
                  <label className="form-label">Pedagogical Lesson Phase</label>
                  <select
                    className="form-input"
                    value={activeElement.placement?.lesson_phase || ""}
                    onChange={(e) => handleFormChange("phase", e.target.value)}
                  >
                    <option value="hook">Hook (Real-world hook)</option>
                    <option value="explore">Explore (Discovery & exploration)</option>
                    <option value="explain">Explain (Direct Instruction)</option>
                    <option value="guided_practice">Guided Practice (Worked example)</option>
                    <option value="independent_practice">Independent Practice (Routine checks)</option>
                    <option value="challenge">Challenge (Non-routine problems)</option>
                    <option value="recall">Recall (Retrieval practice)</option>
                  </select>
                </div>

                {/* Visual Weight */}
                <div className="form-group">
                  <label className="form-label">Visual Weight</label>
                  <select
                    className="form-input"
                    value={activeElement.placement?.visual_weight || "primary"}
                    onChange={(e) => handleFormChange("weight", e.target.value)}
                  >
                    <option value="primary">Primary (Core layout center)</option>
                    <option value="secondary">Secondary (Side/Supplementary)</option>
                  </select>
                </div>

                {/* Memory Role */}
                <div className="form-group">
                  <label className="form-label">Memory Role</label>
                  <select
                    className="form-input"
                    value={activeElement.placement?.memory_role || "anchor"}
                    onChange={(e) => handleFormChange("role", e.target.value)}
                  >
                    <option value="anchor">Anchor (Conceptual benchmark)</option>
                    <option value="example">Example (Worked case)</option>
                    <option value="practice">Practice (Skill reinforcement)</option>
                    <option value="misconception_fix">Misconception Fix (Remediation card)</option>
                    <option value="retrieval">Retrieval (Spaced recalling)</option>
                  </select>
                </div>

                {/* MCQ Question and Answer */}
                {activeElement.type === "multiple_choice" && (
                  <>
                    <div className="form-group">
                      <label className="form-label">Question Text</label>
                      <textarea
                        className="form-input"
                        rows={3}
                        value={activeElement.question || ""}
                        onChange={(e) => handleFormChange("question", e.target.value)}
                        style={{ resize: "none" }}
                      />
                    </div>
                    <div className="form-group">
                      <label className="form-label">Correct Option Answer Key</label>
                      <input
                        type="text"
                        className="form-input"
                        value={activeElement.answer || ""}
                        onChange={(e) => handleFormChange("answer", e.target.value)}
                      />
                    </div>
                  </>
                )}

                {/* Short Answer */}
                {activeElement.type === "short_answer" && (
                  <>
                    <div className="form-group">
                      <label className="form-label">Question Text</label>
                      <textarea
                        className="form-input"
                        rows={3}
                        value={activeElement.question || ""}
                        onChange={(e) => handleFormChange("question", e.target.value)}
                        style={{ resize: "none" }}
                      />
                    </div>
                    <div className="form-group">
                      <label className="form-label">Expected Answer</label>
                      <input
                        type="text"
                        className="form-input"
                        value={activeElement.answer || ""}
                        onChange={(e) => handleFormChange("answer", e.target.value)}
                      />
                    </div>
                  </>
                )}

                {/* Number Line Min and Max */}
                {activeElement.type === "number_line" && (
                  <div style={{ display: "flex", gap: "10px" }}>
                    <div className="form-group" style={{ flex: 1 }}>
                      <label className="form-label">Minimum Range</label>
                      <input
                        type="number"
                        className="form-input"
                        value={activeElement.range?.[0] !== undefined ? activeElement.range[0] : -10}
                        onChange={(e) => handleFormChange("range_min", e.target.value)}
                      />
                    </div>
                    <div className="form-group" style={{ flex: 1 }}>
                      <label className="form-label">Maximum Range</label>
                      <input
                        type="number"
                        className="form-input"
                        value={activeElement.range?.[1] !== undefined ? activeElement.range[1] : 10}
                        onChange={(e) => handleFormChange("range_max", e.target.value)}
                      />
                    </div>
                  </div>
                )}
              </>
            ) : (
              <div style={{ color: "var(--text-muted)", fontSize: "0.85rem", textAlign: "center", marginTop: 40 }}>
                Select an element in the outline panel to edit visually.
              </div>
            )}
          </div>
        )}

        {/* Compile actions & Validation Warnings */}
        <div className="editor-header" style={{ height: "auto", padding: "12px 20px", display: "flex", flexWrap: "wrap", gap: "10px" }}>
          <select
            className="example-select"
            onChange={(e) => {
              if (e.target.value) handleInsertSnippet(e.target.value);
              e.target.value = "";
            }}
            defaultValue=""
            style={{ padding: "6px 12px", fontSize: "0.75rem" }}
          >
            <option value="" disabled>+ Add Visual Element Snippet</option>
            <option value="number_line">Number Line</option>
            <option value="fact_boxes">Fact Boxes</option>
            <option value="mcq">MCQ Question</option>
          </select>
          <button className="btn-primary" onClick={handleCompile} disabled={isCompiling}>
            {isCompiling ? "Syncing..." : "Manual Sync & Recompile"}
          </button>
        </div>

        {warnings.length > 0 && (
          <div className="errors-panel">
            <h4 className="drawer-section-title" style={{ color: "#fca5a5", fontSize: "0.75rem" }}>Validation Warnings / Errors</h4>
            {warnings.map((warn, idx) => (
              <div key={idx} className="error-item">
                {warn}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Resizer Divider 2 */}
      <div className="resizer-col" onMouseDown={(e) => startResizing(e, "editor")} />

      {/* 3. RIGHT COLUMN: LIVE PREVIEW & ATTRIBUTES INSPECTOR */}
      <div className="lesson-preview-area" style={{ flex: 1 }}>
        <div className="editor-header" style={{ borderBottom: "1px solid var(--border-color)", flexShrink: 0 }}>
          <span className="pane-title">Slide Viewport</span>
        </div>

        <div className="slide-viewport" style={{ background: "#0b0f19", flex: 1, minHeight: "350px" }}>
          <div
            dangerouslySetInnerHTML={{ __html: svgHtml }}
            style={{ width: "100%", height: "100%", display: "flex", justifyContent: "center", alignItems: "center" }}
          />
        </div>

        {/* Elements Attributes Inspector */}
        {activeElement && (
          <div className="inspector-container">
            <h4 className="drawer-section-title" style={{ margin: 0 }}>Components Inspector</h4>
            <div className="attribute-grid">
              <div className="attribute-pill">
                <span className="attribute-label">Element Type</span>
                <span className="attribute-value" style={{ color: "var(--secondary)" }}>{activeElement.type}</span>
              </div>
              <div className="attribute-pill">
                <span className="attribute-label">Layout Zone</span>
                <span className="attribute-value">{activeElement.placement?.layout_zone || "center"}</span>
              </div>
              <div className="attribute-pill">
                <span className="attribute-label">Difficulty</span>
                <span className="attribute-value" style={{ color: "var(--accent)" }}>{activeElement.placement?.difficulty || "starter"}</span>
              </div>
              <div className="attribute-pill">
                <span className="attribute-label">Memory Role</span>
                <span className="attribute-value">{activeElement.placement?.memory_role || "anchor"}</span>
              </div>
            </div>
            {activeElement.concepts && (
              <div>
                <span className="attribute-label" style={{ fontSize: "0.75rem", display: "block", marginBottom: 6 }}>Target Concepts Mapping</span>
                <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                  {activeElement.concepts.map((conceptCode: string) => (
                    <span key={conceptCode} className="drawer-badge badge-concept" style={{ margin: 0, padding: "2px 8px", fontSize: "0.65rem" }}>
                      {conceptCode}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
