// TypeScript Bridge for Pyodide (WASM)

export interface ProgressCallback {
  (stage: string, detail: string): void;
}

export interface LessonStructure {
  type: string;
  title: string;
  curriculum: any;
  slides: { index: number; id: string; title: string; type: string }[];
  presentation?: any;
  warnings: string[];
}

class PyodideBridge {
  private pyodide: any = null;
  private isLoaded = false;

  async init(onProgress: ProgressCallback): Promise<any> {
    if (this.isLoaded) return this.pyodide;

    try {
      onProgress("Initializing WebAssembly Core", "Loading Pyodide compiler environment...");
      
      if (!(window as any).loadPyodide) {
        throw new Error("Pyodide script tag not found in DOM.");
      }

      this.pyodide = await (window as any).loadPyodide({
        indexURL: "https://cdn.jsdelivr.net/pyodide/v0.26.2/full/",
      });

      onProgress("Loading Python Packages", "Installing PyYAML, SymPy & Click...");
      await this.pyodide.loadPackage(["pyyaml", "sympy", "click"]);

      onProgress("Downloading EduVis Core", "Fetching compiler package bundle...");
      const baseUrl = (import.meta as any).env.BASE_URL || "./";
      const zipUrl = baseUrl.endsWith("/") ? `${baseUrl}eduvis.zip` : `${baseUrl}/eduvis.zip`;
      const zipResponse = await fetch(zipUrl);
      if (!zipResponse.ok) {
        throw new Error(`Failed to fetch eduvis.zip from ${zipUrl}. Ensure pack_studio has run.`);
      }
      const zipData = await zipResponse.arrayBuffer();

      onProgress("Unpacking Modules", "Extracting package to Pyodide virtual filesystem...");
      this.pyodide.FS.writeFile("/tmp/eduvis.zip", new Uint8Array(zipData));
      
      this.pyodide.runPython(`
        import zipfile
        import sys
        import os
        sys.path.append("/tmp/eduvis_pkg")
        
        # Unpack archive
        os.makedirs("/tmp/eduvis_pkg", exist_ok=True)
        with zipfile.ZipFile("/tmp/eduvis.zip", "r") as zip_ref:
            zip_ref.extractall("/tmp/eduvis_pkg")
      `);

      onProgress("Configuring Python Engine", "Registering compiler functions...");
      this.pyodide.runPython(`
        import yaml
        import json
        from eduvis.renderers.svg.spec_renderer import SVGSpecRenderer
        from eduvis.core.validator import validate_lesson
        from eduvis.compiler.pipeline import CompilerPipeline, CompilationContext
        from eduvis.compiler.curriculum_planner import CurriculumPlanner
        from eduvis.compiler.lesson_planner import LessonPlanner
        from eduvis.compiler.assessment_assembler import AssessmentAssembler
        from eduvis.compiler.presentation_compiler import PresentationCompiler
        
        from eduvis.core.curriculum import CurriculumGraph
        from eduvis.core.learner_state import LearnerState
        from eduvis.core.transition_engine import apply_telemetry_event
        from eduvis.core.mastery_projection import MasteryGraphView
        from eduvis.core.revision_engine import generate_study_plan
        from eduvis.core.remediation_engine import trace_prerequisite_failure_root, select_next_element, generate_hint
        from eduvis.core.spaced_repetition import update_review_schedule, get_due_elements

        renderer = SVGSpecRenderer()

        # Helper method to safely load yaml and merge inline presentation fields
        def _merge_content_and_presentation(content_yaml_str, presentation_yaml_str=None):
            try:
                doc = yaml.safe_load(content_yaml_str) or {}
            except Exception:
                doc = {}
            if not isinstance(doc, dict):
                doc = {}
            if presentation_yaml_str and presentation_yaml_str.strip():
                try:
                    pres = yaml.safe_load(presentation_yaml_str)
                    if isinstance(pres, dict):
                        if "presentation" in pres:
                            doc["presentation"] = pres["presentation"]
                        else:
                            doc["presentation"] = pres
                except Exception:
                    pass
            return doc

        # Exposing core compiler operations as functions returning values to JS
        
        def validate_lesson_py(lesson_yaml):
            try:
                doc = yaml.safe_load(lesson_yaml) or {}
                errors = validate_lesson(doc)
                return json.dumps(errors)
            except Exception as e:
                return json.dumps([f"ERROR: YAML compilation error: {str(e)}"])

        def parse_lesson_structure_py(content_yaml, presentation_yaml=""):
            try:
                doc = _merge_content_and_presentation(content_yaml, presentation_yaml)
                warnings = validate_lesson(doc)
                content = doc.get("content", [])
                slides = []
                for i, element in enumerate(content):
                    if isinstance(element, dict):
                        slides.append({
                            "index": i,
                            "id": element.get("id", f"element_{i}"),
                            "title": element.get("id", f"element_{i}").replace("_", " ").title(),
                            "type": element.get("type", "unknown")
                        })
                return json.dumps({
                    "type": "lesson",
                    "title": (doc.get("lesson") or {}).get("title", "Generated Lesson"),
                    "curriculum": doc.get("curriculum", {}),
                    "slides": slides,
                    "presentation": doc.get("presentation"),
                    "warnings": warnings
                })
            except Exception as e:
                return json.dumps({"error": str(e)})

        def render_slide_py(content_yaml, presentation_yaml, index, group):
            try:
                from eduvis.cli import _element_to_spec, _ZONE_MAP, _LAYOUT_FOR_ZONE, _PHASE_STYLE, _DIFFICULTY_STYLE, _ROLE_COLOR
                doc = _merge_content_and_presentation(content_yaml, presentation_yaml)
                content = doc.get("content", [])
                if index < 0 or index >= len(content):
                    return "<svg><text y='20'>Slide index out of bounds</text></svg>"
                element = content[index]
                
                # Build spec
                placement = element.get("placement") or {}
                if "zones" in element:
                    zones = {k: [_element_to_spec(el) for el in v] if isinstance(v, list) else [_element_to_spec(v)] for k, v in element["zones"].items()}
                    layout = element.get("layout", "two-column")
                else:
                    zone = _ZONE_MAP.get(placement.get("layout_zone", "full"), "full")
                    layout = _LAYOUT_FOR_ZONE.get(zone, "header + full-width")
                    zones = {zone: [_element_to_spec(element)]}
                    
                phase = placement.get("lesson_phase", "")
                difficulty = placement.get("difficulty", "")
                memory_role = placement.get("memory_role", "")
                
                phase_style = _PHASE_STYLE.get(phase, {})
                header_color = phase_style.get("color", "#111111")
                phase_label = phase_style.get("label", "")
                
                if phase == "independent_practice" and difficulty in _DIFFICULTY_STYLE:
                    diff_style = _DIFFICULTY_STYLE[difficulty]
                    header_color = diff_style["color"]
                    phase_label = diff_style["label"]
                    
                role_color = _ROLE_COLOR.get(memory_role, "")
                
                spec_dict = {
                    "layout": layout,
                    "header_color": header_color,
                    "phase_label": phase_label,
                    "role_color": role_color,
                    "memory_role": memory_role,
                    "zones": zones,
                }
                
                spec_yaml = yaml.dump(spec_dict, allow_unicode=True, default_flow_style=False)
                title = element.get("id", "slide").replace("_", " ").title()
                return renderer.render(spec_yaml, title=title, posting_group=group)
            except Exception as e:
                return f"<svg><text y='20' fill='red'>Rendering error: {str(e)}</text></svg>"

        def parse_curriculum_py(curriculum_yaml):
            try:
                data = yaml.safe_load(curriculum_yaml) or {}
                graph = CurriculumGraph.from_dict(data)
                
                concepts_data = []
                for code, node in graph.concepts.items():
                    concepts_data.append({
                        "code": code,
                        "name": node.name,
                        "description": node.description,
                        "exam_weight": node.exam_weight
                    })
                    
                skills_data = []
                for code, skill in graph.skills.items():
                    skills_data.append({
                        "code": code,
                        "name": skill.name,
                        "concept": skill.concept,
                        "exam_weight": skill.exam_weight
                    })
                    
                misconceptions_data = []
                for code, mis in graph.misconceptions.items():
                    misconceptions_data.append({
                        "code": code,
                        "name": mis.name,
                        "concept": mis.concept,
                        "remediation_weight": mis.remediation_weight
                    })
                    
                return json.dumps({
                    "concepts": concepts_data,
                    "skills": skills_data,
                    "misconceptions": misconceptions_data,
                    "dependencies": data.get("dependencies", [])
                })
            except Exception as e:
                return json.dumps({"error": str(e)})

        def project_mastery_py(curriculum_yaml, learner_state_yaml):
            try:
                curr_data = yaml.safe_load(curriculum_yaml) or {}
                graph = CurriculumGraph.from_dict(curr_data)
                
                state_data = yaml.safe_load(learner_state_yaml) or {}
                state = LearnerState.from_dict(state_data)
                
                mastery_view = MasteryGraphView(graph, state)
                
                concepts_mastery = {}
                for code in graph.concepts.keys():
                    info = mastery_view.concept_mastery.get(code)
                    concepts_mastery[code] = {
                        "mastery": info.mastery if info else 0.0,
                        "confidence": info.confidence if info else None
                    }
                    
                skills_mastery = {}
                for code in graph.skills.keys():
                    state_s = state.skills.get(code)
                    skills_mastery[code] = {
                        "mastery": state_s.mastery if state_s else 0.0
                    }
                    
                return json.dumps({
                    "concepts": concepts_mastery,
                    "skills": skills_mastery,
                    "misconceptions": state_data.get("misconceptions", {}),
                    "gaps": mastery_view.prerequisite_gaps,
                    "mastery_threshold": mastery_view.mastery_threshold
                })
            except Exception as e:
                return json.dumps({"error": str(e)})

        def compile_lesson_py(curriculum_yaml, concept_codes):
            try:
                curr_data = yaml.safe_load(curriculum_yaml) or {}
                graph = CurriculumGraph.from_dict(curr_data)
                
                context = CompilationContext()
                context.curriculum_graph = graph
                
                stage = LessonPlanner(concept_codes=list(concept_codes))
                stage.run(context)
                
                lesson_id = list(context.lessons.keys())[0]
                lesson_data = context.lessons[lesson_id]
                return yaml.dump(lesson_data, allow_unicode=True, default_flow_style=False, sort_keys=False)
            except Exception as e:
                return f"# Compilation failed: {str(e)}"

        def compile_assessment_py(curriculum_yaml, lesson_yaml, total_marks):
            try:
                curr_data = yaml.safe_load(curriculum_yaml) or {}
                graph = CurriculumGraph.from_dict(curr_data)
                lesson_data = yaml.safe_load(lesson_yaml) or {}
                
                context = CompilationContext()
                context.curriculum_graph = graph
                context.lessons["current_lesson"] = lesson_data
                
                stage = AssessmentAssembler(total_marks=total_marks, title="Generated Quiz")
                stage.run(context)
                
                paper = context.assessment_papers["Generated Quiz"]
                return yaml.dump(paper, allow_unicode=True, default_flow_style=False, sort_keys=False)
            except Exception as e:
                return f"# Assessment assembly failed: {str(e)}"

        def generate_study_plan_py(curriculum_yaml, learner_state_yaml, mode, hours):
            try:
                curr_data = yaml.safe_load(curriculum_yaml) or {}
                graph = CurriculumGraph.from_dict(curr_data)
                
                state_data = yaml.safe_load(learner_state_yaml) or {}
                state = LearnerState.from_dict(state_data)
                
                mastery_view = MasteryGraphView(graph, state)
                plan = generate_study_plan(mastery_view, graph, hours=float(hours), mode=mode)
                plan_dict = plan.to_dict()
                
                return yaml.dump(plan_dict, allow_unicode=True, default_flow_style=False, sort_keys=False)
            except Exception as e:
                import traceback
                tb = traceback.format_exc()
                return f"# Revision generation failed: {str(e)}\\n\\n# Traceback:\\n# " + tb.replace("\\n", "\\n# ")
      `);

      this.isLoaded = true;
      onProgress("Ready", "EduVis Engine successfully running in WebAssembly.");
      return this.pyodide;
    } catch (err: any) {
      onProgress("Error", `Initialization failed: ${err.message}`);
      throw err;
    }
  }

