# EduVis: Architectural Layers & Schema Structure

This document details the layered architecture, static vs. dynamic schemas, and intermediate representation (IR) structure of the EduVis framework.

---

## Orthogonal Architecture Layers

EduVis separates content, dependencies, telemetry, and layout into four decoupled concern layers:

```mermaid
graph TD
    subgraph Knowledge Layer
        CurriculumGraph["Curriculum Graph<br>(Concepts, Skills, Misconceptions)"]
    end

    subgraph Assessment Layer
        AssessmentEngine["Assessment Engine<br>(Questions, Objectives, Validation)"]
    end

    subgraph Learner State Layer
        LearnerState["Learner State Model<br>(Mastery, Gaps, Telemetry)"]
    end

    subgraph Presentation Layer
        PresentationSpec["Presentation Layer<br>(Slides, Viewport Zoom, Narration)"]
    end

    CurriculumGraph --> LearnerState
    AssessmentEngine -->|Evidence Bridge| LearnerState
    LearnerState -->|Adaptive Routing| PresentationSpec
```

### 1. Knowledge Layer (Static Map)
* **Abstractions**: `curriculum.yaml`.
* **Purpose**: Defines concepts, skills, misconceptions, prerequisite dependencies, outcome mapping, and weights (exam relevance, graph centrality).
* **Properties**: Static, read-only at runtime. Shared globally across multiple lessons.

### 2. Assessment Layer (Testing Logic)
* **Abstractions**: Question elements (`multiple_choice`, `short_answer`, `structured_response`).
* **Purpose**: Declares symbolic correctness, misconception detectors, step-by-step rubrics, partial credit mappings, and Error Carry Forward (ECF) dependencies.
* **Properties**: Client-side checkable (no LLM required at runtime).

### 3. Learner State Layer (Dynamic Context)
* **Abstractions**: `learner_state.json`.
* **Purpose**: Tracks transient concept and skill mastery, active/remediated misconceptions, confidence ratings, and spaced-repetition (SM-2) schedules.
* **Properties**: State is strictly decoupled from content schemas. Updated dynamically via stateless transitions.

### 4. Presentation Layer (Delivery Medium)
* **Abstractions**: `presentation.yaml`.
* **Purpose**: Controls reveal sequencing, audio narration triggers, zoom/pan annotations, and advance modes (manual/auto).
* **Properties**: Maintained as a sidecar, allowing content to render as SVG, React components, PDFs, or slides without altering pedagogical meaning.

---

## Schema Categorization

EduVis organizes its schema files into three distinct functional groups:

| Group | Schema File | Role |
|---|---|---|
| **Core Specifications (Static)** | `curriculum.schema.json` <br> `lesson.schema.json` <br> `presentation.schema.json` | Used by content designers and compiler front-ends to author static curriculum maps, slide sequences, and presentation details. |
| **Runtime Sidecars (Dynamic)** | `learner_state.schema.json` <br> `telemetry_event.schema.json` <br> `assessment_event.schema.json` | Used by tutoring and player runtimes to capture student attempts, trace mastery updates, and record session logs. |
| **Derived Artifacts (Generated)** | `assessment_paper.schema.json` <br> `paper_blueprint.schema.json` | Generated programmatically (e.g. via Graph-driven paper assembly) to represent exam blueprints and custom-compiled assessments. |

---

## The Compiler & IR Model

EduVis operates under the mental model of a **Curriculum Compiler**. Instead of compiling programming code into machine code, it compiles pedagogical graphs and lesson structures into multiple delivery formats.

```text
Syllabus / Concept Graph
          ↓
  [Curriculum Compiler]
          ↓
  EduVis Schemas (IR) — curriculum.yaml, lesson.yaml, presentation.yaml
          ↓
  [Renderer / Player Engines]
          ↓
  Web Lessons · Voice Tutoring · Interactive Slide Decks · Exam PDFs
```

In this pipeline, **EduVis serves as the Pedagogical Intermediate Representation (IR)**. The relationship between the packages forms a coherent ecosystem inspired by compiler/IDE structures like **LLVM/Clang/LLDB** or **TypeScript/VS Code**:

```text
  ┌─────────────────────────────────────────────────────────────┐
  │                        EduVis Studio                        │
  │                  (Visual IDE / Orchestration)               │
  └──────────────────────────────┬──────────────────────────────┘
                                 │ orchestrates
                                 ▼
  ┌─────────────────────────────────────────────────────────────┐
  │                         EduVis Core                         │
  │                 (Parser, Validator, & Compiler)             │
  │                                                             │
  │     Syllabus  ──[Planners]──► Specification (IR) ──► Render │
  └─────────────────────────────────────────────────────────────┘
```

*   **EduVis Core (The Language & IR)**: Defines the semantic schemas and provides the stateless validation rules and parser engine. Akin to **LLVM IR** or the **TypeScript Compiler (tsc)**, it represents the standardized grammar and validation, remaining highly stable and backward-compatible.
*   **The Planners & Assembler (The Compiler)**: Python compilation stages (Curriculum Planner, Lesson Planner, Assessment Assembler) that compile educational intentions down into concrete specifications, akin to **Clang** code generators.
*   **EduVis Studio (The IDE)**: Sits directly on top of this stateless infrastructure. It acts as the local, browser-based authoring and analysis platform:
    1. **State Orchestration**: It runs the Python compiler algorithms, planners, and validators locally in the browser via Pyodide/WASM.
    2. **Visual Projections**: It transforms the educational specification dynamically into multiple interactive views (e.g. concept dependency graphs, slide storyboard progressions, and mastery overlays).
    3. **Validation Loops**: It runs diagnostic scripts directly in client background workers, giving content authors immediate feedback on pedagogical anti-patterns (such as missing prerequisites or unbalanced lesson phases).
