import React, { useState, useEffect } from "react";
import { pyodideBridge } from "./pyodideBridge";
import { LoadingScreen } from "./components/LoadingScreen";
import { CurriculumView } from "./components/CurriculumView";
import { LessonView } from "./components/LessonView";
import { AssessmentView } from "./components/AssessmentView";
import { LearnerView } from "./components/LearnerView";
import { InspectorPanel } from "./components/InspectorPanel";
import { ProblemsPane } from "./components/ProblemsPane";
import { CompilerPipelineView } from "./components/CompilerPipelineView";

type ActiveView = "curriculum" | "lesson" | "assessment" | "learner" | "compiler";

export const App: React.FC = () => {
  const [isLoading, setIsLoading] = useState(true);
  const [loadingStage, setLoadingStage] = useState("Initializing IDE");
  const [loadingDetail, setLoadingDetail] = useState("Preparing layout workspace...");
  const [activeView, setActiveView] = useState<ActiveView>("curriculum");

  const [warnings, setWarnings] = useState<string[]>([]);
  const [activeNodeId, setActiveNodeId] = useState<string | null>(null);
  const [showHelp, setShowHelp] = useState(false);

  // Core specs state
  const [curriculumYaml, setCurriculumYaml] = useState("");
  const [curriculumData, setCurriculumData] = useState<any>(null);
  const [lessonYaml, setLessonYaml] = useState("");
  const [learnerStateYaml, setLearnerStateYaml] = useState("");
  const [learnerData, setLearnerData] = useState<any>(null);

  // Selectable showcase examples
  const [selectedExample, setSelectedExample] = useState("negative-numbers");

  // Fetch a file from public directory helper
  const fetchSampleFile = async (path: string): Promise<string> => {
    const baseUrl = (import.meta as any).env.BASE_URL || "./";
    const cleanPath = path.startsWith("/") ? path.slice(1) : path;
    const url = baseUrl.endsWith("/") ? `${baseUrl}${cleanPath}` : `${baseUrl}/${cleanPath}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`Could not fetch sample asset at ${url}`);
    return res.text();
  };

  // Initialize Pyodide & Fetch initial files on mount
  useEffect(() => {
    const startup = async () => {
      try {
        // Load WebAssembly compiler
        await pyodideBridge.init((stage, detail) => {
          setLoadingStage(stage);
          setLoadingDetail(detail);
        });

        setLoadingStage("Loading Workspace");
        setLoadingDetail("Loading curriculum schemas and cached workspace state...");
        
        // 1. Try to load cached states from LocalStorage first to prevent refresh loss
        const cachedExample = localStorage.getItem("eduvis_studio_example") || "negative-numbers";
        setSelectedExample(cachedExample);

        const cachedCurr = localStorage.getItem("eduvis_studio_curriculum_yaml");
        const cachedLesson = localStorage.getItem("eduvis_studio_lesson_yaml");
        const cachedState = localStorage.getItem("eduvis_studio_learner_state_yaml");

        let currYaml = cachedCurr;
        let lessonYamlText = cachedLesson;
        let stateYaml = cachedState;

        // If no cache, pull default assets
        if (!currYaml || !lessonYamlText || !stateYaml) {
          const defaults = await getShowcaseFiles(cachedExample);
          if (!currYaml) currYaml = defaults.curr;
          if (!lessonYamlText) lessonYamlText = defaults.lesson;
          if (!stateYaml) stateYaml = defaults.state;

          // Save to cache initial
          localStorage.setItem("eduvis_studio_curriculum_yaml", currYaml);
          localStorage.setItem("eduvis_studio_lesson_yaml", lessonYamlText);
          localStorage.setItem("eduvis_studio_learner_state_yaml", stateYaml);
        }

        setCurriculumYaml(currYaml);
        setLessonYaml(lessonYamlText);
        setLearnerStateYaml(stateYaml);

        // Pre-parse the curriculum graph
        const parsedGraph = await pyodideBridge.parseCurriculum(currYaml);
        setCurriculumData(parsedGraph);

        setIsLoading(false);
      } catch (err: any) {
        setLoadingStage("Startup Failure");
        setLoadingDetail(`Error: ${err.message}. Try rebuilding scripts.`);
      }
    };

    startup();
  }, []);

  // Run pedagogical validation in background
  useEffect(() => {
    if (isLoading) return;
    const timer = setTimeout(async () => {
      try {
        const errors = await pyodideBridge.validateLesson(lessonYaml);
        setWarnings(errors);
      } catch (err) {
        console.error("Validation failed", err);
      }
      
      // Update learner telemetry data for Inspector
      try {
        const lData = await pyodideBridge.projectMastery(curriculumYaml, learnerStateYaml);
        setLearnerData(lData);
      } catch (err) {
        console.error("Mastery projection failed", err);
      }
    }, 800);
    return () => clearTimeout(timer);
  }, [lessonYaml, curriculumYaml, learnerStateYaml, isLoading]);

  // Helper to resolve clean showcase files
  const getShowcaseFiles = async (exampleKey: string): Promise<{ curr: string; lesson: string; state: string }> => {
    if (exampleKey === "negative-numbers") {
      return {
        curr: await fetchSampleFile("/showcase/reference/showcase-curriculum.yaml"),
        lesson: await fetchSampleFile("/showcase/lessons/negative-numbers-confidence-ladder-lesson.yaml"),
        state: await fetchSampleFile("/showcase/reference/sample-learner-state.yaml"),
      };
    } else if (exampleKey === "adaptive-remediation") {
      return {
        curr: await fetchSampleFile("/showcase/reference/algebra-curriculum.yaml"),
        lesson: await fetchSampleFile("/showcase/lessons/algebra-linear-equations-lesson.yaml"),
        state: await fetchSampleFile("/showcase/reference/algebra-learner-state.yaml"),
      };
    } else if (exampleKey === "new-workspace") {
      return {
        curr: `schema_version: "1.0"
concepts:
  - code: "concept_1"
    name: "First Concept"
    description: "Define your learning concepts here."
    exam_weight: 1.0
skills:
  - code: "skill_1"
    name: "First Skill"
    concept: "concept_1"
    exam_weight: 1.0
misconceptions: []
dependencies: []`,
        lesson: `schema_version: "1.0"
curriculum:
  code: "new-curriculum"
  topic: "new-topic"
lesson:
  title: "New Lesson"
  concepts:
    - concept_1
progression:
  pattern: "direct_instruction"
  phases:
    - phase: "hook"
content:
  - id: hook_1
    type: fact_boxes
    placement:
      lesson_phase: hook
      layout_zone: center
      memory_role: anchor
    items:
      - text: "Edit this card in the GUI Designer or YAML Script tab!"`,
        state: `schema_version: "1.0"
learner_id: "student_1"
concepts:
  concept_1:
    mastery: 0.0
skills: {}
misconceptions: {}`,
      };
    } else {
      return {
        curr: await fetchSampleFile("/showcase/reference/catalog-curriculum.yaml"),
        lesson: await fetchSampleFile("/showcase/reference/exhaustive-element-catalog.yaml"),
        state: await fetchSampleFile("/showcase/reference/catalog-learner-state.yaml"),
      };
    }
  };

  // Handle switching between different showcases in the IDE
  const handleExampleChange = async (exampleKey: string, forceReset = false) => {
    setSelectedExample(exampleKey);
    localStorage.setItem("eduvis_studio_example", exampleKey);

    if (forceReset) {
      const defaults = await getShowcaseFiles(exampleKey);
      setCurriculumYaml(defaults.curr);
      setLessonYaml(defaults.lesson);
      setLearnerStateYaml(defaults.state);

      localStorage.setItem("eduvis_studio_curriculum_yaml", defaults.curr);
      localStorage.setItem("eduvis_studio_lesson_yaml", defaults.lesson);
      localStorage.setItem("eduvis_studio_learner_state_yaml", defaults.state);

      const parsed = await pyodideBridge.parseCurriculum(defaults.curr);
      setCurriculumData(parsed);
      setIsLoading(false);
    } else {
      // Just fetch files, but do not override local cache if already set
      setIsLoading(true);
      setLoadingStage("Switching Showcases");
      setLoadingDetail(`Fetching files for ${exampleKey}...`);

      const defaults = await getShowcaseFiles(exampleKey);
      setCurriculumYaml(defaults.curr);
      setLessonYaml(defaults.lesson);
      setLearnerStateYaml(defaults.state);

      localStorage.setItem("eduvis_studio_curriculum_yaml", defaults.curr);
      localStorage.setItem("eduvis_studio_lesson_yaml", defaults.lesson);
      localStorage.setItem("eduvis_studio_learner_state_yaml", defaults.state);

      const parsed = await pyodideBridge.parseCurriculum(defaults.curr);
      setCurriculumData(parsed);
      setIsLoading(false);
    }
  };

  // --- Workspace Actions ---

  // Export/Download YAML file to local disk
  const handleExportFile = () => {
    let text = "";
    let filename = "";

    if (activeView === "curriculum") {
      text = curriculumYaml;
      filename = "curriculum.yaml";
    } else if (activeView === "lesson") {
      text = lessonYaml;
      filename = "lesson.yaml";
    } else if (activeView === "learner") {
      text = learnerStateYaml;
      filename = "learner_state.yaml";
    } else {
      return; // Quiz compiled paper not direct editable
    }

    if (!text) return;
    const blob = new Blob([text], { type: "text/yaml" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  // Import/Upload YAML file from local disk
  const handleImportFile = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = async (e) => {
      const text = e.target?.result as string;
      if (!text) return;

      if (activeView === "lesson") {
        setLessonYaml(text);
        localStorage.setItem("eduvis_studio_lesson_yaml", text);
      } else if (activeView === "curriculum") {
        setCurriculumYaml(text);
        localStorage.setItem("eduvis_studio_curriculum_yaml", text);
        try {
          const parsed = await pyodideBridge.parseCurriculum(text);
          setCurriculumData(parsed);
        } catch (err) {
          console.error("Failed to parse imported curriculum:", err);
        }
      } else if (activeView === "learner") {
        setLearnerStateYaml(text);
        localStorage.setItem("eduvis_studio_learner_state_yaml", text);
      }
    };
    reader.readAsText(file);
    event.target.value = ""; // Clear file selector
  };

  // Reset local storage cache to retrieve pristine assets
  const handleResetToDefaults = () => {
    if (window.confirm("Are you sure you want to clear your current progress and reset to defaults?")) {
      handleExampleChange(selectedExample, true);
    }
  };

  if (isLoading) {
    return <LoadingScreen stage={loadingStage} detail={loadingDetail} />;
  }

  return (
    <div className="app-root">
      {/* Sidebar navigation */}
      <aside className="sidebar">
        <div className="sidebar-logo">EV</div>
        
        <nav className="nav-buttons" style={{ display: "flex", flexDirection: "column", height: "calc(100% - 60px)" }}>
          {/* 1. Curriculum View */}
          <button
            className={`nav-btn ${activeView === "curriculum" ? "active" : ""}`}
            onClick={() => setActiveView("curriculum")}
            title="Curriculum Graph Explorer"
          >
            <svg stroke="currentColor" fill="none" strokeWidth="2" viewBox="0 0 24 24" height="1em" width="1em">
              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
            </svg>
            Curriculum
          </button>

          {/* 2. Storyboard View */}
          <button
            className={`nav-btn ${activeView === "lesson" ? "active" : ""}`}
            onClick={() => setActiveView("lesson")}
            title="Lesson Storyboard Viewer"
          >
            <svg stroke="currentColor" fill="none" strokeWidth="2" viewBox="0 0 24 24" height="1em" width="1em">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
              <line x1="16" y1="13" x2="8" y2="13" />
              <line x1="16" y1="17" x2="8" y2="17" />
              <polyline points="10 9 9 9 8 9" />
            </svg>
            Storyboard
          </button>

          {/* 3. Assessment View */}
          <button
            className={`nav-btn ${activeView === "assessment" ? "active" : ""}`}
            onClick={() => setActiveView("assessment")}
            title="Assessment Blueprint & Quiz Assembler"
          >
            <svg stroke="currentColor" fill="none" strokeWidth="2" viewBox="0 0 24 24" height="1em" width="1em">
              <path d="M9 11l3 3L22 4" />
              <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
            </svg>
            Assessment
          </button>

          {/* 4. Learner Projection */}
          <button
            className={`nav-btn ${activeView === "learner" ? "active" : ""}`}
            onClick={() => setActiveView("learner")}
            title="Student Mastery Simulator"
          >
            <svg stroke="currentColor" fill="none" strokeWidth="2" viewBox="0 0 24 24" height="1em" width="1em">
              <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
            </svg>
            Learner
          </button>

          {/* 5. Compiler Pipeline View */}
          <button
            className={`nav-btn ${activeView === "compiler" ? "active" : ""}`}
            onClick={() => setActiveView("compiler")}
            title="Compiler Pipeline Inspector"
          >
            <svg stroke="currentColor" fill="none" strokeWidth="2" viewBox="0 0 24 24" height="1em" width="1em">
              <rect x="2" y="2" width="20" height="8" rx="2" ry="2" />
              <rect x="2" y="14" width="20" height="8" rx="2" ry="2" />
              <line x1="6" y1="6" x2="6.01" y2="6" />
              <line x1="6" y1="18" x2="6.01" y2="18" />
            </svg>
            Compiler
          </button>

          {/* 6. Help Overlay Trigger */}
          <button
            className="nav-btn"
            style={{ marginTop: "auto", borderTop: "1px solid var(--border-color)", paddingTop: "12px", color: "var(--accent)" }}
            onClick={() => setShowHelp(true)}
            title="Studio Documentation & Help"
          >
            <svg stroke="currentColor" fill="none" strokeWidth="2" viewBox="0 0 24 24" height="1em" width="1em">
              <circle cx="12" cy="12" r="10" />
              <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
              <line x1="12" y1="17" x2="12.01" y2="17" />
            </svg>
            Help
          </button>
        </nav>
      </aside>

      {/* Main container panel */}
      <main className="main-content">
        <header className="top-bar">
          <div style={{ display: "flex", flexDirection: "column" }}>
            <h1 className="top-bar-title" style={{ margin: 0 }}>
              {activeView === "curriculum" && "Curriculum View"}
              {activeView === "lesson" && "Storyboard View"}
              {activeView === "assessment" && "Assessment View"}
              {activeView === "learner" && "Learner Projection"}
            </h1>
            <span style={{ fontSize: "0.75rem", color: "var(--accent)", fontWeight: 600, letterSpacing: "0.05em", marginTop: "4px" }}>
              SINGAPORE SECONDARY 1 MATHEMATICS
            </span>
          </div>

          {/* Workspace operations controls */}
          <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
            {/* Import / Export actions */}
            {activeView !== "assessment" && (
              <div style={{ display: "flex", gap: "8px" }}>
                {/* Hidden File Input */}
                <input
                  type="file"
                  id="studio-file-import"
                  style={{ display: "none" }}
                  onChange={handleImportFile}
                  accept=".yaml,.yml"
                />
                
                {/* Import Button */}
                <button
                  className="slide-tab"
                  style={{ padding: "6px 12px", fontSize: "0.75rem" }}
                  onClick={() => document.getElementById("studio-file-import")?.click()}
                  title="Import local YAML file"
                >
                  Import File
                </button>

                {/* Export Button */}
                <button
                  className="slide-tab"
                  style={{ padding: "6px 12px", fontSize: "0.75rem" }}
                  onClick={handleExportFile}
                  title="Download current YAML spec"
                >
                  Export File
                </button>
              </div>
            )}

            {/* Reset Defaults button */}
            <button
              className="slide-tab"
              style={{ padding: "6px 12px", fontSize: "0.75rem", border: "1px solid rgba(239, 68, 68, 0.25)", color: "#fca5a5" }}
              onClick={handleResetToDefaults}
              title="Reset workspace cache to default examples"
            >
              Reset Defaults
            </button>

            {/* Example Spec dropdown */}
            <div className="example-picker">
              <span style={{ fontSize: "0.8rem", color: "var(--text-muted)", fontWeight: 500 }}>Example Spec:</span>
              <select
                className="example-select"
                value={selectedExample}
                onChange={(e) => handleExampleChange(e.target.value)}
              >
                <option value="negative-numbers">Singapore Mathematics - Negative Numbers</option>
                <option value="adaptive-remediation">Algebra - Equations & Balancing (Adaptive)</option>
                <option value="elements-catalog">Exhaustive Layout Element Catalog</option>
                <option value="new-workspace">+ Create New Blank Workspace</option>
              </select>
            </div>
          </div>
        </header>

        {/* View containers */}
        <section className="view-container">
          {activeView === "curriculum" && (
            <CurriculumView
              initialYaml={curriculumYaml}
              onNodeClick={(id) => setActiveNodeId(id)}
              onChangeCurriculumYaml={async (newYaml) => {
                setCurriculumYaml(newYaml);
                localStorage.setItem("eduvis_studio_curriculum_yaml", newYaml);
                try {
                  const parsed = await pyodideBridge.parseCurriculum(newYaml);
                  if (!parsed.error) {
                    setCurriculumData(parsed);
                  }
                } catch (err) {
                  console.error("Dynamic curriculum compilation failed:", err);
                }
              }}
            />
          )}
          {activeView === "lesson" && (
            <LessonView
              initialYaml={lessonYaml}
              onChangeYaml={(newYaml) => {
                setLessonYaml(newYaml);
                localStorage.setItem("eduvis_studio_lesson_yaml", newYaml);
              }}
            />
          )}
          {activeView === "assessment" && (
            <AssessmentView curriculumYaml={curriculumYaml} lessonYaml={lessonYaml} />
          )}
          {activeView === "learner" && (
            <LearnerView
              curriculumYaml={curriculumYaml}
              initialStateYaml={learnerStateYaml}
              onChangeStateYaml={(newYaml) => {
                setLearnerStateYaml(newYaml);
                localStorage.setItem("eduvis_studio_learner_state_yaml", newYaml);
              }}
            />
          )}
          {activeView === "compiler" && (
            <CompilerPipelineView curriculumYaml={curriculumYaml} lessonYaml={lessonYaml} />
          )}
        </section>

        <InspectorPanel 
          activeNodeId={activeNodeId} 
          onClose={() => setActiveNodeId(null)}
          curriculumData={curriculumData}
          learnerData={learnerData}
          onUpdateNode={async (nodeType, code, updates) => {
            try {
              const newYaml = await pyodideBridge.updateNode(curriculumYaml, nodeType, code, updates);
              setCurriculumYaml(newYaml);
              localStorage.setItem("eduvis_studio_curriculum_yaml", newYaml);
              const parsed = await pyodideBridge.parseCurriculum(newYaml);
              if (!parsed.error) {
                setCurriculumData(parsed);
              }
            } catch (err) {
              console.error("Failed to update node details:", err);
            }
          }}
        />
        <ProblemsPane warnings={warnings} />

      </main>

      {/* Help Modal Overlay */}
      {showHelp && (
        <div style={{
          position: "fixed",
          inset: 0,
          background: "rgba(9, 13, 22, 0.85)",
          backdropFilter: "blur(8px)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          zIndex: 9999,
          padding: "24px",
        }}>
          <div className="glass-panel" style={{
            maxWidth: "720px",
            width: "100%",
            maxHeight: "85vh",
            overflowY: "auto",
            padding: "32px",
            border: "1px solid var(--border-color)",
            borderRadius: "16px",
            position: "relative",
            background: "#0c111d",
            boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.5)",
          }}>
            {/* Close Button */}
            <button
              onClick={() => setShowHelp(false)}
              style={{
                position: "absolute",
                top: "16px",
                right: "16px",
                background: "transparent",
                border: "none",
                color: "var(--text-muted)",
                fontSize: "1.5rem",
                cursor: "pointer",
              }}
              title="Close dialog"
            >
              &times;
            </button>

            <h2 style={{ color: "var(--primary)", marginTop: 0, fontSize: "1.6rem", borderBottom: "1px solid var(--border-color)", paddingBottom: "12px" }}>
              EduVis Studio Help & Guide
            </h2>

            <p style={{ fontSize: "0.9rem", lineHeight: "1.6", color: "var(--text-muted)", fontStyle: "italic", marginBottom: "20px" }}>
              "EduVis Studio is not another YAML editor. It is a multi-projection educational IDE where text, graphs, diagnostics, and compiler views are synchronized representations of the same educational specification. Every projection is a synchronized view over the same educational specification; no projection owns the data."
            </p>

            <h3 style={{ color: "var(--secondary)", marginTop: "24px" }}>Workspace Projections</h3>
            <ul style={{ paddingLeft: "20px", display: "flex", flexDirection: "column", gap: "10px", fontSize: "0.85rem", lineHeight: "1.5", color: "var(--text-muted)" }}>
              <li>
                <strong>Curriculum View:</strong> An interactive concept dependency graph mapping Concepts, Skills, and Misconceptions.
              </li>
              <li>
                <strong>Storyboard View:</strong> A visual outline displaying slides grouped by lesson phases (Hook, Explore, Explain, Practice, Retrieve).
              </li>
              <li>
                <strong>Assessment View:</strong> An analytics pane charting concept/skill coverage and difficulty progressions.
              </li>
              <li>
                <strong>Learner Projection:</strong> A student state simulator mapping cognitive mastery levels directly onto the graph canvas.
              </li>
            </ul>

            <h3 style={{ color: "var(--secondary)", marginTop: "20px" }}>The Specification Editor</h3>
            <p style={{ fontSize: "0.85rem", lineHeight: "1.5", color: "var(--text-muted)" }}>
              The text editor pane displayed on the left inside the <strong>Curriculum</strong> and <strong>Storyboard</strong> views is the <strong>Specification View</strong>. It displays the raw educational specification YAML, serving as the absolute source of truth. Changes typed here immediately compile and update the visual projections.
            </p>

            <h3 style={{ color: "var(--secondary)", marginTop: "20px" }}>The Universal Relationship Explorer</h3>
            <p style={{ fontSize: "0.85rem", lineHeight: "1.5", color: "var(--text-muted)" }}>
              Invoked contextually from any active projection. Clicking any element (concept, skill, or misconception) opens a localized, multidirectional inspector displaying prerequisites, outcomes, linked lessons, assessment papers, and cognitive telemetry.
            </p>

            <h3 style={{ color: "var(--secondary)", marginTop: "20px" }}>Developer Features</h3>
            <ul style={{ paddingLeft: "20px", display: "flex", flexDirection: "column", gap: "6px", fontSize: "0.85rem", lineHeight: "1.5", color: "var(--text-muted)" }}>
              <li><strong>Local File Persistence:</strong> Supports importing and exporting specification files directly to your local computer with full offline compatibility.</li>
              <li><strong>Pedagogical Diagnostics:</strong> Warnings or errors are highlighted in a bottom pane for anti-patterns (e.g., missing prerequisites).</li>
            </ul>

            <button
              className="btn-primary"
              style={{ marginTop: "28px", width: "100%", padding: "10px" }}
              onClick={() => setShowHelp(false)}
            >
              Got it, let's build!
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default App;