  // --- API Methods ---

  async validateLesson(lessonYaml: string): Promise<string[]> {
    if (!this.isLoaded) return ["ERROR: Pyodide not loaded yet."];
    
    try {
      const validateFn = this.pyodide.globals.get("validate_lesson_py");
      const errorsJson = validateFn(lessonYaml);
      return JSON.parse(errorsJson);
    } catch (e: any) {
      return [`ERROR: Bridge failed: ${e.message}`];
    }
  }

  async parseLessonStructure(contentYaml: string, presentationYaml?: string): Promise<LessonStructure> {
    if (!this.isLoaded) throw new Error("Pyodide not loaded");
    
    const parseLessonFn = this.pyodide.globals.get("parse_lesson_structure_py");
    const structureJson = parseLessonFn(contentYaml, presentationYaml || "");
    return JSON.parse(structureJson);
  }

  async renderSlide(contentYaml: string, presentationYaml: string, index: number, group: string = "G1"): Promise<string> {
    if (!this.isLoaded) return "<svg><text>Pyodide not loaded</text></svg>";
    
    const renderFn = this.pyodide.globals.get("render_slide_py");
    return renderFn(contentYaml, presentationYaml, index, group);
  }

  async parseCurriculum(curriculumYaml: string): Promise<any> {
    if (!this.isLoaded) throw new Error("Pyodide not loaded");
    
    const parseCurrFn = this.pyodide.globals.get("parse_curriculum_py");
    const resultJson = parseCurrFn(curriculumYaml);
    return JSON.parse(resultJson);
  }

