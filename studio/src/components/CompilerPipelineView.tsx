import React, { useState } from "react";
import { pyodideBridge } from "../pyodideBridge";

interface CompilerPipelineViewProps {
  curriculumYaml: string;
  lessonYaml: string;
}

export const CompilerPipelineView: React.FC<CompilerPipelineViewProps> = ({ curriculumYaml }) => {
  const [targetConcept, setTargetConcept] = useState<string>("negative_numbers");
  const [pipelineOutput, setPipelineOutput] = useState<string>("# Pipeline output will appear here...");
  const [isCompiling, setIsCompiling] = useState(false);

  const runLessonPlanner = async () => {
    setIsCompiling(true);
    setPipelineOutput("# Compiling lesson from curriculum graph...");
    try {
      const concepts = targetConcept.split(",").map(c => c.trim()).filter(c => c);
      if (concepts.length === 0) {
        setPipelineOutput("# Please specify at least one concept code.");
        setIsCompiling(false);
        return;
      }
      
      const output = await pyodideBridge.compileLesson(curriculumYaml, concepts);
      setPipelineOutput(output);
    } catch (err: any) {
      setPipelineOutput(`# Compiler Error:\\n${err.message}`);
    } finally {
      setIsCompiling(false);
    }
  };

  const runAssessmentAssembler = async () => {
    setIsCompiling(true);
    setPipelineOutput("# Assembling assessment based on curriculum & lesson...");
    try {
      const output = await pyodideBridge.compileAssessment(curriculumYaml, lessonYaml, 20); // default 20 marks
      setPipelineOutput(output);
    } catch (err: any) {
      setPipelineOutput(`# Assembler Error:\\n${err.message}`);
    } finally {
      setIsCompiling(false);
    }
  };

  return (
    <div style={{ padding: "24px", height: "100%", overflowY: "auto", display: "flex", flexDirection: "column", gap: "24px" }}>
      <div>
        <h2 style={{ marginTop: 0, color: "var(--primary)" }}>Compiler Pipeline Orchestration</h2>
        <p style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>
          Execute and inspect the intermediate representations (IR) passed between the stateless compilation stages.
        </p>
      </div>

      <div style={{ display: "flex", gap: "16px", padding: "16px", background: "rgba(255,255,255,0.02)", borderRadius: "8px", border: "1px solid var(--border-color)" }}>
        
        {/* Stage 1: Lesson Planner */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: "12px", borderRight: "1px solid var(--border-color)", paddingRight: "16px" }}>
          <h3 style={{ margin: 0, fontSize: "1rem" }}>1. Lesson Planner</h3>
          <p style={{ margin: 0, fontSize: "0.8rem", color: "var(--text-muted)" }}>Generates a pedagogical lesson structure from the Curriculum graph targeting specific concepts.</p>
          <div style={{ display: "flex", gap: "8px", flexDirection: "column", marginTop: "auto" }}>
            <input 
              type="text" 
              value={targetConcept} 
              onChange={(e) => setTargetConcept(e.target.value)}
              placeholder="e.g. negative_numbers, integers"
              style={{ padding: "8px", background: "var(--bg-dark)", border: "1px solid var(--border-color)", color: "var(--text)", borderRadius: "4px" }}
            />
            <button 
              className="btn-primary" 
              onClick={runLessonPlanner} 
              disabled={isCompiling}
              style={{ padding: "8px 16px" }}
            >
              Run Lesson Planner
            </button>
          </div>
        </div>

        {/* Stage 2: Assessment Assembler */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: "12px" }}>
          <h3 style={{ margin: 0, fontSize: "1rem" }}>2. Assessment Assembler</h3>
          <p style={{ margin: 0, fontSize: "0.8rem", color: "var(--text-muted)" }}>Consumes the Curriculum graph and Lesson specification to construct a targeted Quiz blueprint and paper.</p>
          <div style={{ display: "flex", gap: "8px", flexDirection: "column", marginTop: "auto" }}>
            <button 
              className="btn-primary" 
              onClick={runAssessmentAssembler} 
              disabled={isCompiling}
              style={{ padding: "8px 16px", marginTop: "41px" }} // aligned with input box height
            >
              Run Assessment Assembler
            </button>
          </div>
        </div>

      </div>

      {/* Output Console */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: "8px", minHeight: "300px" }}>
        <h4 style={{ margin: 0 }}>Pipeline IR Output</h4>
        <textarea
          readOnly
          value={pipelineOutput}
          style={{
            flex: 1,
            width: "100%",
            background: "var(--bg-dark)",
            color: "var(--text)",
            border: "1px solid var(--border-color)",
            padding: "16px",
            fontFamily: "monospace",
            fontSize: "0.85rem",
            borderRadius: "4px",
            resize: "none"
          }}
        />
      </div>

    </div>
  );
};
