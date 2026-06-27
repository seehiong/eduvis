/**
 * EduVis Live Editor — Pyodide WASM Runner & Python Bridge
 */

window.pyodideInstance = null;

async function initPythonEnvironment(updateStatusCallback, onReadyCallback) {
    try {
        updateStatusCallback("Loading WebAssembly Core", "Fetching Pyodide environment...");
        
        // Temporarily hide Monaco/AMD loader to prevent loading conflicts
        const tempDefine = window.define;
        const tempRequire = window.require;
        window.define = undefined;
        window.require = undefined;

        window.pyodideInstance = await loadPyodide();

        // Restore Monaco/AMD loader
        window.define = tempDefine;
        window.require = tempRequire;

        updateStatusCallback("Setting up Micro Pip", "Loading pip installer package...");
        await window.pyodideInstance.loadPackage("micropip");

        // Dynamically detect package version from main_init.py to construct wheel filename
        let version = "0.5.0";
        try {
            const mainInitText = await fetch('./main_init.py').then(r => r.text());
            const versionMatch = mainInitText.match(/__version__\s*=\s*["']([^"']+)["']/);
            if (versionMatch) {
                version = versionMatch[1];
            }
        } catch (err) {
            console.warn("Could not determine package version from main_init.py, falling back to 0.5.0", err);
        }

        updateStatusCallback("Installing Dependencies", `Installing PyYAML and loading local wheel (v${version})...`);
        const cb = new Date().getTime();
        await window.pyodideInstance.runPythonAsync(`
            import micropip
            await micropip.install("pyyaml")
            await micropip.install("./eduvis-${version}-py3-none-any.whl?cb=${cb}")
        `);

        updateStatusCallback(`Syncing v${version} Engine Updates`, "Fetching local core files...");
        try {
            const [engineCode, validatorCode, genericCode, renderersBaseCode, curriculumCode, coreInitCode, mainInitCode, constantsCode] = await Promise.all([
                fetch('./engine.py').then(r => r.text()),
                fetch('./validator.py').then(r => r.text()),
                fetch('./generic.py').then(r => r.text()),
                fetch('./renderers_base.py').then(r => r.text()),
                fetch('./curriculum.py').then(r => r.text()),
                fetch('./core_init.py').then(r => r.text()),
                fetch('./main_init.py').then(r => r.text()),
                fetch('./constants.py').then(r => r.text())
            ]);

            const ensureDir = (path) => {
                const parts = path.split('/');
                let current = '';
                for (let i = 0; i < parts.length - 1; i++) {
                    if (!parts[i]) continue;
                    current += '/' + parts[i];
                    try { window.pyodideInstance.FS.mkdir(current); } catch(e) {}
                }
            };

            ensureDir('/lib/python3.12/site-packages/eduvis/core/engine.py');
            window.pyodideInstance.FS.writeFile('/lib/python3.12/site-packages/eduvis/core/engine.py', engineCode);
            window.pyodideInstance.FS.writeFile('/lib/python3.12/site-packages/eduvis/core/validator.py', validatorCode);
            window.pyodideInstance.FS.writeFile('/lib/python3.12/site-packages/eduvis/core/elements/generic.py', genericCode);
            window.pyodideInstance.FS.writeFile('/lib/python3.12/site-packages/eduvis/core/curriculum.py', curriculumCode);
            window.pyodideInstance.FS.writeFile('/lib/python3.12/site-packages/eduvis/core/constants.py', constantsCode);
            window.pyodideInstance.FS.writeFile('/lib/python3.12/site-packages/eduvis/core/__init__.py', coreInitCode);
            window.pyodideInstance.FS.writeFile('/lib/python3.12/site-packages/eduvis/__init__.py', mainInitCode);
            
            ensureDir('/lib/python3.12/site-packages/eduvis/renderers/svg/renderers_base.py');
            window.pyodideInstance.FS.writeFile('/lib/python3.12/site-packages/eduvis/renderers/svg/renderers_base.py', renderersBaseCode);
        } catch (syncErr) {
            console.warn(`Could not sync local v${version} code. Using wheel version.`, syncErr);
        }

        updateStatusCallback("Configuring Render Engine", "Importing Python libraries...");
        window.pyodideInstance.runPython(`
import yaml
import json
from eduvis.renderers.svg.spec_renderer import SVGSpecRenderer
from eduvis.cli import _element_title, _ZONE_MAP, _LAYOUT_FOR_ZONE, _element_to_spec, _PHASE_STYLE, _DIFFICULTY_STYLE, _ROLE_COLOR
from eduvis.core.engine import check_answer, evaluate_steps

# Global renderer instance
renderer = SVGSpecRenderer()

def _build_svg_spec_yaml(element: dict, elements_by_id: dict[str, dict] | None = None) -> str:
    # Resolve remediation_block question references if elements_by_id is provided
    if element.get("type") == "remediation_block" and elements_by_id:
        element = element.copy()
        review = element.get("review", {})
        if isinstance(review, dict):
            review = review.copy()
            q_id = review.get("source_question")
            if q_id and q_id in elements_by_id:
                review["question_spec"] = elements_by_id[q_id]
            element["review"] = review

    placement = element.get("placement") or {}
    if "zones" in element:
        zones = {}
        for z_name, z_elements in element["zones"].items():
            if isinstance(z_elements, list):
                zones[z_name] = [_element_to_spec(el) for el in z_elements]
            else:
                zones[z_name] = [_element_to_spec(z_elements)]
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

    # Differentiate starter / routine within independent_practice
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
    return yaml.dump(spec_dict, allow_unicode=True, default_flow_style=False)

def _merge_content_and_presentation(content_yaml_str, presentation_yaml_str):
    doc = yaml.safe_load(content_yaml_str)
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

def split_lesson_yaml(yaml_str):
    try:
        doc = yaml.safe_load(yaml_str)
    except Exception as e:
        return json.dumps({"content": yaml_str, "presentation": ""})
    
    if not isinstance(doc, dict):
        return json.dumps({"content": yaml_str, "presentation": ""})
    
    presentation_dict = {}
    if "presentation" in doc:
        presentation_dict = doc.pop("presentation")
    
    content_str = yaml.dump(doc, allow_unicode=True, default_flow_style=False, sort_keys=False)
    
    presentation_str = ""
    if presentation_dict:
        presentation_str = yaml.dump(presentation_dict, allow_unicode=True, default_flow_style=False, sort_keys=False)
        
    return json.dumps({"content": content_str, "presentation": presentation_str})

def parse_lesson_structure(content_yaml_str, presentation_yaml_str):
    try:
        doc = _merge_content_and_presentation(content_yaml_str, presentation_yaml_str)
        if isinstance(doc, dict) and "content" in doc:
            from eduvis.core import validate_lesson
            warnings = validate_lesson(doc)
            content = doc.get("content", [])
            slides = []
            for i, element in enumerate(content):
                if isinstance(element, dict):
                    slides.append({
                        "index": i,
                        "id": element.get("id", f"slide_{i+1}"),
                        "title": _element_title(element),
                        "type": element.get("type", "")
                    })
            return json.dumps({
                "type": "lesson",
                "title": (doc.get("lesson") or {}).get("title", "Lesson"),
                "curriculum": doc.get("curriculum", {}),
                "slides": slides,
                "presentation": doc.get("presentation"),
                "warnings": warnings
            })
        else:
            return json.dumps({"type": "slide"})
    except Exception as e:
        return json.dumps({"error": str(e)})

def render_slide_from_lesson(content_yaml_str, presentation_yaml_str, index, posting_group, step_index=None):
    doc = _merge_content_and_presentation(content_yaml_str, presentation_yaml_str)
    content = doc.get("content", [])
    elements_by_id = {el["id"]: el for el in content if isinstance(el, dict) and "id" in el}
    
    lesson_title = (doc.get("lesson") or {}).get("title", "")
    element = content[index]
    
    presentation = doc.get("presentation")
    if step_index is not None and isinstance(presentation, dict) and "slides" in presentation:
        slide_id = element.get("id")
        slide_pres = next((s for s in presentation["slides"] if s.get("id") == slide_id), None)
        if slide_pres and "reveals" in slide_pres:
            def filter_elem(el, reveals, step_idx):
                el_id = el.get("id")
                for rev in reveals:
                    target = rev.get("target")
                    if target == el_id and "steps" in rev:
                        steps = rev["steps"]
                        step = next((s for s in steps if s.get("index") == step_idx), None)
                        if step:
                            visible_indices = step.get("visible_items")
                            if visible_indices is not None:
                                el = el.copy()
                                for list_field in ["items", "bars", "rows", "plots", "highlight", "highlights"]:
                                    if list_field in el and isinstance(el[list_field], list):
                                        el[list_field] = [
                                            item for i, item in enumerate(el[list_field])
                                            if i in visible_indices
                                        ]
                if "zones" in el and isinstance(el["zones"], dict):
                     el = el.copy()
                     zones = {}
                     for z_name, z_elements in el["zones"].items():
                         if isinstance(z_elements, list):
                             zones[z_name] = [filter_elem(el_sub, reveals, step_idx) for el_sub in z_elements]
                         else:
                             zones[z_name] = filter_elem(z_elements, reveals, step_idx)
                     el["zones"] = zones
                return el
            
            element = filter_elem(element, slide_pres["reveals"], step_index)
            elements_by_id = {k: filter_elem(v, slide_pres["reveals"], step_index) for k, v in elements_by_id.items()}
            
    first_dict_idx = next((i for i, el in enumerate(content) if isinstance(el, dict)), None)
    if lesson_title and index == first_dict_idx:
        title = f"{lesson_title} - {_element_title(element)}"
    else:
        title = _element_title(element)
    svg_spec_yaml = _build_svg_spec_yaml(element, elements_by_id)
    
    return renderer.render(svg_spec_yaml, title=title, posting_group=posting_group)

def render_raw_slide(yaml_str, posting_group):
    return renderer.render(yaml_str, posting_group=posting_group)

def check_student_answer_py(element_yaml_str, student_answer):
    try:
        el = yaml.safe_load(element_yaml_str)
        res = check_answer(el, student_answer)
        return json.dumps(res)
    except Exception as e:
        return json.dumps({"error": str(e)})

def evaluate_student_steps_py(element_yaml_str, student_working_json):
    try:
        el = yaml.safe_load(element_yaml_str)
        working = json.loads(student_working_json)
        res = evaluate_steps(el, working)
        return json.dumps(res)
    except Exception as e:
        return json.dumps({"error": str(e)})

def get_element_json_py(content_yaml_str, index):
    try:
        doc = yaml.safe_load(content_yaml_str)
        content = doc.get("content", [])
        el = content[index]
        return json.dumps(el)
    except Exception as e:
        return json.dumps({"error": str(e)})

def get_lesson_analytics_py(content_yaml_str):
    try:
        doc = yaml.safe_load(content_yaml_str)
        content = doc.get("content", [])
        counts = {
            "procedural_fluency": 0,
            "conceptual_understanding": 0,
            "application": 0,
            "reasoning": 0,
            "unspecified": 0
        }
        total_questions = 0
        for el in content:
            if isinstance(el, dict) and el.get("type") in ("multiple_choice", "short_answer"):
                total_questions += 1
                placement = el.get("placement") or {}
                obj = placement.get("assessment_objective", "unspecified")
                if obj in counts:
                    counts[obj] += 1
                else:
                    counts["unspecified"] += 1
        return json.dumps({
            "total_questions": total_questions,
            "objectives": counts
        })
    except Exception as e:
        return json.dumps({"error": str(e)})

def get_element_objectives_py(content_yaml_str):
    try:
        doc = yaml.safe_load(content_yaml_str)
        content = doc.get("content", [])
        mapping = {}
        for el in content:
            if isinstance(el, dict) and "id" in el:
                placement = el.get("placement") or {}
                obj = placement.get("assessment_objective", "unspecified")
                mapping[el["id"]] = obj
        return json.dumps(mapping)
    except Exception as e:
        return json.dumps({})



def get_element_yaml_py(content_yaml_str, index):
    try:
        doc = yaml.safe_load(content_yaml_str)
        content = doc.get("content", [])
        el = content[index]
        return yaml.dump(el, allow_unicode=True, default_flow_style=False, sort_keys=False)
    except Exception as e:
        return ""

def get_curriculum_dashboard_py(content_yaml_str, curriculum_yaml_str):
    try:
        from eduvis.core.curriculum import CurriculumGraph
        graph_data = yaml.safe_load(curriculum_yaml_str) or {}
        graph = CurriculumGraph.from_dict(graph_data)
        doc = yaml.safe_load(content_yaml_str) or {}
        coverage = graph.analyze_coverage([doc])
        gaps = graph.detect_dependency_gaps(coverage["covered_concepts"])
        centrality = graph.analyze_centrality()
        
        return json.dumps({
            "concepts": [c.to_dict() for c in graph.concepts.values()],
            "skills": [s.to_dict() for s in graph.skills.values()],
            "misconceptions": [m.to_dict() for m in graph.misconceptions.values()],
            "dependencies": [d.to_dict() for d in graph.dependencies],
            "coverage": coverage,
            "gaps": gaps,
            "centrality": centrality
        })
    except Exception as e:
        return json.dumps({"error": str(e)})

def validate_curriculum_py(curriculum_yaml_str):
    try:
        from eduvis.core import validate_curriculum
        data = yaml.safe_load(curriculum_yaml_str) or {}
        warnings = validate_curriculum(data)
        return json.dumps({"warnings": warnings})
    except Exception as e:
        return json.dumps({"error": str(e)})
        `);

        updateStatusCallback("Ready", "All systems operational.");
        onReadyCallback();
    } catch (error) {
        console.error(error);
        updateStatusCallback("Initialization Failed", error.message);
    }
}