  async projectMastery(curriculumYaml: string, learnerStateYaml: string): Promise<any> {
    if (!this.isLoaded) throw new Error("Pyodide not loaded");

    const projectFn = this.pyodide.globals.get("project_mastery_py");
    const resultJson = projectFn(curriculumYaml, learnerStateYaml);
    return JSON.parse(resultJson);
  }

  async compileLesson(curriculumYaml: string, conceptCodes: string[]): Promise<string> {
    if (!this.isLoaded) throw new Error("Pyodide not loaded");

    const compileFn = this.pyodide.globals.get("compile_lesson_py");
    return compileFn(curriculumYaml, this.pyodide.toPy(conceptCodes));
  }

  async compileAssessment(curriculumYaml: string, lessonYaml: string, totalMarks: number): Promise<string> {
    if (!this.isLoaded) throw new Error("Pyodide not loaded");

    const compileAssFn = this.pyodide.globals.get("compile_assessment_py");
    return compileAssFn(curriculumYaml, lessonYaml, totalMarks);
  }

  async generateStudyPlan(curriculumYaml: string, learnerStateYaml: string, mode: string, hours: number): Promise<string> {
    if (!this.isLoaded) throw new Error("Pyodide not loaded");

    const planFn = this.pyodide.globals.get("generate_study_plan_py");
    return planFn(curriculumYaml, learnerStateYaml, mode, hours);
  }
}

export const pyodideBridge = new PyodideBridge();
