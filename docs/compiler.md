# EduVis: Curriculum Compiler Pipeline (v1.0)

This document describes the design, stages, execution model, and CLI usage of the **EduVis v1.0 Curriculum Compiler Pipeline**.

---

## 1. Architectural Concept

EduVis operates under the mental model of a **Curriculum Compiler**. The compiler pipeline transforms high-level syllabus documents and graph configurations into multiple delivery formats (web lessons, structured slide presentations, and assessment papers) using EduVis YAML schemas as the **Pedagogical Intermediate Representation (IR)**.

```text
Syllabus / Concept Graph
          ↓
  [Curriculum Planner]  → compiles syllabus.yaml into curriculum.yaml graph
          ↓
  [Lesson Planner]      → compiles graph path into lesson.yaml
          ↓
  [Assessment Assembler]→ compiles lesson elements into assessment_paper.yaml
          ↓
  [Presentation Compiler]→ compiles layout and reveals into presentation.yaml
          ↓
  Validated Production Assets (Web, PDF, interactive decks)
```

---

## 2. Pipeline Execution Flow

Each compiler run is managed by an in-memory `CompilationContext` object that flows sequentially through a pipeline of decoupled stages.

### Core Pipeline Components:
*   **`CompilationContext`**: Stores input/output data (curriculum graphs, generated lessons, assessment papers, slide configurations), progress logs, and errors.
*   **`CompilerStage`**: Base class representing an interchangeable step in the compiler pipeline.
*   **`CompilerPipeline`**: Coordinative orchestrator executing registered compiler stages sequentially and failing-fast on validation errors.
*   **`QAEngine`**: Dynamic gatekeeper wrapping all structural, graph, and pedagogical validations. It runs validation checks at the end of each stage.

---

## 3. Decoupled Stages

The compiler defines four specialized stages under `eduvis.compiler`:

### CurriculumPlanner
Translates standard syllabus specifications or outline definitions into a validated `CurriculumGraph` (schema: `curriculum.schema.json`).
*   **Validations**: Schema structure check and cycle detection in prerequisite chains.

### LessonPlanner
Translates a set of target concept codes into a scaffolded, pedagogy-compliant lesson YAML draft.
*   **Inputs**: Compiled `CurriculumGraph` and concept codes list.
*   **Validations**: Structural lesson schema checks, pedagogy sequence flags (like `confidence_first`, `explain_why`), and element placement correctness.

### AssessmentAssembler
Blueprints exam specifications and selects questions aligning to concept skills and cognitive weights.
*   **Inputs**: Blends concept relevance (70% exam relevance, 30% centrality weight) to establish targets.
*   **Selector**: Greedily selects questions from the generated lesson question pool to fit a time/marks budget.

### PresentationCompiler
Compiles slide layouts, reveal timings, and viewport configurations embedded inline into the lesson document.
*   **Narration**: Automatically derives text-to-speech audio narration cues based on element text, captions, or question fields.

---

## 4. CLI Compile Stage Commands

The compilation pipeline is exposed via decoupled commands under the Click group `eduvis compile`:

### 1. Compile Curriculum
Compiles a syllabus text/YAML outline file into a validated curriculum graph YAML:
```bash
uv run eduvis compile curriculum syllabus.yaml -o curriculum.yaml
```

### 2. Compile Lesson
Generates a lesson draft for specified concepts using a curriculum graph:
```bash
uv run eduvis compile lesson curriculum.yaml integers negative_numbers -o lesson.yaml
```

### 3. Compile Assessment
Generates a paper blueprint and assemblies an assessment paper from a lesson element pool:
```bash
uv run eduvis compile assessment curriculum.yaml --lesson-file lesson.yaml --marks 20 -o test_paper.yaml
```

### 4. Compile Presentation
Generates slide presentation viewport mappings and narration sidecars directly into a lesson spec:
```bash
uv run eduvis compile presentation lesson.yaml -o lesson_with_presentation.yaml
```