// Javascript wrappers for Python calls
function pySplitLessonYaml(yamlStr) {
    if (!window.pyodideInstance) return JSON.stringify({ content: yamlStr, presentation: "" });
    return window.pyodideInstance.globals.get("split_lesson_yaml")(yamlStr);
}

function pyParseLessonStructure(contentYaml, presentationYaml) {
    if (!window.pyodideInstance) throw new Error("Pyodide not loaded");
    return window.pyodideInstance.globals.get("parse_lesson_structure")(contentYaml, presentationYaml);
}

function pyRenderSlideFromLesson(contentYaml, presentationYaml, index, postingGroup, stepIndex) {
    if (!window.pyodideInstance) throw new Error("Pyodide not loaded");
    return window.pyodideInstance.globals.get("render_slide_from_lesson")(contentYaml, presentationYaml, index, postingGroup, stepIndex);
}

function pyRenderRawSlide(yamlStr, postingGroup) {
    if (!window.pyodideInstance) throw new Error("Pyodide not loaded");
    return window.pyodideInstance.globals.get("render_raw_slide")(yamlStr, postingGroup);
}

function pyCheckStudentAnswer(elementYamlStr, studentAnswer) {
    if (!window.pyodideInstance) throw new Error("Pyodide not loaded");
    return window.pyodideInstance.globals.get("check_student_answer_py")(elementYamlStr, studentAnswer);
}

