import React, { useState } from "react";
import { pyodideBridge } from "../pyodideBridge";

interface AssessmentViewProps {
  curriculumYaml: string;
  lessonYaml: string;
}

export const AssessmentView: React.FC<AssessmentViewProps> = ({ curriculumYaml, lessonYaml }) => {
  const [title, setTitle] = useState("Unit 1 Class Quiz");
  const [totalMarks, setTotalMarks] = useState(15);
  const [paperYaml, setPaperYaml] = useState<string>("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string>("");

  const handleAssemble = async () => {
    setIsGenerating(true);
    setError("");
    try {
      const generated = await pyodideBridge.compileAssessment(curriculumYaml, lessonYaml, totalMarks);
      setPaperYaml(generated);
    } catch (err: any) {
      setError(err.message);
      setPaperYaml("");
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="assessment-layout">
      {/* Left panel: configurations */}
      <div className="config-col glass-panel" style={{ padding: "24px" }}>
        <h3 className="drawer-title" style={{ fontSize: "1.2rem", marginBottom: "16px" }}>Assessment Compiler</h3>
        
        <div className="form-group">
          <label className="form-label">Quiz Title</label>
          <input
            type="text"
            className="form-input"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
        </div>

        <div className="form-group">
          <label className="form-label">Total Marks Budget</label>
          <input
            type="number"
            className="form-input"
            value={totalMarks}
            onChange={(e) => setTotalMarks(parseInt(e.target.value) || 10)}
            min={5}
            max={50}
          />
        </div>

        <button
          className="btn-primary"
          style={{ width: "100%", marginTop: "10px", padding: "12px" }}
          onClick={handleAssemble}
          disabled={isGenerating}
        >
          {isGenerating ? "Assembling Quiz..." : "Assemble Assessment Paper"}
        </button>

        {error && (
          <div style={{ color: "#fca5a5", fontSize: "0.8rem", marginTop: "12px", background: "rgba(239, 68, 68, 0.1)", padding: "10px", borderRadius: "6px" }}>
            <strong>Assembly failed:</strong> {error}
          </div>
        )}
      </div>

      {/* Right panel: compiled paper display */}
      <div className="paper-col">
        <div className="editor-header" style={{ borderRadius: "12px 12px 0 0", border: "1px solid var(--border-color)", borderBottom: "none" }}>
          <span className="pane-title">Compiled Assessment Paper (YAML)</span>
        </div>
        <pre className="paper-viewer">
          {paperYaml || "# Click \"Assemble Assessment Paper\" on the left to generate the exam spec using the Python blueprints engine..."}
        </pre>
      </div>
    </div>
  );
};