function pyEvaluateStudentSteps(elementYamlStr, studentWorkingArray) {
    if (!window.pyodideInstance) throw new Error("Pyodide not loaded");
    const jsonStr = JSON.stringify(studentWorkingArray);
    return window.pyodideInstance.globals.get("evaluate_student_steps_py")(elementYamlStr, jsonStr);
}

function pyGetElementJson(contentYaml, index) {
    if (!window.pyodideInstance) throw new Error("Pyodide not loaded");
    return window.pyodideInstance.globals.get("get_element_json_py")(contentYaml, index);
}

function pyGetElementYaml(contentYaml, index) {
    if (!window.pyodideInstance) throw new Error("Pyodide not loaded");
    return window.pyodideInstance.globals.get("get_element_yaml_py")(contentYaml, index);
}

function pyGetLessonAnalytics(contentYaml) {
    if (!window.pyodideInstance) throw new Error("Pyodide not loaded");
    return window.pyodideInstance.globals.get("get_lesson_analytics_py")(contentYaml);
}

function pyGetElementObjectives(contentYaml) {
    if (!window.pyodideInstance) throw new Error("Pyodide not loaded");
    return window.pyodideInstance.globals.get("get_element_objectives_py")(contentYaml);
}

function pyGetCurriculumDashboard(contentYaml, curriculumYaml) {
    if (!window.pyodideInstance) throw new Error("Pyodide not loaded");
    return window.pyodideInstance.globals.get("get_curriculum_dashboard_py")(contentYaml, curriculumYaml);
}

function pyValidateCurriculum(curriculumYaml) {
    if (!window.pyodideInstance) throw new Error("Pyodide not loaded");
    return window.pyodideInstance.globals.get("validate_curriculum_py")(curriculumYaml);
}


